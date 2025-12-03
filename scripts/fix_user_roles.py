import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

"""
Script to standardize user roles to lowercase.

This script queries all users and converts their roles to lowercase
to ensure consistency across the application.
"""

from src.database import get_db
from src.models.user import User


def main():
    """Main function to standardize user roles to lowercase."""
    # Get database session
    db = next(get_db())
    
    try:
        # Query all users
        users = db.query(User).all()
        
        print("=== ALL USERS AND THEIR CURRENT ROLES ===")
        for user in users:
            print(f"User: {user.username}, Role: '{user.role}' (type: {type(user.role)})")
        print("=" * 50)
        
        updated_count = 0
        
        # Process each user - forcibly update ALL users with non-None roles
        for user in users:
            if user.role is not None:
                old_role = user.role
                new_role = user.role.lower()
                print(f"Updated {user.username}: {old_role} -> {new_role}")
                user.role = new_role
                updated_count += 1
        
        # Commit changes
        db.commit()
        
        print(f"\nCompleted! Updated {updated_count} users with standardized roles.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
