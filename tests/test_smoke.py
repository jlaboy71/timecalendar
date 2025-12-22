"""
PTO Central - Smoke Tests

Lightweight smoke tests that verify critical functionality.
Run these before and after making changes to catch regressions early.

Usage:
    pytest tests/test_smoke.py -v -m smoke
    pytest tests/test_smoke.py -v  # all smoke tests
"""
import pytest
import os


class TestImports:
    """Verify critical modules can be imported without errors."""

    @pytest.mark.smoke
    def test_import_main(self):
        """Main application module imports cleanly."""
        # Don't actually start the app, just verify import works
        import nicegui_app.main
        assert nicegui_app.main is not None

    @pytest.mark.smoke
    def test_import_pto_service(self):
        """PTO service imports cleanly."""
        from src.services.pto_service import PTOService
        assert PTOService is not None

    @pytest.mark.smoke
    def test_import_balance_service(self):
        """Balance service imports cleanly."""
        from src.services.balance_service import BalanceService
        assert BalanceService is not None

    @pytest.mark.smoke
    def test_import_models(self):
        """Core models import cleanly."""
        from src.models.user import User
        from src.models.pto_request import PTORequest
        from src.models.pto_balance import PTOBalance
        from src.models.department import Department
        assert all([User, PTORequest, PTOBalance, Department])


class TestDatabase:
    """Verify database connectivity and basic operations."""

    @pytest.mark.smoke
    def test_database_connection(self, db):
        """Can connect to database."""
        # db fixture from conftest.py provides in-memory SQLite
        assert db is not None

    @pytest.mark.smoke
    def test_can_create_user(self, db, test_employee):
        """Can create a user record."""
        assert test_employee.id is not None
        assert test_employee.username == "test_employee"

    @pytest.mark.smoke
    def test_can_create_balance(self, db, test_balance):
        """Can create a PTO balance record."""
        assert test_balance.id is not None
        assert test_balance.vacation_total > 0


class TestBalanceCalculations:
    """Verify balance formulas are correct."""

    @pytest.mark.smoke
    def test_vacation_available_formula(self, db, test_balance):
        """Vacation available = total + carryover - used - pending."""
        from decimal import Decimal

        # Set known values
        test_balance.vacation_total = Decimal("80.00")
        test_balance.vacation_carryover = Decimal("16.00")
        test_balance.vacation_used = Decimal("24.00")
        test_balance.vacation_pending = Decimal("8.00")
        db.commit()
        db.refresh(test_balance)

        # Verify formula: 80 + 16 - 24 - 8 = 64
        expected = Decimal("64.00")
        assert test_balance.vacation_available == expected

    @pytest.mark.smoke
    def test_sick_available_formula(self, db, test_balance):
        """Sick available = total + carryover - used."""
        from decimal import Decimal

        test_balance.sick_total = Decimal("40.00")
        test_balance.sick_carryover = Decimal("8.00")
        test_balance.sick_used = Decimal("16.00")
        db.commit()
        db.refresh(test_balance)

        # Verify formula: 40 + 8 - 16 = 32
        expected = Decimal("32.00")
        assert test_balance.sick_available == expected


class TestAuthentication:
    """Verify authentication logic."""

    @pytest.mark.smoke
    def test_password_hashing(self):
        """Password hashing works correctly."""
        from src.utils.password import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password  # Should be hashed
        assert verify_password(password, hashed)  # Should verify
        assert not verify_password("wrong_password", hashed)  # Should reject wrong

    @pytest.mark.smoke
    def test_user_roles_defined(self):
        """All expected user roles are defined."""
        from src.constants import UserRole

        roles = [r.value for r in UserRole]
        assert "employee" in roles
        assert "manager" in roles
        assert "admin" in roles
        assert "superadmin" in roles


class TestPTOService:
    """Verify PTO service core operations."""

    @pytest.mark.smoke
    def test_pto_service_instantiates(self, db):
        """PTOService can be instantiated."""
        from src.services.pto_service import PTOService

        service = PTOService(db)
        assert service is not None
        assert service.db == db

    @pytest.mark.smoke
    def test_balance_service_instantiates(self, db):
        """BalanceService can be instantiated."""
        from src.services.balance_service import BalanceService

        service = BalanceService(db)
        assert service is not None


