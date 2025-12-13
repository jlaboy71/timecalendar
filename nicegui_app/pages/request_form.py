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
from datetime import date, datetime, timedelta
from decimal import Decimal
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from nicegui_app.components.formatting import fmt_days, format_days_hours


def request_form_page():
    """PTO request form page with improved UX and intuitive date selection."""

    apply_dark_mode()

    # Check if user is logged in
    user = app.storage.general.get('user')
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

        # Query market holidays for date validation (current year and next)
        current_year = date.today().year
        holidays = db.query(MarketHoliday).filter(
            MarketHoliday.holiday_date >= date(current_year, 1, 1),
            MarketHoliday.holiday_date <= date(current_year + 1, 12, 31)
        ).all()
        # Get unique dates as ISO strings for JavaScript validation
        holiday_dates_set = set(h.holiday_date.isoformat() for h in holidays)
        holiday_dates_js = str(list(holiday_dates_set)).replace("'", '"')

        # Get manager info from department
        manager_name = None
        if current_user and current_user.department and current_user.department.manager:
            manager = current_user.department.manager
            manager_name = f"{manager.first_name} {manager.last_name}"
    finally:
        db.close()

    # Check for pre-filled date from calendar
    prefill_date_str = app.storage.general.pop('prefill_pto_date', None)
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
    }

    # ============ MAIN PAGE LAYOUT ============
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):

        # Header with greeting
        page_header(title='NEW PTO REQUEST', show_back=False)

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
            'other': {'color': 'grey', 'bg': 'bg-grey-500', 'text': 'text-grey-600', 'border': 'border-grey-500'},
        }

        # Primary types (with dedicated buttons) vs Other types
        primary_types = ['vacation', 'sick', 'personal', 'work_from_home']
        other_types = {k: v for k, v in leave_type_options.items() if k not in primary_types}

        # State for selected type
        selected_type = {'value': 'vacation' if 'vacation' in leave_type_options else list(leave_type_options.keys())[0] if leave_type_options else None}

        # Calendar widget references for dynamic color updates
        calendar_widgets = {}
        # Half-day container reference for visibility control
        half_day_container = {'ref': None}
        # Date range button reference for WFH single-day enforcement
        date_range_btn = {'ref': None}

        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">1</span>', sanitize=False)
                ui.label('Select Leave Type').classes('text-lg font-semibold')

            # Primary type buttons
            with ui.row().classes('w-full gap-2 mb-2'):
                # Create button references
                type_buttons = {}

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
                        update_date_mode_buttons()
                        update_notes_label()
                    return handler

                # Vacation button
                if 'vacation' in leave_type_options:
                    type_buttons['vacation'] = ui.button(
                        'Vacation',
                        icon='beach_access',
                        on_click=create_type_handler('vacation')
                    ).classes('flex-1')

                # Sick button
                if 'sick' in leave_type_options:
                    type_buttons['sick'] = ui.button(
                        'Sick',
                        icon='local_hospital',
                        on_click=create_type_handler('sick')
                    ).classes('flex-1')

                # Personal button
                if 'personal' in leave_type_options:
                    type_buttons['personal'] = ui.button(
                        'Personal',
                        icon='person',
                        on_click=create_type_handler('personal')
                    ).classes('flex-1')

                # Work From Home button (red)
                if 'work_from_home' in leave_type_options:
                    type_buttons['work_from_home'] = ui.button(
                        'WFH',
                        icon='home_work',
                        on_click=create_type_handler('work_from_home')
                    ).classes('flex-1')

            # Other types dropdown (if any exist)
            other_select = None
            if other_types:
                with ui.row().classes('w-full gap-2 items-center'):
                    type_buttons['other'] = ui.button(
                        'Other',
                        icon='more_horiz',
                        on_click=lambda: select_other_type()
                    ).classes('shrink-0')

                    other_select = ui.select(
                        other_types,
                        label='Other Leave Type',
                        value=None
                    ).classes('flex-1')

                    def on_other_select_change(e):
                        if e.value:
                            selected_type['value'] = e.value
                            update_type_button_styles()
                            update_balance_display()
                            update_summary_color()
                            update_calendar_colors()
                            update_half_day_visibility()
                            update_date_mode_buttons()
                            update_notes_label()

                    other_select.on('update:model-value', on_other_select_change)

                    def select_other_type():
                        if other_select and other_select.value:
                            selected_type['value'] = other_select.value
                        elif other_types:
                            # Select first other type
                            first_other = list(other_types.keys())[0]
                            other_select.value = first_other
                            selected_type['value'] = first_other
                        update_type_button_styles()
                        update_balance_display()
                        update_summary_color()
                        update_calendar_colors()
                        update_half_day_visibility()
                        update_date_mode_buttons()
                        update_notes_label()

            def update_type_button_styles():
                """Update button styles based on current selection."""
                current = selected_type['value']
                is_other = current not in primary_types

                for type_code, btn in type_buttons.items():
                    if type_code == 'other':
                        # Other button selected when current type is not primary
                        if is_other:
                            btn.props(remove='outline')
                            btn.props('color=grey')
                        else:
                            btn.props(remove='color=grey color=blue color=green color=purple color=red')
                            btn.props('outline')
                    elif type_code == current:
                        # Selected primary button
                        color = type_colors.get(type_code, {}).get('color', 'primary')
                        btn.props(remove='outline')
                        btn.props(f'color={color}')
                    else:
                        # Unselected primary button
                        btn.props(remove='color=blue color=green color=purple color=red color=grey')
                        btn.props('outline')

                # Clear other select if primary type selected
                if not is_other and other_select:
                    other_select.value = None

            def update_half_day_visibility():
                """Show/hide half-day option based on selected type."""
                if half_day_container['ref']:
                    # WFH doesn't support half-day
                    if selected_type['value'] == 'work_from_home':
                        half_day_container['ref'].set_visibility(False)
                    else:
                        half_day_container['ref'].set_visibility(True)

            def update_date_mode_buttons():
                """Enable/disable date range button based on selected type. WFH is single-day only."""
                if date_range_btn['ref']:
                    if selected_type['value'] == 'work_from_home':
                        # WFH is single-day only - disable date range and force single day
                        date_range_btn['ref'].props('disabled')
                        date_range_btn['ref'].tooltip('WFH requests are limited to single day only')
                        # Force single day mode if not already
                        if not state['is_single_day']:
                            state['is_single_day'] = True
                            state['end_date'] = state['start_date']
                            build_date_selector()
                            update_summary()
                    else:
                        date_range_btn['ref'].props(remove='disabled')
                        date_range_btn['ref'].tooltip('')

            # Initialize button styles
            update_type_button_styles()

            # Create a mock pto_type object for compatibility with existing code
            class PTOTypeProxy:
                @property
                def value(self):
                    return selected_type['value']

            pto_type = PTOTypeProxy()

            # Balance display for selected type
            balance_row = ui.row().classes('w-full mt-3 p-3 rounded-lg justify-around').style('border: 1px solid rgba(128,128,128,0.3)')

            def get_balance_for_type(leave_type_code, for_year=None):
                """Get available, used, and pending hours for a leave type.

                Args:
                    leave_type_code: Type of leave (vacation, sick, personal)
                    for_year: Year to get balance for (defaults to selected start date year)

                Returns:
                    Tuple of (total, used, pending, available, balance_exists)
                """
                if not leave_type_code:
                    return 0, 0, 0, 0, False

                # Use the start date year if no year specified
                target_year = for_year or state['start_date'].year

                # Get or create balance for the target year
                db_session = next(get_db())
                try:
                    bal_svc = BalanceService(db_session)
                    balance = bal_svc.get_or_create_balance(_user_id, target_year)

                    code = leave_type_code.upper()
                    if code == 'VACATION':
                        total = float(balance.vacation_total or 0)
                        used = float(balance.vacation_used or 0)
                        pending = float(balance.vacation_pending or 0)
                        carryover = float(balance.vacation_carryover or 0)
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
                    else:
                        return 0, 0, 0, 0, False

                    available = total + carryover - used - pending
                    # Check if balance has been allocated (total > 0)
                    balance_allocated = total > 0
                    return total + carryover, used, pending, available, balance_allocated
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
                balance_row.clear()
                with balance_row:
                    if not pto_type.value:
                        ui.label('Select a leave type').classes('opacity-60')
                        return

                    # WFH has no balance - show usage count only
                    if pto_type.value == 'work_from_home':
                        wfh_days = get_wfh_usage()
                        with ui.column().classes('items-center'):
                            ui.icon('home_work', color='red').classes('text-2xl')
                            ui.label(f'{wfh_days:.1f}' if wfh_days % 1 else f'{int(wfh_days)}').classes('text-xl font-bold text-red-500')
                            ui.label('DAYS USED').classes('text-xs opacity-60')
                        with ui.column().classes('items-center ml-6'):
                            ui.label('No balance limit').classes('text-sm opacity-60')
                            ui.label('Requires manager approval').classes('text-xs opacity-40')
                        return

                    total, used, pending, available, balance_allocated = get_balance_for_type(pto_type.value)
                    target_year = state['start_date'].year

                    # Show year indicator if different from current year
                    with ui.column().classes('items-center'):
                        if target_year != date.today().year:
                            ui.label(f'{target_year}').classes('text-xs font-bold text-blue-500')

                        # Available
                        color = 'text-green-500' if available >= 16 else ('text-amber-500' if available > 0 else 'text-red-500')
                        avail_display, avail_tooltip = format_days_hours(available)
                        ui.label(avail_display).classes(f'text-xl font-bold {color}').tooltip(avail_tooltip)
                        if not balance_allocated and target_year != date.today().year:
                            ui.label('not yet allocated').classes('text-xs text-amber-500')
                        else:
                            ui.label('AVAILABLE').classes('text-xs opacity-60')

                    ui.element('div').classes('w-px h-10').style('background: rgba(128,128,128,0.3)')

                    # Used
                    with ui.column().classes('items-center'):
                        used_display, used_tooltip = format_days_hours(used)
                        ui.label(used_display).classes('text-lg font-medium opacity-70').tooltip(used_tooltip)
                        ui.label('USED').classes('text-xs opacity-60')

                    if pending > 0:
                        ui.element('div').classes('w-px h-10').style('background: rgba(128,128,128,0.3)')
                        with ui.column().classes('items-center'):
                            pending_display, pending_tooltip = format_days_hours(pending)
                            ui.label(pending_display).classes('text-lg font-medium text-amber-500').tooltip(pending_tooltip)
                            ui.label('PENDING').classes('text-xs opacity-60')

        # ============ STEP 2: DATE SELECTION ============
        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">2</span>', sanitize=False)
                ui.label('Select Date(s)').classes('text-lg font-semibold')

            # Single day vs Date range toggle
            with ui.row().classes('w-full mb-4 gap-2'):
                single_day_btn = ui.button('Single Day', on_click=lambda: set_date_mode(True)).classes('flex-1')
                range_btn = ui.button('Date Range', on_click=lambda: set_date_mode(False)).classes('flex-1')
                date_range_btn['ref'] = range_btn  # Store reference for WFH single-day enforcement

            # Date selection container
            date_selection_container = ui.column().classes('w-full')

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
                }
                new_border = color_map.get(current, 'border-grey-500')
                summary_container.classes(remove='border-blue-500 border-green-500 border-purple-500 border-red-500 border-grey-500')
                summary_container.classes(add=new_border)

            def update_calendar_colors():
                """Update calendar accent colors based on selected PTO type."""
                current = selected_type['value']
                # Use grey for any non-primary type (other types like bereavement, fmla, etc.)
                if current in primary_types:
                    cal_color = type_colors.get(current, {}).get('color', 'blue')
                else:
                    cal_color = 'grey'
                for key, cal in calendar_widgets.items():
                    if cal:
                        cal.props(remove='color=blue color=green color=purple color=red color=grey')
                        cal.props(f'color={cal_color}')

            def set_date_mode(is_single):
                state['is_single_day'] = is_single
                if is_single:
                    state['end_date'] = state['start_date']
                    single_day_btn.props('color=primary')
                    range_btn.props('color=grey')
                else:
                    single_day_btn.props('color=grey')
                    range_btn.props('color=primary')
                build_date_selector()
                update_summary()

            def build_date_selector():
                date_selection_container.clear()
                with date_selection_container:
                    if state['is_single_day']:
                        # SINGLE DAY MODE
                        def on_single_date_change(e):
                            if e.value:
                                picked = date.fromisoformat(e.value) if isinstance(e.value, str) else e.value
                                state['start_date'] = picked
                                state['end_date'] = picked
                                update_balance_display()
                                update_summary()
                                update_warning()

                        # Set minimum date to today, exclude weekends and market holidays
                        # Get initial color based on selected type (grey for non-primary types)
                        cal_color = type_colors.get(selected_type['value'], {}).get('color', 'grey') if selected_type['value'] in primary_types else 'grey'
                        calendar = ui.date(
                            value=state['start_date'].isoformat(),
                            on_change=on_single_date_change
                        ).props(f'color={cal_color} :options="date => {{ const d = new Date(date); const day = d.getUTCDay(); const holidays = {holiday_dates_js}; return date >= \'{date.today().isoformat()}\' && day !== 0 && day !== 6 && !holidays.includes(date); }}"').classes('w-full')
                        calendar_widgets['single'] = calendar

                        # Half-day option (only for single day, not for WFH)
                        half_day_row = ui.row().classes('w-full mt-3 items-center')
                        half_day_container['ref'] = half_day_row
                        with half_day_row:
                            def on_half_day_change(e):
                                state['is_half_day'] = e.value
                                update_summary()
                                update_warning()

                            ui.switch('Half Day (4 hours)', value=state['is_half_day'], on_change=on_half_day_change)

                        # Hide half-day for WFH
                        if selected_type['value'] == 'work_from_home':
                            half_day_row.set_visibility(False)

                    else:
                        # DATE RANGE MODE
                        ui.label('Select start and end dates:').classes('text-sm opacity-70 mb-2')

                        # Reset half day when in range mode
                        state['is_half_day'] = False

                        with ui.row().classes('w-full gap-4'):
                            with ui.column().classes('flex-1'):
                                ui.label('Start Date').classes('text-sm font-medium mb-1')

                                def on_start_change(e):
                                    if e.value:
                                        picked = date.fromisoformat(e.value) if isinstance(e.value, str) else e.value
                                        state['start_date'] = picked
                                        if state['end_date'] < picked:
                                            state['end_date'] = picked
                                            end_calendar.value = picked.isoformat()
                                        update_balance_display()
                                        update_summary()
                                        update_warning()

                                # Set minimum date to today, exclude weekends and market holidays
                                cal_color = type_colors.get(selected_type['value'], {}).get('color', 'grey') if selected_type['value'] in primary_types else 'grey'
                                start_calendar = ui.date(
                                    value=state['start_date'].isoformat(),
                                    on_change=on_start_change
                                ).props(f'color={cal_color} :options="date => {{ const d = new Date(date); const day = d.getUTCDay(); const holidays = {holiday_dates_js}; return date >= \'{date.today().isoformat()}\' && day !== 0 && day !== 6 && !holidays.includes(date); }}"').classes('w-full')
                                calendar_widgets['start'] = start_calendar

                            with ui.column().classes('flex-1'):
                                ui.label('End Date').classes('text-sm font-medium mb-1')

                                def on_end_change(e):
                                    if e.value:
                                        picked = date.fromisoformat(e.value) if isinstance(e.value, str) else e.value
                                        if picked >= state['start_date']:
                                            state['end_date'] = picked
                                        else:
                                            state['end_date'] = state['start_date']
                                            end_calendar.value = state['start_date'].isoformat()
                                        update_summary()
                                        update_warning()

                                # Set minimum date to today, exclude weekends and market holidays
                                cal_color = type_colors.get(selected_type['value'], {}).get('color', 'grey') if selected_type['value'] in primary_types else 'grey'
                                end_calendar = ui.date(
                                    value=state['end_date'].isoformat(),
                                    on_change=on_end_change
                                ).props(f'color={cal_color} :options="date => {{ const d = new Date(date); const day = d.getUTCDay(); const holidays = {holiday_dates_js}; return date >= \'{date.today().isoformat()}\' && day !== 0 && day !== 6 && !holidays.includes(date); }}"').classes('w-full')
                                calendar_widgets['end'] = end_calendar

                        # Quick range buttons
                        with ui.row().classes('w-full gap-2 mt-3 flex-wrap'):
                            def set_range(start, end):
                                state['start_date'] = start
                                state['end_date'] = end
                                start_calendar.value = start.isoformat()
                                end_calendar.value = end.isoformat()
                                update_balance_display()
                                update_summary()
                                update_warning()

                            # This week (remaining days)
                            today = date.today()
                            friday = today + timedelta(days=(4 - today.weekday()))
                            if friday > today:
                                ui.button('Rest of Week', on_click=lambda: set_range(today, friday)).props('size=sm outline')

                            # Next full week
                            next_mon = today + timedelta(days=(7 - today.weekday()))
                            next_fri = next_mon + timedelta(days=4)
                            ui.button('Next Week (Mon-Fri)', on_click=lambda: set_range(next_mon, next_fri)).props('size=sm outline')

            def update_summary():
                summary_container.clear()
                with summary_container:
                    # Calculate request details
                    if state['is_half_day']:
                        total_days = 0.5
                    else:
                        total_days = (state['end_date'] - state['start_date']).days + 1
                    hours_requested = total_days * 8

                    is_wfh = pto_type.value == 'work_from_home'
                    icon_color = 'red' if is_wfh else 'blue'
                    text_color = 'text-red-600' if is_wfh else 'text-blue-600'

                    # Date display
                    with ui.column().classes('items-center'):
                        ui.icon('event', color=icon_color).classes('text-2xl')
                        if state['start_date'] == state['end_date']:
                            ui.label(state['start_date'].strftime('%b %d, %Y')).classes('font-medium')
                            if state['is_half_day']:
                                ui.label('Half Day').classes('text-xs opacity-60')
                        else:
                            ui.label(f"{state['start_date'].strftime('%b %d')} - {state['end_date'].strftime('%b %d, %Y')}").classes('font-medium')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Hours/Days requested
                    with ui.column().classes('items-center'):
                        ui.label(fmt_days(total_days)).classes(f'text-2xl font-bold {text_color}')
                        ui.label(f'day{"s" if total_days != 1 else ""} ({hours_requested:.0f} hrs)').classes('text-xs opacity-60')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Balance after (or WFH indicator)
                    if is_wfh:
                        with ui.column().classes('items-center'):
                            ui.icon('home_work', color='red').classes('text-2xl')
                            ui.label('WFH').classes('text-xs opacity-60')
                    else:
                        _, _, _, available, _ = get_balance_for_type(pto_type.value)
                        remaining = available - hours_requested
                        with ui.column().classes('items-center'):
                            if remaining < 0:
                                ui.label(fmt_days(remaining/8)).classes('text-2xl font-bold text-red-600')
                                ui.label('OVER LIMIT').classes('text-xs text-red-600 font-bold')
                            else:
                                color = 'text-green-600' if remaining >= 16 else 'text-amber-600'
                                ui.label(fmt_days(remaining/8)).classes(f'text-2xl font-bold {color}')
                                ui.label('days remaining').classes('text-xs opacity-60')

            # Initialize the date mode buttons
            single_day_btn.props('color=primary')
            range_btn.props('color=grey')

        # ============ STEP 3: NOTES ============
        with ui.card().classes('w-full mb-4 p-3'):
            with ui.row().classes('items-center mb-2'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">3</span>', sanitize=False)
                notes_header = ui.label('Notes (optional)').classes('text-lg font-semibold')

            description = ui.input().classes('w-full').props('dense')

            # Private toggle - only for managers/admins/superadmins
            if user_role in ['manager', 'admin', 'superadmin']:
                with ui.row().classes('w-full mt-3 items-center gap-2'):
                    def on_private_change(e):
                        state['is_private'] = e.value

                    ui.switch('Keep Private', value=state['is_private'], on_change=on_private_change)
                    ui.label('(Hidden from department calendar)').classes('text-xs opacity-60')

            # Update header if documentation required or WFH (requires reason)
            def update_notes_label():
                if pto_type.value == 'work_from_home':
                    notes_header.text = 'Reason (required)'
                    notes_header.classes('text-lg font-semibold text-red-600', remove='text-gray-600')
                elif pto_type.value in requires_doc_types:
                    notes_header.text = 'Notes (required)'
                    notes_header.classes('text-lg font-semibold text-red-600', remove='text-gray-600')
                else:
                    notes_header.text = 'Notes (optional)'
                    notes_header.classes('text-lg font-semibold', remove='text-red-600')

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
                    total_days = (state['end_date'] - state['start_date']).days + 1
                hours_requested = total_days * 8
                is_wfh = pto_type.value == 'work_from_home'
                _, _, _, available, balance_allocated = get_balance_for_type(pto_type.value)
                target_year = state['start_date'].year

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

                    # Skip balance-related warnings for WFH (no balance system)
                    if not is_wfh:
                        # Warning for unallocated future year balance
                        if not balance_allocated and target_year != date.today().year:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-amber-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('info', color='amber').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'{target_year} PTO balance not yet allocated').classes('text-amber-600 font-medium')
                                        ui.label('Your request will be submitted for manager approval. Balance will be deducted once allocated.').classes('text-sm opacity-70')

                        # Warning for cross-year requests
                        if state['start_date'].year != state['end_date'].year:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-purple-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('calendar_month', color='purple').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Request spans {state["start_date"].year} and {state["end_date"].year}').classes('text-purple-600 font-medium')
                                        ui.label(f'All days will be deducted from your {state["start_date"].year} balance. Consider submitting separate requests for each year.').classes('text-sm opacity-70')

                        # Warning for exceeding available balance
                        if hours_requested > available:
                            with ui.card().classes('w-full p-3 mb-2 border-l-4 border-red-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('warning', color='red').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Request exceeds available balance by {fmt_days((hours_requested - available)/8)} days').classes('text-red-500 font-medium')
                                        ui.label('You may still submit - approval is at manager discretion.').classes('text-sm opacity-70')

                    # Check for holidays in the selected date range
                    try:
                        db_check = next(get_db())
                        holidays_in_range = db_check.query(MarketHoliday).filter(
                            MarketHoliday.holiday_date >= state['start_date'],
                            MarketHoliday.holiday_date <= state['end_date'],
                            MarketHoliday.market == 'Federal'
                        ).all()
                        db_check.close()

                        if holidays_in_range:
                            with ui.card().classes('w-full p-3 border-l-4 border-blue-500'):
                                with ui.row().classes('items-start'):
                                    ui.icon('celebration', color='blue').classes('mr-2 mt-1')
                                    with ui.column().classes('gap-0'):
                                        holiday_names = ', '.join([h.name for h in holidays_in_range])
                                        ui.label(f'Holiday overlap: {holiday_names}').classes('text-blue-600 font-medium')
                                        ui.label('Your selected dates include a company holiday. You may not need to use PTO for this day.').classes('text-sm opacity-70')
                    except Exception:
                        pass  # Don't block form if holiday check fails

            with ui.row().classes('w-full gap-4'):
                submit_btn = ui.button(
                    'Submit Request',
                    icon='send',
                    on_click=lambda: submit_request(
                        user['id'],
                        pto_type.value,
                        state['start_date'],
                        state['end_date'],
                        state['is_half_day'],
                        description.value,
                        submit_btn,
                        state['is_private']
                    )
                ).classes('flex-1').props('color=primary size=lg')

                ui.button(
                    'Cancel',
                    icon='close',
                    on_click=lambda: ui.navigate.to('/dashboard')
                ).classes('flex-1').props('outline size=lg')

        # Build initial state
        build_date_selector()
        update_balance_display()
        update_notes_label()
        update_summary()
        update_summary_color()
        update_warning()


def submit_request(user_id, pto_type, start_date, end_date, half_day, description, submit_btn=None, is_private=False):
    """Submit PTO request with validation and database operations."""
    from datetime import datetime

    if not start_date or not end_date:
        ui.notify('Start date and end date are required', type='negative')
        return

    # Show loading state
    if submit_btn:
        submit_btn.props('loading disabled')

    if start_date > end_date:
        ui.notify('Start date cannot be after end date', type='negative')
        if submit_btn:
            submit_btn.props(remove='loading disabled')
        return

    # WFH date restriction: only within 1 week allowed (employees only)
    if pto_type.lower() == 'work_from_home':
        one_week_out = date.today() + timedelta(days=7)
        if start_date > one_week_out:
            ui.notify('WFH requests are limited to within 1 week', type='negative')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

    db = None
    try:
        db = next(get_db())

        leave_type = db.query(LeaveType).filter(
            LeaveType.code == pto_type.upper()
        ).first()

        # WFH requires a reason
        if pto_type.lower() == 'work_from_home' and not description.strip():
            ui.notify('A reason is required for Work From Home requests', type='negative')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        if leave_type and leave_type.requires_documentation and not description.strip():
            ui.notify(f'Description is required for {leave_type.name}', type='negative')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        user_service = UserService(db)
        employee = user_service.get_user_by_id(user_id)

        if not employee:
            ui.notify('User not found', type='negative')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        accrual_service = AccrualService(db)

        can_use, reason = accrual_service.can_use_leave(employee, pto_type.upper())
        if not can_use:
            ui.notify(f'Cannot use {leave_type.name if leave_type else pto_type}: {reason}', type='negative')
            if submit_btn:
                submit_btn.props(remove='loading disabled')
            return

        policy = accrual_service.get_policy_for_employee(employee, pto_type.upper())

        total_days = (end_date - start_date).days + 1
        if half_day:
            total_days = 0.5
        hours_requested = total_days * 8

        if policy and policy.min_increment_hours:
            if hours_requested < float(policy.min_increment_hours):
                ui.notify(
                    f'Minimum request is {policy.min_increment_hours} hours for your location',
                    type='negative'
                )
                if submit_btn:
                    submit_btn.props(remove='loading disabled')
                return

        if policy and policy.advance_notice_days and policy.advance_notice_days > 0:
            days_until_start = (start_date - date.today()).days
            if days_until_start < policy.advance_notice_days:
                ui.notify(
                    f'Note: {policy.advance_notice_days} days advance notice is typically required',
                    type='warning'
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

            ui.notify('PTO request approved automatically!', type='positive')
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

            ui.notify('PTO request submitted for approval', type='positive')

        ui.navigate.to('/dashboard')

    except Exception as e:
        ui.notify(f'Error submitting request: {str(e)}', type='negative')
        if submit_btn:
            submit_btn.props(remove='loading disabled')

    finally:
        if db:
            db.close()
