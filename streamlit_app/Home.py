"""
Main Streamlit application entry point for the PTO & Market Calendar System.

This is the home page that handles user authentication and redirects
authenticated users to the appropriate dashboard.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from components.auth import is_authenticated, show_login_form


def main():
    """
    Main function for the Home page.
    
    Handles page configuration, authentication checks, and displays
    either the login form or redirects to the employee dashboard.
    """
    # Configure the page
    st.set_page_config(
        page_title="PTO & Market Calendar System",
        page_icon="📅",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    try:
        # Check if user is already authenticated
        if is_authenticated():
            # Redirect to employee dashboard
            st.switch_page("pages/1_Employee_Dashboard.py")
        else:
            # Show login page for unauthenticated users
            show_login_page()
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please refresh the page and try again.")


def show_login_page():
    """
    Display the login page with centered content.
    
    Shows the application title, subtitle, and login form
    in a centered layout for better visual appearance.
    """
    # Create centered columns for better layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # App title and subtitle
        st.title("📅 PTO & Market Calendar System")
        st.subheader("Please log in to continue")
        
        # Add some spacing
        st.markdown("---")
        
        # Show the login form
        show_login_form()
        
        # Add footer information
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666;'>"
            "<small>Employee Time-Off Management & Market Calendar System</small>"
            "</div>", 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()
