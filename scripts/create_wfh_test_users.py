#!/usr/bin/env python3
"""
Script to create ptouser01-06 test accounts with WFH day assignments.

Users:
- ptouser01: Monday WFH
- ptouser02: Tuesday WFH
- ptouser03: Wednesday WFH
- ptouser04: Thursday WFH
- ptouser05: Friday WFH
- ptouser06: Friday WFH

All passwords: 2ez4me!!
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import date
from src.database import get_db
from src.models.user import User
from src.services.user_service import UserService
from src.schemas.user_schemas import UserCreate


# WFH schedule configuration for each user
WFH_USERS = [
    {
        'username': 'ptouser01',
        'first_name': 'PTO',
        'last_name': 'User01',
        'wfh_day': 'monday',
    },
    {
        'username': 'ptouser02',
        'first_name': 'PTO',
        'last_name': 'User02',
        'wfh_day': 'tuesday',
    },
    {
        'username': 'ptouser03',
        'first_name': 'PTO',
        'last_name': 'User03',
        'wfh_day': 'wednesday',
    },
    {
        'username': 'ptouser04',
        'first_name': 'PTO',
        'last_name': 'User04',
        'wfh_day': 'thursday',
    },
    {
        'username': 'ptouser05',
        'first_name': 'PTO',
        'last_name': 'User05',
        'wfh_day': 'friday',
    },
    {
        'username': 'ptouser06',
        'first_name': 'PTO',
        'last_name': 'User06',
        'wfh_day': 'friday',
    },
]

PASSWORD = '2ez4me!!'


def build_remote_schedule(wfh_day: str) -> dict:
    """Build remote_schedule JSON with only one day set to True."""
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    return {day: (day == wfh_day) for day in days}


def main():
    """Main function to create WFH test users."""
    print("=" * 60)
    print("Creating WFH Test Users (ptouser01-06)")
    print("=" * 60)

    db = next(get_db())
    user_service = UserService(db)

    created_count = 0
    skipped_count = 0

    try:
        for user_config in WFH_USERS:
            username = user_config['username']
            print(f"\nProcessing {username}...")

            # Check if user already exists
            existing = user_service.get_user_by_username(username)

            if existing:
                print(f"  {username} already exists (ID: {existing.id})")
                # Update the remote_schedule if it differs
                schedule = build_remote_schedule(user_config['wfh_day'])
                if existing.remote_schedule != schedule:
                    existing.remote_schedule = schedule
                    db.commit()
                    print(f"  Updated WFH day to {user_config['wfh_day'].title()}")
                else:
                    print(f"  WFH day already set to {user_config['wfh_day'].title()}")
                skipped_count += 1
                continue

            # Create new user
            print(f"  Creating {username}...")
            user_data = UserCreate(
                username=username,
                password=PASSWORD,
                email=f"{username}@ptocentral.com",
                first_name=user_config['first_name'],
                last_name=user_config['last_name'],
                role='employee',
                hire_date=date(2024, 1, 1),
                is_active=True
            )

            new_user = user_service.create_user(user_data)

            # Set the remote_schedule
            new_user.remote_schedule = build_remote_schedule(user_config['wfh_day'])
            db.commit()

            print(f"  Created {username} (ID: {new_user.id})")
            print(f"  WFH Day: {user_config['wfh_day'].title()}")
            created_count += 1

        print("\n" + "=" * 60)
        print(f"Summary: {created_count} created, {skipped_count} already existed")
        print("=" * 60)

        # Show final summary
        print("\nUser WFH Schedule:")
        print("-" * 40)
        for user_config in WFH_USERS:
            user = user_service.get_user_by_username(user_config['username'])
            if user:
                wfh_days = [d for d, v in (user.remote_schedule or {}).items() if v]
                wfh_display = ', '.join([d.title() for d in wfh_days]) or 'None'
                print(f"  {user.username}: {wfh_display}")

        print("\nAll users password: 2ez4me!!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
