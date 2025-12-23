"""
Manager notification service for PTO request alerts and digest emails.
"""
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.user import User
from src.models.pto_request import PTORequest
from src.models.manager_notification_preference import ManagerNotificationPreference
from src.models.pending_notification import PendingNotification
from src.services.email_service import EmailService
from src.services.export_service import ExportService
from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing PTO request notifications to managers."""

    # PTO types eligible for trusted auto-approve
    TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()

    def get_manager_preferences(self, manager_id: int) -> ManagerNotificationPreference:
        """
        Get or create default notification preferences for a manager.

        Args:
            manager_id: ID of the manager

        Returns:
            ManagerNotificationPreference record
        """
        stmt = select(ManagerNotificationPreference).where(
            ManagerNotificationPreference.manager_id == manager_id
        )
        prefs = self.db.execute(stmt).scalar_one_or_none()

        if not prefs:
            prefs = ManagerNotificationPreference(manager_id=manager_id)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)

        return prefs

    def update_preferences(
        self,
        manager_id: int,
        digest_frequency: Optional[str] = None,
        preferred_hour: Optional[int] = None,
        preferred_day: Optional[int] = None,
        export_format: Optional[str] = None,
        auto_notify_report_frequency: Optional[str] = None
    ) -> ManagerNotificationPreference:
        """
        Update manager notification preferences.

        Args:
            manager_id: ID of the manager
            digest_frequency: 'immediate', 'daily', 'weekly', 'biweekly', 'monthly'
            preferred_hour: Hour (0-23) for digest delivery
            preferred_day: Day of week (0=Mon, 6=Sun) for weekly digests
            export_format: 'pdf', 'csv', 'html'
            auto_notify_report_frequency: 'weekly', 'bi-weekly', 'monthly' for trusted employee reports

        Returns:
            Updated preference record
        """
        prefs = self.get_manager_preferences(manager_id)

        if digest_frequency:
            prefs.digest_frequency = digest_frequency
        if preferred_hour is not None:
            prefs.preferred_hour = preferred_hour
        if preferred_day is not None:
            prefs.preferred_day = preferred_day
        if export_format:
            prefs.export_format = export_format
        if auto_notify_report_frequency:
            prefs.auto_notify_report_frequency = auto_notify_report_frequency

        prefs.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(prefs)
        return prefs

    def queue_notification(self, manager_id: int, pto_request_id: int) -> PendingNotification:
        """
        Add a notification to the digest queue.

        Args:
            manager_id: ID of the manager to notify
            pto_request_id: ID of the PTO request

        Returns:
            PendingNotification record
        """
        notification = PendingNotification(
            manager_id=manager_id,
            pto_request_id=pto_request_id
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_employee_manager(self, employee: User) -> Optional[User]:
        """
        Get the manager for an employee (via department).

        Args:
            employee: The employee user

        Returns:
            Manager user or None
        """
        if not employee.department_id:
            return None

        dept = employee.department
        if not dept or not dept.manager_id:
            return None

        stmt = select(User).where(User.id == dept.manager_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def notify_manager_of_request(self, request: PTORequest, employee: User):
        """
        Queue or send notification to manager for a PTO request.

        This is called when a PTO request is submitted. Based on the
        manager's preferences, it either sends immediately or queues
        for the digest.

        Args:
            request: The PTO request
            employee: The employee who submitted it
        """
        manager = self.get_employee_manager(employee)
        if not manager:
            logger.warning(f"No manager found for employee {employee.id}")
            return

        prefs = self.get_manager_preferences(manager.id)

        if prefs.digest_frequency == 'immediate':
            self._send_immediate_notification(manager, request, employee)
        else:
            self.queue_notification(manager.id, request.id)
            logger.info(f"Queued notification for manager {manager.id}, request {request.id}")

    def _send_immediate_notification(self, manager: User, request: PTORequest, employee: User):
        """
        Send immediate email notification for a single request.

        Args:
            manager: The manager to notify
            request: The PTO request
            employee: The employee who submitted it
        """
        is_trusted = employee.is_trusted and request.pto_type.lower() in self.TRUSTED_AUTO_APPROVE_TYPES

        if is_trusted:
            subject = f"PTO Auto-Approved: {employee.full_name} - {request.pto_type.title()}"
            status_text = "Auto-Approved (Trusted Employee)"
        else:
            subject = f"PTO Request Pending: {employee.full_name} - {request.pto_type.title()}"
            status_text = "Pending Your Approval"

        # Use existing email service method
        self.email_service.send_pending_request_notification(
            manager_email=manager.email,
            manager_name=manager.full_name,
            employee_name=employee.full_name,
            pto_type=request.pto_type,
            start_date=request.start_date,
            end_date=request.end_date,
            total_days=float(request.total_days)
        )

    def process_digests(self):
        """
        Process all pending digest notifications.

        Called by the scheduler to send digest emails to managers
        whose preferred time has arrived.
        """
        # Get all managers with pending notifications
        stmt = select(PendingNotification.manager_id).where(
            PendingNotification.sent == False
        ).distinct()

        manager_ids = [row[0] for row in self.db.execute(stmt).fetchall()]
        logger.info(f"Processing digests for {len(manager_ids)} managers")

        for manager_id in manager_ids:
            try:
                prefs = self.get_manager_preferences(manager_id)

                if self._should_send_digest(prefs):
                    self._send_digest(manager_id, prefs)
            except Exception as e:
                logger.error(f"Error processing digest for manager {manager_id}: {e}")

    def _should_send_digest(self, prefs: ManagerNotificationPreference) -> bool:
        """
        Check if it's time to send digest based on preferences.

        Args:
            prefs: Manager's notification preferences

        Returns:
            True if digest should be sent now
        """
        now = datetime.now()

        if prefs.digest_frequency == 'immediate':
            return False  # Immediate is handled separately
        elif prefs.digest_frequency == 'daily':
            return now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'weekly':
            return now.weekday() == prefs.preferred_day and now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'biweekly':
            # Send on 1st and 15th
            return now.day in [1, 15] and now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'monthly':
            return now.day == 1 and now.hour == prefs.preferred_hour

        return False

    def _send_digest(self, manager_id: int, prefs: ManagerNotificationPreference):
        """
        Send digest email with all pending notifications.

        Args:
            manager_id: ID of the manager
            prefs: Manager's notification preferences
        """
        # Get pending notifications
        stmt = select(PendingNotification).where(
            PendingNotification.manager_id == manager_id,
            PendingNotification.sent == False
        )
        pending = self.db.execute(stmt).scalars().all()

        if not pending:
            return

        # Get manager
        manager = self.db.execute(select(User).where(User.id == manager_id)).scalar_one()

        # Get all PTO requests
        request_ids = [p.pto_request_id for p in pending]
        requests = self.db.execute(
            select(PTORequest).where(PTORequest.id.in_(request_ids))
        ).scalars().all()

        if not requests:
            return

        logger.info(f"Sending digest to {manager.email} with {len(requests)} requests")

        # Generate report content
        html_content = self._generate_digest_html(requests)

        # Generate attachment based on preferred format
        attachment_data = None
        attachment_name = None
        attachment_type = prefs.export_format

        if prefs.export_format == 'pdf':
            attachment_data = ExportService.generate_report_pdf(html_content, "PTO Digest Report")
            attachment_name = f"pto_digest_{datetime.now().strftime('%Y%m%d')}.pdf"
        elif prefs.export_format == 'csv':
            csv_data = self._generate_digest_csv(requests)
            attachment_data = csv_data.encode('utf-8')
            attachment_name = f"pto_digest_{datetime.now().strftime('%Y%m%d')}.csv"
        else:  # html
            attachment_data = html_content.encode('utf-8')
            attachment_name = f"pto_digest_{datetime.now().strftime('%Y%m%d')}.html"

        # Send email
        subject = f"PTO Request Digest - {len(requests)} Request(s)"

        self.email_service.send_report_email(
            to_email=manager.email,
            subject=subject,
            html_content=html_content,
            attachment_data=attachment_data,
            attachment_name=attachment_name,
            attachment_type=attachment_type
        )

        # Mark as sent
        for notification in pending:
            notification.sent = True
            notification.sent_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Digest sent to {manager.email}, marked {len(pending)} notifications as sent")

    def _generate_digest_html(self, requests: List[PTORequest]) -> str:
        """Generate HTML content for digest email."""
        rows = ""
        for req in requests:
            trusted_badge = '<span style="color: #22c55e; font-weight: bold;">[TRUSTED]</span> ' if req.user.is_trusted else ''
            status_color = '#22c55e' if req.status == 'approved' else '#f59e0b'

            rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{trusted_badge}{req.user.full_name}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{req.pto_type.title()}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{req.start_date.strftime('%b %d, %Y')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{req.end_date.strftime('%b %d, %Y')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{req.total_days}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: {status_color};">{req.status.title()}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PTO Digest - {datetime.now().strftime('%Y-%m-%d')}</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="background-color: {PTO_GRAY}; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">PTO Request Digest</h1>
            </div>
            <div style="padding: 20px;">
                <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <p>You have <strong>{len(requests)}</strong> PTO request(s) to review:</p>
                <table style="border-collapse: collapse; width: 100%; margin-top: 15px;">
                    <tr style="background-color: {PTO_GOLD}; color: white;">
                        <th style="padding: 10px; text-align: left;">Employee</th>
                        <th style="padding: 10px; text-align: left;">Type</th>
                        <th style="padding: 10px; text-align: left;">Start Date</th>
                        <th style="padding: 10px; text-align: left;">End Date</th>
                        <th style="padding: 10px; text-align: left;">Days</th>
                        <th style="padding: 10px; text-align: left;">Status</th>
                    </tr>
                    {rows}
                </table>
                <p style="margin-top: 20px;">Please log in to PTO Central to review pending requests.</p>
            </div>
        </body>
        </html>
        """

    def _generate_digest_csv(self, requests: List[PTORequest]) -> str:
        """Generate CSV content for digest email."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Employee', 'Type', 'Start Date', 'End Date', 'Days', 'Status', 'Trusted'])

        for req in requests:
            writer.writerow([
                req.user.full_name,
                req.pto_type,
                req.start_date.isoformat(),
                req.end_date.isoformat(),
                float(req.total_days),
                req.status,
                'Yes' if req.user.is_trusted else 'No'
            ])

        return output.getvalue()

    def force_send_digest(self, manager_id: int) -> int:
        """
        Force send digest to a manager regardless of schedule.

        Useful for testing or manual triggers.

        Args:
            manager_id: ID of the manager

        Returns:
            Number of notifications sent
        """
        prefs = self.get_manager_preferences(manager_id)

        # Get pending count before
        stmt = select(PendingNotification).where(
            PendingNotification.manager_id == manager_id,
            PendingNotification.sent == False
        )
        pending = self.db.execute(stmt).scalars().all()
        count = len(pending)

        if count > 0:
            self._send_digest(manager_id, prefs)

        return count
