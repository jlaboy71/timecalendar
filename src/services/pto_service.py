"""
PTO service for managing PTO requests in the PTO and Market Calendar System.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.pto_request import PTORequest
from src.models.user import User
from src.schemas.pto_schemas import PTORequestCreate
from .balance_service import BalanceService


class PTOService:
    """
    Service class for managing PTO request operations.
    
    This service provides methods for creating, retrieving, approving, denying,
    and cancelling PTO requests, with proper balance management integration.
    """
    
    def __init__(self, db: Session) -> None:
        """
        Initialize the PTOService with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.balance_service = BalanceService(db)
    
    def create_request(self, request_data: PTORequestCreate) -> PTORequest:
        """
        Create a new PTO request.
        
        Args:
            request_data: PTO request creation data
            
        Returns:
            PTORequest: The created request
            
        Raises:
            ValueError: If user doesn't exist, dates are invalid, or insufficient balance
        """
        # Verify user exists
        stmt = select(User).where(User.id == request_data.user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if user is None:
            raise ValueError(f"User with ID {request_data.user_id} not found")
        
        # Validate start_date is not in the past
        if request_data.start_date < datetime.now().date():
            raise ValueError("Start date cannot be in the past")
        
        # Validate start_date <= end_date
        if request_data.start_date > request_data.end_date:
            raise ValueError("Start date must be before or equal to end date")
        
        # Extract year from start_date
        year = request_data.start_date.year
        
        # Get/create balance
        balance = self.balance_service.get_or_create_balance(request_data.user_id, year)
        
        # Check vacation balance if needed
        if request_data.pto_type == 'vacation':
            if balance.vacation_available < request_data.total_days:
                raise ValueError("Insufficient vacation balance")
        
        # Create PTORequest
        request = PTORequest(
            user_id=request_data.user_id,
            pto_type=request_data.pto_type,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            total_days=request_data.total_days,
            notes=request_data.notes,
            status='pending',
            submitted_at=datetime.now()
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        # Adjust vacation pending if needed
        if request_data.pto_type == 'vacation':
            self.balance_service.adjust_vacation_used(
                balance.id, 
                request_data.total_days, 
                is_pending=True
            )
        
        return request
    
    def get_request_by_id(self, request_id: int) -> Optional[PTORequest]:
        """
        Get PTO request by ID.
        
        Args:
            request_id: ID of the request
            
        Returns:
            Optional[PTORequest]: The request or None if not found
        """
        stmt = select(PTORequest).where(PTORequest.id == request_id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_user_requests(self, user_id: int, status: Optional[str] = None) -> List[PTORequest]:
        """
        Get all requests for a user, optionally filtered by status.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            
        Returns:
            List[PTORequest]: List of requests ordered by submitted_at descending
        """
        stmt = select(PTORequest).where(PTORequest.user_id == user_id)
        
        if status is not None:
            stmt = stmt.where(PTORequest.status == status)
        
        stmt = stmt.order_by(PTORequest.submitted_at.desc())
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def get_pending_requests(self, department_id: Optional[int] = None) -> List[PTORequest]:
        """
        Get all pending requests, optionally filtered by department.
        
        Args:
            department_id: Optional department ID filter
            
        Returns:
            List[PTORequest]: List of pending requests ordered by submitted_at ascending
        """
        stmt = select(PTORequest).where(PTORequest.status == 'pending')
        
        if department_id is not None:
            stmt = stmt.join(User).where(User.department_id == department_id)
        
        stmt = stmt.order_by(PTORequest.submitted_at.asc())
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    
    def approve_request(self, request_id: int, approved_by: int) -> PTORequest:
        """
        Approve a PTO request.
        
        Args:
            request_id: ID of the request to approve
            approved_by: ID of the user approving the request
            
        Returns:
            PTORequest: The approved request
            
        Raises:
            ValueError: If request not found or not pending
        """
        request = self.get_request_by_id(request_id)
        if request is None:
            raise ValueError(f"Request with ID {request_id} not found")
        
        if request.status != 'pending':
            raise ValueError("Only pending requests can be approved")
        
        # Get year from start_date
        year = request.start_date.year
        
        # Get balance
        balance = self.balance_service.get_or_create_balance(request.user_id, year)
        
        # Adjust balances based on PTO type
        if request.pto_type == 'vacation':
            self.balance_service.move_pending_to_used(balance.id, request.total_days)
        elif request.pto_type == 'sick':
            self.balance_service.adjust_sick_used(balance.id, request.total_days)
        elif request.pto_type == 'personal':
            self.balance_service.adjust_personal_used(balance.id, request.total_days)
        
        # Update request
        request.status = 'approved'
        request.approved_by = approved_by
        request.approved_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def deny_request(self, request_id: int, approved_by: int, denial_reason: str) -> PTORequest:
        """
        Deny a PTO request.
        
        Args:
            request_id: ID of the request to deny
            approved_by: ID of the user denying the request
            denial_reason: Reason for denial
            
        Returns:
            PTORequest: The denied request
            
        Raises:
            ValueError: If request not found or not pending
        """
        request = self.get_request_by_id(request_id)
        if request is None:
            raise ValueError(f"Request with ID {request_id} not found")
        
        if request.status != 'pending':
            raise ValueError("Only pending requests can be denied")
        
        # Get year from start_date
        year = request.start_date.year
        
        # Remove pending vacation days if needed
        if request.pto_type == 'vacation':
            balance = self.balance_service.get_or_create_balance(request.user_id, year)
            self.balance_service.remove_pending(balance.id, request.total_days)
        
        # Update request
        request.status = 'denied'
        request.approved_by = approved_by
        request.denial_reason = denial_reason
        request.approved_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def cancel_request(self, request_id: int, user_id: int) -> PTORequest:
        """
        Cancel a PTO request.
        
        Args:
            request_id: ID of the request to cancel
            user_id: ID of the user cancelling the request
            
        Returns:
            PTORequest: The cancelled request
            
        Raises:
            ValueError: If request not found, not owned by user, or not pending
        """
        request = self.get_request_by_id(request_id)
        if request is None:
            raise ValueError(f"Request with ID {request_id} not found")
        
        if request.user_id != user_id:
            raise ValueError("You can only cancel your own requests")
        
        if request.status != 'pending':
            raise ValueError("Only pending requests can be cancelled")
        
        # Get year from start_date
        year = request.start_date.year
        
        # Remove pending vacation days if needed
        if request.pto_type == 'vacation':
            balance = self.balance_service.get_or_create_balance(request.user_id, year)
            self.balance_service.remove_pending(balance.id, request.total_days)
        
        # Update request
        request.status = 'cancelled'
        
        self.db.commit()
        self.db.refresh(request)
        return request
    
    def get_overlapping_requests(
        self, 
        user_id: int, 
        start_date: date, 
        end_date: date, 
        exclude_request_id: Optional[int] = None
    ) -> List[PTORequest]:
        """
        Get overlapping requests for a user within a date range.
        
        Args:
            user_id: ID of the user
            start_date: Start date of the range
            end_date: End date of the range
            exclude_request_id: Optional request ID to exclude from results
            
        Returns:
            List[PTORequest]: List of overlapping requests
        """
        stmt = select(PTORequest).where(
            PTORequest.user_id == user_id,
            PTORequest.status.in_(['pending', 'approved']),
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date
        )
        
        if exclude_request_id is not None:
            stmt = stmt.where(PTORequest.id != exclude_request_id)
        
        result = self.db.execute(stmt)
        return list(result.scalars().all())
