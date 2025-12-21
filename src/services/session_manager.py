"""
Session management for tracking activity and handling timeouts.
"""
from datetime import datetime, timedelta
from nicegui import app, ui


class SessionManager:
    """
    Manages user session activity and timeout.

    Tracks last activity time and automatically logs out
    users after a period of inactivity.
    """

    # Session timeout in minutes (default: 30 minutes)
    TIMEOUT_MINUTES = 30

    @classmethod
    def update_activity(cls) -> None:
        """Update the last activity timestamp for the current user."""
        if app.storage.user.get('user'):
            app.storage.user['last_activity'] = datetime.now().isoformat()

    @classmethod
    def get_last_activity(cls) -> datetime | None:
        """Get the last activity timestamp."""
        last_activity_str = app.storage.user.get('last_activity')
        if last_activity_str:
            try:
                return datetime.fromisoformat(last_activity_str)
            except (ValueError, TypeError):
                return None
        return None

    @classmethod
    def is_session_expired(cls) -> bool:
        """
        Check if the current session has expired due to inactivity.

        Returns:
            True if session is expired, False otherwise
        """
        user = app.storage.user.get('user')
        if not user:
            return True  # No session

        last_activity = cls.get_last_activity()
        if not last_activity:
            # No activity recorded, session just started
            cls.update_activity()
            return False

        # Check if timeout has elapsed
        timeout_delta = timedelta(minutes=cls.TIMEOUT_MINUTES)
        if datetime.now() - last_activity > timeout_delta:
            return True

        return False

    @classmethod
    def get_minutes_remaining(cls) -> int:
        """Get minutes remaining before session timeout."""
        last_activity = cls.get_last_activity()
        if not last_activity:
            return cls.TIMEOUT_MINUTES

        elapsed = datetime.now() - last_activity
        remaining = cls.TIMEOUT_MINUTES - int(elapsed.total_seconds() / 60)
        return max(0, remaining)

    @classmethod
    def clear_session(cls) -> None:
        """Clear all session data."""
        app.storage.user.pop('user', None)
        app.storage.user.pop('dark_mode', None)
        app.storage.user.pop('last_activity', None)

    @classmethod
    def check_and_redirect_if_expired(cls) -> bool:
        """
        Check session and redirect to login if expired.

        Returns:
            True if session is valid, False if expired (and redirecting)
        """
        if cls.is_session_expired():
            cls.clear_session()
            ui.navigate.to('/?timeout=1')
            return False

        # Session valid, update activity
        cls.update_activity()
        return True


def require_auth():
    """
    Decorator/function to check authentication and session timeout.

    Call at the start of protected pages to ensure user is logged in
    and session hasn't timed out.

    Returns:
        True if authenticated and session valid, False otherwise
    """
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return False

    if not SessionManager.check_and_redirect_if_expired():
        return False

    return True
