"""
Simple rate limiter for login attempts.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class LoginRateLimiter:
    """
    In-memory rate limiter for login attempts.

    Tracks failed login attempts by username and locks out
    after MAX_ATTEMPTS failures for LOCKOUT_MINUTES.
    """

    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    # Storage: {username: (failed_count, last_attempt_time, lockout_until)}
    _attempts: Dict[str, Tuple[int, datetime, datetime | None]] = {}

    @classmethod
    def is_locked_out(cls, username: str) -> Tuple[bool, int]:
        """
        Check if a username is currently locked out.

        Returns:
            Tuple of (is_locked, minutes_remaining)
        """
        username_lower = username.lower()

        if username_lower not in cls._attempts:
            return False, 0

        failed_count, last_attempt, lockout_until = cls._attempts[username_lower]

        if lockout_until is None:
            return False, 0

        now = datetime.now()
        if now < lockout_until:
            minutes_remaining = int((lockout_until - now).total_seconds() / 60) + 1
            return True, minutes_remaining

        # Lockout expired, reset
        cls._attempts[username_lower] = (0, now, None)
        return False, 0

    @classmethod
    def record_failed_attempt(cls, username: str) -> Tuple[int, bool]:
        """
        Record a failed login attempt.

        Returns:
            Tuple of (attempts_remaining, is_now_locked_out)
        """
        username_lower = username.lower()
        now = datetime.now()

        if username_lower in cls._attempts:
            failed_count, last_attempt, lockout_until = cls._attempts[username_lower]

            # If there was a lockout that's expired, reset
            if lockout_until and now >= lockout_until:
                failed_count = 0

            failed_count += 1
        else:
            failed_count = 1

        # Check if we should lock out
        if failed_count >= cls.MAX_ATTEMPTS:
            lockout_until = now + timedelta(minutes=cls.LOCKOUT_MINUTES)
            cls._attempts[username_lower] = (failed_count, now, lockout_until)

            # Send security alert for lockout
            logger.warning(f"Account locked due to failed attempts: {username}")
            try:
                from src.services.alert_service import alert_service
                alert_service.alert_auth_breach_attempt(username)
            except Exception:
                pass  # Don't fail login flow if alerting fails

            return 0, True

        cls._attempts[username_lower] = (failed_count, now, None)
        attempts_remaining = cls.MAX_ATTEMPTS - failed_count
        return attempts_remaining, False

    @classmethod
    def record_successful_login(cls, username: str) -> None:
        """Clear failed attempts after successful login."""
        username_lower = username.lower()
        if username_lower in cls._attempts:
            del cls._attempts[username_lower]

    @classmethod
    def get_remaining_attempts(cls, username: str) -> int:
        """Get how many login attempts remain before lockout."""
        username_lower = username.lower()

        if username_lower not in cls._attempts:
            return cls.MAX_ATTEMPTS

        failed_count, last_attempt, lockout_until = cls._attempts[username_lower]

        # If locked out, return 0
        if lockout_until and datetime.now() < lockout_until:
            return 0

        # If lockout expired, reset
        if lockout_until and datetime.now() >= lockout_until:
            return cls.MAX_ATTEMPTS

        return cls.MAX_ATTEMPTS - failed_count
