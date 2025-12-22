"""
WFH Day Swap Request model for the PTO Central System.

Allows employees to swap their designated WFH days with colleagues.
This is a peer-to-peer system - no manager approval required.
"""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Integer, String, Text, Date, DateTime,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class WFHDaySwapRequest(Base):
    """
    WFH Day Swap Request model for tracking employee WFH day exchanges.

    Allows employees to swap their designated WFH days with colleagues,
    with full messaging support and audit trail.

    Flow:
    1. Requester selects a date they want to WFH (not their normal day)
    2. System shows employees who have that day as their WFH day
    3. Requester sends request with required message
    4. Target employee accepts or declines with required response
    5. Both parties are notified of the outcome
    """
    __tablename__ = "wfh_day_swap_requests"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Participants
    requester_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Employee initiating the swap request"
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Employee being asked to swap"
    )

    # Swap details
    swap_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="The date for which the swap is requested"
    )
    requester_original_day: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Requester's normal WFH day (monday, tuesday, etc.)"
    )
    target_original_day: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Target's normal WFH day (the day requester wants)"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, accepted, declined, cancelled, expired"
    )

    # Bidirectional messaging
    request_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Required message from requester explaining the swap need"
    )
    response_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Response message from target (required on accept/decline)"
    )

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        index=True
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Auto-expiration datetime (3 business days from request)"
    )

    # Relationships
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
        backref="wfh_swap_requests_sent"
    )
    target_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[target_user_id],
        backref="wfh_swap_requests_received"
    )

    # Indexes for performance
    __table_args__ = (
        Index('idx_wfh_swap_date_status', 'swap_date', 'status'),
        Index('idx_wfh_swap_requester_status', 'requester_id', 'status'),
        Index('idx_wfh_swap_target_status', 'target_user_id', 'status'),
    )

    def __repr__(self) -> str:
        return (
            f"<WFHDaySwapRequest(id={self.id}, "
            f"requester={self.requester_id}, target={self.target_user_id}, "
            f"date={self.swap_date}, status='{self.status}')>"
        )

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_accepted(self) -> bool:
        return self.status == "accepted"

    @property
    def is_declined(self) -> bool:
        return self.status == "declined"

    @property
    def is_expired(self) -> bool:
        return self.status == "expired"

    @property
    def can_respond(self) -> bool:
        """Check if the request can still be responded to."""
        if self.status != "pending":
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    @property
    def can_cancel(self) -> bool:
        """Check if the request can be cancelled by requester."""
        return self.status == "pending"
