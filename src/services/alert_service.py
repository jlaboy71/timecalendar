"""
Alert service for critical error notifications.

Sends email alerts when critical errors occur in the application.
Includes rate limiting to prevent alert storms.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for sending critical error alerts via email.

    Features:
    - Rate limiting to prevent alert storms (max 1 alert per error type per hour)
    - Configurable via environment variables
    - Falls back gracefully when email not configured
    """

    # Rate limit: minimum time between alerts for same error type
    ALERT_COOLDOWN_MINUTES = 60

    # Track last alert time per error type
    _last_alerts: dict = {}
    _lock = Lock()

    def __init__(self):
        """Initialize alert configuration from environment."""
        self.enabled = os.getenv('ALERT_ENABLED', 'false').lower() == 'true'
        self.alert_email = os.getenv('ALERT_EMAIL', '')

        # Use existing email service config
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('EMAIL_FROM', 'noreply@tjm.com')

    def is_configured(self) -> bool:
        """Check if alerting is properly configured."""
        return bool(
            self.enabled and
            self.alert_email and
            self.smtp_host and
            self.smtp_user and
            self.smtp_password
        )

    def _should_send_alert(self, error_type: str) -> bool:
        """Check if enough time has passed since last alert of this type."""
        with self._lock:
            now = datetime.now()
            last_alert = self._last_alerts.get(error_type)

            if last_alert is None:
                self._last_alerts[error_type] = now
                return True

            cooldown = timedelta(minutes=self.ALERT_COOLDOWN_MINUTES)
            if now - last_alert >= cooldown:
                self._last_alerts[error_type] = now
                return True

            return False

    def send_alert(
        self,
        error_type: str,
        message: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Send an alert email for a critical error.

        Args:
            error_type: Category of error (e.g., 'database', 'auth', 'backup')
            message: Brief error description
            details: Optional detailed error information/stack trace

        Returns:
            True if alert sent, False otherwise (not configured or rate limited)
        """
        if not self.is_configured():
            logger.debug(f"Alert not sent (not configured): {error_type} - {message}")
            return False

        if not self._should_send_alert(error_type):
            logger.debug(f"Alert rate limited: {error_type}")
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            subject = f"[PTO Central ALERT] {error_type}: {message[:50]}"

            # Build HTML email
            details_html = ""
            if details:
                details_html = f"""
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;
                            font-family: monospace; white-space: pre-wrap; margin-top: 20px;">
                    <strong>Details:</strong><br>
                    {details}
                </div>
                """

            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #ef4444; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">PTO Central Alert</h1>
                </div>
                <div style="padding: 20px;">
                    <p><strong>Error Type:</strong> {error_type}</p>
                    <p><strong>Message:</strong> {message}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Server:</strong> {os.getenv('TJM_HOST', 'localhost')}:{os.getenv('TJM_PORT', '8080')}</p>
                    {details_html}
                </div>
                <div style="background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px;">
                    This is an automated alert from PTO Central.
                    Alert rate limit: 1 per error type per hour.
                </div>
            </body>
            </html>
            """

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.alert_email
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.alert_email, msg.as_string())

            logger.info(f"Alert sent: {error_type} - {message}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
            return False

    def alert_database_error(self, error: Exception) -> bool:
        """Send alert for database errors."""
        return self.send_alert(
            error_type="DATABASE",
            message="Database connection or query error",
            details=str(error)
        )

    def alert_backup_failure(self, error: Exception) -> bool:
        """Send alert for backup failures."""
        return self.send_alert(
            error_type="BACKUP",
            message="Database backup failed",
            details=str(error)
        )

    def alert_year_end_failure(self, error: Exception, year: int) -> bool:
        """Send alert for year-end processing failures."""
        return self.send_alert(
            error_type="YEAR_END",
            message=f"Year-end processing failed for {year}",
            details=str(error)
        )

    def alert_auth_breach_attempt(self, username: str, ip: Optional[str] = None) -> bool:
        """Send alert for potential security breach attempts."""
        details = f"Username: {username}"
        if ip:
            details += f"\nIP Address: {ip}"
        return self.send_alert(
            error_type="SECURITY",
            message="Multiple failed login attempts detected",
            details=details
        )


# Global instance
alert_service = AlertService()
