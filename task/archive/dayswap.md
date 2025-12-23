# WFH Day Swap Feature - Implementation Guide

## Overview

This document provides complete instructions for implementing a **WFH (Work From Home) Day Swap** feature in the PTO Central application. This feature allows employees to swap their designated WFH days with teammates, with full messaging support, manager visibility, and audit logging.

**Target Application**: PTO Central (NiceGUI + FastAPI + SQLAlchemy + SQLite)

---

## Table of Contents

1. [Business Requirements](#1-business-requirements)
2. [Employee Reference Data](#2-employee-reference-data)
3. [Database Models](#3-database-models)
4. [Alembic Migrations](#4-alembic-migrations)
5. [Service Layer](#5-service-layer)
6. [UI Components](#6-ui-components)
7. [Notification Integration](#7-notification-integration)
8. [Manager Reporting](#8-manager-reporting)
9. [Admin Configuration](#9-admin-configuration)
10. [Help Documentation & UI Help Buttons](#10-help-documentation--ui-help-buttons)
11. [Testing Scenarios](#11-testing-scenarios)
12. [Testing Checklist](#12-testing-checklist)
13. [Future Expansion](#13-future-expansion)

---

## 1. Business Requirements

### Core Functionality

1. **Employee initiates swap request**
   - Employee selects a date they want to work from home (not their normal WFH day)
   - System shows which employees have that day as their WFH day
   - Employee selects one person and writes a **required message** explaining the reason
   - Request is created with status `pending`

2. **Target employee receives request**
   - Notification appears on their dashboard
   - Email notification sent (using existing email service)
   - They can view the requester's message

3. **Target employee responds**
   - Can **Accept** or **Decline**
   - **Must provide a response message** (required for both actions)
   - Response message is visible to the requester

4. **Requester sees updated status**
   - Dashboard shows request status (Pending → Accepted/Declined)
   - Response message from target is displayed
   - Timestamp of response shown

5. **Manager visibility**
   - Completed swaps appear in manager's existing reports (weekly/bi-weekly/monthly)
   - Audit log entry created for all swap actions
   - Optional: Team Calendar shows swap indicator

### Business Rules

| Rule | Value |
|------|-------|
| Request message | **Required** |
| Response message | **Required** (both accept and decline) |
| Auto-expiration | 3 business days |
| Multiple pending requests | One active request per swap date per requester |
| Swap window | Current week + next 2 weeks |
| Manager approval | Not required (employee-to-employee) |

---

## 2. Employee Reference Data

### Work Schedules

| Employee | User ID | Start Time | End Time | WFH Day | Location |
|----------|---------|------------|----------|---------|----------|
| Employee A | (lookup) | 07:00 | 15:00 | Friday | Chicago |
| Employee B | (lookup) | 07:30 | 15:30 | Friday | Chicago |
| Employee C | (lookup) | 08:00 | 16:00 | Wednesday | Chicago |
| Employee D | (lookup) | 09:00 | 17:00 | Monday | Chicago |
| Employee E | (lookup) | 06:00 | 14:00 | Thursday | Chicago |
| Employee F | (lookup) | 08:00 | 16:00 | Tuesday | Chicago |
| Employee G | (lookup) | 07:00 | 15:00 | Wednesday | Chicago |

### WFH Day Distribution

| Day | Employees WFH | Count |
|-----|---------------|-------|
| Monday | Employee D | 1 |
| Tuesday | Employee F | 1 |
| Wednesday | Employee G, Employee C | 2 |
| Thursday | Employee E | 1 |
| Friday | Employee B, Employee A | 2 |

**Note**: The `remote_schedule` JSON field already exists on the User model. Verify these values match the database before proceeding.

---

## 3. Database Models

### 3.1 New Model: WFHDaySwapRequest

**File**: `src/models/wfh_day_swap.py`

```python
"""
WFH Day Swap Request model for the PTO and Market Calendar System.
"""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Integer, String, Text, Date, DateTime, Boolean, 
    ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class SwapStatus(enum.Enum):
    """Status values for WFH day swap requests."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class WFHDaySwapRequest(Base):
    """
    WFH Day Swap Request model for tracking employee WFH day exchanges.
    
    Allows employees to swap their designated WFH days with teammates,
    with full messaging support and audit trail.
    """
    __tablename__ = "wfh_day_swap_requests"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Participants
    requester_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True,
        comment="Employee initiating the swap request"
    )
    target_user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True,
        comment="Employee being asked to swap"
    )
    
    # Swap details
    swap_date: Mapped[date] = mapped_column(
        Date, 
        nullable=False, 
        index=True,
        comment="The date for which the swap is requested"
    )
    requester_original_day: Mapped[str] = mapped_column(
        String(10), 
        nullable=False,
        comment="Requester's normal WFH day (monday, tuesday, etc.)"
    )
    target_original_day: Mapped[str] = mapped_column(
        String(10), 
        nullable=False,
        comment="Target's normal WFH day (the day requester wants)"
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="pending",
        index=True,
        comment="pending, accepted, declined, cancelled, expired"
    )
    
    # Bidirectional messaging
    request_message: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="Required message from requester explaining the swap need"
    )
    response_message: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Response message from target (required on accept/decline)"
    )
    
    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.now,
        index=True
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True,
        comment="Auto-expiration datetime (3 business days from request)"
    )
    
    # ----- FUTURE EXPANSION FIELDS (nullable for now) -----
    
    # Multi-department support
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
        index=True,
        comment="Department ID for cross-dept reporting (future)"
    )
    
    # Manager approval workflow (future)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="If true, manager must approve after employee accepts"
    )
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="Manager who approved (if requires_approval=True)"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Recurring swaps (future)
    swap_type: Mapped[str] = mapped_column(
        String(20),
        default="one_time",
        nullable=False,
        comment="one_time or recurring (future feature)"
    )
    
    # Coverage override (future)
    coverage_override: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Manager override of coverage warning (future)"
    )
    
    # Soft archive
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Soft archive timestamp for old records"
    )
    
    # ----- RELATIONSHIPS -----
    
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
        backref="swap_requests_made"
    )
    target_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[target_user_id],
        backref="swap_requests_received"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    
    # ----- INDEXES FOR PERFORMANCE -----
    
    __table_args__ = (
        Index('idx_swap_date_status', 'swap_date', 'status'),
        Index('idx_requester_status', 'requester_id', 'status'),
        Index('idx_target_status', 'target_user_id', 'status'),
        Index('idx_requested_at', 'requested_at'),
        Index('idx_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<WFHDaySwapRequest(id={self.id}, "
            f"requester={self.requester_id}, target={self.target_user_id}, "
            f"date={self.swap_date}, status='{self.status}')>"
        )
    
    @property
    def is_pending(self) -> bool:
        return self.status == "pending"
    
    @property
    def is_accepted(self) -> bool:
        return self.status == "accepted"
    
    @property
    def is_declined(self) -> bool:
        return self.status == "declined"
    
    @property
    def is_expired(self) -> bool:
        return self.status == "expired"
    
    @property
    def can_respond(self) -> bool:
        """Check if the request can still be responded to."""
        if self.status != "pending":
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True
```

### 3.2 New Model: EmployeeWorkSchedule

**File**: `src/models/employee_work_schedule.py`

```python
"""
Employee Work Schedule model for tracking work hours.
"""
from datetime import datetime, time
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Time, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from .user import User


class EmployeeWorkSchedule(Base):
    """
    Employee Work Schedule model for tracking daily work hours.
    
    Stores start/end times for each employee, supporting future
    features like coverage analysis and time zone handling.
    """
    __tablename__ = "employee_work_schedules"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Employee reference
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        unique=True,  # One active schedule per user
        comment="Employee this schedule belongs to"
    )
    
    # Work hours
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Daily start time (e.g., 08:00)"
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        comment="Daily end time (e.g., 16:00)"
    )
    
    # ----- FUTURE EXPANSION FIELDS -----
    
    # Flexible scheduling (future)
    schedule_type: Mapped[str] = mapped_column(
        String(20),
        default="fixed",
        nullable=False,
        comment="fixed, flexible, or rotating (future)"
    )
    
    # Effective dating for schedule changes
    effective_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When this schedule became effective"
    )
    
    # Time zone support (future)
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Timezone identifier (e.g., America/Chicago)"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", backref="work_schedule")
    
    def __repr__(self) -> str:
        return (
            f"<EmployeeWorkSchedule(user_id={self.user_id}, "
            f"start={self.start_time}, end={self.end_time})>"
        )
    
    @property
    def hours_per_day(self) -> float:
        """Calculate hours worked per day."""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return (end_minutes - start_minutes) / 60
```

### 3.3 Update Models __init__.py

**File**: `src/models/__init__.py`

Add these imports:

```python
from .wfh_day_swap import WFHDaySwapRequest, SwapStatus
from .employee_work_schedule import EmployeeWorkSchedule

# Update __all__ list
__all__ = [
    # ... existing models ...
    'WFHDaySwapRequest',
    'SwapStatus',
    'EmployeeWorkSchedule',
]
```

### 3.4 Update User Model - Add Email Notification Preference

**File**: `src/models/user.py`

Add this field to the existing User model (after the `is_trusted` fields):

```python
# Email notification preferences
wfh_swap_emails_enabled: Mapped[bool] = mapped_column(
    Boolean,
    default=True,
    nullable=False,
    comment="If false, user won't receive WFH swap email notifications (still creates audit entries)"
)
```

**Full context - add after the trusted employee fields:**

```python
class User(Base):
    # ... existing fields ...
    
    # Trusted employee designation (auto-approve standard PTO)
    is_trusted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="If true, vacation/sick/personal auto-approve"
    )
    trusted_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="Manager who granted trust"
    )
    trusted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When trust was granted"
    )
    
    # ADD THIS NEW FIELD:
    # Email notification preferences
    wfh_swap_emails_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="If false, user won't receive WFH swap email notifications (still creates audit entries)"
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        # ... rest of model ...
    )
```

---

## 4. Alembic Migrations

### 4.1 Create Migration for WFH Day Swap

**Command**: `alembic revision -m "add_wfh_day_swap_tables"`

**Migration file content**:

```python
"""add_wfh_day_swap_tables

Revision ID: [auto-generated]
Revises: [previous_revision]
Create Date: [auto-generated]
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '[auto-generated]'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create employee_work_schedules table
    op.create_table(
        'employee_work_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('schedule_type', sa.String(20), nullable=False, server_default='fixed'),
        sa.Column('effective_date', sa.DateTime(), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_employee_work_schedules_user_id', 'employee_work_schedules', ['user_id'], unique=True)
    
    # Create wfh_day_swap_requests table
    op.create_table(
        'wfh_day_swap_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('swap_date', sa.Date(), nullable=False),
        sa.Column('requester_original_day', sa.String(10), nullable=False),
        sa.Column('target_original_day', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('request_message', sa.Text(), nullable=False),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        # Future expansion fields
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('swap_type', sa.String(20), nullable=False, server_default='one_time'),
        sa.Column('coverage_override', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_wfh_swap_requester_id', 'wfh_day_swap_requests', ['requester_id'])
    op.create_index('ix_wfh_swap_target_user_id', 'wfh_day_swap_requests', ['target_user_id'])
    op.create_index('ix_wfh_swap_swap_date', 'wfh_day_swap_requests', ['swap_date'])
    op.create_index('ix_wfh_swap_status', 'wfh_day_swap_requests', ['status'])
    op.create_index('ix_wfh_swap_requested_at', 'wfh_day_swap_requests', ['requested_at'])
    op.create_index('idx_swap_date_status', 'wfh_day_swap_requests', ['swap_date', 'status'])
    op.create_index('idx_requester_status', 'wfh_day_swap_requests', ['requester_id', 'status'])
    op.create_index('idx_target_status', 'wfh_day_swap_requests', ['target_user_id', 'status'])


def downgrade() -> None:
    op.drop_table('wfh_day_swap_requests')
    op.drop_table('employee_work_schedules')
```

### 4.2 Add Migration for User Email Preference Field

**Command**: `alembic revision -m "add_wfh_swap_email_preference_to_users"`

**Migration file content**:

```python
"""add_wfh_swap_email_preference_to_users

Revision ID: [auto-generated]
Revises: [previous_revision - the wfh_day_swap_tables migration]
Create Date: [auto-generated]
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '[auto-generated]'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add wfh_swap_emails_enabled column to users table
    # Default to True so existing users continue receiving emails
    op.add_column(
        'users',
        sa.Column(
            'wfh_swap_emails_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='1',
            comment='If false, user won\'t receive WFH swap email notifications'
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'wfh_swap_emails_enabled')
```

### 4.3 Data Migration: Populate Work Schedules

After running the schema migration, create a data migration or script to populate initial work schedules:

```python
"""
Script to populate initial employee work schedules.
Run after migration: python scripts/populate_work_schedules.py
"""
from datetime import time
from src.database import get_db
from src.models.user import User
from src.models.employee_work_schedule import EmployeeWorkSchedule

# Employee schedule data
SCHEDULES = {
    'daryn': {'start': time(7, 0), 'end': time(15, 0)},
    'jose': {'start': time(7, 30), 'end': time(15, 30)},
    'johnny': {'start': time(8, 0), 'end': time(16, 0)},
    'omil': {'start': time(9, 0), 'end': time(17, 0)},
    'brad': {'start': time(6, 0), 'end': time(14, 0)},
    'miguel': {'start': time(8, 0), 'end': time(16, 0)},
    'matt': {'start': time(7, 0), 'end': time(15, 0)},
}

def populate_schedules():
    db = next(get_db())
    try:
        for first_name_lower, schedule in SCHEDULES.items():
            # Find user by first name (case-insensitive)
            user = db.query(User).filter(
                User.first_name.ilike(f'{first_name_lower}%')
            ).first()
            
            if user:
                # Check if schedule already exists
                existing = db.query(EmployeeWorkSchedule).filter(
                    EmployeeWorkSchedule.user_id == user.id
                ).first()
                
                if not existing:
                    work_schedule = EmployeeWorkSchedule(
                        user_id=user.id,
                        start_time=schedule['start'],
                        end_time=schedule['end'],
                        schedule_type='fixed',
                        is_active=True
                    )
                    db.add(work_schedule)
                    print(f"Added schedule for {user.full_name}")
                else:
                    print(f"Schedule already exists for {user.full_name}")
            else:
                print(f"User not found: {first_name_lower}")
        
        db.commit()
        print("Work schedules populated successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    populate_schedules()
```

---

## 5. Service Layer

### 5.1 WFH Swap Service

**File**: `src/services/wfh_swap_service.py`

```python
"""
WFH Day Swap service for managing employee WFH day exchanges.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.user import User
from src.models.wfh_day_swap import WFHDaySwapRequest
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Days of the week mapping
DAYS_OF_WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']


class WFHSwapService:
    """Service for managing WFH day swap requests."""
    
    # Configuration (could be moved to SystemSettings in future)
    EXPIRY_BUSINESS_DAYS = 3
    MAX_FUTURE_DAYS = 21  # 3 weeks ahead
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== CORE OPERATIONS ====================
    
    def create_swap_request(
        self,
        requester_id: int,
        target_user_id: int,
        swap_date: date,
        request_message: str
    ) -> WFHDaySwapRequest:
        """
        Create a new WFH day swap request.
        
        Args:
            requester_id: ID of employee initiating the swap
            target_user_id: ID of employee being asked to swap
            swap_date: The date for the swap
            request_message: Required message explaining the swap need
            
        Returns:
            Created WFHDaySwapRequest
            
        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        if not request_message or not request_message.strip():
            raise ValueError("A message explaining the swap request is required.")
        
        # Get both users
        requester = self.db.query(User).filter(User.id == requester_id).first()
        target = self.db.query(User).filter(User.id == target_user_id).first()
        
        if not requester or not target:
            raise ValueError("Invalid user IDs provided.")
        
        if requester_id == target_user_id:
            raise ValueError("Cannot swap with yourself.")
        
        # Validate swap_date is not in the past
        if swap_date < date.today():
            raise ValueError("Cannot request swap for a past date.")
        
        # Validate swap_date is within allowed window
        max_date = date.today() + timedelta(days=self.MAX_FUTURE_DAYS)
        if swap_date > max_date:
            raise ValueError(f"Swap date must be within {self.MAX_FUTURE_DAYS} days.")
        
        # Validate swap_date is a weekday
        if swap_date.weekday() >= 5:
            raise ValueError("Swap date must be a weekday (Monday-Friday).")
        
        # Get WFH days from remote_schedule JSON
        requester_wfh_day = self._get_wfh_day(requester)
        target_wfh_day = self._get_wfh_day(target)
        
        if not requester_wfh_day:
            raise ValueError(f"{requester.full_name} does not have a WFH day configured.")
        
        if not target_wfh_day:
            raise ValueError(f"{target.full_name} does not have a WFH day configured.")
        
        # Validate the swap_date matches target's WFH day
        swap_day_name = DAYS_OF_WEEK[swap_date.weekday()]
        if swap_day_name != target_wfh_day:
            raise ValueError(
                f"{target.full_name}'s WFH day is {target_wfh_day.title()}, "
                f"but {swap_date.strftime('%A')} was selected."
            )
        
        # Check for existing pending request from this requester for same date
        existing = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.requester_id == requester_id,
            WFHDaySwapRequest.swap_date == swap_date,
            WFHDaySwapRequest.status == 'pending'
        ).first()
        
        if existing:
            raise ValueError(
                f"You already have a pending swap request for {swap_date.strftime('%B %d, %Y')}."
            )
        
        # Calculate expiration (3 business days)
        expires_at = self._calculate_expiry(datetime.now())
        
        # Create the request
        swap_request = WFHDaySwapRequest(
            requester_id=requester_id,
            target_user_id=target_user_id,
            swap_date=swap_date,
            requester_original_day=requester_wfh_day,
            target_original_day=target_wfh_day,
            status='pending',
            request_message=request_message.strip(),
            requested_at=datetime.now(),
            expires_at=expires_at,
            department_id=requester.department_id  # For future reporting
        )
        
        self.db.add(swap_request)
        self.db.commit()
        self.db.refresh(swap_request)
        
        # Audit log
        AuditService.log(
            db=self.db,
            action='wfh_swap_requested',
            user_id=requester_id,
            username=requester.username,
            entity_type='wfh_swap_request',
            entity_id=swap_request.id,
            details={
                'target_user': target.full_name,
                'swap_date': swap_date.isoformat(),
                'requester_day': requester_wfh_day,
                'target_day': target_wfh_day
            }
        )
        
        logger.info(
            f"WFH swap request created: {requester.full_name} -> {target.full_name} "
            f"for {swap_date.isoformat()}"
        )
        
        return swap_request
    
    def accept_swap(
        self,
        swap_id: int,
        response_message: str,
        responder_id: int
    ) -> WFHDaySwapRequest:
        """
        Accept a WFH day swap request.
        
        Args:
            swap_id: ID of the swap request
            response_message: Required response message
            responder_id: ID of user accepting (must be target_user_id)
            
        Returns:
            Updated WFHDaySwapRequest
        """
        swap_request = self._get_and_validate_response(
            swap_id, responder_id, response_message
        )
        
        swap_request.status = 'accepted'
        swap_request.response_message = response_message.strip()
        swap_request.responded_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(swap_request)
        
        # Audit log
        responder = self.db.query(User).filter(User.id == responder_id).first()
        requester = self.db.query(User).filter(User.id == swap_request.requester_id).first()
        
        AuditService.log(
            db=self.db,
            action='wfh_swap_accepted',
            user_id=responder_id,
            username=responder.username if responder else None,
            entity_type='wfh_swap_request',
            entity_id=swap_id,
            details={
                'requester': requester.full_name if requester else None,
                'target': responder.full_name if responder else None,
                'swap_date': swap_request.swap_date.isoformat(),
                'requester_day': swap_request.requester_original_day,
                'target_day': swap_request.target_original_day
            }
        )
        
        logger.info(f"WFH swap accepted: Request #{swap_id}")
        
        return swap_request
    
    def decline_swap(
        self,
        swap_id: int,
        response_message: str,
        responder_id: int
    ) -> WFHDaySwapRequest:
        """
        Decline a WFH day swap request.
        
        Args:
            swap_id: ID of the swap request
            response_message: Required response message
            responder_id: ID of user declining (must be target_user_id)
            
        Returns:
            Updated WFHDaySwapRequest
        """
        swap_request = self._get_and_validate_response(
            swap_id, responder_id, response_message
        )
        
        swap_request.status = 'declined'
        swap_request.response_message = response_message.strip()
        swap_request.responded_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(swap_request)
        
        # Audit log
        responder = self.db.query(User).filter(User.id == responder_id).first()
        requester = self.db.query(User).filter(User.id == swap_request.requester_id).first()
        
        AuditService.log(
            db=self.db,
            action='wfh_swap_declined',
            user_id=responder_id,
            username=responder.username if responder else None,
            entity_type='wfh_swap_request',
            entity_id=swap_id,
            details={
                'requester': requester.full_name if requester else None,
                'swap_date': swap_request.swap_date.isoformat()
            }
        )
        
        logger.info(f"WFH swap declined: Request #{swap_id}")
        
        return swap_request
    
    def cancel_swap(self, swap_id: int, user_id: int) -> WFHDaySwapRequest:
        """
        Cancel a pending swap request (by requester only).
        
        Args:
            swap_id: ID of the swap request
            user_id: ID of user cancelling (must be requester)
            
        Returns:
            Updated WFHDaySwapRequest
        """
        swap_request = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.id == swap_id
        ).first()
        
        if not swap_request:
            raise ValueError("Swap request not found.")
        
        if swap_request.requester_id != user_id:
            raise ValueError("Only the requester can cancel this request.")
        
        if swap_request.status != 'pending':
            raise ValueError("Can only cancel pending requests.")
        
        swap_request.status = 'cancelled'
        swap_request.responded_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(swap_request)
        
        # Audit log
        user = self.db.query(User).filter(User.id == user_id).first()
        AuditService.log(
            db=self.db,
            action='wfh_swap_cancelled',
            user_id=user_id,
            username=user.username if user else None,
            entity_type='wfh_swap_request',
            entity_id=swap_id,
            details={'swap_date': swap_request.swap_date.isoformat()}
        )
        
        logger.info(f"WFH swap cancelled: Request #{swap_id}")
        
        return swap_request
    
    # ==================== QUERY METHODS ====================
    
    def get_swap_by_id(self, swap_id: int) -> Optional[WFHDaySwapRequest]:
        """Get a swap request by ID."""
        return self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.id == swap_id
        ).first()
    
    def get_pending_requests_for_user(self, user_id: int) -> List[WFHDaySwapRequest]:
        """
        Get all pending swap requests where user is the target.
        These are requests the user needs to respond to.
        """
        return self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.target_user_id == user_id,
            WFHDaySwapRequest.status == 'pending'
        ).order_by(WFHDaySwapRequest.requested_at.desc()).all()
    
    def get_my_swap_requests(self, user_id: int, include_archived: bool = False) -> List[WFHDaySwapRequest]:
        """
        Get all swap requests initiated by this user.
        """
        query = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.requester_id == user_id
        )
        
        if not include_archived:
            query = query.filter(WFHDaySwapRequest.archived_at.is_(None))
        
        return query.order_by(WFHDaySwapRequest.requested_at.desc()).all()
    
    def get_available_swap_targets(
        self,
        swap_date: date,
        requester_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of employees who work from home on the given date.
        
        Args:
            swap_date: The date to check
            requester_id: ID of requester (to exclude)
            
        Returns:
            List of dicts with user info: [{id, name, wfh_day}]
        """
        # Validate date is a weekday
        if swap_date.weekday() >= 5:
            return []
        
        day_name = DAYS_OF_WEEK[swap_date.weekday()]
        
        # Get all active users except requester
        users = self.db.query(User).filter(
            User.is_active == True,
            User.id != requester_id
        ).all()
        
        targets = []
        for user in users:
            wfh_day = self._get_wfh_day(user)
            if wfh_day == day_name:
                targets.append({
                    'id': user.id,
                    'name': user.full_name,
                    'wfh_day': wfh_day.title()
                })
        
        return targets
    
    def get_swap_history(
        self,
        user_id: int,
        limit: int = 50,
        include_all_involvement: bool = True
    ) -> List[WFHDaySwapRequest]:
        """
        Get swap history for a user (as requester or target).
        
        Args:
            user_id: User ID
            limit: Max records to return
            include_all_involvement: If True, include requests where user was target
            
        Returns:
            List of swap requests
        """
        if include_all_involvement:
            query = self.db.query(WFHDaySwapRequest).filter(
                or_(
                    WFHDaySwapRequest.requester_id == user_id,
                    WFHDaySwapRequest.target_user_id == user_id
                )
            )
        else:
            query = self.db.query(WFHDaySwapRequest).filter(
                WFHDaySwapRequest.requester_id == user_id
            )
        
        return query.order_by(
            WFHDaySwapRequest.requested_at.desc()
        ).limit(limit).all()
    
    def get_swaps_for_date(self, swap_date: date) -> List[WFHDaySwapRequest]:
        """Get all accepted swaps for a specific date."""
        return self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.swap_date == swap_date,
            WFHDaySwapRequest.status == 'accepted'
        ).all()
    
    # ==================== MANAGER/ADMIN METHODS ====================
    
    def get_swaps_by_department(
        self,
        department_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None
    ) -> List[WFHDaySwapRequest]:
        """
        Get swap requests for a department (for manager reporting).
        """
        query = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.department_id == department_id
        )
        
        if start_date:
            query = query.filter(WFHDaySwapRequest.swap_date >= start_date)
        if end_date:
            query = query.filter(WFHDaySwapRequest.swap_date <= end_date)
        if status:
            query = query.filter(WFHDaySwapRequest.status == status)
        
        return query.order_by(WFHDaySwapRequest.swap_date.desc()).all()
    
    def get_all_swaps(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[WFHDaySwapRequest]:
        """
        Get all swap requests (for admin reporting).
        """
        query = self.db.query(WFHDaySwapRequest)
        
        if start_date:
            query = query.filter(WFHDaySwapRequest.swap_date >= start_date)
        if end_date:
            query = query.filter(WFHDaySwapRequest.swap_date <= end_date)
        if status:
            query = query.filter(WFHDaySwapRequest.status == status)
        
        return query.order_by(
            WFHDaySwapRequest.requested_at.desc()
        ).limit(limit).all()
    
    def expire_stale_requests(self) -> int:
        """
        Expire pending requests that have passed their expiration date.
        Should be called by a scheduled job.
        
        Returns:
            Number of requests expired
        """
        now = datetime.now()
        
        stale_requests = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.status == 'pending',
            WFHDaySwapRequest.expires_at < now
        ).all()
        
        count = 0
        for request in stale_requests:
            request.status = 'expired'
            request.responded_at = now
            count += 1
            
            # Audit log
            AuditService.log(
                db=self.db,
                action='wfh_swap_expired',
                entity_type='wfh_swap_request',
                entity_id=request.id,
                details={
                    'swap_date': request.swap_date.isoformat(),
                    'expired_at': now.isoformat()
                }
            )
        
        if count > 0:
            self.db.commit()
            logger.info(f"Expired {count} stale WFH swap requests")
        
        return count
    
    # ==================== COVERAGE ANALYSIS ====================
    
    def get_daily_wfh_status(self, check_date: date) -> Dict[str, Any]:
        """
        Get WFH status for all employees on a given date.
        Considers both regular WFH schedules and accepted swaps.
        
        Returns:
            {
                'date': date,
                'in_office': [{'id': x, 'name': 'y'}, ...],
                'wfh': [{'id': x, 'name': 'y', 'is_swap': bool}, ...],
                'coverage_count': int
            }
        """
        if check_date.weekday() >= 5:
            return {
                'date': check_date,
                'in_office': [],
                'wfh': [],
                'coverage_count': 0,
                'is_weekend': True
            }
        
        day_name = DAYS_OF_WEEK[check_date.weekday()]
        
        # Get accepted swaps for this date
        accepted_swaps = self.get_swaps_for_date(check_date)
        swap_requester_ids = {s.requester_id for s in accepted_swaps}
        swap_target_ids = {s.target_user_id for s in accepted_swaps}
        
        # Get all active users
        users = self.db.query(User).filter(User.is_active == True).all()
        
        in_office = []
        wfh = []
        
        for user in users:
            regular_wfh_day = self._get_wfh_day(user)
            is_regular_wfh = (regular_wfh_day == day_name)
            
            # Check if affected by swap
            if user.id in swap_requester_ids:
                # Requester is WFH on target's day (swap gives them WFH)
                wfh.append({'id': user.id, 'name': user.full_name, 'is_swap': True})
            elif user.id in swap_target_ids:
                # Target gave away their WFH day, so they're in office
                in_office.append({'id': user.id, 'name': user.full_name, 'is_swap': True})
            elif is_regular_wfh:
                wfh.append({'id': user.id, 'name': user.full_name, 'is_swap': False})
            else:
                in_office.append({'id': user.id, 'name': user.full_name, 'is_swap': False})
        
        return {
            'date': check_date,
            'in_office': in_office,
            'wfh': wfh,
            'coverage_count': len(in_office),
            'is_weekend': False
        }
    
    # ==================== HELPER METHODS ====================
    
    def _get_wfh_day(self, user: User) -> Optional[str]:
        """
        Extract WFH day from user's remote_schedule JSON.
        
        The remote_schedule is stored as JSON string:
        {"monday": false, "tuesday": true, "wednesday": false, ...}
        
        Returns the day name (lowercase) where value is True, or None.
        """
        if not user.remote_schedule:
            return None
        
        try:
            # Handle both string and dict formats
            if isinstance(user.remote_schedule, str):
                schedule = json.loads(user.remote_schedule)
            else:
                schedule = user.remote_schedule
            
            for day in DAYS_OF_WEEK:
                if schedule.get(day, False):
                    return day
            
            return None
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _get_and_validate_response(
        self,
        swap_id: int,
        responder_id: int,
        response_message: str
    ) -> WFHDaySwapRequest:
        """Validate and return swap request for response operations."""
        if not response_message or not response_message.strip():
            raise ValueError("A response message is required.")
        
        swap_request = self.db.query(WFHDaySwapRequest).filter(
            WFHDaySwapRequest.id == swap_id
        ).first()
        
        if not swap_request:
            raise ValueError("Swap request not found.")
        
        if swap_request.target_user_id != responder_id:
            raise ValueError("Only the target employee can respond to this request.")
        
        if swap_request.status != 'pending':
            raise ValueError(f"This request has already been {swap_request.status}.")
        
        if swap_request.expires_at and datetime.now() > swap_request.expires_at:
            swap_request.status = 'expired'
            self.db.commit()
            raise ValueError("This request has expired.")
        
        return swap_request
    
    def _calculate_expiry(self, from_datetime: datetime) -> datetime:
        """Calculate expiration datetime (3 business days from now)."""
        business_days = 0
        current = from_datetime
        
        while business_days < self.EXPIRY_BUSINESS_DAYS:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday-Friday
                business_days += 1
        
        # Set to end of business day (5 PM)
        return current.replace(hour=17, minute=0, second=0, microsecond=0)
```

### 5.2 Add Audit Service Methods

**File**: `src/services/audit_service.py`

Add these static methods to the existing AuditService class:

```python
# Add to existing AuditService class

@staticmethod
def log_wfh_swap_request(
    db: Session,
    requester_id: int,
    requester_name: str,
    request_id: int,
    target_name: str,
    swap_date: str
):
    """Log a WFH swap request."""
    return AuditService.log(
        db=db,
        action='wfh_swap_requested',
        user_id=requester_id,
        username=requester_name,
        entity_type='wfh_swap_request',
        entity_id=request_id,
        details={'target': target_name, 'swap_date': swap_date}
    )

@staticmethod
def log_wfh_swap_accepted(
    db: Session,
    responder_id: int,
    responder_name: str,
    request_id: int,
    requester_name: str,
    swap_date: str
):
    """Log a WFH swap acceptance."""
    return AuditService.log(
        db=db,
        action='wfh_swap_accepted',
        user_id=responder_id,
        username=responder_name,
        entity_type='wfh_swap_request',
        entity_id=request_id,
        details={'requester': requester_name, 'swap_date': swap_date}
    )

@staticmethod
def log_wfh_swap_declined(
    db: Session,
    responder_id: int,
    responder_name: str,
    request_id: int,
    requester_name: str,
    swap_date: str
):
    """Log a WFH swap decline."""
    return AuditService.log(
        db=db,
        action='wfh_swap_declined',
        user_id=responder_id,
        username=responder_name,
        entity_type='wfh_swap_request',
        entity_id=request_id,
        details={'requester': requester_name, 'swap_date': swap_date}
    )
```

---

## 6. UI Components

### 6.1 Dashboard Integration

**File**: `nicegui_app/pages/dashboard.py`

Add the following sections to the employee dashboard. Insert after the existing PTO balance cards section.

#### 6.1.1 WFH Swap Card (for initiating swaps)

```python
# Add import at top of file
from src.services.wfh_swap_service import WFHSwapService
from src.models.wfh_day_swap import WFHDaySwapRequest

# Inside the dashboard function, after balance cards:

def render_wfh_swap_section():
    """Render the WFH day swap section on dashboard."""
    db = next(get_db())
    try:
        swap_service = WFHSwapService(db)
        
        # Get user's WFH day
        current_user = db.query(User).filter(User.id == user_id).first()
        wfh_day = swap_service._get_wfh_day(current_user)
        
        # Get pending requests TO this user (need response)
        incoming_requests = swap_service.get_pending_requests_for_user(user_id)
        
        # Get user's own swap requests (to show status)
        my_requests = swap_service.get_my_swap_requests(user_id)
        recent_my_requests = [r for r in my_requests if r.status != 'archived'][:5]
        
    finally:
        db.close()
    
    # ===== INCOMING SWAP REQUESTS (Need Response) =====
    if incoming_requests:
        with ui.card().classes('w-full p-4 mb-4 border-l-4 border-orange-500'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('swap_horiz', color='orange', size='md')
                ui.label(f'WFH Swap Requests ({len(incoming_requests)})').classes('text-lg font-semibold')
                ui.badge(f'{len(incoming_requests)} pending', color='orange')
            
            for request in incoming_requests:
                render_incoming_swap_request(request)
    
    # ===== MY SWAP REQUESTS (Status View) =====
    with ui.card().classes('w-full p-4 mb-4'):
        with ui.row().classes('items-center justify-between w-full mb-3'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('home_work', color='primary', size='md')
                ui.label('WFH Day Swap').classes('text-lg font-semibold')
            
            # Request new swap button
            ui.button(
                'Request Swap',
                icon='add',
                on_click=lambda: show_swap_request_dialog()
            ).props('outline dense').style('color: #c9a227')
        
        if wfh_day:
            ui.label(f'Your regular WFH day: {wfh_day.title()}').classes('text-sm opacity-70 mb-3')
        else:
            ui.label('No WFH day configured. Contact your administrator.').classes('text-sm text-red-500 mb-3')
        
        # Show recent swap requests
        if recent_my_requests:
            ui.separator().classes('my-3')
            ui.label('My Recent Swap Requests').classes('text-sm font-medium opacity-70 mb-2')
            
            for request in recent_my_requests:
                render_my_swap_request(request)
        else:
            ui.label('No swap requests yet.').classes('text-sm opacity-60')


def render_incoming_swap_request(request: WFHDaySwapRequest):
    """Render a single incoming swap request card."""
    db = next(get_db())
    try:
        requester = db.query(User).filter(User.id == request.requester_id).first()
        requester_name = requester.full_name if requester else 'Unknown'
    finally:
        db.close()
    
    with ui.card().classes('w-full p-3 mb-2 bg-orange-50 dark:bg-orange-900/20'):
        with ui.row().classes('items-start justify-between w-full'):
            with ui.column().classes('flex-1'):
                ui.label(f'{requester_name} wants to swap').classes('font-medium')
                ui.label(
                    f"Their {request.requester_original_day.title()} ↔ "
                    f"Your {request.target_original_day.title()} "
                    f"({request.swap_date.strftime('%b %d, %Y')})"
                ).classes('text-sm opacity-70')
                
                # Show requester's message
                with ui.expansion('View message', icon='message').classes('w-full mt-2'):
                    ui.label(f'"{request.request_message}"').classes('italic text-sm p-2 bg-white dark:bg-gray-800 rounded')
            
            with ui.row().classes('gap-2'):
                ui.button(
                    'Respond',
                    icon='reply',
                    on_click=lambda r=request: show_swap_response_dialog(r)
                ).props('dense').style('background-color: #c9a227; color: white;')


def render_my_swap_request(request: WFHDaySwapRequest):
    """Render a single outgoing swap request with status."""
    db = next(get_db())
    try:
        target = db.query(User).filter(User.id == request.target_user_id).first()
        target_name = target.full_name if target else 'Unknown'
    finally:
        db.close()
    
    # Status colors and icons
    status_config = {
        'pending': {'color': 'orange', 'icon': 'hourglass_empty', 'bg': 'bg-orange-50 dark:bg-orange-900/20'},
        'accepted': {'color': 'green', 'icon': 'check_circle', 'bg': 'bg-green-50 dark:bg-green-900/20'},
        'declined': {'color': 'red', 'icon': 'cancel', 'bg': 'bg-red-50 dark:bg-red-900/20'},
        'cancelled': {'color': 'gray', 'icon': 'block', 'bg': 'bg-gray-50 dark:bg-gray-900/20'},
        'expired': {'color': 'gray', 'icon': 'timer_off', 'bg': 'bg-gray-50 dark:bg-gray-900/20'},
    }
    
    config = status_config.get(request.status, status_config['pending'])
    
    with ui.card().classes(f'w-full p-3 mb-2 {config["bg"]}'):
        with ui.row().classes('items-start justify-between w-full'):
            with ui.column().classes('flex-1'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon(config['icon'], color=config['color'], size='sm')
                    ui.label(request.status.upper()).classes(f'text-xs font-bold text-{config["color"]}-600')
                
                ui.label(f'Swap with {target_name}').classes('font-medium')
                ui.label(
                    f"Your {request.requester_original_day.title()} ↔ "
                    f"Their {request.target_original_day.title()} "
                    f"({request.swap_date.strftime('%b %d, %Y')})"
                ).classes('text-sm opacity-70')
                
                # Show response message if available
                if request.response_message:
                    with ui.card().classes('mt-2 p-2 bg-white dark:bg-gray-800'):
                        ui.label(f'{target_name} responded:').classes('text-xs font-medium opacity-70')
                        ui.label(f'"{request.response_message}"').classes('italic text-sm')
                        if request.responded_at:
                            ui.label(
                                request.responded_at.strftime('%b %d at %I:%M %p')
                            ).classes('text-xs opacity-50 mt-1')
            
            # Cancel button for pending requests
            if request.status == 'pending':
                ui.button(
                    icon='close',
                    on_click=lambda r=request: cancel_swap_request(r.id)
                ).props('flat dense round size=sm').tooltip('Cancel request')
```

#### 6.1.2 Swap Request Dialog

```python
def show_swap_request_dialog():
    """Show dialog for creating a new WFH swap request."""
    
    # State for the dialog
    selected_date = {'value': None}
    selected_target = {'value': None}
    available_targets = {'list': []}
    
    with ui.dialog() as dialog, ui.card().classes('min-w-[500px] max-w-[600px] p-6'):
        ui.label('Request WFH Day Swap').classes('text-xl font-bold mb-4')
        
        db = next(get_db())
        try:
            swap_service = WFHSwapService(db)
            current_user = db.query(User).filter(User.id == user_id).first()
            my_wfh_day = swap_service._get_wfh_day(current_user)
        finally:
            db.close()
        
        if my_wfh_day:
            ui.label(f'Your regular WFH day: {my_wfh_day.title()}').classes('text-sm opacity-70 mb-4')
        
        # Date picker (next 3 weeks, weekdays only)
        ui.label('Which day do you need to work from home?').classes('font-medium mb-2')
        
        # Generate date options (next 3 weeks, weekdays, excluding user's WFH day)
        date_options = {}
        from datetime import timedelta
        today = date.today()
        for i in range(21):
            d = today + timedelta(days=i)
            if d.weekday() < 5:  # Weekday only
                day_name = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'][d.weekday()]
                if day_name != my_wfh_day:  # Exclude user's own WFH day
                    label = d.strftime('%A, %b %d')
                    date_options[d.isoformat()] = label
        
        date_select = ui.select(
            date_options,
            label='Select Date',
            with_input=True
        ).props('outlined').classes('w-full mb-4')
        
        # Target employee container (populated after date selection)
        target_container = ui.column().classes('w-full')
        
        # Message input
        ui.label('Message (required)').classes('font-medium mb-2')
        ui.label('Explain why you need this swap').classes('text-xs opacity-60 mb-1')
        message_input = ui.textarea(
            placeholder='e.g., I have a doctor appointment on Wednesday and need to be home that day...'
        ).props('outlined autogrow').classes('w-full mb-4')
        
        # Error display
        error_label = ui.label('').classes('text-red-500 text-sm mb-2')
        error_label.set_visibility(False)
        
        def on_date_change(e):
            """Update available targets when date changes."""
            target_container.clear()
            selected_target['value'] = None
            
            if not e.value:
                return
            
            selected_date['value'] = date.fromisoformat(e.value)
            
            db = next(get_db())
            try:
                swap_service = WFHSwapService(db)
                targets = swap_service.get_available_swap_targets(
                    selected_date['value'],
                    user_id
                )
                available_targets['list'] = targets
            finally:
                db.close()
            
            with target_container:
                if targets:
                    day_name = selected_date['value'].strftime('%A')
                    ui.label(f'Employees who WFH on {day_name}:').classes('font-medium mb-2')
                    
                    target_options = {t['id']: t['name'] for t in targets}
                    target_select = ui.select(
                        target_options,
                        label='Select Employee',
                        with_input=True
                    ).props('outlined').classes('w-full')
                    
                    def on_target_change(ev):
                        selected_target['value'] = ev.value
                    
                    target_select.on('update:model-value', on_target_change)
                else:
                    ui.label(
                        f'No employees have {selected_date["value"].strftime("%A")} as their WFH day.'
                    ).classes('text-orange-500')
        
        date_select.on('update:model-value', on_date_change)
        
        def submit_request():
            """Submit the swap request."""
            error_label.set_visibility(False)
            
            # Validation
            if not selected_date['value']:
                error_label.text = 'Please select a date.'
                error_label.set_visibility(True)
                return
            
            if not selected_target['value']:
                error_label.text = 'Please select an employee to swap with.'
                error_label.set_visibility(True)
                return
            
            if not message_input.value or not message_input.value.strip():
                error_label.text = 'Please provide a message explaining the swap request.'
                error_label.set_visibility(True)
                return
            
            db = next(get_db())
            try:
                swap_service = WFHSwapService(db)
                swap_service.create_swap_request(
                    requester_id=user_id,
                    target_user_id=selected_target['value'],
                    swap_date=selected_date['value'],
                    request_message=message_input.value.strip()
                )
                db.commit()
                
                dialog.close()
                show_success_dialog(
                    'Request Sent',
                    'Your swap request has been sent. You will be notified when they respond.'
                )
                # Refresh dashboard
                ui.navigate.to('/dashboard')
                
            except ValueError as e:
                error_label.text = str(e)
                error_label.set_visibility(True)
            except Exception as e:
                error_label.text = f'Error: {str(e)}'
                error_label.set_visibility(True)
            finally:
                db.close()
        
        # Action buttons
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancel', on_click=dialog.close).props('flat')
            ui.button(
                'Send Request',
                icon='send',
                on_click=submit_request
            ).style('background-color: #c9a227; color: white;')
    
    dialog.open()


def show_swap_response_dialog(request: WFHDaySwapRequest):
    """Show dialog for responding to a swap request."""
    
    db = next(get_db())
    try:
        requester = db.query(User).filter(User.id == request.requester_id).first()
        requester_name = requester.full_name if requester else 'Unknown'
    finally:
        db.close()
    
    with ui.dialog() as dialog, ui.card().classes('min-w-[500px] max-w-[600px] p-6'):
        ui.label('Respond to WFH Swap Request').classes('text-xl font-bold mb-4')
        
        # Request details
        with ui.card().classes('w-full p-4 mb-4 bg-blue-50 dark:bg-blue-900/20'):
            ui.label(f'From: {requester_name}').classes('font-medium')
            ui.label(
                f"Swap: Their {request.requester_original_day.title()} ↔ "
                f"Your {request.target_original_day.title()}"
            ).classes('text-sm')
            ui.label(
                f"Date: {request.swap_date.strftime('%A, %B %d, %Y')}"
            ).classes('text-sm')
        
        # Requester's message
        ui.label(f"{requester_name}'s message:").classes('font-medium mb-2')
        with ui.card().classes('w-full p-3 mb-4 bg-gray-50 dark:bg-gray-800'):
            ui.label(f'"{request.request_message}"').classes('italic')
        
        # Response message
        ui.label('Your response (required):').classes('font-medium mb-2')
        response_input = ui.textarea(
            placeholder='e.g., No problem, I can cover that day! / Sorry, I have a meeting that day...'
        ).props('outlined autogrow').classes('w-full mb-4')
        
        # Error display
        error_label = ui.label('').classes('text-red-500 text-sm mb-2')
        error_label.set_visibility(False)
        
        def accept_swap():
            """Accept the swap request."""
            error_label.set_visibility(False)
            
            if not response_input.value or not response_input.value.strip():
                error_label.text = 'Please provide a response message.'
                error_label.set_visibility(True)
                return
            
            db = next(get_db())
            try:
                swap_service = WFHSwapService(db)
                swap_service.accept_swap(
                    swap_id=request.id,
                    response_message=response_input.value.strip(),
                    responder_id=user_id
                )
                db.commit()
                
                dialog.close()
                show_success_dialog(
                    'Swap Accepted',
                    f'You have accepted the swap with {requester_name}. '
                    f'You will work from home on {request.requester_original_day.title()} instead.'
                )
                ui.navigate.to('/dashboard')
                
            except ValueError as e:
                error_label.text = str(e)
                error_label.set_visibility(True)
            except Exception as e:
                error_label.text = f'Error: {str(e)}'
                error_label.set_visibility(True)
            finally:
                db.close()
        
        def decline_swap():
            """Decline the swap request."""
            error_label.set_visibility(False)
            
            if not response_input.value or not response_input.value.strip():
                error_label.text = 'Please provide a response message explaining why you cannot swap.'
                error_label.set_visibility(True)
                return
            
            db = next(get_db())
            try:
                swap_service = WFHSwapService(db)
                swap_service.decline_swap(
                    swap_id=request.id,
                    response_message=response_input.value.strip(),
                    responder_id=user_id
                )
                db.commit()
                
                dialog.close()
                show_info_dialog(
                    'Swap Declined',
                    f'You have declined the swap request from {requester_name}.'
                )
                ui.navigate.to('/dashboard')
                
            except ValueError as e:
                error_label.text = str(e)
                error_label.set_visibility(True)
            except Exception as e:
                error_label.text = f'Error: {str(e)}'
                error_label.set_visibility(True)
            finally:
                db.close()
        
        # Action buttons
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancel', on_click=dialog.close).props('flat')
            ui.button(
                'Decline',
                icon='close',
                on_click=decline_swap
            ).props('outline').classes('text-red-500')
            ui.button(
                'Accept Swap',
                icon='check',
                on_click=accept_swap
            ).style('background-color: #22c55e; color: white;')
    
    dialog.open()


def cancel_swap_request(swap_id: int):
    """Cancel a pending swap request."""
    db = next(get_db())
    try:
        swap_service = WFHSwapService(db)
        swap_service.cancel_swap(swap_id, user_id)
        db.commit()
        show_info_dialog('Request Cancelled', 'Your swap request has been cancelled.')
        ui.navigate.to('/dashboard')
    except ValueError as e:
        show_error_dialog('Error', str(e))
    finally:
        db.close()
```

### 6.2 My Profile Integration - Email Notification Toggle

**File**: `nicegui_app/pages/dashboard.py` (or wherever My Profile card exists)

Add a notification preferences section to the employee's My Profile card with a toggle switch for WFH swap email notifications.

#### 6.2.1 Profile Card Addition

```python
def render_my_profile_card():
    """Render the My Profile card with notification preferences."""
    db = next(get_db())
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        wfh_emails_enabled = current_user.wfh_swap_emails_enabled if current_user else True
    finally:
        db.close()
    
    with ui.card().classes('w-full p-4 mb-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('person', color='primary', size='md')
            ui.label('My Profile').classes('text-lg font-semibold')
        
        # ... existing profile content ...
        
        # ===== NOTIFICATION PREFERENCES SECTION =====
        ui.separator().classes('my-4')
        
        with ui.row().classes('items-center gap-2 mb-3'):
            ui.icon('notifications', size='sm').style('color: #c9a227')
            ui.label('Notification Preferences').classes('font-medium')
            ui.button(
                icon='help_outline',
                on_click=lambda: show_help_dialog(
                    'Email Notification Preferences',
                    'Control which email notifications you receive.\n\n'
                    '**WFH Swap Emails:**\n'
                    'When enabled, you\'ll receive emails when:\n'
                    '• Someone requests to swap WFH days with you\n'
                    '• Someone responds to your swap request\n\n'
                    '**Note:** Even if disabled, all swap activity is still recorded '
                    'in the audit log for compliance purposes. You\'ll still see '
                    'notifications on your dashboard.'
                )
            ).props('flat dense round size=xs').style('color: #9ca3af')
        
        # WFH Swap Email Toggle
        with ui.row().classes('w-full items-center justify-between p-3 rounded').style(
            'background-color: rgba(201, 162, 39, 0.1); border: 1px solid rgba(201, 162, 39, 0.3);'
        ):
            with ui.column().classes('gap-0'):
                ui.label('WFH Swap Email Notifications').classes('font-medium text-sm')
                ui.label(
                    'Receive emails for swap requests and responses'
                ).classes('text-xs opacity-60')
            
            def on_toggle_change(e):
                """Handle email notification toggle change."""
                new_value = e.value
                toggle_db = next(get_db())
                try:
                    user = toggle_db.query(User).filter(User.id == user_id).first()
                    if user:
                        old_value = user.wfh_swap_emails_enabled
                        user.wfh_swap_emails_enabled = new_value
                        toggle_db.commit()
                        
                        # Create audit log entry for preference change
                        AuditService.log(
                            db=toggle_db,
                            action='notification_preference_changed',
                            user_id=user_id,
                            username=user.username,
                            entity_type='user',
                            entity_id=user_id,
                            details={
                                'preference': 'wfh_swap_emails_enabled',
                                'old_value': old_value,
                                'new_value': new_value
                            }
                        )
                        toggle_db.commit()
                        
                        # Show confirmation
                        status = 'enabled' if new_value else 'disabled'
                        ui.notify(
                            f'WFH swap email notifications {status}',
                            type='positive' if new_value else 'info',
                            position='top'
                        )
                except Exception as ex:
                    ui.notify(f'Error updating preference: {str(ex)}', type='negative')
                finally:
                    toggle_db.close()
            
            ui.switch(
                value=wfh_emails_enabled,
                on_change=on_toggle_change
            ).props('color=amber')
        
        # Info notice about audit logging
        with ui.row().classes('w-full mt-2 items-start gap-2'):
            ui.icon('info', size='xs').classes('opacity-50 mt-0.5')
            ui.label(
                'All swap activity is recorded in audit logs regardless of email preference.'
            ).classes('text-xs opacity-50')
```

#### 6.2.2 Standalone My Profile Page (if exists)

If there's a dedicated `/profile` or `/my-profile` page, add the same notification preferences section:

**File**: `nicegui_app/pages/profile.py` (or similar)

```python
@ui.page('/profile')
def profile_page():
    """User profile page with notification preferences."""
    apply_dark_mode()
    
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return
    
    user_id = user.get('id')
    
    db = next(get_db())
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            ui.navigate.to('/dashboard')
            return
        
        wfh_emails_enabled = current_user.wfh_swap_emails_enabled
        user_full_name = current_user.full_name
        user_email = current_user.email
        user_department = current_user.department.name if current_user.department else 'N/A'
        wfh_day = get_wfh_day_name(current_user)  # Helper to extract WFH day
    finally:
        db.close()
    
    with ui.column().classes('w-full max-w-2xl mx-auto p-6'):
        page_header(title='MY PROFILE', show_back=True)
        
        # Personal Information Card
        with ui.card().classes('w-full p-6 mb-4'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('badge', size='md').style('color: #c9a227')
                ui.label('Personal Information').classes('text-xl font-semibold')
            
            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.column():
                    ui.label('Name').classes('text-xs opacity-60')
                    ui.label(user_full_name).classes('font-medium')
                with ui.column():
                    ui.label('Email').classes('text-xs opacity-60')
                    ui.label(user_email).classes('font-medium')
                with ui.column():
                    ui.label('Department').classes('text-xs opacity-60')
                    ui.label(user_department).classes('font-medium')
                with ui.column():
                    ui.label('WFH Day').classes('text-xs opacity-60')
                    ui.label(wfh_day.title() if wfh_day else 'Not configured').classes('font-medium')
        
        # Notification Preferences Card
        with ui.card().classes('w-full p-6 mb-4'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('notifications', size='md').style('color: #c9a227')
                ui.label('Notification Preferences').classes('text-xl font-semibold')
                ui.button(
                    icon='help_outline',
                    on_click=lambda: show_help_dialog(
                        'Notification Preferences',
                        'Manage how you receive notifications from the system.\n\n'
                        '**Email Notifications:**\n'
                        'Control whether you receive email alerts for various events.\n\n'
                        '**Important:** Disabling emails does NOT disable:\n'
                        '• Dashboard notifications\n'
                        '• Audit log entries\n'
                        '• Manager reports\n\n'
                        'All activity is always recorded for compliance purposes.'
                    )
                ).props('flat dense round size=sm').style('color: #9ca3af')
            
            ui.label(
                'Control which email notifications you receive. '
                'Dashboard notifications and audit logs are always active.'
            ).classes('text-sm opacity-70 mb-4')
            
            # WFH Swap Emails Toggle
            with ui.card().classes('w-full p-4').style(
                'background-color: rgba(201, 162, 39, 0.05); border: 1px solid rgba(201, 162, 39, 0.2);'
            ):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('swap_horiz', size='sm').style('color: #c9a227')
                        with ui.column().classes('gap-0'):
                            ui.label('WFH Day Swap Emails').classes('font-medium')
                            ui.label(
                                'Receive emails when someone requests a swap or responds to your request'
                            ).classes('text-xs opacity-60')
                    
                    # State for the toggle
                    toggle_state = {'value': wfh_emails_enabled}
                    
                    def on_wfh_email_toggle(e):
                        new_value = e.value
                        toggle_db = next(get_db())
                        try:
                            toggle_user = toggle_db.query(User).filter(User.id == user_id).first()
                            if toggle_user:
                                old_value = toggle_user.wfh_swap_emails_enabled
                                toggle_user.wfh_swap_emails_enabled = new_value
                                
                                # Audit log - ALWAYS created even when disabling emails
                                AuditService.log(
                                    db=toggle_db,
                                    action='notification_preference_changed',
                                    user_id=user_id,
                                    username=toggle_user.username,
                                    entity_type='user',
                                    entity_id=user_id,
                                    details={
                                        'preference': 'wfh_swap_emails_enabled',
                                        'old_value': old_value,
                                        'new_value': new_value,
                                        'changed_by': 'self'
                                    }
                                )
                                
                                toggle_db.commit()
                                toggle_state['value'] = new_value
                                
                                status_msg = 'enabled' if new_value else 'disabled'
                                show_success_dialog(
                                    'Preference Updated',
                                    f'WFH swap email notifications have been {status_msg}.\n\n'
                                    f'{"You will now receive emails for swap requests and responses." if new_value else "You will no longer receive swap emails, but you can still see notifications on your dashboard."}'
                                )
                        except Exception as ex:
                            show_error_dialog('Error', f'Could not update preference: {str(ex)}')
                        finally:
                            toggle_db.close()
                    
                    ui.switch(
                        value=wfh_emails_enabled,
                        on_change=on_wfh_email_toggle
                    ).props('color=amber')
            
            # Audit notice
            with ui.row().classes('w-full mt-4 items-center gap-2 p-3 rounded').style(
                'background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2);'
            ):
                ui.icon('security', size='sm').style('color: #3b82f6')
                with ui.column().classes('gap-0'):
                    ui.label('Audit Compliance').classes('text-sm font-medium').style('color: #3b82f6')
                    ui.label(
                        'All WFH swap activity is recorded in audit logs regardless of your email preferences. '
                        'This ensures proper compliance tracking and manager visibility.'
                    ).classes('text-xs opacity-70')
        
        # Back button
        ui.button(
            'Back to Dashboard',
            icon='arrow_back',
            on_click=lambda: ui.navigate.to('/dashboard')
        ).props('outline').classes('mt-4')
```

#### 6.2.3 Helper Function for WFH Day Name

```python
def get_wfh_day_name(user: User) -> Optional[str]:
    """Extract the WFH day name from user's remote_schedule."""
    import json
    
    if not user.remote_schedule:
        return None
    
    try:
        if isinstance(user.remote_schedule, str):
            schedule = json.loads(user.remote_schedule)
        else:
            schedule = user.remote_schedule
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        for day in days:
            if schedule.get(day, False):
                return day
        return None
    except (json.JSONDecodeError, TypeError):
        return None
```

---

## 7. Notification Integration

### 7.1 Email Notifications (with Preference Check)

**File**: `src/services/email_service.py`

Add these methods to the existing EmailService class. **Note**: These methods now check the user's email preference before sending:

```python
def send_swap_request_notification(
    self,
    target_email: str,
    target_name: str,
    requester_name: str,
    swap_date: date,
    requester_day: str,
    target_day: str,
    request_message: str,
    target_user_id: int = None  # NEW: Pass user ID to check preference
):
    """Send email notification for new swap request."""
    # Check if user has disabled email notifications
    if target_user_id:
        from src.database import get_db
        from src.models.user import User
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == target_user_id).first()
            if user and not user.wfh_swap_emails_enabled:
                logger.info(f"Skipping swap request email to {target_name} - emails disabled by user preference")
                return  # Skip sending email but audit log is created elsewhere
        finally:
            db.close()
    
    subject = f"WFH Day Swap Request from {requester_name}"
    
    content = f"""
    <p><strong>{requester_name}</strong> has requested to swap WFH days with you.</p>
    
    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 15px 0;">
        <p style="margin: 5px 0;"><strong>Swap Details:</strong></p>
        <p style="margin: 5px 0;">• Their WFH day: {requester_day.title()}</p>
        <p style="margin: 5px 0;">• Your WFH day: {target_day.title()}</p>
        <p style="margin: 5px 0;">• Swap date: {swap_date.strftime('%A, %B %d, %Y')}</p>
    </div>
    
    <p><strong>{requester_name}'s message:</strong></p>
    <blockquote style="border-left: 3px solid #c9a227; padding-left: 15px; margin: 10px 0; font-style: italic;">
        {request_message}
    </blockquote>
    
    <p>Please log in to TJM Time Calendar to accept or decline this request.</p>
    """
    
    html_body = self._get_email_template(
        title="WFH Day Swap Request",
        title_color="#c9a227",
        content=content,
        footer_text="Please respond within 3 business days."
    )
    
    self._send_email(target_email, subject, html_body)


def send_swap_response_notification(
    self,
    requester_email: str,
    requester_name: str,
    target_name: str,
    swap_date: date,
    status: str,  # 'accepted' or 'declined'
    response_message: str,
    requester_user_id: int = None  # NEW: Pass user ID to check preference
):
    """Send email notification for swap response."""
    # Check if user has disabled email notifications
    if requester_user_id:
        from src.database import get_db
        from src.models.user import User
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == requester_user_id).first()
            if user and not user.wfh_swap_emails_enabled:
                logger.info(f"Skipping swap response email to {requester_name} - emails disabled by user preference")
                return  # Skip sending email but audit log is created elsewhere
        finally:
            db.close()
    
    status_text = 'Accepted' if status == 'accepted' else 'Declined'
    status_color = '#22c55e' if status == 'accepted' else '#ef4444'
    
    subject = f"WFH Swap {status_text}: {target_name}"
    
    if status == 'accepted':
        action_text = f"You will work from home on {swap_date.strftime('%A, %B %d, %Y')} instead of your regular day."
    else:
        action_text = "You may want to request a swap with another teammate."
    
    content = f"""
    <p><strong>{target_name}</strong> has <span style="color: {status_color}; font-weight: bold;">{status_text.upper()}</span> your WFH swap request.</p>
    
    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 15px 0;">
        <p style="margin: 5px 0;"><strong>Swap date:</strong> {swap_date.strftime('%A, %B %d, %Y')}</p>
    </div>
    
    <p><strong>{target_name}'s response:</strong></p>
    <blockquote style="border-left: 3px solid {status_color}; padding-left: 15px; margin: 10px 0; font-style: italic;">
        {response_message}
    </blockquote>
    
    <p>{action_text}</p>
    """
    
    html_body = self._get_email_template(
        title=f"WFH Swap {status_text}",
        title_color=status_color,
        content=content,
        footer_text=""
    )
    
    self._send_email(requester_email, subject, html_body)
```

### 7.2 Trigger Notifications in Service (with User ID for Preference Check)

Update `WFHSwapService` to send emails after swap operations. **Note**: Pass user IDs to allow preference checking:

```python
# In create_swap_request(), after db.commit():
try:
    from src.services.email_service import EmailService
    email_service = EmailService()
    target = self.db.query(User).filter(User.id == target_user_id).first()
    requester = self.db.query(User).filter(User.id == requester_id).first()
    
    # Pass target_user_id to check their email preference
    email_service.send_swap_request_notification(
        target_email=target.email,
        target_name=target.full_name,
        requester_name=requester.full_name,
        swap_date=swap_date,
        requester_day=requester_wfh_day,
        target_day=target_wfh_day,
        request_message=request_message,
        target_user_id=target_user_id  # NEW: For preference check
    )
except Exception as e:
    logger.error(f"Failed to send swap request email: {e}")

# In accept_swap() and decline_swap(), after db.commit():
try:
    from src.services.email_service import EmailService
    email_service = EmailService()
    requester = self.db.query(User).filter(User.id == swap_request.requester_id).first()
    responder = self.db.query(User).filter(User.id == responder_id).first()
    
    # Pass requester_user_id to check their email preference
    email_service.send_swap_response_notification(
        requester_email=requester.email,
        requester_name=requester.full_name,
        target_name=responder.full_name,
        swap_date=swap_request.swap_date,
        status='accepted',  # or 'declined'
        response_message=response_message,
        requester_user_id=swap_request.requester_id  # NEW: For preference check
    )
except Exception as e:
    logger.error(f"Failed to send swap response email: {e}")
```

### 7.3 Audit Logging for Email Preference (Always Created)

**Important**: The audit log is created in the service layer BEFORE the email is sent, ensuring all swap activity is recorded regardless of email preferences.

Add this to the audit service for tracking notification preference changes:

**File**: `src/services/audit_service.py`

```python
@staticmethod
def log_notification_preference_change(
    db: Session,
    user_id: int,
    username: str,
    preference_name: str,
    old_value: bool,
    new_value: bool,
    changed_by: str = 'self'
):
    """Log when a user changes their notification preferences."""
    return AuditService.log(
        db=db,
        action='notification_preference_changed',
        user_id=user_id,
        username=username,
        entity_type='user',
        entity_id=user_id,
        details={
            'preference': preference_name,
            'old_value': old_value,
            'new_value': new_value,
            'changed_by': changed_by
        }
    )
```
```

---

## 8. Manager Reporting

### 8.1 Add Swaps to Auto Notify Reports

**File**: `nicegui_app/pages/admin_auto_notify_reports.py`

Add a new section for WFH swaps in the report generation:

```python
def get_wfh_swaps_for_period(
    db: Session,
    start_date: date,
    end_date: date,
    department_id: Optional[int] = None
) -> List[Dict]:
    """Get accepted WFH swaps for a date range."""
    from src.models.wfh_day_swap import WFHDaySwapRequest
    from src.models.user import User
    
    query = db.query(WFHDaySwapRequest).filter(
        WFHDaySwapRequest.status == 'accepted',
        WFHDaySwapRequest.swap_date >= start_date,
        WFHDaySwapRequest.swap_date <= end_date
    )
    
    if department_id:
        query = query.filter(WFHDaySwapRequest.department_id == department_id)
    
    swaps = query.order_by(WFHDaySwapRequest.swap_date).all()
    
    results = []
    for swap in swaps:
        requester = db.query(User).filter(User.id == swap.requester_id).first()
        target = db.query(User).filter(User.id == swap.target_user_id).first()
        
        results.append({
            'id': swap.id,
            'swap_date': swap.swap_date,
            'requester_name': requester.full_name if requester else 'Unknown',
            'target_name': target.full_name if target else 'Unknown',
            'requester_day': swap.requester_original_day,
            'target_day': swap.target_original_day,
            'requested_at': swap.requested_at,
            'responded_at': swap.responded_at
        })
    
    return results
```

Add to report HTML template:

```python
def generate_swap_report_section(swaps: List[Dict]) -> str:
    """Generate HTML section for WFH swaps."""
    if not swaps:
        return ""
    
    html = """
    <div style="margin-top: 30px;">
        <h3 style="color: #c9a227; border-bottom: 2px solid #c9a227; padding-bottom: 5px;">
            🔄 WFH Day Swaps
        </h3>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <thead>
                <tr style="background-color: #f3f4f6;">
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Date</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Swap</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Completed</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for swap in swaps:
        html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {swap['swap_date'].strftime('%b %d, %Y')}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {swap['requester_name']} ({swap['requester_day'].title()}) ↔ 
                    {swap['target_name']} ({swap['target_day'].title()})
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {swap['responded_at'].strftime('%b %d at %I:%M %p') if swap['responded_at'] else '-'}
                </td>
            </tr>
        """
    
    html += """
            </tbody>
        </table>
    </div>
    """
    
    return html
```

---

## 9. Admin Configuration

### 9.1 System Settings (Future)

Add these to `SystemSetting` for future configurability:

```python
# Settings that can be added to admin_system.py settings panel

WFH_SWAP_SETTINGS = {
    'wfh_swap_enabled': {
        'value': True,
        'type': 'boolean',
        'label': 'Enable WFH Day Swaps',
        'description': 'Allow employees to swap WFH days with teammates'
    },
    'wfh_swap_expiry_days': {
        'value': 3,
        'type': 'integer',
        'label': 'Request Expiry (Business Days)',
        'description': 'Auto-expire pending requests after this many business days'
    },
    'wfh_swap_max_future_days': {
        'value': 21,
        'type': 'integer',
        'label': 'Max Future Days',
        'description': 'How far in advance swaps can be requested'
    },
    'wfh_swap_require_manager_approval': {
        'value': False,
        'type': 'boolean',
        'label': 'Require Manager Approval',
        'description': 'If enabled, manager must approve swaps after employee acceptance'
    },
    'wfh_swap_min_coverage': {
        'value': 3,
        'type': 'integer',
        'label': 'Minimum Office Coverage',
        'description': 'Warn if swap would leave fewer than this many employees in office'
    }
}
```

---

## 10. Testing Checklist

### 10.1 Database Tests
- [ ] Migration runs without errors
- [ ] Work schedules populate correctly
- [ ] All indexes created properly
- [ ] Foreign key constraints work

### 10.2 Service Layer Tests
- [ ] Create swap request - happy path
- [ ] Create swap request - validation errors (past date, weekend, self-swap)
- [ ] Accept swap - updates status and response message
- [ ] Decline swap - updates status and response message
- [ ] Cancel swap - only requester can cancel
- [ ] Expire stale requests - scheduled job works
- [ ] Get available targets - returns correct employees for date

---

## 10. Help Documentation & UI Help Buttons

This section covers all help system updates required for the WFH Day Swap feature.

### 10.1 Help Center Article

**File**: `nicegui_app/pages/help.py`

Add the following article to the `HELP_ARTICLES` dictionary under a new category or existing "PTO Requests" category:

```python
# Add to HELP_ARTICLES dictionary in help.py

"wfh-swaps": {
    "title": "WFH Day Swaps",
    "icon": "swap_horiz",
    "order": 7,
    "required_role": None,  # All users can see this
    "articles": [
        {
            "id": "wfh-swap-overview",
            "title": "WFH Day Swap Overview",
            "content": """
# WFH Day Swap Overview

The WFH Day Swap feature allows you to exchange your designated Work From Home day with a teammate when you need flexibility in your schedule.

## How It Works

Each employee has one designated WFH day per week. Sometimes life happens and you need to work from home on a different day. Instead of losing your WFH day, you can swap with a teammate who normally works from home on the day you need.

### Example Scenario

**Employee G** normally works from home on **Wednesday**, but he has a doctor's appointment on **Monday** and needs to be home that day.

**Employee D** normally works from home on **Monday**.

Employee G can request to swap his Wednesday WFH for Employee D's Monday WFH. If Employee D accepts:
- Employee G works from home on Monday (Employee D's usual day)
- Employee D works from home on Wednesday (Employee G's usual day)
- Both employees still get their WFH day, just swapped for that week

## Key Rules

| Rule | Details |
|------|---------|
| **Message Required** | You must explain why you need the swap |
| **Response Required** | The other person must respond with a message |
| **Time Limit** | Requests expire after 3 business days |
| **One at a Time** | You can only have one pending request per date |
| **Advance Notice** | You can request swaps up to 3 weeks ahead |

## Who Can Swap

You can only swap with employees who have the day you need as their WFH day:

| If you need... | You can swap with... |
|----------------|---------------------|
| Monday | Employee D |
| Tuesday | Miguel |
| Wednesday | Employee G or Employee C |
| Thursday | Brad |
| Friday | Jose or Daryn |

## Manager Visibility

Your manager is automatically notified of all completed swaps. Swaps appear in:
- Manager's weekly/bi-weekly/monthly reports
- Audit logs for compliance tracking
- Team Calendar (with swap indicator)

This ensures proper coverage tracking without requiring manager approval for each swap.
"""
        },
        {
            "id": "requesting-swap",
            "title": "Requesting a WFH Day Swap",
            "content": """
# Requesting a WFH Day Swap

Follow these steps to request a swap with a teammate.

## Step 1: Open the Swap Request

From your **Dashboard**, find the **WFH Day Swap** card and click **"Request Swap"**.

## Step 2: Select the Date

Choose the date you need to work from home. You'll see a calendar showing:
- Only weekdays (Monday-Friday)
- Only dates within the next 3 weeks
- Your regular WFH day is excluded (you already have that day!)

## Step 3: Select a Colleague

After selecting a date, the system shows who has that day as their WFH day. Select the person you'd like to swap with.

**Tip**: If multiple people have that WFH day, consider who might be most likely to accommodate your request.

## Step 4: Write Your Message

You **must** include a message explaining why you need the swap. This helps your teammate understand your situation and make an informed decision.

### Good Message Examples

✅ "Hey Brad, I have a doctor's appointment Thursday morning and need to be home. Would you be able to swap? I can take your usual day this week."

✅ "Hi Employee D, my internet provider is coming Monday to fix an outage. Any chance we could swap days? Happy to return the favor anytime!"

### Poor Message Examples

❌ "Can we swap?" *(No explanation)*

❌ "I need Monday" *(Too brief, no context)*

## Step 5: Send the Request

Click **"Send Request"** to submit. Your teammate will:
- See a notification on their dashboard
- Receive an email notification
- Have 3 business days to respond

## After Sending

Your request appears in the **"My Recent Swap Requests"** section with status **PENDING**. You'll be notified when they respond.

## Cancelling a Request

If you no longer need the swap, you can cancel a pending request by clicking the **X** button on the request card.
"""
        },
        {
            "id": "responding-swap",
            "title": "Responding to a Swap Request",
            "content": """
# Responding to a Swap Request

When a teammate requests to swap WFH days with you, here's how to respond.

## Finding the Request

You'll be notified of incoming swap requests in two ways:
1. **Dashboard Banner**: An orange notification card appears at the top of your dashboard
2. **Email**: You receive an email with the request details

## Reviewing the Request

The request card shows:
- **Who** is asking (teammate's name)
- **What** they're proposing (which days to swap)
- **When** the swap would happen (specific date)
- **Why** they need it (their message)

Click **"View message"** to read their full explanation.

## Making Your Decision

Consider:
- Do you have any commitments that require you to be home on your usual WFH day?
- Can you accommodate working from home on a different day?
- Is there anything that would prevent you from swapping?

## Accepting the Swap

If you can accommodate the swap:

1. Click **"Respond"** on the request card
2. Read their message in the response dialog
3. Write a response message (required)
4. Click **"Accept Swap"**

### Good Acceptance Messages

✅ "No problem, Employee G! I can work from home Wednesday instead. Hope your appointment goes well!"

✅ "Sure thing! Wednesday works fine for me this week."

## Declining the Swap

If you cannot accommodate the swap:

1. Click **"Respond"** on the request card
2. Write a response explaining why you can't swap (required)
3. Click **"Decline"**

### Good Decline Messages

✅ "Sorry Employee G, I have a client meeting at the office on Wednesday that I can't reschedule. Maybe try asking Employee C?"

✅ "I wish I could help, but I have a technician coming to my house on my WFH day. Let me know if you need help another time!"

**Note**: A message is required when declining so your teammate understands why and can ask someone else.

## Response Deadline

You have **3 business days** to respond. After that, the request automatically expires.

## What Happens After You Respond

- **If Accepted**: The swap is confirmed. You'll work from home on their usual day, and they'll work from home on your usual day.
- **If Declined**: Your teammate is notified and can request a swap with someone else.
- Your manager is notified of all completed swaps via their regular reports.
"""
        },
        {
            "id": "swap-status",
            "title": "Understanding Swap Status",
            "content": """
# Understanding Swap Status

Your swap requests can have several statuses. Here's what each one means.

## Status Types

### 🟠 PENDING

Your request has been sent and is waiting for a response.

**What to do**: Wait for your teammate to respond. They have 3 business days.

**You can**: Cancel the request if you no longer need the swap.

---

### 🟢 ACCEPTED

Your teammate agreed to the swap! The swap is now confirmed.

**What happens**:
- You work from home on their usual WFH day
- They work from home on your usual WFH day
- Your manager is notified via reports

**You can**: View their response message on your dashboard.

---

### 🔴 DECLINED

Your teammate was unable to swap with you.

**What to do**: Read their response message to understand why. Consider asking another teammate who has the same WFH day.

**You can**: Click "Try Again" to request a swap with someone else.

---

### ⚫ CANCELLED

You cancelled the request before your teammate responded.

**What happens**: The request is closed. No swap occurs.

**You can**: Create a new request if you still need a swap.

---

### ⚫ EXPIRED

Your teammate didn't respond within 3 business days.

**What happens**: The request automatically closed. No swap occurs.

**What to do**: Consider reaching out to your teammate directly, or request a swap with someone else.

## Viewing Your Swap History

All your swap requests (both made and received) appear in the **"My Recent Swap Requests"** section on your dashboard.

Each request shows:
- Status badge (color-coded)
- Colleague's name
- Which days were involved
- The swap date
- Response message (if responded)
- Response timestamp
"""
        },
        {
            "id": "swap-faq",
            "title": "WFH Swap FAQ",
            "content": """
# WFH Day Swap - Frequently Asked Questions

## General Questions

### Can I swap with anyone in the company?

You can only swap with employees whose WFH day is the day you need. For example, if you need Monday, you can only swap with employees who have Monday as their WFH day.

### Do I need manager approval?

No. WFH day swaps are employee-to-employee arrangements. However, your manager is automatically notified of all completed swaps through their regular reports.

### How far in advance can I request a swap?

You can request swaps up to **3 weeks (21 days)** in advance.

### Can I swap for a day in the past?

No. You can only request swaps for today or future dates.

---

## Request & Response

### Why do I have to write a message?

Messages help your teammate understand why you need the swap and make an informed decision. They also create an audit trail for the request.

### How long does my teammate have to respond?

**3 business days** (Monday-Friday). After that, the request expires automatically.

### What if I need an urgent swap?

For same-day or next-day swaps, consider reaching out to your teammate directly (via Teams, email, or in person) before sending the formal request. This speeds up the process.

### Can I have multiple pending requests?

You can only have **one pending request per swap date**. However, you can have pending requests for different dates simultaneously.

---

## After the Swap

### What if something changes and I can't do the swap anymore?

If the swap was **accepted**, contact your teammate and manager directly to discuss. The system doesn't currently support "un-swapping" after acceptance.

If the request is still **pending**, you can cancel it from your dashboard.

### Does the swap affect my PTO balance?

No. WFH day swaps don't affect any PTO balances. You're simply working from a different location on different days.

### Will this show on the Team Calendar?

Yes. Accepted swaps will be indicated on the Team Calendar so managers and teammates can see who is working from home on any given day.

---

## Troubleshooting

### I don't see the "Request Swap" button

Make sure you have a WFH day configured in your profile. If not, contact your administrator.

### No employees appear when I select a date

This means no one has that day as their WFH day. Check the WFH day distribution:
- Monday: Employee D
- Tuesday: Miguel
- Wednesday: Employee G, Employee C
- Thursday: Brad
- Friday: Jose, Daryn

### My request expired - what now?

You can create a new request with the same or different teammate. Consider reaching out to them directly first to ensure they'll respond promptly.

### I accidentally declined a request

Contact the requester directly and let them know. They can submit a new request, and you can accept it this time.

---

## Email Notifications

### Can I disable email notifications for WFH swaps?

Yes! Go to **My Profile** on your dashboard and find the **Notification Preferences** section. Toggle off "WFH Swap Email Notifications" to stop receiving emails.

**What still works when emails are disabled:**
- Dashboard notifications (you'll still see pending requests)
- Audit log entries (all activity is recorded)
- Manager reports (your manager still sees swaps)

### Why are my swap activities still being logged if I disabled emails?

For compliance and audit purposes, all WFH swap activity is recorded regardless of your email preferences. This ensures:
- Managers can track team swaps through reports
- HR has a complete audit trail
- You have a record of all your swap history

The email toggle only controls whether you receive email notifications - it doesn't affect record-keeping.

### Where can I change my notification preferences?

1. Go to your **Dashboard**
2. Find the **My Profile** card
3. Scroll to **Notification Preferences**
4. Toggle the **WFH Swap Email Notifications** switch

Your preference is saved immediately and takes effect for future notifications.
"""
        }
    ]
},
```

### 10.1.1 Additional Help Article: Notification Preferences

Add this article to the Help Center (can be added to an existing "Settings" or "Profile" category, or as part of WFH Swaps):

```python
{
    "id": "notification-preferences",
    "title": "Managing Email Notification Preferences",
    "content": """
# Managing Email Notification Preferences

You can control which email notifications you receive from the TJM Time Calendar system.

## Accessing Notification Preferences

1. Go to your **Dashboard**
2. Find the **My Profile** card
3. Look for the **Notification Preferences** section

Or navigate directly to your Profile page if available.

## Available Settings

### WFH Swap Email Notifications

**When ENABLED (default):**
- You receive an email when someone requests to swap WFH days with you
- You receive an email when someone responds to your swap request

**When DISABLED:**
- No emails are sent for swap requests or responses
- You still see notifications on your dashboard
- All activity is still recorded in audit logs

## What's Always Active

Regardless of your email settings, the following are **always** recorded:

| Feature | Status |
|---------|--------|
| Dashboard notifications | ✅ Always active |
| Audit log entries | ✅ Always recorded |
| Manager reports | ✅ Always included |
| Swap history | ✅ Always saved |

## Why Audit Logging Can't Be Disabled

For compliance and business purposes, all WFH swap activity must be tracked:

- **Manager Visibility**: Your manager needs to know about schedule changes
- **Coverage Planning**: The team needs accurate WFH schedules
- **Audit Trail**: HR and compliance require complete records
- **Dispute Resolution**: Having a record helps resolve any questions

## Changing Your Preferences

1. Find the notification toggle switch
2. Click to toggle ON or OFF
3. Your change is saved immediately
4. A confirmation message appears

**Note**: Changing your preference is also logged in the audit system.

## Tips

- If you prefer checking the app directly, disable emails to reduce inbox clutter
- Keep emails enabled if you want immediate notification of swap requests
- Remember: You have 3 business days to respond to requests, so check your dashboard regularly if emails are disabled
"""
}
```

Add contextual help buttons throughout the WFH Swap UI. Use the existing `show_help_dialog` pattern from the application.

**File**: `nicegui_app/pages/dashboard.py`

Add this helper function if not already present:

```python
def show_help_dialog(title: str, content: str):
    """Show a help dialog with the given title and content."""
    with ui.dialog() as dialog, ui.card().classes('max-w-[500px] p-6'):
        with ui.row().classes('w-full items-center justify-between mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('help_outline', color='primary', size='sm')
                ui.label(title).classes('text-lg font-semibold')
            ui.button(icon='close', on_click=dialog.close).props('flat dense round')
        
        ui.markdown(content).classes('text-sm')
        
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Got it', on_click=dialog.close).props('flat')
    
    dialog.open()
```

#### Help Button Locations

**1. WFH Swap Section Header**

```python
# In render_wfh_swap_section(), after the section title:
with ui.row().classes('items-center justify-between w-full mb-3'):
    with ui.row().classes('items-center gap-2'):
        ui.icon('home_work', color='primary', size='md')
        ui.label('WFH Day Swap').classes('text-lg font-semibold')
        ui.button(
            icon='help_outline',
            on_click=lambda: show_help_dialog(
                'WFH Day Swap',
                'Swap your designated Work From Home day with a teammate when you need flexibility. '
                'You can only swap with employees who have the day you need as their WFH day.\n\n'
                '**How it works:**\n'
                '1. Click "Request Swap" to start\n'
                '2. Select the date you need\n'
                '3. Choose a teammate and explain why\n'
                '4. Wait for their response (3 business days)\n\n'
                'Your manager is automatically notified of all completed swaps.'
            )
        ).props('flat dense round size=sm').style('color: #c9a227')
```

**2. Request Dialog - Date Selection**

```python
# In show_swap_request_dialog(), after date picker label:
with ui.row().classes('items-center gap-1 mb-2'):
    ui.label('Which day do you need to work from home?').classes('font-medium')
    ui.button(
        icon='help_outline',
        on_click=lambda: show_help_dialog(
            'Selecting a Date',
            'Choose the date you need to work from home.\n\n'
            '**Available dates:**\n'
            '- Weekdays only (Monday-Friday)\n'
            '- Up to 3 weeks in advance\n'
            '- Your regular WFH day is excluded\n\n'
            'After selecting a date, you\'ll see which teammates have that day as their WFH day.'
        )
    ).props('flat dense round size=xs').style('color: #9ca3af')
```

**3. Request Dialog - Message Input**

```python
# In show_swap_request_dialog(), after message label:
with ui.row().classes('items-center gap-1 mb-2'):
    ui.label('Message (required)').classes('font-medium')
    ui.button(
        icon='help_outline',
        on_click=lambda: show_help_dialog(
            'Why a Message is Required',
            'Your message helps your teammate understand why you need the swap.\n\n'
            '**Good message example:**\n'
            '"Hey Brad, I have a doctor\'s appointment Thursday morning and need to be home. '
            'Would you be able to swap? I can take your usual day this week."\n\n'
            '**Tips:**\n'
            '- Be specific about why you need the swap\n'
            '- Be polite and appreciative\n'
            '- Mention you\'re happy to return the favor'
        )
    ).props('flat dense round size=xs').style('color: #9ca3af')
```

**4. Response Dialog - Response Message**

```python
# In show_swap_response_dialog(), after response input label:
with ui.row().classes('items-center gap-1 mb-2'):
    ui.label('Your response (required):').classes('font-medium')
    ui.button(
        icon='help_outline',
        on_click=lambda: show_help_dialog(
            'Responding to a Swap Request',
            'Your response message is shared with the requester.\n\n'
            '**If accepting:**\n'
            '"No problem! I can work from home Wednesday instead. Hope your appointment goes well!"\n\n'
            '**If declining:**\n'
            '"Sorry, I have a client meeting that day. Maybe try asking Employee C?"\n\n'
            'A message is required so your teammate knows why you accepted or declined.'
        )
    ).props('flat dense round size=xs').style('color: #9ca3af')
```

**5. Incoming Request Card**

```python
# In render_incoming_swap_request(), add help button:
with ui.row().classes('items-center gap-1'):
    ui.icon('swap_horiz', color='orange', size='md')
    ui.label(f'WFH Swap Requests ({len(incoming_requests)})').classes('text-lg font-semibold')
    ui.badge(f'{len(incoming_requests)} pending', color='orange')
    ui.button(
        icon='help_outline',
        on_click=lambda: show_help_dialog(
            'Incoming Swap Requests',
            'These are requests from teammates who want to swap WFH days with you.\n\n'
            '**To respond:**\n'
            '1. Click "Respond" on the request\n'
            '2. Read their message\n'
            '3. Write your response\n'
            '4. Accept or Decline\n\n'
            '**Deadline:** You have 3 business days to respond before the request expires.\n\n'
            '**Note:** A response message is required for both accepting and declining.'
        )
    ).props('flat dense round size=sm').style('color: #f59e0b')
```

**6. My Swap Requests Section**

```python
# In render_wfh_swap_section(), after "My Recent Swap Requests" label:
with ui.row().classes('items-center gap-1 mb-2'):
    ui.label('My Recent Swap Requests').classes('text-sm font-medium opacity-70')
    ui.button(
        icon='help_outline',
        on_click=lambda: show_help_dialog(
            'Your Swap Request Status',
            '**Status meanings:**\n\n'
            '🟠 **PENDING** - Waiting for response (you can cancel)\n\n'
            '🟢 **ACCEPTED** - Swap confirmed! Check their response message.\n\n'
            '🔴 **DECLINED** - They couldn\'t swap. Read their message and try someone else.\n\n'
            '⚫ **CANCELLED** - You cancelled the request.\n\n'
            '⚫ **EXPIRED** - No response within 3 business days.'
        )
    ).props('flat dense round size=xs').style('color: #9ca3af')
```

### 10.3 Update Existing Help Articles

**File**: `nicegui_app/pages/help.py`

Update the following existing articles to reference WFH Day Swaps:

#### Update "Dashboard" Article

Add to the Dashboard help article content:

```markdown
## WFH Day Swap Section

If you have a designated Work From Home day, you'll see the **WFH Day Swap** card:

### Request a Swap
- Click **"Request Swap"** to exchange your WFH day with a teammate
- You can only swap with people who have the day you need

### Incoming Requests
- Orange notification cards show pending swap requests from teammates
- Click **"Respond"** to accept or decline

### Your Requests
- Track the status of swaps you've requested
- See response messages from teammates
```

#### Update "Work From Home" Article (if exists)

Add reference to day swaps:

```markdown
## Swapping WFH Days

Need to work from home on a different day? Use the **WFH Day Swap** feature:

1. Go to your Dashboard
2. Click **"Request Swap"** in the WFH Day Swap card
3. Select the date and teammate
4. Wait for their response

See **Help > WFH Day Swaps** for complete details.
```

### 10.4 Manager Help Article Addition

Add to the Manager-specific help section:

```python
{
    "id": "manager-wfh-swaps",
    "title": "Managing Team WFH Swaps",
    "content": """
# Managing Team WFH Day Swaps

As a manager, you have visibility into all WFH day swaps within your team.

## Automatic Notifications

When team members complete a WFH day swap, you are automatically notified through:
- **Weekly Reports**: Summary of all swaps that week
- **Bi-Weekly Reports**: Two-week swap overview
- **Monthly Reports**: Complete monthly swap activity

## What's Included in Reports

Each swap entry shows:
- **Date**: When the swap occurred
- **Participants**: Who swapped with whom
- **Original Days**: Each person's regular WFH day
- **Completion Time**: When the swap was accepted

## Coverage Tracking

Swaps are designed to maintain coverage:
- One person is always working from home
- One person is always in the office
- Net office coverage remains the same

## Audit Trail

All swap activity is logged in the audit system:
- `wfh_swap_requested`: When a request is made
- `wfh_swap_accepted`: When a swap is confirmed
- `wfh_swap_declined`: When a request is declined
- `wfh_swap_cancelled`: When a request is cancelled
- `wfh_swap_expired`: When a request expires

## Team Calendar

Accepted swaps are visible on the Team Calendar with a swap indicator, showing who is actually working from home on any given day (including any swaps that change the normal schedule).

## No Approval Required

WFH day swaps are employee-to-employee arrangements and don't require manager approval. This empowers employees to handle schedule flexibility while keeping you informed through automated reporting.

If you need to implement manager approval for swaps, contact your system administrator about enabling the approval workflow feature.
"""
}
```

---

## 11. Testing Scenarios

Comprehensive testing scenarios for the WFH Day Swap feature.

### 11.1 Scenario: Happy Path - Successful Swap

**Setup**: Employee G (WFH Wednesday) wants to swap with Employee D (WFH Monday)

**Steps**:
1. Log in as **Employee G**
2. Navigate to Dashboard
3. Click "Request Swap" in WFH Day Swap card
4. Select date: Next Monday
5. System shows: Employee D is available (WFH Monday)
6. Select Employee D
7. Enter message: "Hey Employee D, I have a doctor's appointment Monday morning. Can we swap? I'll take your Monday and you can have my Wednesday."
8. Click "Send Request"
9. **Verify**: Success dialog appears, request shows as PENDING on dashboard
10. Log out

11. Log in as **Employee D**
12. **Verify**: Orange notification card appears on dashboard
13. Click "Respond"
14. **Verify**: Dialog shows Employee G's message
15. Enter response: "No problem Employee G! Wednesday works for me."
16. Click "Accept Swap"
17. **Verify**: Success dialog appears
18. Log out

19. Log in as **Employee G**
20. **Verify**: Request now shows as ACCEPTED with Employee D's response message
21. **Verify**: Response timestamp is displayed

22. Log in as **Manager**
23. Navigate to Auto Notify Reports
24. **Verify**: Swap appears in the report

**Expected Audit Log Entries**:
- `wfh_swap_requested` by Employee G
- `wfh_swap_accepted` by Employee D

---

### 11.2 Scenario: Declined Swap

**Setup**: Brad (WFH Thursday) wants to swap with Miguel (WFH Tuesday)

**Steps**:
1. Log in as **Brad**
2. Request swap for next Tuesday with Miguel
3. Message: "Hey Miguel, any chance we could swap days next week?"
4. Submit request
5. Log out

6. Log in as **Miguel**
7. Click "Respond" on Brad's request
8. Enter response: "Sorry Brad, I have a client demo at the office on Thursday. Maybe ask someone else?"
9. Click "Decline"
10. Log out

11. Log in as **Brad**
12. **Verify**: Request shows as DECLINED with Miguel's message
13. **Verify**: "Try Again" button is available

**Expected Audit Log Entries**:
- `wfh_swap_requested` by Brad
- `wfh_swap_declined` by Miguel

---

### 11.3 Scenario: Cancelled Request

**Setup**: Employee C cancels his own request before response

**Steps**:
1. Log in as **Employee C**
2. Request swap for next Friday with Jose
3. Message: "Need to swap days for a delivery"
4. Submit request
5. **Verify**: Request shows as PENDING
6. Click the X (cancel) button on the request
7. Confirm cancellation
8. **Verify**: Request now shows as CANCELLED

9. Log in as **Jose**
10. **Verify**: No pending request notification (request was cancelled)

**Expected Audit Log Entries**:
- `wfh_swap_requested` by Employee C
- `wfh_swap_cancelled` by Employee C

---

### 11.4 Scenario: Expired Request

**Setup**: Test automatic expiration after 3 business days

**Steps**:
1. Log in as **Daryn**
2. Request swap for next Monday with Employee D
3. Submit request
4. Log out

5. **Manually advance system date by 4 business days** (or run expiration job)
6. Run: `WFHSwapService.expire_stale_requests()`

7. Log in as **Daryn**
8. **Verify**: Request shows as EXPIRED

9. Log in as **Employee D**
10. **Verify**: No pending request (it expired)

**Expected Audit Log Entries**:
- `wfh_swap_requested` by Daryn
- `wfh_swap_expired` (system)

---

### 11.5 Scenario: Multiple Swap Targets

**Setup**: Employee wants to swap for Wednesday (Employee G and Employee C both have Wednesday)

**Steps**:
1. Log in as **Brad**
2. Click "Request Swap"
3. Select next Wednesday
4. **Verify**: Both Employee G AND Employee C appear as available
5. Select Employee G
6. Enter message and submit
7. **Verify**: Request sent to Employee G only

---

### 11.6 Scenario: Validation Errors

**Test Case 1: Empty Message**
1. Start swap request
2. Select date and teammate
3. Leave message empty
4. Click Send
5. **Verify**: Error "A message explaining the swap request is required."

**Test Case 2: Past Date**
1. Attempt to select a date in the past
2. **Verify**: Past dates are not available in picker

**Test Case 3: Weekend Date**
1. **Verify**: Saturday/Sunday not available in picker

**Test Case 4: Own WFH Day**
1. Log in as Employee G (WFH Wednesday)
2. Open swap request
3. **Verify**: Wednesday is NOT available in date picker

**Test Case 5: Duplicate Pending Request**
1. Create request for Monday with Employee D
2. Try to create another request for the same Monday
3. **Verify**: Error "You already have a pending swap request for this date"

**Test Case 6: Swap with Self**
1. (Edge case - shouldn't be possible in UI)
2. Service-level test: Attempt to create swap where requester_id == target_user_id
3. **Verify**: Error "Cannot swap with yourself"

---

### 11.7 Scenario: Email Notifications

**Setup**: Verify all email notifications are sent

**Test 1: Request Created**
1. Employee G requests swap with Employee D
2. **Verify**: Employee D receives email with:
   - Subject: "WFH Day Swap Request from Employee G"
   - Content includes swap details and Employee G's message

**Test 2: Request Accepted**
1. Employee D accepts Employee G's request
2. **Verify**: Employee G receives email with:
   - Subject: "WFH Swap Accepted: Employee D"
   - Content includes "ACCEPTED" and Employee D's response

**Test 3: Request Declined**
1. Employee D declines Employee G's request
2. **Verify**: Employee G receives email with:
   - Subject: "WFH Swap Declined: Employee D"
   - Content includes "DECLINED" and Employee D's response

---

### 11.8 Scenario: Manager Report Integration

**Setup**: Verify swaps appear in manager reports

**Steps**:
1. Complete a swap between Employee G and Employee D (accepted)
2. Log in as **Manager/Admin**
3. Navigate to Auto Notify Reports
4. Generate a weekly report for the current period
5. **Verify**: WFH Day Swaps section appears with:
   - Swap date
   - "Employee G (Wednesday) ↔ Employee D (Monday)"
   - Completion timestamp

---

### 11.9 Scenario: Help System Verification

**Steps**:
1. Log in as any employee
2. On Dashboard, click ? next to "WFH Day Swap" header
3. **Verify**: Help dialog appears with overview content

4. Click "Request Swap"
5. Click ? next to date picker
6. **Verify**: Help dialog explains date selection

7. Click ? next to message input
8. **Verify**: Help dialog explains message requirements

9. Navigate to Help Center
10. Find "WFH Day Swaps" category
11. **Verify**: All 5 articles are present and readable:
    - WFH Day Swap Overview
    - Requesting a WFH Day Swap
    - Responding to a Swap Request
    - Understanding Swap Status
    - WFH Swap FAQ

---

### 11.10 Scenario: Edge Cases

**Test 1: No WFH Day Configured**
1. Create test user with no remote_schedule
2. Log in as that user
3. **Verify**: "No WFH day configured. Contact your administrator." message appears
4. **Verify**: "Request Swap" button is disabled or hidden

**Test 2: No Available Swap Partners**
1. Temporarily update all users so no one has Monday as WFH
2. Log in as any employee
3. Select Monday in swap request
4. **Verify**: Message "No employees have Monday as their WFH day."

**Test 3: Request Near Expiration**
1. Create request (3 business day expiry)
2. Wait until day 3
3. **Verify**: Request still shows as PENDING
4. **Verify**: Target can still respond

**Test 4: Response After Date Passed**
1. Create request for swap date = tomorrow
2. Don't respond
3. After swap date passes, try to respond
4. **Verify**: Appropriate error handling (should prevent response)

---

### 11.11 Scenario: Email Notification Preferences

**Setup**: Test the email notification toggle in My Profile

**Test 1: Disable Email Notifications**
1. Log in as **Employee G**
2. Navigate to My Profile / Dashboard profile card
3. Find "Notification Preferences" section
4. **Verify**: WFH Swap Email toggle is ON by default
5. Toggle OFF the "WFH Swap Email Notifications" switch
6. **Verify**: Confirmation message "WFH swap email notifications disabled"
7. **Verify**: Audit log entry created: `notification_preference_changed`
   - Details: `{"preference": "wfh_swap_emails_enabled", "old_value": true, "new_value": false}`

**Test 2: Verify Emails Not Sent When Disabled**
1. Ensure Employee G has email notifications disabled
2. Log in as **Employee D**
3. Request swap with Employee G for next Wednesday
4. **Verify**: Audit log entry created: `wfh_swap_requested`
5. **Verify**: NO email sent to Employee G (check email logs or mock)
6. Log in as **Employee G**
7. **Verify**: Dashboard notification card STILL appears (emails disabled, not dashboard)

**Test 3: Re-enable Email Notifications**
1. Log in as **Employee G**
2. Toggle ON the "WFH Swap Email Notifications" switch
3. **Verify**: Confirmation message "WFH swap email notifications enabled"
4. **Verify**: Audit log entry created with `new_value: true`
5. Have someone send a new swap request
6. **Verify**: Email IS sent this time

**Test 4: Audit Trail Always Exists**
1. Log in as **Brad** (with emails disabled)
2. Request swap, accept swap, decline swap
3. Query audit_logs table
4. **Verify**: ALL swap activity recorded regardless of email preference:
   - `wfh_swap_requested`
   - `wfh_swap_accepted` or `wfh_swap_declined`
   - `notification_preference_changed`

**Test 5: My Profile Help Button**
1. Navigate to My Profile
2. Click ? next to "Notification Preferences"
3. **Verify**: Help dialog explains:
   - What emails are controlled
   - That dashboard notifications still work
   - That audit logs are always created

**Expected Audit Log Entries for Full Test**:
- `notification_preference_changed` (disable)
- `wfh_swap_requested` (even without email)
- `notification_preference_changed` (re-enable)

---

## 12. Testing Checklist

### 12.1 Database Tests
- [ ] Migration runs without errors
- [ ] Work schedules populate correctly
- [ ] All indexes created properly
- [ ] Foreign key constraints work
- [ ] wfh_swap_emails_enabled column added to users table

### 12.2 Service Layer Tests
- [ ] Create swap request - happy path
- [ ] Create swap request - validation errors (past date, weekend, self-swap)
- [ ] Accept swap - updates status and response message
- [ ] Decline swap - updates status and response message
- [ ] Cancel swap - only requester can cancel
- [ ] Expire stale requests - scheduled job works
- [ ] Get available targets - returns correct employees for date
- [ ] Email preference check - skips email when disabled

### 12.3 UI Tests
- [ ] Dashboard shows WFH swap section
- [ ] Request dialog opens and shows dates/employees
- [ ] Response dialog shows requester message
- [ ] Status updates display correctly after response
- [ ] Response message shows on requester's dashboard
- [ ] Help buttons (?) work on all locations
- [ ] Help dialogs show correct content
- [ ] My Profile shows notification preferences section
- [ ] Email toggle switch works correctly
- [ ] Toggle state persists after page refresh

### 12.4 Notification Tests
- [ ] Email sent when request created (if enabled)
- [ ] Email sent when request accepted (if enabled)
- [ ] Email sent when request declined (if enabled)
- [ ] Email NOT sent when user has disabled preference
- [ ] Manager report includes swap data
- [ ] Audit log created even when email skipped

### 12.5 Integration Tests
- [ ] Full workflow: Request → Accept → Dashboard update
- [ ] Full workflow: Request → Decline → Dashboard update
- [ ] Full workflow: Request → Cancel
- [ ] Full workflow: Request → Expire
- [ ] Full workflow: Disable emails → Request → No email → Dashboard shows notification

### 12.6 Help System Tests
- [ ] All ? buttons display correct help content
- [ ] Help Center articles render correctly
- [ ] FAQ answers are accurate
- [ ] Manager help article accessible to managers only

---

## 13. Future Expansion

This implementation is designed to support future enhancements:

### 13.1 Planned Features (Fields Already in Schema)

| Feature | Field(s) | Description |
|---------|----------|-------------|
| Multi-department filtering | `department_id` | Filter swaps by department |
| Manager approval workflow | `requires_approval`, `approved_by_id`, `approved_at` | Optional manager sign-off |
| Recurring swaps | `swap_type` | Allow permanent schedule changes |
| Coverage override | `coverage_override` | Manager can approve despite coverage warnings |
| Archive old records | `archived_at` | Soft archive for data retention |

### 13.2 Future Database Additions

When needed, these can be added:

```python
# Location-based filtering
location_id: FK to Location table

# Recurring swap patterns  
recurrence_pattern: JSON  # {"frequency": "weekly", "end_date": "2025-12-31"}

# Swap categories/reasons
swap_reason_category: Enum ['medical', 'personal', 'childcare', 'other']

# Integration with calendar
calendar_event_id: String  # Google/Outlook calendar event ID
```

### 13.3 Future UI Additions

- **Team Calendar**: Show swap indicators on calendar view
- **Manager Dashboard**: "Team Swaps This Week" widget
- **Coverage Dashboard**: Real-time office coverage visualization
- **Swap Analytics**: Reports on swap frequency, patterns, trends
- **Bulk Operations**: Admin tool to process multiple swaps

### 13.4 Future Integration Points

- **Microsoft Teams**: Send swap notifications via Teams
- **Google Calendar**: Create calendar events for swaps
- **Slack**: Bot notifications for swap requests
- **HR System**: Sync swap data with HR records

---

## Implementation Order

**Phase 1: Foundation** (Required)
1. Create database models
2. Run Alembic migrations
3. Populate work schedules
4. Implement WFHSwapService

**Phase 2: UI** (Required)
1. Dashboard swap section
2. Request dialog
3. Response dialog
4. Status display

**Phase 3: Notifications** (Required)
1. Email templates
2. Trigger emails from service

**Phase 4: Help System** (Required)
1. Add Help Center articles
2. Implement ? buttons throughout UI
3. Update existing help articles

**Phase 5: Reporting** (Recommended)
1. Add to Auto Notify Reports
2. Audit log integration

**Phase 6: Testing** (Required)
1. Run all test scenarios
2. Complete testing checklist
3. Verify help content accuracy

**Phase 7: Configuration** (Optional)
1. Admin settings panel
2. System settings in database

---

## Notes for Claude Code

1. **Always run migrations before testing UI changes** - includes both wfh_day_swap tables AND users.wfh_swap_emails_enabled
2. **Verify remote_schedule data exists in User table before testing**
3. **Use existing patterns from PTO request handling for consistency**
4. **Follow TJM brand colors: Gold (#c9a227), Gray (#5a6a72)**
5. **Test with at least 2 users to verify swap workflow**
6. **Check audit_logs table after each operation** - especially for `notification_preference_changed` entries
7. **Verify all ? help buttons work before marking UI complete**
8. **Run through ALL test scenarios in Section 11 before deployment** - including 11.11 Email Preferences
9. **Use existing `show_help_dialog` pattern from theme.py or create if not present**
10. **Help articles should match the tone of existing help content**
11. **Email notifications must check user preference before sending** - but audit logs are ALWAYS created
12. **My Profile notification toggle must create audit entry on change** - for compliance tracking
13. **Default email preference to TRUE** - existing users should continue receiving emails unless they opt out

---

## Summary of New Features Added

### Email Notification Preference Toggle
- **Location**: My Profile card on Dashboard (or dedicated /profile page)
- **Database**: New `wfh_swap_emails_enabled` boolean on User model (default: true)
- **Migration**: Separate migration after main WFH swap tables
- **Audit**: All preference changes logged to audit_logs
- **Behavior**: When disabled, emails are skipped but:
  - Dashboard notifications still appear
  - All swap activity still logged
  - Manager reports still include swaps

### Files Modified for Email Preference
1. `src/models/user.py` - Add `wfh_swap_emails_enabled` field
2. `alembic/versions/xxx_add_wfh_swap_email_preference.py` - Migration
3. `src/services/email_service.py` - Check preference before sending
4. `nicegui_app/pages/dashboard.py` - Add notification toggle to My Profile
5. `src/services/audit_service.py` - Add `log_notification_preference_change` method
6. `nicegui_app/pages/help.py` - Add notification preferences help article

### Proactive Weekly Limit Warning ✅ COMPLETED
- **Location**: WFH Swap page (`nicegui_app/pages/wfh_swap.py`)
- **Implemented**: Dec 22, 2025
- **Components**:
  - `limit_warning_container` - Amber warning banner displayed below week toggle
  - `render_limit_warning()` - Function to check `user['id'] in users_with_swaps`
  - Disabled state for all employee items when user has reached weekly limit
- **Behavior**:
  - When user has a pending/accepted swap for the displayed week, shows amber banner: "Weekly Limit Reached — You already have a swap request for this week"
  - All other employees become non-clickable with `cursor: not-allowed` and tooltip
  - Warning updates dynamically when toggling between "This Week" and "Next Week"
- **Verification**: Policy parity check passed (100%/100% coverage)
- **Media Studio Fix**: Removed sample swap request from scenario setup (`services/playwright_engine.py`) to allow training video to record "Initiate Swap" flow without triggering the weekly limit block.

---

*Document Version: 1.3*
*Created: December 2024*
*Updated: December 22, 2025 - Added Proactive Weekly Limit Warning (completed)*
*For: PTO Central - WFH Day Swap Feature*
