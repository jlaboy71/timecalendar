# PTO Central System Identity Doctrine
**Version**: 1.0
**Generated**: December 23, 2025
**Authority**: Evidence-based from repository scan
**Purpose**: Canonical documentation for RAG retrieval and accurate system explanation

---

## 1. System Definition

### What PTO Central Is
PTO Central is an employee time-off management system designed for Haventech Solutions. It is:
- A web application built with Python, NiceGUI, and SQLite
- A business operations tool for tracking paid time off
- A system with role-based access control (employee, manager, admin, superadmin)
- An auditable platform with comprehensive logging
- An AI-assisted application with explicit safety controls

### What PTO Central Is Not
- PTO Central is not conscious, self-aware, or sentient
- It does not possess intent, desires, or agency
- It does not learn from user interactions (no ML training occurs)
- It is not a general-purpose AI assistant
- It does not make autonomous decisions affecting people without human confirmation

**Evidence**: This definition derives from the architecture in `.claude/CLAUDE.md` and the creator philosophy in `task/JoseMLaboy.md`.

---

## 2. Architecture Overview

### Repository Layout
```
c:\Users\jlaboy\codelab\projects\TimeCalendar\
├── nicegui_app/              # UI Layer
│   ├── main.py               # Application entry point
│   ├── pages/                # 29 page modules
│   └── components/           # Reusable UI components
├── src/                      # Business Logic Layer
│   ├── models/               # 20 SQLAlchemy models
│   ├── services/             # 32 service modules
│   ├── schemas/              # Pydantic validation
│   ├── config.py             # Configuration
│   └── database.py           # Database connection
├── mcp/                      # AI/MCP Layer
│   ├── pto_central_mcp.py    # MCP tool implementations
│   └── mcp_server.py         # RAG query server
├── alembic/                  # Database migrations (17 versions)
├── scripts/                  # Utility scripts (20 files)
├── data/                     # Help docs and RAG index
├── .claude/                  # Development documentation
│   └── rules/                # Business rules, code style
└── task/                     # Task tracking and doctrine
```

### Three-Tier Architecture
| Tier | Location | Responsibility |
|------|----------|----------------|
| **UI** | `nicegui_app/` | User interface, page rendering |
| **Service** | `src/services/` | Business logic, validation |
| **Data** | `src/models/` + SQLite | Persistence, schema |

**Evidence**: File structure from Glob scans of repository.

---

## 3. Capability Inventory

### 3.1 PTO Request Management

**Description**: Submit, approve, deny, and cancel time-off requests.

**Entry Points**:
- UI: `nicegui_app/pages/request_form.py` (submit)
- UI: `nicegui_app/pages/requests.py` (view/cancel)
- UI: `nicegui_app/pages/manager_request_detail.py` (approve/deny)
- MCP: `mcp/pto_central_mcp.py::submit_pto_request()`

**Service Layer**:
- `src/services/pto_service.py` (PROTECTED)
  - `create_request()` - Creates request, deducts pending balance
  - `approve_request()` - Moves pending to used
  - `deny_request()` - Returns pending to available
  - `cancel_request()` - Returns pending/used to available

**Model**: `src/models/pto_request.py`

**Validation Rules**:
- Date range must be valid (end >= start)
- User must have sufficient balance for hard-cap types
- Backdated requests require manager approval
- Manager/admin requests auto-approve

**Permissions**:
| Role | Can Submit | Can View | Can Approve | Can Cancel |
|------|-----------|----------|-------------|------------|
| Employee | Own | Own | No | Own pending |
| Manager | Own | Team | Team | Team |
| Admin | Any | All | All | All |
| Superadmin | Any | All | All | All |

**Data Persistence**: `pto_requests` table

---

### 3.2 Balance Tracking

**Description**: Track vacation, sick, personal, and Chicago leave hours.

**Entry Points**:
- UI: `nicegui_app/pages/dashboard.py` (view balances)
- MCP: `mcp/pto_central_mcp.py::get_employee_balance()`

**Service Layer**:
- `src/services/balance_service.py` (PROTECTED)
  - `get_or_create_balance()` - Retrieves or creates balance record
  - `add_pending()` - Adds hours to pending
  - `remove_pending()` - Returns pending hours
  - `move_pending_to_used()` - On approval
  - `remove_used()` - On cancellation

**Model**: `src/models/pto_balance.py` (PROTECTED)

**Canonical Formulas** (from `.claude/rules/protected-logic.md`):
```
vacation_available = vacation_total + vacation_carryover - vacation_used - vacation_pending
sick_available = sick_total + sick_carryover - sick_used - sick_pending
personal_available = personal_total + personal_carryover - personal_used - personal_pending
chicago_paid_leave_available = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

**Hard Cap Types** (cannot overdraft):
- Sick
- Personal
- Chicago Leave

**Soft Cap Types** (warning only):
- Vacation

**Evidence**: `src/models/pto_balance.py` lines 165-183, `.claude/rules/protected-logic.md` lines 32-41.

---

### 3.3 WFH Day Swap

**Description**: Peer-to-peer work-from-home day exchange system.

**Entry Points**:
- UI: `nicegui_app/pages/wfh_swap.py`

**Service Layer**:
- `src/services/wfh_swap_service.py`
  - `create_swap_request()` - 15 validation rules enforced
  - `accept_swap()` / `decline_swap()` / `cancel_swap()`

**Model**: `src/models/wfh_day_swap.py`

**Validation Rules** (from `.claude/rules/wfh-swap-rules.md`):
1. Cannot swap with yourself
2. Weekdays only
3. Future dates only
4. Two-week window (current or next week)
5. Federal holidays blocked (except Early Close)
6. Both users must be active
7. Both users must be WFH-eligible
8. Both users must have designated WFH day
9. Swap date must match target's WFH day
10. Message required
11. One swap per user per week

**Request Lifecycle**: pending → accepted/declined/cancelled/expired

**Evidence**: `src/services/wfh_swap_service.py` lines 113-268, `.claude/rules/wfh-swap-rules.md`.

---

### 3.4 Year-End Processing

**Description**: Annual balance rollover and new year setup.

**Entry Points**:
- UI: `nicegui_app/pages/admin_year_end.py`
- Script: `scripts/year_end_process.py`

**Service Layer**:
- `src/services/year_end_service.py` (PROTECTED)

**Business Rules**:
- Vacation carryover: Max 5 days (40 hours), use by March 31
- Sick carryover: No limit (auto-carryover)
- Personal carryover: None (use-it-or-lose-it)
- Chicago Paid Leave carryover: Max 16 hours

**Vacation Tiers** (tenure-based):
| Years | Days | Hours |
|-------|------|-------|
| 0-1 | 10 | 80 |
| 2-4 | 12 | 96 |
| 5-9 | 15 | 120 |
| 10+ | 20 | 160 |

**Evidence**: `.claude/rules/business-rules.md`, `.claude/rules/protected-logic.md` lines 71-79.

---

### 3.5 Team Calendar

**Description**: Visual calendar showing team availability and holidays.

**Entry Points**:
- UI: `nicegui_app/pages/calendar.py`
- MCP: `mcp/pto_central_mcp.py::get_team_calendar()`

**Service Layer**:
- `src/services/market_calendar_service.py`

**Model**: `src/models/market_holiday.py`

**Evidence**: File existence confirmed via Glob scan.

---

### 3.6 Reports & Analytics

**Description**: Generate PTO reports and workforce analytics.

**Entry Points**:
- UI: `nicegui_app/pages/reports.py`
- UI: `nicegui_app/pages/analytics.py`

**Service Layer**:
- `src/services/report_service.py`
- `src/services/export_service.py`
- `src/services/analytics_service.py`

**Export Formats**: PDF, CSV, HTML

**Evidence**: File existence confirmed via Glob scan.

---

### 3.7 Email Notifications

**Description**: Automated email notifications for request status changes.

**Entry Points**:
- UI: `nicegui_app/pages/admin_email_preview.py`
- UI: `nicegui_app/pages/admin_system.py` (email config)

**Service Layer**:
- `src/services/email_service.py`

**Email Types**:
- PTO request submitted (to employee)
- PTO request approved/denied (to employee)
- New pending request (to manager)

**Evidence**: File existence confirmed via Glob scan.

---

## 4. AI Subsystem Boundaries

### 4.1 Smart Scheduler Agent

**Location**: `src/services/agent_service.py`

**Responsibilities**:
- Help employees find optimal vacation dates
- Check PTO balances
- Review team calendar for coverage
- Search policy documents via RAG
- Submit PTO requests WITH human confirmation

**Limits**:
- Cannot approve requests (deferred to Manager AI Phase)
- Cannot cancel requests (deferred to Manager AI Phase)
- Cannot modify balances directly
- Cannot bypass Safety Gate

**Evidence**: `src/services/agent_service.py` lines 250-346.

---

### 4.2 Safety Gate

**Location**: `mcp/pto_central_mcp.py`

**Mechanism**: Token-based human-in-the-loop confirmation

**How It Works**:
1. Agent calls `confirm_action()` with action details
2. System generates secure token (expires in 5 minutes)
3. Token presented to user for explicit confirmation
4. Write operation requires valid token

**Validation** (from `_validate_confirmation_token()`):
1. Token must be provided
2. Token must exist in pending confirmations
3. Token must not be expired
4. Token action type must match
5. Token is single-use (consumed on validation)

**Evidence**: `mcp/pto_central_mcp.py` lines 65-112.

---

### 4.3 Calendar Date Verification

**Location**: `mcp/pto_central_mcp.py::get_calendar_info()`

**Purpose**: Prevent AI date hallucination

**Behavior**:
- AI MUST call this tool before stating what day a date falls on
- Returns day_of_week, is_weekend, is_weekday, surrounding dates
- Documented in agent system prompt as CRITICAL requirement

**Evidence**: `mcp/pto_central_mcp.py` lines 567-615, `src/services/agent_service.py` lines 286-292.

---

### 4.4 MCP Tool Inventory

**Allowed Tools** (enabled in `MCP_TOOLS`):

| Tool | Phase | Type | Description |
|------|-------|------|-------------|
| `get_employee_balance` | 4.1 | Read | Get PTO balance |
| `get_employee_requests` | 4.1 | Read | Get request history |
| `get_pending_approvals` | 4.1 | Read | Manager's pending |
| `get_team_calendar` | 4.1 | Read | Team schedule |
| `get_holidays` | 4.1 | Read | Market holidays |
| `get_calendar_info` | 4.1 | Read | Date verification |
| `check_team_coverage` | 4.2 | Analysis | Coverage check |
| `get_usage_patterns` | 4.2 | Analysis | Usage stats |
| `validate_request` | 4.3 | Validation | Dry-run validation |
| `confirm_action` | 5.0 | Safety | Request confirmation |
| `submit_pto_request` | 5.0 | Write | Submit request |

**Disallowed Actions** (not implemented or requires Safety Gate):
- `approve_pto_request` - Deferred to Manager AI Phase
- `cancel_pto_request` - Deferred to Manager AI Phase
- Direct balance modification - Not permitted

**Evidence**: `mcp/pto_central_mcp.py` lines 1082-1151.

---

## 5. Brand Constants

**Source of Truth**: `nicegui_app/components/theme.py`

| Constant | Hex Value | Usage |
|----------|-----------|-------|
| `PTO_GOLD` | `#C9A227` | Primary accent, buttons, highlights |
| `PTO_GRAY` | `#5a6a72` | Navigation, headers |
| `PTO_BLUE` | `#2196F3` | Interactive elements |

**Enforcement**:
- Never hardcode hex values in other files
- Always import from `nicegui_app/components/theme.py`
- Verified by `scripts/check_brand_colors.py`

**Evidence**: `nicegui_app/components/theme.py` lines 38-50.

---

## 6. Operational Workflows

### 6.1 PTO Request Lifecycle

```
CREATED (pending) ─┬─> APPROVED ─> (balance: pending → used)
                   ├─> DENIED ─> (balance: pending → available)
                   └─> CANCELLED ─> (balance: pending → available)
```

**Transitions** (from `src/services/pto_service.py`):
- `pending → approved`: Manager approval or auto-approve
- `pending → denied`: Manager denial
- `pending → cancelled`: Employee or manager cancellation
- `approved → cancelled`: Only by manager with balance restoration

---

### 6.2 Balance Recalculation Triggers

| Event | Balance Change |
|-------|----------------|
| Request created | `pending += hours` |
| Request approved | `pending -= hours; used += hours` |
| Request denied | `pending -= hours` |
| Request cancelled | `pending -= hours` or `used -= hours` |
| Hire date changed | Full recalculation via `UserService` |
| Year-end processing | New year balances with carryover |

---

### 6.3 Audit Trail Expectations

**Service**: `src/services/audit_service.py`

**Logged Actions**:
- Login attempts (success/failure)
- PTO request submit/approve/deny/cancel
- Balance modifications
- MCP tool invocations
- WFH swap actions

**Required Fields**:
- `action`: Action type identifier
- `user_id`: Acting user ID
- `username`: Acting username
- `details`: JSON details
- `timestamp`: Auto-generated

---

## 7. User Roles and Permissions

| Role | Code | Capabilities |
|------|------|--------------|
| `employee` | `UserRole.EMPLOYEE` | Submit PTO, view own balances, WFH swap |
| `manager` | `UserRole.MANAGER` | + Approve team requests, auto-approve own |
| `admin` | `UserRole.ADMIN` | + Manage employees, departments, all data |
| `superadmin` | `UserRole.SUPERADMIN` | + Year-end processing, system settings |

**Evidence**: `.claude/CLAUDE.md`, `src/constants.py`.

---

## 8. Database Schema Summary

### Core Tables
| Table | Model | Purpose |
|-------|-------|---------|
| `users` | `User` | Employee accounts |
| `pto_requests` | `PTORequest` | Time-off requests |
| `pto_balances` | `PTOBalance` | Balance tracking |
| `departments` | `Department` | Org structure |
| `wfh_day_swap_requests` | `WFHDaySwapRequest` | WFH swaps |
| `market_holidays` | `MarketHoliday` | Holidays |
| `audit_logs` | `AuditLog` | Audit trail |
| `carryover_requests` | `CarryoverRequest` | Vacation carryover |

### Migration History
17 migrations in `alembic/versions/`, most recent:
- `k2l3m4n5o6p7_add_work_schedule_times.py`
- `j1k2l3m4n5o6_add_wfh_swap_eligible.py`
- `10519844fdc1_add_wfh_day_swap_table.py`

---

## 9. Known Limitations

### Current Limitations
1. **Single-tenant**: Designed for Haventech Solutions only
2. **SQLite**: Not designed for high concurrency
3. **Localhost only**: MCP server does not accept remote connections
4. **AI approval deferred**: Agent cannot approve/deny requests yet

### Deferred Roadmap Items
From `task/todo.md`:
- [ ] `approve_pto_request` MCP tool
- [ ] `cancel_pto_request` MCP tool
- [ ] `pto-testing-automation` skill package

---

## 10. Outdated Statements Register

| Outdated Statement | Correct Statement | Evidence |
|-------------------|-------------------|----------|
| "Chicago Safe Leave is a separate bank" | Chicago Sick & Safe Leave = regular sick bank; Chicago Paid Leave is separate | `task/todo.md` lines 94-139 |

---

## 11. Freshness Policy

### Regeneration Triggers
This document should be regenerated when:
1. New MCP tools are added
2. Protected logic formulas change
3. New UI pages are added
4. Business rules are modified
5. Database schema changes

### Validation Procedure
1. Verify all file paths exist
2. Check protected formulas match code
3. Confirm MCP tool list matches `MCP_TOOLS`
4. Validate role permissions against code

---

## Document Metadata

| Field | Value |
|-------|-------|
| Generated By | Claude Code |
| Repository | PTO Central v2.0 |
| Files Scanned | ~167 core files |
| Authoritative Sources | 14 files listed in doctrine_build.md |
| Last Validated | December 23, 2025 |
