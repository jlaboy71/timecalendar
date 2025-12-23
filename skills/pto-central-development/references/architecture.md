# PTO Central - Core Files Reference

**Generated**: December 23, 2025
**Purpose**: Reference for Claude Code desktop project folder injection

---

## Project Overview

PTO Central is an employee PTO (Paid Time Off) and Market Calendar management system for Haventech Solutions. Built with Python, NiceGUI, and SQLite.

**Key Features:**
- PTO request management with approval workflows
- Balance tracking (vacation, sick, personal, Chicago leave)
- WFH Day Swap (peer-to-peer, no manager approval)
- Team calendar with market holidays
- Multi-state policy support
- Year-end processing with carryover
- Comprehensive audit logging
- Media Studio for training video production
- MCP Server for RAG-powered assistant integration

---

## Quick Copy - Essential Files Only

For minimal context injection, use these critical files:

```
.claude/CLAUDE.md
.claude/rules/business-rules.md
.claude/rules/protected-logic.md
.claude/rules/wfh-swap-rules.md
task/formulalogic.md
src/models/pto_balance.py
src/models/pto_request.py
src/models/user.py
src/services/pto_service.py
src/services/balance_service.py
src/constants.py
```

---

## Full Core File List

### Configuration & Rules (`.claude/`)

| File | Purpose |
|------|---------|
| `.claude/CLAUDE.md` | Project overview, architecture, guidelines |
| `.claude/rules/business-rules.md` | PTO policies, carryover rules, leave types, WFH swap rules |
| `.claude/rules/code-style.md` | Python/NiceGUI patterns, common scenarios |
| `.claude/rules/database.md` | Schema reference, migration checklist |
| `.claude/rules/testing.md` | Test patterns, SSL/HTTPS config, video recording settings |
| `.claude/rules/ui-patterns.md` | UI components, colors, styling |
| `.claude/rules/protected-logic.md` | **PROTECTED** - Files requiring approval to modify |
| `.claude/rules/wfh-swap-rules.md` | WFH Day Swap technical specification |

### Task Documentation (`task/`)

| File | Purpose |
|------|---------|
| `task/todo.md` | Current task tracking, completed work log |
| `task/formulalogic.md` | **CRITICAL** - All balance formulas, business logic |
| `task/currentcore.md` | This file - core files reference |
| `task/dayswap.md` | WFH swap feature implementation guide |
| `task/media01.md` | Media Studio documentation |
| `task/MCPRAG.md` | MCP RAG server documentation |
| `task/MCPRAGv2.md` | MCP RAG v2 specification |
| `task/rag_source_manifest.md` | RAG source files manifest |
| `task/ui_enhancement_todo.md` | UI enhancement tracking |
| `task/CHANGELOG_Dec2025.md` | December 2025 changes |
| `task/ptohardened.md` | Security hardening documentation |
| `task/sysadminupgrade.md` | System administration upgrades |
| `task/department_management_enhance.md` | Department management enhancements |
| `task/policy_reconciliation_report.md` | Policy reconciliation reporting |

---

## Source Code - Models (`src/models/`)

### Critical Models (Balance & Requests)

| File | Purpose |
|------|---------|
| `src/models/pto_balance.py` | **PROTECTED** - Balance storage, `*_available` properties |
| `src/models/pto_request.py` | PTO request model, status transitions |
| `src/models/user.py` | User model, roles, location, `wfh_swap_eligible` |
| `src/models/carryover_request.py` | Vacation carryover exception requests |
| `src/models/wfh_day_swap.py` | WFH day swap request model |

### Supporting Models

| File | Purpose |
|------|---------|
| `src/models/department.py` | Department model |
| `src/models/leave_type.py` | Leave type definitions |
| `src/models/leave_policy.py` | Location-based policies |
| `src/models/vacation_accrual_tier.py` | Tenure-based vacation tiers |
| `src/models/market_holiday.py` | Market/federal holidays |
| `src/models/audit_log.py` | Audit trail records |
| `src/models/system_setting.py` | System configuration |
| `src/models/year_end_status.py` | Year-end processing status |
| `src/models/handbook_revision.py` | Handbook versioning |
| `src/models/handbook_upload.py` | Uploaded handbook files |
| `src/models/password_reset.py` | Password reset tokens |
| `src/models/pending_notification.py` | Queued notifications |
| `src/models/manager_notification_preference.py` | Manager alert preferences |
| `src/models/policy_change_log.py` | Policy change tracking |
| `src/models/__init__.py` | Model exports |

**Total: 20 model files**

---

## Source Code - Services (`src/services/`)

### Critical Services (Balance & PTO Logic)

| File | Purpose |
|------|---------|
| `src/services/pto_service.py` | **PROTECTED** - Request CRUD, approve/deny/cancel |
| `src/services/balance_service.py` | **PROTECTED** - Balance adjustments, pending tracking |
| `src/services/year_end_service.py` | **PROTECTED** - Year-end processing, carryover |
| `src/services/accrual_service.py` | **PROTECTED** - Vacation tiers, policy resolution |
| `src/services/policy_engine.py` | Policy evaluation engine |
| `src/services/wfh_swap_service.py` | WFH day swap validation and lifecycle |
| `src/services/integrity_service.py` | Data integrity verification |

### Supporting Services

| File | Purpose |
|------|---------|
| `src/services/user_service.py` | User CRUD operations |
| `src/services/department_service.py` | Department management |
| `src/services/audit_service.py` | Audit logging (includes WFH swap methods) |
| `src/services/email_service.py` | Email notifications |
| `src/services/report_service.py` | Report generation |
| `src/services/eoy_report_service.py` | Year-end report generation |
| `src/services/export_service.py` | PDF/CSV export |
| `src/services/analytics_service.py` | Workforce analytics |
| `src/services/help_service.py` | Help documentation |
| `src/services/handbook_service.py` | Handbook content |
| `src/services/handbook_revision_service.py` | Handbook versions |
| `src/services/handbook_analysis_service.py` | AI handbook analysis |
| `src/services/market_calendar_service.py` | Holiday sync |
| `src/services/ical_export_service.py` | Calendar export |
| `src/services/backup_service.py` | Database backup |
| `src/services/session_manager.py` | Session timeout handling |
| `src/services/password_reset_service.py` | Password reset flow |
| `src/services/rate_limiter.py` | Login rate limiting |
| `src/services/notification_service.py` | Notification dispatch |
| `src/services/alert_service.py` | Alert management |
| `src/services/monitoring_service.py` | System monitoring |
| `src/services/policy_change_service.py` | Policy change tracking |
| `src/services/report_storage_service.py` | Report file storage |
| `src/services/__init__.py` | Service exports |

**Total: 31 service files**

---

## MCP Server (`mcp/`)

Model Context Protocol server for RAG-powered AI assistant integration.

| File | Purpose |
|------|---------|
| `mcp/mcp_server.py` | Main MCP server with 3 read-only inspector tools |
| `mcp/pto_central_mcp.py` | PTO Central MCP tool definitions |
| `mcp/__init__.py` | Package init |

### MCP Tools Available
- `get_employee_info` - Query employee data by ID or username
- `get_pending_requests` - View pending PTO requests
- `check_pto_balance` - Check employee PTO balances

### Related Files
| File | Purpose |
|------|---------|
| `data/rag_index.json` | RAG index for help content |
| `scripts/rag_indexer.py` | RAG index builder script |

---

## Media Studio (`services/` - Root Level)

Training video production system for automated documentation.

| File | Purpose |
|------|---------|
| `services/playwright_engine.py` | Browser automation, login, scenario execution |
| `services/video_producer.py` | Video compilation, title cards, transitions |
| `services/audio_narration.py` | OpenAI TTS audio generation |
| `services/scenario_setup_service.py` | Scenario data preparation |
| `services/doc_generator.py` | Documentation generation |
| `services/__init__.py` | Service exports |

### Media Configuration

| File | Purpose |
|------|---------|
| `config/testing_config.py` | Viewport, video dimensions, TTS settings, test accounts |
| `config/custom_scenarios.py` | Custom scenario definitions |
| `config/scenarios/scenario_history.json` | Scenario execution history |
| `config/__init__.py` | Config exports |

### Media Output Locations

| Type | Path |
|------|------|
| Screenshots | `nicegui_app/static/help/screenshots/{scenario}/` |
| Videos | `nicegui_app/static/help/videos/{scenario}/` |
| Audio | `nicegui_app/static/help/audio/{scenario}/` |
| Timeline | `nicegui_app/static/help/videos/{scenario}.timeline.json` |

---

## Source Code - UI Pages (`nicegui_app/pages/`)

### Employee Pages

| File | Purpose |
|------|---------|
| `nicegui_app/pages/dashboard.py` | **PROTECTED** - Main dashboard, balance tiles |
| `nicegui_app/pages/requests.py` | Request history, cancel pending |
| `nicegui_app/pages/request_form.py` | Submit new PTO request |
| `nicegui_app/pages/calendar.py` | Team calendar view |
| `nicegui_app/pages/carryover.py` | Carryover request submission |
| `nicegui_app/pages/reports.py` | Personal reports |
| `nicegui_app/pages/handbook.py` | Employee handbook viewer |
| `nicegui_app/pages/help.py` | Help center |
| `nicegui_app/pages/wfh_swap.py` | WFH Day Swap page |

### Manager Pages

| File | Purpose |
|------|---------|
| `nicegui_app/pages/manager_request_detail.py` | Approve/deny requests |
| `nicegui_app/pages/manager_team.py` | Team management |
| `nicegui_app/pages/manager_carryover.py` | Carryover approvals |
| `nicegui_app/pages/manager_settings.py` | Manager preferences |

### Admin Pages

| File | Purpose |
|------|---------|
| `nicegui_app/pages/admin_dashboard.py` | Admin overview |
| `nicegui_app/pages/admin_employees.py` | Employee CRUD |
| `nicegui_app/pages/admin_departments.py` | Department CRUD |
| `nicegui_app/pages/admin_approvals.py` | All pending approvals |
| `nicegui_app/pages/admin_system.py` | System administration |
| `nicegui_app/pages/admin_year_end.py` | Year-end processing |
| `nicegui_app/pages/admin_handbook.py` | Handbook management |
| `nicegui_app/pages/admin_email_preview.py` | Email template preview |
| `nicegui_app/pages/admin_auto_notify_reports.py` | Auto notification reports |
| `nicegui_app/pages/admin_policy_viewer.py` | Policy viewer |
| `nicegui_app/pages/analytics.py` | Workforce analytics |
| `nicegui_app/pages/testing_console.py` | Media Studio console |

### Auth Pages

| File | Purpose |
|------|---------|
| `nicegui_app/pages/login.py` | Login page |
| `nicegui_app/pages/password_reset.py` | Password reset flow |
| `nicegui_app/pages/__init__.py` | Page exports |

**Total: 28 page files**

---

## Source Code - UI Components (`nicegui_app/components/`)

| File | Purpose |
|------|---------|
| `nicegui_app/components/theme.py` | Dark mode, dialogs, styling, brand colors |
| `nicegui_app/components/header.py` | Page header component |
| `nicegui_app/components/formatting.py` | Number/date formatting helpers |
| `nicegui_app/components/charts.py` | Chart components |
| `nicegui_app/components/realtime_updates.py` | Real-time refresh |
| `nicegui_app/components/mobile_responsive.py` | Mobile CSS |
| `nicegui_app/components/policy_change_indicator.py` | Policy change badges |
| `nicegui_app/components/__init__.py` | Component exports |

**Total: 8 component files**

---

## Source Code - Schemas (`src/schemas/`)

| File | Purpose |
|------|---------|
| `src/schemas/pto_schemas.py` | PTO request/balance Pydantic schemas |
| `src/schemas/user_schemas.py` | User Pydantic schemas |
| `src/schemas/__init__.py` | Schema exports |

---

## Source Code - Core (`src/`)

| File | Purpose |
|------|---------|
| `src/constants.py` | Enums (UserRole, PTOStatus, PTOType), type icons/colors |
| `src/config.py` | Configuration loading, environment variables |
| `src/database.py` | Database connection, session management |
| `src/logging_config.py` | Logging configuration |
| `src/__init__.py` | Package init |

---

## Scripts (`scripts/`)

### Database & Seeding

| File | Purpose |
|------|---------|
| `scripts/seed.py` | Main database seeding |
| `scripts/seed_leave_types.py` | Seed leave type definitions |
| `scripts/seed_leave_policies.py` | Seed leave policies |
| `scripts/seed_vacation_tiers.py` | Seed vacation accrual tiers |
| `scripts/seed_test_data.py` | Seed test data |
| `scripts/create_test_users.py` | Create test user accounts |
| `scripts/create_wfh_test_users.py` | Create WFH swap test users |
| `scripts/update_pto_users.py` | Bulk update PTO users |
| `scripts/fix_chicago_leave_balances.py` | Fix Chicago leave balances |

### Backup & Restore

| File | Purpose |
|------|---------|
| `scripts/backup_db.py` | Database backup script |
| `scripts/restore_db.py` | Database restore script |

### Reports & Processing

| File | Purpose |
|------|---------|
| `scripts/generate_sample_reports.py` | Generate sample reports |
| `scripts/generate_real_reports.py` | Generate real reports |
| `scripts/year_end_process.py` | Year-end processing script |
| `scripts/migrate_2025_pto.py` | 2025 PTO migration |

### Utilities

| File | Purpose |
|------|---------|
| `scripts/generate_ssl_cert.py` | Generate SSL certificates |
| `scripts/check_brand_colors.py` | Detect hardcoded brand color violations |
| `scripts/rag_indexer.py` | Build RAG index for help content |
| `scripts/process_screenshots_with_cursor.py` | Screenshot processing utility |
| `scripts/__init__.py` | Package init |

**Total: 20 script files**

---

## Application Entry (`nicegui_app/`)

| File | Purpose |
|------|---------|
| `nicegui_app/main.py` | Application entry point, route registration |
| `nicegui_app/logo.py` | PTO Central logo (base64) |

---

## Database & Migrations

| File | Purpose |
|------|---------|
| `pto_central.db` | SQLite database (DO NOT COMMIT) |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Migration environment |
| `alembic/versions/*.py` | Migration scripts |

---

## Help Documentation (`data/help/`)

### Getting Started
| File | Purpose |
|------|---------|
| `data/help/getting-started/overview.md` | System overview |
| `data/help/getting-started/first-login.md` | First login guide |
| `data/help/getting-started/dashboard.md` | Dashboard guide |

### PTO Requests
| File | Purpose |
|------|---------|
| `data/help/pto-requests/submit-request.md` | How to submit requests |
| `data/help/pto-requests/view-requests.md` | View request history |
| `data/help/pto-requests/cancel-request.md` | Cancel requests |
| `data/help/pto-requests/view-balance.md` | View balances |
| `data/help/pto-requests/chicago-paid-leave.md` | Chicago Paid Leave guide |

### Calendar
| File | Purpose |
|------|---------|
| `data/help/calendar/calendar-overview.md` | Calendar features |
| `data/help/calendar/calendar-filters.md` | Calendar filtering |
| `data/help/calendar/calendar-export.md` | Export calendar |
| `data/help/calendar/market-holidays.md` | Market holidays |

### Carryover
| File | Purpose |
|------|---------|
| `data/help/carryover/carryover-overview.md` | Carryover rules |
| `data/help/carryover/submit-carryover.md` | Submit carryover request |
| `data/help/carryover/carryover-status.md` | Check carryover status |

### WFH Day Swap
| File | Purpose |
|------|---------|
| `data/help/wfh-swap/wfh-swap-overview.md` | WFH swap overview |
| `data/help/wfh-swap/requesting-swap.md` | How to request swap |
| `data/help/wfh-swap/responding-to-swaps.md` | Responding to requests |

### Managers
| File | Purpose |
|------|---------|
| `data/help/managers/approve-requests.md` | Approve/deny requests |
| `data/help/managers/carryover-approvals.md` | Carryover approvals |
| `data/help/managers/team-overview.md` | Team management |
| `data/help/managers/handbook-ai.md` | AI handbook analysis |
| `data/help/managers/trusted-employees.md` | Trusted employee feature |
| `data/help/managers/auto-notify-reports.md` | Auto notifications |
| `data/help/managers/manager-settings.md` | Manager settings |

### Reports
| File | Purpose |
|------|---------|
| `data/help/reports/reports-overview.md` | Reports overview |
| `data/help/reports/export-reports.md` | Export reports |
| `data/help/reports/analytics-dashboard.md` | Analytics dashboard |

### Admin
| File | Purpose |
|------|---------|
| `data/help/admin/employee-management.md` | Employee CRUD |
| `data/help/admin/department-management.md` | Department CRUD |
| `data/help/admin/pending-approvals.md` | Pending approvals |
| `data/help/admin/handbook-management.md` | Handbook management |
| `data/help/admin/system-settings.md` | System settings |
| `data/help/admin/year-end-processing.md` | Year-end processing |

### Technical
| File | Purpose |
|------|---------|
| `data/help/technical/troubleshooting.md` | Troubleshooting guide |
| `data/help/technical/keyboard-shortcuts.md` | Keyboard shortcuts |

### Scenarios
| File | Purpose |
|------|---------|
| `data/help/scenarios/scenario_transcripts.md` | Media Studio scenario transcripts |

**Total: 37 help article files**

---

## Project Root

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root Claude instructions |
| `.env` | Environment variables (DO NOT COMMIT) |
| `.env.example` | Environment template |
| `requirements.txt` | Python dependencies |
| `pyproject.toml` | Project configuration |
| `.gitignore` | Git ignore rules |
| `README.md` | Project documentation |
| `DEPLOYMENT.md` | Deployment guide |
| `BACKUP_SETUP.md` | Backup procedures |

---

## Recommended Injection Sets

### Minimal (Bug Fixes)
```
.claude/CLAUDE.md
.claude/rules/protected-logic.md
task/formulalogic.md
src/models/pto_balance.py
src/services/balance_service.py
src/services/pto_service.py
```

### Standard (Feature Work)
```
.claude/CLAUDE.md
.claude/rules/business-rules.md
.claude/rules/code-style.md
.claude/rules/protected-logic.md
task/formulalogic.md
src/constants.py
src/models/pto_balance.py
src/models/pto_request.py
src/models/user.py
src/services/balance_service.py
src/services/pto_service.py
nicegui_app/components/theme.py
```

### WFH Swap Work
```
.claude/CLAUDE.md
.claude/rules/business-rules.md
.claude/rules/wfh-swap-rules.md
src/models/user.py
src/models/wfh_day_swap.py
src/services/wfh_swap_service.py
src/services/audit_service.py
nicegui_app/pages/wfh_swap.py
data/help/wfh-swap/
```

### Media Studio Work
```
.claude/CLAUDE.md
.claude/rules/testing.md
task/media01.md
config/testing_config.py
services/playwright_engine.py
services/video_producer.py
services/audio_narration.py
nicegui_app/pages/testing_console.py
```

### MCP / RAG Work
```
.claude/CLAUDE.md
task/MCPRAG.md
task/MCPRAGv2.md
mcp/mcp_server.py
mcp/pto_central_mcp.py
scripts/rag_indexer.py
data/rag_index.json
```

### Full Context (Major Changes)
```
All files in .claude/
All files in task/
src/constants.py
src/config.py
src/database.py
All files in src/models/
All files in src/services/
nicegui_app/main.py
All files in nicegui_app/components/
Relevant page file(s) from nicegui_app/pages/
```

---

## Key Commands

```bash
# Run the application
venv\Scripts\python.exe nicegui_app/main.py

# Run tests
venv\Scripts\python.exe -m pytest tests/

# Syntax check
venv\Scripts\python.exe -m py_compile path/to/file.py

# Database migrations
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"

# Backup database
venv\Scripts\python.exe scripts/backup_db.py

# Restore database
venv\Scripts\python.exe scripts/restore_db.py

# Check brand color violations
venv\Scripts\python.exe scripts/check_brand_colors.py

# Build RAG index
venv\Scripts\python.exe scripts/rag_indexer.py

# Run MCP server
venv\Scripts\python.exe mcp/mcp_server.py
```

---

## File Statistics

| Category | Count |
|----------|-------|
| Models | 20 files |
| Services (src) | 31 files |
| Services (media) | 6 files |
| MCP | 3 files |
| Pages | 28 files |
| Components | 8 files |
| Schemas | 3 files |
| Scripts | 20 files |
| Rules | 7 files |
| Config | 4 files |
| Help Articles | 37 files |
| **Total Core** | ~167 files |

---

## Brand Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Brand Gold | #C9A227 | Primary accent, highlights |
| Navigation Gray | #5a6a72 | Headers, navigation |
| UI Blue | #2196F3 | Buttons, links |

**Import from theme:** `from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY, PTO_BLUE`

---

## User Roles

| Role | Capabilities |
|------|--------------|
| `employee` | Submit PTO, view own balances, WFH swap |
| `manager` | + Approve/deny team requests, auto-approve own |
| `admin` | + Manage employees, departments, system |
| `superadmin` | + Year-end processing, full system access |

---

## Environment Variables

```env
# Database
DATABASE_URL=sqlite:///pto_central.db

# Security
SECRET_KEY=your-secret-key

# Environment
ENVIRONMENT=development
DEBUG=True

# Email
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM_NAME=PTO Central

# SSL (optional)
PTO_SSL_CERT=certs/server.crt
PTO_SSL_KEY=certs/server.key
PTO_HOST=0.0.0.0
PTO_PORT=8080

# OpenAI (for Media Studio TTS)
OPENAI_API_KEY=your-openai-key
```

---

## Test Accounts (Media Studio)

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| ptouser01 | 2ez4me!! | employee | Standard employee |
| ptomanager | 2ez4me!! | manager | Team manager |
| ptoadmin | 2ez4me!! | admin | System admin |
| netadmin | netpass | admin | Super admin |

---

**END OF DOCUMENT**
