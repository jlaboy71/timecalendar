"""
Leave Type model for configurable PTO categories.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class LeaveType(Base):
    """
    Configurable leave type definitions.

    Categories:
    - accrued: Earned over time (vacation, sick)
    - allocated: Fixed annual grant (personal days)
    - tracking_only: No balance impact (jury duty, bereavement, fmla)
    """
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identification
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="System code: VACATION, SICK, PERSONAL, BEREAVEMENT, FMLA, JURY_DUTY"
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Display name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Classification
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="tracking_only",
        comment="accrued, allocated, tracking_only"
    )

    # Behavior flags
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    requires_documentation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True for bereavement, fmla, jury_duty"
    )
    deducts_from_balance: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="False for jury_duty, bereavement, fmla"
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Default paid status for this leave type"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order in dropdowns"
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

    def __repr__(self) -> str:
        return f"<LeaveType(code='{self.code}', name='{self.name}')>"
