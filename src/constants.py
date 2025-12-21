"""
Application constants and enumerations.

This module provides type-safe enums for common values used throughout
the application, ensuring consistency and enabling IDE autocompletion.
"""
from enum import Enum


class UserRole(str, Enum):
    """
    User role enumeration for role-based access control.

    Roles are hierarchical:
    - EMPLOYEE: Base role with PTO request submission
    - MANAGER: Employee + team management and approvals
    - ADMIN: Manager + system administration
    - SUPERADMIN: Full system access including year-end processing
    """
    EMPLOYEE = 'employee'
    MANAGER = 'manager'
    ADMIN = 'admin'
    SUPERADMIN = 'superadmin'

    @classmethod
    def management_roles(cls) -> list['UserRole']:
        """Roles that can approve/deny PTO requests."""
        return [cls.MANAGER, cls.ADMIN, cls.SUPERADMIN]

    @classmethod
    def admin_roles(cls) -> list['UserRole']:
        """Roles with administrative access."""
        return [cls.ADMIN, cls.SUPERADMIN]


class PTOStatus(str, Enum):
    """
    PTO request status enumeration.

    Lifecycle: PENDING -> APPROVED/DENIED
    Alternative: PENDING -> CANCELLED (by employee)
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    CANCELLED = 'cancelled'

    @classmethod
    def active_statuses(cls) -> list['PTOStatus']:
        """Statuses that count toward balance calculations."""
        return [cls.PENDING, cls.APPROVED]

    @classmethod
    def terminal_statuses(cls) -> list['PTOStatus']:
        """Statuses that represent completed requests."""
        return [cls.APPROVED, cls.DENIED, cls.CANCELLED]


class PTOType(str, Enum):
    """
    PTO request type enumeration.

    Types are categorized as:
    - Accruing: Tracked in PTOBalance (vacation, sick, personal)
    - Non-accruing: No balance limits (bereavement, fmla, etc.)
    """
    VACATION = 'vacation'
    SICK = 'sick'
    PERSONAL = 'personal'
    BEREAVEMENT = 'bereavement'
    FMLA = 'fmla'
    JURY_DUTY = 'jury_duty'
    VOTING = 'voting'
    MILITARY = 'military'
    CHICAGO_LEAVE = 'chicago_leave'  # Chicago Paid Leave (request type)
    CHICAGO_PAID_LEAVE = 'chicago_paid_leave'  # Chicago Paid Leave (balance field reference)

    @classmethod
    def accruing_types(cls) -> list['PTOType']:
        """Types that accrue and have balance tracking."""
        return [cls.VACATION, cls.SICK, cls.PERSONAL]

    @classmethod
    def non_accruing_types(cls) -> list['PTOType']:
        """Types without balance limits."""
        return [
            cls.BEREAVEMENT, cls.FMLA, cls.JURY_DUTY,
            cls.VOTING, cls.MILITARY,
            cls.CHICAGO_LEAVE, cls.CHICAGO_PAID_LEAVE
        ]


class CarryoverStatus(str, Enum):
    """
    Carryover request status enumeration.

    Used for year-end balance carryover requests.
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'


# Type icons for UI display (Material Design icon names)
TYPE_ICONS = {
    PTOType.VACATION: 'beach_access',
    PTOType.SICK: 'medical_services',
    PTOType.PERSONAL: 'person',
    PTOType.BEREAVEMENT: 'sentiment_very_dissatisfied',
    PTOType.FMLA: 'family_restroom',
    PTOType.JURY_DUTY: 'gavel',
    PTOType.VOTING: 'how_to_vote',
    PTOType.MILITARY: 'military_tech',
    PTOType.CHICAGO_LEAVE: 'location_city',
    PTOType.CHICAGO_PAID_LEAVE: 'location_city',
}

# Type colors for UI display (Tailwind/Quasar color names)
TYPE_COLORS = {
    PTOType.VACATION: 'blue',
    PTOType.SICK: 'green',
    PTOType.PERSONAL: 'purple',
    PTOType.BEREAVEMENT: 'brown',
    PTOType.FMLA: 'teal',
    PTOType.JURY_DUTY: 'indigo',
    PTOType.VOTING: 'cyan',
    PTOType.MILITARY: 'deep-orange',
    PTOType.CHICAGO_LEAVE: 'amber',
    PTOType.CHICAGO_PAID_LEAVE: 'amber',
}

# Status colors for UI display
STATUS_COLORS = {
    PTOStatus.PENDING: 'amber',
    PTOStatus.APPROVED: 'green',
    PTOStatus.DENIED: 'red',
    PTOStatus.CANCELLED: 'grey',
}
