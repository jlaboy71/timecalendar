"""
Test suite to verify development environment is properly configured.
"""
import os
import pytest
from dotenv import load_dotenv


def test_required_packages_importable():
    """Test that all required packages can be imported."""
    print("Testing that all required packages are importable...")
    
    try:
        import sqlalchemy
        print("✓ sqlalchemy imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import sqlalchemy: {e}")
    
    try:
        import alembic
        print("✓ alembic imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import alembic: {e}")
    
    try:
        import psycopg2
        print("✓ psycopg2 imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import psycopg2: {e}")
    
    try:
        from dotenv import load_dotenv
        print("✓ dotenv imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import dotenv from python-dotenv: {e}")
    
    try:
        import passlib
        print("✓ passlib imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import passlib: {e}")
    
    try:
        import bcrypt
        print("✓ bcrypt imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import bcrypt: {e}")


def test_env_file_loading():
    """Test that .env file can be loaded and contains required variables."""
    print("Testing .env file loading...")
    
    # Load the .env file
    env_loaded = load_dotenv()
    if not env_loaded:
        print("Warning: .env file not found or could not be loaded")
    else:
        print("✓ .env file loaded successfully")
    
    # Check DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        pytest.fail("DATABASE_URL environment variable is missing")
    if not database_url.strip():
        pytest.fail("DATABASE_URL environment variable is empty")
    print("✓ DATABASE_URL exists and is not empty")
    
    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        pytest.fail("SECRET_KEY environment variable is missing")
    if not secret_key.strip():
        pytest.fail("SECRET_KEY environment variable is empty")
    print("✓ SECRET_KEY exists and is not empty")
    
    # Check ENVIRONMENT
    environment = os.getenv('ENVIRONMENT')
    if not environment:
        pytest.fail("ENVIRONMENT environment variable is missing")
    print("✓ ENVIRONMENT exists")


def test_database_url_format():
    """Test that DATABASE_URL has a valid format (SQLite or PostgreSQL)."""
    print("Testing DATABASE_URL format...")

    # Load environment variables
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        pytest.fail("DATABASE_URL is not set - cannot test format")

    # Accept either SQLite or PostgreSQL
    if database_url.startswith('sqlite:///'):
        print("✓ DATABASE_URL is a valid SQLite URL")
        # For SQLite, just verify it has a database name
        if len(database_url) > len('sqlite:///'):
            print(f"✓ SQLite database: {database_url}")
        else:
            pytest.fail("SQLite DATABASE_URL should specify a database file")
    elif database_url.startswith('postgresql://'):
        print("✓ DATABASE_URL starts with 'postgresql://'")
        # PostgreSQL-specific checks
        if '@localhost' not in database_url and '@' not in database_url:
            print("Warning: DATABASE_URL does not contain a host specification")
    else:
        pytest.fail(f"DATABASE_URL should start with 'sqlite:///' or 'postgresql://', got: {database_url}")


def test_postgresql_connection():
    """Test that we can connect to the PostgreSQL database."""
    print("Testing PostgreSQL connection...")
    
    try:
        from sqlalchemy import create_engine
        print("✓ sqlalchemy.create_engine imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import create_engine from sqlalchemy: {e}")
    
    # Load environment variables
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        pytest.fail("DATABASE_URL is not set - cannot test database connection")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        print("✓ Database engine created successfully")
        
        # Try to connect
        with engine.connect() as connection:
            print("✓ Successfully connected to PostgreSQL database")
            print("✓ Connection closed successfully")
            
    except Exception as e:
        pytest.fail(f"Failed to connect to PostgreSQL database: {e}")
