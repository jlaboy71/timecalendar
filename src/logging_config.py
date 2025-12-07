"""
Logging configuration for TJM Time Calendar.
"""
import os
import logging
import logging.handlers
from pathlib import Path


def setup_logging():
    """Configure application-wide logging."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    environment = os.getenv('ENVIRONMENT', 'development')

    # Create logs directory if needed
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Base format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if environment == 'development' else logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # File handler (rotating, 5MB max, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'tjm_calendar.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

    # Error file handler (separate file for errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'tjm_calendar_errors.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)

    # Set specific loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('nicegui').setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# Initialize logging on import
logger = setup_logging()
