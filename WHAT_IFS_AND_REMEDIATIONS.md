# PTO Central - What-If Scenarios and Remediations

This document enumerates high-impact what-if scenarios across the PTO Central system and documents existing controls, detection mechanisms, and recovery procedures.

**Generated:** December 12, 2025
**Codebase Version:** feature/nicegui-migration branch

---

## Table of Contents

1. [Authentication and Authorization](#1-authentication-and-authorization)
2. [Data Integrity and Validation](#2-data-integrity-and-validation)
3. [Time and Date Logic](#3-time-and-date-logic)
4. [PTO Policy Rules](#4-pto-policy-rules)
5. [Concurrency and Race Conditions](#5-concurrency-and-race-conditions)
6. [API and Backend Failures](#6-api-and-backend-failures)
7. [Database Concerns](#7-database-concerns)
8. [Frontend Input Errors and UX Failure Modes](#8-frontend-input-errors-and-ux-failure-modes)
9. [Notifications and Integrations](#9-notifications-and-integrations)
10. [Security](#10-security)
11. [Observability](#11-observability)
12. [Deployment and Environment Drift](#12-deployment-and-environment-drift)
13. [Disaster Recovery and Business Continuity](#13-disaster-recovery-and-business-continuity)
14. [Compliance and Auditability](#14-compliance-and-auditability)
15. [Gap Register](#gap-register)

---

## 1. Authentication and Authorization

### AUTH-001: Brute Force Login Attacks

| Field | Details |
|-------|---------|
| **Scenario ID** | AUTH-001 |
| **Description** | Attacker attempts to guess user passwords through repeated login attempts |
| **Impact** | High - Unauthorized access to employee PTO data and system functions |
| **Detection Signals** | Logs show multiple `login_failed` audit entries for same username; User sees lockout message |
| **Current Remediation** | **LoginRateLimiter** (`src/services/rate_limiter.py:8-107`) implements in-memory rate limiting: 5 failed attempts triggers 15-minute lockout. `record_failed_attempt()` tracks attempts per username (case-insensitive). Login page (`nicegui_app/pages/login.py:70-74`) checks lockout before authentication. |
| **Recovery Steps** | 1. Wait for lockout to expire (15 min) OR 2. Restart application to clear in-memory rate limiter state |
| **Residual Risk** | Low - Lockout is effective but in-memory storage resets on app restart |
| **Recommended Improvement** | Consider persisting lockout state to database for multi-instance deployments |

### AUTH-002: Session Hijacking/Fixation

| Field | Details |
|-------|---------|
| **Scenario ID** | AUTH-002 |
| **Description** | Attacker steals or fixates user session to gain unauthorized access |
| **Impact** | High - Full access to victim's account and data |
| **Detection Signals** | Unusual activity patterns in audit logs; User reports unexpected actions |
| **Current Remediation** | NiceGUI uses `storage_secret` from `SECRET_KEY` env var for session encryption (`nicegui_app/main.py:337`). Session timeout after 30 minutes inactivity (`src/services/session_manager.py:16`). `SessionManager.check_and_redirect_if_expired()` validates on each protected page. |
| **Recovery Steps** | 1. User logs out/session expires 2. Admin can review audit logs for suspicious activity |
| **Residual Risk** | Medium - No explicit session regeneration on privilege changes |
| **Recommended Improvement** | None - Current implementation adequate for internal business app |

### AUTH-003: Unauthorized Role Escalation

| Field | Details |
|-------|---------|
| **Scenario ID** | AUTH-003 |
| **Description** | User attempts to access functions above their role level |
| **Impact** | High - Unauthorized approvals, data access, or system changes |
| **Detection Signals** | "Access denied" messages in UI; Audit logs of denied actions |
| **Current Remediation** | Role checks at page level: `manager_request_detail.py:20-22` checks `user_role in ['manager', 'admin', 'superadmin']`. Department-scoped access for managers: `manager_request_detail.py:34-38`. Admin pages check roles in each page function. |
| **Recovery Steps** | 1. No recovery needed - access blocked 2. Review audit logs for attempted escalation patterns |
| **Residual Risk** | Low - Consistent role checking across pages |
| **Recommended Improvement** | None |

### AUTH-004: Password Reset Token Abuse

| Field | Details |
|-------|---------|
| **Scenario ID** | AUTH-004 |
| **Description** | Attacker obtains or guesses password reset token |
| **Impact** | High - Account takeover |
| **Detection Signals** | Multiple reset token requests in logs; Token validation failures |
| **Current Remediation** | `PasswordResetService` (`src/services/password_reset_service.py`) implements: Token expiration check (`token_record.is_expired`), Single-use tokens (`used` flag), Previous tokens invalidated on new request (lines 31-35). Tokens validated against user active status. |
| **Recovery Steps** | 1. Generate new token 2. Mark compromised token as used |
| **Residual Risk** | Medium - Tokens stored in plaintext (noted in code comment line 43) |
| **Recommended Improvement** | Hash tokens before storage |

---

## 2. Data Integrity and Validation

### DATA-001: Invalid PTO Request Data Submitted

| Field | Details |
|-------|---------|
| **Scenario ID** | DATA-001 |
| **Description** | User submits PTO request with invalid dates, negative days, or invalid type |
| **Impact** | Medium - Corrupted data, incorrect balance calculations |
| **Detection Signals** | ValueError exceptions; Validation error messages in UI |
| **Current Remediation** | **Multi-layer validation:** 1. Pydantic schemas (`src/schemas/pto_schemas.py:19-25`) validate end_date >= start_date 2. `PTOService.create_request()` (`src/services/pto_service.py:53-59`) validates dates not in past, start <= end 3. `src/utils/validators.py` provides `validate_date_range()`, `validate_pto_days()`, `validate_pto_type()` |
| **Recovery Steps** | 1. Validation prevents bad data entry 2. If bypassed: Admin can edit/delete via database |
| **Residual Risk** | Low - Multiple validation layers |
| **Recommended Improvement** | None |

### DATA-002: Balance Goes Negative (Sick/Personal)

| Field | Details |
|-------|---------|
| **Scenario ID** | DATA-002 |
| **Description** | User requests more sick/personal days than available |
| **Impact** | Medium - Policy violation, unfair time-off allocation |
| **Detection Signals** | ValueError with "Insufficient sick/personal time" message |
| **Current Remediation** | Hard limits enforced in `PTOService.create_request()` (`src/services/pto_service.py:95-111`): Sick and personal days validated against available balance. Same validation on approval (`src/services/pto_service.py:307-322`). Vacation allows over-request (manager discretion). |
| **Recovery Steps** | 1. Request blocked automatically 2. User informed of available balance |
| **Residual Risk** | Low - Server-side enforcement |
| **Recommended Improvement** | None |

### DATA-003: Duplicate/Overlapping PTO Requests

| Field | Details |
|-------|---------|
| **Scenario ID** | DATA-003 |
| **Description** | User submits multiple requests for same dates |
| **Impact** | Medium - Double balance deduction, confusion |
| **Detection Signals** | ValueError with overlap message; Audit logs show rejected submission |
| **Current Remediation** | `PTOService.create_request()` calls `get_overlapping_requests()` (`src/services/pto_service.py:71-83`) to check for existing pending/approved requests in date range. Clear error message tells user to cancel existing request first. |
| **Recovery Steps** | 1. Submission blocked 2. User directed to manage existing requests |
| **Residual Risk** | Low - Server-side duplicate prevention |
| **Recommended Improvement** | None |

### DATA-004: Orphaned Records After User Deletion

| Field | Details |
|-------|---------|
| **Scenario ID** | DATA-004 |
| **Description** | User deleted but PTO records remain, causing foreign key issues |
| **Impact** | Medium - Data integrity issues, query failures |
| **Detection Signals** | Database errors on queries joining user table |
| **Current Remediation** | `UserService.delete_user()` (`src/services/user_service.py:225-250`) explicitly deletes PTO requests and balances before deleting user. Soft delete via `deactivate_user()` recommended to preserve history. |
| **Recovery Steps** | 1. Not applicable - cascade delete handles cleanup |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## 3. Time and Date Logic

### TIME-001: Past Date PTO Submission

| Field | Details |
|-------|---------|
| **Scenario ID** | TIME-001 |
| **Description** | User attempts to submit PTO request for dates that have already passed |
| **Impact** | Low - Historical data manipulation, policy circumvention |
| **Detection Signals** | ValueError "Start date cannot be in the past" |
| **Current Remediation** | Backend validation in `PTOService.create_request()` (`src/services/pto_service.py:53-55`). Frontend date pickers constrained with Quasar `options` prop (`request_form.py`) to disable past dates. `src/utils/validators.py:28-40` provides `validate_date_not_past()`. |
| **Recovery Steps** | 1. Submission blocked automatically |
| **Residual Risk** | Low - Backend enforcement prevents bypass |
| **Recommended Improvement** | None |

### TIME-002: Far-Future Date Requests

| Field | Details |
|-------|---------|
| **Scenario ID** | TIME-002 |
| **Description** | User requests PTO years into the future (potentially accidental) |
| **Impact** | Low - Data confusion, balance allocation issues |
| **Detection Signals** | ValueError about exceeding future year limit |
| **Current Remediation** | `PTOService.create_request()` (`src/services/pto_service.py:64-69`) limits requests to 5 years in advance with clear error message. |
| **Recovery Steps** | 1. Submission blocked automatically |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### TIME-003: Timezone/DST Issues

| Field | Details |
|-------|---------|
| **Scenario ID** | TIME-003 |
| **Description** | Date calculations incorrect due to timezone or DST transitions |
| **Impact** | Low - Off-by-one day errors in requests |
| **Detection Signals** | User reports request shows wrong dates |
| **Current Remediation** | Application uses Python `date` objects (not datetime) for PTO dates, avoiding time-of-day issues. `datetime.now().date()` used for "today" comparisons. All dates stored as DATE type in database. |
| **Recovery Steps** | 1. Admin can edit request dates if needed |
| **Residual Risk** | Low - Date-only storage avoids most TZ issues |
| **Recommended Improvement** | **GAP**: No explicit timezone handling - consider pytz for multi-timezone deployments |

### TIME-004: Half-Day Request Calculation Errors

| Field | Details |
|-------|---------|
| **Scenario ID** | TIME-004 |
| **Description** | Half-day requests (0.5 days) calculated or displayed incorrectly |
| **Impact** | Low - Incorrect balance usage |
| **Detection Signals** | Balance discrepancies; "½" indicator missing on calendar |
| **Current Remediation** | `total_days` stored as `Decimal(4,2)` allowing 0.5 precision (`src/models/pto_request.py:46`). Calendar displays "½" indicator for half-days. `fmt_days()` helper formats display cleanly. |
| **Recovery Steps** | 1. Admin can adjust request if needed |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### TIME-005: Year Boundary PTO Requests

| Field | Details |
|-------|---------|
| **Scenario ID** | TIME-005 |
| **Description** | PTO request spans December 31 to January 1 (two different years) |
| **Impact** | Medium - Balance deduction from wrong year |
| **Detection Signals** | User reports incorrect balance deduction |
| **Current Remediation** | `PTOService.create_request()` uses `request_data.start_date.year` to determine which year's balance to use. Multi-year balance support with year-keyed records (`PTOBalance.year`). |
| **Recovery Steps** | 1. Admin adjusts balances manually if needed |
| **Residual Risk** | Medium - Cross-year requests may need manual review |
| **Recommended Improvement** | **GAP**: Consider splitting cross-year requests into two records |

---

## 4. PTO Policy Rules

### POLICY-001: Tenure Tier Miscalculation

| Field | Details |
|-------|---------|
| **Scenario ID** | POLICY-001 |
| **Description** | Employee vacation allocation doesn't match tenure level |
| **Impact** | Medium - Employee receives wrong vacation days |
| **Detection Signals** | Employee complaints; Balance audit shows discrepancy |
| **Current Remediation** | `YearEndService._calculate_vacation_allocation()` (`src/services/year_end_service.py:192-216`) calculates based on hire_date: <2 years: 10 days, 2-5 years: 12 days, 5-10 years: 15 days, 10+ years: 20 days. `AccrualService.get_vacation_tier()` (`src/services/accrual_service.py:75-88`) queries `VacationAccrualTier` table for policy-driven tiers. |
| **Recovery Steps** | 1. Admin edits employee balance via Admin > Employees |
| **Residual Risk** | Low - Calculation logic is clear and testable |
| **Recommended Improvement** | None |

### POLICY-002: Carryover Cap Exceeded

| Field | Details |
|-------|---------|
| **Scenario ID** | POLICY-002 |
| **Description** | Employee carries over more hours than policy allows |
| **Impact** | Medium - Policy violation, unfair accumulation |
| **Detection Signals** | Year-end processing logs show "capped" message |
| **Current Remediation** | `YearEndService.apply_approved_carryover()` (`src/services/year_end_service.py:296-305`) enforces cap: checks `policy.max_carryover_hours`, calculates available cap, reduces hours if exceeded, logs warning. |
| **Recovery Steps** | 1. Cap automatically enforced during year-end processing |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### POLICY-003: State-Specific Leave Policy Not Applied

| Field | Details |
|-------|---------|
| **Scenario ID** | POLICY-003 |
| **Description** | Employee in state with specific leave laws doesn't get correct policy |
| **Impact** | Medium - Legal compliance issue |
| **Detection Signals** | Employee reports policy mismatch; Compliance audit |
| **Current Remediation** | `AccrualService.get_policy_for_employee()` (`src/services/accrual_service.py:23-73`) implements policy resolution: 1. City-specific (Chicago, IL), 2. State-specific (IL), 3. Default. `User` model has `location_state` and `location_city` fields. `LeavePolicy` table supports state/city overrides. |
| **Recovery Steps** | 1. Update employee location in Admin > Employees 2. Verify policy records exist for location |
| **Residual Risk** | Medium - Requires proper policy data setup |
| **Recommended Improvement** | Add policy validation on employee save |

### POLICY-004: Market Holiday Alignment Issues

| Field | Details |
|-------|---------|
| **Scenario ID** | POLICY-004 |
| **Description** | PTO requests conflict with observed market holidays |
| **Impact** | Low - Employee uses PTO on holiday |
| **Detection Signals** | Calendar shows PTO on holiday |
| **Current Remediation** | `YearEndService.generate_federal_holidays()` (`src/services/year_end_service.py:326-366`) generates all federal holidays with observed dates. `_observed_date()` adjusts weekend holidays (Sat→Fri, Sun→Mon). Calendar page displays holidays alongside PTO. |
| **Recovery Steps** | 1. Employee can cancel request 2. Manager can advise |
| **Residual Risk** | Low - Visual calendar helps avoid |
| **Recommended Improvement** | **GAP**: Consider warning when PTO overlaps holiday |

---

## 5. Concurrency and Race Conditions

### CONC-001: Simultaneous PTO Submissions

| Field | Details |
|-------|---------|
| **Scenario ID** | CONC-001 |
| **Description** | Two users submit requests at exact same time, causing balance race |
| **Impact** | Medium - Incorrect balance calculations |
| **Detection Signals** | Balance audit shows incorrect totals |
| **Current Remediation** | SQLAlchemy transactions with `autocommit=False` (`src/database.py:35-40`). Database-level `UNIQUE` constraint on (user_id, year) for balances (`src/models/pto_balance.py:115-117`). Sequential balance updates within transaction. |
| **Recovery Steps** | 1. One request will fail on constraint violation 2. User retries |
| **Residual Risk** | Medium - SQLite has limited concurrent write support |
| **Recommended Improvement** | **GAP**: Add optimistic locking (version column) for high-concurrency scenarios |

### CONC-002: Double Approval Click

| Field | Details |
|-------|---------|
| **Scenario ID** | CONC-002 |
| **Description** | Manager clicks Approve button twice quickly |
| **Impact** | Medium - Double balance deduction |
| **Detection Signals** | Audit shows duplicate approvals; Balance incorrect |
| **Current Remediation** | `PTOService.approve_request()` (`src/services/pto_service.py:297-298`) checks `request.status != 'pending'` and raises ValueError if already processed. UI shows loading state on button click. |
| **Recovery Steps** | 1. Second click rejected with error |
| **Residual Risk** | Low - Status check prevents double processing |
| **Recommended Improvement** | None |

### CONC-003: Concurrent Balance Modifications

| Field | Details |
|-------|---------|
| **Scenario ID** | CONC-003 |
| **Description** | Admin edits balance while employee submits request |
| **Impact** | Medium - Lost update, incorrect final balance |
| **Detection Signals** | Balance doesn't match expected value |
| **Current Remediation** | SQLAlchemy ORM tracks dirty state; commits are atomic. `updated_at` timestamp on balance records for audit trail. |
| **Recovery Steps** | 1. Admin reviews audit logs 2. Manually corrects balance |
| **Residual Risk** | Medium |
| **Recommended Improvement** | **GAP**: Add row-level locking or optimistic concurrency |

---

## 6. API and Backend Failures

### API-001: Database Connection Failure

| Field | Details |
|-------|---------|
| **Scenario ID** | API-001 |
| **Description** | Application cannot connect to SQLite database |
| **Impact** | Critical - Complete application failure |
| **Detection Signals** | Health check fails (`/health` endpoint); Error logs; UI shows generic error |
| **Current Remediation** | Health check endpoint (`nicegui_app/main.py:301-328`) tests database with `SELECT 1`. Logging captures connection errors (`src/logging_config.py`). `try/finally` blocks ensure session cleanup. |
| **Recovery Steps** | 1. Check database file exists 2. Check file permissions 3. Restart application |
| **Residual Risk** | Medium |
| **Recommended Improvement** | Add automated health check monitoring |

### API-002: Service Layer Exception

| Field | Details |
|-------|---------|
| **Scenario ID** | API-002 |
| **Description** | Unhandled exception in service layer crashes request |
| **Impact** | Medium - Single request fails, user sees error |
| **Detection Signals** | Error log entry; `tjm_calendar_errors.log` file |
| **Current Remediation** | UI code wraps service calls in try/except (e.g., `login.py:131-135`). Rotating error log file (`src/logging_config.py:47-55`) captures errors separately. NiceGUI handles uncaught exceptions gracefully. |
| **Recovery Steps** | 1. User retries action 2. Admin reviews error logs |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### API-003: Year-End Processing Failure

| Field | Details |
|-------|---------|
| **Scenario ID** | API-003 |
| **Description** | Automatic year-end processing fails mid-execution |
| **Impact** | High - Employees don't get new year balances |
| **Detection Signals** | `YearEndStatus.processed = False`; Error in `results['errors']` array |
| **Current Remediation** | `YearEndService.process_year_transition()` (`src/services/year_end_service.py:92-131`) wraps each step in try/except, collects errors, continues processing. Idempotent: checks existing records before creating. `YearEndStatus` table tracks completion. |
| **Recovery Steps** | 1. Admin triggers manual reprocessing via Admin > Year-End 2. Review error logs 3. Fix data issues and retry |
| **Residual Risk** | Low - Idempotent design allows safe retry |
| **Recommended Improvement** | None |

---

## 7. Database Concerns

### DB-001: Database File Corruption

| Field | Details |
|-------|---------|
| **Scenario ID** | DB-001 |
| **Description** | SQLite database file becomes corrupted |
| **Impact** | Critical - Data loss, application unusable |
| **Detection Signals** | SQLite "database disk image is malformed" error |
| **Current Remediation** | `BackupService` (`src/services/backup_service.py`) provides: `create_backup()` with timestamped copies, `list_backups()` to view available backups, `restore_backup()` with safety backup before restore, Automatic cleanup keeping last 7 backups. |
| **Recovery Steps** | 1. Stop application 2. Use `BackupService.restore_backup()` to restore from most recent backup 3. Restart application |
| **Residual Risk** | Medium - Manual backup scheduling required |
| **Recommended Improvement** | **GAP**: Add automated scheduled backups |

### DB-002: Migration Failure

| Field | Details |
|-------|---------|
| **Scenario ID** | DB-002 |
| **Description** | Alembic migration fails, leaving database in inconsistent state |
| **Impact** | High - Application may not start |
| **Detection Signals** | Alembic error output; Application startup failure |
| **Current Remediation** | Alembic version control (`alembic/versions/`) tracks all migrations. `alembic downgrade` available for rollback. `init_db()` (`src/database.py:63-72`) creates missing tables on startup. |
| **Recovery Steps** | 1. `alembic downgrade -1` to roll back 2. Fix migration script 3. Re-run `alembic upgrade head` |
| **Residual Risk** | Medium |
| **Recommended Improvement** | Create pre-migration backup script |

### DB-003: Query Performance Degradation

| Field | Details |
|-------|---------|
| **Scenario ID** | DB-003 |
| **Description** | Slow queries as data volume grows |
| **Impact** | Medium - Poor user experience |
| **Detection Signals** | Slow page loads; SQLAlchemy query timing in debug logs |
| **Current Remediation** | Composite indexes defined (`src/models/pto_request.py:94-97`): `ix_pto_requests_user_status`, `ix_pto_requests_status_dates`. Performance indexes migration (`alembic/versions/ddb4525455a7_add_performance_indexes.py`). N+1 query prevention in `YearEndService` with bulk pre-fetching. |
| **Recovery Steps** | 1. Add indexes as needed 2. Optimize queries |
| **Residual Risk** | Low for current scale |
| **Recommended Improvement** | None |

### DB-004: Foreign Key Violations

| Field | Details |
|-------|---------|
| **Scenario ID** | DB-004 |
| **Description** | Orphaned records created due to FK not enforced |
| **Impact** | Medium - Data integrity issues |
| **Detection Signals** | Queries return null for expected relationships |
| **Current Remediation** | SQLite FK enforcement enabled via PRAGMA (`src/database.py:27-32`): `PRAGMA foreign_keys=ON` on every connection. FK constraints defined on all relationship columns. |
| **Recovery Steps** | 1. FK violations prevented at insert time |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## 8. Frontend Input Errors and UX Failure Modes

### UX-001: Stale Session Data

| Field | Details |
|-------|---------|
| **Scenario ID** | UX-001 |
| **Description** | User sees outdated data after another user makes changes |
| **Impact** | Low - User confusion, potential conflicts |
| **Detection Signals** | User reports data mismatch |
| **Current Remediation** | NiceGUI reactive UI updates on page navigation. Refresh buttons on key pages. Data fetched fresh on each page load. |
| **Recovery Steps** | 1. User refreshes page |
| **Residual Risk** | Low |
| **Recommended Improvement** | **GAP**: Add real-time updates via WebSocket for multi-user scenarios |

### UX-002: Form Submission Timeout

| Field | Details |
|-------|---------|
| **Scenario ID** | UX-002 |
| **Description** | User submits form but connection drops before completion |
| **Impact** | Medium - Uncertain submission state |
| **Detection Signals** | User unsure if action completed; Potential duplicate attempts |
| **Current Remediation** | Loading states on buttons (e.g., `login.py:77`). Database transactions atomic - either complete or rolled back. Duplicate prevention via overlapping request check. |
| **Recovery Steps** | 1. User checks request list to verify submission 2. Retries if not present |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### UX-003: Invalid Input Not Caught by Frontend

| Field | Details |
|-------|---------|
| **Scenario ID** | UX-003 |
| **Description** | Malformed input bypasses frontend validation |
| **Impact** | Low - Backend catches it, but poor UX |
| **Detection Signals** | Server error message shown to user |
| **Current Remediation** | `validate_required()` and other helpers in `nicegui_app/components/theme.py`. Quasar input validation props. Backend validation as safety net (`src/utils/validators.py`). |
| **Recovery Steps** | 1. User corrects input based on error message |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## 9. Notifications and Integrations

### NOTIF-001: Email Delivery Failure

| Field | Details |
|-------|---------|
| **Scenario ID** | NOTIF-001 |
| **Description** | PTO notification emails fail to send |
| **Impact** | Low - User not notified but action still completes |
| **Detection Signals** | `Failed to send email` in logs; User reports missing notification |
| **Current Remediation** | `EmailService._send_email()` (`src/services/email_service.py:38-71`) wraps SMTP in try/except, logs errors, returns False on failure. Email failures do not block PTO operations. `is_configured()` check prevents attempts when not configured. |
| **Recovery Steps** | 1. Check SMTP configuration in `.env` 2. Verify credentials 3. Check spam folder |
| **Residual Risk** | Low - Email is supplementary, not critical |
| **Recommended Improvement** | **GAP**: Add email queue with retry mechanism |

### NOTIF-002: Duplicate Email Sends

| Field | Details |
|-------|---------|
| **Scenario ID** | NOTIF-002 |
| **Description** | Same notification email sent multiple times |
| **Impact** | Low - User annoyance |
| **Detection Signals** | User reports duplicate emails |
| **Current Remediation** | Email sending tied to single service call per action. No automatic retry mechanism (prevents duplicates). |
| **Recovery Steps** | 1. Review code for duplicate calls 2. Fix if found |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### NOTIF-003: SMTP Credentials Exposed

| Field | Details |
|-------|---------|
| **Scenario ID** | NOTIF-003 |
| **Description** | SMTP password leaked in logs or error messages |
| **Impact** | Medium - Email account compromise |
| **Detection Signals** | Password visible in logs |
| **Current Remediation** | SMTP credentials loaded from environment variables (`src/services/email_service.py:20-23`). Error logging captures exception message, not credentials. `.env` file excluded from git (via `.gitignore`). |
| **Recovery Steps** | 1. Rotate SMTP password 2. Review log files for exposure |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## 10. Security

### SEC-001: SQL Injection

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-001 |
| **Description** | Attacker injects SQL via user input |
| **Impact** | Critical - Data breach, data manipulation |
| **Detection Signals** | Unusual database errors; Data anomalies |
| **Current Remediation** | SQLAlchemy ORM used exclusively - parameterized queries by default. No raw SQL string concatenation. `select()` statements use proper where clauses with bound parameters. |
| **Recovery Steps** | 1. Not applicable - ORM prevents injection |
| **Residual Risk** | Very Low |
| **Recommended Improvement** | None |

### SEC-002: Cross-Site Scripting (XSS)

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-002 |
| **Description** | Attacker injects malicious script via user input fields |
| **Impact** | High - Session hijacking, data theft |
| **Detection Signals** | Unexpected JavaScript execution; User reports strange behavior |
| **Current Remediation** | NiceGUI/Vue.js auto-escapes output by default. User input displayed via `ui.label()` which escapes HTML. No `v-html` or `dangerouslySetInnerHTML` usage. |
| **Recovery Steps** | 1. Remove malicious content from database 2. Review input sanitization |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### SEC-003: Weak Password Storage

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-003 |
| **Description** | Passwords stored insecurely, vulnerable to breach |
| **Impact** | Critical - Mass account compromise |
| **Detection Signals** | Security audit; Breach notification |
| **Current Remediation** | `PasswordHasher` (`src/utils/password.py`) uses bcrypt with 12 rounds (line 10). Salt generated per password (`bcrypt.gensalt()`). `verify_password()` uses constant-time comparison via bcrypt. |
| **Recovery Steps** | 1. Not applicable - bcrypt is industry standard |
| **Residual Risk** | Very Low |
| **Recommended Improvement** | None |

### SEC-004: Insecure Direct Object Reference (IDOR)

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-004 |
| **Description** | User manipulates request_id to access others' data |
| **Impact** | High - Unauthorized data access |
| **Detection Signals** | Access denied messages; Audit logs of cross-department access |
| **Current Remediation** | Manager approval scoped to department (`manager_request_detail.py:34-38`). `cancel_request()` (`src/services/pto_service.py:402-403`) validates user owns request. Role checks on admin functions. |
| **Recovery Steps** | 1. Access blocked automatically 2. Review audit logs |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### SEC-005: Missing HTTPS

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-005 |
| **Description** | Application served over HTTP, credentials transmitted in plaintext |
| **Impact** | High - Credential interception |
| **Detection Signals** | Browser security warnings; Network traffic analysis |
| **Current Remediation** | SSL support implemented (`src/config.py:28-29`, `nicegui_app/main.py:342-345`). `TJM_SSL_CERT` and `TJM_SSL_KEY` env vars configure certificates. `.env.example` documents SSL setup (lines 71-78). |
| **Recovery Steps** | 1. Generate SSL certificate 2. Configure env vars 3. Restart application |
| **Residual Risk** | Medium - SSL optional, not enforced |
| **Recommended Improvement** | **GAP**: Add HTTP-to-HTTPS redirect in production |

### SEC-006: Dependency Vulnerabilities

| Field | Details |
|-------|---------|
| **Scenario ID** | SEC-006 |
| **Description** | Third-party packages contain known vulnerabilities |
| **Impact** | Variable - Depends on vulnerability |
| **Detection Signals** | `pip audit` findings; Security advisories |
| **Current Remediation** | `requirements.txt` specifies minimum versions. Key dependencies pinned (SQLAlchemy==2.0.23, bcrypt==4.1.1). |
| **Recovery Steps** | 1. Run `pip audit` 2. Update affected packages 3. Test and deploy |
| **Residual Risk** | Medium |
| **Recommended Improvement** | **GAP**: Add automated dependency scanning (Dependabot, pip-audit CI) |

---

## 11. Observability

### OBS-001: Application Errors Not Logged

| Field | Details |
|-------|---------|
| **Scenario ID** | OBS-001 |
| **Description** | Errors occur but not captured for debugging |
| **Impact** | Medium - Difficult troubleshooting |
| **Detection Signals** | Unexplained user complaints; Missing log entries |
| **Current Remediation** | Comprehensive logging setup (`src/logging_config.py`): Main log (`logs/tjm_calendar.log`) with rotation (5MB, 5 backups). Separate error log (`logs/tjm_calendar_errors.log`). Console output in development. Log level configurable via `LOG_LEVEL` env var. |
| **Recovery Steps** | 1. Review log files 2. Increase log level if needed |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### OBS-002: No Performance Metrics

| Field | Details |
|-------|---------|
| **Scenario ID** | OBS-002 |
| **Description** | Cannot identify slow endpoints or performance issues |
| **Impact** | Medium - Reactive vs proactive performance management |
| **Detection Signals** | User complaints about slowness |
| **Current Remediation** | **GAP**: No metrics collection implemented. Health check endpoint (`/health`) provides basic status. |
| **Recovery Steps** | 1. Add logging for slow operations 2. Profile application |
| **Residual Risk** | Medium |
| **Recommended Improvement** | **GAP**: Add request timing metrics, consider Prometheus integration |

### OBS-003: No Alerting

| Field | Details |
|-------|---------|
| **Scenario ID** | OBS-003 |
| **Description** | Critical failures not escalated to operations team |
| **Impact** | High - Delayed incident response |
| **Detection Signals** | Extended downtime before awareness |
| **Current Remediation** | **GAP**: No alerting implemented. Error logs must be manually monitored. |
| **Recovery Steps** | 1. Manual log review 2. Set up external monitoring |
| **Residual Risk** | High |
| **Recommended Improvement** | **GAP**: Add error alerting (email, Slack, PagerDuty) |

---

## 12. Deployment and Environment Drift

### DEPLOY-001: Dev/Prod Configuration Mismatch

| Field | Details |
|-------|---------|
| **Scenario ID** | DEPLOY-001 |
| **Description** | Production uses different settings than tested in development |
| **Impact** | Variable - Unexpected behavior, security issues |
| **Detection Signals** | Behavior differs between environments |
| **Current Remediation** | `ENVIRONMENT` env var controls mode (`src/config.py:22`). `is_production` property for conditional logic. `.env.example` documents all config options with production checklist (lines 81-89). `DEBUG` flag separate from environment. |
| **Recovery Steps** | 1. Compare `.env` files 2. Align configurations |
| **Residual Risk** | Medium |
| **Recommended Improvement** | Add environment validation on startup |

### DEPLOY-002: Secret Key Not Rotated

| Field | Details |
|-------|---------|
| **Scenario ID** | DEPLOY-002 |
| **Description** | Same SECRET_KEY used since initial deployment |
| **Impact** | Low - Sessions remain valid indefinitely |
| **Detection Signals** | Security audit |
| **Current Remediation** | SECRET_KEY required on startup (`src/config.py:58-59`). `.env.example` provides generation command (line 21). |
| **Recovery Steps** | 1. Generate new SECRET_KEY 2. Update `.env` 3. Restart (invalidates all sessions) |
| **Residual Risk** | Low |
| **Recommended Improvement** | Document rotation schedule |

### DEPLOY-003: Debug Mode in Production

| Field | Details |
|-------|---------|
| **Scenario ID** | DEPLOY-003 |
| **Description** | DEBUG=True accidentally left on in production |
| **Impact** | Medium - Verbose errors, potential info leak |
| **Detection Signals** | Detailed error traces visible to users |
| **Current Remediation** | `DEBUG` defaults to False (`src/config.py:25`). Console log level tied to environment (`src/logging_config.py:31`). Production checklist in `.env.example`. |
| **Recovery Steps** | 1. Set `DEBUG=False` 2. Restart application |
| **Residual Risk** | Low |
| **Recommended Improvement** | Add startup warning if DEBUG=True and ENVIRONMENT=production |

---

## 13. Disaster Recovery and Business Continuity

### DR-001: Complete Data Loss

| Field | Details |
|-------|---------|
| **Scenario ID** | DR-001 |
| **Description** | Database file deleted or corrupted beyond repair |
| **Impact** | Critical - All PTO data lost |
| **Detection Signals** | Application fails to start; Database file missing |
| **Current Remediation** | `BackupService` (`src/services/backup_service.py`) provides backup/restore. Backup directory: `PROJECT_ROOT/dbbackup`. Automatic cleanup retains last 7 backups. Pre-restore safety backup created automatically. |
| **Recovery Steps** | 1. Stop application 2. `BackupService.list_backups()` to find available backups 3. `BackupService.restore_backup(filename)` to restore 4. Restart application |
| **Residual Risk** | Medium - Requires manual backup scheduling |
| **Recommended Improvement** | **GAP**: Add automated daily backup schedule |

### DR-002: Server Hardware Failure

| Field | Details |
|-------|---------|
| **Scenario ID** | DR-002 |
| **Description** | Physical server fails, application inaccessible |
| **Impact** | Critical - Complete service outage |
| **Detection Signals** | Application unreachable |
| **Current Remediation** | **GAP**: No redundancy built-in. Single-server SQLite deployment. Backups stored locally. |
| **Recovery Steps** | 1. Provision new server 2. Install application 3. Restore from backup 4. Update DNS/routing |
| **Residual Risk** | High |
| **Recommended Improvement** | **GAP**: Document recovery procedure, consider off-site backup storage |

### DR-003: Application Code Corruption

| Field | Details |
|-------|---------|
| **Scenario ID** | DR-003 |
| **Description** | Deployment corrupts application files |
| **Impact** | High - Application won't start |
| **Detection Signals** | Import errors; Syntax errors |
| **Current Remediation** | Git version control tracks all code changes. Can checkout previous commit. |
| **Recovery Steps** | 1. `git status` to check state 2. `git checkout <previous-commit>` to restore 3. Restart application |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## 14. Compliance and Auditability

### AUDIT-001: Cannot Determine Who Changed What

| Field | Details |
|-------|---------|
| **Scenario ID** | AUDIT-001 |
| **Description** | Compliance audit requires tracking of all PTO changes |
| **Impact** | Medium - Compliance violation |
| **Detection Signals** | Auditor request; Unable to answer "who approved this?" |
| **Current Remediation** | `AuditLog` model (`src/models/audit_log.py`) captures: `user_id`, `username`, `action`, `entity_type`, `entity_id`, `details` (JSON), `ip_address`, `created_at`. `AuditService` (`src/services/audit_service.py`) provides typed logging methods: `log_login()`, `log_pto_request()`, `log_pto_approve()`, `log_pto_deny()`, `log_user_create()`, `log_user_update()`, `log_user_deactivate()`. |
| **Recovery Steps** | 1. Query audit_logs table 2. Use `AuditService.get_logs_by_user()` or `get_logs_by_action()` |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

### AUDIT-002: Audit Logs Modified/Deleted

| Field | Details |
|-------|---------|
| **Scenario ID** | AUDIT-002 |
| **Description** | Admin modifies audit logs to hide activity |
| **Impact** | High - Compliance violation, fraud |
| **Detection Signals** | Audit log gaps; Sequence ID jumps |
| **Current Remediation** | **GAP**: No write protection on audit_logs table. Database is single-file SQLite. |
| **Recovery Steps** | 1. Compare with backups 2. Review database access logs (if available) |
| **Residual Risk** | Medium |
| **Recommended Improvement** | **GAP**: Add audit log integrity checks (checksums, external archival) |

### AUDIT-003: PTO Approval Without Proper Authority

| Field | Details |
|-------|---------|
| **Scenario ID** | AUDIT-003 |
| **Description** | Request approved by someone without authority |
| **Impact** | Medium - Policy violation |
| **Detection Signals** | Audit log shows unusual approver |
| **Current Remediation** | Role enforcement on approval pages. Manager scoped to department. `approved_by` field on PTORequest records approver ID. Audit log captures approver details. |
| **Recovery Steps** | 1. Review audit logs 2. Investigate unauthorized approval 3. Take corrective action |
| **Residual Risk** | Low |
| **Recommended Improvement** | None |

---

## Gap Register

Summary of scenarios and their remediation status:

### Completed Remediations (December 12, 2025)

| ID | Gap Description | Status | Implementation |
|----|-----------------|--------|----------------|
| DB-001a / DR-001a | No automated backup schedule | ✅ RESOLVED | `scripts/scheduled_backup.bat` + `task/BACKUP_SETUP.md` with Task Scheduler instructions |
| SEC-005a | No HTTP-to-HTTPS redirect | ✅ RESOLVED | `nicegui_app/main.py:52-56` - HTTPSRedirectMiddleware in production |
| SEC-006a | No automated dependency scanning | ✅ RESOLVED | `task/DEPENDENCY_AUDIT.md` created with audit findings and update plan |
| OBS-003a | No alerting system | ✅ RESOLVED | `src/services/alert_service.py` - Email alerts with rate limiting |
| DR-002a | No off-site backup storage | ✅ RESOLVED | `src/services/backup_service.py:236-314` - sync_to_offsite() method |
| POLICY-004a | No warning for PTO on holidays | ✅ RESOLVED | `nicegui_app/pages/request_form.py:459-478` - Holiday overlap warning |
| TIME-005a | Cross-year requests not split | ✅ RESOLVED | `nicegui_app/pages/request_form.py:450-457` - Warning with guidance to split |

### Remaining Gaps (Lower Priority)

| ID | Gap Description | Severity | Proposed Fix | Suggested Owner |
|----|-----------------|----------|--------------|-----------------|
| AUTH-001a | Rate limiter resets on app restart | Low | Persist lockout state to database | Backend |
| TIME-003a | No explicit timezone handling | Low | Add pytz for TZ-aware datetime | Backend |
| CONC-001a | No optimistic locking on balances | Medium | Add version column for concurrent updates | Backend |
| UX-001a | No real-time UI updates | Low | Add WebSocket push for multi-user visibility | Frontend |
| NOTIF-001a | No email retry mechanism | Low | Add email queue with retry logic | Backend |
| OBS-002a | No performance metrics | Medium | Add request timing, Prometheus metrics | Backend |
| AUDIT-002a | Audit logs not write-protected | Medium | Add checksums or external archival | Backend |

---

## Running Tests

```bash
# Environment test
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe -m pytest tests/test_environment.py -v

# Syntax check all files
venv\Scripts\python.exe -m py_compile src/services/pto_service.py
venv\Scripts\python.exe -m py_compile nicegui_app/main.py
```

---

## Environment Variables Reference

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `DATABASE_URL` | Database connection string | - | Yes |
| `SECRET_KEY` | Session encryption key | - | Yes |
| `ENVIRONMENT` | Environment mode | development | No |
| `DEBUG` | Debug mode flag | False | No |
| `LOG_LEVEL` | Logging verbosity | INFO | No |
| `TJM_HOST` | Server bind address | 0.0.0.0 | No |
| `TJM_PORT` | Server port | 8080 | No |
| `TJM_SSL_CERT` | SSL certificate path | - | No |
| `TJM_SSL_KEY` | SSL key path | - | No |
| `EMAIL_ENABLED` | Enable email notifications | false | No |
| `SMTP_HOST` | SMTP server hostname | - | No |
| `SMTP_PORT` | SMTP server port | 587 | No |
| `SMTP_USER` | SMTP username | - | No |
| `SMTP_PASSWORD` | SMTP password | - | No |
| `EMAIL_FROM` | From email address | noreply@tjm.com | No |
| `ANTHROPIC_API_KEY` | AI assistant API key | - | No |
| `ALERT_ENABLED` | Enable error alerting | false | No |
| `ALERT_EMAIL` | Email for alerts | - | No |
| `OFFSITE_BACKUP_PATH` | Off-site backup location | - | No |

---

*Document generated by Claude Code analysis of TJM Time Calendar codebase.*
*Last updated: December 12, 2025*
