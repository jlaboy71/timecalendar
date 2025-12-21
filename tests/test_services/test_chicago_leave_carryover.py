"""
Tests for Chicago Leave carryover year boundary handling.

Per Chicago Paid Leave ordinance:
- Employees get 40 hours annual allocation
- Up to 16 hours can carry over to next year (automatic, no approval needed)
- Carryover is SEPARATE from new year allocation
- Available balance = total + carryover - used - pending

Test scenarios:
1. Employee ends year with 0, 10, 16, and 30 unused hours
2. Verify Jan 1 availability includes carryover immediately
3. Verify current-year accrual totals exclude carryover
4. Verify usage deductions work correctly
5. Verify payroll spanning year boundary attributes hours correctly
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from src.models.system_setting import SystemSetting
from src.services.year_end_service import YearEndService
from src.services.balance_service import BalanceService
from src.constants import UserRole
from src.utils.password import hash_password


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def chicago_employee(db: Session, test_department: Department) -> User:
    """Create a Chicago-based employee for testing."""
    user = User(
        username="chicago_employee",
        email="chicago@test.com",
        first_name="Chicago",
        last_name="Worker",
        role=UserRole.EMPLOYEE.value,
        department_id=test_department.id,
        hire_date=date(2020, 1, 15),
        is_active=True,
        location_city="Chicago",
        location_state="IL",
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def non_chicago_employee(db: Session, test_department: Department) -> User:
    """Create a non-Chicago employee for testing."""
    user = User(
        username="ny_employee",
        email="ny@test.com",
        first_name="New",
        last_name="Yorker",
        role=UserRole.EMPLOYEE.value,
        department_id=test_department.id,
        hire_date=date(2020, 1, 15),
        is_active=True,
        location_city="New York",
        location_state="NY",
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def enable_chicago_leave(db: Session) -> SystemSetting:
    """Enable Chicago Paid Leave feature in system settings."""
    setting = SystemSetting(
        key='chicago.safe_leave_enabled',
        value='true',  # bool_value property reads this
        description='Enable Chicago Paid Leave'
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def create_chicago_balance(
    db: Session,
    user: User,
    year: int,
    total: Decimal = Decimal('40.00'),
    used: Decimal = Decimal('0.00'),
    pending: Decimal = Decimal('0.00'),
    carryover: Decimal = Decimal('0.00')
) -> PTOBalance:
    """Helper to create a Chicago Leave balance for a user."""
    balance = PTOBalance(
        user_id=user.id,
        year=year,
        vacation_total=Decimal('80.00'),
        vacation_used=Decimal('0.00'),
        vacation_pending=Decimal('0.00'),
        vacation_carryover=Decimal('0.00'),
        sick_total=Decimal('40.00'),
        sick_used=Decimal('0.00'),
        sick_pending=Decimal('0.00'),
        sick_carryover=Decimal('0.00'),
        personal_total=Decimal('16.00'),
        personal_used=Decimal('0.00'),
        personal_pending=Decimal('0.00'),
        personal_carryover=Decimal('0.00'),
        chicago_paid_leave_total=total,
        chicago_paid_leave_used=used,
        chicago_paid_leave_pending=pending,
        chicago_paid_leave_carryover=carryover
    )
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return balance


# ============================================================================
# TEST CASES: Year Boundary Carryover Scenarios
# ============================================================================

class TestChicagoLeaveCarryover:
    """Tests for Chicago Leave carryover at year boundary."""

    def test_zero_unused_hours_no_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Employee with 0 unused hours gets 0 carryover."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Create previous year balance: 40 total, 40 used = 0 unused
        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('40.00')
        )

        # Create new year balance (would be created by year-end processing)
        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: no carryover applied
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('0.00')
        assert result['chicago_applied'] == 0

    def test_ten_unused_hours_full_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Employee with 10 unused hours gets full 10 hours carryover (under cap)."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Create previous year balance: 40 total, 30 used = 10 unused
        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('30.00')
        )

        # Create new year balance
        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: 10 hours carried over
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('10.00')
        assert result['chicago_applied'] == 1
        assert result['capped'] == 0

    def test_sixteen_unused_hours_max_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Employee with 16 unused hours gets exactly 16 hours carryover (at cap)."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Create previous year balance: 40 total, 24 used = 16 unused
        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('24.00')
        )

        # Create new year balance
        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: 16 hours carried over (at cap, not over)
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('16.00')
        assert result['chicago_applied'] == 1
        assert result['capped'] == 0  # Not capped because exactly at limit

    def test_thirty_unused_hours_capped_at_sixteen(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Employee with 30 unused hours gets capped at 16 hours carryover."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Create previous year balance: 40 total, 10 used = 30 unused
        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('10.00')
        )

        # Create new year balance
        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: capped at 16 hours
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('16.00')
        assert result['chicago_applied'] == 1
        assert result['capped'] == 1  # Was capped


class TestJanuaryFirstAvailability:
    """Tests to verify carryover is immediately available on Jan 1."""

    def test_jan_first_includes_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify Jan 1 available balance includes carryover immediately."""
        new_year = date.today().year

        # Create new year balance with carryover applied
        balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00'),
            used=Decimal('0.00'),
            pending=Decimal('0.00')
        )

        # Verify available calculation
        # Available = total + carryover - used - pending = 40 + 16 - 0 - 0 = 56
        assert balance.chicago_paid_leave_available == Decimal('56.00')

    def test_carryover_separate_from_accrual(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify carryover is tracked separately from new year allocation."""
        new_year = date.today().year

        # Create new year balance with carryover
        balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00')
        )

        # Verify fields are separate
        assert balance.chicago_paid_leave_total == Decimal('40.00')  # New year accrual
        assert balance.chicago_paid_leave_carryover == Decimal('16.00')  # Carryover

        # They should not be combined in the total field
        assert balance.chicago_paid_leave_total != Decimal('56.00')


class TestAccrualExcludesCarryover:
    """Tests to verify new year accrual doesn't include carryover."""

    def test_accrual_total_excludes_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify new year allocation (total) is always 40 hours, separate from carryover."""
        new_year = date.today().year

        # Create balance with carryover
        balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00')
        )

        # The total field should always be the annual allocation (40 hours)
        # Carryover is in a separate field
        assert balance.chicago_paid_leave_total == Decimal('40.00')
        assert balance.chicago_paid_leave_carryover == Decimal('16.00')

        # If we were to report "accrued this year", it should be just the total
        accrued_this_year = balance.chicago_paid_leave_total
        assert accrued_this_year == Decimal('40.00')
        assert accrued_this_year != Decimal('56.00')  # Should NOT include carryover


class TestUsageDeductions:
    """Tests to verify usage deductions work correctly with carryover."""

    def test_usage_reduces_available_balance(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify usage reduces available balance correctly."""
        new_year = date.today().year

        balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00'),
            used=Decimal('8.00')  # Used 8 hours
        )

        # Available = 40 + 16 - 8 = 48
        assert balance.chicago_paid_leave_available == Decimal('48.00')

    def test_pending_reduces_available_balance(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify pending requests reduce available balance."""
        new_year = date.today().year

        balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00'),
            used=Decimal('8.00'),
            pending=Decimal('16.00')  # 16 hours pending
        )

        # Available = 40 + 16 - 8 - 16 = 32
        assert balance.chicago_paid_leave_available == Decimal('32.00')


class TestNonChicagoEmployees:
    """Tests to verify non-Chicago employees don't get Chicago Leave carryover."""

    def test_non_chicago_no_carryover(
        self, db: Session, non_chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify non-Chicago employees don't get Chicago Leave carryover."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Even if non-Chicago employee somehow had Chicago Leave balance (shouldn't happen)
        # they should not get carryover
        create_chicago_balance(
            db, non_chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('10.00')  # 30 unused
        )

        new_balance = create_chicago_balance(
            db, non_chicago_employee, new_year,
            total=Decimal('0.00'),  # Non-Chicago doesn't get allocation
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: no carryover for non-Chicago employee
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('0.00')


class TestFeatureDisabled:
    """Tests to verify carryover doesn't happen when feature is disabled."""

    def test_no_carryover_when_feature_disabled(
        self, db: Session, chicago_employee: User
    ):
        """Verify no carryover when Chicago Leave feature is disabled."""
        # Note: enable_chicago_leave fixture NOT used - feature is disabled
        previous_year = date.today().year - 1
        new_year = date.today().year

        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('10.00')  # 30 unused
        )

        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing (feature disabled)
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: no carryover applied because feature is disabled
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('0.00')
        assert result['chicago_applied'] == 0


class TestChainedCarryover:
    """Tests for carryover chains across multiple years."""

    def test_carryover_includes_previous_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify unused carryover from previous year is included in calculation."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Previous year: 40 total + 16 carryover - 20 used = 36 unused
        # But capped at 16
        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            carryover=Decimal('16.00'),  # Had carryover from year before
            used=Decimal('20.00')  # Used 20 hours
        )

        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: unused = 40 + 16 - 20 = 36, capped at 16
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('16.00')
        assert result['capped'] == 1


class TestInactiveUsers:
    """Tests for inactive user handling."""

    def test_inactive_user_no_carryover(
        self, db: Session, chicago_employee: User, enable_chicago_leave: SystemSetting
    ):
        """Verify inactive users don't get carryover."""
        previous_year = date.today().year - 1
        new_year = date.today().year

        # Deactivate the user
        chicago_employee.is_active = False
        db.commit()

        create_chicago_balance(
            db, chicago_employee, previous_year,
            total=Decimal('40.00'),
            used=Decimal('10.00')
        )

        new_balance = create_chicago_balance(
            db, chicago_employee, new_year,
            total=Decimal('40.00'),
            carryover=Decimal('0.00')
        )

        # Run carryover processing
        service = YearEndService(db)
        result = service._auto_carryover_chicago_leave_no_commit(new_year)

        # Verify: no carryover for inactive user
        db.refresh(new_balance)
        assert new_balance.chicago_paid_leave_carryover == Decimal('0.00')
