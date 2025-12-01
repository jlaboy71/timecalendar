"""
Database seeding script for PTO Management System.

This script populates the database with initial data including:
- Departments
- Admin user
- Market holidays for 2025
- Admin user PTO balance

Run with: python scripts/seed.py
"""

from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from passlib.hash import bcrypt

from src.database import get_db, SessionLocal
from src.models import User, Department, MarketHoliday, PTOBalance


def seed_departments(session):
    """Create initial departments."""
    departments = [
        {"name": "Executive", "code": "EXEC"},
        {"name": "Technology", "code": "TECH"},
        {"name": "Operations", "code": "OPS"},
        {"name": "Finance", "code": "FIN"},
    ]
    
    for dept_data in departments:
        # Check if department already exists
        existing = session.query(Department).filter_by(code=dept_data["code"]).first()
        if not existing:
            department = Department(**dept_data)
            session.add(department)
            print(f"Created department: {dept_data['name']} ({dept_data['code']})")
        else:
            print(f"Department already exists: {dept_data['name']} ({dept_data['code']})")


def seed_admin_user(session):
    """Create admin user."""
    # Check if admin user already exists
    existing_user = session.query(User).filter_by(username="netadmin").first()
    if existing_user:
        print("Admin user already exists: netadmin")
        return existing_user
    
    # Get Executive department
    exec_dept = session.query(Department).filter_by(code="EXEC").first()
    if not exec_dept:
        raise ValueError("Executive department must be created first")
    
    # Hash password
    hashed_password = bcrypt.hash("netpass")
    
    admin_user = User(
        username="netadmin",
        email="netadmin@haventech.com",
        password_hash=hashed_password,
        first_name="System",
        last_name="Administrator",
        role="admin",
        hire_date=date(2024, 1, 1),
        department_id=exec_dept.id,
        is_active=True
    )
    
    session.add(admin_user)
    print("Created admin user: netadmin")
    return admin_user


def seed_market_holidays(session):
    """Create market holidays for 2025."""
    holidays_2025 = [
        {"name": "New Year's Day", "date": date(2025, 1, 1)},
        {"name": "Martin Luther King Jr. Day", "date": date(2025, 1, 20)},
        {"name": "Presidents Day", "date": date(2025, 2, 17)},
        {"name": "Good Friday", "date": date(2025, 4, 18)},
        {"name": "Memorial Day", "date": date(2025, 5, 26)},
        {"name": "Juneteenth", "date": date(2025, 6, 19)},
        {"name": "Independence Day", "date": date(2025, 7, 4)},
        {"name": "Labor Day", "date": date(2025, 9, 1)},
        {"name": "Thanksgiving Day", "date": date(2025, 11, 27)},
        {"name": "Christmas Day", "date": date(2025, 12, 25)},
    ]
    
    markets = ["NYSE", "CME", "CBOE"]
    
    for market in markets:
        for holiday_data in holidays_2025:
            # Check if holiday already exists for this market
            existing = session.query(MarketHoliday).filter_by(
                market=market,
                holiday_date=holiday_data["date"]
            ).first()
            
            if not existing:
                holiday = MarketHoliday(
                    market=market,
                    name=holiday_data["name"],
                    holiday_date=holiday_data["date"],
                    year=holiday_data["date"].year,
                    is_observed=True
                )
                session.add(holiday)
                print(f"Created {market} holiday: {holiday_data['name']} ({holiday_data['date']})")
            else:
                print(f"{market} holiday already exists: {holiday_data['name']} ({holiday_data['date']})")


def seed_admin_pto_balance(session, admin_user):
    """Create PTO balance for admin user."""
    # Check if PTO balance already exists for 2025
    existing_balance = session.query(PTOBalance).filter_by(
        user_id=admin_user.id,
        year=2025
    ).first()
    
    if existing_balance:
        print("Admin PTO balance already exists for 2025")
        return
    
    pto_balance = PTOBalance(
        user_id=admin_user.id,
        year=2025,
        vacation_total=Decimal("20.00"),
        vacation_used=Decimal("0.00"),
        sick_total=Decimal("10.00"),
        sick_used=Decimal("0.00"),
        personal_total=Decimal("3.00"),
        personal_used=Decimal("0.00"),
        remote_work_used=Decimal("0.00")
    )
    
    session.add(pto_balance)
    print("Created admin PTO balance for 2025")


def main():
    """Main seeding function."""
    session = SessionLocal()
    
    try:
        print("Starting database seeding...")
        
        # Seed departments first (required for users)
        print("\n1. Seeding departments...")
        seed_departments(session)
        session.flush()  # Make departments available for foreign key references
        
        # Seed admin user
        print("\n2. Seeding admin user...")
        admin_user = seed_admin_user(session)
        session.flush()  # Make admin user available for foreign key references
        
        # Seed market holidays
        print("\n3. Seeding market holidays...")
        seed_market_holidays(session)
        session.flush()  # Make holidays available if needed
        
        # Seed admin PTO balance
        print("\n4. Seeding admin PTO balance...")
        seed_admin_pto_balance(session, admin_user)
        session.flush()  # Make PTO balance available if needed
        
        # Commit all changes
        session.commit()
        print("\n✅ Database seeding completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during seeding: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
