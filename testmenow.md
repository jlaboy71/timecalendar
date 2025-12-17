# TJM Time Calendar - Comprehensive Codebase Reference

## 1. PROJECT OVERVIEW

**TJM Time Calendar** is an employee PTO (Paid Time Off) and Market Calendar management system for TJM Holdings / Haventech Solutions. The system provides comprehensive time-off tracking with multi-state policy support, manager approval workflows, trusted employee auto-approval, and complete audit trails.

**Key Characteristics:**
- Front-loaded annual PTO allocation (full balance on January 1st)
- Multi-state and city-specific leave policies
- Tenure-based vacation tiers
- Auto-approval system for trusted employees
- Complete audit logging for compliance
- Interactive team calendars with NYSE/CME/CBOE market holidays
- Role-based access control (Employee, Manager, Admin, SuperAdmin)
- Year-end automatic processing with carryover management

---

## 2. DIRECTORY STRUCTURE

```
TimeCalendar/
├── nicegui_app/                    # NiceGUI UI layer
│   ├── main.py                     # Application entry point
│   ├── logo.py                     # TJM logo as base64 data URL
│   ├── pages/                      # Page components (23 pages)
│   │   ├── dashboard.py           # Employee dashboard with PTO summary
│   │   ├── calendar.py            # Team calendar with market holidays
│   │   ├── request_form.py        # PTO request submission
│   │   ├── requests.py            # Employee view all requests
│   │   ├── carryover.py           # Employee carryover requests
│   │   ├── analytics.py           # Report dashboards
│   │   ├── reports.py             # PTO reports (PDF/CSV/HTML export)
│   │   ├── help.py                # Help and documentation
│   │   ├── handbook.py            # Company handbook viewer
│   │   ├── manager_team.py        # Manager team view
│   │   ├── manager_carryover.py   # Manager carryover approvals
│   │   ├── manager_request_detail.py # Request details & approval
│   │   ├── manager_settings.py    # Manager notification preferences
│   │   ├── admin_dashboard.py     # Admin overview
│   │   ├── admin_employees.py     # Employee management CRUD
│   │   ├── admin_departments.py   # Department management
│   │   ├── admin_approvals.py     # Approval management
│   │   ├── admin_handbook.py      # Handbook management & upload
│   │   ├── admin_system.py        # System settings, policies, users
│   │   ├── admin_year_end.py      # Year-end processing
│   │   ├── admin_email_preview.py # Email template previews
│   │   ├── admin_auto_notify_reports.py # Notification dashboard
│   │   ├── login.py               # Authentication
│   │   ├── password_reset.py      # Password recovery
│   │   └── analytics.py           # Analytics dashboards
│   ├── components/                 # Reusable UI components
│   │   ├── header.py              # Page headers with greeting
│   │   ├── theme.py               # Dark mode, skeleton loaders, dialogs
│   │   ├── formatting.py          # Display formatting helpers
│   │   ├── policy_change_indicator.py # "What's New" section
│   │   ├── charts.py              # Chart components
│   │   └── __init__.py
│   ├── static/                     # Static assets
│   │   └── handbook_content.py     # Handbook data
│   └── __init__.py
├── src/                            # Backend services
│   ├── config.py                   # Environment config loader
│   ├── database.py                 # SQLAlchemy setup
│   ├── constants.py                # App constants
│   ├── logging_config.py           # Logging configuration
│   ├── models/                     # SQLAlchemy ORM models (19 models)
│   │   ├── user.py                # User accounts with roles
│   │   ├── pto_request.py         # PTO requests
│   │   ├── pto_balance.py         # Annual balances per user/year
│   │   ├── department.py          # Organization departments
│   │   ├── carryover_request.py   # Carryover approval workflow
│   │   ├── leave_type.py          # Leave categories (vacation, sick, etc)
│   │   ├── leave_policy.py        # State/city-specific policies
│   │   ├── market_holiday.py      # Market holidays (NYSE, CME, CBOE)
│   │   ├── audit_log.py           # Action audit trail
│   │   ├── system_setting.py      # Feature toggles
│   │   ├── year_end_status.py     # Year-end processing tracking
│   │   ├── vacation_accrual_tier.py # Tenure-based vacation tiers
│   │   ├── handbook_upload.py     # Handbook file uploads
│   │   ├── handbook_revision.py   # Handbook version tracking
│   │   ├── password_reset.py      # Password reset tokens
│   │   ├── pending_notification.py # Queued email notifications
│   │   ├── policy_change_log.py   # Policy change history
│   │   ├── manager_notification_preference.py # Manager alert preferences
│   │   └── __init__.py
│   ├── services/                   # Business logic services (27 services)
│   │   ├── pto_service.py         # PTO request operations
│   │   ├── balance_service.py     # Balance CRUD operations
│   │   ├── year_end_service.py    # Annual processing automation
│   │   ├── user_service.py        # User management
│   │   ├── accrual_service.py     # Accrual calculations
│   │   ├── email_service.py       # Email notifications (dark-themed templates)
│   │   ├── audit_service.py       # Audit logging
│   │   ├── export_service.py      # iCal and report export
│   │   ├── report_service.py      # PDF/CSV/HTML report generation
│   │   ├── analytics_service.py   # Business analytics
│   │   ├── market_calendar_service.py # Market holidays & calendars
│   │   ├── notification_service.py # Notification management
│   │   ├── policy_change_service.py # Policy history tracking
│   │   ├── department_service.py  # Department operations
│   │   ├── handbook_service.py    # Handbook operations
│   │   ├── handbook_revision_service.py # Handbook versioning
│   │   ├── handbook_analysis_service.py # Handbook AI analysis
│   │   ├── password_reset_service.py # Password reset flow
│   │   ├── session_manager.py     # Session & auth management
│   │   ├── rate_limiter.py        # Login rate limiting
│   │   ├── ical_export_service.py # iCal calendar export
│   │   ├── monitoring_service.py  # System monitoring & alerts
│   │   ├── backup_service.py      # Database backup
│   │   ├── report_storage_service.py # Report file management
│   │   ├── help_service.py        # Help content
│   │   ├── alert_service.py       # Alert notifications
│   │   └── __init__.py
│   ├── schemas/                    # Pydantic validation schemas
│   │   ├── pto_schemas.py         # PTO request/balance schemas
│   │   ├── user_schemas.py        # User schemas
│   │   └── __init__.py
│   ├── middleware/                 # HTTP middleware
│   │   ├── security.py            # Security headers
│   │   ├── rate_limit.py          # Rate limiting
│   │   └── __init__.py
│   ├── utils/                      # Utility functions
│   │   ├── validators.py          # Input validation functions
│   │   ├── password.py            # Password hashing
│   │   └── __init__.py
│   ├── auth/                       # Authentication modules
│   │   └── __init__.py
│   └── __init__.py
├── alembic/                        # Database migrations
│   ├── env.py                      # Alembic configuration
│   ├── versions/                   # Migration scripts
│   └── alembic.ini
├── tests/                          # Test suite
│   └── test_*.py                   # Unit tests
├── data/                           # Help content files
│   └── help/                       # Markdown help articles
├── .claude/                        # Development documentation
│   ├── rules/
│   │   ├── business-rules.md       # Business logic rules
│   │   ├── code-style.md           # Python/NiceGUI conventions
│   │   ├── database.md             # Schema documentation
│   │   ├── ui-patterns.md          # UI component patterns
│   │   └── testing.md              # Testing guidelines
│   └── CLAUDE.md                   # Project overview
├── certs/                          # SSL certificates
├── handbook/                       # Company handbook PDFs
├── images/                         # Application images
├── scripts/                        # Utility scripts
├── task/                           # Task/feature documentation
├── pyproject.toml                  # Project configuration (Python 3.11+)
├── requirements.txt                # Python dependencies
├── README.md                       # Main documentation
├── DEPLOYMENT.md                   # Deployment guide
├── CLAUDE.md                       # Development instructions
└── tjm_calendar.db                 # SQLite database
```

---

## 3. KEY MODELS (SQLAlchemy ORM)

### **User** (`src/models/user.py`)
Represents employees with authentication and role-based access.

**Fields:**
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email
- `password_hash` - Bcrypt hash
- `first_name`, `last_name` - Personal info
- `hire_date`, `anniversary_date` - Employment dates
- `role` - Enum: 'employee', 'manager', 'admin', 'superadmin'
- `department_id` - FK to Department
- `location_state`, `location_city` - For policy lookup (e.g., "IL", "Chicago")
- `is_active` - Soft delete flag
- `is_trusted` - Auto-approval flag for standard PTO types
- `trusted_by_id`, `trusted_at` - Trust grant tracking
- `remote_schedule` - JSON: weekly remote days
- `created_at`, `updated_at` - Timestamps

**Relationships:**
- `department` - Back to Department
- `pto_requests` - List of requests submitted by user
- `approved_requests` - List of requests approved by user
- `pto_balances` - Annual balances

### **PTORequest** (`src/models/pto_request.py`)
Individual PTO request submissions with approval workflow.

**Fields:**
- `id` - Primary key
- `user_id` - FK to User (requester)
- `pto_type` - String: 'vacation', 'sick', 'personal', 'bereavement', 'fmla', 'jury_duty', 'voting', 'military'
- `start_date`, `end_date` - Request date range
- `total_days` - Decimal: calculated duration
- `status` - Enum: 'pending', 'approved', 'denied', 'cancelled'
- `is_paid` - Boolean (default True)
- `is_private` - Boolean: hide from team calendar
- `notes`, `denial_reason` - Text fields
- `approved_by` - FK to User (approver)
- `approved_at` - Timestamp when approved
- `cancellation_requested` - Employee-initiated cancellation
- `cancellation_reason`, `cancellation_requested_at` - Cancellation tracking
- `submitted_at`, `created_at`, `updated_at` - Timestamps

**Indexes:**
- Composite: (user_id, status)
- Composite: (status, start_date, end_date)

**Properties:**
- `duration_days` - Calendar days count
- `is_pending`, `is_approved`, `is_denied` - Status checks

### **PTOBalance** (`src/models/pto_balance.py`)
Annual PTO balance tracking per user/year with carryover support.

**Fields:**
- `id` - Primary key
- `user_id` - FK to User
- `year` - Year of balance
- Vacation: `vacation_total`, `vacation_used`, `vacation_pending`, `vacation_carryover`
- Sick: `sick_total`, `sick_used`, `sick_pending`, `sick_carryover`
- Personal: `personal_total`, `personal_used`, `personal_pending`, `personal_carryover`
- Chicago Safe Leave: `chicago_safe_leave_total`, `chicago_safe_leave_used`, `chicago_safe_leave_pending`, `chicago_safe_leave_carryover`
- Chicago Paid Leave: `chicago_paid_leave_total`, `chicago_paid_leave_used`, `chicago_paid_leave_pending`, `chicago_paid_leave_carryover`
- `remote_weekly_used` - Remote work tracking
- `created_at`, `updated_at` - Timestamps

**Constraints:**
- Unique: (user_id, year)

**Calculated Properties:**
- `vacation_available` = total + carryover - used - pending
- `sick_available` = total + carryover - used - pending
- `personal_available` = total + carryover - used - pending
- `chicago_safe_leave_available`
- `chicago_paid_leave_available`

### **Department** (`src/models/department.py`)
Organizational departments.

**Fields:**
- `id` - Primary key
- `name` - Unique name
- `code` - Unique department code
- `manager_id` - FK to User (manager)
- `is_active` - Status flag
- `created_at` - Timestamp

**Relationships:**
- `users` - Employees in department
- `manager` - Department manager

### **CarryoverRequest** (`src/models/carryover_request.py`)
Vacation carryover approval workflow.

**Fields:**
- `id` - Primary key
- `employee_id` - FK to User
- `leave_type_id` - FK to LeaveType
- `from_year`, `to_year` - Year transition
- `hours_requested`, `hours_approved` - Amounts (may differ)
- `status` - Enum: 'pending', 'approved', 'denied'
- `approved_by` - FK to User
- `approved_at` - Timestamp
- `employee_notes`, `manager_notes` - Text fields
- `created_at`, `updated_at` - Timestamps

### **LeaveType** (`src/models/leave_type.py`)
Configurable leave categories.

**Fields:**
- `id` - Primary key
- `code` - Unique code (e.g., 'VACATION', 'SICK')
- `name` - Display name
- `description` - Optional description
- `category` - Enum: 'accrued', 'allocated', 'tracking_only'
- `requires_approval` - Boolean
- `requires_documentation` - Boolean
- `deducts_from_balance` - Boolean
- `is_paid` - Default paid status
- `is_active` - Status flag
- `sort_order` - Display order

### **LeavePolicy** (`src/models/leave_policy.py`)
State and city-specific leave policies with resolution hierarchy.

**Fields:**
- `id` - Primary key
- `leave_type_id` - FK to LeaveType
- `location_state`, `location_city` - NULL = default policy
- `accrual_rate` - Hours per period
- `accrual_period` - 'monthly' or 'per_hours_worked'
- `max_annual_hours`, `max_carryover_hours` - Limits
- `waiting_period_days`, `advance_notice_days` - Usage rules
- `effective_date`, `end_date` - Validity period

**Policy Resolution Order:**
1. City-specific (e.g., Chicago, IL)
2. State-specific (e.g., IL)
3. Default (no location)

### **MarketHoliday** (`src/models/market_holiday.py`)
Financial market holidays for NYSE, CME, CBOE.

**Fields:**
- `id` - Primary key
- `holiday_date` - Date of holiday
- `name` - Holiday name
- `market` - Market code (NYSE, CME, CBOE)
- `year` - Holiday year
- `is_observed` - Boolean

**Constraints:**
- Unique: (holiday_date, market)

### **AuditLog** (`src/models/audit_log.py`)
Complete action audit trail for compliance.

**Fields:**
- `id` - Primary key
- `user_id`, `username` - Who performed action
- `action` - Action type (login, pto_request, pto_approve, etc)
- `entity_type`, `entity_id` - What was affected
- `details` - JSON-serializable string
- `ip_address` - Client IP for security
- `created_at` - Timestamp

### **VacationAccrualTier** (`src/models/vacation_accrual_tier.py`)
Tenure-based vacation allocations.

**Default Tiers:**
| Years of Service | Annual Days |
|-----------------|-------------|
| 0-1 years       | 10 days     |
| 2-4 years       | 12 days     |
| 5-9 years       | 15 days     |
| 10+ years       | 20 days     |

---

## 4. KEY SERVICES

### **PTOService** (`src/services/pto_service.py`)
Manages PTO request lifecycle with balance integration.

**Key Methods:**
- `create_request(request_data)` - Submit new request with balance validation
- `approve_request(request_id, approver_id)` - Approve and update balance
- `deny_request(request_id, denial_reason)` - Deny and return pending hours
- `cancel_request(request_id)` - Employee-initiated cancellation
- `get_user_requests(db, user_id)` - All requests for user
- `get_overlapping_requests(user_id, start_date, end_date)` - Conflict detection
- `get_team_pending_requests(db, manager_id)` - Manager view

**Auto-Approval Logic:**
- Trusted employees: 'vacation', 'sick', 'personal' auto-approve
- Always requires approval: 'bereavement', 'fmla', 'jury_duty', 'voting', 'military'
- Managers: own requests auto-approve

### **BalanceService** (`src/services/balance_service.py`)
CRUD operations for PTO balances.

**Key Methods:**
- `get_or_create_balance(user_id, year, commit=True)` - Get/create balance
- `update_balance(balance, data)` - Update balance fields
- `adjust_vacation_used(balance_id, days, is_pending, commit)` - Adjust vacation
- `adjust_sick_used(balance_id, days, commit)` - Adjust sick
- `adjust_personal_used(balance_id, days, commit)` - Adjust personal
- `move_pending_to_used(balance_id, days, commit)` - Approval processing
- `remove_pending(balance_id, days, commit)` - Denial/cancellation processing

**Chicago Leave Support:**
- Safe Leave: 40 hours/year, 80 hour max carryover
- Paid Leave: 40 hours/year, 16 hour max carryover

### **YearEndService** (`src/services/year_end_service.py`)
Automatic annual balance creation and carryover processing.

**Key Methods:**
- `check_and_run_auto_processing()` - Auto-run on app startup
- `process_year_end(target_year)` - Explicit processing
- `create_balances_for_all_employees(year)` - New year allocations
- `apply_approved_carryovers(year)` - Carryover application
- `generate_market_holidays(year)` - Holiday creation

### **EmailService** (`src/services/email_service.py`)
Dark-themed email notifications with TJM branding.

**Templates:**
- Request submitted/approved/denied/cancelled
- Approval needed (manager)
- Carryover request notifications

### **AuditService** (`src/services/audit_service.py`)
Comprehensive action logging for compliance.

**Tracked Actions:**
- login, logout, password_change
- pto_request, pto_approve, pto_deny, pto_cancel
- balance_update, carryover_approve
- user_create, user_update, user_delete

### **MonitoringService** (`src/services/monitoring_service.py`)
System monitoring and alerting.

**Features:**
- Rate-limited error alerts (1 per hour per error type)
- Performance logging with configurable thresholds
- Global exception handling
- PerformanceTimer context manager

---

## 5. UI PAGES

### **Employee Pages:**
1. **dashboard.py** - Main dashboard with PTO summary
2. **request_form.py** - PTO request submission
3. **requests.py** - View/cancel all requests
4. **carryover.py** - Request carryover
5. **calendar.py** - Team calendar with market holidays
6. **analytics.py** - Personal PTO analytics
7. **reports.py** - Generate reports (PDF/CSV/HTML)
8. **handbook.py** - Company handbook viewer
9. **help.py** - Help documentation

### **Manager Pages:**
10. **manager_team.py** - View team members
11. **manager_request_detail.py** - Request approval/denial
12. **manager_carryover.py** - Carryover approvals
13. **manager_settings.py** - Notification preferences

### **Admin Pages:**
14. **admin_dashboard.py** - System overview
15. **admin_employees.py** - Employee CRUD
16. **admin_departments.py** - Department management
17. **admin_approvals.py** - Approval queue
18. **admin_handbook.py** - Handbook management
19. **admin_system.py** - System settings
20. **admin_year_end.py** - Year-end processing
21. **admin_email_preview.py** - Email template previews
22. **admin_auto_notify_reports.py** - Notification dashboard

### **Authentication:**
23. **login.py** - Login with rate limiting
24. **password_reset.py** - Password recovery

---

## 6. UI COMPONENTS

### **header.py**
- `page_header(title, show_back, back_url)` - Consistent page headers
- Logo, greeting, dark mode toggle

### **theme.py**
- `apply_dark_mode()` - Dark mode styling
- `skeleton_loader()`, `skeleton_table()`, `skeleton_card()` - Loading states
- `show_success_dialog()`, `show_error_dialog()`, `show_warning_dialog()`

**TJM Brand Colors:**
- Primary: #c9a227 (Gold)
- Gray: #5a6a72
- Dark background: #1E2328
- Light background: #E8E6E1

### **formatting.py**
- `format_days_hours(hours)` - Convert to "Xd Yh" format
- Date formatting helpers

---

## 7. USER ROLES & PERMISSIONS

### **Employee**
- Submit PTO requests
- View own balance and requests
- Cancel own pending requests
- Request vacation carryover
- View team calendar

### **Manager**
- All employee permissions
- View/approve/deny team requests
- Auto-approve own PTO
- Approve team carryover requests
- View team analytics

### **Admin**
- All manager permissions
- Add/edit/delete employees
- Manage departments
- View audit logs
- Manage user roles and trusted status
- Manage handbook

### **SuperAdmin**
- All admin permissions
- Manual year-end processing
- All system settings
- Database backup operations

---

## 8. KEY BUSINESS RULES

### **Balance Calculation**
```
available = total + carryover - used - pending
```

### **Vacation Tiers (Tenure-Based)**
| Years of Service | Annual Days |
|-----------------|-------------|
| 0-1 years       | 10 days     |
| 2-4 years       | 12 days     |
| 5-9 years       | 15 days     |
| 10+ years       | 20 days     |

### **Default Allocations**
- Sick Leave: 5 days/year
- Personal Days: 2 days/year

### **Request Workflow**
1. Employee submits → status: `pending`
2. Vacation hours added to `vacation_pending`
3. Manager approves → `pending` moves to `used`
4. Manager denies → `pending` removed

### **Auto-Approval**
- Trusted employees: vacation, sick, personal auto-approve
- Managers: own requests auto-approve
- Always manual: bereavement, fmla, jury_duty, voting, military

### **Year-End Processing**
Automatic on first app access of new year:
1. Create new year balances for all active employees
2. Apply approved carryover from previous year
3. Generate federal holidays for new year

---

## 9. TECHNOLOGY STACK

| Component | Technology |
|-----------|-----------|
| Framework | NiceGUI 3.3.0+ |
| Backend | FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Authentication | Bcrypt/Passlib |
| Validation | Pydantic 2.0+ |
| Charts | Plotly |
| Reports | ReportLab/PyPDF |
| Testing | pytest |

---

## 10. RUNNING THE APPLICATION

```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe nicegui_app/main.py
```
Access at: http://localhost:8080

---

## 11. TEST SUITE

```bash
# Run all tests
venv\Scripts\python.exe -m pytest tests/ -v

# Syntax check
venv\Scripts\python.exe -m py_compile path/to/file.py
```

**Current Status:** 142 tests passing

---

**Document Generated:** December 16, 2025
**Project Status:** Production Ready
