"""
Comprehensive test data seeding script for PTO Management System.

This script:
1. Cleans up existing data (in FK-safe order)
2. Creates 12 departments
3. Creates 36 users (3 per department + 3 superadmins)
4. Sets department managers
5. Creates PTO balances for 2025 based on tenure
6. Updates netadmin if exists

Run with: python scripts/seed_test_data.py
"""

import random
from datetime import date, timedelta
from decimal import Decimal
from passlib.hash import bcrypt

from src.database import SessionLocal
from src.models import User, Department, PTOBalance
from src.models.pto_request import PTORequest
from src.models.carryover_request import CarryoverRequest


# Configuration
DEPARTMENTS_CONFIG = [
    {'name': 'Executive', 'code': 'EXE', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'Accounting', 'code': 'ACC', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'Trading', 'code': 'TRD', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'Operations', 'code': 'OPS', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'Independent', 'code': 'SOL', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'CBOE', 'code': 'CBO', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'CME', 'code': 'CME', 'state': 'IL', 'city': 'Chicago'},
    {'name': 'NYO', 'code': 'NYO', 'state': 'NY', 'city': 'New York'},
    {'name': 'NYSE', 'code': 'NYE', 'state': 'NY', 'city': 'New York'},
    {'name': 'BOCA', 'code': 'BCA', 'state': 'FL', 'city': 'Boca'},
    {'name': 'CNT', 'code': 'CNT', 'state': 'CT', 'city': 'Rowayton'},
    {'name': 'PTO', 'code': 'PTO', 'state': 'IL', 'city': 'Chicago'},
]

# Password for all test users
TEST_PASSWORD = 'testjkl;'
HASHED_PASSWORD = bcrypt.hash(TEST_PASSWORD)


def random_date_years_ago(min_years: int, max_years: int) -> date:
    """Generate a random date between min_years and max_years ago."""
    today = date.today()
    min_days = min_years * 365
    max_days = max_years * 365
    random_days = random.randint(min_days, max_days)
    return today - timedelta(days=random_days)


def calculate_vacation_hours(hire_date: date) -> Decimal:
    """Calculate vacation hours based on tenure."""
    today = date.today()
    years_of_service = (today - hire_date).days // 365

    if years_of_service >= 10:
        return Decimal('160.00')  # 20 days
    elif years_of_service >= 5:
        return Decimal('120.00')  # 15 days
    else:
        return Decimal('80.00')   # 10 days


def cleanup_data(session):
    """Clean up existing data in FK-safe order."""
    print("\n=== Part 1: Cleanup ===")

    # 1. Delete carryover_requests
    count = session.query(CarryoverRequest).delete()
    print(f"Deleted {count} carryover requests")

    # 2. Delete pto_requests
    count = session.query(PTORequest).delete()
    print(f"Deleted {count} PTO requests")

    # 3. Delete pto_balances
    count = session.query(PTOBalance).delete()
    print(f"Deleted {count} PTO balances")

    # 4. Set manager_id = NULL on all departments
    session.query(Department).update({Department.manager_id: None})
    print("Set manager_id = NULL on all departments")

    # 5. Set department_id = NULL on netadmin (so we can delete departments)
    session.query(User).filter(User.username == 'netadmin').update({User.department_id: None})
    print("Set department_id = NULL on netadmin")

    # 6. Delete all users EXCEPT netadmin
    count = session.query(User).filter(User.username != 'netadmin').delete()
    print(f"Deleted {count} users (kept netadmin)")

    # 7. Delete all departments
    count = session.query(Department).delete()
    print(f"Deleted {count} departments")

    session.flush()


def create_departments(session) -> dict:
    """Create all departments and return a mapping of code -> department."""
    print("\n=== Part 2: Create Departments ===")

    dept_map = {}
    for dept_config in DEPARTMENTS_CONFIG:
        department = Department(
            name=dept_config['name'],
            code=dept_config['code'],
            is_active=True
        )
        session.add(department)
        session.flush()  # Get the ID
        dept_map[dept_config['code']] = department
        print(f"Created department: {dept_config['name']} ({dept_config['code']})")

    return dept_map


def create_users(session, dept_map: dict) -> dict:
    """Create users for each department and return mapping for manager assignment."""
    print("\n=== Part 3: Create Users ===")

    user_count = 0
    manager_map = {}  # dept_code -> manager_user

    for dept_config in DEPARTMENTS_CONFIG:
        code = dept_config['code']
        dept = dept_map[code]
        state = dept_config['state']
        city = dept_config['city']
        dept_name = dept_config['name']

        # Skip PTO department for regular users - handled separately
        if code == 'PTO':
            continue

        # Create Employee
        employee_username = f"{code.lower()}user"
        employee = User(
            username=employee_username,
            email=f"{employee_username}@tjmbrokerage.com",
            password_hash=HASHED_PASSWORD,
            first_name=dept_name,
            last_name='Employee',
            role='employee',
            department_id=dept.id,
            hire_date=random_date_years_ago(1, 2),
            location_state=state,
            location_city=city,
            is_active=True
        )
        session.add(employee)
        user_count += 1
        print(f"  Created employee: {employee_username}")

        # Create Manager
        manager_username = f"{code.lower()}man"
        manager = User(
            username=manager_username,
            email=f"{manager_username}@tjmbrokerage.com",
            password_hash=HASHED_PASSWORD,
            first_name=dept_name,
            last_name='Manager',
            role='manager',
            department_id=dept.id,
            hire_date=random_date_years_ago(5, 8),
            location_state=state,
            location_city=city,
            is_active=True
        )
        session.add(manager)
        session.flush()  # Get the ID for manager assignment
        manager_map[code] = manager
        user_count += 1
        print(f"  Created manager: {manager_username}")

        # Create Admin
        admin_username = f"{code.lower()}adm"
        admin = User(
            username=admin_username,
            email=f"{admin_username}@tjmbrokerage.com",
            password_hash=HASHED_PASSWORD,
            first_name=dept_name,
            last_name='Admin',
            role='admin',
            department_id=dept.id,
            hire_date=random_date_years_ago(12, 16),
            location_state=state,
            location_city=city,
            is_active=True
        )
        session.add(admin)
        user_count += 1
        print(f"  Created admin: {admin_username}")

    # Create PTO department superadmins
    pto_dept = dept_map['PTO']

    # ptoadmin
    ptoadmin = User(
        username='ptoadmin',
        email='ptoadmin@tjmbrokerage.com',
        password_hash=HASHED_PASSWORD,
        first_name='PTO',
        last_name='SuperAdmin',
        role='superadmin',
        department_id=pto_dept.id,
        hire_date=random_date_years_ago(20, 25),
        location_state='IL',
        location_city='Chicago',
        is_active=True
    )
    session.add(ptoadmin)
    user_count += 1
    print(f"  Created superadmin: ptoadmin")

    # jlaboy
    jlaboy = User(
        username='jlaboy',
        email='jose@tjmbrokerage.com',
        password_hash=HASHED_PASSWORD,
        first_name='Jose',
        last_name='Laboy',
        role='superadmin',
        department_id=pto_dept.id,
        hire_date=random_date_years_ago(20, 25),
        location_state='IL',
        location_city='Chicago',
        is_active=True
    )
    session.add(jlaboy)
    user_count += 1
    print(f"  Created superadmin: jlaboy")

    session.flush()
    print(f"\nTotal users created: {user_count}")

    return manager_map


def set_department_managers(session, dept_map: dict, manager_map: dict):
    """Set manager_id for each department."""
    print("\n=== Part 4: Set Department Managers ===")

    for code, manager in manager_map.items():
        dept = dept_map[code]
        dept.manager_id = manager.id
        print(f"Set {dept.name} manager to {manager.username}")

    session.flush()


def create_pto_balances(session):
    """Create PTO balances for 2025 based on tenure."""
    print("\n=== Part 5: Create PTO Balances ===")

    users = session.query(User).all()
    balance_count = 0

    for user in users:
        vacation_hours = calculate_vacation_hours(user.hire_date)

        balance = PTOBalance(
            user_id=user.id,
            year=2025,
            vacation_total=vacation_hours,
            vacation_used=Decimal('0.00'),
            vacation_pending=Decimal('0.00'),
            sick_total=Decimal('40.00'),  # 5 days
            sick_used=Decimal('0.00'),
            personal_total=Decimal('16.00'),  # 2 days
            personal_used=Decimal('0.00'),
            vacation_carryover=Decimal('0.00'),
            sick_carryover=Decimal('0.00'),
            personal_carryover=Decimal('0.00'),
            remote_weekly_used=0
        )
        session.add(balance)
        balance_count += 1

    session.flush()
    print(f"Created {balance_count} PTO balances for 2025")


def update_netadmin(session, dept_map: dict):
    """Update netadmin if exists."""
    print("\n=== Part 6: Update netadmin ===")

    netadmin = session.query(User).filter_by(username='netadmin').first()

    if netadmin:
        pto_dept = dept_map['PTO']
        netadmin.role = 'superadmin'
        netadmin.department_id = pto_dept.id
        netadmin.location_state = 'IL'
        netadmin.location_city = 'Chicago'
        # Keep password unchanged
        print(f"Updated netadmin: role=superadmin, department=PTO, location=IL/Chicago")
    else:
        print("netadmin user not found - skipping update")

    session.flush()


def main():
    """Main seeding function."""
    session = SessionLocal()

    try:
        print("=" * 60)
        print("Starting comprehensive test data seeding...")
        print("=" * 60)

        # Part 1: Cleanup
        cleanup_data(session)

        # Part 2: Create Departments
        dept_map = create_departments(session)

        # Part 3: Create Users
        manager_map = create_users(session, dept_map)

        # Part 4: Set Department Managers
        set_department_managers(session, dept_map, manager_map)

        # Part 5: Create PTO Balances
        create_pto_balances(session)

        # Part 6: Update netadmin
        update_netadmin(session, dept_map)

        # Commit all changes
        session.commit()

        print("\n" + "=" * 60)
        print("Database seeding completed successfully!")
        print("=" * 60)

        # Summary
        print("\nSummary:")
        print(f"  - Departments: {len(DEPARTMENTS_CONFIG)}")
        user_count = session.query(User).count()
        print(f"  - Users: {user_count}")
        balance_count = session.query(PTOBalance).count()
        print(f"  - PTO Balances: {balance_count}")

        print("\nTest Credentials:")
        print(f"  - Password for all users: {TEST_PASSWORD}")
        print("  - Superadmins: ptoadmin, jlaboy, netadmin")
        print("  - Per-department users: {code}user, {code}man, {code}adm")
        print("    (e.g., exeuser, exeman, exeadm for Executive)")

    except Exception as e:
        session.rollback()
        print(f"\nError during seeding: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
