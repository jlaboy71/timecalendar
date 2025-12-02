#!/usr/bin/env python3
"""
Script to update the netadmin user's role to 'Manager'.

This script connects to the database, finds the user with username 'netadmin',
updates their role to 'Manager', and commits the changes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.models.user import User


def main():
    """Update netadmin user's role to Manager."""
    try:
        # Get database session
        db = next(get_db())
        
        # Find the netadmin user
        netadmin_user = db.query(User).filter(User.username == 'netadmin').first()
        
        if not netadmin_user:
            print("Error: User 'netadmin' not found in the database.")
            return
        
        # Check current role
        current_role = netadmin_user.role
        print(f"Current role for user 'netadmin': {current_role}")
        
        # Update role to Manager
        netadmin_user.role = 'Manager'
        
        # Commit the changes
        db.commit()
        
        print(f"Successfully updated user 'netadmin' role from '{current_role}' to 'Manager'")
        
    except Exception as e:
        print(f"Error updating netadmin user role: {str(e)}")
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    main()
