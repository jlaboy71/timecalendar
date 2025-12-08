from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.services.department_service import DepartmentService
from src.models.carryover_request import CarryoverRequest
from src.database import get_db
from datetime import datetime, date
import pytz
from nicegui_app.logo import LOGO_DATA_URL
from nicegui_app.components.header import get_time_based_greeting
from nicegui_app.components.theme import apply_dark_mode, skeleton_card


def format_days(hours: float) -> str:
    """Convert hours to days, showing clean whole numbers when possible."""
    days = round(hours / 8, 1)
    # If it's essentially a whole number, show as integer
    if abs(days - round(days)) < 0.01:
        return str(int(round(days)))
    return f"{days:.1f}"


def format_hours_and_days(hours: float) -> str:
    """Format hours with days equivalent."""
    hours_rounded = round(hours)
    days = round(hours / 8, 1)
    if abs(days - round(days)) < 0.01:
        return f"{hours_rounded} hrs ({int(round(days))} days)"
    return f"{hours_rounded} hrs ({days:.1f} days)"


def dashboard_page():
    """Employee dashboard page with PTO balances, quick actions, and recent requests."""

    apply_dark_mode()

    # Check if user is logged in
    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return

    # Get user info
    user_data = app.storage.general.get('user')
    user_first_name = user_data.get('first_name', 'User')
    user_last_name = user_data.get('last_name', '')
    user_id = user_data.get('id')
    user_role = user_data.get('role')

    db = None
    try:
        # Get database session
        db = next(get_db())
        balance_service = BalanceService(db)
        pto_service = PTOService(db)
        accrual_service = AccrualService(db)
        user_service = UserService(db)

        # Get current user object for policy lookups
        current_user = user_service.get_user_by_id(user_id)

        # Get user's current PTO balances for current year
        current_year = date.today().year
        balance = balance_service.get_or_create_balance(user_id, current_year)

        # Get user's requests
        all_requests = PTOService.get_user_requests(db, user_id)
        pending_requests = [r for r in all_requests if r.status == 'pending']
        # Only show approved requests in Recent Requests section (denied/cancelled visible in View All)
        approved_requests = [r for r in all_requests if r.status == 'approved']
        recent_requests = approved_requests[:5]

        # Get team pending requests for managers/admins
        team_pending_requests = []
        if user_role in ['manager', 'admin', 'superadmin']:
            team_pending_requests = PTOService.get_pending_requests_with_employee_info(db)

        # ============ MAIN LAYOUT ============
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):

            # Header with logo, greeting and logout
            with ui.row().classes('w-full justify-between items-center mb-6'):
                with ui.column().classes('gap-2'):
                    ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                    greeting = get_time_based_greeting()
                    ui.label(f'{greeting}, {user_first_name} {user_last_name}').classes('text-xl font-bold uppercase').style('color: #5a6a72;')

                with ui.row().classes('items-center gap-2'):
                    # Help button
                    ui.button(icon='help_outline', on_click=lambda: ui.navigate.to('/help')).props('flat round aria-label="Help Center"').tooltip('Help Center')

                    # Dark mode toggle
                    dark_mode = ui.dark_mode()

                    def toggle_dark_mode():
                        # Get current state from storage, default to False (light mode)
                        current = app.storage.general.get('dark_mode', False)
                        new_state = not current
                        app.storage.general['dark_mode'] = new_state
                        if new_state:
                            dark_mode.enable()
                        else:
                            dark_mode.disable()
                        dark_toggle.props(f'icon={"light_mode" if new_state else "dark_mode"}')

                    # Initialize based on stored preference
                    is_dark = app.storage.general.get('dark_mode', False)
                    if is_dark:
                        dark_mode.enable()

                    dark_toggle = ui.button(
                        icon='light_mode' if is_dark else 'dark_mode',
                        on_click=toggle_dark_mode
                    ).props('flat round')

                    ui.button('Logout', icon='logout', on_click=lambda: logout()).props('flat')

            # ============ PTO BALANCES CARD (not for admin/superadmin - they don't take PTO) ============
            if user_role not in ['admin', 'superadmin']:
              with ui.card().classes('w-full mb-4'):
                ui.label(f'PTO Balances ({current_year})').classes('text-lg font-semibold mb-4')

                if balance:
                    with ui.row().classes('w-full gap-4 justify-center flex-wrap'):
                        # Vacation
                        vacation_available = float(balance.vacation_available)
                        vacation_total = float(balance.vacation_total) + float(balance.vacation_carryover)
                        vacation_pending = float(balance.vacation_pending)
                        vacation_used = float(balance.vacation_used)
                        vacation_pct = (vacation_available / vacation_total * 100) if vacation_total > 0 else 0

                        with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-blue-500'):
                            with ui.row().classes('justify-between items-start'):
                                ui.label('Vacation').classes('font-semibold text-blue-600')
                                # Color indicator
                                if vacation_pct > 50:
                                    ui.badge('', color='green').classes('w-3 h-3 rounded-full')
                                elif vacation_pct > 25:
                                    ui.badge('', color='orange').classes('w-3 h-3 rounded-full')
                                else:
                                    ui.badge('', color='red').classes('w-3 h-3 rounded-full')

                            ui.label(f'{format_days(vacation_available)}').classes('text-3xl font-bold text-blue-600 my-2')
                            ui.label('days available').classes('text-sm opacity-70')

                            with ui.row().classes('mt-2 gap-3 text-xs opacity-60'):
                                ui.label(f'{format_days(vacation_total)} total')
                                if vacation_used > 0:
                                    ui.label(f'{format_days(vacation_used)} used')
                                if vacation_pending > 0:
                                    ui.label(f'{format_days(vacation_pending)} pending').classes('text-amber-500')

                        # Sick
                        sick_available = float(balance.sick_available)
                        sick_total = float(balance.sick_total) + float(balance.sick_carryover)
                        sick_used = float(balance.sick_used)
                        sick_pct = (sick_available / sick_total * 100) if sick_total > 0 else 0

                        with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-green-500'):
                            with ui.row().classes('justify-between items-start'):
                                ui.label('Sick').classes('font-semibold text-green-600')
                                if sick_pct > 50:
                                    ui.badge('', color='green').classes('w-3 h-3 rounded-full')
                                elif sick_pct > 25:
                                    ui.badge('', color='orange').classes('w-3 h-3 rounded-full')
                                else:
                                    ui.badge('', color='red').classes('w-3 h-3 rounded-full')

                            ui.label(f'{format_days(sick_available)}').classes('text-3xl font-bold text-green-600 my-2')
                            ui.label('days available').classes('text-sm opacity-70')

                            with ui.row().classes('mt-2 gap-3 text-xs opacity-60'):
                                ui.label(f'{format_days(sick_total)} total')
                                if sick_used > 0:
                                    ui.label(f'{format_days(sick_used)} used')

                        # Personal
                        personal_available = float(balance.personal_available)
                        personal_total = float(balance.personal_total) + float(balance.personal_carryover)
                        personal_used = float(balance.personal_used)
                        personal_pct = (personal_available / personal_total * 100) if personal_total > 0 else 0

                        with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-purple-500'):
                            with ui.row().classes('justify-between items-start'):
                                ui.label('Personal').classes('font-semibold text-purple-600')
                                if personal_pct > 50:
                                    ui.badge('', color='green').classes('w-3 h-3 rounded-full')
                                elif personal_pct > 25:
                                    ui.badge('', color='orange').classes('w-3 h-3 rounded-full')
                                else:
                                    ui.badge('', color='red').classes('w-3 h-3 rounded-full')

                            ui.label(f'{format_days(personal_available)}').classes('text-3xl font-bold text-purple-600 my-2')
                            ui.label('days available').classes('text-sm opacity-70')

                            with ui.row().classes('mt-2 gap-3 text-xs opacity-60'):
                                ui.label(f'{format_days(personal_total)} total')
                                if personal_used > 0:
                                    ui.label(f'{format_days(personal_used)} used')
                else:
                    ui.label(f'No balance data for {current_year}').classes('opacity-70')

            # ============ PENDING REQUESTS (if any) - employees only ============
            if pending_requests and user_role not in ['manager', 'admin', 'superadmin']:
                with ui.card().classes('w-full mb-4 border-l-4 border-amber-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('pending', color='amber').classes('text-xl')
                            ui.label('Pending Requests').classes('text-lg font-semibold')
                        ui.label(f'{len(pending_requests)} awaiting approval').classes('text-sm text-amber-500')

                    for req in pending_requests:
                        with ui.card().classes('w-full p-3 mb-2'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('gap-2 items-center'):
                                        ui.label(req.pto_type.title()).classes('font-medium')
                                        ui.badge('Pending', color='amber').props('outline')
                                    if req.start_date == req.end_date:
                                        ui.label(req.start_date.strftime('%b %d, %Y')).classes('text-sm opacity-70')
                                    else:
                                        ui.label(f"{req.start_date.strftime('%b %d')} - {req.end_date.strftime('%b %d, %Y')}").classes('text-sm opacity-70')

                                with ui.row().classes('items-center gap-2'):
                                    days_display = float(req.total_days)
                                    ui.label(f'{format_days(days_display * 8)} days').classes('font-medium')

                                    def create_cancel_handler(request_id):
                                        def show_cancel_dialog():
                                            with ui.dialog() as cancel_dialog, ui.card().classes('p-4'):
                                                ui.label('Cancel PTO Request?').classes('text-lg font-semibold mb-2')
                                                ui.label('This will cancel your pending request and restore your balance.').classes('text-sm opacity-70 mb-4')
                                                with ui.row().classes('w-full justify-end gap-2'):
                                                    ui.button('Keep Request', on_click=cancel_dialog.close).props('flat')
                                                    def confirm_cancel():
                                                        cancel_dialog.close()
                                                        cancel_request(request_id)
                                                    ui.button('Cancel Request', on_click=confirm_cancel).props('color=red')
                                            cancel_dialog.open()
                                        return show_cancel_dialog

                                    ui.button('Cancel', icon='close', on_click=create_cancel_handler(req.id)).props('flat dense color=red size=sm')

            # ============ TEAM PENDING REQUESTS (Managers only - admins don't approve requests) ============
            if user_role == 'manager' and team_pending_requests:
                # Pre-compute conflicts for each pending request
                pto_service = PTOService(db)
                request_conflicts = {}
                for req in team_pending_requests:
                    conflicts = pto_service.get_department_conflicts(
                        req['user_id'],
                        req['start_date'],
                        req['end_date'],
                        exclude_request_id=req['request_id']
                    )
                    if conflicts:
                        request_conflicts[req['request_id']] = len(conflicts)

                with ui.card().classes('w-full mb-4 border-l-4 border-indigo-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('supervisor_account', color='indigo').classes('text-xl')
                            ui.label('Team Requests Awaiting Approval').classes('text-lg font-semibold')
                        with ui.row().classes('items-center gap-2'):
                            if request_conflicts:
                                ui.badge(f'{len(request_conflicts)} conflicts', color='amber').props('outline').tooltip('Some requests have scheduling conflicts')
                            ui.badge(f'{len(team_pending_requests)} pending', color='indigo').props('outline')

                    # Type colors for border
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}

                    for req in team_pending_requests[:5]:  # Show first 5
                        pto_type_lower = req['pto_type'].lower()
                        border_color = type_colors.get(pto_type_lower, 'gray')
                        has_conflict = req['request_id'] in request_conflicts

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-3 items-center'):
                                    ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                    with ui.column().classes('gap-0'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(req['employee_name']).classes('font-medium')
                                            # Show conflict warning icon
                                            if has_conflict:
                                                conflict_count = request_conflicts[req['request_id']]
                                                ui.icon('warning', color='amber').classes('text-lg').tooltip(
                                                    f'{conflict_count} other team member(s) off on same date(s)'
                                                )
                                        with ui.row().classes('gap-2 items-center'):
                                            ui.label(req['pto_type'].title()).classes('text-sm opacity-70')
                                            ui.label('•').classes('text-xs opacity-50')
                                            if req['start_date'] == req['end_date']:
                                                ui.label(req['start_date'].strftime('%b %d, %Y')).classes('text-sm opacity-70')
                                            else:
                                                ui.label(f"{req['start_date'].strftime('%b %d')} - {req['end_date'].strftime('%b %d, %Y')}").classes('text-sm opacity-70')

                                with ui.row().classes('items-center gap-3'):
                                    days = float(req['total_days'])
                                    ui.label(f'{format_days(days * 8)} days').classes('font-medium')

                                    def create_review_handler(request_id):
                                        def review():
                                            ui.navigate.to(f'/manager/request/{request_id}')
                                        return review

                                    ui.button('Review', icon='visibility', on_click=create_review_handler(req['request_id'])).props('flat dense color=indigo size=sm')

                    if len(team_pending_requests) > 5:
                        with ui.row().classes('w-full justify-center mt-2'):
                            ui.label(f'+ {len(team_pending_requests) - 5} more pending requests').classes('text-sm opacity-60')

            # ============ MY TEAM (Managers only) ============
            if user_role == 'manager':
                # Get team members from manager's department
                manager_user = user_service.get_user_by_id(user_id)
                if manager_user and manager_user.department_id:
                    team_members = user_service.get_users_by_department(manager_user.department_id)
                    # Exclude the manager themselves and inactive users
                    team_members = [m for m in team_members if m.id != user_id and m.is_active]

                    if team_members:
                        with ui.card().classes('w-full mb-4'):
                            with ui.row().classes('w-full justify-between items-center mb-3'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('groups', color='teal').classes('text-xl')
                                    ui.label('My Team').classes('text-lg font-semibold')
                                ui.badge(f'{len(team_members)} members', color='teal').props('outline')

                            # Team member list with click to view PTO history
                            for member in team_members[:8]:  # Show first 8
                                def create_member_click_handler(member_id, member_name):
                                    def handler():
                                        show_employee_pto_history(member_id, member_name, current_year)
                                    return handler

                                with ui.card().classes('w-full p-3 mb-2 cursor-pointer hover:shadow-md').on('click', create_member_click_handler(member.id, member.full_name)):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        with ui.row().classes('gap-3 items-center'):
                                            ui.icon('person').classes('text-gray-400')
                                            with ui.column().classes('gap-0'):
                                                ui.label(member.full_name).classes('font-medium')
                                                ui.label(member.email).classes('text-xs opacity-60')

                                        # Show quick balance info
                                        member_balance = balance_service.get_or_create_balance(member.id, current_year)
                                        if member_balance:
                                            vacation_avail = float(member_balance.vacation_available)
                                            with ui.row().classes('gap-2 items-center'):
                                                ui.label(f'{format_days(vacation_avail)} vacation days').classes('text-xs opacity-70')
                                                ui.icon('chevron_right').classes('text-gray-400')

                            if len(team_members) > 8:
                                with ui.row().classes('w-full justify-center mt-2'):
                                    ui.label(f'+ {len(team_members) - 8} more team members').classes('text-sm opacity-60')

            # ============ QUICK ACTIONS (employees and managers only) ============
            if user_role not in ['admin', 'superadmin']:
                with ui.card().classes('w-full mb-4 p-4'):
                    # Row 1: My Time Off Actions
                    with ui.column().classes('w-full gap-3'):
                        ui.label('My Time Off').classes('text-xs font-semibold uppercase opacity-60')
                        with ui.row().classes('w-full gap-3 flex-wrap'):
                            # Managers auto-approve, so show "Submit" instead of "Request"
                            time_off_label = 'Submit Time Off' if user_role == 'manager' else 'Request Time Off'
                            ui.button(time_off_label, icon='add_circle', on_click=lambda: ui.navigate.to('/submit-request')).props('outline color=primary').classes('flex-1 min-w-fit')
                            # For managers: "My Time Off History" shows their submitted time with color-coded view
                            # For employees: "My Requests" shows pending/approved requests
                            history_label = 'My Time Off History' if user_role == 'manager' else 'My Requests'
                            ui.button(history_label, icon='history', on_click=lambda: ui.navigate.to('/requests')).props('outline color=primary').classes('flex-1 min-w-fit')
                            # Carryover Request only for employees (managers auto-approve, use Manager Tools > Carryover Approvals)
                            if user_role != 'manager':
                                ui.button('Carryover Request', icon='move_down', on_click=lambda: ui.navigate.to('/carryover')).props('outline color=primary').classes('flex-1 min-w-fit')

                    ui.separator().classes('my-2')

                    # Row 2: Resources
                    with ui.column().classes('w-full gap-3'):
                        ui.label('Resources').classes('text-xs font-semibold uppercase opacity-60')
                        with ui.row().classes('w-full gap-3 flex-wrap'):
                            ui.button('Company Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline color=secondary').classes('flex-1 min-w-fit')
                            ui.button('Employee Handbook', icon='menu_book', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=secondary').classes('flex-1 min-w-fit')
                            ui.button('My Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=secondary').classes('flex-1 min-w-fit')

                    # Row 3: Manager Tools (managers only)
                    if user_role == 'manager':
                        ui.separator().classes('my-2')
                        with ui.column().classes('w-full gap-3'):
                            ui.label('Manager Tools').classes('text-xs font-semibold uppercase opacity-60')
                            with ui.row().classes('w-full gap-3 flex-wrap'):
                                def go_to_team_calendar():
                                    # Pre-set calendar to team view before navigating
                                    app.storage.general['calendar_prefs'] = {
                                        **app.storage.general.get('calendar_prefs', {}),
                                        'view_mode': 'team'
                                    }
                                    ui.navigate.to('/calendar')

                                ui.button('Team Calendar', icon='groups', on_click=go_to_team_calendar).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Carryover Approvals', icon='approval', on_click=lambda: ui.navigate.to('/manager/carryover')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Handbook AI', icon='smart_toy', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Analytics', icon='insights', on_click=lambda: ui.navigate.to('/analytics')).props('outline color=indigo').classes('flex-1 min-w-fit')

            # ============ ADMIN DASHBOARD (admin/superadmin only) ============
            if user_role in ['admin', 'superadmin']:
                # Get pending requests for admins (all departments)
                admin_pending_requests = PTOService.get_pending_requests_with_employee_info(db)
                pending_count = len(admin_pending_requests)

                # Admin Overview Stats
                with ui.card().classes('w-full mb-4 p-4 border-l-4 border-red-500'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('admin_panel_settings', color='red').classes('text-2xl')
                            ui.label('Administration Dashboard').classes('text-lg font-semibold')
                        ui.badge('Admin', color='red').props('outline')

                    # Get stats
                    all_users = user_service.get_all_users()
                    all_departments = DepartmentService.get_all_departments(db)
                    active_users = [u for u in all_users if u.is_active]

                    with ui.row().classes('w-full gap-4 justify-center flex-wrap'):
                        # Total Employees
                        with ui.card().classes('flex-1 min-w-32 p-3 text-center'):
                            ui.label(str(len(active_users))).classes('text-3xl font-bold text-blue-600')
                            ui.label('Active Employees').classes('text-xs opacity-60')

                        # Total Departments
                        with ui.card().classes('flex-1 min-w-32 p-3 text-center'):
                            ui.label(str(len(all_departments))).classes('text-3xl font-bold text-indigo-600')
                            ui.label('Departments').classes('text-xs opacity-60')

                        # Pending Requests (clickable)
                        with ui.card().classes('flex-1 min-w-32 p-3 text-center cursor-pointer hover:bg-amber-50').on('click', lambda: ui.navigate.to('/admin/approvals') if pending_count > 0 else None):
                            ui.label(str(pending_count)).classes('text-3xl font-bold text-amber-600')
                            ui.label('Pending Requests').classes('text-xs opacity-60')

                # ============ PENDING APPROVALS (admins see all pending requests) ============
                if admin_pending_requests:
                    # Pre-compute conflicts for each pending request
                    pto_service = PTOService(db)
                    request_conflicts = {}
                    for req in admin_pending_requests:
                        conflicts = pto_service.get_department_conflicts(
                            req['user_id'],
                            req['start_date'],
                            req['end_date'],
                            exclude_request_id=req['request_id']
                        )
                        if conflicts:
                            request_conflicts[req['request_id']] = len(conflicts)

                    with ui.card().classes('w-full mb-4 border-l-4 border-amber-500'):
                        with ui.row().classes('w-full justify-between items-center mb-3'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('pending_actions', color='amber').classes('text-xl')
                                ui.label('Pending PTO Approvals').classes('text-lg font-semibold')
                            with ui.row().classes('items-center gap-2'):
                                if request_conflicts:
                                    ui.badge(f'{len(request_conflicts)} conflicts', color='amber').props('outline').tooltip('Some requests have scheduling conflicts')
                                ui.badge(f'{pending_count} pending', color='amber').props('outline')

                        # Type colors for border
                        type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
                        type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}

                        for req in admin_pending_requests[:5]:  # Show first 5
                            pto_type_lower = req['pto_type'].lower()
                            border_color = type_colors.get(pto_type_lower, 'gray')
                            has_conflict = req['request_id'] in request_conflicts

                            with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('gap-3 items-center'):
                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                        with ui.column().classes('gap-0'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(req['employee_name']).classes('font-medium')
                                                # Show department name for admins
                                                if req.get('department_name'):
                                                    ui.badge(req['department_name'], color='grey').props('outline dense')
                                                # Show conflict warning icon
                                                if has_conflict:
                                                    conflict_count = request_conflicts[req['request_id']]
                                                    ui.icon('warning', color='amber').classes('text-lg').tooltip(
                                                        f'{conflict_count} other team member(s) off on same date(s)'
                                                    )
                                            with ui.row().classes('gap-2 items-center'):
                                                ui.label(req['pto_type'].title()).classes('text-sm opacity-70')
                                                ui.label('•').classes('text-xs opacity-50')
                                                if req['start_date'] == req['end_date']:
                                                    ui.label(req['start_date'].strftime('%b %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req['start_date'].strftime('%b %d')} - {req['end_date'].strftime('%b %d, %Y')}").classes('text-sm opacity-70')

                                    with ui.row().classes('items-center gap-3'):
                                        days = float(req['total_days'])
                                        ui.label(f'{format_days(days * 8)} days').classes('font-medium')

                                        def create_review_handler(request_id):
                                            def review():
                                                ui.navigate.to(f'/manager/request/{request_id}')
                                            return review

                                        ui.button('Review', icon='visibility', on_click=create_review_handler(req['request_id'])).props('flat dense color=amber size=sm')

                        if len(admin_pending_requests) > 5:
                            with ui.row().classes('w-full justify-center mt-2'):
                                ui.button(f'View All {pending_count} Requests', icon='visibility',
                                         on_click=lambda: ui.navigate.to('/admin/approvals')).props('flat dense')

                # ============ PENDING CARRYOVER REQUESTS (admins see all) ============
                pending_carryovers = db.query(CarryoverRequest).filter(
                    CarryoverRequest.status == 'pending',
                    CarryoverRequest.from_year == current_year
                ).count()

                if pending_carryovers > 0:
                    with ui.card().classes('w-full mb-4 border-l-4 border-purple-500 cursor-pointer hover:shadow-lg').on('click', lambda: ui.navigate.to('/manager/carryover')):
                        with ui.row().classes('w-full justify-between items-center p-2'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('move_down', color='purple').classes('text-2xl')
                                with ui.column().classes('gap-0'):
                                    ui.label('Pending Carryover Requests').classes('font-semibold')
                                    ui.label(f'{pending_carryovers} employee(s) requesting to carry over unused PTO').classes('text-sm opacity-70')
                            ui.badge(str(pending_carryovers), color='purple')

                # Admin Quick Actions
                with ui.card().classes('w-full mb-4 p-4'):
                    ui.label('Management').classes('text-xs font-semibold uppercase opacity-60 mb-3')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        ui.button('Manage Departments', icon='business',
                                  on_click=lambda: ui.navigate.to('/admin/departments')).props('outline color=indigo').classes('flex-1 min-w-fit')
                        ui.button('Manage Employees', icon='people',
                                  on_click=lambda: ui.navigate.to('/admin/employees')).props('outline color=indigo').classes('flex-1 min-w-fit')
                        ui.button('Add Employee', icon='person_add',
                                  on_click=lambda: ui.navigate.to('/admin/employees/add')).props('outline color=primary').classes('flex-1 min-w-fit')

                    ui.separator().classes('my-3')

                    ui.label('Approvals').classes('text-xs font-semibold uppercase opacity-60 mb-3')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        ui.button('PTO Approvals', icon='pending_actions',
                                  on_click=lambda: ui.navigate.to('/admin/approvals')).props('outline color=amber').classes('flex-1 min-w-fit')
                        ui.button('Carryover Approvals', icon='move_down',
                                  on_click=lambda: ui.navigate.to('/manager/carryover')).props('outline color=purple').classes('flex-1 min-w-fit')

                    ui.separator().classes('my-3')

                    ui.label('Resources').classes('text-xs font-semibold uppercase opacity-60 mb-3')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        ui.button('Company Calendar', icon='calendar_month',
                                  on_click=lambda: ui.navigate.to('/calendar')).props('outline color=secondary').classes('flex-1 min-w-fit')
                        ui.button('Manage Handbook', icon='menu_book',
                                  on_click=lambda: ui.navigate.to('/admin/handbook')).props('outline color=secondary').classes('flex-1 min-w-fit')
                        ui.button('Reports', icon='assessment',
                                  on_click=lambda: ui.navigate.to('/reports')).props('outline color=secondary').classes('flex-1 min-w-fit')
                        ui.button('Analytics', icon='insights',
                                  on_click=lambda: ui.navigate.to('/analytics')).props('outline color=secondary').classes('flex-1 min-w-fit')

                    ui.separator().classes('my-3')

                    ui.label('System').classes('text-xs font-semibold uppercase opacity-60 mb-3')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        ui.button('Year-End Processing', icon='event_repeat',
                                  on_click=lambda: ui.navigate.to('/admin/year-end')).props('outline color=teal').classes('flex-1 min-w-fit')
                        if user_role == 'superadmin':
                            ui.button('System Admin', icon='settings_applications',
                                      on_click=lambda: ui.navigate.to('/admin/system')).props('outline color=warning').classes('flex-1 min-w-fit')

            # ============ RECENT APPROVED REQUESTS (not for admin/superadmin) ============
            if user_role not in ['admin', 'superadmin']:
              with ui.card().classes('w-full mb-4'):
                ui.label('Recent Approved Time Off').classes('text-lg font-semibold mb-3')

                if recent_requests:
                    for req in recent_requests:
                        with ui.row().classes('w-full p-3 border-b last:border-0 justify-between items-center'):
                            with ui.row().classes('gap-4 items-center'):
                                # Type icon
                                type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}
                                ui.icon(type_icons.get(req.pto_type.lower(), 'event')).classes('opacity-50')

                                with ui.column().classes('gap-0'):
                                    ui.label(req.pto_type.title()).classes('font-medium')
                                    if req.start_date == req.end_date:
                                        ui.label(req.start_date.strftime('%b %d, %Y')).classes('text-xs opacity-60')
                                    else:
                                        ui.label(f"{req.start_date.strftime('%b %d')} - {req.end_date.strftime('%b %d, %Y')}").classes('text-xs opacity-60')

                            with ui.row().classes('gap-3 items-center'):
                                days_display = float(req.total_days)
                                ui.label(f'{format_days(days_display * 8)} days').classes('text-sm')

                                # Status badge
                                status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}
                                ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey'))
                else:
                    with ui.row().classes('w-full justify-center py-6'):
                        ui.label('No approved time off yet').classes('opacity-60')

            # ============ LEAVE POLICY (Collapsible) - not for admin/superadmin ============
            if user_role not in ['admin', 'superadmin']:
              with ui.expansion('My Leave Policy', icon='policy').classes('w-full'):
                if current_user:
                    # Work Location
                    with ui.row().classes('w-full mb-4 items-center gap-2'):
                        ui.icon('location_on').classes('opacity-60')
                        location_text = ''
                        if current_user.location_city and current_user.location_state:
                            location_text = f'{current_user.location_city}, {current_user.location_state}'
                        elif current_user.location_state:
                            location_text = current_user.location_state
                        else:
                            location_text = 'Not Set'
                        ui.label(f'Work Location: {location_text}').classes('font-medium')

                    if not current_user.location_state:
                        ui.label('Set your work location with HR to see your policy details').classes('text-amber-500 italic')
                    else:
                        with ui.row().classes('w-full gap-4 flex-wrap items-stretch'):
                            # Vacation Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-blue-500 flex flex-col'):
                                ui.label('Vacation Policy').classes('font-semibold text-blue-600 mb-2')
                                vacation_tier = accrual_service.get_vacation_tier(current_user)
                                years_of_service = accrual_service.get_years_of_service(current_user)

                                if vacation_tier:
                                    tier_range = f'{vacation_tier.min_years_service}'
                                    if vacation_tier.max_years_service:
                                        tier_range += f'-{vacation_tier.max_years_service}'
                                    else:
                                        tier_range += '+'
                                    ui.label(f'{vacation_tier.annual_days} days/year').classes('text-sm')
                                    ui.label(f'Your tenure: {years_of_service} years ({tier_range} yr tier)').classes('text-xs opacity-70')

                                vacation_policy = accrual_service.get_policy_for_employee(current_user, 'VACATION')
                                if vacation_policy:
                                    if vacation_policy.max_carryover_hours and float(vacation_policy.max_carryover_hours) > 0:
                                        ui.label(f'Carryover: Up to {int(float(vacation_policy.max_carryover_hours)/8)} days').classes('text-xs opacity-60')
                                    else:
                                        ui.label('Carryover: Requires approval').classes('text-xs text-amber-500')
                                ui.element('div').classes('flex-grow')

                            # Sick Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-green-500 flex flex-col'):
                                ui.label('Sick Time Policy').classes('font-semibold text-green-600 mb-2')
                                sick_policy = accrual_service.get_policy_for_employee(current_user, 'SICK')

                                if sick_policy:
                                    if sick_policy.accrual_hours_divisor:
                                        ui.label(f'Accrual: 1 hr per {sick_policy.accrual_hours_divisor} hrs worked').classes('text-sm')
                                    if sick_policy.max_annual_hours:
                                        ui.label(f'Annual max: {int(float(sick_policy.max_annual_hours)/8)} days').classes('text-xs opacity-70')
                                    if sick_policy.max_carryover_hours:
                                        ui.label(f'Carryover: Up to {int(float(sick_policy.max_carryover_hours)/8)} days').classes('text-xs opacity-60')
                                ui.element('div').classes('flex-grow')

                            # Personal Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-purple-500 flex flex-col'):
                                ui.label('Personal Days Policy').classes('font-semibold text-purple-600 mb-2')
                                personal_policy = accrual_service.get_policy_for_employee(current_user, 'PERSONAL')

                                if personal_policy:
                                    if personal_policy.max_annual_hours:
                                        days = int(float(personal_policy.max_annual_hours) / 8)
                                        ui.label(f'Annual allowance: {days} days').classes('text-sm')
                                    if personal_policy.min_increment_hours:
                                        ui.label(f'Minimum request: {personal_policy.min_increment_hours} hrs').classes('text-xs opacity-70')
                                ui.element('div').classes('flex-grow')
                else:
                    ui.label('Unable to load user information').classes('text-red-500')

    finally:
        if db:
            db.close()


def logout():
    """Clear user session and redirect to home."""
    app.storage.general.pop('user', None)
    ui.navigate.to('/')


def cancel_request(request_id: int):
    """Cancel a pending PTO request."""
    db = None
    try:
        db = next(get_db())
        from src.services.pto_service import PTOService

        # Get the request
        pto_service = PTOService(db)
        request = pto_service.get_request_by_id(request_id)

        if not request:
            ui.notify('Request not found', type='negative')
            return

        if request.status != 'pending':
            ui.notify('Only pending requests can be cancelled', type='warning')
            return

        # Update the request status
        request.status = 'cancelled'

        # If it was vacation, return the pending hours
        if request.pto_type.lower() == 'vacation':
            balance_service = BalanceService(db)
            balance = balance_service.get_or_create_balance(request.user_id, request.start_date.year)
            # Remove from pending
            balance_service.adjust_vacation_used(balance.id, -float(request.total_days), is_pending=True)

        db.commit()
        ui.notify('Request cancelled successfully', type='positive')
        ui.navigate.to('/dashboard')

    except Exception as e:
        ui.notify(f'Error cancelling request: {str(e)}', type='negative')
    finally:
        if db:
            db.close()


def show_employee_pto_history(employee_id: int, employee_name: str, default_year: int):
    """Show a dialog with employee's PTO history, filtering, and clickable events."""
    db = None
    try:
        db = next(get_db())
        balance_service = BalanceService(db)
        user_service = UserService(db)

        # Get employee info
        employee = user_service.get_user_by_id(employee_id)
        if not employee:
            ui.notify('Employee not found', type='negative')
            return

        # Get available years (current year and previous)
        current_year = date.today().year
        available_years = [current_year, current_year - 1]

        # Create dialog
        with ui.dialog() as history_dialog, ui.card().classes('w-full max-w-4xl p-0'):
            # Header
            with ui.row().classes('w-full justify-between items-center p-4 bg-teal-500 text-white'):
                with ui.column().classes('gap-0'):
                    ui.label(employee_name).classes('text-xl font-bold')
                    ui.label(employee.email).classes('text-sm opacity-80')
                ui.button(icon='close', on_click=history_dialog.close).props('flat round dense color=white')

            # Content area with state
            content_container = ui.column().classes('w-full')

            # State variables
            state = {'year': default_year, 'filter_type': 'all'}

            def render_content():
                content_container.clear()
                with content_container:
                    selected_year = state['year']
                    filter_type = state['filter_type']

                    # Get balance for selected year
                    balance = balance_service.get_or_create_balance(employee_id, selected_year)

                    # Balance Summary Card
                    with ui.card().classes('w-full m-4 p-4'):
                        with ui.row().classes('w-full justify-between items-center mb-3'):
                            ui.label(f'{selected_year} PTO Summary').classes('text-lg font-semibold')

                            # Year selector
                            def on_year_change(e):
                                state['year'] = int(e.value)
                                render_content()

                            ui.select(
                                options={y: str(y) for y in available_years},
                                value=selected_year,
                                on_change=on_year_change
                            ).props('dense outlined').classes('w-24')

                        if balance:
                            with ui.row().classes('w-full gap-4 justify-center flex-wrap'):
                                # Vacation
                                with ui.card().classes('flex-1 min-w-32 p-3 border-l-4 border-blue-500 text-center'):
                                    ui.label('Vacation').classes('text-xs font-semibold text-blue-600')
                                    ui.label(f'{format_days(float(balance.vacation_used))}').classes('text-2xl font-bold text-blue-600')
                                    ui.label('days used').classes('text-xs opacity-60')
                                    total = float(balance.vacation_total) + float(balance.vacation_carryover)
                                    ui.label(f'of {format_days(total)} total').classes('text-xs opacity-40')

                                # Sick
                                with ui.card().classes('flex-1 min-w-32 p-3 border-l-4 border-green-500 text-center'):
                                    ui.label('Sick').classes('text-xs font-semibold text-green-600')
                                    ui.label(f'{format_days(float(balance.sick_used))}').classes('text-2xl font-bold text-green-600')
                                    ui.label('days used').classes('text-xs opacity-60')
                                    total = float(balance.sick_total) + float(balance.sick_carryover)
                                    ui.label(f'of {format_days(total)} total').classes('text-xs opacity-40')

                                # Personal
                                with ui.card().classes('flex-1 min-w-32 p-3 border-l-4 border-purple-500 text-center'):
                                    ui.label('Personal').classes('text-xs font-semibold text-purple-600')
                                    ui.label(f'{format_days(float(balance.personal_used))}').classes('text-2xl font-bold text-purple-600')
                                    ui.label('days used').classes('text-xs opacity-60')
                                    total = float(balance.personal_total) + float(balance.personal_carryover)
                                    ui.label(f'of {format_days(total)} total').classes('text-xs opacity-40')

                    # Filter buttons
                    with ui.row().classes('w-full px-4 gap-2 flex-wrap'):
                        ui.label('Filter by:').classes('text-sm opacity-60 self-center')

                        def create_filter_handler(f_type):
                            def handler():
                                state['filter_type'] = f_type
                                render_content()
                            return handler

                        filter_buttons = [
                            ('all', 'All', 'grey'),
                            ('vacation', 'Vacation', 'blue'),
                            ('sick', 'Sick', 'green'),
                            ('personal', 'Personal', 'purple'),
                        ]

                        for f_type, f_label, f_color in filter_buttons:
                            is_active = filter_type == f_type
                            btn = ui.button(
                                f_label,
                                on_click=create_filter_handler(f_type)
                            )
                            if is_active:
                                btn.props(f'color={f_color}')
                            else:
                                btn.props(f'outline color={f_color}')

                    # Get PTO requests for selected year
                    all_requests = PTOService.get_user_requests(db, employee_id)
                    year_requests = [
                        r for r in all_requests
                        if r.start_date.year == selected_year or r.end_date.year == selected_year
                    ]

                    # Apply filter
                    if filter_type != 'all':
                        year_requests = [r for r in year_requests if r.pto_type.lower() == filter_type]

                    # Sort by date descending
                    year_requests.sort(key=lambda x: x.start_date, reverse=True)

                    # Request list
                    with ui.column().classes('w-full p-4 gap-2'):
                        ui.label(f'Time Off History ({len(year_requests)} records)').classes('text-sm font-semibold opacity-70 mb-2')

                        if year_requests:
                            type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
                            type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}
                            status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

                            for req in year_requests:
                                pto_type_lower = req.pto_type.lower()
                                border_color = type_colors.get(pto_type_lower, 'gray')

                                def create_detail_handler(request):
                                    def show_detail():
                                        show_pto_detail_dialog(request)
                                    return show_detail

                                with ui.card().classes(f'w-full p-3 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-md').on('click', create_detail_handler(req)):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        with ui.row().classes('gap-3 items-center'):
                                            ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                            with ui.column().classes('gap-0'):
                                                with ui.row().classes('gap-2 items-center'):
                                                    ui.label(req.pto_type.title()).classes('font-medium')
                                                    ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey')).props('dense')

                                                if req.start_date == req.end_date:
                                                    ui.label(req.start_date.strftime('%B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req.start_date.strftime('%b %d')} - {req.end_date.strftime('%b %d, %Y')}").classes('text-sm opacity-70')

                                        with ui.row().classes('gap-2 items-center'):
                                            days = float(req.total_days)
                                            ui.label(f'{format_days(days * 8)} days').classes('font-medium')
                                            ui.icon('chevron_right').classes('text-gray-400')
                        else:
                            with ui.row().classes('w-full justify-center py-8'):
                                with ui.column().classes('items-center gap-2'):
                                    ui.icon('event_busy', color='grey').classes('text-4xl')
                                    filter_text = f' {filter_type}' if filter_type != 'all' else ''
                                    ui.label(f'No{filter_text} time off records for {selected_year}').classes('opacity-60')

            # Initial render
            render_content()

        history_dialog.open()

    except Exception as e:
        ui.notify(f'Error loading employee history: {str(e)}', type='negative')
    finally:
        if db:
            db.close()


def show_pto_detail_dialog(request):
    """Show detailed information about a PTO request."""
    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

    pto_type_lower = request.pto_type.lower()
    header_color = type_colors.get(pto_type_lower, 'gray')

    with ui.dialog() as detail_dialog, ui.card().classes('w-full max-w-md p-0'):
        # Header
        with ui.row().classes(f'w-full justify-between items-center p-4 bg-{header_color}-500 text-white'):
            with ui.row().classes('gap-2 items-center'):
                type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}
                ui.icon(type_icons.get(pto_type_lower, 'event')).classes('text-2xl')
                ui.label(f'{request.pto_type.title()} Time Off').classes('text-lg font-bold')
            ui.button(icon='close', on_click=detail_dialog.close).props('flat round dense color=white')

        # Content
        with ui.column().classes('w-full p-4 gap-4'):
            # Status badge
            with ui.row().classes('w-full justify-center'):
                ui.badge(request.status.title(), color=status_colors.get(request.status, 'grey')).classes('text-lg px-4 py-1')

            # Date info
            with ui.card().classes('w-full p-3'):
                ui.label('Dates').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                if request.start_date == request.end_date:
                    ui.label(request.start_date.strftime('%A, %B %d, %Y')).classes('font-medium')
                else:
                    ui.label(f"{request.start_date.strftime('%A, %B %d, %Y')}").classes('font-medium')
                    ui.label('to').classes('text-xs opacity-60')
                    ui.label(f"{request.end_date.strftime('%A, %B %d, %Y')}").classes('font-medium')

            # Duration
            with ui.card().classes('w-full p-3'):
                ui.label('Duration').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                days = float(request.total_days)
                hours = days * 8
                ui.label(f'{format_days(hours)} days ({int(hours)} hours)').classes('font-medium')

            # Notes (if any)
            if request.notes:
                with ui.card().classes('w-full p-3'):
                    ui.label('Notes').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                    ui.label(request.notes).classes('text-sm')

            # Denial reason (if denied)
            if request.status == 'denied' and request.denial_reason:
                with ui.card().classes('w-full p-3 border-l-4 border-red-500'):
                    ui.label('Denial Reason').classes('text-xs font-semibold uppercase text-red-500 mb-2')
                    ui.label(request.denial_reason).classes('text-sm')

            # Submission info
            with ui.row().classes('w-full justify-between text-xs opacity-50'):
                ui.label(f'Submitted: {request.created_at.strftime("%b %d, %Y")}')
                if request.approved_at:
                    ui.label(f'Processed: {request.approved_at.strftime("%b %d, %Y")}')

    detail_dialog.open()
