"""
Audit log model for tracking system actions.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AuditLog(Base):
    """
    Audit log model for tracking important system actions.

    Tracks who did what, when, and captures relevant details
    for compliance and debugging purposes.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Who performed the action
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # What action was performed
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g., 'login', 'logout', 'pto_request', 'pto_approve', 'pto_deny',
    #       'user_create', 'user_update', 'user_delete', 'dept_create', etc.

    # What entity was affected
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    # e.g., 'user', 'pto_request', 'department', 'carryover_request'

    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional details (JSON-serializable string)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # IP address (for login tracking)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        index=True
    )

    def __repr__(self) -> str:
        """String representation of the AuditLog model."""
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"
