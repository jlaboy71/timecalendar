"""Tests for working days utility functions."""
import pytest
from datetime import date, timedelta
from src.utils.working_days import (
    count_working_days,
    is_working_day,
    is_weekend,
    get_holidays_in_range,
    validate_start_date,
    validate_end_date,
)
from src.models.market_holiday import MarketHoliday


class TestIsWeekend:
    """Tests for is_weekend function."""

    def test_monday_is_not_weekend(self):
        """Monday should not be a weekend."""
        # Find a Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        monday = today + timedelta(days=days_until_monday)
        # Verify it's Monday
        if monday.weekday() != 0:
            monday = date(2025, 1, 6)  # Known Monday
        assert not is_weekend(monday)

    def test_friday_is_not_weekend(self):
        """Friday should not be a weekend."""
        friday = date(2025, 1, 10)  # Known Friday
        assert friday.weekday() == 4  # Verify it's Friday
        assert not is_weekend(friday)

    def test_saturday_is_weekend(self):
        """Saturday should be a weekend."""
        saturday = date(2025, 1, 11)  # Known Saturday
        assert saturday.weekday() == 5  # Verify it's Saturday
        assert is_weekend(saturday)

    def test_sunday_is_weekend(self):
        """Sunday should be a weekend."""
        sunday = date(2025, 1, 12)  # Known Sunday
        assert sunday.weekday() == 6  # Verify it's Sunday
        assert is_weekend(sunday)


class TestIsWorkingDay:
    """Tests for is_working_day function."""

    def test_weekday_is_working_day(self):
        """A weekday with no holidays should be a working day."""
        monday = date(2025, 1, 6)  # Known Monday
        assert is_working_day(monday)

    def test_weekend_is_not_working_day(self):
        """Weekend days should not be working days."""
        saturday = date(2025, 1, 11)
        sunday = date(2025, 1, 12)
        assert not is_working_day(saturday)
        assert not is_working_day(sunday)

    def test_holiday_is_not_working_day(self):
        """A holiday should not be a working day."""
        # Use a known holiday date
        holiday = date(2025, 1, 1)  # New Year's Day
        holidays = {holiday}
        assert not is_working_day(holiday, holidays)

    def test_weekday_not_in_holidays_is_working_day(self):
        """A weekday not in the holiday set should be a working day."""
        monday = date(2025, 1, 6)
        holidays = {date(2025, 1, 1)}  # Only New Year
        assert is_working_day(monday, holidays)


class TestCountWorkingDays:
    """Tests for count_working_days function."""

    def test_single_weekday_is_one_day(self):
        """A single weekday should count as 1 working day."""
        monday = date(2025, 1, 6)
        result = count_working_days(monday, monday, holidays=set())
        assert result == 1

    def test_single_weekend_is_zero_days(self):
        """A single weekend day should count as 0 working days."""
        saturday = date(2025, 1, 11)
        result = count_working_days(saturday, saturday, holidays=set())
        assert result == 0

    def test_weekdays_only_range(self):
        """Mon-Fri should be 5 working days."""
        monday = date(2025, 1, 6)
        friday = date(2025, 1, 10)
        result = count_working_days(monday, friday, holidays=set())
        assert result == 5

    def test_weekend_excluded_from_range(self):
        """Fri-Mon should be 2 working days (Fri + Mon, not Sat/Sun)."""
        friday = date(2025, 1, 10)
        monday = date(2025, 1, 13)
        result = count_working_days(friday, monday, holidays=set())
        assert result == 2  # Friday + Monday

    def test_full_week_is_five_days(self):
        """A full 7-day week should count as 5 working days."""
        monday = date(2025, 1, 6)
        sunday = date(2025, 1, 12)
        result = count_working_days(monday, sunday, holidays=set())
        assert result == 5  # Mon-Fri

    def test_holiday_excluded_from_count(self):
        """Holidays should be excluded from the count."""
        monday = date(2025, 1, 6)
        friday = date(2025, 1, 10)
        holidays = {date(2025, 1, 8)}  # Wednesday is a holiday
        result = count_working_days(monday, friday, holidays=holidays)
        assert result == 4  # 5 days - 1 holiday

    def test_multiple_holidays_excluded(self):
        """Multiple holidays should all be excluded."""
        monday = date(2025, 1, 6)
        friday = date(2025, 1, 10)
        holidays = {date(2025, 1, 7), date(2025, 1, 9)}  # Tue and Thu
        result = count_working_days(monday, friday, holidays=holidays)
        assert result == 3  # 5 days - 2 holidays

    def test_all_weekends_is_zero(self):
        """A range of only weekend days should be 0."""
        saturday = date(2025, 1, 11)
        sunday = date(2025, 1, 12)
        result = count_working_days(saturday, sunday, holidays=set())
        assert result == 0

    def test_end_before_start_is_zero(self):
        """If end_date is before start_date, return 0."""
        result = count_working_days(date(2025, 1, 10), date(2025, 1, 6), holidays=set())
        assert result == 0

    def test_two_week_range(self):
        """Two full weeks should be 10 working days."""
        monday1 = date(2025, 1, 6)
        friday2 = date(2025, 1, 17)
        result = count_working_days(monday1, friday2, holidays=set())
        assert result == 10


class TestValidateStartDate:
    """Tests for validate_start_date function."""

    def test_weekday_is_valid(self):
        """A weekday should be valid."""
        monday = date(2025, 1, 6)
        is_valid, message = validate_start_date(monday)
        assert is_valid
        assert message == ""

    def test_saturday_is_invalid(self):
        """Saturday should be invalid."""
        saturday = date(2025, 1, 11)
        is_valid, message = validate_start_date(saturday)
        assert not is_valid
        assert "Saturday" in message

    def test_sunday_is_invalid(self):
        """Sunday should be invalid."""
        sunday = date(2025, 1, 12)
        is_valid, message = validate_start_date(sunday)
        assert not is_valid
        assert "Sunday" in message


class TestValidateEndDate:
    """Tests for validate_end_date function."""

    def test_weekday_is_valid(self):
        """A weekday should be valid."""
        friday = date(2025, 1, 10)
        is_valid, message = validate_end_date(friday)
        assert is_valid
        assert message == ""

    def test_weekend_is_invalid(self):
        """Weekend should be invalid."""
        saturday = date(2025, 1, 11)
        is_valid, message = validate_end_date(saturday)
        assert not is_valid
        assert "Saturday" in message


class TestGetHolidaysInRange:
    """Tests for get_holidays_in_range with database."""

    def test_returns_empty_set_for_invalid_range(self):
        """Should return empty set when end is before start."""
        result = get_holidays_in_range(date(2025, 1, 10), date(2025, 1, 5))
        assert result == set()

    def test_returns_holidays_in_range(self, db):
        """Should return holidays within the given range."""
        # Add a test holiday
        holiday = MarketHoliday(
            holiday_date=date(2025, 1, 20),
            name="Test Holiday",
            market="NYSE",
            year=2025
        )
        db.add(holiday)
        db.commit()

        result = get_holidays_in_range(date(2025, 1, 15), date(2025, 1, 25), db)
        assert date(2025, 1, 20) in result

    def test_excludes_early_close_days(self, db):
        """Should exclude early close days from holiday set."""
        # Add regular holiday
        regular = MarketHoliday(
            holiday_date=date(2025, 1, 20),
            name="Regular Holiday",
            market="NYSE",
            year=2025
        )
        # Add early close (should be excluded)
        early_close = MarketHoliday(
            holiday_date=date(2025, 1, 21),
            name="Early Close Day",
            market="NYSE",
            year=2025
        )
        db.add_all([regular, early_close])
        db.commit()

        result = get_holidays_in_range(date(2025, 1, 15), date(2025, 1, 25), db)
        assert date(2025, 1, 20) in result
        assert date(2025, 1, 21) not in result

    def test_returns_empty_when_no_holidays(self, db):
        """Should return empty set when no holidays in range."""
        result = get_holidays_in_range(date(2025, 6, 1), date(2025, 6, 5), db)
        assert result == set()


class TestWorkingDaysWithDatabase:
    """Integration tests for working days with database holidays."""

    def test_count_with_db_holiday(self, db):
        """Should exclude database holidays from count."""
        # Add a holiday
        holiday = MarketHoliday(
            holiday_date=date(2025, 1, 8),  # Wednesday
            name="Test Holiday",
            market="NYSE",
            year=2025
        )
        db.add(holiday)
        db.commit()

        monday = date(2025, 1, 6)
        friday = date(2025, 1, 10)
        result = count_working_days(monday, friday, db_session=db)
        assert result == 4  # 5 weekdays - 1 holiday

    def test_validate_start_with_db_holiday(self, db):
        """Should reject a holiday as start date."""
        # Add a holiday
        holiday = MarketHoliday(
            holiday_date=date(2025, 1, 8),
            name="Test Holiday",
            market="NYSE",
            year=2025
        )
        db.add(holiday)
        db.commit()

        is_valid, message = validate_start_date(date(2025, 1, 8), db)
        assert not is_valid
        assert "holiday" in message.lower()
