# Protected Business Logic - DO NOT MODIFY WITHOUT USER CONSENT

## CRITICAL PROTECTION RULE

**Before modifying ANY of the following files or functions, Claude MUST:**
1. State: "This file/function contains protected business logic. Do I have your explicit permission to modify it?"
2. Wait for user to say "yes" or explicitly approve
3. Explain EXACTLY what change will be made and WHY
4. Only then proceed with the change

## Protected Files

### Balance Calculations
- `src/models/pto_balance.py` - Balance model and `*_available` properties
- `src/services/balance_service.py` - All balance adjustment methods

### PTO Request Logic
- `src/services/pto_service.py` - Request creation, approval, denial, cancellation
  - `create_request()` - Balance deduction on submit
  - `approve_request()` - Move pending to used
  - `deny_request()` - Return pending
  - `cancel_request()` - Return pending/used
  - `_apply_vacation_with_carryover()` - Carryover deduction logic

### Year-End Processing
- `src/services/year_end_service.py` - Year-end balance creation and carryover

### Policy & Accrual
- `src/services/accrual_service.py` - Vacation tier calculations
- `src/services/leave_policy_service.py` - Location-based policy resolution

## Protected Formulas

These formulas are CANONICAL and must not be changed:

```
vacation_available = vacation_total + vacation_carryover - vacation_used - vacation_pending
sick_available = sick_total + sick_carryover - sick_used - sick_pending
personal_available = personal_total + personal_carryover - personal_used - personal_pending
chicago_paid_leave_available = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

## Why This Protection Exists

Balance calculations are the core of this application. Incorrect math means:
- Employees see wrong balances
- Managers approve based on wrong data
- Year-end processing carries over wrong amounts
- Audit trail becomes unreliable

Any change to these formulas requires careful review and explicit approval.

## CRITICAL: Hire Date & Balance Auto-Calculation

### Automatic Balance Calculation (IMPLEMENTED)

**The following is now handled AUTOMATICALLY by `UserService`:**

1. **User Creation** (`create_user()`):
   - PTO balance is created with proper tenure-based vacation allocation
   - Chicago Paid Leave is set for Chicago employees

2. **Hire Date Changes** (`update_user()`):
   - When `hire_date` changes, balance is automatically recalculated
   - When `location_city` changes, Chicago Leave is recalculated

**Location:** `src/services/user_service.py`
- `_calculate_vacation_days()` - Calculates vacation days based on tenure
- `_update_or_create_balance()` - Creates/updates balance with proper allocations

### Vacation Tiers (MUST match year_end_service.py)
| Years of Service | Vacation Days | Hours |
|-----------------|---------------|-------|
| 10+ years | 20 days | 160 hours |
| 5-9 years | 15 days | 120 hours |
| 2-4 years | 12 days | 96 hours |
| 0-1 years | 10 days | 80 hours |

Plus: Sick = 5 days (40 hours), Personal = 2 days (16 hours)

### DO NOT Bypass UserService

**CRITICAL**: When modifying hire dates, ALWAYS use `UserService.update_user()`.

```python
# CORRECT - Uses UserService, balance auto-updates
user_service = UserService(db)
update_data = UserUpdate(hire_date=new_date)
user_service.update_user(user_id, update_data)

# WRONG - Direct modification bypasses balance recalculation!
user.hire_date = new_date
db.commit()  # Balance NOT updated!
```

### For Scripts Modifying Multiple Users
If you need to bypass UserService for performance (bulk updates), call `_update_or_create_balance()` manually:

```python
from src.services.user_service import UserService

user_service = UserService(db)
for user in users:
    user.hire_date = new_date
    user_service._update_or_create_balance(user)
db.commit()
```

### Reference Script
See `scripts/update_pto_users.py` for the correct bulk update pattern.
