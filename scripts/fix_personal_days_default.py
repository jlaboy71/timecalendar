#!/usr/bin/env python3
"""
Script to fix personal days total for users where it should be 2.0.

This script:
1. Connects to the database
2. Queries all pto_balances where personal_total = 3.00
3. Updates to personal_total = 2.00 for user_id = 6 specifically
4. Prints before/after values
5. Commits changes
"""

from decimal import Decimal
from src.database import get_db
from src.models.pto_balance import PTOBalance


def main():
    """Main function to fix personal days default."""
    print("Starting personal days fix script...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Query all balances where personal_total = 3.00
        print("\nQuerying balances with personal_total = 3.00...")
        balances_with_3_days = db.query(PTOBalance).filter(
            PTOBalance.personal_total == Decimal('3.00')
        ).all()
        
        print(f"Found {len(balances_with_3_days)} balance records with personal_total = 3.00")
        
        # Show all records found
        for balance in balances_with_3_days:
            print(f"  User ID: {balance.user_id}, Year: {balance.year}, Personal Total: {balance.personal_total}")
        
        # Find and update specifically user_id = 6
        user_6_balances = [b for b in balances_with_3_days if b.user_id == 6]
        
        if not user_6_balances:
            print("\nNo balances found for user_id = 6 with personal_total = 3.00")
            return
        
        print(f"\nFound {len(user_6_balances)} balance record(s) for user_id = 6 to update:")
        
        # Update each balance for user_id = 6
        for balance in user_6_balances:
            print(f"\nUpdating balance for user_id = 6, year = {balance.year}:")
            print(f"  Before: personal_total = {balance.personal_total}")
            
            # Update to 2.00
            balance.personal_total = Decimal('2.00')
            
            print(f"  After:  personal_total = {balance.personal_total}")
        
        # Commit changes
        db.commit()
        print(f"\nSuccessfully updated {len(user_6_balances)} balance record(s) for user_id = 6")
        print("Changes committed to database.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
