"""
Email notification service for PTO-related communications.
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        """Initialize email configuration from environment variables."""
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('EMAIL_FROM', 'noreply@tjm.com')
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'

    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.enabled and self.smtp_host and self.smtp_user and self.smtp_password)

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content of the email

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_pto_submitted(
        self,
        employee_email: str,
        employee_name: str,
        pto_type: str,
        start_date: date,
        end_date: date,
        total_days: float
    ) -> bool:
        """Send confirmation email when PTO request is submitted."""
        subject = f"TJM Time Calendar: Your {pto_type.title()} Request Submitted"

        date_range = start_date.strftime('%B %d, %Y')
        if start_date != end_date:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #5a6a72; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">TJM Time Calendar</h1>
            </div>
            <div style="padding: 20px;">
                <p>Hi {employee_name},</p>
                <p>Your time off request has been submitted and is pending approval.</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Type:</strong> {pto_type.title()}</p>
                    <p><strong>Dates:</strong> {date_range}</p>
                    <p><strong>Total Days:</strong> {total_days}</p>
                </div>
                <p>You will receive another email once your request has been reviewed.</p>
            </div>
        </body>
        </html>
        """
        return self._send_email(employee_email, subject, html)

    def send_pto_approved(
        self,
        employee_email: str,
        employee_name: str,
        pto_type: str,
        start_date: date,
        end_date: date,
        total_days: float,
        approver_name: str
    ) -> bool:
        """Send email when PTO request is approved."""
        subject = f"TJM Time Calendar: Your {pto_type.title()} Request Approved"

        date_range = start_date.strftime('%B %d, %Y')
        if start_date != end_date:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #22c55e; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Request Approved</h1>
            </div>
            <div style="padding: 20px;">
                <p>Hi {employee_name},</p>
                <p>Great news! Your time off request has been <strong style="color: #22c55e;">approved</strong>.</p>
                <div style="background-color: #f0fdf4; padding: 15px; border-radius: 5px; border-left: 4px solid #22c55e; margin: 20px 0;">
                    <p><strong>Type:</strong> {pto_type.title()}</p>
                    <p><strong>Dates:</strong> {date_range}</p>
                    <p><strong>Total Days:</strong> {total_days}</p>
                    <p><strong>Approved by:</strong> {approver_name}</p>
                </div>
                <p>Enjoy your time off!</p>
            </div>
        </body>
        </html>
        """
        return self._send_email(employee_email, subject, html)

    def send_pto_denied(
        self,
        employee_email: str,
        employee_name: str,
        pto_type: str,
        start_date: date,
        end_date: date,
        total_days: float,
        approver_name: str,
        reason: Optional[str] = None
    ) -> bool:
        """Send email when PTO request is denied."""
        subject = f"TJM Time Calendar: Your {pto_type.title()} Request Denied"

        date_range = start_date.strftime('%B %d, %Y')
        if start_date != end_date:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        reason_html = ""
        if reason:
            reason_html = f"<p><strong>Reason:</strong> {reason}</p>"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ef4444; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Request Denied</h1>
            </div>
            <div style="padding: 20px;">
                <p>Hi {employee_name},</p>
                <p>Unfortunately, your time off request has been <strong style="color: #ef4444;">denied</strong>.</p>
                <div style="background-color: #fef2f2; padding: 15px; border-radius: 5px; border-left: 4px solid #ef4444; margin: 20px 0;">
                    <p><strong>Type:</strong> {pto_type.title()}</p>
                    <p><strong>Dates:</strong> {date_range}</p>
                    <p><strong>Total Days:</strong> {total_days}</p>
                    <p><strong>Reviewed by:</strong> {approver_name}</p>
                    {reason_html}
                </div>
                <p>If you have questions, please speak with your manager.</p>
            </div>
        </body>
        </html>
        """
        return self._send_email(employee_email, subject, html)

    def send_pending_request_notification(
        self,
        manager_email: str,
        manager_name: str,
        employee_name: str,
        pto_type: str,
        start_date: date,
        end_date: date,
        total_days: float
    ) -> bool:
        """Send email to manager when new PTO request needs approval."""
        subject = f"TJM Time Calendar: New {pto_type.title()} Request from {employee_name}"

        date_range = start_date.strftime('%B %d, %Y')
        if start_date != end_date:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f59e0b; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">New Request Pending</h1>
            </div>
            <div style="padding: 20px;">
                <p>Hi {manager_name},</p>
                <p>A new time off request requires your review.</p>
                <div style="background-color: #fffbeb; padding: 15px; border-radius: 5px; border-left: 4px solid #f59e0b; margin: 20px 0;">
                    <p><strong>Employee:</strong> {employee_name}</p>
                    <p><strong>Type:</strong> {pto_type.title()}</p>
                    <p><strong>Dates:</strong> {date_range}</p>
                    <p><strong>Total Days:</strong> {total_days}</p>
                </div>
                <p>Please log in to TJM Time Calendar to approve or deny this request.</p>
            </div>
        </body>
        </html>
        """
        return self._send_email(manager_email, subject, html)

    def send_report_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        message: Optional[str] = None,
        attachment_data: Optional[bytes] = None,
        attachment_name: Optional[str] = None,
        attachment_type: str = 'html'
    ) -> bool:
        """
        Send a formatted report via email with optional attachment.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML report content (used in body if no attachment)
            message: Optional personal message to include
            attachment_data: Raw bytes of attachment file
            attachment_name: Filename for attachment
            attachment_type: Type of attachment ('html', 'csv', 'pdf')

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Build email body
            message_html = ""
            if message:
                message_html = f"""
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0; color: #666;"><em>{message}</em></p>
                </div>
                """

            body_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <div style="background-color: #5a6a72; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">TJM Time Calendar Report</h1>
                </div>
                <div style="padding: 20px;">
                    {message_html}
                    <p>Please find the attached report.</p>
                </div>
            </body>
            </html>
            """

            # Attach body
            msg.attach(MIMEText(body_html, 'html'))

            # Add attachment if provided
            if attachment_data and attachment_name:
                from email.mime.base import MIMEBase
                from email import encoders

                if attachment_type == 'csv':
                    part = MIMEBase('text', 'csv')
                elif attachment_type == 'pdf':
                    part = MIMEBase('application', 'pdf')
                else:  # html
                    part = MIMEBase('text', 'html')

                part.set_payload(attachment_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
                msg.attach(part)
            else:
                # No attachment - include report in body
                full_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                    <div style="background-color: #5a6a72; color: white; padding: 20px; text-align: center;">
                        <h1 style="margin: 0;">TJM Time Calendar Report</h1>
                    </div>
                    <div style="padding: 20px;">
                        {message_html}
                        <p>Please find the report below:</p>
                        <hr style="border: 1px solid #ddd; margin: 20px 0;">
                        {html_content}
                    </div>
                </body>
                </html>
                """
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.from_email
                msg['To'] = to_email
                msg.attach(MIMEText(full_html, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"Report email sent successfully to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send report email to {to_email}: {str(e)}")
            return False


# Global instance
email_service = EmailService()
