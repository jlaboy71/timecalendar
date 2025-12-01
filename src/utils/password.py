"""
Password hashing and verification utilities using bcrypt.
"""
import bcrypt


class PasswordHasher:
    """Password hashing and verification using bcrypt."""
    
    def __init__(self, rounds: int = 12):
        """
        Initialize the password hasher.
        
        Args:
            rounds: Number of rounds for bcrypt (default: 12)
        """
        self.rounds = rounds
    
    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password.
        
        Args:
            password: The plain text password
            
        Returns:
            str: The hashed password
            
        Raises:
            ValueError: If password is empty
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: The plain text password
            password_hash: The hashed password
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if not password or not password_hash:
            return False
        
        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            return False


# Global instance
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Convenience function to hash a password."""
    return password_hasher.hash_password(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Convenience function to verify a password."""
    return password_hasher.verify_password(password, password_hash)
