"""PTO-related Pydantic schemas for request/response validation."""

from datetime import datetime, date
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PTORequestBase(BaseModel):
    """Base PTO request schema with common fields."""
    
    pto_type: str = Field(..., pattern=r"^(vacation|sick|personal|remote)$", description="Type of PTO request")
    start_date: date = Field(..., description="Start date of PTO")
    end_date: date = Field(..., description="End date of PTO")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes for the request")
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        """Validate end_date is not before start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('End date cannot be before start date')
        return v


class PTORequestCreate(PTORequestBase):
    """Schema for creating a new PTO request."""
    
    user_id: int = Field(..., description="ID of user making the request")
    total_days: Decimal = Field(..., ge=0, description="Total days requested")


class PTORequestUpdate(BaseModel):
    """Schema for updating PTO request information."""
    
    notes: Optional[str] = Field(None, max_length=500, description="Updated notes for the request")


class PTORequestApprove(BaseModel):
    """Schema for approving a PTO request."""
    
    approved_by: int = Field(..., description="ID of user approving the request")


class PTORequestDeny(BaseModel):
    """Schema for denying a PTO request."""
    
    approved_by: int = Field(..., description="ID of user denying the request")
    denial_reason: str = Field(..., min_length=10, max_length=500, description="Reason for denial")


class PTORequestResponse(PTORequestBase):
    """Schema for PTO request response data."""
    
    id: int = Field(..., description="Request's unique ID")
    user_id: int = Field(..., description="ID of user who made the request")
    total_days: Decimal = Field(..., description="Total days requested")
    status: str = Field(..., description="Current status of the request")
    approved_by: Optional[int] = Field(None, description="ID of user who approved/denied")
    denial_reason: Optional[str] = Field(None, description="Reason for denial if applicable")
    submitted_at: datetime = Field(..., description="When request was submitted")
    approved_at: Optional[datetime] = Field(None, description="When request was approved/denied")
    created_at: datetime = Field(..., description="When request was created")
    updated_at: datetime = Field(..., description="When request was last updated")
    
    model_config = {"from_attributes": True}


class PTOBalanceBase(BaseModel):
    """Base PTO balance schema with common fields."""
    
    year: int = Field(..., ge=2020, le=2100, description="Year for PTO balance")
    vacation_total: Decimal = Field(Decimal('0.00'), ge=0, description="Total vacation days allocated")
    sick_total: Decimal = Field(Decimal('0.00'), ge=0, description="Total sick days allocated")
    personal_total: Decimal = Field(Decimal('0.00'), ge=0, description="Total personal days allocated")


class PTOBalanceCreate(PTOBalanceBase):
    """Schema for creating a new PTO balance record."""
    
    user_id: int = Field(..., description="ID of user for this balance")


class PTOBalanceUpdate(BaseModel):
    """Schema for updating PTO balance information."""
    
    vacation_total: Optional[Decimal] = Field(None, ge=0, description="Updated vacation total")
    sick_total: Optional[Decimal] = Field(None, ge=0, description="Updated sick total")
    personal_total: Optional[Decimal] = Field(None, ge=0, description="Updated personal total")


class PTOBalanceResponse(PTOBalanceBase):
    """Schema for PTO balance response data."""
    
    id: int = Field(..., description="Balance record's unique ID")
    user_id: int = Field(..., description="ID of user for this balance")
    vacation_used: Decimal = Field(..., description="Vacation days used")
    vacation_pending: Decimal = Field(..., description="Vacation days pending approval")
    vacation_available: Decimal = Field(..., description="Vacation days available")
    sick_used: Decimal = Field(..., description="Sick days used")
    sick_available: Decimal = Field(..., description="Sick days available")
    personal_used: Decimal = Field(..., description="Personal days used")
    personal_available: Decimal = Field(..., description="Personal days available")
    remote_weekly_used: Decimal = Field(..., description="Remote days used this week")
    created_at: datetime = Field(..., description="When balance record was created")
    updated_at: datetime = Field(..., description="When balance record was last updated")
    
    model_config = {"from_attributes": True}
