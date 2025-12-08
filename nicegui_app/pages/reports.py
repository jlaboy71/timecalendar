"""Reports page - Personal reports for all users, Team reports for managers/admins."""
import asyncio
from nicegui import ui, app
from src.database import get_db
from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.services.report_service import ReportService
from datetime import date, datetime
from io import StringIO
import csv
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode


def reports_page():
    """Reports page with personal and team reports."""

    apply_dark_mode()

    # Check if user is logged in
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # State for filters
    current_year = date.today().year
    is_admin_only = user_role in ['admin', 'superadmin']
    filter_state = {
        'year': current_year,
        'department_id': None,
        # Admins don't have personal PTO, so default to team reports
        'report_type': 'team_balance' if is_admin_only else 'my_history',
        'status_filter': 'all'  # 'all', 'approved', 'pending', 'denied'
    }

    # Main container
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        # Header with greeting (no back arrow - we'll add button at bottom)
        page_header(title='REPORTS', show_back=False)

        # Report type selector
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label('Select Report Type').classes('text-lg font-semibold mb-3')

            with ui.column().classes('gap-3'):
                # Personal Reports Section (NOT for admin/superadmin - they don't have PTO)
                if not is_admin_only:
                    ui.label('My Reports').classes('text-sm font-semibold uppercase opacity-60')
                    with ui.row().classes('gap-2 flex-wrap'):
                        my_history_btn = ui.button('My PTO History', on_click=lambda: switch_report('my_history')).props('color=primary')
                        my_balance_btn = ui.button('My Balance Summary', on_click=lambda: switch_report('my_balance')).props('outline')
                        my_calendar_btn = ui.button('My Year at a Glance', on_click=lambda: switch_report('my_calendar')).props('outline')

                # Team Reports Section (managers/admins only)
                if is_manager_or_admin:
                    if not is_admin_only:
                        ui.separator().classes('my-2')
                    ui.label('Team Reports').classes('text-sm font-semibold uppercase opacity-60')
                    with ui.row().classes('gap-2 flex-wrap'):
                        # For admins, default team_balance is selected
                        team_balance_btn = ui.button('Team Balance Summary', on_click=lambda: switch_report('team_balance')).props('color=primary' if is_admin_only else 'outline')
                        team_usage_btn = ui.button('Team Usage Report', on_click=lambda: switch_report('team_usage')).props('outline')
                        audit_btn = ui.button('Audit Log', on_click=lambda: switch_report('audit')).props('outline')

        # Filters section
        filters_card = ui.card().classes('w-full mb-4 p-4')

        # Report content area
        report_container = ui.column().classes('w-full')

        # Button references for styling
        all_buttons = {}
        if not is_admin_only:
            all_buttons.update({
                'my_history': my_history_btn,
                'my_balance': my_balance_btn,
                'my_calendar': my_calendar_btn,
            })
        if is_manager_or_admin:
            all_buttons.update({
                'team_balance': team_balance_btn,
                'team_usage': team_usage_btn,
                'audit': audit_btn,
            })

        def switch_report(report_type):
            filter_state['report_type'] = report_type
            # Update button styles
            for btn_type, btn in all_buttons.items():
                if btn_type == report_type:
                    btn.props('color=primary')
                else:
                    btn.props('outline')
            render_filters()
            render_report()

        def render_filters():
            filters_card.clear()
            with filters_card:
                with ui.row().classes('w-full gap-4 items-end flex-wrap'):
                    # Year filter (common to all reports)
                    years = list(range(current_year - 2, current_year + 2))
                    ui.select(
                        {y: str(y) for y in years},
                        label='Year',
                        value=filter_state['year'],
                        on_change=lambda e: update_filter('year', e.value)
                    ).classes('w-32')

                    # Status filter for history reports
                    if filter_state['report_type'] in ['my_history', 'team_usage']:
                        ui.select(
                            {'all': 'All Status', 'approved': 'Approved', 'pending': 'Pending', 'denied': 'Denied'},
                            label='Status',
                            value=filter_state['status_filter'],
                            on_change=lambda e: update_filter('status_filter', e.value)
                        ).classes('w-36')

                    # Department filter (team reports only)
                    if filter_state['report_type'] in ['team_balance', 'team_usage', 'audit']:
                        db = next(get_db())
                        try:
                            departments = db.query(Department).filter(Department.is_active == True).all()
                            dept_options = {None: 'All Departments'}
                            dept_options.update({d.id: d.name for d in departments})
                            ui.select(
                                dept_options,
                                label='Department',
                                value=filter_state['department_id'],
                                on_change=lambda e: update_filter('department_id', e.value)
                            ).classes('w-48')
                        finally:
                            db.close()

                    # Refresh button
                    ui.button('Refresh', icon='refresh', on_click=render_report).props('outline')

                    # Export dropdown with multiple options
                    with ui.dropdown_button('Export', icon='download', auto_close=True).props('color=secondary') as export_dropdown:
                        async def handle_export_csv():
                            export_dropdown.close()
                            await asyncio.sleep(0.1)
                            export_csv()

                        async def handle_print_preview():
                            export_dropdown.close()
                            await asyncio.sleep(0.1)
                            show_print_preview()

                        async def handle_download_pdf():
                            export_dropdown.close()
                            await asyncio.sleep(0.1)
                            download_pdf()

                        async def handle_email_dialog():
                            export_dropdown.close()
                            await asyncio.sleep(0.1)
                            show_email_dialog()

                        ui.item('Download CSV', on_click=handle_export_csv)
                        ui.item('Print Preview', on_click=handle_print_preview)
                        ui.item('Download PDF', on_click=handle_download_pdf)
                        ui.item('Email Report', on_click=handle_email_dialog)

        def update_filter(key, value):
            filter_state[key] = value
            render_report()

        def render_report():
            report_container.clear()
            with report_container:
                report_type = filter_state['report_type']
                if report_type == 'my_history':
                    render_my_history()
                elif report_type == 'my_balance':
                    render_my_balance()
                elif report_type == 'my_calendar':
                    render_my_calendar()
                elif report_type == 'team_balance':
                    render_team_balance()
                elif report_type == 'team_usage':
                    render_team_usage()
                elif report_type == 'audit':
                    render_audit_report()

        def render_my_history():
            """Render personal PTO history with notes/descriptions."""
            db = next(get_db())
            try:
                query = db.query(PTORequest).filter(
                    PTORequest.user_id == user_id,
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31)
                )

                if filter_state['status_filter'] != 'all':
                    query = query.filter(PTORequest.status == filter_state['status_filter'])

                requests = query.order_by(PTORequest.start_date.desc()).all()

                with ui.card().classes('w-full'):
                    ui.label(f'My PTO History - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not requests:
                        ui.label('No PTO requests found for this period.').classes('opacity-60')
                        return

                    # Summary stats
                    total_days = sum(float(r.total_days or 0) for r in requests if r.status == 'approved')
                    pending_days = sum(float(r.total_days or 0) for r in requests if r.status == 'pending')

                    with ui.row().classes('w-full gap-4 mb-4 flex-wrap'):
                        with ui.card().classes('p-3 border-l-4 border-green-500'):
                            ui.label('Approved').classes('text-sm opacity-70')
                            ui.label(f'{total_days:.1f} days').classes('text-xl font-bold text-green-600')
                        with ui.card().classes('p-3 border-l-4 border-amber-500'):
                            ui.label('Pending').classes('text-sm opacity-70')
                            ui.label(f'{pending_days:.1f} days').classes('text-xl font-bold text-amber-600')
                        with ui.card().classes('p-3 border-l-4 border-blue-500'):
                            ui.label('Total Requests').classes('text-sm opacity-70')
                            ui.label(f'{len(requests)}').classes('text-xl font-bold text-blue-600')

                    # Detailed list with descriptions
                    for req in requests:
                        status_colors = {
                            'approved': 'border-green-500',
                            'pending': 'border-amber-500',
                            'denied': 'border-red-500',
                            'cancelled': 'border-gray-400'
                        }
                        status_icons = {
                            'approved': 'check_circle',
                            'pending': 'schedule',
                            'denied': 'cancel',
                            'cancelled': 'block'
                        }
                        border_color = status_colors.get(req.status, 'border-gray-300')

                        with ui.card().classes(f'w-full mb-3 p-4 border-l-4 {border_color}'):
                            with ui.row().classes('w-full justify-between items-start'):
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon(status_icons.get(req.status, 'event')).classes('text-lg')
                                        ui.label(req.pto_type.title()).classes('font-semibold')
                                        ui.badge(req.status.upper()).props(
                                            f'color={"green" if req.status == "approved" else "amber" if req.status == "pending" else "red"}'
                                        )

                                    # Dates
                                    if req.start_date == req.end_date:
                                        date_str = req.start_date.strftime('%B %d, %Y')
                                    else:
                                        date_str = f'{req.start_date.strftime("%b %d")} - {req.end_date.strftime("%b %d, %Y")}'
                                    ui.label(date_str).classes('text-sm')

                                    # Notes (personal)
                                    if req.notes:
                                        with ui.row().classes('items-start gap-2 mt-2 p-2 rounded').style('background: rgba(0,0,0,0.05)'):
                                            ui.icon('notes', color='grey').classes('text-sm')
                                            ui.label(req.notes).classes('text-sm italic')

                                with ui.column().classes('items-end'):
                                    ui.label(f'{float(req.total_days or 0):.1f} days').classes('font-bold')

            finally:
                db.close()

        def render_my_balance():
            """Render personal balance summary."""
            db = next(get_db())
            try:
                balance = db.query(PTOBalance).filter(
                    PTOBalance.user_id == user_id,
                    PTOBalance.year == filter_state['year']
                ).first()

                with ui.card().classes('w-full'):
                    ui.label(f'My Balance Summary - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not balance:
                        ui.label('No balance record found for this year.').classes('opacity-60')
                        return

                    # Helper to format hours as days (8 hours = 1 day)
                    def hours_to_days(hours):
                        days = hours / 8
                        return f'{days:.1f}'

                    # Helper to create a balance stat column
                    def balance_stat(value_days, value_hrs, label, color_class=''):
                        with ui.column().classes('items-center flex-1'):
                            ui.label(f'{value_days} days').classes(f'text-xl font-bold {color_class}')
                            ui.label(f'({value_hrs:.0f} hrs)').classes('text-xs opacity-50')
                            ui.label(label).classes('text-xs opacity-60 mt-1')

                    # Balance cards - all same structure with 3 columns: Total, Used, Available
                    with ui.row().classes('w-full gap-4 flex-wrap items-stretch'):
                        # Vacation
                        vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                        vac_used = float(balance.vacation_used or 0)
                        vac_pending = float(balance.vacation_pending or 0)
                        vac_avail = vac_total - vac_used - vac_pending

                        with ui.card().classes('flex-1 min-w-64 p-4 border-l-4 border-blue-500'):
                            ui.label('Vacation').classes('text-lg font-semibold mb-3')
                            with ui.row().classes('w-full justify-around gap-2'):
                                balance_stat(hours_to_days(vac_total), vac_total, 'Total')
                                balance_stat(hours_to_days(vac_used), vac_used, 'Used', 'text-red-500')
                                avail_color = 'text-green-600' if vac_avail > 0 else 'text-red-600'
                                balance_stat(hours_to_days(vac_avail), vac_avail, 'Available', avail_color)
                            # Show pending if any
                            if vac_pending > 0:
                                ui.label(f'({hours_to_days(vac_pending)} days pending approval)').classes('text-xs text-amber-500 mt-2 text-center w-full')

                        # Sick
                        sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                        sick_used = float(balance.sick_used or 0)
                        sick_avail = sick_total - sick_used

                        with ui.card().classes('flex-1 min-w-64 p-4 border-l-4 border-green-500'):
                            ui.label('Sick').classes('text-lg font-semibold mb-3')
                            with ui.row().classes('w-full justify-around gap-2'):
                                balance_stat(hours_to_days(sick_total), sick_total, 'Total')
                                balance_stat(hours_to_days(sick_used), sick_used, 'Used', 'text-red-500')
                                avail_color = 'text-green-600' if sick_avail > 0 else 'text-red-600'
                                balance_stat(hours_to_days(sick_avail), sick_avail, 'Available', avail_color)

                        # Personal
                        personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                        personal_used = float(balance.personal_used or 0)
                        personal_avail = personal_total - personal_used

                        with ui.card().classes('flex-1 min-w-64 p-4 border-l-4 border-purple-500'):
                            ui.label('Personal').classes('text-lg font-semibold mb-3')
                            with ui.row().classes('w-full justify-around gap-2'):
                                balance_stat(hours_to_days(personal_total), personal_total, 'Total')
                                balance_stat(hours_to_days(personal_used), personal_used, 'Used', 'text-red-500')
                                avail_color = 'text-green-600' if personal_avail > 0 else 'text-red-600'
                                balance_stat(hours_to_days(personal_avail), personal_avail, 'Available', avail_color)

            finally:
                db.close()

        def render_my_calendar():
            """Render a year-at-a-glance view of personal PTO."""
            db = next(get_db())
            try:
                requests = db.query(PTORequest).filter(
                    PTORequest.user_id == user_id,
                    PTORequest.status == 'approved',
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31)
                ).order_by(PTORequest.start_date).all()

                with ui.card().classes('w-full'):
                    ui.label(f'My Year at a Glance - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not requests:
                        ui.label('No approved PTO for this year.').classes('opacity-60')
                        return

                    # Group by month
                    months = {}
                    for req in requests:
                        month_key = req.start_date.strftime('%B')
                        if month_key not in months:
                            months[month_key] = []
                        months[month_key].append(req)

                    # Display by month
                    for month_name, month_requests in months.items():
                        with ui.expansion(f'{month_name} ({len(month_requests)} requests)', icon='event').classes('w-full mb-2'):
                            for req in month_requests:
                                type_colors = {
                                    'vacation': 'blue',
                                    'sick': 'green',
                                    'personal': 'purple'
                                }
                                color = type_colors.get(req.pto_type.lower(), 'grey')

                                with ui.row().classes('w-full p-2 items-center gap-3 border-b'):
                                    ui.badge(req.pto_type.title(), color=color)
                                    if req.start_date == req.end_date:
                                        ui.label(req.start_date.strftime('%d')).classes('font-medium')
                                    else:
                                        ui.label(f'{req.start_date.strftime("%d")} - {req.end_date.strftime("%d")}').classes('font-medium')
                                    ui.label(f'{float(req.total_days or 0):.1f} days').classes('opacity-70')
                                    if req.notes:
                                        ui.label(f'"{req.notes}"').classes('text-sm italic opacity-60 flex-1')

            finally:
                db.close()

        def render_team_balance():
            """Render team balance summary (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            db = next(get_db())
            try:
                query = db.query(User, PTOBalance).outerjoin(
                    PTOBalance,
                    (PTOBalance.user_id == User.id) & (PTOBalance.year == filter_state['year'])
                ).filter(User.is_active == True)

                if filter_state['department_id']:
                    query = query.filter(User.department_id == filter_state['department_id'])

                results = query.order_by(User.last_name, User.first_name).all()

                with ui.card().classes('w-full'):
                    ui.label(f'Team Balance Summary - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not results:
                        ui.label('No employees found.').classes('opacity-60')
                        return

                    columns = [
                        {'name': 'name', 'label': 'Employee', 'field': 'name', 'sortable': True, 'align': 'left'},
                        {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                        {'name': 'vacation_total', 'label': 'Vac Total', 'field': 'vacation_total', 'sortable': True},
                        {'name': 'vacation_used', 'label': 'Vac Used', 'field': 'vacation_used', 'sortable': True},
                        {'name': 'vacation_available', 'label': 'Vac Avail', 'field': 'vacation_available', 'sortable': True},
                        {'name': 'sick_total', 'label': 'Sick Total', 'field': 'sick_total', 'sortable': True},
                        {'name': 'sick_used', 'label': 'Sick Used', 'field': 'sick_used', 'sortable': True},
                        {'name': 'personal_total', 'label': 'Pers Total', 'field': 'personal_total', 'sortable': True},
                        {'name': 'personal_used', 'label': 'Pers Used', 'field': 'personal_used', 'sortable': True},
                    ]

                    rows = []
                    for user_obj, balance in results:
                        dept_name = user_obj.department.name if user_obj.department else 'No Dept'

                        if balance:
                            vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                            vac_used = float(balance.vacation_used or 0)
                            vac_pending = float(balance.vacation_pending or 0)
                            vac_avail = vac_total - vac_used - vac_pending
                            sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                            sick_used = float(balance.sick_used or 0)
                            personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                            personal_used = float(balance.personal_used or 0)
                        else:
                            vac_total = vac_used = vac_avail = sick_total = sick_used = personal_total = personal_used = 0

                        rows.append({
                            'id': user_obj.id,
                            'name': f'{user_obj.first_name} {user_obj.last_name}',
                            'department': dept_name,
                            'vacation_total': f'{vac_total:.1f}',
                            'vacation_used': f'{vac_used:.1f}',
                            'vacation_available': f'{vac_avail:.1f}',
                            'sick_total': f'{sick_total:.1f}',
                            'sick_used': f'{sick_used:.1f}',
                            'personal_total': f'{personal_total:.1f}',
                            'personal_used': f'{personal_used:.1f}',
                        })

                    ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                    ui.label(f'Total: {len(rows)} employees').classes('mt-2 opacity-60')

            finally:
                db.close()

        def render_team_usage():
            """Render team usage report (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            db = next(get_db())
            try:
                query = db.query(PTORequest, User).join(
                    User, PTORequest.user_id == User.id
                ).filter(
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31)
                )

                if filter_state['status_filter'] != 'all':
                    query = query.filter(PTORequest.status == filter_state['status_filter'])
                else:
                    query = query.filter(PTORequest.status == 'approved')

                if filter_state['department_id']:
                    query = query.filter(User.department_id == filter_state['department_id'])

                results = query.order_by(PTORequest.start_date.desc()).all()

                with ui.card().classes('w-full'):
                    ui.label(f'Team Usage Report - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not results:
                        ui.label('No requests found for this period.').classes('opacity-60')
                        return

                    # Summary by type
                    type_summary = {}
                    for request, user_obj in results:
                        pto_type = request.pto_type.upper()
                        if pto_type not in type_summary:
                            type_summary[pto_type] = {'count': 0, 'days': 0}
                        type_summary[pto_type]['count'] += 1
                        type_summary[pto_type]['days'] += float(request.total_days or 0)

                    with ui.row().classes('w-full gap-4 mb-4 flex-wrap'):
                        for pto_type, stats in sorted(type_summary.items()):
                            with ui.card().classes('p-3'):
                                ui.label(pto_type.title()).classes('font-semibold')
                                ui.label(f'{stats["count"]} requests').classes('text-sm opacity-70')
                                ui.label(f'{stats["days"]:.1f} days').classes('text-lg font-bold')

                    columns = [
                        {'name': 'employee', 'label': 'Employee', 'field': 'employee', 'sortable': True, 'align': 'left'},
                        {'name': 'type', 'label': 'Type', 'field': 'type', 'sortable': True, 'align': 'left'},
                        {'name': 'start_date', 'label': 'Start', 'field': 'start_date', 'sortable': True},
                        {'name': 'end_date', 'label': 'End', 'field': 'end_date', 'sortable': True},
                        {'name': 'days', 'label': 'Days', 'field': 'days', 'sortable': True},
                        {'name': 'status', 'label': 'Status', 'field': 'status', 'sortable': True},
                    ]

                    rows = []
                    for request, user_obj in results:
                        rows.append({
                            'id': request.id,
                            'employee': f'{user_obj.first_name} {user_obj.last_name}',
                            'type': request.pto_type.title(),
                            'start_date': request.start_date.strftime('%Y-%m-%d'),
                            'end_date': request.end_date.strftime('%Y-%m-%d'),
                            'days': f'{float(request.total_days or 0):.1f}',
                            'status': request.status.title(),
                        })

                    ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                    ui.label(f'Total: {len(rows)} requests').classes('mt-2 opacity-60')

            finally:
                db.close()

        def render_audit_report():
            """Render audit log (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            db = next(get_db())
            try:
                query = db.query(PTORequest, User).join(
                    User, PTORequest.user_id == User.id
                ).filter(
                    PTORequest.status.in_(['approved', 'denied']),
                    PTORequest.updated_at >= date(filter_state['year'], 1, 1)
                )

                if filter_state['department_id']:
                    query = query.filter(User.department_id == filter_state['department_id'])

                results = query.order_by(PTORequest.updated_at.desc()).limit(100).all()

                with ui.card().classes('w-full'):
                    ui.label(f'Audit Log - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not results:
                        ui.label('No audit records found for this period.').classes('opacity-60')
                        return

                    columns = [
                        {'name': 'date', 'label': 'Date', 'field': 'date', 'sortable': True},
                        {'name': 'employee', 'label': 'Employee', 'field': 'employee', 'sortable': True, 'align': 'left'},
                        {'name': 'type', 'label': 'Type', 'field': 'type', 'sortable': True, 'align': 'left'},
                        {'name': 'action', 'label': 'Action', 'field': 'action', 'sortable': True},
                        {'name': 'approved_by', 'label': 'By', 'field': 'approved_by', 'sortable': True, 'align': 'left'},
                    ]

                    approver_ids = [r.approved_by for r, _ in results if r.approved_by]
                    approvers = {u.id: f'{u.first_name} {u.last_name}'
                                for u in db.query(User).filter(User.id.in_(approver_ids)).all()}

                    rows = []
                    for request, user_obj in results:
                        rows.append({
                            'id': request.id,
                            'date': request.updated_at.strftime('%Y-%m-%d %H:%M') if request.updated_at else '-',
                            'employee': f'{user_obj.first_name} {user_obj.last_name}',
                            'type': request.pto_type.title(),
                            'action': request.status.upper(),
                            'approved_by': approvers.get(request.approved_by, 'Auto') if request.approved_by else '-',
                        })

                    ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                    ui.label(f'Showing {len(rows)} most recent actions').classes('mt-2 opacity-60')

            finally:
                db.close()

        def export_csv():
            """Export current report to CSV."""
            db = next(get_db())
            try:
                output = StringIO()
                writer = csv.writer(output)
                report_type = filter_state['report_type']

                if report_type == 'my_history':
                    # Personal history with notes
                    writer.writerow(['Type', 'Start Date', 'End Date', 'Days', 'Status', 'Notes/Reason'])

                    query = db.query(PTORequest).filter(
                        PTORequest.user_id == user_id,
                        PTORequest.start_date >= date(filter_state['year'], 1, 1),
                        PTORequest.end_date <= date(filter_state['year'], 12, 31)
                    )
                    if filter_state['status_filter'] != 'all':
                        query = query.filter(PTORequest.status == filter_state['status_filter'])

                    for req in query.order_by(PTORequest.start_date.desc()).all():
                        writer.writerow([
                            req.pto_type.title(),
                            req.start_date.strftime('%Y-%m-%d'),
                            req.end_date.strftime('%Y-%m-%d'),
                            f'{float(req.total_days or 0):.1f}',
                            req.status.title(),
                            req.notes or ''
                        ])

                    filename = f'my_pto_history_{filter_state["year"]}.csv'

                elif report_type == 'my_balance':
                    writer.writerow(['Type', 'Total', 'Used', 'Pending', 'Available'])

                    balance = db.query(PTOBalance).filter(
                        PTOBalance.user_id == user_id,
                        PTOBalance.year == filter_state['year']
                    ).first()

                    if balance:
                        vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                        vac_used = float(balance.vacation_used or 0)
                        vac_pending = float(balance.vacation_pending or 0)
                        writer.writerow(['Vacation', f'{vac_total:.1f}', f'{vac_used:.1f}', f'{vac_pending:.1f}', f'{vac_total - vac_used - vac_pending:.1f}'])

                        sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                        sick_used = float(balance.sick_used or 0)
                        writer.writerow(['Sick', f'{sick_total:.1f}', f'{sick_used:.1f}', '0.0', f'{sick_total - sick_used:.1f}'])

                        personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                        personal_used = float(balance.personal_used or 0)
                        writer.writerow(['Personal', f'{personal_total:.1f}', f'{personal_used:.1f}', '0.0', f'{personal_total - personal_used:.1f}'])

                    filename = f'my_balance_{filter_state["year"]}.csv'

                elif report_type == 'my_calendar':
                    writer.writerow(['Month', 'Type', 'Start', 'End', 'Days', 'Notes'])

                    requests = db.query(PTORequest).filter(
                        PTORequest.user_id == user_id,
                        PTORequest.status == 'approved',
                        PTORequest.start_date >= date(filter_state['year'], 1, 1),
                        PTORequest.end_date <= date(filter_state['year'], 12, 31)
                    ).order_by(PTORequest.start_date).all()

                    for req in requests:
                        writer.writerow([
                            req.start_date.strftime('%B'),
                            req.pto_type.title(),
                            req.start_date.strftime('%Y-%m-%d'),
                            req.end_date.strftime('%Y-%m-%d'),
                            f'{float(req.total_days or 0):.1f}',
                            req.notes or ''
                        ])

                    filename = f'my_year_glance_{filter_state["year"]}.csv'

                elif report_type == 'team_balance':
                    writer.writerow(['Employee', 'Department', 'Vac Total', 'Vac Used', 'Vac Avail',
                                    'Sick Total', 'Sick Used', 'Personal Total', 'Personal Used'])

                    query = db.query(User, PTOBalance).outerjoin(
                        PTOBalance,
                        (PTOBalance.user_id == User.id) & (PTOBalance.year == filter_state['year'])
                    ).filter(User.is_active == True)

                    if filter_state['department_id']:
                        query = query.filter(User.department_id == filter_state['department_id'])

                    for user_obj, balance in query.all():
                        dept_name = user_obj.department.name if user_obj.department else 'No Dept'
                        if balance:
                            vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                            vac_used = float(balance.vacation_used or 0)
                            vac_pending = float(balance.vacation_pending or 0)
                            vac_avail = vac_total - vac_used - vac_pending
                            sick_total = float(balance.sick_total or 0)
                            sick_used = float(balance.sick_used or 0)
                            personal_total = float(balance.personal_total or 0)
                            personal_used = float(balance.personal_used or 0)
                        else:
                            vac_total = vac_used = vac_avail = sick_total = sick_used = personal_total = personal_used = 0

                        writer.writerow([
                            f'{user_obj.first_name} {user_obj.last_name}',
                            dept_name,
                            f'{vac_total:.1f}', f'{vac_used:.1f}', f'{vac_avail:.1f}',
                            f'{sick_total:.1f}', f'{sick_used:.1f}',
                            f'{personal_total:.1f}', f'{personal_used:.1f}'
                        ])

                    filename = f'team_balance_{filter_state["year"]}.csv'

                elif report_type == 'team_usage':
                    writer.writerow(['Employee', 'Type', 'Start', 'End', 'Days', 'Status'])

                    query = db.query(PTORequest, User).join(
                        User, PTORequest.user_id == User.id
                    ).filter(
                        PTORequest.status == 'approved',
                        PTORequest.start_date >= date(filter_state['year'], 1, 1),
                        PTORequest.end_date <= date(filter_state['year'], 12, 31)
                    )

                    if filter_state['department_id']:
                        query = query.filter(User.department_id == filter_state['department_id'])

                    for request, user_obj in query.all():
                        writer.writerow([
                            f'{user_obj.first_name} {user_obj.last_name}',
                            request.pto_type.title(),
                            request.start_date.strftime('%Y-%m-%d'),
                            request.end_date.strftime('%Y-%m-%d'),
                            f'{float(request.total_days or 0):.1f}',
                            request.status.title()
                        ])

                    filename = f'team_usage_{filter_state["year"]}.csv'

                elif report_type == 'audit':
                    writer.writerow(['Date', 'Employee', 'Type', 'Action', 'Approved By'])

                    query = db.query(PTORequest, User).join(
                        User, PTORequest.user_id == User.id
                    ).filter(
                        PTORequest.status.in_(['approved', 'denied']),
                        PTORequest.updated_at >= date(filter_state['year'], 1, 1)
                    )

                    if filter_state['department_id']:
                        query = query.filter(User.department_id == filter_state['department_id'])

                    results = query.order_by(PTORequest.updated_at.desc()).limit(100).all()

                    approver_ids = [r.approved_by for r, _ in results if r.approved_by]
                    approvers = {u.id: f'{u.first_name} {u.last_name}'
                                for u in db.query(User).filter(User.id.in_(approver_ids)).all()}

                    for request, user_obj in results:
                        writer.writerow([
                            request.updated_at.strftime('%Y-%m-%d %H:%M') if request.updated_at else '',
                            f'{user_obj.first_name} {user_obj.last_name}',
                            request.pto_type.title(),
                            request.status.upper(),
                            approvers.get(request.approved_by, 'Auto') if request.approved_by else ''
                        ])

                    filename = f'audit_log_{filter_state["year"]}.csv'

                else:
                    filename = 'report.csv'

                csv_content = output.getvalue()
                ui.download(csv_content.encode('utf-8'), filename)
                ui.notify(f'Downloaded {filename}', type='positive')

            except Exception as e:
                ui.notify(f'Error exporting CSV: {str(e)}', type='negative')
            finally:
                db.close()

        def get_report_html():
            """Generate formatted HTML report using ReportService."""
            db = next(get_db())
            try:
                report_service = ReportService(db)
                report_type = filter_state['report_type']
                year = filter_state['year']

                if report_type == 'my_history':
                    return report_service.generate_history_report_html(
                        user_id, year, filter_state['status_filter']
                    )
                elif report_type == 'my_balance':
                    return report_service.generate_balance_report_html(user_id, year)
                elif report_type == 'team_balance':
                    return report_service.generate_team_balance_report_html(
                        year, filter_state['department_id']
                    )
                else:
                    # For other report types, generate a simple HTML version
                    return generate_simple_report_html(report_type)
            finally:
                db.close()

        def generate_simple_report_html(report_type: str) -> str:
            """Generate a simple HTML report for types not covered by ReportService."""
            db = next(get_db())
            try:
                report_service = ReportService(db)
                now = datetime.now()
                year = filter_state['year']

                # Get current user info
                current_user = db.query(User).filter(User.id == user_id).first()
                employee_name = f"{current_user.first_name} {current_user.last_name}" if current_user else "Unknown"

                header = report_service.get_report_header_html(
                    title=f"{report_type.replace('_', ' ').title()} Report - {year}",
                    employee_name=employee_name if report_type.startswith('my_') else None
                )
                footer = report_service.get_report_footer_html()

                content = '<div style="padding: 20px; font-family: Segoe UI, sans-serif;">'
                content += '<p style="color: #666;">This report type does not have a formatted print version yet.</p>'
                content += '<p>Please use CSV export for detailed data.</p>'
                content += '</div>'

                return f'''
                <!DOCTYPE html>
                <html>
                <head><meta charset="UTF-8"><title>Report</title></head>
                <body style="margin: 0; padding: 0; background: white;">
                    {header}{content}{footer}
                </body>
                </html>
                '''
            finally:
                db.close()

        def show_print_preview():
            """Show print preview dialog with formatted report."""
            import base64
            try:
                html_content = get_report_html()
                # Encode HTML as base64 to avoid escaping issues
                b64_content = base64.b64encode(html_content.encode('utf-8')).decode('ascii')

                dialog = ui.dialog().props('maximized')
                with dialog, ui.card().classes('w-full h-full'):
                    with ui.row().classes('w-full justify-between items-center p-4 border-b'):
                        ui.label('Print Preview').classes('text-xl font-semibold')
                        with ui.row().classes('gap-2'):
                            ui.button('Print', icon='print', on_click=lambda: ui.run_javascript('''
                                const iframe = document.getElementById("print-frame");
                                if (iframe && iframe.contentWindow) {
                                    iframe.contentWindow.print();
                                }
                            ''')).props('color=primary')
                            ui.button('Close', icon='close', on_click=dialog.close).props('flat')

                    # Use data URI to load HTML content into iframe
                    ui.html(f'<iframe id="print-frame" src="data:text/html;base64,{b64_content}" style="width: 100%; height: calc(100vh - 80px); border: 1px solid #ddd; background: white;"></iframe>', sanitize=False).classes('w-full')

                dialog.open()
            except Exception as e:
                ui.notify(f'Error generating print preview: {str(e)}', type='negative')

        def download_pdf():
            """Download report as PDF (using browser print-to-PDF)."""
            import base64
            html_content = get_report_html()
            # Encode HTML as base64 to avoid escaping issues
            b64_content = base64.b64encode(html_content.encode('utf-8')).decode('ascii')

            # Open new window with data URI and trigger print dialog
            ui.run_javascript(f'''
                const printWindow = window.open('data:text/html;base64,{b64_content}', '_blank');
                if (printWindow) {{
                    printWindow.onload = function() {{
                        printWindow.print();
                    }};
                }}
            ''')
            ui.notify("PDF: Use your browser's 'Save as PDF' option in the print dialog", type='info')

        def show_email_dialog():
            """Show dialog to email the report with format selection."""
            report_name = filter_state["report_type"].replace("_", " ").title()

            with ui.dialog() as dialog, ui.card().classes('p-6').style('min-width: 450px;'):
                ui.label('Email Report').classes('text-xl font-semibold mb-4')

                email_input = ui.input().classes('w-full mb-4').props('label="Recipient Email"')

                subject_input = ui.input(
                    value=f'PTO Report - {report_name} ({filter_state["year"]})'
                ).classes('w-full mb-4').props('label="Subject"')

                # Format selection
                ui.label('Attachment Format').classes('text-sm text-gray-600 mb-1')
                format_select = ui.select(
                    options=['PDF (Print Format)', 'CSV (Data Export)', 'HTML (Web Format)'],
                    value='PDF (Print Format)'
                ).classes('w-full mb-4')

                message_input = ui.textarea().classes('w-full mb-4').props('label="Message (optional)"')

                # Attachment preview section
                with ui.card().classes('w-full p-3 bg-gray-100 dark:bg-gray-800 mb-4'):
                    ui.label('Attachment Preview').classes('text-sm font-semibold mb-2')
                    attachment_preview = ui.row().classes('items-center gap-2')
                    with attachment_preview:
                        ui.icon('attach_file', color='primary')
                        attachment_name = ui.label(f'{report_name.replace(" ", "_")}_{filter_state["year"]}.pdf').classes('text-sm')

                def update_attachment_name():
                    fmt = format_select.value
                    base_name = f'{report_name.replace(" ", "_")}_{filter_state["year"]}'
                    if 'PDF' in fmt:
                        attachment_name.set_text(f'{base_name}.pdf')
                    elif 'CSV' in fmt:
                        attachment_name.set_text(f'{base_name}.csv')
                    else:
                        attachment_name.set_text(f'{base_name}.html')

                format_select.on('update:model-value', lambda: update_attachment_name())

                async def send_email():
                    if not email_input.value or '@' not in email_input.value:
                        ui.notify('Please enter a valid email address', type='negative')
                        return

                    try:
                        from src.services.email_service import email_service

                        fmt = format_select.value
                        html_content = get_report_html()
                        base_name = f'{report_name.replace(" ", "_")}_{filter_state["year"]}'

                        # Generate attachment based on format
                        attachment_data = None
                        attachment_name = None
                        attachment_type = 'html'

                        if 'CSV' in fmt:
                            # Generate CSV content
                            csv_content = generate_csv_for_email()
                            if csv_content:
                                attachment_data = csv_content.encode('utf-8')
                                attachment_name = f'{base_name}.csv'
                                attachment_type = 'csv'
                        elif 'HTML' in fmt:
                            attachment_data = html_content.encode('utf-8')
                            attachment_name = f'{base_name}.html'
                            attachment_type = 'html'
                        else:  # PDF - send HTML for now with note
                            attachment_data = html_content.encode('utf-8')
                            attachment_name = f'{base_name}.html'
                            attachment_type = 'html'

                        success = email_service.send_report_email(
                            to_email=email_input.value,
                            subject=subject_input.value,
                            html_content=html_content,
                            message=message_input.value,
                            attachment_data=attachment_data,
                            attachment_name=attachment_name,
                            attachment_type=attachment_type
                        )

                        if success:
                            ui.notify(f'Report sent to {email_input.value}', type='positive')
                            dialog.close()
                        else:
                            ui.notify('Email service not configured. Please configure SMTP settings.', type='warning')

                    except Exception as e:
                        ui.notify(f'Error sending email: {str(e)}', type='negative')

                def generate_csv_for_email() -> str:
                    """Generate CSV content for the current report."""
                    db = next(get_db())
                    try:
                        report_type = filter_state['report_type']
                        year = filter_state['year']
                        output = StringIO()
                        writer = csv.writer(output)

                        if report_type == 'my_balance':
                            user = db.query(User).filter(User.id == user_id).first()
                            balance = db.query(PTOBalance).filter(
                                PTOBalance.user_id == user_id,
                                PTOBalance.year == year
                            ).first()

                            writer.writerow(['Leave Type', 'Total (Hours)', 'Used (Hours)', 'Available (Hours)'])
                            if balance:
                                writer.writerow(['Vacation', balance.vacation_total, balance.vacation_used,
                                               balance.vacation_total - balance.vacation_used])
                                writer.writerow(['Sick', balance.sick_total, balance.sick_used,
                                               balance.sick_total - balance.sick_used])
                                writer.writerow(['Personal', balance.personal_total, balance.personal_used,
                                               balance.personal_total - balance.personal_used])

                        elif report_type == 'my_history':
                            requests = db.query(PTORequest).filter(
                                PTORequest.user_id == user_id
                            ).order_by(PTORequest.start_date.desc()).all()

                            writer.writerow(['Type', 'Start Date', 'End Date', 'Days', 'Status', 'Notes'])
                            for req in requests:
                                writer.writerow([req.pto_type, req.start_date, req.end_date,
                                               req.total_days, req.status, req.notes or ''])

                        elif report_type == 'team_balance':
                            query = db.query(User, PTOBalance).outerjoin(
                                PTOBalance,
                                (PTOBalance.user_id == User.id) & (PTOBalance.year == year)
                            ).filter(User.is_active == True)

                            if filter_state.get('department_id'):
                                query = query.filter(User.department_id == filter_state['department_id'])

                            results = query.order_by(User.last_name).all()

                            writer.writerow(['Employee', 'Vac Total', 'Vac Used', 'Vac Avail',
                                           'Sick Total', 'Sick Used', 'Pers Total', 'Pers Used'])
                            for user, balance in results:
                                if balance:
                                    writer.writerow([
                                        f'{user.first_name} {user.last_name}',
                                        balance.vacation_total, balance.vacation_used,
                                        balance.vacation_total - balance.vacation_used,
                                        balance.sick_total, balance.sick_used,
                                        balance.personal_total, balance.personal_used
                                    ])

                        return output.getvalue()
                    finally:
                        db.close()

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    ui.button('Send', icon='send', on_click=send_email).props('color=primary')

            dialog.open()

        # Initial render
        render_filters()
        render_report()

        # Back to Dashboard button at bottom
        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline')
