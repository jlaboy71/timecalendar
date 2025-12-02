"""
Submit PTO Request page for the PTO and Market Calendar System.

This page allows authenticated users to submit new PTO requests with proper
validation, balance checking, and form handling.
"""
import streamlit as st
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
from typing import Optional

# Import components and services
from streamlit_app.components.auth import get_current_user, is_authenticated
from streamlit_app.components.sidebar import render_sidebar
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from src.schemas.pto_schemas import PTORequestCreate
from src.database import get_db


def calculate_business_days(start_date: date, end_date: date) -> int:
    """
    Calculate business days between two dates (excluding weekends).
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Number of business days
    """
    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Filter out weekends (Saturday=5, Sunday=6)
    business_days = date_range[date_range.weekday < 5]
    
    return len(business_days)


def display_balance_summary(balance_service: BalanceService, user_id: int) -> None:
    """
    Display current PTO balance summary for all types.
    
    Args:
        balance_service: Balance service instance
        user_id: Current user ID
    """
    current_year = datetime.now().year
    balance = balance_service.get_or_create_balance(user_id, current_year)
    
    st.subheader("📊 Current PTO Balance Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="🏖️ Vacation Days",
            value=f"{balance.vacation_available:.1f}",
            delta=f"Used: {balance.vacation_used:.1f}"
        )
    
    with col2:
        st.metric(
            label="🤒 Sick Days",
            value=f"{balance.sick_available:.1f}",
            delta=f"Used: {balance.sick_used:.1f}"
        )
    
    with col3:
        st.metric(
            label="🏠 Personal Days",
            value=f"{balance.personal_available:.1f}",
            delta=f"Used: {balance.personal_used:.1f}"
        )
    
    if balance.vacation_pending > 0:
        st.info(f"⏳ You have {balance.vacation_pending:.1f} vacation days pending approval")


def get_available_balance(balance_service: BalanceService, user_id: int, pto_type: str) -> Decimal:
    """
    Get available balance for specific PTO type.
    
    Args:
        balance_service: Balance service instance
        user_id: Current user ID
        pto_type: Type of PTO ('vacation', 'sick', 'personal')
        
    Returns:
        Available balance as Decimal
    """
    current_year = datetime.now().year
    balance = balance_service.get_or_create_balance(user_id, current_year)
    
    if pto_type == 'vacation':
        return balance.vacation_available
    elif pto_type == 'sick':
        return balance.sick_available
    elif pto_type == 'personal':
        return balance.personal_available
    else:
        return Decimal('0.00')


def main():
    """Main function for the Submit PTO Request page."""
    
    # Page configuration
    st.set_page_config(
        page_title="Submit PTO Request",
        page_icon="📝",
        layout="wide"
    )
    
    # Check authentication
    if not is_authenticated():
        st.error("Please log in to access this page")
        st.stop()
    
    # Get current user and render sidebar
    user = get_current_user()
    if user is None:
        st.error("User session not found")
        st.stop()
    
    render_sidebar(user)
    
    # Main content header
    st.title("📝 Submit New PTO Request")
    st.markdown("---")
    
    # Get database session and services
    db = next(get_db())
    try:
        balance_service = BalanceService(db)
        pto_service = PTOService(db)
        
        # Display balance summary
        display_balance_summary(balance_service, user.id)
        st.markdown("---")
        
        # PTO Request Form
        with st.form("pto_request_form"):
            st.subheader("📋 Request Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                pto_type = st.selectbox(
                    "PTO Type",
                    options=["vacation", "sick", "personal"],
                    format_func=lambda x: {
                        "vacation": "🏖️ Vacation",
                        "sick": "🤒 Sick Leave", 
                        "personal": "🏠 Personal Day"
                    }[x]
                )
                
                start_date = st.date_input(
                    "Start Date",
                    min_value=datetime.now().date(),
                    value=datetime.now().date()
                )
            
            with col2:
                end_date = st.date_input(
                    "End Date",
                    min_value=start_date if start_date else datetime.now().date(),
                    value=start_date if start_date else datetime.now().date()
                )
                
                # Display current balance for selected PTO type
                available_balance = get_available_balance(balance_service, user.id, pto_type)
                st.info(f"Available {pto_type.title()} Balance: {available_balance:.1f} days")
            
            # Notes field
            notes = st.text_area(
                "Notes (Optional)",
                placeholder="Add any additional information about your request...",
                height=100
            )
            
            # Calculate and display total days
            if start_date and end_date:
                if end_date >= start_date:
                    total_days = calculate_business_days(start_date, end_date)
                    st.info(f"📅 Total business days requested: {total_days}")
                    
                    # Check balance sufficiency
                    if pto_type == 'vacation' and total_days > available_balance:
                        st.warning(f"⚠️ Insufficient balance! You need {total_days} days but only have {available_balance:.1f} available.")
                else:
                    st.error("❌ End date must be on or after start date")
                    total_days = 0
            else:
                total_days = 0
            
            # Submit button
            submitted = st.form_submit_button(
                "🚀 Submit Request",
                type="primary",
                use_container_width=True
            )
            
            # Form validation and submission
            if submitted:
                # Validate dates
                if not start_date or not end_date:
                    st.error("❌ Please select both start and end dates")
                elif end_date < start_date:
                    st.error("❌ End date must be on or after start date")
                elif total_days <= 0:
                    st.error("❌ Request must be for at least 1 business day")
                else:
                    # Check balance for vacation requests
                    if pto_type == 'vacation' and total_days > available_balance:
                        st.error(f"❌ Insufficient vacation balance! You need {total_days} days but only have {available_balance:.1f} available.")
                    else:
                        try:
                            # Create request data
                            request_data = PTORequestCreate(
                                user_id=user.id,
                                pto_type=pto_type,
                                start_date=start_date,
                                end_date=end_date,
                                total_days=Decimal(str(total_days)),
                                notes=notes.strip() if notes else None
                            )
                            
                            # Submit request
                            new_request = pto_service.create_request(request_data)
                            
                            # Success message
                            st.success(f"✅ PTO request submitted successfully! Request ID: {new_request.id}")
                            
                            # Show request details
                            with st.expander("📋 Request Details", expanded=True):
                                st.write(f"**Type:** {pto_type.title()}")
                                st.write(f"**Dates:** {start_date} to {end_date}")
                                st.write(f"**Total Days:** {total_days}")
                                st.write(f"**Status:** Pending Approval")
                                if notes:
                                    st.write(f"**Notes:** {notes}")
                            
                            # Navigation buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📊 View Dashboard", use_container_width=True):
                                    st.switch_page("pages/1_Employee_Dashboard.py")
                            
                            with col2:
                                if st.button("📝 Submit Another Request", use_container_width=True):
                                    st.rerun()
                            
                        except ValueError as e:
                            st.error(f"❌ Error submitting request: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Unexpected error: {str(e)}")
    
    finally:
        # Close database session
        db.close()


if __name__ == "__main__":
    main()
