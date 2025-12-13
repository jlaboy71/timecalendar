"""
Pending notification model for PTO digest queue.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User
    from .pto_request import PTORequest


class PendingNotification(Base):
    """
    Queue for PTO request notifications to be sent in digest emails.

    When a PTO request is submitted and the manager prefers digest
    notifications (daily, weekly, etc.), notifications are queued here
    and processed by the scheduler.
    """
    __tablename__ = "pending_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Manager to notify
    manager_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # PTO request that triggered the notification
    pto_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pto_requests.id"),
        nullable=False,
        index=True
    )

    # When notification was queued
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    # Whether notification has been sent
    sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # When notification was sent (null if not sent)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    # Relationships
    manager: Mapped["User"] = relationship("User", foreign_keys=[manager_id])
    pto_request: Mapped["PTORequest"] = relationship("PTORequest")

    # Index for efficient digest processing
    __table_args__ = (
        Index('ix_pending_notifications_manager_sent', 'manager_id', 'sent'),
    )

    def __repr__(self) -> str:
        return f"<PendingNotification(id={self.id}, manager_id={self.manager_id}, sent={self.sent})>"
