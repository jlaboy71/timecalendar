# TJM Time Calendar - Project Overview

## Application Purpose
Employee PTO (Paid Time Off) and Market Calendar management system for TJM/Haventech. Built with NiceGUI (Python web framework) and SQLite database.

## Architecture
- **Frontend**: NiceGUI (Python-based reactive web UI)
- **Backend**: Python services with SQLAlchemy ORM
- **Database**: SQLite (`tjm_calendar.db`)
- **Migrations**: Alembic

## Key Directories
```
nicegui_app/          # UI layer
  pages/              # Page components (dashboard, calendar, reports, etc.)
  components/         # Reusable UI components
src/
  models/             # SQLAlchemy models
  services/           # Business logic services
  schemas/            # Pydantic schemas
alembic/              # Database migrations
```

## User Roles
- **employee**: Submit PTO requests, view own balances
- **manager**: Approve/deny team requests, auto-approve own PTO
- **admin**: Manage all employees, departments, system settings
- **superadmin**: Full system access including year-end processing

## Development Guidelines
1. Keep changes simple and minimal - impact as little code as possible
2. Find root causes for bugs - no temporary fixes
3. Use todo lists to track multi-step tasks
4. Check in with user before making significant changes

## Running the Application
```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe nicegui_app/main.py
```
Access at: http://localhost:8080

## Critical Reminders
- **Audit Trail**: Any action affecting PTO balances or requests must use `AuditService` (see `src/services/audit_service.py`)
- **Business Rules**: Reference `business-rules.md` when modifying PTO logic to ensure handbook compliance
- **Migrations**: Reference `database.md` checklist before adding/modifying model fields
- **Role Testing**: When adding features, verify behavior for all 4 roles (employee, manager, admin, superadmin)
