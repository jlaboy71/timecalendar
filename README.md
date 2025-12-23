# PTO Central

Employee PTO (Paid Time Off) and Market Calendar management system for Haventech Solutions.

## Overview

PTO Central is a comprehensive employee scheduling system that integrates NYSE/CME/CBOE market holidays with PTO management. The system provides role-based access control, approval workflows, and complete audit trails for regulatory compliance.

## Features

### Core PTO Management
- **PTO Request Management**: Submit, approve, deny, and cancel time-off requests
- **Balance Tracking**: Vacation, sick, personal days with carryover support
- **Team Calendar**: Visual calendar with market holidays and team PTO visibility
- **Manager Dashboard**: Approve/deny team requests, view team availability
- **Admin Controls**: Manage employees, departments, system settings

### AI-Powered Features
- **Smart Scheduler Agent**: AI assistant that helps employees find optimal vacation dates, checks balances, team coverage, and can submit requests with human-in-the-loop confirmation
- **RAG Knowledge Base**: Policy documents indexed for accurate AI responses about carryover rules, leave policies, and company procedures

### Collaboration Features
- **WFH Day Swap**: Peer-to-peer work-from-home day exchange system with weekly limits and federal holiday awareness
- **Trusted Employee System**: Auto-approve PTO for designated trusted employees

### Enterprise Features
- **Multi-State Policy Support**: Chicago Paid Leave and location-specific policies
- **Audit Trail**: Complete logging of all PTO-related actions
- **Email Notifications**: Automated notifications for request status changes
- **Report Generation**: Export PTO reports in PDF, CSV, and HTML formats
- **iCal Export**: Download calendar events for Outlook/Google Calendar integration
- **Year-End Processing**: Automatic balance rollover and carryover handling

### UI/UX
- **Gold/Dark Theme**: Professional dark mode with TJM gold accent colors
- **Mobile-Responsive**: Works on desktop and mobile devices

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | NiceGUI 2.x (Python-based reactive web UI) |
| Backend | Python 3.11+, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| AI | Anthropic Claude (Smart Scheduler Agent) |
| Styling | Tailwind CSS, Quasar Components |
| SSL | HTTPS with custom certificates |

## Prerequisites

- Python 3.11 or higher
- Windows 11 (primary supported platform)
- Git (for version control)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TimeCalendar
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize the database**
   ```bash
   # Database tables are created automatically on first run
   # Or run migrations explicitly:
   venv\Scripts\python.exe -m alembic upgrade head
   ```

## Configuration

Create a `.env` file in the project root (or set environment variables):

```env
# Application Settings
SECRET_KEY=your-secret-key-here
HOST=0.0.0.0
PORT=8080

# SSL Configuration (optional)
SSL_ENABLED=false
SSL_CERTFILE=certs/server.crt
SSL_KEYFILE=certs/server.key

# Email Configuration (optional)
EMAIL_ENABLED=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@ptocentral.haventech.com
EMAIL_FROM_NAME=PTO Central

# Digest Scheduler
ENABLE_DIGEST_SCHEDULER=true

# AI Features (Smart Scheduler Agent)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

> **Note**: The `ANTHROPIC_API_KEY` is required for the Smart Scheduler Agent feature. Without it, the AI assistant will be disabled but all other features work normally.

## Running the Application

```bash
# Development mode
venv\Scripts\python.exe nicegui_app/main.py
```

Access the application at: `https://localhost:8080` (or `http://` if SSL disabled)

## User Roles

| Role | Permissions |
|------|-------------|
| **Employee** | Submit PTO requests, view own balances, request cancellations |
| **Manager** | Employee permissions + approve/deny team requests, auto-approve own PTO |
| **Admin** | Manager permissions + manage employees, departments, view all data |
| **Superadmin** | Full system access including year-end processing, system settings |

## Project Structure

```
TimeCalendar/
├── nicegui_app/           # UI layer
│   ├── main.py            # Application entry point
│   ├── pages/             # Page components
│   │   ├── dashboard.py   # Main dashboard
│   │   ├── calendar.py    # Team calendar
│   │   ├── assistant.py   # Smart Scheduler AI chat
│   │   ├── wfh_swap.py    # WFH Day Swap
│   │   ├── reports.py     # Report generation
│   │   ├── admin_*.py     # Admin pages
│   │   └── manager_*.py   # Manager pages
│   └── components/        # Reusable UI components
│       ├── header.py      # Page headers
│       ├── theme.py       # Dark mode, brand colors
│       └── formatting.py  # Display helpers
├── src/
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Business logic services
│   │   ├── agent_service.py   # AI agent orchestration
│   │   └── wfh_swap_service.py # WFH swap logic
│   ├── schemas/           # Pydantic validation schemas
│   ├── config.py          # Application configuration
│   └── database.py        # Database connection
├── mcp/                   # MCP tools for AI agents
│   ├── mcp_server.py      # RAG query server
│   └── pto_central_mcp.py # PTO-specific tools
├── skills/                # Claude Code skill packages
├── data/                  # RAG index and help docs
├── alembic/               # Database migrations
├── tests/                 # Test files
├── certs/                 # SSL certificates
├── .claude/               # Development documentation
│   └── rules/             # Code style and business rules
└── requirements.txt       # Python dependencies
```

## Development Guidelines

For detailed development rules, see `.claude/rules/`:

- **code-style.md**: Python conventions, NiceGUI patterns, service layer patterns
- **business-rules.md**: PTO balance system, request workflow, leave types
- **database.md**: Schema documentation, model relationships
- **ui-patterns.md**: Theme colors, component patterns, status badges
- **testing.md**: Test framework, verification steps

### Key Principles

1. **Keep changes simple** - Impact as little code as possible
2. **Find root causes** - No temporary fixes for bugs
3. **Test all roles** - Verify features work for all user types
4. **Audit trail** - Log all PTO-affecting actions via `AuditService`
5. **Follow existing patterns** - Check codebase before proposing new elements

### Testing

```bash
# Run all tests
venv\Scripts\python.exe -m pytest tests/ -v

# Syntax check
venv\Scripts\python.exe -m py_compile path/to/file.py

# Import test
venv\Scripts\python.exe -c "from nicegui_app.main import *; print('OK')"
```

## Health Check

Access `/health` endpoint to verify system status:
```
https://localhost:8080/health
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | System health check |
| `/api/calendar/export` | Export calendar to iCal format |
| `/api/reports/team-pto` | Export team PTO reports |

## Current Status

**Version**: 2.0.0
**Status**: Production Ready
**Last Updated**: December 2025

### Recent Updates (v2.0)
- Smart Scheduler Agent (AI-powered PTO planning)
- WFH Day Swap (peer-to-peer schedule exchange)
- RAG Knowledge Base (policy document search)
- Gold/Dark Theme (professional UI refresh)
- Calendar date verification (prevents AI date hallucination)

### Core Features
- Full PTO request lifecycle
- Manager approval workflows
- Admin employee management
- Team calendar with filtering
- Report generation (PDF/CSV/HTML)
- Email notifications
- Audit logging
- Year-end processing
- Trusted employee auto-approve
- Multi-state policy support

## License

**Internal Use Only** - Haventech Solutions

---

**Project Lead**: Jose LaBoy, CTO
**Organization**: Haventech Solutions
