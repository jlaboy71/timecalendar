"""
Handbook Upload model for tracking uploaded handbook documents.

Stores uploaded handbooks with AI-extracted policy values,
enabling version control and revert detection via file hash.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base

if TYPE_CHECKING:
    from .user import User
    from .policy_change_log import PolicyChangeLog


class HandbookUpload(Base):
    """
    Records uploaded handbook documents with extracted policy data.

    Used for version control, AI analysis results storage,
    and revert detection via file hash comparison.
    """
    __tablename__ = "handbook_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Version identification
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="Version identifier (e.g., 'v2.5')"
    )

    # File information
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original uploaded filename"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Storage path for the uploaded file"
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash for duplicate/revert detection"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes"
    )

    # AI analysis results (stored as JSON)
    extracted_policies: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="AI-extracted policy values as JSON"
    )
    ai_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Full Claude analysis response as JSON"
    )
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Claude-generated summary of the handbook"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, analyzing, ready, published, reverted, error"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if status='error'"
    )

    # Upload tracking
    uploaded_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="Admin who uploaded the handbook"
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    # Publication tracking
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When changes were published"
    )
    published_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="Admin who published the changes"
    )

    # Revert relationship
    is_revert_of: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("handbook_uploads.id"),
        nullable=True,
        comment="If this upload reverts to a previous version"
    )

    # Detected as duplicate of existing version
    detected_duplicate_of: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Version string if file hash matches previous upload"
    )

    # Relationships
    uploader: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by])
    publisher: Mapped[Optional["User"]] = relationship("User", foreign_keys=[published_by])
    reverted_upload: Mapped[Optional["HandbookUpload"]] = relationship(
        "HandbookUpload",
        remote_side=[id],
        foreign_keys=[is_revert_of]
    )
    policy_changes: Mapped[List["PolicyChangeLog"]] = relationship(
        "PolicyChangeLog",
        foreign_keys="PolicyChangeLog.handbook_upload_id",
        backref="handbook_upload"
    )

    def __repr__(self) -> str:
        return f"<HandbookUpload(version='{self.version}', status='{self.status}')>"

    @property
    def is_published(self) -> bool:
        """Check if this handbook has been published."""
        return self.status == "published" and self.published_at is not None

    @property
    def is_ready_to_publish(self) -> bool:
        """Check if handbook is analyzed and ready for publishing."""
        return self.status == "ready" and self.extracted_policies is not None

    @property
    def change_count(self) -> int:
        """Count of detected policy changes from this upload."""
        if not self.extracted_policies:
            return 0
        return self.extracted_policies.get("change_count", 0)

    def get_changes_summary(self) -> List[dict]:
        """Get list of detected changes for preview."""
        if not self.extracted_policies:
            return []
        return self.extracted_policies.get("changes", [])
