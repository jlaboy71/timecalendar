from nicegui import ui, app
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import get_db
from nicegui_app.pages.login import login_page
from nicegui_app.pages.dashboard import dashboard_page
from nicegui_app.pages.request_form import request_form_page
from nicegui_app.pages.carryover import carryover_page
from nicegui_app.pages.manager_carryover import manager_carryover_page
from nicegui_app.pages.calendar import calendar_page
from nicegui_app.pages.handbook import handbook_page
from nicegui_app.logo import LOGO_DATA_URL

# Set up basic app configuration
app.title = "TJM Time Calendar"

# Add static file serving for logo
STATIC_DIR = Path(__file__).parent / 'static'
app.add_static_files('/static', STATIC_DIR)

@ui.page('/')
def home():
    """Home page with login interface."""
    login_page()

@ui.page('/dashboard')
def dashboard():
    """Dashboard page for logged-in users."""
    dashboard_page()

@ui.page('/submit-request')
def submit_request():
    """PTO Request submission page."""
    request_form_page()

@ui.page('/calendar')
def calendar():
    """Calendar view page."""
    calendar_page()

@ui.page('/carryover')
def carryover():
    """Carryover request page."""
    carryover_page()

@ui.page('/manager/carryover')
def manager_carryover():
    """Manager carryover approval page."""
    manager_carryover_page()

@ui.page('/handbook')
def handbook():
    """Employee handbook page."""
    handbook_page()

@ui.page('/requests')
def requests():
    """User's PTO request history page with filtering and cancel functionality."""
    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return

    user = app.storage.general.get('user')
    user_role = user.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # Current filter state - managers default to 'approved' since their requests auto-approve
    current_filter = {'value': 'approved' if is_manager_or_admin else 'pending'}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header with logo above title
        with ui.column().classes('gap-2 mb-4'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat round')
                # Different title for managers vs employees
                page_title = 'MY TIME OFF' if is_manager_or_admin else 'REQUEST HISTORY'
                ui.label(page_title).classes('text-xl font-bold ml-2').style('color: #5a6a72;')

        db = next(get_db())
        try:
            from src.services.pto_service import PTOService
            from src.services.balance_service import BalanceService
            user_requests = PTOService.get_user_requests(db, user['id'])

            # Sort by submitted_at descending (newest first)
            user_requests_sorted = sorted(user_requests, key=lambda r: r.submitted_at, reverse=True)

            # Summary stats
            pending_requests = [r for r in user_requests_sorted if r.status == 'pending']
            approved_requests = [r for r in user_requests_sorted if r.status == 'approved']
            denied_requests = [r for r in user_requests_sorted if r.status == 'denied']

            # results_container will be created after stat cards (see below)
            results_container = None

            def set_filter(filter_type):
                """Set the filter and re-render the list (for employees pending/denied)."""
                current_filter['value'] = filter_type
                # Update button styles
                update_button_styles()
                # Clear type filter buttons
                for btn in type_filter_buttons.values():
                    btn.props('flat')
                # Filter and render
                if filter_type == 'pending':
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
                                            def cancel():
                                                cancel_user_request(request_id, pto_type, total_days, start_year)
                                            return cancel
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

            # Summary card with total and type breakdown
            with ui.card().classes('w-full mb-4 p-4'):
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('event_available', color='green').classes('text-xl')
                        ui.label(f'{len(approved_requests)} Total Approved').classes('text-lg font-semibold text-green-600')

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

            # For employees: also show pending/denied stats
            if not is_manager_or_admin:
                with ui.row().classes('w-full gap-4 mb-4 items-stretch'):
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


def cancel_user_request(request_id: int, pto_type: str, total_days: float, year: int):
    """Cancel a user's pending PTO request."""
    db = None
    try:
        db = next(get_db())
        from src.services.pto_service import PTOService
        from src.services.balance_service import BalanceService
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

@ui.page('/manager/request/{request_id}')
def manager_request_detail(request_id: int):
    """Request detail page for approval/denial"""
    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['manager', 'admin', 'superadmin']:
        ui.label('Access denied').classes('text-red-500')
        return

    db = next(get_db())
    try:
        from src.services.pto_service import PTOService
        detail = PTOService.get_request_detail(db, request_id)
        
        if not detail:
            ui.label('Request not found').classes('text-red-500')
            return
        
        request = detail['request']
        balance = detail['balance']
        
        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            with ui.column().classes('gap-2 mb-6'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                with ui.row().classes('items-center'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat round')
                    ui.label('PTO REQUEST REVIEW').classes('text-xl font-bold ml-2').style('color: #5a6a72;')
            
            # Employee Info Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Employee Information').classes('text-xl font-bold mb-2')
                ui.label(f"Name: {detail['employee_name']}")
                ui.label(f"Email: {detail['employee_email']}")
            
            # Request Details Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Request Details').classes('text-xl font-bold mb-2')
                ui.label(f"Type: {request.pto_type.title()}")
                ui.label(f"Start Date: {request.start_date.strftime('%Y-%m-%d')}")
                ui.label(f"End Date: {request.end_date.strftime('%Y-%m-%d')}")
                ui.label(f"Total Days: {request.total_days}")
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

            # Current Balance Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Current PTO Balance').classes('text-xl font-bold mb-2')
                ui.label(f"Vacation: {balance.vacation_total - balance.vacation_used:.1f} available")
                ui.label(f"Sick: {balance.sick_total - balance.sick_used:.1f} available")
                ui.label(f"Personal: {balance.personal_total - balance.personal_used:.1f} available")
            
            # Approval Actions
            if request.status == 'pending':
                def approve():
                    db = next(get_db())
                    try:
                        user_id = app.storage.general.get('user').get('id')
                        if PTOService.approve_request(db, request_id, user_id):
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
                        user_id = app.storage.general.get('user').get('id')
                        if PTOService.deny_request(db, request_id, user_id, reason):
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
    
    finally:
        db.close()

@ui.page('/admin')
def admin_panel():
    """Admin panel landing page with navigation to admin functions."""
    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
        with ui.column().classes('gap-2 mb-6'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            ui.label('ADMIN PANEL').classes('text-xl font-bold').style('color: #5a6a72;')

        # Navigation cards
        with ui.row().classes('w-full gap-6 justify-center'):
            # Manage Departments card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('business', size='3rem').classes('text-primary')
                    ui.label('Manage Departments').classes('text-xl font-semibold')
                    ui.label('Create and manage organizational departments').classes('text-gray-600 text-center')
                    ui.button('Go to Departments', on_click=lambda: ui.navigate.to('/admin/departments'), color='primary')
            
            # Manage Employees card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('people', size='3rem').classes('text-primary')
                    ui.label('Manage Employees').classes('text-xl font-semibold')
                    ui.label('Add, edit, and manage employee accounts').classes('text-gray-600 text-center')
                    ui.button('Go to Employees', on_click=lambda: ui.navigate.to('/admin/employees'), color='primary')
            
            # Carryover Approvals card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('approval', size='3rem').classes('text-primary')
                    ui.label('Carryover Approvals').classes('text-xl font-semibold')
                    ui.label('Review and approve employee carryover requests').classes('text-gray-600 text-center')
                    ui.button('Go to Approvals', on_click=lambda: ui.navigate.to('/manager/carryover'), color='primary')

            # Reports card (disabled)
            with ui.card().classes('p-6 opacity-50'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('assessment', size='3rem').classes('text-gray-400')
                    ui.label('Reports').classes('text-xl font-semibold text-gray-400')
                    ui.label('View PTO usage and analytics').classes('text-gray-400 text-center')
                    ui.label('Coming Soon').classes('text-gray-400 font-semibold')
        
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-8')

@ui.page('/admin/departments')
def admin_departments():
    """Admin page for managing departments."""
    from src.services.department_service import DepartmentService
    from src.services.user_service import UserService
    from src.models.user import User

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # Get managers for dropdowns
    db = next(get_db())
    try:
        managers = UserService.get_users_by_role(db, 'manager')
        manager_options = {0: 'No Manager'}
        manager_options.update({m.id: f'{m.first_name} {m.last_name}' for m in managers})
        departments = DepartmentService.get_all_departments(db)

        # Build department data with manager info
        dept_data = []
        for dept in departments:
            manager_name = 'No Manager'
            if dept.manager_id:
                manager = UserService(db).get_user_by_id(dept.manager_id)
                if manager:
                    manager_name = f'{manager.first_name} {manager.last_name}'

            # Get employee count
            employee_count = db.query(User).filter(User.department_id == dept.id).count()

            dept_data.append({
                'id': dept.id,
                'name': dept.name,
                'code': dept.code,
                'manager_id': dept.manager_id or 0,
                'manager_name': manager_name,
                'is_active': dept.is_active,
                'employee_count': employee_count
            })
    finally:
        db.close()

    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        with ui.row().classes('w-full justify-between items-start mb-6'):
            with ui.column().classes('gap-2'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                with ui.row().classes('items-center gap-2'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat round')
                    ui.label('DEPARTMENT MANAGEMENT').classes('text-xl font-bold').style('color: #5a6a72;')

        # Create New Department Card
        with ui.card().classes('w-full mb-6 p-4'):
            with ui.row().classes('items-center gap-2 mb-4'):
                ui.icon('add_business', color='primary').classes('text-xl')
                ui.label('Create New Department').classes('text-lg font-semibold')

            with ui.row().classes('w-full gap-4 items-end'):
                name_input = ui.input('Department Name').props('outlined dense').classes('flex-1')
                code_input = ui.input('Department Code').props('outlined dense').classes('flex-1')
                manager_select = ui.select(manager_options, label='Manager', value=0).props('outlined dense').classes('flex-1')

                def create_dept():
                    if not name_input.value or not code_input.value:
                        ui.notify('Name and code are required', type='negative')
                        return

                    db = next(get_db())
                    try:
                        mgr_id = None if manager_select.value == 0 else manager_select.value
                        DepartmentService.create_department(db, name_input.value, code_input.value, mgr_id)
                        ui.notify(f'Department "{name_input.value}" created successfully', type='positive')
                        ui.navigate.to('/admin/departments')
                    except ValueError as e:
                        ui.notify(str(e), type='negative')
                    finally:
                        db.close()

                ui.button('Create', icon='add', on_click=create_dept).props('color=primary')

        # Existing Departments Card
        with ui.card().classes('w-full'):
            with ui.row().classes('items-center gap-2 mb-4 p-4 pb-0'):
                ui.icon('business', color='indigo').classes('text-xl')
                ui.label('Existing Departments').classes('text-lg font-semibold')
                ui.badge(f'{len(dept_data)} total', color='indigo').props('outline')

            if not dept_data:
                with ui.row().classes('w-full justify-center py-8'):
                    ui.label('No departments created yet').classes('text-xl opacity-60')
            else:
                with ui.column().classes('w-full px-4 pb-4'):
                    for dept in dept_data:
                        with ui.card().classes('w-full p-4 mb-3 border-l-4 border-indigo-500'):
                            with ui.row().classes('w-full justify-between items-start'):
                                # Department info
                                with ui.column().classes('gap-1 flex-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(dept['name']).classes('text-lg font-semibold')
                                        if dept['is_active']:
                                            ui.badge('Active', color='green').props('outline')
                                        else:
                                            ui.badge('Inactive', color='grey').props('outline')

                                    with ui.row().classes('gap-4 text-sm opacity-70'):
                                        ui.label(f"Code: {dept['code']}")
                                        ui.label(f"Manager: {dept['manager_name']}")
                                        ui.label(f"Employees: {dept['employee_count']}")

                                # Action buttons
                                with ui.row().classes('gap-2'):
                                    def create_edit_handler(d, mgr_opts):
                                        def open_edit():
                                            # Edit dialog
                                            with ui.dialog() as edit_dialog, ui.card().classes('p-6 min-w-96'):
                                                ui.label(f"Edit Department: {d['name']}").classes('text-lg font-semibold mb-4')

                                                edit_name = ui.input('Department Name', value=d['name']).props('outlined').classes('w-full mb-2')
                                                edit_code = ui.input('Department Code', value=d['code']).props('outlined').classes('w-full mb-2')
                                                edit_manager = ui.select(mgr_opts, label='Manager', value=d['manager_id']).props('outlined').classes('w-full mb-4')

                                                def save_changes():
                                                    if not edit_name.value or not edit_code.value:
                                                        ui.notify('Name and code are required', type='negative')
                                                        return

                                                    db = next(get_db())
                                                    try:
                                                        mgr_id = None if edit_manager.value == 0 else edit_manager.value
                                                        DepartmentService.update_department(
                                                            db, d['id'],
                                                            name=edit_name.value,
                                                            code=edit_code.value,
                                                            manager_id=mgr_id
                                                        )
                                                        ui.notify('Department updated successfully', type='positive')
                                                        edit_dialog.close()
                                                        ui.navigate.to('/admin/departments')
                                                    except ValueError as e:
                                                        ui.notify(str(e), type='negative')
                                                    finally:
                                                        db.close()

                                                with ui.row().classes('w-full justify-end gap-2'):
                                                    ui.button('Cancel', on_click=edit_dialog.close).props('flat')
                                                    ui.button('Save Changes', on_click=save_changes).props('color=primary')

                                            edit_dialog.open()
                                        return open_edit

                                    ui.button(icon='edit', on_click=create_edit_handler(dept, manager_options)).props('flat round dense').tooltip('Edit Department')

                                    def create_delete_handler(d):
                                        def open_delete():
                                            # Delete confirmation dialog
                                            with ui.dialog() as delete_dialog, ui.card().classes('p-6'):
                                                ui.label('Delete Department').classes('text-lg font-semibold mb-2')

                                                if d['employee_count'] > 0:
                                                    with ui.card().classes('w-full p-3 mb-4 border-l-4 border-red-500'):
                                                        with ui.row().classes('items-center gap-2'):
                                                            ui.icon('warning', color='red')
                                                            ui.label(f"Cannot delete: {d['employee_count']} employee(s) assigned").classes('text-red-600')

                                                    ui.label('Reassign employees to another department before deleting.').classes('text-sm opacity-70 mb-4')

                                                    with ui.row().classes('w-full justify-end'):
                                                        ui.button('Close', on_click=delete_dialog.close).props('flat')
                                                else:
                                                    ui.label(f'Are you sure you want to delete "{d["name"]}"?').classes('mb-4')
                                                    ui.label('This action cannot be undone.').classes('text-sm text-red-500 mb-4')

                                                    def confirm_delete():
                                                        db = next(get_db())
                                                        try:
                                                            DepartmentService.delete_department(db, d['id'])
                                                            ui.notify(f'Department "{d["name"]}" deleted', type='positive')
                                                            delete_dialog.close()
                                                            ui.navigate.to('/admin/departments')
                                                        except ValueError as e:
                                                            ui.notify(str(e), type='negative')
                                                        finally:
                                                            db.close()

                                                    with ui.row().classes('w-full justify-end gap-2'):
                                                        ui.button('Cancel', on_click=delete_dialog.close).props('flat')
                                                        ui.button('Delete', on_click=confirm_delete).props('color=red')

                                            delete_dialog.open()
                                        return open_delete

                                    ui.button(icon='delete', on_click=create_delete_handler(dept)).props('flat round dense color=red').tooltip('Delete Department')

@ui.page('/admin/employees')
def admin_employees():
    """Admin page for managing employees."""
    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        with ui.column().classes('gap-2 mb-6'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            ui.label('EMPLOYEE MANAGEMENT').classes('text-xl font-bold').style('color: #5a6a72;')

        # Add New Employee button
        ui.button('Add New Employee', on_click=lambda: ui.navigate.to('/admin/employees/add'), color='primary').classes('mb-6')
        
        db = next(get_db())
        try:
            from src.services.user_service import UserService
            from src.services.department_service import DepartmentService
            
            # Get all users and departments
            users = UserService(db).get_all_users()
            departments = DepartmentService.get_all_departments(db)
            
            # Create department lookup
            dept_lookup = {dept.id: dept.name for dept in departments}
            
            if not users:
                ui.label('No employees yet').classes('text-xl text-gray-500 text-center mt-8')
            else:
                # Build table data
                columns = [
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                    {'name': 'username', 'label': 'Username', 'field': 'username', 'align': 'left', 'sortable': True},
                    {'name': 'department', 'label': 'Department', 'field': 'department', 'align': 'left', 'sortable': True},
                    {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left', 'sortable': True},
                    {'name': 'hire_date', 'label': 'Hire Date', 'field': 'hire_date', 'align': 'left', 'sortable': True},
                    {'name': 'active', 'label': 'Active', 'field': 'active', 'align': 'center', 'sortable': True},
                ]

                rows = []
                for user in users:
                    department_name = 'No Department'
                    if user.department_id:
                        department_name = dept_lookup.get(user.department_id, 'Unknown Department')

                    rows.append({
                        'id': user.id,
                        'name': f'{user.first_name} {user.last_name}',
                        'username': user.username,
                        'department': department_name,
                        'role': user.role.title(),
                        'hire_date': user.hire_date.strftime('%m-%d-%Y') if user.hire_date else 'Not Set',
                        'active': 'Yes' if user.is_active else 'No',
                    })

                table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                table.on('row-click', lambda e: ui.navigate.to(f'/admin/employees/edit/{e.args[1]["id"]}'))
        
        finally:
            db.close()
        
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')

@ui.page('/admin/employees/add')
def admin_employees_add():
    """Admin page for adding a new employee."""
    from datetime import date as date_type
    import json

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # Get departments for dropdown
    db = next(get_db())
    try:
        from src.services.department_service import DepartmentService
        departments = DepartmentService.get_all_departments(db)
        dept_options = {None: 'No Department'}
        dept_options.update({dept.id: dept.name for dept in departments})
    finally:
        db.close()

    with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
        # Header with back button
        with ui.column().classes('gap-2 mb-6'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
            with ui.row().classes('items-center'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin/employees')).props('flat round')
                ui.label('ADD NEW EMPLOYEE').classes('text-xl font-bold ml-2').style('color: #5a6a72;')

        # Basic Information Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Basic Information').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4'):
                first_name_input = ui.input('First Name').props('outlined').classes('flex-1')
                last_name_input = ui.input('Last Name').props('outlined').classes('flex-1')

            with ui.row().classes('w-full gap-4 mt-2'):
                username_input = ui.input('Username').props('outlined').classes('flex-1')
                email_input = ui.input('Email', validation={'Invalid email format': lambda v: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)) if v else False}).props('outlined').classes('flex-1')

            with ui.row().classes('w-full gap-4 mt-2'):
                password_input = ui.input('Password', password=True).props('outlined').classes('flex-1')
                with ui.column().classes('flex-1'):
                    ui.label('').classes('h-4')  # Spacer for alignment
            ui.label('Minimum 8 characters with at least one letter and one number').classes('text-xs opacity-60 -mt-2')

        # Employment Details Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Employment Details').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4'):
                # Hire Date with calendar picker
                with ui.column().classes('flex-1'):
                    ui.label('Hire Date').classes('text-sm font-medium mb-1')
                    with ui.input('Select date').props('outlined readonly').classes('w-full') as hire_date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date(mask='YYYY-MM-DD').bind_value(hire_date_input) as hire_date_picker:
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menu.close).props('flat')
                        with hire_date_input.add_slot('append'):
                            ui.icon('event').on('click', menu.open).classes('cursor-pointer')

                department_select = ui.select(dept_options, label='Department', value=None).props('outlined').classes('flex-1')

            with ui.row().classes('w-full gap-4 mt-2'):
                role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Super Admin'}
                role_select = ui.select(role_options, label='Role', value='employee').props('outlined').classes('flex-1')

                is_active_check = ui.checkbox('Active Employee', value=True).classes('flex-1 self-center')

        # Work Location Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Work Location').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4'):
                state_options = {None: 'Select State', 'IL': 'Illinois', 'NY': 'New York', 'CT': 'Connecticut', 'FL': 'Florida'}
                location_state_select = ui.select(state_options, label='State', value=None).props('outlined').classes('flex-1')

                city_options = {None: 'Select City'}
                location_city_select = ui.select(city_options, label='City', value=None).props('outlined').classes('flex-1')

                def update_city_options():
                    """Update city dropdown based on selected state."""
                    state = location_state_select.value
                    if state == 'IL':
                        location_city_select.options = {None: 'Select City', 'Chicago': 'Chicago'}
                    elif state == 'NY':
                        location_city_select.options = {None: 'Select City', 'New York': 'New York'}
                    elif state == 'CT':
                        location_city_select.options = {None: 'Select City', 'Rowayton': 'Rowayton'}
                    elif state == 'FL':
                        location_city_select.options = {None: 'Select City', 'Boca': 'Boca'}
                    else:
                        location_city_select.options = {None: 'Select City'}
                    location_city_select.value = None
                    location_city_select.update()

                location_state_select.on('update:model-value', lambda e: update_city_options())

        # Remote Work Schedule Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Remote Work Schedule').classes('text-lg font-semibold mb-2').style('color: #5a6a72;')
            ui.label('Select the days this employee works remotely').classes('text-sm opacity-60 mb-4')

            with ui.row().classes('w-full gap-6 justify-center'):
                monday_check = ui.checkbox('Mon').classes('text-center')
                tuesday_check = ui.checkbox('Tue').classes('text-center')
                wednesday_check = ui.checkbox('Wed').classes('text-center')
                thursday_check = ui.checkbox('Thu').classes('text-center')
                friday_check = ui.checkbox('Fri').classes('text-center')

        # Action Buttons
        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Cancel', on_click=lambda: ui.navigate.to('/admin/employees')).props('flat')

            def create_employee():
                # Validate required fields
                if not first_name_input.value:
                    ui.notify('First Name is required', type='negative')
                    return
                if not last_name_input.value:
                    ui.notify('Last Name is required', type='negative')
                    return
                if not username_input.value:
                    ui.notify('Username is required', type='negative')
                    return
                if not email_input.value:
                    ui.notify('Email is required', type='negative')
                    return
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email_input.value):
                    ui.notify('Please enter a valid email address', type='negative')
                    return
                if not password_input.value:
                    ui.notify('Password is required', type='negative')
                    return
                if len(password_input.value) < 8:
                    ui.notify('Password must be at least 8 characters', type='negative')
                    return
                if not hire_date_input.value:
                    ui.notify('Hire Date is required', type='negative')
                    return

                # Parse hire date
                from datetime import datetime
                try:
                    hire_date = datetime.strptime(hire_date_input.value, '%Y-%m-%d').date()
                except ValueError:
                    ui.notify('Invalid hire date format', type='negative')
                    return

                # Build remote schedule JSON
                remote_schedule = {
                    "monday": monday_check.value,
                    "tuesday": tuesday_check.value,
                    "wednesday": wednesday_check.value,
                    "thursday": thursday_check.value,
                    "friday": friday_check.value
                }

                db = next(get_db())
                try:
                    from src.services.user_service import UserService
                    from src.schemas.user_schemas import UserCreate

                    user_data = UserCreate(
                        username=username_input.value,
                        password=password_input.value,
                        email=email_input.value,
                        first_name=first_name_input.value,
                        last_name=last_name_input.value,
                        department_id=department_select.value,
                        role=role_select.value,
                        hire_date=hire_date,
                        remote_schedule=json.dumps(remote_schedule),
                        is_active=is_active_check.value,
                        location_state=location_state_select.value,
                        location_city=location_city_select.value if location_city_select.value else None
                    )

                    user_service = UserService(db)
                    new_user = user_service.create_user(user_data)

                    ui.notify(f'Employee "{new_user.first_name} {new_user.last_name}" created successfully', type='positive')
                    ui.navigate.to('/admin/employees')

                except Exception as e:
                    ui.notify(f'Error creating employee: {str(e)}', type='negative')
                finally:
                    db.close()

            ui.button('Create Employee', on_click=create_employee, color='positive', icon='person_add')

@ui.page('/admin/employees/edit/{user_id}')
def admin_employees_edit(user_id: int):
    """Admin page for editing an existing employee."""
    import json

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if not app.storage.general.get('user') or user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # Fetch the user by ID
    db = next(get_db())
    try:
        from src.services.user_service import UserService
        from src.services.department_service import DepartmentService
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            ui.notify('Employee not found', type='negative')
            ui.navigate.to('/admin/employees')
            return

        # Get departments for dropdown
        departments = DepartmentService.get_all_departments(db)
        dept_options = {None: 'No Department'}
        dept_options.update({dept.id: dept.name for dept in departments})

        # Parse remote schedule if it exists
        remote_schedule = {}
        if user.remote_schedule:
            try:
                if isinstance(user.remote_schedule, str):
                    remote_schedule = json.loads(user.remote_schedule)
                elif isinstance(user.remote_schedule, dict):
                    remote_schedule = user.remote_schedule
            except:
                remote_schedule = {}

        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            # Header with back button
            with ui.column().classes('gap-2 mb-6'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                with ui.row().classes('items-center'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/admin/employees')).props('flat round')
                    ui.label('EDIT EMPLOYEE').classes('text-xl font-bold ml-2').style('color: #5a6a72;')

            # Employee name display
            with ui.card().classes('w-full p-4 mb-4').style('border-left: 4px solid #5a6a72'):
                ui.label(f'{user.first_name} {user.last_name}').classes('text-lg font-semibold')
                ui.label(f'@{user.username} • {user.email}').classes('text-sm opacity-60')

            # Basic Information Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Basic Information').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                with ui.row().classes('w-full gap-4'):
                    first_name_input = ui.input('First Name', value=user.first_name).props('outlined').classes('flex-1')
                    last_name_input = ui.input('Last Name', value=user.last_name).props('outlined').classes('flex-1')

                with ui.row().classes('w-full gap-4 mt-2'):
                    username_input = ui.input('Username', value=user.username).props('outlined').classes('flex-1')
                    email_input = ui.input('Email', value=user.email, validation={'Invalid email format': lambda v: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)) if v else False}).props('outlined').classes('flex-1')

                with ui.row().classes('w-full gap-4 mt-2'):
                    password_input = ui.input('New Password', password=True).props('outlined').classes('flex-1')
                    with ui.column().classes('flex-1'):
                        ui.label('').classes('h-4')  # Spacer
                ui.label('Leave blank to keep current password').classes('text-xs opacity-60 -mt-2')

            # Employment Details Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Employment Details').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                with ui.row().classes('w-full gap-4'):
                    # Hire Date with calendar picker
                    with ui.column().classes('flex-1'):
                        ui.label('Hire Date').classes('text-sm font-medium mb-1')
                        initial_date = user.hire_date.strftime('%Y-%m-%d') if user.hire_date else ''
                        with ui.input('Select date', value=initial_date).props('outlined readonly').classes('w-full') as hire_date_input:
                            with ui.menu().props('no-parent-event') as menu:
                                with ui.date(mask='YYYY-MM-DD', value=initial_date).bind_value(hire_date_input) as hire_date_picker:
                                    with ui.row().classes('justify-end'):
                                        ui.button('Close', on_click=menu.close).props('flat')
                            with hire_date_input.add_slot('append'):
                                ui.icon('event').on('click', menu.open).classes('cursor-pointer')

                    department_select = ui.select(dept_options, label='Department', value=user.department_id).props('outlined').classes('flex-1')

                with ui.row().classes('w-full gap-4 mt-2'):
                    role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Super Admin'}
                    role_select = ui.select(role_options, label='Role', value=user.role).props('outlined').classes('flex-1')

                    is_active_check = ui.checkbox('Active Employee', value=user.is_active).classes('flex-1 self-center')

            # Work Location Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Work Location').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                def get_city_options_for_state(state):
                    if state == 'IL':
                        return {None: 'Select City', 'Chicago': 'Chicago'}
                    elif state == 'NY':
                        return {None: 'Select City', 'New York': 'New York'}
                    elif state == 'CT':
                        return {None: 'Select City', 'Rowayton': 'Rowayton'}
                    elif state == 'FL':
                        return {None: 'Select City', 'Boca': 'Boca'}
                    else:
                        return {None: 'Select City'}

                with ui.row().classes('w-full gap-4'):
                    state_options = {None: 'Select State', 'IL': 'Illinois', 'NY': 'New York', 'CT': 'Connecticut', 'FL': 'Florida'}
                    location_state_select = ui.select(state_options, label='State', value=user.location_state).props('outlined').classes('flex-1')

                    initial_city_options = get_city_options_for_state(user.location_state)
                    location_city_select = ui.select(initial_city_options, label='City', value=user.location_city).props('outlined').classes('flex-1')

                    def update_city_options_edit():
                        state = location_state_select.value
                        location_city_select.options = get_city_options_for_state(state)
                        location_city_select.value = None
                        location_city_select.update()

                    location_state_select.on('update:model-value', lambda e: update_city_options_edit())

            # Remote Work Schedule Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Remote Work Schedule').classes('text-lg font-semibold mb-2').style('color: #5a6a72;')
                ui.label('Select the days this employee works remotely').classes('text-sm opacity-60 mb-4')

                with ui.row().classes('w-full gap-6 justify-center'):
                    monday_check = ui.checkbox('Mon', value=remote_schedule.get('monday', False)).classes('text-center')
                    tuesday_check = ui.checkbox('Tue', value=remote_schedule.get('tuesday', False)).classes('text-center')
                    wednesday_check = ui.checkbox('Wed', value=remote_schedule.get('wednesday', False)).classes('text-center')
                    thursday_check = ui.checkbox('Thu', value=remote_schedule.get('thursday', False)).classes('text-center')
                    friday_check = ui.checkbox('Fri', value=remote_schedule.get('friday', False)).classes('text-center')

            # Action Buttons
            with ui.row().classes('w-full justify-between mt-4'):
                ui.button('Cancel', on_click=lambda: ui.navigate.to('/admin/employees')).props('flat')

                def save_changes():
                    # Validate required fields
                    if not first_name_input.value:
                        ui.notify('First Name is required', type='negative')
                        return
                    if not last_name_input.value:
                        ui.notify('Last Name is required', type='negative')
                        return
                    if not username_input.value:
                        ui.notify('Username is required', type='negative')
                        return
                    if not email_input.value:
                        ui.notify('Email is required', type='negative')
                        return
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, email_input.value):
                        ui.notify('Please enter a valid email address', type='negative')
                        return
                    if password_input.value and len(password_input.value) < 8:
                        ui.notify('Password must be at least 8 characters if changing', type='negative')
                        return
                    if not hire_date_input.value:
                        ui.notify('Hire Date is required', type='negative')
                        return

                    # Parse hire date
                    from datetime import datetime
                    try:
                        hire_date = datetime.strptime(hire_date_input.value, '%Y-%m-%d').date()
                    except ValueError:
                        ui.notify('Invalid hire date format', type='negative')
                        return

                    # Build remote schedule JSON
                    new_remote_schedule = {
                        "monday": monday_check.value,
                        "tuesday": tuesday_check.value,
                        "wednesday": wednesday_check.value,
                        "thursday": thursday_check.value,
                        "friday": friday_check.value
                    }

                    db = next(get_db())
                    try:
                        from src.services.user_service import UserService
                        from src.schemas.user_schemas import UserUpdate

                        update_data = {
                            'username': username_input.value,
                            'email': email_input.value,
                            'first_name': first_name_input.value,
                            'last_name': last_name_input.value,
                            'department_id': department_select.value,
                            'role': role_select.value,
                            'hire_date': hire_date,
                            'remote_schedule': json.dumps(new_remote_schedule),
                            'is_active': is_active_check.value,
                            'location_state': location_state_select.value,
                            'location_city': location_city_select.value if location_city_select.value else None
                        }

                        if password_input.value:
                            update_data['password'] = password_input.value

                        user_update = UserUpdate(**update_data)
                        user_service = UserService(db)
                        updated_user = user_service.update_user(user_id, user_update)

                        if updated_user:
                            ui.notify(f'Employee updated successfully', type='positive')
                            ui.navigate.to('/admin/employees')
                        else:
                            ui.notify('Error updating employee', type='negative')

                    except Exception as e:
                        ui.notify(f'Error updating employee: {str(e)}', type='negative')
                    finally:
                        db.close()

                ui.button('Save Changes', on_click=save_changes, color='positive', icon='save')

            # Danger Zone section
            with ui.card().classes('w-full p-6 mt-6').style('border: 1px solid #ef4444'):
                ui.label('Danger Zone').classes('text-lg font-semibold text-red-600 mb-4')

                with ui.row().classes('gap-4'):
                    if user.is_active:
                        def confirm_deactivate():
                            with ui.dialog() as dialog, ui.card():
                                ui.label(f'Deactivate {user.first_name} {user.last_name}?').classes('text-lg font-bold mb-2')
                                ui.label('This will set the employee as inactive but preserve their records.').classes('text-sm opacity-70 mb-4')
                                with ui.row().classes('gap-4 justify-end'):
                                    ui.button('Cancel', on_click=dialog.close).props('flat')
                                    async def do_deactivate():
                                        from src.services.user_service import UserService
                                        db = next(get_db())
                                        try:
                                            user_service = UserService(db)
                                            if user_service.deactivate_user(user_id):
                                                ui.notify('Employee deactivated', type='positive')
                                                dialog.close()
                                                ui.navigate.to('/admin/employees')
                                            else:
                                                ui.notify('Error deactivating employee', type='negative')
                                        finally:
                                            db.close()
                                    ui.button('Deactivate', on_click=do_deactivate, color='orange')
                            dialog.open()

                        ui.button('Deactivate', on_click=confirm_deactivate, color='orange', icon='person_off')

                    def confirm_delete():
                        with ui.dialog() as dialog, ui.card():
                            ui.label(f'Delete {user.first_name} {user.last_name}?').classes('text-lg font-bold text-red-600 mb-2')
                            ui.label('This will permanently remove the employee and ALL their PTO records.').classes('text-sm text-red-500 mb-2')
                            ui.label('This action cannot be undone!').classes('text-sm font-bold text-red-600 mb-4')
                            with ui.row().classes('gap-4 justify-end'):
                                ui.button('Cancel', on_click=dialog.close).props('flat')
                                async def do_delete():
                                    from src.services.user_service import UserService
                                    db = next(get_db())
                                    try:
                                        user_service = UserService(db)
                                        if user_service.delete_user(user_id):
                                            ui.notify('Employee deleted', type='positive')
                                            dialog.close()
                                            ui.navigate.to('/admin/employees')
                                        else:
                                            ui.notify('Error deleting employee', type='negative')
                                    finally:
                                        db.close()
                                ui.button('Delete Permanently', on_click=do_delete, color='red')
                        dialog.open()

                    ui.button('Delete', on_click=confirm_delete, color='red', icon='delete_forever')

    finally:
        db.close()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0', storage_secret='your-secret-key-change-in-production')
