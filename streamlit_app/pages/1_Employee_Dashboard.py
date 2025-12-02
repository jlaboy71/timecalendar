"""
Employee Dashboard page for the PTO and Market Calendar System.

This page provides employees with an overview of their PTO balances,
recent requests, and quick actions for managing their time off.
"""
import streamlit as st
from datetime import datetime
from src.database import get_db
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from streamlit_app.components.auth import is_authenticated, get_current_user
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.formatters import format_balance, format_pto_request


# Page configuration
st.set_page_config(
    page_title="Employee Dashboard",
    page_icon="📊",
    layout="wide"
)

# Check authentication
if not is_authenticated():
    st.error("Please log in to access this page")
    st.stop()

# Get current user
user = get_current_user()
if not user:
    st.error("User session not found")
    st.stop()

# Render sidebar
render_sidebar(user)

# Main content header with refresh button
col1, col2 = st.columns([4, 1])
with col1:
    st.title(f"Welcome, {user.full_name}!")
    st.subheader("Your PTO Overview")
with col2:
    if st.button("🔄 Refresh", type="secondary"):
        st.rerun()

# PTO Balance section
st.markdown("---")
st.subheader("📊 PTO Balance")

try:
    # Get database session
    db = next(get_db())
    balance_service = BalanceService(db)
    
    # Get current year balance
    current_year = datetime.now().year
    balance = balance_service.get_or_create_balance(user.id, current_year)
    
    if balance:
        format_balance(balance)
    else:
        st.info("No PTO balance information available for the current year.")
        
except Exception as e:
    st.error(f"Error loading PTO balance: {str(e)}")
finally:
    if 'db' in locals():
        db.close()

# Recent Requests section
st.markdown("---")
st.subheader("📝 Recent PTO Requests")

try:
    # Get database session
    db = next(get_db())
    pto_service = PTOService(db)
    
    # Get recent requests (limit to 5)
    recent_requests = pto_service.get_user_requests(user.id)[:5]
    
    if recent_requests:
        for request in recent_requests:
            format_pto_request(request)
    else:
        st.info("No PTO requests found.")
        
except Exception as e:
    st.error(f"Error loading PTO requests: {str(e)}")
finally:
    if 'db' in locals():
        db.close()

# Quick Actions section
st.markdown("---")
st.subheader("⚡ Quick Actions")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("📝 Submit New PTO Request", type="primary", use_container_width=True):
        st.switch_page("pages/2_Submit_PTO_Request.py")

with col2:
    if st.button("📅 View Calendar", type="secondary", use_container_width=True):
        st.switch_page("pages/3_Calendar.py")
