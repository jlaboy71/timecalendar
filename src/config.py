"""
Configuration module for the PTO and Market Calendar System.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """
    Configuration class that loads and validates environment variables.
    """

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Load environment variables from .env file (override=True ensures .env takes precedence)
        load_dotenv(override=True)

        # Load required environment variables
        self.DATABASE_URL = os.getenv('DATABASE_URL')
        self.SECRET_KEY = os.getenv('SECRET_KEY')
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

        # Debug mode - only True in development
        self.DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

        # SSL/HTTPS settings (optional)
        self.SSL_CERTFILE = os.getenv('TJM_SSL_CERT')
        self.SSL_KEYFILE = os.getenv('TJM_SSL_KEY')

        # Server settings
        self.HOST = os.getenv('TJM_HOST', '0.0.0.0')
        self.PORT = int(os.getenv('TJM_PORT', '8080'))

        # Validate required variables are set
        self._validate_config()

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == 'production'

    @property
    def ssl_enabled(self) -> bool:
        """Check if SSL is configured."""
        return bool(self.SSL_CERTFILE and self.SSL_KEYFILE)
    
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
