"""
PTO-related Pydantic schemas for the PTO and Market Calendar System.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PTORequestBase(BaseModel):
    """Base PTO request schema with common fields."""
    pto_type: str = Field(..., description="Type of PTO (vacation, sick, personal)")
    start_date: date = Field(..., description="Start date of PTO")
    end_date: date = Field(..., description="End date of PTO")
    total_days: Decimal = Field(..., ge=0, description="Total days requested")
    notes: Optional[str] = Field(None, description="Optional notes for the request")
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        """Validate that end_date is not before start_date."""
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('End date must be after or equal to start date')
        return v


class PTORequestCreate(PTORequestBase):
    """Schema for creating a new PTO request."""
    user_id: int = Field(..., description="ID of the user making the request")


class PTOBalanceUpdate(BaseModel):
    """Schema for updating PTO balance totals."""
    vacation_total: Optional[Decimal] = Field(None, ge=0, description="Total vacation days allocated")
    sick_total: Optional[Decimal] = Field(None, ge=0, description="Total sick days allocated")
    personal_total: Optional[Decimal] = Field(None, ge=0, description="Total personal days allocated")
    remote_weekly_used: Optional[int] = Field(None, ge=0, description="Remote work days used this week")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
