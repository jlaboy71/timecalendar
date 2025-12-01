"""
PTO Request model for the PTO and Market Calendar System.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Date, DateTime, Numeric, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class PTORequest(Base):
    """
    PTO Request model representing employee time-off requests.
    
    This model stores PTO request information including dates, type,
    approval status, and related metadata for tracking and approval workflow.
    """
    __tablename__ = "pto_requests"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False,
        index=True
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True
    )
    
    # Request details
    pto_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_days: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    
    # Status and approval
    status: Mapped[str] = mapped_column(
        String(20), 
        default="pending", 
        nullable=False,
        index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    denial_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(), 
        nullable=False
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="pto_requests",
        foreign_keys=[user_id]
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", 
        back_populates="approved_requests",
        foreign_keys=[approved_by]
    )
    
    def __repr__(self) -> str:
        """String representation of the PTORequest model."""
        return (f"<PTORequest(id={self.id}, user_id={self.user_id}, "
                f"type='{self.pto_type}', status='{self.status}')>")
    
    @property
    def duration_days(self) -> int:
        """Calculate the number of calendar days for this request."""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_pending(self) -> bool:
        """Check if the request is pending approval."""
        return self.status == "pending"
    
    @property
    def is_approved(self) -> bool:
        """Check if the request is approved."""
        return self.status == "approved"
    
    @property
    def is_denied(self) -> bool:
        """Check if the request is denied."""
        return self.status == "denied"
