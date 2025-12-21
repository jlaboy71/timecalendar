"""
Unit tests for the PTORequest model.
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from src.models.pto_request import PTORequest
from src.constants import PTOStatus, PTOType


class TestPTORequestCreation:
    """Tests for basic PTORequest creation."""

    def test_pto_request_creation(self, db, test_employee):
        """Test creating a basic PTO request."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=10),
            total_days=Decimal("4.00"),
            notes="Vacation trip"
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        assert request.id is not None
        assert request.user_id == test_employee.id
        assert request.pto_type == "vacation"
        assert request.total_days == Decimal("4.00")
        assert request.notes == "Vacation trip"

    def test_pto_request_default_status(self, db, test_employee):
        """Test that default status is 'pending'."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.SICK.value,
            start_date=date.today(),
            end_date=date.today(),
            total_days=Decimal("1.00")
        )
        db.add(request)
        db.commit()

        assert request.status == PTOStatus.PENDING.value


class TestPTORequestStatusProperties:
    """Tests for status-related properties."""

    def test_is_pending_property(self, test_pto_request):
        """Test is_pending property returns True for pending requests."""
        assert test_pto_request.is_pending is True
        assert test_pto_request.is_approved is False
        assert test_pto_request.is_denied is False

    def test_is_approved_property(self, db, test_pto_request):
        """Test is_approved property returns True for approved requests."""
        test_pto_request.status = PTOStatus.APPROVED.value
        db.commit()

        assert test_pto_request.is_approved is True
        assert test_pto_request.is_pending is False
        assert test_pto_request.is_denied is False

    def test_is_denied_property(self, db, test_pto_request):
        """Test is_denied property returns True for denied requests."""
        test_pto_request.status = PTOStatus.DENIED.value
        db.commit()

        assert test_pto_request.is_denied is True
        assert test_pto_request.is_pending is False
        assert test_pto_request.is_approved is False


class TestPTORequestDurationProperty:
    """Tests for the duration_days property."""

    def test_duration_days_single_day(self, db, test_employee):
        """Test duration for single day request."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.PERSONAL.value,
            start_date=date(2025, 3, 15),
            end_date=date(2025, 3, 15),
            total_days=Decimal("1.00")
        )
        db.add(request)
        db.commit()

        assert request.duration_days == 1

    def test_duration_days_multi_day(self, db, test_employee):
        """Test duration for multi-day request."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date(2025, 3, 10),
            end_date=date(2025, 3, 14),
            total_days=Decimal("5.00")
        )
        db.add(request)
        db.commit()

        # 5 calendar days (10, 11, 12, 13, 14)
        assert request.duration_days == 5

    def test_duration_days_week(self, db, test_employee):
        """Test duration for a week-long request."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.VACATION.value,
            start_date=date(2025, 3, 3),
            end_date=date(2025, 3, 9),
            total_days=Decimal("5.00")  # 5 business days, 7 calendar days
        )
        db.add(request)
        db.commit()

        # 7 calendar days
        assert request.duration_days == 7


class TestPTORequestPrivacyFlag:
    """Tests for the privacy flag."""

    def test_is_private_default(self, test_pto_request):
        """Test that is_private defaults to False."""
        assert test_pto_request.is_private is False

    def test_is_private_can_be_set(self, db, test_employee):
        """Test that is_private can be set to True."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.SICK.value,
            start_date=date.today(),
            end_date=date.today(),
            total_days=Decimal("1.00"),
            is_private=True
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        assert request.is_private is True


class TestPTORequestCancellationFields:
    """Tests for cancellation tracking fields."""

    def test_cancellation_defaults(self, test_pto_request):
        """Test that cancellation fields default to empty/None."""
        assert test_pto_request.cancellation_requested is False
        assert test_pto_request.cancellation_reason is None
        assert test_pto_request.cancellation_requested_at is None

    def test_cancellation_can_be_requested(self, db, test_pto_request):
        """Test that cancellation can be requested."""
        now = datetime.now()
        test_pto_request.cancellation_requested = True
        test_pto_request.cancellation_reason = "Plans changed"
        test_pto_request.cancellation_requested_at = now
        db.commit()
        db.refresh(test_pto_request)

        assert test_pto_request.cancellation_requested is True
        assert test_pto_request.cancellation_reason == "Plans changed"
        assert test_pto_request.cancellation_requested_at is not None


class TestPTORequestApproval:
    """Tests for approval-related fields."""

    def test_approval_fields_default_to_none(self, test_pto_request):
        """Test that approval fields are None for new requests."""
        assert test_pto_request.approved_by is None
        assert test_pto_request.approved_at is None
        assert test_pto_request.denial_reason is None

    def test_request_can_be_approved(self, db, test_pto_request, test_manager):
        """Test approving a request sets appropriate fields."""
        test_pto_request.status = PTOStatus.APPROVED.value
        test_pto_request.approved_by = test_manager.id
        test_pto_request.approved_at = datetime.now()
        db.commit()
        db.refresh(test_pto_request)

        assert test_pto_request.status == "approved"
        assert test_pto_request.approved_by == test_manager.id
        assert test_pto_request.approved_at is not None

    def test_request_can_be_denied(self, db, test_pto_request, test_manager):
        """Test denying a request sets appropriate fields."""
        test_pto_request.status = PTOStatus.DENIED.value
        test_pto_request.approved_by = test_manager.id
        test_pto_request.approved_at = datetime.now()
        test_pto_request.denial_reason = "Coverage needed during this period"
        db.commit()
        db.refresh(test_pto_request)

        assert test_pto_request.status == "denied"
        assert test_pto_request.denial_reason == "Coverage needed during this period"


class TestPTORequestTypes:
    """Tests for different PTO types."""

    @pytest.mark.parametrize("pto_type", [
        PTOType.VACATION,
        PTOType.SICK,
        PTOType.PERSONAL,
        PTOType.BEREAVEMENT,
        PTOType.FMLA,
        PTOType.JURY_DUTY,
        PTOType.VOTING,
        PTOType.MILITARY,
    ])
    def test_all_pto_types_can_be_created(self, db, test_employee, pto_type):
        """Test that all PTO types can be used."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=pto_type.value,
            start_date=date.today(),
            end_date=date.today(),
            total_days=Decimal("1.00")
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        assert request.pto_type == pto_type.value


class TestPTORequestRelationships:
    """Tests for PTO request relationships."""

    def test_request_belongs_to_user(self, test_pto_request, test_employee):
        """Test that request has user relationship."""
        assert test_pto_request.user_id == test_employee.id
        assert test_pto_request.user is not None
        assert test_pto_request.user.username == test_employee.username

    def test_request_has_approver_relationship(self, db, test_pto_request, test_manager):
        """Test that approved request has approver relationship."""
        test_pto_request.status = PTOStatus.APPROVED.value
        test_pto_request.approved_by = test_manager.id
        test_pto_request.approved_at = datetime.now()
        db.commit()
        db.refresh(test_pto_request)

        assert test_pto_request.approver is not None
        assert test_pto_request.approver.username == test_manager.username


class TestPTORequestIsPaid:
    """Tests for the is_paid field."""

    def test_is_paid_default(self, test_pto_request):
        """Test that is_paid defaults to True."""
        assert test_pto_request.is_paid is True

    def test_unpaid_leave_can_be_created(self, db, test_employee):
        """Test creating unpaid leave request."""
        request = PTORequest(
            user_id=test_employee.id,
            pto_type=PTOType.FMLA.value,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_days=Decimal("22.00"),
            is_paid=False
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        assert request.is_paid is False
