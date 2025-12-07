"""
Year-end processing service for TJM Time Calendar.

Handles:
- Creating new year balances for all active employees
- Applying approved carryover to new year balances
- Generating federal/market holidays for the new year
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.pto_balance import PTOBalance
from src.models.carryover_request import CarryoverRequest
from src.models.market_holiday import MarketHoliday
from src.services.balance_service import BalanceService

logger = logging.getLogger(__name__)


class YearEndService:
    """Service for year-end processing operations."""

    # Default PTO allocations (can be overridden per employee based on tenure)
    DEFAULT_VACATION_DAYS = 10
    DEFAULT_SICK_DAYS = 5
    DEFAULT_PERSONAL_DAYS = 2

    def __init__(self, db: Session):
        self.db = db
        self.balance_service = BalanceService(db)

    def process_year_transition(self, new_year: int) -> Dict:
        """
        Process the transition to a new year.

        Args:
            new_year: The new year to process (e.g., 2026)

        Returns:
            Dictionary with processing results
        """
        results = {
            'year': new_year,
            'balances_created': 0,
            'carryovers_applied': 0,
            'holidays_created': 0,
            'errors': []
        }

        try:
            # Step 1: Create balances for all active employees
            balances_result = self.create_new_year_balances(new_year)
            results['balances_created'] = balances_result['created']
            results['errors'].extend(balances_result.get('errors', []))

            # Step 2: Apply approved carryover from previous year
            carryover_result = self.apply_approved_carryover(new_year)
            results['carryovers_applied'] = carryover_result['applied']
            results['errors'].extend(carryover_result.get('errors', []))

            # Step 3: Generate federal holidays for new year
            holidays_result = self.generate_federal_holidays(new_year)
            results['holidays_created'] = holidays_result['created']

            logger.info(f"Year-end processing complete for {new_year}: {results}")

        except Exception as e:
            logger.error(f"Year-end processing failed: {str(e)}")
            results['errors'].append(str(e))

        return results

    def create_new_year_balances(self, year: int) -> Dict:
        """
        Create PTO balances for all active employees for the new year.

        Args:
            year: The year to create balances for

        Returns:
            Dictionary with creation results
        """
        result = {'created': 0, 'skipped': 0, 'errors': []}

        # Get all active employees
        active_users = self.db.query(User).filter(User.is_active == True).all()

        for user in active_users:
            try:
                # Check if balance already exists
                existing = self.db.query(PTOBalance).filter(
                    PTOBalance.user_id == user.id,
                    PTOBalance.year == year
                ).first()

                if existing:
                    result['skipped'] += 1
                    continue

                # Calculate PTO allocation based on tenure
                vacation_days = self._calculate_vacation_allocation(user)

                # Create new balance
                balance = PTOBalance(
                    user_id=user.id,
                    year=year,
                    vacation_total=Decimal(str(vacation_days)),
                    vacation_used=Decimal('0.00'),
                    vacation_pending=Decimal('0.00'),
                    sick_total=Decimal(str(self.DEFAULT_SICK_DAYS)),
                    sick_used=Decimal('0.00'),
                    personal_total=Decimal(str(self.DEFAULT_PERSONAL_DAYS)),
                    personal_used=Decimal('0.00'),
                    vacation_carryover=Decimal('0.00'),
                    sick_carryover=Decimal('0.00'),
                    personal_carryover=Decimal('0.00')
                )

                self.db.add(balance)
                result['created'] += 1
                logger.info(f"Created {year} balance for user {user.username}")

            except Exception as e:
                error_msg = f"Failed to create balance for user {user.id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.commit()
        return result

    def _calculate_vacation_allocation(self, user: User) -> int:
        """
        Calculate vacation days based on employee tenure.

        Args:
            user: The user to calculate for

        Returns:
            Number of vacation days
        """
        if not user.hire_date:
            return self.DEFAULT_VACATION_DAYS

        today = date.today()
        years_of_service = (today - user.hire_date).days // 365

        # Tiered vacation based on tenure
        if years_of_service >= 10:
            return 20  # 4 weeks
        elif years_of_service >= 5:
            return 15  # 3 weeks
        elif years_of_service >= 2:
            return 12  # 2.4 weeks
        else:
            return self.DEFAULT_VACATION_DAYS  # 2 weeks

    def apply_approved_carryover(self, new_year: int) -> Dict:
        """
        Apply approved carryover requests to new year balances.

        Args:
            new_year: The year to apply carryover to

        Returns:
            Dictionary with application results
        """
        result = {'applied': 0, 'errors': []}
        previous_year = new_year - 1

        # Find all approved carryover requests for this transition
        approved_carryovers = self.db.query(CarryoverRequest).filter(
            CarryoverRequest.status == 'approved',
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.to_year == new_year
        ).all()

        for carryover in approved_carryovers:
            try:
                # Get or create the new year balance
                balance = self.db.query(PTOBalance).filter(
                    PTOBalance.user_id == carryover.employee_id,
                    PTOBalance.year == new_year
                ).first()

                if not balance:
                    # Create balance if it doesn't exist
                    user = self.db.query(User).filter(User.id == carryover.employee_id).first()
                    if user:
                        vacation_days = self._calculate_vacation_allocation(user)
                        balance = PTOBalance(
                            user_id=carryover.employee_id,
                            year=new_year,
                            vacation_total=Decimal(str(vacation_days)),
                            sick_total=Decimal(str(self.DEFAULT_SICK_DAYS)),
                            personal_total=Decimal(str(self.DEFAULT_PERSONAL_DAYS))
                        )
                        self.db.add(balance)
                        self.db.flush()

                if balance:
                    # Apply carryover hours (convert to days: hours / 8)
                    hours_approved = carryover.hours_approved or carryover.hours_requested
                    days_to_carryover = hours_approved / Decimal('8')

                    # Add to vacation_carryover field
                    balance.vacation_carryover += days_to_carryover
                    result['applied'] += 1

                    logger.info(
                        f"Applied {hours_approved}hrs carryover for user {carryover.employee_id} "
                        f"({previous_year} -> {new_year})"
                    )

            except Exception as e:
                error_msg = f"Failed to apply carryover {carryover.id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.commit()
        return result

    def generate_federal_holidays(self, year: int) -> Dict:
        """
        Generate federal/market holidays for a given year.

        Args:
            year: The year to generate holidays for

        Returns:
            Dictionary with creation results
        """
        result = {'created': 0, 'skipped': 0}

        holidays = self._calculate_federal_holidays(year)

        for holiday_data in holidays:
            # Check if already exists
            existing = self.db.query(MarketHoliday).filter(
                MarketHoliday.holiday_date == holiday_data['date'],
                MarketHoliday.market == 'Federal'
            ).first()

            if existing:
                result['skipped'] += 1
                continue

            holiday = MarketHoliday(
                holiday_date=holiday_data['date'],
                name=holiday_data['name'],
                market='Federal',
                year=year,
                is_observed=True
            )
            self.db.add(holiday)
            result['created'] += 1

        self.db.commit()
        logger.info(f"Generated {result['created']} federal holidays for {year}")
        return result

    def _calculate_federal_holidays(self, year: int) -> List[Dict]:
        """
        Calculate federal holiday dates for a given year.

        Args:
            year: The year to calculate for

        Returns:
            List of holiday dictionaries with name and date
        """
        from datetime import timedelta

        holidays = []

        # New Year's Day - January 1
        holidays.append({
            'name': "New Year's Day",
            'date': self._observed_date(date(year, 1, 1))
        })

        # MLK Day - Third Monday in January
        holidays.append({
            'name': "Martin Luther King Jr. Day",
            'date': self._nth_weekday(year, 1, 0, 3)  # 3rd Monday of January
        })

        # Presidents Day - Third Monday in February
        holidays.append({
            'name': "Presidents Day",
            'date': self._nth_weekday(year, 2, 0, 3)  # 3rd Monday of February
        })

        # Good Friday - Friday before Easter Sunday
        easter = self._calculate_easter(year)
        holidays.append({
            'name': "Good Friday",
            'date': easter - timedelta(days=2)
        })

        # Memorial Day - Last Monday in May
        holidays.append({
            'name': "Memorial Day",
            'date': self._last_weekday(year, 5, 0)  # Last Monday of May
        })

        # Juneteenth - June 19
        holidays.append({
            'name': "Juneteenth",
            'date': self._observed_date(date(year, 6, 19))
        })

        # Independence Day - July 4
        holidays.append({
            'name': "Independence Day",
            'date': self._observed_date(date(year, 7, 4))
        })

        # Labor Day - First Monday in September
        holidays.append({
            'name': "Labor Day",
            'date': self._nth_weekday(year, 9, 0, 1)  # 1st Monday of September
        })

        # Thanksgiving - Fourth Thursday in November
        holidays.append({
            'name': "Thanksgiving Day",
            'date': self._nth_weekday(year, 11, 3, 4)  # 4th Thursday of November
        })

        # Christmas - December 25
        holidays.append({
            'name': "Christmas Day",
            'date': self._observed_date(date(year, 12, 25))
        })

        return holidays

    def _nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """
        Find the nth occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)
            n: Which occurrence (1=first, 2=second, etc.)

        Returns:
            Date of the nth weekday
        """
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()

        # Days until first occurrence of target weekday
        days_until = (weekday - first_weekday) % 7

        # Add weeks for nth occurrence
        target_day = 1 + days_until + (n - 1) * 7

        return date(year, month, target_day)

    def _last_weekday(self, year: int, month: int, weekday: int) -> date:
        """
        Find the last occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Date of the last weekday
        """
        # Find the last day of the month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        last_day = next_month - timedelta(days=1)

        # Work backwards to find the target weekday
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)

    def _observed_date(self, holiday_date: date) -> date:
        """
        Adjust holiday to observed date if it falls on weekend.

        Saturday -> Friday, Sunday -> Monday

        Args:
            holiday_date: The actual holiday date

        Returns:
            The observed date
        """
        from datetime import timedelta

        weekday = holiday_date.weekday()
        if weekday == 5:  # Saturday
            return holiday_date - timedelta(days=1)
        elif weekday == 6:  # Sunday
            return holiday_date + timedelta(days=1)
        return holiday_date

    def _calculate_easter(self, year: int) -> date:
        """
        Calculate Easter Sunday for a given year using the Anonymous Gregorian algorithm.

        Args:
            year: The year to calculate for

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

    def get_year_end_status(self, year: int) -> Dict:
        """
        Get the status of year-end processing for a given year.

        Args:
            year: The year to check

        Returns:
            Dictionary with status information
        """
        previous_year = year - 1

        # Count balances
        balances_count = self.db.query(PTOBalance).filter(
            PTOBalance.year == year
        ).count()

        active_users = self.db.query(User).filter(User.is_active == True).count()

        # Count pending carryovers
        pending_carryovers = self.db.query(CarryoverRequest).filter(
            CarryoverRequest.status == 'pending',
            CarryoverRequest.from_year == previous_year
        ).count()

        approved_carryovers = self.db.query(CarryoverRequest).filter(
            CarryoverRequest.status == 'approved',
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.to_year == year
        ).count()

        # Count holidays
        holidays_count = self.db.query(MarketHoliday).filter(
            MarketHoliday.year == year
        ).count()

        return {
            'year': year,
            'balances_created': balances_count,
            'active_users': active_users,
            'balances_complete': balances_count >= active_users,
            'pending_carryovers': pending_carryovers,
            'approved_carryovers': approved_carryovers,
            'holidays_created': holidays_count,
            'ready_for_transition': pending_carryovers == 0 and balances_count >= active_users
        }


# Import timedelta for the methods
from datetime import timedelta
