# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PTO Central (formerly TJM Time Calendar) is a PTO (Paid Time Off) and Market Calendar System for Haventech Solutions/TJM Holdings. Built with Python, NiceGUI, and SQLite using a three-tier architecture.

## Commands

```bash
# Run the application
python nicegui_app/main.py  # Starts on http://localhost:8080

# Run tests
pytest tests/
pytest tests/test_environment.py  # Verify environment setup

# Database operations
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
python scripts/seed.py            # Seed database
python scripts/create_test_users.py  # Create test users
```

## Architecture

### Three-Tier Structure

```
src/
├── models/         # SQLAlchemy ORM models (User, PTORequest, PTOBalance, Department, MarketHoliday)
├── services/       # Business logic (UserService, PTOService, BalanceService, DepartmentService)
├── schemas/        # Pydantic validation schemas
└── config.py       # Configuration from .env

nicegui_app/
├── main.py         # Application entry point with all routes
├── pages/          # Page components (login, dashboard, request_form)
└── components/     # Reusable UI components
```

### Key Patterns

**Service Layer**: All business logic in service classes with injected database sessions:
```python
UserService(db).authenticate_user(username, password)
PTOService(db).create_request(request_data)
```

**Database Sessions**: Use generator pattern with `get_db()` from `src/database.py`

**NiceGUI Pages**: Decorated with `@ui.page('/path')`, use `app.storage.user` for session data

**Role-Based Access**: Check `app.storage.user.get('user')['role']` for Admin/Manager/Employee

## Development Workflow

1. Think through the problem, read relevant codebase files, and write a plan to `task/todo.md`
2. The plan should have a list of todo items that you can check off as you complete them
3. Before you begin working, check in with me and I will verify the plan
4. Work on todo items, marking them complete as you go
5. Give high-level explanation of changes at each step
6. Add a review section to `task/todo.md` summarizing changes

## Code Philosophy

- **SIMPLICITY IS PARAMOUNT**: Every change should impact as little code as possible
- **NO LAZY FIXES**: Find root causes and fix them properly. No temporary workarounds.
- **MINIMAL IMPACT**: Only modify code directly relevant to the task
- **AVOID BUGS**: Simple, focused changes reduce bug introduction risk
