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
from nicegui_app.pages.manager_team import manager_team_page
from nicegui_app.pages.requests import requests_page, cancel_user_request
from nicegui_app.pages.manager_request_detail import manager_request_detail_page
from nicegui_app.pages.admin_dashboard import admin_dashboard_page
from nicegui_app.pages.admin_departments import admin_departments_page
from nicegui_app.pages.admin_approvals import admin_approvals_page
from nicegui_app.pages.admin_employees import admin_employees_list_page, admin_employees_add_page, admin_employees_edit_page
from nicegui_app.pages.admin_handbook import admin_handbook_page
from nicegui_app.pages.admin_year_end import admin_year_end_page
from nicegui_app.pages.help import help_page as help_page_content
from nicegui_app.pages.admin_system import admin_system_page
from nicegui_app.logo import LOGO_DATA_URL
from nicegui_app.components.theme import apply_dark_mode, validate_required, validate_email, validate_min_length
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

@ui.page('/manager/team')
def manager_team():
    """Manager team management page."""
    if not require_auth():
        return
    manager_team_page()

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

@ui.page('/analytics')
def analytics():
    """Analytics dashboard for managers and admins."""
    if not require_auth():
        return
    from nicegui_app.pages.analytics import analytics_page
    analytics_page()

@ui.page('/requests')
def requests():
    """User's PTO request history page with filtering and cancel functionality."""
    if not require_auth():
        return
    requests_page()

@ui.page('/manager/request/{request_id}')
def manager_request_detail(request_id: int):
    """Request detail page for approval/denial"""
    if not require_auth():
        return
    manager_request_detail_page(request_id)

@ui.page('/admin')
def admin_panel():
    """Admin panel landing page with navigation to admin functions."""
    if not require_auth():
        return
    admin_dashboard_page()

@ui.page('/admin/departments')
def admin_departments():
    """Admin page for managing departments with dropdown filter and table display."""
    if not require_auth():
        return
    admin_departments_page()

@ui.page('/admin/approvals')
def admin_approvals():
    """Admin page for viewing and approving all pending PTO requests."""
    if not require_auth():
        return
    admin_approvals_page()


@ui.page('/admin/employees')
def admin_employees():
    """Admin page for managing employees."""
    if not require_auth():
        return
    admin_employees_list_page()


@ui.page('/admin/employees/add')
def admin_employees_add():
    """Admin page for adding a new employee."""
    if not require_auth():
        return
    admin_employees_add_page()


@ui.page('/admin/employees/edit/{user_id}')
def admin_employees_edit(user_id: int):
    """Admin page for editing an existing employee."""
    if not require_auth():
        return
    admin_employees_edit_page(user_id)


@ui.page('/admin/handbook')
def admin_handbook():
    """Admin page for managing employee handbook revisions."""
    if not require_auth():
        return
    admin_handbook_page()


@ui.page('/admin/year-end')
def admin_year_end():
    """Admin page for year-end processing status (automatic processing)."""
    if not require_auth():
        return
    admin_year_end_page()


@ui.page('/help')
def help_page():
    """Help documentation page with searchable chapters."""
    if not require_auth():
        return
    help_page_content()


@ui.page('/admin/system')
def admin_system():
    """Super Admin system administration page."""
    if not require_auth():
        return
    admin_system_page()


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
    ui.run(
        port=8080,
        host='0.0.0.0',
        storage_secret=config.SECRET_KEY,
        uvicorn_logging_level='warning'
    )
