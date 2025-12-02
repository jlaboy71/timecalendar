"""
Sidebar component for the PTO and Market Calendar System.

This module provides a sidebar component that displays user information,
role-based navigation, and logout functionality.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.models.user import User
from components.auth import logout


def render_sidebar(user: User) -> None:
    """
    Render the sidebar with user info, navigation, and logout.
    
    Args:
        user: The authenticated user object
        
    Side Effects:
        - Displays user information in sidebar
        - Shows role-based navigation links
        - Provides logout functionality
    """
    # User Info Section
    st.sidebar.markdown("### 👤 User Information")
    st.sidebar.markdown(f"**Welcome, {user.full_name}!**")
    st.sidebar.markdown(f"📧 {user.email}")
    
    # Show department if it exists
    if user.department:
        st.sidebar.markdown(f"🏢 {user.department.name}")
    
    # Role badge with emoji
    role_emoji = "👔" if user.role == "Manager" else "👤"
    st.sidebar.markdown(f"{role_emoji} **{user.role}**")
    
    st.sidebar.markdown("---")
    
    # Navigation Section
    st.sidebar.markdown("### 🧭 Navigation")
    
    # Common navigation for all users
    st.sidebar.page_link("pages/1_Employee_Dashboard.py", label="📊 Dashboard")
    st.sidebar.page_link("pages/2_Submit_PTO_Request.py", label="📝 Submit PTO")
    st.sidebar.page_link("pages/4_Calendar.py", label="📅 Calendar")
    
    # Manager-only navigation
    if user.role == "Manager":
        st.sidebar.page_link("pages/3_Manager_Dashboard.py", label="👔 Manager Dashboard")
    
    st.sidebar.markdown("---")
    
    # Logout Section
    if st.sidebar.button("🚪 Logout", type="primary", use_container_width=True):
        logout()
