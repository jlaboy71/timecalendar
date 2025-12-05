"""
Vacation Accrual Tier model for tenure-based vacation grants.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, Numeric, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class VacationAccrualTier(Base):
    """
    Tenure-based vacation accrual tiers.

    From Haventech Handbook:
    - 1-4 years: 10 days/year (0.83 days/month)
    - 5-9 years: 15 days/year (1.25 days/month)
    - 10+ years: 20 days/year (1.67 days/month)
    """
    __tablename__ = "vacation_accrual_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Tenure range (years of service)
    min_years_service: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Minimum years (inclusive)"
    )
    max_years_service: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum years (inclusive), NULL = no upper limit"
    )

    # Grant amounts
    annual_days: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        comment="Total vacation days granted per year"
    )
    monthly_accrual_rate: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        comment="Days accrued per month (annual_days / 12)"
    )

    # Validity
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=func.current_date()
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        max_yrs = self.max_years_service or "+"
        return f"<VacationAccrualTier({self.min_years_service}-{max_yrs} yrs: {self.annual_days} days)>"
