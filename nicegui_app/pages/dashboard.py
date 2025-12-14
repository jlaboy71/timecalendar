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
from nicegui_app.components.theme import apply_dark_mode, skeleton_card, show_warning_dialog, show_error_dialog
from nicegui_app.components.formatting import format_days_hours


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
        # Sort by approved_at descending (most recently approved first)
        approved_requests.sort(key=lambda x: x.approved_at or x.submitted_at, reverse=True)
        recent_requests = approved_requests  # Show all approved requests (scrollable)

        # Get team pending requests for managers/admins
        team_pending_requests = []
        cancellation_requests = []
        if user_role in ['manager', 'admin', 'superadmin']:
            team_pending_requests = PTOService.get_pending_requests_with_employee_info(db)
            # For managers, only get cancellation requests from their department
            if user_role == 'manager':
                manager_user = user_service.get_user_by_id(user_id)
                if manager_user and manager_user.department_id:
                    cancellation_requests = PTOService.get_cancellation_requests_with_employee_info(db, manager_user.department_id)
            else:
                cancellation_requests = PTOService.get_cancellation_requests_with_employee_info(db)

        # ============ MAIN LAYOUT ============
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):

            # Header with logo, greeting and logout
            is_dark = app.storage.general.get('dark_mode', True)  # Default to dark mode
            greeting_color = '#C9A227' if is_dark else '#5a6a72'
            with ui.row().classes('w-full justify-between items-start mb-6'):
                with ui.column().classes('gap-1'):
                    ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')

                with ui.column().classes('items-end gap-1'):
                    # Greeting at top right
                    greeting = get_time_based_greeting()
                    ui.label(f'{greeting}, {user_first_name} {user_last_name}').classes('text-base font-medium uppercase').style(f'color: {greeting_color};')
                    with ui.row().classes('items-center gap-2'):
                        # Help button
                        ui.button(icon='help_outline', on_click=lambda: ui.navigate.to('/help')).props('flat round aria-label="Help Center"').tooltip('Help Center')

                        # Dark mode toggle
                        dark_mode = ui.dark_mode()

                        def toggle_dark_mode():
                            # Get current state from storage, default to True (dark mode)
                            current = app.storage.general.get('dark_mode', True)
                            new_state = not current
                            app.storage.general['dark_mode'] = new_state
                            if new_state:
                                dark_mode.enable()
                            else:
                                dark_mode.disable()
                            dark_toggle.props(f'icon={"light_mode" if new_state else "dark_mode"}')

                        # Initialize based on stored preference
                        is_dark = app.storage.general.get('dark_mode', True)  # Default to dark mode
                        if is_dark:
                            dark_mode.enable()

                        dark_toggle = ui.button(
                            icon='light_mode' if is_dark else 'dark_mode',
                            on_click=toggle_dark_mode
                        ).props('flat round')

                        ui.button('LOGOUT', icon='logout', on_click=lambda: logout()).props('flat color=red')

            # ============ PTO BALANCES CARD (not for admin/superadmin - they don't take PTO) ============
            if user_role not in ['admin', 'superadmin']:
              with ui.card().classes('w-full mb-4'):
                # Year selector state
                selected_year = {'value': current_year}
                next_year = current_year + 1

                # Header with year toggle
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    balance_title = ui.label(f'PTO Balances ({current_year})').classes('text-lg font-semibold')

                    # Year toggle buttons
                    with ui.button_group().props('outline rounded'):
                        year_btn_current = ui.button(str(current_year), on_click=lambda: switch_year(current_year))
                        year_btn_next = ui.button(str(next_year), on_click=lambda: switch_year(next_year))

                    # Set initial button states
                    year_btn_current.props('color=primary')
                    year_btn_next.props('color=grey')

                # Container for balance display (will be refreshed)
                balance_container = ui.column().classes('w-full')

                def switch_year(year):
                    """Switch the displayed year and refresh balances."""
                    selected_year['value'] = year
                    balance_title.set_text(f'PTO Balances ({year})')

                    # Update button styles
                    if year == current_year:
                        year_btn_current.props('color=primary')
                        year_btn_next.props('color=grey')
                    else:
                        year_btn_current.props('color=grey')
                        year_btn_next.props('color=primary')

                    # Refresh the balance display
                    render_balances(year)

                def render_balances(year):
                    """Render balance cards for the given year."""
                    balance_container.clear()

                    # Get balance for the selected year
                    year_balance = balance_service.get_or_create_balance(user_id, year)

                    # Get requests for the selected year
                    year_requests = [r for r in all_requests if r.start_date.year == year]

                    with balance_container:
                        if year_balance:
                            # Show warning for unallocated future year
                            bal_total = float(year_balance.vacation_total or 0) + float(year_balance.sick_total or 0) + float(year_balance.personal_total or 0)
                            if bal_total == 0 and year != current_year:
                                with ui.card().classes('w-full p-3 mb-4 border-l-4 border-amber-500'):
                                    with ui.row().classes('items-center'):
                                        ui.icon('info', color='amber').classes('mr-2')
                                        ui.label(f'{year} PTO balances not yet allocated by admin').classes('text-amber-600')

                            with ui.row().classes('w-full gap-4 justify-center flex-wrap'):
                                # Vacation
                                vacation_available = float(year_balance.vacation_available)
                                vacation_total = float(year_balance.vacation_total) + float(year_balance.vacation_carryover)
                                vacation_pending = float(year_balance.vacation_pending)
                                vacation_used = float(year_balance.vacation_used)
                                vacation_pct = (vacation_available / vacation_total * 100) if vacation_total > 0 else 0

                                with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-blue-500'):
                                    ui.label('VACATION').classes('text-lg font-bold text-blue-600')

                                    # Show negative balance in red with warning
                                    if vacation_available < 0:
                                        display_text, tooltip_text = format_days_hours(vacation_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-red-500 my-2').tooltip(tooltip_text)
                                        ui.label('OVERDRAWN').classes('text-sm text-red-500 font-medium')
                                    else:
                                        display_text, tooltip_text = format_days_hours(vacation_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-blue-600 my-2').tooltip(tooltip_text)
                                        ui.label('AVAILABLE').classes('text-sm opacity-70')

                                    # Progress bar showing used/total
                                    used_ratio = min(vacation_used / vacation_total, 1.0) if vacation_total > 0 else 0
                                    with ui.column().classes('w-full mt-3 gap-1'):
                                        with ui.row().classes('w-full justify-between text-xs'):
                                            ui.label(f'{format_days(vacation_used)} used').classes('text-blue-600')
                                            ui.label(f'{format_days(vacation_total)} total').classes('opacity-60')
                                        ui.linear_progress(value=used_ratio, show_value=False).props('color=blue-5 track-color=grey-3').classes('w-full')
                                        if vacation_pending > 0:
                                            ui.label(f'{format_days(vacation_pending)} pending').classes('text-xs text-amber-500')

                                # Sick
                                sick_available = float(year_balance.sick_available)
                                sick_total = float(year_balance.sick_total) + float(year_balance.sick_carryover)
                                sick_used = float(year_balance.sick_used)
                                sick_pct = (sick_available / sick_total * 100) if sick_total > 0 else 0

                                with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-green-500'):
                                    ui.label('SICK').classes('text-lg font-bold text-green-600')

                                    # Show negative balance in red with warning
                                    if sick_available < 0:
                                        display_text, tooltip_text = format_days_hours(sick_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-red-500 my-2').tooltip(tooltip_text)
                                        ui.label('OVERDRAWN').classes('text-sm text-red-500 font-medium')
                                    else:
                                        display_text, tooltip_text = format_days_hours(sick_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-green-600 my-2').tooltip(tooltip_text)
                                        ui.label('AVAILABLE').classes('text-sm opacity-70')

                                    # Progress bar showing used/total
                                    used_ratio = min(sick_used / sick_total, 1.0) if sick_total > 0 else 0
                                    with ui.column().classes('w-full mt-3 gap-1'):
                                        with ui.row().classes('w-full justify-between text-xs'):
                                            ui.label(f'{format_days(sick_used)} used').classes('text-green-600')
                                            ui.label(f'{format_days(sick_total)} total').classes('opacity-60')
                                        ui.linear_progress(value=used_ratio, show_value=False).props('color=green-5 track-color=grey-3').classes('w-full')

                                # Personal
                                personal_available = float(year_balance.personal_available)
                                personal_total = float(year_balance.personal_total) + float(year_balance.personal_carryover)
                                personal_used = float(year_balance.personal_used)
                                personal_pct = (personal_available / personal_total * 100) if personal_total > 0 else 0

                                with ui.card().classes('flex-1 min-w-48 p-4 border-l-4 border-purple-500'):
                                    ui.label('PERSONAL').classes('text-lg font-bold text-purple-600')

                                    # Show negative balance in red with warning
                                    if personal_available < 0:
                                        display_text, tooltip_text = format_days_hours(personal_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-red-500 my-2').tooltip(tooltip_text)
                                        ui.label('OVERDRAWN').classes('text-sm text-red-500 font-medium')
                                    else:
                                        display_text, tooltip_text = format_days_hours(personal_available)
                                        ui.label(display_text).classes('text-2xl font-bold text-purple-600 my-2').tooltip(tooltip_text)
                                        ui.label('AVAILABLE').classes('text-sm opacity-70')

                                    # Progress bar showing used/total
                                    used_ratio = min(personal_used / personal_total, 1.0) if personal_total > 0 else 0
                                    with ui.column().classes('w-full mt-3 gap-1'):
                                        with ui.row().classes('w-full justify-between text-xs'):
                                            ui.label(f'{format_days(personal_used)} used').classes('text-purple-600')
                                            ui.label(f'{format_days(personal_total)} total').classes('opacity-60')
                                        ui.linear_progress(value=used_ratio, show_value=False).props('color=purple-5 track-color=grey-3').classes('w-full')

                            # ============ OTHER LEAVE TYPES (Non-Accruing) ============
                            other_leave_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']
                            other_leave_requests = [r for r in year_requests
                                                   if r.pto_type.lower() in other_leave_types
                                                   and r.status == 'approved']

                            other_leave_usage = {}
                            for leave_type in other_leave_types:
                                days_used = sum(float(r.total_days or 0) for r in other_leave_requests
                                               if r.pto_type.lower() == leave_type)
                                other_leave_usage[leave_type] = days_used

                            total_other_used = sum(other_leave_usage.values())

                            with ui.expansion(f'Other Leave Types ({total_other_used:.0f} days used)', icon='more_horiz').classes('w-full'):
                                ui.label(f'Non-accruing leave used in {year}').classes('text-xs opacity-60 mb-3')

                                leave_info = {
                                    'bereavement': {'label': 'Bereavement', 'icon': 'sentiment_very_dissatisfied', 'color': 'brown', 'policy': 'Immediate family: 5 days, Extended: 3 days'},
                                    'fmla': {'label': 'Family & Medical', 'icon': 'family_restroom', 'color': 'teal', 'policy': 'FMLA: Up to 12 weeks unpaid, job-protected'},
                                    'jury_duty': {'label': 'Jury Duty', 'icon': 'gavel', 'color': 'indigo', 'policy': 'Paid time for jury service'},
                                    'voting': {'label': 'Voting Time', 'icon': 'how_to_vote', 'color': 'cyan', 'policy': 'Up to 2 hours if polls not open 4+ hrs outside work'},
                                    'military': {'label': 'Military Leave', 'icon': 'military_tech', 'color': 'deep-orange', 'policy': 'Per USERRA requirements, job-protected'},
                                }

                                with ui.row().classes('w-full gap-2 items-stretch'):
                                    for leave_type, info in leave_info.items():
                                        days = other_leave_usage.get(leave_type, 0)
                                        color = info['color']

                                        with ui.card().classes(f'p-3 border-l-4 border-{color}-500 flex-1').style('height: 180px;'):
                                            with ui.row().classes('items-center gap-2 mb-2'):
                                                ui.icon(info['icon']).classes(f'text-{color}-500')
                                                ui.label(info['label']).classes('font-medium text-sm')

                                            if days > 0:
                                                ui.label(f'{days:.0f} days').classes(f'text-lg font-bold text-{color}-600')
                                            else:
                                                ui.label('—').classes('text-lg font-bold opacity-30')

                                            ui.label(info['policy']).classes('text-xs opacity-50 mt-2')
                        else:
                            ui.label(f'No balance data for {year}').classes('opacity-70')

                # Initial render
                render_balances(current_year)

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
                                        ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                    else:
                                        ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

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
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

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
                                                ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                            else:
                                                ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

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

            # ============ CANCELLATION REQUESTS (Managers/Admins) ============
            if cancellation_requests:
                type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

                with ui.card().classes('w-full mb-4 border-l-4 border-amber-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('cancel_schedule_send', color='amber').classes('text-xl')
                            ui.label('Cancellation Requests').classes('text-lg font-semibold')
                        ui.badge(f'{len(cancellation_requests)} pending', color='amber').props('outline')

                    for req in cancellation_requests[:5]:
                        pto_type_lower = req['pto_type'].lower()
                        border_color = type_colors.get(pto_type_lower, 'gray')

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-3 items-center'):
                                    ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                    with ui.column().classes('gap-0'):
                                        ui.label(req['employee_name']).classes('font-medium')
                                        with ui.row().classes('gap-2 items-center'):
                                            ui.label(req['pto_type'].title()).classes('text-sm opacity-70')
                                            ui.label('•').classes('text-xs opacity-50')
                                            if req['start_date'] == req['end_date']:
                                                ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                            else:
                                                ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')
                                        if req.get('cancellation_reason'):
                                            ui.label(f"Reason: {req['cancellation_reason']}").classes('text-xs opacity-60 italic')

                                with ui.row().classes('items-center gap-3'):
                                    days = float(req['total_days'])
                                    ui.label(f'{format_days(days * 8)} days').classes('font-medium')

                                    def create_review_handler(request_id):
                                        def review():
                                            ui.navigate.to(f'/manager/request/{request_id}')
                                        return review

                                    ui.button('Review', icon='visibility', on_click=create_review_handler(req['request_id'])).props('flat dense color=amber size=sm')

                    if len(cancellation_requests) > 5:
                        with ui.row().classes('w-full justify-center mt-2'):
                            ui.label(f'+ {len(cancellation_requests) - 5} more cancellation requests').classes('text-sm opacity-60')

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
                                    ui.label('Team PTO History').classes('text-lg font-semibold')
                                ui.badge(f'{len(team_members)} members', color='teal').props('outline')

                            # Build options for searchable dropdown
                            team_options = {
                                m.id: f"{m.full_name} ({m.email})" for m in sorted(team_members, key=lambda x: x.full_name)
                            }

                            def on_employee_select(e):
                                if e.value:
                                    selected_member = next((m for m in team_members if m.id == e.value), None)
                                    if selected_member:
                                        show_employee_pto_history(selected_member.id, selected_member.full_name, current_year)
                                    # Reset selection after viewing
                                    e.sender.value = None

                            with ui.row().classes('w-full items-center gap-3'):
                                ui.select(
                                    options=team_options,
                                    with_input=True,
                                    on_change=on_employee_select,
                                    label='Search team member...'
                                ).props('dense outlined use-input input-debounce="300" clearable').classes('flex-1').style('min-width: 250px')
                                ui.label('Select to view PTO history').classes('text-xs opacity-50')

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

                    # Row 2: Resources (employees only - managers use Manager Tools)
                    if user_role != 'manager':
                        ui.separator().classes('my-2')
                        with ui.column().classes('w-full gap-3'):
                            ui.label('Resources').classes('text-xs font-semibold uppercase opacity-60')
                            with ui.row().classes('w-full gap-3 flex-wrap'):
                                ui.button('My Profile', icon='person', on_click=lambda: show_user_profile_dialog(current_user, db)).props('outline color=secondary').classes('flex-1 min-w-fit')
                                ui.button('Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline color=secondary').classes('flex-1 min-w-fit')
                                ui.button('Employee Handbook', icon='menu_book', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=secondary').classes('flex-1 min-w-fit')
                                ui.button('Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=secondary').classes('flex-1 min-w-fit')

                    # Row 3: Manager Tools (managers only)
                    if user_role == 'manager':
                        ui.separator().classes('my-2')
                        with ui.column().classes('w-full gap-3'):
                            ui.label('Manager Tools').classes('text-xs font-semibold uppercase opacity-60')
                            with ui.row().classes('w-full gap-3 flex-wrap'):
                                ui.button('Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Manage Team', icon='badge', on_click=lambda: ui.navigate.to('/manager/team')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Carryover', icon='approval', on_click=lambda: ui.navigate.to('/manager/carryover')).props('outline color=indigo').classes('flex-1 min-w-fit')
                            with ui.row().classes('w-full gap-3 flex-wrap'):
                                ui.button('Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Analytics', icon='insights', on_click=lambda: ui.navigate.to('/analytics')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Handbook', icon='menu_book', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Settings', icon='settings', on_click=lambda: ui.navigate.to('/manager/settings')).props('outline color=indigo').classes('flex-1 min-w-fit')

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
                        type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                        type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

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
                                                    ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

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
                        ui.button('Calendar', icon='calendar_month',
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
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    ui.label('Recent Approved Time Off').classes('text-lg font-semibold')
                    if recent_requests:
                        ui.label(f'{len(recent_requests)} requests').classes('text-xs opacity-50')

                if recent_requests:
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}

                    # Scrollable container with max height
                    with ui.scroll_area().classes('w-full').style('max-height: 300px'):
                      for req in recent_requests:
                        pto_type_lower = req.pto_type.lower()
                        border_color = type_colors.get(pto_type_lower, 'gray')

                        def create_detail_handler(request):
                            def show_detail():
                                show_pto_detail_dialog(request)
                            return show_detail

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-md').on('click', create_detail_handler(req)):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-4 items-center'):
                                    # Type icon
                                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}
                                    ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')

                                    with ui.column().classes('gap-0'):
                                        ui.label(req.pto_type.title()).classes('font-medium')
                                        if req.start_date == req.end_date:
                                            ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-xs opacity-60')
                                        else:
                                            ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-xs opacity-60')

                                with ui.row().classes('gap-3 items-center'):
                                    days_display = float(req.total_days)
                                    ui.label(f'{format_days(days_display * 8)} days').classes('text-sm')
                                    ui.icon('chevron_right').classes('text-gray-400')
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
            show_error_dialog('Not Found', 'The request you are looking for was not found.')
            return

        if request.status != 'pending':
            show_warning_dialog('Cannot Cancel', 'Only pending requests can be cancelled.')
            return

        # Update the request status
        request.status = 'cancelled'

        # If it was vacation, return the pending hours
        if request.pto_type.lower() == 'vacation':
            balance_service = BalanceService(db)
            balance = balance_service.get_or_create_balance(request.user_id, request.start_date.year)
            # Remove from pending (convert to Decimal for balance service)
            from decimal import Decimal
            balance_service.adjust_vacation_used(balance.id, -Decimal(str(request.total_days)), is_pending=True)

        db.commit()
        ui.notify('Request cancelled successfully', type='positive')
        ui.navigate.to('/dashboard')

    except Exception as e:
        show_error_dialog('Error', f'Error cancelling request: {str(e)}')
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
            show_error_dialog('Not Found', 'The employee you are looking for was not found.')
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

                    # Filter buttons - all leave types
                    with ui.row().classes('w-full px-4 gap-2 flex-wrap'):
                        ui.label('Filter by:').classes('text-sm opacity-60 self-center')

                        def create_filter_handler(f_type):
                            def handler():
                                state['filter_type'] = f_type
                                render_content()
                            return handler

                        # All leave types with distinct colors
                        filter_buttons = [
                            ('all', 'All', 'grey'),
                            ('vacation', 'Vacation', 'blue'),
                            ('sick', 'Sick', 'green'),
                            ('personal', 'Personal', 'purple'),
                            ('bereavement', 'Bereavement', 'brown'),
                            ('fmla', 'FMLA', 'teal'),
                            ('jury_duty', 'Jury Duty', 'indigo'),
                            ('voting', 'Voting', 'cyan'),
                            ('military', 'Military', 'deep-orange'),
                        ]

                        for f_type, f_label, f_color in filter_buttons:
                            is_active = filter_type == f_type
                            btn = ui.button(
                                f_label,
                                on_click=create_filter_handler(f_type)
                            ).props('dense size=sm')
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
                            type_colors = {
                                'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
                                'bereavement': 'brown', 'fmla': 'teal', 'jury_duty': 'indigo',
                                'voting': 'cyan', 'military': 'deep-orange', 'work_from_home': 'red'
                            }
                            type_icons = {
                                'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person',
                                'bereavement': 'sentiment_very_dissatisfied', 'fmla': 'family_restroom',
                                'jury_duty': 'gavel', 'voting': 'how_to_vote', 'military': 'military_tech',
                                'work_from_home': 'home_work'
                            }
                            status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

                            for req in year_requests:
                                pto_type_lower = req.pto_type.lower()
                                border_color = type_colors.get(pto_type_lower, 'grey')

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
                                                    ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

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
        show_error_dialog('Error', f'Error loading employee history: {str(e)}')
    finally:
        if db:
            db.close()


def show_pto_detail_dialog(request):
    """Show detailed information about a PTO request with action buttons."""
    type_colors = {
        'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
        'bereavement': 'brown', 'fmla': 'teal', 'jury_duty': 'indigo',
        'voting': 'cyan', 'military': 'deep-orange', 'work_from_home': 'red'
    }
    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

    # Get current user info for action button permissions
    current_user = app.storage.general.get('user', {})
    user_id = current_user.get('id')
    user_role = current_user.get('role', 'employee')

    pto_type_lower = request.pto_type.lower()
    header_color = type_colors.get(pto_type_lower, 'grey')

    # Store request info for action handlers
    req_id = request.id
    req_type = request.pto_type
    req_total_days = float(request.total_days)
    req_year = request.start_date.year
    req_user_id = request.user_id
    req_status = request.status
    is_own_request = (req_user_id == user_id)
    can_direct_delete = user_role in ['admin', 'superadmin'] or (user_role == 'manager' and is_own_request)

    with ui.dialog() as detail_dialog, ui.card().classes('w-full max-w-md p-0'):
        # Header
        with ui.row().classes(f'w-full justify-between items-center p-4 bg-{header_color}-500 text-white'):
            with ui.row().classes('gap-2 items-center'):
                type_icons = {
                    'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person',
                    'bereavement': 'sentiment_very_dissatisfied', 'fmla': 'family_restroom',
                    'jury_duty': 'gavel', 'voting': 'how_to_vote', 'military': 'military_tech'
                }
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

            # Manager Approval info (if approved)
            if request.status == 'approved' and request.approved_at:
                with ui.card().classes('w-full p-3 border-l-4 border-green-500'):
                    ui.label('Manager Approved').classes('text-xs font-semibold uppercase text-green-600 mb-2')
                    ui.label(request.approved_at.strftime('%A, %B %d, %Y')).classes('font-medium')

            # Submission info
            with ui.row().classes('w-full justify-center text-xs opacity-50'):
                ui.label(f'Submitted: {request.created_at.strftime("%b %d, %Y")}')

            # Action buttons section
            def delete_request_direct():
                """Direct delete for admin/superadmin/manager's own requests."""
                del_db = next(get_db())
                try:
                    from src.models.pto_request import PTORequest
                    req = del_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                    if not req:
                        show_error_dialog('Not Found', 'The request was not found.')
                        return

                    req.status = 'cancelled'

                    # Restore balance based on previous status
                    if pto_type_lower in ['vacation', 'sick', 'personal']:
                        balance_service = BalanceService(del_db)
                        balance = balance_service.get_or_create_balance(req_user_id, req_year)
                        hours_to_restore = req_total_days * 8

                        if req_status == 'pending':
                            if pto_type_lower == 'vacation':
                                balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)
                        else:
                            if pto_type_lower == 'vacation':
                                balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                            elif pto_type_lower == 'sick':
                                balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                            elif pto_type_lower == 'personal':
                                balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

                    del_db.commit()
                    ui.notify('Request deleted and balance restored', type='positive')
                    detail_dialog.close()
                    ui.navigate.to('/dashboard')
                finally:
                    del_db.close()

            def cancel_pending_request():
                """Cancel pending request for employee."""
                cancel_db = next(get_db())
                try:
                    from src.models.pto_request import PTORequest
                    req = cancel_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                    if not req:
                        show_error_dialog('Not Found', 'The request was not found.')
                        return

                    req.status = 'cancelled'

                    if req_type.lower() == 'vacation':
                        balance_service = BalanceService(cancel_db)
                        balance = balance_service.get_or_create_balance(req_user_id, req_year)
                        hours_to_restore = req_total_days * 8
                        balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)

                    cancel_db.commit()
                    ui.notify('Request cancelled successfully', type='positive')
                    detail_dialog.close()
                    ui.navigate.to('/dashboard')
                finally:
                    cancel_db.close()

            def show_cancellation_dialog():
                """Show dialog for employee to request cancellation of approved PTO."""
                detail_dialog.close()
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
                            from src.models.pto_request import PTORequest
                            req = req_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                            if not req:
                                show_error_dialog('Not Found', 'The request was not found.')
                                return

                            req.cancellation_requested = True
                            req.cancellation_reason = reason_input.value.strip() if reason_input.value else None
                            req.cancellation_requested_at = datetime.now()

                            req_db.commit()
                            ui.notify('Cancellation request submitted to your manager', type='positive')
                            cancel_dialog.close()
                            ui.navigate.to('/dashboard')
                        finally:
                            req_db.close()

                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancel', on_click=cancel_dialog.close).props('flat')
                        ui.button('Submit Request', on_click=submit_cancellation).props('color=amber')

                cancel_dialog.open()

            # Show action buttons based on role and status
            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                if can_direct_delete and req_status in ['pending', 'approved']:
                    ui.button('Delete', icon='delete', on_click=delete_request_direct).props('color=negative')
                elif is_own_request and req_status == 'pending':
                    ui.button('Cancel Request', icon='cancel', on_click=cancel_pending_request).props('color=negative')
                elif is_own_request and req_status == 'approved':
                    # Check if cancellation already requested
                    has_cancellation = hasattr(request, 'cancellation_requested') and request.cancellation_requested
                    if not has_cancellation:
                        ui.button('Request Cancellation', icon='cancel_schedule_send', on_click=show_cancellation_dialog).props('color=amber')
                    else:
                        ui.label('Cancellation Pending').classes('text-amber-600 text-sm italic')

    detail_dialog.open()


def show_user_profile_dialog(user, _db=None):
    """Show a dialog with user profile details."""
    if not user:
        show_warning_dialog('Not Available', 'User information is not available.')
        return

    # Collect all needed info from database first
    db = next(get_db())
    try:
        # Get department name
        department_name = 'Not Assigned'
        if user.department_id:
            dept = DepartmentService.get_department_by_id(db, user.department_id)
            if dept:
                department_name = dept.name

        # Get manager info
        manager_name = 'Not Assigned'
        if user.department_id:
            dept = DepartmentService.get_department_by_id(db, user.department_id)
            if dept and dept.manager_id:
                user_service = UserService(db)
                manager = user_service.get_user_by_id(dept.manager_id)
                if manager:
                    manager_name = f'{manager.first_name} {manager.last_name}'
    finally:
        db.close()

    # Calculate tenure
    hire_date_str = None
    tenure_text = None
    if user.hire_date:
        hire_date_str = user.hire_date.strftime('%B %d, %Y')
        today = date.today()
        years = today.year - user.hire_date.year
        if (today.month, today.day) < (user.hire_date.month, user.hire_date.day):
            years -= 1
        tenure_text = f'{years} year{"s" if years != 1 else ""}' if years > 0 else 'Less than 1 year'

    # Work location
    location_text = ''
    if user.location_city and user.location_state:
        location_text = f'{user.location_city}, {user.location_state}'
    elif user.location_state:
        location_text = user.location_state
    else:
        location_text = 'Not Set'

    # Use app theme color for header
    is_dark = app.storage.general.get('dark_mode', True)  # Default to dark mode
    header_color = '#C9A227' if is_dark else '#5a6a72'

    with ui.dialog() as profile_dialog, ui.card().classes('w-full max-w-md p-0'):
        # Header - using app theme color
        with ui.row().classes('w-full justify-between items-center p-4 text-white').style(f'background-color: {header_color};'):
            with ui.row().classes('gap-2 items-center'):
                ui.icon('person').classes('text-2xl')
                ui.label('My Profile').classes('text-lg font-bold')
            ui.button(icon='close', on_click=profile_dialog.close).props('flat round dense color=white')

        # Content
        with ui.column().classes('w-full p-4 gap-3'):
            # Name
            with ui.card().classes('w-full p-3'):
                ui.label('Name').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(f'{user.first_name} {user.last_name}').classes('font-medium text-lg')

            # Email
            with ui.card().classes('w-full p-3'):
                ui.label('Email').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(user.email).classes('font-medium')

            # Hire Date
            with ui.card().classes('w-full p-3 border-l-4').style(f'border-color: {header_color};'):
                ui.label('Hire Date').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                if hire_date_str:
                    ui.label(hire_date_str).classes('font-medium')
                    ui.label(f'Tenure: {tenure_text}').classes('text-sm opacity-70')
                else:
                    ui.label('Not Set').classes('font-medium opacity-60')

            # Department
            with ui.card().classes('w-full p-3 border-l-4 border-indigo-500'):
                ui.label('Department').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(department_name).classes('font-medium')

            # Work Location
            with ui.card().classes('w-full p-3 border-l-4 border-green-500'):
                ui.label('Work Location').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(location_text).classes('font-medium')

            # Role
            with ui.card().classes('w-full p-3'):
                ui.label('Role').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(user.role.title()).classes('font-medium')

            # Manager (at bottom)
            with ui.card().classes('w-full p-3 border-l-4 border-teal-500'):
                ui.label('Manager').classes('text-xs font-semibold uppercase opacity-60 mb-1')
                ui.label(manager_name).classes('font-medium')

    profile_dialog.open()
