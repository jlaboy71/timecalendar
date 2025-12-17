"""
Unit tests for the User model.
"""
import pytest
from datetime import date, datetime
from src.models.user import User
from src.constants import UserRole
from src.utils.password import hash_password, verify_password


class TestUserCreation:
    """Tests for basic User creation."""

    def test_user_creation_with_required_fields(self, db, test_department):
        """Test creating a user with all required fields."""
        user = User(
            username="newuser",
            email="newuser@test.com",
            first_name="New",
            last_name="User",
            role=UserRole.EMPLOYEE.value,
            department_id=test_department.id,
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@test.com"
        assert user.first_name == "New"
        assert user.last_name == "User"

    def test_user_default_role(self, db, test_department):
        """Test that default role is 'employee'."""
        user = User(
            username="defaultrole",
            email="defaultrole@test.com",
            first_name="Default",
            last_name="Role",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()

        assert user.role == "employee"

    def test_user_is_active_default(self, db, test_department):
        """Test that is_active defaults to True."""
        user = User(
            username="activetest",
            email="activetest@test.com",
            first_name="Active",
            last_name="Test",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()

        assert user.is_active is True


class TestUserFullNameProperty:
    """Tests for the full_name property."""

    def test_full_name_property(self, test_employee):
        """Test that full_name returns 'First Last'."""
        assert test_employee.full_name == "Test Employee"

    def test_full_name_with_different_names(self, db, test_department):
        """Test full_name with various name combinations."""
        user = User(
            username="johnsmith",
            email="john.smith@test.com",
            first_name="John",
            last_name="Smith",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()

        assert user.full_name == "John Smith"


class TestUserTrustedEmployee:
    """Tests for trusted employee functionality."""

    def test_user_is_trusted_default(self, test_employee):
        """Test that is_trusted defaults to False."""
        assert test_employee.is_trusted is False

    def test_user_trusted_fields(self, db, test_department, test_manager):
        """Test trusted employee fields can be set."""
        user = User(
            username="trusteduser",
            email="trusted@test.com",
            first_name="Trusted",
            last_name="User",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123"),
            is_trusted=True,
            trusted_by_id=test_manager.id,
            trusted_at=datetime.now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.is_trusted is True
        assert user.trusted_by_id == test_manager.id
        assert user.trusted_at is not None


class TestUserSoftDelete:
    """Tests for soft delete functionality."""

    def test_deleted_at_default_is_none(self, test_employee):
        """Test that deleted_at is None by default."""
        assert test_employee.deleted_at is None

    def test_soft_delete_user(self, db, test_employee):
        """Test soft deleting a user by setting deleted_at."""
        test_employee.deleted_at = datetime.now()
        db.commit()
        db.refresh(test_employee)

        assert test_employee.deleted_at is not None
        # User should still exist in database
        assert test_employee.id is not None


class TestUserLocationFields:
    """Tests for location-related fields."""

    def test_location_fields_default_to_none(self, test_employee):
        """Test that location fields default to None."""
        assert test_employee.location_state is None
        assert test_employee.location_city is None

    def test_location_fields_can_be_set(self, db, test_department):
        """Test setting location fields."""
        user = User(
            username="chicagouser",
            email="chicago@test.com",
            first_name="Chicago",
            last_name="User",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123"),
            location_state="IL",
            location_city="Chicago"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.location_state == "IL"
        assert user.location_city == "Chicago"


class TestUserPassword:
    """Tests for password handling."""

    def test_password_is_hashed(self, test_employee):
        """Test that password is stored as a hash, not plain text."""
        # Password hash should not be the plain text password
        assert test_employee.password_hash != "testpass123"
        # But it should verify correctly
        assert verify_password("testpass123", test_employee.password_hash)

    def test_wrong_password_fails_verification(self, test_employee):
        """Test that wrong password fails verification."""
        assert verify_password("wrongpassword", test_employee.password_hash) is False


class TestUserRoles:
    """Tests for different user roles."""

    def test_employee_role(self, test_employee):
        """Test employee role."""
        assert test_employee.role == UserRole.EMPLOYEE.value

    def test_manager_role(self, test_manager):
        """Test manager role."""
        assert test_manager.role == UserRole.MANAGER.value

    def test_admin_role(self, test_admin):
        """Test admin role."""
        assert test_admin.role == UserRole.ADMIN.value

    def test_superadmin_role(self, test_superadmin):
        """Test superadmin role."""
        assert test_superadmin.role == UserRole.SUPERADMIN.value


class TestUserRelationships:
    """Tests for user relationships."""

    def test_user_belongs_to_department(self, test_employee, test_department):
        """Test that user has department relationship."""
        assert test_employee.department_id == test_department.id
        assert test_employee.department is not None
        assert test_employee.department.name == "Test Department"

    def test_user_without_department(self, db):
        """Test creating user without department."""
        user = User(
            username="nodept",
            email="nodept@test.com",
            first_name="No",
            last_name="Department",
            hire_date=date(2023, 1, 15),
            password_hash=hash_password("password123"),
            department_id=None
        )
        db.add(user)
        db.commit()

        assert user.department_id is None
        assert user.department is None
