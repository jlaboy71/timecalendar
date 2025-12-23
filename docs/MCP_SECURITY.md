# PTO Central - MCP Security Configuration

**Version:** 1.0
**Date:** 2025-12-22
**Reference:** task/MCPRAGv2.md Section 10

---

## 1. Overview

This document describes the security configuration for PTO Central's Model Context Protocol (MCP) server, implementing Phase 4 of the MCPRAGv2 governance document.

## 2. Security Principles

### 2.1 Localhost Only

The MCP server only accepts connections from `localhost`. No remote connections are permitted.

```python
# Enforced in server configuration
host = "127.0.0.1"
```

### 2.2 Rate Limiting

All MCP tools are rate-limited to prevent abuse:

| Parameter | Value |
|-----------|-------|
| Max calls per minute | 30 |
| Window duration | 60 seconds |
| Per-tool tracking | Yes |

```python
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window
```

When rate limit is exceeded, tools return:
```json
{"error": "Rate limit exceeded for tool_name. Max 30 calls per 60s."}
```

### 2.3 Audit Logging

All MCP tool invocations are logged to the audit trail:

| Field | Description |
|-------|-------------|
| `action` | `mcp_{tool_name}` |
| `user_id` | `null` (MCP agent) |
| `username` | `mcp_agent` |
| `details` | Tool parameters and result summary |

Audit logs are stored in the `audit_log` database table.

### 2.4 Write Tool Confirmation

Write operations (Phase 4.3) require explicit user confirmation:

1. **Disabled by default**: `submit_request` is disabled until Phase 4.3 approval
2. **Confirmation token required**: When enabled, requires a valid confirmation token
3. **ConfirmationRequiredError**: Raised if confirmation is missing

```python
if not confirmation_token:
    raise ConfirmationRequiredError(
        "PTO request submission requires user confirmation."
    )
```

## 3. Tool Phases

### Phase 4.1: Read-Only Tools (ENABLED)

| Tool | Description | Risk Level |
|------|-------------|------------|
| `get_employee_balance` | Get PTO balance | Low |
| `get_employee_requests` | Get request history | Low |
| `get_pending_approvals` | Get pending requests | Low |
| `get_team_calendar` | Get team schedule | Low |
| `get_holidays` | Get holiday list | Low |

### Phase 4.2: Analysis Tools (ENABLED)

| Tool | Description | Risk Level |
|------|-------------|------------|
| `check_team_coverage` | Coverage analysis | Low |
| `get_usage_patterns` | Usage statistics | Low |

### Phase 4.3: Write Tools (PARTIAL)

| Tool | Description | Risk Level | Status |
|------|-------------|------------|--------|
| `validate_request` | Dry-run validation | Low | ENABLED |
| `submit_request` | Submit PTO request | Medium | DISABLED |

## 4. Error Handling

### 4.1 Rate Limit Errors

```json
{
  "error": "Rate limit exceeded for get_employee_balance. Max 30 calls per 60s."
}
```

### 4.2 Confirmation Required Errors

```json
{
  "error": "PTO request submission requires user confirmation.",
  "requires_confirmation": true
}
```

### 4.3 Tool Disabled Errors

```json
{
  "error": "Tool submit_request is disabled (Phase 4.3)"
}
```

### 4.4 Validation Errors

```json
{
  "error": "Insufficient sick balance. Available: 16h, Requested: 24h"
}
```

## 5. Configuration Files

### 5.1 MCP Server Configuration

Location: `.claude/mcp.json`

```json
{
  "security": {
    "localhost_only": true,
    "rate_limiting": {
      "enabled": true,
      "max_calls_per_minute": 30
    },
    "audit_logging": true,
    "write_confirmation_required": true
  }
}
```

### 5.2 Tool Implementation

Location: `mcp/pto_central_mcp.py`

## 6. Enabling Write Tools

To enable Phase 4.3 write tools:

1. **Update governance**: Modify `task/MCPRAGv2.md` to approve Phase 4.3
2. **Enable in config**: Set `"enabled": true` in `.claude/mcp.json`
3. **Implement confirmation flow**: Add confirmation token generation
4. **Test thoroughly**: Verify write operations work correctly

```python
# In mcp/pto_central_mcp.py
MCP_TOOLS["submit_request"]["enabled"] = True
```

## 7. Monitoring

### 7.1 Audit Log Queries

```sql
-- Recent MCP activity
SELECT * FROM audit_log
WHERE action LIKE 'mcp_%'
ORDER BY created_at DESC
LIMIT 100;

-- Rate limit check
SELECT action, COUNT(*) as calls, MAX(created_at) as last_call
FROM audit_log
WHERE action LIKE 'mcp_%'
  AND created_at > datetime('now', '-1 minute')
GROUP BY action;
```

### 7.2 Error Monitoring

Check application logs for MCP errors:
```
[MCP] Rate limit exceeded for get_employee_balance
[MCP] Tool submit_request is disabled
```

## 8. Security Checklist

Before enabling additional MCP phases:

- [ ] All Phase 4.1 tools tested
- [ ] All Phase 4.2 tools tested
- [ ] Audit logging verified
- [ ] Rate limiting verified
- [ ] No policy violations in tool responses
- [ ] Confirmation flow implemented (for Phase 4.3)

## 9. Incident Response

If MCP security issues are detected:

1. **Disable tools**: Set `enabled: false` in config
2. **Review logs**: Check audit trail for suspicious activity
3. **Investigate**: Determine scope and impact
4. **Remediate**: Fix the security issue
5. **Re-enable**: After verification, re-enable tools

---

**END OF DOCUMENT**
