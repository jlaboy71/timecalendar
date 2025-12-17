"""
Fix Chicago Leave balances - copy chicago_safe_leave values to chicago_paid_leave.

This script fixes existing employee balances after the UI change from using
chicago_safe_leave fields to chicago_paid_leave fields.

Run with: python scripts/fix_chicago_leave_balances.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.models.pto_balance import PTOBalance
from src.models.user import User


def main():
    """Fix Chicago leave balances by copying safe_leave values to paid_leave fields."""

    db = next(get_db())
    try:
        # Find all Chicago employees
        chicago_users = db.query(User).filter(
            User.location_city.ilike('chicago')
        ).all()

        if not chicago_users:
            print("No Chicago employees found.")
            return

        print(f"Found {len(chicago_users)} Chicago employees:")
        for u in chicago_users:
            print(f"  - {u.first_name} {u.last_name} (ID: {u.id})")

        chicago_user_ids = [u.id for u in chicago_users]

        # Get all balances for Chicago employees
        balances = db.query(PTOBalance).filter(
            PTOBalance.user_id.in_(chicago_user_ids)
        ).all()

        print(f"\nFound {len(balances)} balance records to check...")

        updated_count = 0
        for balance in balances:
            # Check if chicago_paid_leave_total is 0 but chicago_safe_leave_total has value
            if balance.chicago_paid_leave_total == 0 and balance.chicago_safe_leave_total > 0:
                user = next((u for u in chicago_users if u.id == balance.user_id), None)
                user_name = f"{user.first_name} {user.last_name}" if user else f"User {balance.user_id}"

                print(f"  Fixing {balance.year} balance for {user_name}:")
                print(f"    chicago_safe_leave_total: {balance.chicago_safe_leave_total}")
                print(f"    chicago_paid_leave_total: {balance.chicago_paid_leave_total} -> {balance.chicago_safe_leave_total}")

                # Copy values from safe_leave to paid_leave
                balance.chicago_paid_leave_total = balance.chicago_safe_leave_total
                balance.chicago_paid_leave_used = balance.chicago_safe_leave_used
                balance.chicago_paid_leave_pending = balance.chicago_safe_leave_pending
                balance.chicago_paid_leave_carryover = balance.chicago_safe_leave_carryover

                updated_count += 1
            elif balance.chicago_paid_leave_total == 0 and balance.chicago_safe_leave_total == 0:
                # Both are 0 - need to set default 40 hours for Chicago employees
                user = next((u for u in chicago_users if u.id == balance.user_id), None)
                user_name = f"{user.first_name} {user.last_name}" if user else f"User {balance.user_id}"

                print(f"  Setting default 40hr for {balance.year} balance for {user_name}")
                balance.chicago_paid_leave_total = 40.00
                updated_count += 1

        if updated_count > 0:
            db.commit()
            print(f"\n{'='*50}")
            print(f"Updated {updated_count} balance records.")
        else:
            print("\nNo balances needed updating - all Chicago Leave values are already set.")

    finally:
        db.close()


if __name__ == '__main__':
    main()
