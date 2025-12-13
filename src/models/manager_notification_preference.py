"""
Manager notification preference model for PTO digest settings.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class ManagerNotificationPreference(Base):
    """
    Stores manager preferences for PTO request notifications.

    Managers can configure:
    - Digest frequency (immediate, daily, weekly, biweekly, monthly)
    - Preferred send time for digests
    - Export format (pdf, csv, html)
    """
    __tablename__ = "manager_notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Manager reference (one preference record per manager)
    manager_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True
    )

    # Digest frequency: 'immediate', 'daily', 'weekly', 'biweekly', 'monthly'
    digest_frequency: Mapped[str] = mapped_column(
        String(20),
        default='immediate',
        nullable=False
    )

    # For daily/weekly digests - preferred send time (hour in 24h format)
    preferred_hour: Mapped[int] = mapped_column(
        Integer,
        default=8,  # 8 AM default
        nullable=False
    )

    # For weekly digest - preferred day (0=Monday, 6=Sunday)
    preferred_day: Mapped[int] = mapped_column(
        Integer,
        default=0,  # Monday default
        nullable=False
    )

    # Export format: 'pdf', 'csv', 'html'
    export_format: Mapped[str] = mapped_column(
        String(10),
        default='pdf',
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    manager: Mapped["User"] = relationship("User", foreign_keys=[manager_id])

    def __repr__(self) -> str:
        return f"<ManagerNotificationPreference(manager_id={self.manager_id}, frequency='{self.digest_frequency}')>"
