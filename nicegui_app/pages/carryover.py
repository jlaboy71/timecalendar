"""Carryover request page for requesting leave balance carryover to next year."""
from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.models.carryover_request import CarryoverRequest
from src.models.leave_type import LeaveType
from src.database import get_db
from datetime import datetime, date
from decimal import Decimal
from nicegui_app.logo import LOGO_DATA_URL


def format_hours_days(hours):
    """Format hours with days equivalent (8 hours = 1 day)."""
    days = hours / 8
    return f'{hours:.1f} hrs ({days:.1f} days)'


def carryover_page():
    """Page for requesting leave balance carryover to next year."""

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

    current_year = date.today().year
    next_year = current_year + 1

    # Get data from database
    db = next(get_db())
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        accrual_service = AccrualService(db)

        current_user = user_service.get_user_by_id(user['id'])
        balance = balance_service.get_or_create_balance(user['id'], current_year)

        # Get leave types that can have carryover
        leave_types = db.query(LeaveType).filter(
            LeaveType.is_active == True,
            LeaveType.deducts_from_balance == True  # Only types with balances
        ).order_by(LeaveType.sort_order).all()

        # Calculate unused balances with full details
        unused_balances = {}
        balance_details = {}
        if balance:
            # Vacation
            vacation_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
            vacation_used = float(balance.vacation_used or 0)
            vacation_pending = float(getattr(balance, 'vacation_pending', 0) or 0)
            vacation_unused = vacation_total - vacation_used - vacation_pending
            if vacation_unused > 0:
                unused_balances['VACATION'] = vacation_unused
                balance_details['VACATION'] = {
                    'total': vacation_total,
                    'used': vacation_used,
                    'pending': vacation_pending,
                    'unused': vacation_unused
                }

            # Sick
            sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
            sick_used = float(balance.sick_used or 0)
            sick_pending = float(getattr(balance, 'sick_pending', 0) or 0)
            sick_unused = sick_total - sick_used - sick_pending
            if sick_unused > 0:
                unused_balances['SICK'] = sick_unused
                balance_details['SICK'] = {
                    'total': sick_total,
                    'used': sick_used,
                    'pending': sick_pending,
                    'unused': sick_unused
                }

            # Personal
            personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
            personal_used = float(balance.personal_used or 0)
            personal_pending = float(getattr(balance, 'personal_pending', 0) or 0)
            personal_unused = personal_total - personal_used - personal_pending
            if personal_unused > 0:
                unused_balances['PERSONAL'] = personal_unused
                balance_details['PERSONAL'] = {
                    'total': personal_total,
                    'used': personal_used,
                    'pending': personal_pending,
                    'unused': personal_unused
                }

        # Get existing carryover requests
        existing_requests = db.query(CarryoverRequest).filter(
            CarryoverRequest.employee_id == user['id'],
            CarryoverRequest.from_year == current_year
        ).order_by(CarryoverRequest.created_at.desc()).all()

        # Build leave type lookup
        leave_type_map = {lt.code: lt for lt in leave_types}

    finally:
        db.close()

    # State for request summary
    selected_type = {'code': None}
    selected_hours = {'value': 0}

    with ui.column().classes('w-full max-w-2xl mx-auto mt-8 p-6'):
        with ui.column().classes('gap-2 mb-2'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            ui.label('REQUEST LEAVE CARRYOVER').classes('text-xl font-bold').style('color: #5a6a72;')
        ui.label(f'Carry unused {current_year} leave balance into {next_year}').classes('opacity-70 mb-6')

        # ============ UNUSED BALANCES CARD ============
        with ui.card().classes('w-full mb-6 p-4 border-l-4 border-blue-500'):
            ui.label(f'Your {current_year} Unused Balances').classes('text-lg font-semibold mb-4')

            if unused_balances:
                with ui.row().classes('w-full justify-around flex-wrap gap-4'):
                    for code, hours in unused_balances.items():
                        leave_type = leave_type_map.get(code)
                        if leave_type:
                            details = balance_details.get(code, {})
                            with ui.card().classes('items-center p-4 rounded-lg min-w-32'):
                                ui.label(leave_type.name).classes('font-semibold mb-2')
                                ui.label(f'{hours:.1f} hrs').classes('text-2xl font-bold text-blue-600')
                                ui.label(f'({hours/8:.1f} days)').classes('text-sm opacity-60')
                                ui.label('unused').classes('text-xs opacity-50 mt-1')

                                # Progress bar showing used vs available
                                total = details.get('total', hours)
                                used_pct = (details.get('used', 0) / total * 100) if total > 0 else 0
                                with ui.row().classes('w-full h-2 rounded-full overflow-hidden bg-gray-200 mt-2'):
                                    if used_pct > 0:
                                        ui.element('div').classes('h-full bg-gray-400').style(f'width: {min(used_pct, 100)}%')
            else:
                with ui.row().classes('w-full items-center justify-center p-4'):
                    ui.icon('info', color='gray').classes('mr-2')
                    ui.label('No unused leave balances available for carryover').classes('opacity-70')

        # ============ REQUEST SUMMARY CARD ============
        summary_card = ui.card().classes('w-full mb-6 p-4').style('border: 1px solid rgba(128,128,128,0.3)')

        def update_summary():
            """Update the request summary based on selections."""
            summary_card.clear()
            with summary_card:
                ui.label('Carryover Request Summary').classes('text-lg font-semibold mb-3')

                hours = selected_hours['value'] or 0
                code = selected_type['code']

                if not code or hours <= 0:
                    ui.label('Select a leave type and enter hours to see summary').classes('opacity-60 text-sm')
                    return

                max_hours = unused_balances.get(code, 0)
                remaining_unused = max_hours - hours

                with ui.row().classes('w-full justify-around'):
                    with ui.column().classes('items-center'):
                        ui.label('Currently Unused').classes('text-xs opacity-60 mb-1')
                        ui.label(f'{max_hours:.1f} hrs').classes('text-lg font-medium')
                        ui.label(f'({max_hours/8:.1f} days)').classes('text-xs opacity-60')

                    with ui.column().classes('items-center'):
                        ui.label('Requesting Carryover').classes('text-xs opacity-60 mb-1')
                        ui.label(f'{hours:.1f} hrs').classes('text-xl font-bold text-blue-600')
                        ui.label(f'({hours/8:.1f} days)').classes('text-xs opacity-60')

                    with ui.column().classes('items-center'):
                        ui.label('Will Expire').classes('text-xs opacity-60 mb-1')
                        if remaining_unused > 0:
                            ui.label(f'{remaining_unused:.1f} hrs').classes('text-lg font-medium text-amber-500')
                            ui.label(f'({remaining_unused/8:.1f} days)').classes('text-xs opacity-60')
                        else:
                            ui.label('0.0 hrs').classes('text-lg font-medium text-green-600')
                            ui.label('(0.0 days)').classes('text-xs opacity-60')

                # Warning if not carrying over all
                if remaining_unused > 0:
                    with ui.card().classes('w-full mt-3 p-2 border-l-4 border-amber-500'):
                        with ui.row().classes('items-center'):
                            ui.icon('info', color='orange').classes('mr-2')
                            ui.label(f'{remaining_unused:.1f} hours ({remaining_unused/8:.1f} days) will expire if not carried over').classes('text-amber-500 text-sm')

        # ============ CARRYOVER REQUEST FORM ============
        if unused_balances:
            with ui.card().classes('w-full mb-6 p-4'):
                ui.label('New Carryover Request').classes('text-lg font-semibold mb-4')

                # Leave type dropdown (only types with unused balance)
                leave_type_options = {}
                for code, hours in unused_balances.items():
                    lt = leave_type_map.get(code)
                    if lt:
                        leave_type_options[lt.id] = f'{lt.name} - {format_hours_days(hours)} available'

                leave_type_select = ui.select(
                    leave_type_options,
                    label='Leave Type',
                    value=list(leave_type_options.keys())[0] if leave_type_options else None
                ).classes('w-full mb-4')

                # Policy context display
                policy_card = ui.card().classes('w-full mb-4 p-3').style('border: 1px solid rgba(128,128,128,0.3)')

                def update_policy_info():
                    """Update policy info based on selected leave type."""
                    policy_card.clear()
                    with policy_card:
                        if not leave_type_select.value or not current_user:
                            ui.label('Select a leave type to see carryover policy').classes('text-sm opacity-60')
                            return

                        db = next(get_db())
                        try:
                            # Find leave type code from ID
                            lt = db.query(LeaveType).filter(LeaveType.id == leave_type_select.value).first()
                            if lt:
                                selected_type['code'] = lt.code
                                accrual_svc = AccrualService(db)
                                policy = accrual_svc.get_policy_for_employee(current_user, lt.code)
                                if policy and policy.max_carryover_hours:
                                    max_auto = float(policy.max_carryover_hours)
                                    if max_auto > 0:
                                        with ui.row().classes('items-center'):
                                            ui.icon('check_circle', color='green').classes('mr-2')
                                            with ui.column():
                                                ui.label(f'Auto-approved up to {format_hours_days(max_auto)}').classes('text-sm font-medium text-green-600')
                                                ui.label('Hours above this limit require manager approval').classes('text-xs opacity-70')
                                    else:
                                        with ui.row().classes('items-center'):
                                            ui.icon('approval', color='orange').classes('mr-2')
                                            ui.label('All carryover requests require manager approval').classes('text-sm text-amber-500')
                                else:
                                    with ui.row().classes('items-center'):
                                        ui.icon('approval', color='orange').classes('mr-2')
                                        ui.label('Manager approval required for carryover').classes('text-sm text-amber-500')
                        finally:
                            db.close()

                    update_summary()

                leave_type_select.on('update:model-value', lambda e: update_policy_info())

                # Hours to carry over with slider
                def get_max_hours():
                    """Get max hours for selected leave type."""
                    if not leave_type_select.value:
                        return 0
                    for code, hours in unused_balances.items():
                        lt = leave_type_map.get(code)
                        if lt and lt.id == leave_type_select.value:
                            return hours
                    return 0

                ui.label('Hours to Carry Over').classes('text-sm font-medium mb-1')

                with ui.row().classes('w-full items-center gap-4 mb-2'):
                    hours_input = ui.number(
                        value=0,
                        min=0,
                        max=get_max_hours(),
                        step=4,
                        format='%.1f'
                    ).classes('w-32')

                    hours_display = ui.label('0.0 days').classes('opacity-70')

                def update_hours_display():
                    hrs = hours_input.value or 0
                    selected_hours['value'] = hrs
                    hours_display.text = f'= {hrs/8:.1f} days'
                    update_summary()

                hours_input.on('update:model-value', lambda e: update_hours_display())

                # Quick select buttons
                with ui.row().classes('gap-2 mb-4'):
                    def set_hours(hrs):
                        max_hrs = get_max_hours()
                        hours_input.value = min(hrs, max_hrs)
                        update_hours_display()

                    ui.button('Half Day (4h)', on_click=lambda: set_hours(4)).props('size=sm dense outline')
                    ui.button('1 Day (8h)', on_click=lambda: set_hours(8)).props('size=sm dense outline')
                    ui.button('2 Days (16h)', on_click=lambda: set_hours(16)).props('size=sm dense outline')
                    ui.button('All Unused', on_click=lambda: set_hours(get_max_hours())).props('size=sm dense outline color=primary')

                # Update max when leave type changes
                def update_hours_max():
                    hours_input.max = get_max_hours()
                    if hours_input.value and hours_input.value > hours_input.max:
                        hours_input.value = hours_input.max
                    update_hours_display()

                leave_type_select.on('update:model-value', lambda e: update_hours_max())

                # Reason/justification
                reason_input = ui.textarea(
                    label='Reason/Justification (required)',
                    placeholder='Explain why you need to carry over these hours (e.g., planned vacation, project deadlines, etc.)'
                ).classes('w-full mb-6')

                # Submit button
                def submit_carryover():
                    """Submit the carryover request."""
                    if not leave_type_select.value:
                        ui.notify('Please select a leave type', type='negative')
                        return

                    if not hours_input.value or hours_input.value <= 0:
                        ui.notify('Please enter hours to carry over', type='negative')
                        return

                    if hours_input.value > get_max_hours():
                        ui.notify(f'Cannot carry over more than {format_hours_days(get_max_hours())}', type='negative')
                        return

                    if not reason_input.value or not reason_input.value.strip():
                        ui.notify('Please provide a reason for the carryover request', type='negative')
                        return

                    db = next(get_db())
                    try:
                        # Get user's role to check for auto-approval
                        user_service = UserService(db)
                        current_employee = user_service.get_user_by_id(user['id'])
                        user_role = current_employee.role if current_employee else 'employee'

                        # Determine if auto-approve applies
                        auto_approve = user_role in ['manager', 'admin', 'superadmin']

                        # Create carryover request
                        request = CarryoverRequest(
                            employee_id=user['id'],
                            leave_type_id=leave_type_select.value,
                            from_year=current_year,
                            to_year=next_year,
                            hours_requested=Decimal(str(hours_input.value)),
                            status='approved' if auto_approve else 'pending',
                            employee_notes=reason_input.value.strip()
                        )

                        # If auto-approving, set approval fields
                        if auto_approve:
                            request.approved_by = user['id']
                            request.approved_at = datetime.now()
                            request.hours_approved = Decimal(str(hours_input.value))

                        db.add(request)
                        db.commit()

                        if auto_approve:
                            ui.notify('Carryover request approved automatically!', type='positive')
                        else:
                            ui.notify('Carryover request submitted for manager approval!', type='positive')
                        ui.navigate.to('/carryover')  # Refresh page

                    except Exception as e:
                        ui.notify(f'Error submitting request: {str(e)}', type='negative')
                    finally:
                        db.close()

                with ui.row().classes('w-full gap-4'):
                    ui.button('Submit Request', on_click=submit_carryover, color='primary').classes('flex-1')
                    ui.button('Cancel', on_click=lambda: ui.navigate.to('/dashboard'), color='secondary').classes('flex-1')

                # Initialize displays
                update_policy_info()

        # ============ EXISTING REQUESTS TABLE ============
        with ui.card().classes('w-full mb-6 p-4'):
            ui.label('Your Carryover Requests').classes('text-lg font-semibold mb-4')

            if existing_requests:
                columns = [
                    {'name': 'leave_type', 'label': 'Leave Type', 'field': 'leave_type', 'align': 'left'},
                    {'name': 'hours', 'label': 'Requested', 'field': 'hours', 'align': 'center'},
                    {'name': 'approved', 'label': 'Approved', 'field': 'approved', 'align': 'center'},
                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                    {'name': 'date', 'label': 'Submitted', 'field': 'date', 'align': 'left'},
                ]

                rows = []
                for req in existing_requests:
                    lt = leave_type_map.get(next((lt.code for lt in leave_types if lt.id == req.leave_type_id), None))
                    lt_name = lt.name if lt else 'Unknown'

                    status_display = req.status.title()
                    if req.status == 'approved':
                        status_display = '✅ Approved'
                    elif req.status == 'denied':
                        status_display = '❌ Denied'
                    elif req.status == 'pending':
                        status_display = '⏳ Pending'

                    hrs_req = float(req.hours_requested)
                    hrs_app = float(req.hours_approved) if req.hours_approved else None

                    rows.append({
                        'leave_type': lt_name,
                        'hours': f'{hrs_req:.1f} hrs ({hrs_req/8:.1f} days)',
                        'approved': f'{hrs_app:.1f} hrs ({hrs_app/8:.1f} days)' if hrs_app else '-',
                        'status': status_display,
                        'date': req.created_at.strftime('%m/%d/%Y')
                    })

                ui.table(columns=columns, rows=rows).classes('w-full')

                # Show manager notes for denied requests
                for req in existing_requests:
                    if req.status == 'denied' and req.manager_notes:
                        with ui.card().classes('w-full mt-2 p-3 border-l-4 border-red-500'):
                            with ui.row().classes('items-start'):
                                ui.icon('error', color='red').classes('mr-2 mt-1')
                                with ui.column():
                                    ui.label('Request Denied').classes('text-sm font-medium text-red-500')
                                    ui.label(f'Manager notes: {req.manager_notes}').classes('text-sm text-red-500')
            else:
                with ui.row().classes('w-full items-center justify-center p-4'):
                    ui.icon('inbox', color='gray').classes('mr-2')
                    ui.label('No carryover requests submitted yet').classes('opacity-70')

        # Back button
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')
