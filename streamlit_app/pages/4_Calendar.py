"""
Calendar View page for the PTO and Market Calendar System.

This page displays a visual calendar showing market holidays and user PTO requests,
with month/year navigation and detailed list views.
"""
import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, extract

from streamlit_app.components.auth import (
    is_authenticated, 
    get_current_user, 
    show_login_form
)
from streamlit_app.components.sidebar import render_sidebar
from src.database import get_db
from src.models.market_holiday import MarketHoliday
from src.models.pto_request import PTORequest
from src.services.pto_service import PTOService


# Page configuration
st.set_page_config(
    page_title="Calendar View",
    page_icon="📅",
    layout="wide"
)


def get_market_holidays_for_month(db: Session, year: int, month: int) -> List[MarketHoliday]:
    """Get market holidays for a specific month and year."""
    stmt = select(MarketHoliday).where(
        and_(
            extract('year', MarketHoliday.holiday_date) == year,
            extract('month', MarketHoliday.holiday_date) == month,
            MarketHoliday.is_observed == True
        )
    ).order_by(MarketHoliday.holiday_date)
    
    result = db.execute(stmt)
    return list(result.scalars().all())


def get_user_pto_for_month(db: Session, user_id: int, year: int, month: int) -> List[PTORequest]:
    """Get user's PTO requests that overlap with a specific month and year."""
    # Create date range for the month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)
    
    stmt = select(PTORequest).where(
        and_(
            PTORequest.user_id == user_id,
            PTORequest.status.in_(['approved', 'pending']),
            PTORequest.start_date < last_day,
            PTORequest.end_date >= first_day
        )
    ).order_by(PTORequest.start_date)
    
    result = db.execute(stmt)
    return list(result.scalars().all())


def create_calendar_dataframe(year: int, month: int, holidays: List[MarketHoliday], 
                            pto_requests: List[PTORequest]) -> pd.DataFrame:
    """Create a calendar DataFrame with holidays and PTO marked."""
    # Get calendar for the month
    cal = calendar.monthcalendar(year, month)
    
    # Create holiday lookup
    holiday_dates = {h.holiday_date.day for h in holidays if h.holiday_date.month == month}
    
    # Create PTO lookup
    approved_pto_dates = set()
    pending_pto_dates = set()
    
    for pto in pto_requests:
        # Get all dates in the PTO request that fall in this month
        current_date = max(pto.start_date, date(year, month, 1))
        end_date = min(pto.end_date, date(year, month, calendar.monthrange(year, month)[1]))
        
        while current_date <= end_date:
            if current_date.month == month:
                if pto.status == 'approved':
                    approved_pto_dates.add(current_date.day)
                elif pto.status == 'pending':
                    pending_pto_dates.add(current_date.day)
            current_date = date(current_date.year, current_date.month, current_date.day + 1)
    
    # Create DataFrame
    weeks = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append("")
            else:
                cell_content = str(day)
                
                # Add markers
                if day in holiday_dates:
                    cell_content += " 🏦"
                if day in approved_pto_dates:
                    cell_content += " ✅"
                if day in pending_pto_dates:
                    cell_content += " ⏳"
                
                # Check if weekend
                day_of_week = date(year, month, day).weekday()
                if day_of_week >= 5:  # Saturday = 5, Sunday = 6
                    cell_content = f"*{cell_content}*"
                
                week_data.append(cell_content)
        weeks.append(week_data)
    
    # Create DataFrame with day names as columns
    df = pd.DataFrame(weeks, columns=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    return df


def display_legend():
    """Display the calendar legend."""
    st.markdown("### 📋 Legend")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("🏦 **Market Holidays**")
    with col2:
        st.markdown("✅ **Your Approved PTO**")
    with col3:
        st.markdown("⏳ **Your Pending PTO**")
    
    st.markdown("*Weekends are shown in italics*")
    st.markdown("---")


def display_market_holidays_list(holidays: List[MarketHoliday]):
    """Display list of market holidays for the month."""
    st.markdown("### 🏦 Market Holidays This Month")
    
    if not holidays:
        st.info("No market holidays this month.")
        return
    
    for holiday in holidays:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{holiday.name}**")
        with col2:
            st.write(holiday.holiday_date.strftime("%A, %B %d"))
        with col3:
            st.write(holiday.market)


def display_pto_list(pto_requests: List[PTORequest]):
    """Display list of user's PTO requests for the month."""
    st.markdown("### 📝 Your PTO This Month")
    
    if not pto_requests:
        st.info("No PTO requests this month.")
        return
    
    # Group by status
    approved_requests = [r for r in pto_requests if r.status == 'approved']
    pending_requests = [r for r in pto_requests if r.status == 'pending']
    
    if approved_requests:
        with st.expander(f"✅ Approved PTO ({len(approved_requests)} requests)", expanded=True):
            for request in approved_requests:
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.write(f"**{request.pto_type.title()}**")
                with col2:
                    if request.start_date == request.end_date:
                        st.write(request.start_date.strftime("%B %d, %Y"))
                    else:
                        st.write(f"{request.start_date.strftime('%b %d')} - {request.end_date.strftime('%b %d, %Y')}")
                with col3:
                    st.write(f"{request.total_days} days")
                with col4:
                    st.success("Approved")
                
                if request.notes:
                    st.caption(f"Notes: {request.notes}")
    
    if pending_requests:
        with st.expander(f"⏳ Pending PTO ({len(pending_requests)} requests)", expanded=True):
            for request in pending_requests:
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.write(f"**{request.pto_type.title()}**")
                with col2:
                    if request.start_date == request.end_date:
                        st.write(request.start_date.strftime("%B %d, %Y"))
                    else:
                        st.write(f"{request.start_date.strftime('%b %d')} - {request.end_date.strftime('%b %d, %Y')}")
                with col3:
                    st.write(f"{request.total_days} days")
                with col4:
                    st.warning("Pending")
                
                if request.notes:
                    st.caption(f"Notes: {request.notes}")


def main():
    """Main function for the Calendar View page."""
    # Check authentication
    if not is_authenticated():
        show_login_form()
        st.stop()
    
    # Get current user and render sidebar
    user = get_current_user()
    if not user:
        st.error("User session not found. Please log in again.")
        st.stop()
    
    render_sidebar(user)
    
    # Main content header
    st.title("📅 Calendar - Market Holidays & PTO")
    
    # Month/Year selector
    st.markdown("### 📆 Select Month and Year")
    col1, col2 = st.columns(2)
    
    current_date = datetime.now()
    
    with col1:
        selected_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=current_date.month - 1,
            format_func=lambda x: calendar.month_name[x]
        )
    
    with col2:
        selected_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2030,
            value=current_date.year,
            step=1
        )
    
    st.markdown("---")
    
    # Display legend
    display_legend()
    
    # Get database session and fetch data
    try:
        db = next(get_db())
        
        # Get market holidays for the month
        holidays = get_market_holidays_for_month(db, selected_year, selected_month)
        
        # Get user's PTO for the month
        pto_requests = get_user_pto_for_month(db, user.id, selected_year, selected_month)
        
        # Create and display calendar
        st.markdown(f"### 📅 {calendar.month_name[selected_month]} {selected_year}")
        
        calendar_df = create_calendar_dataframe(selected_year, selected_month, holidays, pto_requests)
        
        # Display calendar using st.dataframe with styling
        st.dataframe(
            calendar_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                col: st.column_config.TextColumn(
                    col,
                    width="medium",
                    help=f"{col} column"
                ) for col in calendar_df.columns
            }
        )
        
        st.markdown("---")
        
        # Display detailed lists
        col1, col2 = st.columns(2)
        
        with col1:
            display_market_holidays_list(holidays)
        
        with col2:
            display_pto_list(pto_requests)
    
    except Exception as e:
        st.error(f"Error loading calendar data: {str(e)}")
    
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    main()
