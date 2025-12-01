"""
Configuration module for the PTO and Market Calendar System.
"""
import os
from dotenv import load_dotenv


class Config:
    """
    Configuration class that loads and validates environment variables.
    """
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Load required environment variables
        self.DATABASE_URL = os.getenv('DATABASE_URL')
        self.SECRET_KEY = os.getenv('SECRET_KEY')
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        
        # Validate required variables are set
        self._validate_config()
    
    def _validate_config(self):
        """
        Validate that all required configuration variables are set.
        
        Raises:
            ValueError: If any required configuration variable is missing.
        """
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable is required")
        
        if not self.DATABASE_URL.strip():
            raise ValueError("DATABASE_URL cannot be empty")
        
        if not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY cannot be empty")


# Create a global config instance
config = Config()
