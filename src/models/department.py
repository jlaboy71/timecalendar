"""
Department model for the PTO and Market Calendar System.
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class Department(Base):
    """
    Department model representing organizational departments.
    
    This model stores department information including name, code,
    manager assignment, and active status.
    """
    __tablename__ = "departments"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Department information
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Manager assignment
    manager_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(), 
        nullable=False
    )
    
    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User", 
        back_populates="department",
        foreign_keys="User.department_id"
    )
    manager: Mapped[Optional["User"]] = relationship(
        "User", 
        foreign_keys=[manager_id]
    )
    
    def __repr__(self) -> str:
        """String representation of the Department model."""
        return f"<Department(id={self.id}, name='{self.name}', code='{self.code}')>"
