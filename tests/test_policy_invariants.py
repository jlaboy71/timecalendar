"""
Policy Invariant Tests for PTO Central

These tests ensure policy parity across all surfaces (UI, API, service layer).
Any test failure indicates a policy violation that must be fixed before MCP/RAG activation.

Reference: task/MCPRAGv2.md
"""
import pytest
import os
import re
from decimal import Decimal
from datetime import date, timedelta

from src.services.policy_engine import (
    PolicyEngine,
    HARD_CAP_TYPES,
    SOFT_CAP_TYPES,
    TRUSTED_AUTO_APPROVE_TYPES,
    ALWAYS_REQUIRES_APPROVAL,
    BACKDATE_WINDOW_DAYS,
    FUTURE_LIMIT_YEARS,
)
from src.utils.working_days import count_working_days, is_working_day, get_holidays_in_range


class TestNoDuplicateDayCounting:
    """Ensure only one day-counting implementation exists."""

    def test_no_count_business_days_in_ui(self):
        """UI pages must not define their own day-counting functions."""
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'nicegui_app', 'pages')

        # Pattern to match function definitions that count days
        duplicate_patterns = [
            r'def count_business_days\s*\(',
            r'def calculate_working_days\s*\(',
            r'def count_days\s*\(',
        ]

        violations = []

        for filename in os.listdir(ui_path):
            if filename.endswith('.py'):
                filepath = os.path.join(ui_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in duplicate_patterns:
                        if re.search(pattern, content):
                            violations.append(f"{filename}: contains duplicate day-counting function")

        assert not violations, f"Policy parity violation - duplicate implementations found:\n" + "\n".join(violations)

    def test_ui_imports_centralized_function(self):
        """request_form.py must import count_working_days from src/utils."""
        request_form_path = os.path.join(
            os.path.dirname(__file__), '..', 'nicegui_app', 'pages', 'request_form.py'
        )

        with open(request_form_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'from src.utils.working_days import' in content, \
            "request_form.py must import from src.utils.working_days"
        assert 'count_working_days' in content, \
            "request_form.py must import count_working_days"


class TestHardCapTypesParity:
    """Ensure hard cap types are consistent across all surfaces."""

    def test_hard_cap_types_defined_in_policy_engine(self):
        """Hard cap types must be defined in PolicyEngine."""
        assert HARD_CAP_TYPES is not None
        assert len(HARD_CAP_TYPES) > 0
        assert 'sick' in HARD_CAP_TYPES
        assert 'personal' in HARD_CAP_TYPES
        assert 'chicago_leave' in HARD_CAP_TYPES

    def test_vacation_is_soft_cap(self):
        """Vacation must be a soft cap type (warning only, not blocked)."""
        assert 'vacation' in SOFT_CAP_TYPES
        assert 'vacation' not in HARD_CAP_TYPES

    def test_no_hardcoded_hard_cap_lists_in_ui(self):
        """UI pages must not hardcode their own hard cap type lists."""
        request_form_path = os.path.join(
            os.path.dirname(__file__), '..', 'nicegui_app', 'pages', 'request_form.py'
        )

        with open(request_form_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for hardcoded lists (these patterns should NOT be found)
        hardcoded_patterns = [
            r"hard_cap_types\s*=\s*\[",  # hard_cap_types = [...]
            r"\['chicago_leave',\s*'sick',\s*'personal'\]",  # The old hardcoded list
        ]

        for pattern in hardcoded_patterns:
            match = re.search(pattern, content)
            assert match is None, \
                f"Policy parity violation: request_form.py contains hardcoded list matching '{pattern}'"

    def test_ui_uses_policy_engine_constant(self):
        """request_form.py must import HARD_CAP_TYPES from PolicyEngine."""
        request_form_path = os.path.join(
            os.path.dirname(__file__), '..', 'nicegui_app', 'pages', 'request_form.py'
        )

        with open(request_form_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'from src.services.policy_engine import' in content, \
            "request_form.py must import from policy_engine"
        assert 'HARD_CAP_TYPES' in content, \
            "request_form.py must use HARD_CAP_TYPES from policy_engine"


class TestBalanceFormulas:
    """Verify balance formula calculations are correct."""

    def test_vacation_available_formula(self):
        """Vacation available = total + carryover - used - pending."""
        from src.models.pto_balance import PTOBalance

        balance = PTOBalance(
            user_id=1,
            year=2025,
            vacation_total=Decimal('80.00'),
            vacation_carryover=Decimal('16.00'),
            vacation_used=Decimal('24.00'),
            vacation_pending=Decimal('8.00'),
        )

        expected = Decimal('80.00') + Decimal('16.00') - Decimal('24.00') - Decimal('8.00')
        assert balance.vacation_available == expected

    def test_sick_available_formula(self):
        """Sick available = total + carryover - used - pending."""
        from src.models.pto_balance import PTOBalance

        balance = PTOBalance(
            user_id=1,
            year=2025,
            sick_total=Decimal('40.00'),
            sick_carryover=Decimal('8.00'),
            sick_used=Decimal('16.00'),
            sick_pending=Decimal('0.00'),
        )

        expected = Decimal('40.00') + Decimal('8.00') - Decimal('16.00') - Decimal('0.00')
        assert balance.sick_available == expected

    def test_chicago_leave_available_formula(self):
        """Chicago Leave available = total + carryover - used - pending."""
        from src.models.pto_balance import PTOBalance

        balance = PTOBalance(
            user_id=1,
            year=2025,
            chicago_paid_leave_total=Decimal('40.00'),
            chicago_paid_leave_carryover=Decimal('16.00'),
            chicago_paid_leave_used=Decimal('8.00'),
            chicago_paid_leave_pending=Decimal('0.00'),
        )

        expected = Decimal('40.00') + Decimal('16.00') - Decimal('8.00') - Decimal('0.00')
        assert balance.chicago_paid_leave_available == expected


class TestWorkingDaysCalculation:
    """Verify working days calculation excludes weekends and holidays."""

    def test_single_weekday_is_one_day(self):
        """A single weekday should count as 1 working day."""
        # Find a Monday
        today = date.today()
        monday = today + timedelta(days=(7 - today.weekday()) % 7)
        if monday.weekday() != 0:
            monday = today - timedelta(days=today.weekday())

        result = count_working_days(monday, monday)
        assert result == 1

    def test_weekend_is_zero_days(self):
        """A weekend day should count as 0 working days."""
        # Find a Saturday
        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)

        result = count_working_days(saturday, saturday)
        assert result == 0

    def test_full_week_is_five_days_minus_holidays(self):
        """Monday to Friday should count as 5 working days minus any holidays."""
        # Find next Monday
        today = date.today()
        monday = today + timedelta(days=(7 - today.weekday()) % 7)
        friday = monday + timedelta(days=4)

        # Get holidays in range to determine expected count
        holidays = get_holidays_in_range(monday, friday)
        expected = 5 - len(holidays)

        result = count_working_days(monday, friday)
        assert result == expected, \
            f"Expected {expected} working days (5 weekdays - {len(holidays)} holidays)"

    def test_invalid_range_is_zero(self):
        """End date before start date should return 0."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        result = count_working_days(today, yesterday)
        assert result == 0


class TestAutoApproveRules:
    """Verify auto-approve rules are consistent."""

    def test_trusted_types_are_subset_of_valid_types(self):
        """Trusted auto-approve types must be valid PTO types."""
        valid_types = {'vacation', 'sick', 'personal', 'bereavement', 'fmla',
                      'jury_duty', 'voting', 'military', 'wfh', 'chicago_leave'}

        for t in TRUSTED_AUTO_APPROVE_TYPES:
            assert t in valid_types, f"{t} is not a valid PTO type"

    def test_always_requires_approval_types(self):
        """Certain types must always require approval."""
        assert 'bereavement' in ALWAYS_REQUIRES_APPROVAL
        assert 'fmla' in ALWAYS_REQUIRES_APPROVAL
        assert 'jury_duty' in ALWAYS_REQUIRES_APPROVAL

    def test_no_overlap_between_auto_and_always_require(self):
        """A type cannot be in both auto-approve and always-requires-approval."""
        overlap = TRUSTED_AUTO_APPROVE_TYPES & ALWAYS_REQUIRES_APPROVAL
        assert len(overlap) == 0, f"Types in both sets: {overlap}"


class TestDateValidationRules:
    """Verify date validation rules are consistent."""

    def test_backdate_window_is_seven_days(self):
        """Backdate window must be 7 calendar days."""
        assert BACKDATE_WINDOW_DAYS == 7

    def test_future_limit_is_five_years(self):
        """Future request limit must be 5 years."""
        assert FUTURE_LIMIT_YEARS == 5

    def test_policy_engine_validates_backdated_requests(self):
        """PolicyEngine must correctly identify backdated requests."""
        engine = PolicyEngine()
        today = date.today()
        yesterday = today - timedelta(days=1)

        result = engine.validate_request_dates(yesterday, yesterday, 'vacation')

        assert result.is_valid is True
        assert result.is_backdated is True
        assert result.requires_manager_approval is True

    def test_policy_engine_rejects_beyond_backdate_window(self):
        """PolicyEngine must reject requests beyond 7 days in the past."""
        engine = PolicyEngine()
        today = date.today()
        eight_days_ago = today - timedelta(days=8)

        result = engine.validate_request_dates(eight_days_ago, eight_days_ago, 'vacation')

        assert result.is_valid is False
        assert result.is_backdated is True


class TestPolicyEngineParity:
    """Ensure PolicyEngine is the single source of truth."""

    def test_pto_service_constants_match_policy_engine(self):
        """pto_service.py constants should match PolicyEngine."""
        from src.services.pto_service import TRUSTED_AUTO_APPROVE_TYPES as PTO_TRUSTED
        from src.services.pto_service import ALWAYS_REQUIRES_APPROVAL as PTO_REQUIRES

        # These should be identical sets
        assert PTO_TRUSTED == TRUSTED_AUTO_APPROVE_TYPES, \
            "pto_service.py TRUSTED_AUTO_APPROVE_TYPES doesn't match PolicyEngine"
        assert PTO_REQUIRES == ALWAYS_REQUIRES_APPROVAL, \
            "pto_service.py ALWAYS_REQUIRES_APPROVAL doesn't match PolicyEngine"
