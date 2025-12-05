from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.database import get_db
from datetime import datetime, date
import pytz
from nicegui_app.logo import LOGO_DATA_URL


def get_time_based_greeting():
    """Get greeting based on Chicago timezone time of day."""
    chicago_tz = pytz.timezone('America/Chicago')
    chicago_time = datetime.now(chicago_tz)
    hour = chicago_time.hour

    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"


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
        recent_requests = all_requests[:5]

        # ============ MAIN LAYOUT ============
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):

            # Header with logo, greeting and logout
            with ui.row().classes('w-full justify-between items-center mb-6'):
                with ui.column().classes('gap-2'):
                    ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                    greeting = get_time_based_greeting()
                    ui.label(f'{greeting}, {user_first_name} {user_last_name}').classes('text-xl font-bold uppercase').style('color: #5a6a72;')

                with ui.row().classes('items-center gap-2'):
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

            # ============ PTO BALANCES CARD ============
            with ui.card().classes('w-full mb-4'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label(f'PTO Balances ({current_year})').classes('text-lg font-semibold')
                    ui.button('Request Time Off', icon='add', on_click=lambda: ui.navigate.to('/submit-request')).props('color=primary')

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

            # ============ PENDING REQUESTS (if any) ============
            if pending_requests:
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
                                        def cancel():
                                            cancel_request(request_id)
                                        return cancel

                                    ui.button('Cancel', icon='close', on_click=create_cancel_handler(req.id)).props('flat dense color=red size=sm')

            # ============ QUICK ACTIONS ============
            with ui.card().classes('w-full mb-4'):
                ui.label('Quick Actions').classes('text-lg font-semibold mb-3')

                with ui.row().classes('w-full gap-3 flex-wrap'):
                    ui.button('View Calendar', icon='calendar_month', on_click=lambda: ui.navigate.to('/calendar')).props('outline')
                    ui.button('Request History', icon='history', on_click=lambda: ui.navigate.to('/requests')).props('outline')
                    ui.button('Carryover Request', icon='move_down', on_click=lambda: ui.navigate.to('/carryover')).props('outline')

                    # Manager/Admin buttons
                    if user_role in ['manager', 'admin', 'superadmin']:
                        ui.button('Manager Dashboard', icon='supervisor_account', on_click=lambda: ui.navigate.to('/manager')).props('color=accent')

                    if user_role in ['admin', 'superadmin']:
                        ui.button('Admin Panel', icon='admin_panel_settings', on_click=lambda: ui.navigate.to('/admin')).props('color=negative')

            # ============ RECENT REQUESTS ============
            with ui.card().classes('w-full mb-4'):
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    ui.label('Recent Requests').classes('text-lg font-semibold')
                    if all_requests:
                        ui.button('View All', on_click=lambda: ui.navigate.to('/requests')).props('flat dense')

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
                        ui.label('No requests yet').classes('opacity-60')
                        ui.button('Submit Your First Request', on_click=lambda: ui.navigate.to('/submit-request')).props('flat')

            # ============ LEAVE POLICY (Collapsible) ============
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
                        with ui.row().classes('w-full gap-4 flex-wrap'):
                            # Vacation Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-blue-500'):
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

                            # Sick Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-green-500'):
                                ui.label('Sick Time Policy').classes('font-semibold text-green-600 mb-2')
                                sick_policy = accrual_service.get_policy_for_employee(current_user, 'SICK')

                                if sick_policy:
                                    if sick_policy.accrual_hours_divisor:
                                        ui.label(f'Accrual: 1 hr per {sick_policy.accrual_hours_divisor} hrs worked').classes('text-sm')
                                    if sick_policy.max_annual_hours:
                                        ui.label(f'Annual max: {int(float(sick_policy.max_annual_hours)/8)} days').classes('text-xs opacity-70')
                                    if sick_policy.max_carryover_hours:
                                        ui.label(f'Carryover: Up to {int(float(sick_policy.max_carryover_hours)/8)} days').classes('text-xs opacity-60')

                            # Personal Policy
                            with ui.card().classes('flex-1 min-w-64 p-3 border-l-4 border-purple-500'):
                                ui.label('Personal Days Policy').classes('font-semibold text-purple-600 mb-2')
                                personal_policy = accrual_service.get_policy_for_employee(current_user, 'PERSONAL')

                                if personal_policy:
                                    if personal_policy.max_annual_hours:
                                        days = int(float(personal_policy.max_annual_hours) / 8)
                                        ui.label(f'Annual allowance: {days} days').classes('text-sm')
                                    if personal_policy.min_increment_hours:
                                        ui.label(f'Minimum request: {personal_policy.min_increment_hours} hrs').classes('text-xs opacity-70')
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
