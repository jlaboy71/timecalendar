# Task: Fix Role-Based Logic Inconsistencies

## Problem
Admin dashboard showed "Pending Requests" count but admins had no way to approve them. The UI didn't match the logical role capabilities.

## Solution
Give admins full oversight capability to approve requests across all departments.

## Todo Items

- [x] Add "Pending Approvals" card to admin dashboard with link to approval page
- [x] Create `/admin/approvals` page for viewing/filtering all pending PTO requests
- [x] Add "Carryover Requests" card to admin dashboard
- [x] Add "Approvals" section to admin Quick Actions with PTO and Carryover buttons
- [x] Ensure carryover approval page (`/manager/carryover`) already supports admins

## Changes Made

### 1. Dashboard (nicegui_app/pages/dashboard.py)
- Added import for `CarryoverRequest` model
- Admin dashboard now shows clickable "Pending Requests" stat that links to `/admin/approvals`
- Added "Pending PTO Approvals" section showing up to 5 pending requests with:
  - Employee name and department badge
  - PTO type with color-coded border
  - Date range and days requested
  - Conflict warnings if applicable
  - "Review" button linking to request detail page
  - "View All" button if more than 5 pending
- Added "Pending Carryover Requests" card (purple) showing count and linking to carryover page
- Added new "Approvals" section in Quick Actions with:
  - "PTO Approvals" button (amber)
  - "Carryover Approvals" button (purple)

### 2. PTO Service (src/services/pto_service.py)
- Updated `get_pending_requests_with_employee_info()` to include:
  - `employee_department_id` for filtering
  - `department_name` for display badges
- Added `outerjoin` to Department table

### 3. New Admin Approvals Page (nicegui_app/main.py)
- Created `/admin/approvals` page for admins to view all pending PTO requests
- Features:
  - Logo and greeting header
  - Department filter dropdown
  - Request cards with employee info, department badge, dates, conflict warnings
  - "Review" button links to existing `/manager/request/{id}` detail page
  - Back to Dashboard button

### 4. Existing Pages Verified
- `/manager/request/{request_id}` already allows admin/superadmin access
- `/manager/carryover` already shows all departments for admins
- Request approval logic already works for admins (no department restriction)

## Review Summary

The role-based logic is now consistent:

| Role | Can See Pending | Can Approve PTO | Can Approve Carryover |
|------|----------------|-----------------|----------------------|
| Employee | Own only | No | No |
| Manager | Team only | Team only | Team only |
| Admin | All | All | All |
| Superadmin | All | All | All |

Admins now have full visibility and approval capability for:
1. PTO requests from any department
2. Carryover requests from any employee

The dashboard clearly shows pending counts and provides direct access to approval workflows.

---

# Task: Standardize Page Headers Across All Pages

## Problem
Multiple pages had inconsistent headers - some with non-clickable logos, missing help buttons, and no "Back to Dashboard" navigation buttons. User requested all pages have consistent headers with:
- Clickable logo (navigates to dashboard)
- Help button next to dark mode toggle
- Back to Dashboard button at bottom

## Solution
Update all pages to use the shared `page_header()` component and add navigation buttons where missing.

## Todo Items

- [x] Add help button to shared `page_header()` component
- [x] Fix help page card alignment using CSS Grid
- [x] Update `/admin/approvals` page - remove duplicate header
- [x] Update `/requests` page to use `page_header()`
- [x] Update `/manager/request/{request_id}` to use `page_header()`
- [x] Update `/admin` panel to use `page_header()`
- [x] Update `/admin/departments` to use `page_header()`
- [x] Update `/admin/employees/add` to use `page_header()`
- [x] Update `/admin/employees/edit/{user_id}` to use `page_header()` + back button
- [x] Update `/admin/handbook` to use `page_header()`
- [x] Update `/admin/year-end` to use `page_header()`
- [x] Update `/admin/system` to use `page_header()` + back buttons

## Changes Made

### 1. Shared Header Component (nicegui_app/components/header.py)
- Added help button (`icon='help_outline'`) next to dark mode toggle
- Now all pages using `page_header()` automatically have: logo, greeting, help, dark mode, logout

### 2. Help Page (nicegui_app/main.py - `/help`)
- Changed from flexbox to CSS Grid for chapter cards
- Used `display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));`
- Added `h-full` class to cards for consistent height

### 3. Pages Updated to Use `page_header()`:
All these pages now use the shared component instead of custom headers:
- `/admin/approvals` - removed duplicate header (was calling both custom + page_header)
- `/requests` - request history page
- `/manager/request/{request_id}` - manager request review
- `/admin` - admin panel
- `/admin/departments` - department management
- `/admin/employees/add` - add employee form
- `/admin/employees/edit/{user_id}` - edit employee form
- `/admin/handbook` - handbook management
- `/admin/year-end` - year-end processing
- `/admin/system` - superadmin system page

### 4. Back Navigation Buttons Added:
- `/admin/employees/edit/{user_id}` - "Back to Dashboard" button at bottom
- `/admin/system` - "Back to Dashboard" button at bottom
- `/admin/year-end` - "Back to Dashboard" button at bottom (alongside Refresh Status)

## Review Summary

All admin pages now have consistent headers with:
1. ✅ Clickable TJM logo (navigates to /dashboard)
2. ✅ Time-based greeting with user name
3. ✅ Help button (navigates to /help)
4. ✅ Dark mode toggle
5. ✅ Logout button
6. ✅ Back navigation where appropriate

The `page_header()` component pattern ensures future pages will automatically have all these features.

---

# Task: Automatic Year-End Processing

## Problem
1. Manual year-end processing could be triggered incorrectly or at the wrong time
2. Button said "Process Year-End Transition to 2026" which was confusing for future years
3. Date restriction logic (Dec 31 only) was flawed and didn't make sense long-term
4. Users should be able to request PTO for the following year (but not 2+ years ahead)

## Solution
Make year-end processing fully automatic - runs on first login of the new year.

## Todo Items

- [x] Create YearEndStatus model to track which years have been processed
- [x] Add check_and_run_auto_processing() function to YearEndService
- [x] Trigger auto-processing on successful login
- [x] Convert year-end page to status-only (no manual button)
- [x] Validate PTO request allows next year only (not 2+ years ahead)

## Changes Made

### 1. New Model: YearEndStatus (src/models/year_end_status.py)
- Tracks processing status for each year
- Fields: year, processed, processed_at, balances_created, carryovers_applied, holidays_created
- Prevents duplicate processing

### 2. YearEndService Updates (src/services/year_end_service.py)
- Added `check_and_run_auto_processing()` - runs processing if not already done for current year
- Added `is_year_processed()` - checks if a year has been processed
- Added `get_processing_record()` - gets the full processing record for a year
- Processing is idempotent - safe to call multiple times

### 3. Login Integration (nicegui_app/pages/login.py)
- Auto-processing triggers on successful login
- Wrapped in try/except so login never fails due to year-end issues
- Runs once per year (tracked by YearEndStatus)

### 4. Year-End Page Redesign (nicegui_app/main.py - `/admin/year-end`)
- Renamed to "YEAR-END STATUS" (monitoring only, no manual trigger)
- Shows processing status with timestamp and counts
- Shows current year and next year preview
- Warns about pending carryover requests with link to review them
- Buttons: Back to Dashboard, Refresh Status

### 5. PTO Request Validation (src/services/pto_service.py)
- Added validation: requests cannot be more than 1 year in advance
- In 2025, users can request for 2025 or 2026, but not 2027

## How It Works

1. **On January 1st (or any day in the new year)**:
   - First user to log in triggers `check_and_run_auto_processing()`
   - System checks if current year has been processed
   - If not, runs the transition: creates balances, applies carryovers, generates holidays
   - Records the processing in `year_end_status` table

2. **Subsequent logins**:
   - `check_and_run_auto_processing()` sees year is already processed
   - Returns immediately with no action

3. **Admins can monitor**:
   - Visit `/admin/year-end` to see processing status
   - See when processing occurred and what was created
   - Review any pending carryover requests

## Review Summary

Year-end processing is now:
1. ✅ Fully automatic (no manual intervention needed)
2. ✅ Idempotent (safe to call multiple times)
3. ✅ Works year after year (no hardcoded dates)
4. ✅ Tracked (admins can see when/what was processed)
5. ✅ Reliable (runs on first login, never blocks login)
