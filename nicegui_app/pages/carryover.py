"""Carryover request page for requesting sick leave balance carryover to next year."""
from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.models.carryover_request import CarryoverRequest
from src.models.leave_type import LeaveType
from src.database import get_db
from datetime import datetime, date
from decimal import Decimal
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog
from nicegui_app.components.formatting import fmt_days


def carryover_page():
    """Page for requesting sick leave balance carryover to next year."""

    apply_dark_mode()

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

        # Get Sick leave type (only type that can be carried over)
        sick_leave_type = db.query(LeaveType).filter(
            LeaveType.code == 'SICK',
            LeaveType.is_active == True
        ).first()

        # Calculate unused sick balance
        sick_unused = 0
        if balance:
            sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
            sick_used = float(balance.sick_used or 0)
            sick_pending = float(getattr(balance, 'sick_pending', 0) or 0)
            sick_unused = max(0, sick_total - sick_used - sick_pending)

        # Get carryover policy limit (absolute cap)
        max_carryover = 0
        if current_user and sick_leave_type:
            policy = accrual_service.get_policy_for_employee(current_user, 'SICK')
            if policy and policy.max_carryover_hours:
                max_carryover = float(policy.max_carryover_hours)

        # Get existing carryover requests
        existing_requests = db.query(CarryoverRequest).filter(
            CarryoverRequest.employee_id == user['id'],
            CarryoverRequest.from_year == current_year
        ).order_by(CarryoverRequest.created_at.desc()).all()

        # Calculate already-approved carryover for this transition (to enforce cap)
        already_approved = 0
        for req in existing_requests:
            if req.status == 'approved':
                already_approved += float(req.hours_approved or req.hours_requested)

        # Calculate remaining allowance under the cap
        remaining_cap = max(0, max_carryover - already_approved) if max_carryover > 0 else sick_unused

    finally:
        db.close()

    with ui.column().classes('w-full max-w-2xl mx-auto mt-8 p-6'):
        page_header(title='SICK TIME CARRYOVER', show_back=False)
        ui.label(f'Carry unused {current_year} sick time into {next_year}').classes('opacity-70 mb-6')

        # Calculate max requestable (minimum of unused balance and remaining cap)
        max_requestable = min(sick_unused, remaining_cap) if max_carryover > 0 else sick_unused

        # ============ MAIN FORM ============
        if sick_unused > 0 and sick_leave_type and max_requestable > 0:
            # Show available balance
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Available Sick Time').classes('font-medium')
                    ui.label(f'{sick_unused:.0f} hrs ({fmt_days(sick_unused/8)} days)').classes('text-xl font-bold text-green-600')

                if max_carryover > 0:
                    ui.label(f'Policy cap: {max_carryover:.0f} hrs maximum carryover').classes('text-xs opacity-60 mt-2')
                    if already_approved > 0:
                        ui.label(f'Already approved: {already_approved:.0f} hrs | Remaining: {remaining_cap:.0f} hrs').classes('text-xs text-amber-600 mt-1')

            # Hours input - default to max (why would you carry over less?)
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Hours to Carry Over').classes('font-medium')
                    ui.label(f'{max_requestable:.0f} hrs ({fmt_days(max_requestable/8)} days)').classes('text-lg font-bold')

                hours_input = ui.number(
                    value=max_requestable,
                    min=8,
                    max=max_requestable,
                    step=8
                ).classes('w-full')

            # Submit
            def submit_carryover():
                if not hours_input.value or hours_input.value < 8:
                    show_warning_dialog('Minimum Hours Required', 'Please enter at least 8 hours (1 day) for carryover.')
                    return

                if hours_input.value % 8 != 0:
                    show_warning_dialog('Full Days Only', 'Carryover hours must be in full-day (8-hour) increments.')
                    return

                db = next(get_db())
                try:
                    user_service = UserService(db)
                    current_employee = user_service.get_user_by_id(user['id'])
                    user_role = current_employee.role if current_employee else 'employee'

                    # Auto-approve for managers or if within policy limit
                    auto_approve = user_role in ['manager', 'admin', 'superadmin']
                    if not auto_approve and max_carryover > 0 and hours_input.value <= max_carryover:
                        auto_approve = True

                    request = CarryoverRequest(
                        employee_id=user['id'],
                        leave_type_id=sick_leave_type.id,
                        from_year=current_year,
                        to_year=next_year,
                        hours_requested=Decimal(str(hours_input.value)),
                        status='approved' if auto_approve else 'pending',
                        employee_notes='Unused sick time carryover'
                    )

                    if auto_approve:
                        request.approved_by = user['id']
                        request.approved_at = datetime.now()
                        request.hours_approved = Decimal(str(hours_input.value))
                        request.manager_notes = 'Auto-approved per policy'

                    db.add(request)
                    db.commit()

                    msg = 'Carryover approved!' if auto_approve else 'Request submitted for approval'
                    ui.notify(msg, type='positive')
                    ui.navigate.to('/carryover')

                except Exception as e:
                    show_error_dialog('Error', f'An error occurred: {str(e)}')
                finally:
                    db.close()

            with ui.row().classes('w-full gap-4'):
                ui.button('Submit', on_click=submit_carryover, color='primary').classes('flex-1')
                ui.button('Cancel', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('flex-1')

        elif sick_unused > 0 and max_requestable <= 0:
            # Hit the carryover cap
            with ui.card().classes('w-full mb-4 p-4 border-l-4 border-amber-500'):
                with ui.row().classes('items-center'):
                    ui.icon('warning', color='amber').classes('mr-3')
                    with ui.column().classes('gap-1'):
                        ui.label('Carryover Cap Reached').classes('font-medium')
                        ui.label(f'You have already approved {already_approved:.0f} hrs of carryover.').classes('text-sm opacity-70')
                        ui.label(f'Policy maximum is {max_carryover:.0f} hrs - no additional carryover allowed.').classes('text-sm opacity-70')
        else:
            # No sick time available
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('items-center'):
                    ui.icon('info', color='gray').classes('mr-3')
                    ui.label('No sick time available to carry over').classes('opacity-70')

        # ============ EXISTING REQUESTS ============
        if existing_requests:
            ui.separator().classes('my-6')
            ui.label('Your Requests').classes('text-lg font-semibold mb-4')

            for req in existing_requests:
                hrs = float(req.hours_requested)
                status_icon = {'approved': 'check_circle', 'denied': 'cancel', 'pending': 'schedule'}.get(req.status, 'help')
                status_color = {'approved': 'green', 'denied': 'red', 'pending': 'orange'}.get(req.status, 'gray')

                with ui.card().classes('w-full mb-2 p-3'):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon(status_icon, color=status_color)
                            ui.label(f'{hrs:.0f} hrs ({fmt_days(hrs/8)} days)')
                        ui.label(req.created_at.strftime('%A, %B %d, %Y')).classes('text-sm opacity-60')

                    if req.status == 'denied' and req.manager_notes:
                        ui.label(f'Denied: {req.manager_notes}').classes('text-sm text-red-500 mt-2')

        # Back button
        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat').classes('mt-6')
