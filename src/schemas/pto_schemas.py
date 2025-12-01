"""
PTO-related Pydantic schemas for the PTO and Market Calendar System.
"""
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class PTOBalanceUpdate(BaseModel):
    """Schema for updating PTO balance totals."""
    vacation_total: Optional[Decimal] = Field(None, ge=0, description="Total vacation days allocated")
    sick_total: Optional[Decimal] = Field(None, ge=0, description="Total sick days allocated")
    personal_total: Optional[Decimal] = Field(None, ge=0, description="Total personal days allocated")
    remote_weekly_used: Optional[int] = Field(None, ge=0, description="Remote work days used this week")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
