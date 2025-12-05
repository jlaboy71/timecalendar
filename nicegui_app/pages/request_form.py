from nicegui import ui, app
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.database import get_db
from src.models.leave_type import LeaveType
from datetime import date, timedelta


def request_form_page():
    """PTO request form page with form fields and submission handling."""

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
        # Build options dict: code -> name for display
        leave_type_options = {lt.code.lower(): lt.name for lt in leave_types}
        # Track which types require documentation
        requires_doc_types = {lt.code.lower() for lt in leave_types if lt.requires_documentation}

        # Get current user object for policy lookups
        user_service = UserService(db)
        current_user = user_service.get_user_by_id(user['id'])
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

    with ui.column().classes('w-full max-w-md mx-auto mt-8 p-6'):
        ui.label('Submit PTO Request').classes('text-2xl font-bold mb-6')

        # Show notice if date was pre-filled from calendar
        if prefill_date:
            ui.label(f'Requesting time off for {prefill_date.strftime("%B %d, %Y")}').classes('text-sm text-blue-600 mb-4')

        # Form fields - use leave types from database
        pto_type = ui.select(
            leave_type_options,
            label='Leave Type',
            value='vacation' if 'vacation' in leave_type_options else list(leave_type_options.keys())[0] if leave_type_options else None
        ).classes('w-full mb-2')

        # Policy info display (updates when leave type changes)
        policy_info_label = ui.label('').classes('text-sm text-gray-600 mb-4')

        def update_policy_info():
            """Update the policy info display based on selected leave type."""
            if not pto_type.value:
                policy_info_label.text = ''
                return

            db = next(get_db())
            try:
                accrual_service = AccrualService(db)
                user_service = UserService(db)
                emp = user_service.get_user_by_id(user['id'])

                if emp:
                    policy = accrual_service.get_policy_for_employee(emp, pto_type.value.upper())
                    if policy:
                        info_parts = []
                        if policy.min_increment_hours:
                            info_parts.append(f"Min request: {policy.min_increment_hours} hrs")
                        if policy.advance_notice_days and policy.advance_notice_days > 0:
                            info_parts.append(f"Advance notice: {policy.advance_notice_days} days")
                        if policy.waiting_period_days and policy.waiting_period_days > 0:
                            # Check if still in waiting period
                            can_use, reason = accrual_service.can_use_leave(emp, pto_type.value.upper())
                            if not can_use:
                                info_parts.append(f"⚠️ {reason}")

                        policy_info_label.text = ' | '.join(info_parts) if info_parts else ''
                    else:
                        policy_info_label.text = ''
            finally:
                db.close()

        pto_type.on('update:model-value', lambda e: update_policy_info())
        update_policy_info()  # Initial state

        ui.label('Start Date').classes('text-sm font-medium mb-1')
        start_date = ui.date(value=prefill_date or date.today()).classes('w-full mb-4')

        ui.label('End Date').classes('text-sm font-medium mb-1')
        end_date = ui.date(value=prefill_date or date.today()).classes('w-full mb-4')

        half_day = ui.switch(
            'Half Day',
            value=False
        ).classes('mb-4')

        description = ui.textarea(
            label='Description/Notes (required for some leave types)',
            placeholder='Enter description or notes...'
        ).classes('w-full mb-6')

        # Show/hide description based on leave type requirements
        def toggle_description():
            if pto_type.value in requires_doc_types:
                description.visible = True
                description.props('label="Description/Notes (required)"')
            else:
                description.visible = True  # Always show but mark as optional
                description.props('label="Description/Notes (optional)"')

        pto_type.on('update:model-value', lambda e: toggle_description())
        toggle_description()  # Initial state

        # Buttons
        with ui.row().classes('w-full gap-4'):
            ui.button(
                'Submit Request',
                on_click=lambda: submit_request(
                    user['id'],
                    pto_type.value,
                    start_date.value,
                    end_date.value,
                    half_day.value,
                    description.value
                )
            ).classes('flex-1')

            ui.button(
                'Cancel',
                on_click=lambda: ui.navigate.to('/dashboard')
            ).classes('flex-1')


def submit_request(user_id, pto_type, start_date, end_date, half_day, description):
    """Submit PTO request with validation and database operations."""

    # Validate required fields
    if not start_date or not end_date:
        ui.notify('Start date and end date are required', type='negative')
        return

    if start_date > end_date:
        ui.notify('Start date cannot be after end date', type='negative')
        return

    db = None
    try:
        # Get database session
        db = next(get_db())

        # Get leave type and employee for policy validation
        leave_type = db.query(LeaveType).filter(
            LeaveType.code == pto_type.upper()
        ).first()

        # Check if documentation is required
        if leave_type and leave_type.requires_documentation and not description.strip():
            ui.notify(f'Description is required for {leave_type.name}', type='negative')
            return

        # Get employee for policy lookups
        user_service = UserService(db)
        employee = user_service.get_user_by_id(user_id)

        if not employee:
            ui.notify('User not found', type='negative')
            return

        # Policy validation
        accrual_service = AccrualService(db)

        # 1. Validate waiting period
        can_use, reason = accrual_service.can_use_leave(employee, pto_type.upper())
        if not can_use:
            ui.notify(f'Cannot use {leave_type.name if leave_type else pto_type}: {reason}', type='negative')
            return

        # Get applicable policy
        policy = accrual_service.get_policy_for_employee(employee, pto_type.upper())

        # Calculate hours requested
        total_days = (end_date - start_date).days + 1
        if half_day:
            total_days = 0.5
        hours_requested = total_days * 8  # 8 hours per day

        # 2. Validate minimum increment
        if policy and policy.min_increment_hours:
            if hours_requested < float(policy.min_increment_hours):
                ui.notify(
                    f'Minimum request is {policy.min_increment_hours} hours for your location',
                    type='negative'
                )
                return

        # 3. Validate advance notice (warning only, not blocking)
        if policy and policy.advance_notice_days and policy.advance_notice_days > 0:
            days_until_start = (start_date - date.today()).days
            if days_until_start < policy.advance_notice_days:
                ui.notify(
                    f'Note: {policy.advance_notice_days} days advance notice is typically required',
                    type='warning'
                )

        # Create PTO service and submit request
        pto_service = PTOService(db)

        # Create request data
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

        # Submit the request
        pto_service.create_request(request_data)

        # Success feedback
        ui.notify('PTO request submitted successfully!', type='positive')
        ui.navigate.to('/dashboard')

    except Exception as e:
        ui.notify(f'Error submitting request: {str(e)}', type='negative')

    finally:
        if db:
            db.close()
