"""
PTO service for managing PTO requests in the PTO and Market Calendar System.
"""
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.pto_request import PTORequest
from ..models.user import User
from ..schemas.pto_schemas import PTORequestCreate
from .balance_service import BalanceService

logger = logging.getLogger(__name__)

# PTO types eligible for trusted employee auto-approve
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}

# PTO types that ALWAYS require manager approval regardless of trust status
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}


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

        # Validate request is within reasonable future range (5 years ahead max)
        # This allows long-term planning while preventing accidental far-future requests
        current_year = datetime.now().year
        max_future_years = 5
        if year > current_year + max_future_years:
            raise ValueError(f"Cannot request time off more than {max_future_years} years in advance. Maximum year: {current_year + max_future_years}")

        # Get/create balance WITH LOCK to prevent concurrent request race conditions
        # This serializes all PTO requests for the same user
        balance = self.balance_service.get_or_create_balance(request_data.user_id, year)

        # Lock the balance row to serialize concurrent requests for this user
        # This prevents two concurrent requests from both passing the overlap check
        from src.models.pto_balance import PTOBalance
        stmt = select(PTOBalance).where(PTOBalance.id == balance.id).with_for_update()
        self.db.execute(stmt).scalar_one_or_none()

        # Check for overlapping requests (same user, same dates)
        # Now protected by the lock above
        overlapping = self.get_overlapping_requests(
            request_data.user_id,
            request_data.start_date,
            request_data.end_date
        )
        if overlapping:
            overlap_info = overlapping[0]
            raise ValueError(
                f"You already have a {overlap_info.status} {overlap_info.pto_type} request "
                f"for {overlap_info.start_date.strftime('%b %d')} - {overlap_info.end_date.strftime('%b %d, %Y')}. "
                f"Please cancel or modify that request first."
            )

        # Validate vacation balance - employees cannot request more than available
        # Managers/admins can exceed since they have approval authority
        # This prevents regular employees from submitting over-limit requests
        hours_requested_check = float(request_data.total_days) * 8
        if request_data.pto_type == 'vacation':
            vacation_available = float(balance.vacation_total or 0) - float(balance.vacation_used or 0) - float(balance.vacation_pending or 0)
            # Only enforce for non-managers/admins - they have discretion to exceed
            if user.role == 'employee' and hours_requested_check > vacation_available:
                raise ValueError(
                    f"Insufficient vacation time. Requesting {request_data.total_days} days "
                    f"but only {vacation_available / 8:.1f} days available."
                )

        # Determine if auto-approve applies
        # BUSINESS RULE: The following users can self-approve standard PTO types:
        #   1. Managers, Admins, Superadmins - they have authority to approve their own PTO
        #   2. Trusted Employees - flagged by admin, their PTO auto-approves with manager notification
        # NOTE: If your organization requires manager PTO to be approved by their manager,
        # change line 111 condition to exclude managers, or implement approval chain.
        # Current behavior: Managers self-approve (documented in help system and audit trail).
        pto_type_lower = request_data.pto_type.lower()
        is_auto_approve = False
        auto_approve_reason = None

        # Manager/Admin/Superadmin: auto-approve standard PTO types only
        if user.role in ['manager', 'admin', 'superadmin']:
            if pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
                is_auto_approve = True
                auto_approve_reason = f"Self-approved by {user.role}"
            # Special leave types (FMLA, Bereavement, etc.) still need documentation/approval

        # Trusted Employee: auto-approve ONLY for vacation, sick, personal
        elif user.is_trusted and pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
            is_auto_approve = True
            auto_approve_reason = "Auto-approved (trusted employee)"

        # All other combinations: requires approval
        # - Non-trusted employees: always pending
        # - Bereavement, FMLA, Jury Duty, Voting, Military, WFH: always pending

        # Validate sick/personal days don't exceed available balance
        # These have hard limits unlike vacation (which is manager discretion)
        hours_requested = float(request_data.total_days) * 8
        if request_data.pto_type == 'sick':
            available = float(balance.sick_total or 0) - float(balance.sick_used or 0)
            if hours_requested > available:
                raise ValueError(
                    f"Insufficient sick time. Requesting {request_data.total_days} days "
                    f"but only {available / 8:.1f} days available."
                )
        elif request_data.pto_type == 'personal':
            available = float(balance.personal_total or 0) - float(balance.personal_used or 0)
            if hours_requested > available:
                raise ValueError(
                    f"Insufficient personal time. Requesting {request_data.total_days} days "
                    f"but only {available / 8:.1f} days available."
                )

        # Create PTORequest
        request = PTORequest(
            user_id=request_data.user_id,
            pto_type=request_data.pto_type,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            total_days=request_data.total_days,
            notes=request_data.notes,
            is_private=request_data.is_private,
            status='approved' if is_auto_approve else 'pending',
            submitted_at=datetime.now(),
            approved_by=user.id if is_auto_approve else None,
            approved_at=datetime.now() if is_auto_approve else None
        )

        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)

        # Audit log for auto-approved requests
        if is_auto_approve:
            logger.info(
                f"PTO AUTO-APPROVED: Request #{request.id} for user {user.username} (ID:{user.id}), "
                f"Type: {request.pto_type}, Days: {request.total_days}, "
                f"Dates: {request.start_date} to {request.end_date}, "
                f"Reason: {auto_approve_reason}"
            )

        # Handle balance adjustments based on auto-approval status
        if is_auto_approve:
            # For auto-approved requests, directly deduct from used (not pending)
            if request_data.pto_type == 'vacation':
                self.balance_service.adjust_vacation_used(
                    balance.id,
                    request_data.total_days,
                    is_pending=False
                )
            elif request_data.pto_type == 'sick':
                self.balance_service.adjust_sick_used(balance.id, request_data.total_days)
            elif request_data.pto_type == 'personal':
                self.balance_service.adjust_personal_used(balance.id, request_data.total_days)
        else:
            # For regular employees, add to pending
            if request_data.pto_type == 'vacation':
                self.balance_service.adjust_vacation_used(
                    balance.id,
                    request_data.total_days,
                    is_pending=True
                )

        # MANDATORY: Notify manager of all PTO requests (regardless of auto-approve)
        try:
            from .notification_service import NotificationService
            notification_service = NotificationService(self.db)
            notification_service.notify_manager_of_request(request, user)
        except Exception as e:
            # Don't fail the request if notification fails
            import logging
            logging.getLogger(__name__).error(f"Failed to notify manager: {e}")

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
    
    @staticmethod
    def get_pending_requests_with_employee_info(db: Session):
        """Get all pending PTO requests with employee information and department"""
        from ..models.pto_request import PTORequest
        from ..models.user import User
        from ..models.department import Department

        stmt = select(
            PTORequest.id.label('request_id'),
            PTORequest.user_id,
            (User.first_name + ' ' + User.last_name).label('employee_name'),
            User.department_id.label('employee_department_id'),
            Department.name.label('department_name'),
            PTORequest.pto_type,
            PTORequest.start_date,
            PTORequest.end_date,
            PTORequest.total_days,
            PTORequest.submitted_at
        ).join(User, PTORequest.user_id == User.id
        ).outerjoin(Department, User.department_id == Department.id
        ).where(PTORequest.status == 'pending'
        ).order_by(PTORequest.submitted_at.desc())

        results = db.execute(stmt).all()
        return [dict(row._mapping) for row in results]

    @staticmethod
    def get_cancellation_requests_with_employee_info(db: Session, department_id: int = None):
        """Get approved PTO requests with cancellation requested, with employee information."""
        from ..models.pto_request import PTORequest
        from ..models.user import User
        from ..models.department import Department

        stmt = select(
            PTORequest.id.label('request_id'),
            PTORequest.user_id,
            (User.first_name + ' ' + User.last_name).label('employee_name'),
            User.department_id.label('employee_department_id'),
            Department.name.label('department_name'),
            PTORequest.pto_type,
            PTORequest.start_date,
            PTORequest.end_date,
            PTORequest.total_days,
            PTORequest.cancellation_reason,
            PTORequest.cancellation_requested_at
        ).join(User, PTORequest.user_id == User.id
        ).outerjoin(Department, User.department_id == Department.id
        ).where(
            PTORequest.status == 'approved',
            PTORequest.cancellation_requested == True
        )

        if department_id:
            stmt = stmt.where(User.department_id == department_id)

        stmt = stmt.order_by(PTORequest.cancellation_requested_at.desc())
        results = db.execute(stmt).all()
        return [dict(row._mapping) for row in results]

    @staticmethod
    def get_user_requests(db: Session, user_id: int):
        """Get all PTO requests for a specific user"""
        from ..models.pto_request import PTORequest

        stmt = select(PTORequest).where(
            PTORequest.user_id == user_id
        ).order_by(PTORequest.submitted_at.desc())

        return list(db.execute(stmt).scalars().all())
    
    @staticmethod
    def get_request_detail(db: Session, request_id: int):
        """Get detailed request info with employee data"""
        from ..models.pto_request import PTORequest
        from ..models.user import User
        from ..models.pto_balance import PTOBalance

        stmt = select(PTORequest).where(PTORequest.id == request_id)
        request = db.execute(stmt).scalar_one_or_none()
        if not request:
            return None

        stmt = select(User).where(User.id == request.user_id)
        user = db.execute(stmt).scalar_one_or_none()
        if not user:
            return None

        # Use the year from the request's start date
        request_year = request.start_date.year
        stmt = select(PTOBalance).where(
            PTOBalance.user_id == request.user_id,
            PTOBalance.year == request_year
        )
        balance = db.execute(stmt).scalar_one_or_none()

        return {
            'request': request,
            'employee_name': f"{user.first_name} {user.last_name}",
            'employee_email': user.email,
            'employee_department_id': user.department_id,
            'employee_department_name': user.department.name if user.department else 'No Department',
            'balance': balance
        }

    @staticmethod
    def _verify_approval_authorization(db: Session, request: PTORequest, approver_id: int) -> None:
        """
        Verify that the approver is authorized to approve/deny the request.

        Args:
            db: SQLAlchemy database session
            request: The PTO request being approved/denied
            approver_id: ID of the user attempting to approve/deny

        Raises:
            ValueError: If approver is not authorized
        """
        from src.models.user import User

        stmt = select(User).where(User.id == approver_id)
        approver = db.execute(stmt).scalar_one_or_none()
        if approver is None:
            raise ValueError("Approver not found")

        # Admins and superadmins can approve any request
        if approver.role in ['admin', 'superadmin']:
            return

        # Managers can only approve requests from their department
        if approver.role == 'manager':
            stmt = select(User).where(User.id == request.user_id)
            employee = db.execute(stmt).scalar_one_or_none()
            if employee and employee.department_id == approver.department_id:
                return
            raise ValueError("Managers can only approve requests from their own department")

        # Regular employees cannot approve requests
        raise ValueError("You are not authorized to approve requests")

    @staticmethod
    def approve_request(db: Session, request_id: int, approved_by: int) -> PTORequest:
        """
        Approve a PTO request.

        All database operations are wrapped in a single transaction.
        If any step fails, all changes are rolled back.

        Args:
            db: SQLAlchemy database session
            request_id: ID of the request to approve
            approved_by: ID of the user approving the request

        Returns:
            PTORequest: The approved request

        Raises:
            ValueError: If request not found, not pending, or approver not authorized
        """
        stmt = select(PTORequest).where(PTORequest.id == request_id)
        request = db.execute(stmt).scalar_one_or_none()
        if request is None:
            raise ValueError(f"Request with ID {request_id} not found")

        if request.status != 'pending':
            raise ValueError("Only pending requests can be approved")

        # Verify approver is authorized
        PTOService._verify_approval_authorization(db, request, approved_by)

        # Get year from start_date
        year = request.start_date.year

        # Get balance (don't commit yet - part of transaction)
        balance_service = BalanceService(db)
        balance = balance_service.get_or_create_balance(request.user_id, year, commit=False)

        # Validate sick/personal days don't exceed available balance before approving
        hours_requested = float(request.total_days) * 8
        if request.pto_type == 'sick':
            available = float(balance.sick_total or 0) - float(balance.sick_used or 0)
            if hours_requested > available:
                raise ValueError(
                    f"Cannot approve: insufficient sick time. Request is for {request.total_days} days "
                    f"but only {available / 8:.1f} days available."
                )
        elif request.pto_type == 'personal':
            available = float(balance.personal_total or 0) - float(balance.personal_used or 0)
            if hours_requested > available:
                raise ValueError(
                    f"Cannot approve: insufficient personal time. Request is for {request.total_days} days "
                    f"but only {available / 8:.1f} days available."
                )

        try:
            # Adjust balances based on PTO type (don't commit - part of transaction)
            if request.pto_type == 'vacation':
                balance_service.move_pending_to_used(balance.id, request.total_days, commit=False)
            elif request.pto_type == 'sick':
                balance_service.adjust_sick_used(balance.id, request.total_days, commit=False)
            elif request.pto_type == 'personal':
                balance_service.adjust_personal_used(balance.id, request.total_days, commit=False)

            # Update request
            request.status = 'approved'
            request.approved_by = approved_by
            request.approved_at = datetime.now()

            # Commit all changes atomically
            db.commit()
            db.refresh(request)
            return request

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to approve request {request_id}: {e}")
            raise
    
    @staticmethod
    def deny_request(db: Session, request_id: int, approved_by: int, denial_reason: str) -> PTORequest:
        """
        Deny a PTO request.

        All database operations are wrapped in a single transaction.
        If any step fails, all changes are rolled back.

        Args:
            db: SQLAlchemy database session
            request_id: ID of the request to deny
            approved_by: ID of the user denying the request
            denial_reason: Reason for denial

        Returns:
            PTORequest: The denied request

        Raises:
            ValueError: If request not found, not pending, or approver not authorized
        """
        stmt = select(PTORequest).where(PTORequest.id == request_id)
        request = db.execute(stmt).scalar_one_or_none()
        if request is None:
            raise ValueError(f"Request with ID {request_id} not found")

        if request.status != 'pending':
            raise ValueError("Only pending requests can be denied")

        # Verify approver is authorized
        PTOService._verify_approval_authorization(db, request, approved_by)

        try:
            # Get year from start_date
            year = request.start_date.year

            # Remove pending vacation days if needed (don't commit - part of transaction)
            if request.pto_type == 'vacation':
                balance_service = BalanceService(db)
                balance = balance_service.get_or_create_balance(request.user_id, year, commit=False)
                balance_service.remove_pending(balance.id, request.total_days, commit=False)

            # Update request
            request.status = 'denied'
            request.approved_by = approved_by
            request.denial_reason = denial_reason
            request.approved_at = datetime.now()

            # Commit all changes atomically
            db.commit()
            db.refresh(request)
            return request

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to deny request {request_id}: {e}")
            raise
    
    def cancel_request(self, request_id: int, user_id: int) -> PTORequest:
        """
        Cancel a PTO request.

        All database operations are wrapped in a single transaction.
        If any step fails, all changes are rolled back.

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

        try:
            # Get year from start_date
            year = request.start_date.year

            # Remove pending vacation days if needed (don't commit - part of transaction)
            if request.pto_type == 'vacation':
                balance = self.balance_service.get_or_create_balance(request.user_id, year, commit=False)
                self.balance_service.remove_pending(balance.id, request.total_days, commit=False)

            # Update request
            request.status = 'cancelled'

            # Commit all changes atomically
            self.db.commit()
            self.db.refresh(request)
            return request

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cancel request {request_id}: {e}")
            raise
    
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

    def get_department_conflicts(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        exclude_request_id: Optional[int] = None
    ) -> List[dict]:
        """
        Get conflicting time-off requests from other employees in the same department.

        Args:
            user_id: ID of the user making the request
            start_date: Start date of the requested time off
            end_date: End date of the requested time off
            exclude_request_id: Optional request ID to exclude (for editing existing requests)

        Returns:
            List of dicts with conflict info: user name, dates, type, status
        """
        # Get the user's department
        stmt = select(User).where(User.id == user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if not user or not user.department_id:
            return []

        # Find other users in the same department
        stmt = select(User).where(
            User.department_id == user.department_id,
            User.id != user_id,
            User.is_active == True
        )
        dept_users = self.db.execute(stmt).scalars().all()

        if not dept_users:
            return []

        dept_user_ids = [u.id for u in dept_users]

        # Find overlapping requests from department colleagues
        stmt = select(PTORequest).where(
            PTORequest.user_id.in_(dept_user_ids),
            PTORequest.status.in_(['pending', 'approved']),
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date
        )

        if exclude_request_id is not None:
            stmt = stmt.where(PTORequest.id != exclude_request_id)

        conflicts = self.db.execute(stmt).scalars().all()

        # Build conflict details with user info
        conflict_details = []
        user_map = {u.id: u for u in dept_users}

        for conflict in conflicts:
            conflict_user = user_map.get(conflict.user_id)
            if conflict_user:
                conflict_details.append({
                    'request_id': conflict.id,
                    'user_id': conflict.user_id,
                    'user_name': f"{conflict_user.first_name} {conflict_user.last_name}",
                    'start_date': conflict.start_date,
                    'end_date': conflict.end_date,
                    'pto_type': conflict.pto_type,
                    'status': conflict.status,
                    'total_days': float(conflict.total_days)
                })

        return conflict_details
