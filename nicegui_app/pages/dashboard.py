from nicegui import ui, app
from sqlalchemy import select
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.services.policy_change_service import PolicyChangeService
from src.services.audit_service import AuditService
from nicegui_app.components.policy_change_indicator import whats_new_section
from src.services.department_service import DepartmentService
from src.services.email_service import email_service
from src.services.wfh_swap_service import WFHSwapService
from src.models.carryover_request import CarryoverRequest
from src.models.system_setting import SystemSetting
from src.database import get_db
from datetime import datetime, date, timedelta
import pytz
from nicegui_app.logo import LOGO_DATA_URL
from nicegui_app.components.header import get_time_based_greeting
from nicegui_app.components.theme import apply_dark_mode, skeleton_card, show_warning_dialog, show_error_dialog, show_success_dialog
from nicegui_app.components.formatting import format_days_hours, fmt_days
from nicegui_app.components.realtime_updates import setup_dashboard_updates


def format_days(hours: float) -> str:
    """Convert hours to readable days/hours format."""
    return fmt_days(hours / 8)


def format_hours_and_days(hours: float) -> str:
    """Format hours with days equivalent - kept for backwards compatibility."""
    return format_days(hours)


def get_pto_display_name(pto_type: str) -> str:
    """Get user-friendly display name for PTO type."""
    display_names = {
        'chicago_leave': 'LEAVE',
        'leave': 'LEAVE',
        'work_from_home': 'WFH',
    }
    lower_type = pto_type.lower()
    return display_names.get(lower_type, pto_type.replace('_', ' ').title())


def dashboard_page():
    """Employee dashboard page with PTO balances, quick actions, and recent requests."""

    apply_dark_mode()

    # Add custom CSS for admin dashboard enhancements
    ui.add_head_html('''
    <style>
        @keyframes pulse-pending {
            0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
        }
        .pulse-pending {
            animation: pulse-pending 2s ease-in-out infinite;
        }
        .admin-stat-card {
            transition: all 0.2s ease;
        }
        .admin-stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .admin-btn {
            transition: all 0.2s ease;
            border: 2px solid transparent !important;
        }
        .admin-btn:hover {
            border-color: #C9A227 !important;
            transform: scale(1.02);
        }
        .section-header {
            border-left: 3px solid #C9A227;
            padding-left: 12px;
            margin-bottom: 12px;
        }
    </style>
    ''')

    # Check if user is logged in
    if not app.storage.user.get('user'):
        ui.navigate.to('/')
        return

    # Get user info
    user_data = app.storage.user.get('user')
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
        policy_change_service = PolicyChangeService(db)
        swap_service = WFHSwapService(db)

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

        # Get pending WFH swap requests (incoming requests needing response)
        pending_wfh_swaps = swap_service.get_pending_for_user(user_id)

        # Get team approved requests for managers (for My/Team toggle)
        team_approved_requests = []

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
                    # Also get team approved requests for My/Team toggle
                    team_approved_requests = PTOService.get_team_approved_requests(db, manager_user.department_id, exclude_user_id=user_id)
            else:
                cancellation_requests = PTOService.get_cancellation_requests_with_employee_info(db)

        # ============ MAIN LAYOUT ============
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):

            # Header with logo, greeting and logout
            is_dark = app.storage.user.get('dark_mode', True)  # Default to dark mode
            greeting_color = '#C9A227' if is_dark else '#5a6a72'
            with ui.row().classes('w-full justify-between items-start mb-6'):
                with ui.column().classes('gap-1'):
                    ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 70px; width: auto;')

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
                            current = app.storage.user.get('dark_mode', True)
                            new_state = not current
                            app.storage.user['dark_mode'] = new_state
                            if new_state:
                                dark_mode.enable()
                            else:
                                dark_mode.disable()
                            dark_toggle.props(f'icon={"light_mode" if new_state else "dark_mode"}')

                        # Initialize based on stored preference
                        is_dark = app.storage.user.get('dark_mode', True)  # Default to dark mode
                        if is_dark:
                            dark_mode.enable()

                        dark_toggle = ui.button(
                            icon='light_mode' if is_dark else 'dark_mode',
                            on_click=toggle_dark_mode
                        ).props('flat round')

                        ui.button('LOGOUT', on_click=lambda: logout()).props('outline dense').style('color: #ef4444 !important; border-color: #C9A227 !important; font-weight: 600;')

            # ============ WHAT'S NEW SECTION (Policy Changes) ============
            if current_user:
                whats_new_section(current_user, policy_change_service)

            # ============ PTO BALANCES CARD (not for admin/superadmin - they don't take PTO) ============
            if user_role not in ['admin', 'superadmin']:
              with ui.card().classes('w-full mb-4'):
                # Year selector state
                selected_year = {'value': current_year}
                next_year = current_year + 1

                # Header with year dropdown
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    balance_title = ui.label('PTO BALANCES').classes('text-lg font-semibold')

                    # Year dropdown selector
                    years = [current_year, next_year]

                    def on_year_change(e):
                        """Switch the displayed year and refresh balances."""
                        year = e.value
                        selected_year['value'] = year
                        # Title stays the same - year is shown in picker
                        render_balances(year)

                    ui.select(
                        {y: str(y) for y in years},
                        label='Year',
                        value=selected_year['value'],
                        on_change=on_year_change
                    ).props('dense outlined').classes('w-24')

                # Container for balance display (will be refreshed)
                balance_container = ui.column().classes('w-full')

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

                            # Help dialog functions
                            def show_vacation_help():
                                with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                    with ui.row().classes('w-full p-4 bg-blue-500 text-white items-center'):
                                        ui.icon('beach_access', size='md').classes('mr-2')
                                        ui.label('Vacation Time Policy').classes('text-lg font-bold')
                                    with ui.column().classes('p-4 gap-3'):
                                        ui.label('Your vacation accrual is based on years of service:').classes('font-semibold')
                                        with ui.column().classes('pl-4 gap-2'):
                                            ui.label('• 0-4 years: 10 days (80 hours) per year').classes('text-sm')
                                            ui.label('• 5-9 years: 15 days (120 hours) per year').classes('text-sm')
                                            ui.label('• 10+ years: 20 days (160 hours) per year').classes('text-sm')
                                        ui.label('Use-it-or-lose-it by default. Exception carryover possible with manager approval.').classes('text-sm opacity-70 mt-2')
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button('Got it', on_click=help_dialog.close).props('color=primary')
                                help_dialog.open()

                            def show_sick_help():
                                with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                    with ui.row().classes('w-full p-4 bg-green-500 text-white items-center'):
                                        ui.icon('medical_services', size='md').classes('mr-2')
                                        ui.label('Sick Time Policy').classes('text-lg font-bold')
                                    with ui.column().classes('p-4 gap-3'):
                                        ui.label('Annual sick time allocation:').classes('font-semibold')
                                        with ui.column().classes('pl-4 gap-2'):
                                            ui.label('• 5 days (40 hours) per year').classes('text-sm')
                                            ui.label('• For illness, medical appointments, or caring for family').classes('text-sm')
                                        ui.label('Auto-Carryover: Up to 80 hours (10 days) rolls over automatically - no action needed.').classes('text-sm opacity-70 mt-2')
                                        ui.label('State laws may provide additional protections.').classes('text-sm opacity-70')
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button('Got it', on_click=help_dialog.close).props('color=green')
                                help_dialog.open()

                            def show_personal_help():
                                with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                    with ui.row().classes('w-full p-4 bg-purple-500 text-white items-center'):
                                        ui.icon('person', size='md').classes('mr-2')
                                        ui.label('Personal Time Policy').classes('text-lg font-bold')
                                    with ui.column().classes('p-4 gap-3'):
                                        ui.label('Annual personal time allocation:').classes('font-semibold')
                                        with ui.column().classes('pl-4 gap-2'):
                                            ui.label('• 2 days (16 hours) per year').classes('text-sm')
                                            ui.label('• For any personal matters').classes('text-sm')
                                            ui.label('• No documentation required').classes('text-sm')
                                            ui.label('• 24hr advance notice preferred').classes('text-sm')
                                        ui.label('Use-it-or-lose-it: Personal time does NOT carry over to next year.').classes('text-sm opacity-70 mt-2')
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button('Got it', on_click=help_dialog.close).props('color=purple')
                                help_dialog.open()

                            with ui.row().classes('w-full gap-4 justify-center items-stretch'):
                                # Vacation
                                vacation_available = float(year_balance.vacation_available)
                                vacation_allocated = float(year_balance.vacation_total)
                                vacation_carryover = float(year_balance.vacation_carryover)
                                vacation_total = vacation_allocated + vacation_carryover
                                vacation_pending = float(year_balance.vacation_pending)
                                vacation_used = float(year_balance.vacation_used)

                                with ui.card().classes('flex-1 p-4 border-l-4 border-blue-500 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 200px;').on('click', lambda: ui.navigate.to('/submit-request/vacation')):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('beach_access').classes('text-blue-600')
                                        ui.label('VACATION').classes('text-lg font-bold text-blue-600')
                                        ui.button(icon='help_outline').on('click.stop', lambda: show_vacation_help()).props('flat dense round size=xs').style('color: #3b82f6')

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
                                        # Allocated vs carryover breakdown
                                        with ui.row().classes('w-full justify-between text-xs mt-1 opacity-50'):
                                            ui.label(f'{format_days(vacation_allocated)} allocated').tooltip('Annual vacation allocation')
                                            if vacation_carryover > 0:
                                                ui.label(f'+{format_days(vacation_carryover)} carryover').tooltip('Hours carried over with management approval')
                                        ui.label('Carryover not allowed').classes('text-xs opacity-50 mt-1')
                                        ui.label('(requires approval)').classes('text-xs opacity-50')

                                # Sick
                                sick_available = float(year_balance.sick_available)
                                sick_allocated = float(year_balance.sick_total)
                                sick_carryover = float(year_balance.sick_carryover)
                                sick_total = sick_allocated + sick_carryover
                                sick_used = float(year_balance.sick_used)
                                sick_pending = float(year_balance.sick_pending)

                                with ui.card().classes('flex-1 p-4 border-l-4 border-green-500 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 200px;').on('click', lambda: ui.navigate.to('/submit-request/sick')):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('medical_services').classes('text-green-600')
                                        ui.label('SICK').classes('text-lg font-bold text-green-600')
                                        ui.button(icon='help_outline').on('click.stop', lambda: show_sick_help()).props('flat dense round size=xs').style('color: #22c55e')

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
                                        if sick_pending > 0:
                                            ui.label(f'{format_days(sick_pending)} pending').classes('text-xs text-amber-500')
                                        # Allocated vs carryover breakdown
                                        with ui.row().classes('w-full justify-between text-xs mt-1 opacity-50'):
                                            ui.label(f'{format_days(sick_allocated)} allocated').tooltip('Annual sick time allocation')
                                            if sick_carryover > 0:
                                                ui.label(f'+{format_days(sick_carryover)} carryover').tooltip('Hours carried over from last year (max 80 hrs)')
                                        ui.label('80hr (10 days) carryover max').classes('text-xs opacity-50 mt-1')

                                # Personal
                                personal_available = float(year_balance.personal_available)
                                personal_allocated = float(year_balance.personal_total)
                                personal_carryover = float(year_balance.personal_carryover)
                                personal_total = personal_allocated + personal_carryover
                                personal_used = float(year_balance.personal_used)
                                personal_pending = float(year_balance.personal_pending)

                                with ui.card().classes('flex-1 p-4 border-l-4 border-purple-500 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 200px;').on('click', lambda: ui.navigate.to('/submit-request/personal')):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('person').classes('text-purple-600')
                                        ui.label('PERSONAL').classes('text-lg font-bold text-purple-600')
                                        ui.button(icon='help_outline').on('click.stop', lambda: show_personal_help()).props('flat dense round size=xs').style('color: #a855f7')

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
                                        if personal_pending > 0:
                                            ui.label(f'{format_days(personal_pending)} pending').classes('text-xs text-amber-500')
                                        # Allocated breakdown (Personal does NOT carry over)
                                        with ui.row().classes('w-full justify-between text-xs mt-1 opacity-50'):
                                            ui.label(f'{format_days(personal_allocated)} allocated').tooltip('Annual personal time allocation (2 days/year)')
                                        ui.label('Use-it-or-lose-it (no carryover)').classes('text-xs opacity-50 mt-1')
                                        ui.label('24hr advance notice preferred').classes('text-xs opacity-50')

                                # Chicago Paid Leave (only for Chicago employees when feature is enabled)
                                chicago_setting = db.query(SystemSetting).filter(
                                    SystemSetting.key == 'chicago.safe_leave_enabled'
                                ).first()
                                is_chicago_enabled = chicago_setting and chicago_setting.bool_value
                                is_chicago_employee = current_user and current_user.location_city and current_user.location_city.lower() == 'chicago'

                                if is_chicago_enabled and is_chicago_employee:
                                    # Chicago Leave (Paid Leave for Any Reason - 16hr carryover)
                                    chicago_available = float(year_balance.chicago_paid_leave_available)
                                    chicago_accrued = float(year_balance.chicago_paid_leave_total)
                                    chicago_carryover = float(year_balance.chicago_paid_leave_carryover)
                                    chicago_total = chicago_accrued + chicago_carryover
                                    chicago_used = float(year_balance.chicago_paid_leave_used)
                                    chicago_pending = float(year_balance.chicago_paid_leave_pending)

                                    def show_chicago_leave_help():
                                        with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                            with ui.row().classes('w-full p-4 bg-amber-500 text-white items-center'):
                                                ui.icon('location_city', size='md').classes('mr-2')
                                                ui.label('Chicago Paid Leave').classes('text-lg font-bold')
                                            with ui.column().classes('p-4 gap-3'):
                                                ui.label('Per Chicago ordinance (effective July 1, 2024):').classes('font-semibold')
                                                with ui.column().classes('pl-4 gap-2'):
                                                    ui.label('• Use for ANY reason - no justification needed').classes('text-sm')
                                                    ui.label('• Accrual: 1 hour for every 40 hours worked').classes('text-sm')
                                                    ui.label('• Up to 40 hours can be used per year').classes('text-sm')
                                                    ui.label('• Maximum 16 hours can be carried over to next year').classes('text-sm')
                                                ui.label('This is separate from your regular company PTO.').classes('text-sm opacity-70 mt-2')
                                                with ui.row().classes('w-full justify-end mt-2'):
                                                    ui.button('Got it', on_click=help_dialog.close).props('color=amber')
                                        help_dialog.open()

                                    with ui.card().classes('flex-1 p-4 border-l-4 border-amber-500 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 200px;').on('click', lambda: ui.navigate.to('/submit-request/chicago_leave')):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('schedule').classes('text-amber-600')
                                            ui.label('LEAVE').classes('text-lg font-bold text-amber-600')
                                            ui.button(icon='help_outline').on('click.stop', lambda: show_chicago_leave_help()).props('flat dense round size=xs').style('color: #f59e0b')

                                        # Show negative balance in red with warning
                                        if chicago_available < 0:
                                            display_text, tooltip_text = format_days_hours(chicago_available)
                                            ui.label(display_text).classes('text-2xl font-bold text-red-500 my-2').tooltip(tooltip_text)
                                            ui.label('OVERDRAWN').classes('text-sm text-red-500 font-medium')
                                        else:
                                            display_text, tooltip_text = format_days_hours(chicago_available)
                                            ui.label(display_text).classes('text-2xl font-bold text-amber-600 my-2').tooltip(tooltip_text)
                                            ui.label('AVAILABLE').classes('text-sm opacity-70')

                                        # Progress bar showing used/total
                                        chicago_used_ratio = min(chicago_used / chicago_total, 1.0) if chicago_total > 0 else 0
                                        with ui.column().classes('w-full mt-3 gap-1'):
                                            with ui.row().classes('w-full justify-between text-xs'):
                                                ui.label(f'{format_days(chicago_used)} used').classes('text-amber-600')
                                                ui.label(f'{format_days(chicago_total)} total').classes('opacity-60')
                                            ui.linear_progress(value=chicago_used_ratio, show_value=False).props('color=amber-5 track-color=grey-3').classes('w-full')
                                            if chicago_pending > 0:
                                                ui.label(f'{format_days(chicago_pending)} pending').classes('text-xs text-amber-500')
                                            # Show accrued vs carryover breakdown
                                            with ui.row().classes('w-full justify-between text-xs mt-1 opacity-50'):
                                                ui.label(f'{format_days(chicago_accrued)} accrued').tooltip('Hours accrued this year')
                                                if chicago_carryover > 0:
                                                    ui.label(f'+{format_days(chicago_carryover)} carryover').tooltip('Hours carried over from last year (max 16 hrs)')
                                            ui.label('40hrs (5 days) annual max • 16hr (2 days) carryover max').classes('text-xs opacity-50 mt-1')

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

                            # Get vacation carryover balance (from previous year's exception approval)
                            from src.services.pto_service import PTOService
                            vacation_carryover_available = PTOService.get_available_vacation_carryover(db, user_id, year)
                            vacation_carryover_hours = float(vacation_carryover_available)
                            vacation_carryover_days = vacation_carryover_hours / 8

                            # Include carryover in expansion title if available
                            carryover_label = f' + {vacation_carryover_days:.1f}d carryover' if vacation_carryover_days > 0 else ''
                            with ui.expansion(f'Other Leave Types ({total_other_used:.0f} days used{carryover_label})', icon='more_horiz').classes('w-full'):
                                ui.label(f'Non-accruing leave used in {year}').classes('text-xs opacity-60 mb-3')

                                # Show vacation carryover if available (from previous year exception)
                                if vacation_carryover_days > 0:
                                    previous_year = year - 1
                                    with ui.card().classes('w-full p-4 mb-4 border-l-4 border-amber-500'):
                                        with ui.row().classes('w-full items-center gap-3'):
                                            ui.icon('card_giftcard', size='lg').classes('text-amber-500')
                                            with ui.column().classes('flex-1'):
                                                ui.label(f'{previous_year} Vacation Carryover').classes('font-semibold text-amber-500')
                                                ui.label(f'{vacation_carryover_days:.1f} days ({vacation_carryover_hours:.0f} hours) available').classes('text-lg font-bold')
                                                ui.label(f'Exception approved - use by end of Q1 {year}').classes('text-xs opacity-60')
                                            ui.badge('BONUS', color='amber').props('outline')

                                # Colors match request_form.py for consistency
                                leave_info = {
                                    'bereavement': {'label': 'Bereavement', 'icon': 'sentiment_very_dissatisfied', 'hex': '#6366f1', 'policy': 'Immediate family: 5 days, Extended: 3 days'},
                                    'fmla': {'label': 'Family & Medical', 'icon': 'family_restroom', 'hex': '#0891b2', 'policy': 'FMLA: Up to 12 weeks unpaid, job-protected'},
                                    'jury_duty': {'label': 'Jury Duty', 'icon': 'gavel', 'hex': '#ec4899', 'policy': 'Paid time for jury service'},
                                    'voting': {'label': 'Voting Time', 'icon': 'how_to_vote', 'hex': '#0d9488', 'policy': 'Up to 2 hours if polls not open 4+ hrs outside work'},
                                    'military': {'label': 'Military Leave', 'icon': 'military_tech', 'hex': '#64748b', 'policy': 'Per USERRA requirements, job-protected'},
                                }

                                with ui.row().classes('w-full gap-2 items-stretch'):
                                    for leave_type, info in leave_info.items():
                                        days = other_leave_usage.get(leave_type, 0)
                                        hex_color = info['hex']
                                        # Capture leave_type for lambda closure
                                        nav_type = leave_type

                                        with ui.card().classes('p-3 flex-1 cursor-pointer hover:shadow-lg transition-shadow').style(f'border-left: 4px solid {hex_color}; min-width: 120px;').on('click', lambda e, t=nav_type: ui.navigate.to(f'/submit-request/{t}')):
                                            # Centered icon and title
                                            with ui.column().classes('items-center gap-1 w-full'):
                                                ui.icon(info['icon'], size='1.5rem').style(f'color: {hex_color};')
                                                ui.label(info['label']).classes('font-medium text-sm text-center').style(f'color: {hex_color};')

                                            # Days used (only show if > 0)
                                            if days > 0:
                                                ui.label(f'{int(days)}d').classes('text-lg font-bold text-center w-full mt-2').style(f'color: {hex_color};')

                                            # Policy description (directly under title/days)
                                            ui.label(info['policy']).classes('text-xs opacity-60 mt-2 text-center w-full')
                        else:
                            ui.label(f'No balance data for {year}').classes('opacity-70')

                # Initial render
                render_balances(current_year)

            # ============ QUICK ACTIONS (employees and managers only) ============
            if user_role not in ['admin', 'superadmin']:
                with ui.card().classes('w-full mb-4 p-4'):
                    # Row 1: My Time Off Actions
                    with ui.column().classes('w-full gap-3'):
                        def show_time_off_help():
                            with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                with ui.row().classes('w-full p-4 bg-primary text-white items-center'):
                                    ui.icon('schedule', size='md').classes('mr-2')
                                    ui.label('PTO TIME OFF').classes('text-lg font-bold')
                                with ui.column().classes('p-4 gap-3'):
                                    ui.label('Quick actions for managing your time off:').classes('font-semibold')
                                    with ui.column().classes('pl-4 gap-2'):
                                        ui.markdown('**Request/Submit Time Off** - Submit a new PTO request for vacation, sick, personal, or other leave types').classes('text-sm')
                                        ui.markdown('**My Requests/History** - View all your submitted requests and their current status (pending, approved, denied)').classes('text-sm')
                                        ui.markdown('**WFH Day Swap** - Request to swap your designated WFH day with a teammate (peer-to-peer, no manager approval needed)').classes('text-sm')
                                        ui.markdown('**Leave Rollover** - View year-end rollover status:').classes('text-sm')
                                        ui.markdown('&nbsp;&nbsp;• **Sick**: Auto-rolls over (up to 80 hrs) - no action needed').classes('text-xs opacity-80')
                                        ui.markdown('&nbsp;&nbsp;• **Vacation**: Use-it-or-lose-it (exception carryover with manager approval)').classes('text-xs opacity-80')
                                        ui.markdown('&nbsp;&nbsp;• **Personal**: Use-it-or-lose-it (no carryover)').classes('text-xs opacity-80')
                                        ui.markdown('&nbsp;&nbsp;• **Chicago Paid Leave**: Auto-rolls over (up to 16 hrs)').classes('text-xs opacity-80')
                                    with ui.row().classes('w-full justify-end mt-2'):
                                        ui.button('Got it', on_click=help_dialog.close).props('color=primary')
                            help_dialog.open()

                        with ui.row().classes('items-center gap-2'):
                            ui.label('PTO TIME OFF').classes('text-xs font-semibold uppercase opacity-60')
                            ui.button(icon='help_outline', on_click=show_time_off_help).props('flat dense round size=xs').style('color: #3b82f6')
                        with ui.row().classes('w-full gap-3 flex-wrap dashboard-actions'):
                            # Managers auto-approve, so show "Submit" instead of "Request"
                            time_off_label = 'Submit Time Off' if user_role == 'manager' else 'Request Time Off'
                            ui.button(time_off_label, icon='add_circle', on_click=lambda: ui.navigate.to('/submit-request')).props('outline color=primary').classes('flex-1 min-w-fit').tooltip('Submit a new time off request')
                            # For managers: "My Time Off History" shows their submitted time with color-coded view
                            # For employees: "My Requests" shows pending/approved requests
                            history_label = 'My Time Off History' if user_role == 'manager' else 'My Requests'
                            ui.button(history_label, icon='history', on_click=lambda: ui.navigate.to('/requests')).props('outline color=primary').classes('flex-1 min-w-fit').tooltip('View your submitted requests and their status')
                            # WFH Day Swap - peer-to-peer swap of WFH days
                            ui.button('WFH Day Swap', icon='swap_horiz', on_click=lambda: ui.navigate.to('/wfh-swap')).props('outline color=primary').classes('flex-1 min-w-fit').tooltip('Swap your WFH day with a teammate')
                            # Carryover Request only for employees (managers auto-approve, use Manager Tools > Carryover Approvals)
                            if user_role != 'manager':
                                ui.button('Leave Rollover', icon='move_down', on_click=lambda: ui.navigate.to('/carryover')).props('outline color=primary').classes('flex-1 min-w-fit').tooltip('View leave rollover status')

                    # Row 2: Resources (employees only - managers use Manager Tools)
                    if user_role != 'manager':
                        ui.separator().classes('my-2')
                        with ui.column().classes('w-full gap-3'):
                            def show_resources_help():
                                with ui.dialog() as help_dialog, ui.card().classes('p-0 max-w-md'):
                                    with ui.row().classes('w-full p-4 bg-secondary text-white items-center'):
                                        ui.icon('folder_open', size='md').classes('mr-2')
                                        ui.label('Resources').classes('text-lg font-bold')
                                    with ui.column().classes('p-4 gap-3'):
                                        ui.label('Helpful tools and information:').classes('font-semibold')
                                        with ui.column().classes('pl-4 gap-2'):
                                            ui.markdown('**My Profile** - View your profile information including hire date, department, and manager').classes('text-sm')
                                            ui.markdown('**Calendar** - View the team calendar showing holidays, your time off, and team schedules').classes('text-sm')
                                            ui.markdown('**Reports** - Generate reports on your PTO usage and balances').classes('text-sm')
                                            ui.markdown('**Handbook** - Access company policies, PTO guidelines, and leave information').classes('text-sm')
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button('Got it', on_click=help_dialog.close).props('color=secondary')
                                help_dialog.open()

                            with ui.row().classes('items-center gap-2'):
                                ui.label('Resources').classes('text-xs font-semibold uppercase opacity-60')
                                ui.button(icon='help_outline', on_click=show_resources_help).props('flat dense round size=xs').style('color: #6b7280')
                            with ui.row().classes('w-full gap-3 flex-wrap dashboard-actions'):
                                ui.button('My Profile', icon='person', on_click=lambda: show_user_profile_dialog(current_user, db)).props('outline color=secondary').classes('flex-1 min-w-fit').tooltip('View your profile and account information')
                                ui.button('Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline color=secondary').classes('flex-1 min-w-fit').tooltip('View team calendar with holidays and time off')
                                ui.button('Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=secondary').classes('flex-1 min-w-fit').tooltip('Generate reports on your PTO usage')
                                ui.button('Handbook', icon='menu_book', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=secondary').classes('flex-1 min-w-fit').tooltip('Access company policies and PTO guidelines')

                    # Row 3: Manager Tools (managers only)
                    if user_role == 'manager':
                        ui.separator().classes('my-2')
                        with ui.column().classes('w-full gap-3'):
                            ui.label('Manager Tools').classes('text-xs font-semibold uppercase opacity-60')
                            with ui.row().classes('w-full gap-3 flex-wrap dashboard-actions'):
                                ui.button('Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Manage Team', icon='badge', on_click=lambda: ui.navigate.to('/manager/team')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Carryover', icon='approval', on_click=lambda: ui.navigate.to('/manager/carryover')).props('outline color=indigo').classes('flex-1 min-w-fit')
                            with ui.row().classes('w-full gap-3 flex-wrap dashboard-actions'):
                                ui.button('Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Handbook', icon='menu_book', on_click=lambda: ui.navigate.to('/handbook')).props('outline color=indigo').classes('flex-1 min-w-fit')
                                ui.button('Settings', icon='settings', on_click=lambda: ui.navigate.to('/manager/settings')).props('outline color=indigo').classes('flex-1 min-w-fit')

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
                            ui.label('TEAM PTO REQUESTS').classes('text-lg font-semibold')
                        with ui.row().classes('items-center gap-2'):
                            if request_conflicts:
                                ui.badge(f'{len(request_conflicts)} conflicts', color='amber').props('outline').tooltip('Some requests have scheduling conflicts')
                            ui.badge(f'{len(team_pending_requests)} pending', color='indigo').props('outline')

                    # Type colors for border
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

                    # Helper function for inline approval
                    def create_inline_approve_handler(rid, emp_name, emp_email, pto_type, start_dt, end_dt, days_count, card_ref, btn_ref):
                        async def handle_approve():
                            btn_ref.props('loading')
                            btn_ref.disable()
                            approve_db = None
                            try:
                                approve_db = next(get_db())
                                current_user = app.storage.user.get('user')
                                user_id = current_user.get('id')
                                approver_name = f"{current_user.get('first_name')} {current_user.get('last_name')}"

                                if PTOService.approve_request(approve_db, rid, user_id):
                                    # Log the approval
                                    AuditService.log_pto_approve(
                                        approve_db, user_id, approver_name, rid, emp_name
                                    )
                                    # Send email notification
                                    email_service.send_pto_approved(
                                        emp_email, emp_name, pto_type,
                                        start_dt, end_dt, float(days_count), approver_name
                                    )
                                    # Remove the card with animation
                                    card_ref.style('opacity: 0; transform: translateX(-20px); transition: all 0.3s;')
                                    await ui.run_javascript('await new Promise(r => setTimeout(r, 300))')
                                    card_ref.delete()
                                    ui.notify(f'Approved {emp_name}\'s request', type='positive')
                                else:
                                    btn_ref.props(remove='loading')
                                    btn_ref.enable()
                                    ui.notify('Failed to approve request', type='negative')
                            except Exception as ex:
                                btn_ref.props(remove='loading')
                                btn_ref.enable()
                                ui.notify(f'Error: {str(ex)}', type='negative')
                            finally:
                                if approve_db:
                                    approve_db.close()
                        return handle_approve

                    for req in team_pending_requests[:5]:  # Show first 5
                        pto_type_lower = req['pto_type'].lower()
                        border_color = type_colors.get(pto_type_lower, 'gray')
                        has_conflict = req['request_id'] in request_conflicts
                        request_id = req['request_id']

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-lg').on('click', lambda e, rid=request_id: ui.navigate.to(f'/manager/request/{rid}')) as req_card:
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-3 items-center flex-1'):
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
                                            ui.label(get_pto_display_name(req['pto_type'])).classes('text-sm opacity-70')
                                            ui.label('•').classes('text-xs opacity-50')
                                            if req['start_date'] == req['end_date']:
                                                ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                            else:
                                                ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

                                with ui.row().classes('gap-3 items-center'):
                                    days = float(req['total_days'])
                                    ui.label(format_days(days * 8)).classes('font-medium')
                                    # Approve button - click.stop prevents row navigation
                                    approve_btn = ui.button('Approve', icon='check').props('dense color=positive size=sm').classes('ml-2')
                                    approve_btn.on('click.stop', create_inline_approve_handler(
                                        request_id, req['employee_name'], req.get('employee_email', ''),
                                        req['pto_type'], req['start_date'], req['end_date'],
                                        req['total_days'], req_card, approve_btn
                                    ))

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
                        request_id = req['request_id']

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-lg').on('click', lambda e, rid=request_id: ui.navigate.to(f'/manager/request/{rid}')):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-3 items-center'):
                                    ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                    with ui.column().classes('gap-0'):
                                        ui.label(req['employee_name']).classes('font-medium')
                                        with ui.row().classes('gap-2 items-center'):
                                            ui.label(get_pto_display_name(req['pto_type'])).classes('text-sm opacity-70')
                                            ui.label('•').classes('text-xs opacity-50')
                                            if req['start_date'] == req['end_date']:
                                                ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                            else:
                                                ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')
                                        if req.get('cancellation_reason'):
                                            ui.label(f"Reason: {req['cancellation_reason']}").classes('text-xs opacity-60 italic')

                                days = float(req['total_days'])
                                ui.label(format_days(days * 8)).classes('font-medium')

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
                                    ui.label('PTO TEAM HISTORY').classes('text-lg font-semibold')
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

            # ============ PENDING REQUESTS (if any) - employees only ============
            if pending_requests and user_role not in ['manager', 'admin', 'superadmin']:
                # Type colors for border
                pending_type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                pending_type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

                with ui.card().classes('w-full mb-4 border-l-4 border-amber-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('pending', color='amber').classes('text-xl')
                            ui.label('Pending Requests').classes('text-lg font-semibold')
                        ui.label(f'{len(pending_requests)} awaiting approval').classes('text-sm text-amber-500')

                    for req in pending_requests:
                        pto_type_lower = req.pto_type.lower()
                        border_color = pending_type_colors.get(pto_type_lower, 'gray')
                        type_icon = pending_type_icons.get(pto_type_lower, 'event')

                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-md').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('gap-3 items-center'):
                                    ui.icon(type_icon).classes(f'text-{border_color}-500')
                                    with ui.column().classes('gap-0'):
                                        with ui.row().classes('gap-2 items-center'):
                                            # Show "Vacation Rollover" for rollover requests
                                            is_rollover = hasattr(req, 'carryover_from_year') and req.carryover_from_year and pto_type_lower == 'vacation'
                                            display_label = 'Vacation Rollover' if is_rollover else get_pto_display_name(req.pto_type)
                                            ui.label(display_label).classes('font-medium')
                                            ui.badge('Pending', color='amber').props('outline')
                                        if req.start_date == req.end_date:
                                            ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                        else:
                                            ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

                                with ui.row().classes('items-center gap-2'):
                                    days_display = float(req.total_days)
                                    ui.label(format_days(days_display * 8)).classes('font-medium')

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

            # ============ RECENT APPROVED REQUESTS (not for admin/superadmin) ============
            if user_role not in ['admin', 'superadmin']:
              with ui.card().classes('w-full mb-4'):
                # View state for My/Team toggle (managers only)
                view_state = {'mode': 'my'}  # 'my' or 'team'
                view_buttons = {}

                with ui.row().classes('w-full justify-between items-center mb-3'):
                    ui.label('PTO REQUESTS APPROVED').classes('text-lg font-semibold')
                    with ui.row().classes('gap-2 items-center'):
                        # My/Team toggle for managers
                        if user_role == 'manager' and team_approved_requests is not None:
                            def update_view(mode: str):
                                view_state['mode'] = mode
                                # Update button styles
                                for btn_mode, btn in view_buttons.items():
                                    if btn_mode == mode:
                                        btn.style('color: #C9A227 !important; border-color: #C9A227 !important; border-width: 2px !important;')
                                    else:
                                        btn.style('color: rgba(255,255,255,0.7) !important; border-color: rgba(255,255,255,0.3) !important; border-width: 1px !important;')
                                # Re-render the list
                                render_filtered_requests()

                            view_buttons['my'] = ui.button('My', icon='person', on_click=lambda: update_view('my')).props('dense outline size=sm').style('color: #C9A227 !important; border-color: #C9A227 !important; border-width: 2px !important;')
                            view_buttons['team'] = ui.button('Team', icon='group', on_click=lambda: update_view('team')).props('dense outline size=sm').style('color: rgba(255,255,255,0.7) !important; border-color: rgba(255,255,255,0.3) !important; border-width: 1px !important;')

                        count_label = ui.label(f'{len(recent_requests)} requests').classes('text-xs opacity-50')

                if recent_requests or team_approved_requests:
                    # Hex colors for inline styling (icon + text)
                    type_hex_colors = {
                        'all': '#C9A227',  # Brand Gold
                        'vacation': '#3b82f6',  # Blue
                        'sick': '#22c55e',  # Green
                        'personal': '#a855f7',  # Purple
                        'work_from_home': '#ef4444',  # Red
                        'chicago_leave': '#f59e0b',  # Amber
                        'other': '#6b7280'  # Grey
                    }
                    # Tailwind color names for border classes
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red', 'chicago_leave': 'amber', 'leave': 'amber'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work', 'chicago_leave': 'event_available', 'leave': 'event_available'}

                    # Filter state
                    filter_state = {'type': 'all'}
                    filter_buttons = {}
                    button_colors = {}  # Store original colors for each button

                    def update_filter(new_type: str):
                        filter_state['type'] = new_type
                        # Update button styles - selected gets gold border, others get outline with their color
                        for btn_type, btn in filter_buttons.items():
                            btn_color = button_colors.get(btn_type, '#6b7280')
                            if btn_type == new_type:
                                # Selected: gold border, colored text
                                btn.style(f'color: {btn_color} !important; border-color: #C9A227 !important; border-width: 2px !important;')
                            else:
                                # Unselected: subtle border, colored text
                                btn.style(f'color: {btn_color} !important; border-color: rgba(255,255,255,0.3) !important; border-width: 1px !important;')
                        # Refresh the list
                        render_filtered_requests()

                    # Check if Chicago employee for Leave filter
                    is_chicago = current_user and current_user.location_city and current_user.location_city.lower() == 'chicago'

                    # Filter toggle buttons with icons and colors
                    with ui.row().classes('w-full gap-2 mb-3 flex-wrap'):
                        # All button - starts selected with gold border
                        button_colors['all'] = type_hex_colors['all']
                        filter_buttons['all'] = ui.button('All', icon='list', on_click=lambda: update_filter('all')).props('dense outline size=sm').style(f'color: {type_hex_colors["all"]} !important; border-color: #C9A227 !important; border-width: 2px !important;')

                        # Vacation
                        button_colors['vacation'] = type_hex_colors['vacation']
                        filter_buttons['vacation'] = ui.button('Vacation', icon='beach_access', on_click=lambda: update_filter('vacation')).props('dense outline size=sm').style(f'color: {type_hex_colors["vacation"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                        # Sick
                        button_colors['sick'] = type_hex_colors['sick']
                        filter_buttons['sick'] = ui.button('Sick', icon='medical_services', on_click=lambda: update_filter('sick')).props('dense outline size=sm').style(f'color: {type_hex_colors["sick"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                        # Personal
                        button_colors['personal'] = type_hex_colors['personal']
                        filter_buttons['personal'] = ui.button('Personal', icon='person', on_click=lambda: update_filter('personal')).props('dense outline size=sm').style(f'color: {type_hex_colors["personal"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                        # Leave filter for Chicago employees - always show if Chicago
                        if is_chicago:
                            button_colors['chicago_leave'] = type_hex_colors['chicago_leave']
                            filter_buttons['chicago_leave'] = ui.button('Leave', icon='event_available', on_click=lambda: update_filter('chicago_leave')).props('dense outline size=sm').style(f'color: {type_hex_colors["chicago_leave"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                        # WFH filter - always show
                        button_colors['work_from_home'] = type_hex_colors['work_from_home']
                        filter_buttons['work_from_home'] = ui.button('WFH', icon='home_work', on_click=lambda: update_filter('work_from_home')).props('dense outline size=sm').style(f'color: {type_hex_colors["work_from_home"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                        # Other types (bereavement, fmla, etc.)
                        other_types = [r for r in recent_requests if r.pto_type.lower() not in ['vacation', 'sick', 'personal', 'work_from_home', 'chicago_leave', 'leave']]
                        if other_types:
                            button_colors['other'] = type_hex_colors['other']
                            filter_buttons['other'] = ui.button('Other', icon='more_horiz', on_click=lambda: update_filter('other')).props('dense outline size=sm').style(f'color: {type_hex_colors["other"]} !important; border-color: rgba(255,255,255,0.3) !important;')

                    # Container for filtered results
                    results_container = ui.column().classes('w-full')

                    def render_filtered_requests():
                        results_container.clear()
                        with results_container:
                            # Select base list based on view mode (my vs team)
                            is_team_view = view_state['mode'] == 'team'
                            base_requests = team_approved_requests if is_team_view else recent_requests

                            # Filter requests based on selected type
                            if filter_state['type'] == 'all':
                                filtered = base_requests
                            elif filter_state['type'] == 'other':
                                filtered = [r for r in base_requests if r.pto_type.lower() not in ['vacation', 'sick', 'personal', 'work_from_home', 'chicago_leave', 'leave']]
                            elif filter_state['type'] == 'chicago_leave':
                                # Match both 'chicago_leave' and 'leave' types
                                filtered = [r for r in base_requests if r.pto_type.lower() in ['chicago_leave', 'leave']]
                            else:
                                filtered = [r for r in base_requests if r.pto_type.lower() == filter_state['type']]

                            # Update count label
                            count_label.set_text(f'{len(filtered)} requests')

                            if filtered:
                                with ui.scroll_area().classes('w-full').style('max-height: 300px'):
                                    for req in filtered:
                                        pto_type_lower = req.pto_type.lower()
                                        border_color = type_colors.get(pto_type_lower, 'gray')

                                        with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-md').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                                            with ui.row().classes('w-full justify-between items-center'):
                                                with ui.row().classes('gap-4 items-center'):
                                                    ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                                    with ui.column().classes('gap-0'):
                                                        # Determine type label - add (CarryOver) for vacation using previous year
                                                        has_carryover = hasattr(req, 'carryover_from_year') and req.carryover_from_year
                                                        display_name = get_pto_display_name(req.pto_type)
                                                        type_label = f"{display_name} (CarryOver)" if has_carryover and pto_type_lower == 'vacation' else display_name
                                                        # Show employee name in team view
                                                        if is_team_view and hasattr(req, 'employee_name'):
                                                            ui.label(req.employee_name).classes('font-medium')
                                                            ui.label(type_label).classes('text-xs opacity-70 text-amber-500' if has_carryover else 'text-xs opacity-70')
                                                        else:
                                                            ui.label(type_label).classes('font-medium text-amber-500' if has_carryover else 'font-medium')
                                                        if req.start_date == req.end_date:
                                                            ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-xs opacity-60')
                                                        else:
                                                            ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-xs opacity-60')
                                                with ui.row().classes('gap-3 items-center'):
                                                    days_display = float(req.total_days)
                                                    ui.label(format_days(days_display * 8)).classes('text-sm')
                                                    # Show carryover indicator if vacation used previous year's balance
                                                    if hasattr(req, 'carryover_from_year') and req.carryover_from_year:
                                                        ui.badge(f'{req.carryover_from_year}', color='amber').props('outline dense').tooltip(f'Uses {req.carryover_from_year} vacation balance')
                                                    ui.icon('chevron_right').classes('text-gray-400')
                            else:
                                with ui.row().classes('w-full justify-center py-6'):
                                    view_text = 'team' if is_team_view else ''
                                    ui.label(f'No {view_text} {filter_state["type"]} time off').classes('opacity-60')

                    # Initial render
                    render_filtered_requests()
                else:
                    with ui.row().classes('w-full justify-center py-6'):
                        ui.label('No approved time off yet').classes('opacity-60')

            # ============ INCOMING WFH SWAP REQUESTS (if any) ============
            if pending_wfh_swaps:
                with ui.card().classes('w-full mb-4 border-l-4 border-orange-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('swap_horiz', color='orange').classes('text-xl')
                            ui.label('WFH SWAP REQUESTS').classes('text-lg font-semibold')
                        with ui.row().classes('items-center gap-2'):
                            ui.label(f'{len(pending_wfh_swaps)} awaiting response').classes('text-sm text-orange-500')
                            ui.button('View All', icon='open_in_new', on_click=lambda: ui.navigate.to('/wfh-swap')).props('flat dense size=sm')

                    for swap_req in pending_wfh_swaps:
                        requester = user_service.get_user_by_id(swap_req.requester_id)
                        requester_name = f"{requester.first_name} {requester.last_name}" if requester else "Unknown"

                        with ui.card().classes('w-full p-3 mb-2 border-l-4 border-orange-400').style('background-color: #374151;'):
                            with ui.row().classes('w-full justify-between items-start gap-4'):
                                # Left: Request info
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('person', size='sm').style('color: #f97316;')
                                        ui.label(requester_name).classes('font-semibold')
                                        ui.badge('Swap Request', color='orange').props('outline')
                                    ui.label(f'Wants to swap for {swap_req.swap_date.strftime("%A, %B %d")}').classes('text-sm opacity-80')
                                    if swap_req.request_message:
                                        with ui.row().classes('items-start gap-1 mt-1'):
                                            ui.icon('format_quote', size='xs').classes('opacity-50')
                                            ui.label(f'"{swap_req.request_message}"').classes('text-sm italic opacity-70')

                                # Right: Response input and buttons in column
                                with ui.column().classes('gap-2'):
                                    response_input = ui.input(placeholder='Response...').props('dense outlined').style('min-width: 280px;')

                                    def create_accept_handler(req, resp_input):
                                        def accept_swap():
                                            if not resp_input.value or not resp_input.value.strip():
                                                ui.notify('Please enter a response message', type='warning')
                                                return
                                            try:
                                                swap_service.accept_swap(req.id, user_id, resp_input.value.strip())
                                                ui.notify('Swap accepted!', type='positive')
                                                ui.run_javascript('window.location.reload()')  # Force refresh
                                            except Exception as e:
                                                ui.notify(f'Error: {str(e)}', type='negative')
                                        return accept_swap

                                    def create_decline_handler(req, resp_input):
                                        def decline_swap():
                                            if not resp_input.value or not resp_input.value.strip():
                                                ui.notify('Please enter a response message', type='warning')
                                                return
                                            try:
                                                swap_service.decline_swap(req.id, user_id, resp_input.value.strip())
                                                ui.notify('Swap declined', type='info')
                                                ui.run_javascript('window.location.reload()')  # Force refresh
                                            except Exception as e:
                                                ui.notify(f'Error: {str(e)}', type='negative')
                                        return decline_swap

                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button('Accept', icon='check', on_click=create_accept_handler(swap_req, response_input)).props('color=positive dense size=sm')
                                        ui.button('Decline', icon='close', on_click=create_decline_handler(swap_req, response_input)).props('color=negative dense size=sm')

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
                        ui.badge('Admin', color='green').props('rounded')

                    # Get stats
                    all_users = user_service.get_all_users()
                    all_departments = DepartmentService.get_all_departments(db)
                    active_users = [u for u in all_users if u.is_active]

                    # Get PTO this week count using direct query
                    from src.models.pto_request import PTORequest
                    today = date.today()
                    week_start = today - timedelta(days=today.weekday())
                    week_end = week_start + timedelta(days=6)
                    pto_this_week = db.query(PTORequest).filter(
                        PTORequest.status == 'approved',
                        PTORequest.start_date <= week_end,
                        PTORequest.end_date >= week_start
                    ).all()
                    pto_this_week_count = len(set(r.user_id for r in pto_this_week)) if pto_this_week else 0

                    with ui.row().classes('w-full gap-4 justify-center'):
                        # Total Employees - with gradient icon
                        with ui.card().classes('flex-1 p-4 border-l-4 border-blue-500 admin-stat-card'):
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #3b82f6, #1d4ed8);'):
                                    ui.icon('people', color='white').classes('text-xl')
                                with ui.column().classes('gap-0'):
                                    ui.label(str(len(active_users))).classes('text-3xl font-bold')
                                    ui.label('Active Employees').classes('text-xs opacity-60')
                            ui.tooltip('Total active user accounts in the system')

                        # Total Departments - with gradient icon
                        with ui.card().classes('flex-1 p-4 border-l-4 border-purple-500 admin-stat-card'):
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #8b5cf6, #6d28d9);'):
                                    ui.icon('business', color='white').classes('text-xl')
                                with ui.column().classes('gap-0'):
                                    ui.label(str(len(all_departments))).classes('text-3xl font-bold')
                                    ui.label('Departments').classes('text-xs opacity-60')
                            ui.tooltip('Organizational departments')

                        # Pending Requests - with gradient icon (clickable) + pulse when > 0
                        pending_card_classes = 'flex-1 p-4 border-l-4 border-amber-500 cursor-pointer admin-stat-card'
                        if pending_count > 0:
                            pending_card_classes += ' pulse-pending'
                        with ui.card().classes(pending_card_classes).on('click', lambda: ui.navigate.to('/admin/approvals') if pending_count > 0 else None):
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #f59e0b, #d97706);'):
                                    ui.icon('pending_actions', color='white').classes('text-xl')
                                with ui.column().classes('gap-0'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(str(pending_count)).classes('text-3xl font-bold')
                                        if pending_count > 0:
                                            ui.badge('Action', color='amber').props('dense')
                                    ui.label('Pending Requests').classes('text-xs opacity-60')
                            ui.tooltip('Click to review pending PTO requests' if pending_count > 0 else 'No pending requests')

                        # PTO This Week - stat card with gradient icon
                        with ui.card().classes('flex-1 p-4 border-l-4 border-green-500 admin-stat-card'):
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #22c55e, #16a34a);'):
                                    ui.icon('event_busy', color='white').classes('text-xl')
                                with ui.column().classes('gap-0'):
                                    ui.label(str(pto_this_week_count)).classes('text-3xl font-bold')
                                    ui.label('Out This Week').classes('text-xs opacity-60')
                            ui.tooltip('Employees with approved PTO this week')

                # ============ QUICK INSIGHTS PANEL ============
                with ui.row().classes('w-full gap-4 mb-4'):
                    # Upcoming Time Off card - fixed height with scroll
                    with ui.card().classes('flex-1 p-4').style('height: 220px;'):
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('calendar_today', color='primary').classes('text-lg')
                            ui.label('Upcoming Time Off').classes('font-semibold')

                        # Get upcoming PTO (next 14 days, more items for scrolling)
                        upcoming_end = week_end + timedelta(days=14)
                        upcoming_pto = db.query(PTORequest).filter(
                            PTORequest.status == 'approved',
                            PTORequest.start_date <= upcoming_end,
                            PTORequest.start_date >= today
                        ).order_by(PTORequest.start_date).limit(10).all()

                        if upcoming_pto:
                            type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                            with ui.scroll_area().classes('w-full').style('height: 140px;'):
                                for req in upcoming_pto:
                                    user_obj = user_service.get_user_by_id(req.user_id)
                                    if user_obj:
                                        pto_color = type_colors.get(req.pto_type.lower(), 'gray')
                                        with ui.row().classes('w-full items-center gap-3 py-2 border-b border-gray-700 last:border-0'):
                                            with ui.element('div').classes(f'w-8 h-8 rounded-full flex items-center justify-center bg-{pto_color}-500/20'):
                                                ui.label(user_obj.first_name[0]).classes(f'font-bold text-{pto_color}-500')
                                            with ui.column().classes('gap-0 flex-1'):
                                                ui.label(f'{user_obj.first_name} {user_obj.last_name}').classes('font-medium text-sm')
                                                ui.label(f"{get_pto_display_name(req.pto_type)} • {req.start_date.strftime('%b %d')}").classes('text-xs opacity-60')
                        else:
                            with ui.column().classes('w-full items-center py-4 opacity-50'):
                                ui.icon('event_available', size='xl')
                                ui.label('No upcoming time off').classes('text-sm')

                    # Department PTO Usage card - same fixed height
                    with ui.card().classes('flex-1 p-4').style('height: 220px;'):
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('bar_chart', color='secondary').classes('text-lg')
                            ui.label('Department PTO Usage').classes('font-semibold')

                        # Calculate department usage
                        from src.models.pto_balance import PTOBalance
                        dept_usage = []
                        for dept in all_departments:
                            dept_users = [u for u in active_users if u.department_id == dept.id]
                            if dept_users:
                                total_allocated = 0
                                total_used = 0
                                for u in dept_users:
                                    bal = db.query(PTOBalance).filter(
                                        PTOBalance.user_id == u.id,
                                        PTOBalance.year == current_year
                                    ).first()
                                    if bal:
                                        total_allocated += float(bal.vacation_total or 0)
                                        total_used += float(bal.vacation_used or 0)
                                if total_allocated > 0:
                                    usage_pct = min(100, int((total_used / total_allocated) * 100))
                                    dept_usage.append({'name': dept.name, 'pct': usage_pct})

                        if dept_usage:
                            colors = ['blue', 'green', 'purple', 'amber']
                            with ui.column().classes('w-full gap-3'):
                                for i, dept in enumerate(dept_usage[:4]):
                                    color = colors[i % len(colors)]
                                    with ui.column().classes('w-full gap-1'):
                                        with ui.row().classes('w-full justify-between'):
                                            ui.label(dept['name']).classes('text-sm')
                                            ui.label(f"{dept['pct']}%").classes('text-sm font-medium')
                                        with ui.element('div').classes('w-full h-2 rounded-full bg-gray-700'):
                                            ui.element('div').classes(f'h-2 rounded-full bg-{color}-500').style(f"width: {dept['pct']}%")
                            ui.label('% of vacation PTO used this year').classes('text-xs opacity-40 mt-auto')
                        else:
                            with ui.column().classes('w-full items-center py-4 opacity-50'):
                                ui.icon('trending_up', size='xl')
                                ui.label('No usage data').classes('text-sm')

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
                            request_id = req['request_id']

                            with ui.card().classes(f'w-full p-3 mb-2 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-lg').on('click', lambda e, rid=request_id: ui.navigate.to(f'/manager/request/{rid}')):
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
                                                ui.label(get_pto_display_name(req['pto_type'])).classes('text-sm opacity-70')
                                                ui.label('•').classes('text-xs opacity-50')
                                                if req['start_date'] == req['end_date']:
                                                    ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

                                    days = float(req['total_days'])
                                    ui.label(format_days(days * 8)).classes('font-medium')

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
                    # Management section with icon
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('settings', size='sm').classes('opacity-60')
                        ui.label('Management').classes('text-xs font-semibold uppercase opacity-60')
                    with ui.row().classes('w-full gap-3'):
                        ui.button('Add Employee', icon='person_add',
                                  on_click=lambda: ui.navigate.to('/admin/employees/add')).props('outline color=indigo').classes('flex-1 admin-btn')
                        ui.button('Manage Employees', icon='people',
                                  on_click=lambda: ui.navigate.to('/admin/employees')).props('outline color=indigo').classes('flex-1 admin-btn')
                        ui.button('Manage Departments', icon='business',
                                  on_click=lambda: ui.navigate.to('/admin/departments')).props('outline color=indigo').classes('flex-1 admin-btn')

                    ui.separator().classes('my-3')

                    # Approvals section with icon
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('task_alt', size='sm').classes('opacity-60')
                        ui.label('Approvals').classes('text-xs font-semibold uppercase opacity-60')
                    with ui.row().classes('w-full gap-3'):
                        ui.button('PTO Approvals', icon='pending_actions',
                                  on_click=lambda: ui.navigate.to('/admin/approvals')).props('outline color=purple').classes('flex-1 admin-btn')
                        ui.button('Carryover Approvals', icon='move_down',
                                  on_click=lambda: ui.navigate.to('/manager/carryover')).props('outline color=purple').classes('flex-1 admin-btn')

                    ui.separator().classes('my-3')

                    # Resources section with icon - 2 buttons per row edge to edge
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('folder_open', size='sm').classes('opacity-60')
                        ui.label('Resources').classes('text-xs font-semibold uppercase opacity-60')
                    with ui.row().classes('w-full gap-3'):
                        ui.button('Calendar', icon='calendar_month',
                                  on_click=lambda: ui.navigate.to('/calendar')).props('outline color=secondary').classes('flex-1 admin-btn')
                        ui.button('Reports', icon='assessment',
                                  on_click=lambda: ui.navigate.to('/reports')).props('outline color=secondary').classes('flex-1 admin-btn')

                    # System section - superadmin only
                    if user_role == 'superadmin':
                        ui.separator().classes('my-3')

                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('settings_applications', size='sm').classes('opacity-60')
                            ui.label('System').classes('text-xs font-semibold uppercase opacity-60')
                        with ui.row().classes('w-full gap-3'):
                            ui.button('System Admin', icon='settings_applications',
                                      on_click=lambda: ui.navigate.to('/admin/system')).props('outline color=amber').classes('flex-1 admin-btn')

            # ============ ACCEPTED WFH SWAPS (show user's accepted swaps) ============
            # Get accepted swaps where user is either requester or target
            from sqlalchemy import or_
            from src.models.wfh_day_swap import WFHDaySwapRequest
            accepted_swaps_stmt = select(WFHDaySwapRequest).where(
                or_(
                    WFHDaySwapRequest.requester_id == user_id,
                    WFHDaySwapRequest.target_user_id == user_id
                ),
                WFHDaySwapRequest.status == 'accepted'
            ).order_by(WFHDaySwapRequest.swap_date.asc())
            accepted_swaps = list(db.execute(accepted_swaps_stmt).scalars().all())

            if accepted_swaps:
                with ui.card().classes('w-full mb-4 border-l-4 border-green-500'):
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('check_circle', color='green').classes('text-xl')
                            ui.label('WFH SWAP APPROVED').classes('text-lg font-semibold')
                        ui.button('View All', icon='open_in_new', on_click=lambda: ui.navigate.to('/wfh-swap')).props('flat dense size=sm')

                    for swap in accepted_swaps:
                        is_requester = swap.requester_id == user_id
                        if is_requester:
                            other = user_service.get_user_by_id(swap.target_user_id)
                            direction = "with"
                        else:
                            other = user_service.get_user_by_id(swap.requester_id)
                            direction = "from"
                        other_name = f"{other.first_name} {other.last_name}" if other else "Unknown"

                        with ui.card().classes('w-full p-3 mb-2 border-l-4 border-green-400').style('background-color: #374151;'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('swap_horiz', size='sm').style('color: #22c55e;')
                                        ui.label(f'Swap {direction} {other_name}').classes('font-semibold')
                                        ui.badge('Accepted', color='green').props('outline')
                                    ui.label(f'{swap.swap_date.strftime("%A, %B %d")}').classes('text-sm opacity-80')
                                # Show the original days info
                                with ui.column().classes('text-right'):
                                    ui.label(f'Your WFH: {swap.requester_original_day.title() if is_requester else swap.target_original_day.title()}').classes('text-xs opacity-60')
                                    ui.label(f'Swapped to: {swap.target_original_day.title() if is_requester else swap.requester_original_day.title()}').classes('text-xs text-green-400')

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

        # ============ REAL-TIME UPDATES ============
        # Set up automatic refresh when PTO request statuses change (30 second interval)
        setup_dashboard_updates(db, user_id, user_role, interval=30.0)

    finally:
        if db:
            db.close()


def logout():
    """Clear user session and redirect to home."""
    app.storage.user.pop('user', None)
    ui.navigate.to('/')


def cancel_request(request_id: int):
    """Cancel a pending PTO request."""
    db = None
    try:
        db = next(get_db())
        from src.services.pto_service import PTOService

        current_user = app.storage.user.get('user', {})
        user_id = current_user.get('id')

        # Use PTOService.cancel_request which handles ALL PTO types correctly
        pto_service = PTOService(db)

        # Get employee name for audit log before cancelling
        request = pto_service.get_request_by_id(request_id)
        if not request:
            show_error_dialog('Not Found', 'The request you are looking for was not found.')
            return
        employee_name = request.user.full_name if request.user else 'Unknown'

        # Cancel via service (handles balance restoration for ALL PTO types)
        pto_service.cancel_request(request_id, user_id)

        # Audit log the cancellation
        AuditService.log_pto_cancel(
            db=db,
            user_id=user_id,
            username=current_user.get('username'),
            request_id=request_id,
            employee_name=employee_name,
            cancelled_by_self=True
        )

        show_success_dialog('Success', 'Request cancelled successfully', on_close=lambda: ui.navigate.to('/dashboard'))

    except ValueError as e:
        # PTOService raises ValueError for validation errors
        show_warning_dialog('Cannot Cancel', str(e))
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
            # Header - using brand gray for better readability
            with ui.row().classes('w-full justify-between items-center p-4 text-white').style('background-color: #5a6a72;'):
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
                            ui.label('PTO SUMMARY').classes('text-lg font-semibold')

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
                                    with ui.row().classes('w-full justify-center items-center gap-2 mb-2'):
                                        ui.icon('beach_access', size='md').style('color: #3b82f6')
                                        ui.label('Vacation').classes('text-base font-bold text-blue-600')
                                    ui.label(f'{format_days(float(balance.vacation_used))}').classes('text-2xl font-bold text-blue-600')
                                    ui.label('days used').classes('text-xs opacity-60')
                                    total = float(balance.vacation_total) + float(balance.vacation_carryover)
                                    ui.label(f'of {format_days(total)} total').classes('text-xs opacity-40')

                                # Sick
                                with ui.card().classes('flex-1 min-w-32 p-3 border-l-4 border-green-500 text-center'):
                                    with ui.row().classes('w-full justify-center items-center gap-2 mb-2'):
                                        ui.icon('local_hospital', size='md').style('color: #22c55e')
                                        ui.label('Sick').classes('text-base font-bold text-green-600')
                                    ui.label(f'{format_days(float(balance.sick_used))}').classes('text-2xl font-bold text-green-600')
                                    ui.label('days used').classes('text-xs opacity-60')
                                    total = float(balance.sick_total) + float(balance.sick_carryover)
                                    ui.label(f'of {format_days(total)} total').classes('text-xs opacity-40')

                                # Personal
                                with ui.card().classes('flex-1 min-w-32 p-3 border-l-4 border-purple-500 text-center'):
                                    with ui.row().classes('w-full justify-center items-center gap-2 mb-2'):
                                        ui.icon('person', size='md').style('color: #a855f7')
                                        ui.label('Personal').classes('text-base font-bold text-purple-600')
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

                                # Use lambda with default arg to capture req value properly
                                with ui.card().classes(f'w-full p-3 border-l-4 border-{border_color}-500 cursor-pointer hover:shadow-md').on('click', lambda e, r=req: show_pto_detail_dialog(r)):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        with ui.row().classes('gap-3 items-center'):
                                            ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500')
                                            with ui.column().classes('gap-0'):
                                                with ui.row().classes('gap-2 items-center'):
                                                    ui.label(get_pto_display_name(req.pto_type)).classes('font-medium')
                                                    ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey')).props('dense')

                                                if req.start_date == req.end_date:
                                                    ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req.start_date.strftime('%A, %B %d')} - {req.end_date.strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')

                                        with ui.row().classes('gap-2 items-center'):
                                            days = float(req.total_days)
                                            ui.label(format_days(days * 8)).classes('font-medium')
                                            ui.icon('chevron_right').classes('text-gray-400')
                        else:
                            with ui.row().classes('w-full justify-center py-8'):
                                with ui.column().classes('items-center gap-2'):
                                    ui.icon('event_busy', color='grey').classes('text-4xl')
                                    filter_text = f' {filter_type}' if filter_type != 'all' else ''
                                    ui.label(f'No{filter_text} time off records for {selected_year}').classes('opacity-60')

            # Open dialog first, then use timer to render after DOM is ready
            history_dialog.open()
            # Small delay ensures dialog is fully in DOM before adding clickable content
            ui.timer(0.05, render_content, once=True)

    except Exception as e:
        show_error_dialog('Error', f'Error loading employee history: {str(e)}')
    finally:
        if db:
            db.close()


def show_pto_detail_dialog(request_or_id):
    """Show detailed information about a PTO request with action buttons.

    Args:
        request_or_id: Either a PTORequest object or a request ID (int).
                       Will fetch fresh from DB to ensure relationships are loaded.
    """
    from src.models.pto_request import PTORequest

    type_colors = {
        'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
        'bereavement': 'brown', 'fmla': 'teal', 'jury_duty': 'indigo',
        'voting': 'cyan', 'military': 'deep-orange', 'work_from_home': 'red',
        'chicago_leave': 'orange', 'leave': 'orange'
    }
    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

    # Get current user info for action button permissions
    current_user = app.storage.user.get('user', {})
    user_id = current_user.get('id')
    user_role = current_user.get('role', 'employee')
    is_trusted = current_user.get('is_trusted', False)

    # Always fetch fresh to ensure we have an active session with loaded relationships
    db = next(get_db())
    try:
        if isinstance(request_or_id, int):
            request = db.query(PTORequest).filter(PTORequest.id == request_or_id).first()
        else:
            request = db.query(PTORequest).filter(PTORequest.id == request_or_id.id).first()

        if not request:
            show_error_dialog('Error', 'Request not found')
            return

        # Extract ALL data from ORM object into plain variables before closing session
        req_id = request.id
        req_type = request.pto_type
        req_type_lower = request.pto_type.lower()
        req_total_days = float(request.total_days)
        req_start_date = request.start_date
        req_end_date = request.end_date
        req_year = request.start_date.year
        req_user_id = request.user_id
        req_status = request.status
        req_notes = request.notes
        req_denial_reason = request.denial_reason
        req_approved_at = request.approved_at
        req_cancellation_requested = getattr(request, 'cancellation_requested', False)
        req_employee_name = request.user.full_name if request.user else 'Unknown'
        req_created_at = request.created_at
        req_carryover_from_year = getattr(request, 'carryover_from_year', None)
    finally:
        db.close()

    # Now work only with plain variables - session is closed
    header_color = type_colors.get(req_type_lower, 'grey')
    is_own_request = (req_user_id == user_id)
    can_direct_delete = user_role in ['admin', 'superadmin'] or (user_role == 'manager' and is_own_request) or (is_trusted and is_own_request)

    with ui.dialog() as detail_dialog, ui.card().classes(f'w-full max-w-2xl p-0 border-l-4 border-{header_color}-500'):
        # Type icons mapping
        type_icons = {
            'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person',
            'bereavement': 'sentiment_very_dissatisfied', 'fmla': 'family_restroom',
            'jury_duty': 'gavel', 'voting': 'how_to_vote', 'military': 'military_tech',
            'chicago_leave': 'location_city', 'leave': 'location_city', 'work_from_home': 'home_work'
        }
        # Display name - rename chicago_leave to LEAVE (uppercase), add (CarryOver) for vacation carryover
        display_type = 'LEAVE' if req_type_lower in ['chicago_leave', 'leave'] else req_type.replace('_', ' ').upper()
        type_label = f'{display_type} (CarryOver)' if req_carryover_from_year and req_type_lower == 'vacation' else display_type

        # Header
        with ui.row().classes('w-full justify-between items-center p-4'):
            ui.label('LEAVE TIME OFF').classes('text-lg font-bold')
            ui.button(icon='close', on_click=detail_dialog.close).props('flat round dense')

        # Horizontal layout: Left identity panel + Right details panel
        with ui.element('div').style('display: flex; flex-direction: row; width: 100%; min-height: 300px;'):
            # LEFT PANEL - Identity (40%)
            with ui.element('div').style(f'width: 40%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1rem; gap: 0.75rem; background-color: rgba(0,0,0,0.1); border-right: 1px solid rgba(128,128,128,0.3);'):
                # Employee name
                ui.label(req_employee_name).classes('font-medium text-xl text-center')
                # Large colored icon
                ui.icon(type_icons.get(req_type_lower, 'event'), size='4rem').classes(f'text-{header_color}-500')
                # Type label under icon
                ui.label(type_label).classes(f'font-bold text-lg text-{header_color}-500 text-center')
                # Status badge
                ui.badge(req_status.title(), color=status_colors.get(req_status, 'grey')).classes('text-sm px-3 py-1')

            # RIGHT PANEL - Details (60%)
            with ui.element('div').style('width: 60%; display: flex; flex-direction: column; padding: 1rem; gap: 0.75rem;'):
                # Date info
                with ui.card().classes('w-full p-3'):
                    ui.label('Dates').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                    if req_start_date == req_end_date:
                        ui.label(req_start_date.strftime('%A, %B %d, %Y')).classes('font-medium')
                    else:
                        ui.label(f"{req_start_date.strftime('%A, %B %d, %Y')}").classes('font-medium')
                        ui.label('to').classes('text-xs opacity-60')
                        ui.label(f"{req_end_date.strftime('%A, %B %d, %Y')}").classes('font-medium')

                # Duration
                with ui.card().classes('w-full p-3'):
                    ui.label('Duration').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                    hours = req_total_days * 8
                    ui.label(format_days(hours)).classes('font-medium')

                # Notes (if any)
                if req_notes:
                    with ui.card().classes('w-full p-3'):
                        ui.label('Notes').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                        ui.label(req_notes).classes('text-sm')

                # Denial reason (if denied)
                if req_status == 'denied' and req_denial_reason:
                    with ui.card().classes('w-full p-3 border-l-4 border-red-500'):
                        ui.label('Denial Reason').classes('text-xs font-semibold uppercase text-red-500 mb-2')
                        ui.label(req_denial_reason).classes('text-sm')

                # Manager Approval info (if approved)
                if req_status == 'approved' and req_approved_at:
                    with ui.card().classes('w-full p-3 border-l-4 border-green-500'):
                        ui.label('Manager Approved').classes('text-xs font-semibold uppercase text-green-600 mb-2')
                        ui.label(req_approved_at.strftime('%A, %B %d, %Y')).classes('font-medium')

                # Carryover info (if vacation used previous year's balance)
                if req_carryover_from_year and req_type_lower == 'vacation':
                    with ui.card().classes('w-full p-3 border-l-4 border-amber-500'):
                        ui.label('Balance Source').classes('text-xs font-semibold uppercase text-amber-500 mb-2')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('card_giftcard', size='sm').classes('text-amber-500')
                            ui.label(f'Uses {req_carryover_from_year} unused vacation balance').classes('font-medium')
                        ui.label(f'This vacation day is deducted from your {req_carryover_from_year} allocation (carryover exception).').classes('text-xs opacity-70 mt-1')

                # Submission info
                with ui.row().classes('w-full justify-center text-xs opacity-50'):
                    ui.label(f'Submitted: {req_created_at.strftime("%b %d, %Y")}')

        # Function definitions (defined inside dialog but outside columns - no UI rendered here)
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
                # IMPORTANT: For carryover requests, restore to the FROM year (carryover_from_year)
                if req_type_lower in ['vacation', 'sick', 'personal']:
                    balance_service = BalanceService(del_db)
                    hours_to_restore = req_total_days * 8

                    if req_status == 'pending':
                        # CRITICAL: Use carryover_from_year for vacation rollover requests
                        balance_year = req_carryover_from_year if (req_type_lower == 'vacation' and req_carryover_from_year) else req_year
                        balance = balance_service.get_or_create_balance(req_user_id, balance_year)
                        if req_type_lower == 'vacation':
                            balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)
                    else:
                        # For vacation carryover, restore to the correct year
                        if req_type_lower == 'vacation' and req_carryover_from_year:
                            # Restore to the FROM year (e.g., 2025)
                            balance = balance_service.get_or_create_balance(req_user_id, req_carryover_from_year)
                            balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                        else:
                            balance = balance_service.get_or_create_balance(req_user_id, req_year)
                            if req_type_lower == 'vacation':
                                balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                            elif req_type_lower == 'sick':
                                balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                            elif req_type_lower == 'personal':
                                balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

                del_db.commit()

                # Audit log the cancellation
                AuditService.log_pto_cancel(
                    db=del_db,
                    user_id=current_user.get('id'),
                    username=current_user.get('username'),
                    request_id=req_id,
                    employee_name=req_employee_name,
                    cancelled_by_self=is_own_request
                )

                detail_dialog.close()
                ui.notify('Request deleted', type='positive')
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
                    # CRITICAL: Use carryover_from_year for vacation rollover requests
                    balance_year = req_carryover_from_year if req_carryover_from_year else req_year
                    balance = balance_service.get_or_create_balance(req_user_id, balance_year)
                    hours_to_restore = req_total_days * 8
                    balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)

                cancel_db.commit()

                # Audit log the cancellation
                AuditService.log_pto_cancel(
                    db=cancel_db,
                    user_id=current_user.get('id'),
                    username=current_user.get('username'),
                    request_id=req_id,
                    employee_name=req_employee_name,
                    cancelled_by_self=True
                )

                detail_dialog.close()
                ui.notify('Request cancelled', type='positive')
                ui.navigate.to('/dashboard')
            finally:
                cancel_db.close()

        def delete_approved_request_employee():
            """Employee directly deletes their approved PTO request with manager notification."""
            del_db = next(get_db())
            try:
                from src.models.pto_request import PTORequest
                req = del_db.query(PTORequest).filter(PTORequest.id == req_id).first()
                if not req:
                    show_error_dialog('Not Found', 'The request was not found.')
                    return

                # Get manager info for notification BEFORE modifying request
                manager_email = None
                manager_name = None
                if req.user and req.user.department and req.user.department.manager:
                    manager = req.user.department.manager
                    manager_email = manager.email
                    manager_name = manager.first_name

                # Store request details for email
                emp_name = req.user.full_name if req.user else 'Unknown'
                pto_type_for_email = req.pto_type
                start_for_email = req.start_date
                end_for_email = req.end_date
                days_for_email = float(req.total_days)

                req.status = 'cancelled'

                # Restore balance based on PTO type
                # IMPORTANT: For carryover requests, restore to the FROM year (carryover_from_year)
                if req_type_lower in ['vacation', 'sick', 'personal']:
                    balance_service = BalanceService(del_db)
                    hours_to_restore = req_total_days * 8

                    # For vacation carryover, restore to the correct year
                    if req_type_lower == 'vacation' and req_carryover_from_year:
                        # Restore to the FROM year (e.g., 2025)
                        balance = balance_service.get_or_create_balance(req_user_id, req_carryover_from_year)
                        balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                    else:
                        balance = balance_service.get_or_create_balance(req_user_id, req_year)
                        if req_type_lower == 'vacation':
                            balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                        elif req_type_lower == 'sick':
                            balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                        elif req_type_lower == 'personal':
                            balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

                del_db.commit()

                # Audit log the cancellation
                AuditService.log_pto_cancel(
                    db=del_db,
                    user_id=current_user.get('id'),
                    username=current_user.get('username'),
                    request_id=req_id,
                    employee_name=emp_name,
                    cancelled_by_self=True
                )

                # Send manager notification
                if manager_email:
                    try:
                        email_service.send_pto_cancelled_notification(
                            manager_email=manager_email,
                            manager_name=manager_name,
                            employee_name=emp_name,
                            pto_type=pto_type_for_email,
                            start_date=start_for_email,
                            end_date=end_for_email,
                            total_days=days_for_email
                        )
                    except Exception as e:
                        # Don't fail the deletion if email fails
                        pass

                detail_dialog.close()
                ui.notify('Request deleted', type='positive')
                ui.navigate.to('/dashboard')
            finally:
                del_db.close()

        # Show action buttons based on role and status
        # Past approved requests cannot be cancelled (time was already taken)
        # Past pending requests CAN be cancelled (never approved, so no time used)
        is_past_request = req_end_date < date.today()

        with ui.row().classes('w-full justify-end gap-2 mt-2 p-4'):
            if can_direct_delete and req_status in ['pending', 'approved']:
                # Admin/manager can delete pending anytime, approved only if not past
                if req_status == 'pending' or not is_past_request:
                    ui.button('Delete', icon='delete', on_click=delete_request_direct).props('color=negative')
            elif is_own_request and req_status == 'pending':
                # Employee can cancel their own pending requests (even past dates - never approved)
                ui.button('Cancel Request', icon='cancel', on_click=cancel_pending_request).props('color=negative')
            elif not is_past_request and is_own_request and req_status == 'approved':
                # Employee can directly delete approved requests (manager will be notified)
                # But NOT past approved requests (time was already taken)
                ui.button('Delete Request', icon='delete', on_click=delete_approved_request_employee).props('color=negative')

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
    is_dark = app.storage.user.get('dark_mode', True)  # Default to dark mode
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
