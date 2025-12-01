"""
Balance service for managing PTO balances in the PTO and Market Calendar System.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.pto_balance import PTOBalance
from ..schemas.pto_schemas import PTOBalanceUpdate


class BalanceService:
    """
    Service class for managing PTO balance operations.
    
    This service provides methods for creating, retrieving, and updating
    PTO balances for users across different years.
    """
    
    def __init__(self, db: Session) -> None:
        """
        Initialize the BalanceService with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_or_create_balance(self, user_id: int, year: int) -> PTOBalance:
        """
        Get existing balance for user/year or create new one with zeros.
        
        Args:
            user_id: ID of the user
            year: Year for the balance
            
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
            # Create new balance with zeros
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
                remote_weekly_used=0
            )
            self.db.add(balance)
            self.db.commit()
            self.db.refresh(balance)
        
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
        is_pending: bool = False
    ) -> PTOBalance:
        """
        Adjust vacation used or pending days.
        
        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            is_pending: If True, adjust pending; otherwise adjust used
            
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
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
    
    def adjust_sick_used(self, balance_id: int, days: Decimal) -> PTOBalance:
        """
        Adjust sick days used.
        
        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            
        Returns:
            PTOBalance: Updated balance
            
        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")
        
        balance.sick_used += days
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
    
    def adjust_personal_used(self, balance_id: int, days: Decimal) -> PTOBalance:
        """
        Adjust personal days used.
        
        Args:
            balance_id: ID of the balance
            days: Number of days to adjust (can be negative)
            
        Returns:
            PTOBalance: Updated balance
            
        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")
        
        balance.personal_used += days
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
    
    def move_pending_to_used(self, balance_id: int, days: Decimal) -> PTOBalance:
        """
        Move days from pending to used (when request is approved).
        
        Args:
            balance_id: ID of the balance
            days: Number of days to move
            
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
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
    
    def remove_pending(self, balance_id: int, days: Decimal) -> PTOBalance:
        """
        Remove days from pending (when request is denied).
        
        Args:
            balance_id: ID of the balance
            days: Number of days to remove from pending
            
        Returns:
            PTOBalance: Updated balance
            
        Raises:
            ValueError: If balance not found
        """
        balance = self.get_balance_by_id(balance_id)
        if balance is None:
            raise ValueError(f"Balance with ID {balance_id} not found")
        
        balance.vacation_pending -= days
        
        self.db.commit()
        self.db.refresh(balance)
        return balance
