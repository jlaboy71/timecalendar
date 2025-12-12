# TJM Time Calendar - Complete Implementation Guide

## PROJECT CONTEXT

**Project:** TJM Time Calendar - PTO and Market Calendar System  
**Company:** Haventech Solutions / TJM Holdings  
**Framework:** NiceGUI (Python)  
**Database:** SQLite (`tjm_calendar.db`)  
**Port:** 8080  
**Test Credentials:** netadmin/netpass (manager role)

---

## COMPLETED WORK (Sessions 1-5)

### ✅ Session 1-2: Foundation & Authentication
- NiceGUI project structure established
- SQLite database connection working
- Login/logout system with session management
- Role-based routing (employee vs manager views)

### ✅ Session 3: Employee Dashboard & PTO Request
- Live PTO balance display (vacation, sick, personal)
- PTO request submission form (basic - vacation/sick/personal only)
- Date range picker with validation
- Business day calculations

### ✅ Session 4: Manager Approval Queue
- Manager dashboard with pending requests table
- Request detail page with employee context
- Approve/deny workflow with balance deduction
- Status updates (pending → approved/denied)

### ✅ Session 5: Employee Request History
- Employee can view their own PTO request history
- Status indicators (pending/approved/denied)
- Filter capabilities

### ✅ Database Migration (Just Completed)
- Migrated from PostgreSQL to SQLite
- Fresh migration: `d1d45e7991f9_initial_sqlite_migration.py`
- 10 tables created with seed data
- File: `tjm_calendar.db` (180KB)

---

## REMAINING IMPLEMENTATION SESSIONS

Complete these sessions in order. Each session includes tasks, self-checks, and expected outcomes.

---

## SESSION 6: Database Schema Enhancements

### Objective
Add missing fields to support full business requirements.

### Tasks

**Task 6.1: Update User Model**
Add to the `users` table/model:
- `anniversary_date` (Date, nullable) - Employee work anniversary for vacation accrual calculation
- `remote_schedule` (JSON/Text, nullable) - Store which days employee works from home
  - Format: `{"monday": false, "tuesday": true, "wednesday": false, "thursday": false, "friday": false}`
- `is_active` (Boolean, default True) - Soft delete capability

**Task 6.2: Expand PTO Types**
Current types: `vacation`, `sick`, `personal`, `remote`

Add these new types to the `pto_type` enum or leave_types table:
- `jury_duty` (non-deductible, requires approval)
- `bereavement` (non-deductible, requires approval)
- `maternity` (non-deductible, requires approval)
- `paternity` (non-deductible, requires approval)
- `medical_leave` (non-deductible, requires approval)
- `unpaid` (non-deductible, requires approval)
- `fmla` (non-deductible, requires approval)
- `voting` (non-deductible, requires approval)
- `military` (non-deductible, requires approval)

**Task 6.3: Enhance PTO Requests Table**
Add/verify these fields:
- `description` (Text, nullable) - Required reason/description for the request
- `is_paid` (Boolean, default True) - Whether this leave type is paid
- `deducts_balance` (Boolean, default True) - Whether it deducts from PTO balances

**Task 6.4: Create Alembic Migration**
```bash
alembic revision --autogenerate -m "Add anniversary_date, remote_schedule, expanded PTO types"
alembic upgrade head
```

### Self-Check for Session 6
- [ ] `users` table has `anniversary_date`, `remote_schedule`, `is_active` columns
- [ ] All new PTO types are available in the system
- [ ] `pto_requests` table has `description`, `is_paid`, `deducts_balance` columns
- [ ] Migration runs without errors
- [ ] Existing data is preserved
- [ ] App starts successfully on port 8080

---

## SESSION 7: Enhanced PTO Request Form

### Objective
Update the PTO request submission form with all leave types and required description.

### Tasks

**Task 7.1: Update Request Form UI**
Modify the `/submit-request` route to include:
- Dropdown with ALL PTO types (vacation, sick, personal, jury_duty, bereavement, maternity, paternity, medical_leave, unpaid, fmla, voting, military)
- Required `description` textarea field (minimum 10 characters)
- Display whether selected type deducts from balance or not
- Show current balance for deductible types

**Task 7.2: Update Form Validation**
- Description is required for all requests
- For balance-deducting types, validate sufficient balance exists
- For non-deducting types, skip balance validation
- Date validation (start date <= end date, not in past)

**Task 7.3: Update Submission Logic**
- Set `is_paid` and `deducts_balance` based on leave type
- Store description in database
- Only deduct balance for applicable types on approval

**Task 7.4: Update Leave Type Display**
Create a helper that categorizes leave types:
```python
DEDUCTIBLE_TYPES = ['vacation', 'sick', 'personal']
NON_DEDUCTIBLE_TYPES = ['jury_duty', 'bereavement', 'maternity', 'paternity', 'medical_leave', 'unpaid', 'fmla', 'voting', 'military']
```

### Self-Check for Session 7
- [ ] All leave types appear in dropdown
- [ ] Description field is present and required
- [ ] Form shows "Deducts from balance" or "Does not deduct from balance"
- [ ] Balance validation works for deductible types
- [ ] Non-deductible requests can be submitted without balance check
- [ ] Submitted requests have description stored in database

---

## SESSION 8: Employee Management (Admin Panel)

### Objective
Build admin interface for managing employees.

### Tasks

**Task 8.1: Create Admin Route**
- New route: `/admin/employees`
- Protected: only accessible by users with `role='admin'` or `role='manager'`
- Navigation link in sidebar (visible only to admin/manager)

**Task 8.2: Employee List Table**
Display all employees in a NiceGUI table:
- Columns: Name, Email, Department, Role, Hire Date, Anniversary Date, Status (Active/Inactive)
- Include Edit and Deactivate buttons per row
- Add "Add New Employee" button at top
- Filter by department, status, role

**Task 8.3: Add Employee Form**
Create modal or separate page with fields:
- First Name (required)
- Last Name (required)
- Email (required, unique)
- Username (required, unique)
- Password (required, minimum 8 characters)
- Department (dropdown from departments table)
- Role (dropdown: employee, manager, admin)
- Hire Date (date picker)
- Anniversary Date (date picker, defaults to hire date)
- Remote Work Schedule (checkboxes for each weekday)
- Is Active (checkbox, default True)

**Task 8.4: Edit Employee Form**
- Pre-populate all fields with current values
- Password field optional (only update if provided)
- Save updates to database

**Task 8.5: Soft Delete (Deactivate)**
- "Deactivate" button sets `is_active=False`
- Confirmation dialog before deactivating
- Deactivated users cannot login
- Show "Reactivate" button for inactive users

**Task 8.6: Initialize PTO Balances**
When creating new employee:
- Calculate vacation days based on anniversary date and company policy:
  - 0-4 years: 10 days (80 hours)
  - 5-9 years: 15 days (120 hours)
  - 10+ years: 20 days (160 hours)
- Set sick days: 5 days (40 hours)
- Set personal days: 2 days (16 hours)
- Create entry in `pto_balances` table

### Self-Check for Session 8
- [ ] `/admin/employees` route works and is protected
- [ ] Employee list displays all employees with correct data
- [ ] "Add Employee" creates new user with all fields
- [ ] Password is hashed before storing
- [ ] "Edit Employee" updates existing user correctly
- [ ] "Deactivate" sets `is_active=False` and user cannot login
- [ ] "Reactivate" sets `is_active=True` and user can login again
- [ ] New employees get correct initial PTO balances
- [ ] Anniversary-based vacation calculation works correctly

---

## SESSION 9: Team Calendar View

### Objective
Build calendar visualization showing PTO and market holidays.

### Tasks

**Task 9.1: Create Calendar Route**
- New route: `/calendar`
- Accessible to all authenticated users
- Navigation link in sidebar

**Task 9.2: Integrate FullCalendar.js**
NiceGUI can embed JavaScript libraries. Use FullCalendar for the calendar display:
```python
ui.html('''
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css' rel='stylesheet' />
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
''')
```

**Task 9.3: Display Approved PTO**
- Query all approved PTO requests
- Color-code by type:
  - Vacation: Blue
  - Sick: Orange
  - Personal: Green
  - Other types: Gray
- Show employee name on calendar event

**Task 9.4: Display Market Holidays**
- Query `market_holidays` table
- Display as all-day events
- Color: Red
- Show exchange name (NYSE, CME, CBOE)

**Task 9.5: Calendar Controls**
- Month/Week/Day view toggle
- Previous/Next navigation
- Today button
- Optional: Filter by department

**Task 9.6: Click Event Details**
When clicking a calendar event:
- Show modal with full details
- PTO: Employee name, type, dates, description, status
- Holiday: Exchange name, holiday name, date

### Self-Check for Session 9
- [ ] `/calendar` route loads without errors
- [ ] Calendar displays current month by default
- [ ] Approved PTO requests appear on correct dates
- [ ] Market holidays appear on correct dates
- [ ] Color coding works correctly
- [ ] Month/Week/Day views work
- [ ] Navigation (prev/next/today) works
- [ ] Clicking event shows details

---

## SESSION 10: Manager Features Enhancement

### Objective
Enhance manager approval workflow with additional features.

### Tasks

**Task 10.1: Team Calendar Filter**
On calendar page, managers can:
- Filter to show only their department's PTO
- Filter to show only direct reports
- Toggle to show/hide market holidays

**Task 10.2: Bulk Approval**
On manager dashboard:
- Checkboxes to select multiple pending requests
- "Approve Selected" button
- "Deny Selected" button (requires shared denial reason)
- Confirmation dialog before bulk action

**Task 10.3: Conflict Detection**
When viewing pending request:
- Show warning if dates overlap with:
  - Other approved PTO in same department
  - Market holidays
  - Company blackout dates (if any)
- Display who else is out on those dates

**Task 10.4: Request History Filter**
Manager can view all requests (not just pending):
- Filter by status (all, pending, approved, denied)
- Filter by employee
- Filter by date range
- Filter by PTO type

### Self-Check for Session 10
- [ ] Department filter works on calendar
- [ ] Bulk approval processes multiple requests correctly
- [ ] Balances deducted correctly for bulk approvals
- [ ] Conflict warnings display when applicable
- [ ] Request history filters work correctly

---

## SESSION 11: Reports & Export

### Objective
Add reporting and data export capabilities.

### Tasks

**Task 11.1: Create Reports Route**
- New route: `/reports`
- Accessible to managers and admins only

**Task 11.2: Balance Summary Report**
- Table showing all employees and their current balances
- Columns: Employee, Department, Vacation (Used/Total), Sick (Used/Total), Personal (Used/Total)
- Export to CSV button

**Task 11.3: Usage Report**
- Filter by date range
- Show PTO usage by employee
- Group by department or leave type
- Export to CSV button

**Task 11.4: Audit Log Report**
- Show recent approval/denial actions
- Columns: Date, Request ID, Employee, Action, Approved/Denied By
- Filter by date range

**Task 11.5: CSV Export Function**
Create reusable export function:
```python
def export_to_csv(data: list, filename: str, columns: list):
    # Generate CSV and trigger download
```

### Self-Check for Session 11
- [ ] `/reports` route works and is protected
- [ ] Balance summary shows correct data
- [ ] Usage report filters work correctly
- [ ] CSV export downloads valid file
- [ ] Audit log shows recent actions

---

## SESSION 12: Polish & Production Prep

### Objective
Final cleanup and production readiness.

### Tasks

**Task 12.1: Remove Debug Code**
- Remove all `print()` statements
- Remove any hardcoded test data
- Remove unused imports

**Task 12.2: Error Handling**
- Add try/catch around database operations
- Display user-friendly error messages
- Log errors to file (not console)

**Task 12.3: Input Validation**
- Sanitize all user inputs
- Validate email formats
- Validate date ranges
- Prevent SQL injection (SQLAlchemy handles this, but verify)

**Task 12.4: UI Polish**
- Consistent styling across all pages
- Loading indicators for async operations
- Success/error notifications (toast messages)
- Mobile responsive adjustments

**Task 12.5: Session Security**
- Session timeout after inactivity
- Secure session cookies
- CSRF protection if applicable

**Task 12.6: Documentation**
- Update README with final setup instructions
- Document all routes and their purposes
- Document database schema
- Create user guide for end users

### Self-Check for Session 12
- [ ] No debug print statements in code
- [ ] Errors display user-friendly messages
- [ ] All inputs are validated
- [ ] UI is consistent and professional
- [ ] Session management is secure
- [ ] README is complete and accurate

---

## DATABASE SCHEMA REFERENCE

### Current Tables (after Session 6)

**users**
- id, username, email, hashed_password, first_name, last_name
- department_id, role, hire_date, anniversary_date
- remote_schedule (JSON), is_active, created_at, updated_at

**departments**
- id, name, created_at

**pto_requests**
- id, user_id, pto_type, start_date, end_date, days_requested
- description, status, is_paid, deducts_balance
- approved_by, approved_at, denial_reason, notes
- created_at, updated_at

**pto_balances**
- id, user_id, year
- vacation_total, vacation_used, vacation_pending
- sick_total, sick_used
- personal_total, personal_used
- remote_weekly_used
- created_at, updated_at

**market_holidays**
- id, date, name, exchange (NYSE/CME/CBOE)
- created_at

**leave_types** (if using separate table)
- id, name, code, is_paid, deducts_balance, requires_approval
- created_at

**leave_policies** (if using)
- id, state, leave_type_id, rules (JSON)

---

## BUSINESS RULES REFERENCE

### Vacation Accrual (Anniversary-Based)
- 0-4 years of service: 10 days/year
- 5-9 years of service: 15 days/year
- 10+ years of service: 20 days/year

### Sick Time
- All employees: 5 days/year (40 hours)

### Personal Days
- All employees: 2 days/year
- Max 1 personal day per 6-month period

### Leave Types That DO Deduct Balance
- Vacation, Sick, Personal

### Leave Types That DO NOT Deduct Balance
- Jury Duty, Bereavement, Maternity, Paternity
- Medical Leave, FMLA, Unpaid, Voting, Military

### Request Validation
- Start date cannot be in the past
- End date must be >= start date
- Description required for all requests
- Balance check only for deductible types

---

## ROUTES SUMMARY

| Route | Access | Purpose |
|-------|--------|---------|
| `/` | Public | Login page |
| `/dashboard` | All authenticated | Employee dashboard, balances |
| `/submit-request` | All authenticated | Submit PTO request |
| `/requests` | All authenticated | View own request history |
| `/calendar` | All authenticated | Team calendar view |
| `/manager` | Manager/Admin | Pending approvals queue |
| `/manager/request/{id}` | Manager/Admin | Approve/deny specific request |
| `/admin/employees` | Manager/Admin | Employee management |
| `/reports` | Manager/Admin | Reports and exports |
| `/logout` | All authenticated | End session |

---

## HOW TO USE THIS GUIDE

1. **Start each session** by telling Claude in VS Code which session you're working on
2. **Complete all tasks** in order within each session
3. **Run self-checks** before moving to next session
4. **Commit after each session**: `git add -A && git commit -m "Session X complete"`
5. **Test the app** after each session: `python -m nicegui_app.main` (or however your app runs)

### Example Prompt for Claude in VS Code:

```
Working on TJM Time Calendar project.
Current session: Session 6 - Database Schema Enhancements

Please implement Task 6.1: Update the User model to add:
- anniversary_date (Date, nullable)
- remote_schedule (JSON/Text, nullable)
- is_active (Boolean, default True)

After updating the model, create the Alembic migration.
```

---

## TROUBLESHOOTING

### App Won't Start
- Check SQLite file exists: `tjm_calendar.db`
- Verify DATABASE_URL in `.env`: `DATABASE_URL=sqlite:///tjm_calendar.db`
- Run migrations: `alembic upgrade head`

### Database Errors
- Check model matches current schema
- May need to recreate database: delete `tjm_calendar.db` and run `alembic upgrade head`

### Import Errors
- Verify all dependencies installed: `pip install -r requirements.txt --break-system-packages`

### Port Already in Use
- Kill existing process or change port in app config

---

## FINAL NOTES

- This guide assumes NiceGUI framework - adjust if using different UI
- SQLite is now the database (migrated from PostgreSQL)
- All code should be production-ready, not prototypes
- Follow existing code patterns in the project
- Test after each change before committing

**Good luck! Work through each session methodically.**
