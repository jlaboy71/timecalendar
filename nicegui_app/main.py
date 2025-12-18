from nicegui import ui, app
import sys
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
from nicegui_app.pages.manager_settings import manager_settings_page
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
from nicegui_app.pages.admin_email_preview import email_preview_page
from nicegui_app.pages.admin_auto_notify_reports import auto_notify_reports_page
from nicegui_app.logo import LOGO_DATA_URL
from nicegui_app.components.theme import apply_dark_mode
from src.services.session_manager import require_auth
from src.services.email_service import email_service

# Ensure all database tables exist (creates any missing tables)
init_db()

# Set up basic app configuration
app.title = "TJM Time Calendar"

# Add static file serving for logo
STATIC_DIR = Path(__file__).parent / 'static'
app.add_static_files('/static', STATIC_DIR)

# HTTPS redirect middleware for production
if config.is_production and config.ssl_enabled:
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)
    logger.info("HTTPS redirect middleware enabled for production")

# Security headers middleware - always enabled
from src.middleware.security import add_security_headers
add_security_headers(app)
logger.info("Security headers middleware enabled")


# Global exception handler middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
from src.services.monitoring_service import MonitoringService

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global exception handler that logs errors and returns user-friendly messages.

    Does not expose stack traces to users in production.
    """
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Get user context if available
            user_context = None
            try:
                user = app.storage.user.get('user')
                if user:
                    user_context = {
                        'user_id': user.get('id'),
                        'username': user.get('username'),
                        'role': user.get('role')
                    }
            except Exception:
                pass

            # Log and alert using monitoring service
            monitoring = MonitoringService()
            monitoring.log_exception(
                exception=e,
                context=f"Request to {request.url.path}",
                user_context=user_context,
                send_alert=True
            )

            # Return user-friendly error page
            error_html = """
            <!DOCTYPE html>
            <html>
            <head><title>Error - TJM Time Calendar</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #5a6a72;">Something went wrong</h1>
                <p>We encountered an unexpected error processing your request.</p>
                <p>Our team has been notified and is working to fix the issue.</p>
                <p><a href="/dashboard" style="color: #c9a227;">Return to Dashboard</a></p>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=500)

app.add_middleware(ExceptionHandlerMiddleware)
logger.info("Global exception handler middleware enabled")


# Health check endpoint for monitoring
from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from sqlalchemy import text

@app.get('/health')
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        JSON with application health status including database connectivity.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'database': 'unknown'
    }

    # Test database connectivity
    try:
        db = next(get_db())
        try:
            # Simple query to verify connection
            db.execute(text('SELECT 1'))
            health_status['database'] = 'connected'
        finally:
            db.close()
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['database'] = 'error'
        health_status['database_error'] = str(e)
        return JSONResponse(content=health_status, status_code=503)

    return JSONResponse(content=health_status, status_code=200)


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

@ui.page('/submit-request/{pto_type}')
def submit_request_with_type(pto_type: str):
    """PTO Request submission page with pre-selected type."""
    if not require_auth():
        return
    request_form_page(preselect_type=pto_type)

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

@ui.page('/manager/settings')
def manager_settings():
    """Manager notification settings page."""
    if not require_auth():
        return
    manager_settings_page()

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


@ui.page('/admin/email-preview')
def admin_email_preview():
    """Admin email template preview page."""
    if not require_auth():
        return
    email_preview_page()


@ui.page('/admin/auto-notify-reports')
def admin_auto_notify_reports():
    """Auto-notify reports page for managers and admins."""
    if not require_auth():
        return
    auto_notify_reports_page()


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
    user = app.storage.user.get('user')
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


# ============================================================
# TEAM PTO REPORT EXPORT ENDPOINT
# ============================================================
@app.get('/api/reports/team-pto')
def export_team_pto_report(
    start: str = None,
    end: str = None,
    format: str = 'pdf'
):
    """
    Export team PTO report for managers.

    Args:
        start: Start date (ISO format)
        end: End date (ISO format)
        format: Export format ('pdf', 'csv', 'html')
    """
    from datetime import date, datetime, timedelta
    from sqlalchemy import select, and_
    from src.models.pto_request import PTORequest
    from src.models.user import User
    from src.services.export_service import ExportService
    import csv
    from io import StringIO

    # Get current user from session
    user = app.storage.user.get('user')
    if not user:
        return Response(content="Unauthorized", status_code=401)

    user_id = user.get('id')
    user_role = user.get('role')

    if user_role not in ['manager', 'admin', 'superadmin']:
        return Response(content="Forbidden", status_code=403)

    # Parse dates
    today = date.today()
    try:
        start_date = date.fromisoformat(start) if start else today - timedelta(days=30)
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        return Response(content="Invalid date format", status_code=400)

    db = next(get_db())
    try:
        # Get manager's department
        manager = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not manager:
            return Response(content="User not found", status_code=404)

        # Get team members (for managers, their department; for admins, all)
        if user_role == 'manager':
            if not manager.department_id:
                return Response(content="No department assigned", status_code=400)
            team_stmt = select(User.id).where(User.department_id == manager.department_id)
        else:
            team_stmt = select(User.id)

        team_ids = [r[0] for r in db.execute(team_stmt).fetchall()]

        # Get PTO requests in date range
        requests_stmt = select(PTORequest).where(
            and_(
                PTORequest.user_id.in_(team_ids),
                PTORequest.start_date >= start_date,
                PTORequest.end_date <= end_date
            )
        ).order_by(PTORequest.start_date.desc())

        requests = db.execute(requests_stmt).scalars().all()

        # Generate report based on format
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Employee', 'Type', 'Start Date', 'End Date', 'Days', 'Status', 'Trusted'])
            for req in requests:
                writer.writerow([
                    req.user.full_name,
                    req.pto_type.title(),
                    req.start_date.isoformat(),
                    req.end_date.isoformat(),
                    float(req.total_days),
                    req.status.title(),
                    'Yes' if req.user.is_trusted else 'No'
                ])
            content = output.getvalue()
            filename = f"team_pto_report_{start_date}_{end_date}.csv"
            media_type = "text/csv"

        elif format == 'html':
            rows = ""
            for req in requests:
                trusted_badge = '<span style="color: #22c55e;">✓</span> ' if req.user.is_trusted else ''
                status_color = '#22c55e' if req.status == 'approved' else '#f59e0b' if req.status == 'pending' else '#ef4444'
                rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{trusted_badge}{req.user.full_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.pto_type.title()}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.start_date.strftime('%b %d, %Y')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.end_date.strftime('%b %d, %Y')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{req.total_days}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: {status_color};">{req.status.title()}</td>
                </tr>
                """
            content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Team PTO Report</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="background-color: #5a6a72; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">Team PTO Report</h1>
                </div>
                <div style="padding: 20px;">
                    <p><strong>Period:</strong> {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}</p>
                    <p><strong>Total Requests:</strong> {len(requests)}</p>
                    <table style="border-collapse: collapse; width: 100%; margin-top: 15px;">
                        <tr style="background-color: #c9a227; color: white;">
                            <th style="padding: 10px; text-align: left;">Employee</th>
                            <th style="padding: 10px; text-align: left;">Type</th>
                            <th style="padding: 10px; text-align: left;">Start</th>
                            <th style="padding: 10px; text-align: left;">End</th>
                            <th style="padding: 10px; text-align: center;">Days</th>
                            <th style="padding: 10px; text-align: left;">Status</th>
                        </tr>
                        {rows}
                    </table>
                </div>
            </body>
            </html>
            """
            filename = f"team_pto_report_{start_date}_{end_date}.html"
            media_type = "text/html"

        else:  # PDF
            # Generate HTML first, then convert to PDF
            rows = ""
            for req in requests:
                trusted_badge = '✓ ' if req.user.is_trusted else ''
                rows += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{trusted_badge}{req.user.full_name}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.pto_type.title()}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.start_date.strftime('%b %d')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.end_date.strftime('%b %d')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{req.total_days}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{req.status.title()}</td>
                </tr>
                """
            html_content = f"""
            <h2>Team PTO Report</h2>
            <p><strong>Period:</strong> {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}</p>
            <p><strong>Total Requests:</strong> {len(requests)}</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #c9a227; color: white;">
                    <th style="padding: 8px;">Employee</th>
                    <th style="padding: 8px;">Type</th>
                    <th style="padding: 8px;">Start</th>
                    <th style="padding: 8px;">End</th>
                    <th style="padding: 8px;">Days</th>
                    <th style="padding: 8px;">Status</th>
                </tr>
                {rows}
            </table>
            """
            content = ExportService.generate_report_pdf(html_content, "Team PTO Report")
            filename = f"team_pto_report_{start_date}_{end_date}.pdf"
            media_type = "application/pdf"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    finally:
        db.close()


# ============================================================
# NOTIFICATION DIGEST SCHEDULER
# ============================================================
import os
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize scheduler
digest_scheduler = BackgroundScheduler()

def process_notification_digests():
    """Hourly job to check and send digest emails."""
    from src.services.notification_service import NotificationService

    db = next(get_db())
    try:
        service = NotificationService(db)
        service.process_digests()
        logger.debug("Digest processing completed")
    except Exception as e:
        logger.error(f"Digest processing failed: {e}")
    finally:
        db.close()

# Only enable scheduler if configured (default: enabled)
if os.getenv('ENABLE_DIGEST_SCHEDULER', 'true').lower() == 'true':
    digest_scheduler.add_job(
        process_notification_digests,
        'interval',
        hours=1,
        id='digest_processor',
        replace_existing=True
    )
    digest_scheduler.start()
    logger.info("Notification digest scheduler started (hourly)")


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

    # Build run options
    run_options = {
        'title': 'TJM Time Calendar',
        'favicon': STATIC_DIR / 'favicon.ico',
        'port': config.PORT,
        'host': config.HOST,
        'storage_secret': config.SECRET_KEY,
        'uvicorn_logging_level': 'warning',
    }

    # Add SSL if configured
    if config.ssl_enabled:
        run_options['ssl_certfile'] = config.SSL_CERTFILE
        run_options['ssl_keyfile'] = config.SSL_KEYFILE
        logger.info(f"HTTPS enabled with certificate: {config.SSL_CERTFILE}")

    ui.run(**run_options)
