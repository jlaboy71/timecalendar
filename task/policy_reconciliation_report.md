# Policy Reconciliation Report

**Generated**: December 19, 2024
**Status**: ALL STEPS COMPLETE

---

## 1. Date Validation - Current Implementation

### Calendar UI (`nicegui_app/pages/calendar.py`)

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 1039-1041 | `show_quick_request_popup()` | Blocks ALL past dates: `if click_date < today` | Allow 7-day backdating | **DISCREPANCY** |

**Code:**
```python
# Line 1039-1041
if click_date < today:
    show_warning_dialog('Past Date', 'Cannot request time off for past dates. Please select a future date.')
    return
```

**Issue**: Calendar is MORE restrictive than policy. Users cannot click past dates at all, even within the 7-day window.

---

### Request Form (`nicegui_app/pages/request_form.py`)

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 1436-1446 | `submit_request()` | Allows 7-day backdating with message | Allow 7-day backdating | **CORRECT** |

**Code:**
```python
# Line 1436-1446
days_until_start = (start_date - date.today()).days
if days_until_start < -7:
    show_warning_dialog(
        'Date Too Far Back',
        'Requests for dates more than 7 days ago require manager assistance. '
        'Please contact your manager to submit this request on your behalf.'
    )
```

**Status**: Correctly implements 7-day backdating limit.

---

### PTO Service (`src/services/pto_service.py`) - PROTECTED

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 69-73 | `create_request()` | Allows 7-day backdating | Allow 7-day backdating | **CORRECT** |

**Code:**
```python
# Line 69-73
min_allowed_date = datetime.now().date() - timedelta(days=7)
if request_data.start_date < min_allowed_date:
    raise ValueError("Start date cannot be more than 7 days in the past")
```

**Status**: Correctly implements 7-day backdating limit at API level.

---

## 2. Auto-Approval Rules - Current Implementation

### PTO Service (`src/services/pto_service.py`) - PROTECTED

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 26-29 | Constants | `TRUSTED_AUTO_APPROVE_TYPES`, `ALWAYS_REQUIRES_APPROVAL` defined | Correct types | **CORRECT** |
| 179-203 | `create_request()` | Auto-approves for managers/trusted + trusted types | Add backdating exception | **DISCREPANCY** |

**Current Auto-Approve Logic (Lines 179-199):**
```python
pto_type_lower = request_data.pto_type.lower()
is_auto_approve = False
auto_approve_reason = None

# Manager/Admin/Superadmin: auto-approve standard PTO types only
if user.role in ['manager', 'admin', 'superadmin']:
    if pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
        is_auto_approve = True
        auto_approve_reason = f"Self-approved by {user.role}"

# Trusted Employee: auto-approve ONLY for vacation, sick, personal
elif user.is_trusted and pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
    is_auto_approve = True
    auto_approve_reason = "Auto-approved (trusted employee)"

# VACATION ROLLOVER: Never auto-approve
if is_vacation_rollover:
    is_auto_approve = False
    auto_approve_reason = None
```

**Issue**: NO check for backdated requests. Managers/trusted employees can auto-approve their own backdated requests.

**Required Addition:**
```python
# BACKDATED REQUESTS: Never auto-approve (start_date < today)
if request_data.start_date < datetime.now().date():
    is_auto_approve = False
    auto_approve_reason = None
```

---

## 3. Balance Validation - Current Implementation

### Request Form (`nicegui_app/pages/request_form.py`)

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 1049-1051 | `update_warning()` | Hard cap for sick, personal, chicago_leave | Hard cap for these types | **CORRECT** |
| 1072-1080 | `update_warning()` | Warning only for vacation | Warning only for vacation | **CORRECT** |

**Code (Lines 1049-1051):**
```python
hard_cap_types = ['chicago_leave', 'sick', 'personal']
should_block = pto_type.value in hard_cap_types
```

**Status**: Correctly implements hard caps for sick/personal/chicago_leave, warning-only for vacation.

---

### PTO Service (`src/services/pto_service.py`) - PROTECTED

| Line | Function | Current Behavior | Policy Requirement | Status |
|------|----------|------------------|-------------------|--------|
| 209-225 | `create_request()` | Hard block for sick/personal | Hard block for these types | **CORRECT** |
| 167-170 | Comment | Vacation is manager discretion | Warning only for vacation | **CORRECT** |

**Status**: Correctly implements balance validation at API level.

---

## 4. Discrepancy Summary

| Area | Discrepancy | Severity | Fix Required |
|------|-------------|----------|--------------|
| Calendar UI - Past Dates | Blocks ALL past dates (should allow 7-day window) | **HIGH** | Update calendar.py line 1039 |
| Auto-Approve - Backdating | No check for backdated requests | **MEDIUM** | Add backdating check in pto_service.py |

---

## 5. Constants Location

Currently defined in `src/services/pto_service.py` (lines 26-29):
```python
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}
```

**Recommendation**: Move to new `src/services/policy_engine.py` as single source of truth.

---

## 6. Files to Modify

| File | Change Type | Protected? |
|------|-------------|------------|
| `src/services/policy_engine.py` | NEW FILE | No |
| `nicegui_app/pages/admin_policy_viewer.py` | NEW FILE | No |
| `nicegui_app/pages/calendar.py` | Update line 1039 | No |
| `nicegui_app/pages/request_form.py` | Add PolicyEngine call | No |
| `src/services/pto_service.py` | Add backdating check to auto-approve | **YES** |
| `nicegui_app/pages/admin_system.py` | Add link to policy viewer | No |
| `nicegui_app/main.py` | Register new route | No |
| `tests/test_policy_engine.py` | NEW FILE | No |

---

## 7. Impact Assessment

**Low Risk Changes:**
- Creating new `policy_engine.py` (additive)
- Creating new `admin_policy_viewer.py` (additive)
- Updating calendar.py to use PolicyEngine (behavior change: allows 7-day backdating)
- Adding link in admin_system.py (additive)

**Medium Risk Changes:**
- Updating pto_service.py auto-approve logic (protected file, but minimal change)

**No Changes Required:**
- Balance formulas in pto_balance.py
- Vacation tier calculations
- Carryover logic
- Year-end processing

---

## 8. Changes Made

### New Files Created
| File | Purpose |
|------|---------|
| `src/services/policy_engine.py` | Centralized policy validation engine |
| `nicegui_app/pages/admin_policy_viewer.py` | Policy & Formula Reference UI |
| `tests/test_policy_engine.py` | 37 comprehensive tests |

### Files Modified
| File | Change |
|------|--------|
| `nicegui_app/pages/calendar.py` | Updated line 1034-1047 to use PolicyEngine for date validation |
| `nicegui_app/pages/request_form.py` | Updated line 1436-1448 to use PolicyEngine for date validation |
| `src/services/pto_service.py` | Added backdating check at line 205-213 (auto-approve logic) |
| `nicegui_app/main.py` | Added import and route for `/admin/policy` |
| `nicegui_app/pages/admin_system.py` | Added "Policy Reference" to navigation hub |

### Test Results
```
37 passed in 0.19s
```

All tests cover:
- Date validation (backdating, future limits)
- Auto-approve determination (roles, trust, backdating exception)
- Balance validation (hard cap vs soft cap)
- Policy documentation structure
- Calendar/Request Form consistency

---

## 9. Review Summary

**Problem Solved**: Date validation and auto-approval logic was inconsistent across Calendar UI (blocked all past dates) and Request Form (allowed 7-day backdating). The PolicyEngine now provides a single source of truth.

**Key Behavior Changes**:
1. Calendar UI now allows clicking dates up to 7 days in the past (with approval notice)
2. Backdated requests NEVER auto-approve, even for managers/trusted employees
3. Policy documentation is now viewable at System Administration > Policy Reference

**Protected Files**: Only the `pto_service.py` auto-approve logic was modified, per the approved plan. No balance formulas, vacation tiers, or carryover logic were changed.

---

**END OF REPORT**
