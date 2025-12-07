"""Shared header component for all pages."""
from nicegui import ui, app
from datetime import datetime
import pytz
from nicegui_app.logo import LOGO_DATA_URL


def get_time_based_greeting():
    """Get greeting based on Chicago timezone time of day."""
    chicago_tz = pytz.timezone('America/Chicago')
    chicago_time = datetime.now(chicago_tz)
    hour = chicago_time.hour

    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"


def page_header(title: str = None, show_back: bool = True, back_url: str = '/dashboard'):
    """
    Render a consistent page header with logo, greeting, and optional title.

    Args:
        title: Optional page title to show (e.g., 'REPORTS', 'REQUEST TIME OFF')
        show_back: Whether to show back button
        back_url: URL to navigate to when back button is clicked
    """
    user = app.storage.general.get('user')
    if not user:
        return

    user_first_name = user.get('first_name', 'User')
    user_last_name = user.get('last_name', '')
    greeting = get_time_based_greeting()

    with ui.row().classes('w-full justify-between items-center mb-6'):
        with ui.column().classes('gap-2'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto; cursor: pointer;').on('click', lambda: ui.navigate.to('/dashboard'))
            if title:
                with ui.row().classes('items-center gap-2'):
                    if show_back:
                        ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(back_url)).props('flat round dense')
                    ui.label(title).classes('text-xl font-bold uppercase').style('color: #5a6a72;')
            ui.label(f'{greeting}, {user_first_name} {user_last_name}').classes('text-lg font-medium').style('color: #5a6a72;')

        with ui.row().classes('items-center gap-2'):
            # Dark mode toggle
            dark_mode = ui.dark_mode()
            is_dark = app.storage.general.get('dark_mode', False)
            if is_dark:
                dark_mode.enable()

            def toggle_dark_mode():
                is_currently_dark = app.storage.general.get('dark_mode', False)
                new_dark_mode = not is_currently_dark
                app.storage.general['dark_mode'] = new_dark_mode
                if new_dark_mode:
                    dark_mode.enable()
                else:
                    dark_mode.disable()

            ui.button(icon='dark_mode', on_click=toggle_dark_mode).props('flat round')
            ui.button('Logout', on_click=lambda: [app.storage.general.clear(), ui.navigate.to('/')]).props('flat color=red')
