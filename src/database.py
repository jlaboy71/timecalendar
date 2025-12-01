"""
Database configuration and session management for the PTO and Market Calendar System.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm.session import Session
from typing import Generator

from src.config import config


# Create database engine using SQLAlchemy 2.0 syntax
engine = create_engine(
    config.DATABASE_URL,
    echo=config.ENVIRONMENT == 'development',  # Enable SQL logging in development
    future=True  # Use SQLAlchemy 2.0 style
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True  # Use SQLAlchemy 2.0 style
)

# Create declarative base for model definitions
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that yields database sessions.
    
    This function creates a new database session, yields it for use,
    and ensures it's properly closed after use.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This function creates all tables defined by models that inherit
    from the Base class. Note: Models must be imported before calling
    this function to ensure they are registered with Base.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)
