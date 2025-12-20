from nicegui import ui, app
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.balance_service import BalanceService
from src.services.user_service import UserService
from src.services.audit_service import AuditService
from src.services.email_service import email_service
from src.database import get_db
from src.models.leave_type import LeaveType
from src.models.pto_request import PTORequest
from src.models.market_holiday import MarketHoliday
from src.models.system_setting import SystemSetting
from datetime import date, datetime, timedelta
from decimal import Decimal
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog
from nicegui_app.components.formatting import fmt_days, format_days_hours
from src.utils.working_days import is_weekend, is_working_day, get_holidays_in_range


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


def count_business_days(start_date, end_date):
    """Count business days (Mon-Fri) between two dates, inclusive, excluding holidays.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Number of business days (weekdays only, excluding market holidays)
    """
    if start_date > end_date:
        return 0

    # Get holidays in the date range (only full closure days, not early close)
    holiday_dates = set()
    try:
        db = next(get_db())
        holidays = db.query(MarketHoliday.holiday_date).filter(
            MarketHoliday.holiday_date >= start_date,
            MarketHoliday.holiday_date <= end_date,
            ~MarketHoliday.name.contains('Early Close')  # Exclude early close days
        ).distinct().all()
        holiday_dates = {h.holiday_date for h in holidays}
        db.close()
    except Exception:
        pass  # If we can't get holidays, just count business days

    business_days = 0
    current = start_date
    while current <= end_date:
        # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        if current.weekday() < 5:  # Monday to Friday
            # Also check if it's not a holiday
            if current not in holiday_dates:
                business_days += 1
        current += timedelta(days=1)
    return business_days


def request_form_page(preselect_type: str = None):
    """PTO request form page with improved UX and intuitive date selection.

    Args:
        preselect_type: Optional PTO type code to pre-select (e.g., 'vacation', 'sick')
    """

    apply_dark_mode()

    # Check if user is logged in
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    # Query active leave types and get current user from database
    db = next(get_db())
    try:
        leave_types = db.query(LeaveType).filter(
            LeaveType.is_active == True
        ).order_by(LeaveType.sort_order).all()
        leave_type_options = {lt.code.lower(): lt.name for lt in leave_types}
        requires_doc_types = {lt.code.lower() for lt in leave_types if lt.requires_documentation}

        user_service = UserService(db)
        current_user = user_service.get_user_by_id(user['id'])

        balance_service = BalanceService(db)
        # We'll fetch balance dynamically based on selected dates
        # Store service for later use
        _balance_service = balance_service
        _user_id = user['id']

        pending_requests = db.query(PTORequest).filter(
            PTORequest.user_id == user['id'],
            PTORequest.status == 'pending'
        ).all()

        # NOTE: Holiday validation is now done server-side in count_business_days()
        # Removed client-side JS validation that caused iOS Safari blank screen

        # Get manager info from department
        manager_name = None
        if current_user and current_user.department and current_user.department.manager:
            manager = current_user.department.manager
            manager_name = f"{manager.first_name} {manager.last_name}"

        # Check if Chicago Safe Leave is enabled and if user is in Chicago
        chicago_setting = db.query(SystemSetting).filter(
            SystemSetting.key == 'chicago.safe_leave_enabled'
        ).first()
        is_chicago_enabled = chicago_setting and chicago_setting.bool_value
        is_chicago_employee = current_user and current_user.location_city and current_user.location_city.lower() == 'chicago'
        show_chicago_leave = is_chicago_enabled and is_chicago_employee

        # Add chicago_leave to options if user is eligible (needed for preselect navigation)
        if show_chicago_leave:
            leave_type_options['chicago_leave'] = 'Chicago Leave'
    finally:
        db.close()

    # Check for pre-filled date from calendar
    prefill_date_str = app.storage.user.pop('prefill_pto_date', None)
    prefill_date = None
    if prefill_date_str:
        try:
            prefill_date = date.fromisoformat(prefill_date_str)
        except (ValueError, TypeError):
            prefill_date = None

    # Get user role for private toggle visibility
    user_role = user.get('role', 'employee')

    # State management
    state = {
        'start_date': prefill_date or date.today(),
        'end_date': prefill_date or date.today(),
        'is_single_day': True,
        'is_half_day': False,
        'is_private': False,  # Only managers/admins can use this
        'chicago_blocked': False,  # Blocks Chicago Safe Leave when over balance
    }

    # ============ MAIN PAGE LAYOUT ============
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):

        # Header with greeting
        page_header(title='REQUEST FORM', show_back=False)

        # Show notice if date was pre-filled from calendar
        if prefill_date:
            with ui.card().classes('w-full mb-4 p-3 border-l-4 border-blue-500'):
                with ui.row().classes('items-center'):
                    ui.icon('event', color='blue').classes('mr-2')
                    ui.label(f'Pre-selected: {prefill_date.strftime("%A, %B %d, %Y")}').classes('text-blue-500')

        # ============ STEP 1: LEAVE TYPE ============
        # Define color mappings for PTO types
        type_colors = {
            'vacation': {'color': 'blue', 'bg': 'bg-blue-500', 'text': 'text-blue-600', 'border': 'border-blue-500'},
            'sick': {'color': 'green', 'bg': 'bg-green-500', 'text': 'text-green-600', 'border': 'border-green-500'},
            'personal': {'color': 'purple', 'bg': 'bg-purple-500', 'text': 'text-purple-600', 'border': 'border-purple-500'},
            'work_from_home': {'color': 'red', 'bg': 'bg-red-500', 'text': 'text-red-600', 'border': 'border-red-500'},
            'chicago_leave': {'color': 'orange', 'bg': 'bg-amber-500', 'text': 'text-amber-600', 'border': 'border-amber-500'},
            'other': {'color': 'grey', 'bg': 'bg-grey-500', 'text': 'text-grey-600', 'border': 'border-grey-500'},
        }

        # Primary types (with dedicated buttons) vs Other types
        primary_types = ['vacation', 'sick', 'personal', 'chicago_leave']
        other_types = {k: v for k, v in leave_type_options.items() if k not in primary_types}

        # State for selected type - use preselect_type if valid, otherwise default to vacation
        default_type = 'vacation' if 'vacation' in leave_type_options else list(leave_type_options.keys())[0] if leave_type_options else None
        if preselect_type and preselect_type.lower() in leave_type_options:
            default_type = preselect_type.lower()
        selected_type = {'value': default_type}

        # Calendar widget references for dynamic color updates
        calendar_widgets = {}
        # Half-day container reference for visibility control
        half_day_container = {'ref': None}

        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">1</span>', sanitize=False)
                ui.label('Select Leave Type').classes('text-lg font-semibold')
                help_text = (
                    'PRIMARY LEAVE TYPES:\n\n'
                    'Vacation: Planned time off for rest and relaxation. Accrues based on tenure.\n\n'
                    'Sick: For illness, medical appointments, or caring for sick family.\n\n'
                    'Personal: Flexible time for personal matters. Limited hours per year.\n\n'
                    'WFH: Work From Home - single day only, requires reason.'
                )
                if show_chicago_leave:
                    help_text += '\n\nChicago Leave: Use for ANY reason. 40hr annual max. 16hr carryover.'
                help_text += (
                    '\n\n─────────────────\n\n'
                    'OTHER LEAVE TYPES (click "More Leave Types"):\n\n'
                    'Bereavement, FMLA, Jury Duty, Voting, Military - no balance tracking.\n\n'
                    '🔒 Notes for these types are PRIVATE and only visible to you.'
                )
                ui.button(icon='help_outline', on_click=lambda: show_help_tip('Leave Types', help_text)).props('flat dense round size=sm').style('color: #f59e0b')

            # Primary type buttons - stacked icons with colors
            with ui.row().classes('w-full gap-4 mb-3 justify-center flex-wrap'):
                # Create button references
                type_buttons = {}

                # Icon and color mapping for each type
                type_icons = {
                    'vacation': ('beach_access', '#3b82f6'),    # Blue
                    'sick': ('local_hospital', '#22c55e'),       # Green
                    'personal': ('person', '#a855f7'),           # Purple
                    'chicago_leave': ('spa', '#f59e0b'),         # Amber
                    'work_from_home': ('home_work', '#ef4444'),  # Red
                }

                def create_type_handler(type_code):
                    def handler():
                        selected_type['value'] = type_code
                        # Reset half-day for WFH since it doesn't support half-days
                        if type_code == 'work_from_home':
                            state['is_half_day'] = False
                        update_type_button_styles()
                        update_balance_display()
                        update_summary_color()
                        update_calendar_colors()
                        update_half_day_visibility()
                        update_date_mode_for_type()
                        update_notes_label()
                        build_date_selector()  # Rebuild to update PTO type overlay
                    return handler

                def get_available_for_type(type_code):
                    """Get available hours for a leave type."""
                    if type_code == 'work_from_home':
                        return 0  # WFH has no balance
                    db_bal = next(get_db())
                    try:
                        bal_svc = BalanceService(db_bal)
                        balance = bal_svc.get_or_create_balance(_user_id, date.today().year)
                        code = type_code.upper()
                        if code == 'VACATION':
                            total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                            used = float(balance.vacation_used or 0)
                            pending = float(balance.vacation_pending or 0)
                        elif code == 'SICK':
                            total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                            used = float(balance.sick_used or 0)
                            pending = 0
                        elif code == 'PERSONAL':
                            total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                            used = float(balance.personal_used or 0)
                            pending = 0
                        elif code == 'CHICAGO_LEAVE':
                            total = float(balance.chicago_paid_leave_total or 0) + float(balance.chicago_paid_leave_carryover or 0)
                            used = float(balance.chicago_paid_leave_used or 0)
                            pending = float(balance.chicago_paid_leave_pending or 0)
                        else:
                            return 0
                        return max(0, total - used - pending)
                    finally:
                        db_bal.close()

                def get_full_balance_for_type(type_code):
                    """Get full balance details for a leave type."""
                    if type_code == 'work_from_home':
                        return {'total': 0, 'used': 0, 'pending': 0, 'carryover': 0, 'available': 0, 'allocated': 0}

                    db_bal = next(get_db())
                    try:
                        bal_svc = BalanceService(db_bal)
                        balance = bal_svc.get_or_create_balance(_user_id, date.today().year)
                        code = type_code.upper()

                        if code == 'VACATION':
                            allocated = float(balance.vacation_total or 0)
                            carryover = float(balance.vacation_carryover or 0)
                            used = float(balance.vacation_used or 0)
                            pending = float(balance.vacation_pending or 0)
                        elif code == 'SICK':
                            allocated = float(balance.sick_total or 0)
                            carryover = float(balance.sick_carryover or 0)
                            used = float(balance.sick_used or 0)
                            pending = float(balance.sick_pending or 0)
                        elif code == 'PERSONAL':
                            allocated = float(balance.personal_total or 0)
                            carryover = float(balance.personal_carryover or 0)
                            used = float(balance.personal_used or 0)
                            pending = float(balance.personal_pending or 0)
                        elif code == 'CHICAGO_LEAVE':
                            allocated = float(balance.chicago_paid_leave_total or 0)
                            carryover = float(balance.chicago_paid_leave_carryover or 0)
                            used = float(balance.chicago_paid_leave_used or 0)
                            pending = float(balance.chicago_paid_leave_pending or 0)
                        else:
                            return {'total': 0, 'used': 0, 'pending': 0, 'carryover': 0, 'available': 0, 'allocated': 0}

                        total = allocated + carryover
                        available = total - used - pending
                        return {'total': total, 'used': used, 'pending': pending, 'carryover': carryover, 'available': available, 'allocated': allocated}
                    finally:
                        db_bal.close()

                def format_days_simple(hours):
                    """Format hours as days string."""
                    if hours == 0:
                        return '0 days'
                    days = hours / 8
                    if days == int(days):
                        return f'{int(days)} days' if days != 1 else '1 day'
                    return f'{days:.1f} days'

                def create_type_card(type_code, label, icon, color, text_class, border_class, quasar_color, carryover_note=''):
                    """Create a dashboard-style type selection card matching main dashboard exactly."""
                    bal = get_full_balance_for_type(type_code)

                    with ui.card().classes(f'flex-1 p-4 {border_class} cursor-pointer hover:shadow-lg transition-shadow').style(
                        'min-width: 200px; border-width: 2px; border-style: solid; border-color: transparent; transition: all 0.2s ease;'
                    ) as card:
                        card.on('click', create_type_handler(type_code))

                        # Header: Large Icon + Title (matching dashboard)
                        with ui.row().classes('items-center gap-2'):
                            ui.icon(icon, size='1.5rem').classes(text_class)
                            ui.label(label.upper()).classes(f'text-lg font-bold {text_class}')

                        # Available balance (large) - matches dashboard
                        avail_display, avail_tooltip = format_days_hours(bal['available'])
                        if bal['available'] < 0:
                            ui.label(avail_display).classes('text-2xl font-bold text-red-500 my-2').tooltip(avail_tooltip)
                            ui.label('OVERDRAWN').classes('text-sm text-red-500 font-medium')
                        else:
                            ui.label(avail_display).classes(f'text-2xl font-bold {text_class} my-2').tooltip(avail_tooltip)
                            ui.label('AVAILABLE').classes('text-sm opacity-70')

                        # Progress bar with used/total - matches dashboard exactly
                        if bal['total'] > 0:
                            used_ratio = min(bal['used'] / bal['total'], 1.0)
                            with ui.column().classes('w-full mt-3 gap-1'):
                                with ui.row().classes('w-full justify-between text-xs'):
                                    ui.label(f'{format_days_simple(bal["used"])} used').classes(text_class)
                                    ui.label(f'{format_days_simple(bal["total"])} total').classes('opacity-60')
                                ui.linear_progress(value=used_ratio, show_value=False).props(f'color={quasar_color} track-color=grey-3').classes('w-full')
                                if bal['pending'] > 0:
                                    ui.label(f'{format_days_simple(bal["pending"])} pending').classes('text-xs text-amber-500')
                                # Allocated vs carryover breakdown (matches dashboard)
                                with ui.row().classes('w-full justify-between text-xs mt-1 opacity-50'):
                                    ui.label(f'{format_days_simple(bal["allocated"])} allocated')
                                    if bal['carryover'] > 0:
                                        ui.label(f'+{format_days_simple(bal["carryover"])} carryover')
                                if carryover_note:
                                    ui.label(carryover_note).classes('text-xs opacity-50 mt-1')
                    return card

                # Vacation card (matches dashboard)
                if 'vacation' in leave_type_options:
                    type_buttons['vacation'] = create_type_card(
                        'vacation', 'Vacation', 'beach_access', '#3b82f6',
                        'text-blue-600', 'border-l-4 border-blue-500', 'blue-5', 'Carryover requires approval'
                    )

                # Sick card (matches dashboard)
                if 'sick' in leave_type_options:
                    type_buttons['sick'] = create_type_card(
                        'sick', 'Sick', 'local_hospital', '#22c55e',
                        'text-green-600', 'border-l-4 border-green-500', 'green-5', 'Auto carryover (max 80hr)'
                    )

                # Personal card (matches dashboard)
                if 'personal' in leave_type_options:
                    type_buttons['personal'] = create_type_card(
                        'personal', 'Personal', 'person', '#a855f7',
                        'text-purple-600', 'border-l-4 border-purple-500', 'purple-5', 'Use it or lose it'
                    )

                # Chicago Leave card - amber, shown only for Chicago employees (matches dashboard)
                if show_chicago_leave:
                    type_buttons['chicago_leave'] = create_type_card(
                        'chicago_leave', 'Leave', 'spa', '#f59e0b',
                        'text-amber-600', 'border-l-4 border-amber-500', 'amber-5', '16hr carryover max'
                    )

            # Other types - expandable row underneath main types
            other_types_container = {'ref': None, 'visible': False}
            if other_types:
                # Icon and color mapping for "Other" leave types (colors work in both light/dark mode)
                # Colors chosen to be distinct from primary types and each other
                other_type_icons = {
                    'work_from_home': ('home_work', '#ef4444'),                   # Red (WFH moved here)
                    'bereavement': ('sentiment_very_dissatisfied', '#6366f1'),  # Indigo
                    'fmla': ('medical_services', '#0891b2'),                     # Cyan
                    'jury_duty': ('gavel', '#ec4899'),                           # Pink/Rose (distinct from indigo)
                    'voting': ('how_to_vote', '#0d9488'),                        # Teal
                    'military': ('military_tech', '#64748b'),                    # Slate gray (professional)
                }
                default_other_icon = ('event_note', '#78716c')  # Stone gray

                def toggle_other_types():
                    other_types_container['visible'] = not other_types_container['visible']
                    other_types_container['ref'].set_visibility(other_types_container['visible'])
                    # Update toggle button text
                    if other_types_container['visible']:
                        toggle_btn.text = 'Hide Other Leave Types'
                        toggle_btn.props('icon=expand_less')
                    else:
                        toggle_btn.text = 'More Leave Types'
                        toggle_btn.props('icon=expand_more')

                # Toggle button - styled with TJM gold accent
                with ui.row().classes('w-full justify-center mt-3'):
                    toggle_btn = ui.button(
                        'More Leave Types',
                        icon='expand_more',
                        on_click=toggle_other_types
                    ).props('outline rounded').style('color: #c9a227; border-color: #c9a227;').classes('text-sm')

                # Container for other leave type cards (hidden by default)
                other_types_container['ref'] = ui.row().classes('w-full gap-4 mt-4 justify-center flex-wrap')
                other_types_container['ref'].set_visibility(False)

                def create_other_type_card(type_code, label, icon, color):
                    """Create a card for other leave types - same size as primary types."""
                    with ui.card().classes('cursor-pointer p-4 text-center').style(
                        f'width: 120px; height: 120px; border: 2px solid transparent; transition: all 0.2s ease;'
                    ) as card:
                        card.on('click', create_type_handler(type_code))
                        with ui.column().classes('items-center justify-center gap-1 h-full'):
                            ui.icon(icon, size='3.5rem').style(f'color: {color};')
                            ui.label(label).classes('text-base font-semibold').style(f'color: {color};')
                            # No balance for other types
                            ui.label('No Limit').classes('text-sm').style(f'color: {color}; opacity: 0.7;')
                    return card

                with other_types_container['ref']:
                    for code, name in other_types.items():
                        icon_info = other_type_icons.get(code, default_other_icon)
                        # Shorten long names for display
                        short_name = name.replace(' Leave', '').replace('Bereavement', 'Bereave.')
                        type_buttons[code] = create_other_type_card(code, short_name, icon_info[0], icon_info[1])

            def update_type_button_styles():
                """Update card styles based on current selection."""
                current = selected_type['value']

                # Color mapping for border highlights (primary + other types)
                card_colors = {
                    'vacation': '#3b82f6',      # Blue
                    'sick': '#22c55e',          # Green
                    'personal': '#a855f7',      # Purple
                    'chicago_leave': '#f59e0b', # Amber
                    'work_from_home': '#ef4444', # Red
                    # Other leave types
                    'bereavement': '#6366f1',   # Indigo
                    'fmla': '#0891b2',          # Cyan
                    'jury_duty': '#ec4899',     # Pink/Rose
                    'voting': '#0d9488',        # Teal
                    'military': '#64748b',      # Slate gray
                }

                for type_code, card in type_buttons.items():
                    if type_code == current:
                        # Selected card - add colored border and subtle glow
                        color = card_colors.get(type_code, '#64748b')
                        card.style(f'border: 3px solid {color}; box-shadow: 0 0 12px {color}40; transform: scale(1.05);')
                    else:
                        # Unselected card - transparent border
                        card.style('border: 2px solid transparent; box-shadow: none; transform: scale(1);')

            def update_half_day_visibility():
                """Show/hide half-day option based on selected type."""
                if half_day_container['ref']:
                    # WFH doesn't support half-day
                    if selected_type['value'] == 'work_from_home':
                        half_day_container['ref'].set_visibility(False)
                    else:
                        half_day_container['ref'].set_visibility(True)

            def update_date_mode_for_type():
                """Handle type-specific date mode restrictions (e.g., WFH is single-day only)."""
                if selected_type['value'] == 'work_from_home':
                    # WFH is single-day only - force single day mode if in range
                    if not state['is_single_day']:
                        state['is_single_day'] = True
                        state['end_date'] = state['start_date']
                        build_date_selector()
                        update_summary()

            # Initialize button styles
            update_type_button_styles()

            # Create a mock pto_type object for compatibility with existing code
            class PTOTypeProxy:
                @property
                def value(self):
                    return selected_type['value']

            pto_type = PTOTypeProxy()

            def get_balance_for_type(leave_type_code, for_year=None):
                """Get available, used, and pending hours for a leave type.

                Args:
                    leave_type_code: Type of leave (vacation, sick, personal)
                    for_year: Year to get balance for (defaults to selected start date year)

                Returns:
                    Tuple of (total, used, pending, available, balance_exists, exception_carryover)
                """
                if not leave_type_code:
                    return 0, 0, 0, 0, False, 0

                # Use the start date year if no year specified
                target_year = for_year or state['start_date'].year
                current_year = date.today().year
                current_month = date.today().month

                # VACATION ROLLOVER: If December and vacation for January next year,
                # use current year balance (rollover scenario)
                is_vacation_rollover = (
                    leave_type_code.upper() == 'VACATION' and
                    current_month == 12 and
                    state['start_date'].year > current_year and
                    state['start_date'].month == 1 and
                    state['end_date'].month == 1
                )
                if is_vacation_rollover:
                    target_year = current_year

                # Get or create balance for the target year
                db_session = next(get_db())
                try:
                    bal_svc = BalanceService(db_session)
                    balance = bal_svc.get_or_create_balance(_user_id, target_year)
                    exception_carryover = 0  # Vacation exception carryover from previous year

                    code = leave_type_code.upper()
                    if code == 'VACATION':
                        total = float(balance.vacation_total or 0)
                        used = float(balance.vacation_used or 0)
                        pending = float(balance.vacation_pending or 0)
                        carryover = float(balance.vacation_carryover or 0)
                        # Also get vacation exception carryover from previous year
                        exception_carryover = float(PTOService.get_available_vacation_carryover(db_session, _user_id, target_year))
                    elif code == 'SICK':
                        total = float(balance.sick_total or 0)
                        used = float(balance.sick_used or 0)
                        pending = 0
                        carryover = float(balance.sick_carryover or 0)
                    elif code == 'PERSONAL':
                        total = float(balance.personal_total or 0)
                        used = float(balance.personal_used or 0)
                        pending = 0
                        carryover = float(balance.personal_carryover or 0)
                    elif code == 'CHICAGO_LEAVE':
                        # Chicago Leave uses the chicago_paid_leave balance (16hr carryover)
                        total = float(balance.chicago_paid_leave_total or 0)
                        used = float(balance.chicago_paid_leave_used or 0)
                        pending = float(balance.chicago_paid_leave_pending or 0)
                        carryover = float(balance.chicago_paid_leave_carryover or 0)
                    else:
                        return 0, 0, 0, 0, False, 0

                    available = total + carryover + exception_carryover - used - pending
                    # Check if balance has been allocated (total > 0 OR exception carryover exists)
                    balance_allocated = total > 0 or exception_carryover > 0
                    return total + carryover, used, pending, available, balance_allocated, exception_carryover
                finally:
                    db_session.close()

            def get_wfh_usage():
                """Get total WFH days used by the employee."""
                db_session = next(get_db())
                try:
                    # Count approved WFH requests
                    wfh_requests = db_session.query(PTORequest).filter(
                        PTORequest.user_id == _user_id,
                        PTORequest.pto_type.ilike('work_from_home'),
                        PTORequest.status == 'approved'
                    ).all()
                    total_days = sum(float(r.total_days) for r in wfh_requests)
                    return total_days
                finally:
                    db_session.close()

            def update_balance_display():
                """No-op - balance is now shown in the type cards."""
                pass

        # ============ STEP 2: DATE SELECTION ============
        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">2</span>', sanitize=False)
                ui.label('Select Date(s)').classes('text-lg font-semibold')
                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                    'Date Selection',
                    'Click once for a single day, or click two dates for a range.\n\n'
                    'Business Days Only: Weekends (Sat/Sun) and company holidays are automatically excluded from your request and won\'t count against your balance.\n\n'
                    'Half Day: Available for single-day requests (except WFH and Personal days).\n\n'
                    'WFH requests are limited to single day only and must be within 7 days.'
                )).props('flat dense round size=sm').style('color: #f59e0b')

            # Microcopy explaining the calendar interaction
            ui.label('Click a start date, then an end date. Weekends and holidays are excluded from your total.').classes('text-sm opacity-70 mb-3')

            # Date selection container
            date_selection_container = ui.column().classes('w-full')

            # Half-day container reference (for showing/hiding)
            half_day_switch_ref = {'ref': None}

            # Summary display (updates in real-time)
            summary_container = ui.row().classes('w-full mt-4 p-3 rounded-lg justify-around items-center border-l-4 border-blue-500')

            def update_summary_color():
                """Update summary container border color based on selected PTO type."""
                current = selected_type['value']
                color_map = {
                    'vacation': 'border-blue-500',
                    'sick': 'border-green-500',
                    'personal': 'border-purple-500',
                    'work_from_home': 'border-red-500',
                    'chicago_leave': 'border-amber-500',
                    # Other leave types
                    'bereavement': 'border-indigo-500',
                    'fmla': 'border-cyan-500',
                    'jury_duty': 'border-pink-500',
                    'voting': 'border-teal-500',
                    'military': 'border-slate-500',
                }
                new_border = color_map.get(current, 'border-gray-500')
                summary_container.classes(remove='border-blue-500 border-green-500 border-purple-500 border-red-500 border-amber-500 border-teal-500 border-grey-500 border-gray-500 border-indigo-500 border-cyan-500 border-pink-500 border-slate-500')
                summary_container.classes(add=new_border)

            def update_calendar_colors():
                """Update calendar accent colors based on selected PTO type."""
                current = selected_type['value']
                # Map types to Quasar colors
                cal_color_map = {
                    'vacation': 'blue',
                    'sick': 'green',
                    'personal': 'purple',
                    'work_from_home': 'red',
                    'chicago_leave': 'amber',
                    'bereavement': 'indigo',
                    'fmla': 'cyan',
                    'jury_duty': 'pink',
                    'voting': 'teal',
                    'military': 'blue-grey',
                }
                cal_color = cal_color_map.get(current, 'grey')
                for key, cal in calendar_widgets.items():
                    if cal:
                        cal.props(remove='color=blue color=green color=purple color=red color=amber color=grey color=indigo color=cyan color=pink color=teal color=blue-grey')
                        cal.props(f'color={cal_color}')

            def update_half_day_visibility():
                """Update half-day switch visibility based on PTO type and date selection."""
                if half_day_switch_ref['ref'] is None:
                    return
                # Half-day is hidden for:
                # - Date ranges (start != end)
                # - WFH requests
                # - Personal day requests
                is_single_day = state['start_date'] == state['end_date']
                is_wfh = selected_type['value'] == 'work_from_home'
                is_personal = selected_type['value'] == 'personal'
                should_show = is_single_day and not is_wfh and not is_personal
                half_day_switch_ref['ref'].set_visibility(should_show)
                # Reset half-day if hidden
                if not should_show:
                    state['is_half_day'] = False

            def on_clear_dates():
                """Reset date selection to today."""
                today = date.today()
                # Find next working day if today is weekend
                current = today
                while is_weekend(current):
                    current += timedelta(days=1)
                state['start_date'] = current
                state['end_date'] = current
                state['is_single_day'] = True
                state['is_half_day'] = False
                build_date_selector()
                update_summary()
                update_half_day_visibility()

            def build_date_selector():
                date_selection_container.clear()
                with date_selection_container:
                    # Get PTO type info for overlay
                    current_type = selected_type['value']
                    type_icon, type_hex = type_icons.get(current_type, ('event', '#9ca3af'))
                    # Create uppercase labels for calendar overlay
                    label_map = {
                        'vacation': 'VACATION',
                        'sick': 'SICK',
                        'personal': 'PERSONAL',
                        'work_from_home': 'WFH',
                        'chicago_leave': 'LEAVE',
                        'bereavement': 'BEREAVEMENT',
                        'fmla': 'FMLA',
                        'jury_duty': 'JURY DUTY',
                        'voting': 'VOTING',
                        'military': 'MILITARY',
                    }
                    type_label = label_map.get(current_type, current_type.replace('_', ' ').upper()) if current_type else 'SELECT'

                    # Single range calendar with click-click pattern
                    def on_date_change(e):
                        if e.value is None:
                            return

                        value = e.value

                        # Handle range selection (dict with 'from' and 'to')
                        if isinstance(value, dict):
                            from_date = date.fromisoformat(value['from']) if value.get('from') else None
                            to_date = date.fromisoformat(value['to']) if value.get('to') else None

                            if from_date and to_date:
                                # Validate start date is not weekend/holiday
                                if is_weekend(from_date):
                                    show_warning_dialog('Invalid Start Date',
                                        f'Start date cannot be a {from_date.strftime("%A")}. Please select a business day (Mon-Fri).')
                                    # Reset to previous state
                                    range_calendar.value = state['start_date'].isoformat()
                                    return

                                # Check for cross-year requests
                                if from_date.year != to_date.year:
                                    show_warning_dialog('Cross-Year Request Not Allowed',
                                        'PTO requests cannot span multiple years. '
                                        'Please submit separate requests for each year.')
                                    range_calendar.value = state['start_date'].isoformat()
                                    return

                                # Check for unreasonably large date range
                                if (to_date - from_date).days > 90:
                                    show_warning_dialog('Date Range Too Large',
                                        f'The selected range spans {(to_date - from_date).days} days. '
                                        'Please select a shorter range (max ~3 months). '
                                        'For extended leave, please contact HR.')
                                    range_calendar.value = state['start_date'].isoformat()
                                    return

                                # WFH is single-day only - collapse to start date
                                if selected_type['value'] == 'work_from_home' and from_date != to_date:
                                    ui.notify('WFH requests are single-day only. Using start date.', type='info')
                                    state['start_date'] = from_date
                                    state['end_date'] = from_date
                                    state['is_single_day'] = True
                                    range_calendar.value = from_date.isoformat()
                                else:
                                    state['start_date'] = from_date
                                    state['end_date'] = to_date
                                    state['is_single_day'] = (from_date == to_date)

                        # Handle single date selection (string)
                        elif isinstance(value, str):
                            picked = date.fromisoformat(value)

                            # Validate not weekend/holiday
                            if is_weekend(picked):
                                show_warning_dialog('Invalid Date',
                                    f'Cannot select a {picked.strftime("%A")}. Please select a business day (Mon-Fri).')
                                range_calendar.value = state['start_date'].isoformat()
                                return

                            state['start_date'] = picked
                            state['end_date'] = picked
                            state['is_single_day'] = True

                        update_balance_display()
                        update_summary()
                        update_warning()
                        update_half_day_visibility()

                    # Set calendar color based on PTO type (includes all leave types)
                    cal_color_map = {
                        'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
                        'work_from_home': 'red', 'chicago_leave': 'amber',
                        'bereavement': 'indigo', 'fmla': 'cyan', 'jury_duty': 'pink',
                        'voting': 'teal', 'military': 'blue-grey',
                    }
                    cal_color = cal_color_map.get(selected_type['value'], 'grey')

                    # Build initial value - use range dict if dates differ, else single string
                    if state['start_date'] == state['end_date']:
                        initial_value = state['start_date'].isoformat()
                    else:
                        initial_value = {'from': state['start_date'].isoformat(), 'to': state['end_date'].isoformat()}

                    # Wrap calendar in relative container for icon overlay
                    # NOTE: Removed complex inline :options JS that caused iOS Safari blank screen
                    # Weekend/holiday exclusion is handled server-side in count_business_days()
                    with ui.element('div').classes('relative w-full'):
                        range_calendar = ui.date(
                            value=initial_value,
                            on_change=on_date_change
                        ).props(f'range color={cal_color}').classes('w-full')
                        calendar_widgets['range'] = range_calendar

                        # PTO type overlay on calendar header
                        with ui.element('div').classes('absolute top-2 right-2 flex flex-col items-center gap-0').style('z-index: 10;'):
                            ui.icon(type_icon, size='xl').style(f'color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.3);')
                            ui.label(type_label).classes('text-xs font-bold').style('color: white; text-shadow: 0 1px 2px rgba(0,0,0,0.3);')

                    # Half-day option and Clear button row
                    with ui.row().classes('w-full mt-3 items-center justify-between'):
                        # Half-day switch (only for single day, not for WFH or Personal)
                        half_day_row = ui.row().classes('items-center')
                        half_day_switch_ref['ref'] = half_day_row
                        half_day_container['ref'] = half_day_row
                        with half_day_row:
                            def on_half_day_change(e):
                                state['is_half_day'] = e.value
                                update_summary()
                                update_warning()

                            ui.switch('Half Day (4 hours)', value=state['is_half_day'], on_change=on_half_day_change)

                        # Clear Dates button
                        ui.button('Clear Dates', icon='clear', on_click=on_clear_dates).props('flat dense').classes('text-sm')

                    # Update half-day visibility based on current state
                    update_half_day_visibility()

            def update_summary():
                summary_container.clear()
                with summary_container:
                    # Calculate request details - count only business days (Mon-Fri)
                    if state['is_half_day']:
                        total_days = 0.5
                    else:
                        total_days = count_business_days(state['start_date'], state['end_date'])
                    hours_requested = total_days * 8

                    is_wfh = pto_type.value == 'work_from_home'
                    is_chicago = pto_type.value == 'chicago_leave'
                    non_balance_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']
                    is_non_balance = pto_type.value and pto_type.value.lower() in non_balance_types

                    # Determine colors based on leave type
                    if is_wfh:
                        icon_color = 'red'
                        text_color = 'text-red-600'
                    elif is_chicago:
                        icon_color = 'amber'
                        text_color = 'text-amber-600'
                    elif is_non_balance:
                        icon_color = 'grey'
                        text_color = 'text-grey-600'
                    else:
                        icon_color = type_colors.get(pto_type.value, {}).get('color', 'blue')
                        text_color = type_colors.get(pto_type.value, {}).get('text', 'text-blue-600')

                    # Date display
                    with ui.column().classes('items-center'):
                        ui.icon('event', color=icon_color).classes('text-2xl')
                        if state['start_date'] == state['end_date']:
                            ui.label(state['start_date'].strftime('%A, %B %d, %Y')).classes('font-medium')
                            if state['is_half_day']:
                                ui.label('Half Day').classes('text-xs opacity-60')
                        else:
                            ui.label(f"{state['start_date'].strftime('%A, %B %d')} - {state['end_date'].strftime('%A, %B %d, %Y')}").classes('font-medium')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Hours/Days requested
                    with ui.column().classes('items-center'):
                        ui.label(fmt_days(total_days)).classes(f'text-2xl font-bold {text_color}')
                        ui.label(f'{hours_requested:.0f} hours total').classes('text-xs opacity-60')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Balance after (or special indicators)
                    if is_wfh:
                        with ui.column().classes('items-center'):
                            ui.icon('home_work', color='red').classes('text-2xl')
                            ui.label('WFH').classes('text-xs opacity-60')
                    elif is_non_balance:
                        with ui.column().classes('items-center'):
                            ui.icon('check_circle', color='green').classes('text-2xl')
                            ui.label('No balance limit').classes('text-xs opacity-60')
                    else:
                        _, _, _, available, _, _ = get_balance_for_type(pto_type.value)
                        remaining = available - hours_requested
                        with ui.column().classes('items-center'):
                            if remaining < 0:
                                remaining_display, remaining_tooltip = format_days_hours(remaining)
                                ui.label(remaining_display).classes('text-2xl font-bold text-amber-600').tooltip(remaining_tooltip)
                                ui.label('over balance').classes('text-xs text-amber-600')
                            else:
                                color = 'text-green-600' if remaining >= 16 else 'text-amber-600'
                                remaining_display, remaining_tooltip = format_days_hours(remaining)
                                ui.label(remaining_display).classes(f'text-2xl font-bold {color}').tooltip(remaining_tooltip)
                                ui.label('remaining').classes('text-xs opacity-60')

        # ============ STEP 3: NOTES ============
        # Define which types have private notes (other leave types)
        private_notes_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']

        with ui.card().classes('w-full mb-4 p-3'):
            with ui.row().classes('items-center mb-2'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">3</span>', sanitize=False)
                notes_header = ui.label('Notes (optional)').classes('text-lg font-semibold')
                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                    'Notes & Privacy',
                    'Notes: Add context for your request.\n\n'
                    'Required for: WFH requests only (reason needed).\n\n'
                    '🔒 PRIVATE NOTES: For Bereavement, FMLA, Jury Duty, Voting, and Military leave, notes are optional and ONLY visible to you - your manager will NOT see them.\n\n'
                    'Keep Private: Managers/admins can mark requests private to hide from the department calendar.'
                )).props('flat dense round size=sm').style('color: #f59e0b')

            description = ui.input().classes('w-full').props('dense')

            # Privacy notice container (shown for other leave types)
            privacy_notice_container = ui.row().classes('w-full mt-2 items-center gap-2 p-2 rounded').style('background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3);')
            privacy_notice_container.set_visibility(False)
            with privacy_notice_container:
                ui.icon('lock', color='indigo', size='sm')
                ui.label('Notes are private - only visible to you, not your manager').classes('text-xs text-indigo-400')

            # Private toggle - only for managers/admins/superadmins
            if user_role in ['manager', 'admin', 'superadmin']:
                with ui.row().classes('w-full mt-3 items-center gap-2'):
                    def on_private_change(e):
                        state['is_private'] = e.value

                    ui.switch('Keep Private', value=state['is_private'], on_change=on_private_change)
                    ui.label('(Hidden from department calendar)').classes('text-xs opacity-60')

            # Update header and privacy notice based on leave type
            def update_notes_label():
                is_private_type = pto_type.value in private_notes_types
                if pto_type.value == 'work_from_home':
                    # Only WFH requires a reason
                    notes_header.text = 'Reason (required)'
                    notes_header.classes('text-lg font-semibold text-red-600', remove='text-gray-600 text-indigo-400')
                    privacy_notice_container.set_visibility(False)
                elif is_private_type:
                    # Other leave types (bereavement, fmla, etc.) have private optional notes
                    notes_header.text = 'Private Notes (optional)'
                    notes_header.classes('text-lg font-semibold text-indigo-400', remove='text-red-600 text-gray-600')
                    privacy_notice_container.set_visibility(True)
                else:
                    # Vacation, Sick, Personal, Leave - all have optional notes with privacy notice
                    notes_header.text = 'Notes (optional)'
                    notes_header.classes('text-lg font-semibold', remove='text-red-600 text-indigo-400')
                    privacy_notice_container.set_visibility(True)

        # ============ SUBMIT SECTION ============
        with ui.card().classes('w-full'):
            # Manager info - who will approve this request
            if manager_name:
                with ui.row().classes('w-full items-center mb-4 p-3 rounded-lg').style('border: 1px solid rgba(128,128,128,0.3)'):
                    ui.icon('person', color='blue').classes('mr-2')
                    ui.label('Approving Manager:').classes('opacity-70')
                    ui.label(manager_name).classes('font-semibold ml-2')

            # Warning for insufficient balance
            warning_container = ui.column().classes('w-full mb-4')

            def update_warning():
                warning_container.clear()
                if state['is_half_day']:
                    total_days = 0.5
                else:
                    total_days = count_business_days(state['start_date'], state['end_date'])
                hours_requested = total_days * 8
                is_wfh = pto_type.value == 'work_from_home'
                _, _, _, available, balance_allocated, _ = get_balance_for_type(pto_type.value)

                # Detect vacation rollover scenario
                current_year = date.today().year
                current_month = date.today().month
                is_vacation_rollover = (
                    pto_type.value == 'vacation' and
                    current_month == 12 and
                    state['start_date'].year > current_year and
                    state['start_date'].month == 1 and
                    state['end_date'].month == 1
                )
                # For rollover, use current year; otherwise use start_date year
                target_year = current_year if is_vacation_rollover else state['start_date'].year

                with warning_container:
                    # WFH date restriction: only within 1 week allowed
                    if is_wfh:
                        one_week_out = date.today() + timedelta(days=7)
                        if state['start_date'] > one_week_out:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-red-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('error', color='red').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label('WFH requests limited to within 1 week').classes('text-red-500 font-medium')
                                        ui.label('Work From Home must be submitted within 7 days. For advance requests, contact your manager.').classes('text-sm opacity-70')

                    # Personal leave: 24hr advance notice warning (informational, not blocking)
                    if pto_type.value == 'personal':
                        hours_until_start = (datetime.combine(state['start_date'], datetime.min.time()) - datetime.now()).total_seconds() / 3600
                        if hours_until_start < 24:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-blue-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('schedule', color='blue').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label('Personal time - 24hr notice preferred').classes('text-blue-500 font-medium')
                                        ui.label('When possible, please request personal time at least 24 hours in advance.').classes('text-sm opacity-70')

                    # Skip balance-related warnings for WFH (no balance system)
                    if not is_wfh:
                        # VACATION ROLLOVER info card
                        if is_vacation_rollover:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-green-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('sync', color='green').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Vacation Rollover from {current_year}').classes('text-green-500 font-medium')
                                        ui.label(f'This vacation will be deducted from your {current_year} balance and requires manager approval.').classes('text-sm opacity-70')

                        # Warning for unallocated future year balance (NOT for vacation rollover)
                        elif not balance_allocated and target_year != date.today().year:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-amber-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('schedule', color='amber').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Planning ahead for {target_year}').classes('text-amber-600 font-medium')
                                        ui.label(f"Your {target_year} balance will be allocated in January. This request will count against that allocation.").classes('text-sm opacity-70')

                        # Warning for cross-year requests
                        if state['start_date'].year != state['end_date'].year:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-purple-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('calendar_month', color='purple').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Request spans {state["start_date"].year} and {state["end_date"].year}').classes('text-purple-600 font-medium')
                                        ui.label(f'All days will be deducted from your {state["start_date"].year} balance. Consider submitting separate requests for each year.').classes('text-sm opacity-70')

                        # Warning for exceeding available balance
                        # HARD CAP TYPES: These types have fixed annual allocations and CANNOT be overdrafted
                        # - sick: 5 days/year (40 hours) - hard cap, no manager override
                        # - personal: 2 days/year (16 hours) - hard cap, no manager override
                        # - chicago_leave: Chicago Paid Leave ordinance requires accrual-based usage
                        # SOFT CAP TYPES: These allow overdraft with manager approval
                        # - vacation: Manager can approve requests exceeding balance
                        hard_cap_types = ['chicago_leave', 'sick', 'personal']
                        should_block = pto_type.value in hard_cap_types

                        if hours_requested > available:
                            if should_block:
                                # BLOCK - these types have hard annual caps, no overdraft allowed
                                state['chicago_blocked'] = True  # Using existing state key for submit button logic

                                # Type-specific messaging
                                if pto_type.value == 'chicago_leave':
                                    block_reason = 'Per Chicago ordinance, you can only use time that has been accrued.'
                                elif pto_type.value == 'sick':
                                    block_reason = 'Sick leave has a fixed annual allocation and cannot exceed your balance.'
                                else:  # personal
                                    block_reason = 'Personal days have a fixed annual allocation and cannot exceed your balance.'

                                with ui.card().classes('w-full p-3 mb-2 border-l-4 border-red-500 bg-red-900/20'):
                                    with ui.row().classes('items-start'):
                                        ui.icon('block', color='red').classes('mr-2 mt-1')
                                        with ui.column().classes('gap-0'):
                                            ui.label(f'Cannot request - insufficient balance').classes('text-red-500 font-bold')
                                            ui.label(f'Request exceeds available balance by {fmt_days((hours_requested - available)/8)}').classes('text-red-400 text-sm')
                                            ui.label(block_reason).classes('text-sm opacity-70 mt-1')
                            else:
                                # WARNING only - vacation allows manager override
                                state['chicago_blocked'] = False
                                with ui.card().classes('w-full p-3 mb-2 border-l-4 border-amber-500'):
                                    with ui.row().classes('items-start'):
                                        ui.icon('info', color='amber').classes('mr-2 mt-1')
                                        with ui.column().classes('gap-0'):
                                            ui.label(f'This will use {fmt_days((hours_requested - available)/8)} more than currently available').classes('text-amber-600 font-medium')
                                            ui.label('Your manager can approve requests that exceed your current balance.').classes('text-sm opacity-70')
                        else:
                            state['chicago_blocked'] = False

                    # Check for holidays in the selected date range
                    # Only show full closure holidays (not early close - those are still work days)
                    try:
                        db_check = next(get_db())
                        holidays_in_range = db_check.query(MarketHoliday).filter(
                            MarketHoliday.holiday_date >= state['start_date'],
                            MarketHoliday.holiday_date <= state['end_date'],
                            MarketHoliday.market == 'Federal',
                            ~MarketHoliday.name.contains('Early Close')  # Same filter as count_business_days
                        ).all()
                        db_check.close()

                        if holidays_in_range:
                            with ui.card().classes('w-full p-3 border-l-4 border-blue-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('celebration', color='blue').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        holiday_names = ', '.join([h.name for h in holidays_in_range])
                                        is_plural = len(holidays_in_range) > 1
                                        ui.label(f'Holiday overlap: {holiday_names}').classes('text-blue-600 font-medium')
                                        msg = 'These are company holidays and have been excluded' if is_plural else 'This is a company holiday and has been excluded'
                                        ui.label(f'{msg} from your PTO total.').classes('text-sm opacity-70')
                    except Exception:
                        pass  # Don't block form if holiday check fails

                # Update submit button state after warning check
                try:
                    update_submit_button()
                except NameError:
                    pass  # Function not defined yet during initial setup

            # Submit button container (updated dynamically based on blocking state)
            submit_container = ui.row().classes('w-full justify-between')
            submit_btn_ref = {'btn': None}

            def update_submit_button():
                """Update submit button based on blocking state."""
                submit_container.clear()
                with submit_container:
                    if state['chicago_blocked']:
                        # Disabled submit button for blocked Chicago Safe Leave
                        submit_btn_ref['btn'] = ui.button(
                            'Cannot Submit - Insufficient Balance',
                            icon='block',
                        ).props('color=red disabled')
                    else:
                        submit_btn_ref['btn'] = ui.button(
                            'Submit Request',
                            icon='send',
                            on_click=lambda: submit_request(
                                user['id'],
                                pto_type.value,
                                state['start_date'],
                                state['end_date'],
                                state['is_half_day'],
                                description.value,
                                submit_btn_ref['btn'],
                                state['is_private']
                            )
                        ).props('color=primary')

                    ui.button(
                        'Cancel',
                        icon='close',
                        on_click=go_back
                    ).props('outline')

        # Build initial state
        build_date_selector()
        update_balance_display()
        update_notes_label()
        update_summary()
        update_summary_color()
        update_warning()
        update_submit_button()


def submit_request(user_id, pto_type, start_date, end_date, half_day, description, submit_btn=None, is_private=False):
    """Submit PTO request with validation and database operations."""
    from datetime import datetime

    # Define which types have private notes (other leave types)
    private_notes_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']

    # Automatically make notes private for other leave types
    if pto_type.lower() in private_notes_types:
        is_private = True

    if not start_date or not end_date:
        show_warning_dialog('Missing Dates', 'Please select both a start date and end date for your request.')
        return

    # Show loading state
    if submit_btn:
        submit_btn.props('loading disabled')

    if start_date > end_date:
        show_warning_dialog('Invalid Date Range', 'Start date cannot be after end date. Please adjust your dates.')
        if submit_btn:
            submit_btn.props(remove='loading disabled')
        return

    # Cross-year request check (not allowed)
    if start_date.year != end_date.year:
        show_warning_dialog('Cross-Year Request Not Allowed',
            'PTO requests cannot span multiple years. '
            'Please submit separate requests for each year.')
        if submit_btn:
            submit_btn.props(remove='loading disabled')
        return

    # Future year requests handling
    current_year = date.today().year
    current_month = date.today().month
    is_future_year = start_date.year > current_year

    # Track if this is a vacation rollover request
    is_vacation_rollover = False

    if is_future_year:
        # Non-vacation balance types: NOT allowed for future years
        non_vacation_balance_types = ['sick', 'personal', 'chicago_leave']
        if pto_type.lower() in non_vacation_balance_types:
            show_warning_dialog('Future Year Request Not Allowed',
                f'{pto_type.replace("_", " ").title()} requests cannot be submitted for future years. '
                'Please submit your request when the new year begins.')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        # Vacation rollover: Only allowed in December for January of next year
        if pto_type.lower() == 'vacation':
            # Must be December to request rollover
            if current_month != 12:
                show_warning_dialog('Vacation Rollover Not Available',
                    'Vacation rollover requests can only be submitted in December. '
                    'Please wait until December to request vacation time for next year.')
                if submit_btn:
                    submit_btn.props(remove='loading disabled')
                return

            # Must be for January only
            if start_date.month != 1 or end_date.month != 1:
                show_warning_dialog('Vacation Rollover - January Only',
                    'Vacation rollover can only be used in January of the new year. '
                    'Please select dates in January only.')
                if submit_btn:
                    submit_btn.props(remove='loading disabled')
                return

            # Must have vacation balance in current year
            db_rollover_check = next(get_db())
            try:
                from src.models import PTOBalance
                balance = db_rollover_check.query(PTOBalance).filter(
                    PTOBalance.user_id == user_id,
                    PTOBalance.year == current_year
                ).first()

                if balance:
                    vacation_available = (
                        float(balance.vacation_total or 0) +
                        float(balance.vacation_carryover or 0) -
                        float(balance.vacation_used or 0) -
                        float(balance.vacation_pending or 0)
                    )
                else:
                    vacation_available = 0

                if vacation_available <= 0:
                    show_warning_dialog('No Vacation Balance',
                        f'You have no available vacation time in {current_year} to roll over. '
                        'Vacation rollover requires unused vacation days from the current year.')
                    if submit_btn:
                        submit_btn.props(remove='loading disabled')
                    return

                # Check if requesting more days than available
                if half_day:
                    days_requested = 0.5
                else:
                    days_requested = count_business_days(start_date, end_date)
                hours_requested = days_requested * 8

                if hours_requested > vacation_available:
                    show_warning_dialog('Insufficient Vacation Balance',
                        f'You are requesting {days_requested} days but only have '
                        f'{vacation_available / 8:.1f} days available in {current_year} to roll over.')
                    if submit_btn:
                        submit_btn.props(remove='loading disabled')
                    return

                # All checks passed - this is a valid vacation rollover
                is_vacation_rollover = True

            finally:
                db_rollover_check.close()

    # Maximum date range check (90 calendar days / ~3 months)
    days_diff = (end_date - start_date).days
    if days_diff > 90:
        show_warning_dialog('Date Range Too Large',
            f'The selected range spans {days_diff} days. Please select a shorter range (max ~3 months). '
            'For extended leave, please contact HR.')
        if submit_btn:
            submit_btn.props(remove='loading disabled')
        return

    # WFH date restriction: only within 1 week allowed (employees only)
    if pto_type.lower() == 'work_from_home':
        one_week_out = date.today() + timedelta(days=7)
        if start_date > one_week_out:
            show_warning_dialog('WFH Time Limit', 'Work From Home requests can only be submitted for dates within the next 7 days.')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

    # Chicago Leave - block if exceeding accrued balance (per city ordinance)
    if pto_type.lower() == 'chicago_leave':
        db_chicago_check = next(get_db())
        try:
            from src.models import PTOBalance
            balance = db_chicago_check.query(PTOBalance).filter(
                PTOBalance.user_id == user_id,
                PTOBalance.year == start_date.year
            ).first()

            if balance:
                # Get Chicago Leave available balance (uses chicago_paid_leave fields)
                chicago_available = float(balance.chicago_paid_leave_available)
                leave_name = 'Chicago Leave'

                if half_day:
                    total_days = 0.5
                else:
                    total_days = count_business_days(start_date, end_date)
                hours_requested = total_days * 8

                if hours_requested > chicago_available:
                    with ui.dialog() as chicago_dialog, ui.card().classes('p-0 max-w-md'):
                        with ui.row().classes('w-full p-4 bg-red-500 text-white items-center'):
                            ui.icon('block', size='md').classes('mr-2')
                            ui.label('Insufficient Accrued Time').classes('text-lg font-bold')
                        with ui.column().classes('p-4 gap-3'):
                            ui.label(f'{leave_name} can only be used after it has been accrued.').classes('text-base')
                            ui.label(f'Requested: {fmt_days(total_days)} ({hours_requested:.0f} hours)').classes('text-sm')
                            ui.label(f'Available: {chicago_available:.0f} hours').classes('text-sm font-semibold')
                            ui.label('Per Chicago ordinance, you accrue 1 hour for every 40 hours worked.').classes('text-sm opacity-70 mt-2')
                            with ui.row().classes('w-full justify-end mt-2'):
                                ui.button('OK', on_click=chicago_dialog.close).props('color=primary')
                    chicago_dialog.open()
                    if submit_btn:
                        submit_btn.props(remove='loading disabled')
                    return
        finally:
            db_chicago_check.close()

    # Block if start or end date is a weekend (server-side safety check)
    # Note: Calendar picker already blocks weekend selection, but this catches bypassed validation
    # Weekends IN BETWEEN dates are fine - they're just excluded from business day count
    weekend_endpoints = []
    if start_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        weekend_endpoints.append(('Start date', start_date.strftime('%A, %b %d')))
    if end_date.weekday() >= 5:
        weekend_endpoints.append(('End date', end_date.strftime('%A, %b %d')))
    if weekend_endpoints:
        with ui.dialog() as weekend_dialog, ui.card().classes('p-0 max-w-md'):
            with ui.row().classes('w-full p-4 bg-amber-500 text-white items-center'):
                ui.icon('weekend', size='md').classes('mr-2')
                ui.label('Weekend Selected').classes('text-lg font-bold')
            with ui.column().classes('p-4 gap-3'):
                ui.label('Start and end dates must be business days.').classes('text-base')
                with ui.column().classes('pl-4'):
                    for label, wd in weekend_endpoints:
                        ui.label(f'• {label}: {wd}').classes('text-sm font-medium')
                ui.label('Please select Monday through Friday for your date range.').classes('text-sm opacity-70 mt-2')
                with ui.row().classes('w-full justify-end mt-2'):
                    ui.button('OK', on_click=weekend_dialog.close).props('color=primary')
        weekend_dialog.open()
        if submit_btn:
            submit_btn.props(remove='loading disabled')
        return

    # NOTE: Holiday handling is done via count_business_days() which excludes
    # holidays from the day count. The inline banner in update_warning() informs
    # users which holidays are excluded. No blocking modal needed - Policy A.
    # See: docs/bugs/BUG-HOLIDAY-MODAL-LOOP.md

    db = None
    try:
        db = next(get_db())

        leave_type = db.query(LeaveType).filter(
            LeaveType.code == pto_type.upper()
        ).first()

        # Only WFH requires a reason - all other leave types have optional notes
        if pto_type.lower() == 'work_from_home' and not description.strip():
            show_warning_dialog('Reason Required', 'Please provide a reason for your Work From Home request in the notes field.')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        user_service = UserService(db)
        employee = user_service.get_user_by_id(user_id)

        if not employee:
            show_warning_dialog('Session Issue', 'We couldn\'t find your account. Please try logging out and back in.')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        accrual_service = AccrualService(db)

        can_use, reason = accrual_service.can_use_leave(employee, pto_type.upper())
        if not can_use:
            leave_name = leave_type.name if leave_type else pto_type
            show_warning_dialog('Cannot Submit Request', f'{leave_name} is not available: {reason}')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        policy = accrual_service.get_policy_for_employee(employee, pto_type.upper())

        # Calculate business days only (Mon-Fri)
        total_days = count_business_days(start_date, end_date)
        if half_day:
            total_days = 0.5
        elif total_days == 0:
            # No business days in range - shouldn't happen with client validation, but check anyway
            with ui.dialog() as dialog, ui.card().classes('p-6'):
                ui.label('No Business Days Selected').classes('text-lg font-bold text-amber-600 mb-2')
                ui.label('The selected date range contains no business days (Mon-Fri).').classes('mb-4')
                ui.label('Please select a range that includes at least one weekday.').classes('text-gray-600 mb-4')
                ui.button('OK', on_click=dialog.close).props('color=primary')
            dialog.open()
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return
        hours_requested = total_days * 8

        if policy and policy.min_increment_hours:
            if hours_requested < float(policy.min_increment_hours):
                show_warning_dialog(
                    'Minimum Hours',
                    f'Your location requires a minimum of {policy.min_increment_hours} hours per request. '
                    'Please adjust your selection.'
                )
                if submit_btn:
                    submit_btn.props(remove='loading disabled')
                return

        # Use PolicyEngine for date validation (centralized policy logic)
        from src.services.policy_engine import PolicyEngine
        policy_engine = PolicyEngine()
        pto_type_str = pto_type.value if hasattr(pto_type, 'value') else str(pto_type)
        date_result = policy_engine.validate_request_dates(start_date, end_date, pto_type_str)

        if not date_result.is_valid:
            show_warning_dialog('Invalid Date', date_result.rejection_reason)
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        # Calculate days for advance notice check
        days_until_start = (start_date - date.today()).days

        # Advance notice reminder (only for future dates) - use non-blocking notification
        if policy and policy.advance_notice_days and policy.advance_notice_days > 0:
            if days_until_start >= 0 and days_until_start < policy.advance_notice_days:
                ui.notify(
                    f'Note: {policy.advance_notice_days} days advance notice is typically preferred, '
                    'but your request will still be submitted.',
                    type='warning',
                    timeout=5000
                )

        pto_service = PTOService(db)

        from src.schemas.pto_schemas import PTORequestCreate
        request_data = PTORequestCreate(
            user_id=user_id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            notes=description if description.strip() else None,
            is_private=is_private
        )

        pto_request = pto_service.create_request(request_data)

        # Log the PTO request submission
        AuditService.log_pto_request(
            db, user_id, employee.username, pto_request.id,
            {'pto_type': pto_type, 'start_date': str(start_date), 'end_date': str(end_date), 'total_days': float(total_days)}
        )

        # create_request() handles auto-approval for managers/admins including balance adjustments
        # Here we just handle emails and notifications
        if pto_request.status == 'approved':
            # Log the auto-approval
            AuditService.log_pto_approve(
                db, user_id, f"{employee.first_name} {employee.last_name}",
                pto_request.id, f"{employee.first_name} {employee.last_name} (self)"
            )

            # Send auto-approval email to employee
            email_service.send_pto_approved(
                employee.email,
                f"{employee.first_name} {employee.last_name}",
                pto_type,
                start_date,
                end_date,
                float(total_days),
                f"{employee.first_name} {employee.last_name} (auto-approved)"
            )

            show_success_dialog('Request Approved', 'PTO request approved automatically!', on_close=lambda: ui.navigate.to('/dashboard'))
            return  # Exit early, navigation handled by dialog
        else:
            # Send confirmation email to employee
            email_service.send_pto_submitted(
                employee.email,
                f"{employee.first_name} {employee.last_name}",
                pto_type,
                start_date,
                end_date,
                float(total_days)
            )

            # Send notification to manager if employee has a department with a manager
            if employee.department and employee.department.manager:
                manager = employee.department.manager
                email_service.send_pending_request_notification(
                    manager.email,
                    f"{manager.first_name} {manager.last_name}",
                    f"{employee.first_name} {employee.last_name}",
                    pto_type,
                    start_date,
                    end_date,
                    float(total_days)
                )

            # Show appropriate success message for rollover vs regular request
            if is_vacation_rollover:
                show_success_dialog('Vacation Rollover Submitted',
                    f'Your vacation rollover request for January {start_date.year} has been submitted. '
                    f'This will be deducted from your {current_year} balance once approved.',
                    on_close=lambda: ui.navigate.to('/dashboard'))
            else:
                show_success_dialog('Request Submitted', 'PTO request submitted for approval', on_close=lambda: ui.navigate.to('/dashboard'))

    except Exception as e:
        # Show a friendlier error message
        error_msg = str(e)
        if 'more than 7 days' in error_msg.lower() or 'days ago' in error_msg.lower():
            # This shouldn't happen with UI validation, but just in case
            show_warning_dialog('Invalid Date', error_msg)
        else:
            show_warning_dialog(
                'Unable to Submit',
                f'We couldn\'t process your request: {error_msg}. Please try again or contact your manager for assistance.'
            )
        if submit_btn:
            submit_btn.props(remove='loading disabled')

    finally:
        if db:
            db.close()
