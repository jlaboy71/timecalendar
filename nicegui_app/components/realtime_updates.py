"""
Real-time update utilities for PTO Central.
Provides automatic page refresh when PTO request statuses change.
"""
from nicegui import ui, app
from typing import Callable, Optional
import hashlib
import json


def get_requests_hash(requests_data: list) -> str:
    """
    Generate a hash of request statuses to detect changes.

    Args:
        requests_data: List of request dicts or objects with id and status

    Returns:
        Hash string representing current state
    """
    # Extract id and status from each request
    state_data = []
    for req in requests_data:
        if isinstance(req, dict):
            state_data.append({
                'id': req.get('id'),
                'status': req.get('status'),
            })
        else:
            state_data.append({
                'id': getattr(req, 'id', None),
                'status': getattr(req, 'status', None),
            })

    # Sort by id for consistent hashing
    state_data.sort(key=lambda x: x['id'] or 0)

    # Create hash
    state_json = json.dumps(state_data, sort_keys=True)
    return hashlib.md5(state_json.encode()).hexdigest()


def setup_realtime_updates(
    check_function: Callable[[], str],
    interval_seconds: float = 15.0,
    on_change_message: str = "Updates available",
    auto_reload: bool = True,
    storage_key: str = 'last_requests_hash'
):
    """
    Set up real-time update checking for a page.

    Args:
        check_function: Function that returns current state hash
        interval_seconds: How often to check (default 15 seconds)
        on_change_message: Notification message when changes detected
        auto_reload: Whether to auto-reload page on change
        storage_key: Key to store last hash in session storage

    Returns:
        The timer object (for cleanup if needed)
    """
    # Store initial hash
    initial_hash = check_function()
    app.storage.user[storage_key] = initial_hash

    # Track if we've already shown a notification
    notification_shown = {'value': False}

    def check_for_updates():
        """Check if data has changed and notify user."""
        try:
            current_hash = check_function()
            stored_hash = app.storage.user.get(storage_key)

            if current_hash != stored_hash and not notification_shown['value']:
                notification_shown['value'] = True

                # Silent reload - no notification
                ui.run_javascript('location.reload()')
        except Exception as e:
            # Silently handle errors (e.g., database connection issues)
            pass

    # Create timer
    timer = ui.timer(interval_seconds, check_for_updates)

    return timer


def setup_dashboard_updates(db, user_id: int, user_role: str, interval: float = 15.0):
    """
    Set up real-time updates specifically for the dashboard.

    Args:
        db: Database session
        user_id: Current user's ID
        user_role: Current user's role
        interval: Check interval in seconds

    Returns:
        The timer object
    """
    from src.services.pto_service import PTOService

    def get_current_hash():
        """Get hash of current request states."""
        try:
            # Create a fresh database session for the check
            from src.database import get_db
            check_db = next(get_db())
            try:
                # Get user's own requests
                user_requests = PTOService.get_user_requests(check_db, user_id)

                # For managers/admins, also include team pending requests
                all_requests = list(user_requests)

                if user_role in ['manager', 'admin', 'superadmin']:
                    team_requests = PTOService.get_pending_requests_with_employee_info(check_db)
                    for req in team_requests:
                        all_requests.append({
                            'id': req['id'],
                            'status': req['status']
                        })

                return get_requests_hash(all_requests)
            finally:
                check_db.close()
        except Exception:
            return ""

    message = "Your requests have been updated" if user_role == 'employee' else "Request status changed"

    return setup_realtime_updates(
        check_function=get_current_hash,
        interval_seconds=interval,
        on_change_message=message,
        auto_reload=True,
        storage_key=f'dashboard_hash_{user_id}'
    )


def setup_calendar_updates(db, user_id: int, interval: float = 15.0):
    """
    Set up real-time updates for the calendar page.

    Args:
        db: Database session
        user_id: Current user's ID
        interval: Check interval in seconds

    Returns:
        The timer object
    """
    from src.services.pto_service import PTOService

    def get_current_hash():
        """Get hash of all approved/pending requests (affects calendar display)."""
        try:
            from src.database import get_db
            check_db = next(get_db())
            try:
                # Get all requests that would appear on calendar
                all_requests = PTOService.get_all_requests(check_db)
                # Filter to approved and pending only
                calendar_requests = [
                    {'id': r.id, 'status': r.status}
                    for r in all_requests
                    if r.status in ['approved', 'pending']
                ]
                return get_requests_hash(calendar_requests)
            finally:
                check_db.close()
        except Exception:
            return ""

    return setup_realtime_updates(
        check_function=get_current_hash,
        interval_seconds=interval,
        on_change_message="Calendar updated",
        auto_reload=True,
        storage_key=f'calendar_hash_{user_id}'
    )


def setup_manager_approvals_updates(db, manager_id: int, department_id: int, interval: float = 15.0):
    """
    Set up real-time updates for manager approval pages.

    Args:
        db: Database session
        manager_id: Manager's user ID
        department_id: Manager's department ID
        interval: Check interval in seconds

    Returns:
        The timer object
    """
    from src.services.pto_service import PTOService

    def get_current_hash():
        """Get hash of pending requests in department."""
        try:
            from src.database import get_db
            check_db = next(get_db())
            try:
                pending_requests = PTOService.get_pending_requests_with_employee_info(check_db)
                return get_requests_hash(pending_requests)
            finally:
                check_db.close()
        except Exception:
            return ""

    return setup_realtime_updates(
        check_function=get_current_hash,
        interval_seconds=interval,
        on_change_message="New pending requests",
        auto_reload=True,
        storage_key=f'manager_hash_{manager_id}'
    )
