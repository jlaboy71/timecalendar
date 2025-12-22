"""
WFH Day Swap service for managing employee WFH day exchanges.

This is a peer-to-peer system - no manager approval required.
Employees can swap their designated WFH days with colleagues directly.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_

from ..models.wfh_day_swap import WFHDaySwapRequest
from ..models.user import User
from ..models.market_holiday import MarketHoliday

logger = logging.getLogger(__name__)


class WFHSwapService:
    """
    Service class for managing WFH day swap operations.

    Provides methods for creating, accepting, declining, and cancelling
    WFH day swap requests between employees.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the WFHSwapService with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _get_wfh_day(self, user: User) -> Optional[str]:
        """
        Extract the WFH day from user's remote_schedule.

        Args:
            user: User object

        Returns:
            Day name (e.g., 'monday', 'tuesday') or None if no WFH day set
        """
        if not user.remote_schedule:
            return None

        schedule = user.remote_schedule
        if isinstance(schedule, dict):
            # Look for the designated WFH day
            # remote_schedule format: {"monday": true, "tuesday": false, ...}
            for day, is_wfh in schedule.items():
                if is_wfh:
                    return day.lower()
        return None

    def _calculate_expiration(self, from_date: datetime) -> datetime:
        """
        Calculate 3 business days from the given date.

        Args:
            from_date: Starting datetime

        Returns:
            Expiration datetime (3 business days later at end of day)
        """
        business_days = 0
        current = from_date

        while business_days < 3:
            current += timedelta(days=1)
            # Skip weekends (5 = Saturday, 6 = Sunday)
            if current.weekday() < 5:
                business_days += 1

        # Set to end of day
        return current.replace(hour=23, minute=59, second=59)

    def _get_day_of_week(self, d: date) -> str:
        """Get the day of week name for a date."""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        return days[d.weekday()]

    def get_users_with_wfh_day(self, day_name: str, exclude_user_id: int = None) -> List[User]:
        """
        Get all active, swap-eligible users who have the specified day as their WFH day.

        Args:
            day_name: Day of week (e.g., 'monday', 'tuesday')
            exclude_user_id: User ID to exclude from results

        Returns:
            List of users with that WFH day who are eligible for swaps
        """
        stmt = select(User).where(
            User.is_active == True,
            User.wfh_swap_eligible == True  # Only include swap-eligible users
        )
        users = self.db.execute(stmt).scalars().all()

        result = []
        for user in users:
            if exclude_user_id and user.id == exclude_user_id:
                continue
            wfh_day = self._get_wfh_day(user)
            if wfh_day and wfh_day.lower() == day_name.lower():
                result.append(user)

        return result

    def create_swap_request(
        self,
        requester_id: int,
        target_user_id: int,
        swap_date: date,
        message: str
    ) -> WFHDaySwapRequest:
        """
        Create a new WFH day swap request.

        Args:
            requester_id: ID of user requesting the swap
            target_user_id: ID of user being asked to swap
            swap_date: The date for the swap
            message: Required message explaining the request

        Returns:
            Created WFHDaySwapRequest

        Raises:
            ValueError: If validation fails
        """
        # Validate requester exists
        requester = self.db.get(User, requester_id)
        if not requester:
            raise ValueError(f"Requester with ID {requester_id} not found")

        # Validate target exists
        target = self.db.get(User, target_user_id)
        if not target:
            raise ValueError(f"Target user with ID {target_user_id} not found")

        # Can't swap with yourself
        if requester_id == target_user_id:
            raise ValueError("Cannot swap WFH day with yourself")

        # Validate swap_date is a weekday
        if swap_date.weekday() >= 5:
            raise ValueError("Swap date must be a weekday")

        # Validate swap_date is in the future
        if swap_date <= date.today():
            raise ValueError("Swap date must be in the future")

        # Validate swap_date is within allowed window (current week + next week only)
        today = date.today()
        # Calculate end of next week (Sunday)
        days_until_sunday = 6 - today.weekday()  # Days until this Sunday
        end_of_next_week = today + timedelta(days=days_until_sunday + 7)  # End of next week
        if swap_date > end_of_next_week:
            raise ValueError("Swap date must be within current week or next week only")

        # Validate swap_date is NOT a federal holiday (excluding Early Close days which are working half-days)
        holiday = self.db.execute(
            select(MarketHoliday).where(
                MarketHoliday.holiday_date == swap_date,
                MarketHoliday.market == 'Federal'
            )
        ).scalar_one_or_none()
        if holiday and 'Early Close' not in holiday.name:
            raise ValueError(f"Cannot swap on {holiday.name} - office is closed for federal holiday")

        # Validate user account status
        if not requester.is_active:
            raise ValueError("Your account is not active")
        if not target.is_active:
            raise ValueError("Target user's account is not active")

        # Validate WFH swap eligibility
        if not requester.wfh_swap_eligible:
            raise ValueError("You are not eligible for WFH day swaps")
        if not target.wfh_swap_eligible:
            raise ValueError("Target user is not eligible for WFH day swaps")

        # Calculate the swap week boundaries (used for both requester and target checks)
        swap_week_start = swap_date - timedelta(days=swap_date.weekday())  # Monday of swap week
        swap_week_end = swap_week_start + timedelta(days=6)  # Sunday of swap week

        # Check if requester already has a pending or accepted swap for the same week
        # (both as requester or as target - one swap per week per user)
        existing_requester_swap = self.db.execute(
            select(WFHDaySwapRequest).where(
                or_(
                    WFHDaySwapRequest.requester_id == requester_id,
                    WFHDaySwapRequest.target_user_id == requester_id
                ),
                WFHDaySwapRequest.status.in_(['pending', 'accepted']),
                WFHDaySwapRequest.swap_date >= swap_week_start,
                WFHDaySwapRequest.swap_date <= swap_week_end
            )
        ).scalar_one_or_none()

        if existing_requester_swap:
            raise ValueError("You already have a swap request for this week. Only one swap per week is allowed.")

        existing_target_swap = self.db.execute(
            select(WFHDaySwapRequest).where(
                or_(
                    WFHDaySwapRequest.requester_id == target_user_id,
                    WFHDaySwapRequest.target_user_id == target_user_id
                ),
                WFHDaySwapRequest.status.in_(['pending', 'accepted']),
                WFHDaySwapRequest.swap_date >= swap_week_start,
                WFHDaySwapRequest.swap_date <= swap_week_end
            )
        ).scalar_one_or_none()

        if existing_target_swap:
            raise ValueError(f"This teammate already has a swap request for that week")

        # Get WFH days for both users
        requester_wfh_day = self._get_wfh_day(requester)
        target_wfh_day = self._get_wfh_day(target)

        if not requester_wfh_day:
            raise ValueError("You don't have a designated WFH day")

        if not target_wfh_day:
            raise ValueError("Target user doesn't have a designated WFH day")

        # Verify target has the swap_date as their WFH day
        swap_day_name = self._get_day_of_week(swap_date)
        if target_wfh_day.lower() != swap_day_name.lower():
            raise ValueError(
                f"Target user's WFH day is {target_wfh_day.title()}, "
                f"but swap date is a {swap_day_name.title()}"
            )

        # Validate message is not empty
        if not message or not message.strip():
            raise ValueError("A message is required for swap requests")

        # Create the request
        now = datetime.now()
        swap_request = WFHDaySwapRequest(
            requester_id=requester_id,
            target_user_id=target_user_id,
            swap_date=swap_date,
            requester_original_day=requester_wfh_day,
            target_original_day=target_wfh_day,
            status='pending',
            request_message=message.strip(),
            requested_at=now,
            expires_at=self._calculate_expiration(now)
        )

        self.db.add(swap_request)
        self.db.commit()
        self.db.refresh(swap_request)

        logger.info(
            f"WFH swap request created: {requester.username} -> {target.username} "
            f"for {swap_date} (ID: {swap_request.id})"
        )

        return swap_request

    def accept_swap(
        self,
        swap_id: int,
        responder_id: int,
        message: str
    ) -> WFHDaySwapRequest:
        """
        Accept a WFH day swap request.

        Args:
            swap_id: ID of the swap request
            responder_id: ID of user accepting (must be target_user_id)
            message: Required response message

        Returns:
            Updated WFHDaySwapRequest

        Raises:
            ValueError: If validation fails
        """
        swap_request = self.db.get(WFHDaySwapRequest, swap_id)
        if not swap_request:
            raise ValueError(f"Swap request with ID {swap_id} not found")

        # Verify responder is the target
        if swap_request.target_user_id != responder_id:
            raise ValueError("Only the target user can accept this request")

        # Verify request is pending
        if swap_request.status != 'pending':
            raise ValueError(f"Cannot accept a request with status '{swap_request.status}'")

        # Check if expired
        if swap_request.expires_at and datetime.now() > swap_request.expires_at:
            swap_request.status = 'expired'
            self.db.commit()
            raise ValueError("This swap request has expired")

        # Validate response message
        if not message or not message.strip():
            raise ValueError("A response message is required")

        # Accept the request
        swap_request.status = 'accepted'
        swap_request.response_message = message.strip()
        swap_request.responded_at = datetime.now()

        self.db.commit()
        self.db.refresh(swap_request)

        logger.info(f"WFH swap request {swap_id} accepted")

        return swap_request

    def decline_swap(
        self,
        swap_id: int,
        responder_id: int,
        message: str
    ) -> WFHDaySwapRequest:
        """
        Decline a WFH day swap request.

        Args:
            swap_id: ID of the swap request
            responder_id: ID of user declining (must be target_user_id)
            message: Required response message

        Returns:
            Updated WFHDaySwapRequest

        Raises:
            ValueError: If validation fails
        """
        swap_request = self.db.get(WFHDaySwapRequest, swap_id)
        if not swap_request:
            raise ValueError(f"Swap request with ID {swap_id} not found")

        # Verify responder is the target
        if swap_request.target_user_id != responder_id:
            raise ValueError("Only the target user can decline this request")

        # Verify request is pending
        if swap_request.status != 'pending':
            raise ValueError(f"Cannot decline a request with status '{swap_request.status}'")

        # Validate response message
        if not message or not message.strip():
            raise ValueError("A response message is required when declining")

        # Decline the request
        swap_request.status = 'declined'
        swap_request.response_message = message.strip()
        swap_request.responded_at = datetime.now()

        self.db.commit()
        self.db.refresh(swap_request)

        logger.info(f"WFH swap request {swap_id} declined")

        return swap_request

    def cancel_swap(
        self,
        swap_id: int,
        requester_id: int
    ) -> WFHDaySwapRequest:
        """
        Cancel a pending WFH day swap request.

        Args:
            swap_id: ID of the swap request
            requester_id: ID of user cancelling (must be original requester)

        Returns:
            Updated WFHDaySwapRequest

        Raises:
            ValueError: If validation fails
        """
        swap_request = self.db.get(WFHDaySwapRequest, swap_id)
        if not swap_request:
            raise ValueError(f"Swap request with ID {swap_id} not found")

        # Verify requester is the original requester
        if swap_request.requester_id != requester_id:
            raise ValueError("Only the requester can cancel this request")

        # Verify request is pending
        if swap_request.status != 'pending':
            raise ValueError(f"Cannot cancel a request with status '{swap_request.status}'")

        # Cancel the request
        swap_request.status = 'cancelled'
        swap_request.responded_at = datetime.now()

        self.db.commit()
        self.db.refresh(swap_request)

        logger.info(f"WFH swap request {swap_id} cancelled by requester")

        return swap_request

    def get_pending_for_user(self, user_id: int) -> List[WFHDaySwapRequest]:
        """
        Get all pending swap requests where user is the target.

        Args:
            user_id: User ID

        Returns:
            List of pending swap requests for this user to respond to
        """
        stmt = select(WFHDaySwapRequest).where(
            WFHDaySwapRequest.target_user_id == user_id,
            WFHDaySwapRequest.status == 'pending'
        ).order_by(WFHDaySwapRequest.requested_at.desc())

        return list(self.db.execute(stmt).scalars().all())

    def get_sent_requests(self, user_id: int) -> List[WFHDaySwapRequest]:
        """
        Get all swap requests sent by a user.

        Args:
            user_id: User ID

        Returns:
            List of swap requests sent by this user
        """
        stmt = select(WFHDaySwapRequest).where(
            WFHDaySwapRequest.requester_id == user_id
        ).order_by(WFHDaySwapRequest.requested_at.desc())

        return list(self.db.execute(stmt).scalars().all())

    def get_user_swap_history(self, user_id: int, limit: int = 50) -> List[WFHDaySwapRequest]:
        """
        Get swap request history for a user (both sent and received).

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List of swap requests involving this user
        """
        stmt = select(WFHDaySwapRequest).where(
            or_(
                WFHDaySwapRequest.requester_id == user_id,
                WFHDaySwapRequest.target_user_id == user_id
            )
        ).order_by(WFHDaySwapRequest.requested_at.desc()).limit(limit)

        return list(self.db.execute(stmt).scalars().all())

    def get_accepted_swaps_for_date(self, swap_date: date) -> List[WFHDaySwapRequest]:
        """
        Get all accepted swaps for a specific date.

        Useful for calendar display and WFH schedule lookups.

        Args:
            swap_date: The date to check

        Returns:
            List of accepted swap requests for that date
        """
        stmt = select(WFHDaySwapRequest).where(
            WFHDaySwapRequest.swap_date == swap_date,
            WFHDaySwapRequest.status == 'accepted'
        )

        return list(self.db.execute(stmt).scalars().all())

    def expire_old_requests(self) -> int:
        """
        Mark expired pending requests as expired.

        Should be called periodically (e.g., daily task).

        Returns:
            Number of requests marked as expired
        """
        now = datetime.now()

        stmt = select(WFHDaySwapRequest).where(
            WFHDaySwapRequest.status == 'pending',
            WFHDaySwapRequest.expires_at < now
        )

        expired_requests = self.db.execute(stmt).scalars().all()
        count = 0

        for request in expired_requests:
            request.status = 'expired'
            request.responded_at = now
            count += 1
            logger.info(f"WFH swap request {request.id} marked as expired")

        if count > 0:
            self.db.commit()

        return count

    def get_swap_by_id(self, swap_id: int) -> Optional[WFHDaySwapRequest]:
        """
        Get a swap request by ID.

        Args:
            swap_id: Swap request ID

        Returns:
            WFHDaySwapRequest or None
        """
        return self.db.get(WFHDaySwapRequest, swap_id)

    def delete_swap(self, swap_id: int) -> bool:
        """
        Delete a swap request. Only managers/admins should call this.

        Args:
            swap_id: Swap request ID

        Returns:
            True if deleted, False if not found
        """
        swap_request = self.db.get(WFHDaySwapRequest, swap_id)
        if swap_request:
            self.db.delete(swap_request)
            self.db.commit()
            logger.info(f"WFH swap request {swap_id} deleted")
            return True
        return False
