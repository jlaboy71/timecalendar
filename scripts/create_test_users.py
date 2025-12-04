#!/usr/bin/env python3
"""
Script to create netuser and netmanager test accounts.

This script:
1. Connects to the database
2. Checks if users already exist (skips if they do)
3. Creates netuser with employee role
4. Creates netmanager with manager role
5. Uses UserService to properly hash passwords
6. Prints success messages
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


def main():
    """Main function to create test users."""
    print("Starting test user creation script...")
    
    # Get database session
    db = next(get_db())
    user_service = UserService(db)
    
    try:
        # Check if netuser already exists
        print("\nChecking if netuser already exists...")
        existing_netuser = user_service.get_user_by_username("netuser")
        
        if existing_netuser:
            print("netuser already exists, skipping creation")
        else:
            print("Creating netuser...")
            netuser_data = UserCreate(
                username="netuser",
                password="netpass1",
                email="netuser@tjmbrokerag.com",
                first_name="Net",
                last_name="User",
                role="employee",
                hire_date=date(2024, 1, 15),
                is_active=True
            )
            
            netuser = user_service.create_user(netuser_data)
            print(f"Successfully created netuser with ID: {netuser.id}")
        
        # Check if netmanager already exists
        print("\nChecking if netmanager already exists...")
        existing_netmanager = user_service.get_user_by_username("netmanager")
        
        if existing_netmanager:
            print("netmanager already exists, skipping creation")
        else:
            print("Creating netmanager...")
            netmanager_data = UserCreate(
                username="netmanager",
                password="netpass1",
                email="netmanager@tjmbrokerag.com",
                first_name="Net",
                last_name="Manager",
                role="manager",
                hire_date=date(2023, 6, 1),
                is_active=True
            )
            
            netmanager = user_service.create_user(netmanager_data)
            print(f"Successfully created netmanager with ID: {netmanager.id}")
        
        print("\nTest user creation completed successfully!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
