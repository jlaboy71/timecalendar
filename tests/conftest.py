"""
Pytest configuration and fixtures for TJM Time Calendar tests.

This module provides:
- In-memory SQLite database for isolated testing
- Database session fixtures with automatic rollback
- Pre-configured test users (employee, manager, admin, superadmin)
- Test department and PTO balance fixtures
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.constants import UserRole, PTOStatus, PTOType
from src.utils.password import hash_password


@pytest.fixture(scope="function")
def engine():
    """
    Create an in-memory SQLite database engine for testing.

    Uses StaticPool to ensure the same connection is used throughout
    the test, preventing 'database is locked' errors.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    # Create all tables
    Base.metadata.create_all(engine)
    yield engine
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(engine) -> Session:
    """
    Create a database session that rolls back after each test.

    This ensures test isolation - changes in one test don't affect others.
    """
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_department(db: Session) -> Department:
    """Create a test department."""
    dept = Department(
        name="Test Department",
        code="TEST",
        manager_id=None  # Will be set if needed
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@pytest.fixture
def test_employee(db: Session, test_department: Department) -> User:
    """Create a test employee user."""
    user = User(
        username="test_employee",
        email="employee@test.com",
        first_name="Test",
        last_name="Employee",
        role=UserRole.EMPLOYEE.value,
        department_id=test_department.id,
        hire_date=date(2020, 1, 15),
        is_active=True,
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_manager(db: Session, test_department: Department) -> User:
    """Create a test manager user."""
    user = User(
        username="test_manager",
        email="manager@test.com",
        first_name="Test",
        last_name="Manager",
        role=UserRole.MANAGER.value,
        department_id=test_department.id,
        hire_date=date(2018, 6, 1),
        is_active=True,
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Update department to have this manager
    test_department.manager_id = user.id
    db.commit()

    return user


@pytest.fixture
def test_admin(db: Session, test_department: Department) -> User:
    """Create a test admin user."""
    user = User(
        username="test_admin",
        email="admin@test.com",
        first_name="Test",
        last_name="Admin",
        role=UserRole.ADMIN.value,
        department_id=test_department.id,
        hire_date=date(2015, 3, 1),
        is_active=True,
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_superadmin(db: Session, test_department: Department) -> User:
    """Create a test superadmin user."""
    user = User(
        username="test_superadmin",
        email="superadmin@test.com",
        first_name="Test",
        last_name="SuperAdmin",
        role=UserRole.SUPERADMIN.value,
        department_id=test_department.id,
        hire_date=date(2010, 1, 1),
        is_active=True,
        password_hash=hash_password("testpass123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_balance(db: Session, test_employee: User) -> PTOBalance:
    """Create a test PTO balance for the current year."""
    current_year = date.today().year
    balance = PTOBalance(
        user_id=test_employee.id,
        year=current_year,
        vacation_total=Decimal("80.00"),  # 10 days
        vacation_used=Decimal("0.00"),
        vacation_pending=Decimal("0.00"),
        vacation_carryover=Decimal("0.00"),
        sick_total=Decimal("40.00"),  # 5 days
        sick_used=Decimal("0.00"),
        sick_carryover=Decimal("0.00"),
        personal_total=Decimal("16.00"),  # 2 days
        personal_used=Decimal("0.00"),
        personal_carryover=Decimal("0.00")
    )
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return balance


@pytest.fixture
def test_pto_request(db: Session, test_employee: User) -> PTORequest:
    """Create a test PTO request."""
    request = PTORequest(
        user_id=test_employee.id,
        pto_type=PTOType.VACATION.value,
        start_date=date.today(),
        end_date=date.today(),
        total_days=Decimal("1.00"),
        status=PTOStatus.PENDING.value,
        notes="Test PTO request"
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


# Helper fixture for creating multiple users
@pytest.fixture
def all_test_users(test_employee, test_manager, test_admin, test_superadmin):
    """Return all test users as a dict for easy access."""
    return {
        'employee': test_employee,
        'manager': test_manager,
        'admin': test_admin,
        'superadmin': test_superadmin
    }
