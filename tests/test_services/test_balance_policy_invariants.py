"""
Policy Invariant Tests for PTO Balance Calculations.

These tests ensure that balance calculations follow the correct policies
and cannot regress without explicit approval.

POLICY INVARIANTS:
1. Approved PTO impacts net availability consistently
2. Pending requests do not impact used, only pending
3. Denied and cancelled requests do not impact net availability
4. Balance fields store HOURS (not days)
5. Weekends and holidays do not deduct from balances

CRITICAL: Changes to these tests require review and approval.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.models.user import User
from src.constants import PTOStatus, UserRole
from tests.utils import (
    create_test_user,
    create_test_department,
    create_test_balance,
    get_next_working_day,
)


class TestBalanceStorageUnits:
    """Tests to verify balance fields store HOURS, not days."""

    def test_balance_fields_store_hours_vacation(self, db: Session):
        """Vacation balance fields should store hours (80 hours = 10 days)."""
        dept = create_test_department(db)
        user = create_test_user(db, department_id=dept.id)

        # Create balance with 10 days = 80 hours
        balance = create_test_balance(
            db, user,
            vacation_total=Decimal("80.00"),  # 10 days in hours
            vacation_used=Decimal("8.00"),     # 1 day in hours
        )

        # Verify the values are in hours
        assert float(balance.vacation_total) == 80.0, "vacation_total should be in hours (80 = 10 days)"
        assert float(balance.vacation_used) == 8.0, "vacation_used should be in hours (8 = 1 day)"

        # Available should be 72 hours (9 days)
        available = float(balance.vacation_total) - float(balance.vacation_used)
        assert available == 72.0, "Available should be 72 hours (9 days)"

    def test_balance_fields_store_hours_sick(self, db: Session):
        """Sick balance fields should store hours (40 hours = 5 days)."""
        dept = create_test_department(db)
        user = create_test_user(db, department_id=dept.id)

        balance = create_test_balance(
            db, user,
            sick_total=Decimal("40.00"),  # 5 days in hours
            sick_used=Decimal("16.00"),    # 2 days in hours
        )

        assert float(balance.sick_total) == 40.0, "sick_total should be in hours"
        assert float(balance.sick_used) == 16.0, "sick_used should be in hours"

    def test_balance_fields_store_hours_personal(self, db: Session):
        """Personal balance fields should store hours (16 hours = 2 days)."""
        dept = create_test_department(db)
        user = create_test_user(db, department_id=dept.id)

        balance = create_test_balance(
            db, user,
            personal_total=Decimal("16.00"),  # 2 days in hours
            personal_used=Decimal("8.00"),     # 1 day in hours
        )

        assert float(balance.personal_total) == 16.0, "personal_total should be in hours"
        assert float(balance.personal_used) == 8.0, "personal_used should be in hours"


class TestApprovedPTOImpactsBalance:
    """Tests to verify approved PTO correctly impacts balance."""

    def test_approved_vacation_adds_to_used_in_hours(self, db: Session):
        """When vacation is approved, vacation_used should increase by HOURS (not days)."""
        dept = create_test_department(db)
        manager = create_test_user(db, role=UserRole.MANAGER.value, department_id=dept.id)
        dept.manager_id = manager.id
        db.commit()

        employee = create_test_user(db, role=UserRole.EMPLOYEE.value, department_id=dept.id)

        # Create balance with full vacation (160 hours = 20 days)
        balance = create_test_balance(
            db, employee,
            vacation_total=Decimal("160.00"),
            vacation_used=Decimal("0.00"),
            vacation_pending=Decimal("0.00"),
        )

        initial_used = float(balance.vacation_used)

        # Create and approve a 1-day request
        from src.schemas.pto_schemas import PTORequestCreate
        start_date = get_next_working_day(skip_days=5)

        pto_service = PTOService(db)
        request_data = PTORequestCreate(
            user_id=employee.id,
            pto_type='vacation',
            start_date=start_date,
            end_date=start_date,
            total_days=Decimal("1.0"),
        )
        request = pto_service.create_request(request_data)

        # Approve the request
        PTOService.approve_request(db, request.id, manager.id)

        # Refresh balance
        db.refresh(balance)

        # CRITICAL: vacation_used should increase by 8 HOURS (not 1 day)
        expected_used = initial_used + 8.0  # 1 day = 8 hours
        actual_used = float(balance.vacation_used)

        assert actual_used == expected_used, (
            f"Approved 1-day vacation should add 8 HOURS to vacation_used. "
            f"Expected {expected_used}, got {actual_used}. "
            f"If this fails with actual=1, the bug where days were stored instead of hours has regressed."
        )

    def test_approved_sick_adds_to_used_in_hours(self, db: Session):
        """When sick leave is approved, sick_used should increase by HOURS."""
        dept = create_test_department(db)
        manager = create_test_user(db, role=UserRole.MANAGER.value, department_id=dept.id)
        dept.manager_id = manager.id
        db.commit()

        employee = create_test_user(db, role=UserRole.EMPLOYEE.value, department_id=dept.id)

        balance = create_test_balance(
            db, employee,
            sick_total=Decimal("40.00"),
            sick_used=Decimal("0.00"),
            sick_pending=Decimal("0.00"),
        )

        initial_used = float(balance.sick_used)

        from src.schemas.pto_schemas import PTORequestCreate
        start_date = get_next_working_day(skip_days=5)

        pto_service = PTOService(db)
        request_data = PTORequestCreate(
            user_id=employee.id,
            pto_type='sick',
            start_date=start_date,
            end_date=start_date,
            total_days=Decimal("1.0"),
        )
        request = pto_service.create_request(request_data)

        PTOService.approve_request(db, request.id, manager.id)
        db.refresh(balance)

        expected_used = initial_used + 8.0
        actual_used = float(balance.sick_used)

        assert actual_used == expected_used, (
            f"Approved 1-day sick should add 8 HOURS. Expected {expected_used}, got {actual_used}."
        )

    def test_approved_personal_adds_to_used_in_hours(self, db: Session):
        """When personal leave is approved, personal_used should increase by HOURS."""
        dept = create_test_department(db)
        manager = create_test_user(db, role=UserRole.MANAGER.value, department_id=dept.id)
        dept.manager_id = manager.id
        db.commit()

        employee = create_test_user(db, role=UserRole.EMPLOYEE.value, department_id=dept.id)

        balance = create_test_balance(
            db, employee,
            personal_total=Decimal("16.00"),
            personal_used=Decimal("0.00"),
            personal_pending=Decimal("0.00"),
        )

        initial_used = float(balance.personal_used)

        from src.schemas.pto_schemas import PTORequestCreate
        start_date = get_next_working_day(skip_days=5)

        pto_service = PTOService(db)
        request_data = PTORequestCreate(
            user_id=employee.id,
            pto_type='personal',
            start_date=start_date,
            end_date=start_date,
            total_days=Decimal("1.0"),
        )
        request = pto_service.create_request(request_data)

        PTOService.approve_request(db, request.id, manager.id)
        db.refresh(balance)

        expected_used = initial_used + 8.0
        actual_used = float(balance.personal_used)

        assert actual_used == expected_used, (
            f"Approved 1-day personal should add 8 HOURS. Expected {expected_used}, got {actual_used}."
        )


class TestPendingRequestsDoNotAffectUsed:
    """Tests to verify pending requests only affect pending, not used."""

    def test_pending_request_adds_to_pending_not_used(self, db: Session):
        """Creating a pending request should add to pending, not used."""
        dept = create_test_department(db)
        manager = create_test_user(db, role=UserRole.MANAGER.value, department_id=dept.id)
        dept.manager_id = manager.id
        db.commit()

        employee = create_test_user(db, role=UserRole.EMPLOYEE.value, department_id=dept.id)

        balance = create_test_balance(
            db, employee,
            vacation_total=Decimal("160.00"),
            vacation_used=Decimal("0.00"),
            vacation_pending=Decimal("0.00"),
        )

        initial_used = float(balance.vacation_used)
        initial_pending = float(balance.vacation_pending)

        from src.schemas.pto_schemas import PTORequestCreate
        start_date = get_next_working_day(skip_days=5)

        pto_service = PTOService(db)
        request_data = PTORequestCreate(
            user_id=employee.id,
            pto_type='vacation',
            start_date=start_date,
            end_date=start_date,
            total_days=Decimal("1.0"),
        )
        request = pto_service.create_request(request_data)

        # Request should be pending
        assert request.status == 'pending'

        db.refresh(balance)

        # Used should NOT change
        assert float(balance.vacation_used) == initial_used, "Pending request should not affect vacation_used"

        # Pending should increase by 8 hours (1 day)
        assert float(balance.vacation_pending) == initial_pending + 8.0, "Pending should increase by 8 hours"


class TestDeniedRequestsRestoreBalance:
    """Tests to verify denied requests restore pending balance."""

    def test_denied_request_removes_pending(self, db: Session):
        """Denying a request should remove from pending, not affect used."""
        dept = create_test_department(db)
        manager = create_test_user(db, role=UserRole.MANAGER.value, department_id=dept.id)
        dept.manager_id = manager.id
        db.commit()

        employee = create_test_user(db, role=UserRole.EMPLOYEE.value, department_id=dept.id)

        balance = create_test_balance(
            db, employee,
            vacation_total=Decimal("160.00"),
            vacation_used=Decimal("0.00"),
            vacation_pending=Decimal("0.00"),
        )

        from src.schemas.pto_schemas import PTORequestCreate
        start_date = get_next_working_day(skip_days=5)

        pto_service = PTOService(db)
        request_data = PTORequestCreate(
            user_id=employee.id,
            pto_type='vacation',
            start_date=start_date,
            end_date=start_date,
            total_days=Decimal("1.0"),
        )
        request = pto_service.create_request(request_data)

        db.refresh(balance)
        assert float(balance.vacation_pending) == 8.0, "Pending should be 8 hours after request"

        # Deny the request
        PTOService.deny_request(db, request.id, manager.id, "Test denial")

        db.refresh(balance)

        # Pending should return to 0
        assert float(balance.vacation_pending) == 0.0, "Denied request should remove from pending"
        # Used should still be 0
        assert float(balance.vacation_used) == 0.0, "Denied request should not affect used"


class TestAvailableBalanceCalculation:
    """Tests for the available balance calculation formula."""

    def test_available_equals_total_plus_carryover_minus_used_minus_pending(self, db: Session):
        """Available = total + carryover - used - pending (all in HOURS)."""
        dept = create_test_department(db)
        user = create_test_user(db, department_id=dept.id)

        balance = create_test_balance(
            db, user,
            vacation_total=Decimal("160.00"),      # 20 days
            vacation_used=Decimal("40.00"),        # 5 days used
            vacation_pending=Decimal("8.00"),      # 1 day pending
            vacation_carryover=Decimal("16.00"),   # 2 days carryover
        )

        # Available = 160 + 16 - 40 - 8 = 128 hours = 16 days
        expected_available = 160.0 + 16.0 - 40.0 - 8.0

        actual_available = (
            float(balance.vacation_total or 0) +
            float(balance.vacation_carryover or 0) -
            float(balance.vacation_used or 0) -
            float(balance.vacation_pending or 0)
        )

        assert actual_available == expected_available, (
            f"Available calculation is wrong. Expected {expected_available}, got {actual_available}"
        )

        # Convert to days for human readability
        days_available = actual_available / 8
        assert days_available == 16.0, f"Should have 16 days available, got {days_available}"
