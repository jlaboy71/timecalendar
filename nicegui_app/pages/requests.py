"""User's PTO request history page with filtering and cancel functionality."""
from datetime import date
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService


def cancel_user_request(request_id: int, pto_type: str, total_days: float, year: int):
    """Cancel a user's pending PTO request."""
    db = None
    try:
        db = next(get_db())
        from src.models.pto_request import PTORequest

        # Get the request
        request = db.query(PTORequest).filter(PTORequest.id == request_id).first()

        if not request:
            ui.notify('Request not found', type='negative')
            return

        if request.status != 'pending':
            ui.notify('Only pending requests can be cancelled', type='warning')
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
        ui.notify(f'Error cancelling request: {str(e)}', type='negative')
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
                        btn.props('color=primary')
                    else:
                        btn.props('flat')

            # Calculate totals by type (for approved requests)
            vacation_approved = [r for r in approved_requests if r.pto_type.lower() == 'vacation']
            sick_approved = [r for r in approved_requests if r.pto_type.lower() == 'sick']
            personal_approved = [r for r in approved_requests if r.pto_type.lower() == 'personal']

            # Type filter state for the list
            type_filter = {'value': None}
            type_filter_buttons = {}

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
                                type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
                                type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}

                                pto_type_lower = req.pto_type.lower()
                                type_color = type_colors.get(pto_type_lower, 'gray')
                                border_class = f'border-l-4 border-{type_color}-500'

                                with ui.row().classes(f'w-full p-4 border-b last:border-0 justify-between items-center {border_class}'):
                                    with ui.row().classes('gap-4 items-center'):
                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{type_color}-500 text-2xl')

                                        with ui.column().classes('gap-1'):
                                            with ui.row().classes('gap-2 items-center'):
                                                with ui.element('div').classes(f'bg-{type_color}-100 text-{type_color}-700 px-2 py-0.5 rounded'):
                                                    ui.label(req.pto_type.title()).classes('font-semibold text-sm')
                                                # Show status badge for employees (they have pending/denied)
                                                if not is_manager_or_admin:
                                                    status_colors = {'pending': 'amber', 'approved': 'green', 'denied': 'red', 'cancelled': 'grey'}
                                                    ui.badge(req.status.title(), color=status_colors.get(req.status, 'grey'))

                                            if req.start_date == req.end_date:
                                                ui.label(req.start_date.strftime('%B %d, %Y')).classes('text-sm')
                                            else:
                                                ui.label(f"{req.start_date.strftime('%b %d')} - {req.end_date.strftime('%b %d, %Y')}").classes('text-sm')

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

                                    # Cancel button for pending requests (employees only)
                                    if not is_manager_or_admin and req.status == 'pending':
                                        def create_cancel_handler(request_id, pto_type, total_days, start_year):
                                            def show_cancel_dialog():
                                                with ui.dialog() as cancel_dialog, ui.card().classes('p-4'):
                                                    ui.label('Cancel PTO Request?').classes('text-lg font-semibold mb-2')
                                                    ui.label('This will cancel your pending request and restore your balance.').classes('text-sm opacity-70 mb-4')
                                                    with ui.row().classes('w-full justify-end gap-2'):
                                                        ui.button('Keep Request', on_click=cancel_dialog.close).props('flat')
                                                        def confirm_cancel():
                                                            cancel_dialog.close()
                                                            cancel_user_request(request_id, pto_type, total_days, start_year)
                                                        ui.button('Cancel Request', on_click=confirm_cancel).props('color=red')
                                                cancel_dialog.open()
                                            return show_cancel_dialog
                                        ui.button('Cancel', icon='close', on_click=create_cancel_handler(req.id, req.pto_type, float(req.total_days), req.start_date.year)).props('flat color=red size=sm')

            def apply_type_filter(pto_type):
                """Apply type filter and update button styles."""
                type_filter['value'] = pto_type
                # Update button styles
                for btn_type, btn in type_filter_buttons.items():
                    if pto_type and btn_type == pto_type:
                        btn.props('color=primary')
                    else:
                        btn.props('flat')
                # Render filtered list
                if pto_type == 'vacation':
                    render_requests_by_type(vacation_approved, 'Vacation')
                elif pto_type == 'sick':
                    render_requests_by_type(sick_approved, 'Sick')
                elif pto_type == 'personal':
                    render_requests_by_type(personal_approved, 'Personal')
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

            # Summary card with total and type breakdown
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('event_available', color='green').classes('text-xl')
                        ui.label(f'{len(approved_requests)} Total Approved ({year_filter["value"]})').classes('text-lg font-semibold text-green-600')

                # Type breakdown with filter buttons
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    # Vacation
                    btn_vacation = ui.button(
                        f'Vacation ({len(vacation_approved)})',
                        icon='beach_access',
                        on_click=lambda: apply_type_filter('vacation')
                    ).props('flat dense').classes('text-blue-600')
                    type_filter_buttons['vacation'] = btn_vacation

                    # Sick
                    btn_sick = ui.button(
                        f'Sick ({len(sick_approved)})',
                        icon='medical_services',
                        on_click=lambda: apply_type_filter('sick')
                    ).props('flat dense').classes('text-green-600')
                    type_filter_buttons['sick'] = btn_sick

                    # Personal
                    btn_personal = ui.button(
                        f'Personal ({len(personal_approved)})',
                        icon='person',
                        on_click=lambda: apply_type_filter('personal')
                    ).props('flat dense').classes('text-purple-600')
                    type_filter_buttons['personal'] = btn_personal

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
