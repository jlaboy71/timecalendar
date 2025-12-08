# TimeCalendar Enhancement Roadmap v2

## Overview
This roadmap contains all remaining enhancements to make the TJM Time Calendar system run perfectly. Items are prioritized by impact and grouped by category. Mobile responsive CSS work is intentionally placed last per requirements.

---

## Phase 1: Form Validation & Data Integrity ✅ COMPLETE

### 1.1 Edit Employee Form Validation ✅
- [x] Add inline validation to Edit Employee dialog (required fields, email format, password length)
- [x] Ensure validation matches Add Employee form behavior
- [x] Clear validation errors when dialog opens

### 1.2 PTO Request Form Validation ✅
- [x] Add validation for required date selection (already handled by calendar UI)
- [x] Validate date range (end date >= start date) - already implemented in submit_request
- [x] Validate hours field (positive numbers only) - handled by UI constraints
- [x] Prevent submission of invalid requests - already implemented

### 1.3 Department/Team Form Validation ✅
- [x] Add required field validation to Add Department form
- [x] Add required field validation to Edit Department form
- [x] Validate manager selection where applicable (optional field)

---

## Phase 2: User Experience Improvements ✅ COMPLETE

### 2.1 Loading States on Actions ✅
- [x] Add loading spinner/disabled state to login button during authentication
- [x] Add loading state to PTO request submission
- [x] Add loading state to employee create/update operations
- [x] Add loading state to approve/deny bulk operations
- [x] Add loading state to report exports (info notification)

### 2.2 Confirmation Dialogs ✅
- [x] Review all destructive actions have confirmation dialogs
- [x] Add confirmation to cancel PTO request (both dashboard and requests page)
- [x] Bulk deny already has confirmation dialog
- [x] Delete department, deactivate/delete employee already have confirmations

### 2.3 Success/Error Feedback ✅
- [x] Standardize notification styling (success = green, error = red, warning = amber)
- [x] Already consistent throughout the application
- [x] Error messages are user-friendly

---

## Phase 3: Data Loading Experience ⏸️ PARTIAL

### 3.1 Skeleton Loader Integration (Deferred)
- [ ] Integrate skeleton loaders into dashboard cards during initial load
- [ ] Add skeleton tables to employee management page
- [ ] Add skeleton loaders to reports tab content
- [ ] Consider async data loading patterns for smoother UX
- **Note**: Skeleton components exist but full integration requires async restructuring of page rendering

### 3.2 Empty State Handling ✅
- [x] Add friendly empty state messages when no data exists
- [x] Add empty state for filtered results with "no matches" message
- [x] Added icons to empty states for better visual feedback
- [ ] Include action prompts in empty states (e.g., "Create your first employee") - deferred

---

## Phase 4: Consistency & Polish ✅ COMPLETE

### 4.1 Button Styling Consistency ✅
- [x] Audit all buttons across the application
- [x] Standardize primary action buttons (blue filled) - already consistent
- [x] Standardize secondary action buttons (outlined or flat) - already consistent
- [x] Standardize danger/delete buttons (red) - already consistent
- [x] Ensure consistent button sizing - already consistent
- [x] Standardize "Back to Dashboard" buttons (icon='arrow_back', props='outline')

### 4.2 Table Styling Consistency ✅
- [x] Review all tables for consistent column widths - using w-full consistently
- [x] Standardize action column placement (always last) - already consistent
- [x] Ensure consistent row heights - using dense prop where appropriate
- [x] Add hover states to all tables - built into NiceGUI tables

### 4.3 Dialog Consistency ✅
- [x] Standardize dialog widths by type (small, medium, large) - using min-w-* classes
- [x] Ensure consistent header styling - already consistent
- [x] Standardize button placement in dialogs (Cancel left, Primary right) - using justify-end
- [x] Add consistent padding (p-6) to all confirmation dialogs

---

## Phase 5: Error Handling & Resilience ✅ COMPLETE

### 5.1 Database Error Handling ✅
- [x] Add try/catch blocks around all database operations - already comprehensive
- [x] Show user-friendly error messages instead of technical errors - using ui.notify
- [x] Log errors to audit log for debugging - AuditService integrated
- [x] Gracefully handle connection failures - try/finally with db.close()
- [x] Fixed bare `except:` clause to use specific exception types

### 5.2 Session Handling ✅
- [x] Review session timeout behavior - SessionManager class implemented
- [x] Ensure graceful handling of expired sessions - redirect with ?timeout=1
- [x] Add "session will expire soon" warning - popup dialog implemented in header

### 5.3 Input Sanitization ✅
- [x] Review all user inputs for proper sanitization - NiceGUI handles automatically
- [x] Prevent XSS in any user-generated content - no raw HTML with user input
- [x] Validate file inputs (if any) - handbook PDF upload validates file type
- [x] SQLAlchemy ORM used throughout - parameterized queries prevent SQL injection

---

## Phase 6: Accessibility (A11Y) ⏸️ PARTIAL

### 6.1 Keyboard Navigation
- [x] Ensure all interactive elements are keyboard accessible (NiceGUI/Quasar built-in)
- [x] Add proper tab order to forms (NiceGUI/Quasar built-in)
- [x] Support Enter key for form submission (login form + handbook AI)
- [x] Support Escape key to close dialogs (Quasar built-in)

### 6.2 Screen Reader Support
- [x] Add ARIA labels to icon-only buttons (13 buttons updated)
- [ ] Add ARIA labels to form inputs - deferred (NiceGUI labels provide implicit association)
- [ ] Ensure proper heading hierarchy (h1, h2, h3) - deferred
- [ ] Add alt text to images/icons - deferred (decorative icons don't require alt text)

### 6.3 Focus Management
- [x] Auto-focus first field when dialogs open (Quasar built-in)
- [x] Return focus to trigger element when dialog closes (Quasar built-in)
- [x] Add visible focus indicators (Quasar built-in focus rings)

---

## Phase 7: Performance Optimization ✅ COMPLETE

### 7.1 Query Optimization ✅
- [x] Review database queries for N+1 issues - fixed in reports.py and manager_carryover.py
- [x] Add indexes where beneficial - added composite indexes via migration
- [x] Consider pagination on large data sets (already done for employees)

### 7.2 Frontend Optimization ✅
- [x] Review for unnecessary re-renders (NiceGUI/Vue.js handles reactivity)
- [x] Optimize large table rendering (pagination implemented)
- [x] Consider lazy loading for report exports (async with notifications)

---

## Phase 8: Mobile Responsive CSS ⏭️ SKIPPED

**Note**: This phase was skipped - the application will only be accessed from desktop browsers, not mobile devices.

---

## Review Section
_To be filled in as work progresses_

### Completed Items
- [x] Pagination for employee management
- [x] Skeleton loader components created
- [x] Audit log filtering and export
- [x] Form validation utilities created
- [x] Back arrows removed from all pages
- [x] Add Employee form validation
- [x] Login form validation
- [x] Edit Employee form validation (inline)
- [x] Create Department form validation (inline)
- [x] Edit Department form validation (inline)
- [x] PTO Request form validation (already implemented)
- [x] Loading state on login button
- [x] Loading state on PTO request submission
- [x] Loading state on employee create/update
- [x] Loading state on bulk approve/deny
- [x] Confirmation dialog on cancel PTO request (dashboard + requests page)
- [x] Loading notification on report exports
- [x] Empty state icons added to reports page (5 locations)
- [x] Empty state icons added to employee list filter
- [x] Empty state icon added to pending approvals department filter
- [x] Standardized "Back to Dashboard" buttons across all pages (icon='arrow_back', props='outline')
- [x] Added consistent p-6 padding to confirmation dialogs
- [x] Fixed bare `except:` clause to use specific exception types (json.JSONDecodeError, TypeError, ValueError)
- [x] Added ARIA labels to 13 icon-only buttons (header, calendar, pagination, backup, etc.)
- [x] Added Enter key support to login form (username and password fields)
- [x] Verified keyboard navigation built into NiceGUI/Quasar framework
- [x] Fixed N+1 query issue in reports.py team balance (added joinedload for department)
- [x] Fixed N+1 query issue in manager_carryover.py (added joinedload for department)
- [x] Added composite indexes: ix_pto_requests_user_status, ix_pto_requests_status_dates, ix_audit_logs_action_created

### Notes
- Skeleton loaders created but require async restructuring to fully integrate
- Form validation utilities available: `validate_required`, `validate_email`, `validate_min_length`, `FormValidator` class
- Dark mode already implemented and working

---

## Getting Started
Begin with Phase 1 (Form Validation) as it directly impacts data integrity and user experience. Each phase builds on the previous one, though some items can be worked on in parallel.
