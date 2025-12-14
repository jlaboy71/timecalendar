"""
Handbook Revision model for tracking handbook updates.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class HandbookRevision(Base):
    """
    Tracks revisions to the employee handbook.

    Stores each version of the handbook content with metadata
    about who made changes, when, and what changed.
    """
    __tablename__ = "handbook_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Version info
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Version number (e.g., '1.0', '1.1')"
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full handbook content in markdown format"
    )

    # Change tracking
    change_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated summary of changes from previous version"
    )
    change_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed list of specific changes (JSON)"
    )

    # Metadata
    created_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this is the currently active version"
    )

    # Relationships
    author = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<HandbookRevision(version={self.version}, active={self.is_active})>"
