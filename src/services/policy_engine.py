"""
Centralized policy engine for PTO request validation and auto-approval decisions.

All UI and API validations MUST call this engine rather than implementing their own rules.
This is the single source of truth for policy constants and validation logic.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.user import User


# =============================================================================
# POLICY CONSTANTS - Single Source of Truth
# =============================================================================

# Date validation
BACKDATE_WINDOW_DAYS = 7  # Calendar days, not business days
FUTURE_LIMIT_YEARS = 5
TIMEZONE = 'America/Chicago'

# Auto-approval types
TRUSTED_AUTO_APPROVE_TYPES = frozenset({'vacation', 'sick', 'personal'})
ALWAYS_REQUIRES_APPROVAL = frozenset({'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh', 'chicago_leave'})

# Balance validation - hard cap vs soft cap (warning only)
HARD_CAP_TYPES = frozenset({'sick', 'personal', 'chicago_leave'})
SOFT_CAP_TYPES = frozenset({'vacation'})  # Warning only, negative allowed


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class PolicyResult:
    """Result of date validation."""
    is_valid: bool
    requires_manager_approval: bool = False
    rejection_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    is_backdated: bool = False


@dataclass
class AutoApproveResult:
    """Result of auto-approve determination."""
    auto_approve: bool
    reason: str
    notify_manager: bool = True


@dataclass
class BalanceValidationResult:
    """Result of balance validation."""
    is_valid: bool
    is_warning_only: bool = False
    available_hours: float = 0.0
    shortfall_hours: float = 0.0
    message: Optional[str] = None


@dataclass
class PolicyHelp:
    """Help content for a policy rule."""
    title: str
    plain_english: str
    business_reason: str
    example: str
    related_rules: List[str] = field(default_factory=list)


@dataclass
class PolicySection:
    """A section of policy documentation."""
    id: str
    title: str
    icon: str
    content: List[Dict[str, Any]]
    help_items: List[PolicyHelp] = field(default_factory=list)


# =============================================================================
# POLICY ENGINE CLASS
# =============================================================================

class PolicyEngine:
    """
    Centralized policy evaluation for PTO requests.

    All UI and API validations MUST call this engine rather than
    implementing their own rules.
    """

    # Expose constants as class attributes for external access
    BACKDATE_WINDOW_DAYS = BACKDATE_WINDOW_DAYS
    FUTURE_LIMIT_YEARS = FUTURE_LIMIT_YEARS
    TIMEZONE = TIMEZONE
    TRUSTED_AUTO_APPROVE_TYPES = TRUSTED_AUTO_APPROVE_TYPES
    ALWAYS_REQUIRES_APPROVAL = ALWAYS_REQUIRES_APPROVAL
    HARD_CAP_TYPES = HARD_CAP_TYPES
    SOFT_CAP_TYPES = SOFT_CAP_TYPES

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize PolicyEngine.

        Args:
            db: Optional database session for balance lookups
        """
        self.db = db

    def validate_request_dates(
        self,
        start_date: date,
        end_date: date,
        pto_type: str,
        user: Optional[User] = None
    ) -> PolicyResult:
        """
        Validate request dates against policy rules.

        Args:
            start_date: Request start date
            end_date: Request end date
            pto_type: Type of PTO request
            user: Optional user for role-specific validation

        Returns:
            PolicyResult with validation outcome
        """
        today = datetime.now().date()
        warnings = []

        # Check end_date >= start_date
        if end_date < start_date:
            return PolicyResult(
                is_valid=False,
                rejection_reason="End date must be on or after start date"
            )

        # Check future limit
        max_future_date = date(today.year + FUTURE_LIMIT_YEARS, 12, 31)
        if start_date > max_future_date:
            return PolicyResult(
                is_valid=False,
                rejection_reason=f"Cannot request time off more than {FUTURE_LIMIT_YEARS} years in advance"
            )

        # Check backdating
        days_ago = (today - start_date).days
        is_backdated = days_ago > 0

        if is_backdated:
            if days_ago > BACKDATE_WINDOW_DAYS:
                # Beyond 7-day window - rejected
                return PolicyResult(
                    is_valid=False,
                    rejection_reason=f"Requests for dates more than {BACKDATE_WINDOW_DAYS} days ago require manager assistance. Please contact your manager.",
                    is_backdated=True
                )
            else:
                # Within 7-day window - allowed but requires approval
                warnings.append(
                    f"This request is for {days_ago} day(s) ago. It will require manager approval."
                )
                return PolicyResult(
                    is_valid=True,
                    requires_manager_approval=True,
                    warnings=warnings,
                    is_backdated=True
                )

        # Future or today - valid
        return PolicyResult(
            is_valid=True,
            requires_manager_approval=False,
            warnings=warnings,
            is_backdated=False
        )

    def determine_auto_approve(
        self,
        user: User,
        pto_type: str,
        start_date: date,
        is_vacation_rollover: bool = False
    ) -> AutoApproveResult:
        """
        Determine if a request should be auto-approved.

        Auto-approve if ALL conditions met:
        1. User is manager/admin/superadmin OR user.is_trusted
        2. PTO type is in TRUSTED_AUTO_APPROVE_TYPES
        3. Request is NOT a vacation rollover
        4. Request is NOT backdated (start_date < today)

        Args:
            user: The user submitting the request
            pto_type: Type of PTO request
            start_date: Request start date
            is_vacation_rollover: Whether this is a vacation rollover request

        Returns:
            AutoApproveResult with decision and reason
        """
        today = datetime.now().date()
        pto_type_lower = pto_type.lower()

        # Check if backdated
        is_backdated = start_date < today
        if is_backdated:
            return AutoApproveResult(
                auto_approve=False,
                reason="Backdated requests require manager approval",
                notify_manager=True
            )

        # Check if vacation rollover
        if is_vacation_rollover:
            return AutoApproveResult(
                auto_approve=False,
                reason="Vacation rollover requests require manager approval",
                notify_manager=True
            )

        # Check if type requires approval
        if pto_type_lower in ALWAYS_REQUIRES_APPROVAL:
            return AutoApproveResult(
                auto_approve=False,
                reason=f"{pto_type.title()} requests always require manager approval",
                notify_manager=True
            )

        # Check if type is auto-approvable
        if pto_type_lower not in TRUSTED_AUTO_APPROVE_TYPES:
            return AutoApproveResult(
                auto_approve=False,
                reason=f"{pto_type.title()} is not an auto-approve type",
                notify_manager=True
            )

        # Check user role/trust status
        if user.role in ('manager', 'admin', 'superadmin'):
            return AutoApproveResult(
                auto_approve=True,
                reason=f"Self-approved by {user.role}",
                notify_manager=True  # Still notify for record-keeping
            )

        if getattr(user, 'is_trusted', False):
            return AutoApproveResult(
                auto_approve=True,
                reason="Auto-approved (trusted employee)",
                notify_manager=True
            )

        # Regular employee - requires approval
        return AutoApproveResult(
            auto_approve=False,
            reason="Employee requests require manager approval",
            notify_manager=True
        )

    def validate_balance(
        self,
        pto_type: str,
        hours_requested: float,
        available_hours: float
    ) -> BalanceValidationResult:
        """
        Validate if user has sufficient balance for the request.

        Args:
            pto_type: Type of PTO request
            hours_requested: Hours being requested
            available_hours: Current available hours

        Returns:
            BalanceValidationResult with validation outcome
        """
        pto_type_lower = pto_type.lower()
        shortfall = hours_requested - available_hours

        if shortfall <= 0:
            # Sufficient balance
            return BalanceValidationResult(
                is_valid=True,
                is_warning_only=False,
                available_hours=available_hours,
                shortfall_hours=0.0
            )

        # Insufficient balance - check if hard cap or soft cap
        if pto_type_lower in HARD_CAP_TYPES:
            # Hard cap - block submission
            type_label = pto_type.replace('_', ' ').title()
            return BalanceValidationResult(
                is_valid=False,
                is_warning_only=False,
                available_hours=available_hours,
                shortfall_hours=shortfall,
                message=f"Insufficient {type_label} time. You have {available_hours/8:.1f} days available but are requesting {hours_requested/8:.1f} days."
            )

        if pto_type_lower in SOFT_CAP_TYPES:
            # Soft cap - warning only, allow submission
            return BalanceValidationResult(
                is_valid=True,
                is_warning_only=True,
                available_hours=available_hours,
                shortfall_hours=shortfall,
                message=f"This request exceeds your available vacation balance by {shortfall/8:.1f} days. Manager approval is at their discretion."
            )

        # Unknown type - allow with warning
        return BalanceValidationResult(
            is_valid=True,
            is_warning_only=True,
            available_hours=available_hours,
            shortfall_hours=shortfall
        )

    def get_policy_documentation(self) -> List[PolicySection]:
        """
        Get all policy rules in a structured format for the PolicyViewer.

        Returns:
            List of PolicySection objects for display
        """
        return [
            self._build_balance_formulas_section(),
            self._build_vacation_tiers_section(),
            self._build_request_lifecycle_section(),
            self._build_carryover_rules_section(),
            self._build_auto_approve_section(),
            self._build_date_validation_section(),
            self._build_location_policies_section(),
            self._build_year_end_section(),
        ]

    def _build_balance_formulas_section(self) -> PolicySection:
        """Build the balance formulas documentation section."""
        return PolicySection(
            id='balance_formulas',
            title='Balance Formulas',
            icon='calculate',
            content=[
                {
                    'type': 'formula',
                    'label': 'Vacation Available',
                    'formula': 'vacation_total + vacation_carryover - vacation_used - vacation_pending',
                    'description': 'Total allocation plus any approved carryover, minus hours used and pending approval'
                },
                {
                    'type': 'formula',
                    'label': 'Sick Available',
                    'formula': 'sick_total + sick_carryover - sick_used',
                    'description': 'Total allocation plus auto-carryover, minus hours used (no pending tracking)'
                },
                {
                    'type': 'formula',
                    'label': 'Personal Available',
                    'formula': 'personal_total - personal_used',
                    'description': 'Total allocation minus hours used (no carryover, no pending tracking)'
                },
                {
                    'type': 'formula',
                    'label': 'Chicago Paid Leave Available',
                    'formula': 'chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used',
                    'description': 'Per Chicago ordinance - total plus carryover minus used'
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Why Vacation Has Pending",
                    plain_english="Vacation tracks pending hours because requests need manager approval before they're confirmed.",
                    business_reason="Prevents employees from submitting multiple overlapping requests that exceed their balance.",
                    example="You have 40 hours vacation. You submit a 24-hour request (pending). Your available shows 16 hours until approved/denied.",
                    related_rules=["Request Lifecycle", "Auto-Approve Rules"]
                ),
            ]
        )

    def _build_vacation_tiers_section(self) -> PolicySection:
        """Build the vacation tiers documentation section."""
        return PolicySection(
            id='vacation_tiers',
            title='Vacation Tiers',
            icon='trending_up',
            content=[
                {
                    'type': 'table',
                    'headers': ['Years of Service', 'Annual Days', 'Annual Hours'],
                    'rows': [
                        ['0-1 years', '10 days', '80 hours'],
                        ['2-4 years', '12 days', '96 hours'],
                        ['5-9 years', '15 days', '120 hours'],
                        ['10+ years', '20 days', '160 hours'],
                    ]
                },
            ],
            help_items=[
                PolicyHelp(
                    title="When Tier Changes Apply",
                    plain_english="Your vacation tier increases at the start of the calendar year after you reach the service milestone.",
                    business_reason="Simplifies administration by aligning tier changes with year-end processing.",
                    example="If you hit 5 years in March 2025, you'll get 15 days starting January 1, 2026.",
                    related_rules=["Year-End Processing"]
                ),
            ]
        )

    def _build_request_lifecycle_section(self) -> PolicySection:
        """Build the request lifecycle documentation section."""
        return PolicySection(
            id='request_lifecycle',
            title='Request Lifecycle',
            icon='swap_horiz',
            content=[
                {
                    'type': 'flow',
                    'steps': [
                        {'status': 'submitted', 'label': 'Submitted', 'description': 'Hours added to pending (vacation only)'},
                        {'status': 'pending', 'label': 'Pending', 'description': 'Awaiting manager review'},
                        {'status': 'approved', 'label': 'Approved', 'description': 'Pending moved to used'},
                        {'status': 'denied', 'label': 'Denied', 'description': 'Pending removed, hours restored'},
                    ]
                },
                {
                    'type': 'note',
                    'text': 'Cancelled requests restore pending hours. Approved requests can only be cancelled by managers.'
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Auto-Approved Requests",
                    plain_english="Managers and trusted employees skip the pending state - their requests are immediately approved.",
                    business_reason="Reduces administrative burden while maintaining audit trail.",
                    example="A manager submits sick time. It's immediately approved and deducted from their balance.",
                    related_rules=["Auto-Approve Rules"]
                ),
            ]
        )

    def _build_carryover_rules_section(self) -> PolicySection:
        """Build the carryover rules documentation section."""
        return PolicySection(
            id='carryover_rules',
            title='Carryover Rules',
            icon='event_repeat',
            content=[
                {
                    'type': 'table',
                    'headers': ['Leave Type', 'Carryover Rule', 'Max Carryover'],
                    'rows': [
                        ['Vacation', 'Exception only (manager approval)', 'Per approval'],
                        ['Sick', 'Automatic', '80 hours (Chicago: 80 hours)'],
                        ['Personal', 'None (use-it-or-lose-it)', '0 hours'],
                        ['Chicago Paid Leave', 'Automatic', '16 hours'],
                    ]
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Vacation Exception Carryover",
                    plain_english="Unused vacation does NOT automatically carry over. Employees must request an exception, which managers can approve as a bonus.",
                    business_reason="Encourages employees to use vacation for work-life balance. Exception process allows flexibility for special circumstances.",
                    example="You have 16 hours unused vacation at year-end. You submit a carryover exception request. If approved, those hours are added as a bonus to next year.",
                    related_rules=["Year-End Processing"]
                ),
            ]
        )

    def _build_auto_approve_section(self) -> PolicySection:
        """Build the auto-approve rules documentation section."""
        return PolicySection(
            id='auto_approve',
            title='Auto-Approve Rules',
            icon='verified',
            content=[
                {
                    'type': 'list',
                    'title': 'Auto-Approve Eligible Types',
                    'items': list(TRUSTED_AUTO_APPROVE_TYPES)
                },
                {
                    'type': 'list',
                    'title': 'Always Requires Approval',
                    'items': list(ALWAYS_REQUIRES_APPROVAL)
                },
                {
                    'type': 'rules',
                    'title': 'Auto-Approve Conditions (ALL must be met)',
                    'items': [
                        'User is manager/admin/superadmin OR is marked as trusted employee',
                        'PTO type is vacation, sick, or personal',
                        'Request is NOT a vacation rollover',
                        'Request is NOT backdated (start date < today)',
                    ]
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Trusted Employee Status",
                    plain_english="Admins can mark reliable employees as 'trusted', allowing their standard PTO to auto-approve.",
                    business_reason="Reduces manager workload for employees with established track records.",
                    example="Sarah has been with the company 5 years with no PTO issues. Admin marks her as trusted. Now her vacation requests auto-approve.",
                    related_rules=["Request Lifecycle"]
                ),
                PolicyHelp(
                    title="Backdated Requests",
                    plain_english="Requests for past dates (up to 7 days ago) always require manager approval, even for trusted employees.",
                    business_reason="Ensures oversight for retroactive time-off entries while allowing correction of forgotten entries.",
                    example="A manager forgets to log yesterday's sick day. They can submit it, but it goes to their manager (or admin) for approval.",
                    related_rules=["Date Validation Rules"]
                ),
            ]
        )

    def _build_date_validation_section(self) -> PolicySection:
        """Build the date validation documentation section."""
        return PolicySection(
            id='date_validation',
            title='Date Validation Rules',
            icon='event_available',
            content=[
                {
                    'type': 'rules',
                    'title': 'Date Limits',
                    'items': [
                        f'Backdating allowed up to {BACKDATE_WINDOW_DAYS} calendar days',
                        f'Future requests allowed up to {FUTURE_LIMIT_YEARS} years ahead',
                        'Weekends and holidays are excluded from day count',
                        'Start date must be on or before end date',
                    ]
                },
                {
                    'type': 'note',
                    'text': f'All date calculations use {TIMEZONE} timezone.'
                },
            ],
            help_items=[
                PolicyHelp(
                    title="7-Day Backdating Window",
                    plain_english="Employees can submit PTO requests for dates up to 7 days in the past, but these always require manager approval.",
                    business_reason="Allows correction of forgotten time-off entries while maintaining oversight. The 7-day limit prevents abuse.",
                    example="Today is December 19th. You forgot to log sick time from December 15th. You can submit the request, but your manager must approve it.",
                    related_rules=["Auto-Approve Rules"]
                ),
            ]
        )

    def _build_location_policies_section(self) -> PolicySection:
        """Build the location policies documentation section."""
        return PolicySection(
            id='location_policies',
            title='Location Policies',
            icon='location_on',
            content=[
                {
                    'type': 'heading',
                    'text': 'Chicago, IL - Special Rules'
                },
                {
                    'type': 'rules',
                    'title': 'Chicago Paid Leave Ordinance',
                    'items': [
                        '40 hours (5 days) Chicago Paid Leave per year',
                        'Can be used for any reason',
                        'Up to 16 hours carryover allowed',
                        'Cannot exceed available balance (hard cap)',
                    ]
                },
                {
                    'type': 'rules',
                    'title': 'Chicago Sick & Safe Leave',
                    'items': [
                        'Uses company Sick Leave bank',
                        'Up to 80 hours carryover (vs 40 for non-Chicago)',
                        'Can be used for safe leave purposes (domestic violence, etc.)',
                    ]
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Chicago Leave vs Sick Leave",
                    plain_english="Chicago employees get TWO separate leave banks: regular Sick Leave (same as all employees, with higher carryover) AND Chicago Paid Leave (separate bank, any reason).",
                    business_reason="Chicago ordinance requires employers to provide Paid Leave separate from Sick Leave.",
                    example="A Chicago employee has 40 hours sick and 40 hours Chicago Paid Leave. They can use Chicago Paid Leave for a vacation day if their vacation is exhausted.",
                    related_rules=["Balance Formulas", "Carryover Rules"]
                ),
            ]
        )

    def _build_year_end_section(self) -> PolicySection:
        """Build the year-end processing documentation section."""
        return PolicySection(
            id='year_end',
            title='Year-End Processing',
            icon='calendar_month',
            content=[
                {
                    'type': 'rules',
                    'title': 'Automatic Processing (runs on first login of new year)',
                    'items': [
                        'Create new year balances for all active employees',
                        'Apply vacation tier increases based on tenure',
                        'Auto-carryover unused Sick up to policy maximum',
                        'Auto-carryover Chicago Paid Leave up to 16 hours',
                        'Apply approved vacation exception carryover as bonus',
                        'Generate federal holidays for new year',
                    ]
                },
                {
                    'type': 'note',
                    'text': 'Personal days do NOT carry over - use them or lose them by December 31st.'
                },
            ],
            help_items=[
                PolicyHelp(
                    title="Vacation Exception Carryover",
                    plain_english="When a manager approves a vacation carryover exception, those hours are added as a BONUS to the new year's allocation.",
                    business_reason="The exception is a reward, not just a deferral. The new year's regular allocation is not affected.",
                    example="You get 80 hours vacation for 2026. Manager approved 16-hour carryover from 2025. You start 2026 with 96 hours total.",
                    related_rules=["Carryover Rules"]
                ),
            ]
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_policy_engine(db: Optional[Session] = None) -> PolicyEngine:
    """Get a PolicyEngine instance."""
    return PolicyEngine(db=db)
