"""
Balance and data integrity verification service.

Provides methods to detect data inconsistencies such as:
- Stale pending balances (pending > 0 but no actual pending requests)
- Orphaned requests (requests without valid users)
- Balance calculation mismatches
- Policy validation (date limits, auto-approve rules, hard caps)
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.models.user import User

# Policy constants (from policy_engine.py)
BACKDATE_WINDOW_DAYS = 7
FUTURE_LIMIT_YEARS = 5
HARD_CAP_TYPES = frozenset({'sick', 'personal', 'chicago_leave'})


class IntegrityService:
    """Service for verifying data integrity across the application."""

    def __init__(self, db: Session):
        self.db = db

    def run_full_check(self) -> Dict:
        """
        Run all integrity checks and return comprehensive results.

        Returns:
            Dict with check results, issues found, and summary
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'issues': [],
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }

        # Run all checks - grouped by category
        checks = [
            # Data Consistency Checks
            self._check_stale_vacation_pending(),
            self._check_stale_sick_pending(),
            self._check_stale_personal_pending(),
            self._check_stale_chicago_pending(),
            self._check_orphaned_requests(),
            self._check_orphaned_balances(),
            self._check_balance_formula_integrity(),
            # Policy Validation Checks
            self._check_negative_balances(),
            self._check_hard_cap_violations(),
            self._check_backdated_auto_approve(),
            self._check_request_date_limits(),
            self._check_approved_request_metadata(),
        ]

        for check in checks:
            results['checks'].append(check)
            results['summary']['total_checks'] += 1

            if check['status'] == 'PASS':
                results['summary']['passed'] += 1
            elif check['status'] == 'FAIL':
                results['summary']['failed'] += 1
                results['issues'].extend(check.get('issues', []))
            elif check['status'] == 'WARN':
                results['summary']['warnings'] += 1
                results['issues'].extend(check.get('issues', []))

        return results

    def _check_stale_vacation_pending(self) -> Dict:
        """Check for stale vacation_pending values."""
        result = self._check_stale_pending('vacation')
        result['description'] = 'Verifies vacation pending hours match actual pending requests'
        return result

    def _check_stale_sick_pending(self) -> Dict:
        """Check for stale sick_pending values."""
        result = self._check_stale_pending('sick')
        result['description'] = 'Verifies sick pending hours match actual pending requests'
        return result

    def _check_stale_personal_pending(self) -> Dict:
        """Check for stale personal_pending values."""
        result = self._check_stale_pending('personal')
        result['description'] = 'Verifies personal pending hours match actual pending requests'
        return result

    def _check_stale_chicago_pending(self) -> Dict:
        """Check for stale chicago_paid_leave_pending values."""
        result = self._check_stale_pending('chicago_leave')
        result['description'] = 'Verifies Chicago Leave pending hours match actual pending requests'
        return result

    def _check_stale_pending(self, pto_type: str) -> Dict:
        """
        Check if pending balance matches actual pending requests.

        Args:
            pto_type: Type of PTO to check

        Returns:
            Dict with check name, status, and any issues
        """
        check_name = f"Stale {pto_type.replace('_', ' ').title()} Pending"
        issues = []

        # Map PTO type to balance field
        field_map = {
            'vacation': 'vacation_pending',
            'sick': 'sick_pending',
            'personal': 'personal_pending',
            'chicago_leave': 'chicago_paid_leave_pending'
        }
        pending_field = field_map.get(pto_type, f'{pto_type}_pending')

        # Request type mapping
        request_type_map = {
            'chicago_leave': 'chicago_leave'
        }
        request_type = request_type_map.get(pto_type, pto_type)

        # Get all balances with pending > 0
        stmt = select(PTOBalance).where(getattr(PTOBalance, pending_field) > 0)
        balances = self.db.execute(stmt).scalars().all()

        for balance in balances:
            # Get actual pending requests for this user/year/type
            stmt = select(func.sum(PTORequest.total_days)).where(
                PTORequest.user_id == balance.user_id,
                PTORequest.pto_type == request_type,
                PTORequest.status == 'pending'
            )
            # Filter by year based on start_date
            actual_pending_days = self.db.execute(stmt).scalar() or Decimal('0')
            actual_pending_hours = actual_pending_days * Decimal('8')

            stored_pending = getattr(balance, pending_field) or Decimal('0')

            if abs(float(stored_pending) - float(actual_pending_hours)) > 0.01:
                # Get username for better reporting
                stmt = select(User.username).where(User.id == balance.user_id)
                username = self.db.execute(stmt).scalar() or f'User {balance.user_id}'

                issues.append({
                    'user_id': balance.user_id,
                    'username': username,
                    'year': balance.year,
                    'pto_type': pto_type,
                    'stored_pending': float(stored_pending),
                    'actual_pending': float(actual_pending_hours),
                    'difference': float(stored_pending - actual_pending_hours),
                    'message': f"{username} ({balance.year}): {pto_type} pending is {float(stored_pending)}hrs but should be {float(actual_pending_hours)}hrs"
                })

        return {
            'name': check_name,
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(balances)} balances with pending > 0"
        }

    def _check_orphaned_requests(self) -> Dict:
        """Check for PTO requests without valid users."""
        check_name = "Orphaned Requests"
        issues = []

        # Find requests where user doesn't exist
        stmt = select(PTORequest).where(
            ~PTORequest.user_id.in_(
                select(User.id)
            )
        )
        orphaned = self.db.execute(stmt).scalars().all()

        for req in orphaned:
            issues.append({
                'request_id': req.id,
                'user_id': req.user_id,
                'message': f"Request #{req.id} references non-existent user {req.user_id}"
            })

        return {
            'name': check_name,
            'description': 'Finds PTO requests that reference deleted or non-existent users',
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Found {len(orphaned)} orphaned requests"
        }

    def _check_orphaned_balances(self) -> Dict:
        """Check for PTO balances without valid users."""
        check_name = "Orphaned Balances"
        issues = []

        # Find balances where user doesn't exist
        stmt = select(PTOBalance).where(
            ~PTOBalance.user_id.in_(
                select(User.id)
            )
        )
        orphaned = self.db.execute(stmt).scalars().all()

        for bal in orphaned:
            issues.append({
                'balance_id': bal.id,
                'user_id': bal.user_id,
                'year': bal.year,
                'message': f"Balance for year {bal.year} references non-existent user {bal.user_id}"
            })

        return {
            'name': check_name,
            'description': 'Finds PTO balances that reference deleted or non-existent users',
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Found {len(orphaned)} orphaned balances"
        }

    def _check_negative_balances(self) -> Dict:
        """Check for unexpected negative balances (warning for vacation, error for others)."""
        check_name = "Negative Balances"
        issues = []

        # Get all balances
        stmt = select(PTOBalance)
        balances = self.db.execute(stmt).scalars().all()

        for balance in balances:
            # Get username
            stmt = select(User.username).where(User.id == balance.user_id)
            username = self.db.execute(stmt).scalar() or f'User {balance.user_id}'

            # Vacation can go negative (manager discretion) - just warn if extreme
            if balance.vacation_available < -160:  # More than 20 days negative is suspicious
                issues.append({
                    'user_id': balance.user_id,
                    'username': username,
                    'year': balance.year,
                    'pto_type': 'vacation',
                    'available': float(balance.vacation_available),
                    'severity': 'warning',
                    'message': f"{username} ({balance.year}): vacation significantly negative ({float(balance.vacation_available)}hrs)"
                })

        return {
            'name': check_name,
            'description': 'Warns about unusually large negative vacation balances (>160hrs overdraft)',
            'status': 'WARN' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(balances)} balances"
        }

    def _check_hard_cap_violations(self) -> Dict:
        """Check for negative balances on hard-cap types (sick, personal, chicago_leave)."""
        check_name = "Hard Cap Violations"
        issues = []

        # Get all balances
        stmt = select(PTOBalance)
        balances = self.db.execute(stmt).scalars().all()

        for balance in balances:
            # Get username
            stmt = select(User.username).where(User.id == balance.user_id)
            username = self.db.execute(stmt).scalar() or f'User {balance.user_id}'

            # Check hard-cap types - these should NEVER be negative
            checks = [
                ('sick', balance.sick_available),
                ('personal', balance.personal_available),
                ('chicago_leave', balance.chicago_paid_leave_available),
            ]

            for pto_type, available in checks:
                if available < 0:
                    issues.append({
                        'user_id': balance.user_id,
                        'username': username,
                        'year': balance.year,
                        'pto_type': pto_type,
                        'available': float(available),
                        'severity': 'error',
                        'message': f"{username} ({balance.year}): {pto_type} is negative ({float(available)}hrs) - policy violation"
                    })

        return {
            'name': check_name,
            'description': 'Sick, Personal, and Chicago Leave cannot go negative per policy',
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(balances)} balances for hard-cap types"
        }

    def _check_balance_formula_integrity(self) -> Dict:
        """Verify balance formula calculations are consistent."""
        check_name = "Balance Formula Integrity"
        issues = []

        stmt = select(PTOBalance)
        balances = self.db.execute(stmt).scalars().all()

        for balance in balances:
            # Verify vacation formula: available = total + carryover - used - pending
            expected_vacation = (
                (balance.vacation_total or Decimal('0')) +
                (balance.vacation_carryover or Decimal('0')) -
                (balance.vacation_used or Decimal('0')) -
                (balance.vacation_pending or Decimal('0'))
            )
            if abs(float(balance.vacation_available) - float(expected_vacation)) > 0.01:
                stmt = select(User.username).where(User.id == balance.user_id)
                username = self.db.execute(stmt).scalar() or f'User {balance.user_id}'
                issues.append({
                    'user_id': balance.user_id,
                    'username': username,
                    'year': balance.year,
                    'pto_type': 'vacation',
                    'message': f"{username} ({balance.year}): vacation formula mismatch"
                })

        return {
            'name': check_name,
            'description': 'Verifies: available = total + carryover - used - pending',
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Verified formulas for {len(balances)} balances"
        }

    def _check_backdated_auto_approve(self) -> Dict:
        """Check that backdated requests were not auto-approved."""
        check_name = "Backdated Auto-Approve"
        issues = []
        today = date.today()

        # Find approved requests where start_date < today (backdated)
        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            PTORequest.start_date < today
        )
        backdated_approved = self.db.execute(stmt).scalars().all()

        for req in backdated_approved:
            # Check if this was auto-approved (no approved_by or approved_by == user_id)
            # Auto-approved requests have approved_by == user_id (self-approved)
            if req.approved_by == req.user_id:
                # Get username
                stmt = select(User.username).where(User.id == req.user_id)
                username = self.db.execute(stmt).scalar() or f'User {req.user_id}'

                issues.append({
                    'request_id': req.id,
                    'user_id': req.user_id,
                    'username': username,
                    'start_date': req.start_date.isoformat(),
                    'pto_type': req.pto_type,
                    'severity': 'warning',
                    'message': f"Request #{req.id} ({username}): backdated {req.pto_type} was self-approved"
                })

        return {
            'name': check_name,
            'description': 'Backdated requests should require manager approval, not self-approve',
            'status': 'WARN' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(backdated_approved)} backdated approved requests"
        }

    def _check_request_date_limits(self) -> Dict:
        """Check for requests with dates outside allowed limits."""
        check_name = "Request Date Limits"
        issues = []
        today = date.today()
        min_date = today - timedelta(days=BACKDATE_WINDOW_DAYS)
        max_date = date(today.year + FUTURE_LIMIT_YEARS, 12, 31)

        # Find active requests (pending or approved) with dates outside limits
        stmt = select(PTORequest).where(
            PTORequest.status.in_(['pending', 'approved'])
        )
        requests = self.db.execute(stmt).scalars().all()

        for req in requests:
            # Skip checking past dates for already-approved requests (those are historical)
            if req.status == 'approved' and req.start_date < today:
                continue

            # Check pending requests for invalid dates
            if req.status == 'pending' and req.start_date < min_date:
                stmt = select(User.username).where(User.id == req.user_id)
                username = self.db.execute(stmt).scalar() or f'User {req.user_id}'
                issues.append({
                    'request_id': req.id,
                    'user_id': req.user_id,
                    'username': username,
                    'start_date': req.start_date.isoformat(),
                    'message': f"Request #{req.id} ({username}): pending request for {req.start_date} exceeds 7-day backdate limit"
                })

            # Check for requests too far in future (any status)
            if req.start_date > max_date:
                stmt = select(User.username).where(User.id == req.user_id)
                username = self.db.execute(stmt).scalar() or f'User {req.user_id}'
                issues.append({
                    'request_id': req.id,
                    'user_id': req.user_id,
                    'username': username,
                    'start_date': req.start_date.isoformat(),
                    'message': f"Request #{req.id} ({username}): start date {req.start_date} exceeds 5-year future limit"
                })

        return {
            'name': check_name,
            'description': 'Requests must be within 7 days past and 5 years future',
            'status': 'FAIL' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(requests)} active requests"
        }

    def _check_approved_request_metadata(self) -> Dict:
        """Check that approved requests have proper metadata."""
        check_name = "Approved Request Metadata"
        issues = []

        # Find approved requests
        stmt = select(PTORequest).where(PTORequest.status == 'approved')
        approved_requests = self.db.execute(stmt).scalars().all()

        for req in approved_requests:
            # Approved requests should have approved_by set
            if req.approved_by is None:
                stmt = select(User.username).where(User.id == req.user_id)
                username = self.db.execute(stmt).scalar() or f'User {req.user_id}'
                issues.append({
                    'request_id': req.id,
                    'user_id': req.user_id,
                    'username': username,
                    'severity': 'warning',
                    'message': f"Request #{req.id} ({username}): approved but missing approved_by"
                })

            # Approved requests should have approved_at set
            if req.approved_at is None:
                stmt = select(User.username).where(User.id == req.user_id)
                username = self.db.execute(stmt).scalar() or f'User {req.user_id}'
                issues.append({
                    'request_id': req.id,
                    'user_id': req.user_id,
                    'username': username,
                    'severity': 'warning',
                    'message': f"Request #{req.id} ({username}): approved but missing approved_at timestamp"
                })

        return {
            'name': check_name,
            'description': 'Approved requests must have approver and timestamp recorded',
            'status': 'WARN' if issues else 'PASS',
            'issues': issues,
            'details': f"Checked {len(approved_requests)} approved requests"
        }

    def fix_stale_pending(self, dry_run: bool = True) -> Dict:
        """
        Fix all stale pending balances.

        Args:
            dry_run: If True, only report what would be fixed. If False, apply fixes.

        Returns:
            Dict with fixes applied/proposed
        """
        fixes = []

        for pto_type in ['vacation', 'sick', 'personal', 'chicago_leave']:
            field_map = {
                'vacation': 'vacation_pending',
                'sick': 'sick_pending',
                'personal': 'personal_pending',
                'chicago_leave': 'chicago_paid_leave_pending'
            }
            pending_field = field_map[pto_type]
            request_type = pto_type

            # Get all balances with pending > 0
            stmt = select(PTOBalance).where(getattr(PTOBalance, pending_field) > 0)
            balances = self.db.execute(stmt).scalars().all()

            for balance in balances:
                # Calculate actual pending
                stmt = select(func.sum(PTORequest.total_days)).where(
                    PTORequest.user_id == balance.user_id,
                    PTORequest.pto_type == request_type,
                    PTORequest.status == 'pending'
                )
                actual_pending_days = self.db.execute(stmt).scalar() or Decimal('0')
                actual_pending_hours = actual_pending_days * Decimal('8')

                stored_pending = getattr(balance, pending_field) or Decimal('0')

                if abs(float(stored_pending) - float(actual_pending_hours)) > 0.01:
                    stmt = select(User.username).where(User.id == balance.user_id)
                    username = self.db.execute(stmt).scalar() or f'User {balance.user_id}'

                    fix = {
                        'user_id': balance.user_id,
                        'username': username,
                        'year': balance.year,
                        'pto_type': pto_type,
                        'old_value': float(stored_pending),
                        'new_value': float(actual_pending_hours),
                        'applied': not dry_run
                    }

                    if not dry_run:
                        setattr(balance, pending_field, actual_pending_hours)

                    fixes.append(fix)

        if not dry_run and fixes:
            self.db.commit()

        return {
            'dry_run': dry_run,
            'fixes': fixes,
            'total_fixed': len(fixes) if not dry_run else 0,
            'total_would_fix': len(fixes) if dry_run else 0
        }
