"""Password hashing utilities using bcrypt.

This module provides secure password hashing and verification functionality
using the bcrypt algorithm. It includes both a class-based interface for
configurable hashing and module-level convenience functions.
"""

import bcrypt
from typing import Union


class PasswordHasher:
    """A password hasher using bcrypt algorithm.
    
    This class provides methods to hash passwords and verify them against
    stored hashes using the bcrypt algorithm with configurable rounds.
    """
    
    def __init__(self, rounds: int = 12) -> None:
        """Initialize the password hasher.
        
        Args:
            rounds: The number of bcrypt rounds to use for hashing.
                   Higher values are more secure but slower. Default is 12.
        """
        self.rounds = rounds
    
    def hash_password(self, password: str) -> str:
        """Hash a plain text password.
        
        Args:
            password: The plain text password to hash.
            
        Returns:
            The bcrypt hash of the password as a string.
            
        Raises:
            ValueError: If password is None or empty.
        """
        if not password:
            raise ValueError("Password cannot be None or empty")
        
        # Convert string to bytes, hash it, then convert back to string
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a stored hash.
        
        Args:
            password: The plain text password to verify.
            password_hash: The stored bcrypt hash to verify against.
            
        Returns:
            True if the password matches the hash, False otherwise.
            Returns False on any error (invalid inputs, malformed hash, etc.).
        """
        try:
            if not password or not password_hash:
                return False
            
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            # Return False on any error (malformed hash, encoding issues, etc.)
            return False


# Global instance for convenience functions
_default_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plain text password using default settings.
    
    This is a convenience function that uses a global PasswordHasher
    instance with default settings (12 rounds).
    
    Args:
        password: The plain text password to hash.
        
    Returns:
        The bcrypt hash of the password as a string.
        
    Raises:
        ValueError: If password is None or empty.
    """
    return _default_hasher.hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash using default settings.
    
    This is a convenience function that uses a global PasswordHasher
    instance with default settings.
    
    Args:
        password: The plain text password to verify.
        password_hash: The stored bcrypt hash to verify against.
        
    Returns:
        True if the password matches the hash, False otherwise.
        Returns False on any error.
    """
    return _default_hasher.verify_password(password, password_hash)
