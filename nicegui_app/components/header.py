"""Shared header component for all pages."""
from nicegui import ui, app
from datetime import datetime
import pytz
from nicegui_app.logo import LOGO_DATA_URL
from src.database import get_db
from src.services.audit_service import AuditService
from src.services.session_manager import SessionManager
from nicegui_app.components.theme import show_success_dialog

# Warning threshold in minutes (show warning when this many minutes remain)
SESSION_WARNING_MINUTES = 5


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


def go_back():
    """Navigate back using browser history."""
    ui.run_javascript('window.history.back()')


def page_header(title: str = None, show_back: bool = True, back_url: str = None):
    """
    Render a consistent page header with logo, greeting, and optional title.

    Args:
        title: Optional page title to show (e.g., 'REPORTS', 'REQUEST TIME OFF')
        show_back: Whether to show back button
        back_url: Optional fallback URL (if provided, uses direct navigation instead of history.back())
    """
    user = app.storage.user.get('user')
    if not user:
        return

    # Update session activity timestamp
    SessionManager.update_activity()

    user_first_name = user.get('first_name', 'User')
    user_last_name = user.get('last_name', '')
    greeting = get_time_based_greeting()
    is_dark = app.storage.user.get('dark_mode', True)  # Default to dark mode
    greeting_color = '#C9A227' if is_dark else '#5a6a72'

    with ui.row().classes('w-full justify-between items-start mb-6 no-print'):
        with ui.column().classes('gap-1'):
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto; cursor: pointer;').on('click', lambda: ui.navigate.to('/dashboard'))
            if title:
                with ui.row().classes('items-center gap-2').style('padding-left: 52px; margin-top: -8px;'):
                    if show_back:
                        # Use browser history back for natural navigation, or fallback URL if specified
                        if back_url:
                            ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to(back_url)).props('flat round dense aria-label="Go back"')
                        else:
                            ui.button(icon='arrow_back', on_click=go_back).props('flat round dense aria-label="Go back"')
                    ui.label(title).classes('text-lg font-bold uppercase').style(f'color: {greeting_color};')

        # Define logout handler before using it
        def do_logout():
            """Clear user session, log logout, and redirect to login."""
            current_user = app.storage.user.get('user')
            if current_user:
                try:
                    db = next(get_db())
                    AuditService.log_logout(db, current_user.get('id'), current_user.get('username'))
                    db.close()
                except Exception:
                    pass  # Don't block logout if audit logging fails
            SessionManager.clear_session()
            ui.navigate.to('/')

        with ui.column().classes('items-end gap-1'):
            # Row 1: Greeting - right aligned
            ui.label(f'{greeting}, {user_first_name} {user_last_name}').classes('text-lg font-bold uppercase').style(f'color: {greeting_color};')

            # Row 2: Utility icons + LOGOUT - right aligned
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='help_outline', on_click=lambda: ui.navigate.to('/help')).props('flat round dense size=sm aria-label="Help Center"').tooltip('Help Center').style('color: #C9A227 !important;')

                dark_mode = ui.dark_mode()
                is_dark = app.storage.user.get('dark_mode', True)
                if is_dark:
                    dark_mode.enable()

                initial_icon = 'light_mode' if is_dark else 'dark_mode'
                dark_toggle_btn = ui.button(icon=initial_icon, on_click=lambda: None).props('flat round dense size=sm aria-label="Toggle Dark Mode"').tooltip('Toggle Dark Mode').style('color: #C9A227 !important;')

                def toggle_dark_mode():
                    is_currently_dark = app.storage.user.get('dark_mode', True)
                    new_dark_mode = not is_currently_dark
                    app.storage.user['dark_mode'] = new_dark_mode
                    if new_dark_mode:
                        dark_mode.enable()
                        dark_toggle_btn.props(f'icon=light_mode')
                    else:
                        dark_mode.disable()
                        dark_toggle_btn.props(f'icon=dark_mode')

                dark_toggle_btn.on('click', toggle_dark_mode)

                # LOGOUT button with gold outline
                ui.button('LOGOUT', on_click=do_logout).props('outline dense').style('color: #ef4444 !important; border-color: #C9A227 !important; font-weight: 600;')

    # Session timeout warning system
    _setup_session_timeout_warning()


def _setup_session_timeout_warning():
    """
    Set up a timer to check session timeout and show warning modal.

    Checks every 30 seconds if session is about to expire (within 5 minutes).
    Shows a modal warning with countdown and option to extend session.
    """
    warning_shown = {'value': False}
    timer_ref = {'timer': None}

    # Create the warning dialog (hidden initially)
    with ui.dialog() as warning_dialog:
        warning_dialog.props('persistent')
        with ui.card().classes('p-6 text-center').style('min-width: 350px;'):
            ui.icon('warning', color='amber', size='xl').classes('mb-4')
            ui.label('Session Expiring Soon').classes('text-xl font-bold mb-2')
            countdown_label = ui.label('Your session will expire in 5 minutes.').classes('mb-4')
            ui.label('Click below to stay logged in.').classes('text-sm opacity-70 mb-4')

            with ui.row().classes('w-full justify-center gap-4'):
                def extend_session():
                    SessionManager.update_activity()
                    warning_shown['value'] = False
                    warning_dialog.close()
                    show_success_dialog('Session Extended', 'Your session has been extended')

                def logout_now():
                    warning_dialog.close()
                    SessionManager.clear_session()
                    ui.navigate.to('/')

                ui.button('Stay Logged In', on_click=extend_session).props('color=primary')
                ui.button('Logout', on_click=logout_now).props('flat color=red')

    async def check_session():
        """Check session status and show warning if needed."""
        user = app.storage.user.get('user')
        if not user:
            # No longer logged in, stop checking
            if timer_ref['timer']:
                timer_ref['timer'].deactivate()
            return

        minutes_remaining = SessionManager.get_minutes_remaining()

        # Session expired - redirect to login
        if minutes_remaining <= 0:
            if timer_ref['timer']:
                timer_ref['timer'].deactivate()
            SessionManager.clear_session()
            ui.navigate.to('/?timeout=1')
            return

        # Show warning if within threshold and not already shown
        if minutes_remaining <= SESSION_WARNING_MINUTES and not warning_shown['value']:
            warning_shown['value'] = True
            countdown_label.set_text(f'Your session will expire in {minutes_remaining} minute{"s" if minutes_remaining != 1 else ""}.')
            warning_dialog.open()

        # Update countdown if warning is shown
        elif warning_shown['value'] and warning_dialog.value:
            countdown_label.set_text(f'Your session will expire in {minutes_remaining} minute{"s" if minutes_remaining != 1 else ""}.')

    # Start checking every 30 seconds
    timer_ref['timer'] = ui.timer(30, check_session)
