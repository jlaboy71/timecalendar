"""
Monitoring and alerting service for PTO Central.

Provides error notification, performance logging, and health monitoring.
"""
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Service for monitoring application health and sending alerts.

    Features:
    - Email alerts for critical errors (rate-limited)
    - Performance metric logging
    - Configurable alert thresholds
    """

    # Class-level alert tracking for rate limiting
    _last_alert_times: Dict[str, datetime] = defaultdict(lambda: datetime.min)
    _alert_counts: Dict[str, int] = defaultdict(int)

    # Default configuration
    DEFAULT_ALERT_COOLDOWN_MINUTES = 60  # Max 1 alert per error type per hour
    DEFAULT_SLOW_REQUEST_THRESHOLD_MS = 5000  # Log warning for requests > 5s
    DEFAULT_CRITICAL_REQUEST_THRESHOLD_MS = 30000  # Alert for requests > 30s

    def __init__(
        self,
        db_session=None,
        alert_cooldown_minutes: int = DEFAULT_ALERT_COOLDOWN_MINUTES,
        slow_request_threshold_ms: int = DEFAULT_SLOW_REQUEST_THRESHOLD_MS,
        critical_request_threshold_ms: int = DEFAULT_CRITICAL_REQUEST_THRESHOLD_MS
    ):
        """
        Initialize the monitoring service.

        Args:
            db_session: Optional database session for DB-related monitoring
            alert_cooldown_minutes: Minimum minutes between alerts of same type
            slow_request_threshold_ms: Threshold for slow request warnings (ms)
            critical_request_threshold_ms: Threshold for critical slow request alerts (ms)
        """
        self._db_session = db_session
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)
        self.slow_threshold_ms = slow_request_threshold_ms
        self.critical_threshold_ms = critical_request_threshold_ms

    def _can_send_alert(self, error_type: str) -> bool:
        """
        Check if an alert can be sent (rate limiting).

        Args:
            error_type: Category/type of the error

        Returns:
            True if alert can be sent, False if rate-limited
        """
        now = datetime.now()
        last_sent = self._last_alert_times[error_type]

        if now - last_sent >= self.alert_cooldown:
            return True
        return False

    def _record_alert_sent(self, error_type: str) -> None:
        """Record that an alert was sent for rate limiting."""
        self._last_alert_times[error_type] = datetime.now()
        self._alert_counts[error_type] += 1

    def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        error_details: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Send an email alert for a critical error.

        Args:
            error_type: Category of the error (e.g., 'database_error', 'auth_failure')
            error_message: Brief description of the error
            error_details: Full error details/stack trace
            user_context: Optional dict with user info (user_id, username, etc.)
            force: If True, bypass rate limiting

        Returns:
            True if alert was sent, False if rate-limited or failed
        """
        # Check rate limiting unless forced
        if not force and not self._can_send_alert(error_type):
            logger.debug(f"Alert rate-limited for error type: {error_type}")
            return False

        # Build alert content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"[PTO Central ALERT] {error_type}: {error_message[:50]}"

        body_parts = [
            f"<h2>PTO Central - Critical Error Alert</h2>",
            f"<p><strong>Time:</strong> {timestamp}</p>",
            f"<p><strong>Error Type:</strong> {error_type}</p>",
            f"<p><strong>Message:</strong> {error_message}</p>",
        ]

        if user_context:
            body_parts.append("<h3>User Context</h3><ul>")
            for key, value in user_context.items():
                body_parts.append(f"<li><strong>{key}:</strong> {value}</li>")
            body_parts.append("</ul>")

        if error_details:
            body_parts.append(f"<h3>Details</h3><pre>{error_details}</pre>")

        body_parts.append(
            "<hr><p><em>This is an automated alert from PTO Central."
            f"Alert count for this error type: {self._alert_counts[error_type] + 1}</em></p>"
        )

        body = "\n".join(body_parts)

        # Try to send email using EmailService
        try:
            from src.services.email_service import EmailService
            from src.config import settings

            # Get admin email from settings or use default
            admin_email = getattr(settings, 'ADMIN_ALERT_EMAIL', None)
            if not admin_email:
                admin_email = getattr(settings, 'SMTP_FROM', None)

            if not admin_email:
                logger.warning("No admin email configured for alerts, logging only")
                logger.error(f"ALERT [{error_type}]: {error_message}\n{error_details or ''}")
                self._record_alert_sent(error_type)
                return True

            email_service = EmailService(self._db_session)
            success = email_service.send_email(
                to_email=admin_email,
                subject=subject,
                body=body
            )

            if success:
                logger.info(f"Error alert sent for {error_type}")
                self._record_alert_sent(error_type)
                return True
            else:
                logger.error(f"Failed to send error alert email for {error_type}")
                return False

        except Exception as e:
            # If email fails, at least log the error
            logger.error(f"Could not send alert email: {e}")
            logger.error(f"ALERT [{error_type}]: {error_message}\n{error_details or ''}")
            self._record_alert_sent(error_type)
            return False

    def log_exception(
        self,
        exception: Exception,
        context: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        send_alert: bool = True
    ) -> None:
        """
        Log an exception with full details and optionally send alert.

        Args:
            exception: The exception object
            context: Description of where/what was happening
            user_context: Optional dict with user info
            send_alert: Whether to send email alert
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        error_details = traceback.format_exc()

        # Always log
        logger.error(f"Exception in {context or 'unknown context'}: {error_message}")
        logger.error(error_details)

        # Optionally send alert
        if send_alert:
            full_context = context or "Application Error"
            self.send_error_alert(
                error_type=error_type,
                error_message=f"{full_context}: {error_message}",
                error_details=error_details,
                user_context=user_context
            )

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a performance metric with configurable thresholds.

        Args:
            operation: Name of the operation being measured
            duration_ms: Duration in milliseconds
            details: Optional additional context
        """
        details_str = f" | Details: {details}" if details else ""

        if duration_ms >= self.critical_threshold_ms:
            # Critical - send alert
            logger.critical(f"CRITICAL SLOW: {operation} took {duration_ms:.0f}ms{details_str}")
            self.send_error_alert(
                error_type="performance_critical",
                error_message=f"Critical slow operation: {operation} ({duration_ms:.0f}ms)",
                error_details=f"Operation: {operation}\nDuration: {duration_ms:.0f}ms\nDetails: {details}"
            )
        elif duration_ms >= self.slow_threshold_ms:
            # Warning level
            logger.warning(f"SLOW: {operation} took {duration_ms:.0f}ms{details_str}")
        else:
            # Debug level for normal operations
            logger.debug(f"Performance: {operation} took {duration_ms:.0f}ms{details_str}")

    @classmethod
    def reset_rate_limits(cls) -> None:
        """Reset all rate limiting counters. Useful for testing."""
        cls._last_alert_times.clear()
        cls._alert_counts.clear()

    @classmethod
    def get_alert_stats(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics about sent alerts.

        Returns:
            Dict mapping error types to their stats (count, last_sent)
        """
        stats = {}
        for error_type, count in cls._alert_counts.items():
            stats[error_type] = {
                'count': count,
                'last_sent': cls._last_alert_times[error_type].isoformat()
                    if cls._last_alert_times[error_type] != datetime.min else None
            }
        return stats


class PerformanceTimer:
    """
    Context manager for timing operations and logging performance.

    Usage:
        with PerformanceTimer("database_query", monitoring_service):
            # do something slow
            pass
    """

    def __init__(
        self,
        operation: str,
        monitoring_service: Optional[MonitoringService] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the timer.

        Args:
            operation: Name of the operation being timed
            monitoring_service: Optional monitoring service for logging
            details: Optional additional context
        """
        self.operation = operation
        self.monitoring = monitoring_service
        self.details = details
        self.start_time: float = 0
        self.duration_ms: float = 0

    def __enter__(self) -> 'PerformanceTimer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        end_time = time.perf_counter()
        self.duration_ms = (end_time - self.start_time) * 1000

        if self.monitoring:
            self.monitoring.log_performance(
                self.operation,
                self.duration_ms,
                self.details
            )
        else:
            # Fallback to basic logging if no monitoring service
            logger.debug(f"Performance: {self.operation} took {self.duration_ms:.0f}ms")
