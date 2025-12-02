"""
Manager Dashboard page for the PTO and Market Calendar System.

This page provides managers with functionality to view and approve/deny
pending PTO requests from their team members.
"""
import streamlit as st
from datetime import datetime
from typing import List, Optional

from src.database import get_db
from src.services.pto_service import PTOService
from src.services.balance_service import BalanceService
from streamlit_app.components.auth import require_role, get_current_user
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.formatters import format_pto_request, status_badge


# Page configuration
st.set_page_config(
    page_title="Manager Dashboard",
    page_icon="👔",
    layout="wide"
)


@require_role('Manager')
def main():
    """Main function for the Manager Dashboard page."""
    # Get current user and render sidebar
    user = get_current_user()
    if user:
        render_sidebar(user)
    
    # Main content header
    st.title("👔 Manager Dashboard - PTO Approvals")
    
    # Get database session
    db = next(get_db())
    try:
        pto_service = PTOService(db)
        balance_service = BalanceService(db)
        
        # Get pending requests
        pending_requests = pto_service.get_pending_requests()
        
        # Display pending requests section
        st.header("⏳ Pending Requests")
        st.subheader(f"Pending Requests: {len(pending_requests)}")
        
        if pending_requests:
            # Process each pending request
            for request in pending_requests:
                with st.expander(
                    f"🔍 {request.user.full_name} - {request.pto_type.title()} "
                    f"({request.start_date.strftime('%m/%d/%Y')} - {request.end_date.strftime('%m/%d/%Y')})"
                ):
                    # Display request details
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Employee:** {request.user.full_name}")
                        st.write(f"**PTO Type:** {request.pto_type.title()}")
                        st.write(f"**Dates:** {request.start_date.strftime('%B %d, %Y')} - {request.end_date.strftime('%B %d, %Y')}")
                        st.write(f"**Total Days:** {request.total_days}")
                        st.write(f"**Submitted:** {request.submitted_at.strftime('%B %d, %Y at %I:%M %p')}")
                        
                        if request.notes:
                            st.write(f"**Reason/Notes:** {request.notes}")
                        else:
                            st.write("**Reason/Notes:** None provided")
                    
                    with col2:
                        # Show employee's current balance
                        st.write("**Current Balance:**")
                        year = request.start_date.year
                        balance = balance_service.get_or_create_balance(request.user_id, year)
                        
                        if request.pto_type == 'vacation':
                            st.write(f"Vacation Available: {balance.vacation_available:.1f}")
                        elif request.pto_type == 'sick':
                            st.write(f"Sick Available: {balance.sick_available:.1f}")
                        elif request.pto_type == 'personal':
                            st.write(f"Personal Available: {balance.personal_available:.1f}")
                    
                    st.markdown("---")
                    
                    # Action buttons
                    col_approve, col_deny = st.columns(2)
                    
                    with col_approve:
                        st.write("**Approve Request:**")
                        approval_note = st.text_input(
                            "Optional approval note:",
                            key=f"approve_note_{request.id}",
                            placeholder="Optional note for approval..."
                        )
                        
                        if st.button(
                            "✅ Approve",
                            key=f"approve_{request.id}",
                            type="primary",
                            use_container_width=True
                        ):
                            try:
                                pto_service.approve_request(request.id, user.id)
                                st.success(f"✅ Request approved for {request.user.full_name}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error approving request: {str(e)}")
                    
                    with col_deny:
                        st.write("**Deny Request:**")
                        denial_reason = st.text_input(
                            "Denial reason (required):",
                            key=f"deny_reason_{request.id}",
                            placeholder="Please provide a reason for denial..."
                        )
                        
                        if st.button(
                            "❌ Deny",
                            key=f"deny_{request.id}",
                            type="secondary",
                            use_container_width=True
                        ):
                            if denial_reason.strip():
                                try:
                                    pto_service.deny_request(request.id, user.id, denial_reason)
                                    st.success(f"❌ Request denied for {request.user.full_name}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error denying request: {str(e)}")
                            else:
                                st.error("Please provide a reason for denial")
        else:
            st.success("✅ No pending approvals!")
        
        # Recently processed requests section
        st.markdown("---")
        st.header("📋 Recently Processed Requests")
        
        # Get recently processed requests (approved or denied in last 30 days)
        from sqlalchemy import select, and_, or_
        from src.models.pto_request import PTORequest
        from datetime import timedelta
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        stmt = select(PTORequest).where(
            and_(
                PTORequest.status.in_(['approved', 'denied']),
                PTORequest.approved_at >= thirty_days_ago
            )
        ).order_by(PTORequest.approved_at.desc()).limit(10)
        
        recent_requests = list(db.execute(stmt).scalars().all())
        
        if recent_requests:
            for request in recent_requests:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{request.user.full_name}** - {request.pto_type.title()}")
                        st.write(f"{request.start_date.strftime('%m/%d/%Y')} - {request.end_date.strftime('%m/%d/%Y')} ({request.total_days} days)")
                    
                    with col2:
                        st.markdown(status_badge(request.status), unsafe_allow_html=True)
                    
                    with col3:
                        if request.approved_at:
                            st.write(f"Processed: {request.approved_at.strftime('%m/%d/%Y')}")
                    
                    if request.denial_reason:
                        st.write(f"**Denial Reason:** {request.denial_reason}")
                    
                    st.markdown("---")
        else:
            st.info("No recently processed requests")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
