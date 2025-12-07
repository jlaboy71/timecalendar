from nicegui import ui, app
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize logging first
from src.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from src.database import get_db, init_db
from src.config import config
# Import all models to ensure they're registered with Base before init_db
from src import models
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

# Ensure all database tables exist (creates any missing tables)
init_db()

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

                    # Use database version if exists, otherwise use default static content
                    content_to_display = active.content if active else HANDBOOK_CONTENT
                    version_label = f'Version {active.version}' if active else 'Default Version (May 1, 2024)'
                    updated_label = f"Last updated: {active.created_at.strftime('%B %d, %Y at %I:%M %p')}" if active else 'Source: Haventech LLC Employee Handbook'

                    with ui.card().classes('w-full p-4 mb-4'):
                        with ui.row().classes('justify-between items-center'):
                            with ui.column():
                                ui.label(version_label).classes('text-lg font-bold')
                                ui.label(updated_label).classes('text-sm opacity-70')
                                ui.label(f'{len(content_to_display):,} characters').classes('text-sm opacity-70')
                            ui.badge('Active', color='green')

                        if active and active.change_summary:
                            with ui.card().classes('w-full mt-4 p-3 border-l-4 border-blue-500'):
                                ui.label('Change Summary').classes('font-semibold text-sm')
                                ui.label(active.change_summary).classes('text-sm')

                    # Content preview card
                    with ui.card().classes('w-full p-4'):
                        ui.label('Content Preview').classes('font-semibold mb-2')
                        preview_text = content_to_display[:1500] + '...' if len(content_to_display) > 1500 else content_to_display
                        ui.markdown(preview_text).classes('text-sm')

                    # View Full Handbook button
                    def show_full_handbook():
                        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl max-h-screen'):
                            with ui.row().classes('w-full justify-between items-center mb-4'):
                                ui.label('Employee Handbook').classes('text-xl font-bold')
                                ui.button(icon='close', on_click=dialog.close).props('flat round')
                            with ui.scroll_area().classes('w-full').style('height: 70vh'):
                                ui.markdown(content_to_display).classes('text-sm')
                        dialog.open()

                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('View Full Handbook', icon='menu_book', on_click=show_full_handbook).props('outline')

                finally:
                    db.close()

            # Update Handbook Panel
            with ui.tab_panel(update_tab):
                # State for preview
                preview_state = {'report': None, 'new_content': None, 'backup_file': None}

                # PDF Upload Section
                with ui.card().classes('w-full p-4 mb-4 border-2 border-dashed border-blue-400'):
                    ui.label('Upload New Handbook PDF').classes('text-lg font-bold mb-2')
                    ui.label('Upload a PDF file to extract and validate handbook content. The system will check for required PTO policy sections.').classes('text-sm opacity-70 mb-4')

                    # Validation results container
                    validation_container = ui.column().classes('w-full')
                    validation_container.set_visibility(False)

                    # Required sections for validation
                    REQUIRED_SECTIONS = [
                        ('holidays', ['holiday', 'holidays', 'market holiday']),
                        ('vacation', ['vacation', 'vacation policy', 'annual vacation']),
                        ('personal', ['personal day', 'personal days']),
                        ('sick', ['sick time', 'sick leave', 'paid sick']),
                    ]

                    OPTIONAL_SECTIONS = [
                        ('fmla', ['fmla', 'family and medical leave']),
                        ('bereavement', ['bereavement']),
                        ('jury duty', ['jury duty']),
                        ('remote work', ['remote work', 'work from home']),
                    ]

                    async def handle_pdf_upload(e):
                        """Handle PDF file upload and validation."""
                        if not e.content:
                            ui.notify('No file selected', type='warning')
                            return

                        try:
                            import io
                            import os
                            import hashlib
                            from pathlib import Path
                            from pypdf import PdfReader

                            # Read PDF content
                            pdf_bytes = e.content.read()

                            # Calculate hash of the uploaded file for duplicate detection
                            file_hash = hashlib.md5(pdf_bytes).hexdigest()

                            # Check for existing PDFs in handbook folder
                            handbook_dir = Path(__file__).parent.parent / 'handbook'
                            handbook_dir.mkdir(exist_ok=True)

                            # Scan all subfolders for existing PDFs and compare hashes
                            duplicate_found = None
                            for subfolder in handbook_dir.iterdir():
                                if subfolder.is_dir():
                                    for pdf_file in subfolder.glob('*.pdf'):
                                        existing_hash = hashlib.md5(pdf_file.read_bytes()).hexdigest()
                                        if existing_hash == file_hash:
                                            duplicate_found = (subfolder.name, pdf_file.name)
                                            break
                                if duplicate_found:
                                    break

                            # If duplicate found, show friendly message and stop
                            if duplicate_found:
                                validation_container.clear()
                                validation_container.set_visibility(True)
                                with validation_container:
                                    with ui.card().classes('w-full p-4 border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('info', color='orange').classes('text-2xl')
                                            ui.label('This File Already Exists').classes('font-bold text-amber-700 dark:text-amber-400')
                                        ui.label(f'This handbook PDF has already been uploaded and saved.').classes('text-sm mb-2')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('folder', color='blue')
                                            ui.label(f'Location: handbook/{duplicate_found[0]}/{duplicate_found[1]}').classes('text-sm font-mono')
                                        ui.label('If you need to update the handbook, please upload a different version of the PDF.').classes('text-sm mt-3 opacity-70')
                                return

                            # Parse PDF
                            pdf_file_io = io.BytesIO(pdf_bytes)
                            reader = PdfReader(pdf_file_io)

                            # Extract text from all pages
                            extracted_text = []
                            for page_num, page in enumerate(reader.pages, 1):
                                text = page.extract_text()
                                if text:
                                    extracted_text.append(f"--- Page {page_num} ---\n{text}")

                            full_text = "\n\n".join(extracted_text)
                            text_lower = full_text.lower()

                            # Validate required sections
                            validation_results = []
                            missing_required = []
                            found_required = []

                            for section_name, keywords in REQUIRED_SECTIONS:
                                found = any(kw in text_lower for kw in keywords)
                                if found:
                                    found_required.append(section_name)
                                else:
                                    missing_required.append(section_name)

                            # Check optional sections
                            found_optional = []
                            for section_name, keywords in OPTIONAL_SECTIONS:
                                if any(kw in text_lower for kw in keywords):
                                    found_optional.append(section_name)

                            # Show validation results
                            validation_container.clear()
                            validation_container.set_visibility(True)

                            with validation_container:
                                # File info
                                with ui.row().classes('items-center gap-2 mb-3'):
                                    ui.icon('picture_as_pdf', color='red').classes('text-2xl')
                                    ui.label(f'{e.name}').classes('font-bold')
                                    ui.label(f'({len(reader.pages)} pages, {len(full_text):,} characters)').classes('text-sm opacity-70')

                                if missing_required:
                                    # Warning - missing required sections
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20'):
                                        ui.label('Missing Required Sections').classes('font-bold text-red-700 dark:text-red-400')
                                        ui.label('This PDF is missing the following required PTO policy sections:').classes('text-sm mb-2')
                                        for section in missing_required:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('cancel', color='red')
                                                ui.label(section.title()).classes('text-sm')
                                        ui.label('The handbook must contain Holidays, Vacation, Personal Days, and Sick Time policies.').classes('text-sm mt-2 opacity-70')
                                else:
                                    # Success - all required sections found
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-green-500 bg-green-50 dark:bg-green-900/20'):
                                        ui.label('All Required Sections Found').classes('font-bold text-green-700 dark:text-green-400')
                                        for section in found_required:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('check_circle', color='green')
                                                ui.label(section.title()).classes('text-sm')

                                # Optional sections found
                                if found_optional:
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-blue-500'):
                                        ui.label('Additional Sections Detected').classes('font-bold')
                                        for section in found_optional:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('info', color='blue')
                                                ui.label(section.title()).classes('text-sm')

                                # Action buttons
                                with ui.row().classes('gap-4 mt-4 items-center flex-wrap'):
                                    if not missing_required:
                                        # Store pdf_bytes and filename for save function
                                        upload_state = {'pdf_bytes': pdf_bytes, 'filename': e.name}

                                        def save_and_load():
                                            # Create dated subfolder (MMDDYY format)
                                            today = datetime.now().strftime('%m%d%y')
                                            save_dir = handbook_dir / today
                                            save_dir.mkdir(exist_ok=True)

                                            # Save PDF file
                                            save_path = save_dir / upload_state['filename']
                                            save_path.write_bytes(upload_state['pdf_bytes'])

                                            # Load content into editor
                                            content_input.value = full_text
                                            ui.notify(f'PDF saved to handbook/{today}/ and content loaded into editor.', type='positive')
                                            validation_container.set_visibility(False)

                                        ui.button('Save PDF & Load Content', icon='save', on_click=save_and_load).props('color=primary')
                                        ui.label(f'Saves to handbook/{datetime.now().strftime("%m%d%y")}/ and loads text into editor.').classes('text-sm opacity-70')
                                    else:
                                        upload_state = {'pdf_bytes': pdf_bytes, 'filename': e.name}

                                        def save_anyway():
                                            today = datetime.now().strftime('%m%d%y')
                                            save_dir = handbook_dir / today
                                            save_dir.mkdir(exist_ok=True)
                                            save_path = save_dir / upload_state['filename']
                                            save_path.write_bytes(upload_state['pdf_bytes'])
                                            content_input.value = full_text
                                            ui.notify(f'PDF saved. Missing sections may cause issues.', type='warning')
                                            validation_container.set_visibility(False)

                                        ui.button('Save Anyway (Not Recommended)', icon='warning', on_click=save_anyway).props('color=warning outline')

                        except ImportError:
                            ui.notify('PDF parsing library not installed. Run: pip install pypdf', type='negative')
                        except Exception as ex:
                            ui.notify(f'Error reading PDF: {str(ex)}', type='negative')

                    with ui.row().classes('items-center gap-4'):
                        ui.upload(
                            label='Select PDF File',
                            on_upload=handle_pdf_upload,
                            auto_upload=True,
                            max_files=1
                        ).props('accept=".pdf" color=primary').classes('max-w-xs')
                        ui.label('or paste content manually below').classes('text-sm opacity-70')

                # Manual Content Section
                with ui.card().classes('w-full p-4'):
                    ui.label('Handbook Content Editor').classes('text-lg font-bold mb-2')
                    ui.label('Edit the handbook content below. Click "Preview Changes" to review before applying.').classes('text-sm opacity-70 mb-4')

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

        # Back to Dashboard button at bottom (left aligned)
        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'), icon='arrow_back').props('outline')


@ui.page('/admin/year-end')
def admin_year_end():
    """Admin page for year-end processing status (automatic processing)."""
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
        page_header(title='YEAR-END STATUS', show_back=True, back_url='/dashboard')

        # Info card explaining automatic processing
        with ui.card().classes('w-full p-4 mb-4 border-l-4 border-blue-500'):
            ui.label('Automatic Year-End Processing').classes('font-semibold text-blue-600')
            ui.label('Year-end processing runs automatically on the first login of each new year. '
                     'This page shows the current status of balances, carryovers, and holidays.').classes('text-sm opacity-80')

        # Status cards container
        status_container = ui.column().classes('w-full gap-4')

        def refresh_status():
            status_container.clear()
            db = next(get_db())
            try:
                service = YearEndService(db)

                # Current year status
                current_status = service.get_year_end_status(current_year)

                # Get processing record
                processing_record = service.get_processing_record(current_year)

                with status_container:
                    # Processing Status Card
                    with ui.card().classes('w-full p-4'):
                        ui.label(f'Year {current_year} Processing Status').classes('text-lg font-bold mb-2')

                        if processing_record and processing_record.processed:
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('check_circle', color='green').classes('text-2xl')
                                ui.label('Processing Complete').classes('text-green-600 font-semibold')

                            ui.label(f"Processed: {processing_record.processed_at.strftime('%B %d, %Y at %I:%M %p')}").classes('text-sm opacity-70')

                            with ui.row().classes('gap-6 mt-3'):
                                with ui.column().classes('gap-0'):
                                    ui.label(str(processing_record.balances_created)).classes('text-2xl font-bold text-blue-600')
                                    ui.label('Balances Created').classes('text-xs opacity-60')
                                with ui.column().classes('gap-0'):
                                    ui.label(str(processing_record.carryovers_applied)).classes('text-2xl font-bold text-purple-600')
                                    ui.label('Carryovers Applied').classes('text-xs opacity-60')
                                with ui.column().classes('gap-0'):
                                    ui.label(str(processing_record.holidays_created)).classes('text-2xl font-bold text-teal-600')
                                    ui.label('Holidays Created').classes('text-xs opacity-60')
                        else:
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('schedule', color='orange').classes('text-2xl')
                                ui.label('Pending').classes('text-orange-600 font-semibold')
                            ui.label('Year-end processing will run automatically on the first login of the new year.').classes('text-sm opacity-70')

                    # Current Year Details Card
                    with ui.card().classes('w-full p-4'):
                        ui.label(f'Current Year: {current_year}').classes('text-lg font-bold mb-2')
                        with ui.row().classes('gap-8'):
                            with ui.column():
                                ui.label(f"Active Employees: {current_status['active_users']}")
                                ui.label(f"Balances Created: {current_status['balances_created']}")
                            with ui.column():
                                ui.label(f"Pending Carryovers: {current_status['pending_carryovers']}")
                                ui.label(f"Holidays: {current_status['holidays_created']}")

                    # Next Year Preview Card
                    next_status = service.get_year_end_status(next_year)
                    next_record = service.get_processing_record(next_year)

                    with ui.card().classes('w-full p-4'):
                        ui.label(f'Next Year: {next_year}').classes('text-lg font-bold mb-2')

                        if next_record and next_record.processed:
                            ui.badge('Already Processed', color='green').classes('mb-2')
                        else:
                            ui.badge('Will process on first login', color='blue').props('outline').classes('mb-2')

                        with ui.row().classes('gap-8'):
                            with ui.column():
                                ui.label(f"Balances: {next_status['balances_created']} / {next_status['active_users']}")
                            with ui.column():
                                ui.label(f"Holidays: {next_status['holidays_created']}")

                    # Warnings about pending carryovers
                    if current_status['pending_carryovers'] > 0:
                        with ui.card().classes('w-full p-4 border-l-4 border-amber-500'):
                            ui.label(f"⚠️ {current_status['pending_carryovers']} carryover requests pending").classes('font-semibold text-amber-600')
                            ui.label("Review these before year-end to ensure they are applied correctly.").classes('text-sm')
                            ui.button('Review Carryover Requests', icon='approval',
                                      on_click=lambda: ui.navigate.to('/manager/carryover')).props('flat dense color=amber').classes('mt-2')

            finally:
                db.close()

        # Initial load
        refresh_status()

        # Action buttons
        with ui.row().classes('w-full gap-4 mt-4 justify-center'):
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'), icon='dashboard')
            ui.button('Refresh Status', on_click=refresh_status, icon='refresh')


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

        # System Status Overview - Quick health check at a glance
        db_url = config.DATABASE_URL
        if db_url.startswith('sqlite:///'):
            db_filename = db_url.replace('sqlite:///', '')
            db_path = Path(__file__).parent.parent / db_filename
        else:
            db_path = Path(__file__).parent.parent / 'tjm_calendar.db'
        db_exists = db_path.exists()

        smtp_configured = os.getenv('SMTP_HOST') is not None
        ai_configured = os.getenv('ANTHROPIC_API_KEY') is not None
        logs_dir = Path(__file__).parent.parent / 'logs'
        has_errors = (logs_dir / 'tjm_calendar_errors.log').exists() and (logs_dir / 'tjm_calendar_errors.log').stat().st_size > 0

        with ui.card().classes('w-full p-4 mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('monitor_heart', size='md', color='blue')
                    ui.label('System Health').classes('text-lg font-bold')

                with ui.row().classes('gap-6'):
                    # Database status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('storage', color='green' if db_exists else 'red')
                        ui.label('Database').classes('text-sm')
                        ui.badge('Online' if db_exists else 'Offline', color='green' if db_exists else 'red')

                    # Email status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('email', color='green' if smtp_configured else 'amber')
                        ui.label('Email').classes('text-sm')
                        ui.badge('Ready' if smtp_configured else 'Not Set', color='green' if smtp_configured else 'amber')

                    # AI status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('smart_toy', color='green' if ai_configured else 'amber')
                        ui.label('AI').classes('text-sm')
                        ui.badge('Ready' if ai_configured else 'Not Set', color='green' if ai_configured else 'amber')

                    # Errors indicator
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('error_outline', color='red' if has_errors else 'green')
                        ui.label('Errors').classes('text-sm')
                        ui.badge('Check Logs' if has_errors else 'None', color='red' if has_errors else 'green')

        # Tabs for different sections
        with ui.tabs().classes('w-full').props('dense active-color=primary indicator-color=primary') as tabs:
            database_tab = ui.tab('Database', icon='storage')
            email_tab = ui.tab('Email Config', icon='email')
            logs_tab = ui.tab('System Logs', icon='description')
            settings_tab = ui.tab('Settings', icon='tune')

        with ui.tab_panels(tabs, value=database_tab).classes('w-full'):
            # ========== DATABASE TAB ==========
            with ui.tab_panel(database_tab):
                db_size = db_path.stat().st_size / (1024 * 1024) if db_exists else 0  # MB

                # Database Status Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('storage', size='sm', color='blue')
                        ui.label('Database Status').classes('text-lg font-semibold')

                    with ui.row().classes('gap-8 flex-wrap'):
                        # Status indicator
                        with ui.column().classes('min-w-32'):
                            ui.label('Status').classes('text-xs text-gray-500 uppercase tracking-wide')
                            with ui.row().classes('items-center gap-2 mt-1'):
                                ui.icon('check_circle' if db_exists else 'error', color='green' if db_exists else 'red', size='xs')
                                ui.label('Online' if db_exists else 'Offline').classes('font-semibold')

                        # File info
                        with ui.column().classes('min-w-32'):
                            ui.label('File').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(str(db_path.name)).classes('font-mono text-sm mt-1')

                        # Size
                        with ui.column().classes('min-w-32'):
                            ui.label('Size').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(f'{db_size:.2f} MB').classes('font-mono text-sm mt-1')

                        # Location
                        with ui.column().classes('flex-1'):
                            ui.label('Location').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(str(db_path.parent)).classes('font-mono text-xs mt-1 opacity-70 truncate')

                # Backup Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('backup', size='sm', color='green')
                        ui.label('Backup Management').classes('text-lg font-semibold')

                    # Backup info box
                    with ui.row().classes('w-full gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                        with ui.column().classes('flex-1'):
                            ui.label('Backup creates a complete copy of your database').classes('text-sm')
                            with ui.row().classes('gap-4 mt-2'):
                                ui.label(f'Format: {db_path.stem}_YYYYMMDD_HHMMSS.db').classes('text-xs font-mono opacity-70')
                                ui.label('Destination: dbbackup/').classes('text-xs font-mono opacity-70')

                    backup_status = ui.label('').classes('text-sm mb-2')

                    def run_backup():
                        try:
                            backup_status.set_text('Running backup...')
                            backup_dir = Path(__file__).parent.parent / 'dbbackup'
                            backup_dir.mkdir(exist_ok=True)

                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            db_name = db_path.stem  # Get filename without extension
                            backup_file = backup_dir / f'{db_name}_{timestamp}.db'

                            import shutil
                            shutil.copy2(db_path, backup_file)

                            # Verify the backup was created and has the same size
                            if backup_file.exists() and backup_file.stat().st_size == db_path.stat().st_size:
                                backup_status.set_text(f'Backup created: {backup_file.name} ({backup_file.stat().st_size / 1024:.1f} KB)')
                                ui.notify(f'Backup successful: {backup_file.name}', type='positive')
                            else:
                                backup_status.set_text('Warning: Backup size mismatch')
                                ui.notify('Backup created but size differs from source', type='warning')

                            refresh_backups()
                        except Exception as e:
                            backup_status.set_text(f'Error: {str(e)}')
                            ui.notify(f'Backup failed: {str(e)}', type='negative')

                    ui.button('Create Backup Now', icon='backup', on_click=run_backup).props('color=primary')

                # Existing Backups Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('folder_open', size='sm', color='amber')
                            ui.label('Backup History').classes('text-lg font-semibold')
                        ui.button('Refresh', icon='refresh', on_click=lambda: refresh_backups()).props('flat dense')

                    backups_container = ui.column().classes('w-full')

                    def refresh_backups():
                        backups_container.clear()
                        backup_dir = Path(__file__).parent.parent / 'dbbackup'
                        if not backup_dir.exists():
                            with backups_container:
                                with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                                    with ui.column().classes('items-center gap-2'):
                                        ui.icon('folder_off', size='lg', color='gray')
                                        ui.label('No backups yet').classes('text-gray-500')
                                        ui.label('Create your first backup using the button above').classes('text-sm text-gray-400')
                            return

                        backup_files = sorted(backup_dir.glob('*.db'), key=lambda x: x.stat().st_mtime, reverse=True)
                        if not backup_files:
                            with backups_container:
                                with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                                    with ui.column().classes('items-center gap-2'):
                                        ui.icon('folder_off', size='lg', color='gray')
                                        ui.label('No backups found').classes('text-gray-500')
                            return

                        with backups_container:
                            # Summary row with stats
                            total_size = sum(bf.stat().st_size for bf in backup_files)
                            oldest = datetime.fromtimestamp(backup_files[-1].stat().st_mtime).strftime('%Y-%m-%d')
                            newest = datetime.fromtimestamp(backup_files[0].stat().st_mtime).strftime('%Y-%m-%d')
                            with ui.row().classes('w-full items-center justify-between p-3 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg mb-4'):
                                with ui.row().classes('items-center gap-4'):
                                    ui.icon('inventory_2', color='green')
                                    ui.label(f'{len(backup_files)} backup{"s" if len(backup_files) != 1 else ""}').classes('font-semibold')
                                with ui.row().classes('gap-6 text-sm'):
                                    ui.label(f'Total: {total_size / (1024 * 1024):.2f} MB').classes('opacity-70')
                                    ui.label(f'Oldest: {oldest}').classes('opacity-70')
                                    ui.label(f'Latest: {newest}').classes('opacity-70')

                            # Backup list with improved styling
                            for idx, bf in enumerate(backup_files):
                                size_mb = bf.stat().st_size / (1024 * 1024)
                                mtime = datetime.fromtimestamp(bf.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                is_latest = idx == 0
                                with ui.row().classes(f'w-full items-center gap-4 p-3 border rounded-lg mb-2 {"border-green-300 bg-green-50/50 dark:bg-green-900/10" if is_latest else "hover:bg-gray-50 dark:hover:bg-gray-800"}'):
                                    ui.icon('backup', color='green' if is_latest else 'blue')
                                    with ui.column().classes('flex-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(bf.name).classes('font-mono text-sm')
                                            if is_latest:
                                                ui.badge('Latest', color='green').props('dense')
                                        ui.label(f'{mtime} | {size_mb:.2f} MB').classes('text-xs opacity-70')

                                    # Action buttons
                                    with ui.row().classes('gap-1'):
                                        def create_restore_handler(backup_file):
                                            def restore():
                                                with ui.dialog() as dialog, ui.card().classes('p-6'):
                                                    ui.label('Restore Database').classes('text-lg font-semibold mb-2')
                                                    ui.label(f'Restore from: {backup_file.name}').classes('mb-2')
                                                    with ui.card().classes('w-full p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 mb-4'):
                                                        ui.label('WARNING: This will overwrite the current database!').classes('text-red-600 dark:text-red-400 font-semibold')
                                                        ui.label('Make sure to create a backup of the current database first.').classes('text-sm')

                                                    def confirm_restore():
                                                        try:
                                                            import shutil
                                                            shutil.copy2(backup_file, db_path)
                                                            ui.notify('Database restored successfully. Please restart the application.', type='positive')
                                                            dialog.close()
                                                        except Exception as e:
                                                            ui.notify(f'Restore failed: {str(e)}', type='negative')

                                                    with ui.row().classes('gap-2 justify-end'):
                                                        ui.button('Cancel', on_click=dialog.close).props('flat')
                                                        ui.button('Restore', on_click=confirm_restore, icon='restore').props('color=red')
                                                dialog.open()
                                            return restore

                                        def create_delete_handler(backup_file):
                                            def delete():
                                                with ui.dialog() as dialog, ui.card().classes('p-6'):
                                                    ui.label('Delete Backup').classes('text-lg font-semibold mb-2')
                                                    ui.label(f'Delete: {backup_file.name}').classes('mb-2')
                                                    ui.label('This action cannot be undone.').classes('text-sm opacity-70 mb-4')

                                                    def confirm_delete():
                                                        try:
                                                            backup_file.unlink()
                                                            ui.notify(f'Deleted: {backup_file.name}', type='positive')
                                                            dialog.close()
                                                            refresh_backups()
                                                        except Exception as e:
                                                            ui.notify(f'Delete failed: {str(e)}', type='negative')

                                                    with ui.row().classes('gap-2 justify-end'):
                                                        ui.button('Cancel', on_click=dialog.close).props('flat')
                                                        ui.button('Delete', on_click=confirm_delete, icon='delete').props('color=red')
                                                dialog.open()
                                            return delete

                                        ui.button(icon='restore', on_click=create_restore_handler(bf)).props('flat dense').tooltip('Restore this backup')
                                        ui.button(icon='delete', on_click=create_delete_handler(bf)).props('flat dense color=red').tooltip('Delete this backup')

                    refresh_backups()

                # Market Calendar Sync Card
                with ui.card().classes('w-full p-4 mt-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('event', size='sm', color='purple')
                        ui.label('Market Calendar Sync').classes('text-lg font-semibold')

                    ui.label('Sync market holidays for NYSE, CME, and CBOE exchanges.').classes('text-sm opacity-70 mb-4')

                    # Current year and next year
                    current_year = datetime.now().year
                    sync_status_label = ui.label('').classes('text-sm mb-2')
                    sync_results_container = ui.column().classes('w-full')

                    def sync_market_holidays(year: int):
                        """Sync market holidays for a specific year."""
                        sync_status_label.set_text(f'Syncing {year} holidays...')
                        try:
                            from src.services.market_calendar_service import MarketCalendarService
                            service = MarketCalendarService(db_session=db)
                            result = service.sync_market_holidays(year)

                            if result.success:
                                source_display = result.source.value.replace('_', ' ').title()
                                msg = f'{year}: Synced {result.count} holidays from {source_display}'
                                if result.warning:
                                    msg += f' (Warning: {result.warning})'
                                    ui.notify(msg, type='warning')
                                else:
                                    ui.notify(msg, type='positive')
                                sync_status_label.set_text(msg)
                            else:
                                ui.notify(f'Sync failed: {result.error}', type='negative')
                                sync_status_label.set_text(f'Error: {result.error}')

                            refresh_holiday_stats()
                        except Exception as e:
                            sync_status_label.set_text(f'Error: {str(e)}')
                            ui.notify(f'Sync error: {str(e)}', type='negative')

                    def refresh_holiday_stats():
                        """Refresh the holiday statistics display."""
                        sync_results_container.clear()
                        try:
                            from src.models.market_holiday import MarketHoliday
                            with sync_results_container:
                                # Show stats for current and next year
                                for year in [current_year, current_year + 1]:
                                    count = db.query(MarketHoliday).filter(MarketHoliday.year == year).count()
                                    markets = db.query(MarketHoliday.market).filter(
                                        MarketHoliday.year == year
                                    ).distinct().all()
                                    market_list = ', '.join([m[0] for m in markets]) if markets else 'None'

                                    color = 'green' if count > 0 else 'gray'
                                    with ui.row().classes(f'w-full items-center gap-4 p-3 bg-{color}-50 dark:bg-{color}-900/20 rounded-lg mb-2'):
                                        ui.icon('calendar_month', color=color)
                                        with ui.column().classes('flex-1'):
                                            ui.label(f'{year}').classes('font-semibold')
                                            ui.label(f'{count} holidays | Markets: {market_list}').classes('text-xs opacity-70')
                                        ui.button('Sync', icon='sync', on_click=lambda y=year: sync_market_holidays(y)).props('flat dense')
                        except Exception as e:
                            with sync_results_container:
                                ui.label(f'Error loading stats: {e}').classes('text-red-500')

                    # Sync buttons
                    with ui.row().classes('gap-2 mb-4'):
                        ui.button(f'Sync {current_year}', icon='sync', on_click=lambda: sync_market_holidays(current_year)).props('color=primary')
                        ui.button(f'Sync {current_year + 1}', icon='sync', on_click=lambda: sync_market_holidays(current_year + 1)).props('color=secondary')

                    refresh_holiday_stats()

            # ========== EMAIL CONFIG TAB ==========
            with ui.tab_panel(email_tab):
                # Current config values
                smtp_host = os.getenv('SMTP_HOST', '')
                smtp_port = os.getenv('SMTP_PORT', '')
                smtp_user = os.getenv('SMTP_USER', '')
                smtp_from = os.getenv('SMTP_FROM', '')
                email_configured = bool(smtp_host)

                # Status Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('email', size='sm', color='blue')
                        ui.label('Email Service Status').classes('text-lg font-semibold')

                    # Status banner
                    if email_configured:
                        with ui.row().classes('w-full p-4 bg-green-50 dark:bg-green-900/20 rounded-lg items-center gap-3'):
                            ui.icon('check_circle', color='green', size='md')
                            with ui.column().classes('flex-1'):
                                ui.label('Email service is configured').classes('font-semibold text-green-700 dark:text-green-400')
                                ui.label('Your application can send notification emails').classes('text-sm opacity-70')
                    else:
                        with ui.row().classes('w-full p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg items-center gap-3'):
                            ui.icon('warning', color='amber', size='md')
                            with ui.column().classes('flex-1'):
                                ui.label('Email service not configured').classes('font-semibold text-amber-700 dark:text-amber-400')
                                ui.label('Configure SMTP settings to enable email notifications').classes('text-sm opacity-70')

                # Configuration Details Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings', size='sm', color='gray')
                        ui.label('SMTP Configuration').classes('text-lg font-semibold')

                    with ui.row().classes('gap-8 flex-wrap'):
                        with ui.column().classes('min-w-40'):
                            ui.label('Host').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_host or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_host else ""}')

                        with ui.column().classes('min-w-20'):
                            ui.label('Port').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_port or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_port else ""}')

                        with ui.column().classes('min-w-40'):
                            ui.label('User').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_user or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_user else ""}')

                        with ui.column().classes('flex-1'):
                            ui.label('From Address').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_from or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_from else ""}')

                # Test Email Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('send', size='sm', color='green')
                        ui.label('Test Email').classes('text-lg font-semibold')

                    ui.label('Send a test email to verify your configuration').classes('text-sm opacity-70 mb-4')

                    with ui.row().classes('items-center gap-4'):
                        test_email_input = ui.input(placeholder='Enter recipient email address').props('outlined dense').classes('w-80')

                        def send_test_email():
                            if not test_email_input.value:
                                ui.notify('Please enter an email address', type='warning')
                                return
                            if not email_configured:
                                ui.notify('SMTP not configured. Set environment variables first.', type='negative')
                                return

                            ui.notify('Sending test email...', type='info')
                            try:
                                from src.services.email_service import email_service
                                success = email_service.send_email(
                                    to_email=test_email_input.value,
                                    subject='TJM Calendar - Test Email',
                                    body='This is a test email from the TJM Time Calendar system.\n\nIf you received this, your email configuration is working correctly!'
                                )
                                if success:
                                    ui.notify('Test email sent successfully!', type='positive')
                                else:
                                    ui.notify('Failed to send email - check logs', type='negative')
                            except Exception as e:
                                ui.notify(f'Error: {str(e)}', type='negative')

                        ui.button('Send Test', icon='send', on_click=send_test_email).props('color=primary')

                # Setup Guide Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('help_outline', size='sm', color='blue')
                        ui.label('Setup Guide').classes('text-lg font-semibold')

                    with ui.expansion('How to Configure Email', icon='menu_book').classes('w-full'):
                        ui.markdown('''
**Add these to your `.env` file:**

```
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@company.com
```

**Common SMTP Providers:**

| Provider | Host | Port |
|----------|------|------|
| Gmail | smtp.gmail.com | 587 |
| Microsoft 365 | smtp.office365.com | 587 |
| Amazon SES | email-smtp.us-east-1.amazonaws.com | 587 |

*Restart the application after updating `.env`*
                        ''')

            # ========== LOGS TAB ==========
            with ui.tab_panel(logs_tab):
                # Log file paths (reuse logs_dir from status overview)
                main_log_path = logs_dir / 'tjm_calendar.log'
                error_log_path = logs_dir / 'tjm_calendar_errors.log'

                # State for current log and AI analysis
                log_state = {'current_log': 'main', 'current_content': ''}

                # Log Files Overview Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('description', size='sm', color='blue')
                        ui.label('Log Files').classes('text-lg font-semibold')

                    # Container for log file cards (will be refreshed dynamically)
                    log_cards_container = ui.row().classes('w-full gap-4')

                    def refresh_log_cards():
                        """Refresh the log file cards with current sizes."""
                        log_cards_container.clear()

                        # Get current file info
                        main_exists = main_log_path.exists()
                        main_size = main_log_path.stat().st_size / 1024 if main_exists else 0
                        error_exists = error_log_path.exists()
                        error_size = error_log_path.stat().st_size / 1024 if error_exists else 0

                        with log_cards_container:
                            # Main log card
                            def switch_to_main():
                                log_state['current_log'] = 'main'
                                refresh_logs()
                                refresh_log_cards()
                                ai_analysis_container.clear()
                                ai_analysis_container.set_visibility(False)

                            with ui.card().classes('p-4 cursor-pointer hover:shadow-md transition-shadow flex-1').on('click', switch_to_main):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('article', color='blue', size='md')
                                    with ui.column().classes('flex-1'):
                                        ui.label('Application Log').classes('font-semibold')
                                        ui.label('General application events and info').classes('text-xs opacity-70')
                                    with ui.column().classes('items-end'):
                                        ui.label(f'{main_size:.1f} KB').classes('font-mono text-sm')
                                        ui.badge('Active' if main_exists and main_size > 0 else 'Empty', color='green' if main_exists and main_size > 0 else 'gray').props('dense')

                            # Error log card
                            def switch_to_errors():
                                log_state['current_log'] = 'errors'
                                refresh_logs()
                                refresh_log_cards()
                                ai_analysis_container.clear()
                                ai_analysis_container.set_visibility(False)

                            error_has_content = error_exists and error_size > 0
                            with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow flex-1 {"border-red-300 border-2" if error_has_content else ""}').on('click', switch_to_errors):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('error_outline', color='red', size='md')
                                    with ui.column().classes('flex-1'):
                                        ui.label('Error Log').classes('font-semibold')
                                        ui.label('Errors and exceptions only').classes('text-xs opacity-70')
                                    with ui.column().classes('items-end'):
                                        ui.label(f'{error_size:.1f} KB').classes('font-mono text-sm')
                                        if error_has_content:
                                            ui.badge('Has Errors', color='red').props('dense')
                                        else:
                                            ui.badge('Clear', color='green').props('dense')

                    # Initial render
                    refresh_log_cards()

                # Log Viewer Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('terminal', size='sm', color='gray')
                            current_log_label = ui.label('Viewing: Application Log').classes('text-lg font-semibold')

                        def refresh_all():
                            refresh_logs()
                            refresh_log_cards()

                        with ui.row().classes('gap-2'):
                            ui.button('Refresh', icon='refresh', on_click=refresh_all).props('flat dense')

                    # Log viewer (tall to fill the viewing area)
                    log_display = ui.textarea('').props('outlined readonly').classes('w-full font-mono text-xs bg-gray-50 dark:bg-gray-900').style('height: 380px;')

                    def get_current_log_path():
                        return error_log_path if log_state['current_log'] == 'errors' else main_log_path

                    def refresh_logs(lines=100):
                        log_path = get_current_log_path()
                        # Update the label
                        if log_state['current_log'] == 'errors':
                            current_log_label.set_text('Viewing: Error Log')
                        else:
                            current_log_label.set_text('Viewing: Application Log')

                        if not log_path.exists():
                            log_display.value = 'Log file not found. Logs will appear after application activity.'
                            log_state['current_content'] = ''
                            return
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                                all_lines = f.readlines()
                                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                                content = ''.join(recent)
                                log_display.value = content
                                log_state['current_content'] = content
                        except Exception as e:
                            log_display.value = f'Error reading log: {str(e)}'
                            log_state['current_content'] = ''

                    # Controls row
                    with ui.row().classes('w-full justify-between items-center mt-3'):
                        with ui.row().classes('gap-2'):
                            ui.label('Show:').classes('text-sm opacity-70')
                            ui.button('50 lines', on_click=lambda: refresh_logs(50)).props('flat dense size=sm')
                            ui.button('100 lines', on_click=lambda: refresh_logs(100)).props('flat dense size=sm')
                            ui.button('500 lines', on_click=lambda: refresh_logs(500)).props('flat dense size=sm')

                        def clear_current_log():
                            log_path = get_current_log_path()
                            if log_path.exists():
                                try:
                                    with open(log_path, 'w') as f:
                                        f.write('')
                                    ui.notify('Log cleared', type='positive')
                                    refresh_logs()
                                    refresh_log_cards()  # Update the file size display
                                except Exception as e:
                                    ui.notify(f'Error: {str(e)}', type='negative')

                        ui.button('Clear Log', icon='delete_sweep', on_click=clear_current_log).props('flat dense color=red')

                    refresh_logs()

                # AI Analysis Section
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('smart_toy', size='sm', color='purple')
                        ui.label('AI Log Analysis').classes('text-lg font-semibold')
                        if ai_configured:
                            ui.badge('Ready', color='green').props('dense')
                        else:
                            ui.badge('Not Configured', color='amber').props('dense')

                    ui.label('Get an AI-powered summary of your logs or analyze specific sections.').classes('text-sm opacity-70 mb-4')

                    # Two equal cards - using table layout for perfect alignment
                    with ui.element('div').style('display: table; width: 100%; table-layout: fixed;'):
                        with ui.element('div').style('display: table-row;'):
                            # Full log analysis card (left cell)
                            with ui.element('div').style('display: table-cell; width: 50%; padding-right: 8px; vertical-align: top;'):
                                with ui.card().classes('w-full p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20').style('height: 240px;'):
                                    with ui.column().classes('h-full'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('analytics', color='blue')
                                            ui.label('Full Log Analysis').classes('font-semibold')
                                        ui.label('Analyze the entire visible log content').classes('text-xs opacity-70 mb-2')
                                        # Spacer to match the textarea height in the right card
                                        ui.element('div').classes('flex-grow').style('min-height: 56px;')

                                        def analyze_full_log():
                                            if not log_state['current_content']:
                                                ui.notify('No log content to analyze', type='warning')
                                                return
                                            run_ai_analysis(log_state['current_content'], is_selection=False)

                                        ui.button('Analyze Log', icon='play_arrow', on_click=analyze_full_log).props('color=primary')

                            # Selection analysis card (right cell)
                            with ui.element('div').style('display: table-cell; width: 50%; padding-left: 8px; vertical-align: top;'):
                                with ui.card().classes('w-full p-4 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20').style('height: 240px;'):
                                    with ui.column().classes('h-full'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('highlight_alt', color='purple')
                                            ui.label('Selection Analysis').classes('font-semibold')
                                        ui.label('Paste a specific section for focused analysis').classes('text-xs opacity-70 mb-2')
                                        selection_input = ui.textarea(
                                            placeholder='Paste log content here...'
                                        ).classes('w-full').props('outlined dense rows=2').style('width: 100%;')

                                        def analyze_selection():
                                            if not selection_input.value.strip():
                                                ui.notify('Please paste some log content to analyze', type='warning')
                                                return
                                            run_ai_analysis(selection_input.value.strip(), is_selection=True)

                                        ui.button('Analyze Selection', icon='psychology', on_click=analyze_selection).props('color=secondary')

                    # AI Analysis results container
                    ai_analysis_container = ui.column().classes('w-full')
                    ai_analysis_container.set_visibility(False)

                    def run_ai_analysis(content: str, is_selection: bool = False):
                        """Run AI analysis on log content."""
                        ai_analysis_container.clear()
                        ai_analysis_container.set_visibility(True)

                        # Show loading state
                        with ai_analysis_container:
                            with ui.card().classes('w-full p-4 border-l-4 border-blue-500'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.spinner('dots', size='sm')
                                    ui.label('Analyzing logs... This may take a moment.').classes('text-sm')

                        try:
                            import anthropic
                            api_key = os.getenv('ANTHROPIC_API_KEY')

                            if not api_key:
                                ai_analysis_container.clear()
                                with ai_analysis_container:
                                    with ui.card().classes('w-full p-4 border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20'):
                                        ui.label('AI Analysis Unavailable').classes('font-semibold text-amber-700 dark:text-amber-400')
                                        ui.label('ANTHROPIC_API_KEY not configured in .env file.').classes('text-sm')
                                return

                            client = anthropic.Anthropic(api_key=api_key)

                            # Truncate if too long
                            max_chars = 8000
                            truncated = False
                            analysis_content = content
                            if len(analysis_content) > max_chars:
                                analysis_content = analysis_content[-max_chars:]
                                truncated = True

                            context = "a specific selection from the" if is_selection else "the recent"

                            prompt = f"""Analyze {context} application log below and provide a concise summary for a system administrator.

Your analysis should include:
1. **Overview**: Brief summary of what's happening in the log (1-2 sentences)
2. **Key Events**: Important events or activities (logins, requests, database operations)
3. **Errors/Warnings**: Any errors, warnings, or concerning patterns (highlight severity)
4. **Recommendations**: Any suggested actions if issues are found

Keep it concise and actionable. Use bullet points. If the log shows normal operation with no issues, say so briefly.

{"Note: Log was truncated to last " + str(max_chars) + " characters." if truncated else ""}

LOG CONTENT:
{analysis_content}"""

                            response = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1024,
                                messages=[{"role": "user", "content": prompt}]
                            )

                            analysis_text = response.content[0].text

                            ai_analysis_container.clear()
                            with ai_analysis_container:
                                with ui.card().classes('w-full p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-900/10'):
                                    with ui.row().classes('w-full justify-between items-center mb-3'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('check_circle', color='green')
                                            ui.label('AI Analysis Complete').classes('font-semibold text-green-700 dark:text-green-400')
                                        ui.label(f'{"Selection" if is_selection else "Full Log"} Analysis').classes('text-xs opacity-60')

                                    ui.markdown(analysis_text).classes('text-sm')

                                    with ui.row().classes('w-full justify-end mt-3'):
                                        ui.button('Close', icon='close', on_click=lambda: ai_analysis_container.set_visibility(False)).props('flat dense')

                            ui.notify('Analysis complete', type='positive')

                        except Exception as e:
                            ai_analysis_container.clear()
                            with ai_analysis_container:
                                with ui.card().classes('w-full p-4 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20'):
                                    ui.label('Analysis Failed').classes('font-semibold text-red-700 dark:text-red-400')
                                    ui.label(f'Error: {str(e)}').classes('text-sm')
                            ui.notify(f'Analysis failed: {str(e)}', type='negative')

            # ========== SETTINGS TAB ==========
            with ui.tab_panel(settings_tab):
                import platform
                import sys as sys_module

                # Security Settings Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('security', size='sm', color='blue')
                        ui.label('Security Settings').classes('text-lg font-semibold')

                    debug_val = os.getenv('DEBUG', 'false')
                    secret = os.getenv('SECRET_KEY', '')
                    timeout = os.getenv('SESSION_TIMEOUT_MINUTES', '30')

                    with ui.row().classes('gap-4 flex-wrap'):
                        # Debug Mode
                        with ui.card().classes(f'p-4 flex-1 min-w-48 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if debug_val.lower() == "true" else "bg-green-50 dark:bg-green-900/20"}'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('bug_report', color='red' if debug_val.lower() == 'true' else 'green')
                                ui.label('Debug Mode').classes('font-semibold')
                            if debug_val.lower() == 'true':
                                ui.badge('ENABLED', color='red')
                                ui.label('Disable in production!').classes('text-xs text-red-600 dark:text-red-400 mt-1')
                            else:
                                ui.badge('Disabled', color='green')
                                ui.label('Production ready').classes('text-xs opacity-70 mt-1')

                        # Secret Key
                        with ui.card().classes(f'p-4 flex-1 min-w-48 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if not (secret and len(secret) > 20) else "bg-green-50 dark:bg-green-900/20"}'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('key', color='green' if secret and len(secret) > 20 else 'red')
                                ui.label('Secret Key').classes('font-semibold')
                            if secret and len(secret) > 20:
                                ui.badge('Configured', color='green')
                                ui.label(f'{len(secret)} characters').classes('text-xs opacity-70 mt-1')
                            else:
                                ui.badge('Weak/Missing', color='red')
                                ui.label('Set a strong key in .env').classes('text-xs text-red-600 dark:text-red-400 mt-1')

                        # Session Timeout
                        with ui.card().classes('p-4 flex-1 min-w-48 bg-gray-50 dark:bg-gray-800'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('timer', color='blue')
                                ui.label('Session Timeout').classes('font-semibold')
                            ui.label(f'{timeout} minutes').classes('font-mono text-lg')
                            ui.label('User inactivity limit').classes('text-xs opacity-70 mt-1')

                # Environment Variables Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings_applications', size='sm', color='amber')
                        ui.label('Environment Configuration').classes('text-lg font-semibold')

                    # Environment vars as a cleaner table
                    env_vars = [
                        ('SECRET_KEY', os.getenv('SECRET_KEY'), 'Security', 'key'),
                        ('DEBUG', os.getenv('DEBUG', 'false'), 'Development', 'bug_report'),
                        ('DATABASE_URL', os.getenv('DATABASE_URL'), 'Database', 'storage'),
                        ('SMTP_HOST', os.getenv('SMTP_HOST'), 'Email', 'email'),
                        ('ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY'), 'AI', 'smart_toy'),
                        ('LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO'), 'Logging', 'description'),
                    ]

                    with ui.element('div').classes('w-full rounded-lg overflow-hidden border'):
                        for i, (var_name, var_val, category, icon) in enumerate(env_vars):
                            is_set = bool(var_val)
                            display_val = 'Configured' if var_val and var_name in ['SECRET_KEY', 'ANTHROPIC_API_KEY', 'DATABASE_URL'] else (var_val or 'Not set')
                            with ui.row().classes(f'w-full justify-between items-center p-3 {"bg-gray-50 dark:bg-gray-800" if i % 2 == 0 else ""}'):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon(icon, color='green' if is_set else 'gray', size='xs')
                                    with ui.column():
                                        ui.label(var_name).classes('font-mono text-sm')
                                        ui.label(category).classes('text-xs opacity-50')
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(display_val).classes(f'text-sm {"font-mono" if var_val else "opacity-50"}')
                                    ui.icon('check_circle' if is_set else 'cancel', color='green' if is_set else 'gray', size='xs')

                # System Information Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('computer', size='sm', color='gray')
                        ui.label('System Information').classes('text-lg font-semibold')

                    with ui.row().classes('gap-4 flex-wrap'):
                        # Python
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-blue-50 dark:bg-blue-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('code', color='blue')
                                ui.label('Python').classes('font-semibold')
                            ui.label(sys_module.version.split()[0]).classes('font-mono text-lg')

                        # Platform
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-green-50 dark:bg-green-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('laptop', color='green')
                                ui.label('Platform').classes('font-semibold')
                            ui.label(platform.system()).classes('font-mono text-lg')

                        # Architecture
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-purple-50 dark:bg-purple-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('memory', color='purple')
                                ui.label('Architecture').classes('font-semibold')
                            ui.label(platform.machine()).classes('font-mono text-lg')

                        # NiceGUI Version
                        try:
                            import nicegui
                            nicegui_version = nicegui.__version__
                        except Exception:
                            nicegui_version = 'Unknown'

                        with ui.card().classes('p-4 flex-1 min-w-40 bg-amber-50 dark:bg-amber-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('web', color='amber')
                                ui.label('NiceGUI').classes('font-semibold')
                            ui.label(nicegui_version).classes('font-mono text-lg')

        # Back button
        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat')


# ============================================================
# CALENDAR EXPORT ENDPOINT
# ============================================================
from fastapi.responses import Response

@app.get('/api/calendar/export')
def export_calendar(
    type: str = 'my',  # 'my', 'team', 'holidays'
    year: int = None,
    department_id: int = None
):
    """
    Export calendar to iCal (.ics) format.

    Args:
        type: 'my' for personal, 'team' for department, 'holidays' for market holidays only
        year: Year to export (defaults to current year)
        department_id: Department ID for team exports (admin only)
    """
    from datetime import date
    from src.services.ical_export_service import ICalExportService

    # Get current user from session
    user = app.storage.general.get('user')
    if not user:
        return Response(content="Unauthorized", status_code=401)

    user_id = user.get('id')
    user_role = user.get('role')

    if year is None:
        year = date.today().year

    db = next(get_db())
    try:
        service = ICalExportService(db_session=db)

        if type == 'holidays':
            ical_content = service.generate_holidays_only(year)
            filename = f"market_holidays_{year}.ics"
        elif type == 'team':
            if user_role not in ['manager', 'admin', 'superadmin']:
                return Response(content="Forbidden", status_code=403)

            # For managers, use their department
            if user_role == 'manager':
                from src.services.user_service import UserService
                user_service = UserService(db)
                manager = user_service.get_user_by_id(user_id)
                dept_id = manager.department_id if manager else None
                dept_name = manager.department.name if manager and manager.department else "Team"
            else:
                # Admin/superadmin can specify department
                dept_id = department_id
                if dept_id:
                    from src.models.department import Department
                    dept = db.query(Department).filter(Department.id == dept_id).first()
                    dept_name = dept.name if dept else "Team"
                else:
                    dept_name = "All Departments"

            ical_content = service.generate_team_calendar(dept_id, year, dept_name)
            filename = f"team_calendar_{year}.ics"
        else:  # 'my'
            ical_content = service.generate_my_calendar(user_id, year)
            filename = f"my_pto_calendar_{year}.ics"

        return Response(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    finally:
        db.close()


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
