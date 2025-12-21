"""Reports page - Personal reports for all users, Team reports for managers/admins."""
import asyncio
from nicegui import ui, app
from sqlalchemy.orm import joinedload
from src.database import get_db
from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.models.audit_log import AuditLog
from src.services.report_service import ReportService
from src.services.export_service import ExportService
from datetime import date, datetime, timedelta
from io import StringIO
import csv
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, skeleton_table, show_warning_dialog, show_error_dialog, show_success_dialog, show_info_dialog
from nicegui_app.components.formatting import fmt_days
from nicegui_app.pages.dashboard import show_pto_detail_dialog


# PTO type icons and colors - consistent with request_form.py and dashboard.py
PTO_TYPE_STYLES = {
    'vacation': {'icon': 'beach_access', 'hex': '#3b82f6', 'border': 'border-blue-500'},
    'sick': {'icon': 'local_hospital', 'hex': '#22c55e', 'border': 'border-green-500'},
    'personal': {'icon': 'person', 'hex': '#a855f7', 'border': 'border-purple-500'},
    'work_from_home': {'icon': 'home_work', 'hex': '#ef4444', 'border': 'border-red-500'},
    'chicago_leave': {'icon': 'spa', 'hex': '#f59e0b', 'border': 'border-amber-500'},
    'bereavement': {'icon': 'sentiment_very_dissatisfied', 'hex': '#6366f1', 'border': 'border-indigo-500'},
    'fmla': {'icon': 'family_restroom', 'hex': '#0891b2', 'border': 'border-cyan-500'},
    'jury_duty': {'icon': 'gavel', 'hex': '#ec4899', 'border': 'border-pink-500'},
    'voting': {'icon': 'how_to_vote', 'hex': '#0d9488', 'border': 'border-teal-500'},
    'military': {'icon': 'military_tech', 'hex': '#64748b', 'border': 'border-slate-500'},
}


def get_pto_style(pto_type: str) -> dict:
    """Get icon, color, and border for a PTO type."""
    return PTO_TYPE_STYLES.get(pto_type.lower(), {'icon': 'event', 'hex': '#6b7280', 'border': 'border-gray-500'})


def show_help_tip(title: str, message: str):
    """Show a help tip dialog with OK button."""
    with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('help', color='amber', size='md')
            ui.label(title).classes('text-lg font-bold')
        ui.label(message).classes('text-sm opacity-80')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('OK', on_click=dialog.close).style('background-color: #C9A227 !important; color: white !important;')
    dialog.open()


def reports_page():
    """Reports page with personal and team reports."""

    apply_dark_mode()

    # Check if user is logged in
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']
    # Manager and Admin are restricted to their department; only SuperAdmin sees all
    is_department_restricted = user_role in ['manager', 'admin']
    is_manager_only = is_department_restricted  # Keep backward compatibility

    # Get user's department if applicable (for manager/admin)
    # Also load Technology department as default for superadmins
    manager_department_id = None
    manager_team_members = []
    default_department_id = None  # For superadmins
    all_departments = []

    db = next(get_db())
    try:
        from src.services.user_service import UserService
        user_service = UserService(db)

        if is_department_restricted:
            current_user = user_service.get_user_by_id(user_id)
            if current_user and current_user.department_id:
                manager_department_id = current_user.department_id
                # Get team members for individual reports
                team_members = user_service.get_users_by_department(manager_department_id)
                manager_team_members = [m for m in team_members if m.id != user_id and m.is_active]

        # Load all departments and find Technology as default for superadmins
        all_departments = db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()
        for dept in all_departments:
            if 'technology' in dept.name.lower():
                default_department_id = dept.id
                break
    finally:
        db.close()

    # State for filters
    current_year = date.today().year
    is_admin_only = user_role in ['admin', 'superadmin']
    filter_state = {
        'year': current_year,
        # Managers auto-filter to their department, superadmins default to Technology
        'department_id': manager_department_id if is_department_restricted else default_department_id,
        # Admins don't have personal PTO, so default to team reports
        'report_type': 'team_balance' if is_admin_only else 'my_pto',
        'status_filter': 'all',  # 'all', 'approved', 'pending', 'cancelled'
        'pto_type_filter': 'all',  # 'all', 'vacation', 'sick', 'personal', etc.
        # My PTO dashboard filters (multi-select)
        'selected_pto_types': set(),  # Empty set = all types, set of type codes for multi-select
        # Calendar view type filters (checkboxes for main types)
        'calendar_types': ['vacation', 'sick', 'personal', 'work_from_home'],  # Default: all main types selected
        'calendar_other_type': None,  # Selected "other" type for calendar
        # Audit log filters
        'audit_action': 'all',  # filter by action type
        'audit_date_from': None,  # date range start
        'audit_date_to': None,  # date range end
        'audit_search': '',  # text search across user, entity, details
        'audit_user': 'all',  # filter by specific user
        'audit_preset': 'last_30',  # date preset: today, last_7, last_30, this_month, custom
        # Individual employee filter (for managers)
        'employee_id': None,
    }

    # Report name mapping for display
    report_names = {
        'my_pto': 'My PTO',
        'my_history': 'My PTO History',
        'my_balance': 'My Balance Summary',
        'my_calendar': 'My Year at a Glance',
        'team_balance': 'Team Balance Summary',
        'team_usage': 'Team Usage Report',
        'audit': 'Audit Log'
    }

    # Main container
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):
        # Header with greeting (no back arrow - we'll add button at bottom)
        page_header(title='REPORTS', show_back=False)

        # ===== ACTIONS BAR (Top) =====
        actions_card = ui.card().classes('w-full mb-4 p-3')

        # ===== REPORT INDICATOR =====
        report_indicator = ui.row().classes('w-full mb-2 items-center gap-2')

        # Report type selector (only shown for managers/admins who have multiple report options)
        my_pto_btn = None  # Will be set for managers only
        if is_manager_or_admin:
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full gap-6 flex-wrap'):
                    # My PTO section (managers only - admins don't have PTO)
                    if not is_admin_only:
                        with ui.column().classes('gap-2'):
                            with ui.row().classes('items-center gap-1'):
                                ui.label('My Reports').classes('text-sm font-semibold uppercase opacity-60')
                                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                    'My Reports',
                                    'View your personal PTO information including requests, balances, and a calendar view of your time off throughout the year.'
                                )).props('flat dense round size=xs').style('color: #f59e0b')
                            with ui.row().classes('gap-2'):
                                my_pto_btn = ui.button('My PTO', icon='person', on_click=lambda: switch_report('my_pto')).props('color=primary')

                    # Team Reports section
                    with ui.column().classes('gap-2'):
                        with ui.row().classes('items-center gap-1'):
                            ui.label('Team Reports').classes('text-sm font-semibold uppercase opacity-60')
                            ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                'Team Reports',
                                'Team Balance: View all team members\' PTO balances (available, used, pending).\n\n'
                                'Team Usage: See approved time off requests by employee.\n\n'
                                'Audit Log: Track all system activity including logins, PTO requests, and approvals.'
                            )).props('flat dense round size=xs').style('color: #f59e0b')
                        with ui.row().classes('gap-2 flex-wrap'):
                            # For admins, default team_balance is selected
                            team_balance_btn = ui.button('Team Balance', on_click=lambda: switch_report('team_balance')).props('color=primary' if is_admin_only else 'outline')
                            team_usage_btn = ui.button('Team Usage', on_click=lambda: switch_report('team_usage')).props('outline')
                            audit_btn = ui.button('Audit Log', on_click=lambda: switch_report('audit')).props('outline')

        # Filters section
        filters_card = ui.card().classes('w-full mb-4 p-4')

        # Report content area
        report_container = ui.column().classes('w-full')

        # Button references for styling (only for managers/admins with multiple reports)
        all_buttons = {}
        if is_manager_or_admin:
            all_buttons.update({
                'team_balance': team_balance_btn,
                'team_usage': team_usage_btn,
                'audit': audit_btn,
            })
            if my_pto_btn:
                all_buttons['my_pto'] = my_pto_btn

        def switch_report(report_type):
            filter_state['report_type'] = report_type
            # Update button styles - must remove 'outline' for selected, add for others
            for btn_type, btn in all_buttons.items():
                if btn_type == report_type:
                    btn.props('color=primary', remove='outline')
                else:
                    btn.props('outline', remove='color')
            render_report_indicator()
            render_filters()
            render_report()

        def render_report_indicator():
            """Update the 'Viewing' indicator with current report name and year."""
            report_indicator.clear()
            with report_indicator:
                ui.icon('description', color='primary').classes('text-lg')
                report_name = report_names.get(filter_state['report_type'], 'Report')
                ui.label(f'Viewing: {report_name}').classes('text-sm font-medium')
                ui.label(f'({filter_state["year"]})').classes('text-sm opacity-60')

        def render_actions():
            """Render the action buttons bar."""
            actions_card.clear()
            with actions_card:
                with ui.row().classes('w-full justify-between items-center'):
                    # Left side: Actions label
                    ui.label('Actions').classes('text-xs font-semibold uppercase opacity-50')

                    # Right side: Action buttons
                    with ui.row().classes('gap-2 flex-wrap'):
                        # Download dropdown
                        with ui.dropdown_button('Download', icon='download', auto_close=True).props('flat dense') as download_dropdown:
                            async def handle_download_csv():
                                download_dropdown.close()
                                await asyncio.sleep(0.1)
                                export_csv()

                            async def handle_download_pdf():
                                download_dropdown.close()
                                await asyncio.sleep(0.1)
                                download_pdf()

                            ui.item('Download CSV', on_click=handle_download_csv)
                            ui.item('Download PDF', on_click=handle_download_pdf)

                        # Print Preview button
                        ui.button('Print Preview', icon='print', on_click=show_print_preview).props('flat dense')

                        # Email Report button
                        ui.button('Email Report', icon='email', on_click=show_email_dialog).props('flat dense')

        def render_filters():
            filters_card.clear()
            # Hide filters card for my_pto (all filters are inline with title)
            if filter_state['report_type'] == 'my_pto':
                filters_card.set_visibility(False)
                return
            filters_card.set_visibility(True)

            with filters_card:
                # Row 1: Filters
                with ui.row().classes('w-full gap-4 items-end flex-wrap'):
                    # Year filter
                    years = [current_year, current_year + 1]
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

                    # PTO type filter for history/usage reports (dropdown)
                    if filter_state['report_type'] in ['my_history', 'team_usage']:
                        pto_type_options = {
                            'all': 'All Types',
                            'vacation': 'Vacation',
                            'sick': 'Sick',
                            'personal': 'Personal',
                            'work_from_home': 'Work From Home',
                            'bereavement': 'Bereavement',
                            'fmla': 'FMLA',
                            'jury_duty': 'Jury Duty',
                            'voting': 'Voting',
                            'military': 'Military'
                        }
                        ui.select(
                            pto_type_options,
                            label='PTO Type',
                            value=filter_state['pto_type_filter'],
                            on_change=lambda e: update_filter('pto_type_filter', e.value)
                        ).classes('w-44')

                    # PTO type checkboxes for my_calendar view only
                    if filter_state['report_type'] == 'my_calendar':
                        # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                        main_types = [
                            ('vacation', 'Vacation', '#3b82f6'),
                            ('sick', 'Sick', '#22c55e'),
                            ('personal', 'Personal', '#a855f7'),
                            ('work_from_home', 'Work From Home', '#ef4444'),
                        ]

                        def toggle_calendar_type(type_code):
                            if type_code in filter_state['calendar_types']:
                                filter_state['calendar_types'].remove(type_code)
                            else:
                                filter_state['calendar_types'].append(type_code)
                            render_report()

                        with ui.row().classes('items-center gap-4'):
                            for type_code, label, color in main_types:
                                is_checked = type_code in filter_state['calendar_types']
                                with ui.element('div').classes('flex items-center gap-1 cursor-pointer').on(
                                    'click', lambda tc=type_code: toggle_calendar_type(tc)
                                ):
                                    ui.checkbox(value=is_checked).props('dense').on(
                                        'update:model-value', lambda e, tc=type_code: toggle_calendar_type(tc)
                                    )
                                    ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                    ui.label(label).classes('text-sm')

                            # Other types as clickable icons
                            other_types = [
                                ('bereavement', 'Bereave.'),
                                ('fmla', 'FMLA'),
                                ('jury_duty', 'Jury'),
                                ('voting', 'Voting'),
                                ('military', 'Military'),
                            ]

                            def toggle_other_type(type_code):
                                if filter_state['calendar_other_type'] == type_code:
                                    filter_state['calendar_other_type'] = None
                                else:
                                    filter_state['calendar_other_type'] = type_code
                                render_report()

                            for type_code, label in other_types:
                                style = PTO_TYPE_STYLES.get(type_code, {})
                                is_selected = filter_state['calendar_other_type'] == type_code
                                border = '2px solid ' + style.get('hex', '#6b7280') if is_selected else '1px solid transparent'
                                bg = f"rgba({int(style.get('hex', '#6b7280')[1:3], 16)}, {int(style.get('hex', '#6b7280')[3:5], 16)}, {int(style.get('hex', '#6b7280')[5:7], 16)}, 0.15)" if is_selected else 'transparent'
                                with ui.element('div').classes('flex items-center gap-1 cursor-pointer px-2 py-1 rounded').style(
                                    f'border: {border}; background: {bg};'
                                ).on('click', lambda tc=type_code: toggle_other_type(tc)):
                                    ui.icon(style.get('icon', 'event'), size='xs').style(f'color: {style.get("hex", "#6b7280")};')
                                    ui.label(label).classes('text-xs').style(f'color: {style.get("hex", "#6b7280")};')

                    # Other types for my_pto view are now rendered inline with the title in render_my_pto()

                    # Department filter (team reports only)
                    if filter_state['report_type'] in ['team_balance', 'team_usage', 'audit']:
                        db = next(get_db())
                        try:
                            # Managers can only see their own department
                            if is_manager_only:
                                dept = db.query(Department).filter(Department.id == manager_department_id).first()
                                if dept:
                                    ui.label(f'Department: {dept.name}').classes('self-center text-sm font-medium px-3 py-2 rounded').style('background: rgba(0,128,128,0.1)')
                            else:
                                # Admins/Superadmins can select any department
                                dept_options = {None: 'All Departments'}
                                dept_options.update({d.id: d.name for d in all_departments})

                                def on_dept_change(e):
                                    filter_state['department_id'] = e.value
                                    filter_state['employee_id'] = None  # Reset employee when dept changes
                                    render_filters()  # Re-render to update employee list
                                    render_report()

                                ui.select(
                                    dept_options,
                                    label='Department',
                                    value=filter_state['department_id'],
                                    on_change=on_dept_change
                                ).classes('w-48')

                            # Employee filter for superadmins (when a department is selected)
                            if not is_manager_only and filter_state['report_type'] in ['team_balance', 'team_usage']:
                                employee_options = {None: 'All Employees'}
                                # Load employees for selected department
                                if filter_state['department_id']:
                                    dept_employees = db.query(User).filter(
                                        User.department_id == filter_state['department_id'],
                                        User.is_active == True
                                    ).order_by(User.last_name, User.first_name).all()
                                else:
                                    dept_employees = db.query(User).filter(
                                        User.is_active == True
                                    ).order_by(User.last_name, User.first_name).all()

                                employee_options.update({
                                    emp.id: f"{emp.first_name} {emp.last_name}"
                                    for emp in dept_employees
                                })
                                ui.select(
                                    employee_options,
                                    label='Employee',
                                    value=filter_state['employee_id'],
                                    on_change=lambda e: update_filter('employee_id', e.value),
                                    with_input=True
                                ).props('dense outlined use-input').classes('w-56')
                        finally:
                            db.close()

                    # Individual employee filter (managers only, for team reports)
                    if is_manager_only and filter_state['report_type'] in ['team_balance', 'team_usage'] and manager_team_members:
                        employee_options = {None: 'All Team Members'}
                        employee_options.update({
                            m.id: f"{m.first_name} {m.last_name}"
                            for m in sorted(manager_team_members, key=lambda x: x.last_name)
                        })
                        ui.select(
                            employee_options,
                            label='Employee',
                            value=filter_state['employee_id'],
                            on_change=lambda e: update_filter('employee_id', e.value),
                            with_input=True
                        ).props('dense outlined use-input').classes('w-56')

        def update_filter(key, value):
            filter_state[key] = value
            if key == 'year':
                render_report_indicator()
            render_report()

        def render_report():
            report_container.clear()
            with report_container:
                report_type = filter_state['report_type']
                if report_type == 'my_pto':
                    render_my_pto()
                elif report_type == 'my_history':
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

                if filter_state['pto_type_filter'] != 'all':
                    query = query.filter(PTORequest.pto_type == filter_state['pto_type_filter'])

                requests = query.order_by(PTORequest.start_date.desc()).all()

                with ui.card().classes('w-full'):
                    ui.label(f'My PTO History - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not requests:
                        with ui.column().classes('w-full items-center py-8'):
                            ui.icon('event_busy', size='3rem').classes('opacity-30 mb-2')
                            ui.label('No PTO requests found for this period.').classes('opacity-60')
                        return

                    # Summary stats - count from ALL requests (not filtered)
                    all_requests = db.query(PTORequest).filter(
                        PTORequest.user_id == user_id,
                        PTORequest.start_date >= date(filter_state['year'], 1, 1),
                        PTORequest.end_date <= date(filter_state['year'], 12, 31)
                    ).all()
                    approved_days = sum(float(r.total_days or 0) for r in all_requests if r.status == 'approved')
                    pending_days = sum(float(r.total_days or 0) for r in all_requests if r.status == 'pending')
                    cancelled_days = sum(float(r.total_days or 0) for r in all_requests if r.status == 'cancelled')
                    approved_count = len([r for r in all_requests if r.status == 'approved'])
                    pending_count = len([r for r in all_requests if r.status == 'pending'])
                    cancelled_count = len([r for r in all_requests if r.status == 'cancelled'])

                    def filter_by_status(status, count):
                        # Only filter if there are requests for this status, or if returning to 'all'
                        if status == 'all' or count > 0:
                            filter_state['status_filter'] = 'all' if filter_state['status_filter'] == status else status
                            render_report()

                    # Edge-to-edge clickable summary grid
                    current_filter = filter_state['status_filter']
                    with ui.element('div').classes('w-full grid grid-cols-4 gap-4 mb-4'):
                        # Approved tile
                        is_active = current_filter == 'approved'
                        can_click = approved_count > 0
                        with ui.element('div').classes(f'p-4 rounded-lg {"cursor-pointer hover:opacity-80" if can_click else ""}').style(
                            f"background-color: {'#14532d' if is_active else '#374151'}; border-top: 4px solid #22c55e;"
                        ).on('click', lambda s='approved', c=approved_count: filter_by_status(s, c)):
                            ui.label('Approved').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(fmt_days(approved_days)).classes('text-xl font-bold').style('color: #22c55e')
                            ui.label(f'{approved_count} request{"s" if approved_count != 1 else ""}').classes('text-xs opacity-50')

                        # Pending tile
                        is_active = current_filter == 'pending'
                        can_click = pending_count > 0
                        with ui.element('div').classes(f'p-4 rounded-lg {"cursor-pointer hover:opacity-80" if can_click else ""}').style(
                            f"background-color: {'#78350f' if is_active else '#374151'}; border-top: 4px solid #f59e0b;"
                        ).on('click', lambda s='pending', c=pending_count: filter_by_status(s, c)):
                            ui.label('Pending').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(fmt_days(pending_days)).classes('text-xl font-bold').style('color: #f59e0b')
                            ui.label(f'{pending_count} request{"s" if pending_count != 1 else ""}').classes('text-xs opacity-50')

                        # Cancelled tile
                        is_active = current_filter == 'cancelled'
                        can_click = cancelled_count > 0
                        with ui.element('div').classes(f'p-4 rounded-lg {"cursor-pointer hover:opacity-80" if can_click else ""}').style(
                            f"background-color: {'#7f1d1d' if is_active else '#374151'}; border-top: 4px solid #ef4444;"
                        ).on('click', lambda s='cancelled', c=cancelled_count: filter_by_status(s, c)):
                            ui.label('Cancelled').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(fmt_days(cancelled_days)).classes('text-xl font-bold').style('color: #ef4444')
                            ui.label(f'{cancelled_count} request{"s" if cancelled_count != 1 else ""}').classes('text-xs opacity-50')

                        # Total tile (always clickable)
                        is_active = current_filter == 'all'
                        with ui.element('div').classes('p-4 rounded-lg cursor-pointer hover:opacity-80').style(
                            f"background-color: {'#1e3a5f' if is_active else '#374151'}; border-top: 4px solid #3b82f6;"
                        ).on('click', lambda: filter_by_status('all', 1)):
                            ui.label('Total').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(f'{len(all_requests)}').classes('text-xl font-bold').style('color: #3b82f6')
                            ui.label('requests').classes('text-xs opacity-50')

                    # Detailed list with descriptions
                    for req in requests:
                        # Get PTO type styling (icon, color, border)
                        pto_style = get_pto_style(req.pto_type)

                        with ui.card().classes(f'w-full mb-3 p-4 border-l-4 {pto_style["border"]} cursor-pointer hover:shadow-md').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                            with ui.row().classes('w-full justify-between items-start'):
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon(pto_style['icon'], size='sm').style(f'color: {pto_style["hex"]};')
                                        ui.label(req.pto_type.replace('_', ' ').title()).classes('font-semibold').style(f'color: {pto_style["hex"]};')
                                        ui.badge(req.status.upper()).props(
                                            f'color={"green" if req.status == "approved" else "amber" if req.status == "pending" else "red"}'
                                        )

                                    # Dates
                                    if req.start_date == req.end_date:
                                        date_str = req.start_date.strftime('%A, %B %d, %Y')
                                    else:
                                        date_str = f'{req.start_date.strftime("%A, %B %d")} - {req.end_date.strftime("%A, %B %d, %Y")}'
                                    ui.label(date_str).classes('text-sm')

                                    # Notes (personal)
                                    if req.notes:
                                        with ui.row().classes('items-start gap-2 mt-2 p-2 rounded').style('background: rgba(0,0,0,0.05)'):
                                            ui.icon('notes', color='grey').classes('text-sm')
                                            ui.label(req.notes).classes('text-sm italic')

                                with ui.column().classes('items-end'):
                                    ui.label(fmt_days(float(req.total_days or 0))).classes('font-bold')

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
                        with ui.column().classes('w-full items-center py-8'):
                            ui.icon('account_balance_wallet', size='3rem').classes('opacity-30 mb-2')
                            ui.label('No balance record found for this year.').classes('opacity-60')
                        return

                    # Helper to format hours as days (8 hours = 1 day)
                    def hours_to_days(hours):
                        return fmt_days(hours / 8)

                    # Helper to create a balance stat column
                    def balance_stat(value_days, value_hrs, label, color_class=''):
                        with ui.column().classes('items-center flex-1'):
                            ui.label(value_days).classes(f'text-xl font-bold {color_class}')
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
                query = db.query(PTORequest).filter(
                    PTORequest.user_id == user_id,
                    PTORequest.status == 'approved',
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31)
                )

                # Build list of selected types from checkboxes + other dropdown
                selected_types = list(filter_state['calendar_types'])
                if filter_state['calendar_other_type']:
                    selected_types.append(filter_state['calendar_other_type'])

                # Filter by selected types (if any selected)
                if selected_types:
                    from sqlalchemy import func
                    query = query.filter(func.lower(PTORequest.pto_type).in_([t.lower() for t in selected_types]))

                requests = query.order_by(PTORequest.start_date).all()

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
                                    'personal': 'purple',
                                    'work_from_home': 'red'
                                }
                                type_display = {
                                    'vacation': 'Vacation',
                                    'sick': 'Sick',
                                    'personal': 'Personal',
                                    'work_from_home': 'WFH'
                                }
                                pto_lower = req.pto_type.lower()
                                color = type_colors.get(pto_lower, 'grey')
                                display_name = type_display.get(pto_lower, req.pto_type.replace('_', ' ').title())

                                with ui.row().classes('w-full p-2 items-center gap-3 border-b cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                                    ui.badge(display_name, color=color)
                                    if req.start_date == req.end_date:
                                        ui.label(req.start_date.strftime('%d')).classes('font-medium')
                                    else:
                                        ui.label(f'{req.start_date.strftime("%d")} - {req.end_date.strftime("%d")}').classes('font-medium')
                                    ui.label(fmt_days(float(req.total_days or 0))).classes('opacity-70')
                                    if req.notes:
                                        ui.label(f'"{req.notes}"').classes('text-sm italic opacity-60 flex-1')

            finally:
                db.close()

        def render_my_pto():
            """Render combined My PTO dashboard with balance, status tiles, and history."""
            db = next(get_db())
            try:
                # Get balance data
                balance = db.query(PTOBalance).filter(
                    PTOBalance.user_id == user_id,
                    PTOBalance.year == filter_state['year']
                ).first()

                # Check if user is Chicago employee (for LEAVE tile visibility)
                from src.models.system_setting import SystemSetting
                user_obj = db.query(User).filter(User.id == user_id).first()
                is_chicago_employee = user_obj and user_obj.location_city and user_obj.location_city.lower() == 'chicago'
                chicago_setting = db.query(SystemSetting).filter(SystemSetting.key == 'chicago.safe_leave_enabled').first()
                show_chicago_leave = is_chicago_employee and chicago_setting and chicago_setting.bool_value

                # Get all requests for the year
                all_requests = db.query(PTORequest).filter(
                    PTORequest.user_id == user_id,
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31)
                ).all()

                # Group requests by type for counting
                requests_by_type = {
                    'vacation': [r for r in all_requests if r.pto_type.lower() == 'vacation'],
                    'sick': [r for r in all_requests if r.pto_type.lower() == 'sick'],
                    'personal': [r for r in all_requests if r.pto_type.lower() == 'personal'],
                    'work_from_home': [r for r in all_requests if r.pto_type.lower() == 'work_from_home'],
                }

                # Apply filters to get display requests
                filtered_requests = all_requests

                # Apply PTO type filter (main tiles - multi-select or other types)
                if filter_state['selected_pto_types']:
                    filtered_requests = [r for r in filtered_requests if r.pto_type.lower() in filter_state['selected_pto_types']]
                elif filter_state['calendar_other_type']:
                    filtered_requests = [r for r in filtered_requests if r.pto_type.lower() == filter_state['calendar_other_type'].lower()]

                # Apply status filter
                if filter_state['status_filter'] != 'all':
                    filtered_requests = [r for r in filtered_requests if r.status == filter_state['status_filter']]

                # Sort by date descending
                filtered_requests = sorted(filtered_requests, key=lambda r: r.start_date, reverse=True)

                # Calculate stats based on current PTO type filter (for status tiles)
                if filter_state['selected_pto_types']:
                    # Combine requests from all selected types
                    type_requests = [r for r in all_requests if r.pto_type.lower() in filter_state['selected_pto_types']]
                else:
                    type_requests = all_requests

                approved_days = sum(float(r.total_days or 0) for r in type_requests if r.status == 'approved')
                pending_days = sum(float(r.total_days or 0) for r in type_requests if r.status == 'pending')
                cancelled_days = sum(float(r.total_days or 0) for r in type_requests if r.status == 'cancelled')
                approved_count = len([r for r in type_requests if r.status == 'approved'])
                pending_count = len([r for r in type_requests if r.status == 'pending'])
                cancelled_count = len([r for r in type_requests if r.status == 'cancelled'])

                # Info dialog helper
                def show_info_dialog(title: str, message: str):
                    with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 350px; max-width: 450px'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('info', color='blue', size='md')
                            ui.label(title).classes('text-lg font-bold')
                        ui.label(message).classes('text-sm opacity-80')
                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button('OK', on_click=dialog.close).props('color=primary')
                    dialog.open()

                with ui.card().classes('w-full'):
                    # Title row with inline filters (Year + Other Types)
                    with ui.row().classes('w-full justify-between items-center mb-4 flex-wrap gap-2'):
                        ui.label(f'My PTO Dashboard - {filter_state["year"]}').classes('text-lg font-semibold')

                        # Inline filters: Year selector + Other types
                        with ui.row().classes('items-center gap-3'):
                            # Year selector
                            years = [current_year, current_year + 1]
                            ui.select(
                                {y: str(y) for y in years},
                                label='Year',
                                value=filter_state['year'],
                                on_change=lambda e: update_filter('year', e.value)
                            ).props('dense outlined').classes('w-24')

                            # Other types as clickable icons
                            other_types_list = [
                                ('bereavement', 'Bereave.'),
                                ('fmla', 'FMLA'),
                                ('jury_duty', 'Jury'),
                                ('voting', 'Voting'),
                                ('military', 'Military'),
                            ]

                            def toggle_other_type_inline(type_code):
                                if filter_state['calendar_other_type'] == type_code:
                                    filter_state['calendar_other_type'] = None
                                else:
                                    filter_state['calendar_other_type'] = type_code
                                    # Clear main tile selection (mutually exclusive)
                                    filter_state['selected_pto_types'] = set()
                                filter_state['status_filter'] = 'all'
                                render_report()

                            for type_code, label in other_types_list:
                                style = PTO_TYPE_STYLES.get(type_code, {})
                                is_selected = filter_state['calendar_other_type'] == type_code
                                border = '2px solid ' + style.get('hex', '#6b7280') if is_selected else '1px solid transparent'
                                bg = f"rgba({int(style.get('hex', '#6b7280')[1:3], 16)}, {int(style.get('hex', '#6b7280')[3:5], 16)}, {int(style.get('hex', '#6b7280')[5:7], 16)}, 0.15)" if is_selected else 'transparent'
                                with ui.element('div').classes('flex items-center gap-1 cursor-pointer px-2 py-1 rounded').style(
                                    f'border: {border}; background: {bg};'
                                ).on('click', lambda tc=type_code: toggle_other_type_inline(tc)):
                                    ui.icon(style.get('icon', 'event'), size='xs').style(f'color: {style.get("hex", "#6b7280")};')
                                    ui.label(label).classes('text-xs').style(f'color: {style.get("hex", "#6b7280")};')

                    # === BALANCE TILES (Clickable - Multi-Select) ===
                    tile_cards = {}  # Store card references for style updates
                    tile_border_colors = {}  # Store tile border colors for dynamic styling

                    def format_days_verbose(hours):
                        """Format hours as 'x days' or 'x days and y hours'."""
                        whole_days = int(hours // 8)
                        remaining_hours = int(hours % 8)
                        if remaining_hours > 0:
                            return f"{whole_days} days and {remaining_hours} hours"
                        return f"{whole_days} days"

                    def update_tile_styles():
                        """Update tile card styles based on selected types - show bottom border when selected."""
                        for pto_type, card in tile_cards.items():
                            if card is None:
                                continue
                            is_selected = pto_type in filter_state['selected_pto_types']
                            border_color = tile_border_colors.get(pto_type, '#6b7280')
                            if is_selected:
                                # Show bottom border when selected
                                card.style(f'border-bottom: 4px solid {border_color}; transform: scale(1.02);')
                            else:
                                # Hide bottom border when not selected
                                card.style('border-bottom: 4px solid transparent; transform: scale(1);')

                    def select_pto_type(type_code, type_label, request_count):
                        """Select PTO type - multi-select toggle behavior."""
                        # Toggle: add or remove from selected set
                        if type_code in filter_state['selected_pto_types']:
                            filter_state['selected_pto_types'].discard(type_code)
                        else:
                            filter_state['selected_pto_types'].add(type_code)
                            # Clear other type selection (mutually exclusive with main tiles)
                            filter_state['calendar_other_type'] = None
                        # Reset status filter when changing PTO type
                        filter_state['status_filter'] = 'all'
                        update_tile_styles()
                        render_report()

                    # Balance data for tiles
                    if balance:
                        vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                        vac_used = float(balance.vacation_used or 0)
                        vac_pending = float(balance.vacation_pending or 0)
                        vac_avail = vac_total - vac_used - vac_pending

                        sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                        sick_used = float(balance.sick_used or 0)
                        sick_avail = sick_total - sick_used

                        personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                        personal_used = float(balance.personal_used or 0)
                        personal_avail = personal_total - personal_used

                        # Chicago Leave balance
                        chicago_avail = float(balance.chicago_paid_leave_available or 0) if hasattr(balance, 'chicago_paid_leave_available') else 0
                    else:
                        vac_avail = sick_avail = personal_avail = vac_pending = chicago_avail = 0

                    # WFH stats
                    wfh_requests = requests_by_type['work_from_home']
                    wfh_days = sum(float(r.total_days or 0) for r in wfh_requests)
                    wfh_count = len(wfh_requests)

                    # Chicago Leave requests (need to add to requests_by_type)
                    chicago_requests = [r for r in all_requests if r.pto_type.lower() == 'chicago_leave']
                    chicago_count = len(chicago_requests)

                    # Tile data: type_code, label, icon, hours_avail, color, bg_active, pending_hours, request_count, is_count_only
                    tiles = [
                        ('vacation', 'Vacation', 'beach_access', vac_avail, '#3b82f6', '#1e3a5f', vac_pending, len(requests_by_type['vacation']), False),
                        ('sick', 'Sick', 'local_hospital', sick_avail, '#22c55e', '#14532d', 0, len(requests_by_type['sick']), False),
                        ('personal', 'Personal', 'person', personal_avail, '#a855f7', '#581c87', 0, len(requests_by_type['personal']), False),
                    ]
                    # Only show Chicago Leave tile for Chicago employees with setting enabled
                    if show_chicago_leave:
                        tiles.append(('chicago_leave', 'Leave', 'spa', chicago_avail, '#f59e0b', '#78350f', 0, chicago_count, False))
                    tiles.append(('work_from_home', 'WFH', 'home_work', wfh_days * 8, '#ef4444', '#7f1d1d', 0, wfh_count, True))

                    # Border class mapping for tailwind
                    border_classes = {
                        '#3b82f6': 'border-blue-500',
                        '#22c55e': 'border-green-500',
                        '#a855f7': 'border-purple-500',
                        '#f59e0b': 'border-amber-500',
                        '#ef4444': 'border-red-500',
                    }

                    # Use CSS Grid - 5 columns if Chicago leave shown, 4 otherwise
                    grid_cols = 'grid-cols-5' if show_chicago_leave else 'grid-cols-4'
                    with ui.element('div').classes(f'w-full grid {grid_cols} gap-3 mb-4'):
                        for type_code, label, icon, hours_avail, color, bg_active, pending_hours, req_count, is_count_only in tiles:
                            is_selected = type_code in filter_state['selected_pto_types']
                            border_class = border_classes.get(color, 'border-gray-500')

                            # Store the hex color for this tile type
                            tile_border_colors[type_code] = color

                            # Create card with top border only, transparent bottom (shown on select)
                            card = ui.card().classes(f'p-3 border-t-4 {border_class} cursor-pointer hover:opacity-80 transition-all duration-200').style(
                                'border-bottom: 4px solid transparent;'
                            ).on(
                                'click', lambda tc=type_code, lbl=label, cnt=req_count: select_pto_type(tc, lbl, cnt)
                            )
                            tile_cards[type_code] = card
                            # Apply initial style if selected
                            if is_selected:
                                card.style(f'border-bottom: 4px solid {color}; transform: scale(1.02);')

                            with card:
                                # Centered icon, label, and value
                                with ui.column().classes('items-center w-full'):
                                    ui.icon(icon, size='1.5rem').style(f'color: {color};')
                                    ui.label(label).classes('text-sm font-semibold text-center').style(f'color: {color}')

                                    # Value display
                                    if is_count_only:
                                        # WFH shows count
                                        ui.label(f'{req_count} request{"s" if req_count != 1 else ""}').classes('text-xs opacity-60 text-center')
                                    else:
                                        # Balance types show verbose format
                                        ui.label(format_days_verbose(hours_avail)).classes('text-sm font-bold text-center')
                                        if pending_hours > 0:
                                            ui.label(f'({format_days_verbose(pending_hours)} pending)').classes('text-xs text-amber-500 text-center')

                    # === STATUS INFO (for help dialogs and empty state cards) ===
                    status_info = {
                        'approved': {
                            'name': 'Approved Requests',
                            'icon': 'check_circle',
                            'color': '#22c55e',
                            'border': 'border-green-500',
                            'description': 'Approved requests have been reviewed and confirmed by your manager. These hours are deducted from your balance and the time off is officially scheduled.'
                        },
                        'pending': {
                            'name': 'Pending Requests',
                            'icon': 'pending',
                            'color': '#f59e0b',
                            'border': 'border-amber-500',
                            'description': 'Pending requests are awaiting manager approval. Your balance shows these hours as "pending" until approved or denied. You\'ll receive notification once a decision is made.'
                        },
                        'cancelled': {
                            'name': 'Cancelled Requests',
                            'icon': 'cancel',
                            'color': '#ef4444',
                            'border': 'border-red-500',
                            'description': 'Cancelled requests were withdrawn before or after approval. Hours from cancelled requests are returned to your available balance.'
                        },
                        'all': {
                            'name': 'All Requests',
                            'icon': 'list_alt',
                            'color': '#3b82f6',
                            'border': 'border-blue-500',
                            'description': 'View all your PTO requests regardless of status. This includes approved, pending, denied, and cancelled requests.'
                        }
                    }

                    def show_status_info(status_code):
                        """Show a dialog with information about the request status."""
                        info = status_info.get(status_code, {})
                        with ui.dialog() as info_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
                            with ui.row().classes('items-center gap-3 mb-4'):
                                ui.icon(info.get('icon', 'info'), size='lg').style(f'color: {info.get("color", "#6b7280")};')
                                ui.label(info.get('name', status_code.title())).classes('text-lg font-bold').style(f'color: {info.get("color", "#6b7280")};')
                            ui.label(info.get('description', 'No description available.')).classes('text-sm opacity-80')
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('OK', on_click=info_dialog.close).style('background-color: #C9A227 !important; color: white !important;')
                        info_dialog.open()

                    # === STATUS TILES (Clickable - filter within selected PTO type) ===
                    def filter_by_status(status, count):
                        # Toggle: if already selected, go back to all; otherwise select
                        # Allow selecting even if count is 0 - will show styled empty card
                        filter_state['status_filter'] = 'all' if filter_state['status_filter'] == status else status
                        render_report()

                    current_status_filter = filter_state['status_filter']
                    # Use CSS Grid for perfect 4-column alignment
                    with ui.element('div').classes('w-full grid grid-cols-4 gap-3 mb-4'):
                        # Approved tile
                        is_active = current_status_filter == 'approved'
                        ring_class = 'ring-2 ring-offset-2 ring-offset-gray-900' if is_active else ''
                        with ui.card().classes(f'p-3 border-t-4 border-green-500 cursor-pointer hover:opacity-80 {ring_class}').on(
                            'click', lambda s='approved', c=approved_count: filter_by_status(s, c)
                        ):
                            ui.label('Approved').classes('text-xs opacity-60 uppercase')
                            ui.label(fmt_days(approved_days)).classes('text-lg font-bold').style('color: #22c55e')
                            ui.label(f'{approved_count} request{"s" if approved_count != 1 else ""}').classes('text-xs opacity-50')

                        # Pending tile
                        is_active = current_status_filter == 'pending'
                        ring_class = 'ring-2 ring-offset-2 ring-offset-gray-900' if is_active else ''
                        with ui.card().classes(f'p-3 border-t-4 border-amber-500 cursor-pointer hover:opacity-80 {ring_class}').on(
                            'click', lambda s='pending', c=pending_count: filter_by_status(s, c)
                        ):
                            ui.label('Pending').classes('text-xs opacity-60 uppercase')
                            ui.label(fmt_days(pending_days)).classes('text-lg font-bold').style('color: #f59e0b')
                            ui.label(f'{pending_count} request{"s" if pending_count != 1 else ""}').classes('text-xs opacity-50')

                        # Cancelled tile
                        is_active = current_status_filter == 'cancelled'
                        ring_class = 'ring-2 ring-offset-2 ring-offset-gray-900' if is_active else ''
                        with ui.card().classes(f'p-3 border-t-4 border-red-500 cursor-pointer hover:opacity-80 {ring_class}').on(
                            'click', lambda s='cancelled', c=cancelled_count: filter_by_status(s, c)
                        ):
                            ui.label('Cancelled').classes('text-xs opacity-60 uppercase')
                            ui.label(fmt_days(cancelled_days)).classes('text-lg font-bold').style('color: #ef4444')
                            ui.label(f'{cancelled_count} request{"s" if cancelled_count != 1 else ""}').classes('text-xs opacity-50')

                        # Total/All tile
                        is_active = current_status_filter == 'all'
                        total_count = len(type_requests)
                        ring_class = 'ring-2 ring-offset-2 ring-offset-gray-900' if is_active else ''
                        with ui.card().classes(f'p-3 border-t-4 border-blue-500 cursor-pointer hover:opacity-80 {ring_class}').on(
                            'click', lambda: filter_by_status('all', 1)
                        ):
                            ui.label('Total').classes('text-xs opacity-60 uppercase')
                            ui.label(f'{total_count}').classes('text-lg font-bold').style('color: #3b82f6')
                            ui.label('requests').classes('text-xs opacity-50')

                    # === REQUEST LIST ===
                    # PTO type full names and descriptions
                    pto_type_info = {
                        'vacation': {
                            'name': 'Vacation',
                            'description': 'Paid time off for personal rest, travel, or leisure activities. Accrues based on tenure and can be carried over per company policy.'
                        },
                        'sick': {
                            'name': 'Sick Leave',
                            'description': 'Time off for illness, medical appointments, or caring for sick family members. Does not require advance notice for genuine illness.'
                        },
                        'personal': {
                            'name': 'Personal Day',
                            'description': 'Flexible time off for personal matters that don\'t fall under other categories. Use for appointments, errands, or personal needs.'
                        },
                        'chicago_leave': {
                            'name': 'Chicago Paid Leave',
                            'description': 'Paid leave available to Chicago-based employees under local ordinance. Can be used for any purpose with proper notice.'
                        },
                        'work_from_home': {
                            'name': 'Work From Home',
                            'description': 'Remote work request to work from home instead of the office. Subject to manager approval and job requirements.'
                        },
                        'bereavement': {
                            'name': 'Bereavement Leave',
                            'description': 'Paid time off following the death of a family member. Immediate family: up to 5 days. Extended family: up to 3 days.'
                        },
                        'fmla': {
                            'name': 'FMLA - Family and Medical Leave Act',
                            'description': 'Up to 12 weeks of unpaid, job-protected leave per year for serious health conditions, caring for family members, or bonding with a new child. Requires 30 days advance notice when foreseeable.'
                        },
                        'jury_duty': {
                            'name': 'Jury Duty',
                            'description': 'Paid time off for mandatory jury service. Provide court documentation. You will receive full pay during service.'
                        },
                        'voting': {
                            'name': 'Voting Leave',
                            'description': 'Up to 2 hours of paid time to vote if polls are not open for 2 consecutive hours outside of work schedule.'
                        },
                        'military': {
                            'name': 'Military Leave',
                            'description': 'Leave for military service, training, or duty as required by USERRA. Job protection and benefits continuation apply.'
                        },
                    }

                    def show_pto_type_info(type_code):
                        """Show a dialog with information about the PTO type."""
                        info = pto_type_info.get(type_code, {})
                        style = get_pto_style(type_code)
                        with ui.dialog() as info_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
                            with ui.row().classes('items-center gap-3 mb-4'):
                                ui.icon(style['icon'], size='lg').style(f'color: {style["hex"]};')
                                ui.label(info.get('name', type_code.replace('_', ' ').title())).classes('text-lg font-bold').style(f'color: {style["hex"]};')
                            ui.label(info.get('description', 'No description available.')).classes('text-sm opacity-80')
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('OK', on_click=info_dialog.close).style('background-color: #C9A227 !important; color: white !important;')
                        info_dialog.open()

                    if not filtered_requests:
                        # Check if a specific type is selected (main tiles or other types)
                        selected_types = filter_state.get('selected_pto_types', set())
                        selected_type = next(iter(selected_types), None) if selected_types else filter_state.get('calendar_other_type')
                        current_status = filter_state.get('status_filter', 'all')

                        if selected_type:
                            # Show styled card with the type's icon, full name, and "no requests" message
                            pto_style = get_pto_style(selected_type)
                            type_info = pto_type_info.get(selected_type, {})
                            type_label = type_info.get('name', selected_type.replace('_', ' ').title())
                            status_suffix = f' {current_status}' if current_status != 'all' else ''
                            with ui.card().classes(f'w-full mb-3 p-4 border-l-4 {pto_style["border"]} cursor-pointer hover:shadow-md').on('click', lambda t=selected_type: show_pto_type_info(t)):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon(pto_style['icon'], size='lg').style(f'color: {pto_style["hex"]};')
                                    with ui.column().classes('gap-1'):
                                        ui.label(type_label).classes('font-semibold').style(f'color: {pto_style["hex"]};')
                                        ui.label(f'You have no{status_suffix} {type_label.lower()} requests for {filter_state["year"]}.').classes('text-sm opacity-70')
                                        ui.label('Click for more information about this leave type').classes('text-xs opacity-50')

                        elif current_status != 'all':
                            # Show styled card for status filter with no results
                            s_info = status_info.get(current_status, {})
                            with ui.card().classes(f'w-full mb-3 p-4 border-t-4 {s_info.get("border", "border-gray-500")} cursor-pointer hover:shadow-md').on('click', lambda s=current_status: show_status_info(s)):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon(s_info.get('icon', 'info'), size='lg').style(f'color: {s_info.get("color", "#6b7280")};')
                                    with ui.column().classes('gap-1'):
                                        ui.label(s_info.get('name', current_status.title())).classes('font-semibold').style(f'color: {s_info.get("color", "#6b7280")};')
                                        ui.label(f'You have no {current_status} requests for {filter_state["year"]}.').classes('text-sm opacity-70')
                                        ui.label('Click for more information about this status').classes('text-xs opacity-50')

                        else:
                            # Generic empty state when no type or status is selected
                            with ui.column().classes('w-full items-center py-8'):
                                ui.icon('event_busy', size='3rem').classes('opacity-30 mb-2')
                                ui.label('No PTO requests found for the current filters.').classes('opacity-60')
                    else:
                        for req in filtered_requests:
                            # Get PTO type styling (icon, color, border)
                            pto_style = get_pto_style(req.pto_type)

                            with ui.card().classes(f'w-full mb-3 p-4 border-l-4 {pto_style["border"]} cursor-pointer hover:shadow-md').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                                with ui.row().classes('w-full justify-between items-start'):
                                    with ui.column().classes('gap-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon(pto_style['icon'], size='sm').style(f'color: {pto_style["hex"]};')
                                            ui.label(req.pto_type.replace('_', ' ').title()).classes('font-semibold').style(f'color: {pto_style["hex"]};')
                                            ui.badge(req.status.upper()).props(
                                                f'color={"green" if req.status == "approved" else "amber" if req.status == "pending" else "red"}'
                                            )

                                        if req.start_date == req.end_date:
                                            date_str = req.start_date.strftime('%A, %B %d, %Y')
                                        else:
                                            date_str = f'{req.start_date.strftime("%A, %B %d")} - {req.end_date.strftime("%A, %B %d, %Y")}'
                                        ui.label(date_str).classes('text-sm')

                                        if req.notes:
                                            with ui.row().classes('items-start gap-2 mt-2 p-2 rounded').style('background: rgba(0,0,0,0.05)'):
                                                ui.icon('notes', color='grey').classes('text-sm')
                                                ui.label(req.notes).classes('text-sm italic')

                                    with ui.column().classes('items-end'):
                                        ui.label(fmt_days(float(req.total_days or 0))).classes('font-bold')

            finally:
                db.close()

        def render_team_balance():
            """Render team balance summary (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            # Store employee data for detail lookup
            employee_lookup = {}

            def show_employee_balance_detail(employee_id):
                """Show a detail dialog for an employee's balance."""
                data = employee_lookup.get(employee_id)
                if not data:
                    return

                with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 450px; max-width: 550px;'):
                    # Header
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Balance Details').classes('text-lg font-bold')
                        ui.badge(str(filter_state['year']), color='primary')

                    # Employee info
                    with ui.row().classes('w-full items-center gap-3 mb-4 pb-4').style('border-bottom: 1px solid #374151'):
                        ui.icon('person', size='md').style('color: #3b82f6')
                        with ui.column().classes('gap-0'):
                            ui.label(data['name']).classes('font-semibold')
                            ui.label(data['department']).classes('text-sm opacity-60')

                    # Balance breakdown by type with icons
                    balance_types = [
                        {'name': 'Vacation', 'icon': 'beach_access', 'color': '#3b82f6', 'total': data['vac_total'], 'used': data['vac_used'], 'pending': data['vac_pending'], 'avail': data['vac_avail']},
                        {'name': 'Sick', 'icon': 'local_hospital', 'color': '#22c55e', 'total': data['sick_total'], 'used': data['sick_used'], 'pending': 0, 'avail': data['sick_total'] - data['sick_used']},
                        {'name': 'Personal', 'icon': 'person', 'color': '#a855f7', 'total': data['personal_total'], 'used': data['personal_used'], 'pending': 0, 'avail': data['personal_total'] - data['personal_used']},
                        {'name': 'WFH', 'icon': 'home_work', 'color': '#ef4444', 'total': None, 'used': data.get('wfh_used', 0), 'pending': 0, 'avail': None},
                    ]

                    for bt in balance_types:
                        with ui.element('div').classes('w-full mb-3 p-3 rounded').style(f'background-color: #374151; border-left: 4px solid {bt["color"]}'):
                            with ui.row().classes('w-full justify-between items-center mb-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(bt['icon'], size='sm').style(f'color: {bt["color"]}')
                                    ui.label(bt['name']).classes('font-semibold').style(f'color: {bt["color"]}')
                            with ui.row().classes('w-full gap-4'):
                                # WFH has no Total/Available - just show Used
                                if bt['total'] is not None:
                                    with ui.column().classes('gap-0 flex-1 text-center'):
                                        ui.label('Total').classes('text-xs opacity-60')
                                        ui.label(fmt_days(bt["total"])).classes('font-medium')
                                with ui.column().classes('gap-0 flex-1 text-center'):
                                    ui.label('Used').classes('text-xs opacity-60')
                                    ui.label(fmt_days(bt["used"])).classes('font-medium')
                                if bt['name'] == 'Vacation' and bt['pending'] > 0:
                                    with ui.column().classes('gap-0 flex-1 text-center'):
                                        ui.label('Pending').classes('text-xs opacity-60')
                                        ui.label(fmt_days(bt["pending"])).classes('font-medium').style('color: #f59e0b')
                                if bt['avail'] is not None:
                                    with ui.column().classes('gap-0 flex-1 text-center'):
                                        ui.label('Available').classes('text-xs opacity-60')
                                        avail_color = '#22c55e' if bt['avail'] > 0 else '#ef4444'
                                        ui.label(fmt_days(bt["avail"])).classes('font-bold').style(f'color: {avail_color}')

                    # OK button
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('OK', on_click=dialog.close).props('color=primary')

                dialog.open()

            db = next(get_db())
            try:
                query = db.query(User, PTOBalance).options(
                    joinedload(User.department)
                ).outerjoin(
                    PTOBalance,
                    (PTOBalance.user_id == User.id) & (PTOBalance.year == filter_state['year'])
                ).filter(User.is_active == True)

                if filter_state['department_id']:
                    query = query.filter(User.department_id == filter_state['department_id'])

                # Filter by specific employee (for managers)
                selected_employee_name = None
                if filter_state.get('employee_id'):
                    query = query.filter(User.id == filter_state['employee_id'])
                    # Get the employee name for the title
                    emp = db.query(User).filter(User.id == filter_state['employee_id']).first()
                    if emp:
                        selected_employee_name = f"{emp.first_name} {emp.last_name}"

                results = query.order_by(User.last_name, User.first_name).all()

                with ui.card().classes('w-full'):
                    # Dynamic title based on filter
                    if selected_employee_name:
                        title = f'{selected_employee_name} Balance Summary - {filter_state["year"]}'
                    else:
                        title = f'Team Balance Summary - {filter_state["year"]}'
                    ui.label(title).classes('text-lg font-semibold mb-4')

                    if not results:
                        with ui.column().classes('w-full items-center py-8'):
                            ui.icon('people_outline', size='3rem').classes('opacity-30 mb-2')
                            ui.label('No employees found.').classes('opacity-60')
                        return

                    # Helper to convert hours to days with clean formatting
                    def h2d(hours):
                        return fmt_days(hours / 8)

                    # Get WFH days used per employee for the year
                    from sqlalchemy import func
                    wfh_query = db.query(
                        PTORequest.user_id,
                        func.sum(PTORequest.total_days).label('wfh_days')
                    ).filter(
                        PTORequest.pto_type == 'work_from_home',
                        PTORequest.status == 'approved',
                        PTORequest.start_date >= date(filter_state['year'], 1, 1),
                        PTORequest.end_date <= date(filter_state['year'], 12, 31)
                    ).group_by(PTORequest.user_id).all()
                    wfh_by_user = {uid: float(days or 0) for uid, days in wfh_query}

                    # Colored section header labels with icons
                    with ui.row().classes('w-full mb-2 gap-0'):
                        ui.element('div').classes('flex-none').style('width: 200px;')  # Employee column spacer
                        with ui.element('div').classes('flex-1 text-center py-2 rounded-t').style('background-color: #3b82f620; border-bottom: 2px solid #3b82f6; border-right: 1px solid #374151;'):
                            with ui.column().classes('items-center gap-0'):
                                ui.icon('beach_access', size='sm').style('color: #3b82f6;')
                                ui.label('VACATION').classes('text-xs font-bold').style('color: #3b82f6;')
                        with ui.element('div').classes('flex-1 text-center py-2 rounded-t').style('background-color: #22c55e20; border-bottom: 2px solid #22c55e; border-right: 1px solid #374151;'):
                            with ui.column().classes('items-center gap-0'):
                                ui.icon('local_hospital', size='sm').style('color: #22c55e;')
                                ui.label('SICK').classes('text-xs font-bold').style('color: #22c55e;')
                        with ui.element('div').classes('flex-1 text-center py-2 rounded-t').style('background-color: #a855f720; border-bottom: 2px solid #a855f7; border-right: 1px solid #374151;'):
                            with ui.column().classes('items-center gap-0'):
                                ui.icon('person', size='sm').style('color: #a855f7;')
                                ui.label('PERSONAL').classes('text-xs font-bold').style('color: #a855f7;')
                        with ui.element('div').classes('text-center py-2 rounded-t').style('width: 80px; background-color: #ef444420; border-bottom: 2px solid #ef4444;'):
                            with ui.column().classes('items-center gap-0'):
                                ui.icon('home_work', size='sm').style('color: #ef4444;')
                                ui.label('WFH').classes('text-xs font-bold').style('color: #ef4444;')

                    columns = [
                        {'name': 'name', 'label': 'Employee', 'field': 'name', 'sortable': True, 'align': 'left'},
                        {'name': 'vacation_total', 'label': 'Total', 'field': 'vacation_total', 'sortable': True},
                        {'name': 'vacation_used', 'label': 'Used', 'field': 'vacation_used', 'sortable': True},
                        {'name': 'vacation_available', 'label': 'Avail', 'field': 'vacation_available', 'sortable': True},
                        {'name': 'sick_total', 'label': 'Total', 'field': 'sick_total', 'sortable': True},
                        {'name': 'sick_used', 'label': 'Used', 'field': 'sick_used', 'sortable': True},
                        {'name': 'personal_total', 'label': 'Total', 'field': 'personal_total', 'sortable': True},
                        {'name': 'personal_used', 'label': 'Used', 'field': 'personal_used', 'sortable': True},
                        {'name': 'wfh_used', 'label': 'Used', 'field': 'wfh_used', 'sortable': True},
                    ]

                    rows = []
                    for user_obj, balance in results:
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
                            vac_total = vac_used = vac_avail = vac_pending = sick_total = sick_used = personal_total = personal_used = 0

                        wfh_used = wfh_by_user.get(user_obj.id, 0)

                        # Store plain data for detail lookup (db session will be closed)
                        employee_lookup[user_obj.id] = {
                            'name': f'{user_obj.first_name} {user_obj.last_name}',
                            'department': user_obj.department.name if user_obj.department else 'No Department',
                            'vac_total': vac_total / 8,  # Convert hours to days
                            'vac_used': vac_used / 8,
                            'vac_pending': vac_pending / 8,
                            'vac_avail': vac_avail / 8,
                            'sick_total': sick_total / 8,
                            'sick_used': sick_used / 8,
                            'personal_total': personal_total / 8,
                            'personal_used': personal_used / 8,
                            'wfh_used': wfh_used,
                        }

                        rows.append({
                            'id': user_obj.id,
                            'name': f'{user_obj.first_name} {user_obj.last_name}',
                            'vacation_total': h2d(vac_total),
                            'vacation_used': h2d(vac_used),
                            'vacation_available': h2d(vac_avail),
                            '_vac_used_raw': vac_used,  # Raw values for comparison
                            '_vac_total_raw': vac_total,
                            '_vac_avail_raw': vac_avail,
                            'sick_total': h2d(sick_total),
                            'sick_used': h2d(sick_used),
                            '_sick_used_raw': sick_used,
                            '_sick_total_raw': sick_total,
                            'personal_total': h2d(personal_total),
                            'personal_used': h2d(personal_used),
                            '_personal_used_raw': personal_used,
                            '_personal_total_raw': personal_total,
                            'wfh_used': fmt_days(wfh_used),
                            '_wfh_used_raw': wfh_used,
                        })

                    def on_row_click(e):
                        """Handle row click to show detail dialog."""
                        row = e.args[1]  # Second arg is the row data
                        if row and 'id' in row:
                            show_employee_balance_detail(row['id'])

                    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full cursor-pointer')
                    table.on('row-click', on_row_click)
                    # Style the Used column: yellow normally, red if used equals total (all days used)
                    table.add_slot('body-cell-vacation_used', '''
                        <q-td :props="props">
                            <span :style="{ fontWeight: 'bold', color: (props.row._vac_used_raw >= props.row._vac_total_raw && props.row._vac_total_raw > 0) ? '#ef4444' : '#eab308' }">{{ props.value }}</span>
                        </q-td>
                    ''')
                    # Style the Avail column: yellow if available, red if zero
                    table.add_slot('body-cell-vacation_available', '''
                        <q-td :props="props">
                            <span :style="{ fontWeight: 'bold', color: props.row._vac_avail_raw <= 0 ? '#ef4444' : '#eab308' }">{{ props.value }}</span>
                        </q-td>
                    ''')
                    # Style Sick Used: yellow normally, red if used >= total
                    table.add_slot('body-cell-sick_used', '''
                        <q-td :props="props">
                            <span :style="{ fontWeight: 'bold', color: (props.row._sick_used_raw >= props.row._sick_total_raw && props.row._sick_total_raw > 0) ? '#ef4444' : '#eab308' }">{{ props.value }}</span>
                        </q-td>
                    ''')
                    # Style Personal Used: yellow normally, red if used >= total
                    table.add_slot('body-cell-personal_used', '''
                        <q-td :props="props">
                            <span :style="{ fontWeight: 'bold', color: (props.row._personal_used_raw >= props.row._personal_total_raw && props.row._personal_total_raw > 0) ? '#ef4444' : '#eab308' }">{{ props.value }}</span>
                        </q-td>
                    ''')
                    # Style WFH Used: yellow if 0, red if > 0 (has used WFH)
                    table.add_slot('body-cell-wfh_used', '''
                        <q-td :props="props">
                            <span :style="{ fontWeight: 'bold', color: props.row._wfh_used_raw > 0 ? '#ef4444' : '#eab308' }">{{ props.value }}</span>
                        </q-td>
                    ''')

                    with ui.row().classes('w-full justify-between items-center mt-2'):
                        ui.label(f'Total: {len(rows)} employees (click row for details)').classes('opacity-60')
                        ui.label('* Values shown in days (1 day = 8 hours)').classes('text-xs opacity-50')

            finally:
                db.close()

        def render_team_usage():
            """Render team usage report (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            # Local filter state for tile selection
            tile_filter = {'selected': None}  # None = all, or 'VACATION', 'SICK', etc.

            # Store request data for detail lookup (plain dicts, not ORM objects)
            request_lookup = {}

            def show_request_detail(request_id):
                """Show a detail dialog for a request."""
                data = request_lookup.get(request_id)
                if not data:
                    return

                # Type color for styling
                type_colors = {
                    'vacation': '#3b82f6', 'sick': '#22c55e',
                    'personal': '#a855f7', 'work_from_home': '#ef4444'
                }
                type_color = type_colors.get(data['pto_type'].lower(), '#6b7280')

                with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
                    # Header with type badge
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Request Details').classes('text-lg font-bold')
                        ui.badge(data['pto_type'].replace('_', ' ').title(), color='primary').style(f'background-color: {type_color}')

                    # Employee info
                    with ui.row().classes('w-full items-center gap-3 mb-4 pb-4').style('border-bottom: 1px solid #374151'):
                        ui.icon('person', size='md').style(f'color: {type_color}')
                        with ui.column().classes('gap-0'):
                            ui.label(data['employee_name']).classes('font-semibold')
                            ui.label(data['department']).classes('text-sm opacity-60')

                    # Date range
                    with ui.row().classes('w-full gap-8 mb-4'):
                        with ui.column().classes('gap-1'):
                            ui.label('Start Date').classes('text-xs opacity-60 uppercase')
                            ui.label(data['start_date']).classes('font-medium')
                        with ui.column().classes('gap-1'):
                            ui.label('End Date').classes('text-xs opacity-60 uppercase')
                            ui.label(data['end_date']).classes('font-medium')

                    # Days and status
                    with ui.row().classes('w-full gap-8 mb-4'):
                        with ui.column().classes('gap-1'):
                            ui.label('Total Days').classes('text-xs opacity-60 uppercase')
                            ui.label(data['days']).classes('font-medium text-lg').style(f'color: {type_color}')
                        with ui.column().classes('gap-1'):
                            ui.label('Status').classes('text-xs opacity-60 uppercase')
                            status_colors = {'approved': '#22c55e', 'pending': '#f59e0b', 'denied': '#ef4444', 'cancelled': '#6b7280'}
                            ui.label(data['status'].title()).classes('font-medium').style(f'color: {status_colors.get(data["status"], "#6b7280")}')

                    # Notes if present
                    if data.get('notes'):
                        with ui.column().classes('w-full mb-4 p-3 rounded').style('background-color: #374151'):
                            ui.label('Notes').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(data['notes']).classes('text-sm')

                    # Approval info if approved/denied
                    if data['status'] in ['approved', 'denied'] and data.get('approved_by'):
                        with ui.column().classes('w-full mb-4'):
                            ui.label('Approved By' if data['status'] == 'approved' else 'Denied By').classes('text-xs opacity-60 uppercase mb-1')
                            ui.label(data['approved_by']).classes('text-sm')
                            if data.get('approved_at'):
                                ui.label(data['approved_at']).classes('text-xs opacity-60')

                    # OK button
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('OK', on_click=dialog.close).props('color=primary')

                dialog.open()

            db = next(get_db())
            try:
                # Base query for approved requests
                base_query = db.query(PTORequest, User).join(
                    User, PTORequest.user_id == User.id
                ).filter(
                    PTORequest.start_date >= date(filter_state['year'], 1, 1),
                    PTORequest.end_date <= date(filter_state['year'], 12, 31),
                    PTORequest.status == 'approved'
                )

                if filter_state['department_id']:
                    base_query = base_query.filter(User.department_id == filter_state['department_id'])

                if filter_state.get('employee_id'):
                    base_query = base_query.filter(User.id == filter_state['employee_id'])

                all_results = base_query.order_by(PTORequest.start_date.desc()).all()

                # Get team balances for available calculation
                balance_query = db.query(PTOBalance).join(User).filter(
                    PTOBalance.year == filter_state['year'],
                    User.is_active == True
                )
                if filter_state['department_id']:
                    balance_query = balance_query.filter(User.department_id == filter_state['department_id'])
                if filter_state.get('employee_id'):
                    balance_query = balance_query.filter(User.id == filter_state['employee_id'])
                balances = balance_query.all()

                # Calculate team totals for available balance
                team_available = {
                    'VACATION': sum(float(b.vacation_total or 0) - float(b.vacation_used or 0) for b in balances) / 8,
                    'SICK': sum(float(b.sick_total or 0) - float(b.sick_used or 0) for b in balances) / 8,
                    'PERSONAL': sum(float(b.personal_total or 0) - float(b.personal_used or 0) for b in balances) / 8,
                    'WORK_FROM_HOME': 0,  # WFH has no balance limit
                }

                with ui.card().classes('w-full'):
                    ui.label(f'Team Usage Report - {filter_state["year"]}').classes('text-lg font-semibold mb-4')

                    if not all_results:
                        with ui.column().classes('w-full items-center py-8'):
                            ui.icon('event_busy', size='3rem').classes('opacity-30 mb-2')
                            ui.label('No requests found for this period.').classes('opacity-60')
                        return

                    # Summary by type - track full days vs half days
                    type_summary = {}
                    for request, user_obj in all_results:
                        pto_type = request.pto_type.upper()
                        if pto_type not in type_summary:
                            type_summary[pto_type] = {'count': 0, 'days': 0, 'full_days': 0, 'half_days': 0}
                        type_summary[pto_type]['count'] += 1
                        total_days = float(request.total_days or 0)
                        type_summary[pto_type]['days'] += total_days
                        if total_days >= 1:
                            type_summary[pto_type]['full_days'] += 1
                        else:
                            type_summary[pto_type]['half_days'] += 1

                    # Color coding: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                    type_colors = {
                        'VACATION': '#3b82f6',
                        'SICK': '#22c55e',
                        'PERSONAL': '#a855f7',
                        'WORK_FROM_HOME': '#ef4444',
                    }

                    type_display_names = {
                        'VACATION': 'Vacation',
                        'SICK': 'Sick',
                        'PERSONAL': 'Personal',
                        'WORK_FROM_HOME': 'WFH',
                    }

                    # Tile references for styling
                    tile_refs = {}

                    # Table container placeholder (created later, after tiles)
                    table_container_ref = {'container': None}

                    def render_table(filter_type=None):
                        """Render the requests table, optionally filtered by PTO type."""
                        if not table_container_ref['container']:
                            return
                        table_container_ref['container'].clear()

                        if filter_type:
                            filtered_results = [(r, u) for r, u in all_results if r.pto_type.upper() == filter_type]
                            filter_label = type_display_names.get(filter_type, filter_type.title())
                        else:
                            filtered_results = all_results
                            filter_label = None

                        with table_container_ref['container']:
                            if not filtered_results:
                                with ui.column().classes('w-full items-center py-8'):
                                    ui.icon('event_busy', size='2rem').classes('opacity-30 mb-2')
                                    ui.label(f'No {filter_label.lower() if filter_label else ""} requests found.').classes('opacity-60')
                                return

                            columns = [
                                {'name': 'employee', 'label': 'Employee', 'field': 'employee', 'sortable': True, 'align': 'left'},
                                {'name': 'type', 'label': 'Type', 'field': 'type', 'sortable': True, 'align': 'left'},
                                {'name': 'start_date', 'label': 'Start', 'field': 'start_date', 'sortable': True},
                                {'name': 'end_date', 'label': 'End', 'field': 'end_date', 'sortable': True},
                                {'name': 'days', 'label': 'Days', 'field': 'days', 'sortable': True},
                                {'name': 'status', 'label': 'Status', 'field': 'status', 'sortable': True},
                            ]

                            rows = []
                            for request, user_obj in filtered_results:
                                # Store plain data for detail lookup (db session will be closed)
                                request_lookup[request.id] = {
                                    'pto_type': request.pto_type,
                                    'employee_name': f'{user_obj.first_name} {user_obj.last_name}',
                                    'department': user_obj.department.name if user_obj.department else 'No Department',
                                    'start_date': request.start_date.strftime('%A, %B %d, %Y'),
                                    'end_date': request.end_date.strftime('%A, %B %d, %Y'),
                                    'days': fmt_days(float(request.total_days or 0)),
                                    'status': request.status,
                                    'notes': request.notes,
                                    'approved_by': request.approved_by,
                                    'approved_at': request.approved_at.strftime('%B %d, %Y at %I:%M %p') if request.approved_at else None,
                                }
                                # Get color for this PTO type
                                pto_color = type_colors.get(request.pto_type.upper(), '#6b7280')
                                rows.append({
                                    'id': request.id,
                                    'employee': f'{user_obj.first_name} {user_obj.last_name}',
                                    'type': request.pto_type.title(),
                                    'start_date': request.start_date.strftime('%A, %B %d, %Y'),
                                    'end_date': request.end_date.strftime('%A, %B %d, %Y'),
                                    'days': fmt_days(float(request.total_days or 0)),
                                    'status': request.status.title(),
                                    'row_color': pto_color,
                                })

                            table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

                            # Add colored left border to rows and handle click
                            table.add_slot('body', '''
                                <q-tr :props="props" style="cursor: pointer;"
                                      @click="$parent.$emit('row-click', $event, props.row)">
                                    <q-td v-for="(col, index) in props.cols" :key="col.name" :props="props"
                                          :style="index === 0 ? 'border-left: 4px solid ' + props.row.row_color + ';' : ''">
                                        {{ col.value }}
                                    </q-td>
                                </q-tr>
                            ''')

                            def on_row_click(e):
                                """Handle row click to show detail dialog."""
                                row = e.args[1]  # Second arg is the row data
                                if row and 'id' in row:
                                    show_request_detail(row['id'])

                            table.on('row-click', on_row_click)

                            total_label = f'Showing: {len(rows)} {filter_label.lower() if filter_label else ""} requests'
                            ui.label(total_label.strip() + ' (click row for details)').classes('mt-2 opacity-60')

                    def on_tile_click(pto_type):
                        """Handle tile click - toggle filter."""
                        if tile_filter['selected'] == pto_type:
                            # Deselect - show all
                            tile_filter['selected'] = None
                            render_table(None)
                        else:
                            # Select this type
                            tile_filter['selected'] = pto_type
                            render_table(pto_type)

                        # Update tile styling
                        for t, ref in tile_refs.items():
                            color = type_colors.get(t, '#6b7280')
                            if tile_filter['selected'] == t:
                                ref.style(f'background-color: rgba(255,255,255,0.1); border-left: 4px solid {color};')
                            else:
                                ref.style(f'background-color: transparent; border-left: 4px solid {color};')

                    # Summary tiles - transparent with left border, clickable (BEFORE table)
                    with ui.row().classes('w-full gap-4 mb-4'):
                        for pto_type in ['VACATION', 'SICK', 'PERSONAL', 'WORK_FROM_HOME']:
                            stats = type_summary.get(pto_type, {'count': 0, 'days': 0, 'full_days': 0, 'half_days': 0})
                            color = type_colors.get(pto_type, '#6b7280')
                            display_name = type_display_names.get(pto_type, pto_type.replace('_', ' ').title())
                            available = team_available.get(pto_type, 0)

                            def make_handler(t=pto_type):
                                return lambda: on_tile_click(t)

                            tile = ui.element('div').classes('flex-1 p-4 rounded-lg cursor-pointer hover:bg-white/5').style(
                                f'background-color: transparent; border-left: 4px solid {color};'
                            ).on('click', make_handler())
                            tile_refs[pto_type] = tile

                            with tile:
                                ui.label(display_name).classes('font-semibold text-base').style(f'color: {color}')
                                # Show breakdown
                                full_days = stats['full_days']
                                half_days = stats['half_days']
                                if half_days > 0 and full_days > 0:
                                    breakdown = f'{full_days} full + {half_days} half day'
                                elif half_days > 0:
                                    breakdown = f'{half_days} half day request{"s" if half_days > 1 else ""}'
                                else:
                                    breakdown = f'{stats["count"]} request{"s" if stats["count"] > 1 else ""}'
                                ui.label(breakdown).classes('text-sm opacity-70')

                                # Show "X days used with Y available"
                                used_days = stats['days']
                                if pto_type == 'WORK_FROM_HOME':
                                    ui.label(fmt_days(used_days)).classes('text-xl font-bold')
                                else:
                                    ui.label(f'{fmt_days(used_days)} used / {fmt_days(available)} avail').classes('text-lg font-bold')

                    # Table container (AFTER tiles)
                    table_container_ref['container'] = ui.column().classes('w-full')

                    # Initial table render
                    render_table(None)

            finally:
                db.close()

        def render_audit_report():
            """Render enhanced audit log with modern filters (managers/admins only)."""
            if not is_manager_or_admin:
                ui.label('Access denied').classes('text-red-500')
                return

            # Action color mapping for badges
            action_colors = {
                'login': '#22c55e',  # green
                'logout': '#22c55e',  # green
                'pto_approve': '#22c55e',  # green
                'carryover_approve': '#22c55e',  # green
                'pto_deny': '#ef4444',  # red
                'carryover_deny': '#ef4444',  # red
                'pto_cancel': '#f59e0b',  # amber
                'pto_request': '#3b82f6',  # blue
                'carryover_request': '#3b82f6',  # blue
                'user_create': '#8b5cf6',  # purple
                'user_update': '#8b5cf6',  # purple
                'user_delete': '#ef4444',  # red
                'balance_update': '#06b6d4',  # cyan
            }
            default_color = '#6b7280'  # gray

            # Quick action filter categories
            action_categories = {
                'all': {'label': 'All', 'actions': None, 'icon': 'list'},
                'logins': {'label': 'Logins', 'actions': ['login', 'logout'], 'icon': 'login'},
                'approvals': {'label': 'Approvals', 'actions': ['pto_approve', 'carryover_approve'], 'icon': 'check_circle'},
                'denials': {'label': 'Denials', 'actions': ['pto_deny', 'carryover_deny'], 'icon': 'cancel'},
                'requests': {'label': 'Requests', 'actions': ['pto_request', 'carryover_request'], 'icon': 'add_circle'},
                'user_changes': {'label': 'User Changes', 'actions': ['user_create', 'user_update', 'user_delete', 'balance_update'], 'icon': 'person'},
            }

            # Date presets
            today = date.today()
            date_presets = {
                'today': {'label': 'Today', 'from': today, 'to': today},
                'last_7': {'label': 'Last 7 Days', 'from': today - timedelta(days=7), 'to': today},
                'last_30': {'label': 'Last 30 Days', 'from': today - timedelta(days=30), 'to': today},
                'this_month': {'label': 'This Month', 'from': today.replace(day=1), 'to': today},
                'custom': {'label': 'Custom', 'from': None, 'to': None},
            }

            db = next(get_db())
            try:
                # Get distinct users for filter dropdown
                user_list = db.query(AuditLog.user_id, AuditLog.username).distinct().filter(AuditLog.user_id.isnot(None)).all()
                user_options = {'all': 'All Users'}
                for uid, uname in user_list:
                    if uid:
                        user_options[str(uid)] = uname or f'User #{uid}'

                with ui.card().classes('w-full'):
                    ui.label('System Audit Log').classes('text-lg font-semibold mb-4')

                    # Quick action filter chips
                    chip_refs = {}
                    with ui.row().classes('w-full gap-2 mb-4 flex-wrap'):
                        for key, cat in action_categories.items():
                            is_selected = filter_state['audit_action'] == key

                            def make_chip_handler(k):
                                def handler():
                                    filter_state['audit_action'] = k
                                    render_report()
                                return handler

                            chip = ui.button(cat['label'], icon=cat['icon'], on_click=make_chip_handler(key)).props(
                                f'{"" if is_selected else "outline"} dense rounded'
                            ).classes('text-sm')
                            if is_selected:
                                chip.props('color=primary')
                            chip_refs[key] = chip

                    # Search and filters row
                    with ui.row().classes('w-full gap-4 items-end flex-wrap mb-4'):
                        # Text search
                        def on_search_change(e):
                            filter_state['audit_search'] = e.value or ''
                            render_report()

                        ui.input(
                            placeholder='Search user, entity, details...',
                            value=filter_state['audit_search'],
                            on_change=on_search_change
                        ).props('dense outlined clearable').classes('w-64').style('min-width: 200px;')

                        # User filter
                        def on_user_change(e):
                            filter_state['audit_user'] = e.value
                            render_report()

                        ui.select(
                            user_options,
                            label='User',
                            value=filter_state['audit_user'],
                            on_change=on_user_change
                        ).props('dense outlined').classes('w-40')

                        # Date preset buttons
                        with ui.row().classes('gap-1'):
                            for preset_key, preset in date_presets.items():
                                if preset_key == 'custom':
                                    continue  # Handle custom separately
                                is_active = filter_state['audit_preset'] == preset_key

                                def make_preset_handler(pk, pv):
                                    def handler():
                                        filter_state['audit_preset'] = pk
                                        filter_state['audit_date_from'] = pv['from'].strftime('%Y-%m-%d') if pv['from'] else None
                                        filter_state['audit_date_to'] = pv['to'].strftime('%Y-%m-%d') if pv['to'] else None
                                        render_report()
                                    return handler

                                btn = ui.button(preset['label'], on_click=make_preset_handler(preset_key, preset)).props(
                                    f'dense flat {"color=primary" if is_active else ""}'
                                ).classes('text-xs')

                        # Custom date range
                        with ui.row().classes('gap-2 items-center'):
                            def on_date_from_change(e):
                                filter_state['audit_date_from'] = e.value
                                filter_state['audit_preset'] = 'custom'
                                render_report()

                            def on_date_to_change(e):
                                filter_state['audit_date_to'] = e.value
                                filter_state['audit_preset'] = 'custom'
                                render_report()

                            with ui.input('From').props('dense outlined').classes('w-32') as date_from:
                                date_from.value = filter_state['audit_date_from'] or ''
                                with date_from.add_slot('append'):
                                    ui.icon('event').on('click', lambda: menu_from.open()).classes('cursor-pointer')
                                with ui.menu() as menu_from:
                                    ui.date(on_change=lambda e: (setattr(date_from, 'value', e.value), on_date_from_change(e), menu_from.close()))

                            with ui.input('To').props('dense outlined').classes('w-32') as date_to:
                                date_to.value = filter_state['audit_date_to'] or ''
                                with date_to.add_slot('append'):
                                    ui.icon('event').on('click', lambda: menu_to.open()).classes('cursor-pointer')
                                with ui.menu() as menu_to:
                                    ui.date(on_change=lambda e: (setattr(date_to, 'value', e.value), on_date_to_change(e), menu_to.close()))

                        # Clear all filters
                        def clear_filters():
                            filter_state['audit_action'] = 'all'
                            filter_state['audit_date_from'] = None
                            filter_state['audit_date_to'] = None
                            filter_state['audit_search'] = ''
                            filter_state['audit_user'] = 'all'
                            filter_state['audit_preset'] = 'last_30'
                            render_report()

                        ui.button('Clear All', icon='clear', on_click=clear_filters).props('flat dense')

                    # Build query with filters
                    query = db.query(AuditLog)

                    # Date range filters based on preset or custom
                    if filter_state['audit_preset'] != 'custom' and filter_state['audit_preset'] in date_presets:
                        preset = date_presets[filter_state['audit_preset']]
                        if preset['from']:
                            query = query.filter(AuditLog.created_at >= datetime.combine(preset['from'], datetime.min.time()))
                        if preset['to']:
                            query = query.filter(AuditLog.created_at <= datetime.combine(preset['to'], datetime.max.time()))
                    else:
                        # Custom date range
                        if filter_state['audit_date_from']:
                            try:
                                from_date = datetime.strptime(filter_state['audit_date_from'], '%Y-%m-%d')
                                query = query.filter(AuditLog.created_at >= from_date)
                            except ValueError:
                                pass

                        if filter_state['audit_date_to']:
                            try:
                                to_date = datetime.strptime(filter_state['audit_date_to'], '%Y-%m-%d')
                                to_date = to_date.replace(hour=23, minute=59, second=59)
                                query = query.filter(AuditLog.created_at <= to_date)
                            except ValueError:
                                pass

                    # Action category filter
                    if filter_state['audit_action'] != 'all' and filter_state['audit_action'] in action_categories:
                        actions = action_categories[filter_state['audit_action']]['actions']
                        if actions:
                            query = query.filter(AuditLog.action.in_(actions))

                    # User filter
                    if filter_state['audit_user'] != 'all':
                        try:
                            uid = int(filter_state['audit_user'])
                            query = query.filter(AuditLog.user_id == uid)
                        except ValueError:
                            pass

                    results = query.order_by(AuditLog.created_at.desc()).limit(500).all()

                    # Apply text search filter (client-side for flexibility)
                    search_term = filter_state['audit_search'].lower().strip()
                    if search_term:
                        filtered_results = []
                        for log in results:
                            searchable = ' '.join([
                                log.username or '',
                                log.entity_type or '',
                                str(log.entity_id) if log.entity_id else '',
                                log.details or '',
                                log.action or ''
                            ]).lower()
                            if search_term in searchable:
                                filtered_results.append(log)
                        results = filtered_results

                    # Summary stats row
                    if results:
                        stats = {}
                        for log in results:
                            action = log.action
                            stats[action] = stats.get(action, 0) + 1

                        with ui.row().classes('w-full gap-3 mb-4 flex-wrap'):
                            # Show top action counts
                            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:6]
                            for action, count in sorted_stats:
                                color = action_colors.get(action, default_color)
                                with ui.element('div').classes('flex items-center gap-2 px-3 py-1 rounded-full').style(
                                    f'background-color: {color}20; border: 1px solid {color};'
                                ):
                                    ui.label(action.replace('_', ' ').title()).classes('text-xs font-medium').style(f'color: {color};')
                                    ui.label(str(count)).classes('text-xs font-bold').style(f'color: {color};')

                    if not results:
                        with ui.column().classes('w-full items-center py-8'):
                            ui.icon('history', size='3rem').classes('opacity-30 mb-2')
                            ui.label('No audit records found for this period.').classes('opacity-60')
                        return

                    columns = [
                        {'name': 'date', 'label': 'Date/Time', 'field': 'date', 'sortable': True},
                        {'name': 'user', 'label': 'User', 'field': 'user', 'sortable': True, 'align': 'left'},
                        {'name': 'action', 'label': 'Action', 'field': 'action', 'sortable': True, 'align': 'left'},
                        {'name': 'entity', 'label': 'Entity', 'field': 'entity', 'sortable': True, 'align': 'left'},
                        {'name': 'details', 'label': 'Details', 'field': 'details', 'align': 'left'},
                    ]

                    rows = []
                    for log in results:
                        # Parse details if available
                        detail_str = ''
                        if log.details:
                            try:
                                import json
                                details = json.loads(log.details)
                                if isinstance(details, dict):
                                    detail_str = ', '.join(f'{k}: {v}' for k, v in list(details.items())[:3])
                            except (json.JSONDecodeError, TypeError):
                                detail_str = str(log.details)[:50]

                        # Get color for action badge
                        action_color = action_colors.get(log.action, default_color)

                        rows.append({
                            'id': log.id,
                            'date': log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else '-',
                            'user': log.username or f'User #{log.user_id}' if log.user_id else 'System',
                            'action': log.action.replace('_', ' ').title(),
                            'action_raw': log.action,
                            'action_color': action_color,
                            'entity': f'{log.entity_type or ""} #{log.entity_id}' if log.entity_id else log.entity_type or '-',
                            'details': detail_str[:100] if detail_str else '-',
                            'details_full': detail_str,
                        })

                    # Custom table with color-coded action badges
                    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

                    # Add custom body slot for action column with colored badges
                    table.add_slot('body-cell-action', '''
                        <q-td :props="props">
                            <q-badge :style="'background-color: ' + props.row.action_color">
                                {{ props.row.action }}
                            </q-badge>
                        </q-td>
                    ''')

                    # Add expandable details on row click
                    table.add_slot('body-cell-details', '''
                        <q-td :props="props">
                            <div class="cursor-pointer" @click="props.expand = !props.expand">
                                {{ props.row.details }}
                                <q-icon v-if="props.row.details_full && props.row.details_full.length > 50"
                                        :name="props.expand ? 'expand_less' : 'expand_more'" size="xs" />
                            </div>
                        </q-td>
                    ''')

                    ui.label(f'Showing {len(rows)} records (max 500)').classes('mt-2 opacity-60')

            finally:
                db.close()

        def export_csv():
            """Export current report to CSV."""
            db = next(get_db())
            try:
                output = StringIO()
                writer = csv.writer(output)
                report_type = filter_state['report_type']

                if report_type == 'my_pto':
                    # Combined PTO export with balance and history
                    writer.writerow(['=== Balance Summary ==='])
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
                    writer.writerow([])
                    writer.writerow(['=== PTO History ==='])
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
                    filename = f'my_pto_{filter_state["year"]}.csv'

                elif report_type == 'my_history':
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
                    writer.writerow(['Date/Time', 'User', 'Action', 'Entity', 'Details'])

                    # Build query with same filters as display
                    query = db.query(AuditLog)
                    year_start = date(filter_state['year'], 1, 1)
                    year_end = date(filter_state['year'], 12, 31)

                    if filter_state['audit_date_from']:
                        try:
                            from_date = datetime.strptime(filter_state['audit_date_from'], '%Y-%m-%d')
                            query = query.filter(AuditLog.created_at >= from_date)
                        except ValueError:
                            query = query.filter(AuditLog.created_at >= year_start)
                    else:
                        query = query.filter(AuditLog.created_at >= year_start)

                    if filter_state['audit_date_to']:
                        try:
                            to_date = datetime.strptime(filter_state['audit_date_to'], '%Y-%m-%d')
                            to_date = to_date.replace(hour=23, minute=59, second=59)
                            query = query.filter(AuditLog.created_at <= to_date)
                        except ValueError:
                            query = query.filter(AuditLog.created_at <= year_end)
                    else:
                        query = query.filter(AuditLog.created_at <= year_end)

                    if filter_state['audit_action'] != 'all':
                        query = query.filter(AuditLog.action == filter_state['audit_action'])

                    for log in query.order_by(AuditLog.created_at.desc()).limit(500).all():
                        detail_str = ''
                        if log.details:
                            try:
                                import json
                                details = json.loads(log.details)
                                if isinstance(details, dict):
                                    detail_str = ', '.join(f'{k}: {v}' for k, v in details.items())
                            except (json.JSONDecodeError, TypeError):
                                detail_str = str(log.details)
                        entity_str = f'{log.entity_type or ""} #{log.entity_id}' if log.entity_id else log.entity_type or ''
                        writer.writerow([
                            log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else '',
                            log.username or f'User #{log.user_id}' if log.user_id else 'System',
                            log.action.replace('_', ' ').title(),
                            entity_str,
                            detail_str
                        ])

                    filename = f'audit_log_{filter_state["year"]}.csv'

                else:
                    filename = 'report.csv'

                csv_content = output.getvalue()
                ui.download(csv_content.encode('utf-8'), filename)
                show_success_dialog('Download Complete', f'Downloaded {filename}')

            except Exception as e:
                show_error_dialog('Export Error', f'Error exporting CSV: {str(e)}')
            finally:
                db.close()

        def get_report_html():
            """Generate formatted HTML report using ReportService."""
            db = next(get_db())
            try:
                report_service = ReportService(db)
                report_type = filter_state['report_type']
                year = filter_state['year']

                if report_type == 'my_pto':
                    # Combined report: balance + history
                    balance_html = report_service.generate_balance_report_html(user_id, year)
                    history_html = report_service.generate_history_report_html(
                        user_id, year, filter_state['status_filter']
                    )
                    # Combine the two reports (strip closing tags from balance and opening from history)
                    return balance_html.replace('</body></html>', '<hr style="margin: 30px 0;">') + history_html.split('<body')[1].split('>', 1)[1]
                elif report_type == 'my_history':
                    return report_service.generate_history_report_html(
                        user_id, year, filter_state['status_filter']
                    )
                elif report_type == 'my_balance':
                    return report_service.generate_balance_report_html(user_id, year)
                elif report_type == 'my_calendar':
                    return report_service.generate_calendar_report_html(user_id, year)
                elif report_type == 'team_balance':
                    return report_service.generate_team_balance_report_html(
                        year, filter_state['department_id'], filter_state.get('employee_id')
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

                preview_dialog = ui.dialog().props('maximized')

                def go_to_dashboard():
                    preview_dialog.close()
                    ui.navigate.to('/dashboard')

                with preview_dialog, ui.card().classes('w-full h-full'):
                    with ui.row().classes('w-full justify-between items-center p-4 border-b'):
                        ui.label('Print Preview').classes('text-xl font-semibold')
                        with ui.row().classes('gap-2'):
                            ui.button('Print', icon='print', on_click=lambda: ui.run_javascript(f'''
                                // Open content in new window and print
                                const printWindow = window.open('', '_blank', 'width=800,height=600');
                                if (printWindow) {{
                                    printWindow.document.write(atob("{b64_content}"));
                                    printWindow.document.close();
                                    printWindow.focus();
                                    setTimeout(function() {{
                                        printWindow.print();
                                    }}, 250);
                                }} else {{
                                    alert('Please allow pop-ups to print the report');
                                }}
                            ''')).props('color=primary')
                            ui.button('Close', icon='close', on_click=preview_dialog.close).props('flat')

                    # Create iframe and write content using JavaScript (avoids data URI security blocks)
                    ui.html('<iframe id="print-frame" style="width: 100%; height: calc(100vh - 140px); border: 1px solid #ddd; background: white;"></iframe>', sanitize=False).classes('w-full')
                    # Write HTML content to iframe using JavaScript
                    ui.run_javascript(f'''
                        const frame = document.getElementById('print-frame');
                        if (frame) {{
                            const doc = frame.contentDocument || frame.contentWindow.document;
                            doc.open();
                            doc.write(atob("{b64_content}"));
                            doc.close();
                        }}
                    ''')

                    # Footer with Back to Dashboard button
                    with ui.row().classes('w-full justify-start items-center p-4 border-t'):
                        ui.button('Back to Dashboard', icon='home', on_click=go_to_dashboard).props('outline')

                preview_dialog.open()
            except Exception as e:
                show_error_dialog('Preview Error', f'Error generating print preview: {str(e)}')

        def download_pdf():
            """Download report as PDF using reportlab."""
            try:
                html_content = get_report_html()
                report_type = filter_state['report_type']
                year = filter_state['year']
                filename = f'{report_type}_{year}.pdf'

                # Generate actual PDF using ExportService
                pdf_bytes = ExportService.generate_report_pdf(html_content, filename)
                ui.download(pdf_bytes, filename)
                show_success_dialog('Download Complete', f'Downloaded {filename}')
            except Exception as e:
                show_error_dialog('PDF Error', f'Error generating PDF: {str(e)}')

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
                        show_error_dialog('Invalid Email', 'Please enter a valid email address.')
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
                        else:  # PDF - generate actual PDF
                            try:
                                pdf_bytes = ExportService.generate_report_pdf(html_content, base_name)
                                attachment_data = pdf_bytes
                                attachment_name = f'{base_name}.pdf'
                                attachment_type = 'pdf'
                            except Exception as pdf_error:
                                show_warning_dialog('PDF Generation Failed', f'PDF generation failed: {pdf_error}. Sending as HTML instead.')
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
                            show_success_dialog('Email Sent', f'Report sent to {email_input.value}')
                            dialog.close()
                        else:
                            show_warning_dialog('Email Not Configured', 'Email service not configured. Please configure SMTP settings.')

                    except Exception as e:
                        show_error_dialog('Email Error', f'Error sending email: {str(e)}')

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
        render_actions()
        render_report_indicator()
        render_filters()
        render_report()

        # Navigation buttons at bottom
        with ui.row().classes('w-full justify-between mt-6'):
            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline')
            if is_manager_or_admin:
                ui.button('View Analytics', icon='insights', on_click=lambda: ui.navigate.to('/analytics')).props('outline')
