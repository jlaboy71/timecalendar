"""User's PTO request history page with filtering and cancel functionality."""
from datetime import date, datetime
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog
from nicegui_app.components.realtime_updates import setup_dashboard_updates
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.services.audit_service import AuditService
from src.services.email_service import email_service
from src.services.user_service import UserService
from src.models.user import User
from src.models.system_setting import SystemSetting
from nicegui_app.components.formatting import format_days_hours, fmt_days


def cancel_user_request(request_id: int, pto_type: str, total_days: float, year: int):
    """Cancel a user's pending PTO request (for employees).

    Note: pto_type, total_days, year params kept for API compatibility but not used.
    PTOService.cancel_request handles all balance restoration for ALL PTO types.
    """
    db = None
    try:
        db = next(get_db())
        current_user = app.storage.user.get('user', {})
        user_id = current_user.get('id')

        # Use PTOService.cancel_request which handles ALL PTO types correctly
        pto_service = PTOService(db)
        pto_service.cancel_request(request_id, user_id)

        # Audit log the cancellation
        AuditService.log_pto_cancel(
            db=db,
            user_id=user_id,
            username=current_user.get('username'),
            request_id=request_id,
            employee_name=current_user.get('full_name', current_user.get('username')),
            cancelled_by_self=True
        )

        show_success_dialog('Success', 'Request cancelled successfully', on_close=lambda: ui.navigate.to('/requests'))

    except ValueError as e:
        # PTOService raises ValueError for validation errors (not found, not pending, not owner)
        show_warning_dialog('Cannot Cancel', str(e))
    except Exception as e:
        show_error_dialog('Error', f'Error cancelling request: {str(e)}')
    finally:
        if db:
            db.close()


def cancel_approved_request(request_id: int, pto_type: str, total_days: float, year: int):
    """Cancel an approved PTO request (for managers/admins) with balance recalculation."""
    db = None
    try:
        db = next(get_db())
        from src.models.pto_request import PTORequest

        request = db.query(PTORequest).filter(PTORequest.id == request_id).first()

        if not request:
            show_error_dialog('Not Found', 'The request was not found.')
            return

        if request.status != 'approved':
            show_warning_dialog('Cannot Cancel', 'Only approved requests can be cancelled this way.')
            return

        # Get employee name before commit
        employee_name = request.user.full_name if request.user else 'Unknown'

        # Update the request status
        request.status = 'cancelled'

        # Use centralized balance restoration
        # For vacation rollover, use carryover_from_year for balance lookup
        pto_type_lower = pto_type.lower()
        if pto_type_lower in ['vacation', 'sick', 'personal']:
            balance_service = BalanceService(db)
            balance_year = request.carryover_from_year if request.carryover_from_year else year
            balance = balance_service.get_or_create_balance(request.user_id, balance_year)
            # Restore balance using centralized method (was_approved=True since we're cancelling approved request)
            balance_service.restore_balance(balance.id, pto_type_lower, total_days * 8, was_approved=True)

        db.commit()

        # Audit log the cancellation (manager/admin cancelling)
        current_user = app.storage.user.get('user', {})
        AuditService.log_pto_cancel(
            db=db,
            user_id=current_user.get('id'),
            username=current_user.get('username'),
            request_id=request_id,
            employee_name=employee_name,
            cancelled_by_self=False
        )

        show_success_dialog('Success', 'Request cancelled and balance restored', on_close=lambda: ui.navigate.to('/requests'))

    except Exception as e:
        show_error_dialog('Error', f'Error cancelling request: {str(e)}')
    finally:
        if db:
            db.close()


def request_cancellation(request_id: int, reason: str = None):
    """Submit a cancellation request for an approved PTO (for employees)."""
    db = None
    try:
        db = next(get_db())
        from src.models.pto_request import PTORequest

        request = db.query(PTORequest).filter(PTORequest.id == request_id).first()

        if not request:
            show_error_dialog('Not Found', 'The request was not found.')
            return

        if request.status != 'approved':
            show_warning_dialog('Cannot Request Cancellation', 'Only approved requests can have cancellation requested.')
            return

        if request.cancellation_requested:
            show_warning_dialog('Already Requested', 'A cancellation has already been requested for this time off.')
            return

        # VACATION ROLLOVER: Employees cannot cancel approved rollover - only manager can
        if request.carryover_from_year and request.pto_type.lower() == 'vacation':
            show_warning_dialog('Cannot Cancel Rollover',
                'Approved vacation rollover cannot be cancelled by the employee. '
                'Please contact your manager to cancel this time off.')
            return

        # Mark cancellation as requested
        request.cancellation_requested = True
        request.cancellation_reason = reason.strip() if reason else None
        request.cancellation_requested_at = datetime.now()

        db.commit()
        show_success_dialog('Request Submitted', 'Cancellation request submitted to your manager', on_close=lambda: ui.navigate.to('/requests'))

    except Exception as e:
        show_error_dialog('Error', f'Error requesting cancellation: {str(e)}')
    finally:
        if db:
            db.close()


def show_request_detail_dialog(request, current_user_id: int, user_role: str):
    """Show detailed information about a PTO request with double-confirmation delete."""
    type_colors = {
        'vacation': 'blue', 'sick': 'green', 'personal': 'purple',
        'bereavement': 'brown', 'fmla': 'teal', 'jury_duty': 'indigo',
        'voting': 'cyan', 'military': 'deep-orange', 'work_from_home': 'red'
    }
    type_icons = {
        'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person',
        'bereavement': 'sentiment_very_dissatisfied', 'fmla': 'family_restroom',
        'jury_duty': 'gavel', 'voting': 'how_to_vote', 'military': 'military_tech',
        'work_from_home': 'home_work'
    }
    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}

    pto_type_lower = request.pto_type.lower()
    header_color = type_colors.get(pto_type_lower, 'grey')

    # Store request info for handlers
    req_id = request.id
    req_type = request.pto_type
    req_total_days = float(request.total_days)
    req_year = request.start_date.year
    req_user_id = request.user_id
    req_status = request.status
    req_carryover_from_year = getattr(request, 'carryover_from_year', None)

    # Determine title - add (CarryOver) if vacation uses previous year balance
    title_label = f'{request.pto_type.title()} (CarryOver)' if req_carryover_from_year and pto_type_lower == 'vacation' else request.pto_type.title()

    with ui.dialog() as detail_dialog, ui.card().classes('w-full max-w-md p-0'):
        # Header with colored background
        with ui.row().classes(f'w-full justify-between items-center p-4 bg-{header_color}-500 text-white'):
            with ui.row().classes('gap-2 items-center'):
                ui.icon(type_icons.get(pto_type_lower, 'event')).classes('text-2xl')
                ui.label(f'{title_label} Time Off').classes('text-lg font-bold')
            ui.button(icon='close', on_click=detail_dialog.close).props('flat round dense color=white')

        # Content
        with ui.column().classes('w-full p-4 gap-4'):
            # Status badge
            with ui.row().classes('w-full justify-center'):
                ui.badge(request.status.title(), color=status_colors.get(request.status, 'grey')).classes('text-lg px-4 py-1')

            # Date info
            with ui.card().classes('w-full p-3'):
                ui.label('Dates').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                if request.start_date == request.end_date:
                    ui.label(request.start_date.strftime('%A, %B %d, %Y')).classes('font-medium')
                else:
                    ui.label(f"{request.start_date.strftime('%A, %B %d, %Y')}").classes('font-medium')
                    ui.label('to').classes('text-xs opacity-60')
                    ui.label(f"{request.end_date.strftime('%A, %B %d, %Y')}").classes('font-medium')

            # Duration
            with ui.card().classes('w-full p-3'):
                ui.label('Duration').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                hours = float(request.total_days) * 8
                duration_display, duration_tooltip = format_days_hours(hours)
                ui.label(duration_display).classes('font-medium').tooltip(duration_tooltip)

            # Notes (if any)
            if request.notes:
                with ui.card().classes('w-full p-3'):
                    ui.label('Notes').classes('text-xs font-semibold uppercase opacity-60 mb-2')
                    ui.label(request.notes).classes('text-sm')

            # Denial reason (if denied)
            if request.status == 'denied' and hasattr(request, 'denial_reason') and request.denial_reason:
                with ui.card().classes('w-full p-3 border-l-4 border-red-500'):
                    ui.label('Denial Reason').classes('text-xs font-semibold uppercase text-red-500 mb-2')
                    ui.label(request.denial_reason).classes('text-sm')

            # Manager Approval info (if approved)
            if request.status == 'approved' and hasattr(request, 'approved_at') and request.approved_at:
                with ui.card().classes('w-full p-3 border-l-4 border-green-500'):
                    ui.label('Manager Approved').classes('text-xs font-semibold uppercase text-green-600 mb-2')
                    ui.label(request.approved_at.strftime('%A, %B %d, %Y')).classes('font-medium')

            # Cancellation pending indicator
            if request.status == 'approved' and hasattr(request, 'cancellation_requested') and request.cancellation_requested:
                with ui.card().classes('w-full p-3 border-l-4 border-amber-500'):
                    ui.label('Cancellation Pending').classes('text-xs font-semibold uppercase text-amber-600 mb-2')
                    ui.label('Awaiting manager approval').classes('text-sm')

            # Submission info
            with ui.row().classes('w-full justify-center text-xs opacity-50'):
                ui.label(f'Submitted: {request.submitted_at.strftime("%b %d, %Y")}')

            # Delete button with double confirmation (only for present/future dates)
            is_future_or_today = request.start_date >= date.today()
            if req_status in ['pending', 'approved'] and is_future_or_today:
                def show_first_confirm():
                    """First confirmation dialog."""
                    detail_dialog.close()
                    with ui.dialog() as confirm1, ui.card().classes('p-4 max-w-sm'):
                        ui.label('Delete this time off?').classes('text-lg font-semibold mb-2')
                        ui.label('This will cancel the request and restore your PTO balance.').classes('text-sm opacity-70 mb-4')
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('No, Keep It', on_click=confirm1.close).props('flat')
                            def show_second_confirm():
                                confirm1.close()
                                # Second confirmation
                                with ui.dialog() as confirm2, ui.card().classes('p-4 max-w-sm'):
                                    ui.label('Are you sure?').classes('text-lg font-semibold mb-2 text-red-600')
                                    ui.label('This action cannot be undone.').classes('text-sm opacity-70 mb-4')
                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button('Cancel', on_click=confirm2.close).props('flat')
                                        def do_delete():
                                            confirm2.close()
                                            delete_request_with_balance(req_id, req_type, req_total_days, req_year, req_user_id, req_status)
                                        ui.button('Yes, Delete', on_click=do_delete).props('color=negative')
                                confirm2.open()
                            ui.button('Yes, Delete', on_click=show_second_confirm).props('color=negative')
                    confirm1.open()

                with ui.row().classes('w-full justify-end mt-2'):
                    ui.button('Delete', icon='delete', on_click=show_first_confirm).props('color=negative')

    detail_dialog.open()


def delete_request_with_balance(request_id: int, pto_type: str, total_days: float, year: int, user_id: int, status: str):
    """Delete a request and restore balance (used by double confirmation delete)."""
    db = None
    try:
        db = next(get_db())
        from src.models.pto_request import PTORequest

        request = db.query(PTORequest).filter(PTORequest.id == request_id).first()
        if not request:
            show_error_dialog('Not Found', 'The request was not found.')
            return

        # Store info for manager notification before changing status
        was_approved = status == 'approved'
        employee_name = request.user.full_name if request.user else 'Unknown'
        start_date = request.start_date
        end_date = request.end_date

        # Get manager info if this was an approved request
        manager_email = None
        manager_name = None
        if was_approved and request.user and request.user.department and request.user.department.manager:
            manager = request.user.department.manager
            manager_email = manager.email
            manager_name = manager.first_name

        # Check for carryover_from_year before cancelling
        carryover_from_year = getattr(request, 'carryover_from_year', None)

        request.status = 'cancelled'

        # Restore balance based on PTO type and previous status
        # IMPORTANT: For carryover requests, restore to the FROM year (carryover_from_year)
        pto_type_lower = pto_type.lower()
        if pto_type_lower in ['vacation', 'sick', 'personal']:
            balance_service = BalanceService(db)
            hours_to_restore = total_days * 8

            if status == 'pending':
                balance = balance_service.get_or_create_balance(user_id, year)
                if pto_type_lower == 'vacation':
                    balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)
            else:  # approved
                # For vacation carryover, restore to the correct year
                if pto_type_lower == 'vacation' and carryover_from_year:
                    # Restore to the FROM year (e.g., 2025)
                    balance = balance_service.get_or_create_balance(user_id, carryover_from_year)
                    balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                else:
                    balance = balance_service.get_or_create_balance(user_id, year)
                    if pto_type_lower == 'vacation':
                        balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                    elif pto_type_lower == 'sick':
                        balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                    elif pto_type_lower == 'personal':
                        balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

        db.commit()

        # Audit log the cancellation
        current_user = app.storage.user.get('user', {})
        AuditService.log_pto_cancel(
            db=db,
            user_id=current_user.get('id'),
            username=current_user.get('username'),
            request_id=request_id,
            employee_name=employee_name,
            cancelled_by_self=(current_user.get('id') == user_id)
        )

        # Send manager notification if this was an approved request
        if was_approved and manager_email:
            try:
                email_service.send_pto_cancelled_notification(
                    manager_email=manager_email,
                    manager_name=manager_name,
                    employee_name=employee_name,
                    pto_type=pto_type,
                    start_date=start_date,
                    end_date=end_date,
                    total_days=total_days
                )
            except Exception:
                pass  # Don't block success if email fails

        show_success_dialog('Success', 'Request deleted and balance restored', on_close=lambda: ui.navigate.to('/requests'))

    except Exception as e:
        show_error_dialog('Error', f'Error deleting request: {str(e)}')
    finally:
        if db:
            db.close()


def requests_page():
    """User's PTO request history page content."""
    apply_dark_mode()

    user = app.storage.user.get('user')
    user_role = user.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # Current filter state - managers default to 'approved' since their requests auto-approve
    current_filter = {'value': 'approved' if is_manager_or_admin else 'pending'}

    # Year filter state - default to current year, use storage to persist selection
    current_year = date.today().year
    next_year = current_year + 1
    stored_year = app.storage.user.get('requests_year_filter', current_year)
    year_filter = {'value': stored_year if stored_year in [current_year, next_year] else current_year}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):
        # Page title is always TIME OFF
        page_header(title='TIME OFF', show_back=False)

        db = next(get_db())
        try:
            # Get current user's department members (for team view) - need this BEFORE view_state
            current_user_obj = db.query(User).filter(User.id == user['id']).first()
            team_members = []
            team_member_ids = set()
            if is_manager_or_admin and current_user_obj and current_user_obj.department_id:
                team_members_db = db.query(User).filter(
                    User.department_id == current_user_obj.department_id,
                    User.is_active == True
                ).order_by(User.last_name, User.first_name).all()
                # Convert to dict for dropdown
                team_members = [{'id': u.id, 'name': f"{u.first_name} {u.last_name}"} for u in team_members_db]
                team_member_ids = {u.id for u in team_members_db}

            # View state: 'my' or 'team' - persist selection in storage
            stored_view_user_id = app.storage.user.get('requests_view_user_id', None)
            # Validate stored selection is still valid (user is in team)
            if stored_view_user_id and stored_view_user_id != user['id'] and stored_view_user_id in team_member_ids:
                view_state = {'mode': 'team', 'selected_user_id': stored_view_user_id}
            else:
                view_state = {'mode': 'my', 'selected_user_id': user['id']}

            # Check if viewed user is Chicago employee (for LEAVE tile)
            # When viewing team member, check THEIR location, not the logged-in manager's
            viewed_user_obj = current_user_obj
            if view_state['mode'] == 'team' and view_state['selected_user_id'] != user['id']:
                viewed_user_obj = db.query(User).filter(User.id == view_state['selected_user_id']).first()
            is_chicago_employee = viewed_user_obj and viewed_user_obj.location_city and viewed_user_obj.location_city.lower() == 'chicago'
            chicago_setting = db.query(SystemSetting).filter(SystemSetting.key == 'chicago.safe_leave_enabled').first()
            show_chicago_leave = is_chicago_employee and chicago_setting and chicago_setting.bool_value

            # Container refs for dynamic updates
            content_container = None
            team_selector_container = None

            def get_requests_for_user(target_user_id):
                """Get requests for a specific user."""
                return PTOService.get_user_requests(db, target_user_id)

            all_user_requests = get_requests_for_user(view_state['selected_user_id'])

            # Sort by submitted_at descending (newest first)
            all_user_requests_sorted = sorted(all_user_requests, key=lambda r: r.submitted_at, reverse=True)

            # Filter by year - use start_date year
            def get_year_filtered_requests(year):
                return [r for r in all_user_requests_sorted if r.start_date.year == year]

            user_requests_sorted = get_year_filtered_requests(year_filter['value'])

            # Summary stats (will be updated when year changes)
            pending_requests = [r for r in user_requests_sorted if r.status == 'pending']
            approved_requests = [r for r in user_requests_sorted if r.status == 'approved']
            denied_requests = [r for r in user_requests_sorted if r.status == 'denied']

            # results_container will be created after stat cards (see below)
            results_container = None

            def set_filter(filter_type):
                """Set the filter and re-render the list. Toggle: clicking same status shows all approved."""
                # Toggle behavior: if clicking same status, show all approved
                if current_filter['value'] == filter_type:
                    current_filter['value'] = None
                    render_requests_by_type(approved_requests, None)
                    return

                current_filter['value'] = filter_type
                # Filter and render
                if filter_type == 'approved':
                    render_requests_by_type(approved_requests, 'Approved')
                elif filter_type == 'pending':
                    render_requests_by_type(pending_requests, 'Pending')
                elif filter_type == 'denied':
                    render_requests_by_type(denied_requests, 'Denied')

            # Store references (not used for styling anymore, but kept for compatibility)
            filter_buttons = {}

            # Calculate totals by type (for approved requests)
            vacation_approved = [r for r in approved_requests if r.pto_type.lower() == 'vacation']
            sick_approved = [r for r in approved_requests if r.pto_type.lower() == 'sick']
            personal_approved = [r for r in approved_requests if r.pto_type.lower() == 'personal']
            # Other types
            other_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']
            other_approved = [r for r in approved_requests if r.pto_type.lower() in other_types]

            # Type filter state for the list - use set for multi-select
            type_filter = {'selected': set()}
            tile_cards = {}  # Store card references for style updates
            other_dropdown_ref = {'select': None}

            # PTO type info for empty state cards and info dialogs
            pto_type_info = {
                'vacation': {
                    'name': 'Vacation',
                    'icon': 'beach_access',
                    'color': '#3b82f6',
                    'border': 'border-blue-500',
                    'description': 'Paid time off for personal rest, travel, or leisure activities. Accrues based on tenure and can be carried over per company policy.'
                },
                'sick': {
                    'name': 'Sick Leave',
                    'icon': 'medical_services',
                    'color': '#22c55e',
                    'border': 'border-green-500',
                    'description': 'Time off for illness, medical appointments, or caring for sick family members. Does not require advance notice for genuine illness.'
                },
                'personal': {
                    'name': 'Personal Day',
                    'icon': 'person',
                    'color': '#a855f7',
                    'border': 'border-purple-500',
                    'description': 'Flexible time off for personal matters that don\'t fall under other categories. Use for appointments, errands, or personal needs.'
                },
                'work_from_home': {
                    'name': 'Work From Home',
                    'icon': 'home_work',
                    'color': '#ef4444',
                    'border': 'border-red-500',
                    'description': 'Remote work request to work from home instead of the office. Subject to manager approval and job requirements.'
                },
                'bereavement': {
                    'name': 'Bereavement Leave',
                    'icon': 'sentiment_very_dissatisfied',
                    'color': '#78716c',
                    'border': 'border-stone-500',
                    'description': 'Paid time off following the death of a family member. Immediate family: up to 5 days. Extended family: up to 3 days.'
                },
                'fmla': {
                    'name': 'FMLA Leave',
                    'icon': 'family_restroom',
                    'color': '#14b8a6',
                    'border': 'border-teal-500',
                    'description': 'Family and Medical Leave Act protected leave for qualifying medical or family situations. Up to 12 weeks unpaid, job-protected.'
                },
                'jury_duty': {
                    'name': 'Jury Duty',
                    'icon': 'gavel',
                    'color': '#6366f1',
                    'border': 'border-indigo-500',
                    'description': 'Paid time off for jury service. Provide court documentation upon return.'
                },
                'voting': {
                    'name': 'Voting Leave',
                    'icon': 'how_to_vote',
                    'color': '#06b6d4',
                    'border': 'border-cyan-500',
                    'description': 'Time off to vote in elections if unable to vote outside work hours. Up to 2 hours as needed.'
                },
                'military': {
                    'name': 'Military Leave',
                    'icon': 'military_tech',
                    'color': '#f97316',
                    'border': 'border-orange-500',
                    'description': 'Leave for military service or training per USERRA requirements. Job protection guaranteed.'
                },
                'chicago_leave': {
                    'name': 'Chicago Paid Leave',
                    'icon': 'spa',
                    'color': '#f59e0b',
                    'border': 'border-amber-500',
                    'description': 'Chicago Paid Leave per city ordinance. Accrues based on hours worked and can be used for any reason. Cannot exceed available accrued balance.'
                }
            }

            # Status info for empty state cards and info dialogs
            status_info = {
                'approved': {
                    'name': 'Approved Requests',
                    'icon': 'check_circle',
                    'color': '#22c55e',
                    'border': 'border-green-500',
                    'description': 'Approved requests have been reviewed and confirmed by your manager. These hours are deducted from your balance and the time off is officially scheduled.'
                },
                'pending': {
                    'name': 'Pending Requests',
                    'icon': 'pending',
                    'color': '#f59e0b',
                    'border': 'border-amber-500',
                    'description': 'Pending requests are awaiting manager approval. Your balance shows these hours as "pending" until approved or denied. You\'ll receive notification once a decision is made.'
                },
                'denied': {
                    'name': 'Denied Requests',
                    'icon': 'cancel',
                    'color': '#ef4444',
                    'border': 'border-red-500',
                    'description': 'Denied requests were not approved by your manager. The denial reason should be provided. You may resubmit with different dates or discuss with your manager.'
                }
            }

            def show_pto_type_info(type_code):
                """Show info dialog for a PTO type."""
                info = pto_type_info.get(type_code, {})
                with ui.dialog() as info_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
                    with ui.row().classes('items-center gap-3 mb-4'):
                        ui.icon(info.get('icon', 'event'), size='lg').style(f'color: {info.get("color", "#6b7280")};')
                        ui.label(info.get('name', type_code.replace('_', ' ').title())).classes('text-lg font-bold').style(f'color: {info.get("color", "#6b7280")};')
                    ui.label(info.get('description', 'No description available.')).classes('text-sm opacity-80')
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('OK', on_click=info_dialog.close).style('background-color: #C9A227 !important; color: white !important;')
                info_dialog.open()

            def show_status_info(status):
                """Show info dialog for a status."""
                info = status_info.get(status, {})
                with ui.dialog() as info_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
                    with ui.row().classes('items-center gap-3 mb-4'):
                        ui.icon(info.get('icon', 'info'), size='lg').style(f'color: {info.get("color", "#6b7280")};')
                        ui.label(info.get('name', status.title())).classes('text-lg font-bold').style(f'color: {info.get("color", "#6b7280")};')
                    ui.label(info.get('description', 'No description available.')).classes('text-sm opacity-80')
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('OK', on_click=info_dialog.close).style('background-color: #C9A227 !important; color: white !important;')
                info_dialog.open()

            def render_requests_by_type(requests_to_show, filter_names=None):
                """Render requests, optionally filtered by type(s)."""
                results_container.clear()
                with results_container:
                    # Show filter indicator if filtering
                    if filter_names:
                        with ui.row().classes('w-full items-center gap-2 mb-2'):
                            ui.label(f'Showing: {filter_names}').classes('text-sm font-medium opacity-70')
                            ui.button('Clear Filters', on_click=lambda: clear_type_filters(), icon='close').props('flat dense size=sm')

                    if not requests_to_show:
                        # Get selected types and status for styled empty card
                        selected_types = type_filter.get('selected', set())
                        selected_status = current_filter.get('value')

                        if len(selected_types) == 1:
                            # Single type selected - show styled card
                            selected_type = list(selected_types)[0]
                            if selected_type in pto_type_info:
                                info = pto_type_info[selected_type]
                                status_suffix = f' {selected_status}' if selected_status else ''
                                with ui.card().classes(f'w-full mb-3 p-4 border-l-4 {info["border"]} cursor-pointer hover:shadow-md').on(
                                    'click', lambda t=selected_type: show_pto_type_info(t)
                                ):
                                    with ui.row().classes('w-full items-center gap-3'):
                                        ui.icon(info['icon'], size='lg').style(f'color: {info["color"]};')
                                        with ui.column().classes('gap-1'):
                                            ui.label(info['name']).classes('font-semibold').style(f'color: {info["color"]};')
                                            ui.label(f'You have no{status_suffix} {info["name"].lower()} requests for {year_filter["value"]}.').classes('text-sm opacity-70')
                                            ui.label('Click for more information about this leave type').classes('text-xs opacity-50')

                        elif len(selected_types) > 1:
                            # Multiple types selected but no results
                            with ui.card().classes('w-full p-8 text-center'):
                                ui.icon('event_available', size='4rem').classes('opacity-30 mb-4')
                                type_names = ', '.join([pto_type_info.get(t, {}).get('name', t.title()) for t in selected_types])
                                ui.label(f'No {type_names} requests').classes('text-xl opacity-60')

                        elif selected_status and selected_status in status_info:
                            # Show styled card for selected status
                            info = status_info[selected_status]
                            with ui.card().classes(f'w-full mb-3 p-4 border-t-4 {info["border"]} cursor-pointer hover:shadow-md').on(
                                'click', lambda s=selected_status: show_status_info(s)
                            ):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon(info['icon'], size='lg').style(f'color: {info["color"]};')
                                    with ui.column().classes('gap-1'):
                                        ui.label(info['name']).classes('font-semibold').style(f'color: {info["color"]};')
                                        ui.label(f'You have no {selected_status} requests for {year_filter["value"]}.').classes('text-sm opacity-70')
                                        ui.label('Click for more information about this status').classes('text-xs opacity-50')

                        else:
                            # Generic empty state
                            with ui.card().classes('w-full p-8 text-center'):
                                ui.icon('event_available', size='4rem').classes('opacity-30 mb-4')
                                label_text = f'No {filter_name.lower()} time off' if filter_name else 'No time off submitted yet'
                                ui.label(label_text).classes('text-xl opacity-60')
                    else:
                        with ui.card().classes('w-full'):
                            for req in requests_to_show:
                                # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                                type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                                type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}
                                type_display = {'vacation': 'Vacation', 'sick': 'Sick', 'personal': 'Personal', 'work_from_home': 'WFH'}

                                pto_type_lower = req.pto_type.lower()
                                type_color = type_colors.get(pto_type_lower, 'gray')
                                border_class = f'border-l-4 border-{type_color}-500'

                                # Create click handler for this request
                                def create_row_handler(request):
                                    return lambda: show_request_detail_dialog(request, user['id'], user_role)

                                # Make entire row clickable
                                with ui.row().classes(f'w-full p-4 border-b last:border-0 justify-between items-center {border_class} cursor-pointer hover:bg-white/5').on(
                                    'click', create_row_handler(req)
                                ):
                                    with ui.row().classes('gap-4 items-center'):
                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{type_color}-500 text-2xl')

                                        with ui.column().classes('gap-1'):
                                            with ui.row().classes('gap-2 items-center'):
                                                # Check if vacation uses carryover from previous year
                                                has_carryover = hasattr(req, 'carryover_from_year') and req.carryover_from_year
                                                base_label = type_display.get(pto_type_lower, req.pto_type.title())
                                                label_text = f'{base_label} (CarryOver)' if has_carryover and pto_type_lower == 'vacation' else base_label
                                                label_color = 'text-amber-500' if has_carryover else f'text-{type_color}-500'
                                                ui.label(label_text).classes(f'font-bold text-sm {label_color}')
                                                # Show status badge for employees (they have pending/denied)
                                                if not is_manager_or_admin:
                                                    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}
                                                    ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey'))

                                            if req.start_date == req.end_date:
                                                ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm')
                                            else:
                                                ui.label(f"{req.start_date.strftime('%a, %b %d')} - {req.end_date.strftime('%a, %b %d, %Y')}").classes('text-sm')

                                            with ui.row().classes('gap-3 text-xs opacity-60'):
                                                hours = float(req.total_days) * 8
                                                duration_display, _ = format_days_hours(hours)
                                                ui.label(duration_display)
                                                ui.label(f'Submitted {req.submitted_at.strftime("%m/%d/%Y")}')

                                            # Show denial reason if denied
                                            if req.status == 'denied' and hasattr(req, 'denial_reason') and req.denial_reason:
                                                ui.label(f'Reason: {req.denial_reason}').classes('text-xs text-red-500 mt-1')

                                            if req.notes:
                                                ui.label(f'Note: {req.notes}').classes('text-xs opacity-50 mt-1')

                                            # Show cancellation requested indicator for employees
                                            if not is_manager_or_admin and req.status == 'approved' and hasattr(req, 'cancellation_requested') and req.cancellation_requested:
                                                ui.label('Cancellation Pending Manager Approval').classes('text-xs text-amber-600 mt-1 font-medium')

                                    # Chevron icon to indicate clickable
                                    ui.icon('chevron_right').classes('text-xl opacity-40')

            # Store tile border colors for dynamic styling
            tile_border_colors = {}

            def update_tile_styles():
                """Update tile card styles based on selected types - show bottom border when selected."""
                for pto_type, card in tile_cards.items():
                    if card is None:
                        continue
                    is_selected = pto_type in type_filter['selected']
                    border_color = tile_border_colors.get(pto_type, '#6b7280')
                    if is_selected:
                        # Show bottom border when selected
                        card.style(f'border-bottom: 4px solid {border_color}; transform: scale(1.02);')
                    else:
                        # Hide bottom border when not selected
                        card.style('border-bottom: 4px solid transparent; transform: scale(1);')

            def clear_type_filters():
                """Clear all type filters and show all approved requests."""
                type_filter['selected'].clear()
                if other_dropdown_ref['select']:
                    other_dropdown_ref['select'].value = None
                update_tile_styles()
                render_requests_by_type(approved_requests, None)

            def apply_type_filter(pto_type):
                """Apply type filter with multi-select toggle behavior."""
                if pto_type is None:
                    # Clear all filters
                    clear_type_filters()
                    return

                # Toggle behavior: add or remove from selected set
                if pto_type in type_filter['selected']:
                    type_filter['selected'].discard(pto_type)
                else:
                    type_filter['selected'].add(pto_type)

                # Update tile styles
                update_tile_styles()

                # Clear other dropdown if not selecting other type
                if other_dropdown_ref['select'] and pto_type not in other_types:
                    other_dropdown_ref['select'].value = None

                # Render filtered list based on selected types
                selected = type_filter['selected']
                if not selected:
                    # No filters - show all
                    render_requests_by_type(approved_requests, None)
                else:
                    # Filter by selected types
                    filtered = [r for r in approved_requests if r.pto_type.lower() in selected]
                    # Build filter name string
                    type_names = []
                    name_map = {'vacation': 'Vacation', 'sick': 'Sick', 'personal': 'Personal', 'work_from_home': 'WFH'}
                    for t in selected:
                        type_names.append(name_map.get(t, t.replace('_', ' ').title()))
                    filter_label = ' + '.join(sorted(type_names))
                    render_requests_by_type(filtered, filter_label)

            # Year selector
            def switch_year(year):
                """Switch year and refresh page."""
                year_filter['value'] = year
                app.storage.user['requests_year_filter'] = year
                ui.navigate.to('/requests')

            def on_view_change(selected_value):
                """Handle view dropdown change."""
                if selected_value == 'my':
                    # Clear storage to show own data
                    app.storage.user['requests_view_user_id'] = None
                else:
                    # Team member selected - save user ID to storage
                    app.storage.user['requests_view_user_id'] = selected_value
                ui.navigate.to('/requests')

            with ui.card().classes('w-full mb-4 p-3'):
                with ui.row().classes('w-full justify-between items-center'):
                    # Show whose requests we're viewing
                    if view_state['mode'] == 'team' and viewed_user_obj and viewed_user_obj.id != user['id']:
                        header_name = f"{viewed_user_obj.first_name} {viewed_user_obj.last_name}"
                        ui.label(f"{header_name}'s Requests - {year_filter['value']}").classes('text-lg font-semibold')
                    else:
                        ui.label(f'My Requests - {year_filter["value"]}').classes('text-lg font-semibold')

                    with ui.row().classes('items-center gap-3'):
                        # View dropdown (for managers/admins only)
                        if is_manager_or_admin and team_members:
                            # Build options: My Time + team members
                            view_options = {'my': 'My Time'}
                            for m in team_members:
                                if m['id'] != user['id']:  # Don't duplicate current user
                                    view_options[m['id']] = m['name']

                            current_view_value = 'my' if view_state['mode'] == 'my' else view_state['selected_user_id']
                            ui.select(
                                options=view_options,
                                label='View',
                                value=current_view_value,
                                on_change=lambda e: on_view_change(e.value)
                            ).props('dense outlined').classes('w-40')

                        # Year dropdown
                        years = [current_year, next_year]
                        ui.select(
                            {y: str(y) for y in years},
                            label='Year',
                            value=year_filter['value'],
                            on_change=lambda e: switch_year(e.value)
                        ).props('dense outlined').classes('w-24')

            # PTO type tiles - transparent cards with colored border accents (matching Dashboard/Reports)
            wfh_approved = [r for r in approved_requests if r.pto_type.lower() == 'work_from_home']
            chicago_leave_approved = [r for r in approved_requests if r.pto_type.lower() == 'chicago_leave']

            # Define tile data with CAPS labels and larger icons
            tile_data = [
                {'type': 'vacation', 'label': 'VACATION', 'icon': 'beach_access', 'count': len(vacation_approved),
                 'days': sum(float(r.total_days or 0) for r in vacation_approved),
                 'border': 'blue', 'text': '#3b82f6'},
                {'type': 'sick', 'label': 'SICK', 'icon': 'medical_services', 'count': len(sick_approved),
                 'days': sum(float(r.total_days or 0) for r in sick_approved),
                 'border': 'green', 'text': '#22c55e'},
                {'type': 'personal', 'label': 'PERSONAL', 'icon': 'person', 'count': len(personal_approved),
                 'days': sum(float(r.total_days or 0) for r in personal_approved),
                 'border': 'purple', 'text': '#a855f7'},
            ]

            # Add LEAVE tile for Chicago employees (between Personal and WFH)
            if show_chicago_leave:
                tile_data.append({
                    'type': 'chicago_leave', 'label': 'LEAVE', 'icon': 'spa', 'count': len(chicago_leave_approved),
                    'days': sum(float(r.total_days or 0) for r in chicago_leave_approved),
                    'border': 'amber', 'text': '#f59e0b'
                })

            # Add WFH tile last
            tile_data.append({
                'type': 'work_from_home', 'label': 'WFH', 'icon': 'home_work', 'count': len(wfh_approved),
                'days': sum(float(r.total_days or 0) for r in wfh_approved),
                'border': 'red', 'text': '#ef4444'
            })

            # Grid columns: 4 normally, 5 with Chicago leave
            grid_cols = 'grid-cols-5' if show_chicago_leave else 'grid-cols-4'

            with ui.element('div').classes(f'w-full grid {grid_cols} gap-3 mb-4'):
                for tile in tile_data:
                    def make_click_handler(t=tile['type']):
                        return lambda: apply_type_filter(t)

                    # Store the hex color for this tile type
                    tile_border_colors[tile['type']] = tile['text']

                    card = ui.card().classes(f'p-3 border-t-4 border-{tile["border"]}-500 cursor-pointer hover:opacity-80 transition-all duration-200').style(
                        'border-bottom: 4px solid transparent;'
                    ).on('click', make_click_handler())
                    tile_cards[tile['type']] = card
                    with card:
                        with ui.column().classes('items-center w-full'):
                            ui.icon(tile['icon'], size='lg').style(f"color: {tile['text']}")
                            ui.label(tile['label']).classes('font-bold text-center text-sm').style(f"color: {tile['text']}")
                            ui.label(f'{tile["count"]} request{"s" if tile["count"] != 1 else ""}').classes('text-xs opacity-60 text-center')
                            ui.label(fmt_days(tile["days"])).classes('text-sm font-bold text-center')

            # Other types dropdown (if any exist)
            if other_approved:
                with ui.row().classes('w-full mb-4'):
                    other_options = {
                        'bereavement': 'Bereavement',
                        'fmla': 'FMLA',
                        'jury_duty': 'Jury Duty',
                        'voting': 'Voting',
                        'military': 'Military'
                    }
                    # Only show types that have approved requests
                    available_other = {k: v for k, v in other_options.items()
                                       if any(r.pto_type.lower() == k for r in other_approved)}

                    def on_other_change(e):
                        if e.value:
                            apply_type_filter(e.value)

                    other_select = ui.select(
                        options=available_other,
                        label=f'Other Types ({len(other_approved)})',
                        on_change=on_other_change
                    ).props('dense outlined').classes('min-w-[150px]')
                    other_dropdown_ref['select'] = other_select

            # For employees: show approved/pending/denied status cards
            if not is_manager_or_admin:
                with ui.element('div').classes('w-full grid grid-cols-3 gap-3 mb-4'):
                    # Approved
                    with ui.card().classes('p-3 border-t-4 border-green-500 cursor-pointer hover:opacity-80').on(
                        'click', lambda: set_filter('approved')
                    ):
                        ui.label('Approved').classes('text-xs opacity-60 uppercase')
                        ui.label(str(len(approved_requests))).classes('text-lg font-bold').style('color: #22c55e')
                        ui.label(fmt_days(sum(float(r.total_days or 0) for r in approved_requests))).classes('text-xs opacity-50')
                    filter_buttons['approved'] = None

                    # Pending
                    with ui.card().classes('p-3 border-t-4 border-amber-500 cursor-pointer hover:opacity-80').on(
                        'click', lambda: set_filter('pending')
                    ):
                        ui.label('Pending').classes('text-xs opacity-60 uppercase')
                        ui.label(str(len(pending_requests))).classes('text-lg font-bold').style('color: #f59e0b')
                        ui.label(fmt_days(sum(float(r.total_days or 0) for r in pending_requests))).classes('text-xs opacity-50')
                    filter_buttons['pending'] = None

                    # Denied
                    with ui.card().classes('p-3 border-t-4 border-red-500 cursor-pointer hover:opacity-80').on(
                        'click', lambda: set_filter('denied')
                    ):
                        ui.label('Denied').classes('text-xs opacity-60 uppercase')
                        ui.label(str(len(denied_requests))).classes('text-lg font-bold').style('color: #ef4444')
                        ui.label(fmt_days(sum(float(r.total_days or 0) for r in denied_requests))).classes('text-xs opacity-50')
                    filter_buttons['denied'] = None

            # Container for the results list
            results_container = ui.column().classes('w-full')

            # Default: show all approved requests
            render_requests_by_type(approved_requests, None)

            # ============ REAL-TIME UPDATES ============
            # Set up automatic refresh when PTO request statuses change (30 second interval)
            setup_dashboard_updates(db, user['id'], user_role, interval=30.0)

        finally:
            db.close()
