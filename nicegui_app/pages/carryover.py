"""Carryover/rollover page - context-aware for Chicago vs non-Chicago employees."""
from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.models.carryover_request import CarryoverRequest
from src.models.leave_type import LeaveType
from src.database import get_db
from datetime import datetime, date
from decimal import Decimal
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_error_dialog, show_success_dialog
from nicegui_app.components.formatting import fmt_days, format_days_hours
from nicegui_app.components.policy_change_indicator import policy_change_badge, policy_change_tooltip
from src.services.policy_change_service import PolicyChangeService
from src.services.audit_service import AuditService


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


def carryover_page():
    """Page for leave rollover/carryover - adapts based on employee location."""

    apply_dark_mode()

    user = app.storage.user.get('user')
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
        policy_change_service = PolicyChangeService(db)

        current_user = user_service.get_user_by_id(user['id'])
        balance = balance_service.get_or_create_balance(user['id'], current_year)

        # Check if user is a Chicago employee
        is_chicago = current_user and current_user.location_city and current_user.location_city.lower() == 'chicago'

        if is_chicago:
            # ============ CHICAGO EMPLOYEE VIEW ============
            _render_chicago_rollover_view(current_user, balance, current_year, next_year)
        else:
            # ============ NON-CHICAGO EMPLOYEE VIEW ============
            _render_standard_carryover_view(
                db, user, current_user, balance, current_year, next_year,
                accrual_service, policy_change_service
            )

    finally:
        db.close()


def _render_chicago_rollover_view(current_user, balance, current_year, next_year):
    """Render the Chicago employee rollover view - informational, automatic rollover."""

    # Calculate Sick & Safe Leave (uses sick_* fields - company sick = Chicago Sick & Safe, 80hr max carryover)
    sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
    sick_used = float(balance.sick_used or 0)
    sick_pending = float(getattr(balance, 'sick_pending', 0) or 0)
    sick_unused = max(0, sick_total - sick_used - sick_pending)
    sick_max_carryover = 80  # Per Chicago ordinance
    sick_will_rollover = min(sick_unused, sick_max_carryover)
    sick_will_expire = max(0, sick_unused - sick_will_rollover)

    # Calculate Chicago Paid Leave (16hr/2-day max carryover)
    paid_leave_total = float(balance.chicago_paid_leave_total or 0) + float(balance.chicago_paid_leave_carryover or 0)
    paid_leave_used = float(balance.chicago_paid_leave_used or 0)
    paid_leave_pending = float(balance.chicago_paid_leave_pending or 0)
    paid_leave_unused = max(0, paid_leave_total - paid_leave_used - paid_leave_pending)
    paid_leave_max_carryover = 16  # Per Chicago ordinance (2 days)
    paid_leave_will_rollover = min(paid_leave_unused, paid_leave_max_carryover)
    paid_leave_will_expire = max(0, paid_leave_unused - paid_leave_will_rollover)

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='LEAVE ROLLOVER', show_back=False)
        ui.label(f'Your Chicago leave automatically rolls over to {next_year}').classes('opacity-70 mb-6')

        # Info banner
        with ui.card().classes('w-full mb-6').style('background: rgba(201, 162, 39, 0.1); border: 1px solid #C9A227;'):
            with ui.card_section().classes('p-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('location_city', size='lg').style('color: #C9A227;')
                    with ui.column().classes('gap-1'):
                        ui.label('Chicago Employee').classes('font-bold')
                        ui.label('Per Chicago ordinance, your leave balances roll over automatically on January 1st.').classes('text-sm opacity-80')

        # ============ CHICAGO LEAVE CARDS (HORIZONTAL LAYOUT) ============
        def build_leave_card(title: str, badge_text: str, color: str, icon: str,
                             unused_hrs: float, max_carryover: int, will_rollover: float):
            """Build a horizontal leave card: LEFT = icon/title/description, RIGHT = stats cards."""
            unused_display, unused_tooltip = format_days_hours(unused_hrs)
            rollover_display, rollover_tooltip = format_days_hours(will_rollover)
            max_days = max_carryover // 8

            with ui.card().classes('w-full').style(f'border-left: 4px solid {color};'):
                with ui.card_section().classes('p-4'):
                    with ui.row().classes('w-full items-start justify-between gap-6'):
                        # LEFT SIDE: Icon, Title, Badge/Description
                        with ui.column().classes('gap-2'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon(icon, size='2rem').style(f'color: {color};')
                                ui.label(title).classes('text-lg font-bold')
                            ui.label(badge_text).classes('text-xs px-2 py-1 rounded').style(f'border: 1px solid {color}; color: {color};')
                            ui.label(f'{max_carryover} hrs ({max_days}d) max carryover').classes('text-xs opacity-50 mt-1')

                        # RIGHT SIDE: Stats Cards (aligned columns)
                        with ui.row().classes('gap-3'):
                            # Unused Card
                            with ui.card().classes('p-3 text-center').style('width: 90px;'):
                                ui.label(unused_display).classes('text-xl font-bold').style(f'color: {color};').tooltip(unused_tooltip)
                                ui.label('UNUSED').classes('text-xs opacity-60')

                            # Rollover Card (highlighted)
                            with ui.card().classes('p-3 text-center').style('width: 90px; background: rgba(34, 197, 94, 0.15);'):
                                ui.label(rollover_display).classes('text-xl font-bold text-green-500').tooltip(rollover_tooltip)
                                ui.label(f'→ {next_year}').classes('text-xs opacity-60')

        with ui.column().classes('w-full gap-4'):
            # Sick Leave Card - uses company sick leave balance
            build_leave_card(
                title='SICK LEAVE',
                badge_text='Health Use Only',
                color='#22c55e',
                icon='medical_services',
                unused_hrs=sick_unused,
                max_carryover=sick_max_carryover,
                will_rollover=sick_will_rollover
            )

            # Paid Leave Card
            build_leave_card(
                title='PAID LEAVE',
                badge_text='Any Reason',
                color='#3b82f6',
                icon='event_available',
                unused_hrs=paid_leave_unused,
                max_carryover=paid_leave_max_carryover,
                will_rollover=paid_leave_will_rollover
            )

        # Info note
        with ui.row().classes('items-start gap-2 mt-4 opacity-60'):
            ui.icon('info', size='sm')
            ui.label('Your leave balances will automatically roll over on January 1st. No action required.').classes('text-sm')

        # Back button
        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6').style('border-color: #C9A227 !important; color: #C9A227 !important;')


def _render_standard_carryover_view(db, user, current_user, balance, current_year, next_year, accrual_service, policy_change_service):
    """Render the standard sick time carryover request view for non-Chicago employees."""

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
    sick_carryover_change = None
    if current_user and sick_leave_type:
        policy = accrual_service.get_policy_for_employee(current_user, 'SICK')
        if policy and policy.max_carryover_hours:
            max_carryover = float(policy.max_carryover_hours)
        sick_carryover_change = policy_change_service.get_change_for_field('sick_carryover_max', current_user)

    # Get existing carryover requests
    existing_requests = db.query(CarryoverRequest).filter(
        CarryoverRequest.employee_id == user['id'],
        CarryoverRequest.from_year == current_year
    ).order_by(CarryoverRequest.created_at.desc()).all()

    # Calculate already-approved carryover
    already_approved = 0
    pending_hours = 0
    for req in existing_requests:
        if req.status == 'approved':
            already_approved += float(req.hours_approved or req.hours_requested)
        elif req.status == 'pending':
            pending_hours += float(req.hours_requested)

    remaining_cap = max(0, max_carryover - already_approved) if max_carryover > 0 else sick_unused

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='SICK TIME CARRYOVER', show_back=False)
        ui.label(f'Carry unused {current_year} sick time into {next_year}').classes('opacity-70 mb-6')

        carryover_amount = min(sick_unused, remaining_cap) if max_carryover > 0 else sick_unused
        will_expire = max(0, sick_unused - carryover_amount)
        has_pending = pending_hours > 0

        if sick_unused > 0 and sick_leave_type and carryover_amount > 0 and not has_pending:
            with ui.card().classes('w-full mb-6').style('border-left: 4px solid #C9A227;'):
                with ui.card_section().classes('p-6'):
                    with ui.row().classes('items-center gap-3 mb-6'):
                        ui.icon('sync', size='2rem').style('color: #C9A227;')
                        ui.label('Carryover Summary').classes('text-xl font-bold')

                    with ui.column().classes('gap-4 w-full'):
                        with ui.row().classes('w-full justify-between items-center py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1);'):
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Your Unused Sick Time').classes('opacity-80')
                                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                    'Unused Sick Time',
                                    'This is your remaining sick time balance for the current year.'
                                )).props('flat dense round size=sm').style('color: #f59e0b')
                            sick_display, sick_tooltip = format_days_hours(sick_unused)
                            ui.label(sick_display).classes('font-bold text-lg').tooltip(sick_tooltip)

                        if max_carryover > 0:
                            with ui.row().classes('w-full justify-between items-center py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1);'):
                                with ui.row().classes('items-center gap-1'):
                                    ui.label('Policy Maximum').classes('opacity-80')
                                    if sick_carryover_change:
                                        policy_change_badge(sick_carryover_change)
                                    ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                        'Policy Maximum',
                                        'Your location\'s policy sets a maximum number of sick hours that can be carried over each year.'
                                    )).props('flat dense round size=sm').style('color: #f59e0b')
                                value_label = ui.label(f'{max_carryover:.0f} hrs').classes('font-medium')
                                if sick_carryover_change:
                                    value_label.tooltip(policy_change_tooltip(sick_carryover_change))

                            if already_approved > 0:
                                with ui.row().classes('w-full justify-between items-center py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1);'):
                                    with ui.row().classes('items-center gap-1'):
                                        ui.label('Already Approved').classes('opacity-80')
                                        ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                            'Already Approved',
                                            'Hours you\'ve already requested and had approved for carryover this year.'
                                        )).props('flat dense round size=sm').style('color: #f59e0b')
                                    ui.label(f'{already_approved:.0f} hrs').classes('font-medium text-green-500')

                        with ui.row().classes('w-full justify-between items-center py-3 mt-2').style('background: rgba(201, 162, 39, 0.1); border-radius: 8px; padding-left: 12px; padding-right: 12px;'):
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Will Carry Over to ' + str(next_year)).classes('font-medium')
                                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                    'Carryover Amount',
                                    f'This is the amount of sick time that will transfer to {next_year}.'
                                )).props('flat dense round size=sm').style('color: #f59e0b')
                            carryover_display, carryover_tooltip = format_days_hours(carryover_amount)
                            ui.label(carryover_display).classes('font-bold text-xl').style('color: #22c55e;').tooltip(carryover_tooltip)

                        if will_expire > 0:
                            with ui.row().classes('w-full justify-between items-center py-2'):
                                with ui.row().classes('items-center gap-1'):
                                    ui.label('Will Expire (Use Before Year-End)').classes('opacity-80')
                                    ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                                        'Expiring Hours',
                                        'These hours exceed your policy\'s carryover limit and will be lost on January 1st if not used.'
                                    )).props('flat dense round size=sm').style('color: #f59e0b')
                                expire_display, expire_tooltip = format_days_hours(will_expire)
                                ui.label(expire_display).classes('font-medium text-red-500').tooltip(expire_tooltip)

            def submit_carryover():
                db_inner = next(get_db())
                try:
                    user_service_inner = UserService(db_inner)
                    current_employee = user_service_inner.get_user_by_id(user['id'])
                    user_role = current_employee.role if current_employee else 'employee'

                    auto_approve = user_role in ['manager', 'admin', 'superadmin']
                    if not auto_approve and max_carryover > 0 and carryover_amount <= max_carryover:
                        auto_approve = True

                    request = CarryoverRequest(
                        employee_id=user['id'],
                        leave_type_id=sick_leave_type.id,
                        from_year=current_year,
                        to_year=next_year,
                        hours_requested=Decimal(str(carryover_amount)),
                        status='approved' if auto_approve else 'pending',
                        employee_notes='Unused sick time carryover request'
                    )

                    if auto_approve:
                        request.approved_by = user['id']
                        request.approved_at = datetime.now()
                        request.hours_approved = Decimal(str(carryover_amount))
                        request.manager_notes = 'Auto-approved per policy'

                    db_inner.add(request)
                    db_inner.commit()
                    db_inner.refresh(request)

                    AuditService.log_carryover_request(
                        db=db_inner,
                        user_id=user['id'],
                        username=user.get('username'),
                        request_id=request.id,
                        hours=float(carryover_amount),
                        from_year=current_year,
                        to_year=next_year
                    )

                    if auto_approve:
                        AuditService.log_carryover_approve(
                            db=db_inner,
                            approver_id=user['id'],
                            approver_name=user.get('full_name', user.get('username')),
                            request_id=request.id,
                            employee_name=user.get('full_name', user.get('username')),
                            hours_approved=float(carryover_amount)
                        )

                    msg = 'Carryover approved!' if auto_approve else 'Request submitted for manager approval'
                    show_success_dialog('Carryover Request', msg, on_close=lambda: ui.navigate.to('/carryover'))

                except Exception as e:
                    show_error_dialog('Error', f'An error occurred: {str(e)}')
                finally:
                    db_inner.close()

            ui.button(
                f'Request Carryover ({carryover_amount:.0f} hrs)',
                icon='check_circle',
                on_click=submit_carryover
            ).classes('w-full text-lg py-4').style('background-color: #C9A227 !important; color: white !important;')

            with ui.row().classes('items-start gap-2 mt-4 opacity-60'):
                ui.icon('info', size='sm')
                ui.label('Your sick time will automatically carry over on January 1st once approved.').classes('text-sm')

        elif has_pending:
            with ui.card().classes('w-full mb-4').style('border-left: 4px solid #f59e0b;'):
                with ui.card_section().classes('p-6'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('schedule', size='2rem', color='orange')
                        with ui.column().classes('gap-1'):
                            ui.label('Request Pending').classes('font-bold text-lg')
                            ui.label(f'You already have a pending carryover request for {pending_hours:.0f} hrs.').classes('opacity-80')
                            ui.label('Please wait for manager approval or cancel the existing request.').classes('text-sm opacity-60')

        elif sick_unused > 0 and carryover_amount <= 0:
            with ui.card().classes('w-full mb-4').style('border-left: 4px solid #f59e0b;'):
                with ui.card_section().classes('p-6'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('warning', size='2rem', color='amber')
                        with ui.column().classes('gap-1'):
                            ui.label('Carryover Cap Reached').classes('font-bold text-lg')
                            ui.label(f'You have already approved {already_approved:.0f} hrs of carryover.').classes('opacity-80')
                            ui.label(f'Policy maximum is {max_carryover:.0f} hrs - no additional carryover allowed.').classes('text-sm opacity-60')

        else:
            with ui.card().classes('w-full mb-4'):
                with ui.card_section().classes('p-6 text-center'):
                    ui.icon('sentiment_satisfied', size='3rem').classes('opacity-30 mb-4')
                    ui.label('No Sick Time to Carry Over').classes('text-lg font-medium opacity-70')
                    ui.label('You have used all your sick time this year.').classes('text-sm opacity-50')

        if existing_requests:
            ui.separator().classes('my-6')
            ui.label('Your Carryover Requests').classes('text-lg font-semibold mb-4')

            for req in existing_requests:
                hrs = float(req.hours_requested)
                status_icon = {'approved': 'check_circle', 'denied': 'cancel', 'pending': 'schedule'}.get(req.status, 'help')
                status_color = {'approved': 'green', 'denied': 'red', 'pending': 'orange'}.get(req.status, 'gray')

                with ui.card().classes('w-full mb-2'):
                    with ui.card_section().classes('p-4'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon(status_icon, color=status_color, size='md')
                                with ui.column().classes('gap-0'):
                                    req_display, req_tooltip = format_days_hours(hrs)
                                    ui.label(req_display).classes('font-medium').tooltip(req_tooltip)
                                    ui.label(req.status.upper()).classes(f'text-xs text-{status_color}-500')
                            ui.label(req.created_at.strftime('%b %d, %Y')).classes('text-sm opacity-60')

                        if req.status == 'approved' and req.hours_approved:
                            approved_hrs = float(req.hours_approved)
                            if approved_hrs != hrs:
                                ui.label(f'Approved: {approved_hrs:.0f} hrs').classes('text-sm text-green-500 mt-2')

                        if req.status == 'denied' and req.manager_notes:
                            ui.label(f'Reason: {req.manager_notes}').classes('text-sm text-red-500 mt-2')

        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6').style('border-color: #C9A227 !important; color: #C9A227 !important;')
