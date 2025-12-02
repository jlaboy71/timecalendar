"""
Streamlit authentication module for the PTO and Market Calendar System.

This module provides authentication functions, decorators, and session management
for the Streamlit web application.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from functools import wraps
from typing import Optional, Callable, Any
from src.services.user_service import UserService
from src.database import get_db
from src.models.user import User


def login(username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username to authenticate
        password: Plain text password to verify
        
    Returns:
        User object if authentication successful, None otherwise
        
    Side Effects:
        - Stores user in st.session_state['user'] if successful
        - Stores user role in st.session_state['role'] if successful
        - Shows error message if authentication fails
    """
    try:
        # Get database session
        db = next(get_db())
        user_service = UserService(db)
        
        # Attempt authentication
        user = user_service.authenticate_user(username, password)
        
        if user:
            # Eagerly load department to avoid DetachedInstanceError
            _ = user.department
            # Store user information in session state
            st.session_state['user'] = user
            st.session_state['role'] = user.role
            st.session_state['authenticated'] = True
            return user
        else:
            st.error("Invalid username or password")
            return None
            
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None
    finally:
        # Close database session
        if 'db' in locals():
            db.close()


def logout() -> None:
    """
    Log out the current user by clearing session state.
    
    Side Effects:
        - Clears all authentication-related session state
        - Forces Streamlit to rerun the app
    """
    # Clear authentication session state
    if 'user' in st.session_state:
        del st.session_state['user']
    if 'role' in st.session_state:
        del st.session_state['role']
    if 'authenticated' in st.session_state:
        del st.session_state['authenticated']
    
    # Force app to rerun to show login screen
    st.rerun()


def require_auth() -> Callable:
    """
    Decorator that requires user authentication.
    
    Checks if user is logged in and redirects to login if not authenticated.
    
    Returns:
        Decorator function
        
    Usage:
        @require_auth()
        def my_protected_function():
            # This function requires authentication
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not is_authenticated():
                st.error("Please log in to access this page")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(required_role: str) -> Callable:
    """
    Decorator that requires a specific user role.
    
    Checks if user has the required role (Employee/Manager) and shows error if unauthorized.
    
    Args:
        required_role: Required role ('Employee' or 'Manager')
        
    Returns:
        Decorator function
        
    Usage:
        @require_role('Manager')
        def manager_only_function():
            # This function requires Manager role
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not is_authenticated():
                st.error("Please log in to access this page")
                st.stop()
            
            current_role = st.session_state.get('role')
            if current_role != required_role:
                st.error(f"Access denied. This page requires {required_role} role.")
                st.stop()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user() -> Optional[User]:
    """
    Get the currently authenticated user from session state.
    
    Returns:
        User object if authenticated, None otherwise
    """
    return st.session_state.get('user')


def is_authenticated() -> bool:
    """
    Check if a user is currently authenticated.
    
    Returns:
        True if user is authenticated, False otherwise
    """
    return (
        st.session_state.get('authenticated', False) and 
        st.session_state.get('user') is not None
    )


def get_current_role() -> Optional[str]:
    """
    Get the role of the currently authenticated user.
    
    Returns:
        User role string if authenticated, None otherwise
    """
    return st.session_state.get('role')


def show_login_form() -> None:
    """
    Display a login form in the Streamlit interface.
    
    This function creates a login form with username and password fields
    and handles the authentication process when submitted.
    """
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username and password:
                user = login(username, password)
                if user:
                    st.success(f"Welcome, {user.full_name}!")
                    st.rerun()
            else:
                st.error("Please enter both username and password")


def show_user_info() -> None:
    """
    Display current user information in the sidebar.
    
    Shows user details and logout button if authenticated.
    """
    if is_authenticated():
        user = get_current_user()
        if user:
            st.sidebar.markdown("---")
            st.sidebar.markdown("**Current User:**")
            st.sidebar.markdown(f"👤 {user.full_name}")
            st.sidebar.markdown(f"🏢 {user.role}")
            st.sidebar.markdown(f"📧 {user.email}")
            
            if st.sidebar.button("Logout"):
                logout()
