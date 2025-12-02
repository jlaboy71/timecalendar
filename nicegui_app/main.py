from nicegui import ui, app
from src.database import get_db

# Set up basic app configuration
app.title = "TJM Time Calendar"

@ui.page('/')
def home():
    """Home page with login interface."""
    with ui.column().classes('w-full items-center justify-center min-h-screen'):
        ui.label('TJM Time Calendar System').classes('text-4xl font-bold mb-8')
        ui.button('Login').classes('px-8 py-3 text-lg')

if __name__ == '__main__':
    ui.run(port=8080, host='0.0.0.0')
