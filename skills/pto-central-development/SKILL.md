---
name: pto-central-development
description: Primary skill for PTO Central development. Use when working on any PTO Central code including balance calculations, request workflows, UI pages, services, or database operations. Triggers on "PTO Central", "balance calculation", "year-end processing", "WFH swap", "carryover", "leave request", "Haventech", "TJM Time".
---

# PTO Central Development Skill

## Architecture Overview

PTO Central is built with:
- **Frontend**: NiceGUI (Quasar/Vue + Python)
- **Backend**: Python services with SQLAlchemy ORM
- **Database**: SQLite with Alembic migrations
- **Auth**: Session-based with role hierarchy

## Critical Files (PROTECTED)

These files require careful review before modification:
- `src/models/pto_balance.py` - Balance storage
- `src/services/balance_service.py` - Balance calculations
- `src/services/pto_service.py` - Request CRUD
- `src/services/year_end_service.py` - Year-end processing
- `src/services/policy_engine.py` - Policy validation
- `task/formulalogic.md` - Business rules source of truth

## Key Patterns

### Balance Calculation
Always use `balance_service.get_available_balance()` - never calculate manually.
The `*_available` properties on PTOBalance model handle pending request deductions.

### Request Lifecycle
pending → approved/denied → (if approved) deducted from balance
Cancellation restores pending hold, not actual balance.

### Role Hierarchy
employee < manager < admin < superadmin
Managers auto-approve their own requests.

## MANDATORY: Calendar Date Verification

**CRITICAL RULE**: Never state what day of the week a date falls on without verification.

LLMs cannot reliably calculate day-of-week for dates. To avoid errors:

1. **Always use `get_calendar_info(date_str)`** from `mcp/pto_central_mcp.py`
2. **Never guess** - "December 30 is a Monday" could be wrong
3. **Agent integration**: The SmartSchedulerAgent has this tool and MUST use it

Example:
```python
from mcp.pto_central_mcp import get_calendar_info

result = get_calendar_info("2025-12-30")
# Returns: {"day_of_week": "Tuesday", "is_weekend": False, ...}
```

This prevents date hallucination bugs in scheduling recommendations.

## References

- See `references/architecture.md` for full system diagram
- See `references/database-schema.md` for all 20 models
- See `references/services-api.md` for service method signatures
