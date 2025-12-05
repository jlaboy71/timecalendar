"""
Carryover Request model for manager-approved vacation carryover.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from .user import User
    from .leave_type import LeaveType


class CarryoverRequest(Base):
    """
    Tracks employee requests to carry over unused leave.

    From Haventech Handbook:
    - Vacation carryover requires prior written approval from management
    - Default: No carryover allowed
    - Chicago employees: Up to 16 hours automatic carryover
    """
    __tablename__ = "carryover_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Employee and leave type
    employee_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    leave_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leave_types.id"),
        nullable=False
    )

    # Year transition
    from_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Year the hours are coming from"
    )
    to_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Year the hours are carrying into"
    )

    # Hours
    hours_requested: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    hours_approved: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="May differ from requested"
    )

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending, approved, denied"
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Notes
    employee_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for carryover request"
    )
    manager_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Approval/denial notes"
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
    employee: Mapped["User"] = relationship(
        "User",
        foreign_keys=[employee_id],
        backref="carryover_requests"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by]
    )
    leave_type: Mapped["LeaveType"] = relationship("LeaveType")

    def __repr__(self) -> str:
        return f"<CarryoverRequest(employee_id={self.employee_id}, {self.from_year}->{self.to_year}, {self.hours_requested}hrs)>"
