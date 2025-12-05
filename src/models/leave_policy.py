"""
Leave Policy model for state/city-specific leave rules.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from .leave_type import LeaveType


class LeavePolicy(Base):
    """
    State and city-specific leave policy configurations.

    Policy resolution order:
    1. City-specific (e.g., location_city='Chicago')
    2. State-specific (e.g., location_state='IL')
    3. Default (location_state=NULL, location_city=NULL)
    """
    __tablename__ = "leave_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Link to leave type
    leave_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leave_types.id"),
        nullable=False,
        index=True
    )

    # Location scope (NULL = default policy)
    location_state: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="State code or NULL for default"
    )
    location_city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="City name or NULL for state-wide"
    )

    # Accrual configuration
    accrual_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Hours accrued per period"
    )
    accrual_period: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="monthly, per_hours_worked"
    )
    accrual_hours_divisor: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="For per_hours_worked: 40, 35, or 30"
    )

    # Limits
    max_annual_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Maximum hours that can be accrued per year"
    )
    max_carryover_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Maximum hours that can roll over"
    )

    # Usage rules
    waiting_period_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Days before leave can be used (e.g., 90 for probation)"
    )
    min_increment_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 2),
        nullable=True,
        comment="Minimum request size (e.g., 2.0 or 4.0 hours)"
    )
    max_increment_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Maximum single request (NULL = unlimited)"
    )
    advance_notice_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Required advance notice (e.g., 14 days for vacation)"
    )

    # Validity period
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date()
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="NULL = currently active"
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
    leave_type: Mapped["LeaveType"] = relationship("LeaveType")

    def __repr__(self) -> str:
        location = f"{self.location_city or ''}, {self.location_state or 'DEFAULT'}".strip(", ")
        return f"<LeavePolicy(leave_type_id={self.leave_type_id}, location='{location}')>"
