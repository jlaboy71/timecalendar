from nicegui import ui, app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import get_db
from nicegui_app.pages.login import login_page
from nicegui_app.pages.dashboard import dashboard_page
from nicegui_app.pages.request_form import request_form_page

# Set up basic app configuration
app.title = "TJM Time Calendar"

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
    ui.label('Calendar View - Coming in Session 5').classes('text-2xl')
    ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))

@ui.page('/requests')
def requests():
    """Request history page."""
    ui.label('Request History - Coming Soon').classes('text-2xl')
    ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))

@ui.page('/manager')
def manager():
    """Manager dashboard page for viewing pending PTO requests."""
    # Check if user is logged in and has manager role
    if not app.storage.user.get('id') or app.storage.user.get('role') != 'manager':
        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            ui.label('Access denied. Manager role required.').classes('text-xl text-red-500')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
        return

    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('Manager Dashboard - Pending PTO Requests').classes('text-3xl font-bold mb-6')

        # Get pending requests
        db = next(get_db())
        try:
            from src.services.pto_service import PTOService
            pending_requests = PTOService.get_pending_requests_with_employee_info(db)

            if not pending_requests:
                ui.label('No pending requests').classes('text-xl text-gray-500 text-center mt-8')
            else:
                # Create table with pending requests
                columns = [
                    {'name': 'employee_name', 'label': 'Employee', 'field': 'employee_name', 'align': 'left'},
                    {'name': 'pto_type', 'label': 'Type', 'field': 'pto_type', 'align': 'left'},
                    {'name': 'start_date', 'label': 'Start Date', 'field': 'start_date', 'align': 'left'},
                    {'name': 'end_date', 'label': 'End Date', 'field': 'end_date', 'align': 'left'},
                    {'name': 'total_days', 'label': 'Days', 'field': 'total_days', 'align': 'center'},
                    {'name': 'submitted_at', 'label': 'Submitted', 'field': 'submitted_at', 'align': 'left'}
                ]

                # Format dates for display
                formatted_requests = []
                for req in pending_requests:
                    formatted_requests.append({
                        'request_id': req['request_id'],
                        'employee_name': req['employee_name'],
                        'pto_type': req['pto_type'].title(),
                        'start_date': req['start_date'].strftime('%Y-%m-%d'),
                        'end_date': req['end_date'].strftime('%Y-%m-%d'),
                        'total_days': req['total_days'],
                        'submitted_at': req['submitted_at'].strftime('%Y-%m-%d %H:%M')
                    })

                table = ui.table(columns=columns, rows=formatted_requests, row_key='request_id')
                table.classes('w-full')

                # Make rows clickable
                def on_row_click(e):
                    request_id = e.args[1]['request_id']
                    ui.navigate.to(f'/manager/request/{request_id}')

                table.on('rowClick', on_row_click)

        finally:
            db.close()

        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0')
