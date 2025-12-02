from nicegui import ui, app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import get_db
from nicegui_app.pages.login import login_page
from nicegui_app.pages.dashboard import dashboard_page

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
    ui.label('Submit PTO Request - Coming in Session 3').classes('text-2xl')
    ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))

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

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0')
