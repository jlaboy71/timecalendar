"""User's PTO request history page with filtering and cancel functionality."""
from datetime import date, datetime
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService


def cancel_user_request(request_id: int, pto_type: str, total_days: float, year: int):
    """Cancel a user's pending PTO request (for employees)."""
    db = None
    try:
        db = next(get_db())
        from src.models.pto_request import PTORequest

        # Get the request
        request = db.query(PTORequest).filter(PTORequest.id == request_id).first()

        if not request:
            show_error_dialog('Not Found', 'The request was not found.')
            return

        if request.status != 'pending':
            show_warning_dialog('Cannot Cancel', 'Only pending requests can be cancelled.')
            return

        # Update the request status
        request.status = 'cancelled'

        # If it was vacation, return the pending hours
        if pto_type.lower() == 'vacation':
            balance_service = BalanceService(db)
            balance = balance_service.get_or_create_balance(request.user_id, year)
            balance_service.adjust_vacation_used(balance.id, -total_days, is_pending=True)

        db.commit()
        ui.notify('Request cancelled successfully', type='positive')
        ui.navigate.to('/requests')

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

        # Update the request status
        request.status = 'cancelled'

        # Return the USED hours (not pending) back to the balance
        pto_type_lower = pto_type.lower()
        if pto_type_lower in ['vacation', 'sick', 'personal']:
            balance_service = BalanceService(db)
            balance = balance_service.get_or_create_balance(request.user_id, year)

            if pto_type_lower == 'vacation':
                # Reduce vacation_used by total_days (in hours = days * 8)
                current_used = float(balance.vacation_used or 0)
                balance.vacation_used = max(0, current_used - (total_days * 8))
            elif pto_type_lower == 'sick':
                current_used = float(balance.sick_used or 0)
                balance.sick_used = max(0, current_used - (total_days * 8))
            elif pto_type_lower == 'personal':
                current_used = float(balance.personal_used or 0)
                balance.personal_used = max(0, current_used - (total_days * 8))

        db.commit()
        ui.notify('Request cancelled and balance restored', type='positive')
        ui.navigate.to('/requests')

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

        # Mark cancellation as requested
        request.cancellation_requested = True
        request.cancellation_reason = reason.strip() if reason else None
        request.cancellation_requested_at = datetime.now()

        db.commit()
        ui.notify('Cancellation request submitted to your manager', type='positive')
        ui.navigate.to('/requests')

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

    with ui.dialog() as detail_dialog, ui.card().classes('w-full max-w-md p-0'):
        # Header with colored background
        with ui.row().classes(f'w-full justify-between items-center p-4 bg-{header_color}-500 text-white'):
            with ui.row().classes('gap-2 items-center'):
                ui.icon(type_icons.get(pto_type_lower, 'event')).classes('text-2xl')
                ui.label(f'{request.pto_type.title()} Time Off').classes('text-lg font-bold')
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
                days = float(request.total_days)
                if days == int(days):
                    day_str = f'{int(days)} day{"s" if days != 1 else ""}'
                else:
                    day_str = f'{days:.1f} days'
                ui.label(f'{day_str} ({int(days * 8)} hours)').classes('font-medium')

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

        request.status = 'cancelled'

        # Restore balance based on PTO type and previous status
        pto_type_lower = pto_type.lower()
        if pto_type_lower in ['vacation', 'sick', 'personal']:
            balance_service = BalanceService(db)
            balance = balance_service.get_or_create_balance(user_id, year)
            hours_to_restore = total_days * 8

            if status == 'pending':
                if pto_type_lower == 'vacation':
                    balance.vacation_pending = max(0, float(balance.vacation_pending or 0) - hours_to_restore)
            else:  # approved
                if pto_type_lower == 'vacation':
                    balance.vacation_used = max(0, float(balance.vacation_used or 0) - hours_to_restore)
                elif pto_type_lower == 'sick':
                    balance.sick_used = max(0, float(balance.sick_used or 0) - hours_to_restore)
                elif pto_type_lower == 'personal':
                    balance.personal_used = max(0, float(balance.personal_used or 0) - hours_to_restore)

        db.commit()
        ui.notify('Request deleted and balance restored', type='positive')
        ui.navigate.to('/requests')

    except Exception as e:
        show_error_dialog('Error', f'Error deleting request: {str(e)}')
    finally:
        if db:
            db.close()


def requests_page():
    """User's PTO request history page content."""
    apply_dark_mode()

    user = app.storage.general.get('user')
    user_role = user.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # Current filter state - managers default to 'approved' since their requests auto-approve
    current_filter = {'value': 'approved' if is_manager_or_admin else 'pending'}

    # Year filter state - default to current year, use storage to persist selection
    current_year = date.today().year
    next_year = current_year + 1
    stored_year = app.storage.general.get('requests_year_filter', current_year)
    year_filter = {'value': stored_year if stored_year in [current_year, next_year] else current_year}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Different title for managers vs employees
        page_title = 'MY TIME OFF' if is_manager_or_admin else 'REQUEST HISTORY'
        page_header(title=page_title, show_back=False)

        db = next(get_db())
        try:
            all_user_requests = PTOService.get_user_requests(db, user['id'])

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
                """Set the filter and re-render the list (for employees approved/pending/denied)."""
                current_filter['value'] = filter_type
                # Update button styles
                update_button_styles()
                # Clear type filter buttons
                for btn in type_filter_buttons.values():
                    btn.props('flat')
                # Filter and render
                if filter_type == 'approved':
                    render_requests_by_type(approved_requests, 'Approved')
                elif filter_type == 'pending':
                    render_requests_by_type(pending_requests, 'Pending')
                elif filter_type == 'denied':
                    render_requests_by_type(denied_requests, 'Denied')

            # Store button references for style updates
            filter_buttons = {}

            def update_button_styles():
                """Update button styles based on current filter."""
                for btn_name, btn in filter_buttons.items():
                    if current_filter['value'] and btn_name == current_filter['value']:
                        btn.props('color=primary', remove='flat')
                    else:
                        btn.props('flat', remove='color')

            # Calculate totals by type (for approved requests)
            vacation_approved = [r for r in approved_requests if r.pto_type.lower() == 'vacation']
            sick_approved = [r for r in approved_requests if r.pto_type.lower() == 'sick']
            personal_approved = [r for r in approved_requests if r.pto_type.lower() == 'personal']
            # Other types
            other_types = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military']
            other_approved = [r for r in approved_requests if r.pto_type.lower() in other_types]

            # Type filter state for the list
            type_filter = {'value': None}
            type_filter_buttons = {}
            other_dropdown_ref = {'select': None}

            def render_requests_by_type(requests_to_show, filter_name=None):
                """Render requests, optionally filtered by type."""
                results_container.clear()
                with results_container:
                    # Show filter indicator if filtering
                    if filter_name:
                        with ui.row().classes('w-full items-center gap-2 mb-2'):
                            ui.label(f'Showing: {filter_name.title()}').classes('text-sm font-medium opacity-70')
                            ui.button('Show All', on_click=lambda: apply_type_filter(None), icon='close').props('flat dense size=sm')

                    if not requests_to_show:
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

                                with ui.row().classes(f'w-full p-4 border-b last:border-0 justify-between items-center {border_class}'):
                                    with ui.row().classes('gap-4 items-center'):
                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{type_color}-500 text-2xl')

                                        with ui.column().classes('gap-1'):
                                            with ui.row().classes('gap-2 items-center'):
                                                with ui.element('div').classes(f'bg-{type_color}-100 text-{type_color}-700 px-2 py-0.5 rounded'):
                                                    ui.label(type_display.get(pto_type_lower, req.pto_type.title())).classes('font-semibold text-sm')
                                                # Show status badge for employees (they have pending/denied)
                                                if not is_manager_or_admin:
                                                    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}
                                                    ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey'))

                                            if req.start_date == req.end_date:
                                                ui.label(req.start_date.strftime('%A, %B %d, %Y')).classes('text-sm')
                                            else:
                                                ui.label(f"{req.start_date.strftime('%a, %b %d')} - {req.end_date.strftime('%a, %b %d, %Y')}").classes('text-sm')

                                            with ui.row().classes('gap-3 text-xs opacity-60'):
                                                days = round(float(req.total_days), 1)
                                                if days == int(days):
                                                    ui.label(f'{int(days)} day{"s" if days != 1 else ""}')
                                                else:
                                                    ui.label(f'{days} days')
                                                ui.label(f'Submitted {req.submitted_at.strftime("%m/%d/%Y")}')

                                            # Show denial reason if denied
                                            if req.status == 'denied' and hasattr(req, 'denial_reason') and req.denial_reason:
                                                ui.label(f'Reason: {req.denial_reason}').classes('text-xs text-red-500 mt-1')

                                            if req.notes:
                                                ui.label(f'Note: {req.notes}').classes('text-xs opacity-50 mt-1')

                                            # Show cancellation requested indicator for employees
                                            if not is_manager_or_admin and req.status == 'approved' and hasattr(req, 'cancellation_requested') and req.cancellation_requested:
                                                ui.label('Cancellation Pending Manager Approval').classes('text-xs text-amber-600 mt-1 font-medium')

                                    # Action buttons container
                                    with ui.row().classes('gap-1 items-center'):
                                        # Details button for all users
                                        def create_detail_handler(request):
                                            def show_detail():
                                                show_request_detail_dialog(request, user['id'], user_role)
                                            return show_detail
                                        ui.button('Details', icon='info', on_click=create_detail_handler(req)).props('flat size=sm')

            def apply_type_filter(pto_type):
                """Apply type filter and render filtered list."""
                type_filter['value'] = pto_type
                # Clear other dropdown if not selecting other
                if other_dropdown_ref['select'] and pto_type not in other_types:
                    other_dropdown_ref['select'].value = None
                # Render filtered list
                if pto_type == 'vacation':
                    render_requests_by_type(vacation_approved, 'Vacation')
                elif pto_type == 'sick':
                    render_requests_by_type(sick_approved, 'Sick')
                elif pto_type == 'personal':
                    render_requests_by_type(personal_approved, 'Personal')
                elif pto_type == 'work_from_home':
                    wfh_filtered = [r for r in approved_requests if r.pto_type.lower() == 'work_from_home']
                    render_requests_by_type(wfh_filtered, 'WFH')
                elif pto_type in other_types:
                    filtered = [r for r in approved_requests if r.pto_type.lower() == pto_type]
                    render_requests_by_type(filtered, pto_type.replace('_', ' ').title())
                else:
                    render_requests_by_type(approved_requests, None)

            # Year toggle card
            with ui.card().classes('w-full mb-4 p-3'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label(f'Viewing: {year_filter["value"]}').classes('text-sm font-medium opacity-70')

                    # Year toggle buttons
                    with ui.button_group().props('outline rounded'):
                        year_btn_current = ui.button(str(current_year), on_click=lambda: switch_year(current_year))
                        year_btn_next = ui.button(str(next_year), on_click=lambda: switch_year(next_year))

                    # Set initial button states
                    if year_filter['value'] == current_year:
                        year_btn_current.props('color=primary')
                        year_btn_next.props('color=grey')
                    else:
                        year_btn_current.props('color=grey')
                        year_btn_next.props('color=primary')

            def switch_year(year):
                """Switch year and refresh page."""
                year_filter['value'] = year
                app.storage.general['requests_year_filter'] = year
                # Refresh by navigating to same page
                ui.navigate.to('/requests')

            # Summary header with total
            total_days = sum(float(r.total_days or 0) for r in approved_requests)
            with ui.element('div').classes('w-full mb-4 p-4 rounded-lg').style('background-color: #1f2937; border-left: 4px solid #22c55e'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('check_circle', size='lg').style('color: #22c55e')
                        with ui.column().classes('gap-0'):
                            ui.label(f'{len(approved_requests)} Total Approved').classes('text-2xl font-bold').style('color: #22c55e')
                            ui.label(f'{year_filter["value"]}').classes('text-sm opacity-70')
                    with ui.column().classes('items-end gap-0'):
                        ui.label(f'{total_days:.1f}').classes('text-2xl font-bold').style('color: #86efac')
                        ui.label('days taken').classes('text-xs opacity-60')

            # PTO type tiles - 4 separate colored cards
            wfh_approved = [r for r in approved_requests if r.pto_type.lower() == 'work_from_home']

            # Define tile data with colors matching the rest of the app
            # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
            tile_data = [
                {'type': 'vacation', 'label': 'Vacation', 'icon': 'beach_access', 'count': len(vacation_approved),
                 'days': sum(float(r.total_days or 0) for r in vacation_approved),
                 'bg': '#1e3a5f', 'border': '#3b82f6', 'text': '#3b82f6'},
                {'type': 'sick', 'label': 'Sick', 'icon': 'medical_services', 'count': len(sick_approved),
                 'days': sum(float(r.total_days or 0) for r in sick_approved),
                 'bg': '#14532d', 'border': '#22c55e', 'text': '#22c55e'},
                {'type': 'personal', 'label': 'Personal', 'icon': 'person', 'count': len(personal_approved),
                 'days': sum(float(r.total_days or 0) for r in personal_approved),
                 'bg': '#581c87', 'border': '#a855f7', 'text': '#a855f7'},
                {'type': 'work_from_home', 'label': 'WFH', 'icon': 'home_work', 'count': len(wfh_approved),
                 'days': sum(float(r.total_days or 0) for r in wfh_approved),
                 'bg': '#7f1d1d', 'border': '#ef4444', 'text': '#ef4444'},
            ]

            with ui.row().classes('w-full gap-4 mb-4'):
                for tile in tile_data:
                    def make_click_handler(t=tile['type']):
                        return lambda: apply_type_filter(t)

                    with ui.element('div').classes('flex-1 p-4 rounded-lg cursor-pointer').style(
                        f"background-color: {tile['bg']}; border-top: 4px solid {tile['border']};"
                    ).on('click', make_click_handler()):
                        with ui.row().classes('items-center gap-2 mb-2'):
                            ui.icon(tile['icon']).style(f"color: {tile['text']}")
                            ui.label(tile['label']).classes('font-semibold').style(f"color: {tile['text']}")
                        ui.label(f'{tile["count"]} request{"s" if tile["count"] != 1 else ""}').classes('text-sm opacity-70')
                        ui.label(f'{tile["days"]:.1f} days').classes('text-xl font-bold')

                    # Store reference for button styling (for highlighting selected)
                    type_filter_buttons[tile['type']] = None  # Tiles don't need style updates

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
                with ui.row().classes('w-full gap-4 mb-4 items-stretch'):
                    # Approved
                    with ui.card().classes('flex-1 p-3 text-center border-l-4 border-green-500 flex flex-col'):
                        ui.label(str(len(approved_requests))).classes('text-2xl font-bold text-green-500')
                        ui.label('Approved').classes('text-xs opacity-60 mb-2')
                        ui.element('div').classes('flex-grow')
                        btn_approved = ui.button('Show Approved', on_click=lambda: set_filter('approved')).props('dense size=sm flat').classes('w-full')
                        filter_buttons['approved'] = btn_approved

                    # Pending
                    with ui.card().classes('flex-1 p-3 text-center border-l-4 border-amber-500 flex flex-col'):
                        ui.label(str(len(pending_requests))).classes('text-2xl font-bold text-amber-500')
                        ui.label('Pending').classes('text-xs opacity-60 mb-2')
                        ui.element('div').classes('flex-grow')
                        btn_pending = ui.button('Show Pending', on_click=lambda: set_filter('pending')).props('dense size=sm flat').classes('w-full')
                        filter_buttons['pending'] = btn_pending

                    # Denied
                    with ui.card().classes('flex-1 p-3 text-center border-l-4 border-red-500 flex flex-col'):
                        ui.label(str(len(denied_requests))).classes('text-2xl font-bold text-red-500')
                        ui.label('Denied').classes('text-xs opacity-60 mb-2')
                        ui.element('div').classes('flex-grow')
                        btn_denied = ui.button('Show Denied', on_click=lambda: set_filter('denied')).props('dense size=sm flat').classes('w-full')
                        filter_buttons['denied'] = btn_denied

            # Container for the results list
            results_container = ui.column().classes('w-full')

            # Default: show all approved requests
            render_requests_by_type(approved_requests, None)

            # Return to Dashboard button
            ui.button('Return to Dashboard', icon='home', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')

        finally:
            db.close()
