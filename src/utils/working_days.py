"""Working days calculation utility.

Shared utility for calculating business days (Mon-Fri) excluding holidays.
Used by both UI layer and service layer for consistent date calculations.
"""
from datetime import date, timedelta
from typing import Optional, Set
from sqlalchemy.orm import Session


def get_holidays_in_range(
    start_date: date,
    end_date: date,
    db_session: Optional[Session] = None
) -> Set[date]:
    """Get holiday dates within a date range.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        db_session: Optional database session. If not provided, creates one.

    Returns:
        Set of holiday dates (excluding early close days)
    """
    if start_date > end_date:
        return set()

    holiday_dates: Set[date] = set()

    # Import here to avoid circular imports
    from src.models.market_holiday import MarketHoliday

    should_close_db = False
    db = db_session

    try:
        if db is None:
            from src.database import get_db
            db = next(get_db())
            should_close_db = True

        holidays = db.query(MarketHoliday.holiday_date).filter(
            MarketHoliday.holiday_date >= start_date,
            MarketHoliday.holiday_date <= end_date,
            ~MarketHoliday.name.contains('Early Close')  # Exclude early close days
        ).distinct().all()

        holiday_dates = {h.holiday_date for h in holidays}

    except Exception:
        pass  # If we can't get holidays, return empty set
    finally:
        if should_close_db and db is not None:
            db.close()

    return holiday_dates


def is_working_day(
    date_obj: date,
    holidays: Optional[Set[date]] = None
) -> bool:
    """Check if a date is a working day (Mon-Fri, not a holiday).

    Args:
        date_obj: The date to check
        holidays: Optional set of holiday dates. If None, only checks weekday.

    Returns:
        True if date is a working day, False otherwise
    """
    # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    if date_obj.weekday() >= 5:  # Saturday or Sunday
        return False

    if holidays is not None and date_obj in holidays:
        return False

    return True


def is_weekend(date_obj: date) -> bool:
    """Check if a date is a weekend (Saturday or Sunday).

    Args:
        date_obj: The date to check

    Returns:
        True if date is Saturday or Sunday
    """
    return date_obj.weekday() >= 5


def count_working_days(
    start_date: date,
    end_date: date,
    db_session: Optional[Session] = None,
    holidays: Optional[Set[date]] = None
) -> int:
    """Count business days (Mon-Fri) between two dates, inclusive, excluding holidays.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        db_session: Optional database session for holiday lookup
        holidays: Optional pre-fetched set of holiday dates. If provided,
                  db_session is ignored for holiday lookup.

    Returns:
        Number of business days (weekdays only, excluding market holidays)
    """
    if start_date > end_date:
        return 0

    # Get holidays if not provided
    if holidays is None:
        holidays = get_holidays_in_range(start_date, end_date, db_session)

    business_days = 0
    current = start_date

    while current <= end_date:
        if is_working_day(current, holidays):
            business_days += 1
        current += timedelta(days=1)

    return business_days


def validate_start_date(
    start_date: date,
    db_session: Optional[Session] = None
) -> tuple[bool, str]:
    """Validate that a start date is a valid working day.

    Args:
        start_date: The proposed start date
        db_session: Optional database session for holiday lookup

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string.
    """
    if is_weekend(start_date):
        day_name = start_date.strftime('%A')
        return False, f"Start date cannot be a {day_name}. Please select a business day (Mon-Fri)."

    # Check if it's a holiday
    holidays = get_holidays_in_range(start_date, start_date, db_session)
    if start_date in holidays:
        return False, "Start date cannot be a holiday. Please select a business day."

    return True, ""


def validate_end_date(
    end_date: date,
    db_session: Optional[Session] = None
) -> tuple[bool, str]:
    """Validate that an end date is a valid working day.

    Args:
        end_date: The proposed end date
        db_session: Optional database session for holiday lookup

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string.
    """
    if is_weekend(end_date):
        day_name = end_date.strftime('%A')
        return False, f"End date cannot be a {day_name}. Please select a business day (Mon-Fri)."

    # Check if it's a holiday
    holidays = get_holidays_in_range(end_date, end_date, db_session)
    if end_date in holidays:
        return False, "End date cannot be a holiday. Please select a business day."

    return True, ""
