# PTO Business Rules Skill

This skill provides comprehensive knowledge of TJM Time Calendar PTO business rules, calculations, and validation patterns.

---

## 1. Leave Type Categories

### Accruing Types (Balance Tracked)
| Type | Annual Allocation | Carryover | Hard Block |
|------|------------------|-----------|------------|
| **Vacation** | 80-160 hrs (by tenure) | 0 hrs default (exception only) | NO - manager discretion |
| **Sick** | 40 hrs (5 days) | 56-80 hrs cap (accumulates) | YES |
| **Personal** | 16 hrs (2 days) | 0 hrs (use-it-or-lose-it) | YES |
| **Chicago Leave** | 40 hrs (5 days) | 16 hrs max (auto) | NO |

### Non-Accruing Types (No Balance Limits)
- Bereavement, FMLA, Jury Duty, Voting, Military
- These require documentation/approval but no balance tracking

---

## 2. Vacation Tiers by Tenure

```python
# Service years calculated from hire_date
def get_vacation_tier(years_of_service: int) -> int:
    if years_of_service < 2:
        return 80   # 10 days
    elif years_of_service < 5:
        return 96   # 12 days
    elif years_of_service < 10:
        return 120  # 15 days
    else:
        return 160  # 20 days
```

**File**: `src/services/accrual_service.py`

---

## 3. Balance Calculation Formula

```python
# Available balance formula (same for all types)
available = total + carryover - used - pending

# Example for vacation:
vacation_available = (
    vacation_total +      # Annual allocation
    vacation_carryover -  # Approved carryover from previous year
    vacation_used -       # Approved requests
    vacation_pending      # Pending requests awaiting approval
)
```

**Critical**: Always use `Decimal` for balance calculations to avoid floating-point errors.

---

## 4. Request Status Lifecycle

```
PENDING ─────┬────> APPROVED ────> (balance: pending → used)
             │
             ├────> DENIED ──────> (balance: pending restored)
             │
             └────> CANCELLED ───> (balance: pending restored)
```

### Status Transitions
| From | To | Who Can Do | Balance Action |
|------|-----|------------|----------------|
| pending | approved | Manager/Admin/SuperAdmin | `pending` → `used` |
| pending | denied | Manager/Admin/SuperAdmin | `pending` restored |
| pending | cancelled | Requestor only | `pending` restored |

---

## 5. Auto-Approval Rules

### Self-Approving Roles
```python
# These roles auto-approve their own standard PTO (vacation, sick, personal)
AUTO_APPROVE_ROLES = ['manager', 'admin', 'superadmin']

# Hours go directly to `used` (skip pending)
```

### Trusted Employees
```python
# User.is_trusted = True enables auto-approval for:
TRUSTED_AUTO_APPROVE_TYPES = ['vacation', 'sick', 'personal']

# Special types (FMLA, Bereavement, etc.) still require approval
```

---

## 6. Carryover Rules

### Sick Leave (Auto-Carryover)
```python
# Automatic - no approval required
# Cap varies by state: 56-80 hours
# Accumulates over multiple years

unused_sick = sick_total + sick_carryover - sick_used
carryover = min(unused_sick, SICK_CARRYOVER_MAX)  # 56-80 hrs
```

### Chicago Paid Leave (Auto-Carryover)
```python
# Per Chicago ordinance - automatic
# Max 16 hours (2 days) carryover

unused_chicago = chicago_total + chicago_carryover - chicago_used
carryover = min(unused_chicago, Decimal('16.00'))
```

### Vacation (Exception Only)
```python
# DEFAULT: Use-it-or-lose-it (NO carryover)
# EXCEPTION: Employee requests carryover → Manager approves
# Approved carryover stored in CarryoverRequest, NOT balance field

# Carryover is applied from previous year's balance when used:
# - Check CarryoverRequest for approved hours
# - Deduct from previous year first (hours_used tracking)
# - Then current year
```

### Personal (No Carryover)
```python
# ALWAYS use-it-or-lose-it
# No exceptions, no carryover mechanism
```

---

## 7. Year-End Processing Order

```python
# Transaction order in YearEndService.process_year_transition():
1. Create new year balances for all active employees
2. Auto-carryover sick leave (up to cap)
3. Auto-carryover Chicago leave (up to 16 hrs)
4. Apply approved vacation exception carryover (from CarryoverRequest)
5. Generate federal holidays for new year
6. Purge old reports (optional)
```

**File**: `src/services/year_end_service.py`

---

## 8. Validation Rules

### Hard Blocks (Raise ValueError)
```python
# These MUST be enforced - request cannot be created:
- start_date > 7 days in the past
- start_date > end_date
- Request > 5 years in future
- Overlapping request exists (same user, same dates)
- Sick hours requested > available sick balance
- Personal hours requested > available personal balance
```

### Soft Warnings (Allow with Warning)
```python
# These show warning but DO NOT block submission:
- Vacation hours requested > available vacation balance
  # Reason: Manager discretion - they may approve anyway
- Chicago leave hours > available
  # Same manager discretion logic
```

---

## 9. Balance Service Patterns

### Getting/Creating Balance
```python
# Always use get_or_create_balance to ensure balance exists
balance = balance_service.get_or_create_balance(user_id, year)

# Year is extracted from request start_date
year = request.start_date.year
```

### Adjusting Balances
```python
# For pending requests (employee submitted):
balance_service.adjust_vacation_used(balance.id, days, is_pending=True)

# For approved requests (moving pending to used):
balance_service.adjust_vacation_used(balance.id, days, is_pending=False)
balance_service.adjust_vacation_used(balance.id, -days, is_pending=True)  # Remove pending
```

---

## 10. Chicago Leave Specifics

### Eligibility Check
```python
def is_chicago_employee(user: User) -> bool:
    return (
        user.location_city and
        user.location_city.lower() == 'chicago'
    )
```

### Feature Toggle
```python
# System setting controls feature availability
setting = db.query(SystemSetting).filter(
    SystemSetting.key == 'chicago.safe_leave_enabled'
).first()

is_enabled = setting and setting.bool_value  # Uses @property
```

### Balance Fields
```python
# PTOBalance model fields for Chicago:
chicago_paid_leave_total      # 40 hrs annual allocation
chicago_paid_leave_used       # Hours consumed
chicago_paid_leave_pending    # Hours awaiting approval
chicago_paid_leave_carryover  # Hours from previous year (max 16)
```

---

## 11. Common Pitfalls

### 1. Year Boundary Issues
```python
# WRONG: Assuming request year matches current year
year = date.today().year

# RIGHT: Use request's start_date year
year = request.start_date.year
```

### 2. Decimal Precision
```python
# WRONG: Using float
hours = 8.0 * days

# RIGHT: Using Decimal
hours = Decimal('8') * Decimal(str(days))
```

### 3. Pending vs Used
```python
# Employee request: Add to PENDING (not used)
# After approval: Move PENDING to USED

# Manager/Trusted request: Add directly to USED (skip pending)
```

### 4. Carryover Separation
```python
# WRONG: Adding carryover to total
balance.vacation_total += carryover_hours

# RIGHT: Keep separate fields
balance.vacation_carryover = carryover_hours
# Formula handles: total + carryover - used - pending
```

---

## 12. Audit Trail Requirements

All PTO-affecting actions MUST be logged via AuditService:

```python
from src.services.audit_service import AuditService

# After any balance change:
AuditService.log_pto_approve(db, user_id, username, request_id, ...)
AuditService.log_pto_deny(db, user_id, username, request_id, ...)
AuditService.log_pto_cancel(db, user_id, username, request_id, ...)
AuditService.log_balance_adjustment(db, user_id, username, ...)
```

---

## 13. Testing Patterns

### Balance Test Setup
```python
@pytest.fixture
def test_balance(db, test_employee):
    balance = PTOBalance(
        user_id=test_employee.id,
        year=date.today().year,  # Match request year!
        vacation_total=Decimal("80.00"),
        vacation_used=Decimal("0.00"),
        vacation_pending=Decimal("0.00"),
        # ... other fields
    )
    db.add(balance)
    db.commit()
    return balance
```

### Request Date Safety
```python
# WRONG: May cross year boundary near Dec 31
start_date = date.today() + timedelta(days=14)

# RIGHT: Stay within current year
start_date = date.today() + timedelta(days=1)
```
