"""
Audit logging service for tracking system actions.
"""
import json
from typing import Optional, Any
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


class AuditService:
    """Service for creating and querying audit logs."""

    @staticmethod
    def log(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            db: Database session
            action: Action performed (e.g., 'login', 'pto_approve')
            user_id: ID of user who performed the action
            username: Username of user who performed the action
            entity_type: Type of entity affected (e.g., 'user', 'pto_request')
            entity_id: ID of affected entity
            details: Additional details as a dictionary
            ip_address: IP address of the request

        Returns:
            Created AuditLog entry
        """
        log_entry = AuditLog(
            action=action,
            user_id=user_id,
            username=username,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def log_login(db: Session, user_id: int, username: str, success: bool = True):
        """Log a login attempt."""
        return AuditService.log(
            db=db,
            action='login_success' if success else 'login_failed',
            user_id=user_id if success else None,
            username=username,
            details={'success': success}
        )

    @staticmethod
    def log_logout(db: Session, user_id: int, username: str):
        """Log a logout."""
        return AuditService.log(
            db=db,
            action='logout',
            user_id=user_id,
            username=username
        )

    @staticmethod
    def log_pto_request(db: Session, user_id: int, username: str, request_id: int, details: dict):
        """Log a PTO request submission."""
        return AuditService.log(
            db=db,
            action='pto_request',
            user_id=user_id,
            username=username,
            entity_type='pto_request',
            entity_id=request_id,
            details=details
        )

    @staticmethod
    def log_pto_approve(db: Session, approver_id: int, approver_name: str, request_id: int, employee_name: str):
        """Log a PTO approval."""
        return AuditService.log(
            db=db,
            action='pto_approve',
            user_id=approver_id,
            username=approver_name,
            entity_type='pto_request',
            entity_id=request_id,
            details={'employee': employee_name}
        )

    @staticmethod
    def log_pto_deny(db: Session, approver_id: int, approver_name: str, request_id: int, employee_name: str, reason: str):
        """Log a PTO denial."""
        return AuditService.log(
            db=db,
            action='pto_deny',
            user_id=approver_id,
            username=approver_name,
            entity_type='pto_request',
            entity_id=request_id,
            details={'employee': employee_name, 'reason': reason}
        )

    @staticmethod
    def log_user_create(db: Session, admin_id: int, admin_name: str, new_user_id: int, new_username: str):
        """Log user creation."""
        return AuditService.log(
            db=db,
            action='user_create',
            user_id=admin_id,
            username=admin_name,
            entity_type='user',
            entity_id=new_user_id,
            details={'new_username': new_username}
        )

    @staticmethod
    def log_user_update(db: Session, admin_id: int, admin_name: str, target_user_id: int, changes: dict):
        """Log user update."""
        return AuditService.log(
            db=db,
            action='user_update',
            user_id=admin_id,
            username=admin_name,
            entity_type='user',
            entity_id=target_user_id,
            details=changes
        )

    @staticmethod
    def log_user_deactivate(db: Session, admin_id: int, admin_name: str, target_user_id: int, target_username: str):
        """Log user deactivation (soft delete)."""
        return AuditService.log(
            db=db,
            action='user_deactivate',
            user_id=admin_id,
            username=admin_name,
            entity_type='user',
            entity_id=target_user_id,
            details={'deactivated_user': target_username}
        )

    @staticmethod
    def get_recent_logs(db: Session, limit: int = 100) -> list:
        """Get recent audit log entries."""
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_logs_by_user(db: Session, user_id: int, limit: int = 50) -> list:
        """Get audit logs for a specific user."""
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_logs_by_action(db: Session, action: str, limit: int = 50) -> list:
        """Get audit logs for a specific action type."""
        return db.query(AuditLog).filter(
            AuditLog.action == action
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
