# PTO Central

Employee PTO (Paid Time Off) and Market Calendar management system for Haventech Solutions.

## Overview

PTO Central is a comprehensive employee scheduling system that integrates NYSE/CME/CBOE market holidays with PTO management. The system provides role-based access control, approval workflows, and complete audit trails for regulatory compliance.

## Features

- **PTO Request Management**: Submit, approve, deny, and cancel time-off requests
- **Balance Tracking**: Vacation, sick, personal days with carryover support
- **Team Calendar**: Visual calendar with market holidays and team PTO visibility
- **Manager Dashboard**: Approve/deny team requests, view team availability
- **Admin Controls**: Manage employees, departments, system settings
- **Trusted Employee System**: Auto-approve PTO for designated trusted employees
- **Multi-State Policy Support**: Chicago Safe Leave and location-specific policies
- **Audit Trail**: Complete logging of all PTO-related actions
- **Email Notifications**: Automated notifications for request status changes
- **Report Generation**: Export PTO reports in PDF, CSV, and HTML formats
- **iCal Export**: Download calendar events for Outlook/Google Calendar integration
- **Year-End Processing**: Automatic balance rollover and carryover handling

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | NiceGUI 2.x (Python-based reactive web UI) |
| Backend | Python 3.11+, FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
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
```

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
│   │   ├── reports.py     # Report generation
│   │   ├── admin_*.py     # Admin pages
│   │   └── manager_*.py   # Manager pages
│   └── components/        # Reusable UI components
│       ├── header.py      # Page headers
│       ├── theme.py       # Dark mode, dialogs
│       └── formatting.py  # Display helpers
├── src/
│   ├── models/            # SQLAlchemy models
│   ├── services/          # Business logic services
│   ├── schemas/           # Pydantic validation schemas
│   ├── config.py          # Application configuration
│   └── database.py        # Database connection
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

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: December 2025

### Completed Features
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
