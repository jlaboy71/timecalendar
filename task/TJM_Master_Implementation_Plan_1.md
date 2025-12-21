# TJM TIME CALENDAR — MASTER IMPROVEMENT IMPLEMENTATION PLAN

**Document Version:** 1.0  
**Created:** December 16, 2025  
**Purpose:** Step-by-step guide to implement all assessment corrections safely  
**Guarantee:** Every change includes verification steps to ensure ZERO negative impact  

---

## CRITICAL SAFETY PROTOCOLS

### Before ANY Implementation Session

```
□ 1. Stop the TJM Calendar service
□ 2. Create timestamped backup:
      Compress-Archive -Path ".\tjm-calendar" -DestinationPath ".\tjm-calendar_BACKUP_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').zip"
□ 3. Verify backup integrity by checking file size
□ 4. Document current working state
□ 5. Only then proceed with changes
```

### After EVERY Change

```
□ 1. Run syntax check: venv\Scripts\python.exe -m py_compile [modified_file.py]
□ 2. Start application: venv\Scripts\python.exe nicegui_app/main.py
□ 3. Test affected functionality manually
□ 4. Verify no console errors
□ 5. If ANY issue: restore from backup immediately
```

### Rollback Procedure

```powershell
# If anything goes wrong:
1. Stop the service (Ctrl+C or close terminal)
2. Rename current folder: Rename-Item ".\tjm-calendar" ".\tjm-calendar_FAILED"
3. Extract backup: Expand-Archive -Path ".\tjm-calendar_BACKUP_[timestamp].zip" -DestinationPath ".\"
4. Restart service and verify
5. Document what went wrong before retrying
```

---

## IMPLEMENTATION PHASES

| Phase | Focus Area | Risk Level | Duration | Impact on Operations |
|-------|------------|------------|----------|---------------------|
| 1 | Documentation & README | NONE | 1 day | Zero downtime |
| 2 | Code Constants & Enums | LOW | 2 days | Zero downtime |
| 3 | Linting Configuration | NONE | 1 day | Zero downtime |
| 4 | Test Infrastructure | NONE | 3 days | Zero downtime |
| 5 | Unit Tests - Models | NONE | 2 days | Zero downtime |
| 6 | Unit Tests - Services | NONE | 5 days | Zero downtime |
| 7 | Security Headers | LOW | 1 day | Brief restart |
| 8 | Rate Limiting | LOW | 1 day | Brief restart |
| 9 | Health Check Endpoint | LOW | 1 day | Brief restart |
| 10 | Backup Automation | NONE | 1 day | Zero downtime |
| 11 | Query Style Standardization | MEDIUM | 3 days | Testing required |
| 12 | Help Service Refactor | MEDIUM | 2 days | Testing required |
| 13 | Transaction Boundaries | MEDIUM | 2 days | Testing required |
| 14 | Monitoring & Alerting | LOW | 2 days | Brief restart |

**Total Estimated Duration:** 27 days (spread across 90 days recommended)

---

## PHASE 1: DOCUMENTATION & README
**Risk Level:** NONE — No code changes  
**Estimated Time:** 1 day  
**Impact:** Zero downtime, no restart required  

### Task 1.1: Create README.md

**File to Create:** `README.md` (project root)

**Instructions for Claude:**
```
Create a comprehensive README.md file for the TJM Time Calendar project with the following sections:

1. Project Title and Description
2. Features list
3. Technology Stack (NiceGUI, FastAPI, SQLAlchemy, SQLite)
4. Prerequisites (Python 3.11+, Windows 11)
5. Installation Steps
6. Configuration (.env setup)
7. Running the Application
8. User Roles (employee, manager, admin, superadmin)
9. Project Structure overview
10. Development Guidelines (reference .claude/rules/)
11. License (Internal Use Only)

Base content on the existing .claude/CLAUDE.md file but expand for general readability.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created at project root
□ All sections present and accurate
□ No existing files modified
□ Application still starts normally
```

---

### Task 1.2: Create DEPLOYMENT.md

**File to Create:** `DEPLOYMENT.md` (project root)

**Instructions for Claude:**
```
Create a DEPLOYMENT.md file documenting production deployment steps:

1. Server Requirements
2. SSL Certificate Installation
3. Environment Configuration for Production
4. Service Installation (Windows Service or Task Scheduler)
5. Firewall Configuration
6. Backup Procedures
7. Monitoring Setup
8. Troubleshooting Common Issues

Reference existing src/config.py for SSL configuration options.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created at project root
□ Steps are accurate and complete
□ No existing files modified
```

---

## PHASE 2: CODE CONSTANTS & ENUMS
**Risk Level:** LOW — Additive changes only  
**Estimated Time:** 2 days  
**Impact:** Zero downtime during development  

### Task 2.1: Create UserRole Enum

**File to Create:** `src/constants.py`

**Instructions for Claude:**
```
Create a new file src/constants.py with the following enums and constants:

1. UserRole enum:
   - EMPLOYEE = 'employee'
   - MANAGER = 'manager'
   - ADMIN = 'admin'
   - SUPERADMIN = 'superadmin'

2. PTOStatus enum:
   - PENDING = 'pending'
   - APPROVED = 'approved'
   - DENIED = 'denied'
   - CANCELLED = 'cancelled'

3. PTOType enum:
   - VACATION = 'vacation'
   - SICK = 'sick'
   - PERSONAL = 'personal'
   - BEREAVEMENT = 'bereavement'
   - FMLA = 'fmla'
   - JURY_DUTY = 'jury_duty'
   - VOTING = 'voting'
   - MILITARY = 'military'

Use Python's enum.Enum with str mixin for JSON serialization compatibility.
Include docstrings explaining each enum's purpose.
Do NOT modify any existing files yet.
```

**Verification:**
```
□ File created with all enums
□ Syntax check passes: venv\Scripts\python.exe -m py_compile src/constants.py
□ Enums are importable: venv\Scripts\python.exe -c "from src.constants import UserRole; print(UserRole.ADMIN.value)"
□ Application still starts (constants not yet used)
```

---

### Task 2.2: Integrate Enums (One File at a Time)

**IMPORTANT:** Do ONE file at a time, test after each file.

**Instructions for Claude:**
```
I want to integrate the UserRole enum into the codebase. 

CRITICAL RULES:
1. Modify ONLY ONE FILE at a time
2. After each file, I will test before proceeding
3. Replace string literals with enum values
4. Ensure backward compatibility (enum.value returns the same string)

Start with: src/services/pto_service.py

Show me the exact changes (use str_replace format) and wait for my approval.
```

**File-by-File Integration Order:**
```
1. src/services/pto_service.py
   □ Change made □ Syntax check passed □ App starts □ Approval workflow tested

2. src/services/user_service.py
   □ Change made □ Syntax check passed □ App starts □ User management tested

3. nicegui_app/pages/login.py
   □ Change made □ Syntax check passed □ App starts □ Login tested

4. nicegui_app/pages/dashboard.py
   □ Change made □ Syntax check passed □ App starts □ Dashboard tested

5. [Continue for each file using role checks...]
```

**Verification After Each File:**
```
□ Syntax check passes
□ Application starts without errors
□ Affected functionality works correctly
□ Console shows no warnings or errors
```

---

## PHASE 3: LINTING CONFIGURATION
**Risk Level:** NONE — Configuration files only  
**Estimated Time:** 1 day  
**Impact:** Zero downtime  

### Task 3.1: Create Ruff Configuration

**File to Create:** `pyproject.toml` (project root)

**Instructions for Claude:**
```
Create a pyproject.toml file with Ruff linting configuration:

1. Set Python target version to 3.11
2. Set line length to 100
3. Enable rules for:
   - E (pycodestyle errors)
   - F (pyflakes)
   - I (isort)
   - UP (pyupgrade)
4. Exclude:
   - venv/
   - alembic/versions/
   - __pycache__/
5. Add per-file ignores for test files

Do NOT run the linter yet - just create the configuration.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created at project root
□ Application still starts (config file doesn't affect runtime)
```

---

### Task 3.2: Add Ruff to Requirements

**File to Modify:** `requirements.txt`

**Instructions for Claude:**
```
Add the following development dependencies to requirements.txt:

# Development Tools
ruff>=0.1.0
pytest-cov>=4.1.0

Add these at the end of the file under a new comment section.
Show me the exact change before applying.
```

**Verification:**
```
□ Requirements updated
□ Install new packages: venv\Scripts\pip.exe install -r requirements.txt
□ Ruff runs: venv\Scripts\ruff.exe check src/ --statistics
□ Application still starts
```

---

## PHASE 4: TEST INFRASTRUCTURE
**Risk Level:** NONE — New files only  
**Estimated Time:** 3 days  
**Impact:** Zero downtime  

### Task 4.1: Create Test Configuration

**File to Create:** `tests/conftest.py`

**Instructions for Claude:**
```
Create a pytest configuration file at tests/conftest.py with:

1. Fixture for in-memory SQLite test database
2. Fixture for database session that rolls back after each test
3. Fixture for creating test users (one of each role)
4. Fixture for creating test department
5. Fixture for creating test PTO balance

Requirements:
- Use in-memory SQLite (sqlite:///:memory:)
- Create all tables before tests
- Rollback/cleanup after each test
- Do NOT use production database

Reference src/database.py for session creation patterns.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created at tests/conftest.py
□ Syntax check passes
□ Pytest recognizes fixtures: venv\Scripts\python.exe -m pytest tests/conftest.py --collect-only
```

---

### Task 4.2: Create Test Utilities

**File to Create:** `tests/utils.py`

**Instructions for Claude:**
```
Create test utility functions at tests/utils.py:

1. create_test_user(db, role='employee', **overrides) -> User
2. create_test_department(db, **overrides) -> Department
3. create_test_pto_request(db, user, **overrides) -> PTORequest
4. create_test_balance(db, user, year, **overrides) -> PTOBalance

Each function should:
- Accept database session as first argument
- Use sensible defaults for all required fields
- Allow overrides via **kwargs
- Return the created object

Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ Syntax check passes
□ Imports work: venv\Scripts\python.exe -c "from tests.utils import create_test_user"
```

---

### Task 4.3: Create Empty Test Files

**Files to Create:**
- `tests/__init__.py`
- `tests/test_models/__init__.py`
- `tests/test_services/__init__.py`
- `tests/test_integration/__init__.py`

**Instructions for Claude:**
```
Create the test directory structure with empty __init__.py files:

tests/
  __init__.py
  conftest.py (already created)
  utils.py (already created)
  test_models/
    __init__.py
  test_services/
    __init__.py
  test_integration/
    __init__.py

Each __init__.py should be empty or contain a brief docstring.
Do NOT modify any existing files.
```

**Verification:**
```
□ All directories and files created
□ Pytest discovers test directories: venv\Scripts\python.exe -m pytest tests/ --collect-only
```

---

## PHASE 5: UNIT TESTS — MODELS
**Risk Level:** NONE — Test files only  
**Estimated Time:** 2 days  
**Impact:** Zero downtime  

### Task 5.1: User Model Tests

**File to Create:** `tests/test_models/test_user.py`

**Instructions for Claude:**
```
Create unit tests for the User model at tests/test_models/test_user.py:

Test cases:
1. test_user_creation - basic user creation with required fields
2. test_user_full_name_property - verify full_name returns "First Last"
3. test_user_default_role - verify default role is 'employee'
4. test_user_is_active_default - verify default is True
5. test_user_trusted_employee_fields - verify is_trusted, trusted_by_id, trusted_at
6. test_user_soft_delete - verify deleted_at field works
7. test_user_location_fields - verify location_state and location_city

Use the fixtures from conftest.py.
Each test should be independent and not affect others.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ Syntax check passes
□ Tests run: venv\Scripts\python.exe -m pytest tests/test_models/test_user.py -v
□ All tests pass
```

---

### Task 5.2: PTORequest Model Tests

**File to Create:** `tests/test_models/test_pto_request.py`

**Instructions for Claude:**
```
Create unit tests for the PTORequest model:

Test cases:
1. test_pto_request_creation - basic request creation
2. test_pto_request_default_status - verify default is 'pending'
3. test_pto_request_is_pending_property - verify is_pending property
4. test_pto_request_is_approved_property - verify is_approved property
5. test_pto_request_is_denied_property - verify is_denied property
6. test_pto_request_duration_days_property - verify calculation
7. test_pto_request_privacy_flag - verify is_private field
8. test_pto_request_cancellation_fields - verify cancellation tracking

Use the fixtures from conftest.py.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ All tests pass
□ No impact on application
```

---

### Task 5.3: PTOBalance Model Tests

**File to Create:** `tests/test_models/test_pto_balance.py`

**Instructions for Claude:**
```
Create unit tests for the PTOBalance model:

Test cases:
1. test_balance_creation - basic balance creation
2. test_balance_default_values - verify all defaults are Decimal('0.00')
3. test_balance_vacation_available_property - verify calculation
4. test_balance_sick_available_property - verify calculation
5. test_balance_personal_available_property - verify calculation
6. test_balance_unique_constraint - verify user_id + year uniqueness
7. test_balance_carryover_fields - verify carryover tracking

Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ All tests pass
□ Run full model test suite: venv\Scripts\python.exe -m pytest tests/test_models/ -v
```

---

## PHASE 6: UNIT TESTS — SERVICES
**Risk Level:** NONE — Test files only  
**Estimated Time:** 5 days  
**Impact:** Zero downtime  

### Task 6.1: BalanceService Tests

**File to Create:** `tests/test_services/test_balance_service.py`

**Instructions for Claude:**
```
Create unit tests for BalanceService:

Test cases:
1. test_get_or_create_balance_creates_new - new user gets new balance
2. test_get_or_create_balance_returns_existing - existing balance returned
3. test_get_user_balance - retrieve balance for user/year
4. test_update_balance_used - increment used correctly
5. test_update_balance_pending - increment/decrement pending
6. test_available_calculation - total + carryover - used - pending
7. test_balance_year_isolation - different years are separate

Use in-memory database from fixtures.
Test business logic, not database operations.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ All tests pass
□ Business logic validated
```

---

### Task 6.2: PTOService Tests

**File to Create:** `tests/test_services/test_pto_service.py`

**Instructions for Claude:**
```
Create unit tests for PTOService:

Test cases:
1. test_create_request - basic request creation
2. test_create_request_updates_pending - pending balance increases
3. test_approve_request - status changes, balance updated
4. test_approve_request_authorization - only authorized users can approve
5. test_deny_request - status changes, pending returned
6. test_cancel_request - status changes, pending returned
7. test_manager_auto_approve - manager PTO auto-approves
8. test_trusted_employee_auto_approve - trusted employee auto-approves
9. test_get_pending_requests - filter by status
10. test_get_user_requests - filter by user

Test the complete approval workflow.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ All tests pass
□ Approval workflow fully tested
```

---

### Task 6.3: Integration Test — Full Workflow

**File to Create:** `tests/test_integration/test_pto_workflow.py`

**Instructions for Claude:**
```
Create an integration test for the complete PTO workflow:

Test scenario:
1. Create employee user
2. Create manager user in same department
3. Create admin user
4. Create PTO balance for employee
5. Employee submits vacation request
6. Verify balance pending increased
7. Manager approves request
8. Verify status is approved
9. Verify balance used increased, pending decreased
10. Verify audit log entry created

This tests multiple services working together.
Use in-memory database.
Do NOT modify any existing files.
```

**Verification:**
```
□ File created
□ Integration test passes
□ Full test suite runs: venv\Scripts\python.exe -m pytest tests/ -v
□ Generate coverage: venv\Scripts\python.exe -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## PHASE 7: SECURITY HEADERS
**Risk Level:** LOW — Middleware addition  
**Estimated Time:** 1 day  
**Impact:** Brief restart required  

### Task 7.1: Create Security Middleware

**File to Create:** `src/middleware/security.py`

**Instructions for Claude:**
```
Create a security middleware file at src/middleware/security.py:

1. Create add_security_headers() function that adds:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - X-XSS-Protection: 1; mode=block
   - Referrer-Policy: strict-origin-when-cross-origin
   - Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:;

2. Make it compatible with NiceGUI/FastAPI middleware pattern

Do NOT modify any existing files yet.
Reference NiceGUI documentation for middleware integration.
```

**Verification:**
```
□ File created
□ Syntax check passes
```

---

### Task 7.2: Integrate Security Middleware

**File to Modify:** `nicegui_app/main.py`

**Instructions for Claude:**
```
Integrate the security middleware into main.py:

1. Import the security middleware
2. Add it to the FastAPI app BEFORE ui.run()
3. Ensure it doesn't break existing functionality

Show me the EXACT changes using str_replace format.
Wait for my approval before applying.
```

**Verification:**
```
□ Changes reviewed and approved
□ Application starts
□ Check headers in browser: Developer Tools > Network > Response Headers
□ Security headers present
□ All pages still load correctly
□ Login works
□ Dashboard works
```

---

## PHASE 8: RATE LIMITING
**Risk Level:** LOW — New functionality  
**Estimated Time:** 1 day  
**Impact:** Brief restart required  

### Task 8.1: Create Rate Limiter

**File to Create:** `src/middleware/rate_limit.py`

**Instructions for Claude:**
```
Create a simple rate limiter for login attempts at src/middleware/rate_limit.py:

Requirements:
1. Track failed login attempts by IP address
2. After 5 failed attempts, block for 15 minutes
3. Store attempts in memory (simple dict with timestamps)
4. Provide functions:
   - record_failed_attempt(ip: str)
   - is_blocked(ip: str) -> bool
   - clear_attempts(ip: str) - call on successful login
5. Auto-cleanup old entries periodically

Keep it simple - no external dependencies.
Do NOT modify any existing files yet.
```

**Verification:**
```
□ File created
□ Syntax check passes
□ Unit test created and passes
```

---

### Task 8.2: Integrate Rate Limiting into Login

**File to Modify:** `nicegui_app/pages/login.py`

**Instructions for Claude:**
```
Integrate rate limiting into the login page:

1. Import the rate limiter
2. Before attempting login, check if IP is blocked
3. If blocked, show message: "Too many failed attempts. Please try again in 15 minutes."
4. On failed login, record the attempt
5. On successful login, clear attempts for that IP

Show me the EXACT changes using str_replace format.
Wait for my approval before applying.
```

**Verification:**
```
□ Changes reviewed and approved
□ Application starts
□ Normal login works
□ Test: Enter wrong password 5 times
□ Verify blocked message appears
□ Wait 15 minutes (or adjust for testing) and verify unblocked
```

---

## PHASE 9: HEALTH CHECK ENDPOINT
**Risk Level:** LOW — New endpoint  
**Estimated Time:** 1 day  
**Impact:** Brief restart required  

### Task 9.1: Create Health Check Endpoint

**File to Modify:** `nicegui_app/main.py`

**Instructions for Claude:**
```
Add a health check endpoint to main.py:

1. Create route at /health
2. Return JSON with:
   - status: "healthy" or "unhealthy"
   - timestamp: current UTC time
   - database: "connected" or "error"
   - version: application version (read from somewhere or hardcode "1.0.0")
3. Test database connection by executing a simple query
4. Return 200 if healthy, 503 if unhealthy

Show me the EXACT changes using str_replace format.
Wait for my approval before applying.
```

**Verification:**
```
□ Changes applied
□ Application starts
□ Access http://localhost:8080/health
□ Returns JSON with healthy status
□ Stop database (rename .db file) and verify unhealthy response
□ Restore database and verify healthy again
```

---

## PHASE 10: BACKUP AUTOMATION
**Risk Level:** NONE — External script  
**Estimated Time:** 1 day  
**Impact:** Zero downtime  

### Task 10.1: Create Backup Script

**File to Create:** `scripts/backup.ps1`

**Instructions for Claude:**
```
Create a PowerShell backup script at scripts/backup.ps1:

1. Define backup directory (configurable)
2. Create timestamped backup filename
3. Copy database file to backup directory
4. Keep only last 7 daily backups (delete older)
5. Log backup operations to backup.log
6. Return exit code 0 on success, 1 on failure

Include comments explaining each step.
Do NOT modify any existing files.
```

**Verification:**
```
□ Script created
□ Run manually: powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
□ Backup file created in backup directory
□ Log file updated
```

---

### Task 10.2: Create Task Scheduler Instructions

**File to Create:** `scripts/BACKUP_SETUP.md`

**Instructions for Claude:**
```
Create documentation for setting up automated backups:

1. Windows Task Scheduler setup steps
2. Recommended schedule (daily at 2 AM)
3. How to verify backups are running
4. How to restore from backup
5. Troubleshooting common issues

Do NOT modify any existing files.
```

**Verification:**
```
□ Documentation created
□ Steps are clear and accurate
```

---

## PHASE 11: QUERY STYLE STANDARDIZATION
**Risk Level:** MEDIUM — Modifying existing code  
**Estimated Time:** 3 days  
**Impact:** Thorough testing required  

### Pre-Phase Checklist
```
□ All Phase 6 tests passing
□ Fresh backup created
□ Test environment ready
```

### Task 11.1: Identify All Legacy Queries

**Instructions for Claude:**
```
Search the codebase for all instances of legacy SQLAlchemy 1.x query style:
- db.query(Model)
- .filter(
- .filter_by(

List each file and line number.
Do NOT modify anything yet.
```

---

### Task 11.2: Convert One File at a Time

**Process for EACH file:**

```
1. □ Create backup of specific file
2. □ Convert legacy queries to 2.0 style:
      FROM: db.query(Model).filter(Model.id == x).first()
      TO:   stmt = select(Model).where(Model.id == x)
            db.execute(stmt).scalar_one_or_none()
3. □ Run syntax check
4. □ Run related unit tests
5. □ Start application
6. □ Test affected functionality manually
7. □ If any failure: restore file from backup
8. □ Document conversion in changelog
```

**Conversion Order (lowest risk first):**
```
1. src/services/department_service.py
2. src/services/analytics_service.py
3. src/services/report_service.py
4. src/services/user_service.py
5. src/services/balance_service.py
6. src/services/pto_service.py (highest risk - most critical)
```

---

## PHASE 12: HELP SERVICE REFACTOR
**Risk Level:** MEDIUM — Large file modification  
**Estimated Time:** 2 days  
**Impact:** Help system testing required  

### Task 12.1: Extract Help Content to Files

**Directory to Create:** `data/help/`

**Instructions for Claude:**
```
Extract help content from help_service.py to separate Markdown files:

1. Create data/help/ directory
2. For each chapter in CHAPTERS dict, create:
   - data/help/[chapter-id]/[article-id].md
3. Each .md file contains only the content (no Python)
4. Create data/help/manifest.json with chapter metadata:
   - title, icon, order, required_role, articles list

Do NOT modify help_service.py yet.
```

**Verification:**
```
□ All content files created
□ Manifest.json valid JSON
□ No existing files modified
```

---

### Task 12.2: Update HelpService to Load from Files

**Instructions for Claude:**
```
Modify src/services/help_service.py to:

1. Load content from data/help/ files instead of inline strings
2. Read manifest.json for structure
3. Cache loaded content in memory
4. Keep all existing public methods working identically
5. Add fallback to inline content if files missing

Show me the changes in small chunks.
Wait for approval before each chunk.
```

**Verification:**
```
□ Each change chunk approved
□ Syntax check passes
□ Application starts
□ Help page loads
□ Search works
□ All articles display correctly
□ Role filtering still works
```

---

## PHASE 13: TRANSACTION BOUNDARIES
**Risk Level:** MEDIUM — Critical business logic  
**Estimated Time:** 2 days  
**Impact:** Approval workflow testing required  

### Task 13.1: Identify Multi-Commit Operations

**Instructions for Claude:**
```
Search for operations in services that have multiple db.commit() calls
or that modify multiple tables without transaction wrapping.

Priority operations:
1. PTOService.approve_request
2. PTOService.deny_request
3. PTOService.cancel_request
4. YearEndService.process_year_end
5. BalanceService balance adjustments

List each location.
Do NOT modify anything yet.
```

---

### Task 13.2: Add Transaction Wrapper

**Instructions for Claude:**
```
For each identified operation, wrap in explicit transaction:

Pattern:
```python
def approve_request(self, ...):
    try:
        # All operations here
        self.db.commit()
    except Exception as e:
        self.db.rollback()
        raise
```

Or use context manager if available:
```python
with self.db.begin():
    # All operations here
```

Modify ONE function at a time.
Show me exact changes.
Wait for approval.
Test approval workflow after each change.
```

**Verification for EACH change:**
```
□ Change approved
□ Syntax check passes
□ Application starts
□ Create test PTO request
□ Approve request - verify success
□ Check balance updated correctly
□ Check audit log created
□ Deny a request - verify rollback on simulated failure
```

---

## PHASE 14: MONITORING & ALERTING
**Risk Level:** LOW — New functionality  
**Estimated Time:** 2 days  
**Impact:** Brief restart required  

### Task 14.1: Create Error Notification Service

**File to Create:** `src/services/monitoring_service.py`

**Instructions for Claude:**
```
Create a monitoring service at src/services/monitoring_service.py:

1. Function to send email alert on critical errors
2. Function to log performance metrics
3. Integration with existing EmailService
4. Configurable alert thresholds
5. Rate limiting on alerts (max 1 per hour per error type)

Use existing email infrastructure.
Do NOT modify any existing files yet.
```

**Verification:**
```
□ File created
□ Syntax check passes
□ Unit tests created and pass
```

---

### Task 14.2: Integrate Error Alerting

**File to Modify:** `nicegui_app/main.py`

**Instructions for Claude:**
```
Add global exception handler that:

1. Logs all unhandled exceptions
2. Sends email alert for critical errors
3. Returns user-friendly error page
4. Does not expose stack traces to users

Show me exact changes.
Wait for approval.
```

**Verification:**
```
□ Changes applied
□ Application starts
□ Simulate error (e.g., stop database)
□ Verify alert email sent (or logged if email not configured)
□ Verify user sees friendly error, not stack trace
```

---

## FINAL VERIFICATION CHECKLIST

After completing all phases:

```
□ All unit tests pass: venv\Scripts\python.exe -m pytest tests/ -v
□ Test coverage > 70%: venv\Scripts\python.exe -m pytest tests/ --cov=src
□ Application starts without errors
□ Login works for all 4 roles
□ PTO request submission works
□ PTO approval workflow works
□ Balance calculations correct
□ Reports generate correctly
□ Calendar displays correctly
□ Help system works
□ Health check returns healthy
□ Security headers present in responses
□ Rate limiting blocks after 5 failures
□ Backup script runs successfully
□ No console errors during normal operation
```

---

## IMPLEMENTATION SCHEDULE RECOMMENDATION

| Week | Phases | Focus |
|------|--------|-------|
| 1 | 1, 2, 3 | Documentation, Constants, Linting |
| 2-3 | 4, 5, 6 | Test Infrastructure & Unit Tests |
| 4 | 7, 8, 9 | Security & Health Check |
| 5 | 10 | Backup Automation |
| 6-7 | 11 | Query Standardization |
| 8 | 12 | Help Service Refactor |
| 9 | 13 | Transaction Boundaries |
| 10 | 14 | Monitoring & Alerting |

**Total: 10 weeks** for careful, tested implementation

---

## GUARANTEE STATEMENT

This implementation plan is designed with the following guarantees:

1. **No Blind Changes:** Every modification requires explicit approval before execution
2. **Incremental Approach:** One change at a time, tested before proceeding
3. **Immediate Rollback:** Clear instructions for reverting if anything fails
4. **Zero Data Loss:** Database is never modified without backup
5. **Business Continuity:** System can remain operational during development phases
6. **Verification at Every Step:** Specific test criteria must pass before proceeding

**If followed exactly as written, this plan will NOT cause:**
- Application crashes
- Data corruption
- Lost functionality
- Security regressions
- Business process interruptions

---

**Document Prepared By:** Claude (AI Assistant)  
**For:** Jose LaBoy, CTO - TJM Holdings / Haventech Solutions  
**Date:** December 16, 2025
