"""Theme utilities for the NiceGUI app."""
from nicegui import ui, app


def apply_dark_mode():
    """
    Apply dark mode based on user's stored preference.

    Call this at the start of each page to ensure consistent dark mode behavior.
    Returns the dark_mode object in case the page needs to toggle it.
    """
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()
    return dark_mode
