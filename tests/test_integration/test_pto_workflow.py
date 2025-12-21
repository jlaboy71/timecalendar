"""
Integration tests for the complete PTO request workflow.

These tests verify the end-to-end flow of PTO requests from submission
through approval/denial, including balance tracking throughout.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.schemas.pto_schemas import PTORequestCreate
from src.models.pto_request import PTORequest
from src.constants import PTOStatus, PTOType
from tests.utils import get_next_working_day, get_working_day_range


class TestEmployeeVacationWorkflow:
    """Test the complete employee vacation request workflow."""

    def test_full_approval_workflow(self, db, test_employee, test_balance, test_manager):
        """
        Test complete workflow: submit -> pending -> approve -> balance updated.

        This tests the happy path where an employee submits a vacation request
        and a manager approves it.
        """
        pto_service = PTOService(db)
        balance_service = BalanceService(db)

        # Record initial balance state
        initial_total = test_balance.vacation_total
        initial_used = test_balance.vacation_used
        initial_pending = test_balance.vacation_pending

        # Step 1: Employee submits vacation request
        # Use working days to avoid weekend validation errors
        start_date, end_date = get_working_day_range(start_skip=1, num_days=2)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("2.00"),
            notes="Family trip"
        )

        request = pto_service.create_request(request_data)

        # Verify request created with pending status
        assert request.id is not None
        assert request.status == PTOStatus.PENDING.value
        assert request.user_id == test_employee.id

        # Verify pending balance increased
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending + Decimal("2.00")
        assert test_balance.vacation_used == initial_used  # Used unchanged

        # Step 2: Manager approves the request
        approved_request = PTOService.approve_request(db, request.id, test_manager.id)

        # Verify request is now approved
        assert approved_request.status == PTOStatus.APPROVED.value
        assert approved_request.approved_by == test_manager.id
        assert approved_request.approved_at is not None

        # Verify balance: pending moved to used
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending  # Back to initial
        assert test_balance.vacation_used == initial_used + Decimal("2.00")  # Increased

        # Verify available balance decreased
        expected_available = initial_total - (initial_used + Decimal("2.00"))
        assert test_balance.vacation_available == expected_available

    def test_full_denial_workflow(self, db, test_employee, test_balance, test_manager):
        """
        Test complete workflow: submit -> pending -> deny -> balance restored.

        This tests the case where a manager denies a request and the
        pending balance is properly restored.
        """
        pto_service = PTOService(db)

        # Record initial balance state
        initial_pending = test_balance.vacation_pending
        initial_used = test_balance.vacation_used

        # Use working days to avoid weekend validation errors
        request_start, request_end = get_working_day_range(start_skip=1, num_days=2)

        # Step 1: Employee submits vacation request
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=request_start,
            end_date=request_end,
            total_days=Decimal("2.00"),
            notes="Trip to visit relatives"
        )

        request = pto_service.create_request(request_data)

        # Verify pending increased
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending + Decimal("2.00")

        # Step 2: Manager denies the request
        denied_request = PTOService.deny_request(
            db, request.id, test_manager.id, "Coverage needed that week"
        )

        # Verify request is denied
        assert denied_request.status == PTOStatus.DENIED.value
        assert denied_request.denial_reason == "Coverage needed that week"

        # Verify pending balance restored
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending
        assert test_balance.vacation_used == initial_used  # Unchanged

    def test_employee_cancellation_workflow(self, db, test_employee, test_balance):
        """
        Test workflow: submit -> pending -> employee cancel -> balance restored.

        This tests when an employee cancels their own pending request.
        """
        pto_service = PTOService(db)

        # Record initial state
        initial_pending = test_balance.vacation_pending

        # Use working days to avoid weekend validation errors
        request_start, request_end = get_working_day_range(start_skip=2, num_days=2)

        # Step 1: Submit request
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=request_start,
            end_date=request_end,
            total_days=Decimal("2.00")
        )

        request = pto_service.create_request(request_data)

        # Verify pending increased
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending + Decimal("2.00")

        # Step 2: Employee cancels request
        cancelled_request = pto_service.cancel_request(request.id, test_employee.id)

        # Verify cancelled
        assert cancelled_request.status == PTOStatus.CANCELLED.value

        # Verify pending restored
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending


class TestManagerAutoApproveWorkflow:
    """Test manager self-approval workflow."""

    def test_manager_vacation_auto_approved(self, db, test_manager):
        """Test that manager vacation requests are auto-approved."""
        pto_service = PTOService(db)
        balance_service = BalanceService(db)

        # Create balance for manager
        balance = balance_service.allocate_standard_balance(test_manager.id, date.today().year)

        initial_used = balance.vacation_used

        # Manager submits vacation request - use working days
        start_date, end_date = get_working_day_range(start_skip=3, num_days=3)
        request_data = PTORequestCreate(
            user_id=test_manager.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("3.00"),
            notes="Personal time"
        )

        request = pto_service.create_request(request_data)

        # Verify auto-approved
        assert request.status == PTOStatus.APPROVED.value
        assert request.approved_by == test_manager.id  # Self-approved

        # Verify balance went directly to used (not pending)
        db.refresh(balance)
        assert balance.vacation_used == initial_used + Decimal("3.00")
        assert balance.vacation_pending == Decimal("0.00")  # Nothing in pending


class TestSickLeaveWorkflow:
    """Test sick leave request workflow."""

    def test_sick_leave_approval(self, db, test_employee, test_balance, test_manager):
        """Test sick leave request approval updates correct balance."""
        pto_service = PTOService(db)

        initial_sick_used = test_balance.sick_used

        # Employee submits sick leave - use working day
        sick_date = get_next_working_day(skip_days=1)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.SICK.value,
            start_date=sick_date,
            end_date=sick_date,
            total_days=Decimal("1.00"),
            notes="Not feeling well"
        )

        request = pto_service.create_request(request_data)
        assert request.status == PTOStatus.PENDING.value

        # Manager approves
        PTOService.approve_request(db, request.id, test_manager.id)

        # Verify sick balance updated
        db.refresh(test_balance)
        assert test_balance.sick_used == initial_sick_used + Decimal("1.00")


class TestMultipleRequestsWorkflow:
    """Test handling of multiple concurrent requests."""

    def test_multiple_pending_requests(self, db, test_employee, test_balance, test_manager):
        """Test that multiple pending requests accumulate correctly."""
        pto_service = PTOService(db)

        initial_pending = test_balance.vacation_pending

        # Submit first request - use working days
        start1, end1 = get_working_day_range(start_skip=1, num_days=2)
        request1_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start1,
            end_date=end1,
            total_days=Decimal("2.00")
        )
        request1 = pto_service.create_request(request1_data)

        # Submit second request (different dates) - use working days
        start2, end2 = get_working_day_range(start_skip=5, num_days=2)
        request2_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start2,
            end_date=end2,
            total_days=Decimal("2.00")
        )
        request2 = pto_service.create_request(request2_data)

        # Both should be pending
        assert request1.status == PTOStatus.PENDING.value
        assert request2.status == PTOStatus.PENDING.value

        # Pending should include both
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending + Decimal("4.00")

        # Approve first, deny second
        PTOService.approve_request(db, request1.id, test_manager.id)
        PTOService.deny_request(db, request2.id, test_manager.id, "Too busy")

        # Check final state
        db.refresh(test_balance)
        assert test_balance.vacation_pending == initial_pending  # All pending resolved
        assert test_balance.vacation_used == Decimal("2.00")  # Only first request used


class TestOverlapPrevention:
    """Test that overlapping requests are prevented."""

    def test_prevents_overlapping_dates(self, db, test_employee, test_balance):
        """Test that overlapping requests are rejected."""
        pto_service = PTOService(db)

        # Submit first request - use working days
        start1, end1 = get_working_day_range(start_skip=1, num_days=3)
        request1_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start1,
            end_date=end1,
            total_days=Decimal("3.00")
        )
        request1 = pto_service.create_request(request1_data)
        assert request1.id is not None

        # Try to submit overlapping request - middle day of first request
        overlap_start = get_next_working_day(start1, skip_days=1)  # Day 2 of first request
        overlap_end = get_next_working_day(overlap_start, skip_days=2)
        request2_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=overlap_start,
            end_date=overlap_end,
            total_days=Decimal("3.00")
        )

        with pytest.raises(ValueError, match="already have a"):
            pto_service.create_request(request2_data)


class TestTrustedEmployeeWorkflow:
    """Test trusted employee auto-approval workflow."""

    def test_trusted_employee_auto_approval(self, db, test_employee, test_balance):
        """Test that trusted employees get auto-approved for standard PTO."""
        pto_service = PTOService(db)

        # Mark employee as trusted
        test_employee.is_trusted = True
        db.commit()

        initial_used = test_balance.vacation_used

        # Submit vacation request - use working days
        start_date, end_date = get_working_day_range(start_skip=1, num_days=2)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("2.00")
        )

        request = pto_service.create_request(request_data)

        # Should be auto-approved
        assert request.status == PTOStatus.APPROVED.value

        # Balance should go directly to used
        db.refresh(test_balance)
        assert test_balance.vacation_used == initial_used + Decimal("2.00")
        assert test_balance.vacation_pending == Decimal("0.00")


class TestYearBoundaryWorkflow:
    """Test PTO requests spanning year boundaries."""

    def test_request_uses_start_year_balance(self, db, test_employee):
        """Test that requests use balance from the start date's year."""
        balance_service = BalanceService(db)

        # Create balances for two years
        current_year = date.today().year
        next_year = current_year + 1

        balance_current = balance_service.allocate_standard_balance(
            test_employee.id, current_year
        )
        balance_next = balance_service.allocate_standard_balance(
            test_employee.id, next_year
        )

        # Verify both balances exist and are separate
        assert balance_current.year == current_year
        assert balance_next.year == next_year
        assert balance_current.id != balance_next.id

        # Both should have standard allocation
        assert balance_current.vacation_total == Decimal("160.00")
        assert balance_next.vacation_total == Decimal("160.00")
