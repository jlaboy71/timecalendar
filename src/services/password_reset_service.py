"""
Password reset service for managing password reset tokens.
"""
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from src.models.password_reset import PasswordResetToken
from src.models.user import User
from src.utils.password import hash_password


class PasswordResetService:
    """Service for managing password reset tokens and resets."""

    def __init__(self, db: Session):
        self.db = db

    def create_reset_token(self, user_id: int, created_by: Optional[int] = None) -> Tuple[str, PasswordResetToken]:
        """
        Create a new password reset token for a user.

        Args:
            user_id: ID of user who needs password reset
            created_by: ID of admin creating the reset (None if self-service)

        Returns:
            Tuple of (plain_token, token_record)
            The plain_token should be given to the user (only shown once)
        """
        # Invalidate any existing unused tokens for this user
        stmt = update(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used == False
        ).values(used=True, used_at=datetime.now())
        self.db.execute(stmt)

        # Generate new token
        plain_token = PasswordResetToken.generate_token()

        # Create token record
        token_record = PasswordResetToken(
            user_id=user_id,
            token=plain_token,  # In production, you might want to hash this
            created_by=created_by,
            expires_at=PasswordResetToken.calculate_expiry()
        )

        self.db.add(token_record)
        self.db.commit()
        self.db.refresh(token_record)

        return plain_token, token_record

    def validate_token(self, token: str) -> Tuple[bool, Optional[User], str]:
        """
        Validate a password reset token.

        Args:
            token: The token to validate

        Returns:
            Tuple of (is_valid, user, error_message)
        """
        stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
        token_record = self.db.execute(stmt).scalar_one_or_none()

        if not token_record:
            return False, None, "Invalid or expired reset link"

        if token_record.used:
            return False, None, "This reset link has already been used"

        if token_record.is_expired:
            return False, None, "This reset link has expired"

        stmt = select(User).where(User.id == token_record.user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if not user:
            return False, None, "User not found"

        if not user.is_active:
            return False, None, "This account has been deactivated"

        return True, user, ""

    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset a user's password using a valid token.

        Args:
            token: The reset token
            new_password: The new password to set

        Returns:
            Tuple of (success, message)
        """
        is_valid, user, error_message = self.validate_token(token)

        if not is_valid:
            return False, error_message

        # Update user's password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now()

        # Mark token as used
        stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
        token_record = self.db.execute(stmt).scalar_one_or_none()
        token_record.used = True
        token_record.used_at = datetime.now()

        self.db.commit()

        return True, "Password reset successfully"

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        stmt = select(User).where(User.email == email, User.is_active == True)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username."""
        stmt = select(User).where(User.username == username, User.is_active == True)
        return self.db.execute(stmt).scalar_one_or_none()

    def admin_reset_password(self, user_id: int, new_password: str, admin_id: int) -> Tuple[bool, str]:
        """
        Admin directly resets a user's password (no token needed).

        Args:
            user_id: ID of user to reset
            new_password: New password to set
            admin_id: ID of admin performing the reset

        Returns:
            Tuple of (success, message)
        """
        stmt = select(User).where(User.id == user_id)
        user = self.db.execute(stmt).scalar_one_or_none()

        if not user:
            return False, "User not found"

        # Update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now()

        self.db.commit()

        return True, f"Password reset for {user.username}"
