"""
Logging configuration for PTO Central.
"""
import os
import sys
import logging
import logging.handlers
from pathlib import Path


class InvalidHTTPFilter(logging.Filter):
    """Filter out 'Invalid HTTP request received' messages from uvicorn."""

    def filter(self, record):
        # Filter out the annoying invalid HTTP request messages
        if hasattr(record, 'msg') and 'Invalid HTTP request received' in str(record.msg):
            return False
        return True


class StderrFilter:
    """
    Custom stderr wrapper that filters out unwanted messages.
    Used to suppress messages that bypass the logging system.
    """
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.suppressed_patterns = [
            'Invalid HTTP request received',
        ]

    def write(self, message):
        # Check if message should be suppressed
        for pattern in self.suppressed_patterns:
            if pattern in message:
                return  # Suppress this message
        self.original_stderr.write(message)

    def flush(self):
        self.original_stderr.flush()

    def __getattr__(self, name):
        return getattr(self.original_stderr, name)


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
        log_dir / 'pto_central.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

    # Error file handler (separate file for errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'pto_central_errors.log',
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)

    # Suppress noisy loggers from console output
    # SQLAlchemy engine logs
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.WARNING)
    sqlalchemy_logger.propagate = False
    sqlalchemy_logger.addHandler(file_handler)  # Still log to file

    # Watchfiles logs (hot reload)
    watchfiles_logger = logging.getLogger('watchfiles')
    watchfiles_logger.setLevel(logging.WARNING)
    watchfiles_logger.propagate = False
    watchfiles_logger.addHandler(file_handler)

    # NiceGUI logs
    nicegui_logger = logging.getLogger('nicegui')
    nicegui_logger.setLevel(logging.WARNING)
    nicegui_logger.propagate = False
    nicegui_logger.addHandler(file_handler)

    # Uvicorn access logs
    uvicorn_access = logging.getLogger('uvicorn.access')
    uvicorn_access.setLevel(logging.WARNING)
    uvicorn_access.propagate = False
    uvicorn_access.addHandler(file_handler)

    # Uvicorn error logger (startup messages)
    uvicorn_error = logging.getLogger('uvicorn.error')
    uvicorn_error.setLevel(logging.WARNING)
    uvicorn_error.propagate = False
    uvicorn_error.addHandler(file_handler)

    # Root uvicorn logger
    uvicorn_root = logging.getLogger('uvicorn')
    uvicorn_root.setLevel(logging.WARNING)
    uvicorn_root.propagate = False
    uvicorn_root.addHandler(file_handler)

    # Add filter for Invalid HTTP request messages (all handlers)
    http_filter = InvalidHTTPFilter()
    console_handler.addFilter(http_filter)

    # Wrap stderr to catch messages that bypass the logging system
    # (uvicorn prints some messages directly to stderr)
    sys.stderr = StderrFilter(sys.stderr)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# Initialize logging on import
logger = setup_logging()
