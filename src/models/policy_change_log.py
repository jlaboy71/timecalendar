"""
Policy Change Log model for tracking policy value changes.

Tracks changes to leave policies with before/after values,
enabling 30-day visibility windows and revert detection.
"""
from datetime import datetime, date, timedelta
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from .user import User


class PolicyChangeLog(Base):
    """
    Records policy changes with before/after values for tracking and display.

    Used to show change indicators (badges, tooltips) on policy values
    for 30 days after a change is published.
    """
    __tablename__ = "policy_change_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Version tracking
    handbook_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Version identifier (e.g., 'v2.5')"
    )

    # Policy identification
    policy_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Policy field identifier (e.g., 'sick_carryover_max', 'vacation_days')"
    )

    # Location scope (NULL = default/all employees)
    location_state: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="State code or NULL for all states"
    )
    location_city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="City name or NULL for state-wide/all"
    )

    # Change values (stored as strings for flexibility)
    old_value: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Previous value as string"
    )
    new_value: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="New value as string"
    )

    # Human-readable display values
    old_value_display: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Previous value formatted for display (e.g., '80 hrs')"
    )
    new_value_display: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="New value formatted for display (e.g., '56 hrs')"
    )

    # Effective date and reason
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="When the policy change takes effect"
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Admin-provided or AI-detected reason for change"
    )

    # AI-generated friendly summary
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Claude-generated friendly explanation for employees"
    )

    # Tracking
    changed_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="Admin who published the change"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    # Display window (30 days from creation)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When change indicator stops displaying (created_at + 30 days)"
    )

    # Revert tracking
    is_revert: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this change reverts to a previous version"
    )
    reverted_to_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="If is_revert=True, which version was restored"
    )

    # Link to handbook upload that created this change
    handbook_upload_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("handbook_uploads.id"),
        nullable=True,
        comment="Source handbook upload"
    )

    # Relationships
    changed_by_user: Mapped["User"] = relationship("User", foreign_keys=[changed_by])

    def __repr__(self) -> str:
        return f"<PolicyChangeLog(policy_type='{self.policy_type}', {self.old_value_display}→{self.new_value_display})>"

    @property
    def is_active(self) -> bool:
        """Check if change indicator should still be displayed."""
        return datetime.utcnow() < self.expires_at

    @classmethod
    def create_with_expiration(
        cls,
        policy_type: str,
        handbook_version: str,
        old_value: str,
        new_value: str,
        old_value_display: str,
        new_value_display: str,
        effective_date: date,
        changed_by: int,
        location_state: Optional[str] = None,
        location_city: Optional[str] = None,
        reason: Optional[str] = None,
        ai_summary: Optional[str] = None,
        is_revert: bool = False,
        reverted_to_version: Optional[str] = None,
        handbook_upload_id: Optional[int] = None,
        display_days: int = 30
    ) -> "PolicyChangeLog":
        """
        Factory method to create a change log entry with automatic expiration.

        Args:
            display_days: Number of days to show the change indicator (default 30)
        """
        now = datetime.utcnow()
        return cls(
            policy_type=policy_type,
            handbook_version=handbook_version,
            old_value=old_value,
            new_value=new_value,
            old_value_display=old_value_display,
            new_value_display=new_value_display,
            effective_date=effective_date,
            changed_by=changed_by,
            location_state=location_state,
            location_city=location_city,
            reason=reason,
            ai_summary=ai_summary,
            is_revert=is_revert,
            reverted_to_version=reverted_to_version,
            handbook_upload_id=handbook_upload_id,
            created_at=now,
            expires_at=now + timedelta(days=display_days)
        )
