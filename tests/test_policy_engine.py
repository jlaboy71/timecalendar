"""
Tests for the PolicyEngine module.

Tests cover:
- Date validation (backdating, future limits)
- Auto-approve determination (roles, trust, backdating exception)
- Balance validation (hard cap vs soft cap)
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from src.services.policy_engine import (
    PolicyEngine,
    PolicyResult,
    AutoApproveResult,
    BalanceValidationResult,
    BACKDATE_WINDOW_DAYS,
    FUTURE_LIMIT_YEARS,
    TRUSTED_AUTO_APPROVE_TYPES,
    ALWAYS_REQUIRES_APPROVAL,
    HARD_CAP_TYPES,
    SOFT_CAP_TYPES,
)


class TestPolicyEngineConstants:
    """Test that policy constants are correctly defined."""

    def test_backdate_window_is_7_days(self):
        assert BACKDATE_WINDOW_DAYS == 7

    def test_future_limit_is_5_years(self):
        assert FUTURE_LIMIT_YEARS == 5

    def test_trusted_auto_approve_types(self):
        assert 'vacation' in TRUSTED_AUTO_APPROVE_TYPES
        assert 'sick' in TRUSTED_AUTO_APPROVE_TYPES
        assert 'personal' in TRUSTED_AUTO_APPROVE_TYPES
        assert 'bereavement' not in TRUSTED_AUTO_APPROVE_TYPES

    def test_always_requires_approval_types(self):
        assert 'bereavement' in ALWAYS_REQUIRES_APPROVAL
        assert 'fmla' in ALWAYS_REQUIRES_APPROVAL
        assert 'jury_duty' in ALWAYS_REQUIRES_APPROVAL
        assert 'vacation' not in ALWAYS_REQUIRES_APPROVAL

    def test_hard_cap_types(self):
        assert 'sick' in HARD_CAP_TYPES
        assert 'personal' in HARD_CAP_TYPES
        assert 'chicago_leave' in HARD_CAP_TYPES
        assert 'vacation' not in HARD_CAP_TYPES

    def test_soft_cap_types(self):
        assert 'vacation' in SOFT_CAP_TYPES
        assert 'sick' not in SOFT_CAP_TYPES


class TestValidateRequestDates:
    """Test date validation logic."""

    def setup_method(self):
        self.engine = PolicyEngine()
        self.today = date.today()

    def test_future_date_is_valid(self):
        """Future dates should be valid without requiring approval."""
        future_date = self.today + timedelta(days=10)
        result = self.engine.validate_request_dates(future_date, future_date, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is False
        assert result.is_backdated is False
        assert result.rejection_reason is None

    def test_today_is_valid(self):
        """Today's date should be valid."""
        result = self.engine.validate_request_dates(self.today, self.today, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is False
        assert result.is_backdated is False

    def test_backdated_within_7_days_requires_approval(self):
        """Dates within 7 days ago should be valid but require approval."""
        past_date = self.today - timedelta(days=5)
        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is True
        assert result.is_backdated is True
        assert len(result.warnings) > 0

    def test_backdated_beyond_7_days_is_rejected(self):
        """Dates more than 7 days ago should be rejected."""
        past_date = self.today - timedelta(days=10)
        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is False
        assert result.rejection_reason is not None
        assert '7' in result.rejection_reason or 'days' in result.rejection_reason.lower()

    def test_exactly_7_days_ago_requires_approval(self):
        """Exactly 7 days ago should be allowed with approval required."""
        past_date = self.today - timedelta(days=7)
        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is True
        assert result.is_backdated is True

    def test_8_days_ago_is_rejected(self):
        """8 days ago should be rejected."""
        past_date = self.today - timedelta(days=8)
        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is False

    def test_future_beyond_5_years_is_rejected(self):
        """Dates more than 5 years in the future should be rejected."""
        far_future = date(self.today.year + 6, 1, 1)
        result = self.engine.validate_request_dates(far_future, far_future, 'vacation')

        assert result.is_valid is False
        assert 'years' in result.rejection_reason.lower()

    def test_end_before_start_is_rejected(self):
        """End date before start date should be rejected."""
        start = self.today + timedelta(days=10)
        end = self.today + timedelta(days=5)
        result = self.engine.validate_request_dates(start, end, 'vacation')

        assert result.is_valid is False
        assert 'end date' in result.rejection_reason.lower() or 'before' in result.rejection_reason.lower()


class TestDetermineAutoApprove:
    """Test auto-approve determination logic."""

    def setup_method(self):
        self.engine = PolicyEngine()
        self.today = date.today()
        self.future_date = self.today + timedelta(days=10)
        self.past_date = self.today - timedelta(days=3)

    def _create_user(self, role='employee', is_trusted=False):
        """Create a mock user object."""
        user = MagicMock()
        user.role = role
        user.is_trusted = is_trusted
        return user

    def test_manager_auto_approves_vacation(self):
        """Managers should auto-approve their own vacation requests."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(user, 'vacation', self.future_date)

        assert result.auto_approve is True
        assert 'manager' in result.reason.lower()

    def test_admin_auto_approves_vacation(self):
        """Admins should auto-approve their own vacation requests."""
        user = self._create_user(role='admin')
        result = self.engine.determine_auto_approve(user, 'vacation', self.future_date)

        assert result.auto_approve is True
        assert 'admin' in result.reason.lower()

    def test_trusted_employee_auto_approves_vacation(self):
        """Trusted employees should auto-approve vacation requests."""
        user = self._create_user(role='employee', is_trusted=True)
        result = self.engine.determine_auto_approve(user, 'vacation', self.future_date)

        assert result.auto_approve is True
        assert 'trusted' in result.reason.lower()

    def test_regular_employee_does_not_auto_approve(self):
        """Regular employees should not auto-approve."""
        user = self._create_user(role='employee', is_trusted=False)
        result = self.engine.determine_auto_approve(user, 'vacation', self.future_date)

        assert result.auto_approve is False

    def test_manager_does_not_auto_approve_bereavement(self):
        """Managers should not auto-approve bereavement (always requires approval)."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(user, 'bereavement', self.future_date)

        assert result.auto_approve is False
        assert 'approval' in result.reason.lower()

    def test_backdated_request_does_not_auto_approve_for_manager(self):
        """CRITICAL: Backdated requests should NOT auto-approve, even for managers."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(user, 'vacation', self.past_date)

        assert result.auto_approve is False
        assert 'backdat' in result.reason.lower()

    def test_backdated_request_does_not_auto_approve_for_trusted(self):
        """CRITICAL: Backdated requests should NOT auto-approve, even for trusted employees."""
        user = self._create_user(role='employee', is_trusted=True)
        result = self.engine.determine_auto_approve(user, 'vacation', self.past_date)

        assert result.auto_approve is False
        assert 'backdat' in result.reason.lower()

    def test_vacation_rollover_does_not_auto_approve(self):
        """Vacation rollover should not auto-approve, even for managers."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(
            user, 'vacation', self.future_date, is_vacation_rollover=True
        )

        assert result.auto_approve is False
        assert 'rollover' in result.reason.lower()

    def test_manager_auto_approves_sick(self):
        """Managers should auto-approve their own sick time."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(user, 'sick', self.future_date)

        assert result.auto_approve is True

    def test_manager_auto_approves_personal(self):
        """Managers should auto-approve their own personal time."""
        user = self._create_user(role='manager')
        result = self.engine.determine_auto_approve(user, 'personal', self.future_date)

        assert result.auto_approve is True


class TestValidateBalance:
    """Test balance validation logic."""

    def setup_method(self):
        self.engine = PolicyEngine()

    def test_sufficient_vacation_is_valid(self):
        """Vacation request within balance should be valid."""
        result = self.engine.validate_balance('vacation', 16.0, 40.0)

        assert result.is_valid is True
        assert result.is_warning_only is False
        assert result.shortfall_hours == 0.0

    def test_vacation_overdraft_is_warning_only(self):
        """Vacation overdraft should show warning but allow submission."""
        result = self.engine.validate_balance('vacation', 48.0, 40.0)

        assert result.is_valid is True  # Still valid, just warning
        assert result.is_warning_only is True
        assert result.shortfall_hours == 8.0
        assert result.message is not None

    def test_sick_overdraft_is_blocked(self):
        """Sick overdraft should block submission (hard cap)."""
        result = self.engine.validate_balance('sick', 48.0, 40.0)

        assert result.is_valid is False  # Blocked
        assert result.is_warning_only is False
        assert result.shortfall_hours == 8.0

    def test_personal_overdraft_is_blocked(self):
        """Personal overdraft should block submission (hard cap)."""
        result = self.engine.validate_balance('personal', 24.0, 16.0)

        assert result.is_valid is False  # Blocked
        assert result.is_warning_only is False

    def test_chicago_leave_overdraft_is_blocked(self):
        """Chicago leave overdraft should block submission (hard cap)."""
        result = self.engine.validate_balance('chicago_leave', 48.0, 40.0)

        assert result.is_valid is False  # Blocked
        assert result.is_warning_only is False

    def test_sufficient_sick_is_valid(self):
        """Sick request within balance should be valid."""
        result = self.engine.validate_balance('sick', 8.0, 40.0)

        assert result.is_valid is True
        assert result.is_warning_only is False


class TestPolicyDocumentation:
    """Test that policy documentation is properly structured."""

    def setup_method(self):
        self.engine = PolicyEngine()

    def test_get_policy_documentation_returns_sections(self):
        """Policy documentation should return multiple sections."""
        sections = self.engine.get_policy_documentation()

        assert len(sections) == 8
        assert all(hasattr(s, 'id') for s in sections)
        assert all(hasattr(s, 'title') for s in sections)
        assert all(hasattr(s, 'icon') for s in sections)
        assert all(hasattr(s, 'content') for s in sections)

    def test_balance_formulas_section_exists(self):
        """Balance formulas section should exist."""
        sections = self.engine.get_policy_documentation()
        ids = [s.id for s in sections]

        assert 'balance_formulas' in ids

    def test_auto_approve_section_exists(self):
        """Auto-approve section should exist."""
        sections = self.engine.get_policy_documentation()
        ids = [s.id for s in sections]

        assert 'auto_approve' in ids

    def test_date_validation_section_exists(self):
        """Date validation section should exist."""
        sections = self.engine.get_policy_documentation()
        ids = [s.id for s in sections]

        assert 'date_validation' in ids


class TestCalendarAndRequestFormConsistency:
    """Test that Calendar UI and Request Form produce identical validation results."""

    def setup_method(self):
        self.engine = PolicyEngine()
        self.today = date.today()

    def test_both_reject_dates_beyond_7_days(self):
        """Both should reject dates more than 7 days ago."""
        past_date = self.today - timedelta(days=10)

        # Same validation call used by both Calendar and Request Form
        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is False

    def test_both_allow_dates_within_7_days(self):
        """Both should allow dates within 7 days (with approval required)."""
        past_date = self.today - timedelta(days=5)

        result = self.engine.validate_request_dates(past_date, past_date, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is True

    def test_both_allow_future_dates(self):
        """Both should allow future dates without special approval."""
        future_date = self.today + timedelta(days=10)

        result = self.engine.validate_request_dates(future_date, future_date, 'vacation')

        assert result.is_valid is True
        assert result.requires_manager_approval is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
