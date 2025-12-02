"""
Formatting helpers for Streamlit displays in the PTO and Market Calendar System.

This module provides utility functions to format and display various data objects
in a consistent and visually appealing way using Streamlit components.
"""
from typing import Optional
import streamlit as st
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.models.market_holiday import MarketHoliday


def format_balance(balance_obj: PTOBalance) -> None:
    """
    Display PTO balance information using Streamlit components.
    
    Args:
        balance_obj: PTOBalance object to display
    """
    # Vacation Balance
    st.subheader("🏖️ Vacation Balance")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Available", f"{balance_obj.vacation_available:.1f}")
    with col2:
        st.metric("Total", f"{balance_obj.vacation_total:.1f}")
    with col3:
        st.metric("Used", f"{balance_obj.vacation_used:.1f}")
    with col4:
        st.metric("Pending", f"{balance_obj.vacation_pending:.1f}")
    
    # Sick Leave Balance
    st.subheader("🤒 Sick Leave Balance")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Available", f"{balance_obj.sick_available:.1f}")
    with col2:
        st.metric("Total", f"{balance_obj.sick_total:.1f}")
    with col3:
        st.metric("Used", f"{balance_obj.sick_used:.1f}")
    
    # Personal Days Balance
    st.subheader("👤 Personal Days Balance")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Available", f"{balance_obj.personal_available:.1f}")
    with col2:
        st.metric("Total", f"{balance_obj.personal_total:.1f}")
    with col3:
        st.metric("Used", f"{balance_obj.personal_used:.1f}")


def format_pto_request(request_obj: PTORequest) -> None:
    """
    Display PTO request details in card format using Streamlit container.
    
    Args:
        request_obj: PTORequest object to display
    """
    with st.container():
        st.markdown("---")
        
        # Header with status badge
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"{request_obj.pto_type.title()} Request")
        with col2:
            st.markdown(status_badge(request_obj.status), unsafe_allow_html=True)
        
        # Date range
        start_date_str = request_obj.start_date.strftime("%b %d, %Y")
        end_date_str = request_obj.end_date.strftime("%b %d, %Y")
        st.write(f"**Dates:** {start_date_str} - {end_date_str}")
        
        # Days requested
        st.write(f"**Days Requested:** {request_obj.total_days}")
        
        # Submitted date
        submitted_str = request_obj.submitted_at.strftime("%b %d, %Y")
        st.write(f"**Submitted:** {submitted_str}")
        
        # Notes if present
        if request_obj.notes:
            st.write(f"**Notes:** {request_obj.notes}")
        
        # Denial reason if present
        if request_obj.denial_reason:
            st.write(f"**Denial Reason:** {request_obj.denial_reason}")
        
        # Approval info if approved
        if request_obj.is_approved and request_obj.approved_at:
            approved_str = request_obj.approved_at.strftime("%b %d, %Y")
            st.write(f"**Approved:** {approved_str}")


def format_market_holiday(holiday_obj: MarketHoliday) -> None:
    """
    Display market holiday information with calendar emoji and formatted date.
    
    Args:
        holiday_obj: MarketHoliday object to display
    """
    with st.container():
        # Holiday name with calendar emoji
        st.subheader(f"📅 {holiday_obj.name}")
        
        # Date formatted nicely
        date_str = holiday_obj.holiday_date.strftime("%b %d, %Y")
        st.write(f"**Date:** {date_str}")
        
        # Market
        st.write(f"**Market:** {holiday_obj.market}")
        
        # Observed status
        if holiday_obj.is_observed:
            st.write("**Status:** ✅ Observed")
        else:
            st.write("**Status:** ❌ Not Observed")


def status_badge(status: str) -> str:
    """
    Return colored HTML badge for status display.
    
    Args:
        status: Status string (pending, approved, denied)
        
    Returns:
        HTML string for colored status badge
    """
    status_lower = status.lower()
    
    if status_lower == "pending":
        return '<span style="background-color: #FFA500; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">⏳ PENDING</span>'
    elif status_lower == "approved":
        return '<span style="background-color: #28A745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">✅ APPROVED</span>'
    elif status_lower == "denied":
        return '<span style="background-color: #DC3545; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">❌ DENIED</span>'
    else:
        return f'<span style="background-color: #6C757D; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{status.upper()}</span>'
