"""Manager request detail page for approval/denial."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from nicegui_app.components.formatting import fmt_days
from src.services.pto_service import PTOService
from src.services.audit_service import AuditService
from src.services.email_service import email_service


def manager_request_detail_page(request_id: int):
    """Request detail page for approval/denial content."""
    apply_dark_mode()

    current_user = app.storage.general.get('user', {})
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

        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
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

                # Current Balance Card
                with ui.card().classes('flex-1 p-4'):
                    ui.label('Current PTO Balance').classes('text-xl font-bold mb-3')
                    # Convert hours to days (8 hours = 1 day)
                    # Include carryover and subtract pending for accurate available balance
                    vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                    vac_used = float(balance.vacation_used or 0)
                    vac_pending = float(balance.vacation_pending or 0)
                    vac_avail = (vac_total - vac_used - vac_pending) / 8

                    sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
                    sick_avail = (sick_total - float(balance.sick_used or 0)) / 8

                    personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
                    personal_avail = (personal_total - float(balance.personal_used or 0)) / 8

                    with ui.column().classes('gap-2'):
                        with ui.row().classes('items-center gap-2'):
                            ui.element('div').classes('w-3 h-3 rounded-full bg-blue-500')
                            vac_label = f"Vacation: {fmt_days(vac_avail)} days available"
                            if vac_pending > 0:
                                vac_label += f" ({fmt_days(vac_pending/8)} pending)"
                            ui.label(vac_label)
                        with ui.row().classes('items-center gap-2'):
                            ui.element('div').classes('w-3 h-3 rounded-full bg-green-500')
                            ui.label(f"Sick: {fmt_days(sick_avail)} days available")
                        with ui.row().classes('items-center gap-2'):
                            ui.element('div').classes('w-3 h-3 rounded-full bg-purple-500')
                            ui.label(f"Personal: {fmt_days(personal_avail)} days available")

            # Request Details Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Request Details').classes('text-xl font-bold mb-2')
                ui.label(f"Type: {request.pto_type.title()}")
                ui.label(f"Start Date: {request.start_date.strftime('%Y-%m-%d')}")
                ui.label(f"End Date: {request.end_date.strftime('%Y-%m-%d')}")
                ui.label(f"Total Days: {fmt_days(float(request.total_days))}")
                ui.label(f"Status: {request.status.title()}")
                ui.label(f"Submitted: {request.submitted_at.strftime('%Y-%m-%d %H:%M')}")
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

                            with ui.card().classes('w-full p-3'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('items-center gap-3'):
                                        ui.icon(status_icon, color=status_color)
                                        with ui.column().classes('gap-0'):
                                            ui.label(conflict['user_name']).classes('font-semibold')
                                            ui.label(f"{conflict['pto_type'].title()} - {conflict['total_days']} day(s)").classes('text-sm opacity-70')
                                    with ui.column().classes('text-right gap-0'):
                                        if conflict['start_date'] == conflict['end_date']:
                                            ui.label(conflict['start_date'].strftime('%b %d, %Y')).classes('text-sm')
                                        else:
                                            ui.label(f"{conflict['start_date'].strftime('%b %d')} - {conflict['end_date'].strftime('%b %d, %Y')}").classes('text-sm')
                                        ui.badge(conflict['status'].title(), color=status_color)

                    ui.label(
                        'Note: Concurrent leave is allowed, but please consider staffing needs before approving.'
                    ).classes('text-xs opacity-60 mt-3 italic')

            # Approval Actions
            if request.status == 'pending':
                def approve():
                    db = next(get_db())
                    try:
                        current_user = app.storage.general.get('user')
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
                            ui.notify('Request approved!', type='positive')
                            ui.navigate.to('/dashboard')
                        else:
                            ui.notify('Error approving request', type='negative')
                    finally:
                        db.close()

                def deny():
                    db = next(get_db())
                    try:
                        reason = denial_input.value or 'No reason provided'
                        current_user = app.storage.general.get('user')
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
                            ui.notify('Request denied', type='warning')
                            ui.navigate.to('/dashboard')
                        else:
                            ui.notify('Error denying request', type='negative')
                    finally:
                        db.close()

                with ui.row().classes('w-full justify-between items-end mt-6'):
                    # Approve button on the left
                    ui.button('Approve', on_click=approve, color='positive')

                    # Denial reason and Deny button on the right
                    with ui.row().classes('gap-4 items-end'):
                        denial_input = ui.input('Denial Reason (optional)').classes('w-64')
                        ui.button('Deny', on_click=deny, color='negative')

            # Back button at the bottom
            ui.button('Back to Calendar', icon='arrow_back', on_click=lambda: ui.navigate.to('/calendar')).props('outline').classes('mt-6')

    finally:
        db.close()
