"""User-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User's email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")
    role: str = Field(..., pattern=r"^(employee|manager|admin)$", description="User role")
    department_id: Optional[int] = Field(None, description="ID of user's department")
    hire_date: datetime = Field(..., description="Date user was hired")
    is_active: bool = Field(True, description="Whether user account is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(..., min_length=8, description="User password")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password has at least one letter and one number."""
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern=r"^(employee|manager|admin)$")
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response data."""
    
    id: int = Field(..., description="User's unique ID")
    created_at: datetime = Field(..., description="When user was created")
    updated_at: datetime = Field(..., description="When user was last updated")
    
    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login credentials."""
    
    username: str = Field(..., description="Username for login")
    password: str = Field(..., description="Password for login")


class UserPasswordChange(BaseModel):
    """Schema for changing user password."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password has at least one letter and one number."""
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v
