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


def carryover_page():
    """Page for requesting leave balance carryover to next year."""

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

        # Calculate unused balances
        unused_balances = {}
        if balance:
            # Vacation
            vacation_unused = float(balance.vacation_total) - float(balance.vacation_used) - float(getattr(balance, 'vacation_pending', 0) or 0)
            if vacation_unused > 0:
                unused_balances['VACATION'] = vacation_unused

            # Sick
            sick_unused = float(balance.sick_total) - float(balance.sick_used) - float(getattr(balance, 'sick_pending', 0) or 0)
            if sick_unused > 0:
                unused_balances['SICK'] = sick_unused

            # Personal
            personal_unused = float(balance.personal_total) - float(balance.personal_used) - float(getattr(balance, 'personal_pending', 0) or 0)
            if personal_unused > 0:
                unused_balances['PERSONAL'] = personal_unused

        # Get existing carryover requests
        existing_requests = db.query(CarryoverRequest).filter(
            CarryoverRequest.employee_id == user['id'],
            CarryoverRequest.from_year == current_year
        ).order_by(CarryoverRequest.created_at.desc()).all()

        # Build leave type lookup
        leave_type_map = {lt.code: lt for lt in leave_types}

    finally:
        db.close()

    with ui.column().classes('w-full max-w-2xl mx-auto mt-8 p-6'):
        ui.label('Request Leave Carryover').classes('text-2xl font-bold mb-6')
        ui.label(f'Carry unused {current_year} leave into {next_year}').classes('text-gray-600 mb-6')

        # Current Unused Balances Section
        with ui.card().classes('w-full mb-6'):
            ui.label('Your Unused Balances').classes('text-xl font-semibold mb-4')

            if unused_balances:
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    for code, hours in unused_balances.items():
                        leave_type = leave_type_map.get(code)
                        if leave_type:
                            with ui.card().classes('p-4 bg-blue-50'):
                                ui.label(leave_type.name).classes('font-medium')
                                ui.label(f'{hours:.1f} hours unused').classes('text-sm text-gray-600')
            else:
                ui.label('No unused leave balances available for carryover').classes('text-gray-600')

        # Carryover Request Form
        if unused_balances:
            with ui.card().classes('w-full mb-6'):
                ui.label('New Carryover Request').classes('text-xl font-semibold mb-4')

                # Leave type dropdown (only types with unused balance)
                leave_type_options = {}
                for code, hours in unused_balances.items():
                    lt = leave_type_map.get(code)
                    if lt:
                        leave_type_options[lt.id] = f'{lt.name} ({hours:.1f} hrs available)'

                leave_type_select = ui.select(
                    leave_type_options,
                    label='Leave Type',
                    value=list(leave_type_options.keys())[0] if leave_type_options else None
                ).classes('w-full mb-4')

                # Policy context display
                policy_info = ui.label('').classes('text-sm text-gray-600 mb-4')

                def update_policy_info():
                    """Update policy info based on selected leave type."""
                    if not leave_type_select.value or not current_user:
                        policy_info.text = ''
                        return

                    db = next(get_db())
                    try:
                        # Find leave type code from ID
                        lt = db.query(LeaveType).filter(LeaveType.id == leave_type_select.value).first()
                        if lt:
                            accrual_svc = AccrualService(db)
                            policy = accrual_svc.get_policy_for_employee(current_user, lt.code)
                            if policy and policy.max_carryover_hours:
                                max_auto = float(policy.max_carryover_hours)
                                if max_auto > 0:
                                    policy_info.text = f'Your location allows up to {max_auto:.0f} hours automatic carryover. Hours above this require manager approval.'
                                else:
                                    policy_info.text = 'Your location requires manager approval for all carryover requests.'
                            else:
                                policy_info.text = 'No automatic carryover allowed. Manager approval required.'
                    finally:
                        db.close()

                leave_type_select.on('update:model-value', lambda e: update_policy_info())
                update_policy_info()

                # Hours to carry over
                def get_max_hours():
                    """Get max hours for selected leave type."""
                    if not leave_type_select.value:
                        return 0
                    for code, hours in unused_balances.items():
                        lt = leave_type_map.get(code)
                        if lt and lt.id == leave_type_select.value:
                            return hours
                    return 0

                hours_input = ui.number(
                    label='Hours to Carry Over',
                    value=0,
                    min=0.5,
                    max=get_max_hours(),
                    step=0.5
                ).classes('w-full mb-4')

                # Update max when leave type changes
                def update_hours_max():
                    hours_input.max = get_max_hours()
                    if hours_input.value > hours_input.max:
                        hours_input.value = hours_input.max

                leave_type_select.on('update:model-value', lambda e: update_hours_max())

                # Reason/justification
                reason_input = ui.textarea(
                    label='Reason/Justification (required)',
                    placeholder='Explain why you need to carry over these hours...'
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
                        ui.notify(f'Cannot carry over more than {get_max_hours():.1f} hours', type='negative')
                        return

                    if not reason_input.value or not reason_input.value.strip():
                        ui.notify('Please provide a reason for the carryover request', type='negative')
                        return

                    db = next(get_db())
                    try:
                        # Create carryover request
                        request = CarryoverRequest(
                            employee_id=user['id'],
                            leave_type_id=leave_type_select.value,
                            from_year=current_year,
                            to_year=next_year,
                            hours_requested=Decimal(str(hours_input.value)),
                            status='pending',
                            employee_notes=reason_input.value.strip()
                        )
                        db.add(request)
                        db.commit()

                        ui.notify('Carryover request submitted for manager approval!', type='positive')
                        ui.navigate.to('/carryover')  # Refresh page

                    except Exception as e:
                        ui.notify(f'Error submitting request: {str(e)}', type='negative')
                    finally:
                        db.close()

                with ui.row().classes('w-full gap-4'):
                    ui.button('Submit Request', on_click=submit_carryover, color='primary').classes('flex-1')
                    ui.button('Cancel', on_click=lambda: ui.navigate.to('/dashboard'), color='secondary').classes('flex-1')

        # Existing Carryover Requests Section
        with ui.card().classes('w-full mb-6'):
            ui.label('Your Carryover Requests').classes('text-xl font-semibold mb-4')

            if existing_requests:
                columns = [
                    {'name': 'leave_type', 'label': 'Leave Type', 'field': 'leave_type', 'align': 'left'},
                    {'name': 'hours', 'label': 'Hours Requested', 'field': 'hours', 'align': 'center'},
                    {'name': 'approved', 'label': 'Hours Approved', 'field': 'approved', 'align': 'center'},
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

                    rows.append({
                        'leave_type': lt_name,
                        'hours': f'{req.hours_requested:.1f}',
                        'approved': f'{req.hours_approved:.1f}' if req.hours_approved else '-',
                        'status': status_display,
                        'date': req.created_at.strftime('%m/%d/%Y')
                    })

                ui.table(columns=columns, rows=rows).classes('w-full')

                # Show manager notes for denied requests
                for req in existing_requests:
                    if req.status == 'denied' and req.manager_notes:
                        with ui.card().classes('w-full mt-2 bg-red-50 p-3'):
                            ui.label(f'Manager notes: {req.manager_notes}').classes('text-sm text-red-800')
            else:
                ui.label('No carryover requests submitted').classes('text-gray-600')

        # Back button
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')
