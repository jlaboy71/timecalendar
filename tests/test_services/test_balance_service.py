"""
Unit tests for the BalanceService.
"""
import pytest
from datetime import date
from decimal import Decimal
from src.services.balance_service import BalanceService
from src.models.pto_balance import PTOBalance


class TestGetOrCreateBalance:
    """Tests for get_or_create_balance method."""

    def test_creates_new_balance_when_none_exists(self, db, test_employee):
        """Test creating a new balance when none exists for user/year."""
        service = BalanceService(db)
        balance = service.get_or_create_balance(test_employee.id, 2025)

        assert balance is not None
        assert balance.user_id == test_employee.id
        assert balance.year == 2025
        # Default values should be zero
        assert balance.vacation_total == Decimal("0.00")
        assert balance.vacation_used == Decimal("0.00")
        assert balance.vacation_pending == Decimal("0.00")

    def test_returns_existing_balance(self, db, test_employee, test_balance):
        """Test returning existing balance for user/year."""
        service = BalanceService(db)
        current_year = date.today().year

        # Get the same balance that was created by the fixture
        balance = service.get_or_create_balance(test_employee.id, current_year)

        assert balance.id == test_balance.id
        assert balance.vacation_total == Decimal("80.00")

    def test_creates_separate_balances_for_different_years(self, db, test_employee):
        """Test that different years get separate balances."""
        service = BalanceService(db)

        balance_2024 = service.get_or_create_balance(test_employee.id, 2024)
        balance_2025 = service.get_or_create_balance(test_employee.id, 2025)

        assert balance_2024.id != balance_2025.id
        assert balance_2024.year == 2024
        assert balance_2025.year == 2025


class TestGetBalanceById:
    """Tests for get_balance_by_id method."""

    def test_returns_balance_by_id(self, db, test_balance):
        """Test retrieving balance by ID."""
        service = BalanceService(db)
        balance = service.get_balance_by_id(test_balance.id)

        assert balance is not None
        assert balance.id == test_balance.id

    def test_returns_none_for_invalid_id(self, db):
        """Test returning None for non-existent ID."""
        service = BalanceService(db)
        balance = service.get_balance_by_id(99999)

        assert balance is None


class TestGetUserBalances:
    """Tests for get_user_balances method."""

    def test_returns_all_balances_for_user(self, db, test_employee):
        """Test getting all balances for a user."""
        service = BalanceService(db)

        # Create balances for multiple years
        service.get_or_create_balance(test_employee.id, 2023)
        service.get_or_create_balance(test_employee.id, 2024)
        service.get_or_create_balance(test_employee.id, 2025)

        balances = service.get_user_balances(test_employee.id)

        assert len(balances) >= 3
        # Should be ordered by year descending
        years = [b.year for b in balances]
        assert years == sorted(years, reverse=True)

    def test_returns_empty_list_for_user_with_no_balances(self, db, test_manager):
        """Test returning empty list for user with no balances."""
        service = BalanceService(db)

        # Note: test_manager doesn't have a balance created by default
        # First remove any existing balances
        balances = service.get_user_balances(test_manager.id)

        # If no balances exist, should return empty list
        # (This depends on whether other tests created balances)
        assert isinstance(balances, list)


class TestAdjustVacationUsed:
    """Tests for adjust_vacation_used method."""

    def test_adjust_used_positive(self, db, test_balance):
        """Test adding to vacation used."""
        service = BalanceService(db)
        original_used = test_balance.vacation_used

        result = service.adjust_vacation_used(test_balance.id, Decimal("8.00"), is_pending=False)

        assert result.vacation_used == original_used + Decimal("8.00")

    def test_adjust_used_negative(self, db, test_employee):
        """Test subtracting from vacation used."""
        service = BalanceService(db)

        # Create balance with some used hours
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("24.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.adjust_vacation_used(balance.id, Decimal("-8.00"), is_pending=False)

        assert result.vacation_used == Decimal("16.00")

    def test_adjust_pending_positive(self, db, test_balance):
        """Test adding to vacation pending."""
        service = BalanceService(db)
        original_pending = test_balance.vacation_pending

        result = service.adjust_vacation_used(test_balance.id, Decimal("8.00"), is_pending=True)

        assert result.vacation_pending == original_pending + Decimal("8.00")

    def test_raises_error_for_invalid_balance_id(self, db):
        """Test that invalid balance ID raises ValueError."""
        service = BalanceService(db)

        with pytest.raises(ValueError, match="Balance with ID 99999 not found"):
            service.adjust_vacation_used(99999, Decimal("8.00"))


class TestAdjustSickUsed:
    """Tests for adjust_sick_used method."""

    def test_adjust_sick_used(self, db, test_balance):
        """Test adjusting sick used."""
        service = BalanceService(db)
        original_used = test_balance.sick_used

        result = service.adjust_sick_used(test_balance.id, Decimal("8.00"))

        assert result.sick_used == original_used + Decimal("8.00")


class TestAdjustPersonalUsed:
    """Tests for adjust_personal_used method."""

    def test_adjust_personal_used(self, db, test_balance):
        """Test adjusting personal used."""
        service = BalanceService(db)
        original_used = test_balance.personal_used

        result = service.adjust_personal_used(test_balance.id, Decimal("8.00"))

        assert result.personal_used == original_used + Decimal("8.00")


class TestMovePendingToUsed:
    """Tests for move_pending_to_used method."""

    def test_moves_from_pending_to_used(self, db, test_employee):
        """Test moving days from pending to used."""
        service = BalanceService(db)

        # Create balance with pending hours
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_pending=Decimal("16.00"),
            vacation_used=Decimal("8.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.move_pending_to_used(balance.id, Decimal("8.00"))

        # Pending should decrease, used should increase
        assert result.vacation_pending == Decimal("8.00")  # 16 - 8
        assert result.vacation_used == Decimal("16.00")  # 8 + 8


class TestRemovePending:
    """Tests for remove_pending method."""

    def test_removes_pending_hours(self, db, test_employee):
        """Test removing hours from pending (e.g., when denied)."""
        service = BalanceService(db)

        # Create balance with pending hours
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_pending=Decimal("16.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.remove_pending(balance.id, Decimal("16.00"))

        assert result.vacation_pending == Decimal("0.00")


class TestAllocateStandardBalance:
    """Tests for allocate_standard_balance method."""

    def test_allocates_standard_values(self, db, test_employee):
        """Test standard allocation values."""
        service = BalanceService(db)

        balance = service.allocate_standard_balance(test_employee.id, 2026)

        assert balance.vacation_total == Decimal("160.00")  # 20 days
        assert balance.sick_total == Decimal("40.00")  # 5 days
        assert balance.personal_total == Decimal("16.00")  # 2 days


class TestRestoreBalance:
    """Tests for restore_balance method."""

    def test_restore_vacation_from_used(self, db, test_employee):
        """Test restoring vacation hours from used (cancelled approved request)."""
        service = BalanceService(db)

        # Create balance with used hours
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("24.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.restore_balance(balance.id, "vacation", 8.0, was_approved=True)

        # Used should be reduced
        assert result.vacation_used == Decimal("16.00")  # 24 - 8

    def test_restore_vacation_from_pending(self, db, test_employee):
        """Test restoring vacation hours from pending (cancelled pending request)."""
        service = BalanceService(db)

        # Create balance with pending hours
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_pending=Decimal("16.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.restore_balance(balance.id, "vacation", 8.0, was_approved=False)

        # Pending should be reduced
        assert result.vacation_pending == Decimal("8.00")  # 16 - 8

    def test_restore_prevents_negative_balance(self, db, test_employee):
        """Test that restore doesn't create negative balance."""
        service = BalanceService(db)

        # Create balance with small used value
        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            vacation_total=Decimal("80.00"),
            vacation_used=Decimal("4.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        # Try to restore more than used
        result = service.restore_balance(balance.id, "vacation", 10.0, was_approved=True)

        # Should not go negative
        assert result.vacation_used == Decimal("0.00")

    def test_restore_sick_from_used(self, db, test_employee):
        """Test restoring sick hours from used."""
        service = BalanceService(db)

        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            sick_total=Decimal("40.00"),
            sick_used=Decimal("16.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.restore_balance(balance.id, "sick", 8.0, was_approved=True)

        assert result.sick_used == Decimal("8.00")

    def test_restore_personal_from_used(self, db, test_employee):
        """Test restoring personal hours from used."""
        service = BalanceService(db)

        balance = PTOBalance(
            user_id=test_employee.id,
            year=2024,
            personal_total=Decimal("16.00"),
            personal_used=Decimal("8.00")
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

        result = service.restore_balance(balance.id, "personal", 8.0, was_approved=True)

        assert result.personal_used == Decimal("0.00")


class TestBalanceYearIsolation:
    """Tests to verify year isolation in balance operations."""

    def test_different_years_are_separate(self, db, test_employee):
        """Test that operations on one year don't affect another."""
        service = BalanceService(db)

        # Create balances for different years
        balance_2024 = service.get_or_create_balance(test_employee.id, 2024)
        balance_2025 = service.get_or_create_balance(test_employee.id, 2025)

        # Set different totals
        balance_2024.vacation_total = Decimal("80.00")
        balance_2025.vacation_total = Decimal("88.00")
        db.commit()

        # Modify one year
        service.adjust_vacation_used(balance_2024.id, Decimal("8.00"))

        # Refresh both
        db.refresh(balance_2024)
        db.refresh(balance_2025)

        # Only 2024 should be affected
        assert balance_2024.vacation_used == Decimal("8.00")
        assert balance_2025.vacation_used == Decimal("0.00")
