# WFH Day Swap Feature - Complete Technical Specification

## Overview
Peer-to-peer WFH day exchange system allowing employees to swap their designated Work From Home days with teammates. No manager approval required.

## Architecture

### Data Flow
```
UI Layer (wfh_swap.py)
    ├── Page Render: db session created, closed in finally block
    ├── Display Functions: Use page-level db (safe - runs before finally)
    └── Callbacks: MUST use fresh db session (runs AFTER page finally)
         │
         ▼
Service Layer (wfh_swap_service.py)
    ├── create_swap_request() - 11 validations enforced
    ├── accept_swap() / decline_swap() / cancel_swap()
    └── Query methods for data retrieval
         │
         ▼
Data Layer
    ├── WFHDaySwapRequest model (wfh_day_swap.py)
    ├── User model (user.py) - wfh_swap_eligible, remote_schedule
    ├── MarketHoliday model - Federal holiday validation
    └── AuditLog model - Activity tracking
```

### Critical: Database Session Lifecycle
```python
# Page-level session - OK for reads during render
db = next(get_db())
try:
    # ... page rendering code ...
finally:
    db.close()  # Session closed BEFORE callbacks execute!

# Callback pattern - MUST get fresh session
def callback_handler(e, ...):
    callback_db = next(get_db())  # Fresh session
    try:
        # ... callback logic ...
    except ValueError as err:
        show_error_dialog('Error', str(err))
    except Exception as err:
        logger.error(f"Error: {err}")
        show_error_dialog('Error', f'An unexpected error occurred: {str(err)}')
    finally:
        callback_db.close()  # Always close
```

## Validation Rules (Service Layer)

All validations enforced in `create_swap_request()` at `wfh_swap_service.py:113-268`:

| # | Rule | Code Location | Error Message |
|---|------|---------------|---------------|
| 1 | Self-swap blocked | Line 146-147 | "Cannot swap WFH day with yourself" |
| 2 | Weekdays only | Line 149-151 | "Swap date must be a weekday" |
| 3 | Future dates only | Line 153-155 | "Swap date must be in the future" |
| 4 | Two-week window | Line 157-163 | "Swap date must be within current week or next week only" |
| 5 | Federal holiday blocked | Line 165-173 | "Cannot swap on {name} - office is closed for federal holiday" |
| 6 | Requester active | Line 176-177 | "Your account is not active" |
| 7 | Target active | Line 178-179 | "Target user's account is not active" |
| 8 | Requester eligible | Line 182-183 | "You are not eligible for WFH day swaps" |
| 9 | Target eligible | Line 184-185 | "Target user is not eligible for WFH day swaps" |
| 10 | Weekly limit (requester) | Line 193-206 | "You already have a swap request for this week..." |
| 11 | Weekly limit (target) | Line 208-221 | "This teammate already has a swap request for that week" |
| 12 | Requester WFH day | Line 227-228 | "You don't have a designated WFH day" |
| 13 | Target WFH day | Line 230-231 | "Target user doesn't have a designated WFH day" |
| 14 | Day match | Line 234-239 | "Target user's WFH day is {day}, but swap date is a {day}" |
| 15 | Message required | Line 241-243 | "A message is required for swap requests" |

## Holiday Handling

### Case Sensitivity (CRITICAL)
```python
# CORRECT - Database stores 'Federal' with capital F
MarketHoliday.market == 'Federal'

# WRONG - Will not match any holidays!
MarketHoliday.market == 'FEDERAL'
```

### Early Close vs Full Holiday
```python
# Early Close days (e.g., "Christmas Eve (Early Close)") - SWAPS ALLOWED
if 'Early Close' in holiday.name:
    # Working half-day, swaps permitted
    # Show orange clock icon, amber label

# Full holidays - SWAPS BLOCKED
else:
    # Office closed, swaps not allowed
    # Grey out column, show red icon
```

## Request Lifecycle

| Status | Description | Who Can Set | Next States |
|--------|-------------|-------------|-------------|
| `pending` | Awaiting target response | System on create | accepted, declined, cancelled, expired |
| `accepted` | Target approved swap | Target user | (terminal) |
| `declined` | Target rejected swap | Target user | (terminal) |
| `cancelled` | Requester withdrew | Requester only | (terminal) |
| `expired` | No response in 3 business days | System/cron | (terminal) |

## UI Display Rules

### Week View
- Toggle between "This Week" and "Next Week" only
- Each day column shows date under day name
- User's effective WFH day (swapped or default) has gold star + border

### Employee Display
| Condition | Display | Clickable |
|-----------|---------|-----------|
| Normal employee | Colored dot + name + hours | Yes (opens swap dialog) |
| Self | Slightly dimmed | No |
| Has swap this week | Swap icon with pair color | No (tooltip: "Already has swap") |
| Swapped position | Name in pair color | No |
| Holiday (full) | Greyed out | Yes (shows holiday info) |

### Swap Pair Colors
Users in the same swap share a color for visual pairing:
- Amber (#f59e0b), Green (#22c55e), Blue (#3b82f6), Purple (#a855f7), etc.

## Audit Logging

### Actions Logged
| Action | Method | Details Stored |
|--------|--------|----------------|
| `wfh_swap_request` | `log_wfh_swap_request()` | target_employee, swap_date |
| `wfh_swap_accept` | `log_wfh_swap_accept()` | requester_name, swap_date |
| `wfh_swap_decline` | `log_wfh_swap_decline()` | requester_name, swap_date |
| `wfh_swap_cancel` | `log_wfh_swap_cancel()` | (swap_id only) |
| `wfh_swap_admin_delete` | `AuditService.log()` | deleted_swap_id, swap_date |

### Role-Based Visibility
- **Employees**: See activity for This Week and Next Week only
- **Managers/Admins/Superadmins**: See full year activity

## Error Handling Pattern

### Standard Callback Error Handling
```python
def callback_handler(e, ...):
    callback_db = next(get_db())
    try:
        # Business logic
        callback_service = WFHSwapService(callback_db)
        callback_service.some_action(...)

        # Audit logging (non-critical)
        try:
            AuditService.log_wfh_swap_*(db=callback_db, ...)
        except Exception:
            pass  # Audit failure shouldn't break flow

        # Success feedback
        show_success_dialog('Title', 'Message')
        refresh_all()

    except ValueError as err:
        # Business rule violation - show user-friendly message
        show_error_dialog('Validation Error', str(err))
    except Exception as err:
        # Unexpected error - log and show generic message
        logger.error(f"Error in {action}: {err}")
        show_error_dialog('Error', f'An unexpected error occurred: {str(err)}')
    finally:
        callback_db.close()
```

### Email Handling (Non-Critical)
```python
try:
    if target.email:
        email_service.send_wfh_swap_*(...)
except Exception:
    show_warning_dialog('Email Failed', 'Email notification could not be sent.')
    # Continue - email failure doesn't block the action
```

## Code Locations

| Component | File | Key Lines |
|-----------|------|-----------|
| UI Page | `nicegui_app/pages/wfh_swap.py` | Full file |
| Service | `src/services/wfh_swap_service.py` | Full file |
| Model | `src/models/wfh_day_swap.py` | Full file |
| Audit Methods | `src/services/audit_service.py` | Lines 207-289 |
| User Eligibility | `src/models/user.py` | `wfh_swap_eligible` field |
| Holiday Model | `src/models/market_holiday.py` | `market`, `name` fields |

## Testing Checklist

When modifying WFH swap feature:
- [ ] Test as employee (can send, cancel own requests)
- [ ] Test as manager (same as employee)
- [ ] Test as admin (can delete any swap)
- [ ] Test as superadmin (can delete audit entries)
- [ ] Verify audit log records all actions
- [ ] Check holiday blocking (full holidays blocked, Early Close allowed)
- [ ] Verify weekly limit prevents double-swaps
- [ ] Test email notifications (non-blocking on failure)
- [ ] Verify swap pair colors match for both users
- [ ] Check week toggle updates all displays
