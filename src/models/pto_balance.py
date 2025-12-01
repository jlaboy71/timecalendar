"""
PTO Balance model for the PTO and Market Calendar System.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


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
        """Calculate available vacation days."""
        return self.vacation_total - self.vacation_used - self.vacation_pending
    
    @property
    def sick_available(self) -> Decimal:
        """Calculate available sick days."""
        return self.sick_total - self.sick_used
    
    @property
    def personal_available(self) -> Decimal:
        """Calculate available personal days."""
        return self.personal_total - self.personal_used
