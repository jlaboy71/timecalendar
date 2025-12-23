"""
PTO Central MCP Server

Model Context Protocol server exposing PTO Central functionality to AI agents.
Implements Phase 4 of MCPRAGv2.md governance document.

Security:
- localhost only (no remote connections)
- Rate limiting per tool
- Audit logging for all operations
- Write tools require explicit confirmation

Tool Phases:
- Phase 4.1: Read-only tools (get_balance, get_requests, get_calendar)
- Phase 4.2: Analysis tools (check_coverage, usage_patterns)
- Phase 4.3: Write tools with confirmation (submit_request, approve_request)
"""

import json
import logging
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from functools import wraps
import time

# Rate limiting state
_rate_limits: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: SAFETY GATE - Human-in-the-Loop Confirmation System
# ═══════════════════════════════════════════════════════════════════════════

# Pending confirmation tokens (in production, use Redis or database)
_pending_confirmations: Dict[str, Dict[str, Any]] = {}
CONFIRMATION_TOKEN_EXPIRY_SECONDS = 300  # 5 minutes

# Valid action types that can be confirmed
VALID_CONFIRMATION_ACTIONS = frozenset({
    "submit_pto_request",
    "cancel_pto_request",
    "approve_pto_request"
})

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class ConfirmationRequiredError(Exception):
    """Raised when write operation requires confirmation."""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# SAFETY GATE HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _validate_confirmation_token(token: Optional[str], action_type: str) -> bool:
    """
    Validate a confirmation token for a write operation.

    This is the critical security gate that ensures:
    1. A token was provided (not None or empty)
    2. The token exists in our pending confirmations
    3. The token has not expired (5-minute window)
    4. The token matches the requested action type
    5. The token is consumed (single-use)

    Args:
        token: The confirmation token to validate
        action_type: The action type being performed (must match token's action)

    Returns:
        bool: True if valid, False otherwise
    """
    # Check token provided
    if not token:
        logger.warning(f"Safety Gate BLOCKED: No confirmation token for {action_type}")
        return False

    # Check token exists
    if token not in _pending_confirmations:
        logger.warning(f"Safety Gate BLOCKED: Unknown token for {action_type}")
        return False

    conf = _pending_confirmations[token]

    # Check expiry
    if time.time() > conf["expires"]:
        logger.warning(f"Safety Gate BLOCKED: Expired token for {action_type}")
        del _pending_confirmations[token]
        return False

    # Check action type matches
    if conf["action_type"] != action_type:
        logger.warning(
            f"Safety Gate BLOCKED: Token action mismatch. "
            f"Expected {action_type}, got {conf['action_type']}"
        )
        return False

    # Token is single-use - consume it
    logger.info(f"Safety Gate PASSED: Token validated for {action_type}")
    del _pending_confirmations[token]
    return True


def _cleanup_expired_tokens():
    """Remove expired tokens from pending confirmations."""
    now = time.time()
    expired = [
        token for token, conf in _pending_confirmations.items()
        if now > conf["expires"]
    ]
    for token in expired:
        del _pending_confirmations[token]


def rate_limit(tool_name: str):
    """Decorator to enforce rate limiting on tools."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if tool_name not in _rate_limits:
                _rate_limits[tool_name] = []

            # Remove old timestamps
            _rate_limits[tool_name] = [
                ts for ts in _rate_limits[tool_name]
                if now - ts < RATE_LIMIT_WINDOW
            ]

            if len(_rate_limits[tool_name]) >= RATE_LIMIT_MAX_CALLS:
                raise RateLimitError(
                    f"Rate limit exceeded for {tool_name}. "
                    f"Max {RATE_LIMIT_MAX_CALLS} calls per {RATE_LIMIT_WINDOW}s."
                )

            _rate_limits[tool_name].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def audit_log(tool_name: str, params: Dict[str, Any], result: Any):
    """Log tool invocation for audit trail."""
    from src.database import get_db
    from src.services.audit_service import AuditService

    db = next(get_db())
    try:
        AuditService.log(
            db=db,
            action=f"mcp_{tool_name}",
            user_id=None,  # MCP agent
            username="mcp_agent",
            details=json.dumps({
                "tool": tool_name,
                "params": {k: str(v) for k, v in params.items()},
                "result_summary": str(result)[:200]
            })
        )
    except Exception as e:
        logger.warning(f"Failed to log MCP audit: {e}")
    finally:
        db.close()


def json_serializer(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: CONFIRMATION TOOL (Human-in-the-Loop Gate)
# ═══════════════════════════════════════════════════════════════════════════

@rate_limit("confirm_action")
def confirm_action(
    action_type: str,
    action_summary: str,
    user_id: int
) -> Dict[str, Any]:
    """
    Request human confirmation before executing a write action.

    This is the REQUIRED first step before any write operation.
    Returns a confirmation token that expires in 5 minutes.

    The AI assistant should:
    1. Call this tool with action details
    2. Present the summary to the user
    3. Wait for explicit user confirmation
    4. Use the token in the subsequent write call

    CRITICAL: Without a valid token from this function, ALL write
    operations will be rejected. This ensures human-in-the-loop control.

    Args:
        action_type: One of: submit_pto_request, cancel_pto_request, approve_pto_request
        action_summary: Human-readable summary of what will happen
        user_id: The user who must confirm

    Returns:
        dict with confirmation_token and expiry
    """
    # Validate action type
    if action_type not in VALID_CONFIRMATION_ACTIONS:
        return {
            "success": False,
            "error": f"Invalid action type '{action_type}'. Must be one of: {list(VALID_CONFIRMATION_ACTIONS)}"
        }

    # Cleanup any expired tokens first
    _cleanup_expired_tokens()

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expiry = time.time() + CONFIRMATION_TOKEN_EXPIRY_SECONDS

    # Store the pending confirmation
    _pending_confirmations[token] = {
        "action_type": action_type,
        "user_id": user_id,
        "summary": action_summary,
        "expires": expiry,
        "created": time.time()
    }

    logger.info(
        f"Safety Gate: Confirmation requested for {action_type} by user {user_id}. "
        f"Token expires in {CONFIRMATION_TOKEN_EXPIRY_SECONDS}s"
    )

    # Audit log the confirmation request
    audit_log("confirm_action", {
        "action_type": action_type,
        "user_id": user_id,
        "summary": action_summary[:100]
    }, "token_generated")

    return {
        "success": True,
        "confirmation_token": token,
        "expires_in_seconds": CONFIRMATION_TOKEN_EXPIRY_SECONDS,
        "action_summary": action_summary,
        "instruction": (
            "IMPORTANT: Present this summary to the user. "
            "Only proceed with the write operation if they explicitly confirm. "
            "The token expires in 5 minutes and can only be used once."
        )
    }


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4.1: READ-ONLY TOOLS
# ═══════════════════════════════════════════════════════════════════════════

@rate_limit("get_employee_balance")
def get_employee_balance(employee_id: int, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Get PTO balance for an employee.

    Args:
        employee_id: The employee's user ID
        year: Optional year (defaults to current year)

    Returns:
        Balance information including vacation, sick, personal hours
    """
    from src.database import get_db
    from src.services.balance_service import BalanceService
    from src.models.user import User

    if year is None:
        year = date.today().year

    db = next(get_db())
    try:
        # Get user info
        user = db.query(User).filter(User.id == employee_id).first()
        if not user:
            return {"error": f"Employee {employee_id} not found"}

        # Get balance
        balance_service = BalanceService(db)
        balance = balance_service.get_or_create_balance(employee_id, year)

        result = {
            "employee_id": employee_id,
            "employee_name": f"{user.first_name} {user.last_name}",
            "year": year,
            "vacation": {
                "available": float(balance.vacation_available),
                "total": float(balance.vacation_total),
                "used": float(balance.vacation_used),
                "pending": float(balance.vacation_pending),
                "carryover": float(balance.vacation_carryover)
            },
            "sick": {
                "available": float(balance.sick_available),
                "total": float(balance.sick_total),
                "used": float(balance.sick_used),
                "carryover": float(balance.sick_carryover)
            },
            "personal": {
                "available": float(balance.personal_available),
                "total": float(balance.personal_total),
                "used": float(balance.personal_used)
            }
        }

        # Add Chicago Leave if applicable
        if user.location_city and user.location_city.lower() == "chicago":
            result["chicago_leave"] = {
                "available": float(balance.chicago_paid_leave_available),
                "total": float(balance.chicago_paid_leave_total),
                "used": float(balance.chicago_paid_leave_used),
                "carryover": float(balance.chicago_paid_leave_carryover)
            }

        audit_log("get_employee_balance", {"employee_id": employee_id, "year": year}, result)
        return result
    finally:
        db.close()


@rate_limit("get_employee_requests")
def get_employee_requests(
    employee_id: int,
    status: Optional[str] = None,
    year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get PTO requests for an employee.

    Args:
        employee_id: The employee's user ID
        status: Optional filter by status (pending, approved, denied, cancelled)
        year: Optional filter by year

    Returns:
        List of PTO requests
    """
    from src.database import get_db
    from src.models.pto_request import PTORequest
    from sqlalchemy import select, and_

    db = next(get_db())
    try:
        conditions = [PTORequest.user_id == employee_id]

        if status:
            conditions.append(PTORequest.status == status)

        if year:
            conditions.append(PTORequest.start_date >= date(year, 1, 1))
            conditions.append(PTORequest.start_date <= date(year, 12, 31))

        stmt = select(PTORequest).where(and_(*conditions)).order_by(PTORequest.start_date.desc())
        requests = db.execute(stmt).scalars().all()

        result = [
            {
                "id": req.id,
                "pto_type": req.pto_type,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "total_days": float(req.total_days),
                "status": req.status,
                "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
                "notes": req.notes
            }
            for req in requests
        ]

        audit_log("get_employee_requests", {
            "employee_id": employee_id, "status": status, "year": year
        }, f"{len(result)} requests")
        return result
    finally:
        db.close()


@rate_limit("get_pending_approvals")
def get_pending_approvals(manager_id: int) -> List[Dict[str, Any]]:
    """
    Get pending PTO requests for a manager's team.

    Args:
        manager_id: The manager's user ID

    Returns:
        List of pending requests from team members
    """
    from src.database import get_db
    from src.models.pto_request import PTORequest
    from src.models.user import User
    from src.models.department import Department
    from sqlalchemy import select, and_

    db = next(get_db())
    try:
        # Get departments managed by this manager
        dept_stmt = select(Department.id).where(Department.manager_id == manager_id)
        dept_ids = [d for d in db.execute(dept_stmt).scalars().all()]

        if not dept_ids:
            return []

        # Get pending requests from team members
        stmt = select(PTORequest, User).join(
            User, PTORequest.user_id == User.id
        ).where(
            and_(
                PTORequest.status == 'pending',
                User.department_id.in_(dept_ids)
            )
        ).order_by(PTORequest.submitted_at.desc())

        results = db.execute(stmt).all()

        result = [
            {
                "request_id": req.id,
                "employee_id": req.user_id,
                "employee_name": f"{user.first_name} {user.last_name}",
                "pto_type": req.pto_type,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "total_days": float(req.total_days),
                "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
                "notes": req.notes
            }
            for req, user in results
        ]

        audit_log("get_pending_approvals", {"manager_id": manager_id}, f"{len(result)} pending")
        return result
    finally:
        db.close()


@rate_limit("get_team_calendar")
def get_team_calendar(
    manager_id: int,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """
    Get approved time-off events for a manager's team within a date range.

    Args:
        manager_id: The manager's user ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of approved time-off events
    """
    from src.database import get_db
    from src.models.pto_request import PTORequest
    from src.models.user import User
    from src.models.department import Department
    from sqlalchemy import select, and_, or_
    from datetime import datetime as dt

    start = dt.strptime(start_date, "%Y-%m-%d").date()
    end = dt.strptime(end_date, "%Y-%m-%d").date()

    db = next(get_db())
    try:
        # Get departments managed by this manager
        dept_stmt = select(Department.id).where(Department.manager_id == manager_id)
        dept_ids = [d for d in db.execute(dept_stmt).scalars().all()]

        if not dept_ids:
            return []

        # Get approved requests that overlap with date range
        stmt = select(PTORequest, User).join(
            User, PTORequest.user_id == User.id
        ).where(
            and_(
                PTORequest.status == 'approved',
                User.department_id.in_(dept_ids),
                PTORequest.start_date <= end,
                PTORequest.end_date >= start
            )
        ).order_by(PTORequest.start_date)

        results = db.execute(stmt).all()

        result = [
            {
                "employee_id": req.user_id,
                "employee_name": f"{user.first_name} {user.last_name}",
                "pto_type": req.pto_type,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "total_days": float(req.total_days)
            }
            for req, user in results
        ]

        audit_log("get_team_calendar", {
            "manager_id": manager_id, "start_date": start_date, "end_date": end_date
        }, f"{len(result)} events")
        return result
    finally:
        db.close()


@rate_limit("get_holidays")
def get_holidays(year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get market holidays for a year.

    Args:
        year: Optional year (defaults to current year)

    Returns:
        List of holidays
    """
    from src.database import get_db
    from src.models.market_holiday import MarketHoliday
    from sqlalchemy import select, extract

    if year is None:
        year = date.today().year

    db = next(get_db())
    try:
        stmt = select(MarketHoliday).where(
            extract('year', MarketHoliday.date) == year
        ).order_by(MarketHoliday.date)

        holidays = db.execute(stmt).scalars().all()

        result = [
            {
                "date": h.date.isoformat(),
                "name": h.name,
                "market": h.market
            }
            for h in holidays
        ]

        audit_log("get_holidays", {"year": year}, f"{len(result)} holidays")
        return result
    finally:
        db.close()


@rate_limit("get_calendar_info")
def get_calendar_info(date_str: str) -> Dict[str, Any]:
    """
    Get calendar information for a specific date.

    IMPORTANT: Use this tool to verify day-of-week before making date claims.
    LLMs are prone to calendar hallucinations - always verify dates!

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Dict with day_of_week, is_weekend, is_weekday, and surrounding dates
    """
    from datetime import datetime as dt

    try:
        target_date = dt.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday

    # Calculate surrounding dates for context
    dates_context = []
    for offset in range(-3, 4):  # 3 days before and after
        d = target_date + timedelta(days=offset)
        dates_context.append({
            "date": d.isoformat(),
            "day_name": day_names[d.weekday()],
            "is_target": offset == 0
        })

    result = {
        "date": target_date.isoformat(),
        "day_of_week": day_names[day_of_week],
        "day_number": day_of_week,  # 0=Monday, 6=Sunday
        "is_weekend": day_of_week >= 5,
        "is_weekday": day_of_week < 5,
        "week_number": target_date.isocalendar()[1],
        "year": target_date.year,
        "month": target_date.month,
        "day": target_date.day,
        "surrounding_dates": dates_context
    }

    audit_log("get_calendar_info", {"date": date_str}, result["day_of_week"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4.2: ANALYSIS TOOLS
# ═══════════════════════════════════════════════════════════════════════════

@rate_limit("check_team_coverage")
def check_team_coverage(
    manager_id: int,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Check team coverage for a date range.

    Args:
        manager_id: The manager's user ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Coverage analysis including days with conflicts
    """
    from src.database import get_db
    from src.models.pto_request import PTORequest
    from src.models.user import User
    from src.models.department import Department
    from sqlalchemy import select, and_, func
    from datetime import datetime as dt

    start = dt.strptime(start_date, "%Y-%m-%d").date()
    end = dt.strptime(end_date, "%Y-%m-%d").date()

    db = next(get_db())
    try:
        # Get team size
        dept_stmt = select(Department.id).where(Department.manager_id == manager_id)
        dept_ids = [d for d in db.execute(dept_stmt).scalars().all()]

        if not dept_ids:
            return {"error": "No departments found for manager"}

        team_size = db.query(func.count(User.id)).filter(
            User.department_id.in_(dept_ids),
            User.is_active == True
        ).scalar()

        # Get approved/pending requests
        stmt = select(PTORequest).join(
            User, PTORequest.user_id == User.id
        ).where(
            and_(
                PTORequest.status.in_(['approved', 'pending']),
                User.department_id.in_(dept_ids),
                PTORequest.start_date <= end,
                PTORequest.end_date >= start
            )
        )

        requests = db.execute(stmt).scalars().all()

        # Analyze coverage by day
        day_coverage = {}
        current = start
        while current <= end:
            if current.weekday() < 5:  # Weekdays only
                out_count = 0
                for req in requests:
                    if req.start_date <= current <= req.end_date:
                        out_count += 1

                coverage_pct = ((team_size - out_count) / team_size * 100) if team_size > 0 else 100
                day_coverage[current.isoformat()] = {
                    "team_size": team_size,
                    "out_count": out_count,
                    "coverage_pct": round(coverage_pct, 1),
                    "status": "critical" if coverage_pct < 50 else "warning" if coverage_pct < 75 else "ok"
                }
            current += timedelta(days=1)

        # Summary
        critical_days = [d for d, c in day_coverage.items() if c["status"] == "critical"]
        warning_days = [d for d, c in day_coverage.items() if c["status"] == "warning"]

        result = {
            "start_date": start_date,
            "end_date": end_date,
            "team_size": team_size,
            "critical_days": critical_days,
            "warning_days": warning_days,
            "day_breakdown": day_coverage
        }

        audit_log("check_team_coverage", {
            "manager_id": manager_id, "start_date": start_date, "end_date": end_date
        }, f"{len(critical_days)} critical, {len(warning_days)} warning")
        return result
    finally:
        db.close()


@rate_limit("get_usage_patterns")
def get_usage_patterns(
    scope: str = "team",
    scope_id: Optional[int] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analyze PTO usage patterns.

    Args:
        scope: "employee", "team", or "department"
        scope_id: ID for the scope (employee_id, manager_id, or department_id)
        year: Optional year (defaults to current year)

    Returns:
        Usage statistics and patterns
    """
    from src.database import get_db
    from src.models.pto_request import PTORequest
    from src.models.user import User
    from src.models.department import Department
    from sqlalchemy import select, and_, func

    if year is None:
        year = date.today().year

    db = next(get_db())
    try:
        # Build query based on scope
        if scope == "employee" and scope_id:
            user_filter = PTORequest.user_id == scope_id
        elif scope == "team" and scope_id:
            dept_stmt = select(Department.id).where(Department.manager_id == scope_id)
            dept_ids = [d for d in db.execute(dept_stmt).scalars().all()]
            user_ids_stmt = select(User.id).where(User.department_id.in_(dept_ids))
            user_ids = [u for u in db.execute(user_ids_stmt).scalars().all()]
            user_filter = PTORequest.user_id.in_(user_ids)
        elif scope == "department" and scope_id:
            user_ids_stmt = select(User.id).where(User.department_id == scope_id)
            user_ids = [u for u in db.execute(user_ids_stmt).scalars().all()]
            user_filter = PTORequest.user_id.in_(user_ids)
        else:
            return {"error": "Invalid scope or missing scope_id"}

        # Get approved requests
        stmt = select(PTORequest).where(
            and_(
                PTORequest.status == 'approved',
                user_filter,
                PTORequest.start_date >= date(year, 1, 1),
                PTORequest.start_date <= date(year, 12, 31)
            )
        )

        requests = db.execute(stmt).scalars().all()

        # Analyze by type
        by_type = {}
        by_month = {m: 0 for m in range(1, 13)}

        for req in requests:
            pto_type = req.pto_type
            if pto_type not in by_type:
                by_type[pto_type] = {"count": 0, "total_days": 0}
            by_type[pto_type]["count"] += 1
            by_type[pto_type]["total_days"] += float(req.total_days)

            by_month[req.start_date.month] += float(req.total_days)

        result = {
            "scope": scope,
            "scope_id": scope_id,
            "year": year,
            "total_requests": len(requests),
            "total_days_used": sum(float(r.total_days) for r in requests),
            "by_type": by_type,
            "by_month": by_month,
            "peak_month": max(by_month.keys(), key=lambda m: by_month[m]) if requests else None
        }

        audit_log("get_usage_patterns", {
            "scope": scope, "scope_id": scope_id, "year": year
        }, f"{len(requests)} requests analyzed")
        return result
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4.3: WRITE TOOLS (Require Confirmation)
# ═══════════════════════════════════════════════════════════════════════════

@rate_limit("validate_request")
def validate_request(
    employee_id: int,
    pto_type: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Validate a PTO request before submission (dry-run).

    Args:
        employee_id: The employee's user ID
        pto_type: Type of leave (vacation, sick, personal)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Validation result with any warnings or errors
    """
    from src.database import get_db
    from src.services.policy_engine import PolicyEngine
    from src.services.balance_service import BalanceService
    from src.utils.working_days import count_working_days
    from datetime import datetime as dt

    start = dt.strptime(start_date, "%Y-%m-%d").date()
    end = dt.strptime(end_date, "%Y-%m-%d").date()

    db = next(get_db())
    try:
        # Calculate working days
        working_days = count_working_days(start, end)
        hours = working_days * 8

        # Validate dates
        engine = PolicyEngine()
        date_result = engine.validate_request_dates(start, end, pto_type)

        if not date_result.is_valid:
            return {
                "valid": False,
                "error": date_result.error_message,
                "working_days": working_days,
                "hours": hours
            }

        # Check balance
        balance_service = BalanceService(db)
        balance = balance_service.get_or_create_balance(employee_id, start.year)

        available = {
            "vacation": float(balance.vacation_available),
            "sick": float(balance.sick_available),
            "personal": float(balance.personal_available)
        }.get(pto_type, float('inf'))

        warnings = []
        if hours > available:
            from src.services.policy_engine import HARD_CAP_TYPES
            if pto_type in HARD_CAP_TYPES:
                return {
                    "valid": False,
                    "error": f"Insufficient {pto_type} balance. Available: {available}h, Requested: {hours}h",
                    "working_days": working_days,
                    "hours": hours
                }
            else:
                warnings.append(f"Request exceeds available balance ({available}h available)")

        if date_result.is_backdated:
            warnings.append("Backdated request - requires manager approval")

        result = {
            "valid": True,
            "working_days": working_days,
            "hours": hours,
            "available_balance": available,
            "warnings": warnings
        }

        audit_log("validate_request", {
            "employee_id": employee_id, "pto_type": pto_type,
            "start_date": start_date, "end_date": end_date
        }, result)
        return result
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: WRITE TOOLS (Require Safety Gate Confirmation)
# ═══════════════════════════════════════════════════════════════════════════

@rate_limit("submit_pto_request")
def submit_pto_request(
    user_id: int,
    pto_type: str,
    start_date: str,
    end_date: str,
    notes: str = "",
    confirmation_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a new PTO request on behalf of a user.

    REQUIRES confirmation_token from prior confirm_action call.
    This ensures human-in-the-loop approval before any write operation.

    CRITICAL: The first line of this function validates the confirmation token.
    If validation fails, the request is REJECTED immediately.

    Args:
        user_id: Employee ID submitting the request
        pto_type: One of: vacation, sick, personal, chicago_paid_leave, bereavement, jury_duty
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        notes: Optional notes for the request
        confirmation_token: REQUIRED - Token from confirm_action call

    Returns:
        dict with request_id, status, and validation results
    """
    # ═══════════════════════════════════════════════════════════════════
    # SAFETY GATE CHECK - THIS MUST BE THE FIRST VALIDATION
    # ═══════════════════════════════════════════════════════════════════
    if not _validate_confirmation_token(confirmation_token, "submit_pto_request"):
        return {
            "success": False,
            "error": "Invalid or expired confirmation token. Call confirm_action first.",
            "action_required": "confirm_action",
            "hint": "You must call confirm_action to get a token before submitting a PTO request."
        }
    # ═══════════════════════════════════════════════════════════════════

    from src.database import get_db
    from src.services.pto_service import PTOService
    from src.services.balance_service import BalanceService
    from src.services.policy_engine import PolicyEngine, HARD_CAP_TYPES
    from src.services.audit_service import AuditService
    from src.schemas.pto_schemas import PTORequestCreate
    from src.utils.working_days import count_working_days
    from datetime import datetime as dt

    # Parse dates
    try:
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid date format. Use YYYY-MM-DD. Details: {str(e)}"
        }

    db = next(get_db())
    try:
        # Pre-validate using PolicyEngine
        engine = PolicyEngine(db)
        date_result = engine.validate_request_dates(start, end, pto_type)

        if not date_result.is_valid:
            return {
                "success": False,
                "validation_errors": [date_result.rejection_reason],
                "suggestions": ["Check the date range and try again"]
            }

        # Calculate working days and hours
        working_days = count_working_days(start, end)
        hours = Decimal(str(working_days * 8))

        # Check balance for hard-cap types
        balance_service = BalanceService(db)
        balance = balance_service.get_or_create_balance(user_id, start.year)

        available_map = {
            "vacation": balance.vacation_available,
            "sick": balance.sick_available,
            "personal": balance.personal_available,
            "chicago_paid_leave": getattr(balance, 'chicago_paid_leave_available', Decimal('0'))
        }
        available = float(available_map.get(pto_type.lower(), Decimal('999')))

        if pto_type.lower() in HARD_CAP_TYPES and float(hours) > available:
            return {
                "success": False,
                "validation_errors": [
                    f"Insufficient {pto_type} balance. "
                    f"Available: {available}h, Requested: {float(hours)}h"
                ],
                "available_balance": available,
                "requested_hours": float(hours)
            }

        # Create the request using existing service
        request_data = PTORequestCreate(
            user_id=user_id,
            pto_type=pto_type,
            start_date=start,
            end_date=end,
            total_days=Decimal(str(working_days)),
            notes=f"[AI-Submitted via MCP] {notes}" if notes else "[AI-Submitted via MCP]"
        )

        pto_service = PTOService(db)
        request = pto_service.create_request(request_data)

        # Audit log the AI submission
        AuditService.log(
            db=db,
            action="mcp_submit_pto_request",
            user_id=user_id,
            username="mcp_agent",
            details=json.dumps({
                "request_id": request.id,
                "pto_type": pto_type,
                "start_date": start_date,
                "end_date": end_date,
                "working_days": working_days,
                "hours": float(hours),
                "status": request.status,
                "submitted_via": "MCP_SAFETY_GATE"
            })
        )

        logger.info(
            f"MCP: PTO request {request.id} created for user {user_id}. "
            f"Type: {pto_type}, Days: {working_days}, Status: {request.status}"
        )

        # Calculate projected balance after this request
        projected_balance = available - float(hours)

        return {
            "success": True,
            "request_id": request.id,
            "status": request.status,
            "pto_type": pto_type,
            "start_date": start_date,
            "end_date": end_date,
            "working_days": working_days,
            "hours_requested": float(hours),
            "previous_balance": available,
            "projected_balance_after": max(0, projected_balance),
            "requires_approval": request.status == "pending",
            "message": (
                f"PTO request submitted successfully. "
                f"{'Awaiting manager approval.' if request.status == 'pending' else 'Auto-approved.'}"
            )
        }

    except ValueError as e:
        # Business rule violation from PTOService
        logger.warning(f"MCP submit_pto_request validation error: {e}")
        return {
            "success": False,
            "validation_errors": [str(e)],
            "suggestions": ["Review the error and adjust your request"]
        }
    except Exception as e:
        logger.error(f"MCP submit_pto_request unexpected error: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "hint": "Please try again or contact support"
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: DOCTRINE QUERY TOOLS - System Self-Knowledge
# ═══════════════════════════════════════════════════════════════════════════

def query_system_knowledge(
    question: str,
    include_source: bool = True
) -> Dict[str, Any]:
    """
    Query PTO Central's self-knowledge using the System Identity Doctrine.

    Use this for questions about:
    - What PTO Central is and does
    - Who created it
    - System capabilities and limitations
    - Design decisions and architecture
    - Prohibited claims (consciousness, etc.)

    Args:
        question: Natural language question about the system
        include_source: Whether to include source file references

    Returns:
        dict with answer, source, and confidence level
    """
    from src.services.doctrine_query_service import get_doctrine_service

    service = get_doctrine_service()
    result = service.query(question)

    if not include_source:
        result.pop("source_file", None)

    logger.info(f"Doctrine query: '{question[:50]}...' -> {result.get('source', 'unknown')}")
    return result


def validate_ai_response(
    response_text: str
) -> Dict[str, Any]:
    """
    Validate that an AI-generated response doesn't contain
    prohibited claims (consciousness, self-awareness, etc.).

    Use this before sending any response that discusses
    PTO Central's nature or capabilities.

    Args:
        response_text: The response to validate

    Returns:
        dict with valid (bool) and any violations found
    """
    from src.services.doctrine_query_service import get_doctrine_service

    service = get_doctrine_service()
    result = service.validate_response(response_text)

    if not result["valid"]:
        logger.warning(f"AI response validation failed: {result['violations']}")

    return result


def get_system_summary() -> Dict[str, Any]:
    """
    Get a summary of the PTO Central system.

    Returns key facts about the system including:
    - System name and version
    - Creator attribution
    - Consciousness status (always False)
    - Doctrine status

    Returns:
        dict with system summary information
    """
    from src.services.doctrine_query_service import get_doctrine_service

    service = get_doctrine_service()
    return service.get_system_summary()


# ═══════════════════════════════════════════════════════════════════════════
# MCP SERVER DEFINITION
# ═══════════════════════════════════════════════════════════════════════════

MCP_TOOLS = {
    # Phase 4.1: Read-only tools
    "get_employee_balance": {
        "handler": get_employee_balance,
        "description": "Get PTO balance for an employee",
        "phase": "4.1",
        "enabled": True
    },
    "get_employee_requests": {
        "handler": get_employee_requests,
        "description": "Get PTO requests for an employee",
        "phase": "4.1",
        "enabled": True
    },
    "get_pending_approvals": {
        "handler": get_pending_approvals,
        "description": "Get pending approvals for a manager",
        "phase": "4.1",
        "enabled": True
    },
    "get_team_calendar": {
        "handler": get_team_calendar,
        "description": "Get team time-off calendar",
        "phase": "4.1",
        "enabled": True
    },
    "get_holidays": {
        "handler": get_holidays,
        "description": "Get market holidays",
        "phase": "4.1",
        "enabled": True
    },

    # Phase 4.2: Analysis tools
    "check_team_coverage": {
        "handler": check_team_coverage,
        "description": "Check team coverage for date range",
        "phase": "4.2",
        "enabled": True
    },
    "get_usage_patterns": {
        "handler": get_usage_patterns,
        "description": "Analyze PTO usage patterns",
        "phase": "4.2",
        "enabled": True
    },

    # Phase 4.3: Write tools (validation only)
    "validate_request": {
        "handler": validate_request,
        "description": "Validate PTO request (dry-run)",
        "phase": "4.3",
        "enabled": True  # Validation is safe
    },

    # Phase 5: Write tools with Safety Gate
    "confirm_action": {
        "handler": confirm_action,
        "description": "Request human confirmation before write operations (REQUIRED for all writes)",
        "phase": "5.0",
        "enabled": True
    },
    "submit_pto_request": {
        "handler": submit_pto_request,
        "description": "Submit PTO request (requires confirmation_token from confirm_action)",
        "phase": "5.0",
        "enabled": True,
        "requires_confirmation": True
    },

    # Phase 6: Doctrine/Self-Knowledge tools
    "query_system_knowledge": {
        "handler": query_system_knowledge,
        "description": "Query PTO Central's self-knowledge using System Identity Doctrine",
        "phase": "6.0",
        "enabled": True
    },
    "validate_ai_response": {
        "handler": validate_ai_response,
        "description": "Validate AI response doesn't contain prohibited claims",
        "phase": "6.0",
        "enabled": True
    },
    "get_system_summary": {
        "handler": get_system_summary,
        "description": "Get summary of PTO Central system (name, version, creator)",
        "phase": "6.0",
        "enabled": True
    }
}


def get_available_tools() -> List[Dict[str, Any]]:
    """Get list of available MCP tools."""
    return [
        {
            "name": name,
            "description": tool["description"],
            "phase": tool["phase"],
            "enabled": tool["enabled"]
        }
        for name, tool in MCP_TOOLS.items()
    ]


def invoke_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Invoke an MCP tool."""
    if tool_name not in MCP_TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}

    tool = MCP_TOOLS[tool_name]

    if not tool["enabled"]:
        return {"error": f"Tool {tool_name} is disabled (Phase {tool['phase']})"}

    try:
        return tool["handler"](**kwargs)
    except RateLimitError as e:
        return {"error": str(e)}
    except ConfirmationRequiredError as e:
        return {"error": str(e), "requires_confirmation": True}
    except Exception as e:
        logger.error(f"MCP tool {tool_name} error: {e}")
        return {"error": f"Tool execution failed: {str(e)}"}


if __name__ == "__main__":
    # Test the tools
    print("PTO Central MCP Server")
    print("=" * 50)
    print("\nAvailable Tools:")
    for tool in get_available_tools():
        status = "ENABLED" if tool["enabled"] else "DISABLED"
        print(f"  [{tool['phase']}] {tool['name']}: {tool['description']} ({status})")
