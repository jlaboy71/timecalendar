# TJM Time Calendar - Formula & Business Logic Reference

**Document Version**: 1.0
**Last Updated**: December 19, 2024
**Status**: PROTECTED - Changes require explicit user approval

---

## Table of Contents

1. [Core Balance Formulas](#1-core-balance-formulas)
2. [Vacation Tier System](#2-vacation-tier-system)
3. [PTO Request Lifecycle](#3-pto-request-lifecycle)
4. [Carryover Rules](#4-carryover-rules)
5. [Location-Based Policies](#5-location-based-policies)
6. [Auto-Approve Rules](#6-auto-approve-rules)
7. [Year-End Processing](#7-year-end-processing)
8. [Balance Adjustment Rules](#8-balance-adjustment-rules)
9. [Validation Rules](#9-validation-rules)
10. [What-If Scenarios](#10-what-if-scenarios)

---

## 1. Core Balance Formulas

### Primary Balance Calculations (PROTECTED)

These formulas are canonical and stored in `src/models/pto_balance.py`:

```
VACATION_AVAILABLE = vacation_total + vacation_carryover - vacation_used - vacation_pending
SICK_AVAILABLE     = sick_total + sick_carryover - sick_used - sick_pending
PERSONAL_AVAILABLE = personal_total + personal_carryover - personal_used - personal_pending
CHICAGO_LEAVE_AVAILABLE = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

### Storage Units

| Field Type | Unit | Conversion |
|------------|------|------------|
| `*_total` | Hours | 8 hours = 1 day |
| `*_used` | Hours | 8 hours = 1 day |
| `*_pending` | Hours | 8 hours = 1 day |
| `*_carryover` | Hours | 8 hours = 1 day |
| `total_days` (request) | Days | Direct |

### Display Formula

```
Days Available = AVAILABLE_HOURS / 8
```

---

## 2. Vacation Tier System

### Tenure-Based Allocation (PROTECTED)

Stored in `vacation_accrual_tier` table, applied via `src/services/accrual_service.py`:

| Years of Service | Annual Days | Annual Hours |
|-----------------|-------------|--------------|
| 0-1 years       | 10 days     | 80 hours     |
| 2-4 years       | 12 days     | 96 hours     |
| 5-9 years       | 15 days     | 120 hours    |
| 10+ years       | 20 days     | 160 hours    |

### Calculation Formula

```python
years_of_service = (today - hire_date).days // 365
vacation_hours = tier.annual_days * 8
```

### Front-Load Policy

- Full year allocation given on January 1st
- NO monthly accrual - employees get entire balance upfront
- Year-end processing creates new year balances automatically

---

## 3. PTO Request Lifecycle

### Status Transitions (PROTECTED)

```
PENDING  -->  APPROVED  (manager/admin approves)
PENDING  -->  DENIED    (manager/admin denies)
PENDING  -->  CANCELLED (employee cancels)
APPROVED -->  CANCELLED (with manager approval for approved requests)
```

### Balance Impact by Status

| Action | Balance Effect |
|--------|----------------|
| Submit (employee) | `pending += hours` |
| Submit (manager/admin/trusted) | `used += hours` (auto-approve) |
| Approve | `pending -= hours`, `used += hours` |
| Deny | `pending -= hours` |
| Cancel (pending) | `pending -= hours` |
| Cancel (approved) | `used -= hours` |

### Key Code Locations

- Submit: `src/services/pto_service.py:create_request()`
- Approve: `src/services/pto_service.py:approve_request()`
- Deny: `src/services/pto_service.py:deny_request()`
- Cancel: `src/services/pto_service.py:cancel_request()`

---

## 4. Carryover Rules

### By Leave Type (PROTECTED)

| Leave Type | Carryover Rule | Max Carryover |
|------------|----------------|---------------|
| **Vacation** | NO auto-carryover, exception request only | Manager discretion |
| **Sick** | AUTO-carryover (legally required) | Policy-defined (e.g., 80hrs for Chicago) |
| **Personal** | NO carryover (use-it-or-lose-it) | 0 hours |
| **Chicago Paid Leave** | AUTO-carryover | 16 hours (2 days) max |

### Vacation Carryover Exception Process

1. Employee submits `CarryoverRequest` before year-end
2. Manager reviews and approves/denies
3. If approved: hours tracked in `CarryoverRequest.hours_approved`
4. When used: Deducted from FROM year's balance, NOT the new year

```python
# Vacation carryover deduction logic (pto_service.py:_apply_vacation_with_carryover)
if carryover_request.hours_remaining > 0:
    hours_from_carryover = min(carryover.hours_remaining, hours_to_apply)
    prev_balance.vacation_used += hours_from_carryover  # Deduct from FROM year
```

### Sick Auto-Carryover Formula

```python
# year_end_service.py:_auto_carryover_sick_no_commit
unused_sick = sick_total + sick_carryover - sick_used
carryover = min(unused_sick, max_carryover_hours)  # Capped by policy
new_balance.sick_carryover = carryover
```

### Chicago Leave Auto-Carryover Formula

```python
# year_end_service.py:_auto_carryover_chicago_leave_no_commit
CHICAGO_LEAVE_CARRYOVER_MAX = 16  # hours (per ordinance)
unused = total + carryover - used
carryover = min(unused, CHICAGO_LEAVE_CARRYOVER_MAX)
new_balance.chicago_paid_leave_carryover = carryover
```

---

## 5. Location-Based Policies

### Policy Resolution Order (PROTECTED)

```python
# accrual_service.py:get_policy_for_employee
1. City-specific  (e.g., Chicago, IL)  -> Most specific
2. State-specific (e.g., IL)           -> State fallback
3. Default        (NULL location)      -> System default
```

### Chicago-Specific Rules

**Chicago Paid Leave** (per city ordinance):
- Annual allocation: 40 hours (5 days)
- Auto-carryover: Up to 16 hours max
- Eligibility: `user.location_city == 'Chicago'`
- Feature toggle: `system_setting.chicago.safe_leave_enabled`

```python
# balance_service.py:_is_chicago_leave_applicable
def _is_chicago_leave_applicable(self, user_id: int) -> bool:
    # 1. Check feature enabled
    # 2. Check user.location_city.lower() == 'chicago'
    return feature_enabled and is_chicago_employee
```

**Chicago Sick Leave**:
- Uses standard `sick_*` fields (NOT a separate bank)
- Higher carryover max (80 hours vs default)
- Same as company-wide sick leave, just different carryover limit

### State-Specific Examples

| State | Sick Carryover Max | Other Rules |
|-------|-------------------|-------------|
| IL (Chicago) | 80 hours | Chicago Paid Leave separate |
| IL (other) | 40 hours | Standard |
| Default | 40 hours | Standard |

---

## 6. Auto-Approve Rules

### Who Auto-Approves (PROTECTED)

```python
# pto_service.py:create_request (lines 179-199)
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}

# Auto-approve if:
if user.role in ['manager', 'admin', 'superadmin']:
    if pto_type in TRUSTED_AUTO_APPROVE_TYPES:
        is_auto_approve = True

elif user.is_trusted and pto_type in TRUSTED_AUTO_APPROVE_TYPES:
    is_auto_approve = True

# Exception: Vacation rollover NEVER auto-approves
if is_vacation_rollover:
    is_auto_approve = False
```

### Auto-Approve Balance Handling

```python
# Auto-approved requests go directly to 'used' (no pending)
if is_auto_approve:
    balance.vacation_used += hours  # NOT vacation_pending
else:
    balance.vacation_pending += hours  # Regular employee
```

---

## 7. Year-End Processing

### Execution Trigger

- Runs automatically on first app access of new year
- OR manually via System Admin

### Processing Steps (PROTECTED)

```python
# year_end_service.py:run_year_end_processing
1. Create new year balances (vacation_total based on tenure tier)
2. Auto-carryover Sick (up to policy max) - REQUIRED BY LAW
3. Auto-carryover Chicago Paid Leave (up to 16hrs) - REQUIRED BY ORDINANCE
4. Apply approved Vacation exception carryovers - RARE, MANAGER APPROVED
5. Generate federal holidays
6. Update status record
```

### New Year Balance Initialization

```python
new_balance = PTOBalance(
    vacation_total=calculate_vacation_hours(user),  # Based on tenure
    vacation_used=0,
    vacation_pending=0,
    vacation_carryover=0,  # NOT auto-carried
    sick_total=40,         # Standard 5 days
    sick_carryover=carried_over_sick,  # AUTO-carried
    personal_total=16,     # 2 days
    personal_carryover=0,  # NEVER carries over
    chicago_paid_leave_total=40 if chicago_eligible else 0,
    chicago_paid_leave_carryover=carried_over_chicago  # AUTO-carried
)
```

---

## 8. Balance Adjustment Rules

### Submit Request

| PTO Type | Employee | Manager/Admin/Trusted |
|----------|----------|----------------------|
| Vacation | `pending += hours` | `used += hours` |
| Sick | `pending += hours` | `used += hours` |
| Personal | `pending += hours` | `used += hours` |
| Chicago Leave | `pending += hours` | `used += hours` |
| Other | No balance tracking | No balance tracking |

### Approve Request

```python
# balance_service.py:move_pending_to_used
pending -= hours
used += hours
```

### Deny/Cancel Request

```python
# balance_service.py:remove_pending
pending -= hours
# (hours returned to available)
```

### Cancel Approved Request

```python
# For approved requests being cancelled:
used -= hours
# (hours returned to available)
```

---

## 9. Validation Rules

### Request Date Validation (PROTECTED)

```python
# pto_service.py:create_request
# Start date rules:
- Cannot be more than 7 days in the past
- Cannot be a weekend
- Cannot be a holiday

# End date rules:
- Must be >= start_date
- Cannot be a weekend
- Cannot be a holiday

# Future limit:
- Max 5 years in advance
```

### Balance Validation

| Leave Type | Hard Block? | Details |
|------------|-------------|---------|
| Vacation | NO | Warning only, manager discretion |
| Sick | YES | Cannot exceed available |
| Personal | YES | Cannot exceed available |
| Chicago Leave | YES | Cannot exceed available |

### Working Days Calculation

```python
# utils/working_days.py:count_working_days
total_days = 0
for date in range(start, end):
    if not is_weekend(date) and not is_holiday(date):
        total_days += 1
return total_days
```

---

## 10. What-If Scenarios

### Scenario: Employee cancels pending vacation request

**Expected Behavior**:
1. `request.status` -> 'cancelled'
2. `vacation_pending` -= request hours
3. `vacation_available` increases by same amount
4. Audit log created

**If Bug Exists**: Pending not cleared, available shows wrong value

---

### Scenario: Manager approves vacation that exceeds balance

**Expected Behavior**:
1. Warning shown but NOT blocked (vacation is manager discretion)
2. `vacation_pending` -> 0 for this request
3. `vacation_used` += request hours
4. `vacation_available` may go negative (allowed for vacation)

---

### Scenario: Employee in Chicago submits sick leave

**Expected Behavior**:
1. Uses standard `sick_*` fields (NOT chicago_paid_leave)
2. Policy lookup finds Chicago policy (80hr carryover max)
3. Balance validation uses sick_available formula
4. At year-end: Up to 80hrs carries over (vs 40hrs default)

---

### Scenario: December vacation rollover request

**Expected Behavior**:
1. Employee requests January vacation in December
2. System detects: `year > current_year && current_month == 12 && request.month == 1`
3. `carryover_from_year` set to current year (e.g., 2025)
4. NEVER auto-approves (even for managers)
5. When approved: Deducts from 2025 balance, not 2026

---

### Scenario: Year-end with unused Chicago Paid Leave

**Expected Behavior**:
1. Employee has 24 hours unused Chicago Leave
2. System calculates: `carryover = min(24, 16) = 16`
3. 8 hours lost (exceeds 16hr cap)
4. New year: `chicago_paid_leave_total=40, chicago_paid_leave_carryover=16`
5. Total available: 56 hours (7 days)

---

### Scenario: Trusted employee submits sick leave

**Expected Behavior**:
1. `user.is_trusted == True`
2. PTO type is 'sick' (in TRUSTED_AUTO_APPROVE_TYPES)
3. Auto-approve triggers
4. `sick_used` += hours (NOT sick_pending)
5. Status immediately 'approved'
6. Manager notified but no approval needed

---

## Appendix A: Constants Reference

```python
# From src/constants.py and src/services/balance_service.py

# Chicago Leave
CHICAGO_PAID_LEAVE_ANNUAL_MAX = 40  # hours (5 days)
CHICAGO_LEAVE_CARRYOVER_MAX = 16    # hours (2 days)

# PTO Types
ACCRUING_TYPES = ['vacation', 'sick', 'personal']
NON_ACCRUING_TYPES = ['bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh']

# Auto-approve
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}

# Standard allocations (hours)
SICK_ANNUAL = 40     # 5 days
PERSONAL_ANNUAL = 16 # 2 days
```

## Appendix B: File Reference

| Logic Area | Primary File | Protected? |
|------------|--------------|------------|
| Balance formulas | `src/models/pto_balance.py` | YES |
| Balance adjustments | `src/services/balance_service.py` | YES |
| Request lifecycle | `src/services/pto_service.py` | YES |
| Year-end processing | `src/services/year_end_service.py` | YES |
| Vacation tiers | `src/services/accrual_service.py` | YES |
| Policy resolution | `src/services/accrual_service.py` | YES |
| Constants | `src/constants.py` | YES |

---

## Change Log

| Date | Change | Approved By |
|------|--------|-------------|
| 2024-12-19 | Document created | Initial |

---

**END OF DOCUMENT**
