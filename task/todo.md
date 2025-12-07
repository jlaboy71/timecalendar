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
- `/admin/system` - "Back to Admin" and "Back to Dashboard" buttons at bottom

## Review Summary

All admin pages now have consistent headers with:
1. ✅ Clickable TJM logo (navigates to /dashboard)
2. ✅ Time-based greeting with user name
3. ✅ Help button (navigates to /help)
4. ✅ Dark mode toggle
5. ✅ Logout button
6. ✅ Back navigation where appropriate

The `page_header()` component pattern ensures future pages will automatically have all these features.
