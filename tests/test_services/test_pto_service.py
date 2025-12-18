"""
Unit tests for the PTOService.
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.schemas.pto_schemas import PTORequestCreate
from src.models.pto_request import PTORequest
from src.models.pto_balance import PTOBalance
from src.constants import PTOStatus, PTOType
from tests.utils import get_next_working_day, get_working_day_range


class TestCreateRequest:
    """Tests for create_request method."""

    def test_creates_pending_request_for_employee(self, db, test_employee, test_balance):
        """Test that regular employee request is created as pending."""
        service = PTOService(db)

        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00"),
            notes="Test vacation"
        )

        request = service.create_request(request_data)

        assert request.id is not None
        assert request.status == PTOStatus.PENDING.value
        assert request.user_id == test_employee.id
        assert request.total_days == Decimal("2.00")
        assert request.approved_by is None

    def test_auto_approves_manager_vacation(self, db, test_manager):
        """Test that manager vacation request is auto-approved."""
        service = PTOService(db)
        balance_service = BalanceService(db)

        # Create balance for manager
        balance_service.get_or_create_balance(test_manager.id, date.today().year)
        balance_service.allocate_standard_balance(test_manager.id, date.today().year)

        request_data = PTORequestCreate(
            user_id=test_manager.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00")
        )

        request = service.create_request(request_data)

        assert request.status == PTOStatus.APPROVED.value
        assert request.approved_by == test_manager.id

    def test_auto_approves_admin_vacation(self, db, test_admin):
        """Test that admin vacation request is auto-approved."""
        service = PTOService(db)
        balance_service = BalanceService(db)

        # Create balance for admin
        balance_service.allocate_standard_balance(test_admin.id, date.today().year)

        request_data = PTORequestCreate(
            user_id=test_admin.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00")
        )

        request = service.create_request(request_data)

        assert request.status == PTOStatus.APPROVED.value

    def test_rejects_past_start_date(self, db, test_employee, test_balance):
        """Test that start date in the past is rejected."""
        service = PTOService(db)

        # Dates within 7 days in the past are now allowed (retroactive submissions)
        # Test that dates MORE than 7 days in the past are rejected
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=9),
            total_days=Decimal("1.00")
        )

        with pytest.raises(ValueError, match="Start date cannot be more than 7 days in the past"):
            service.create_request(request_data)

    def test_rejects_end_before_start(self, db, test_employee, test_balance):
        """Test that end date before start date is rejected by schema validation."""
        # Pydantic schema validates end_date >= start_date
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="End date must be after or equal to start date"):
            PTORequestCreate(
                user_id=test_employee.id,
                pto_type=PTOType.VACATION.value,
                start_date=date.today() + timedelta(days=10),
                end_date=date.today() + timedelta(days=5),
                total_days=Decimal("1.00")
            )

    def test_rejects_nonexistent_user(self, db):
        """Test that request for non-existent user is rejected."""
        service = PTOService(db)

        request_data = PTORequestCreate(
            user_id=99999,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00")
        )

        with pytest.raises(ValueError, match="User with ID 99999 not found"):
            service.create_request(request_data)

    def test_rejects_far_future_request(self, db, test_employee, test_balance):
        """Test that requests more than 5 years ahead are rejected."""
        service = PTOService(db)

        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=365 * 6),
            end_date=date.today() + timedelta(days=365 * 6 + 1),
            total_days=Decimal("1.00")
        )

        with pytest.raises(ValueError, match="more than 5 years in advance"):
            service.create_request(request_data)

    def test_adds_to_vacation_pending_for_employee(self, db, test_employee, test_balance):
        """Test that employee request adds to vacation pending."""
        service = PTOService(db)
        original_pending = test_balance.vacation_pending

        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00")
        )

        service.create_request(request_data)
        db.refresh(test_balance)

        assert test_balance.vacation_pending == original_pending + Decimal("2.00")

    def test_allows_vacation_request_exceeding_balance(self, db, test_employee, test_balance):
        """
        Test that vacation requests exceeding balance are ALLOWED to be submitted.

        Per business rules (pto_service.py:109-111):
        "Vacation balance validation is NOT a hard block per business rules.
        Employees can submit requests exceeding available balance - manager decides whether to approve."

        Only sick and personal days have hard limits enforced.
        """
        service = PTOService(db)

        # Request more days than available (balance has 80 hours = 10 days)
        # Use working days to avoid weekend validation errors
        start_date, end_date = get_working_day_range(start_skip=1, num_days=15)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("15.00")  # More than 10 days available
        )

        # Should NOT raise - vacation requests are not hard-blocked
        request = service.create_request(request_data)
        assert request is not None
        assert request.status == 'pending'  # Goes to pending for manager review


class TestGetRequestById:
    """Tests for get_request_by_id method."""

    def test_returns_request_by_id(self, db, test_pto_request):
        """Test retrieving request by ID."""
        service = PTOService(db)
        request = service.get_request_by_id(test_pto_request.id)

        assert request is not None
        assert request.id == test_pto_request.id

    def test_returns_none_for_invalid_id(self, db):
        """Test returning None for non-existent ID."""
        service = PTOService(db)
        request = service.get_request_by_id(99999)

        assert request is None


class TestGetUserRequests:
    """Tests for get_user_requests static method."""

    def test_returns_all_user_requests(self, db, test_employee, test_pto_request):
        """Test getting all requests for a user."""
        # Create another request
        another_request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.SICK.value,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
            total_days=Decimal("1.00"),
            status=PTOStatus.PENDING.value
        )
        db.add(another_request)
        db.commit()

        # Use static method signature
        requests = PTOService.get_user_requests(db, test_employee.id)

        assert len(requests) >= 2

    def test_returns_requests_ordered_by_date(self, db, test_employee, test_pto_request):
        """Test requests are returned ordered by submitted_at descending."""
        # Create another request
        another_request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.SICK.value,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=30),
            total_days=Decimal("1.00"),
            status=PTOStatus.PENDING.value
        )
        db.add(another_request)
        db.commit()

        requests = PTOService.get_user_requests(db, test_employee.id)

        # Should be ordered by submitted_at descending
        if len(requests) > 1:
            for i in range(len(requests) - 1):
                assert requests[i].submitted_at >= requests[i + 1].submitted_at


class TestGetPendingRequests:
    """Tests for get_pending_requests method."""

    def test_returns_pending_requests(self, db, test_pto_request):
        """Test getting all pending requests."""
        service = PTOService(db)
        pending = service.get_pending_requests()

        assert len(pending) >= 1
        assert all(r.status == PTOStatus.PENDING.value for r in pending)

    def test_excludes_non_pending(self, db, test_employee):
        """Test that non-pending requests are excluded."""
        service = PTOService(db)

        # Create an approved request
        approved_request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=31),
            total_days=Decimal("2.00"),
            status=PTOStatus.APPROVED.value
        )
        db.add(approved_request)
        db.commit()

        pending = service.get_pending_requests()

        # Approved request should not be in pending list
        approved_ids = [r.id for r in pending]
        assert approved_request.id not in approved_ids


class TestApproveRequest:
    """Tests for approve_request static method."""

    def test_approves_pending_request(self, db, test_pto_request, test_manager, test_balance):
        """Test approving a pending request."""
        # Test_manager is in same department as test_employee
        result = PTOService.approve_request(db, test_pto_request.id, test_manager.id)

        assert result.status == PTOStatus.APPROVED.value
        assert result.approved_by == test_manager.id
        assert result.approved_at is not None

    def test_moves_pending_to_used_on_approval(self, db, test_employee, test_balance, test_manager):
        """Test that approving moves vacation from pending to used."""
        # Create a pending vacation request
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00"),
            status=PTOStatus.PENDING.value
        )
        db.add(request)

        # Add to pending balance
        test_balance.vacation_pending = Decimal("2.00")
        db.commit()
        db.refresh(request)

        original_used = test_balance.vacation_used

        PTOService.approve_request(db, request.id, test_manager.id)
        db.refresh(test_balance)

        # Pending should decrease, used should increase
        assert test_balance.vacation_pending == Decimal("0.00")
        assert test_balance.vacation_used == original_used + Decimal("2.00")

    def test_rejects_non_pending_approval(self, db, test_pto_request, test_manager):
        """Test that only pending requests can be approved."""
        test_pto_request.status = PTOStatus.APPROVED.value
        db.commit()

        with pytest.raises(ValueError, match="Only pending requests can be approved"):
            PTOService.approve_request(db, test_pto_request.id, test_manager.id)

    def test_rejects_nonexistent_request(self, db, test_manager):
        """Test approving non-existent request raises error."""
        with pytest.raises(ValueError, match="Request with ID 99999 not found"):
            PTOService.approve_request(db, 99999, test_manager.id)

    def test_admin_can_approve_any_request(self, db, test_pto_request, test_admin, test_balance):
        """Test that admin can approve requests from any department."""
        result = PTOService.approve_request(db, test_pto_request.id, test_admin.id)

        assert result.status == PTOStatus.APPROVED.value

    def test_employee_cannot_approve(self, db, test_pto_request, test_balance):
        """Test that regular employee cannot approve requests."""
        # Create another employee
        from src.models.user import User
        from src.utils.password import hash_password

        other_employee = User(
            username="other_employee",
            email="other@test.com",
            first_name="Other",
            last_name="Employee",
            role="employee",
            department_id=test_pto_request.user.department_id,
            hire_date=date(2020, 1, 1),
            is_active=True,
            password_hash=hash_password("testpass123")
        )
        db.add(other_employee)
        db.commit()

        with pytest.raises(ValueError, match="not authorized"):
            PTOService.approve_request(db, test_pto_request.id, other_employee.id)


class TestDenyRequest:
    """Tests for deny_request static method."""

    def test_denies_pending_request(self, db, test_pto_request, test_manager):
        """Test denying a pending request."""
        result = PTOService.deny_request(
            db,
            test_pto_request.id,
            test_manager.id,
            "Coverage needed"
        )

        assert result.status == PTOStatus.DENIED.value
        assert result.denial_reason == "Coverage needed"
        assert result.approved_by == test_manager.id

    def test_removes_pending_on_denial(self, db, test_employee, test_balance, test_manager):
        """Test that denying removes vacation from pending."""
        # Create a pending vacation request
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00"),
            status=PTOStatus.PENDING.value
        )
        db.add(request)

        # Add to pending balance
        test_balance.vacation_pending = Decimal("2.00")
        db.commit()
        db.refresh(request)

        PTOService.deny_request(db, request.id, test_manager.id, "Denied")
        db.refresh(test_balance)

        # Pending should be removed
        assert test_balance.vacation_pending == Decimal("0.00")

    def test_rejects_non_pending_denial(self, db, test_pto_request, test_manager):
        """Test that only pending requests can be denied."""
        test_pto_request.status = PTOStatus.APPROVED.value
        db.commit()

        with pytest.raises(ValueError, match="Only pending requests can be denied"):
            PTOService.deny_request(db, test_pto_request.id, test_manager.id, "reason")


class TestCancelRequest:
    """Tests for cancel_request method."""

    def test_cancels_own_pending_request(self, db, test_employee, test_pto_request):
        """Test that user can cancel their own pending request."""
        service = PTOService(db)
        result = service.cancel_request(test_pto_request.id, test_employee.id)

        assert result.status == PTOStatus.CANCELLED.value

    def test_cannot_cancel_others_request(self, db, test_pto_request, test_manager):
        """Test that user cannot cancel another user's request."""
        service = PTOService(db)

        with pytest.raises(ValueError, match="only cancel your own requests"):
            service.cancel_request(test_pto_request.id, test_manager.id)

    def test_cannot_cancel_non_pending(self, db, test_employee, test_pto_request):
        """Test that only pending requests can be cancelled."""
        service = PTOService(db)
        test_pto_request.status = PTOStatus.APPROVED.value
        db.commit()

        with pytest.raises(ValueError, match="Only pending requests can be cancelled"):
            service.cancel_request(test_pto_request.id, test_employee.id)

    def test_removes_pending_on_cancel(self, db, test_employee, test_balance):
        """Test that cancelling removes vacation from pending."""
        service = PTOService(db)

        # Create a pending vacation request
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            total_days=Decimal("2.00"),
            status=PTOStatus.PENDING.value
        )
        db.add(request)

        # Add to pending balance
        test_balance.vacation_pending = Decimal("2.00")
        db.commit()
        db.refresh(request)

        service.cancel_request(request.id, test_employee.id)
        db.refresh(test_balance)

        assert test_balance.vacation_pending == Decimal("0.00")


class TestGetOverlappingRequests:
    """Tests for get_overlapping_requests method."""

    def test_finds_overlapping_requests(self, db, test_employee, test_pto_request):
        """Test finding overlapping requests."""
        service = PTOService(db)

        # test_pto_request is for today, so check overlap with today
        overlapping = service.get_overlapping_requests(
            test_employee.id,
            date.today(),
            date.today()
        )

        assert len(overlapping) >= 1
        assert test_pto_request.id in [r.id for r in overlapping]

    def test_no_overlap_for_different_dates(self, db, test_employee, test_pto_request):
        """Test no overlap for non-overlapping dates."""
        service = PTOService(db)

        # Check far in the future (test_pto_request is for today)
        overlapping = service.get_overlapping_requests(
            test_employee.id,
            date.today() + timedelta(days=365),
            date.today() + timedelta(days=370)
        )

        assert len(overlapping) == 0

    def test_excludes_specified_request(self, db, test_employee, test_pto_request):
        """Test that excluded request ID is not in results."""
        service = PTOService(db)

        overlapping = service.get_overlapping_requests(
            test_employee.id,
            date.today(),
            date.today(),
            exclude_request_id=test_pto_request.id
        )

        assert test_pto_request.id not in [r.id for r in overlapping]


class TestTrustedEmployeeAutoApprove:
    """Tests for trusted employee auto-approve functionality."""

    def test_trusted_employee_vacation_auto_approved(self, db, test_employee, test_balance):
        """Test that trusted employee vacation is auto-approved."""
        service = PTOService(db)

        # Mark employee as trusted
        test_employee.is_trusted = True
        db.commit()

        # Use working days to avoid weekend validation errors
        start_date, end_date = get_working_day_range(start_skip=3, num_days=2)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("2.00")
        )

        request = service.create_request(request_data)

        assert request.status == PTOStatus.APPROVED.value

    def test_trusted_employee_bereavement_not_auto_approved(self, db, test_employee, test_balance):
        """Test that trusted employee special leave still requires approval."""
        service = PTOService(db)

        # Mark employee as trusted
        test_employee.is_trusted = True
        db.commit()

        # Use working days to avoid weekend validation errors
        start_date, end_date = get_working_day_range(start_skip=3, num_days=3)
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.BEREAVEMENT.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("3.00")
        )

        request = service.create_request(request_data)

        # Bereavement always requires approval
        assert request.status == PTOStatus.PENDING.value


class TestWeekendHolidayValidation:
    """Tests for server-side weekend and holiday validation."""

    def test_rejects_weekend_start_date(self, db, test_employee, test_balance):
        """Test that weekend start dates are rejected."""
        service = PTOService(db)

        # Find a Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        saturday = today + timedelta(days=days_until_saturday)

        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=saturday,
            end_date=saturday,
            total_days=Decimal("1.00")
        )

        with pytest.raises(ValueError) as excinfo:
            service.create_request(request_data)

        assert "Saturday" in str(excinfo.value) or "weekend" in str(excinfo.value).lower()

    def test_rejects_weekend_end_date(self, db, test_employee, test_balance):
        """Test that weekend end dates are rejected."""
        service = PTOService(db)

        # Find a Friday and following Sunday
        today = date.today()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        friday = today + timedelta(days=days_until_friday)
        sunday = friday + timedelta(days=2)

        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=friday,
            end_date=sunday,
            total_days=Decimal("1.00")
        )

        with pytest.raises(ValueError) as excinfo:
            service.create_request(request_data)

        assert "Sunday" in str(excinfo.value) or "weekend" in str(excinfo.value).lower()

    def test_server_recalculates_total_days(self, db, test_employee, test_balance):
        """Test that server recalculates total_days and overrides client value."""
        service = PTOService(db)

        # Use a 5-day working week (Mon-Fri)
        start_date, end_date = get_working_day_range(start_skip=1, num_days=5)

        # Client sends wrong total_days
        request_data = PTORequestCreate(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal("10.00")  # Wrong - should be 5
        )

        request = service.create_request(request_data)

        # Server should have recalculated to 5 days
        assert request.total_days == Decimal("5.00")
