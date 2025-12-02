from nicegui import ui, app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import get_db
from nicegui_app.pages.login import login_page

# Set up basic app configuration
app.title = "TJM Time Calendar"

@ui.page('/')
def home():
    """Home page with login interface."""
    login_page()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0')
