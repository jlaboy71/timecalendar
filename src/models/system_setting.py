"""
System Setting model for feature toggles and configuration.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class SystemSetting(Base):
    """
    System settings for feature toggles and global configuration.

    Key naming convention: category.setting_name (e.g., 'chicago.safe_leave_enabled')
    """
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit fields
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}', value='{self.value}')>"

    @property
    def bool_value(self) -> bool:
        """Get value as boolean."""
        return self.value.lower() in ('true', '1', 'yes', 'on')

    @property
    def int_value(self) -> int:
        """Get value as integer."""
        try:
            return int(self.value)
        except ValueError:
            return 0
