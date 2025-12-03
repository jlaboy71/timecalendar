"""
User service for managing user operations.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..models.user import User
from ..schemas.user_schemas import UserCreate, UserUpdate, UserPasswordChange
from ..utils.password import hash_password, verify_password


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
            is_active=user_data.is_active
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
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
        
        # Check for email uniqueness if email is being updated
        update_data = user_data.model_dump(exclude_unset=True)
        if 'email' in update_data and update_data['email'] != user.email:
            existing_user = self.get_user_by_email(update_data['email'])
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Email '{update_data['email']}' already exists")
        
        # Update user attributes
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """
        Soft delete a user by setting is_active to False.
        
        Args:
            user_id: ID of user to delete
            
        Returns:
            True if user was found and deleted, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
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
