# PTO Central - Phase 5: Ignition
## MCP Write Access & Agent Activation

**Generated**: December 23, 2025  
**Purpose**: Claude Code instruction file for enabling MCP write operations and final agent deployment  
**Prerequisite**: Phases 1-4 complete (MCP read-only, RAG indexed, agent framework designed)

---

## Executive Summary

This document enables the transition from **read-only MCP** to **full write access**, allowing AI agents to actually submit PTO requests, not just read them. This is the final step before production deployment of intelligent automation.

---

## Current State Analysis

### ✅ What You Already Have (From currentcore.md)

| Component | Status | Files |
|-----------|--------|-------|
| **MCP Server** | ✅ Implemented (READ-ONLY) | `mcp/mcp_server.py`, `mcp/pto_central_mcp.py` |
| **RAG Index** | ✅ Built | `data/rag_index.json`, `scripts/rag_indexer.py` |
| **Policy Engine** | ✅ Implemented | `src/services/policy_engine.py` |
| **Audit Logging** | ✅ Comprehensive | `src/services/audit_service.py` |
| **Protected Logic** | ✅ Documented | `.claude/rules/protected-logic.md` |
| **Business Rules** | ✅ Documented | `.claude/rules/business-rules.md`, `task/formulalogic.md` |

### 🔲 What You Need for Phase 5

| Component | Status | Action Required |
|-----------|--------|-----------------|
| **MCP Write Tools** | 🔲 Not implemented | Add 4 write tools to MCP server |
| **Agent Orchestrator** | 🔲 Not implemented | Create `src/services/agent_service.py` |
| **Confirmation Flow** | 🔲 Not implemented | Human-in-the-loop before writes |
| **Skills (6 total)** | 🔲 Not implemented | Create skill packages |
| **Rate Limiting** | ✅ Exists for login | Extend to MCP endpoints |

---

## Phase 5A: MCP Write Access Implementation

### Overview

Current MCP server has 3 read-only tools:
- `get_employee_info` - Query employee data
- `get_pending_requests` - View pending requests  
- `check_pto_balance` - Check balances

### New Write Tools to Add (4 total)

#### Tool 1: `submit_pto_request`

```python
# Add to mcp/pto_central_mcp.py

@mcp.tool()
async def submit_pto_request(
    user_id: int,
    pto_type: str,
    start_date: str,
    end_date: str,
    notes: str = "",
    confirmation_token: str = None
) -> dict:
    """
    Submit a new PTO request on behalf of a user.
    
    REQUIRES confirmation_token from prior confirm_action call.
    This ensures human-in-the-loop approval before any write operation.
    
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
    # Validate confirmation token first
    if not _validate_confirmation_token(confirmation_token, "submit_pto_request"):
        return {
            "success": False,
            "error": "Invalid or expired confirmation token. Call confirm_action first.",
            "action_required": "confirm_action"
        }
    
    # Use existing policy_engine for validation
    from src.services.policy_engine import PolicyEngine
    from src.services.pto_service import PTOService
    from src.database import get_db_session
    
    with get_db_session() as db:
        engine = PolicyEngine(db)
        
        # Pre-validate before submission
        validation = engine.validate_pto_request(
            user_id=user_id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not validation["is_valid"]:
            return {
                "success": False,
                "validation_errors": validation["errors"],
                "suggestions": validation.get("suggestions", [])
            }
        
        # Create the request using existing service
        pto_service = PTOService(db)
        request = pto_service.create_request(
            user_id=user_id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date,
            notes=f"[AI-Submitted] {notes}",
            submitted_by_agent=True  # New field for audit trail
        )
        
        # Audit log
        from src.services.audit_service import AuditService
        AuditService(db).log_action(
            user_id=user_id,
            action="AI_SUBMIT_PTO",
            details={
                "request_id": request.id,
                "pto_type": pto_type,
                "dates": f"{start_date} to {end_date}",
                "agent": "MCP_SMART_SCHEDULER"
            }
        )
        
        return {
            "success": True,
            "request_id": request.id,
            "status": request.status,
            "days_requested": validation["days_calculated"],
            "remaining_balance_after": validation["projected_balance"]
        }
```

#### Tool 2: `cancel_pto_request`

```python
@mcp.tool()
async def cancel_pto_request(
    request_id: int,
    user_id: int,
    reason: str = "",
    confirmation_token: str = None
) -> dict:
    """
    Cancel an existing pending PTO request.
    
    REQUIRES confirmation_token from prior confirm_action call.
    
    Args:
        request_id: The PTO request ID to cancel
        user_id: The user making the cancellation (must own the request)
        reason: Optional cancellation reason
        confirmation_token: REQUIRED - Token from confirm_action call
        
    Returns:
        dict with success status and updated request info
    """
    if not _validate_confirmation_token(confirmation_token, "cancel_pto_request"):
        return {
            "success": False,
            "error": "Invalid or expired confirmation token",
            "action_required": "confirm_action"
        }
    
    from src.services.pto_service import PTOService
    from src.database import get_db_session
    
    with get_db_session() as db:
        pto_service = PTOService(db)
        
        # Verify ownership
        request = pto_service.get_request(request_id)
        if not request or request.user_id != user_id:
            return {"success": False, "error": "Request not found or unauthorized"}
        
        if request.status != "pending":
            return {"success": False, "error": f"Cannot cancel {request.status} request"}
        
        # Cancel using existing service
        result = pto_service.cancel_request(
            request_id=request_id,
            cancelled_by=user_id,
            reason=f"[AI-Cancelled] {reason}"
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "previous_status": "pending",
            "new_status": "cancelled",
            "balance_restored": True
        }
```

#### Tool 3: `approve_pto_request` (Manager/Admin only)

```python
@mcp.tool()
async def approve_pto_request(
    request_id: int,
    approver_id: int,
    approval_notes: str = "",
    confirmation_token: str = None
) -> dict:
    """
    Approve a pending PTO request (manager/admin action).
    
    REQUIRES:
    - confirmation_token from confirm_action call
    - approver must have manager/admin role
    - approver must be the requestor's manager OR admin
    
    Args:
        request_id: The PTO request ID to approve
        approver_id: The manager/admin approving
        approval_notes: Optional approval notes
        confirmation_token: REQUIRED - Token from confirm_action call
        
    Returns:
        dict with approval status
    """
    if not _validate_confirmation_token(confirmation_token, "approve_pto_request"):
        return {"success": False, "error": "Invalid confirmation token"}
    
    from src.services.pto_service import PTOService
    from src.services.user_service import UserService
    from src.database import get_db_session
    
    with get_db_session() as db:
        user_service = UserService(db)
        approver = user_service.get_user(approver_id)
        
        # Role check
        if approver.role not in ["manager", "admin", "superadmin"]:
            return {"success": False, "error": "Insufficient permissions"}
        
        pto_service = PTOService(db)
        request = pto_service.get_request(request_id)
        
        # Authority check
        requestor = user_service.get_user(request.user_id)
        if approver.role == "manager" and requestor.manager_id != approver_id:
            return {"success": False, "error": "Not authorized to approve this request"}
        
        # Approve
        result = pto_service.approve_request(
            request_id=request_id,
            approved_by=approver_id,
            notes=f"[AI-Assisted Approval] {approval_notes}"
        )
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "approved",
            "approved_by": approver.username,
            "employee": requestor.username
        }
```

#### Tool 4: `confirm_action` (Human-in-the-Loop Gate)

```python
import secrets
import time

# Token storage (in production, use Redis or database)
_pending_confirmations = {}

@mcp.tool()
async def confirm_action(
    action_type: str,
    action_summary: str,
    user_id: int
) -> dict:
    """
    Request human confirmation before executing a write action.
    
    This is the REQUIRED first step before any write operation.
    Returns a confirmation token that expires in 5 minutes.
    
    The AI assistant should:
    1. Call this tool with action details
    2. Present the summary to the user
    3. Wait for explicit user confirmation
    4. Use the token in the subsequent write call
    
    Args:
        action_type: One of: submit_pto_request, cancel_pto_request, approve_pto_request
        action_summary: Human-readable summary of what will happen
        user_id: The user who must confirm
        
    Returns:
        dict with confirmation_token and expiry
    """
    valid_actions = ["submit_pto_request", "cancel_pto_request", "approve_pto_request"]
    if action_type not in valid_actions:
        return {"success": False, "error": f"Invalid action type. Must be one of: {valid_actions}"}
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    expiry = time.time() + 300  # 5 minutes
    
    _pending_confirmations[token] = {
        "action_type": action_type,
        "user_id": user_id,
        "summary": action_summary,
        "expires": expiry,
        "created": time.time()
    }
    
    return {
        "success": True,
        "confirmation_token": token,
        "expires_in_seconds": 300,
        "action_summary": action_summary,
        "instruction": "Present this summary to the user. Only proceed if they explicitly confirm."
    }


def _validate_confirmation_token(token: str, action_type: str) -> bool:
    """Validate a confirmation token."""
    if not token or token not in _pending_confirmations:
        return False
    
    conf = _pending_confirmations[token]
    
    # Check expiry
    if time.time() > conf["expires"]:
        del _pending_confirmations[token]
        return False
    
    # Check action type matches
    if conf["action_type"] != action_type:
        return False
    
    # Token is single-use
    del _pending_confirmations[token]
    return True
```

---

## Phase 5B: Agent Service Implementation

### Create `src/services/agent_service.py`

```python
"""
PTO Central Agent Service
=========================
Orchestrates AI agents for intelligent PTO management.

Agents:
1. Smart Scheduler - Finds optimal vacation dates
2. Year-End Optimizer - Prevents December chaos  
3. Approval Assistant - Helps managers decide faster

All agents use MCP tools with human-in-the-loop confirmation.
"""

from anthropic import Anthropic
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.database import get_db_session
from src.services.policy_engine import PolicyEngine
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class PTOAgent:
    """Base class for PTO Central AI agents."""
    
    def __init__(self, user_id: int, agent_type: str):
        self.user_id = user_id
        self.agent_type = agent_type
        self.client = Anthropic()
        self.conversation_history = []
        self.pending_action = None
        self.actions_log = []
    
    def _get_system_prompt(self) -> str:
        """Override in subclasses for agent-specific prompts."""
        raise NotImplementedError
    
    def _get_tools(self) -> List[dict]:
        """Define available tools for this agent."""
        raise NotImplementedError
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message through the agentic loop."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=self._get_system_prompt(),
                tools=self._get_tools(),
                messages=self.conversation_history
            )
            
            if response.stop_reason == "tool_use":
                # Execute tools and continue
                tool_results = await self._execute_tools(response.content)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })
            else:
                # Agent has final response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text = block.text
                        break
                
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response.content
                })
                
                return {
                    "response": final_text,
                    "actions_taken": self.actions_log,
                    "pending_confirmation": self.pending_action
                }
    
    async def _execute_tools(self, content) -> List[dict]:
        """Execute tool calls and return results."""
        results = []
        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                
                # Execute the tool
                result = await self._call_tool(tool_name, tool_input)
                self.actions_log.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result
                })
                
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        
        return results
    
    async def _call_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Route tool calls to MCP server or local services."""
        # This connects to the MCP server
        # In production, use proper MCP client
        from mcp.pto_central_mcp import (
            get_employee_info,
            check_pto_balance,
            get_pending_requests,
            confirm_action,
            submit_pto_request
        )
        
        tool_map = {
            "get_employee_info": get_employee_info,
            "check_pto_balance": check_pto_balance,
            "get_pending_requests": get_pending_requests,
            "confirm_action": confirm_action,
            "submit_pto_request": submit_pto_request
        }
        
        if tool_name in tool_map:
            return await tool_map[tool_name](**tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}


class SmartSchedulerAgent(PTOAgent):
    """
    Smart Scheduler Agent
    ---------------------
    Helps employees find optimal vacation dates by:
    - Checking available balance
    - Looking at team calendar for coverage
    - Finding market holidays to extend
    - Avoiding skeleton crew situations
    """
    
    def __init__(self, user_id: int):
        super().__init__(user_id, "smart_scheduler")
    
    def _get_system_prompt(self) -> str:
        return """You are the Smart Scheduler Agent for PTO Central.

Your job is to help employees find the OPTIMAL dates for their time off.

CAPABILITIES:
- Check the user's PTO balance for all leave types
- View who else on the team is scheduled off
- Know all market holidays (NYSE/NASDAQ closed dates)
- Calculate day usage efficiently (extend weekends, holidays)

WORKFLOW:
1. Understand what the user wants (vacation length, preferred timing)
2. Check their balance - can they afford it?
3. Check team calendar - is there coverage?
4. Find opportunities - market holidays nearby?
5. Propose 2-3 optimal date options with reasoning
6. If user confirms, use confirm_action then submit_pto_request

RULES:
- Never submit without explicit user confirmation
- Always check balance BEFORE suggesting dates
- Prefer dates that maximize consecutive days off
- Warn if team coverage drops below 50%
- Be conversational and helpful

MARKET HOLIDAYS TO KNOW (2025):
- Jan 1: New Year's Day
- Jan 20: MLK Day  
- Feb 17: Presidents Day
- Apr 18: Good Friday
- May 26: Memorial Day
- Jun 19: Juneteenth
- Jul 4: Independence Day
- Sep 1: Labor Day
- Nov 27: Thanksgiving
- Dec 25: Christmas

Example optimization: "Take Dec 22-24 (3 days) + Dec 26 (1 day) = 4 PTO days for 11 days off (Dec 20-Jan 1)"
"""
    
    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "check_pto_balance",
                "description": "Get user's current PTO balance across all leave types",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "description": "Employee ID"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "get_employee_info",
                "description": "Get employee details including department and manager",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer", "description": "Employee ID"},
                        "username": {"type": "string", "description": "Username (alternative)"}
                    }
                }
            },
            {
                "name": "get_pending_requests",
                "description": "View pending PTO requests for a team/department",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "department_id": {"type": "integer"},
                        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "end_date": {"type": "string", "description": "YYYY-MM-DD"}
                    }
                }
            },
            {
                "name": "confirm_action",
                "description": "Request user confirmation before submitting. REQUIRED before any write.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string", "enum": ["submit_pto_request"]},
                        "action_summary": {"type": "string"},
                        "user_id": {"type": "integer"}
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "submit_pto_request",
                "description": "Submit a PTO request. REQUIRES confirmation_token from confirm_action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "pto_type": {"type": "string", "enum": ["vacation", "sick", "personal", "chicago_paid_leave"]},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "notes": {"type": "string"},
                        "confirmation_token": {"type": "string"}
                    },
                    "required": ["user_id", "pto_type", "start_date", "end_date", "confirmation_token"]
                }
            }
        ]


class YearEndOptimizerAgent(PTOAgent):
    """
    Year-End Optimizer Agent
    ------------------------
    Proactively prevents December chaos by:
    - Alerting users with expiring time
    - Suggesting optimal use-it-or-lose-it dates
    - Preventing skeleton crew situations
    """
    
    def __init__(self, user_id: int):
        super().__init__(user_id, "year_end_optimizer")
    
    def _get_system_prompt(self) -> str:
        return """You are the Year-End Optimizer Agent for PTO Central.

Your job is to help employees USE their time before it expires.

HAVENTECH CARRYOVER RULES:
- Vacation: Max 5 days carryover (use-by March 31 next year)
- Sick: No limit carryover
- Personal: No carryover (use it or lose it Dec 31)
- Chicago Paid Leave: No carryover (use it or lose it Dec 31)

WORKFLOW:
1. Check user's current balances
2. Calculate what will expire Dec 31
3. Check December calendar for open slots
4. Propose dates that won't create coverage issues
5. Be PROACTIVE - reach out before they ask

SKELETON CREW RULES:
- Trading desk: Minimum 2 people always
- Operations: Minimum 1 person always
- Never schedule more than 50% of department off

Be helpful but urgent when time is running out. December is critical.
"""
    
    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "check_pto_balance",
                "description": "Get user's current PTO balance",
                "input_schema": {
                    "type": "object",
                    "properties": {"user_id": {"type": "integer"}},
                    "required": ["user_id"]
                }
            },
            {
                "name": "get_pending_requests", 
                "description": "Check team calendar for availability",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "department_id": {"type": "integer"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    }
                }
            },
            {
                "name": "confirm_action",
                "description": "Request user confirmation before submitting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string"},
                        "action_summary": {"type": "string"},
                        "user_id": {"type": "integer"}
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "submit_pto_request",
                "description": "Submit PTO request (requires confirmation token)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "pto_type": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "confirmation_token": {"type": "string"}
                    },
                    "required": ["user_id", "pto_type", "start_date", "end_date", "confirmation_token"]
                }
            }
        ]


class ApprovalAssistantAgent(PTOAgent):
    """
    Approval Assistant Agent
    ------------------------
    Helps managers make faster approval decisions by:
    - Checking team coverage automatically
    - Reviewing historical patterns
    - Flagging potential issues
    - Recommending approve/review/deny
    """
    
    def __init__(self, user_id: int):
        super().__init__(user_id, "approval_assistant")
    
    def _get_system_prompt(self) -> str:
        return """You are the Approval Assistant Agent for PTO Central.

Your job is to help MANAGERS make faster, better approval decisions.

WORKFLOW FOR EACH PENDING REQUEST:
1. Check team coverage for the requested dates
2. Look for conflicts (multiple people out)
3. Check requestor's balance - do they have enough?
4. Review historical patterns (do they always request same dates?)
5. Generate recommendation

RECOMMENDATIONS:
✅ APPROVE - Full coverage maintained, balance sufficient
⚠️ REVIEW - Coverage concerns but manageable
❌ DENY - Critical coverage issue or insufficient balance

MANAGER AUTO-APPROVE:
- Managers can approve their OWN requests (Haventech policy)
- Still need human confirmation before executing

Be efficient. Managers are busy. Give clear, actionable recommendations.
"""
    
    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "get_pending_requests",
                "description": "Get all pending requests for manager's team",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {"type": "integer"},
                        "include_all_pending": {"type": "boolean", "default": True}
                    }
                }
            },
            {
                "name": "check_pto_balance",
                "description": "Verify requestor has sufficient balance",
                "input_schema": {
                    "type": "object",
                    "properties": {"user_id": {"type": "integer"}},
                    "required": ["user_id"]
                }
            },
            {
                "name": "get_employee_info",
                "description": "Get employee and team details",
                "input_schema": {
                    "type": "object",
                    "properties": {"user_id": {"type": "integer"}}
                }
            },
            {
                "name": "confirm_action",
                "description": "Request manager confirmation before approving",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string", "enum": ["approve_pto_request"]},
                        "action_summary": {"type": "string"},
                        "user_id": {"type": "integer"}
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "approve_pto_request",
                "description": "Approve a pending request (requires confirmation token)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "integer"},
                        "approver_id": {"type": "integer"},
                        "approval_notes": {"type": "string"},
                        "confirmation_token": {"type": "string"}
                    },
                    "required": ["request_id", "approver_id", "confirmation_token"]
                }
            }
        ]
```

---

## Phase 5C: Skills Implementation

### Skills Directory Structure

Create this structure in your project:

```
skills/
├── pto-central-development/
│   ├── SKILL.md
│   ├── references/
│   │   ├── architecture.md
│   │   ├── database-schema.md
│   │   └── services-api.md
│   └── scripts/
│       └── validate_balance.py
├── pto-policy-validator/
│   ├── SKILL.md
│   └── references/
│       ├── handbook-rules.md
│       ├── chicago-ordinance.md
│       └── validation-rules.md
├── pto-testing-automation/
│   ├── SKILL.md
│   ├── references/
│   │   └── test-scenarios.md
│   └── scripts/
│       └── generate_test.py
├── pto-mcp-builder/
│   ├── SKILL.md
│   └── references/
│       ├── mcp-tools-spec.md
│       └── security-model.md
├── pto-rag-knowledge/
│   ├── SKILL.md
│   └── references/
│       ├── indexing-guide.md
│       └── query-patterns.md
└── pto-agent-orchestrator/
    ├── SKILL.md
    └── references/
        ├── agent-specs.md
        └── guardrails.md
```

### Priority Skill: `pto-central-development/SKILL.md`

```markdown
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

## References

- See `references/architecture.md` for full system diagram
- See `references/database-schema.md` for all 20 models
- See `references/services-api.md` for service method signatures
```

---

## Phase 5D: Final Deployment Checklist

### Security Review

```bash
# 1. Verify MCP server is localhost-only
grep -r "0.0.0.0" mcp/
# Should return nothing - only bind to 127.0.0.1

# 2. Check confirmation flow is enforced
grep -r "confirmation_token" mcp/pto_central_mcp.py
# All write tools should require it

# 3. Verify audit logging
grep -r "AI_SUBMIT\|AI_CANCEL\|AI_APPROVE" src/services/audit_service.py
# Should have handlers for all AI actions
```

### Integration Tests

```python
# tests/test_mcp_write_access.py

import pytest
from mcp.pto_central_mcp import (
    confirm_action,
    submit_pto_request,
    _pending_confirmations
)

@pytest.mark.asyncio
async def test_submit_requires_confirmation():
    """Write operations must require confirmation token."""
    result = await submit_pto_request(
        user_id=1,
        pto_type="vacation",
        start_date="2025-02-01",
        end_date="2025-02-03",
        confirmation_token=None  # No token
    )
    assert result["success"] is False
    assert "confirmation" in result["error"].lower()

@pytest.mark.asyncio
async def test_confirmation_flow():
    """Full confirmation flow should work."""
    # Step 1: Get confirmation
    conf = await confirm_action(
        action_type="submit_pto_request",
        action_summary="Submit 3 days vacation Feb 1-3",
        user_id=1
    )
    assert conf["success"] is True
    assert "confirmation_token" in conf
    
    # Step 2: Use token (would need valid DB for full test)
    token = conf["confirmation_token"]
    assert token in _pending_confirmations

@pytest.mark.asyncio
async def test_token_expiry():
    """Tokens should expire after 5 minutes."""
    import time
    
    conf = await confirm_action(
        action_type="submit_pto_request",
        action_summary="Test",
        user_id=1
    )
    token = conf["confirmation_token"]
    
    # Manually expire the token
    _pending_confirmations[token]["expires"] = time.time() - 1
    
    result = await submit_pto_request(
        user_id=1,
        pto_type="vacation",
        start_date="2025-02-01",
        end_date="2025-02-03",
        confirmation_token=token
    )
    assert result["success"] is False
```

### Environment Variables

Add to `.env`:

```env
# Agent Configuration
AGENT_ENABLED=true
AGENT_CONFIRMATION_TIMEOUT=300
AGENT_MAX_REQUESTS_PER_MINUTE=10

# MCP Configuration  
MCP_WRITE_ACCESS=true
MCP_AUDIT_ALL_ACTIONS=true
```

---

## Implementation Order

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 5 TIMELINE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Day 1-2: MCP Write Tools                                   │
│  ├── Add confirm_action tool                                │
│  ├── Add submit_pto_request tool                            │
│  ├── Add cancel_pto_request tool                            │
│  └── Add approve_pto_request tool                           │
│                                                             │
│  Day 3-4: Agent Service                                     │
│  ├── Create agent_service.py                                │
│  ├── Implement SmartSchedulerAgent                          │
│  ├── Implement YearEndOptimizerAgent                        │
│  └── Implement ApprovalAssistantAgent                       │
│                                                             │
│  Day 5: Skills Package                                      │
│  ├── Create pto-central-development skill                   │
│  ├── Create pto-policy-validator skill                      │
│  └── Package remaining 4 skills                             │
│                                                             │
│  Day 6-7: Integration & Testing                             │
│  ├── Write integration tests                                │
│  ├── Security review                                        │
│  ├── End-to-end agent testing                               │
│  └── Documentation update                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Commands Reference

```bash
# Run MCP server with write access
set MCP_WRITE_ACCESS=true && venv\Scripts\python.exe mcp/mcp_server.py

# Test agent service
venv\Scripts\python.exe -c "from src.services.agent_service import SmartSchedulerAgent; print('Agent loaded')"

# Run integration tests
venv\Scripts\python.exe -m pytest tests/test_mcp_write_access.py -v

# Verify confirmation tokens work
venv\Scripts\python.exe -c "
import asyncio
from mcp.pto_central_mcp import confirm_action
result = asyncio.run(confirm_action('submit_pto_request', 'Test', 1))
print(result)
"
```

---

## Success Criteria

| Criteria | Validation |
|----------|------------|
| Write tools require confirmation | ✅ All writes fail without token |
| Tokens expire correctly | ✅ 5-minute timeout enforced |
| Audit trail complete | ✅ All AI actions logged with agent identifier |
| Role permissions enforced | ✅ Manager-only tools reject employees |
| MCP localhost only | ✅ No external network exposure |
| Agents can complete workflows | ✅ End-to-end test passes |

---

**END OF DOCUMENT**

Ready for Claude Code injection. Feed this file to begin Phase 5 implementation.
