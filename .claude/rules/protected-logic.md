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
