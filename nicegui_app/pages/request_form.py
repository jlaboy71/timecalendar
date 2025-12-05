from nicegui import ui, app
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.balance_service import BalanceService
from src.services.user_service import UserService
from src.database import get_db
from src.models.leave_type import LeaveType
from src.models.pto_request import PTORequest
from datetime import date, timedelta
from decimal import Decimal
from nicegui_app.logo import LOGO_DATA_URL


def request_form_page():
    """PTO request form page with improved UX and intuitive date selection."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

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
        current_balance = balance_service.get_or_create_balance(user['id'], date.today().year)

        pending_requests = db.query(PTORequest).filter(
            PTORequest.user_id == user['id'],
            PTORequest.status == 'pending'
        ).all()

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

    # State management
    state = {
        'start_date': prefill_date or date.today(),
        'end_date': prefill_date or date.today(),
        'is_single_day': True,
        'is_half_day': False,
    }

    # ============ MAIN PAGE LAYOUT ============
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):

        # Header with logo and back button
        with ui.column().classes('gap-2 mb-4'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat round')
                ui.label('NEW PTO REQUEST').classes('text-xl font-bold ml-2').style('color: #5a6a72;')

        # Show notice if date was pre-filled from calendar
        if prefill_date:
            with ui.card().classes('w-full mb-4 p-3 border-l-4 border-blue-500'):
                with ui.row().classes('items-center'):
                    ui.icon('event', color='blue').classes('mr-2')
                    ui.label(f'Pre-selected: {prefill_date.strftime("%A, %B %d, %Y")}').classes('text-blue-500')

        # ============ STEP 1: LEAVE TYPE ============
        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">1</span>', sanitize=False)
                ui.label('Select Leave Type').classes('text-lg font-semibold')

            pto_type = ui.select(
                leave_type_options,
                label='Leave Type',
                value='vacation' if 'vacation' in leave_type_options else list(leave_type_options.keys())[0] if leave_type_options else None
            ).classes('w-full')

            # Balance display for selected type
            balance_row = ui.row().classes('w-full mt-3 p-3 rounded-lg justify-around').style('border: 1px solid rgba(128,128,128,0.3)')

            def get_balance_for_type(leave_type_code):
                """Get available, used, and pending hours for a leave type."""
                if not leave_type_code:
                    return 0, 0, 0, 0

                code = leave_type_code.upper()
                if code == 'VACATION':
                    total = float(current_balance.vacation_total or 0)
                    used = float(current_balance.vacation_used or 0)
                    pending = float(current_balance.vacation_pending or 0)
                    carryover = float(current_balance.vacation_carryover or 0)
                elif code == 'SICK':
                    total = float(current_balance.sick_total or 0)
                    used = float(current_balance.sick_used or 0)
                    pending = 0
                    carryover = float(current_balance.sick_carryover or 0)
                elif code == 'PERSONAL':
                    total = float(current_balance.personal_total or 0)
                    used = float(current_balance.personal_used or 0)
                    pending = 0
                    carryover = float(current_balance.personal_carryover or 0)
                else:
                    return 0, 0, 0, 0

                available = total + carryover - used - pending
                return total + carryover, used, pending, max(0, available)

            def update_balance_display():
                balance_row.clear()
                with balance_row:
                    if not pto_type.value:
                        ui.label('Select a leave type').classes('opacity-60')
                        return

                    total, used, pending, available = get_balance_for_type(pto_type.value)

                    # Available
                    with ui.column().classes('items-center'):
                        color = 'text-green-500' if available >= 16 else ('text-amber-500' if available > 0 else 'text-red-500')
                        ui.label(f'{available/8:.1f}').classes(f'text-2xl font-bold {color}')
                        ui.label('days available').classes('text-xs opacity-60')

                    ui.element('div').classes('w-px h-10').style('background: rgba(128,128,128,0.3)')

                    # Used
                    with ui.column().classes('items-center'):
                        ui.label(f'{used/8:.1f}').classes('text-xl font-medium opacity-70')
                        ui.label('days used').classes('text-xs opacity-60')

                    if pending > 0:
                        ui.element('div').classes('w-px h-10').style('background: rgba(128,128,128,0.3)')
                        with ui.column().classes('items-center'):
                            ui.label(f'{pending/8:.1f}').classes('text-xl font-medium text-amber-500')
                            ui.label('pending').classes('text-xs opacity-60')

        # ============ STEP 2: DATE SELECTION ============
        with ui.card().classes('w-full mb-4'):
            with ui.row().classes('items-center mb-3'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">2</span>', sanitize=False)
                ui.label('Select Date(s)').classes('text-lg font-semibold')

            # Single day vs Date range toggle
            with ui.row().classes('w-full mb-4 gap-2'):
                single_day_btn = ui.button('Single Day', on_click=lambda: set_date_mode(True)).classes('flex-1')
                range_btn = ui.button('Date Range', on_click=lambda: set_date_mode(False)).classes('flex-1')

            # Date selection container
            date_selection_container = ui.column().classes('w-full')

            # Summary display (updates in real-time)
            summary_container = ui.row().classes('w-full mt-4 p-3 rounded-lg justify-around items-center border-l-4 border-blue-500')

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
                        # SINGLE DAY MODE - Simple and clear
                        ui.label('Pick your day off:').classes('text-sm opacity-70 mb-2')

                        # Quick select buttons
                        with ui.row().classes('w-full gap-2 mb-3 flex-wrap'):
                            def set_single_date(d):
                                state['start_date'] = d
                                state['end_date'] = d
                                calendar.value = d.isoformat()
                                update_summary()

                            ui.button('Today', on_click=lambda: set_single_date(date.today())).props('size=sm outline')
                            ui.button('Tomorrow', on_click=lambda: set_single_date(date.today() + timedelta(days=1))).props('size=sm outline')

                            # Next Monday
                            days_until_monday = (7 - date.today().weekday()) % 7
                            if days_until_monday == 0:
                                days_until_monday = 7
                            next_monday = date.today() + timedelta(days=days_until_monday)
                            ui.button('Next Monday', on_click=lambda: set_single_date(next_monday)).props('size=sm outline')

                        def on_single_date_change(e):
                            if e.value:
                                picked = date.fromisoformat(e.value) if isinstance(e.value, str) else e.value
                                state['start_date'] = picked
                                state['end_date'] = picked
                                update_summary()

                        calendar = ui.date(
                            value=state['start_date'].isoformat(),
                            on_change=on_single_date_change
                        ).classes('w-full')

                        # Half-day option (only for single day)
                        with ui.row().classes('w-full mt-3 items-center'):
                            def on_half_day_change(e):
                                state['is_half_day'] = e.value
                                update_summary()

                            ui.switch('Half Day (4 hours)', value=state['is_half_day'], on_change=on_half_day_change)

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
                                        update_summary()

                                start_calendar = ui.date(
                                    value=state['start_date'].isoformat(),
                                    on_change=on_start_change
                                ).classes('w-full')

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

                                end_calendar = ui.date(
                                    value=state['end_date'].isoformat(),
                                    on_change=on_end_change
                                ).classes('w-full')

                        # Quick range buttons
                        with ui.row().classes('w-full gap-2 mt-3 flex-wrap'):
                            def set_range(start, end):
                                state['start_date'] = start
                                state['end_date'] = end
                                start_calendar.value = start.isoformat()
                                end_calendar.value = end.isoformat()
                                update_summary()

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

                    _, _, _, available = get_balance_for_type(pto_type.value)
                    remaining = available - hours_requested

                    # Date display
                    with ui.column().classes('items-center'):
                        ui.icon('event', color='blue').classes('text-2xl')
                        if state['start_date'] == state['end_date']:
                            ui.label(state['start_date'].strftime('%b %d, %Y')).classes('font-medium')
                            if state['is_half_day']:
                                ui.label('Half Day').classes('text-xs opacity-60')
                        else:
                            ui.label(f"{state['start_date'].strftime('%b %d')} - {state['end_date'].strftime('%b %d, %Y')}").classes('font-medium')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Hours/Days requested
                    with ui.column().classes('items-center'):
                        ui.label(f'{total_days:.1f}' if total_days != int(total_days) else f'{int(total_days)}').classes('text-2xl font-bold text-blue-600')
                        ui.label(f'day{"s" if total_days != 1 else ""} ({hours_requested:.0f} hrs)').classes('text-xs opacity-60')

                    ui.icon('arrow_forward').classes('opacity-40')

                    # Balance after
                    with ui.column().classes('items-center'):
                        if remaining < 0:
                            ui.label(f'{remaining/8:.1f}').classes('text-2xl font-bold text-red-600')
                            ui.label('OVER LIMIT').classes('text-xs text-red-600 font-bold')
                        else:
                            color = 'text-green-600' if remaining >= 16 else 'text-amber-600'
                            ui.label(f'{remaining/8:.1f}').classes(f'text-2xl font-bold {color}')
                            ui.label('days remaining').classes('text-xs opacity-60')

            # Initialize the date mode buttons
            single_day_btn.props('color=primary')
            range_btn.props('color=grey')

        # ============ STEP 3: NOTES ============
        with ui.card().classes('w-full mb-4 p-3'):
            with ui.row().classes('items-center mb-2'):
                ui.html('<span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-2">3</span>', sanitize=False)
                notes_header = ui.label('Notes (optional)').classes('text-lg font-semibold')

            description = ui.input(
                placeholder='e.g., Family vacation, doctor appointment...'
            ).classes('w-full').props('dense')

            # Update header if documentation required
            def update_notes_label():
                if pto_type.value in requires_doc_types:
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
                _, _, _, available = get_balance_for_type(pto_type.value)

                if hours_requested > available:
                    with warning_container:
                        with ui.card().classes('w-full p-3 border-l-4 border-red-500'):
                            with ui.row().classes('items-center'):
                                ui.icon('warning', color='red').classes('mr-2')
                                ui.label(f'This request exceeds your available balance by {(hours_requested - available)/8:.1f} days').classes('text-red-500')

            with ui.row().classes('w-full gap-4'):
                ui.button(
                    'Submit Request',
                    icon='send',
                    on_click=lambda: submit_request(
                        user['id'],
                        pto_type.value,
                        state['start_date'],
                        state['end_date'],
                        state['is_half_day'],
                        description.value
                    )
                ).classes('flex-1').props('color=primary size=lg')

                ui.button(
                    'Cancel',
                    icon='close',
                    on_click=lambda: ui.navigate.to('/dashboard')
                ).classes('flex-1').props('outline size=lg')

        # Wire up all the update handlers
        def on_type_change():
            update_balance_display()
            update_notes_label()
            update_summary()
            update_warning()

        pto_type.on('update:model-value', lambda e: on_type_change())

        # Build initial state
        build_date_selector()
        update_balance_display()
        update_notes_label()
        update_summary()
        update_warning()


def submit_request(user_id, pto_type, start_date, end_date, half_day, description):
    """Submit PTO request with validation and database operations."""
    from datetime import datetime

    if not start_date or not end_date:
        ui.notify('Start date and end date are required', type='negative')
        return

    if start_date > end_date:
        ui.notify('Start date cannot be after end date', type='negative')
        return

    db = None
    try:
        db = next(get_db())

        leave_type = db.query(LeaveType).filter(
            LeaveType.code == pto_type.upper()
        ).first()

        if leave_type and leave_type.requires_documentation and not description.strip():
            ui.notify(f'Description is required for {leave_type.name}', type='negative')
            return

        user_service = UserService(db)
        employee = user_service.get_user_by_id(user_id)

        if not employee:
            ui.notify('User not found', type='negative')
            return

        accrual_service = AccrualService(db)

        can_use, reason = accrual_service.can_use_leave(employee, pto_type.upper())
        if not can_use:
            ui.notify(f'Cannot use {leave_type.name if leave_type else pto_type}: {reason}', type='negative')
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
            half_day=half_day,
            description=description if description.strip() else None
        )

        pto_request = pto_service.create_request(request_data)

        # Auto-approve for managers, admins, and superadmins
        if employee.role in ['manager', 'admin', 'superadmin']:
            pto_request.status = 'approved'
            pto_request.approved_by = user_id
            pto_request.approved_at = datetime.now()
            db.commit()

            # Move from pending to used for vacation type
            if pto_type.lower() == 'vacation':
                from src.services.balance_service import BalanceService
                balance_service = BalanceService(db)
                balance = balance_service.get_or_create_balance(user_id, start_date.year)
                balance_service.adjust_vacation_used(balance.id, -total_days, is_pending=True)
                balance_service.adjust_vacation_used(balance.id, total_days, is_pending=False)

            ui.notify('PTO request approved automatically!', type='positive')
        else:
            ui.notify('PTO request submitted for approval', type='positive')

        ui.navigate.to('/dashboard')

    except Exception as e:
        ui.notify(f'Error submitting request: {str(e)}', type='negative')

    finally:
        if db:
            db.close()
