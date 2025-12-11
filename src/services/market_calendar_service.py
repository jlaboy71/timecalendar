"""
Market Calendar Service with multi-tier fallback for holiday data.

Tier 1: pandas_market_calendars (local library)
Tier 2: Official exchange websites (future implementation)
Tier 3: Web scraping backup (future implementation)
Tier 4: Static calculation (guaranteed fallback)
"""
import logging
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source tiers for market holidays."""
    PANDAS_MARKET_CALENDARS = "pandas_market_calendars"
    OFFICIAL_WEBSITE = "official_website"
    WEB_SCRAPE = "web_scrape"
    STATIC_CALCULATION = "static_calculation"


class Confidence(Enum):
    """Confidence level for holiday data."""
    VERIFIED = "verified"
    CALCULATED = "calculated"
    UNVERIFIED = "unverified"


@dataclass
class SyncResult:
    """Result of a market holiday sync operation."""
    success: bool
    source: DataSource
    count: int
    year: int
    warning: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MarketHolidayData:
    """Market holiday data structure."""
    date: date
    name: str
    exchange: str  # NYSE, CME, CBOE, ALL
    is_full_closure: bool = True
    early_close_time: Optional[time] = None
    observed_date: Optional[date] = None  # If different from actual date


class MarketCalendarService:
    """Service for fetching and managing market holiday data."""

    # US Markets we track (includes Federal for company holidays)
    EXCHANGES = ['NYSE', 'CME', 'CBOE', 'Federal']

    def __init__(self, db_session=None):
        """Initialize the market calendar service."""
        self._db_session = db_session
        self._pandas_available = self._check_pandas_available()

    def _check_pandas_available(self) -> bool:
        """Check if pandas_market_calendars is installed."""
        try:
            import pandas_market_calendars
            return True
        except ImportError:
            logger.warning("pandas_market_calendars not installed, will use static calculations")
            return False

    def sync_market_holidays(self, year: int) -> SyncResult:
        """
        Sync market holidays for a given year using tiered fallback.

        Args:
            year: The year to sync holidays for

        Returns:
            SyncResult with details of the sync operation
        """
        # Tier 1: Try pandas_market_calendars
        if self._pandas_available:
            try:
                holidays = self._get_from_pandas(year)
                if holidays:
                    self._save_to_database(holidays, DataSource.PANDAS_MARKET_CALENDARS)
                    logger.info(f"Synced {len(holidays)} holidays from pandas_market_calendars for {year}")
                    return SyncResult(
                        success=True,
                        source=DataSource.PANDAS_MARKET_CALENDARS,
                        count=len(holidays),
                        year=year
                    )
            except Exception as e:
                logger.warning(f"Tier 1 (pandas_market_calendars) failed: {e}")

        # Tier 2: Official websites (placeholder for future implementation)
        # try:
        #     holidays = self._fetch_from_official_sites(year)
        #     ...
        # except Exception as e:
        #     logger.warning(f"Tier 2 (Official Websites) failed: {e}")

        # Tier 3: Web scraping (placeholder for future implementation)
        # try:
        #     holidays = self._scrape_holidays(year)
        #     ...
        # except Exception as e:
        #     logger.warning(f"Tier 3 (Web Scraping) failed: {e}")

        # Tier 4: Static calculation (GUARANTEED)
        try:
            holidays = self._calculate_static_holidays(year)
            self._save_to_database(holidays, DataSource.STATIC_CALCULATION)
            logger.info(f"Generated {len(holidays)} holidays from static calculation for {year}")
            return SyncResult(
                success=True,
                source=DataSource.STATIC_CALCULATION,
                count=len(holidays),
                year=year,
                warning="Using calculated holidays - verify manually for accuracy"
            )
        except Exception as e:
            logger.error(f"Tier 4 (Static Calculation) failed: {e}")
            return SyncResult(
                success=False,
                source=DataSource.STATIC_CALCULATION,
                count=0,
                year=year,
                error=str(e)
            )

    def _get_from_pandas(self, year: int) -> List[MarketHolidayData]:
        """
        Tier 1: Get holidays from pandas_market_calendars library.

        Args:
            year: Year to fetch holidays for

        Returns:
            List of MarketHolidayData objects
        """
        import pandas_market_calendars as mcal

        holidays = []
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'

        # NYSE Calendar
        try:
            nyse = mcal.get_calendar('NYSE')
            nyse_schedule = nyse.schedule(start_date=start_date, end_date=end_date)

            # Get holidays (days not in schedule)
            all_days = mcal.date_range(nyse_schedule, frequency='1D') if not nyse_schedule.empty else []

            # Get the actual holidays list
            nyse_holidays = nyse.holidays()
            if hasattr(nyse_holidays, 'holidays'):
                for h in nyse_holidays.holidays:
                    if hasattr(h, 'year') and h.year == year:
                        holidays.append(MarketHolidayData(
                            date=h if isinstance(h, date) else h.date(),
                            name=self._get_holiday_name(h if isinstance(h, date) else h.date()),
                            exchange='NYSE',
                            is_full_closure=True
                        ))

            # Get early closes
            early_closes = nyse.early_closes(schedule=nyse_schedule) if not nyse_schedule.empty else []
            for ec in early_closes.index if hasattr(early_closes, 'index') else []:
                ec_date = ec.date() if hasattr(ec, 'date') else ec
                if ec_date.year == year:
                    holidays.append(MarketHolidayData(
                        date=ec_date,
                        name=f"{self._get_holiday_name(ec_date)} (Early Close)",
                        exchange='NYSE',
                        is_full_closure=False,
                        early_close_time=time(13, 0)
                    ))
        except Exception as e:
            logger.warning(f"Error fetching NYSE calendar: {e}")

        # CME Calendar
        try:
            cme = mcal.get_calendar('CME_Equity')
            cme_holidays = cme.holidays()
            if hasattr(cme_holidays, 'holidays'):
                for h in cme_holidays.holidays:
                    h_date = h if isinstance(h, date) else h.date()
                    if h_date.year == year:
                        # Avoid duplicates with NYSE
                        if not any(hd.date == h_date and hd.exchange == 'CME' for hd in holidays):
                            holidays.append(MarketHolidayData(
                                date=h_date,
                                name=self._get_holiday_name(h_date),
                                exchange='CME',
                                is_full_closure=True
                            ))
        except Exception as e:
            logger.warning(f"Error fetching CME calendar: {e}")

        # CBOE Calendar (CFE)
        try:
            cboe = mcal.get_calendar('CFE')
            cboe_holidays = cboe.holidays()
            if hasattr(cboe_holidays, 'holidays'):
                for h in cboe_holidays.holidays:
                    h_date = h if isinstance(h, date) else h.date()
                    if h_date.year == year:
                        # Avoid duplicates
                        if not any(hd.date == h_date and hd.exchange == 'CBOE' for hd in holidays):
                            holidays.append(MarketHolidayData(
                                date=h_date,
                                name=self._get_holiday_name(h_date),
                                exchange='CBOE',
                                is_full_closure=True
                            ))
        except Exception as e:
            logger.warning(f"Error fetching CBOE calendar: {e}")

        return holidays

    def _calculate_static_holidays(self, year: int) -> List[MarketHolidayData]:
        """
        Tier 4: Calculate holidays algorithmically (GUARANTEED to work).

        Args:
            year: Year to calculate holidays for

        Returns:
            List of MarketHolidayData objects
        """
        holidays = []

        # New Year's Day - January 1
        new_years = self._observed_date(date(year, 1, 1))
        holidays.append(MarketHolidayData(
            date=new_years,
            name="New Year's Day",
            exchange='ALL',
            is_full_closure=True,
            observed_date=new_years if new_years != date(year, 1, 1) else None
        ))

        # Martin Luther King Jr. Day - 3rd Monday of January
        mlk_day = self._nth_weekday(year, 1, 0, 3)  # month=1, weekday=0 (Mon), nth=3
        holidays.append(MarketHolidayData(
            date=mlk_day,
            name="Martin Luther King Jr. Day",
            exchange='ALL',
            is_full_closure=True
        ))

        # Presidents Day - 3rd Monday of February
        presidents_day = self._nth_weekday(year, 2, 0, 3)
        holidays.append(MarketHolidayData(
            date=presidents_day,
            name="Presidents Day",
            exchange='ALL',
            is_full_closure=True
        ))

        # Good Friday - Friday before Easter
        easter = self._calculate_easter(year)
        good_friday = easter - timedelta(days=2)
        holidays.append(MarketHolidayData(
            date=good_friday,
            name="Good Friday",
            exchange='ALL',
            is_full_closure=True
        ))

        # Memorial Day - Last Monday of May
        memorial_day = self._last_weekday(year, 5, 0)
        holidays.append(MarketHolidayData(
            date=memorial_day,
            name="Memorial Day",
            exchange='ALL',
            is_full_closure=True
        ))

        # Juneteenth - June 19 (observed since 2022)
        if year >= 2022:
            juneteenth = self._observed_date(date(year, 6, 19))
            holidays.append(MarketHolidayData(
                date=juneteenth,
                name="Juneteenth National Independence Day",
                exchange='ALL',
                is_full_closure=True,
                observed_date=juneteenth if juneteenth != date(year, 6, 19) else None
            ))

        # Independence Day - July 4
        july_4 = date(year, 7, 4)
        july_4_observed = self._observed_date(july_4)
        holidays.append(MarketHolidayData(
            date=july_4_observed,
            name="Independence Day",
            exchange='ALL',
            is_full_closure=True,
            observed_date=july_4_observed if july_4_observed != july_4 else None
        ))

        # Day before July 4 - Early close (if July 4 is not Monday and not weekend)
        if july_4.weekday() not in (0, 5, 6):  # Not Monday, Saturday, or Sunday
            july_3 = july_4 - timedelta(days=1)
            if july_3.weekday() < 5:  # Weekday
                holidays.append(MarketHolidayData(
                    date=july_3,
                    name="Independence Day Eve (Early Close)",
                    exchange='ALL',
                    is_full_closure=False,
                    early_close_time=time(13, 0)
                ))

        # Labor Day - 1st Monday of September
        labor_day = self._nth_weekday(year, 9, 0, 1)
        holidays.append(MarketHolidayData(
            date=labor_day,
            name="Labor Day",
            exchange='ALL',
            is_full_closure=True
        ))

        # Thanksgiving Day - 4th Thursday of November
        thanksgiving = self._nth_weekday(year, 11, 3, 4)  # weekday=3 (Thu)
        holidays.append(MarketHolidayData(
            date=thanksgiving,
            name="Thanksgiving Day",
            exchange='ALL',
            is_full_closure=True
        ))

        # Day after Thanksgiving - Early close
        black_friday = thanksgiving + timedelta(days=1)
        holidays.append(MarketHolidayData(
            date=black_friday,
            name="Day After Thanksgiving (Early Close)",
            exchange='ALL',
            is_full_closure=False,
            early_close_time=time(13, 0)
        ))

        # Christmas Eve - Early close (if not weekend)
        christmas_eve = date(year, 12, 24)
        if christmas_eve.weekday() < 5:  # Weekday
            holidays.append(MarketHolidayData(
                date=christmas_eve,
                name="Christmas Eve (Early Close)",
                exchange='ALL',
                is_full_closure=False,
                early_close_time=time(13, 0)
            ))

        # Christmas Day - December 25
        christmas = date(year, 12, 25)
        christmas_observed = self._observed_date(christmas)
        holidays.append(MarketHolidayData(
            date=christmas_observed,
            name="Christmas Day",
            exchange='ALL',
            is_full_closure=True,
            observed_date=christmas_observed if christmas_observed != christmas else None
        ))

        return holidays

    def _save_to_database(self, holidays: List[MarketHolidayData], source: DataSource) -> int:
        """
        Save holidays to the database.

        Args:
            holidays: List of MarketHolidayData to save
            source: Data source that provided the holidays

        Returns:
            Number of holidays saved
        """
        if not self._db_session:
            logger.warning("No database session provided, cannot save holidays")
            return 0

        from src.models.market_holiday import MarketHoliday

        saved_count = 0
        for holiday in holidays:
            # Handle 'ALL' exchange by creating entries for each exchange
            exchanges = self.EXCHANGES if holiday.exchange == 'ALL' else [holiday.exchange]

            for exchange in exchanges:
                # Check if already exists
                existing = self._db_session.query(MarketHoliday).filter(
                    MarketHoliday.holiday_date == holiday.date,
                    MarketHoliday.market == exchange
                ).first()

                if existing:
                    # Update existing
                    existing.name = holiday.name
                    existing.is_observed = True
                else:
                    # Create new
                    new_holiday = MarketHoliday(
                        holiday_date=holiday.date,
                        name=holiday.name,
                        market=exchange,
                        year=holiday.date.year,
                        is_observed=True
                    )
                    self._db_session.add(new_holiday)
                    saved_count += 1

        try:
            self._db_session.commit()
            logger.info(f"Saved {saved_count} new holidays to database from {source.value}")
        except Exception as e:
            self._db_session.rollback()
            logger.error(f"Failed to save holidays: {e}")
            raise

        return saved_count

    def get_holidays_for_year(self, year: int) -> List[Dict]:
        """
        Get all holidays for a given year from the database.

        Args:
            year: Year to get holidays for

        Returns:
            List of holiday dictionaries
        """
        if not self._db_session:
            return []

        from src.models.market_holiday import MarketHoliday

        holidays = self._db_session.query(MarketHoliday).filter(
            MarketHoliday.year == year
        ).order_by(MarketHoliday.holiday_date).all()

        return [{
            'id': h.id,
            'date': h.holiday_date,
            'name': h.name,
            'market': h.market,
            'is_observed': h.is_observed
        } for h in holidays]

    def get_upcoming_holidays(self, days: int = 30) -> List[Dict]:
        """
        Get holidays within the next N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of upcoming holiday dictionaries
        """
        if not self._db_session:
            return []

        from src.models.market_holiday import MarketHoliday

        today = date.today()
        end_date = today + timedelta(days=days)

        holidays = self._db_session.query(MarketHoliday).filter(
            MarketHoliday.holiday_date >= today,
            MarketHoliday.holiday_date <= end_date
        ).order_by(MarketHoliday.holiday_date).all()

        return [{
            'id': h.id,
            'date': h.holiday_date,
            'name': h.name,
            'market': h.market,
            'is_observed': h.is_observed
        } for h in holidays]

    # Helper functions

    def _nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """
        Get nth occurrence of weekday in month (1-indexed).

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)
            n: Which occurrence (1=first, 2=second, etc.)

        Returns:
            Date of the nth weekday
        """
        first_day = date(year, month, 1)
        # Find first occurrence of the weekday
        days_until = (weekday - first_day.weekday()) % 7
        first_weekday = first_day + timedelta(days=days_until)
        # Add weeks to get to nth occurrence
        return first_weekday + timedelta(weeks=n - 1)

    def _last_weekday(self, year: int, month: int, weekday: int) -> date:
        """
        Get last occurrence of weekday in month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Date of the last weekday in the month
        """
        # Get first day of next month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        # Last day of current month
        last_day = next_month - timedelta(days=1)
        # Find last occurrence of weekday
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)

    def _observed_date(self, holiday: date) -> date:
        """
        Adjust for weekend observation (Friday if Saturday, Monday if Sunday).

        Args:
            holiday: The actual holiday date

        Returns:
            The observed date
        """
        if holiday.weekday() == 5:  # Saturday
            return holiday - timedelta(days=1)  # Friday
        elif holiday.weekday() == 6:  # Sunday
            return holiday + timedelta(days=1)  # Monday
        return holiday

    def _calculate_easter(self, year: int) -> date:
        """
        Calculate Easter Sunday using the Computus algorithm.

        Args:
            year: Year to calculate Easter for

        Returns:
            Date of Easter Sunday
        """
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    def _get_holiday_name(self, holiday_date: date) -> str:
        """
        Get the holiday name for a given date based on common US market holidays.

        Args:
            holiday_date: Date to identify

        Returns:
            Name of the holiday or "Market Holiday"
        """
        year = holiday_date.year
        month = holiday_date.month
        day = holiday_date.day

        # Check specific dates
        if month == 1 and day == 1:
            return "New Year's Day"
        if month == 7 and day == 4:
            return "Independence Day"
        if month == 12 and day == 25:
            return "Christmas Day"
        if month == 6 and day == 19:
            return "Juneteenth"

        # Check calculated holidays
        if holiday_date == self._nth_weekday(year, 1, 0, 3):
            return "Martin Luther King Jr. Day"
        if holiday_date == self._nth_weekday(year, 2, 0, 3):
            return "Presidents Day"
        if holiday_date == self._last_weekday(year, 5, 0):
            return "Memorial Day"
        if holiday_date == self._nth_weekday(year, 9, 0, 1):
            return "Labor Day"
        if holiday_date == self._nth_weekday(year, 11, 3, 4):
            return "Thanksgiving Day"

        # Check Good Friday
        easter = self._calculate_easter(year)
        if holiday_date == easter - timedelta(days=2):
            return "Good Friday"

        # Check observed dates
        new_years = self._observed_date(date(year, 1, 1))
        if holiday_date == new_years and new_years != date(year, 1, 1):
            return "New Year's Day (Observed)"

        july_4_observed = self._observed_date(date(year, 7, 4))
        if holiday_date == july_4_observed and july_4_observed != date(year, 7, 4):
            return "Independence Day (Observed)"

        christmas_observed = self._observed_date(date(year, 12, 25))
        if holiday_date == christmas_observed and christmas_observed != date(year, 12, 25):
            return "Christmas Day (Observed)"

        return "Market Holiday"
