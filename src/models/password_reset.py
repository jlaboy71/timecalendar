"""
Password reset token model for secure password resets.
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class PasswordResetToken(Base):
    """
    Model for storing password reset tokens.

    Tokens are single-use and expire after a configurable time period.
    """
    __tablename__ = "password_reset_tokens"

    # Token expires after this many hours
    EXPIRY_HOURS = 24

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User this token is for
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # The secure token (hashed for storage)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # Who created this reset (admin user id, or None if self-service)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Whether token has been used
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship to user
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, used={self.used})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.used and not self.is_expired

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    @classmethod
    def calculate_expiry(cls) -> datetime:
        """Calculate expiry time based on EXPIRY_HOURS."""
        return datetime.now() + timedelta(hours=cls.EXPIRY_HOURS)
