"""
2025 PTO Historical Data Migration Script
Run from project root: python scripts/migrate_2025_pto.py
"""
import sys
sys.path.insert(0, '.')

from datetime import date, datetime
from decimal import Decimal
from src.database import get_db
from src.models.user import User
from src.models.department import Department
from src.models.pto_request import PTORequest
from src.models.pto_balance import PTOBalance
from src.services.balance_service import BalanceService
from src.utils.password import hash_password
from sqlalchemy import select


# Employee data - (first, last, username, email, hire_date, role, remote_day)
EMPLOYEES = [
    ("Jose", "Laboy", "jlaboy", "jose@tjmit.com", "2006-01-30", "superadmin", "Friday"),
    ("Daryn", "Obrien", "dobrien", "daryn@tjmit.com", "2008-10-15", "employee", "Friday"),
    ("Johnny", "Laluz", "jlaluz", "johnny@tjmit.com", "2005-06-15", "employee", "Wednesday"),
    ("Omil", "Andujar", "oandujar", "omil@tjmit.com", "2013-11-04", "employee", "Monday"),
    ("Brad", "Garrett", "bgarrett", "brad@tjmit.com", "2021-12-20", "employee", "Thursday"),
    ("Miguel", "Zavala", "mzavala", "miguel@tjmit.com", "2022-10-31", "employee", "Tuesday"),
    ("Matt", "Weisbaum", "mweisbaum", "matt@tjmit.com", "2023-09-01", "employee", "Wednesday"),
]

# Vacation tiers (hours) based on years of service
# 20 days = 160 hours, 10 days = 80 hours
VACATION_HOURS = {
    "jlaboy": 160,    # 18+ years -> 20 days
    "dobrien": 160,   # 16+ years -> 20 days
    "jlaluz": 160,    # 19+ years -> 20 days
    "oandujar": 160,  # 11+ years -> 20 days
    "bgarrett": 80,   # 3+ years -> 10 days
    "mzavala": 80,    # 2+ years -> 10 days
    "mweisbaum": 80,  # 1+ years -> 10 days
}

# Standard allocations (hours)
SICK_HOURS = 40      # 5 days
PERSONAL_HOURS = 16  # 2 days

# Remote day mapping
REMOTE_DAYS = {
    "Monday": {"monday": True},
    "Tuesday": {"tuesday": True},
    "Wednesday": {"wednesday": True},
    "Thursday": {"thursday": True},
    "Friday": {"friday": True},
}

# PTO Events - (name, username, pto_type, start_date, end_date, notes, total_days)
PTO_EVENTS = [
    # Omil Andujar (7 events)
    ("Omil V-Day", "oandujar", "vacation", "2025-12-01", "2025-12-05", None, 5.0),
    ("Omil Half Day", "oandujar", "vacation", "2025-06-10", "2025-06-10", None, 0.5),
    ("Omil V-Day 8-13", "oandujar", "vacation", "2025-06-11", "2025-06-18", None, 6.0),
    ("Omil V-Day 1-7", "oandujar", "vacation", "2025-01-30", "2025-02-07", None, 7.0),
    ("Omil S-Day 1", "oandujar", "sick", "2025-03-11", "2025-03-11", None, 1.0),
    ("Omil S-Day 2", "oandujar", "sick", "2025-05-06", "2025-05-06", None, 1.0),
    ("Omil S-Day", "oandujar", "sick", "2025-08-07", "2025-08-07", None, 1.0),

    # Jose M. Laboy (11 events)
    ("Jose V-Day 1", "jlaboy", "vacation", "2025-01-17", "2025-01-17", None, 1.0),
    ("Jose V-Day 2", "jlaboy", "vacation", "2025-02-14", "2025-02-14", None, 1.0),
    ("Jose V-Day 3", "jlaboy", "vacation", "2025-04-04", "2025-04-04", None, 1.0),
    ("Jose V-Day 4", "jlaboy", "vacation", "2025-05-22", "2025-05-26", "Tuscon Arizona", 3.0),
    ("Jose V-Day 5", "jlaboy", "vacation", "2025-07-03", "2025-07-03", None, 1.0),
    ("Jose V-Day 6-11", "jlaboy", "vacation", "2025-08-01", "2025-08-10", "Caribbean Cruise", 6.0),
    ("Jose V-Day 12", "jlaboy", "vacation", "2025-10-16", "2025-10-16", None, 1.0),
    ("Jose - Florida", "jlaboy", "vacation", "2025-10-06", "2025-10-10", "Florida Trip", 5.0),
    ("Jose S-Day 1", "jlaboy", "sick", "2025-01-08", "2025-01-08", "Wife Shoulder Surgery", 1.0),
    ("Jose S-Day 2", "jlaboy", "sick", "2025-09-22", "2025-09-22", None, 1.0),
    ("Jose - 1/2 day", "jlaboy", "personal", "2025-05-05", "2025-05-05", "Chaparone", 0.5),

    # Daryn O'Brien (21 events)
    ("Daryn S-Day 1 1/2", "dobrien", "sick", "2025-01-10", "2025-01-10", "PT for surgery", 0.5),
    ("Daryn P-Day 1 1/2", "dobrien", "personal", "2025-01-14", "2025-01-14", "PT for surgery", 0.5),
    ("Daryn S-Day 1 1/2", "dobrien", "sick", "2025-01-21", "2025-01-21", None, 0.5),
    ("Daryn S-Day 2", "dobrien", "sick", "2025-01-28", "2025-01-28", None, 1.0),
    ("Daryn S-Day 3", "dobrien", "sick", "2025-01-29", "2025-01-29", None, 1.0),
    ("Daryn S-Day 4", "dobrien", "sick", "2025-03-24", "2025-03-24", None, 1.0),
    ("Daryn P-day 1 1/2", "dobrien", "personal", "2025-03-27", "2025-03-27", None, 0.5),
    ("Daryn V-Day 1-4", "dobrien", "vacation", "2025-04-01", "2025-04-04", None, 4.0),
    ("Daryn P-Day 2 (1/2)", "dobrien", "personal", "2025-05-05", "2025-05-05", None, 0.5),
    ("Daryn P-Day 2 (1/2)", "dobrien", "personal", "2025-05-15", "2025-05-15", None, 0.5),
    ("Daryn P-Day 3 (1/2)", "dobrien", "personal", "2025-06-04", "2025-06-04", None, 0.5),
    ("Daryn V-Day 5-6", "dobrien", "vacation", "2025-07-02", "2025-07-03", None, 2.0),
    ("Daryn P-day 3 (1/2)", "dobrien", "personal", "2025-07-15", "2025-07-15", None, 0.5),
    ("Daryn V-day 7-9", "dobrien", "vacation", "2025-08-06", "2025-08-08", None, 3.0),
    ("Daryn V-Day 7", "dobrien", "vacation", "2025-10-13", "2025-10-13", None, 1.0),
    ("Daryn V-day 10", "dobrien", "vacation", "2025-11-07", "2025-11-07", None, 1.0),
    ("Daryn V-day 14", "dobrien", "vacation", "2025-11-17", "2025-11-17", None, 1.0),
    ("Daryn V-Day 11", "dobrien", "vacation", "2025-11-28", "2025-11-28", None, 1.0),
    ("Daryn V-Day 15 (1/2)", "dobrien", "vacation", "2025-12-11", "2025-12-11", None, 0.5),
    ("Daryn V-Day 12-13", "dobrien", "vacation", "2025-12-22", "2025-12-23", None, 2.0),
    ("Daryn V-Day 1 (2026)", "dobrien", "vacation", "2026-01-05", "2026-01-05", None, 1.0),

    # Johnny La Luz (12 events)
    ("Johnny V-Day 1-5", "jlaluz", "vacation", "2025-02-08", "2025-02-15", "Mission's Trip to DR", 5.0),
    ("Johnny S-Day 1", "jlaluz", "sick", "2025-02-20", "2025-02-20", None, 1.0),
    ("Johnny V-Day 6-9", "jlaluz", "vacation", "2025-04-11", "2025-04-16", None, 4.0),
    ("Johnny P-Day 1", "jlaluz", "personal", "2025-04-30", "2025-04-30", None, 1.0),
    ("Johnny S-Day 2", "jlaluz", "sick", "2025-05-09", "2025-05-09", None, 1.0),
    ("Johnny V-Day 10-11", "jlaluz", "vacation", "2025-07-21", "2025-07-22", None, 2.0),
    ("Johnny S-Day 3", "jlaluz", "sick", "2025-09-29", "2025-09-29", None, 1.0),
    ("Johnny V-Day 12-13", "jlaluz", "vacation", "2025-12-15", "2025-12-16", None, 2.0),
    ("Johnny V-Day 14-15", "jlaluz", "vacation", "2025-12-18", "2025-12-19", None, 2.0),
    ("Johnny V-Day 16-17", "jlaluz", "vacation", "2025-12-22", "2025-12-23", None, 2.0),
    ("Johnny V-Day 18", "jlaluz", "vacation", "2025-12-26", "2025-12-26", None, 1.0),
    ("Johnny V-Day 19-20", "jlaluz", "vacation", "2025-12-29", "2025-12-30", None, 2.0),

    # Brad Garrett (22 events)
    ("Brad P-Day 1 1/2", "bgarrett", "personal", "2025-01-13", "2025-01-13", "Driving Wife to Airport", 0.5),
    ("Brad S-Day 1 1/2", "bgarrett", "sick", "2025-01-14", "2025-01-14", None, 0.5),
    ("Brad S-Day 1 1/2", "bgarrett", "sick", "2025-01-15", "2025-01-15", None, 0.5),
    ("Brad P-Day 1 1/2", "bgarrett", "personal", "2025-01-16", "2025-01-16", "Picking Wife up from Airport", 0.5),
    ("Brad V-Day 1", "bgarrett", "vacation", "2025-02-14", "2025-02-14", "Kids off School", 1.0),
    ("Brad S-Day 2 1/2", "bgarrett", "sick", "2025-03-18", "2025-03-18", None, 0.5),
    ("Brad V-Day 2", "bgarrett", "vacation", "2025-03-27", "2025-03-27", "Spring Break", 1.0),
    ("Brad V-Day 3", "bgarrett", "vacation", "2025-03-28", "2025-03-28", "Spring Break", 1.0),
    ("Brad V-Day 4", "bgarrett", "vacation", "2025-03-31", "2025-03-31", "Spring Break", 1.0),
    ("Brad S-Day 2 1/2", "bgarrett", "sick", "2025-05-06", "2025-05-06", None, 0.5),
    ("Brad P-Day 2 1/2", "bgarrett", "personal", "2025-05-15", "2025-05-15", "Daughters School Event", 0.5),
    ("Brad P-Day 2 1/2", "bgarrett", "personal", "2025-05-23", "2025-05-23", "Kids Last day of school", 0.5),
    ("Brad S-Day 3", "bgarrett", "sick", "2025-06-11", "2025-06-11", "Taking wife for her Surgery", 1.0),
    ("Brad V-Day 5", "bgarrett", "vacation", "2025-07-18", "2025-07-18", None, 1.0),
    ("Brad V-Day 6", "bgarrett", "vacation", "2025-08-08", "2025-08-08", "Daughters Birthday", 1.0),
    ("Brad S-Day 4", "bgarrett", "sick", "2025-09-03", "2025-09-03", None, 1.0),
    ("Brad S-Day 5", "bgarrett", "sick", "2025-09-29", "2025-09-29", None, 1.0),
    ("Brad V-Day 7", "bgarrett", "vacation", "2025-10-24", "2025-10-24", "Kids off School", 1.0),
    ("Brad V-Day 8", "bgarrett", "vacation", "2025-11-03", "2025-11-03", None, 1.0),
    ("Brad V-Day 9-10", "bgarrett", "vacation", "2025-11-18", "2025-11-19", None, 2.0),
    ("Brad V-Day 1 (2026)", "bgarrett", "vacation", "2026-01-02", "2026-01-02", None, 1.0),
    ("Brad V-Day 2 (2026)", "bgarrett", "vacation", "2026-01-05", "2026-01-05", None, 1.0),

    # Miguel Zavala (17 events)
    ("Miguel P-Day 1-2", "mzavala", "personal", "2025-03-06", "2025-03-07", None, 2.0),
    ("Miguel S-Day 1", "mzavala", "sick", "2025-03-28", "2025-03-28", None, 1.0),
    ("Miguel V-Day 1", "mzavala", "vacation", "2025-04-21", "2025-04-21", None, 1.0),
    ("Miguel S-Day 1/2", "mzavala", "sick", "2025-05-08", "2025-05-08", None, 0.5),
    ("Miguel V-Day 2", "mzavala", "vacation", "2025-06-20", "2025-06-20", None, 1.0),
    ("Miguel V-Day 3", "mzavala", "vacation", "2025-06-23", "2025-06-23", None, 1.0),
    ("Miguel S-Day 2", "mzavala", "sick", "2025-07-24", "2025-07-24", None, 1.0),
    ("Miguel S-Day 2 1/2", "mzavala", "sick", "2025-10-09", "2025-10-09", None, 0.5),
    ("Miguel S-Day 3", "mzavala", "sick", "2025-10-20", "2025-10-20", None, 0.5),
    ("Miguel S-Day 4", "mzavala", "sick", "2025-10-27", "2025-10-27", None, 1.0),
    ("Miguel V-Day 4", "mzavala", "vacation", "2025-11-24", "2025-11-24", None, 1.0),
    ("Miguel V-Day 9", "mzavala", "vacation", "2025-11-26", "2025-11-26", None, 1.0),
    ("Miguel V-Day 5", "mzavala", "vacation", "2025-11-28", "2025-11-28", None, 1.0),
    ("Miguel V-Day 6", "mzavala", "vacation", "2025-12-26", "2025-12-26", None, 1.0),
    ("Miguel V-Day 7", "mzavala", "vacation", "2025-12-29", "2025-12-29", None, 1.0),
    ("Miguel V-Day 8", "mzavala", "vacation", "2025-12-31", "2025-12-31", None, 1.0),
    ("Miguel V-Day 10 (2026)", "mzavala", "vacation", "2026-01-02", "2026-01-02", None, 1.0),

    # Matthew Weisbaum (14 events)
    ("Matt S-Day 1 1/2", "mweisbaum", "sick", "2025-03-31", "2025-03-31", None, 0.5),
    ("Matt V-Day 1", "mweisbaum", "vacation", "2025-05-30", "2025-05-30", None, 1.0),
    ("Matt S-Day 1 2/2", "mweisbaum", "sick", "2025-06-04", "2025-06-04", None, 0.5),
    ("Matt S-Day 2 1/2", "mweisbaum", "sick", "2025-07-07", "2025-07-07", None, 0.5),
    ("Matt S-Day 2 2/2", "mweisbaum", "sick", "2025-07-14", "2025-07-14", None, 0.5),
    ("Matt S-Day 3 1/2", "mweisbaum", "sick", "2025-07-21", "2025-07-21", None, 0.5),
    ("Matt S-Day 3 2/2", "mweisbaum", "sick", "2025-08-21", "2025-08-21", None, 0.5),
    ("Matt V-Day 2", "mweisbaum", "vacation", "2025-09-02", "2025-09-02", None, 1.0),
    ("Matt S-Day 4", "mweisbaum", "sick", "2025-09-23", "2025-09-23", None, 1.0),
    ("Matt St Croix", "mweisbaum", "personal", "2025-11-06", "2025-11-07", None, 2.0),
    ("Matt V-Day 3", "mweisbaum", "vacation", "2025-11-10", "2025-11-10", None, 1.0),
    ("Matt V-Day 8-9", "mweisbaum", "vacation", "2025-12-08", "2025-12-09", None, 2.0),
    ("Matt V-Day 4-7", "mweisbaum", "vacation", "2025-12-22", "2025-12-26", None, 5.0),
]


def migrate_users(db):
    """Create or update user accounts."""
    print("\n=== PHASE 1: User Migration ===")

    # Get Technology department
    tech_dept = db.execute(
        select(Department).where(Department.name == 'Technology')
    ).scalar_one_or_none()

    if not tech_dept:
        print("ERROR: Technology department not found!")
        return False

    print(f"Technology Department ID: {tech_dept.id}")

    default_password_hash = hash_password("2ez4me!!")
    created = 0
    updated = 0

    for first, last, username, email, hire_date_str, role, remote_day in EMPLOYEES:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        hire_date = date.fromisoformat(hire_date_str)
        remote_schedule = REMOTE_DAYS.get(remote_day, {})

        if user:
            # Update existing user
            user.department_id = tech_dept.id
            user.location_state = "IL"
            user.location_city = "Chicago"
            user.remote_schedule = remote_schedule
            user.hire_date = hire_date
            # Don't change role for existing users
            updated += 1
            print(f"  Updated: {username} (kept role: {user.role})")
        else:
            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=default_password_hash,
                first_name=first,
                last_name=last,
                role=role,
                department_id=tech_dept.id,
                hire_date=hire_date,
                location_state="IL",
                location_city="Chicago",
                remote_schedule=remote_schedule,
                is_active=True
            )
            db.add(user)
            created += 1
            print(f"  Created: {username} ({role})")

    db.commit()
    print(f"\nUsers: {created} created, {updated} updated")
    return True


def migrate_balances(db):
    """Create 2025 and 2026 PTO balances."""
    print("\n=== PHASE 1b: Balance Migration ===")

    balance_service = BalanceService(db)

    for first, last, username, email, hire_date_str, role, remote_day in EMPLOYEES:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            print(f"  WARNING: User {username} not found!")
            continue

        vacation_hours = VACATION_HOURS.get(username, 80)

        # Create 2025 balance
        balance_2025 = balance_service.get_or_create_balance(user.id, 2025)
        balance_2025.vacation_total = Decimal(str(vacation_hours))
        balance_2025.sick_total = Decimal(str(SICK_HOURS))
        balance_2025.personal_total = Decimal(str(PERSONAL_HOURS))
        print(f"  {username} 2025: V={vacation_hours}h, S={SICK_HOURS}h, P={PERSONAL_HOURS}h")

        # Create 2026 balance (for users with 2026 events)
        if username in ['dobrien', 'bgarrett', 'mzavala']:
            balance_2026 = balance_service.get_or_create_balance(user.id, 2026)
            balance_2026.vacation_total = Decimal(str(vacation_hours))
            balance_2026.sick_total = Decimal(str(SICK_HOURS))
            balance_2026.personal_total = Decimal(str(PERSONAL_HOURS))
            print(f"  {username} 2026: V={vacation_hours}h, S={SICK_HOURS}h, P={PERSONAL_HOURS}h")

    db.commit()
    print("\nBalances created for 2025 (and 2026 where needed)")
    return True


def migrate_pto_events(db):
    """Import PTO events as approved."""
    print("\n=== PHASE 2: PTO Event Migration ===")

    # Get manager (jlaboy) for approved_by
    manager = db.execute(
        select(User).where(User.username == 'jlaboy')
    ).scalar_one_or_none()

    if not manager:
        print("ERROR: Manager (jlaboy) not found!")
        return False

    print(f"Approver: {manager.first_name} {manager.last_name} (id={manager.id})")

    balance_service = BalanceService(db)
    imported = 0
    skipped = 0

    for name, username, pto_type, start_str, end_str, notes, total_days in PTO_EVENTS:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            print(f"  WARNING: User {username} not found, skipping {name}")
            skipped += 1
            continue

        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
        year = start_date.year

        # Convert days to hours
        total_hours = Decimal(str(total_days * 8))

        # Create approved PTO request
        request = PTORequest(
            user_id=user.id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date,
            total_days=Decimal(str(total_days)),
            status='approved',
            submitted_at=datetime.now(),
            approved_at=datetime.now(),
            approved_by=manager.id,
            notes=notes
        )
        db.add(request)

        # Update balance (add to used, not pending)
        balance = balance_service.get_or_create_balance(user.id, year)

        if pto_type == 'vacation':
            balance.vacation_used = (balance.vacation_used or Decimal('0')) + total_hours
        elif pto_type == 'sick':
            balance.sick_used = (balance.sick_used or Decimal('0')) + total_hours
        elif pto_type == 'personal':
            balance.personal_used = (balance.personal_used or Decimal('0')) + total_hours

        imported += 1

    db.commit()
    print(f"\nPTO Events: {imported} imported, {skipped} skipped")
    return True


def validate_migration(db):
    """Validate migration results."""
    print("\n=== PHASE 3: Validation ===")

    # Count users in Technology dept
    tech_dept = db.execute(
        select(Department).where(Department.name == 'Technology')
    ).scalar_one()

    tech_users = db.execute(
        select(User).where(User.department_id == tech_dept.id)
    ).scalars().all()

    print(f"\nTechnology Department Users: {len(tech_users)}")
    for u in tech_users:
        print(f"  {u.username}: {u.first_name} {u.last_name} ({u.role})")

    # Count PTO requests
    total_requests = db.execute(
        select(PTORequest).where(PTORequest.status == 'approved')
    ).scalars().all()

    print(f"\nApproved PTO Requests: {len(total_requests)}")

    # Balance summary
    print("\n2025 Balance Summary:")
    print("-" * 70)
    print(f"{'Employee':<15} {'Vac Total':>10} {'Vac Used':>10} {'Sick Used':>10} {'Pers Used':>10}")
    print("-" * 70)

    for first, last, username, email, hire_date_str, role, remote_day in EMPLOYEES:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            continue

        balance = db.execute(
            select(PTOBalance).where(
                PTOBalance.user_id == user.id,
                PTOBalance.year == 2025
            )
        ).scalar_one_or_none()

        if balance:
            vt = float(balance.vacation_total or 0) / 8
            vu = float(balance.vacation_used or 0) / 8
            su = float(balance.sick_used or 0) / 8
            pu = float(balance.personal_used or 0) / 8
            print(f"{username:<15} {vt:>10.1f}d {vu:>10.1f}d {su:>10.1f}d {pu:>10.1f}d")

    print("-" * 70)
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("2025 PTO Historical Data Migration")
    print("=" * 60)

    db = next(get_db())
    try:
        if not migrate_users(db):
            print("\nMigration aborted due to user errors")
            sys.exit(1)

        if not migrate_balances(db):
            print("\nMigration aborted due to balance errors")
            sys.exit(1)

        if not migrate_pto_events(db):
            print("\nMigration aborted due to PTO event errors")
            sys.exit(1)

        validate_migration(db)

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
