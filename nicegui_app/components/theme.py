"""Theme utilities for the NiceGUI app."""
from nicegui import ui, app


def skeleton_loader(rows: int = 3, width: str = '100%'):
    """
    Display a skeleton loader placeholder while content loads.

    Args:
        rows: Number of skeleton rows to display
        width: Width of the skeleton container
    """
    with ui.column().classes('w-full gap-3').style(f'width: {width};'):
        for i in range(rows):
            # Vary widths for more natural look
            row_width = '100%' if i == 0 else f'{85 - (i * 10)}%'
            ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4').style(f'width: {row_width};')


def skeleton_table(rows: int = 5, cols: int = 4):
    """
    Display a skeleton table placeholder while data loads.

    Args:
        rows: Number of skeleton rows
        cols: Number of columns
    """
    with ui.column().classes('w-full gap-2'):
        # Header row
        with ui.row().classes('w-full gap-4'):
            for _ in range(cols):
                ui.element('div').classes('animate-pulse bg-gray-300 dark:bg-gray-600 rounded h-6 flex-1')
        # Data rows
        for _ in range(rows):
            with ui.row().classes('w-full gap-4'):
                for _ in range(cols):
                    ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-5 flex-1')


def skeleton_card():
    """Display a skeleton card placeholder."""
    with ui.card().classes('w-full p-4'):
        ui.element('div').classes('animate-pulse bg-gray-300 dark:bg-gray-600 rounded h-6 w-1/3 mb-4')
        ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-full mb-2')
        ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-4/5')


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
