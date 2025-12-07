from nicegui import ui, app
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logging first
from src.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from src.database import get_db
from src.config import config
from src.services.audit_service import AuditService
from nicegui_app.pages.login import login_page
from nicegui_app.pages.dashboard import dashboard_page
from nicegui_app.pages.request_form import request_form_page
from nicegui_app.pages.carryover import carryover_page
from nicegui_app.pages.manager_carryover import manager_carryover_page
from nicegui_app.pages.calendar import calendar_page
from nicegui_app.pages.handbook import handbook_page
from nicegui_app.pages.reports import reports_page
from nicegui_app.pages.password_reset import password_reset_request_page, password_reset_page
from nicegui_app.logo import LOGO_DATA_URL
from src.services.session_manager import SessionManager, require_auth
from src.services.email_service import email_service

# Set up basic app configuration
app.title = "TJM Time Calendar"

# Add static file serving for logo
STATIC_DIR = Path(__file__).parent / 'static'
app.add_static_files('/static', STATIC_DIR)

@ui.page('/')
def home(timeout: str = None):
    """Home page with login interface."""
    login_page(timeout)

@ui.page('/forgot-password')
def forgot_password():
    """Password reset request page."""
    password_reset_request_page()

@ui.page('/reset-password/{token}')
def reset_password(token: str):
    """Password reset page with token."""
    password_reset_page(token)

@ui.page('/dashboard')
def dashboard():
    """Dashboard page for logged-in users."""
    if not require_auth():
        return
    dashboard_page()

@ui.page('/submit-request')
def submit_request():
    """PTO Request submission page."""
    if not require_auth():
        return
    request_form_page()

@ui.page('/calendar')
def calendar():
    """Calendar view page."""
    if not require_auth():
        return
    calendar_page()

@ui.page('/carryover')
def carryover():
    """Carryover request page."""
    if not require_auth():
        return
    carryover_page()

@ui.page('/manager/carryover')
def manager_carryover():
    """Manager carryover approval page."""
    if not require_auth():
        return
    manager_carryover_page()

@ui.page('/handbook')
def handbook():
    """Employee handbook page."""
    if not require_auth():
        return
    handbook_page()

@ui.page('/reports')
def reports():
    """Reports page for managers and admins."""
    if not require_auth():
        return
    reports_page()

@ui.page('/requests')
def requests():
    """User's PTO request history page with filtering and cancel functionality."""
    if not require_auth():
        return

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user = app.storage.general.get('user')
    user_role = user.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # Current filter state - managers default to 'approved' since their requests auto-approve
    current_filter = {'value': 'approved' if is_manager_or_admin else 'pending'}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Different title for managers vs employees
        page_title = 'MY TIME OFF' if is_manager_or_admin else 'REQUEST HISTORY'
        page_header(title=page_title, show_back=True)

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
    if not require_auth():
        return

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    current_user = app.storage.general.get('user', {})
    user_role = current_user.get('role')
    user_department_id = current_user.get('department_id')

    if user_role not in ['manager', 'admin', 'superadmin']:
        ui.label('Access denied').classes('text-red-500')
        return

    db = next(get_db())
    try:
        from src.services.pto_service import PTOService
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
            page_header(title='PTO REQUEST REVIEW', show_back=True)
            
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
    
    finally:
        db.close()

@ui.page('/admin')
def admin_panel():
    """Admin panel landing page with navigation to admin functions."""
    if not require_auth():
        return

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        page_header(title='ADMIN PANEL', show_back=True)

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

            # Year-End Processing card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('event_repeat', size='3rem').classes('text-primary')
                    ui.label('Year-End Processing').classes('text-xl font-semibold')
                    ui.label('Process year transitions and holidays').classes('text-gray-600 text-center')
                    ui.button('Go to Year-End', on_click=lambda: ui.navigate.to('/admin/year-end'), color='primary')

        # Second row of cards
        with ui.row().classes('w-full gap-6 justify-center mt-6'):
            # Handbook Management card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('menu_book', size='3rem').classes('text-primary')
                    ui.label('Handbook Management').classes('text-xl font-semibold')
                    ui.label('Update and manage employee handbook').classes('text-gray-600 text-center')
                    ui.button('Manage Handbook', on_click=lambda: ui.navigate.to('/admin/handbook'), color='primary')

        # Third row - Super Admin only
        if user_role == 'superadmin':
            with ui.row().classes('w-full gap-6 justify-center mt-6'):
                # System Administration card
                with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-amber-500'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('settings_applications', size='3rem').classes('text-amber-600')
                        ui.label('System Administration').classes('text-xl font-semibold')
                        ui.label('Database, email config, logs, and system settings').classes('text-gray-600 text-center')
                        ui.button('System Settings', on_click=lambda: ui.navigate.to('/admin/system'), color='warning')

        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-8')

@ui.page('/admin/departments')
def admin_departments():
    """Admin page for managing departments with dropdown filter and table display."""
    if not require_auth():
        return

    from src.services.department_service import DepartmentService
    from src.services.user_service import UserService
    from src.models.user import User

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # State for selected department
    view_state = {'selected_dept_id': None, 'employee_filter': ''}

    def load_department_data():
        """Load all department data with members."""
        db = next(get_db())
        try:
            managers = UserService.get_users_by_role(db, 'manager')
            manager_options = {0: 'No Manager'}
            manager_options.update({m.id: f'{m.first_name} {m.last_name}' for m in managers})
            departments = DepartmentService.get_all_departments(db)

            dept_data = []
            for dept in departments:
                manager_name = 'No Manager'
                if dept.manager_id:
                    manager = UserService(db).get_user_by_id(dept.manager_id)
                    if manager:
                        manager_name = f'{manager.first_name} {manager.last_name}'

                # Get employees in this department
                employees = db.query(User).filter(
                    User.department_id == dept.id,
                    User.is_active == True
                ).order_by(User.last_name, User.first_name).all()

                dept_data.append({
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code,
                    'manager_id': dept.manager_id or 0,
                    'manager_name': manager_name,
                    'is_active': dept.is_active,
                    'employee_count': len(employees),
                    'employees': [{'id': e.id, 'name': f'{e.first_name} {e.last_name}', 'email': e.email, 'role': e.role} for e in employees]
                })
            return dept_data, manager_options
        finally:
            db.close()

    dept_data, manager_options = load_department_data()

    # Build dropdown options for department filter
    dept_dropdown_options = {0: '-- Select Department --'}
    dept_dropdown_options.update({d['id']: f"{d['name']} ({d['employee_count']} employees)" for d in dept_data})

    from nicegui_app.components.header import page_header

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_header(title='DEPARTMENT MANAGEMENT', show_back=True, back_url='/admin')

        # Create New Department Card (collapsible)
        with ui.expansion('Create New Department', icon='add_business').classes('w-full mb-4'):
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('w-full gap-4 items-end'):
                    name_input = ui.input('Department Name').props('outlined dense').classes('flex-1')
                    code_input = ui.input('Department Code').props('outlined dense').classes('flex-1')
                    create_manager_select = ui.select(manager_options, label='Manager', value=0).props('outlined dense').classes('flex-1')

                    def create_dept():
                        if not name_input.value or not code_input.value:
                            ui.notify('Name and code are required', type='negative')
                            return
                        db = next(get_db())
                        try:
                            mgr_id = None if create_manager_select.value == 0 else create_manager_select.value
                            DepartmentService.create_department(db, name_input.value, code_input.value, mgr_id)
                            ui.notify(f'Department "{name_input.value}" created successfully', type='positive')
                            ui.navigate.to('/admin/departments')
                        except ValueError as e:
                            ui.notify(str(e), type='negative')
                        finally:
                            db.close()

                    ui.button('Create', icon='add', on_click=create_dept).props('color=primary')

        # Department Filter Card
        with ui.card().classes('w-full mb-4 p-4'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('filter_list', color='primary').classes('text-xl')
                ui.label('Filter by Department').classes('font-semibold')

            with ui.row().classes('w-full items-center gap-4 mt-3'):
                dept_select = ui.select(
                    dept_dropdown_options,
                    label='Select Department',
                    value=0,
                    on_change=lambda e: on_dept_change(e.value)
                ).props('outlined dense').classes('flex-1')

                employee_filter_input = ui.input(
                    placeholder='Filter employees by name or email...'
                ).props('outlined dense clearable').classes('flex-1')
                employee_filter_input.set_visibility(False)

        # Results Container
        results_container = ui.column().classes('w-full')

        def on_dept_change(dept_id):
            view_state['selected_dept_id'] = dept_id if dept_id != 0 else None
            view_state['employee_filter'] = ''
            employee_filter_input.value = ''
            employee_filter_input.set_visibility(dept_id != 0)
            render_department_view()

        def filter_employees():
            view_state['employee_filter'] = employee_filter_input.value or ''
            render_department_view()

        employee_filter_input.on('keydown.enter', lambda: filter_employees())
        employee_filter_input.on('clear', lambda: filter_employees())

        def render_department_view():
            results_container.clear()
            selected_id = view_state['selected_dept_id']
            emp_filter = view_state['employee_filter'].lower().strip()

            with results_container:
                if not selected_id:
                    # Show summary of all departments
                    with ui.card().classes('w-full p-4'):
                        ui.label('All Departments').classes('text-lg font-semibold mb-3')
                        ui.label(f'{len(dept_data)} department(s) total').classes('text-sm opacity-70 mb-4')

                        # Summary table
                        columns = [
                            {'name': 'name', 'label': 'Department', 'field': 'name', 'align': 'left', 'sortable': True},
                            {'name': 'code', 'label': 'Code', 'field': 'code', 'align': 'left'},
                            {'name': 'manager', 'label': 'Manager', 'field': 'manager_name', 'align': 'left'},
                            {'name': 'employees', 'label': 'Employees', 'field': 'employee_count', 'align': 'center', 'sortable': True},
                            {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                        ]
                        rows = [
                            {
                                'id': d['id'],
                                'name': d['name'],
                                'code': d['code'],
                                'manager_name': d['manager_name'],
                                'employee_count': d['employee_count'],
                                'status': 'Active' if d['is_active'] else 'Inactive'
                            }
                            for d in dept_data
                        ]

                        def on_row_click(e):
                            # e.args is [evt, row, index] - row is the second element
                            row_data = e.args[1] if len(e.args) > 1 else None
                            if row_data and 'id' in row_data:
                                dept_select.value = row_data['id']
                                on_dept_change(row_data['id'])

                        ui.table(
                            columns=columns,
                            rows=rows,
                            row_key='id',
                            pagination={'rowsPerPage': 10}
                        ).classes('w-full cursor-pointer').on('row-click', on_row_click).props('dense')

                        ui.label('Click a row to view department details').classes('text-xs opacity-50 mt-2')
                else:
                    # Show selected department details
                    dept = next((d for d in dept_data if d['id'] == selected_id), None)
                    if not dept:
                        ui.label('Department not found').classes('text-red-500')
                        return

                    # Department header card
                    with ui.card().classes('w-full p-4 mb-4 border-l-4 border-indigo-500'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(dept['name']).classes('text-xl font-bold')
                                    if dept['is_active']:
                                        ui.badge('Active', color='green').props('outline')
                                    else:
                                        ui.badge('Inactive', color='grey').props('outline')

                                with ui.row().classes('gap-6 text-sm opacity-70 mt-1'):
                                    ui.label(f"Code: {dept['code']}")
                                    ui.label(f"Manager: {dept['manager_name']}")
                                    ui.label(f"Total Employees: {dept['employee_count']}")

                            # Action buttons
                            with ui.row().classes('gap-2'):
                                def create_edit_handler(d):
                                    def open_edit():
                                        with ui.dialog() as edit_dialog, ui.card().classes('p-6 min-w-96'):
                                            ui.label(f"Edit: {d['name']}").classes('text-lg font-semibold mb-4')
                                            edit_name = ui.input('Department Name', value=d['name']).props('outlined').classes('w-full mb-2')
                                            edit_code = ui.input('Department Code', value=d['code']).props('outlined').classes('w-full mb-2')
                                            edit_manager = ui.select(manager_options, label='Manager', value=d['manager_id']).props('outlined').classes('w-full mb-4')

                                            def save_changes():
                                                if not edit_name.value or not edit_code.value:
                                                    ui.notify('Name and code are required', type='negative')
                                                    return
                                                db = next(get_db())
                                                try:
                                                    mgr_id = None if edit_manager.value == 0 else edit_manager.value
                                                    DepartmentService.update_department(db, d['id'], name=edit_name.value, code=edit_code.value, manager_id=mgr_id)
                                                    ui.notify('Department updated', type='positive')
                                                    edit_dialog.close()
                                                    ui.navigate.to('/admin/departments')
                                                except ValueError as e:
                                                    ui.notify(str(e), type='negative')
                                                finally:
                                                    db.close()

                                            with ui.row().classes('w-full justify-end gap-2'):
                                                ui.button('Cancel', on_click=edit_dialog.close).props('flat')
                                                ui.button('Save', on_click=save_changes).props('color=primary')
                                        edit_dialog.open()
                                    return open_edit

                                ui.button('Edit', icon='edit', on_click=create_edit_handler(dept)).props('flat')

                                def create_delete_handler(d):
                                    def open_delete():
                                        with ui.dialog() as delete_dialog, ui.card().classes('p-6'):
                                            ui.label('Delete Department').classes('text-lg font-semibold mb-2')
                                            if d['employee_count'] > 0:
                                                ui.label(f"Cannot delete: {d['employee_count']} employee(s) assigned").classes('text-red-600 mb-4')
                                                ui.button('Close', on_click=delete_dialog.close).props('flat')
                                            else:
                                                ui.label(f'Delete "{d["name"]}"? This cannot be undone.').classes('mb-4')
                                                with ui.row().classes('gap-2'):
                                                    ui.button('Cancel', on_click=delete_dialog.close).props('flat')
                                                    def confirm():
                                                        db = next(get_db())
                                                        try:
                                                            DepartmentService.delete_department(db, d['id'])
                                                            ui.notify('Deleted', type='positive')
                                                            delete_dialog.close()
                                                            ui.navigate.to('/admin/departments')
                                                        except ValueError as e:
                                                            ui.notify(str(e), type='negative')
                                                        finally:
                                                            db.close()
                                                    ui.button('Delete', on_click=confirm).props('color=red')
                                        delete_dialog.open()
                                    return open_delete

                                ui.button('Delete', icon='delete', on_click=create_delete_handler(dept)).props('flat color=red')

                    # Employees table
                    employees = dept['employees']

                    # Apply employee filter if set
                    if emp_filter:
                        employees = [e for e in employees if emp_filter in e['name'].lower() or emp_filter in e['email'].lower()]

                    with ui.card().classes('w-full p-4'):
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('people', color='indigo')
                            ui.label('Department Members').classes('text-lg font-semibold')
                            ui.badge(f'{len(employees)}', color='indigo')

                        if not employees:
                            if emp_filter:
                                ui.label(f'No employees match "{emp_filter}"').classes('opacity-60')
                            else:
                                ui.label('No employees in this department').classes('opacity-60')
                        else:
                            # Employee table - clean rows, not cards
                            emp_columns = [
                                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                                {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'},
                                {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'center'},
                            ]
                            emp_rows = [
                                {'id': e['id'], 'name': e['name'], 'email': e['email'], 'role': e['role'].title()}
                                for e in employees
                            ]

                            ui.table(
                                columns=emp_columns,
                                rows=emp_rows,
                                row_key='id',
                                pagination={'rowsPerPage': 15}
                            ).classes('w-full').props('dense')

        # Initial render
        render_department_view()

        # Back to Dashboard button
        ui.button('Back to Dashboard', icon='dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')


@ui.page('/admin/approvals')
def admin_approvals():
    """Admin page for viewing and approving all pending PTO requests."""
    if not require_auth():
        return

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    current_user = app.storage.general.get('user', {})
    user_role = current_user.get('role')

    if user_role not in ['admin', 'superadmin']:
        ui.label('Access denied - Admin only').classes('text-red-500')
        return

    db = next(get_db())
    try:
        from src.services.pto_service import PTOService
        from src.services.department_service import DepartmentService

        # Get all pending requests
        pending_requests = PTOService.get_pending_requests_with_employee_info(db)

        # Get all departments for filtering
        all_departments = DepartmentService.get_all_departments(db)

        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='PENDING PTO APPROVALS', show_back=True)

            if not pending_requests:
                with ui.card().classes('w-full p-6 text-center'):
                    ui.icon('check_circle', color='green').classes('text-4xl mb-2')
                    ui.label('No pending requests').classes('text-lg font-semibold text-green-600')
                    ui.label('All PTO requests have been processed.').classes('text-sm opacity-70')
            else:
                # Summary
                ui.label(f'{len(pending_requests)} request(s) awaiting approval').classes('text-sm opacity-70 mb-4')

                # Filter by department
                dept_options = {'all': 'All Departments'}
                for dept in all_departments:
                    dept_options[dept.id] = dept.name

                selected_dept = ui.select(
                    options=dept_options,
                    value='all',
                    label='Filter by Department'
                ).classes('w-64 mb-4')

                # Request list container
                request_container = ui.column().classes('w-full gap-3')

                def render_requests(filter_dept=None):
                    request_container.clear()

                    filtered = pending_requests
                    if filter_dept and filter_dept != 'all':
                        filtered = [r for r in pending_requests if r.get('employee_department_id') == filter_dept]

                    if not filtered:
                        with request_container:
                            ui.label('No pending requests in this department').classes('text-sm opacity-70 italic')
                        return

                    # Type colors
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person'}

                    # Pre-compute conflicts
                    pto_service = PTOService(db)
                    request_conflicts = {}
                    for req in filtered:
                        conflicts = pto_service.get_department_conflicts(
                            req['user_id'],
                            req['start_date'],
                            req['end_date'],
                            exclude_request_id=req['request_id']
                        )
                        if conflicts:
                            request_conflicts[req['request_id']] = len(conflicts)

                    with request_container:
                        for req in filtered:
                            pto_type_lower = req['pto_type'].lower()
                            border_color = type_colors.get(pto_type_lower, 'gray')
                            has_conflict = req['request_id'] in request_conflicts

                            with ui.card().classes(f'w-full p-4 border-l-4 border-{border_color}-500'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('gap-3 items-center'):
                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500 text-2xl')
                                        with ui.column().classes('gap-1'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(req['employee_name']).classes('font-semibold text-lg')
                                                if req.get('department_name'):
                                                    ui.badge(req['department_name'], color='grey').props('outline')
                                                if has_conflict:
                                                    conflict_count = request_conflicts[req['request_id']]
                                                    ui.icon('warning', color='amber').classes('text-lg').tooltip(
                                                        f'{conflict_count} other team member(s) off on same date(s)'
                                                    )
                                            with ui.row().classes('gap-2 items-center'):
                                                ui.label(req['pto_type'].title()).classes('text-sm')
                                                ui.label('•').classes('text-xs opacity-50')
                                                if req['start_date'] == req['end_date']:
                                                    ui.label(req['start_date'].strftime('%b %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req['start_date'].strftime('%b %d')} - {req['end_date'].strftime('%b %d, %Y')}").classes('text-sm opacity-70')
                                                ui.label('•').classes('text-xs opacity-50')
                                                days = float(req['total_days'])
                                                ui.label(f'{days:.1f} days').classes('text-sm font-medium')

                                    ui.button('Review', icon='visibility',
                                             on_click=lambda r=req: ui.navigate.to(f"/manager/request/{r['request_id']}")).props('color=primary')

                # Initial render
                render_requests()

                # Update on filter change
                selected_dept.on('update:model-value', lambda e: render_requests(e.args))

            # Back to Dashboard button
            ui.button('Back to Dashboard', icon='dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')

    finally:
        db.close()


@ui.page('/admin/employees')
def admin_employees():
    """Admin page for managing employees."""
    if not require_auth():
        return

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # Load data
    db = next(get_db())
    try:
        from src.services.user_service import UserService
        from src.services.department_service import DepartmentService

        # Get all users and departments
        all_users = UserService(db).get_all_users()
        departments = DepartmentService.get_all_departments(db)

        # Create department lookup
        dept_lookup = {dept.id: dept.name for dept in departments}

        # Build complete row data for all users
        all_rows = []
        for user in all_users:
            department_name = 'No Department'
            if user.department_id:
                department_name = dept_lookup.get(user.department_id, 'Unknown Department')

            all_rows.append({
                'id': user.id,
                'name': f'{user.first_name} {user.last_name}',
                'username': user.username,
                'department': department_name,
                'department_id': user.department_id,
                'role': user.role.title(),
                'role_raw': user.role,
                'hire_date': user.hire_date.strftime('%m-%d-%Y') if user.hire_date else 'Not Set',
                'active': 'Yes' if user.is_active else 'No',
                'is_active': user.is_active,
            })

        # Build autocomplete options from employee names
        employee_names = [row['name'] for row in all_rows]

    finally:
        db.close()

    # Filter state
    filter_state = {
        'search': '',
        'department_id': None,
        'status': 'all',  # 'all', 'active', 'inactive'
        'role': None,
    }

    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        page_header(title='EMPLOYEE MANAGEMENT', show_back=False)

        # Add New Employee button
        ui.button('Add New Employee', icon='person_add', on_click=lambda: ui.navigate.to('/admin/employees/add')).props('color=primary').classes('mb-4')

        # Filters card
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label('Search & Filter').classes('text-sm font-semibold uppercase opacity-60 mb-3')

            with ui.row().classes('w-full gap-4 items-end flex-wrap'):
                # Search input with autocomplete
                search_input = ui.input(
                    placeholder='Search by name or username...',
                    autocomplete=employee_names
                ).classes('flex-grow min-w-48').props('clearable outlined dense')

                # Department filter
                dept_options = {None: 'All Departments'}
                dept_options.update({dept.id: dept.name for dept in departments})
                dept_select = ui.select(
                    dept_options,
                    label='Department',
                    value=None
                ).classes('w-48').props('outlined dense')

                # Role filter
                role_options = {None: 'All Roles', 'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Superadmin'}
                role_select = ui.select(
                    role_options,
                    label='Role',
                    value=None
                ).classes('w-40').props('outlined dense')

                # Status filter
                status_options = {'all': 'All Status', 'active': 'Active Only', 'inactive': 'Inactive Only'}
                status_select = ui.select(
                    status_options,
                    label='Status',
                    value='all'
                ).classes('w-36').props('outlined dense')

        # Results count
        results_label = ui.label('').classes('text-sm opacity-60 mb-2')

        # Table container
        table_container = ui.column().classes('w-full')

        # Table columns
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
            {'name': 'username', 'label': 'Username', 'field': 'username', 'align': 'left', 'sortable': True},
            {'name': 'department', 'label': 'Department', 'field': 'department', 'align': 'left', 'sortable': True},
            {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left', 'sortable': True},
            {'name': 'hire_date', 'label': 'Hire Date', 'field': 'hire_date', 'align': 'left', 'sortable': True},
            {'name': 'active', 'label': 'Active', 'field': 'active', 'align': 'center', 'sortable': True},
        ]

        def has_any_filter():
            """Check if any filter is applied."""
            return (
                filter_state['search'].strip() != '' or
                filter_state['department_id'] is not None or
                filter_state['role'] is not None or
                filter_state['status'] != 'all'
            )

        def filter_and_render():
            """Filter rows based on current filter state and re-render table."""
            table_container.clear()

            # If no filters applied, show prompt to search
            if not has_any_filter():
                results_label.text = f'{len(all_rows)} employees total'
                with table_container:
                    with ui.column().classes('w-full items-center py-8'):
                        ui.icon('search', size='xl').classes('opacity-40 mb-2')
                        ui.label('Use the search or filters above to find employees').classes('text-gray-500')
                return

            filtered_rows = all_rows.copy()

            # Apply search filter
            search_term = filter_state['search'].lower().strip()
            if search_term:
                filtered_rows = [r for r in filtered_rows if search_term in r['name'].lower() or search_term in r['username'].lower()]

            # Apply department filter
            if filter_state['department_id'] is not None:
                filtered_rows = [r for r in filtered_rows if r['department_id'] == filter_state['department_id']]

            # Apply role filter
            if filter_state['role'] is not None:
                filtered_rows = [r for r in filtered_rows if r['role_raw'] == filter_state['role']]

            # Apply status filter
            if filter_state['status'] == 'active':
                filtered_rows = [r for r in filtered_rows if r['is_active']]
            elif filter_state['status'] == 'inactive':
                filtered_rows = [r for r in filtered_rows if not r['is_active']]

            # Update results count
            results_label.text = f'Showing {len(filtered_rows)} of {len(all_rows)} employees'

            with table_container:
                if not filtered_rows:
                    ui.label('No employees match your filters').classes('text-gray-500 text-center py-8')
                else:
                    table = ui.table(columns=columns, rows=filtered_rows, row_key='id').classes('w-full')
                    table.on('row-click', lambda e: ui.navigate.to(f'/admin/employees/edit/{e.args[1]["id"]}'))

        # Wire up filter handlers - use widget.value instead of event.value
        def on_search_change(e):
            filter_state['search'] = search_input.value or ''
            filter_and_render()

        def on_dept_change(e):
            filter_state['department_id'] = dept_select.value
            filter_and_render()

        def on_role_change(e):
            filter_state['role'] = role_select.value
            filter_and_render()

        def on_status_change(e):
            filter_state['status'] = status_select.value
            filter_and_render()

        search_input.on('update:model-value', on_search_change)
        dept_select.on('update:model-value', on_dept_change)
        role_select.on('update:model-value', on_role_change)
        status_select.on('update:model-value', on_status_change)

        # Initial render
        filter_and_render()

        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-4')

@ui.page('/admin/employees/add')
def admin_employees_add():
    """Admin page for adding a new employee."""
    if not require_auth():
        return

    from datetime import date as date_type
    import json

    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
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

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        page_header(title='ADD NEW EMPLOYEE', show_back=True, back_url='/admin/employees')

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

            with ui.row().classes('w-full gap-4 items-end'):
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

                with ui.column().classes('flex-1'):
                    department_select = ui.select(dept_options, label='Department', value=None).props('outlined').classes('w-full')

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

                    # Log user creation
                    current_user = app.storage.general.get('user')
                    AuditService.log_user_create(
                        db, current_user.get('id'),
                        f"{current_user.get('first_name')} {current_user.get('last_name')}",
                        new_user.id, new_user.username
                    )

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
    if not require_auth():
        return

    import json
    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
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

        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            # Header using shared component
            page_header(title='EDIT EMPLOYEE', show_back=True, back_url='/admin/employees')

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

                with ui.row().classes('w-full gap-4 items-end'):
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

                    with ui.column().classes('flex-1'):
                        department_select = ui.select(dept_options, label='Department', value=user.department_id).props('outlined').classes('w-full')

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
                            # Log user update
                            current_user = app.storage.general.get('user')
                            AuditService.log_user_update(
                                db, current_user.get('id'),
                                f"{current_user.get('first_name')} {current_user.get('last_name')}",
                                user_id, {'fields_updated': list(update_data.keys())}
                            )
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
                                                # Log user deactivation
                                                current_user = app.storage.general.get('user')
                                                AuditService.log_user_deactivate(
                                                    db, current_user.get('id'),
                                                    f"{current_user.get('first_name')} {current_user.get('last_name')}",
                                                    user_id, user.username
                                                )
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
                                            # Log user deletion
                                            current_user = app.storage.general.get('user')
                                            AuditService.log(
                                                db, action='user_delete',
                                                user_id=current_user.get('id'),
                                                username=f"{current_user.get('first_name')} {current_user.get('last_name')}",
                                                entity_type='user', entity_id=user_id,
                                                details={'deleted_user': user.username}
                                            )
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

            # Back to Dashboard button
            ui.button('Back to Dashboard', icon='dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')

    finally:
        db.close()


@ui.page('/admin/handbook')
def admin_handbook():
    """Admin page for managing employee handbook revisions."""
    if not require_auth():
        return

    from datetime import datetime
    from src.services.handbook_revision_service import HandbookRevisionService
    from nicegui_app.static.handbook_content import HANDBOOK_CONTENT
    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    current_user = app.storage.general.get('user')

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='HANDBOOK MANAGEMENT', show_back=True, back_url='/admin')

        # Tabs for different views
        with ui.tabs().classes('w-full') as tabs:
            current_tab = ui.tab('current', label='Current Version', icon='visibility')
            update_tab = ui.tab('update', label='Update Handbook', icon='edit')
            history_tab = ui.tab('history', label='Revision History', icon='history')

        with ui.tab_panels(tabs, value=current_tab).classes('w-full'):
            # Current Version Panel
            with ui.tab_panel(current_tab):
                db = next(get_db())
                try:
                    service = HandbookRevisionService(db)
                    active = service.get_active_revision()

                    if active:
                        with ui.card().classes('w-full p-4 mb-4'):
                            with ui.row().classes('justify-between items-center'):
                                with ui.column():
                                    ui.label(f'Version {active.version}').classes('text-lg font-bold')
                                    ui.label(f"Last updated: {active.created_at.strftime('%B %d, %Y at %I:%M %p')}").classes('text-sm opacity-70')
                                ui.badge('Active', color='green')

                            if active.change_summary:
                                with ui.card().classes('w-full mt-4 p-3 border-l-4 border-blue-500'):
                                    ui.label('Change Summary').classes('font-semibold text-sm')
                                    ui.label(active.change_summary).classes('text-sm')

                        with ui.card().classes('w-full p-4'):
                            ui.label('Content Preview').classes('font-semibold mb-2')
                            ui.markdown(active.content[:2000] + '...' if len(active.content) > 2000 else active.content).classes('text-sm')
                    else:
                        with ui.card().classes('w-full p-4'):
                            ui.label('No handbook version found').classes('text-lg')
                            ui.label('Use the "Update Handbook" tab to create the first version.').classes('text-sm opacity-70')
                            ui.label(f"Default content available: {len(HANDBOOK_CONTENT)} characters").classes('text-sm opacity-70 mt-2')
                finally:
                    db.close()

            # Update Handbook Panel
            with ui.tab_panel(update_tab):
                # State for preview
                preview_state = {'report': None, 'new_content': None, 'backup_file': None}

                with ui.card().classes('w-full p-4'):
                    ui.label('Update Handbook Content').classes('text-lg font-bold mb-2')
                    ui.label('Paste the new handbook content below. Click "Preview Changes" to review before applying.').classes('text-sm opacity-70 mb-4')

                    # Load current content or default
                    db = next(get_db())
                    try:
                        service = HandbookRevisionService(db)
                        active = service.get_active_revision()
                        initial_content = active.content if active else HANDBOOK_CONTENT
                    finally:
                        db.close()

                    content_input = ui.textarea(
                        label='Handbook Content (Markdown)',
                        value=initial_content
                    ).classes('w-full').props('outlined rows=20')

                    # Preview container (initially hidden)
                    preview_container = ui.column().classes('w-full mt-4')
                    preview_container.set_visibility(False)

                    # Confirmation buttons container (initially hidden)
                    confirm_container = ui.row().classes('w-full justify-end gap-4 mt-4')
                    confirm_container.set_visibility(False)

                    def preview_changes():
                        """Analyze changes and show preview before applying."""
                        new_content = content_input.value.strip()
                        if not new_content:
                            ui.notify('Content cannot be empty', type='negative')
                            return

                        preview_db = next(get_db())
                        try:
                            preview_service = HandbookRevisionService(preview_db)
                            current = preview_service.get_active_revision()
                            old_content = current.content if current else ""

                            # Analyze changes without saving
                            report = preview_service._analyze_changes(old_content, new_content)

                            if not report.get('has_changes'):
                                ui.notify('No changes detected in the content', type='info')
                                return

                            # Store for confirmation
                            preview_state['report'] = report
                            preview_state['new_content'] = new_content

                            # Show preview
                            preview_container.clear()
                            preview_container.set_visibility(True)
                            confirm_container.set_visibility(True)

                            with preview_container:
                                ui.label('Change Preview').classes('text-lg font-bold mb-2')

                                # Stats card
                                stats = report.get('stats', {})
                                with ui.card().classes('w-full p-4 mb-4 border-l-4 border-amber-500'):
                                    with ui.row().classes('gap-8'):
                                        with ui.column():
                                            ui.label('Lines Added').classes('text-sm opacity-70')
                                            ui.label(f"+{stats.get('additions', 0)}").classes('text-2xl font-bold text-green-600')
                                        with ui.column():
                                            ui.label('Lines Removed').classes('text-sm opacity-70')
                                            ui.label(f"-{stats.get('deletions', 0)}").classes('text-2xl font-bold text-red-600')
                                        with ui.column():
                                            ui.label('Total Changes').classes('text-sm opacity-70')
                                            ui.label(f"{stats.get('total_lines_changed', 0)}").classes('text-2xl font-bold')

                                # Changes by section
                                changes = report.get('changes', [])
                                if changes:
                                    ui.label('Changes by Section').classes('font-semibold mb-2')
                                    with ui.card().classes('w-full p-3'):
                                        for change in changes[:10]:  # Show first 10
                                            with ui.row().classes('items-center gap-2 py-1 border-b last:border-0'):
                                                section = change.get('section', 'General')
                                                summary = change.get('summary', '')
                                                ui.label(section or 'General').classes('font-medium')
                                                ui.label(summary).classes('text-sm opacity-70')
                                        if len(changes) > 10:
                                            ui.label(f'...and {len(changes) - 10} more sections').classes('text-sm opacity-50 mt-2')

                                # Warning
                                with ui.card().classes('w-full p-3 mt-4 border-l-4 border-blue-500'):
                                    ui.label('A backup will be automatically created before applying changes.').classes('text-sm')
                                    ui.label('You can restore from Admin > System > Database if needed.').classes('text-sm opacity-70')

                        except Exception as e:
                            ui.notify(f'Error analyzing changes: {str(e)}', type='negative')
                        finally:
                            preview_db.close()

                    def cancel_preview():
                        """Cancel the preview and hide confirmation."""
                        preview_container.set_visibility(False)
                        confirm_container.set_visibility(False)
                        preview_state['report'] = None
                        preview_state['new_content'] = None

                    def confirm_and_save():
                        """Create backup and save the new handbook version."""
                        if not preview_state['new_content'] or not preview_state['report']:
                            ui.notify('Please preview changes first', type='warning')
                            return

                        import shutil
                        from pathlib import Path

                        # Step 1: Create backup before changes
                        try:
                            # Get database path from config
                            handbook_db_url = config.DATABASE_URL
                            if handbook_db_url.startswith('sqlite:///'):
                                handbook_db_filename = handbook_db_url.replace('sqlite:///', '')
                                db_path = Path(__file__).parent.parent / handbook_db_filename
                            else:
                                db_path = Path(__file__).parent.parent / 'tjm_calendar.db'
                            backup_dir = Path(__file__).parent.parent / 'backups' / 'handbook_changes'
                            backup_dir.mkdir(parents=True, exist_ok=True)

                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_file = backup_dir / f'pre_handbook_change_{timestamp}.db'
                            shutil.copy2(db_path, backup_file)
                            preview_state['backup_file'] = backup_file
                            logger.info(f"Created handbook change backup: {backup_file}")
                        except Exception as e:
                            ui.notify(f'Backup failed: {str(e)}. Changes not applied.', type='negative')
                            logger.error(f"Handbook backup failed: {str(e)}")
                            return

                        # Step 2: Save the new version
                        save_db = next(get_db())
                        try:
                            save_service = HandbookRevisionService(save_db)
                            revision, report = save_service.create_revision(
                                content=preview_state['new_content'],
                                created_by=current_user.get('id')
                            )

                            stats = report.get('stats', {})
                            ui.notify(
                                f"Version {revision.version} saved! Backup: {backup_file.name}",
                                type='positive'
                            )
                            logger.info(f"Handbook updated to version {revision.version}")

                            # Hide preview and reset
                            cancel_preview()

                        except Exception as e:
                            ui.notify(f'Error saving: {str(e)}. Backup available at {backup_file.name}', type='negative')
                            logger.error(f"Handbook save failed: {str(e)}")
                        finally:
                            save_db.close()

                    # Initial button - Preview Changes
                    with ui.row().classes('w-full justify-end gap-4 mt-4'):
                        ui.button('Preview Changes', on_click=preview_changes, color='primary', icon='preview')

                    # Confirmation buttons (shown after preview)
                    with confirm_container:
                        ui.button('Cancel', on_click=cancel_preview, icon='close').props('flat')
                        ui.button('Apply Changes', on_click=confirm_and_save, color='positive', icon='check').classes('text-white')

            # Revision History Panel
            with ui.tab_panel(history_tab):
                history_container = ui.column().classes('w-full')

                def load_history():
                    history_container.clear()
                    db = next(get_db())
                    try:
                        service = HandbookRevisionService(db)
                        revisions = service.get_all_revisions()

                        with history_container:
                            if not revisions:
                                ui.label('No revisions found').classes('opacity-70')
                                return

                            for rev in revisions:
                                with ui.card().classes('w-full mb-3 p-4'):
                                    with ui.row().classes('justify-between items-start'):
                                        with ui.column():
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(f'Version {rev.version}').classes('font-bold')
                                                if rev.is_active:
                                                    ui.badge('Active', color='green')
                                            ui.label(f"Created: {rev.created_at.strftime('%Y-%m-%d %H:%M')}").classes('text-sm opacity-70')
                                            if rev.change_summary:
                                                ui.label(rev.change_summary).classes('text-sm mt-2')
                    finally:
                        db.close()

                load_history()


@ui.page('/admin/year-end')
def admin_year_end():
    """Admin page for year-end processing."""
    if not require_auth():
        return

    from datetime import datetime
    from src.services.year_end_service import YearEndService
    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    current_year = datetime.now().year
    next_year = current_year + 1

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        page_header(title='YEAR-END PROCESSING', show_back=True, back_url='/admin')

        # Status cards container
        status_container = ui.column().classes('w-full gap-4')

        def refresh_status():
            status_container.clear()
            db = next(get_db())
            try:
                service = YearEndService(db)

                # Current year status
                current_status = service.get_year_end_status(current_year)

                # Next year status
                next_status = service.get_year_end_status(next_year)

                with status_container:
                    # Current Year Card
                    with ui.card().classes('w-full p-4'):
                        ui.label(f'Current Year: {current_year}').classes('text-lg font-bold mb-2')
                        with ui.row().classes('gap-8'):
                            with ui.column():
                                ui.label(f"Active Employees: {current_status['active_users']}")
                                ui.label(f"Balances Created: {current_status['balances_created']}")
                            with ui.column():
                                ui.label(f"Pending Carryovers: {current_status['pending_carryovers']}")
                                ui.label(f"Holidays: {current_status['holidays_created']}")

                    # Next Year Card
                    with ui.card().classes('w-full p-4'):
                        ui.label(f'Next Year: {next_year}').classes('text-lg font-bold mb-2')
                        with ui.row().classes('gap-8'):
                            with ui.column():
                                ui.label(f"Balances Created: {next_status['balances_created']} / {next_status['active_users']}")
                                status_text = "Complete" if next_status['balances_complete'] else "Incomplete"
                                status_color = "green" if next_status['balances_complete'] else "orange"
                                ui.badge(status_text, color=status_color)
                            with ui.column():
                                ui.label(f"Carryovers Applied: {next_status['approved_carryovers']}")
                                ui.label(f"Holidays: {next_status['holidays_created']}")

                    # Warnings
                    if current_status['pending_carryovers'] > 0:
                        with ui.card().classes('w-full p-4 border-l-4 border-amber-500'):
                            ui.label(f"⚠️ {current_status['pending_carryovers']} carryover requests pending").classes('font-semibold text-amber-600')
                            ui.label("These should be approved or denied before year-end processing.").classes('text-sm')

                    # Process Button
                    if not next_status['balances_complete'] or next_status['holidays_created'] == 0:
                        def process_year_end():
                            process_db = next(get_db())
                            try:
                                process_service = YearEndService(process_db)
                                results = process_service.process_year_transition(next_year)

                                if results['errors']:
                                    ui.notify(f"Completed with {len(results['errors'])} errors", type='warning')
                                else:
                                    ui.notify(
                                        f"Success! Created {results['balances_created']} balances, "
                                        f"applied {results['carryovers_applied']} carryovers, "
                                        f"generated {results['holidays_created']} holidays",
                                        type='positive'
                                    )
                                refresh_status()
                            finally:
                                process_db.close()

                        with ui.row().classes('w-full justify-center mt-4'):
                            ui.button(
                                f'Process Year-End Transition to {next_year}',
                                on_click=process_year_end,
                                color='primary',
                                icon='play_arrow'
                            ).classes('text-lg')
                    else:
                        with ui.row().classes('w-full justify-center mt-4'):
                            ui.label(f"✓ Year-end processing complete for {next_year}").classes('text-green-600 font-semibold')

            finally:
                db.close()

        # Initial load
        refresh_status()

        ui.button('Refresh Status', on_click=refresh_status, icon='refresh').classes('mt-4')


@ui.page('/help')
def help_page():
    """Help documentation page with searchable chapters."""
    if not require_auth():
        return

    from src.services.help_service import HelpService
    from nicegui_app.components.header import page_header

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    # State for current view
    current_view = {'chapter': None, 'article': None}
    search_results = {'items': []}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header using shared component (no help button on help page itself)
        page_header(title='HELP CENTER', show_back=True)

        # Search bar
        search_input = ui.input(placeholder='Search help articles...').classes('w-full mb-4').props('outlined dense clearable')

        # Content container
        content_container = ui.column().classes('w-full')

        def show_chapters():
            """Show all chapters (home view)."""
            current_view['chapter'] = None
            current_view['article'] = None
            content_container.clear()
            with content_container:
                chapters = HelpService.get_all_chapters()
                # Use CSS grid for consistent card sizing
                with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;'):
                    for chapter in chapters:
                        with ui.card().classes('cursor-pointer hover:shadow-lg transition-shadow h-full').on('click', lambda c=chapter['id']: show_chapter(c)):
                            with ui.card_section().classes('h-full'):
                                with ui.row().classes('items-center gap-3 mb-3'):
                                    ui.icon(chapter['icon'], size='2rem').classes('text-primary')
                                    ui.label(chapter['title']).classes('text-lg font-semibold')
                                ui.label(f"{chapter['article_count']} articles").classes('text-sm opacity-70 mb-2')
                                for article in chapter['articles'][:3]:
                                    ui.label(f"• {article['title']}").classes('text-sm truncate')
                                if len(chapter['articles']) > 3:
                                    ui.label(f"  + {len(chapter['articles']) - 3} more...").classes('text-xs opacity-50')

        def show_chapter(chapter_id):
            """Show articles in a chapter."""
            current_view['chapter'] = chapter_id
            current_view['article'] = None
            content_container.clear()
            with content_container:
                chapter = HelpService.get_chapter(chapter_id)
                if not chapter:
                    ui.label('Chapter not found')
                    return

                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').classes('text-primary cursor-pointer').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(chapter['title']).classes('font-semibold')

                # Articles list
                with ui.card().classes('w-full'):
                    for article in chapter['articles']:
                        with ui.row().classes('w-full p-4 border-b last:border-0 items-center cursor-pointer hover:bg-gray-50').on('click', lambda a=article['id'], c=chapter_id: show_article(c, a)):
                            ui.icon('article').classes('text-primary mr-3')
                            ui.label(article['title']).classes('text-lg')
                            ui.space()
                            ui.icon('chevron_right').classes('opacity-50')

        def show_article(chapter_id, article_id):
            """Show a single article."""
            current_view['chapter'] = chapter_id
            current_view['article'] = article_id
            content_container.clear()
            with content_container:
                article = HelpService.get_article(chapter_id, article_id)
                if not article:
                    ui.label('Article not found')
                    return

                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').classes('text-primary cursor-pointer').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(article['chapter_title']).classes('text-primary cursor-pointer').on('click', lambda c=chapter_id: show_chapter(c))
                    ui.label('/').classes('opacity-50')
                    ui.label(article['title']).classes('font-semibold')

                # Article content
                with ui.card().classes('w-full p-6'):
                    ui.markdown(article['content']).classes('prose max-w-none')

        def do_search(e):
            """Perform search and show results."""
            query = e.value if hasattr(e, 'value') else search_input.value
            if not query or len(query) < 2:
                show_chapters()
                return

            results = HelpService.search(query)
            content_container.clear()
            with content_container:
                # Breadcrumb
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Help').classes('text-primary cursor-pointer').on('click', show_chapters)
                    ui.label('/').classes('opacity-50')
                    ui.label(f'Search: "{query}"').classes('font-semibold')

                if not results:
                    with ui.card().classes('w-full p-8 text-center'):
                        ui.icon('search_off', size='3rem').classes('opacity-30 mb-2')
                        ui.label(f'No results found for "{query}"').classes('text-lg opacity-60')
                else:
                    ui.label(f'{len(results)} result(s) found').classes('text-sm opacity-70 mb-2')
                    with ui.card().classes('w-full'):
                        for result in results:
                            with ui.row().classes('w-full p-4 border-b last:border-0 cursor-pointer hover:bg-gray-50').on('click', lambda r=result: show_article(r['chapter_id'], r['article_id'])):
                                with ui.column().classes('flex-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(result['article_title']).classes('font-semibold')
                                        ui.badge(result['chapter_title']).classes('text-xs')
                                    if result['snippet']:
                                        ui.label(result['snippet']).classes('text-sm opacity-70 mt-1')

        search_input.on('keydown.enter', do_search)

        # Initial view
        show_chapters()

        # Back to Dashboard button
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-6')


@ui.page('/admin/system')
def admin_system():
    """Super Admin system administration page."""
    if not require_auth():
        return

    import os
    import subprocess
    from datetime import datetime
    from pathlib import Path
    from src.config import config

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role != 'superadmin':
        ui.notify('Access denied - Super Admin only', type='negative')
        ui.navigate.to('/')
        return

    from nicegui_app.components.header import page_header

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        # Header
        page_header(title='SYSTEM ADMINISTRATION', show_back=True, back_url='/admin')

        # Tabs for different sections
        with ui.tabs().classes('w-full') as tabs:
            database_tab = ui.tab('Database', icon='storage')
            email_tab = ui.tab('Email Config', icon='email')
            logs_tab = ui.tab('System Logs', icon='description')
            settings_tab = ui.tab('Settings', icon='tune')

        with ui.tab_panels(tabs, value=database_tab).classes('w-full'):
            # ========== DATABASE TAB ==========
            with ui.tab_panel(database_tab):
                with ui.card().classes('w-full p-4 mb-4'):
                    ui.label('Database Management').classes('text-lg font-semibold mb-4')

                    # Database info - derive path from DATABASE_URL config
                    db_url = config.DATABASE_URL
                    if db_url.startswith('sqlite:///'):
                        db_filename = db_url.replace('sqlite:///', '')
                        db_path = Path(__file__).parent.parent / db_filename
                    else:
                        db_path = Path(__file__).parent.parent / 'tjm_calendar.db'
                    db_exists = db_path.exists()
                    db_size = db_path.stat().st_size / (1024 * 1024) if db_exists else 0  # MB

                    with ui.row().classes('gap-8 mb-4'):
                        with ui.column():
                            ui.label('Database File').classes('text-sm opacity-70')
                            ui.label(str(db_path.name)).classes('font-mono')
                        with ui.column():
                            ui.label('Size').classes('text-sm opacity-70')
                            ui.label(f'{db_size:.2f} MB').classes('font-mono')
                        with ui.column():
                            ui.label('Status').classes('text-sm opacity-70')
                            if db_exists:
                                ui.badge('Online', color='green')
                            else:
                                ui.badge('Not Found', color='red')

                    ui.separator().classes('my-4')

                    # Backup section
                    ui.label('Backup Database').classes('font-semibold mb-2')
                    backup_status = ui.label('').classes('text-sm')

                    def run_backup():
                        try:
                            backup_status.set_text('Running backup...')
                            backup_dir = Path(__file__).parent.parent / 'backups'
                            backup_dir.mkdir(exist_ok=True)

                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            db_name = db_path.stem  # Get filename without extension
                            backup_file = backup_dir / f'{db_name}_{timestamp}.db'

                            import shutil
                            shutil.copy2(db_path, backup_file)

                            backup_status.set_text(f'Backup created: {backup_file.name}')
                            ui.notify(f'Backup successful: {backup_file.name}', type='positive')
                            refresh_backups()
                        except Exception as e:
                            backup_status.set_text(f'Error: {str(e)}')
                            ui.notify(f'Backup failed: {str(e)}', type='negative')

                    ui.button('Create Backup Now', icon='backup', on_click=run_backup).props('color=primary')

                    ui.separator().classes('my-4')

                    # Existing backups
                    ui.label('Existing Backups').classes('font-semibold mb-2')
                    backups_container = ui.column().classes('w-full')

                    def refresh_backups():
                        backups_container.clear()
                        backup_dir = Path(__file__).parent.parent / 'backups'
                        if not backup_dir.exists():
                            with backups_container:
                                ui.label('No backups directory found').classes('opacity-60')
                            return

                        backup_files = sorted(backup_dir.glob('*.db'), key=lambda x: x.stat().st_mtime, reverse=True)
                        if not backup_files:
                            with backups_container:
                                ui.label('No backups found').classes('opacity-60')
                            return

                        with backups_container:
                            for bf in backup_files[:10]:  # Show last 10
                                size_mb = bf.stat().st_size / (1024 * 1024)
                                mtime = datetime.fromtimestamp(bf.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                with ui.row().classes('w-full items-center gap-4 p-2 border-b'):
                                    ui.icon('save').classes('opacity-50')
                                    ui.label(bf.name).classes('font-mono flex-1')
                                    ui.label(f'{size_mb:.2f} MB').classes('text-sm opacity-70')
                                    ui.label(mtime).classes('text-sm opacity-70')

                                    def create_restore_handler(backup_file):
                                        def restore():
                                            with ui.dialog() as dialog, ui.card().classes('p-6'):
                                                ui.label('Restore Database').classes('text-lg font-semibold mb-2')
                                                ui.label(f'Restore from: {backup_file.name}').classes('mb-2')
                                                ui.label('WARNING: This will overwrite the current database!').classes('text-red-500 mb-4')

                                                def confirm_restore():
                                                    try:
                                                        import shutil
                                                        shutil.copy2(backup_file, db_path)
                                                        ui.notify('Database restored successfully. Please restart the application.', type='positive')
                                                        dialog.close()
                                                    except Exception as e:
                                                        ui.notify(f'Restore failed: {str(e)}', type='negative')

                                                with ui.row().classes('gap-2'):
                                                    ui.button('Cancel', on_click=dialog.close).props('flat')
                                                    ui.button('Restore', on_click=confirm_restore).props('color=red')
                                            dialog.open()
                                        return restore

                                    ui.button(icon='restore', on_click=create_restore_handler(bf)).props('flat dense').tooltip('Restore this backup')

                    refresh_backups()

            # ========== EMAIL CONFIG TAB ==========
            with ui.tab_panel(email_tab):
                with ui.card().classes('w-full p-4'):
                    ui.label('Email Configuration').classes('text-lg font-semibold mb-4')

                    # Current config display
                    smtp_host = os.getenv('SMTP_HOST', 'Not configured')
                    smtp_port = os.getenv('SMTP_PORT', 'Not configured')
                    smtp_user = os.getenv('SMTP_USER', 'Not configured')
                    smtp_from = os.getenv('SMTP_FROM', 'Not configured')
                    smtp_configured = smtp_host != 'Not configured'

                    with ui.row().classes('gap-8 mb-4'):
                        with ui.column():
                            ui.label('Status').classes('text-sm opacity-70')
                            if smtp_configured:
                                ui.badge('Configured', color='green')
                            else:
                                ui.badge('Not Configured', color='red')
                        with ui.column():
                            ui.label('SMTP Host').classes('text-sm opacity-70')
                            ui.label(smtp_host).classes('font-mono')
                        with ui.column():
                            ui.label('SMTP Port').classes('text-sm opacity-70')
                            ui.label(smtp_port).classes('font-mono')

                    with ui.row().classes('gap-8 mb-4'):
                        with ui.column():
                            ui.label('SMTP User').classes('text-sm opacity-70')
                            ui.label(smtp_user if smtp_user != 'Not configured' else '-').classes('font-mono')
                        with ui.column():
                            ui.label('From Address').classes('text-sm opacity-70')
                            ui.label(smtp_from).classes('font-mono')

                    ui.separator().classes('my-4')

                    # Test email
                    ui.label('Send Test Email').classes('font-semibold mb-2')
                    test_email_input = ui.input('Recipient Email').props('outlined dense').classes('w-80')
                    test_status = ui.label('').classes('text-sm mt-2')

                    def send_test_email():
                        if not test_email_input.value:
                            ui.notify('Please enter an email address', type='warning')
                            return
                        if not smtp_configured:
                            ui.notify('SMTP not configured. Set environment variables first.', type='negative')
                            return

                        test_status.set_text('Sending test email...')
                        try:
                            from src.services.email_service import email_service
                            success = email_service.send_email(
                                to_email=test_email_input.value,
                                subject='TJM Calendar - Test Email',
                                body='This is a test email from the TJM Time Calendar system.\n\nIf you received this, your email configuration is working correctly!'
                            )
                            if success:
                                test_status.set_text('Test email sent successfully!')
                                ui.notify('Test email sent!', type='positive')
                            else:
                                test_status.set_text('Failed to send test email. Check logs.')
                                ui.notify('Failed to send email', type='negative')
                        except Exception as e:
                            test_status.set_text(f'Error: {str(e)}')
                            ui.notify(f'Error: {str(e)}', type='negative')

                    ui.button('Send Test', icon='send', on_click=send_test_email).props('color=primary')

                    ui.separator().classes('my-4')

                    # Configuration instructions
                    with ui.expansion('How to Configure Email', icon='help_outline').classes('w-full'):
                        ui.markdown('''
Set these environment variables in your `.env` file:

```
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@company.com
```

**Common providers:**
- Gmail: `smtp.gmail.com:587`
- Microsoft 365: `smtp.office365.com:587`
- Amazon SES: `email-smtp.us-east-1.amazonaws.com:587`

After updating `.env`, restart the application.
                        ''')

            # ========== LOGS TAB ==========
            with ui.tab_panel(logs_tab):
                with ui.card().classes('w-full p-4'):
                    ui.label('System Logs').classes('text-lg font-semibold mb-4')

                    log_path = Path(__file__).parent.parent / 'logs' / 'tjm_calendar.log'
                    log_exists = log_path.exists()

                    with ui.row().classes('gap-4 mb-4 items-center'):
                        ui.label('Log File:').classes('text-sm opacity-70')
                        ui.label(str(log_path.name) if log_exists else 'Not found').classes('font-mono')
                        if log_exists:
                            log_size = log_path.stat().st_size / 1024  # KB
                            ui.label(f'({log_size:.1f} KB)').classes('text-sm opacity-70')

                    # Log viewer
                    log_display = ui.textarea('').props('readonly outlined').classes('w-full font-mono text-xs').style('height: 400px;')

                    def refresh_logs(lines=100):
                        if not log_exists:
                            log_display.value = 'Log file not found. Logs will appear after application activity.'
                            return
                        try:
                            with open(log_path, 'r') as f:
                                all_lines = f.readlines()
                                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                                log_display.value = ''.join(recent)
                        except Exception as e:
                            log_display.value = f'Error reading log: {str(e)}'

                    with ui.row().classes('gap-2 mb-2'):
                        ui.button('Refresh', icon='refresh', on_click=lambda: refresh_logs()).props('flat')
                        ui.button('Last 50', on_click=lambda: refresh_logs(50)).props('flat dense')
                        ui.button('Last 100', on_click=lambda: refresh_logs(100)).props('flat dense')
                        ui.button('Last 500', on_click=lambda: refresh_logs(500)).props('flat dense')

                        def clear_logs():
                            if log_exists:
                                try:
                                    with open(log_path, 'w') as f:
                                        f.write('')
                                    ui.notify('Logs cleared', type='positive')
                                    refresh_logs()
                                except Exception as e:
                                    ui.notify(f'Error: {str(e)}', type='negative')

                        ui.button('Clear Logs', icon='delete', on_click=clear_logs).props('flat color=red')

                    refresh_logs()

            # ========== SETTINGS TAB ==========
            with ui.tab_panel(settings_tab):
                with ui.card().classes('w-full p-4'):
                    ui.label('System Settings').classes('text-lg font-semibold mb-4')

                    # Current settings display
                    with ui.row().classes('gap-8 mb-4'):
                        with ui.column():
                            ui.label('Debug Mode').classes('text-sm opacity-70')
                            debug_val = os.getenv('DEBUG', 'false')
                            if debug_val.lower() == 'true':
                                ui.badge('ENABLED', color='red')
                            else:
                                ui.badge('Disabled', color='green')
                        with ui.column():
                            ui.label('Secret Key').classes('text-sm opacity-70')
                            secret = os.getenv('SECRET_KEY', '')
                            if secret and len(secret) > 20:
                                ui.badge('Configured', color='green')
                            else:
                                ui.badge('Weak/Missing', color='red')
                        with ui.column():
                            ui.label('Session Timeout').classes('text-sm opacity-70')
                            timeout = os.getenv('SESSION_TIMEOUT_MINUTES', '30')
                            ui.label(f'{timeout} minutes').classes('font-mono')

                    ui.separator().classes('my-4')

                    # Environment variables summary
                    ui.label('Environment Variables').classes('font-semibold mb-2')
                    env_vars = [
                        ('SECRET_KEY', 'Yes' if os.getenv('SECRET_KEY') else 'No'),
                        ('DEBUG', os.getenv('DEBUG', 'false')),
                        ('DATABASE_URL', 'Configured' if os.getenv('DATABASE_URL') else 'Default'),
                        ('SMTP_HOST', os.getenv('SMTP_HOST', 'Not set')),
                        ('ANTHROPIC_API_KEY', 'Set' if os.getenv('ANTHROPIC_API_KEY') else 'Not set'),
                    ]

                    with ui.card().classes('w-full p-3 bg-gray-50'):
                        for var_name, var_val in env_vars:
                            with ui.row().classes('w-full justify-between py-1 border-b last:border-0'):
                                ui.label(var_name).classes('font-mono text-sm')
                                ui.label(var_val).classes('text-sm opacity-70')

                    ui.separator().classes('my-4')

                    # System info
                    ui.label('System Information').classes('font-semibold mb-2')
                    import platform
                    import sys

                    with ui.row().classes('gap-8'):
                        with ui.column():
                            ui.label('Python Version').classes('text-sm opacity-70')
                            ui.label(sys.version.split()[0]).classes('font-mono')
                        with ui.column():
                            ui.label('Platform').classes('text-sm opacity-70')
                            ui.label(platform.system()).classes('font-mono')
                        with ui.column():
                            ui.label('Architecture').classes('text-sm opacity-70')
                            ui.label(platform.machine()).classes('font-mono')

        # Back button
        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))


@ui.page('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    from datetime import datetime
    from sqlalchemy import text

    status = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

    db = None
    try:
        # Test database connection
        db = next(get_db())
        db.execute(text('SELECT 1'))
        status['database'] = 'connected'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['database'] = f'error: {str(e)}'
        logger.error(f"Health check failed - database error: {str(e)}")
    finally:
        if db:
            db.close()

    with ui.column().classes('w-full max-w-md mx-auto mt-8 p-6'):
        color = 'green' if status['status'] == 'healthy' else 'red'
        ui.label(f"Status: {status['status'].upper()}").classes(f'text-2xl font-bold text-{color}-600')
        ui.label(f"Database: {status['database']}").classes('text-lg')
        ui.label(f"Timestamp: {status['timestamp']}").classes('text-sm opacity-70')


if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Starting TJM Time Calendar application")
    ui.run(port=8080, host='0.0.0.0', storage_secret=config.SECRET_KEY)
