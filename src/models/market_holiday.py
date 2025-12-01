"""
Market Holiday model for the PTO and Market Calendar System.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Date, DateTime, Boolean, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class MarketHoliday(Base):
    """
    Market Holiday model representing financial market holidays.
    
    This model stores information about holidays for different financial
    markets (NYSE, CME, CBOE, etc.) to help with PTO planning and scheduling.
    """
    __tablename__ = "market_holidays"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Holiday information
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Status
    is_observed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=func.now(), 
        nullable=False
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('holiday_date', 'market', name='uq_holiday_date_market'),
    )
    
    def __repr__(self) -> str:
        """String representation of the MarketHoliday model."""
        return (f"<MarketHoliday(id={self.id}, date={self.holiday_date}, "
                f"name='{self.name}', market='{self.market}')>")
    
    @property
    def is_current_year(self) -> bool:
        """Check if the holiday is in the current year."""
        from datetime import datetime
        return self.year == datetime.now().year
