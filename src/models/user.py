"""
User model for the PTO and Market Calendar System.
"""
from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .department import Department
    from .pto_request import PTORequest
    from .pto_balance import PTOBalance


class User(Base):
    """
    User model representing employees in the PTO system.
    
    This model stores user information including authentication details,
    personal information, department association, and role-based access.
    """
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Authentication fields
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Personal information
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Department and role
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("departments.id"), 
        nullable=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    
    # Employment information
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    anniversary_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remote_schedule: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Location information (for state-specific leave policies)
    location_state: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="State code: IL, NY, CT, FL"
    )
    location_city: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="City name (e.g., Chicago for IL-specific rules)"
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
    department: Mapped[Optional["Department"]] = relationship(
        "Department", 
        back_populates="users",
        foreign_keys=[department_id]
    )
    pto_requests: Mapped[List["PTORequest"]] = relationship(
        "PTORequest", 
        back_populates="user",
        foreign_keys="PTORequest.user_id"
    )
    approved_requests: Mapped[List["PTORequest"]] = relationship(
        "PTORequest", 
        back_populates="approver",
        foreign_keys="PTORequest.approved_by"
    )
    pto_balances: Mapped[List["PTOBalance"]] = relationship(
        "PTOBalance", 
        back_populates="user"
    )
    
    def __repr__(self) -> str:
        """String representation of the User model."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"
