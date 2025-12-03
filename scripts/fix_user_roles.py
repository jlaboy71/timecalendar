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
        
        updated_count = 0
        
        # Process each user
        for user in users:
            # Check if user has a role and it's not None
            if user.role and user.role != user.role.lower():
                print(f"Updating user {user.username}: '{user.role}' -> '{user.role.lower()}'")
                user.role = user.role.lower()
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
