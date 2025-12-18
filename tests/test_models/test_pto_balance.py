"""
Unit tests for the PTOBalance model.
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from src.models.pto_balance import PTOBalance


class TestPTOBalanceCreation:
    """Tests for basic PTOBalance creation."""

    def test_balance_creation(self, db, test_employee):
        """Test creating a basic PTO balance."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            sick_total=Decimal("40.00"),
            personal_total=Decimal("16.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        assert balance.id is not None
        assert balance.user_id == test_employee.id
        assert balance.year == 2025

    def test_balance_with_all_fields(self, db, test_employee):
        """Test creating balance with all fields populated."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("24.00"),
            vacation_pending=Decimal("8.00"),
            vacation_carryover=Decimal("16.00"),
            sick_total=Decimal("40.00"),
            sick_used=Decimal("8.00"),
            sick_carryover=Decimal("4.00"),
            personal_total=Decimal("16.00"),
            personal_used=Decimal("8.00"),
            personal_carryover=Decimal("0.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        assert balance.vacation_total == Decimal("80.00")
        assert balance.vacation_used == Decimal("24.00")
        assert balance.vacation_pending == Decimal("8.00")
        assert balance.vacation_carryover == Decimal("16.00")


class TestPTOBalanceDefaultValues:
    """Tests for default values."""

    def test_defaults_are_zero(self, db, test_employee):
        """Test that all balance fields default to Decimal('0.00')."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        # Vacation defaults
        assert balance.vacation_total == Decimal("0.00")
        assert balance.vacation_used == Decimal("0.00")
        assert balance.vacation_pending == Decimal("0.00")
        assert balance.vacation_carryover == Decimal("0.00")

        # Sick defaults
        assert balance.sick_total == Decimal("0.00")
        assert balance.sick_used == Decimal("0.00")
        assert balance.sick_pending == Decimal("0.00")
        assert balance.sick_carryover == Decimal("0.00")

        # Personal defaults
        assert balance.personal_total == Decimal("0.00")
        assert balance.personal_used == Decimal("0.00")
        assert balance.personal_pending == Decimal("0.00")
        assert balance.personal_carryover == Decimal("0.00")

        # Remote work default
        assert balance.remote_weekly_used == 0


class TestVacationAvailableProperty:
    """Tests for vacation_available property."""

    def test_vacation_available_basic(self, test_balance):
        """Test basic vacation available calculation."""
        # test_balance has: total=80, used=0, pending=0, carryover=0
        assert test_balance.vacation_available == Decimal("80.00")

    def test_vacation_available_with_used(self, db, test_employee):
        """Test vacation available with used hours."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("24.00")
        )
        db.add(balance)
        db.commit()

        # 80 - 24 = 56
        assert balance.vacation_available == Decimal("56.00")

    def test_vacation_available_with_pending(self, db, test_employee):
        """Test vacation available with pending hours."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_pending=Decimal("16.00")
        )
        db.add(balance)
        db.commit()

        # 80 - 16 = 64
        assert balance.vacation_available == Decimal("64.00")

    def test_vacation_available_with_carryover(self, db, test_employee):
        """Test vacation available includes carryover."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_carryover=Decimal("24.00")
        )
        db.add(balance)
        db.commit()

        # 80 + 24 = 104
        assert balance.vacation_available == Decimal("104.00")

    def test_vacation_available_full_calculation(self, db, test_employee):
        """Test full vacation available calculation: total + carryover - used - pending."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("24.00"),
            vacation_pending=Decimal("8.00"),
            vacation_carryover=Decimal("16.00")
        )
        db.add(balance)
        db.commit()

        # 80 + 16 - 24 - 8 = 64
        assert balance.vacation_available == Decimal("64.00")


class TestSickAvailableProperty:
    """Tests for sick_available property."""

    def test_sick_available_basic(self, test_balance):
        """Test basic sick available calculation."""
        # test_balance has: total=40, used=0, pending=0, carryover=0
        assert test_balance.sick_available == Decimal("40.00")

    def test_sick_available_full_calculation(self, db, test_employee):
        """Test full sick available calculation."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            sick_total=Decimal("40.00"),
            sick_used=Decimal("8.00"),
            sick_pending=Decimal("8.00"),
            sick_carryover=Decimal("8.00")
        )
        db.add(balance)
        db.commit()

        # 40 + 8 - 8 - 8 = 32
        assert balance.sick_available == Decimal("32.00")


class TestPersonalAvailableProperty:
    """Tests for personal_available property."""

    def test_personal_available_basic(self, test_balance):
        """Test basic personal available calculation."""
        # test_balance has: total=16, used=0, pending=0, carryover=0
        assert test_balance.personal_available == Decimal("16.00")

    def test_personal_available_full_calculation(self, db, test_employee):
        """Test full personal available calculation."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            personal_total=Decimal("16.00"),
            personal_used=Decimal("8.00"),
            personal_pending=Decimal("0.00"),
            personal_carryover=Decimal("8.00")
        )
        db.add(balance)
        db.commit()

        # 16 + 8 - 8 - 0 = 16
        assert balance.personal_available == Decimal("16.00")


class TestBalanceUniqueConstraint:
    """Tests for the user_id + year unique constraint."""

    def test_unique_constraint_allows_different_years(self, db, test_employee):
        """Test that same user can have balances for different years."""
        balance_2024 = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00")
        )
        balance_2025 = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("88.00")
        )
        db.add(balance_2024)
        db.add(balance_2025)
        db.commit()

        assert balance_2024.id is not None
        assert balance_2025.id is not None
        assert balance_2024.id != balance_2025.id

    def test_unique_constraint_prevents_duplicate(self, db, test_employee):
        """Test that duplicate user_id + year is rejected."""
        balance1 = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00")
        )
        db.add(balance1)
        db.commit()

        balance2 = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("88.00")
        )
        db.add(balance2)

        with pytest.raises(IntegrityError):
            db.commit()


class TestCarryoverFields:
    """Tests for carryover tracking fields."""

    def test_carryover_can_be_set(self, db, test_employee):
        """Test that carryover fields can be set."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            vacation_total=Decimal("80.00"),
            vacation_carryover=Decimal("24.00"),
            sick_total=Decimal("40.00"),
            sick_carryover=Decimal("16.00"),
            personal_total=Decimal("16.00"),
            personal_carryover=Decimal("8.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        assert balance.vacation_carryover == Decimal("24.00")
        assert balance.sick_carryover == Decimal("16.00")
        assert balance.personal_carryover == Decimal("8.00")


class TestChicagoLeaveFields:
    """Tests for Chicago-specific leave fields."""

    def test_chicago_leave_defaults(self, db, test_employee):
        """Test Chicago leave fields default to zero."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        # Paid leave defaults
        assert balance.chicago_paid_leave_total == Decimal("0.00")
        assert balance.chicago_paid_leave_used == Decimal("0.00")
        assert balance.chicago_paid_leave_pending == Decimal("0.00")
        assert balance.chicago_paid_leave_carryover == Decimal("0.00")

    def test_chicago_paid_leave_available(self, db, test_employee):
        """Test Chicago paid leave available calculation."""
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2025,
            chicago_paid_leave_total=Decimal("40.00"),
            chicago_paid_leave_used=Decimal("16.00"),
            chicago_paid_leave_pending=Decimal("8.00"),
            chicago_paid_leave_carryover=Decimal("8.00")
        )
        db.add(balance)
        db.commit()

        # 40 + 8 - 16 - 8 = 24
        assert balance.chicago_paid_leave_available == Decimal("24.00")


class TestBalanceRelationships:
    """Tests for balance relationships."""

    def test_balance_belongs_to_user(self, test_balance, test_employee):
        """Test that balance has user relationship."""
        assert test_balance.user_id == test_employee.id
        assert test_balance.user is not None
        assert test_balance.user.username == test_employee.username
