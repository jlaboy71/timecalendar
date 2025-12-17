"""
PTO Balance model for the PTO and Market Calendar System.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class PTOBalance(Base):
    """
    PTO Balance model representing employee PTO balances by year.
    
    This model tracks various types of PTO balances including vacation,
    sick leave, personal days, and remote work usage for each employee by year.
    """
    __tablename__ = "pto_balances"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False,
        index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Vacation balances
    vacation_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00'), 
        nullable=False
    )
    vacation_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00'), 
        nullable=False
    )
    vacation_pending: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00'), 
        nullable=False
    )
    
    # Sick leave balances
    sick_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False
    )
    sick_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False
    )
    sick_pending: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Sick hours in pending requests'
    )

    # Personal day balances
    personal_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False
    )
    personal_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False
    )
    personal_pending: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Personal hours in pending requests'
    )

    # Carryover balances (hours carried from previous year)
    vacation_carryover: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Vacation hours carried over from previous year'
    )
    sick_carryover: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Sick hours carried over from previous year'
    )
    personal_carryover: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Personal hours carried over from previous year'
    )

    # Chicago Paid Sick and Safe Leave (separate bank per Chicago ordinance)
    # Health-related use only, 80hr max carryover
    chicago_safe_leave_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Sick & Safe Leave hours allocated for the year'
    )
    chicago_safe_leave_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Sick & Safe Leave hours used'
    )
    chicago_safe_leave_pending: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Sick & Safe Leave hours in pending requests'
    )
    chicago_safe_leave_carryover: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Sick & Safe Leave hours carried over (max 80 hrs per ordinance)'
    )

    # Chicago Paid Leave for Any Reason (separate bank per Chicago ordinance)
    # Any reason use allowed, 16hr max carryover
    chicago_paid_leave_total: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Paid Leave hours allocated for the year (40hr max)'
    )
    chicago_paid_leave_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Paid Leave hours used'
    )
    chicago_paid_leave_pending: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Paid Leave hours in pending requests'
    )
    chicago_paid_leave_carryover: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal('0.00'),
        nullable=False,
        comment='Chicago Paid Leave hours carried over (max 16 hrs per ordinance)'
    )

    # Remote work tracking
    remote_weekly_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
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
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'year', name='uq_user_year'),
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pto_balances")
    
    def __repr__(self) -> str:
        """String representation of the PTOBalance model."""
        return f"<PTOBalance(id={self.id}, user_id={self.user_id}, year={self.year})>"
    
    @property
    def vacation_available(self) -> Decimal:
        """Calculate available vacation days (including carryover)."""
        return self.vacation_total + self.vacation_carryover - self.vacation_used - self.vacation_pending

    @property
    def sick_available(self) -> Decimal:
        """Calculate available sick days (including carryover, minus pending)."""
        return self.sick_total + self.sick_carryover - self.sick_used - self.sick_pending

    @property
    def personal_available(self) -> Decimal:
        """Calculate available personal days (including carryover, minus pending)."""
        return self.personal_total + self.personal_carryover - self.personal_used - self.personal_pending

    @property
    def chicago_safe_leave_available(self) -> Decimal:
        """Calculate available Chicago Sick & Safe Leave hours (including carryover, minus pending)."""
        return self.chicago_safe_leave_total + self.chicago_safe_leave_carryover - self.chicago_safe_leave_used - self.chicago_safe_leave_pending

    @property
    def chicago_paid_leave_available(self) -> Decimal:
        """Calculate available Chicago Paid Leave hours (including carryover, minus pending)."""
        return self.chicago_paid_leave_total + self.chicago_paid_leave_carryover - self.chicago_paid_leave_used - self.chicago_paid_leave_pending
