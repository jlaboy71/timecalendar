"""
Test utility functions for creating test data.

These functions provide a convenient way to create test objects
with sensible defaults while allowing overrides for specific test cases.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.constants import UserRole, PTOStatus, PTOType
from src.utils.password import hash_password


def create_test_user(
    db: Session,
    role: str = UserRole.EMPLOYEE.value,
    username: Optional[str] = None,
    email: Optional[str] = None,
    first_name: str = "Test",
    last_name: str = "User",
    department_id: Optional[int] = None,
    hire_date: Optional[date] = None,
    is_active: bool = True,
    is_trusted: bool = False,
    password: str = "testpass123",
    **kwargs
) -> User:
    """
    Create a test user with sensible defaults.

    Args:
        db: Database session
        role: User role (default: employee)
        username: Username (auto-generated if not provided)
        email: Email (auto-generated if not provided)
        first_name: First name
        last_name: Last name
        department_id: Department ID
        hire_date: Hire date (default: 2 years ago)
        is_active: Whether user is active
        is_trusted: Whether user is trusted for auto-approval
        password: Password to set
        **kwargs: Additional fields to set on the user

    Returns:
        Created User object
    """
    # Generate unique identifiers if not provided
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    if username is None:
        username = f"test_{role}_{unique_id}"
    if email is None:
        email = f"{username}@test.com"
    if hire_date is None:
        hire_date = date.today() - timedelta(days=730)  # 2 years ago

    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        department_id=department_id,
        hire_date=hire_date,
        is_active=is_active,
        is_trusted=is_trusted,
        password_hash=hash_password(password),
        **kwargs
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_department(
    db: Session,
    name: Optional[str] = None,
    manager_id: Optional[int] = None,
    **kwargs
) -> Department:
    """
    Create a test department with sensible defaults.

    Args:
        db: Database session
        name: Department name (auto-generated if not provided)
        manager_id: Manager user ID
        **kwargs: Additional fields

    Returns:
        Created Department object
    """
    import uuid
    if name is None:
        name = f"Test Department {str(uuid.uuid4())[:8]}"

    dept = Department(
        name=name,
        manager_id=manager_id,
        **kwargs
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def create_test_pto_request(
    db: Session,
    user: User,
    pto_type: str = PTOType.VACATION.value,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    total_days: Optional[Decimal] = None,
    status: str = PTOStatus.PENDING.value,
    notes: Optional[str] = None,
    **kwargs
) -> PTORequest:
    """
    Create a test PTO request with sensible defaults.

    Args:
        db: Database session
        user: User submitting the request
        pto_type: Type of PTO (default: vacation)
        start_date: Start date (default: tomorrow)
        end_date: End date (default: same as start)
        total_days: Total days (calculated if not provided)
        status: Request status (default: pending)
        notes: Optional notes
        **kwargs: Additional fields

    Returns:
        Created PTORequest object
    """
    if start_date is None:
        start_date = date.today() + timedelta(days=1)
    if end_date is None:
        end_date = start_date
    if total_days is None:
        # Simple calculation (doesn't account for weekends)
        total_days = Decimal(str((end_date - start_date).days + 1))

    request = PTORequest(
        user_id=user.id,
        pto_type=pto_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        status=status,
        notes=notes,
        **kwargs
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def create_test_balance(
    db: Session,
    user: User,
    year: Optional[int] = None,
    vacation_total: Decimal = Decimal("80.00"),
    vacation_used: Decimal = Decimal("0.00"),
    vacation_pending: Decimal = Decimal("0.00"),
    vacation_carryover: Decimal = Decimal("0.00"),
    sick_total: Decimal = Decimal("40.00"),
    sick_used: Decimal = Decimal("0.00"),
    sick_carryover: Decimal = Decimal("0.00"),
    personal_total: Decimal = Decimal("16.00"),
    personal_used: Decimal = Decimal("0.00"),
    personal_carryover: Decimal = Decimal("0.00"),
    **kwargs
) -> PTOBalance:
    """
    Create a test PTO balance with sensible defaults.

    Args:
        db: Database session
        user: User to create balance for
        year: Year (default: current year)
        vacation_total: Total vacation hours (default: 80 = 10 days)
        vacation_used: Used vacation hours
        vacation_pending: Pending vacation hours
        vacation_carryover: Carryover vacation hours
        sick_total: Total sick hours (default: 40 = 5 days)
        sick_used: Used sick hours
        sick_carryover: Carryover sick hours
        personal_total: Total personal hours (default: 16 = 2 days)
        personal_used: Used personal hours
        personal_carryover: Carryover personal hours
        **kwargs: Additional fields

    Returns:
        Created PTOBalance object
    """
    if year is None:
        year = date.today().year

    balance = PTOBalance(
        user_id=user.id,
        year=year,
        vacation_total=vacation_total,
        vacation_used=vacation_used,
        vacation_pending=vacation_pending,
        vacation_carryover=vacation_carryover,
        sick_total=sick_total,
        sick_used=sick_used,
        sick_carryover=sick_carryover,
        personal_total=personal_total,
        personal_used=personal_used,
        personal_carryover=personal_carryover,
        **kwargs
    )
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return balance


def get_next_working_day(from_date: date = None, skip_days: int = 0) -> date:
    """
    Get the next working day (Mon-Fri) from a given date.

    Args:
        from_date: Starting date (default: today)
        skip_days: Number of working days to skip forward

    Returns:
        Next working day date
    """
    if from_date is None:
        from_date = date.today()

    current = from_date
    working_days_skipped = 0

    while working_days_skipped <= skip_days:
        # weekday(): 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        if current.weekday() < 5:  # It's a working day
            if working_days_skipped == skip_days:
                return current
            working_days_skipped += 1
        current += timedelta(days=1)

    return current


def get_working_day_range(start_skip: int = 1, num_days: int = 5) -> tuple[date, date]:
    """
    Get a range of working days for testing.

    Args:
        start_skip: Number of working days from today to start
        num_days: Number of working days in the range

    Returns:
        Tuple of (start_date, end_date) that are both working days
    """
    start = get_next_working_day(skip_days=start_skip)
    end = get_next_working_day(start, skip_days=num_days - 1)
    return start, end


def approve_request(db: Session, request: PTORequest, approver: User) -> PTORequest:
    """
    Helper to approve a PTO request.

    Args:
        db: Database session
        request: Request to approve
        approver: User approving the request

    Returns:
        Updated PTORequest object
    """
    from datetime import datetime
    request.status = PTOStatus.APPROVED.value
    request.approved_by = approver.id
    request.approved_at = datetime.now()
    db.commit()
    db.refresh(request)
    return request


def deny_request(
    db: Session,
    request: PTORequest,
    approver: User,
    reason: str = "Test denial"
) -> PTORequest:
    """
    Helper to deny a PTO request.

    Args:
        db: Database session
        request: Request to deny
        approver: User denying the request
        reason: Denial reason

    Returns:
        Updated PTORequest object
    """
    from datetime import datetime
    request.status = PTOStatus.DENIED.value
    request.approved_by = approver.id
    request.approved_at = datetime.now()
    request.denial_reason = reason
    db.commit()
    db.refresh(request)
    return request
