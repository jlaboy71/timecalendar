"""
Balance service for managing PTO balances in the PTO and Market Calendar System.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.pto_balance import PTOBalance
from ..models.user import User
from ..models.system_setting import SystemSetting
from ..schemas.pto_schemas import PTOBalanceUpdate


class BalanceService:
    """
    Service class for managing PTO balance operations.
    
    This service provides methods for creating, retrieving, and updating
    PTO balances for users across different years.
    """
    
    # Chicago Safe Leave annual max (40 hours per ordinance)
    CHICAGO_SAFE_LEAVE_ANNUAL_MAX = Decimal('40.00')

    def __init__(self, db: Session) -> None:
        """
        Initialize the BalanceService with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _is_chicago_leave_applicable(self, user_id: int) -> bool:
        """
        Check if Chicago Safe Leave should be applied to a user.

        Returns True if:
        1. Chicago Safe Leave feature is enabled in system settings
        2. User's location_city is 'Chicago' (case-insensitive)

        Args:
            user_id: ID of the user to check

        Returns:
            bool: True if Chicago leave should be applied
        """
        # Check if feature is enabled
        stmt = select(SystemSetting).where(SystemSetting.key == 'chicago.safe_leave_enabled')
        chicago_setting = self.db.execute(stmt).scalar_one_or_none()

        if not chicago_setting or not chicago_setting.bool_value:
            return False

        # Check if user is in Chicago
        stmt = select(User).where(User.id == user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if not user or not user.location_city:
            return False

        return user.location_city.lower() == 'chicago'

    def get_or_create_balance(self, user_id: int, year: int, commit: bool = True) -> PTOBalance:
        """
        Get existing balance for user/year or create new one with zeros.

        Args:
            user_id: ID of the user
            year: Year for the balance
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: The existing or newly created balance
        """
        # Try to get existing balance
        stmt = select(PTOBalance).where(
            PTOBalance.user_id == user_id,
            PTOBalance.year == year
        )
        balance = self.db.execute(stmt).scalar_one_or_none()

        if balance is None:
            # Check if Chicago leave applies to this user
            chicago_leave_total = Decimal('0.00')
            if self._is_chicago_leave_applicable(user_id):
                chicago_leave_total = self.CHICAGO_SAFE_LEAVE_ANNUAL_MAX

            # Create new balance with zeros (Chicago leave set if applicable)
            balance = PTOBalance(
                user_id=user_id,
                year=year,
                vacation_total=Decimal('0.00'),
                vacation_used=Decimal('0.00'),
                vacation_pending=Decimal('0.00'),
                sick_total=Decimal('0.00'),
                sick_used=Decimal('0.00'),
                personal_total=Decimal('0.00'),
                personal_used=Decimal('0.00'),
                remote_weekly_used=0,
                chicago_safe_leave_total=chicago_leave_total,
                chicago_safe_leave_used=Decimal('0.00'),
                chicago_safe_leave_pending=Decimal('0.00'),
                chicago_safe_leave_carryover=Decimal('0.00')
            )
            self.db.add(balance)
            if commit:
                self.db.commit()
                self.db.refresh(balance)
            else:
                self.db.flush()

        return balance
    
    def get_balance_by_id(self, balance_id: int) -> Optional[PTOBalance]:
        """
        Get balance by ID.
        
        Args:
            balance_id: ID of the balance
            
        Returns:
            Optional[PTOBalance]: The balance or None if not found
        """
        stmt = select(PTOBalance).where(PTOBalance.id == balance_id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_user_balances(self, user_id: int) -> List[PTOBalance]:
        """
        Get all balances for a user ordered by year descending.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List[PTOBalance]: List of balances ordered by year descending
        """
        stmt = select(PTOBalance).where(
            PTOBalance.user_id == user_id
        ).order_by(PTOBalance.year.desc())
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def get_current_year_balance(self, user_id: int) -> Optional[PTOBalance]:
        """
        Get balance for current year.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Optional[PTOBalance]: The current year balance or None if not found
        """
        current_year = datetime.now().year
        stmt = select(PTOBalance).where(
            PTOBalance.user_id == user_id,
            PTOBalance.year == current_year
        )
        return self.db.execute(stmt).scalar_one_or_none()
    
    def update_balance_totals(
        self, 
        balance_id: int, 
        balance_data: PTOBalanceUpdate
    ) -> Optional[PTOBalance]:
        """
        Update balance totals with provided data.
        
        Args:
            balance_id: ID of the balance to update
            balance_data: Data containing fields to update
            
        Returns:
            Optional[PTOBalance]: Updated balance or None if not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            return None
        
        # Update only provided fields
        update_data = balance_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(balance, field, value)
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
    
    def adjust_vacation_used(
        self,
        balance_id: int,
        days: Decimal,
        is_pending: bool = False,
        commit: bool = True
    ) -> PTOBalance:
        """
        Adjust vacation used or pending days.

        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            is_pending: If True, adjust pending; otherwise adjust used
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        if is_pending:
            balance.vacation_pending += days
        else:
            balance.vacation_used += days

        if commit:
            self.db.commit()
            self.db.refresh(balance)
        return balance
    
    def adjust_sick_used(self, balance_id: int, days: Decimal, commit: bool = True) -> PTOBalance:
        """
        Adjust sick days used.

        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        balance.sick_used += days

        if commit:
            self.db.commit()
            self.db.refresh(balance)
        return balance
    
    def adjust_personal_used(self, balance_id: int, days: Decimal, commit: bool = True) -> PTOBalance:
        """
        Adjust personal days used.

        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        balance.personal_used += days

        if commit:
            self.db.commit()
            self.db.refresh(balance)
        return balance
    
    def move_pending_to_used(self, balance_id: int, days: Decimal, commit: bool = True) -> PTOBalance:
        """
        Move days from pending to used (when request is approved).

        Args:
            balance_id: ID of the balance
            days: Number of days to move
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        balance.vacation_pending -= days
        balance.vacation_used += days

        if commit:
            self.db.commit()
            self.db.refresh(balance)
        return balance
    
    def remove_pending(self, balance_id: int, days: Decimal, commit: bool = True) -> PTOBalance:
        """
        Remove days from pending (when request is denied).

        Args:
            balance_id: ID of the balance
            days: Number of days to remove from pending
            commit: If True, commit the transaction (default). Set to False for transaction participation.

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        balance.vacation_pending -= days

        if commit:
            self.db.commit()
            self.db.refresh(balance)
        return balance

    def allocate_standard_balance(self, user_id: int, year: int = None) -> PTOBalance:
        """
        Create or update balance with standard PTO allocation for new employees.

        Standard allocation:
        - Vacation: 160 hours (20 days)
        - Sick: 40 hours (5 days)
        - Personal: 16 hours (2 days)

        Args:
            user_id: ID of the user
            year: Year for the balance (defaults to current year)

        Returns:
            PTOBalance: The balance with standard allocation
        """
        if year is None:
            year = datetime.now().year

        # Get or create the balance record
        balance = self.get_or_create_balance(user_id, year)

        # Set standard allocation values
        balance.vacation_total = Decimal('160.00')
        balance.sick_total = Decimal('40.00')
        balance.personal_total = Decimal('16.00')

        # Set Chicago leave if applicable
        if self._is_chicago_leave_applicable(user_id):
            balance.chicago_safe_leave_total = self.CHICAGO_SAFE_LEAVE_ANNUAL_MAX

        self.db.commit()
        self.db.refresh(balance)
        return balance

    def restore_balance(
        self,
        balance_id: int,
        pto_type: str,
        hours: float,
        was_approved: bool
    ) -> PTOBalance:
        """
        Restore balance when a request is cancelled or deleted.

        This centralized method handles all balance restoration consistently,
        using Decimal arithmetic and preventing negative values.

        Args:
            balance_id: ID of the balance record
            pto_type: Type of PTO ('vacation', 'sick', 'personal')
            hours: Number of hours to restore
            was_approved: True if request was approved (restore from used),
                         False if pending (restore from pending)

        Returns:
            PTOBalance: Updated balance

        Raises:
            ValueError: If balance not found or invalid pto_type
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")

        # Convert hours to Decimal for consistent arithmetic
        hours_decimal = Decimal(str(hours))
        pto_type_lower = pto_type.lower()

        if pto_type_lower == 'vacation':
            if was_approved:
                # Restore from used
                current = Decimal(str(balance.vacation_used or 0))
                balance.vacation_used = max(Decimal('0'), current - hours_decimal)
            else:
                # Restore from pending
                current = Decimal(str(balance.vacation_pending or 0))
                balance.vacation_pending = max(Decimal('0'), current - hours_decimal)
        elif pto_type_lower == 'sick':
            if was_approved:
                current = Decimal(str(balance.sick_used or 0))
                balance.sick_used = max(Decimal('0'), current - hours_decimal)
            # Note: sick_pending field doesn't exist yet - will be added in future migration
        elif pto_type_lower == 'personal':
            if was_approved:
                current = Decimal(str(balance.personal_used or 0))
                balance.personal_used = max(Decimal('0'), current - hours_decimal)
            # Note: personal_pending field doesn't exist yet - will be added in future migration
        # WFH and other types don't affect balance

        self.db.commit()
        self.db.refresh(balance)
        return balance
