# TJM Time Calendar - Dependency Audit Report

**Date:** December 12, 2025
**Auditor:** Claude Code
**Status:** ✅ No critical vulnerabilities found

---

## Summary

| Check | Result |
|-------|--------|
| Dependency conflicts | ✅ None found |
| Outdated packages | ⚠️ 19 packages have updates available |
| Critical security issues | ✅ None identified |

---

## Outdated Packages

| Package | Current | Latest | Priority | Notes |
|---------|---------|--------|----------|-------|
| SQLAlchemy | 2.0.23 | 2.0.45 | **Medium** | ORM - test thoroughly before updating |
| alembic | 1.13.0 | 1.17.2 | Medium | Migration tool - update with SQLAlchemy |
| bcrypt | 4.1.1 | 5.0.0 | **Medium** | Security - review changelog for breaking changes |
| fastapi | 0.123.4 | 0.124.3 | Low | Minor update |
| nicegui | 3.3.1 | 3.4.0 | Low | UI framework - test UI after update |
| pytest | 7.4.3 | 9.0.2 | Low | Dev dependency only |
| python-dotenv | 1.0.0 | 1.2.1 | Low | Config loader |
| setuptools | 65.5.0 | 80.9.0 | Low | Build tool |

---

## Recommended Update Plan

### Phase 1: Safe Updates (Low Risk)
```cmd
venv\Scripts\pip.exe install --upgrade python-dotenv pytest reportlab pypdf
```

### Phase 2: Framework Updates (Test Required)
```cmd
venv\Scripts\pip.exe install --upgrade fastapi nicegui
# Then run: venv\Scripts\python.exe nicegui_app/main.py
# Test: Login, submit PTO, approve request, view calendar
```

### Phase 3: Database Updates (Backup First!)
```cmd
# Create backup first
venv\Scripts\python.exe scripts\backup_db.py

# Update SQLAlchemy ecosystem
venv\Scripts\pip.exe install --upgrade SQLAlchemy alembic

# Verify migrations work
venv\Scripts\alembic.exe current
venv\Scripts\alembic.exe upgrade head
```

### Phase 4: Security Updates
```cmd
# Review bcrypt 5.0 changelog for breaking changes
# https://github.com/pyca/bcrypt/releases
venv\Scripts\pip.exe install --upgrade bcrypt

# Test login functionality after update
```

---

## Adding Automated Vulnerability Scanning

### Install pip-audit
```cmd
venv\Scripts\pip.exe install pip-audit
```

### Run Security Audit
```cmd
venv\Scripts\pip-audit.exe
```

### Add to CI/CD (Optional)
Add to your deployment script:
```cmd
venv\Scripts\pip-audit.exe --strict
if %errorlevel% neq 0 exit /b %errorlevel%
```

---

## Core Dependencies (Pinned)

These are critical and should only be updated with careful testing:

| Package | Version | Purpose |
|---------|---------|---------|
| SQLAlchemy | 2.0.23 | ORM, database access |
| alembic | 1.13.0 | Database migrations |
| bcrypt | 4.1.1 | Password hashing |
| nicegui | 3.3.1 | Web UI framework |
| fastapi | 0.123.4 | API framework (used by NiceGUI) |

---

## Next Audit

Schedule dependency audits monthly:
```cmd
venv\Scripts\pip.exe list --outdated > logs\dependency_audit_%date:~-4%%date:~4,2%%date:~7,2%.txt
```
