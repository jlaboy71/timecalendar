"""
User service for managing user operations.
"""
from typing import List, Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from ..models.user import User
from ..models.pto_balance import PTOBalance
from ..schemas.user_schemas import UserCreate, UserUpdate, UserPasswordChange
from ..utils.password import hash_password, verify_password

# ══════════════════════════════════════════════════════════════════════════════
# PTO ALLOCATION CONSTANTS (MUST match year_end_service.py)
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_SICK_DAYS = 5       # 40 hours
DEFAULT_PERSONAL_DAYS = 2   # 16 hours
CHICAGO_PAID_LEAVE_HOURS = Decimal('40.00')  # 5 days for Chicago employees

# Vacation tiers based on tenure (years of service -> days)
VACATION_TIERS = {
    10: 20,  # 10+ years: 4 weeks (160 hours)
    5: 15,   # 5-9 years: 3 weeks (120 hours)
    2: 12,   # 2-4 years: 2.4 weeks (96 hours)
    0: 10,   # 0-1 years: 2 weeks (80 hours)
}


class UserService:
    """
    Service class for managing user operations.
    
    This service provides methods for creating, retrieving, updating, and
    authenticating users, with proper password handling and validation.
    """
    
    def __init__(self, db: Session) -> None:
        """
        Initialize the UserService with a database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _calculate_vacation_days(self, hire_date: date) -> int:
        """
        Calculate vacation days based on employee tenure.

        CRITICAL: This logic MUST match year_end_service.py!

        Args:
            hire_date: Employee's hire date

        Returns:
            Number of vacation days based on tenure
        """
        if not hire_date:
            return VACATION_TIERS[0]

        today = date.today()
        years_of_service = (today - hire_date).days // 365

        # Find the right tier
        for min_years, days in sorted(VACATION_TIERS.items(), reverse=True):
            if years_of_service >= min_years:
                return days

        return VACATION_TIERS[0]

    def _update_or_create_balance(self, user: User, year: int = None) -> PTOBalance:
        """
        Update or create PTO balance with proper allocations based on hire date.

        CRITICAL: This function ensures balances match tenure-based allocations.
        Called automatically when:
        - New user is created
        - Hire date is changed

        Args:
            user: The user to update balance for
            year: The year for the balance (defaults to current year)

        Returns:
            The created or updated PTOBalance
        """
        if year is None:
            year = date.today().year

        # Calculate allocations based on tenure
        vacation_days = self._calculate_vacation_days(user.hire_date)
        vacation_hours = Decimal(str(vacation_days * 8))
        sick_hours = Decimal(str(DEFAULT_SICK_DAYS * 8))
        personal_hours = Decimal(str(DEFAULT_PERSONAL_DAYS * 8))

        # Chicago Paid Leave for Chicago employees
        chicago_leave = CHICAGO_PAID_LEAVE_HOURS if user.location_city and user.location_city.lower() == 'chicago' else Decimal('0.00')

        # Check for existing balance
        bal_stmt = select(PTOBalance).where(
            PTOBalance.user_id == user.id,
            PTOBalance.year == year
        )
        balance = self.db.execute(bal_stmt).scalar_one_or_none()

        if balance:
            # Update existing balance totals (preserve used/pending)
            balance.vacation_total = vacation_hours
            balance.sick_total = sick_hours
            balance.personal_total = personal_hours
            balance.chicago_paid_leave_total = chicago_leave
        else:
            # Create new balance
            balance = PTOBalance(
                user_id=user.id,
                year=year,
                vacation_total=vacation_hours,
                vacation_used=Decimal('0.00'),
                vacation_pending=Decimal('0.00'),
                sick_total=sick_hours,
                sick_used=Decimal('0.00'),
                personal_total=personal_hours,
                personal_used=Decimal('0.00'),
                remote_weekly_used=0,
                chicago_paid_leave_total=chicago_leave,
                chicago_paid_leave_used=Decimal('0.00'),
                chicago_paid_leave_pending=Decimal('0.00'),
                chicago_paid_leave_carryover=Decimal('0.00')
            )
            self.db.add(balance)

        return balance

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with validation.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created User instance
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check for duplicate username
        if self.get_user_by_username(user_data.username):
            raise ValueError(f"Username '{user_data.username}' already exists")
        
        # Check for duplicate email
        if self.get_user_by_email(user_data.email):
            raise ValueError(f"Email '{user_data.email}' already exists")
        
        # Hash the password
        password_hash = hash_password(user_data.password)
        
        # Create user instance
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            department_id=user_data.department_id,
            hire_date=user_data.hire_date,
            is_active=user_data.is_active,
            location_state=user_data.location_state,
            location_city=user_data.location_city,
            remote_schedule=user_data.remote_schedule,
            anniversary_date=user_data.anniversary_date
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # CRITICAL: Create PTO balance with proper tenure-based allocation
        self._update_or_create_balance(user)
        self.db.commit()

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by ID.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User instance if found, None otherwise
        """
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User instance if found, None otherwise
        """
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User instance if found, None otherwise
        """
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_all_users(self, skip: int = 0, limit: int = 100, active_only: bool = False) -> List[User]:
        """
        Retrieve all users with pagination and filtering options.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            active_only: If True, only return active users
            
        Returns:
            List of User instances
        """
        stmt = select(User)
        
        if active_only:
            stmt = stmt.where(User.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())
    
    @staticmethod
    def get_users_by_role(db: Session, role: str) -> List[User]:
        """
        Retrieve all users with a specific role.

        Args:
            db: Database session
            role: Role to filter by (e.g., 'manager', 'admin', 'employee')

        Returns:
            List of User instances with the specified role
        """
        stmt = select(User).where(User.role == role, User.is_active == True)
        return list(db.execute(stmt).scalars().all())

    def get_users_by_department(self, department_id: int) -> List[User]:
        """
        Retrieve all users in a specific department.

        Args:
            department_id: Department ID to filter by

        Returns:
            List of User instances in the specified department
        """
        stmt = select(User).where(User.department_id == department_id)
        return list(self.db.execute(stmt).scalars().all())
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: ID of user to update
            user_data: Updated user data
            
        Returns:
            Updated User instance if found, None otherwise
            
        Raises:
            ValueError: If email is being changed to one that already exists
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Check for username uniqueness if username is being updated
        update_data = user_data.model_dump(exclude_unset=True)
        if 'username' in update_data and update_data['username'] != user.username:
            existing_user = self.get_user_by_username(update_data['username'])
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Username '{update_data['username']}' already exists")

        # Check for email uniqueness if email is being updated
        if 'email' in update_data and update_data['email'] != user.email:
            existing_user = self.get_user_by_email(update_data['email'])
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Email '{update_data['email']}' already exists")

        # Handle password update separately (needs hashing)
        if 'password' in update_data and update_data['password']:
            user.password_hash = hash_password(update_data['password'])
            del update_data['password']

        # CRITICAL: Track if hire_date or location changes (affects PTO allocation)
        old_hire_date = user.hire_date
        old_location_city = user.location_city
        hire_date_changing = 'hire_date' in update_data and update_data['hire_date'] != old_hire_date
        location_changing = 'location_city' in update_data and update_data['location_city'] != old_location_city

        # Update user attributes
        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        # CRITICAL: Recalculate PTO balance if hire_date or location changed
        if hire_date_changing or location_changing:
            self._update_or_create_balance(user)
            self.db.commit()

        return user

    def deactivate_user(self, user_id: int) -> bool:
        """
        Soft delete a user by setting is_active to False.
        This preserves historical PTO data linked to the user.

        Args:
            user_id: ID of user to deactivate

        Returns:
            True if user was found and deactivated, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        self.db.commit()
        return True

    def delete_user(self, user_id: int) -> bool:
        """
        Hard delete a user and all related records from the database.
        Use this for permanently removing terminated/quit employees.

        Args:
            user_id: ID of user to delete

        Returns:
            True if user was found and deleted, False otherwise
        """
        from src.models.pto_balance import PTOBalance
        from src.models.pto_request import PTORequest

        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Delete related PTO records first (cascade)
        self.db.execute(delete(PTORequest).where(PTORequest.user_id == user_id))
        self.db.execute(delete(PTOBalance).where(PTOBalance.user_id == user_id))

        # Delete the user
        self.db.delete(user)
        self.db.commit()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username to authenticate
            password: Plain text password to verify
            
        Returns:
            User instance if authentication successful, None otherwise
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if verify_password(password, user.password_hash):
            return user
        
        return None
    
    def change_password(self, user_id: int, password_change: UserPasswordChange) -> bool:
        """
        Change a user's password after verifying the current password.
        
        Args:
            user_id: ID of user changing password
            password_change: Password change data with current and new passwords
            
        Returns:
            True if password was changed successfully, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not verify_password(password_change.current_password, user.password_hash):
            return False
        
        # Hash and update new password
        user.password_hash = hash_password(password_change.new_password)
        self.db.commit()
        return True
