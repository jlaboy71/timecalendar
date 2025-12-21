"""
Policy Change Service for tracking and displaying policy changes.

Manages policy change logs, determines active changes for display,
and provides change data for UI components.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from src.models.policy_change_log import PolicyChangeLog
from src.models.handbook_upload import HandbookUpload
from src.models.user import User


class PolicyChangeService:
    """
    Service for managing policy changes, versioning, and indicator display.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_active_changes(
        self,
        policy_type: Optional[str] = None,
        location_state: Optional[str] = None,
        location_city: Optional[str] = None
    ) -> List[PolicyChangeLog]:
        """
        Get changes still within 30-day display window.

        Args:
            policy_type: Filter by specific policy type
            location_state: Filter by state
            location_city: Filter by city

        Returns:
            List of active policy changes
        """
        now = datetime.utcnow()

        stmt = select(PolicyChangeLog).where(
            PolicyChangeLog.expires_at > now
        )

        if policy_type:
            stmt = stmt.where(PolicyChangeLog.policy_type == policy_type)

        if location_state is not None:
            # Include NULL (default) policies and state-specific
            stmt = stmt.where(
                (PolicyChangeLog.location_state.is_(None)) |
                (PolicyChangeLog.location_state == location_state)
            )

        if location_city is not None:
            # Include NULL (default) policies and city-specific
            stmt = stmt.where(
                (PolicyChangeLog.location_city.is_(None)) |
                (PolicyChangeLog.location_city == location_city)
            )

        return self.db.execute(stmt.order_by(PolicyChangeLog.created_at.desc())).scalars().all()

    def get_change_for_field(
        self,
        policy_type: str,
        user: User
    ) -> Optional[PolicyChangeLog]:
        """
        Get the most recent active change for a specific policy field for user's location.

        This is the primary method used by UI components to determine
        if a change indicator should be displayed.

        Args:
            policy_type: The policy field identifier (e.g., 'sick_carryover_max')
            user: The user to check location-specific changes for

        Returns:
            The most recent active change, or None if no active changes
        """
        now = datetime.utcnow()

        # Base conditions for location resolution (most specific first)
        base_conditions = [
            PolicyChangeLog.policy_type == policy_type,
            PolicyChangeLog.expires_at > now
        ]

        # Try city-specific first
        if user.location_city and user.location_state:
            stmt = select(PolicyChangeLog).where(
                *base_conditions,
                PolicyChangeLog.location_state == user.location_state,
                PolicyChangeLog.location_city == user.location_city
            ).order_by(PolicyChangeLog.created_at.desc())
            city_change = self.db.execute(stmt).scalar_one_or_none()
            if city_change:
                return city_change

        # Try state-specific
        if user.location_state:
            stmt = select(PolicyChangeLog).where(
                *base_conditions,
                PolicyChangeLog.location_state == user.location_state,
                PolicyChangeLog.location_city.is_(None)
            ).order_by(PolicyChangeLog.created_at.desc())
            state_change = self.db.execute(stmt).scalar_one_or_none()
            if state_change:
                return state_change

        # Fall back to default (NULL location)
        stmt = select(PolicyChangeLog).where(
            *base_conditions,
            PolicyChangeLog.location_state.is_(None),
            PolicyChangeLog.location_city.is_(None)
        ).order_by(PolicyChangeLog.created_at.desc())
        return self.db.execute(stmt).scalar_one_or_none()

    def get_whats_new(
        self,
        user: User,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent changes relevant to user's location for dashboard display.

        Args:
            user: The user to get changes for
            limit: Maximum number of changes to return

        Returns:
            List of change dictionaries with formatted data for display
        """
        now = datetime.utcnow()

        # Build statement for changes applicable to user's location
        stmt = select(PolicyChangeLog).where(
            PolicyChangeLog.expires_at > now
        )

        # Filter to applicable locations (default or user's location)
        if user.location_state:
            if user.location_city:
                stmt = stmt.where(
                    (PolicyChangeLog.location_state.is_(None)) |
                    ((PolicyChangeLog.location_state == user.location_state) &
                     ((PolicyChangeLog.location_city.is_(None)) |
                      (PolicyChangeLog.location_city == user.location_city)))
                )
            else:
                stmt = stmt.where(
                    (PolicyChangeLog.location_state.is_(None)) |
                    (PolicyChangeLog.location_state == user.location_state)
                )

        changes = self.db.execute(
            stmt.order_by(PolicyChangeLog.created_at.desc()).limit(limit)
        ).scalars().all()

        # Format for display
        return [
            {
                'id': change.id,
                'policy_type': change.policy_type,
                'old_value_display': change.old_value_display,
                'new_value_display': change.new_value_display,
                'effective_date': change.effective_date,
                'reason': change.reason,
                'ai_summary': change.ai_summary,
                'is_revert': change.is_revert,
                'created_at': change.created_at,
                'days_remaining': (change.expires_at - now).days
            }
            for change in changes
        ]

    def create_change_log(
        self,
        policy_type: str,
        handbook_version: str,
        old_value: str,
        new_value: str,
        old_value_display: str,
        new_value_display: str,
        effective_date: date,
        changed_by: int,
        location_state: Optional[str] = None,
        location_city: Optional[str] = None,
        reason: Optional[str] = None,
        ai_summary: Optional[str] = None,
        is_revert: bool = False,
        reverted_to_version: Optional[str] = None,
        handbook_upload_id: Optional[int] = None
    ) -> PolicyChangeLog:
        """
        Create a new policy change log entry.

        Args:
            policy_type: Policy field identifier
            handbook_version: Version string of the handbook
            old_value: Previous value as string
            new_value: New value as string
            old_value_display: Human-readable previous value
            new_value_display: Human-readable new value
            effective_date: When the change takes effect
            changed_by: User ID of admin who published
            location_state: State scope (None = all)
            location_city: City scope (None = all in state)
            reason: Explanation for the change
            ai_summary: Claude-generated friendly summary
            is_revert: Whether this reverts a previous change
            reverted_to_version: Version being restored (if revert)
            handbook_upload_id: Link to source handbook

        Returns:
            Created PolicyChangeLog instance
        """
        change = PolicyChangeLog.create_with_expiration(
            policy_type=policy_type,
            handbook_version=handbook_version,
            old_value=old_value,
            new_value=new_value,
            old_value_display=old_value_display,
            new_value_display=new_value_display,
            effective_date=effective_date,
            changed_by=changed_by,
            location_state=location_state,
            location_city=location_city,
            reason=reason,
            ai_summary=ai_summary,
            is_revert=is_revert,
            reverted_to_version=reverted_to_version,
            handbook_upload_id=handbook_upload_id
        )

        self.db.add(change)
        self.db.commit()
        self.db.refresh(change)

        return change

    def get_handbook_versions(self) -> List[HandbookUpload]:
        """
        Get all published handbook versions for version history.

        Returns:
            List of published handbook uploads, most recent first
        """
        stmt = select(HandbookUpload).where(
            HandbookUpload.status == 'published'
        ).order_by(HandbookUpload.published_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_latest_handbook(self) -> Optional[HandbookUpload]:
        """
        Get the most recently published handbook.

        Returns:
            Latest published HandbookUpload or None
        """
        stmt = select(HandbookUpload).where(
            HandbookUpload.status == 'published'
        ).order_by(HandbookUpload.published_at.desc())
        return self.db.execute(stmt).scalar_one_or_none()

    def check_for_duplicate(self, file_hash: str) -> Optional[HandbookUpload]:
        """
        Check if a file hash matches a previous handbook upload.

        Used for revert detection.

        Args:
            file_hash: SHA-256 hash of the uploaded file

        Returns:
            Matching HandbookUpload if found, None otherwise
        """
        stmt = select(HandbookUpload).where(
            HandbookUpload.file_hash == file_hash
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def format_policy_type_name(self, policy_type: str) -> str:
        """
        Convert policy type code to human-readable name.

        Args:
            policy_type: Internal policy type code

        Returns:
            Human-readable name
        """
        names = {
            'sick_carryover_max': 'Sick Time Carryover Maximum',
            'vacation_days': 'Vacation Days',
            'vacation_carryover_max': 'Vacation Carryover Maximum',
            'personal_days': 'Personal Days',
            'personal_carryover_max': 'Personal Carryover Maximum',
            'wfh_weekly_limit': 'Work From Home Weekly Limit',
            'bereavement_days': 'Bereavement Leave Days',
            'sick_accrual_rate': 'Sick Time Accrual Rate',
            'vacation_accrual_rate': 'Vacation Accrual Rate',
        }
        return names.get(policy_type, policy_type.replace('_', ' ').title())

    def get_change_count_for_user(self, user: User) -> int:
        """
        Get count of active changes applicable to a user.

        Used for badge counts on navigation.

        Args:
            user: User to check changes for

        Returns:
            Count of active changes
        """
        now = datetime.utcnow()

        conditions = [PolicyChangeLog.expires_at > now]

        # Filter to applicable locations
        if user.location_state:
            if user.location_city:
                conditions.append(
                    (PolicyChangeLog.location_state.is_(None)) |
                    ((PolicyChangeLog.location_state == user.location_state) &
                     ((PolicyChangeLog.location_city.is_(None)) |
                      (PolicyChangeLog.location_city == user.location_city)))
                )
            else:
                conditions.append(
                    (PolicyChangeLog.location_state.is_(None)) |
                    (PolicyChangeLog.location_state == user.location_state)
                )

        stmt = select(func.count()).select_from(PolicyChangeLog).where(*conditions)
        return self.db.execute(stmt).scalar()
