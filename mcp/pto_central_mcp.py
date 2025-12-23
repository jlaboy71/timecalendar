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
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from functools import wraps
import time

# Rate limiting state
_rate_limits: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


class ConfirmationRequiredError(Exception):
    """Raised when write operation requires confirmation."""
    pass


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


# NOTE: submit_request and approve_request are DISABLED by default
# They require explicit enablement and confirmation flow

def submit_request_with_confirmation(
    employee_id: int,
    pto_type: str,
    start_date: str,
    end_date: str,
    notes: Optional[str] = None,
    confirmation_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit a PTO request (requires confirmation).

    This tool is DISABLED by default and requires:
    1. Explicit enablement in MCP config
    2. A valid confirmation token from the user

    Args:
        employee_id: The employee's user ID
        pto_type: Type of leave
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        notes: Optional notes
        confirmation_token: Required confirmation token

    Returns:
        Submission result or confirmation required error
    """
    if not confirmation_token:
        raise ConfirmationRequiredError(
            "PTO request submission requires user confirmation. "
            "Please confirm this action in the UI before proceeding."
        )

    # Actual implementation would go here
    # For Phase 4, this is intentionally disabled
    return {"error": "Write operations disabled in Phase 4.1-4.2"}


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

    # Phase 4.3: Write tools (disabled by default)
    "validate_request": {
        "handler": validate_request,
        "description": "Validate PTO request (dry-run)",
        "phase": "4.3",
        "enabled": True  # Validation is safe
    },
    "submit_request": {
        "handler": submit_request_with_confirmation,
        "description": "Submit PTO request (requires confirmation)",
        "phase": "4.3",
        "enabled": False  # Disabled until Phase 4.3 approval
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
