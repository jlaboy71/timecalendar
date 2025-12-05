"""Manager carryover approval page for reviewing and processing employee carryover requests."""
from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.models.carryover_request import CarryoverRequest
from src.models.leave_type import LeaveType
from src.models.user import User
from src.database import get_db
from datetime import datetime, date
from decimal import Decimal
from nicegui_app.logo import LOGO_DATA_URL


def manager_carryover_page():
    """Manager page for reviewing and approving/denying carryover requests."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    # Check if user is logged in and has manager/admin role
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    if user.get('role') not in ['manager', 'admin', 'superadmin']:
        ui.notify('Access denied. Manager or Admin role required.', type='negative')
        ui.navigate.to('/dashboard')
        return

    # Superadmin and admin have full access to all departments
    is_admin = user.get('role') in ['admin', 'superadmin']
    current_year = date.today().year

    with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
        with ui.column().classes('gap-2 mb-2'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            ui.label('CARRYOVER REQUEST APPROVALS').classes('text-xl font-bold').style('color: #5a6a72;')
        ui.label(f'Review carryover requests from {current_year} to {current_year + 1}').classes('opacity-70 mb-6')

        # Container for pending requests - will be refreshed
        pending_container = ui.column().classes('w-full mb-6')

        # Container for processed requests
        processed_container = ui.column().classes('w-full')

        def load_requests():
            """Load and display all carryover requests."""
            pending_container.clear()
            processed_container.clear()

            db = next(get_db())
            try:
                user_service = UserService(db)
                accrual_service = AccrualService(db)
                balance_service = BalanceService(db)

                # Get current manager's info to filter by department
                manager = user_service.get_user_by_id(user['id'])

                # Build query for carryover requests
                query = db.query(CarryoverRequest).filter(
                    CarryoverRequest.from_year == current_year
                )

                # If not admin, filter by department
                if not is_admin and manager and manager.department_id:
                    # Get employees in manager's department
                    dept_employee_ids = [
                        emp.id for emp in db.query(User).filter(
                            User.department_id == manager.department_id,
                            User.is_active == True
                        ).all()
                    ]
                    query = query.filter(CarryoverRequest.employee_id.in_(dept_employee_ids))

                # Separate pending and processed
                pending_requests = query.filter(
                    CarryoverRequest.status == 'pending'
                ).order_by(CarryoverRequest.created_at.asc()).all()

                processed_requests = query.filter(
                    CarryoverRequest.status != 'pending'
                ).order_by(CarryoverRequest.approved_at.desc()).limit(20).all()

                # Build lookup dictionaries
                leave_types = {lt.id: lt for lt in db.query(LeaveType).all()}
                employee_ids = set(r.employee_id for r in pending_requests + processed_requests)
                employees = {emp.id: emp for emp in db.query(User).filter(User.id.in_(employee_ids)).all()}

                # Display pending requests
                with pending_container:
                    with ui.card().classes('w-full'):
                        ui.label('Pending Requests').classes('text-xl font-semibold mb-4')

                        if pending_requests:
                            for req in pending_requests:
                                employee = employees.get(req.employee_id)
                                leave_type = leave_types.get(req.leave_type_id)

                                if not employee or not leave_type:
                                    continue

                                # Get policy context for this employee
                                policy = accrual_service.get_policy_for_employee(employee, leave_type.code)
                                max_auto_carryover = float(policy.max_carryover_hours) if policy and policy.max_carryover_hours else 0

                                # Get employee's current balance for context
                                balance = balance_service.get_or_create_balance(employee.id, current_year)

                                with ui.card().classes('w-full mb-4 p-4 border-l-4 border-amber-500'):
                                    # Header row with employee info
                                    with ui.row().classes('w-full justify-between items-start mb-4'):
                                        with ui.column():
                                            ui.label(f'{employee.full_name}').classes('font-semibold text-lg')
                                            ui.label(f'{leave_type.name} • {req.hours_requested} hours requested').classes('opacity-70')
                                            if employee.department:
                                                ui.label(f'Department: {employee.department.name}').classes('text-sm opacity-60')
                                            location = f'{employee.location_city}, {employee.location_state}' if employee.location_city else employee.location_state or 'Not set'
                                            ui.label(f'Location: {location}').classes('text-sm opacity-60')

                                        ui.label(f'Submitted: {req.created_at.strftime("%m/%d/%Y")}').classes('text-sm opacity-60')

                                    # Policy context
                                    with ui.row().classes('w-full gap-4 mb-4'):
                                        with ui.card().classes('flex-1 p-3'):
                                            ui.label('Policy Context').classes('font-medium text-sm')
                                            if max_auto_carryover > 0:
                                                ui.label(f'Auto carryover limit: {max_auto_carryover} hrs').classes('text-sm')
                                            else:
                                                ui.label('No auto carryover allowed').classes('text-sm text-amber-500')

                                        # Show current unused balance
                                        if balance:
                                            unused = 0
                                            if leave_type.code == 'VACATION':
                                                unused = float(balance.vacation_total) - float(balance.vacation_used) - float(balance.vacation_pending)
                                            elif leave_type.code == 'SICK':
                                                unused = float(balance.sick_total) - float(balance.sick_used)
                                            elif leave_type.code == 'PERSONAL':
                                                unused = float(balance.personal_total) - float(balance.personal_used)

                                            with ui.card().classes('flex-1 p-3'):
                                                ui.label('Current Balance').classes('font-medium text-sm')
                                                ui.label(f'{unused:.1f} hrs unused').classes('text-sm')

                                    # Employee notes
                                    if req.employee_notes:
                                        with ui.card().classes('w-full p-3 mb-4'):
                                            ui.label('Employee Notes:').classes('font-medium text-sm')
                                            ui.label(req.employee_notes).classes('text-sm opacity-80')

                                    # Approval form
                                    with ui.row().classes('w-full gap-4 items-end'):
                                        hours_approved = ui.number(
                                            label='Hours to Approve',
                                            value=float(req.hours_requested),
                                            min=0,
                                            max=float(req.hours_requested),
                                            step=0.5
                                        ).classes('w-32')

                                        manager_notes = ui.input(
                                            label='Manager Notes (optional)',
                                            placeholder='Reason for decision...'
                                        ).classes('flex-1')

                                        def create_approve_handler(r, ha, mn):
                                            def handler():
                                                approve_request(r.id, float(ha.value), mn.value)
                                            return handler

                                        def create_deny_handler(r, mn):
                                            def handler():
                                                deny_request(r.id, mn.value)
                                            return handler

                                        ui.button(
                                            'Approve',
                                            on_click=create_approve_handler(req, hours_approved, manager_notes),
                                            color='positive'
                                        )
                                        ui.button(
                                            'Deny',
                                            on_click=create_deny_handler(req, manager_notes),
                                            color='negative'
                                        )
                        else:
                            ui.label('No pending carryover requests').classes('opacity-70')

                # Display processed requests
                with processed_container:
                    with ui.expansion('Recently Processed Requests', icon='history').classes('w-full'):
                        if processed_requests:
                            columns = [
                                {'name': 'employee', 'label': 'Employee', 'field': 'employee', 'align': 'left'},
                                {'name': 'leave_type', 'label': 'Leave Type', 'field': 'leave_type', 'align': 'left'},
                                {'name': 'requested', 'label': 'Requested', 'field': 'requested', 'align': 'center'},
                                {'name': 'approved', 'label': 'Approved', 'field': 'approved', 'align': 'center'},
                                {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                                {'name': 'date', 'label': 'Processed', 'field': 'date', 'align': 'left'},
                            ]

                            rows = []
                            for req in processed_requests:
                                employee = employees.get(req.employee_id)
                                leave_type = leave_types.get(req.leave_type_id)

                                status_display = '✅ Approved' if req.status == 'approved' else '❌ Denied'

                                rows.append({
                                    'employee': employee.full_name if employee else 'Unknown',
                                    'leave_type': leave_type.name if leave_type else 'Unknown',
                                    'requested': f'{req.hours_requested:.1f}',
                                    'approved': f'{req.hours_approved:.1f}' if req.hours_approved else '-',
                                    'status': status_display,
                                    'date': req.approved_at.strftime('%m/%d/%Y') if req.approved_at else '-'
                                })

                            ui.table(columns=columns, rows=rows).classes('w-full')
                        else:
                            ui.label('No processed requests').classes('opacity-70')

            finally:
                db.close()

        def approve_request(request_id: int, hours_approved: float, manager_notes: str):
            """Approve a carryover request and update the employee's balance."""
            db = next(get_db())
            try:
                # Get the request
                request = db.query(CarryoverRequest).filter(CarryoverRequest.id == request_id).first()
                if not request:
                    ui.notify('Request not found', type='negative')
                    return

                if request.status != 'pending':
                    ui.notify('Request has already been processed', type='warning')
                    load_requests()
                    return

                # Update carryover request
                request.status = 'approved'
                request.hours_approved = Decimal(str(hours_approved))
                request.approved_by = user['id']
                request.approved_at = datetime.now()
                request.manager_notes = manager_notes.strip() if manager_notes else None

                # Get or create balance for the target year
                balance_service = BalanceService(db)
                target_balance = balance_service.get_or_create_balance(
                    request.employee_id,
                    request.to_year
                )

                # Get leave type to determine which carryover field to update
                leave_type = db.query(LeaveType).filter(LeaveType.id == request.leave_type_id).first()

                if target_balance and leave_type:
                    # Add hours to appropriate carryover field
                    if leave_type.code == 'VACATION':
                        target_balance.vacation_carryover = (
                            target_balance.vacation_carryover or Decimal('0')
                        ) + Decimal(str(hours_approved))
                    elif leave_type.code == 'SICK':
                        target_balance.sick_carryover = (
                            target_balance.sick_carryover or Decimal('0')
                        ) + Decimal(str(hours_approved))
                    elif leave_type.code == 'PERSONAL':
                        target_balance.personal_carryover = (
                            target_balance.personal_carryover or Decimal('0')
                        ) + Decimal(str(hours_approved))

                db.commit()
                ui.notify(f'Approved {hours_approved} hours carryover', type='positive')
                load_requests()

            except Exception as e:
                db.rollback()
                ui.notify(f'Error approving request: {str(e)}', type='negative')
            finally:
                db.close()

        def deny_request(request_id: int, manager_notes: str):
            """Deny a carryover request."""
            db = next(get_db())
            try:
                request = db.query(CarryoverRequest).filter(CarryoverRequest.id == request_id).first()
                if not request:
                    ui.notify('Request not found', type='negative')
                    return

                if request.status != 'pending':
                    ui.notify('Request has already been processed', type='warning')
                    load_requests()
                    return

                # Update request
                request.status = 'denied'
                request.approved_by = user['id']
                request.approved_at = datetime.now()
                request.manager_notes = manager_notes.strip() if manager_notes else None

                db.commit()
                ui.notify('Carryover request denied', type='warning')
                load_requests()

            except Exception as e:
                db.rollback()
                ui.notify(f'Error denying request: {str(e)}', type='negative')
            finally:
                db.close()

        # Initial load
        load_requests()

        # Back button
        with ui.row().classes('w-full mt-6'):
            if is_admin:
                ui.button('Back to Admin', on_click=lambda: ui.navigate.to('/admin')).classes('mr-4')
            else:
                ui.button('Back to Manager Dashboard', on_click=lambda: ui.navigate.to('/manager')).classes('mr-4')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
