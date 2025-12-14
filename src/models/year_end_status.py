"""
Year-End Status model for tracking annual processing.
"""
from datetime import datetime
from sqlalchemy import Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class YearEndStatus(Base):
    """
    Tracks whether year-end processing has been completed for each year.
    """
    __tablename__ = "year_end_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    balances_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    carryovers_applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    holidays_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<YearEndStatus(year={self.year}, processed={self.processed})>"
