"""
Accrual calculation service with state-specific policy support.
"""
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.leave_type import LeaveType
from src.models.leave_policy import LeavePolicy
from src.models.vacation_accrual_tier import VacationAccrualTier


class AccrualService:
    """
    Handles leave accrual calculations based on policies.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_policy_for_employee(
        self,
        employee: User,
        leave_type_code: str
    ) -> Optional[LeavePolicy]:
        """
        Get the applicable policy for an employee based on their location.

        Resolution order:
        1. City-specific (e.g., Chicago, IL)
        2. State-specific (e.g., IL)
        3. Default (NULL location)
        """
        leave_type = self.db.query(LeaveType).filter_by(code=leave_type_code).first()
        if not leave_type:
            return None

        today = date.today()

        # Try city-specific first
        if employee.location_city and employee.location_state:
            policy = self.db.query(LeavePolicy).filter(
                LeavePolicy.leave_type_id == leave_type.id,
                LeavePolicy.location_state == employee.location_state,
                LeavePolicy.location_city == employee.location_city,
                LeavePolicy.effective_date <= today,
                (LeavePolicy.end_date.is_(None) | (LeavePolicy.end_date >= today))
            ).first()
            if policy:
                return policy

        # Try state-specific
        if employee.location_state:
            policy = self.db.query(LeavePolicy).filter(
                LeavePolicy.leave_type_id == leave_type.id,
                LeavePolicy.location_state == employee.location_state,
                LeavePolicy.location_city.is_(None),
                LeavePolicy.effective_date <= today,
                (LeavePolicy.end_date.is_(None) | (LeavePolicy.end_date >= today))
            ).first()
            if policy:
                return policy

        # Fall back to default
        return self.db.query(LeavePolicy).filter(
            LeavePolicy.leave_type_id == leave_type.id,
            LeavePolicy.location_state.is_(None),
            LeavePolicy.location_city.is_(None),
            LeavePolicy.effective_date <= today,
            (LeavePolicy.end_date.is_(None) | (LeavePolicy.end_date >= today))
        ).first()

    def get_vacation_tier(self, employee: User) -> Optional[VacationAccrualTier]:
        """
        Get vacation accrual tier based on employee tenure.
        """
        if not employee.hire_date:
            return None

        years_of_service = (date.today() - employee.hire_date).days // 365

        return self.db.query(VacationAccrualTier).filter(
            VacationAccrualTier.min_years_service <= years_of_service,
            (VacationAccrualTier.max_years_service.is_(None) |
             (VacationAccrualTier.max_years_service >= years_of_service))
        ).first()

    def calculate_annual_vacation_hours(self, employee: User) -> Decimal:
        """
        Calculate annual vacation hours based on tenure.
        """
        tier = self.get_vacation_tier(employee)
        if not tier:
            return Decimal("0")

        # Convert days to hours (8 hours per day)
        return tier.annual_days * Decimal("8")

    def calculate_monthly_vacation_hours(self, employee: User) -> Decimal:
        """
        Calculate monthly vacation accrual hours based on tenure.
        """
        tier = self.get_vacation_tier(employee)
        if not tier:
            return Decimal("0")

        # Convert days to hours (8 hours per day)
        return tier.monthly_accrual_rate * Decimal("8")

    def can_use_leave(
        self,
        employee: User,
        leave_type_code: str
    ) -> Tuple[bool, str]:
        """
        Check if employee can use a specific leave type.

        Returns:
            (can_use: bool, reason: str)
        """
        policy = self.get_policy_for_employee(employee, leave_type_code)

        if not policy:
            return True, "No policy restrictions"

        # Check waiting period
        if policy.waiting_period_days > 0 and employee.hire_date:
            days_employed = (date.today() - employee.hire_date).days
            if days_employed < policy.waiting_period_days:
                days_remaining = policy.waiting_period_days - days_employed
                return False, f"Must wait {days_remaining} more days"

        return True, "Eligible"

    def get_max_carryover_hours(
        self,
        employee: User,
        leave_type_code: str
    ) -> Decimal:
        """
        Get maximum carryover hours allowed for employee.
        """
        policy = self.get_policy_for_employee(employee, leave_type_code)
        if policy and policy.max_carryover_hours is not None:
            return policy.max_carryover_hours
        return Decimal("0")

    def get_min_increment_hours(
        self,
        employee: User,
        leave_type_code: str
    ) -> Optional[Decimal]:
        """
        Get minimum increment hours for a leave request.
        """
        policy = self.get_policy_for_employee(employee, leave_type_code)
        if policy and policy.min_increment_hours is not None:
            return policy.min_increment_hours
        return None

    def get_advance_notice_days(
        self,
        employee: User,
        leave_type_code: str
    ) -> int:
        """
        Get required advance notice days for leave requests.
        """
        policy = self.get_policy_for_employee(employee, leave_type_code)
        if policy:
            return policy.advance_notice_days
        return 0

    def get_years_of_service(self, employee: User) -> int:
        """
        Calculate years of service for an employee.
        """
        if not employee.hire_date:
            return 0
        return (date.today() - employee.hire_date).days // 365
