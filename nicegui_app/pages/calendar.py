"""Team Calendar page showing market holidays and approved PTO."""
from nicegui import ui, app
from src.database import get_db
from src.models.market_holiday import MarketHoliday
from src.models.pto_request import PTORequest
from src.models.user import User
from src.services.user_service import UserService
from src.services.department_service import DepartmentService
from datetime import date, timedelta
from calendar import monthcalendar, month_name
from collections import defaultdict
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog, show_info_dialog
from nicegui_app.components.formatting import fmt_days, format_days_hours
from nicegui_app.components.realtime_updates import setup_calendar_updates
from src.services.balance_service import BalanceService
from src.services.audit_service import AuditService
from datetime import datetime as dt


def calendar_page():
    """Team calendar page with monthly view of holidays and PTO."""

    apply_dark_mode()

    # Check if user is logged in
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')

    # Get user's department ID and Chicago status
    user_department_id = None
    is_chicago_employee = False
    db = next(get_db())
    try:
        from src.models.system_setting import SystemSetting
        current_user = db.query(User).filter(User.id == user_id).first()
        if current_user:
            user_department_id = current_user.department_id
            # Check if user is in Chicago AND Chicago leave is enabled
            user_is_in_chicago = current_user.location_city and current_user.location_city.lower() == 'chicago'
            chicago_setting = db.query(SystemSetting).filter(SystemSetting.key == 'chicago.safe_leave_enabled').first()
            is_chicago_employee = user_is_in_chicago and chicago_setting and chicago_setting.bool_value
    finally:
        db.close()

    # State for current month/year view
    today = date.today()
    current_month = {'month': today.month, 'year': today.year}

    # Load persisted preferences from session or use defaults
    calendar_prefs = app.storage.user.get('calendar_prefs', {})

    # State for filters with persistence
    selected_department = {'id': calendar_prefs.get('department_id', None)}
    selected_employee = {'id': calendar_prefs.get('employee_id', None)}  # New employee filter
    view_mode = {'mode': calendar_prefs.get('view_mode', 'my')}
    show_holidays = {'value': calendar_prefs.get('show_holidays', True)}
    show_weekends = {'value': calendar_prefs.get('show_weekends', False)}  # Default to weekdays only
    leave_type_filters = {
        'vacation': calendar_prefs.get('filter_vacation', True),
        'sick': calendar_prefs.get('filter_sick', True),
        'personal': calendar_prefs.get('filter_personal', True),
        'work_from_home': calendar_prefs.get('filter_work_from_home', True),
        'chicago_leave': calendar_prefs.get('filter_chicago_leave', True),  # Chicago leave (both types)
        'other': calendar_prefs.get('filter_other', True)
    }
    current_view = {'view': calendar_prefs.get('current_view', 'month')}  # 'month' or 'year'
    highlight_half_days = {'value': calendar_prefs.get('highlight_half_days', False)}

    # Store PTO request details for click handlers
    pto_requests_cache = {}

    def save_preferences():
        """Save current filter preferences to session."""
        app.storage.user['calendar_prefs'] = {
            'department_id': selected_department['id'],
            'employee_id': selected_employee['id'],
            'view_mode': view_mode['mode'],
            'show_holidays': show_holidays['value'],
            'show_weekends': show_weekends['value'],
            'filter_vacation': leave_type_filters['vacation'],
            'filter_sick': leave_type_filters['sick'],
            'filter_personal': leave_type_filters['personal'],
            'filter_work_from_home': leave_type_filters['work_from_home'],
            'filter_chicago_leave': leave_type_filters['chicago_leave'],
            'filter_other': leave_type_filters['other'],
            'current_view': current_view['view'],
            'highlight_half_days': highlight_half_days['value']
        }

    def show_wfh_for_employee_dialog():
        """Show dialog for managers to submit WFH request on behalf of an employee."""
        db = next(get_db())
        try:
            # Get employees based on role
            if user_role == 'superadmin':
                employees = db.query(User).filter(User.is_active == True).order_by(User.first_name).all()
            elif user_role == 'admin':
                employees = db.query(User).filter(User.is_active == True).order_by(User.first_name).all()
            else:  # manager
                current_manager = db.query(User).filter(User.id == user_id).first()
                if current_manager and current_manager.department_id:
                    employees = db.query(User).filter(
                        User.department_id == current_manager.department_id,
                        User.is_active == True,
                        User.id != user_id  # Exclude self - managers should use regular form
                    ).order_by(User.first_name).all()
                else:
                    employees = []

            employee_options = {emp.id: f"{emp.first_name} {emp.last_name}" for emp in employees}
        finally:
            db.close()

        if not employee_options:
            show_warning_dialog('No Employees', 'No employees found in your department to submit WFH for.')
            return

        with ui.dialog() as wfh_dialog, ui.card().classes('min-w-[400px] p-4'):
            ui.label('Submit WFH for Employee').classes('text-xl font-bold mb-4')
            ui.label('Submit a Work From Home request on behalf of a team member.').classes('text-sm opacity-70 mb-4')

            # Employee select
            employee_select = ui.select(
                employee_options,
                label='Select Employee',
                with_input=True
            ).props('outlined').classes('w-full mb-4')

            # Date select (within 1 week, excluding weekends)
            date_options = {}
            for i in range(8):  # Today through 7 days out
                d = date.today() + timedelta(days=i)
                if d.weekday() < 5:  # Monday=0 through Friday=4
                    label = "Today" if i == 0 else d.strftime('%A, %b %d')
                    date_options[d.isoformat()] = f"{label} ({d.strftime('%b %d, %Y')})"
            date_select = ui.select(
                date_options,
                label='Date',
                value=date.today().isoformat() if date.today().weekday() < 5 else list(date_options.keys())[0]
            ).props('outlined').classes('w-full mb-4')

            # Notes/reason (required)
            notes_input = ui.textarea(
                label='Reason (required)'
            ).props('outlined autogrow').classes('w-full mb-4')

            def submit_wfh_for_employee():
                if not employee_select.value:
                    show_warning_dialog('Employee Required', 'Please select an employee from the dropdown.')
                    return
                if not notes_input.value or not notes_input.value.strip():
                    show_warning_dialog('Reason Required', 'Please provide a reason for the Work From Home request.')
                    return

                wfh_db = next(get_db())
                try:
                    from src.services.pto_service import PTOService
                    from src.schemas.pto_schemas import PTORequestCreate

                    selected_date = date.fromisoformat(date_select.value)

                    request_data = PTORequestCreate(
                        user_id=employee_select.value,
                        pto_type='work_from_home',
                        start_date=selected_date,
                        end_date=selected_date,
                        total_days=1.0,
                        notes=f"[Submitted by manager] {notes_input.value.strip()}"
                    )

                    pto_service = PTOService(wfh_db)
                    pto_request = pto_service.create_request(request_data)

                    # Auto-approve since manager is submitting
                    if pto_request.status == 'pending':
                        pto_service.approve_request(pto_request.id, user_id)

                    wfh_db.commit()
                    show_success_dialog('WFH Submitted', f'WFH submitted for {employee_options[employee_select.value]}')
                    wfh_dialog.close()
                    render_current_view()
                except Exception as e:
                    show_error_dialog('Error', f'Error submitting WFH: {str(e)}')
                finally:
                    wfh_db.close()

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=wfh_dialog.close).props('flat')
                ui.button('Submit WFH', icon='home_work', on_click=submit_wfh_for_employee).props('color=red')

        wfh_dialog.open()

    # Main container
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):
        # Print CSS styles - printer-friendly with white background
        ui.add_head_html('''
        <style>
            @media print {
                /* Hide specific non-essential elements */
                .no-print,
                .q-drawer,
                .q-expansion-item {
                    display: none !important;
                }

                /* Reset page margins and use landscape */
                @page {
                    size: landscape;
                    margin: 0.3in;
                }

                /* Force white background on page */
                html, body {
                    background: white !important;
                    color: black !important;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }

                /* Main container - white background */
                .q-page, .q-layout, .q-page-container, .nicegui-content {
                    background: white !important;
                }

                /* Override dark mode backgrounds */
                body.body--dark,
                .body--dark .q-page,
                .body--dark .q-card,
                .body--dark .q-layout {
                    background: white !important;
                    color: black !important;
                }

                /* Cards - white with border, no shadow */
                .q-card {
                    box-shadow: none !important;
                    background: white !important;
                    border: 1px solid #ccc !important;
                }

                /* Force dark text everywhere */
                body, p, span, div, label, td, th {
                    color: black !important;
                }

                /* Calendar grid cells - white background */
                .print-calendar td,
                .print-calendar th {
                    background: white !important;
                    border: 1px solid #999 !important;
                    color: black !important;
                }

                /* Day header row - light gray */
                .print-calendar th,
                .print-calendar .font-bold {
                    background: #f0f0f0 !important;
                }

                /* PTO event colors - light pastels for print */
                [class*="bg-blue"] { background-color: #dbeafe !important; }
                [class*="bg-green"] { background-color: #dcfce7 !important; }
                [class*="bg-purple"] { background-color: #f3e8ff !important; }
                [class*="bg-red"] { background-color: #fee2e2 !important; }
                [class*="bg-orange"] { background-color: #ffedd5 !important; }
                [class*="bg-amber"] { background-color: #fef3c7 !important; }
                [class*="bg-teal"] { background-color: #ccfbf1 !important; }
                [class*="bg-indigo"] { background-color: #e0e7ff !important; }
                [class*="bg-gray"], [class*="bg-grey"] { background-color: #f3f4f6 !important; }

                /* Remove max-width constraint for print */
                .max-w-6xl {
                    max-width: 100% !important;
                    padding: 0.1in !important;
                    margin: 0 !important;
                }

                /* Print header visible */
                .print-header {
                    display: flex !important;
                    color: black !important;
                    margin-bottom: 0.2in !important;
                }
            }

            /* Hide print header on screen */
            .print-header {
                display: none;
            }
        </style>
        ''')

        # Print header (only visible when printing)
        with ui.row().classes('print-header w-full justify-between items-center mb-2'):
            ui.label('Team Calendar').classes('text-xl font-bold')

        # Header with greeting
        page_header(title='CALENDAR', show_back=False)

        # ===== VIEW TOGGLE + ACTION BUTTONS ===== (hidden in print)
        with ui.row().classes('w-full mb-4 gap-2 justify-between items-center no-print'):
            # Left side: View toggle
            with ui.row().classes('gap-2 items-center'):
                ui.label('View:').classes('font-medium self-center')

                # Create buttons first, then define handlers that reference them
                my_btn = ui.button('My Calendar')
                team_label = 'TEAM CALENDAR'
                team_btn = ui.button(team_label)

                def update_view_button_styles():
                    """Update button styles based on current view mode."""
                    if view_mode['mode'] == 'my':
                        my_btn.props(remove='outline')
                        my_btn.props('color=primary unelevated')
                        team_btn.props(remove='color=primary unelevated')
                        team_btn.props('outline')
                    else:
                        my_btn.props(remove='color=primary unelevated')
                        my_btn.props('outline')
                        team_btn.props(remove='outline')
                        team_btn.props('color=primary unelevated')

                def set_view_mode(mode):
                    view_mode['mode'] = mode
                    update_view_button_styles()
                    save_preferences()
                    render_current_view()

                my_btn.on('click', lambda: set_view_mode('my'))
                team_btn.on('click', lambda: set_view_mode('team'))

                # Set initial styles
                update_view_button_styles()

            # Right side: Action buttons
            with ui.row().classes('gap-2 items-center'):
                ui.button('PTO Request', icon='add', on_click=lambda: ui.navigate.to('/submit-request')).props('color=primary')

                # Submit WFH for Employee button (managers/admins only)
                if user_role in ['manager', 'admin', 'superadmin']:
                    ui.button('WFH for Employee', icon='home_work', on_click=lambda: show_wfh_for_employee_dialog()).props('color=red outline')

                def print_calendar():
                    ui.run_javascript('window.print()')

                ui.button('Print', icon='print', on_click=print_calendar).props('outline')

        # ===== FILTERS ROW =====
        with ui.expansion('Filters & Options', icon='filter_list').classes('w-full mb-4'):
            with ui.column().classes('w-full gap-4 p-2'):
                # Row 1: Department filter (superadmin only) and Leave Type filters
                with ui.row().classes('w-full gap-6 flex-wrap'):
                    # Department filter (superadmin only - they can see all departments)
                    if user_role == 'superadmin':
                        with ui.column().classes('gap-1'):
                            ui.label('Department').classes('text-sm font-medium')
                            db = next(get_db())
                            try:
                                departments = DepartmentService.get_all_departments(db)
                                dept_options = {None: 'All Departments'}
                                dept_options.update({dept.id: dept.name for dept in departments})
                            finally:
                                db.close()

                            def on_dept_change(e):
                                selected_department['id'] = e.value
                                # Reset employee filter when department changes
                                selected_employee['id'] = None
                                save_preferences()
                                render_current_view()

                            dept_select = ui.select(
                                dept_options,
                                value=selected_department['id'],
                                on_change=on_dept_change
                            ).classes('w-48')

                            # Disable when in "My Calendar" mode
                            if view_mode['mode'] == 'my':
                                dept_select.disable()

                    # Employee filter (managers, admins, superadmins - team view only)
                    if user_role in ['manager', 'admin', 'superadmin']:
                        with ui.column().classes('gap-1'):
                            ui.label('Employee').classes('text-sm font-medium')
                            db = next(get_db())
                            try:
                                emp_options = {None: 'All Employees'}
                                if user_role in ['manager', 'admin']:
                                    # Manager/Admin sees only their department's employees
                                    if user_department_id:
                                        employees = db.query(User).filter(
                                            User.department_id == user_department_id,
                                            User.is_active == True
                                        ).order_by(User.first_name).all()
                                        for emp in employees:
                                            emp_options[emp.id] = f"{emp.first_name} {emp.last_name}"
                                else:
                                    # Superadmin sees employees based on department filter
                                    emp_query = db.query(User).filter(User.is_active == True)
                                    if selected_department['id']:
                                        emp_query = emp_query.filter(User.department_id == selected_department['id'])
                                    employees = emp_query.order_by(User.first_name).all()
                                    for emp in employees:
                                        emp_options[emp.id] = f"{emp.first_name} {emp.last_name}"
                            finally:
                                db.close()

                            def on_emp_change(e):
                                selected_employee['id'] = e.value
                                save_preferences()
                                render_current_view()

                            # Validate selected employee exists in options
                            if selected_employee['id'] not in emp_options:
                                selected_employee['id'] = None

                            emp_select = ui.select(
                                emp_options,
                                value=selected_employee['id'],
                                on_change=on_emp_change
                            ).classes('w-48')

                            # Disable when in "My Calendar" mode
                            if view_mode['mode'] == 'my':
                                emp_select.disable()

                    # Display Options
                    with ui.column().classes('gap-1'):
                        ui.label('Display Options').classes('text-sm font-medium')
                        with ui.row().classes('gap-4'):
                            def on_weekends_change(e):
                                show_weekends['value'] = e.value
                                save_preferences()
                                render_current_view()

                            ui.checkbox(
                                'Show Weekends',
                                value=show_weekends['value'],
                                on_change=on_weekends_change
                            )

        # ===== MY BALANCE SUMMARY ===== (hidden in print)
        balance_container = ui.column().classes('w-full mb-4 no-print')

        def render_balance_summary():
            """Render the user's PTO balance summary."""
            balance_container.clear()
            with balance_container:
                db = next(get_db())
                try:
                    balance_service = BalanceService(db)
                    year = current_month['year']
                    balance = balance_service.get_or_create_balance(user_id, year)

                    # Calculate available days for each type
                    vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                    vac_used = float(balance.vacation_used or 0)
                    vac_pending = float(balance.vacation_pending or 0)
                    vac_avail = (vac_total - vac_used - vac_pending) / 8

                    sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                    sick_used = float(balance.sick_used or 0)
                    sick_avail = (sick_total - sick_used) / 8

                    personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                    personal_used = float(balance.personal_used or 0)
                    personal_avail = (personal_total - personal_used) / 8

                    with ui.card().classes('w-full p-4 shadow-md'):
                        with ui.row().classes('w-full items-center gap-4 flex-wrap'):
                            ui.label(f'My {year} Balance').classes('font-bold text-lg')
                            ui.element('div').classes('flex-grow')

                            # Vacation
                            with ui.row().classes('gap-2 items-center'):
                                ui.element('div').classes('w-4 h-4 bg-blue-500 rounded-full')
                                vac_hours = vac_total - vac_used - vac_pending
                                vac_display, vac_tooltip = format_days_hours(vac_hours)
                                ui.label(f'Vacation: {vac_display}').classes('font-medium text-blue-600').tooltip(vac_tooltip)
                                if vac_pending > 0:
                                    pending_display, _ = format_days_hours(vac_pending)
                                    ui.label(f'({pending_display} pending)').classes('text-xs text-amber-500')

                            ui.element('div').classes('w-px h-6').style('background: rgba(128,128,128,0.3)')

                            # Sick
                            with ui.row().classes('gap-2 items-center'):
                                ui.element('div').classes('w-4 h-4 bg-green-500 rounded-full')
                                sick_hours = sick_total - sick_used
                                sick_display, sick_tooltip = format_days_hours(sick_hours)
                                ui.label(f'Sick: {sick_display}').classes('font-medium text-green-600').tooltip(sick_tooltip)

                            ui.element('div').classes('w-px h-6').style('background: rgba(128,128,128,0.3)')

                            # Personal
                            with ui.row().classes('gap-2 items-center'):
                                ui.element('div').classes('w-4 h-4 bg-purple-500 rounded-full')
                                personal_hours = personal_total - personal_used
                                personal_display, personal_tooltip = format_days_hours(personal_hours)
                                ui.label(f'Personal: {personal_display}').classes('font-medium text-purple-600').tooltip(personal_tooltip)

                            # Chicago Paid Leave (only for Chicago employees)
                            if is_chicago_employee:
                                chicago_total = float(balance.chicago_paid_leave_total or 0) + float(balance.chicago_paid_leave_carryover or 0)
                                chicago_used = float(balance.chicago_paid_leave_used or 0)
                                chicago_pending = float(balance.chicago_paid_leave_pending or 0)
                                chicago_hours = chicago_total - chicago_used - chicago_pending
                                if chicago_total > 0:
                                    ui.element('div').classes('w-px h-6').style('background: rgba(128,128,128,0.3)')
                                    with ui.row().classes('gap-2 items-center'):
                                        ui.element('div').classes('w-4 h-4 bg-amber-500 rounded-full')
                                        chicago_display, chicago_tooltip = format_days_hours(chicago_hours)
                                        ui.label(f'Leave: {chicago_display}').classes('font-medium text-amber-600').tooltip(chicago_tooltip)
                finally:
                    db.close()

        # Initial balance render
        render_balance_summary()

        # ===== NAVIGATION ROW =====
        with ui.row().classes('w-full justify-between items-center mb-4'):
            # Month/Year navigation
            with ui.row().classes('gap-2 items-center'):
                ui.button(icon='chevron_left', on_click=lambda: navigate_month(-1)).props('flat aria-label="Previous month"').classes('no-print')

                month_label = ui.label().classes('text-xl font-semibold min-w-48 text-center')

                ui.button(icon='chevron_right', on_click=lambda: navigate_month(1)).props('flat aria-label="Next month"').classes('no-print')

                ui.button('Today', on_click=lambda: go_to_today()).props('flat').classes('no-print')

            # Export and View toggle (hidden in print)
            with ui.row().classes('gap-2 items-center no-print'):
                # Export dropdown
                with ui.dropdown_button('Export', icon='download', auto_close=True).props('flat color=primary'):
                    def export_my_calendar():
                        year = current_month['year']
                        ui.download(f'/api/calendar/export?type=my&year={year}')
                        show_info_dialog('Downloading', f'Downloading My PTO Calendar {year}...')

                    def export_team_calendar():
                        year = current_month['year']
                        dept_param = f'&department_id={selected_department["id"]}' if selected_department['id'] else ''
                        ui.download(f'/api/calendar/export?type=team&year={year}{dept_param}')
                        show_info_dialog('Downloading', f'Downloading Team Calendar {year}...')

                    def export_holidays():
                        year = current_month['year']
                        ui.download(f'/api/calendar/export?type=holidays&year={year}')
                        show_info_dialog('Downloading', f'Downloading Market Holidays {year}...')

                    ui.item('My PTO Calendar', on_click=export_my_calendar).props('clickable')
                    if user_role in ['manager', 'admin', 'superadmin']:
                        ui.item('Team Calendar', on_click=export_team_calendar).props('clickable')
                    ui.item('Market Holidays', on_click=export_holidays).props('clickable')

            # View toggle (Month / Year)
            with ui.row().classes('gap-2'):
                month_view_btn = ui.button('Month')
                year_view_btn = ui.button('Year')

                def update_period_button_styles():
                    """Update button styles based on current period view."""
                    if current_view['view'] == 'month':
                        month_view_btn.props(remove='outline')
                        month_view_btn.props('color=primary unelevated')
                        year_view_btn.props(remove='color=primary unelevated')
                        year_view_btn.props('outline')
                    else:
                        month_view_btn.props(remove='color=primary unelevated')
                        month_view_btn.props('outline')
                        year_view_btn.props(remove='outline')
                        year_view_btn.props('color=primary unelevated')

                def set_month_view():
                    current_view['view'] = 'month'
                    update_period_button_styles()
                    save_preferences()
                    render_current_view()

                def set_year_view():
                    current_view['view'] = 'year'
                    update_period_button_styles()
                    save_preferences()
                    render_current_view()

                month_view_btn.on('click', set_month_view)
                year_view_btn.on('click', set_year_view)

                # Set initial styles
                update_period_button_styles()

        # Calendar container (printable)
        calendar_container = ui.column().classes('w-full print-calendar')

        # Legend - Interactive filtering with checkboxes (hidden in print)
        with ui.card().classes('w-full p-4 mt-2 no-print shadow-md'):
            with ui.row().classes('w-full gap-4 flex-wrap items-center'):
                ui.label('Calendar Legend').classes('font-bold text-lg')
                ui.element('div').classes('flex-grow')

                # Create filter handlers for legend checkboxes
                def create_legend_filter_handler(filter_key):
                    def handler(e):
                        leave_type_filters[filter_key] = e.value
                        save_preferences()
                        render_current_view()
                    return handler

                def on_legend_holidays_change(e):
                    show_holidays['value'] = e.value
                    save_preferences()
                    render_current_view()

                def on_legend_half_days_change(e):
                    highlight_half_days['value'] = e.value
                    save_preferences()
                    render_current_view()

                with ui.row().classes('gap-4 flex-wrap'):
                    # Market Holiday - filterable
                    ui.checkbox(
                        'Market Holiday',
                        value=show_holidays['value'],
                        on_change=on_legend_holidays_change
                    ).props('dense').classes('text-sm font-medium text-orange-500')

                    # Vacation - filterable
                    ui.checkbox(
                        'Vacation',
                        value=leave_type_filters['vacation'],
                        on_change=create_legend_filter_handler('vacation')
                    ).props('dense').classes('text-sm font-medium text-blue-600')

                    # Sick - filterable
                    ui.checkbox(
                        'Sick',
                        value=leave_type_filters['sick'],
                        on_change=create_legend_filter_handler('sick')
                    ).props('dense').classes('text-sm font-medium text-green-600')

                    # Personal - filterable
                    ui.checkbox(
                        'Personal',
                        value=leave_type_filters['personal'],
                        on_change=create_legend_filter_handler('personal')
                    ).props('dense').classes('text-sm font-medium text-purple-600')

                    # Work From Home - filterable
                    ui.checkbox(
                        'WFH',
                        value=leave_type_filters['work_from_home'],
                        on_change=create_legend_filter_handler('work_from_home')
                    ).props('dense').classes('text-sm font-medium text-red-600')

                    # Chicago Leave - filterable (only for Chicago employees)
                    if is_chicago_employee:
                        ui.checkbox(
                            'Leave',
                            value=leave_type_filters['chicago_leave'],
                            on_change=create_legend_filter_handler('chicago_leave')
                        ).props('dense').classes('text-sm font-medium text-amber-600')

                    # Other - filterable
                    ui.checkbox(
                        'Other',
                        value=leave_type_filters['other'],
                        on_change=create_legend_filter_handler('other')
                    ).props('dense').classes('text-sm font-medium')

                    # Half Day - filterable (controls highlight)
                    ui.checkbox(
                        '½ Day',
                        value=highlight_half_days['value'],
                        on_change=on_legend_half_days_change
                    ).props('dense').classes('text-sm font-medium text-orange-600')

        # Back button (hidden in print)
        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6 no-print')

        # ===== MODAL FUNCTIONS =====

        def show_pto_detail_modal(request_id: int):
            """Show modal with PTO request details."""
            db = next(get_db())
            try:
                pto_request = db.query(PTORequest).filter(PTORequest.id == request_id).first()
                if not pto_request:
                    show_error_dialog('Not Found', 'The request was not found.')
                    return

                pto_user = db.query(User).filter(User.id == pto_request.user_id).first()
                employee_name = f"{pto_user.first_name} {pto_user.last_name}" if pto_user else "Unknown"

                # Get approver info if approved
                approver_name = None
                if pto_request.approved_by:
                    approver = db.query(User).filter(User.id == pto_request.approved_by).first()
                    if approver:
                        approver_name = f"{approver.first_name} {approver.last_name}"

                # Only the owner can edit their own notes - managers should not edit employee notes
                can_edit_notes = (pto_request.user_id == user_id)

                # Get color for leave type
                pto_type_lower = pto_request.pto_type.lower()
                if 'vacation' in pto_type_lower:
                    accent_color = 'blue'
                    icon_name = 'beach_access'
                elif 'sick' in pto_type_lower:
                    accent_color = 'green'
                    icon_name = 'local_hospital'
                elif 'personal' in pto_type_lower:
                    accent_color = 'purple'
                    icon_name = 'person'
                else:
                    accent_color = 'gray'
                    icon_name = 'event'

                with ui.dialog() as dialog, ui.card().classes('min-w-[420px] p-0 overflow-hidden'):
                    # Header with accent color
                    with ui.element('div').classes(f'w-full bg-{accent_color}-500 p-4'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon(icon_name).classes('text-white text-3xl')
                            with ui.column().classes('gap-0'):
                                ui.label('Time Off Request').classes('text-white text-lg font-bold')
                                ui.label(pto_request.pto_type.title()).classes('text-white/80 text-sm')

                    # Content
                    with ui.column().classes('p-5 gap-4'):
                        # Employee info
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes(f'w-10 h-10 rounded-full bg-{accent_color}-100 flex items-center justify-center'):
                                initials = f"{pto_user.first_name[0]}{pto_user.last_name[0]}" if pto_user else "?"
                                ui.label(initials).classes(f'text-{accent_color}-600 font-bold')
                            with ui.column().classes('gap-0'):
                                ui.label(employee_name).classes('font-semibold text-lg')
                                ui.label(f'Status: {pto_request.status.title()}').classes('text-sm opacity-70')

                        ui.separator()

                        # Date details in a nice grid
                        with ui.element('div').classes('grid grid-cols-2 gap-4'):
                            with ui.column().classes('gap-1'):
                                ui.label('Start Date').classes('text-xs opacity-60 uppercase tracking-wide')
                                ui.label(pto_request.start_date.strftime("%A, %B %d, %Y")).classes('font-medium')
                            with ui.column().classes('gap-1'):
                                ui.label('End Date').classes('text-xs opacity-60 uppercase tracking-wide')
                                ui.label(pto_request.end_date.strftime("%A, %B %d, %Y")).classes('font-medium')
                            with ui.column().classes('gap-1'):
                                ui.label('Duration').classes('text-xs opacity-60 uppercase tracking-wide')
                                ui.label(fmt_days(float(pto_request.total_days))).classes('font-medium text-xl')
                            with ui.column().classes('gap-1'):
                                ui.label('Leave Type').classes('text-xs opacity-60 uppercase tracking-wide')
                                with ui.element('div').classes(f'inline-flex items-center gap-1 bg-{accent_color}-100 text-{accent_color}-700 px-2 py-1 rounded'):
                                    ui.label(pto_request.pto_type.title()).classes('font-medium text-sm')

                        # Approval info section (if approved or denied)
                        if pto_request.status in ['approved', 'denied'] and (approver_name or pto_request.approved_at):
                            ui.separator()
                            with ui.column().classes('gap-2 w-full'):
                                status_label = 'Approved' if pto_request.status == 'approved' else 'Denied'
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('check_circle' if pto_request.status == 'approved' else 'cancel').classes(
                                        'text-green-600' if pto_request.status == 'approved' else 'text-red-600'
                                    )
                                    ui.label(f'{status_label} By').classes('text-xs opacity-60 uppercase tracking-wide')
                                with ui.element('div').classes('grid grid-cols-2 gap-4 ml-7'):
                                    with ui.column().classes('gap-1'):
                                        ui.label('Manager').classes('text-xs opacity-60')
                                        ui.label(approver_name or 'N/A').classes('font-medium')
                                    with ui.column().classes('gap-1'):
                                        ui.label('Date').classes('text-xs opacity-60')
                                        approval_date = pto_request.approved_at.strftime("%B %d, %Y") if pto_request.approved_at else 'N/A'
                                        ui.label(approval_date).classes('font-medium')

                        # Notes section - only show if user owns the request (managers don't see employee notes)
                        if can_edit_notes:
                            ui.separator()
                            with ui.column().classes('gap-2 w-full'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label('Notes').classes('text-xs opacity-60 uppercase tracking-wide')
                                    ui.label('(editable)').classes('text-xs text-blue-500')

                                # Editable textarea
                                notes_input = ui.textarea(
                                    value=pto_request.notes or '',
                                    placeholder='Add notes about this time off request...'
                                ).props('outlined autogrow').classes('w-full')

                                # Save notes button
                                def save_notes():
                                    save_db = next(get_db())
                                    try:
                                        req = save_db.query(PTORequest).filter(PTORequest.id == request_id).first()
                                        if req:
                                            req.notes = notes_input.value if notes_input.value.strip() else None
                                            save_db.commit()
                                            show_success_dialog('Success', 'Notes saved successfully')
                                        else:
                                            show_error_dialog('Not Found', 'The request was not found.')
                                    except Exception as e:
                                        show_error_dialog('Error', f'Error saving notes: {str(e)}')
                                    finally:
                                        save_db.close()

                                with ui.row().classes('w-full justify-end'):
                                    ui.button('Save Notes', on_click=save_notes, icon='save').props('flat color=primary').classes('text-sm')

                        # Denial reason (if denied)
                        if pto_request.status == 'denied' and pto_request.denial_reason:
                            with ui.column().classes('gap-2 w-full'):
                                ui.label('Denial Reason').classes('text-xs opacity-60 uppercase tracking-wide')
                                with ui.card().classes('w-full p-3 bg-red-50 border-l-4 border-red-500'):
                                    ui.label(pto_request.denial_reason).classes('text-sm text-red-700')

                        ui.separator()

                        # Action buttons
                        with ui.row().classes('w-full justify-between gap-2'):
                            # DELETE/CANCEL button logic based on role and status
                            is_own_request = (pto_request.user_id == user_id)
                            can_direct_delete = user_role in ['admin', 'superadmin'] or (user_role == 'manager' and is_own_request)

                            # Store request info for handlers
                            req_id = request_id
                            req_type = pto_request.pto_type
                            req_total_days = float(pto_request.total_days)
                            req_year = pto_request.start_date.year
                            req_user_id = pto_request.user_id
                            req_status = pto_request.status
                            req_employee_name = pto_request.user.full_name if pto_request.user else 'Unknown'

                            def delete_request_direct():
                                """Direct delete for admin/superadmin/manager's own requests."""
                                del_db = next(get_db())
                                try:
                                    req = del_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                                    if not req:
                                        show_error_dialog('Not Found', 'The request was not found.')
                                        return

                                    req.status = 'cancelled'

                                    # Restore balance based on previous status
                                    pto_type_lower = req_type.lower()
                                    if pto_type_lower in ['vacation', 'sick', 'personal']:
                                        balance_service = BalanceService(del_db)
                                        balance = balance_service.get_or_create_balance(req_user_id, req_year)
                                        hours_to_restore = req_total_days * 8

                                        if req_status == 'pending':
                                            # Pending uses vacation_pending
                                            if pto_type_lower == 'vacation':
                                                balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)
                                        else:
                                            # Approved uses *_used fields
                                            if pto_type_lower == 'vacation':
                                                balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                                            elif pto_type_lower == 'sick':
                                                balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                                            elif pto_type_lower == 'personal':
                                                balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

                                    del_db.commit()

                                    # Audit log the cancellation
                                    current_user = app.storage.user.get('user', {})
                                    AuditService.log_pto_cancel(
                                        db=del_db,
                                        user_id=current_user.get('id'),
                                        username=current_user.get('username'),
                                        request_id=req_id,
                                        employee_name=req_employee_name,
                                        cancelled_by_self=(req_user_id == current_user.get('id'))
                                    )

                                    show_success_dialog('Success', 'Request deleted and balance restored')
                                    dialog.close()
                                    render_current_view()
                                finally:
                                    del_db.close()

                            def cancel_pending_request():
                                """Cancel pending request for employee."""
                                cancel_db = next(get_db())
                                try:
                                    current_user = app.storage.user.get('user', {})
                                    user_id = current_user.get('id')

                                    # Use PTOService.cancel_request which handles ALL PTO types correctly
                                    from src.services.pto_service import PTOService
                                    pto_service = PTOService(cancel_db)
                                    pto_service.cancel_request(req_id, user_id)

                                    # Audit log the cancellation
                                    AuditService.log_pto_cancel(
                                        db=cancel_db,
                                        user_id=user_id,
                                        username=current_user.get('username'),
                                        request_id=req_id,
                                        employee_name=req_employee_name,
                                        cancelled_by_self=True
                                    )

                                    show_success_dialog('Success', 'Request cancelled successfully')
                                    dialog.close()
                                    render_current_view()
                                except ValueError as e:
                                    show_warning_dialog('Cannot Cancel', str(e))
                                except Exception as e:
                                    show_error_dialog('Error', f'Error cancelling request: {str(e)}')
                                finally:
                                    cancel_db.close()

                            def show_cancellation_dialog():
                                """Show dialog for employee to request cancellation of approved PTO."""
                                dialog.close()
                                with ui.dialog() as cancel_dialog, ui.card().classes('min-w-[350px] p-4'):
                                    ui.label('Request Cancellation').classes('text-xl font-bold mb-4')
                                    ui.label('Your manager will need to approve this cancellation request.').classes('text-sm opacity-70 mb-4')

                                    reason_input = ui.textarea(
                                        label='Reason (optional)',
                                        placeholder='Why do you need to cancel this time off?'
                                    ).props('outlined autogrow').classes('w-full mb-4')

                                    def submit_cancellation():
                                        req_db = next(get_db())
                                        try:
                                            req = req_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                                            if not req:
                                                show_error_dialog('Not Found', 'The request was not found.')
                                                return

                                            req.cancellation_requested = True
                                            req.cancellation_reason = reason_input.value.strip() if reason_input.value else None
                                            req.cancellation_requested_at = dt.now()

                                            req_db.commit()
                                            show_success_dialog('Request Submitted', 'Cancellation request submitted to your manager')
                                            cancel_dialog.close()
                                            render_current_view()
                                        finally:
                                            req_db.close()

                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button('Cancel', on_click=cancel_dialog.close).props('flat')
                                        ui.button('Submit Request', on_click=submit_cancellation).props('color=amber')

                                cancel_dialog.open()

                            # Show appropriate delete/cancel button
                            with ui.row().classes('gap-2'):
                                if can_direct_delete and req_status in ['pending', 'approved']:
                                    ui.button('Delete', icon='delete', on_click=delete_request_direct).props('color=negative')
                                elif is_own_request and req_status == 'pending':
                                    ui.button('Cancel Request', icon='cancel', on_click=cancel_pending_request).props('color=negative')
                                elif is_own_request and req_status == 'approved':
                                    ui.button('Request Cancellation', icon='cancel_schedule_send', on_click=show_cancellation_dialog).props('color=amber')

                            with ui.row().classes('gap-2'):
                                if user_role in ['manager', 'admin', 'superadmin'] and pto_request.user_id != user_id:
                                    ui.button(
                                        'View Full Request',
                                        on_click=lambda: (dialog.close(), ui.navigate.to(f'/manager/request/{request_id}'))
                                    ).props('color=primary')
                                ui.button('Close', on_click=dialog.close).props('flat')

                dialog.open()
            finally:
                db.close()

        def show_holiday_modal(holiday_date: date, holidays: list):
            """Show modal with market holiday details."""
            holiday_info = {}
            for h in holidays:
                if h.name not in holiday_info:
                    holiday_info[h.name] = []
                holiday_info[h.name].append(h.market)

            with ui.dialog() as dialog, ui.card().classes('min-w-80'):
                ui.label('Market Holiday').classes('text-xl font-bold mb-4')

                with ui.column().classes('gap-3'):
                    ui.label(f'Date: {holiday_date.strftime("%A, %B %d, %Y")}').classes('font-medium')

                    for h_name, markets in holiday_info.items():
                        with ui.card().classes('w-full border-l-4 border-red-500 p-3'):
                            ui.label(h_name).classes('font-semibold text-red-500')

                            major_exchanges = {'NYSE', 'CME', 'CBOE'}
                            closed_exchanges = set(markets)

                            if major_exchanges.issubset(closed_exchanges):
                                ui.label('All major exchanges closed').classes('text-sm text-red-500')
                            else:
                                ui.label(f'Exchanges closed: {", ".join(markets)}').classes('text-sm text-red-500')

                    ui.separator()
                    ui.label('Company offices may be closed on this day.').classes('text-sm opacity-70 italic')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=dialog.close).props('flat')

            dialog.open()

        def show_all_pto_modal(click_date: date, pto_entries: list):
            """Show modal listing all PTO entries for a day."""
            with ui.dialog() as dialog, ui.card().classes('min-w-96'):
                ui.label(f'PTO on {click_date.strftime("%A, %B %d, %Y")}').classes('text-xl font-bold mb-4')

                with ui.column().classes('gap-2 max-h-96 overflow-y-auto'):
                    for entry in pto_entries:
                        color_class = get_pto_color(entry['type'])

                        def create_click_handler(req_id):
                            return lambda: (dialog.close(), show_pto_detail_modal(req_id))

                        with ui.card().classes(f'w-full p-3 cursor-pointer hover:shadow-md {color_class}').on('click', create_click_handler(entry['request_id'])):
                            ui.label(entry['full_name']).classes('font-semibold')
                            ui.label(entry['type'].title()).classes('text-sm')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=dialog.close).props('flat')

            dialog.open()

        def show_quick_request_popup(click_date: date):
            """Show popup for quick PTO request on empty day (employees only)."""
            from src.services.policy_engine import PolicyEngine

            if user_role != 'employee':
                return

            # Use PolicyEngine for date validation
            policy = PolicyEngine()
            result = policy.validate_request_dates(click_date, click_date, 'vacation')

            if not result.is_valid:
                show_warning_dialog('Invalid Date', result.rejection_reason)
                return

            with ui.dialog() as dialog, ui.card().classes('min-w-80'):
                ui.label('SUBMIT PTO').classes('text-xl font-bold mb-2')
                ui.label(f'{click_date.strftime("%A, %B %d, %Y")}').classes('opacity-70 mb-4')

                # Show backdating notice if applicable
                if result.is_backdated:
                    with ui.element('div').classes('p-3 rounded-lg mb-4').style('background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b;'):
                        with ui.row().classes('items-start gap-2'):
                            ui.icon('info', size='xs', color='amber')
                            ui.label('This date is in the past. Your request will require manager approval.').classes('text-sm')

                ui.label('Would you like to submit a PTO request for this date?').classes('mb-4')

                with ui.row().classes('w-full justify-end gap-2'):
                    def go_to_request():
                        dialog.close()
                        app.storage.user['prefill_pto_date'] = click_date.isoformat()
                        ui.navigate.to('/submit-request')

                    ui.button('Submit Request', on_click=go_to_request).props('color=primary')
                    ui.button('Cancel', on_click=dialog.close).props('flat')

            dialog.open()

        # ===== HELPER FUNCTIONS =====

        def navigate_month(delta):
            """Navigate to previous or next month."""
            new_month = current_month['month'] + delta
            new_year = current_month['year']

            if new_month > 12:
                new_month = 1
                new_year += 1
            elif new_month < 1:
                new_month = 12
                new_year -= 1

            current_month['month'] = new_month
            current_month['year'] = new_year
            render_current_view()

        def go_to_today():
            """Jump to current month."""
            current_month['month'] = today.month
            current_month['year'] = today.year
            render_current_view()

        def get_pto_color(pto_type: str) -> str:
            """Get color class based on PTO type - solid background with white text."""
            pto_type_lower = pto_type.lower()
            if 'vacation' in pto_type_lower:
                return 'bg-blue-500 text-white'
            elif 'chicago' in pto_type_lower:
                return 'bg-amber-500 text-white'
            elif 'sick' in pto_type_lower:
                return 'bg-green-500 text-white'
            elif 'personal' in pto_type_lower:
                return 'bg-purple-500 text-white'
            elif 'work_from_home' in pto_type_lower or 'wfh' in pto_type_lower:
                return 'bg-red-500 text-white'
            else:
                return 'bg-gray-500 text-white'

        def get_leave_type_category(pto_type: str) -> str:
            """Categorize leave type for filtering."""
            pto_type_lower = pto_type.lower()
            if 'vacation' in pto_type_lower:
                return 'vacation'
            elif 'chicago' in pto_type_lower:
                return 'chicago_leave'
            elif 'sick' in pto_type_lower:
                return 'sick'
            elif 'personal' in pto_type_lower:
                return 'personal'
            elif 'work_from_home' in pto_type_lower or 'wfh' in pto_type_lower:
                return 'work_from_home'
            else:
                return 'other'

        def should_show_pto(pto_type: str) -> bool:
            """Check if PTO type should be shown based on filters."""
            category = get_leave_type_category(pto_type)
            return leave_type_filters.get(category, True)

        def render_current_view():
            """Render either month or year view based on current selection."""
            render_balance_summary()  # Update balance for current year
            if current_view['view'] == 'year':
                render_year_view()
            else:
                render_calendar()

        def render_year_view():
            """Render 12-month year overview with mini calendars in 2 rows (Jan-Jun / Jul-Dec)."""
            calendar_container.clear()
            year = current_month['year']

            month_label.text = str(year)

            db = next(get_db())
            try:
                # Query all holidays and PTO for the year
                year_start = date(year, 1, 1)
                year_end = date(year, 12, 31)

                holidays = db.query(MarketHoliday).filter(
                    MarketHoliday.holiday_date >= year_start,
                    MarketHoliday.holiday_date <= year_end
                ).all() if show_holidays['value'] else []

                # Build holiday lookup by date
                holidays_by_date = set()
                for h in holidays:
                    holidays_by_date.add(h.holiday_date)

                # Query PTO based on view mode
                pto_query = db.query(PTORequest).filter(
                    PTORequest.status == 'approved',
                    PTORequest.start_date <= year_end,
                    PTORequest.end_date >= year_start
                )

                if view_mode['mode'] == 'my':
                    pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role == 'employee' and view_mode['mode'] == 'team':
                    if user_department_id:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == user_department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(
                            PTORequest.user_id.in_(dept_user_ids),
                            PTORequest.is_private == False
                        )
                    else:
                        pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role in ['manager', 'admin'] and view_mode['mode'] == 'team':
                    if selected_employee['id']:
                        pto_query = pto_query.filter(PTORequest.user_id == selected_employee['id'])
                    elif user_department_id:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == user_department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))
                elif user_role == 'superadmin' and view_mode['mode'] == 'team':
                    if selected_employee['id']:
                        pto_query = pto_query.filter(PTORequest.user_id == selected_employee['id'])
                    elif selected_department['id']:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == selected_department['id'],
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))

                approved_pto = pto_query.all()

                # Build PTO lookup by date with type info
                pto_by_date = defaultdict(list)
                for pto in approved_pto:
                    if not should_show_pto(pto.pto_type):
                        continue
                    current_date = max(pto.start_date, year_start)
                    end = min(pto.end_date, year_end)
                    while current_date <= end:
                        # Skip weekends - this is a Mon-Fri system (Mon=0, Fri=4)
                        if current_date.weekday() < 5:
                            pto_by_date[current_date].append(pto.pto_type)
                        current_date += timedelta(days=1)

            finally:
                db.close()

            # Fixed 6-column grid layout (Jan-Jun / Jul-Dec) - full width
            with calendar_container:
                # 6-column CSS grid that fills full width (calendar-year-grid class for mobile responsive targeting)
                with ui.element('div').classes('calendar-year-grid').style('display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; width: 100%;'):
                    for month_num in range(1, 13):
                        is_current_month = month_num == today.month and year == today.year

                        def create_month_click_handler(m):
                            def handler():
                                current_month['month'] = m
                                current_view['view'] = 'month'
                                save_preferences()
                                render_current_view()
                            return handler

                        # Card with ring highlight for current month
                        card_style = 'width: 100%; max-width: none;'
                        if is_current_month:
                            card_style += ' box-shadow: 0 0 0 2px var(--q-primary);'

                        with ui.card().classes('p-2 cursor-pointer hover:shadow-lg').style(card_style).on('click', create_month_click_handler(month_num)):
                            # Month name header
                            ui.label(month_name[month_num]).classes('text-sm font-semibold text-center mb-1')

                            # Build HTML table for mini calendar (guaranteed alignment)
                            weeks = monthcalendar(year, month_num)

                            # Build table HTML
                            table_html = '<table style="width:100%; border-collapse:collapse; table-layout:fixed;">'
                            # Header row
                            table_html += '<tr>'
                            for day_name in ['S', 'M', 'T', 'W', 'T', 'F', 'S']:
                                table_html += f'<th style="text-align:center; font-size:0.7rem; opacity:0.5; padding:2px 0; font-weight:normal;">{day_name}</th>'
                            table_html += '</tr>'

                            # Week rows - convert Mon-start to Sun-start
                            for week in weeks:
                                sun_week = [week[6]] + week[0:6]
                                table_html += '<tr>'
                                for day_num in sun_week:
                                    if day_num == 0:
                                        table_html += '<td style="padding:2px 0;"></td>'
                                    else:
                                        current_date = date(year, month_num, day_num)
                                        is_today_date = current_date == today
                                        is_holiday = current_date in holidays_by_date
                                        pto_types = pto_by_date.get(current_date, [])

                                        # Determine background color
                                        bg_color = ''
                                        text_color = 'inherit'
                                        if is_holiday:
                                            bg_color = '#f97316'
                                            text_color = 'white'
                                        elif pto_types:
                                            first_type = pto_types[0].lower()
                                            if 'vacation' in first_type:
                                                bg_color = '#3b82f6'
                                            elif 'sick' in first_type:
                                                bg_color = '#22c55e'
                                            elif 'personal' in first_type:
                                                bg_color = '#a855f7'
                                            elif 'work_from_home' in first_type or 'wfh' in first_type:
                                                bg_color = '#ef4444'
                                            else:
                                                bg_color = '#6b7280'
                                            text_color = 'white'

                                        # Build cell style
                                        cell_style = 'text-align:center; font-size:0.7rem; padding:2px 0; border-radius:2px;'
                                        if bg_color:
                                            cell_style += f' background:{bg_color}; color:{text_color};'
                                        if is_today_date:
                                            cell_style += ' box-shadow:0 0 0 2px var(--q-primary); font-weight:bold;'

                                        table_html += f'<td style="{cell_style}">{day_num}</td>'
                                table_html += '</tr>'
                            table_html += '</table>'

                            ui.html(table_html, sanitize=False)

        def render_calendar():
            """Render the calendar grid for the current month."""
            calendar_container.clear()
            pto_requests_cache.clear()

            month = current_month['month']
            year = current_month['year']

            month_label.text = f'{month_name[month]} {year}'

            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            db = next(get_db())
            try:
                # Query market holidays
                holidays_by_date = defaultdict(list)
                if show_holidays['value']:
                    holidays = db.query(MarketHoliday).filter(
                        MarketHoliday.holiday_date >= first_day,
                        MarketHoliday.holiday_date <= last_day
                    ).all()
                    for holiday in holidays:
                        holidays_by_date[holiday.holiday_date].append(holiday)

                # Query approved PTO based on view mode
                pto_query = db.query(PTORequest).filter(
                    PTORequest.status == 'approved',
                    PTORequest.start_date <= last_day,
                    PTORequest.end_date >= first_day
                )

                # Apply view mode filtering
                if view_mode['mode'] == 'my':
                    pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role == 'employee' and view_mode['mode'] == 'team':
                    # Employee department view: see their department's non-private PTO
                    if user_department_id:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == user_department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(
                            PTORequest.user_id.in_(dept_user_ids),
                            PTORequest.is_private == False  # Exclude private PTO
                        )
                    else:
                        # No department, fallback to my calendar
                        pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role in ['manager', 'admin'] and view_mode['mode'] == 'team':
                    # Manager/Admin: restricted to their department
                    if selected_employee['id']:
                        pto_query = pto_query.filter(PTORequest.user_id == selected_employee['id'])
                    elif user_department_id:
                        # Show all employees in their department
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == user_department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))
                elif user_role == 'superadmin' and view_mode['mode'] == 'team':
                    # Superadmin: can see all departments, with optional filters
                    if selected_employee['id']:
                        pto_query = pto_query.filter(PTORequest.user_id == selected_employee['id'])
                    elif selected_department['id']:
                        # Filter by selected department
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == selected_department['id'],
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))
                    # If no filters selected, superadmin sees all

                approved_pto = pto_query.all()

                for pto in approved_pto:
                    pto_requests_cache[pto.id] = pto

                # Build PTO lookup by date with filtering
                pto_by_date = defaultdict(list)
                user_ids = set(pto.user_id for pto in approved_pto)
                users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

                for pto in approved_pto:
                    if not should_show_pto(pto.pto_type):
                        continue

                    current_date = max(pto.start_date, first_day)
                    end = min(pto.end_date, last_day)
                    while current_date <= end:
                        # Skip weekends - this is a Mon-Fri system (Mon=0, Fri=4)
                        if current_date.weekday() < 5:
                            pto_user = users.get(pto.user_id)
                            if pto_user:
                                initials = f"{pto_user.first_name[0]}{pto_user.last_name[0]}"
                                pto_by_date[current_date].append({
                                    'request_id': pto.id,
                                    'user': pto_user,
                                    'initials': initials,
                                    'type': pto.pto_type,
                                    'full_name': f"{pto_user.first_name} {pto_user.last_name}",
                                    'total_days': float(pto.total_days or 1),
                                    'is_half_day': float(pto.total_days or 1) < 1
                                })
                        current_date += timedelta(days=1)

            finally:
                db.close()

            # Generate calendar grid
            weeks = monthcalendar(year, month)

            # Determine which days to show
            # Python's monthcalendar returns weeks starting Monday (0=Mon, 6=Sun)
            if show_weekends['value']:
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                day_indices = list(range(7))
            else:
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
                day_indices = [0, 1, 2, 3, 4]  # Monday=0 through Friday=4

            with calendar_container:
                with ui.element('div').classes('w-full rounded-lg overflow-hidden').style('border: 1px solid rgba(128,128,128,0.3)'):
                    # Header row
                    with ui.row().classes('w-full').style('background: rgba(128,128,128,0.1)'):
                        for day_name in day_names:
                            with ui.element('div').classes('flex-1 p-2 text-center font-semibold last:border-r-0').style('border-right: 1px solid rgba(128,128,128,0.3)'):
                                ui.label(day_name).classes('text-sm')

                    # Calendar weeks
                    for week in weeks:
                        # Filter days if hiding weekends
                        if show_weekends['value']:
                            display_days = week
                        else:
                            # week is [Mon, Tue, Wed, Thu, Fri, Sat, Sun] - we want Mon-Fri (indices 0-4)
                            display_days = week[0:5]

                        # Skip weeks that are all zeros after filtering
                        if all(d == 0 for d in display_days):
                            continue

                        with ui.row().classes('w-full').style('border-top: 1px solid rgba(128,128,128,0.3)'):
                            for idx, day_num in enumerate(display_days):
                                cell_classes = 'flex-1 min-h-24 p-1 last:border-r-0 relative'
                                cell_style = 'border-right: 1px solid rgba(128,128,128,0.3);'

                                if day_num == 0:
                                    cell_style += ' background: rgba(128,128,128,0.05);'
                                    with ui.element('div').classes(cell_classes).style(cell_style):
                                        pass
                                else:
                                    current_date = date(year, month, day_num)
                                    is_today = current_date == today
                                    is_weekend = current_date.weekday() >= 5
                                    has_holiday = current_date in holidays_by_date and show_holidays['value']
                                    has_pto = current_date in pto_by_date

                                    if has_holiday:
                                        cell_style += ' background: rgba(239,68,68,0.1);'  # red-500 with opacity
                                    elif is_weekend:
                                        cell_style += ' background: rgba(128,128,128,0.05);'

                                    if user_role == 'employee' and not has_holiday and not has_pto:
                                        cell_classes += ' cursor-pointer hover:bg-blue-500/10'

                                    def create_empty_day_handler(d):
                                        return lambda: show_quick_request_popup(d)

                                    cell_element = ui.element('div').classes(cell_classes).style(cell_style)

                                    if user_role == 'employee' and not has_holiday and not has_pto:
                                        cell_element.on('click', create_empty_day_handler(current_date))

                                    with cell_element:
                                        day_classes = 'text-sm font-medium'
                                        is_clickable_day = user_role == 'employee' and current_date >= today and not has_holiday

                                        def create_day_click_handler(d):
                                            def handler():
                                                app.storage.user['prefill_pto_date'] = d.isoformat()
                                                ui.navigate.to('/submit-request')
                                            return handler

                                        if is_today:
                                            if is_clickable_day:
                                                day_el = ui.element('div').classes('w-6 h-6 bg-primary rounded-full flex items-center justify-center cursor-pointer hover:ring-2 hover:ring-primary hover:ring-offset-1').tooltip('Click to request time off')
                                                day_el.on('click', create_day_click_handler(current_date))
                                                with day_el:
                                                    ui.label(str(day_num)).classes('text-white text-sm font-bold')
                                            else:
                                                with ui.element('div').classes('w-6 h-6 bg-primary rounded-full flex items-center justify-center'):
                                                    ui.label(str(day_num)).classes('text-white text-sm font-bold')
                                        else:
                                            if is_weekend:
                                                day_classes += ' opacity-50'
                                            if is_clickable_day:
                                                day_el = ui.element('div').classes('inline-block cursor-pointer hover:bg-blue-100 hover:rounded-full px-1').tooltip('Click to request time off')
                                                day_el.on('click', create_day_click_handler(current_date))
                                                with day_el:
                                                    ui.label(str(day_num)).classes(day_classes)
                                            else:
                                                ui.label(str(day_num)).classes(day_classes)

                                        # Show holidays - ONE entry per date (consolidate different market names)
                                        if has_holiday:
                                            holiday_list = holidays_by_date[current_date]
                                            # Get unique holiday names and use the shortest one for display
                                            unique_names = set(h.name for h in holiday_list)
                                            display_name = min(unique_names, key=len)  # Use shortest name
                                            all_markets = list(set(h.market for h in holiday_list))

                                            def create_holiday_handler(d, h_list):
                                                return lambda: show_holiday_modal(d, h_list)

                                            tooltip_text = f"{display_name} ({', '.join(all_markets)}) - Click for details"
                                            holiday_el = ui.element('div').classes(
                                                'text-xs bg-orange-500 text-white px-1 rounded mt-1 truncate cursor-pointer hover:bg-orange-600'
                                            ).tooltip(tooltip_text)
                                            holiday_el.on('click', create_holiday_handler(current_date, holiday_list))
                                            with holiday_el:
                                                ui.label(display_name[:15] + ('...' if len(display_name) > 15 else '')).classes('text-xs text-white')

                                        # Show PTO entries
                                        if has_pto:
                                            pto_entries = pto_by_date[current_date]

                                            def create_pto_handler(req_id):
                                                return lambda: show_pto_detail_modal(req_id)

                                            for pto_entry in pto_entries[:3]:
                                                color_class = get_pto_color(pto_entry['type'])
                                                # More descriptive label: First name + leave type + half-day indicator
                                                first_name = pto_entry['full_name'].split()[0]
                                                leave_label = pto_entry['type'].title()
                                                is_half = pto_entry.get('is_half_day', False)
                                                half_day_indicator = " ½" if is_half else ""
                                                display_text = f"{first_name} - {leave_label}{half_day_indicator}"
                                                days_text = fmt_days(pto_entry.get('total_days', 1))
                                                tooltip_text = f"{pto_entry['full_name']} - {pto_entry['type'].title()} ({days_text}) - Click for details"

                                                # Highlight half-day events if toggle is enabled
                                                highlight_style = 'min-height: 20px; font-size: 11px;'
                                                if is_half and highlight_half_days['value']:
                                                    highlight_style += ' border: 2px dotted white; box-shadow: 0 0 0 1px rgba(0,0,0,0.3);'

                                                # Use a button styled as a div for reliable click handling
                                                pto_btn = ui.button(display_text, on_click=create_pto_handler(pto_entry['request_id'])).props('flat dense no-caps align=left').classes(
                                                    f'text-xs {color_class} px-1 py-0 rounded mt-1 w-full text-left'
                                                ).tooltip(tooltip_text).style(highlight_style)

                                            if len(pto_entries) > 3:
                                                extra_count = len(pto_entries) - 3

                                                def create_more_handler(d, entries):
                                                    return lambda e: (e.stop_propagation(), show_all_pto_modal(d, entries))

                                                more_el = ui.element('div').classes(
                                                    'text-xs opacity-60 mt-1 cursor-pointer hover:text-blue-600 hover:underline'
                                                )
                                                more_el.on('click', create_more_handler(current_date, pto_entries))
                                                with more_el:
                                                    ui.label(f'+{extra_count} more')

        # Initial render
        render_current_view()

        # ============ REAL-TIME UPDATES ============
        # Set up automatic refresh when PTO requests change (30 second interval)
        setup_calendar_updates(None, user_id, interval=30.0)
