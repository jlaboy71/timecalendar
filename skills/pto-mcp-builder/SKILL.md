---
name: pto-mcp-builder
description: Build and maintain MCP (Model Context Protocol) server for PTO Central AI integration. Use when adding MCP tools, debugging MCP connections, or integrating with Claude/AI assistants. Triggers on "MCP server", "MCP tool", "Claude integration", "AI assistant", "tool definition", "Safety Gate", "confirmation token".
---

# PTO MCP Builder Skill

## MCP Server Location

`mcp/pto_central_mcp.py`

## Current Tool Inventory (16 Tools)

### Read Tools (Safe - No Confirmation Required)
| Tool | Purpose |
|------|---------|
| `get_employee_info` | Query employee details |
| `check_pto_balance` | Get balance for all leave types |
| `get_pending_requests` | View pending PTO requests |
| `get_market_holidays` | List market closed dates |
| `get_team_calendar` | See team schedule |
| `get_holidays` | Get holidays for date range |

### Doctrine Tools
| Tool | Purpose |
|------|---------|
| `query_system_knowledge` | Query system self-knowledge |
| `validate_ai_response` | Check for prohibited claims |
| `get_system_summary` | Quick system overview |

### Write Tools (Require Safety Gate)
| Tool | Requires Token | Purpose |
|------|----------------|---------|
| `confirm_action` | N/A (creates token) | Request human confirmation |
| `submit_pto_request` | Yes | Submit new request |
| `cancel_pto_request` | Yes | Cancel pending request |
| `approve_pto_request` | Yes | Manager approves |
| `deny_pto_request` | Yes | Manager denies |

### Utility Tools
| Tool | Purpose |
|------|---------|
| `get_confirmation_status` | Check pending confirmations |

## Safety Gate Pattern

ALL write operations MUST follow this pattern:

```
1. User expresses intent -> "I want to submit vacation for next week"
2. Agent calls confirm_action -> Gets token + summary
3. Agent presents summary -> "Submit 5 days vacation Dec 23-27?"
4. User confirms explicitly -> "Yes" / "Do it" / "Confirm"
5. Agent calls write tool with token -> submit_pto_request(..., token)
6. Token is consumed (single-use)
```

## Adding a New Read Tool

```python
@mcp.tool()
async def my_new_read_tool(
    user_id: int,
    optional_param: str = ""
) -> dict:
    """
    Description of what this tool does.

    Claude reads this to understand when to use the tool.
    Be specific about inputs and outputs.

    Args:
        user_id: The employee ID to query
        optional_param: Optional description

    Returns:
        dict with result fields
    """
    try:
        from src.services.some_service import SomeService
        from src.database import get_db_session

        with get_db_session() as db:
            service = SomeService(db)
            result = service.get_something(user_id)

            return {
                "success": True,
                "data": result
            }
    except Exception as e:
        logger.error(f"my_new_read_tool failed: {e}")
        return {"success": False, "error": str(e)}
```

## Adding a New Write Tool

```python
@mcp.tool()
async def my_new_write_tool(
    user_id: int,
    some_data: str,
    confirmation_token: str = ""
) -> dict:
    """
    Description of write operation.

    REQUIRES confirmation_token from prior confirm_action call.

    Args:
        user_id: User performing action
        some_data: Data to write
        confirmation_token: REQUIRED - Token from confirm_action

    Returns:
        dict with success status
    """
    # 1. Validate token FIRST
    token_valid, token_error = _validate_confirmation_token(
        confirmation_token,
        "my_new_write_action"  # Must be in VALID_CONFIRMATION_ACTIONS
    )
    if not token_valid:
        return {
            "success": False,
            "error": token_error,
            "action_required": "Call confirm_action first"
        }

    # 2. Perform the write
    try:
        from src.services.some_service import SomeService
        from src.database import get_db_session

        with get_db_session() as db:
            service = SomeService(db)
            result = service.do_write(user_id, some_data)

            # 3. Audit log
            audit_log(db, user_id, "MY_WRITE_ACTION", {"data": some_data})

            db.commit()

            return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"my_new_write_tool failed: {e}")
        return {"success": False, "error": str(e)}
```

## Registering New Action Types

Add to `VALID_CONFIRMATION_ACTIONS`:

```python
VALID_CONFIRMATION_ACTIONS = frozenset({
    "submit_pto_request",
    "cancel_pto_request",
    "approve_pto_request",
    "deny_pto_request",
    "my_new_write_action",  # Add new action here
})
```

## Testing MCP Tools

```bash
# Syntax check
venv\Scripts\python.exe -m py_compile mcp/pto_central_mcp.py

# Test a read tool
venv\Scripts\python.exe -c "
from mcp.pto_central_mcp import get_employee_balance

result = get_employee_balance(user_id=1)
print(result)
"

# Test Safety Gate flow
venv\Scripts\python.exe -c "
from mcp.pto_central_mcp import confirm_action

# Get confirmation
conf = confirm_action(
    action_type='submit_pto_request',
    user_id=1,
    action_summary='Test submission'
)
print(f'Token: {conf.get(\"confirmation_token\", \"NONE\")[:20]}...')
"
```

## Token Validation Logic

```python
def _validate_confirmation_token(token: str, action_type: str) -> tuple:
    """
    Validate a confirmation token.

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not token:
        return False, "Confirmation token required"

    if token not in _pending_confirmations:
        return False, "Invalid or expired token"

    conf = _pending_confirmations[token]

    # Check action type matches
    if conf["action_type"] != action_type:
        return False, f"Token is for {conf['action_type']}, not {action_type}"

    # Check expiry (5 minutes)
    if time.time() > conf["expires_at"]:
        del _pending_confirmations[token]
        return False, "Token has expired"

    # Single-use: consume the token
    del _pending_confirmations[token]
    return True, None
```

## When to Use This Skill

- Adding new MCP tools
- Debugging tool execution
- Updating Safety Gate logic
- Connecting new services to MCP
- Testing AI tool integration
