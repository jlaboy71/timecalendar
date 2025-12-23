"""
PTO Central - Scenario Setup Service
Creates test data required for training video scenarios.

This service runs BEFORE browser automation to ensure:
- Manager approval scenarios have pending requests to approve
- Team calendar scenarios have visible data
- Carryover scenarios have pending carryover requests
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.models.user import User
from src.models.pto_request import PTORequest
from src.models.pto_balance import PTOBalance
from src.models.carryover_request import CarryoverRequest
from src.models.wfh_day_swap import WFHDaySwapRequest
from sqlalchemy import select


class ScenarioSetupService:
    """
    Creates and manages test data for scenario execution.

    Supported action types:
    - create_pto_request: Creates a PTO request (pending or approved)
    - create_carryover_request: Creates a carryover exception request
    - ensure_balance: Ensures user has sufficient PTO balance
    - set_wfh_day: Sets up a user's WFH day in remote_schedule
    - create_wfh_swap_request: Creates a WFH swap request for demo
    - cleanup: Removes test data created during setup
    """

    # Track created test data for cleanup
    _created_data: Dict[str, List[int]] = {
        'pto_requests': [],
        'carryover_requests': [],
        'wfh_swap_requests': [],
    }

    @classmethod
    def run_setup_actions(cls, actions: List[Any], log_callback: Optional[callable] = None) -> bool:
        """
        Execute a list of setup actions before scenario runs.

        Args:
            actions: List of SetupAction objects
            log_callback: Optional callback for logging (message, level)

        Returns:
            True if all setup actions succeeded
        """
        if not actions:
            return True

        def log(msg: str, level: str = 'info'):
            if log_callback:
                log_callback(msg, level)
            else:
                print(f"[SETUP] {msg}")

        log(f"Running {len(actions)} setup action(s)...")

        db = next(get_db())
        try:
            for i, action in enumerate(actions):
                action_type = action.action_type
                params = action.params
                description = action.description or action_type

                log(f"  [{i+1}/{len(actions)}] {description}")

                if action_type == 'create_pto_request':
                    cls._create_pto_request(db, params, log)
                elif action_type == 'create_carryover_request':
                    cls._create_carryover_request(db, params, log)
                elif action_type == 'ensure_balance':
                    cls._ensure_balance(db, params, log)
                elif action_type == 'create_team_requests':
                    cls._create_team_requests(db, params, log)
                elif action_type == 'set_wfh_day':
                    cls._set_wfh_day(db, params, log)
                elif action_type == 'create_wfh_swap_request':
                    cls._create_wfh_swap_request(db, params, log)
                else:
                    log(f"    Unknown action type: {action_type}", 'warning')

            db.commit()
            log("Setup complete!", 'success')
            return True

        except Exception as e:
            db.rollback()
            log(f"Setup failed: {str(e)}", 'error')
            return False
        finally:
            db.close()

    @classmethod
    def cleanup(cls, log_callback: Optional[callable] = None) -> None:
        """Remove all test data created during setup."""
        def log(msg: str, level: str = 'info'):
            if log_callback:
                log_callback(msg, level)
            else:
                print(f"[CLEANUP] {msg}")

        if not any(cls._created_data.values()):
            return

        log("Cleaning up test data...")

        db = next(get_db())
        try:
            # Delete PTO requests
            for request_id in cls._created_data['pto_requests']:
                request = db.get(PTORequest, request_id)
                if request:
                    db.delete(request)
                    log(f"  Deleted PTO request #{request_id}")

            # Delete carryover requests
            for request_id in cls._created_data['carryover_requests']:
                request = db.get(CarryoverRequest, request_id)
                if request:
                    db.delete(request)
                    log(f"  Deleted carryover request #{request_id}")

            # Delete WFH swap requests
            for request_id in cls._created_data['wfh_swap_requests']:
                request = db.get(WFHDaySwapRequest, request_id)
                if request:
                    db.delete(request)
                    log(f"  Deleted WFH swap request #{request_id}")

            db.commit()

            # Clear tracking
            cls._created_data = {
                'pto_requests': [],
                'carryover_requests': [],
                'wfh_swap_requests': [],
            }

            log("Cleanup complete!", 'success')

        except Exception as e:
            db.rollback()
            log(f"Cleanup failed: {str(e)}", 'error')
        finally:
            db.close()

    @classmethod
    def _get_user_by_username(cls, db, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        return db.execute(stmt).scalar_one_or_none()

    @classmethod
    def _get_manager_for_user(cls, db, user: User) -> Optional[User]:
        """Get the manager for a user (via department)."""
        if user.department and user.department.manager_id:
            return db.get(User, user.department.manager_id)
        # Fallback: find any manager
        stmt = select(User).where(User.role == 'manager').limit(1)
        return db.execute(stmt).scalar_one_or_none()

    @classmethod
    def _create_pto_request(cls, db, params: Dict[str, Any], log: callable) -> Optional[int]:
        """
        Create a PTO request for testing.

        Params:
            employee_username: Username of the employee
            pto_type: Type of PTO ('vacation', 'sick', 'personal')
            days: Number of days (default 2)
            status: Request status ('pending', 'approved', 'denied')
            start_offset: Days from today for start date (default 7)
        """
        username = params.get('employee_username', 'ptouser01')
        pto_type = params.get('pto_type', 'vacation')
        days = params.get('days', 2)
        status = params.get('status', 'pending')
        start_offset = params.get('start_offset', 7)

        # Get the employee user
        user = cls._get_user_by_username(db, username)
        if not user:
            log(f"    User '{username}' not found", 'error')
            return None

        # Calculate dates
        start_date = date.today() + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=days - 1)

        # Check for existing pending request to avoid duplicates
        existing = db.execute(
            select(PTORequest).where(
                PTORequest.user_id == user.id,
                PTORequest.status == 'pending',
                PTORequest.pto_type == pto_type
            )
        ).scalar_one_or_none()

        if existing:
            log(f"    Using existing pending {pto_type} request #{existing.id}")
            return existing.id

        # Create the request
        request = PTORequest(
            user_id=user.id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date,
            total_days=days,
            status=status,
            notes=f"Test request for training video (auto-generated)"
        )

        db.add(request)
        db.flush()  # Get the ID

        cls._created_data['pto_requests'].append(request.id)
        log(f"    Created {status} {pto_type} request #{request.id} for {user.full_name}")

        return request.id

    @classmethod
    def _create_carryover_request(cls, db, params: Dict[str, Any], log: callable) -> Optional[int]:
        """
        Create a carryover exception request for testing.

        Params:
            employee_username: Username of the employee
            hours: Hours requested (default 16)
            status: Request status ('pending', 'approved', 'denied')
        """
        username = params.get('employee_username', 'ptouser01')
        hours = params.get('hours', 16)
        status = params.get('status', 'pending')
        current_year = date.today().year

        user = cls._get_user_by_username(db, username)
        if not user:
            log(f"    User '{username}' not found", 'error')
            return None

        # Check for existing
        existing = db.execute(
            select(CarryoverRequest).where(
                CarryoverRequest.employee_id == user.id,
                CarryoverRequest.status == 'pending',
                CarryoverRequest.from_year == current_year
            )
        ).scalar_one_or_none()

        if existing:
            log(f"    Using existing pending carryover request #{existing.id}")
            return existing.id

        request = CarryoverRequest(
            employee_id=user.id,
            from_year=current_year,
            to_year=current_year + 1,
            hours_requested=hours,
            status=status,
            reason="Test carryover request for training video (auto-generated)"
        )

        db.add(request)
        db.flush()

        cls._created_data['carryover_requests'].append(request.id)
        log(f"    Created {status} carryover request #{request.id} for {user.full_name}")

        return request.id

    @classmethod
    def _ensure_balance(cls, db, params: Dict[str, Any], log: callable) -> None:
        """
        Ensure user has PTO balance for the current year.

        Params:
            employee_username: Username of the employee
            vacation_total: Total vacation hours (default 80)
            sick_total: Total sick hours (default 40)
            personal_total: Total personal hours (default 16)
        """
        username = params.get('employee_username', 'ptouser01')

        user = cls._get_user_by_username(db, username)
        if not user:
            log(f"    User '{username}' not found", 'error')
            return

        current_year = date.today().year

        # Check for existing balance
        existing = db.execute(
            select(PTOBalance).where(
                PTOBalance.user_id == user.id,
                PTOBalance.year == current_year
            )
        ).scalar_one_or_none()

        if existing:
            log(f"    Balance already exists for {user.full_name}")
            return

        balance = PTOBalance(
            user_id=user.id,
            year=current_year,
            vacation_total=params.get('vacation_total', 80),
            sick_total=params.get('sick_total', 40),
            personal_total=params.get('personal_total', 16)
        )

        db.add(balance)
        log(f"    Created balance for {user.full_name}")

    @classmethod
    def _create_team_requests(cls, db, params: Dict[str, Any], log: callable) -> None:
        """
        Create multiple PTO requests to populate team calendar.

        Params:
            manager_username: Username of the manager (finds team members)
            count: Number of requests to create (default 3)
            team_usernames: Optional explicit list of usernames
        """
        manager_username = params.get('manager_username')
        count = params.get('count', 3)
        usernames = params.get('team_usernames', [])

        # If manager provided, find their team members
        if manager_username and not usernames:
            manager = cls._get_user_by_username(db, manager_username)
            if manager and manager.department_id:
                # Find employees in the same department
                from src.models.department import Department
                stmt = select(User).where(
                    User.department_id == manager.department_id,
                    User.id != manager.id,
                    User.is_active == True
                ).limit(count)
                team_members = db.execute(stmt).scalars().all()
                usernames = [u.username for u in team_members]

        # Fallback to default test users (PTO-Department)
        if not usernames:
            usernames = ['ptouser01'][:count]  # Use ptouser01 for fallback

        # Create mix of approved and pending
        pto_types = ['vacation', 'sick', 'personal', 'vacation']
        statuses = ['approved', 'approved', 'pending', 'approved']

        for i, username in enumerate(usernames[:count]):
            cls._create_pto_request(db, {
                'employee_username': username,
                'pto_type': pto_types[i % len(pto_types)],
                'days': 1 + (i % 3),  # Vary the days
                'status': statuses[i % len(statuses)],
                'start_offset': 3 + (i * 3)  # Spread out the dates
            }, log)

    @classmethod
    def _set_wfh_day(cls, db, params: Dict[str, Any], log: callable) -> None:
        """
        Set up a user's WFH day in their remote_schedule.

        Params:
            username: Username of the employee
            wfh_day: Day of week ('monday', 'tuesday', etc.)
        """
        username = params.get('username')
        wfh_day = params.get('wfh_day', '').lower()

        if not username or not wfh_day:
            log("    Missing username or wfh_day parameter", 'error')
            return

        user = cls._get_user_by_username(db, username)
        if not user:
            log(f"    User '{username}' not found", 'error')
            return

        # Build remote_schedule JSON
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        if wfh_day not in days:
            log(f"    Invalid WFH day: {wfh_day}", 'error')
            return

        schedule = {day: (day == wfh_day) for day in days}
        user.remote_schedule = schedule

        log(f"    Set WFH day to {wfh_day.title()} for {user.full_name}")

    @classmethod
    def _create_wfh_swap_request(cls, db, params: Dict[str, Any], log: callable) -> Optional[int]:
        """
        Create a WFH swap request for demo purposes.

        Params:
            requester_username: Username requesting the swap
            target_username: Username being asked to swap
            days_ahead: Days from today for swap date (default 7)
            message: Request message
        """
        from datetime import datetime

        requester_username = params.get('requester_username')
        target_username = params.get('target_username')
        days_ahead = params.get('days_ahead', 7)
        message = params.get('message', 'I need to swap WFH days for a personal appointment.')

        if not requester_username or not target_username:
            log("    Missing requester or target username", 'error')
            return None

        requester = cls._get_user_by_username(db, requester_username)
        target = cls._get_user_by_username(db, target_username)

        if not requester:
            log(f"    Requester '{requester_username}' not found", 'error')
            return None
        if not target:
            log(f"    Target '{target_username}' not found", 'error')
            return None

        # Calculate swap date
        swap_date = date.today() + timedelta(days=days_ahead)
        # Make sure it's a weekday
        while swap_date.weekday() >= 5:
            swap_date += timedelta(days=1)

        # Get WFH days
        requester_schedule = requester.remote_schedule or {}
        target_schedule = target.remote_schedule or {}

        requester_wfh = None
        target_wfh = None
        for day, is_wfh in requester_schedule.items():
            if is_wfh:
                requester_wfh = day
                break
        for day, is_wfh in target_schedule.items():
            if is_wfh:
                target_wfh = day
                break

        if not requester_wfh:
            requester_wfh = 'monday'  # Default
        if not target_wfh:
            target_wfh = 'wednesday'  # Default

        # Check for existing pending request
        existing = db.execute(
            select(WFHDaySwapRequest).where(
                WFHDaySwapRequest.requester_id == requester.id,
                WFHDaySwapRequest.status == 'pending'
            )
        ).scalar_one_or_none()

        if existing:
            log(f"    Using existing pending WFH swap request #{existing.id}")
            return existing.id

        # Create the request
        swap_request = WFHDaySwapRequest(
            requester_id=requester.id,
            target_user_id=target.id,
            swap_date=swap_date,
            requester_original_day=requester_wfh,
            target_original_day=target_wfh,
            status='pending',
            request_message=message,
            requested_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=3)
        )

        db.add(swap_request)
        db.flush()

        cls._created_data['wfh_swap_requests'].append(swap_request.id)
        log(f"    Created pending WFH swap request #{swap_request.id}: {requester.full_name} → {target.full_name}")

        return swap_request.id


# Convenience function for quick setup
def setup_scenario_data(actions: List[Any], log_callback: Optional[callable] = None) -> bool:
    """Run setup actions for a scenario."""
    return ScenarioSetupService.run_setup_actions(actions, log_callback)


def cleanup_scenario_data(log_callback: Optional[callable] = None) -> None:
    """Clean up test data created during setup."""
    ScenarioSetupService.cleanup(log_callback)
