"""Manager request detail page for approval/denial."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog
from nicegui_app.components.formatting import fmt_days, format_days_hours
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.services.audit_service import AuditService
from src.services.email_service import email_service


def manager_request_detail_page(request_id: int):
    """Request detail page for approval/denial content."""
    apply_dark_mode()

    current_user = app.storage.user.get('user', {})
    user_role = current_user.get('role')
    user_department_id = current_user.get('department_id')

    if user_role not in ['manager', 'admin', 'superadmin']:
        ui.label('Access denied').classes('text-red-500')
        return

    db = next(get_db())
    try:
        detail = PTOService.get_request_detail(db, request_id)

        if not detail:
            ui.label('Request not found').classes('text-red-500')
            return

        # Managers can only approve requests from their own department
        # Admins and superadmins can approve any request
        if user_role == 'manager':
            employee_dept_id = detail.get('employee_department_id')
            if employee_dept_id != user_department_id:
                ui.label('Access denied - You can only review requests from your department').classes('text-red-500')
                return

        request = detail['request']
        balance = detail['balance']

        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='PTO REQUEST REVIEW', show_back=False)

            # Employee Info and PTO Balance side by side
            with ui.row().classes('w-full gap-4 mb-4'):
                # Employee Info Card
                with ui.card().classes('flex-1 p-4'):
                    ui.label('Employee Information').classes('text-xl font-bold mb-3')
                    with ui.column().classes('gap-2'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('person', size='sm').classes('opacity-60')
                            ui.label(f"{detail['employee_name']}").classes('font-medium')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('email', size='sm').classes('opacity-60')
                            ui.label(f"{detail['employee_email']}")
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('business', size='sm').classes('opacity-60')
                            dept_name = detail.get('employee_department_name', 'Unknown')
                            ui.label(f"{dept_name}").classes('text-sm')
                        # Hire date
                        hire_date = detail.get('employee_hire_date')
                        if hire_date:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('event', size='sm').classes('opacity-60')
                                ui.label(f"Hired: {hire_date.strftime('%B %d, %Y')}").classes('text-sm')

                # Current Balance Card
                with ui.card().classes('flex-1 p-4'):
                    ui.label('Current PTO Balance').classes('text-xl font-bold mb-3')
                    # Include carryover and subtract pending for accurate available balance
                    vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                    vac_used = float(balance.vacation_used or 0)
                    vac_pending = float(balance.vacation_pending or 0)

                    sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                    sick_used = float(balance.sick_used or 0)
                    sick_pending = float(getattr(balance, 'sick_pending', 0) or 0)

                    personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                    personal_used = float(balance.personal_used or 0)
                    personal_pending = float(getattr(balance, 'personal_pending', 0) or 0)

                    # Check if Chicago employee for Chicago leave display
                    is_chicago = detail.get('employee_location_city', '').lower() == 'chicago'

                    with ui.column().classes('gap-2'):
                        # Vacation
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('beach_access', size='sm').classes('text-blue-500')
                            vac_hours = vac_total - vac_used - vac_pending
                            vac_display, vac_tooltip = format_days_hours(vac_hours)
                            vac_label = f"Vacation: {vac_display}"
                            if vac_pending > 0:
                                pending_display, _ = format_days_hours(vac_pending)
                                vac_label += f" ({pending_display} pending)"
                            ui.label(vac_label).tooltip(vac_tooltip)

                        # Sick
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('medical_services', size='sm').classes('text-green-500')
                            sick_hours = sick_total - sick_used - sick_pending
                            sick_display, sick_tooltip = format_days_hours(sick_hours)
                            sick_label = f"Sick: {sick_display}"
                            if sick_pending > 0:
                                pending_display, _ = format_days_hours(sick_pending)
                                sick_label += f" ({pending_display} pending)"
                            ui.label(sick_label).tooltip(sick_tooltip)

                        # Personal
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('person', size='sm').classes('text-purple-500')
                            personal_hours = personal_total - personal_used - personal_pending
                            personal_display, personal_tooltip = format_days_hours(personal_hours)
                            personal_label = f"Personal: {personal_display}"
                            if personal_pending > 0:
                                pending_display, _ = format_days_hours(personal_pending)
                                personal_label += f" ({pending_display} pending)"
                            ui.label(personal_label).tooltip(personal_tooltip)

                        # Chicago Paid Leave (if Chicago employee)
                        if is_chicago and balance:
                            paid_total = float(getattr(balance, 'chicago_paid_leave_total', 0) or 0) + float(getattr(balance, 'chicago_paid_leave_carryover', 0) or 0)
                            paid_used = float(getattr(balance, 'chicago_paid_leave_used', 0) or 0)
                            paid_pending = float(getattr(balance, 'chicago_paid_leave_pending', 0) or 0)
                            paid_hours = paid_total - paid_used - paid_pending
                            if paid_total > 0:
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('event_available', size='sm').classes('text-amber-500')
                                    paid_display, paid_tooltip = format_days_hours(paid_hours)
                                    ui.label(f"Chicago Paid: {paid_display}").tooltip(paid_tooltip)

            # Request Details Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Request Details').classes('text-xl font-bold mb-2')
                ui.label(f"Type: {request.pto_type.title()}")
                ui.label(f"Start Date: {request.start_date.strftime('%A, %B %d, %Y')}")
                ui.label(f"End Date: {request.end_date.strftime('%A, %B %d, %Y')}")
                ui.label(f"Duration: {fmt_days(float(request.total_days))}")
                ui.label(f"Status: {request.status.title()}")
                ui.label(f"Submitted: {request.submitted_at.strftime('%A, %B %d, %Y at %I:%M %p')}")
                if request.notes:
                    ui.label(f"Notes: {request.notes}")

            # Check for department conflicts
            pto_service = PTOService(db)
            conflicts = pto_service.get_department_conflicts(
                request.user_id,
                request.start_date,
                request.end_date,
                exclude_request_id=request_id
            )

            # Conflict Warning Card (if conflicts exist)
            if conflicts:
                # PTO type colors and icons for conflict display
                type_colors = {
                    'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
                    'work_from_home': 'red', 'chicago_leave': 'amber', 'bereavement': 'brown',
                    'fmla': 'teal', 'jury_duty': 'indigo', 'voting': 'cyan', 'military': 'deep-orange'
                }
                type_icons = {
                    'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person',
                    'work_from_home': 'home_work', 'chicago_leave': 'location_city', 'bereavement': 'sentiment_very_dissatisfied',
                    'fmla': 'family_restroom', 'jury_duty': 'gavel', 'voting': 'how_to_vote', 'military': 'military_tech'
                }

                with ui.card().classes('w-full p-4 mb-4 border-l-4 border-amber-500'):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('warning', color='amber').classes('text-2xl')
                        ui.label('Schedule Conflict Detected').classes('text-xl font-bold text-amber-600')

                    ui.label(
                        f'{len(conflicts)} other employee(s) in the same department have overlapping time off.'
                    ).classes('text-sm mb-3')

                    with ui.column().classes('gap-2'):
                        for conflict in conflicts:
                            status_color = 'green' if conflict['status'] == 'approved' else 'amber'
                            status_icon = 'check_circle' if conflict['status'] == 'approved' else 'pending'
                            pto_type_lower = conflict['pto_type'].lower().replace(' ', '_')
                            border_color = type_colors.get(pto_type_lower, 'gray')
                            pto_icon = type_icons.get(pto_type_lower, 'event')

                            with ui.card().classes(f'w-full p-3 border-l-4 border-{border_color}-500'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('items-center gap-3'):
                                        ui.icon(status_icon, color=status_color)
                                        with ui.column().classes('gap-0'):
                                            ui.label(conflict['user_name']).classes('font-semibold')
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon(pto_icon, size='xs').classes(f'text-{border_color}-500')
                                                ui.label(f"{conflict['pto_type'].title()} - {fmt_days(float(conflict['total_days']))}").classes('text-sm opacity-70')
                                    with ui.column().classes('text-right gap-0'):
                                        if conflict['start_date'] == conflict['end_date']:
                                            ui.label(conflict['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm')
                                        else:
                                            ui.label(f"{conflict['start_date'].strftime('%A, %B %d')} - {conflict['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm')
                                        ui.badge(conflict['status'].title(), color=status_color)

                    ui.label(
                        'Note: Concurrent leave is allowed, but please consider staffing needs before approving.'
                    ).classes('text-xs opacity-60 mt-3 italic')

            # Cancellation Request Section (for approved requests with cancellation requested)
            if request.status == 'approved' and hasattr(request, 'cancellation_requested') and request.cancellation_requested:
                with ui.card().classes('w-full p-4 mb-4 border-l-4 border-amber-500'):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('cancel_schedule_send', color='amber').classes('text-2xl')
                        ui.label('Cancellation Requested').classes('text-xl font-bold text-amber-600')

                    if hasattr(request, 'cancellation_reason') and request.cancellation_reason:
                        ui.label(f"Reason: {request.cancellation_reason}").classes('text-sm mb-3')

                    if hasattr(request, 'cancellation_requested_at') and request.cancellation_requested_at:
                        ui.label(f"Requested: {request.cancellation_requested_at.strftime('%Y-%m-%d %H:%M')}").classes('text-xs opacity-60 mb-3')

                    ui.label('The employee is requesting to cancel this approved time off.').classes('text-sm opacity-70 mb-4')

                    def approve_cancellation():
                        db_cancel = next(get_db())
                        try:
                            from src.models.pto_request import PTORequest
                            req = db_cancel.query(PTORequest).filter(PTORequest.id == request_id).first()
                            if req:
                                # Cancel the request
                                req.status = 'cancelled'
                                req.cancellation_requested = False

                                # Restore balance
                                pto_type_lower = req.pto_type.lower()
                                total_days = float(req.total_days)
                                if pto_type_lower in ['vacation', 'sick', 'personal']:
                                    balance_service = BalanceService(db_cancel)
                                    balance = balance_service.get_or_create_balance(req.user_id, req.start_date.year)
                                    if pto_type_lower == 'vacation':
                                        balance.vacation_used = max(0, float(balance.vacation_used or 0) - (total_days * 8))
                                    elif pto_type_lower == 'sick':
                                        balance.sick_used = max(0, float(balance.sick_used or 0) - (total_days * 8))
                                    elif pto_type_lower == 'personal':
                                        balance.personal_used = max(0, float(balance.personal_used or 0) - (total_days * 8))

                                db_cancel.commit()
                                show_success_dialog('Cancellation Approved', 'Time off cancelled and balance restored', on_close=lambda: ui.navigate.to('/calendar'))
                        finally:
                            db_cancel.close()

                    def deny_cancellation():
                        db_deny = next(get_db())
                        try:
                            from src.models.pto_request import PTORequest
                            req = db_deny.query(PTORequest).filter(PTORequest.id == request_id).first()
                            if req:
                                req.cancellation_requested = False
                                req.cancellation_reason = None
                                req.cancellation_requested_at = None
                                db_deny.commit()
                                show_warning_dialog('Cancellation Denied', 'Time off remains scheduled', on_close=lambda: ui.navigate.to('/calendar'))
                        finally:
                            db_deny.close()

                    with ui.row().classes('w-full justify-end gap-4'):
                        ui.button('Deny Cancellation', on_click=deny_cancellation).props('flat color=grey')
                        ui.button('Approve Cancellation', on_click=approve_cancellation).props('color=amber')

            # Approval Actions
            if request.status == 'pending':
                def approve():
                    db = next(get_db())
                    try:
                        current_user = app.storage.user.get('user')
                        user_id = current_user.get('id')
                        approver_name = f"{current_user.get('first_name')} {current_user.get('last_name')}"
                        if PTOService.approve_request(db, request_id, user_id):
                            # Log the approval
                            AuditService.log_pto_approve(
                                db, user_id, approver_name, request_id, detail['employee_name']
                            )
                            # Send email notification
                            email_service.send_pto_approved(
                                detail['employee_email'],
                                detail['employee_name'],
                                request.pto_type,
                                request.start_date,
                                request.end_date,
                                float(request.total_days),
                                approver_name
                            )
                            show_success_dialog('Request Approved', 'PTO request has been approved!', on_close=lambda: ui.navigate.to('/calendar'))
                        else:
                            show_error_dialog('Approval Failed', 'There was an error approving the request. Please try again.')
                    finally:
                        db.close()

                def deny():
                    db = next(get_db())
                    try:
                        reason = denial_input.value or 'No reason provided'
                        current_user = app.storage.user.get('user')
                        user_id = current_user.get('id')
                        approver_name = f"{current_user.get('first_name')} {current_user.get('last_name')}"
                        if PTOService.deny_request(db, request_id, user_id, reason):
                            # Log the denial
                            AuditService.log_pto_deny(
                                db, user_id, approver_name, request_id, detail['employee_name'], reason
                            )
                            # Send email notification
                            email_service.send_pto_denied(
                                detail['employee_email'],
                                detail['employee_name'],
                                request.pto_type,
                                request.start_date,
                                request.end_date,
                                float(request.total_days),
                                approver_name,
                                reason
                            )
                            show_warning_dialog('Request Denied', 'PTO request has been denied')
                            ui.navigate.to('/calendar')
                        else:
                            show_error_dialog('Denial Failed', 'There was an error denying the request. Please try again.')
                    finally:
                        db.close()

                with ui.row().classes('w-full justify-between items-end mt-6'):
                    # Approve button on the left
                    ui.button('Approve', on_click=approve, color='positive')

                    # Denial reason and Deny button on the right
                    with ui.row().classes('gap-4 items-end'):
                        denial_input = ui.input('Denial Reason (optional)').classes('w-64')
                        ui.button('Deny', on_click=deny, color='negative')

            # Back button at the bottom - uses browser history for proper navigation
            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6')

    finally:
        db.close()
