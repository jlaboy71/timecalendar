"""
Year-end processing service for TJM Time Calendar.

Handles:
- Creating new year balances for all active employees
- Applying approved carryover to new year balances
- Generating federal/market holidays for the new year
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from src.models.user import User
from src.models.pto_balance import PTOBalance
from src.models.carryover_request import CarryoverRequest
from src.models.market_holiday import MarketHoliday
from src.models.year_end_status import YearEndStatus
from src.models.leave_type import LeaveType
from src.models.system_setting import SystemSetting
from src.services.balance_service import BalanceService
from src.services.accrual_service import AccrualService
from src.services.report_storage_service import ReportStorageService

logger = logging.getLogger(__name__)


class YearEndService:
    """Service for year-end processing operations."""

    # Default PTO allocations (can be overridden per employee based on tenure)
    DEFAULT_VACATION_DAYS = 10
    DEFAULT_SICK_DAYS = 5
    DEFAULT_PERSONAL_DAYS = 2

    # Chicago Leave limits per ordinance
    CHICAGO_LEAVE_ANNUAL_MAX = Decimal('40.00')  # 40 hours (5 days) annual allocation
    CHICAGO_LEAVE_CARRYOVER_MAX = Decimal('16.00')  # 16 hours (2 days) max carryover

    def __init__(self, db: Session):
        self.db = db
        self.balance_service = BalanceService(db)

    def _get_chicago_leave_amount(self, user: User) -> Decimal:
        """
        Get Chicago Leave allocation for a user.

        Returns 40 hours if:
        1. Chicago Leave feature is enabled
        2. User's location_city is 'Chicago'

        Returns 0 otherwise.
        """
        # Check if feature is enabled
        stmt = select(SystemSetting).where(SystemSetting.key == 'chicago.safe_leave_enabled')
        chicago_setting = self.db.execute(stmt).scalar_one_or_none()

        if not chicago_setting or not chicago_setting.bool_value:
            return Decimal('0.00')

        # Check if user is in Chicago
        if user and user.location_city and user.location_city.lower() == 'chicago':
            return self.CHICAGO_LEAVE_ANNUAL_MAX

        return Decimal('0.00')

    def check_and_run_auto_processing(self) -> Optional[Dict]:
        """
        Check if year-end processing is needed for the current year and run if not done.

        This should be called on app startup or user login to ensure automatic processing.

        Returns:
            Processing results if run, None if already processed or not needed
        """
        current_year = date.today().year

        # Check if already processed for current year
        stmt = select(YearEndStatus).where(YearEndStatus.year == current_year)
        status = self.db.execute(stmt).scalar_one_or_none()

        if status and status.processed:
            logger.debug(f"Year-end processing already complete for {current_year}")
            return None

        # Run the processing
        logger.info(f"Running automatic year-end processing for {current_year}")
        results = self.process_year_transition(current_year)

        # Record that processing is complete
        if not status:
            status = YearEndStatus(year=current_year)
            self.db.add(status)

        status.processed = True
        status.processed_at = datetime.now()
        status.balances_created = results['balances_created']
        # Sum all carryover types for the total count (Personal does NOT carry over)
        status.carryovers_applied = (
            results['sick_carryovers_auto'] +
            results['vacation_exceptions_applied']
        )
        status.holidays_created = results['holidays_created']

        self.db.commit()
        logger.info(f"Year-end processing for {current_year} recorded as complete")

        return results

    def is_year_processed(self, year: int) -> bool:
        """Check if a year has been processed."""
        stmt = select(YearEndStatus).where(YearEndStatus.year == year)
        status = self.db.execute(stmt).scalar_one_or_none()
        return status is not None and status.processed

    def get_processing_record(self, year: int) -> Optional[YearEndStatus]:
        """Get the processing record for a year."""
        stmt = select(YearEndStatus).where(YearEndStatus.year == year)
        return self.db.execute(stmt).scalar_one_or_none()

    def process_year_transition(self, new_year: int) -> Dict:
        """
        Process the transition to a new year.

        All database operations are wrapped in a single transaction.
        If any step fails, all changes are rolled back to prevent partial/corrupt data.

        Args:
            new_year: The new year to process (e.g., 2026)

        Returns:
            Dictionary with processing results
        """
        results = {
            'year': new_year,
            'balances_created': 0,
            'sick_carryovers_auto': 0,
            'chicago_leave_carryovers_auto': 0,
            'vacation_exceptions_applied': 0,
            'holidays_created': 0,
            'reports_purged': 0,
            'errors': []
        }

        try:
            # All database operations in a single transaction
            # Step 1: Create balances for all active employees
            balances_result = self._create_new_year_balances_no_commit(new_year)
            results['balances_created'] = balances_result['created']
            results['errors'].extend(balances_result.get('errors', []))

            # Step 2: AUTO-CARRYOVER sick only (Personal does NOT carry over - use-it-or-lose-it)
            auto_carryover_result = self._auto_carryover_sick_no_commit(new_year)
            results['sick_carryovers_auto'] = auto_carryover_result['sick_applied']
            results['errors'].extend(auto_carryover_result.get('errors', []))

            # Step 2b: AUTO-CARRYOVER Chicago Paid Leave (up to 16 hours per ordinance)
            chicago_carryover_result = self._auto_carryover_chicago_leave_no_commit(new_year)
            results['chicago_leave_carryovers_auto'] = chicago_carryover_result['chicago_applied']
            results['errors'].extend(chicago_carryover_result.get('errors', []))

            # Step 3: Apply approved VACATION exception carryover (rare manager-approved cases)
            vacation_result = self._apply_vacation_exception_carryover_no_commit(new_year)
            results['vacation_exceptions_applied'] = vacation_result['applied']
            results['errors'].extend(vacation_result.get('errors', []))

            # Step 4: Generate federal holidays for new year
            holidays_result = self._generate_federal_holidays_no_commit(new_year)
            results['holidays_created'] = holidays_result['created']

            # If we had any errors during processing, rollback
            if results['errors']:
                logger.error(f"Year-end processing had errors, rolling back: {results['errors']}")
                self.db.rollback()
                return results

            # All steps succeeded - commit the transaction
            self.db.commit()
            logger.info(f"Year-end processing committed successfully for {new_year}")

            # DISABLED: Auto-purge of reports removed per user request
            # Reports should only be deleted via explicit user action
            # previous_year = new_year - 1
            # reports_purged = ReportStorageService.purge_year_reports(previous_year)
            # results['reports_purged'] = reports_purged
            # if reports_purged > 0:
            #     logger.info(f"Purged {reports_purged} auto-notify reports from {previous_year}")
            results['reports_purged'] = 0  # No auto-purge

            logger.info(f"Year-end processing complete for {new_year}: {results}")

        except Exception as e:
            logger.error(f"Year-end processing failed, rolling back: {str(e)}")
            self.db.rollback()
            results['errors'].append(str(e))

        return results

    def create_new_year_balances(self, year: int) -> Dict:
        """
        Create PTO balances for all active employees for the new year.
        This is the standalone version that commits after completion.

        Args:
            year: The year to create balances for

        Returns:
            Dictionary with creation results
        """
        result = self._create_new_year_balances_no_commit(year)
        if not result['errors']:
            self.db.commit()
        return result

    def _create_new_year_balances_no_commit(self, year: int) -> Dict:
        """
        Internal: Create PTO balances without committing (for transaction participation).

        Args:
            year: The year to create balances for

        Returns:
            Dictionary with creation results
        """
        result = {'created': 0, 'skipped': 0, 'errors': []}

        # Get all active employees
        stmt = select(User).where(User.is_active == True)
        active_users = self.db.execute(stmt).scalars().all()

        # Pre-fetch all existing balances for this year in one query (avoid N+1)
        stmt = select(PTOBalance.user_id).where(PTOBalance.year == year)
        existing_balances = self.db.execute(stmt).all()
        existing_user_ids = {b.user_id for b in existing_balances}

        for user in active_users:
            try:
                # Check if balance already exists (from pre-fetched set)
                if user.id in existing_user_ids:
                    result['skipped'] += 1
                    continue

                # Calculate PTO allocation based on tenure
                vacation_days = self._calculate_vacation_allocation(user)

                # Get Chicago leave amount if applicable
                chicago_leave = self._get_chicago_leave_amount(user)

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
                    personal_carryover=Decimal('0.00'),
                    # Chicago Leave (uses chicago_paid_leave fields - 16hr carryover max)
                    chicago_paid_leave_total=chicago_leave,
                    chicago_paid_leave_used=Decimal('0.00'),
                    chicago_paid_leave_pending=Decimal('0.00'),
                    chicago_paid_leave_carryover=Decimal('0.00')
                )

                self.db.add(balance)
                result['created'] += 1
                logger.info(f"Created {year} balance for user {user.username}")

            except Exception as e:
                error_msg = f"Failed to create balance for user {user.id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.flush()  # Flush to DB but don't commit
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
        This is the standalone version that commits after completion.

        Enforces the policy cap - total sick_carryover cannot exceed max_carryover_hours.

        Args:
            new_year: The year to apply carryover to

        Returns:
            Dictionary with application results
        """
        result = self._apply_approved_carryover_no_commit(new_year)
        if not result['errors']:
            self.db.commit()
        return result

    def _apply_approved_carryover_no_commit(self, new_year: int) -> Dict:
        """
        Internal: Apply approved carryover without committing (for transaction participation).

        Args:
            new_year: The year to apply carryover to

        Returns:
            Dictionary with application results
        """
        result = {'applied': 0, 'capped': 0, 'errors': []}
        previous_year = new_year - 1

        # Find all approved carryover requests for this transition
        stmt = select(CarryoverRequest).where(
            CarryoverRequest.status == 'approved',
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.to_year == new_year
        )
        approved_carryovers = self.db.execute(stmt).scalars().all()

        if not approved_carryovers:
            return result

        # Pre-fetch all balances and users in bulk to avoid N+1 queries
        carryover_user_ids = [c.employee_id for c in approved_carryovers]
        stmt = select(PTOBalance).where(
            PTOBalance.user_id.in_(carryover_user_ids),
            PTOBalance.year == new_year
        )
        existing_balances = {b.user_id: b for b in self.db.execute(stmt).scalars().all()}
        stmt = select(User).where(User.id.in_(carryover_user_ids))
        users_map = {u.id: u for u in self.db.execute(stmt).scalars().all()}

        # Get accrual service for policy lookups
        accrual_service = AccrualService(self.db)

        for carryover in approved_carryovers:
            try:
                # Get or create the new year balance from pre-fetched data
                balance = existing_balances.get(carryover.employee_id)

                if not balance:
                    # Create balance if it doesn't exist
                    user = users_map.get(carryover.employee_id)
                    if user:
                        vacation_days = self._calculate_vacation_allocation(user)
                        chicago_leave = self._get_chicago_leave_amount(user)
                        balance = PTOBalance(
                            user_id=carryover.employee_id,
                            year=new_year,
                            vacation_total=Decimal(str(vacation_days)),
                            sick_total=Decimal(str(self.DEFAULT_SICK_DAYS)),
                            personal_total=Decimal(str(self.DEFAULT_PERSONAL_DAYS)),
                            sick_carryover=Decimal('0.00'),
                            # Chicago Leave (uses chicago_paid_leave fields)
                            chicago_paid_leave_total=chicago_leave,
                            chicago_paid_leave_used=Decimal('0.00'),
                            chicago_paid_leave_pending=Decimal('0.00'),
                            chicago_paid_leave_carryover=Decimal('0.00')
                        )
                        self.db.add(balance)
                        self.db.flush()
                        existing_balances[carryover.employee_id] = balance

                if balance:
                    hours_approved = carryover.hours_approved or carryover.hours_requested

                    # Get policy cap for this user
                    user = users_map.get(carryover.employee_id)
                    max_carryover_hours = Decimal('0')
                    if user:
                        policy = accrual_service.get_policy_for_employee(user, 'SICK')
                        if policy and policy.max_carryover_hours:
                            max_carryover_hours = policy.max_carryover_hours

                    # Calculate current carryover in hours (sick_carryover is stored in days)
                    current_carryover_hours = (balance.sick_carryover or Decimal('0')) * Decimal('8')

                    # Enforce cap: total carryover cannot exceed policy maximum
                    if max_carryover_hours > 0:
                        available_cap = max_carryover_hours - current_carryover_hours
                        if hours_approved > available_cap:
                            logger.warning(
                                f"Capping carryover for user {carryover.employee_id}: "
                                f"requested {hours_approved}hrs but only {available_cap}hrs allowed under cap"
                            )
                            hours_approved = max(Decimal('0'), available_cap)
                            result['capped'] += 1

                    if hours_approved > 0:
                        # Convert hours to days and add to sick_carryover (NOT vacation_carryover)
                        days_to_carryover = hours_approved / Decimal('8')
                        balance.sick_carryover = (balance.sick_carryover or Decimal('0')) + days_to_carryover
                        result['applied'] += 1

                        logger.info(
                            f"Applied {hours_approved}hrs sick carryover for user {carryover.employee_id} "
                            f"({previous_year} -> {new_year})"
                        )

            except Exception as e:
                error_msg = f"Failed to apply carryover {carryover.id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.flush()  # Flush to DB but don't commit
        return result

    def _auto_carryover_sick_no_commit(self, new_year: int) -> Dict:
        """
        Auto-carryover unused sick leave only (no approval needed - required by law).

        NOTE: Personal leave does NOT carry over (use-it-or-lose-it policy per company handbook).

        Calculates unused sick from previous year and carries over up to policy max.

        Args:
            new_year: The year to apply carryover to

        Returns:
            Dictionary with application results
        """
        result = {'sick_applied': 0, 'errors': []}
        previous_year = new_year - 1

        # Get all active users with previous year balances
        stmt = select(PTOBalance).where(PTOBalance.year == previous_year)
        previous_balances = self.db.execute(stmt).scalars().all()

        if not previous_balances:
            return result

        # Pre-fetch new year balances and users
        user_ids = [b.user_id for b in previous_balances]
        stmt = select(PTOBalance).where(
            PTOBalance.user_id.in_(user_ids),
            PTOBalance.year == new_year
        )
        new_balances = {b.user_id: b for b in self.db.execute(stmt).scalars().all()}

        stmt = select(User).where(User.id.in_(user_ids), User.is_active == True)
        users_map = {u.id: u for u in self.db.execute(stmt).scalars().all()}

        accrual_service = AccrualService(self.db)

        for prev_balance in previous_balances:
            user_id = prev_balance.user_id
            user = users_map.get(user_id)

            if not user:
                continue  # Skip inactive users

            new_balance = new_balances.get(user_id)
            if not new_balance:
                continue  # Skip if no new year balance exists

            try:
                # Calculate unused sick (total + carryover - used)
                unused_sick = (
                    (prev_balance.sick_total or Decimal('0')) +
                    (prev_balance.sick_carryover or Decimal('0')) -
                    (prev_balance.sick_used or Decimal('0'))
                )

                # Get sick policy max carryover
                sick_policy = accrual_service.get_policy_for_employee(user, 'SICK')
                max_sick_carryover_hours = Decimal('0')
                if sick_policy and sick_policy.max_carryover_hours:
                    max_sick_carryover_hours = sick_policy.max_carryover_hours

                # Convert unused sick days to hours and cap
                unused_sick_hours = unused_sick * Decimal('8')
                if max_sick_carryover_hours > 0 and unused_sick_hours > max_sick_carryover_hours:
                    unused_sick_hours = max_sick_carryover_hours

                # Apply sick carryover (convert back to days)
                if unused_sick_hours > 0:
                    new_balance.sick_carryover = unused_sick_hours / Decimal('8')
                    result['sick_applied'] += 1
                    logger.info(f"Auto-carried over {unused_sick_hours}hrs sick for user {user_id}")

                # NOTE: Personal leave does NOT carry over (use-it-or-lose-it)

            except Exception as e:
                error_msg = f"Failed auto-carryover for user {user_id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.flush()
        return result

    def _auto_carryover_chicago_leave_no_commit(self, new_year: int) -> Dict:
        """
        Auto-carryover unused Chicago Paid Leave (no approval needed - per Chicago ordinance).

        Per Chicago Paid Leave ordinance:
        - Employees can carry over up to 16 hours (2 days) of unused Paid Leave
        - Carryover is automatic (no approval required)
        - Carryover is SEPARATE from new year allocation (not combined)

        Ledger separation:
        - chicago_paid_leave_total: New year allocation (40 hours)
        - chicago_paid_leave_carryover: Hours carried from previous year (max 16)
        - These are tracked separately in balance calculations

        Args:
            new_year: The year to apply carryover to

        Returns:
            Dictionary with application results
        """
        result = {'chicago_applied': 0, 'capped': 0, 'errors': []}
        previous_year = new_year - 1

        # Check if Chicago Leave feature is enabled
        stmt = select(SystemSetting).where(SystemSetting.key == 'chicago.safe_leave_enabled')
        chicago_setting = self.db.execute(stmt).scalar_one_or_none()

        if not chicago_setting or not chicago_setting.bool_value:
            logger.debug("Chicago Leave feature not enabled, skipping carryover")
            return result

        # Get all previous year balances that have Chicago Leave data
        stmt = select(PTOBalance).where(
            PTOBalance.year == previous_year,
            PTOBalance.chicago_paid_leave_total > 0
        )
        previous_balances = self.db.execute(stmt).scalars().all()

        if not previous_balances:
            logger.debug(f"No Chicago Leave balances found for {previous_year}")
            return result

        # Pre-fetch new year balances and users
        user_ids = [b.user_id for b in previous_balances]
        stmt = select(PTOBalance).where(
            PTOBalance.user_id.in_(user_ids),
            PTOBalance.year == new_year
        )
        new_balances = {b.user_id: b for b in self.db.execute(stmt).scalars().all()}

        stmt = select(User).where(User.id.in_(user_ids), User.is_active == True)
        users_map = {u.id: u for u in self.db.execute(stmt).scalars().all()}

        for prev_balance in previous_balances:
            user_id = prev_balance.user_id
            user = users_map.get(user_id)

            if not user:
                continue  # Skip inactive users

            # Verify user is still a Chicago employee
            if not user.location_city or user.location_city.lower() != 'chicago':
                continue  # Skip if user is no longer in Chicago

            new_balance = new_balances.get(user_id)
            if not new_balance:
                continue  # Skip if no new year balance exists

            try:
                # Calculate unused Chicago Paid Leave (hours)
                # Formula: total + carryover_from_previous - used
                # Note: pending is NOT subtracted (unused = what's not consumed)
                unused_chicago = (
                    (prev_balance.chicago_paid_leave_total or Decimal('0')) +
                    (prev_balance.chicago_paid_leave_carryover or Decimal('0')) -
                    (prev_balance.chicago_paid_leave_used or Decimal('0'))
                )

                # Skip if nothing to carry over
                if unused_chicago <= 0:
                    logger.debug(f"User {user_id} has no unused Chicago Leave to carry over")
                    continue

                # Cap at 16 hours (per Chicago ordinance)
                carryover_hours = min(unused_chicago, self.CHICAGO_LEAVE_CARRYOVER_MAX)

                if unused_chicago > self.CHICAGO_LEAVE_CARRYOVER_MAX:
                    result['capped'] += 1
                    logger.info(
                        f"User {user_id} Chicago Leave carryover capped: "
                        f"{unused_chicago:.2f}hrs unused -> {carryover_hours:.2f}hrs carried over (16hr max)"
                    )

                # Apply carryover to new year balance (SEPARATE from total allocation)
                new_balance.chicago_paid_leave_carryover = carryover_hours
                result['chicago_applied'] += 1

                logger.info(
                    f"Auto-carried over {carryover_hours:.2f}hrs Chicago Paid Leave for user {user_id} "
                    f"({previous_year} -> {new_year})"
                )

            except Exception as e:
                error_msg = f"Failed Chicago Leave auto-carryover for user {user_id}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        self.db.flush()
        return result

    def _apply_vacation_exception_carryover_no_commit(self, new_year: int) -> Dict:
        """
        Count approved vacation exception carryover requests (for stats only).

        NOTE: Vacation carryover is NOT added to the new year's vacation_carryover field.
        Instead, when vacation is used in the new year and there's an approved carryover,
        the usage is deducted from the FROM year's balance (tracked via hours_used).
        The CarryoverRequest record serves as the reference for available carryover.

        Args:
            new_year: The year to check carryover for

        Returns:
            Dictionary with count of approved carryover requests
        """
        result = {'applied': 0, 'errors': []}
        previous_year = new_year - 1

        # Find approved vacation carryover requests only (for counting/logging)
        stmt = select(CarryoverRequest).where(
            CarryoverRequest.status == 'approved',
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.to_year == new_year
        )
        approved_requests = self.db.execute(stmt).scalars().all()

        if not approved_requests:
            return result

        # Just count - DO NOT add to vacation_carryover
        # The CarryoverRequest record IS the carryover reference
        # Usage will be tracked via hours_used and deducted from FROM year balance
        for request in approved_requests:
            hours_approved = request.hours_approved or request.hours_requested
            if hours_approved > 0:
                result['applied'] += 1
                logger.info(
                    f"Vacation exception carryover available: {hours_approved}hrs for user {request.employee_id} "
                    f"({previous_year} -> {new_year}) - tracked via CarryoverRequest"
                )

        return result

    def generate_federal_holidays(self, year: int) -> Dict:
        """
        Generate federal/market holidays for a given year.
        This is the standalone version that commits after completion.

        Args:
            year: The year to generate holidays for

        Returns:
            Dictionary with creation results
        """
        result = self._generate_federal_holidays_no_commit(year)
        self.db.commit()
        return result

    def _generate_federal_holidays_no_commit(self, year: int) -> Dict:
        """
        Internal: Generate federal holidays without committing (for transaction participation).

        Args:
            year: The year to generate holidays for

        Returns:
            Dictionary with creation results
        """
        result = {'created': 0, 'skipped': 0}

        holidays = self._calculate_federal_holidays(year)

        # Pre-fetch existing federal holidays for this year in one query
        stmt = select(MarketHoliday.holiday_date).where(
            MarketHoliday.year == year,
            MarketHoliday.market == 'Federal'
        )
        existing_holidays = {h.holiday_date for h in self.db.execute(stmt).all()}

        for holiday_data in holidays:
            # Check if already exists from pre-fetched set
            if holiday_data['date'] in existing_holidays:
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

        self.db.flush()  # Flush to DB but don't commit
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
        stmt = select(func.count()).select_from(PTOBalance).where(PTOBalance.year == year)
        balances_count = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(User).where(User.is_active == True)
        active_users = self.db.execute(stmt).scalar()

        # Count pending carryovers
        stmt = select(func.count()).select_from(CarryoverRequest).where(
            CarryoverRequest.status == 'pending',
            CarryoverRequest.from_year == previous_year
        )
        pending_carryovers = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(CarryoverRequest).where(
            CarryoverRequest.status == 'approved',
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.to_year == year
        )
        approved_carryovers = self.db.execute(stmt).scalar()

        # Count holidays
        stmt = select(func.count()).select_from(MarketHoliday).where(MarketHoliday.year == year)
        holidays_count = self.db.execute(stmt).scalar()

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
