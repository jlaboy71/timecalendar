"""
Rate limiting middleware for login attempts.

Tracks failed login attempts by IP address and blocks access after
too many failures to prevent brute force attacks.
"""
import time
from threading import Lock
from typing import Dict, Tuple


class LoginRateLimiter:
    """
    Rate limiter for login attempts.

    Tracks failed attempts by IP address and blocks IPs after
    exceeding the maximum allowed failures within a time window.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        block_duration_seconds: int = 900,  # 15 minutes
        cleanup_interval_seconds: int = 300  # 5 minutes
    ):
        """
        Initialize the rate limiter.

        Args:
            max_attempts: Maximum failed attempts before blocking
            block_duration_seconds: How long to block after max failures
            cleanup_interval_seconds: How often to clean up old entries
        """
        self.max_attempts = max_attempts
        self.block_duration = block_duration_seconds
        self.cleanup_interval = cleanup_interval_seconds

        # Store: {ip: (attempt_count, first_attempt_timestamp, blocked_until)}
        self._attempts: Dict[str, Tuple[int, float, float]] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self) -> None:
        """Remove expired entries to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        expired_ips = []
        for ip, (count, first_attempt, blocked_until) in self._attempts.items():
            # Remove if block has expired and no recent attempts
            if blocked_until > 0 and now > blocked_until:
                expired_ips.append(ip)
            # Remove old attempt records that are past the block duration
            elif now - first_attempt > self.block_duration:
                expired_ips.append(ip)

        for ip in expired_ips:
            del self._attempts[ip]

        self._last_cleanup = now

    def record_failed_attempt(self, ip: str) -> None:
        """
        Record a failed login attempt for an IP address.

        Args:
            ip: The IP address that failed to login
        """
        with self._lock:
            self._cleanup_old_entries()
            now = time.time()

            if ip in self._attempts:
                count, first_attempt, blocked_until = self._attempts[ip]

                # If currently blocked, don't update
                if blocked_until > now:
                    return

                # If past the block window, reset
                if now - first_attempt > self.block_duration:
                    self._attempts[ip] = (1, now, 0)
                else:
                    # Increment attempt count
                    new_count = count + 1
                    if new_count >= self.max_attempts:
                        # Block the IP
                        self._attempts[ip] = (new_count, first_attempt, now + self.block_duration)
                    else:
                        self._attempts[ip] = (new_count, first_attempt, 0)
            else:
                # First failed attempt
                self._attempts[ip] = (1, now, 0)

    def is_blocked(self, ip: str) -> bool:
        """
        Check if an IP address is currently blocked.

        Args:
            ip: The IP address to check

        Returns:
            True if blocked, False otherwise
        """
        with self._lock:
            self._cleanup_old_entries()

            if ip not in self._attempts:
                return False

            count, first_attempt, blocked_until = self._attempts[ip]

            if blocked_until > 0:
                if time.time() < blocked_until:
                    return True
                else:
                    # Block has expired, remove entry
                    del self._attempts[ip]
                    return False

            return False

    def clear_attempts(self, ip: str) -> None:
        """
        Clear failed attempts for an IP address (call on successful login).

        Args:
            ip: The IP address to clear
        """
        with self._lock:
            if ip in self._attempts:
                del self._attempts[ip]

    def get_remaining_attempts(self, ip: str) -> int:
        """
        Get the number of remaining attempts before blocking.

        Args:
            ip: The IP address to check

        Returns:
            Number of remaining attempts (0 if blocked)
        """
        with self._lock:
            if ip not in self._attempts:
                return self.max_attempts

            count, _, blocked_until = self._attempts[ip]

            if blocked_until > 0 and time.time() < blocked_until:
                return 0

            return max(0, self.max_attempts - count)

    def get_block_remaining_seconds(self, ip: str) -> int:
        """
        Get remaining seconds until block expires.

        Args:
            ip: The IP address to check

        Returns:
            Seconds until unblocked (0 if not blocked)
        """
        with self._lock:
            if ip not in self._attempts:
                return 0

            _, _, blocked_until = self._attempts[ip]

            if blocked_until > 0:
                remaining = blocked_until - time.time()
                return max(0, int(remaining))

            return 0


# Global rate limiter instance
login_rate_limiter = LoginRateLimiter()


def record_failed_attempt(ip: str) -> None:
    """Record a failed login attempt for an IP address."""
    login_rate_limiter.record_failed_attempt(ip)


def is_blocked(ip: str) -> bool:
    """Check if an IP address is blocked."""
    return login_rate_limiter.is_blocked(ip)


def clear_attempts(ip: str) -> None:
    """Clear attempts for an IP on successful login."""
    login_rate_limiter.clear_attempts(ip)


def get_block_message(ip: str) -> str:
    """Get a user-friendly block message with remaining time."""
    remaining = login_rate_limiter.get_block_remaining_seconds(ip)
    if remaining > 60:
        minutes = remaining // 60
        return f"Too many failed login attempts. Please try again in {minutes} minute{'s' if minutes != 1 else ''}."
    elif remaining > 0:
        return f"Too many failed login attempts. Please try again in {remaining} seconds."
    return ""
