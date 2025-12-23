# PTO Central v2.0 - Project Status
**Last Updated**: December 23, 2025
**Status**: Production Ready

---

## Executive Summary

PTO Central v2.0 is complete and ready for production deployment. The application has evolved from a standard PTO management system into an AI-powered platform with the Smart Scheduler Agent and peer-to-peer WFH Day Swap features.

### What's New in v2.0
| Feature | Description |
|---------|-------------|
| **Smart Scheduler Agent** | AI assistant for PTO planning with RAG knowledge base |
| **WFH Day Swap** | Peer-to-peer work-from-home day exchange system |
| **Safety Gate** | Token-based human-in-the-loop confirmation for AI actions |
| **Calendar Verification** | Prevents AI date hallucination with `get_calendar_info()` tool |
| **Brand Centralization** | All brand colors consolidated to `theme.py` constants |
| **System Identity Doctrine** | Canonical documentation for RAG retrieval and self-knowledge |

---

## Architecture Overview

```
PTO Central v2.0
├── UI Layer (NiceGUI)
│   ├── Pages: dashboard, calendar, assistant, wfh_swap, reports, admin_*
│   └── Components: header, theme, formatting
│
├── Service Layer
│   ├── Core: PTOService, BalanceService, UserService
│   ├── AI: AgentService (SmartSchedulerAgent)
│   └── Features: WFHSwapService, EmailService, AuditService
│
├── Data Layer
│   ├── SQLite: pto_central.db
│   ├── Models: User, PTORequest, PTOBalance, WFHDaySwapRequest
│   └── Migrations: Alembic
│
├── AI/MCP Layer
│   ├── RAG Index: data/rag_index.json (418 chunks)
│   ├── MCP Tools: mcp/pto_central_mcp.py (14 tools)
│   └── Safety Gate: confirm_action() with token verification
│
└── Doctrine Layer
    ├── System Identity: task/system_identity.md
    ├── Creator Profile: task/creator_profile.md
    ├── Knowledge Contract: task/knowledge_contract.md
    └── DoctrineQueryService: src/services/doctrine_query_service.py
```

---

## Key Files Reference

### Core Application
| File | Purpose |
|------|---------|
| `nicegui_app/main.py` | Application entry point |
| `nicegui_app/pages/assistant.py` | Smart Scheduler AI chat interface |
| `nicegui_app/pages/wfh_swap.py` | WFH Day Swap UI |
| `nicegui_app/pages/dashboard.py` | Main employee dashboard |
| `nicegui_app/components/theme.py` | Brand colors (PTO_GOLD, PTO_GRAY, PTO_BLUE) |

### AI/Agent System
| File | Purpose |
|------|---------|
| `src/services/agent_service.py` | SmartSchedulerAgent orchestration |
| `mcp/pto_central_mcp.py` | MCP tools (get_balance, submit_pto_request, etc.) |
| `mcp/mcp_server.py` | RAG query server |
| `data/rag_index.json` | Policy document index (381 chunks) |

### Business Logic
| File | Purpose |
|------|---------|
| `src/services/pto_service.py` | PTO request lifecycle (PROTECTED) |
| `src/services/balance_service.py` | Balance calculations (PROTECTED) |
| `src/services/wfh_swap_service.py` | WFH swap validation and lifecycle |
| `src/services/audit_service.py` | Audit trail logging |

---

## Running the Application

```bash
# Start the application
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe nicegui_app/main.py

# Access at: https://localhost:8080
```

### Required Environment Variables
```env
SECRET_KEY=<64-character-hex>
ANTHROPIC_API_KEY=<your-api-key>  # Required for AI features
```

---

## Deployment Checklist

### Pre-Production
- [ ] Set `ENVIRONMENT=production` in .env
- [ ] Set `DEBUG=False` in .env
- [ ] Rotate API keys (Anthropic, SMTP)
- [ ] Verify HTTPS is working
- [ ] Test all user roles (employee, manager, admin, superadmin)

### Database
- [ ] Run final backup: `python scripts/backup_db.py`
- [ ] Verify migrations: `alembic upgrade head`

### Optional: Git Tag
```bash
git add -A
git commit -m "chore: v2.0 release"
git tag -a v2.0 -m "Release v2.0: AI Agent and WFH Swap"
```

---

## Future Roadmap (Deferred)

These items are planned but not blocking v2.0:

### Manager AI Phase
- [ ] `approve_pto_request` tool - AI can approve with manager confirmation
- [ ] `cancel_pto_request` tool - AI can cancel with manager confirmation

### Testing Automation
- [ ] `pto-testing-automation` skill package

---

## Documentation Reference

| Document | Location |
|----------|----------|
| Business Rules | `.claude/rules/business-rules.md` |
| Code Style | `.claude/rules/code-style.md` |
| Database Schema | `.claude/rules/database.md` |
| UI Patterns | `.claude/rules/ui-patterns.md` |
| WFH Swap Rules | `.claude/rules/wfh-swap-rules.md` |
| Protected Logic | `.claude/rules/protected-logic.md` |
| Testing Guidelines | `.claude/rules/testing.md` |

---

## Quick Commands

```bash
# Run tests
venv\Scripts\python.exe -m pytest tests/ -v

# Syntax check
venv\Scripts\python.exe -m py_compile path/to/file.py

# Database backup
venv\Scripts\python.exe scripts/backup_db.py

# Lock dependencies
venv\Scripts\pip.exe freeze > requirements.txt

# Generate SSL cert
venv\Scripts\python.exe scripts/generate_ssl_cert.py
```

---

## Support

**Project Lead**: Jose LaBoy, CTO
**Organization**: Haventech Solutions
**Version**: 2.0.0
**Last Backup**: December 23, 2025
