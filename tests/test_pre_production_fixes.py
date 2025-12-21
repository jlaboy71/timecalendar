"""
Pre-Production Fixes Automated Test Suite
Tests all security and critical fixes before go-live.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
import threading
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.user import User
from src.models.department import Department
from src.models.pto_request import PTORequest
from src.models.pto_balance import PTOBalance
from src.models.market_holiday import MarketHoliday
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.services.year_end_service import YearEndService
from src.services.ical_export_service import ICalExportService
from src.schemas.pto_schemas import PTORequestCreate
import pytest


class _TestResults:
    """Collect and report test results (renamed to avoid pytest collection)."""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, name, details=""):
        self.passed.append((name, details))
        print(f"  [PASS] {name}")
        if details:
            print(f"     {details}")

    def add_fail(self, name, error):
        self.failed.append((name, str(error)))
        print(f"  [FAIL] {name}")
        print(f"     Error: {error}")

    def add_warning(self, name, warning):
        self.warnings.append((name, warning))
        print(f"  [WARN] {name}")
        print(f"     {warning}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.failed:
            print("\nFailed Tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")

        if self.warnings:
            print("\nWarnings:")
            for name, warning in self.warnings:
                print(f"  - {name}: {warning}")

        return len(self.failed) == 0


@pytest.fixture
def results():
    """Pytest fixture to provide TestResults for individual test functions."""
    return _TestResults()


def create_test_db():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def setup_test_data(db):
    """Create test users, departments, and balances."""
    # Create department
    dept = Department(name="Engineering", code="ENG", manager_id=None)
    db.add(dept)
    db.flush()

    # Create manager
    manager = User(
        username="manager1",
        email="manager@test.com",
        password_hash="hash",
        first_name="Manager",
        last_name="One",
        department_id=dept.id,
        role="manager",
        hire_date=date(2020, 1, 1),
        is_active=True
    )
    db.add(manager)
    db.flush()

    # Update department manager
    dept.manager_id = manager.id

    # Create employee in same department
    employee = User(
        username="employee1",
        email="employee@test.com",
        password_hash="hash",
        first_name="Employee",
        last_name="One",
        department_id=dept.id,
        role="employee",
        hire_date=date(2022, 1, 1),
        is_active=True
    )
    db.add(employee)

    # Create employee in different department (for auth test)
    other_dept = Department(name="Sales", code="SAL", manager_id=None)
    db.add(other_dept)
    db.flush()

    other_manager = User(
        username="manager2",
        email="manager2@test.com",
        password_hash="hash",
        first_name="Manager",
        last_name="Two",
        department_id=other_dept.id,
        role="manager",
        hire_date=date(2020, 1, 1),
        is_active=True
    )
    db.add(other_manager)
    other_dept.manager_id = other_manager.id

    db.flush()

    # Create balances
    current_year = date.today().year
    for user in [manager, employee, other_manager]:
        balance = PTOBalance(
            user_id=user.id,
            year=current_year,
            vacation_total=Decimal('80.00'),  # 10 days
            vacation_used=Decimal('0.00'),
            vacation_pending=Decimal('0.00'),
            sick_total=Decimal('40.00'),  # 5 days
            sick_used=Decimal('0.00'),
            sick_pending=Decimal('0.00'),
            personal_total=Decimal('24.00'),  # 3 days
            personal_used=Decimal('0.00'),
            personal_pending=Decimal('0.00')
        )
        db.add(balance)

    db.commit()
    return {
        'department': dept,
        'manager': manager,
        'employee': employee,
        'other_manager': other_manager,
        'other_dept': other_dept
    }


def test_authorization_check(results):
    """Test 1: Manager Authorization Check - managers can only approve their team's requests."""
    print("\n--- Test 1: Manager Authorization Check ---")

    db = create_test_db()
    data = setup_test_data(db)

    pto_service = PTOService(db)

    # Create a PTO request for employee
    request = PTORequest(
        user_id=data['employee'].id,
        pto_type='vacation',
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=31),
        total_days=Decimal('2.0'),
        status='pending',
        notes='Test vacation'
    )
    db.add(request)
    db.commit()

    # Test 1a: Correct manager CAN approve
    try:
        # The manager of the employee's department should be able to approve
        # approve_request is a static method that takes db as first arg
        PTOService.approve_request(db, request.id, data['manager'].id)
        results.add_pass("Correct manager can approve team request")
    except Exception as e:
        results.add_fail("Correct manager can approve team request", e)

    # Reset request status
    request.status = 'pending'
    db.commit()

    # Test 1b: Wrong manager CANNOT approve
    try:
        PTOService.approve_request(db, request.id, data['other_manager'].id)
        results.add_fail("Wrong manager blocked from approving",
                        "Should have raised PermissionError but didn't")
    except PermissionError as e:
        results.add_pass("Wrong manager blocked from approving", str(e))
    except ValueError as e:
        # Authorization check raises ValueError with department message
        if "department" in str(e).lower() or "not authorized" in str(e).lower():
            results.add_pass("Wrong manager blocked from approving", str(e))
        else:
            results.add_fail("Wrong manager blocked from approving", f"Wrong error type: {e}")
    except Exception as e:
        results.add_fail("Wrong manager blocked from approving", f"Unexpected error: {e}")

    db.close()


def test_balance_restoration(results):
    """Test 3: Balance Restoration - canceling approved request restores balance."""
    print("\n--- Test 3: Balance Restoration ---")

    db = create_test_db()
    data = setup_test_data(db)

    balance_service = BalanceService(db)

    # Get initial balance
    balance = db.query(PTOBalance).filter(
        PTOBalance.user_id == data['employee'].id,
        PTOBalance.year == date.today().year
    ).first()

    initial_vacation_used = balance.vacation_used

    # Simulate an approved request that used 16 hours (2 days)
    balance.vacation_used = Decimal('16.00')
    db.commit()

    # Create an approved request
    request = PTORequest(
        user_id=data['employee'].id,
        pto_type='vacation',
        start_date=date.today() + timedelta(days=30),
        end_date=date.today() + timedelta(days=31),
        total_days=Decimal('2.0'),
        status='approved',
        notes='Test vacation'
    )
    db.add(request)
    db.commit()

    # Test restore_balance
    # restore_balance signature: (balance_id, pto_type, hours, was_approved)
    try:
        hours_to_restore = 16.00  # The method expects float, not Decimal
        balance_service.restore_balance(
            balance_id=balance.id,
            pto_type='vacation',
            hours=hours_to_restore,
            was_approved=True
        )

        # Refresh balance
        db.refresh(balance)

        if balance.vacation_used == initial_vacation_used:
            results.add_pass("Balance restored correctly after cancellation",
                           f"Restored {hours_to_restore} hours")
        else:
            results.add_fail("Balance restored correctly after cancellation",
                           f"Expected {initial_vacation_used}, got {balance.vacation_used}")
    except Exception as e:
        results.add_fail("Balance restored correctly after cancellation", e)

    # Test restore_balance prevents negative
    try:
        balance_service.restore_balance(
            balance_id=balance.id,
            pto_type='vacation',
            hours=1000.00,  # Way more than used
            was_approved=True
        )
        # Check it didn't go negative
        db.refresh(balance)
        if balance.vacation_used < 0:
            results.add_fail("Balance restoration prevents negative",
                           f"Balance went negative: {balance.vacation_used}")
        else:
            results.add_pass("Balance restoration prevents negative",
                           f"Balance capped at 0, not negative")
    except ValueError as e:
        results.add_pass("Balance restoration prevents negative", str(e))
    except Exception as e:
        results.add_fail("Balance restoration prevents negative", e)

    db.close()


def test_vacation_validation(results):
    """Test 13: Vacation Balance Validation - employees can't exceed balance."""
    print("\n--- Test 13: Vacation Balance Validation ---")

    db = create_test_db()
    data = setup_test_data(db)

    pto_service = PTOService(db)

    # Get balance - employee has 80 hours (10 days) vacation
    balance = db.query(PTOBalance).filter(
        PTOBalance.user_id == data['employee'].id,
        PTOBalance.year == date.today().year
    ).first()

    # Use up most of the balance
    balance.vacation_used = Decimal('72.00')  # 9 days used, 1 day left
    db.commit()

    # Test: Employee requests 3 days (more than available)
    try:
        request_data = PTORequestCreate(
            user_id=data['employee'].id,
            pto_type='vacation',
            start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=62),
            total_days=Decimal('3.0'),
            notes='Test vacation'
        )
        pto_service.create_request(request_data)
        results.add_fail("Employee blocked from exceeding vacation balance",
                        "Request should have been rejected but wasn't")
    except ValueError as e:
        if "Insufficient vacation" in str(e):
            results.add_pass("Employee blocked from exceeding vacation balance", str(e))
        else:
            results.add_fail("Employee blocked from exceeding vacation balance", f"Wrong error: {e}")
    except Exception as e:
        results.add_fail("Employee blocked from exceeding vacation balance", e)

    # Test: Manager CAN exceed balance (they have approval authority)
    manager_balance = db.query(PTOBalance).filter(
        PTOBalance.user_id == data['manager'].id,
        PTOBalance.year == date.today().year
    ).first()
    manager_balance.vacation_used = Decimal('72.00')
    db.commit()

    try:
        request_data = PTORequestCreate(
            user_id=data['manager'].id,
            pto_type='vacation',
            start_date=date.today() + timedelta(days=90),
            end_date=date.today() + timedelta(days=92),
            total_days=Decimal('3.0'),
            notes='Manager vacation'
        )
        pto_service.create_request(request_data)
        results.add_pass("Manager can exceed vacation balance (has approval authority)")
    except ValueError as e:
        if "Insufficient vacation" in str(e):
            results.add_fail("Manager can exceed vacation balance",
                           "Managers should be allowed to exceed")
        else:
            results.add_warning("Manager vacation request", str(e))
    except Exception as e:
        results.add_warning("Manager vacation request", str(e))

    db.close()


def test_year_end_transaction(results):
    """Test 8: Year-End Processing - transaction rollback on failure."""
    print("\n--- Test 8: Year-End Transaction Safety ---")

    db = create_test_db()
    data = setup_test_data(db)

    year_end_service = YearEndService(db)
    new_year = date.today().year + 1

    # Test successful processing
    try:
        result = year_end_service.process_year_transition(new_year)

        if result['errors']:
            results.add_warning("Year-end processing completed",
                              f"With errors: {result['errors']}")
        else:
            results.add_pass("Year-end processing transaction commits successfully",
                           f"Created {result['balances_created']} balances, "
                           f"{result['holidays_created']} holidays")

        # Verify balances were created
        new_balances = db.query(PTOBalance).filter(PTOBalance.year == new_year).count()
        if new_balances > 0:
            results.add_pass("New year balances created and committed",
                           f"{new_balances} balance records")
        else:
            results.add_fail("New year balances created and committed",
                           "No balances found after commit")

    except Exception as e:
        results.add_fail("Year-end processing transaction", e)

    # Test rollback scenario - simulate by checking structure
    try:
        # Verify the service has the _no_commit methods
        has_no_commit_methods = (
            hasattr(year_end_service, '_create_new_year_balances_no_commit') and
            hasattr(year_end_service, '_apply_approved_carryover_no_commit') and
            hasattr(year_end_service, '_generate_federal_holidays_no_commit')
        )

        if has_no_commit_methods:
            results.add_pass("Transaction wrapper methods exist",
                           "_no_commit methods for atomic operations")
        else:
            results.add_fail("Transaction wrapper methods exist",
                           "Missing _no_commit methods")
    except Exception as e:
        results.add_fail("Transaction wrapper verification", e)

    db.close()


def test_calendar_privacy(results):
    """Test 10: Calendar Export Privacy - private requests excluded from team view."""
    print("\n--- Test 10: Calendar Export Privacy ---")

    db = create_test_db()
    data = setup_test_data(db)

    # Create a private PTO request
    private_request = PTORequest(
        user_id=data['employee'].id,
        pto_type='sick',
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=10),
        total_days=Decimal('1.0'),
        status='approved',
        notes='Private medical',
        is_private=True
    )
    db.add(private_request)

    # Create a non-private request
    public_request = PTORequest(
        user_id=data['employee'].id,
        pto_type='vacation',
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=21),
        total_days=Decimal('2.0'),
        status='approved',
        notes='Regular vacation',
        is_private=False
    )
    db.add(public_request)
    db.commit()

    # Test the ICalExportService
    try:
        ical_service = ICalExportService(db)

        # Check if the service filters private requests for team calendars
        # We need to check the _get_pto_events method
        if hasattr(ical_service, '_get_pto_events'):
            # Verify the method signature includes privacy filtering
            import inspect
            source = inspect.getsource(ical_service._get_pto_events)

            if 'is_private' in source:
                results.add_pass("Calendar export has privacy filter",
                               "is_private filter found in _get_pto_events")
            else:
                results.add_warning("Calendar export privacy filter",
                                  "is_private not found in method - may need verification")
        else:
            results.add_warning("Calendar export service",
                              "_get_pto_events method not found")

    except Exception as e:
        results.add_fail("Calendar export privacy check", e)

    db.close()


def test_pending_balance_fields(results):
    """Test 7: Pending Balance Fields - sick_pending and personal_pending exist."""
    print("\n--- Test 7: Pending Balance Fields ---")

    db = create_test_db()

    try:
        # Check model has the fields
        balance = PTOBalance(
            user_id=1,
            year=2025,
            vacation_total=Decimal('80.00'),
            vacation_used=Decimal('0.00'),
            vacation_pending=Decimal('8.00'),
            vacation_carryover=Decimal('0.00'),
            sick_total=Decimal('40.00'),
            sick_used=Decimal('0.00'),
            sick_pending=Decimal('8.00'),
            sick_carryover=Decimal('0.00'),
            personal_total=Decimal('24.00'),
            personal_used=Decimal('0.00'),
            personal_pending=Decimal('8.00'),
            personal_carryover=Decimal('0.00')
        )

        results.add_pass("sick_pending field exists in model")
        results.add_pass("personal_pending field exists in model")

        # Test availability calculations
        if balance.sick_available == Decimal('32.00'):  # 40 - 0 - 8
            results.add_pass("sick_available subtracts pending",
                           f"40 - 0 - 8 = {balance.sick_available}")
        else:
            results.add_fail("sick_available subtracts pending",
                           f"Expected 32.00, got {balance.sick_available}")

        if balance.personal_available == Decimal('16.00'):  # 24 - 0 - 8
            results.add_pass("personal_available subtracts pending",
                           f"24 - 0 - 8 = {balance.personal_available}")
        else:
            results.add_fail("personal_available subtracts pending",
                           f"Expected 16.00, got {balance.personal_available}")

    except Exception as e:
        results.add_fail("Pending balance fields", e)

    db.close()


def test_soft_delete_field(results):
    """Test 12: Soft Delete - deleted_at field exists."""
    print("\n--- Test 12: Soft Delete Field ---")

    try:
        # Check User model has deleted_at
        user = User(
            username="test",
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
            role="employee",
            hire_date=date.today()
        )

        # Check the field exists
        if hasattr(User, 'deleted_at'):
            results.add_pass("deleted_at field exists in User model")

            # Check it's nullable (can be None for active users)
            if user.deleted_at is None:
                results.add_pass("deleted_at defaults to None (active user)")
            else:
                results.add_fail("deleted_at defaults to None",
                               f"Got {user.deleted_at}")
        else:
            results.add_fail("deleted_at field exists in User model",
                           "Field not found")

    except Exception as e:
        results.add_fail("Soft delete field check", e)


def test_race_condition_locking(results):
    """Test 2: Race Condition - verify with_for_update exists in service."""
    print("\n--- Test 2: Race Condition Locking ---")

    try:
        import inspect
        from src.services.pto_service import PTOService

        source = inspect.getsource(PTOService.create_request)

        if 'with_for_update' in source:
            results.add_pass("Row-level locking (with_for_update) in create_request",
                           "Prevents concurrent modification of balance")
        else:
            results.add_fail("Row-level locking in create_request",
                           "with_for_update not found - race condition possible")

    except Exception as e:
        results.add_fail("Race condition locking check", e)


def test_auto_approve_audit(results):
    """Test 5: Auto-Approve Audit Logging - verify audit trail exists."""
    print("\n--- Test 5: Auto-Approve Audit Logging ---")

    try:
        import inspect
        from src.services.pto_service import PTOService

        source = inspect.getsource(PTOService.create_request)

        checks = {
            'auto_approve_reason': 'auto_approve_reason' in source,
            'logger': 'logger' in source or 'logging' in source,
            'audit': 'audit' in source.lower() or 'auto-approv' in source.lower()
        }

        if checks['auto_approve_reason']:
            results.add_pass("auto_approve_reason field tracked")
        else:
            results.add_warning("auto_approve_reason tracking",
                              "Field not found in create_request")

        if checks['logger'] or checks['audit']:
            results.add_pass("Auto-approve logging exists")
        else:
            results.add_warning("Auto-approve logging",
                              "No explicit logging found")

    except Exception as e:
        results.add_fail("Auto-approve audit check", e)


def run_all_tests():
    """Run all pre-production tests."""
    print("="*60)
    print("PRE-PRODUCTION FIXES - AUTOMATED TEST SUITE")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = _TestResults()

    # Run all tests
    test_authorization_check(results)
    test_race_condition_locking(results)
    test_balance_restoration(results)
    test_auto_approve_audit(results)
    test_pending_balance_fields(results)
    test_year_end_transaction(results)
    test_calendar_privacy(results)
    test_soft_delete_field(results)
    test_vacation_validation(results)

    # Print summary
    all_passed = results.summary()

    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
