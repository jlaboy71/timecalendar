"""
Email notification service for PTO-related communications.
"""
import smtplib
import os
import logging
import base64
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


def _get_pto_type_icon(pto_type: str) -> str:
    """Get emoji icon for PTO type."""
    icons = {
        'vacation': '🏖️',
        'sick': '🏥',
        'personal': '👤',
        'bereavement': '🕯️',
        'fmla': '👨‍👩‍👧',
        'jury_duty': '⚖️',
        'voting': '🗳️',
        'military': '🎖️',
        'chicago_paid_leave': '📍',
        'chicago_leave': '📍',
    }
    return icons.get(pto_type.lower(), '📅')


def _format_date_with_day(d: date) -> str:
    """Format date with day of week (e.g., 'Monday, December 16, 2024')."""
    return d.strftime('%A, %B %d, %Y')


def _format_date_range_with_days(start_date: date, end_date: date) -> str:
    """Format date range with days of week."""
    if start_date == end_date:
        return _format_date_with_day(start_date)
    else:
        return f"{start_date.strftime('%A, %B %d')} - {_format_date_with_day(end_date)}"


def _get_logo_base64() -> str:
    """Get the PTO Central logo as base64 string for email embedding."""
    try:
        logo_path = Path(__file__).parent.parent.parent / 'nicegui_app' / 'static' / 'PTOCentralLogo.png'
        with open(logo_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception:
        return ""


def _get_email_template(title: str, title_color: str, content: str, footer_text: str = "") -> str:
    """
    Generate a dark-themed email template matching the app's style.

    Args:
        title: Header title text
        title_color: Color for the title (hex)
        content: Main HTML content
        footer_text: Optional footer message
    """
    logo_base64 = _get_logo_base64()
    logo_html = ""
    if logo_base64:
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" alt="PTO Central" style="height: 50px; width: auto; margin-bottom: 15px;">'

    footer_html = ""
    if footer_text:
        footer_html = f'<p style="margin-top: 20px; color: #9ca3af;">{footer_text}</p>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #111827;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #111827;">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%;">
                        <!-- Header with Logo -->
                        <tr>
                            <td style="background-color: #1f2937; padding: 25px; text-align: center; border-radius: 12px 12px 0 0; border-bottom: 3px solid {title_color};">
                                {logo_html}
                                <h1 style="margin: 0; color: {title_color}; font-size: 24px; font-weight: 600;">{title}</h1>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="background-color: #1f2937; padding: 30px; color: #e5e7eb;">
                                {content}
                                {footer_html}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #374151; padding: 20px; text-align: center; border-radius: 0 0 12px 12px;">
                                <p style="margin: 0; color: #6b7280; font-size: 12px;">PTO Central</p>
                                <p style="margin: 5px 0 0 0; color: #4b5563; font-size: 11px;">This is an automated notification</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        """Initialize email configuration from environment variables."""
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('EMAIL_FROM', 'noreply@tjm.com')
        self.from_name = os.getenv('EMAIL_FROM_NAME', 'PTO Central')
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'

        # Format the From address with display name
        if self.from_name:
            self.from_address = f'"{self.from_name}" <{self.from_email}>'
        else:
            self.from_address = self.from_email

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
            msg['From'] = self.from_address
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
        pto_icon = _get_pto_type_icon(pto_type)
        pto_label = pto_type.replace('_', ' ').title()
        subject = f"PTO Central: Your {pto_label} Request Submitted"

        date_range = _format_date_range_with_days(start_date, end_date)

        # Format days nicely
        days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

        # Chicago Paid Leave indicator
        chicago_row = ""
        if pto_type in ('chicago_leave', 'chicago_paid_leave'):
            chicago_row = """
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Location:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">📍 Chicago (Paid Leave)</td>
                </tr>
            """

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {employee_name},</p>
        <p style="margin-bottom: 25px;">Your time off request has been submitted and is <span style="color: #f59e0b; font-weight: 600;">pending approval</span>.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {pto_label}</td>
                </tr>
                {chicago_row}
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td>
                </tr>
            </table>
        </div>
        """

        html = _get_email_template(
            title="Request Submitted",
            title_color="#f59e0b",
            content=content,
            footer_text="You will receive another email once your request has been reviewed."
        )
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
        pto_icon = _get_pto_type_icon(pto_type)
        pto_label = pto_type.replace('_', ' ').title()
        subject = f"PTO Central: Your {pto_label} Request Approved"

        date_range = _format_date_range_with_days(start_date, end_date)

        # Format days nicely
        days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

        # Chicago Paid Leave indicator
        chicago_row = ""
        if pto_type in ('chicago_leave', 'chicago_paid_leave'):
            chicago_row = """
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Location:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #22c55e;">📍 Chicago (Paid Leave)</td>
                </tr>
            """

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {employee_name},</p>
        <p style="margin-bottom: 25px;">Great news! Your time off request has been <span style="color: #22c55e; font-weight: 600;">approved</span>.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #22c55e;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {pto_label}</td>
                </tr>
                {chicago_row}
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #22c55e;">{days_display}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Approved by:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{approver_name}</td>
                </tr>
            </table>
        </div>
        """

        html = _get_email_template(
            title="Request Approved",
            title_color="#22c55e",
            content=content,
            footer_text="Enjoy your time off!"
        )
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
        pto_icon = _get_pto_type_icon(pto_type)
        pto_label = pto_type.replace('_', ' ').title()
        subject = f"PTO Central: Your {pto_label} Request Denied"

        date_range = _format_date_range_with_days(start_date, end_date)

        # Format days nicely
        days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

        reason_row = ""
        if reason:
            reason_row = f"""
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af; vertical-align: top;">Reason:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #fca5a5;">{reason}</td>
                </tr>
            """

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {employee_name},</p>
        <p style="margin-bottom: 25px;">Unfortunately, your time off request has been <span style="color: #ef4444; font-weight: 600;">denied</span>.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {pto_label}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{days_display}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Reviewed by:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{approver_name}</td>
                </tr>
                {reason_row}
            </table>
        </div>
        """

        html = _get_email_template(
            title="Request Denied",
            title_color="#ef4444",
            content=content,
            footer_text="If you have questions, please speak with your manager."
        )
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
        pto_icon = _get_pto_type_icon(pto_type)
        pto_label = pto_type.replace('_', ' ').title()
        subject = f"PTO Central: New {pto_label} Request from {employee_name}"

        date_range = _format_date_range_with_days(start_date, end_date)

        # Format days nicely
        days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

        # Chicago Paid Leave indicator
        chicago_row = ""
        if pto_type in ('chicago_leave', 'chicago_paid_leave'):
            chicago_row = """
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Location:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">📍 Chicago (Paid Leave)</td>
                </tr>
            """

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {manager_name},</p>
        <p style="margin-bottom: 25px;">A new time off request requires your review.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Employee:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{employee_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {pto_label}</td>
                </tr>
                {chicago_row}
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td>
                </tr>
            </table>
        </div>
        """

        html = _get_email_template(
            title="New Request Pending",
            title_color="#f59e0b",
            content=content,
            footer_text="Please log in to PTO Central to approve or deny this request."
        )
        return self._send_email(manager_email, subject, html)

    def send_pto_cancelled_notification(
        self,
        manager_email: str,
        manager_name: str,
        employee_name: str,
        pto_type: str,
        start_date: date,
        end_date: date,
        total_days: float
    ) -> bool:
        """Send email to manager when an employee cancels their approved PTO."""
        pto_icon = _get_pto_type_icon(pto_type)
        pto_label = pto_type.replace('_', ' ').title()
        subject = f"PTO Central: {employee_name} Cancelled Approved {pto_label}"

        date_range = _format_date_range_with_days(start_date, end_date)

        # Format days nicely
        days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {manager_name},</p>
        <p style="margin-bottom: 25px;">An employee has <span style="color: #ef4444; font-weight: 600;">cancelled</span> their previously approved time off.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Employee:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{employee_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {pto_label}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                    <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #ef4444;">{days_display}</td>
                </tr>
            </table>
        </div>
        """

        html = _get_email_template(
            title="Approved PTO Cancelled",
            title_color="#ef4444",
            content=content,
            footer_text="The employee's PTO balance has been restored automatically."
        )
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
            msg['From'] = self.from_address
            msg['To'] = to_email

            # Build email body with dark theme
            message_html = ""
            if message:
                message_html = f"""
                <div style="background-color: #374151; padding: 15px; border-radius: 8px; border-left: 4px solid #C9A227; margin-bottom: 20px;">
                    <p style="margin: 0; color: #e5e7eb; font-style: italic;">{message}</p>
                </div>
                """

            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px; color: #e5e7eb;">Please find the attached report.</p>
            {message_html}
            """

            body_html = _get_email_template(
                title="Report",
                title_color="#C9A227",
                content=content
            )

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
                content_with_report = f"""
                <p style="font-size: 16px; margin-bottom: 20px; color: #e5e7eb;">Please find the report below:</p>
                {message_html}
                <div style="background-color: #374151; padding: 20px; border-radius: 8px; margin-top: 20px;">
                    {html_content}
                </div>
                """

                full_html = _get_email_template(
                    title="Report",
                    title_color="#C9A227",
                    content=content_with_report
                )
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.from_address
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


    # WFH Day Swap email notifications
    def send_wfh_swap_request(
        self,
        target_email: str,
        target_name: str,
        requester_name: str,
        swap_date: date,
        message: str
    ) -> bool:
        """Send email to target user when someone requests a WFH day swap."""
        day_name = swap_date.strftime('%A')
        formatted_date = _format_date_with_day(swap_date)
        subject = f"PTO Central: WFH Day Swap Request from {requester_name}"

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {target_name},</p>
        <p style="margin-bottom: 25px;">{requester_name} would like to <span style="color: #f59e0b; font-weight: 600;">swap WFH days</span> with you.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">From:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{requester_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Swap Date:</td>
                    <td style="padding: 8px 0; font-weight: 600;">🏠 {formatted_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Day Requested:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{day_name} (your WFH day)</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #374151; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #6b7280;">
            <p style="margin: 0 0 5px 0; color: #9ca3af; font-size: 12px;">Message from {requester_name}:</p>
            <p style="margin: 0; color: #e5e7eb; font-style: italic;">"{message}"</p>
        </div>
        """

        html = _get_email_template(
            title="WFH Swap Request",
            title_color="#f59e0b",
            content=content,
            footer_text="Please log in to PTO Central to accept or decline this request."
        )
        return self._send_email(target_email, subject, html)

    def send_wfh_swap_accepted(
        self,
        requester_email: str,
        requester_name: str,
        target_name: str,
        swap_date: date,
        message: str
    ) -> bool:
        """Send email to requester when target accepts the WFH day swap."""
        formatted_date = _format_date_with_day(swap_date)
        subject = f"PTO Central: {target_name} Accepted Your WFH Swap Request"

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {requester_name},</p>
        <p style="margin-bottom: 25px;">Great news! Your WFH day swap request has been <span style="color: #22c55e; font-weight: 600;">accepted</span>.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #22c55e;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Accepted by:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #22c55e;">✓ {target_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Swap Date:</td>
                    <td style="padding: 8px 0; font-weight: 600;">🏠 {formatted_date}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #374151; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #22c55e;">
            <p style="margin: 0 0 5px 0; color: #9ca3af; font-size: 12px;">Message from {target_name}:</p>
            <p style="margin: 0; color: #e5e7eb; font-style: italic;">"{message}"</p>
        </div>
        """

        html = _get_email_template(
            title="Swap Accepted",
            title_color="#22c55e",
            content=content,
            footer_text="You can now work from home on this date."
        )
        return self._send_email(requester_email, subject, html)

    def send_wfh_swap_declined(
        self,
        requester_email: str,
        requester_name: str,
        target_name: str,
        swap_date: date,
        message: str
    ) -> bool:
        """Send email to requester when target declines the WFH day swap."""
        formatted_date = _format_date_with_day(swap_date)
        subject = f"PTO Central: WFH Swap Request Declined"

        content = f"""
        <p style="font-size: 16px; margin-bottom: 20px;">Hi {requester_name},</p>
        <p style="margin-bottom: 25px;">Unfortunately, your WFH day swap request has been <span style="color: #ef4444; font-weight: 600;">declined</span>.</p>

        <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <table style="width: 100%; color: #e5e7eb;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Declined by:</td>
                    <td style="padding: 8px 0; font-weight: 600; color: #ef4444;">✗ {target_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Requested Date:</td>
                    <td style="padding: 8px 0; font-weight: 600;">🏠 {formatted_date}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #374151; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #ef4444;">
            <p style="margin: 0 0 5px 0; color: #9ca3af; font-size: 12px;">Message from {target_name}:</p>
            <p style="margin: 0; color: #e5e7eb; font-style: italic;">"{message}"</p>
        </div>
        """

        html = _get_email_template(
            title="Swap Declined",
            title_color="#ef4444",
            content=content,
            footer_text="You may want to try requesting a swap with a different teammate."
        )
        return self._send_email(requester_email, subject, html)

    def send_eoy_report(
        self,
        subject: str,
        html_content: str,
        recipient_email: str = None
    ) -> bool:
        """
        Send the EOY Assessment Report to the network administrator.

        Args:
            subject: Email subject
            html_content: Pre-formatted HTML report content
            recipient_email: Optional override for recipient (defaults to NETADMIN_EMAIL or from_email)

        Returns:
            True if sent successfully, False otherwise
        """
        # Use provided email or fall back to NETADMIN_EMAIL env var or SMTP_USER
        to_email = recipient_email or os.getenv('NETADMIN_EMAIL', self.smtp_user)

        if not to_email:
            logger.error("No recipient email configured for EOY report")
            return False

        # Wrap the report content in a full HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 20px; background-color: #111827; color: white;">
            {html_content}
        </body>
        </html>
        """

        return self._send_email(to_email, subject, full_html)


# Global instance
email_service = EmailService()
