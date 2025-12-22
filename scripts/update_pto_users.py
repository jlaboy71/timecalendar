#!/usr/bin/env python3
"""
Script to update PTO test users with correct location, department, hire dates, AND PTO balances.

Updates:
- All PTO users set to Illinois, Chicago
- All PTO users assigned to "PTO-Dept" department
- Random hire dates from 2020 to 6 months ago
- Except PTO Manager: hired 2010-01-01
- CREATES/UPDATES PTO balances based on tenure (CRITICAL!)
"""

import sys
import random
from pathlib import Path
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db
from src.models.user import User
from src.models.department import Department
from src.models.pto_balance import PTOBalance
from sqlalchemy import select

# ══════════════════════════════════════════════════════════════════════════════
# PTO ALLOCATION CONSTANTS (from year_end_service.py)
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_SICK_DAYS = 5       # 40 hours
DEFAULT_PERSONAL_DAYS = 2   # 16 hours
CHICAGO_PAID_LEAVE_HOURS = Decimal('40.00')  # 5 days for Chicago employees

# Vacation tiers based on tenure (years of service -> days)
VACATION_TIERS = {
    10: 20,  # 10+ years: 4 weeks (160 hours)
    5: 15,   # 5-9 years: 3 weeks (120 hours)
    2: 12,   # 2-4 years: 2.4 weeks (96 hours)
    0: 10,   # 0-1 years: 2 weeks (80 hours)
}


def get_random_hire_date():
    """Generate random hire date from Jan 2020 to 6 months ago."""
    start_date = date(2020, 1, 1)
    end_date = date.today() - relativedelta(months=6)

    # Calculate days between dates
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)

    return start_date + relativedelta(days=random_days)


def calculate_vacation_days(hire_date: date) -> int:
    """
    Calculate vacation days based on employee tenure.

    CRITICAL: This must match the logic in year_end_service.py!
    """
    if not hire_date:
        return VACATION_TIERS[0]

    today = date.today()
    years_of_service = (today - hire_date).days // 365

    # Find the right tier
    for min_years, days in sorted(VACATION_TIERS.items(), reverse=True):
        if years_of_service >= min_years:
            return days

    return VACATION_TIERS[0]


def update_or_create_balance(db, user: User, year: int = 2025):
    """
    Update or create PTO balance with proper allocations based on hire date.

    CRITICAL: This function ensures balances match tenure-based allocations.
    """
    # Calculate allocations
    vacation_days = calculate_vacation_days(user.hire_date)
    vacation_hours = Decimal(str(vacation_days * 8))
    sick_hours = Decimal(str(DEFAULT_SICK_DAYS * 8))
    personal_hours = Decimal(str(DEFAULT_PERSONAL_DAYS * 8))

    # Chicago Paid Leave for Chicago employees
    chicago_leave = CHICAGO_PAID_LEAVE_HOURS if user.location_city and user.location_city.lower() == 'chicago' else Decimal('0.00')

    # Check for existing balance
    bal_stmt = select(PTOBalance).where(
        PTOBalance.user_id == user.id,
        PTOBalance.year == year
    )
    balance = db.execute(bal_stmt).scalar_one_or_none()

    if balance:
        # Update existing balance
        balance.vacation_total = vacation_hours
        balance.sick_total = sick_hours
        balance.personal_total = personal_hours
        balance.chicago_paid_leave_total = chicago_leave
        action = "Updated"
    else:
        # Create new balance
        balance = PTOBalance(
            user_id=user.id,
            year=year,
            vacation_total=vacation_hours,
            vacation_used=Decimal('0.00'),
            vacation_pending=Decimal('0.00'),
            sick_total=sick_hours,
            sick_used=Decimal('0.00'),
            personal_total=personal_hours,
            personal_used=Decimal('0.00'),
            remote_weekly_used=0,
            chicago_paid_leave_total=chicago_leave,
            chicago_paid_leave_used=Decimal('0.00'),
            chicago_paid_leave_pending=Decimal('0.00'),
            chicago_paid_leave_carryover=Decimal('0.00')
        )
        db.add(balance)
        action = "Created"

    years_of_service = (date.today() - user.hire_date).days // 365 if user.hire_date else 0
    return f"{action} {year} balance: {vacation_days}d vac ({years_of_service}yr tenure), {DEFAULT_SICK_DAYS}d sick, {DEFAULT_PERSONAL_DAYS}d personal"


def main():
    """Update PTO users with correct settings."""
    print("=" * 60)
    print("PTO USER UPDATE SCRIPT")
    print("=" * 60)

    db = next(get_db())

    try:
        # ══════════════════════════════════════════════════════════════
        # STEP 1: Create or find PTO-Dept department
        # ══════════════════════════════════════════════════════════════
        print("\n[1] Checking for PTO-Dept department...")

        # Check by name first, then by code
        dept_stmt = select(Department).where(
            (Department.name == "PTO-Dept") | (Department.code == "PTO")
        )
        pto_dept = db.execute(dept_stmt).scalar_one_or_none()

        if not pto_dept:
            print("    Creating PTO-Dept department...")
            pto_dept = Department(name="PTO-Dept", code="PTODEPT")
            db.add(pto_dept)
            db.flush()  # Get the ID
            print(f"    Created PTO-Dept with ID: {pto_dept.id}")
        else:
            # Update name if needed
            if pto_dept.name != "PTO-Dept":
                print(f"    Found department '{pto_dept.name}' with code '{pto_dept.code}', renaming to PTO-Dept")
                pto_dept.name = "PTO-Dept"
            print(f"    Using department: {pto_dept.name} (ID: {pto_dept.id})")

        # ══════════════════════════════════════════════════════════════
        # STEP 2: Find and update PTO users
        # ══════════════════════════════════════════════════════════════
        print("\n[2] Finding and updating PTO users...")

        pto_usernames = [
            'ptouser', 'ptomanager', 'ptoadmin',
            'ptouser01', 'ptouser02', 'ptouser03',
            'ptouser04', 'ptouser05', 'ptouser06'
        ]

        for username in pto_usernames:
            user_stmt = select(User).where(User.username == username)
            user = db.execute(user_stmt).scalar_one_or_none()

            if not user:
                print(f"    [WARN] User '{username}' not found - skipping")
                continue

            # Set location
            user.location_state = "IL"
            user.location_city = "Chicago"

            # Set department
            user.department_id = pto_dept.id

            # Set hire date
            if username == 'ptomanager':
                user.hire_date = date(2010, 1, 1)
            else:
                user.hire_date = get_random_hire_date()

            # CRITICAL: Update PTO balance based on new hire date
            balance_msg = update_or_create_balance(db, user, 2025)

            print(f"    [OK] {username}: IL/Chicago, PTO-Dept, hired {user.hire_date}")
            print(f"         {balance_msg}")

        # ══════════════════════════════════════════════════════════════
        # STEP 3: Set department manager
        # ══════════════════════════════════════════════════════════════
        print("\n[3] Setting PTO Manager as department manager...")

        manager_stmt = select(User).where(User.username == 'ptomanager')
        manager = db.execute(manager_stmt).scalar_one_or_none()

        if manager:
            pto_dept.manager_id = manager.id
            print(f"    [OK] Set ptomanager (ID: {manager.id}) as manager of PTO-Dept")
        else:
            print("    [WARN] ptomanager not found - cannot set department manager")

        # ══════════════════════════════════════════════════════════════
        # COMMIT
        # ══════════════════════════════════════════════════════════════
        db.commit()
        print("\n" + "=" * 60)
        print("SUCCESS - All PTO users updated with proper balances!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
