# PTO Central - Final Pre-MCP/RAG Scan Report

**Version:** 1.0
**Date:** 2025-12-22
**Status:** HOLD - Critical issues must be resolved before MCP/RAG activation
**Auditor:** Claude Code (Phase 1 READ-ONLY verification)

---

## 1. Executive Summary

### Verdict: **HOLD**

The PTO Central codebase has strong foundational policy architecture including:
- Well-documented balance formulas in `pto_balance.py`
- A centralized `PolicyEngine` for validation rules
- Consistent status transitions in `pto_service.py`
- Proper year-end processing with atomic transactions

However, **critical policy parity violations** were discovered that must be resolved before MCP/RAG activation.

### Critical Issues (MUST FIX)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Duplicate day-counting function** | CRITICAL | `request_form.py:33-69` has `count_business_days()` instead of using `src/utils/working_days.py:count_working_days()` |
| 2 | **Hardcoded policy constants** | HIGH | `request_form.py:1059` hardcodes `hard_cap_types` instead of using `PolicyEngine.HARD_CAP_TYPES` |

### Moderate Issues

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 3 | PolicyEngine not used for balance validation | MEDIUM | `request_form.py` implements its own balance warning logic |
| 4 | `pto_service.py` has its own `TRUSTED_AUTO_APPROVE_TYPES` constant | MEDIUM | Should reference `PolicyEngine` |

---

## 2. Balance Formula Verification

### Status: **PASS**

**Source of Truth:** `src/models/pto_balance.py` (lines 165-183)

```python
vacation_available = vacation_total + vacation_carryover - vacation_used - vacation_pending
sick_available = sick_total + sick_carryover - sick_used - sick_pending
personal_available = personal_total + personal_carryover - personal_used - personal_pending
chicago_paid_leave_available = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

**Verification:**
- Formulas match `task/formulalogic.md`
- `@property` decorators ensure calculated values
- All fields use `Decimal` type for precision
- Chicago Leave 16-hour carryover cap documented in model comments

**No issues found.**

---

## 3. Status Transition Verification

### Status: **PASS**

**Source of Truth:** `src/services/pto_service.py`

| Transition | Method | Balance Impact | Verified |
|------------|--------|----------------|----------|
| Submit (employee) | `create_request()` | pending += hours | Yes |
| Submit (trusted/manager) | `create_request()` | used += hours (auto-approve) | Yes |
| Approve | `approve_request()` | pending -= hours, used += hours | Yes |
| Deny | `deny_request()` | pending -= hours | Yes |
| Cancel (pending) | `cancel_request()` | pending -= hours | Yes |

**Verification:**
- All transitions use atomic database transactions
- Rollback on failure prevents partial state
- Vacation rollover uses `carryover_from_year` correctly

**No issues found.**

---

## 4. Chargeable Date Logic Verification

### Status: **CRITICAL DEFECT**

**Expected:** Single source of truth for working day calculation
**Actual:** **TWO implementations exist**

#### Implementation 1: `src/utils/working_days.py:count_working_days()` (CANONICAL)
- Used by: `pto_service.py` (service layer)
- Excludes: Weekends, holidays (except Early Close)
- Database session handling: Correct

#### Implementation 2: `nicegui_app/pages/request_form.py:count_business_days()` (DUPLICATE)
- Used by: UI request form only
- Logic: Appears identical but **not guaranteed to stay in sync**
- Lines: 33-69

**Risk:** If either implementation is updated without the other, day calculations will diverge between UI and API.

**Finding:**
```
CRITICAL: Duplicate chargeable date logic detected
Location: request_form.py:33-69
Impact: UI may calculate different working days than service layer
Fix: Remove duplicate and import from src/utils/working_days
```

---

## 5. PTO Type Enforcement Matrix

### Status: **PASS** (with parity concern)

Extracted from code (not assumptions):

| PTO Type | Hard Cap (Block) | Soft Cap (Warn) | Manager Override | Trusted Auto-Approve |
|----------|------------------|-----------------|------------------|----------------------|
| Vacation | No | Yes | Yes | Yes |
| Sick | **Yes** | No | **No** | Yes |
| Personal | **Yes** | No | **No** | Yes |
| Chicago Leave | **Yes** | No | **No** | No |
| Bereavement | N/A | N/A | Required | No |
| FMLA | N/A | N/A | Required | No |
| Jury Duty | N/A | N/A | Required | No |
| WFH | N/A | N/A | Required | No |

**Verification:**
- Service layer: `pto_service.py:222-235` (create), `pto_service.py:623-649` (approve)
- UI layer: `request_form.py:1059-1091`
- PolicyEngine: `policy_engine.py:30-31` defines `HARD_CAP_TYPES` and `SOFT_CAP_TYPES`

**Parity Issue:** `request_form.py:1059` hardcodes `hard_cap_types = ['chicago_leave', 'sick', 'personal']` instead of using `PolicyEngine.HARD_CAP_TYPES`. This creates a maintenance risk.

---

## 6. Warning vs Blocking Rules

### Status: **PASS** (behavior correct, parity concern)

| Type | UI Behavior | API Behavior | Match |
|------|-------------|--------------|-------|
| Sick over balance | Block submit | Reject request | Yes |
| Personal over balance | Block submit | Reject request | Yes |
| Chicago Leave over balance | Block submit | Reject request | Yes |
| Vacation over balance | Warning only | Allow (manager discretion) | Yes |

**Note:** Both surfaces implement the same logic, but using different code paths. Recommend centralizing in `PolicyEngine.validate_balance()`.

---

## 7. Backdating and Future Request Rules

### Status: **PASS**

**Source of Truth:** `src/services/policy_engine.py`

| Rule | Value | Enforced In |
|------|-------|-------------|
| Backdate window | 7 calendar days | `PolicyEngine.BACKDATE_WINDOW_DAYS` |
| Future limit | 5 years | `PolicyEngine.FUTURE_LIMIT_YEARS` |
| Timezone | America/Chicago | `PolicyEngine.TIMEZONE` |

**Verification:**
- `request_form.py:1446-1450` uses `PolicyEngine.validate_request_dates()`
- `calendar.py:1039-1045` uses `PolicyEngine.validate_request_dates()`
- `pto_service.py:71-73` also validates (redundant but consistent)

**Minor Issue:** `pto_service.py` has its own 7-day check that doesn't reference `PolicyEngine.BACKDATE_WINDOW_DAYS`. If the constant changes in PolicyEngine, the service won't update automatically.

---

## 8. Trusted Employee Automation

### Status: **PASS**

**Source of Truth:** `src/services/policy_engine.py:26-27`

```python
TRUSTED_AUTO_APPROVE_TYPES = frozenset({'vacation', 'sick', 'personal'})
ALWAYS_REQUIRES_APPROVAL = frozenset({'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh', 'chicago_leave'})
```

**Verification:**
- `pto_service.py:26-29` defines same constants (duplicate)
- Auto-approval logic correctly checks user role and trust status
- Vacation rollover correctly bypasses auto-approval
- Backdated requests correctly bypass auto-approval

**Parity Issue:** `pto_service.py` duplicates `TRUSTED_AUTO_APPROVE_TYPES` instead of importing from `PolicyEngine`.

---

## 9. WFH Day Swap Verification

### Status: **PASS**

**Confirmed:**
- No balance impact (no hours deducted)
- Peer-to-peer only (no manager approval)
- Proper audit logging via `AuditService`
- Weekly limit enforced (one swap per user per week)
- Holiday validation (swaps blocked on full holidays)

**No issues found.**

---

## 10. Year-End Processing Verification

### Status: **PASS**

**Source of Truth:** `src/services/year_end_service.py`

| Step | Verified |
|------|----------|
| Create new year balances | Yes |
| Tenure-based vacation allocation | Yes |
| Auto-carryover Sick (up to policy max) | Yes |
| Auto-carryover Chicago Leave (up to 16 hrs) | Yes |
| Vacation exception carryover as BONUS | Yes |
| Personal - NO carryover | Yes |
| Federal holiday generation | Yes |
| Atomic transaction (rollback on failure) | Yes |

**No issues found.**

---

## 11. Cross-Surface Policy Parity Matrix

| Policy Rule | Service Layer | UI (Request Form) | UI (Calendar) | Match |
|-------------|---------------|-------------------|---------------|-------|
| Working day count | `working_days.py` | **DUPLICATE** | N/A | **NO** |
| Hard cap types | Inline in code | Inline in code | N/A | Yes (but fragile) |
| Backdate 7-day rule | Inline + PolicyEngine | PolicyEngine | PolicyEngine | Yes |
| Future 5-year limit | Inline + PolicyEngine | PolicyEngine | PolicyEngine | Yes |
| Auto-approve logic | Inline in code | N/A | N/A | N/A |
| Balance formulas | `pto_balance.py` | Display only | N/A | Yes |

### Parity Violations

1. **Chargeable date logic** - Two implementations
2. **Hard cap constants** - Defined in multiple places
3. **Auto-approve types** - Defined in `pto_service.py` AND `policy_engine.py`

---

## 12. Known Defect Family Scan

| Defect Pattern | Present? | Location | Severity |
|----------------|----------|----------|----------|
| Holiday exclusion claimed but not applied | No | - | - |
| Sick/Personal oversubscription allowed | No | - | - |
| Modal acknowledgment loops | No | - | - |
| Multiple day-counting functions | **YES** | `request_form.py:33` | CRITICAL |
| Unit mismatches (hours vs days) | No | - | - |
| UI blocking without API enforcement | No | - | - |
| API enforcement without UI visibility | No | - | - |
| Duplicate policy constants | **YES** | Multiple files | MEDIUM |

---

## 13. Deterministic Time Rules

| Rule | Value | Source |
|------|-------|--------|
| Server timezone | America/Chicago | `PolicyEngine.TIMEZONE` |
| "Today" definition | `datetime.now().date()` | All services |
| Time freeze for tests | Not implemented | Recommend adding |

**Recommendation:** Consider using a `TimeProvider` abstraction for testability.

---

## 14. Minimal Fix Plan (NO CODE IN THIS DOCUMENT)

### Priority 1: CRITICAL (Must fix before Phase 2)

**Fix 1: Remove duplicate day-counting function**
- File: `nicegui_app/pages/request_form.py`
- Action: Delete lines 33-69 (`count_business_days` function)
- Replace usages with: `from src.utils.working_days import count_working_days`
- Estimated scope: Single file change, ~5 lines

**Fix 2: Centralize hard cap constants**
- File: `nicegui_app/pages/request_form.py:1059`
- Action: Replace `hard_cap_types = ['chicago_leave', 'sick', 'personal']`
- With: `from src.services.policy_engine import HARD_CAP_TYPES`
- Estimated scope: Single line change

### Priority 2: HIGH (Should fix in Phase 2)

**Fix 3: Centralize auto-approve types**
- File: `src/services/pto_service.py:26-29`
- Action: Import from `PolicyEngine` instead of defining locally
- Estimated scope: 2 lines changed

**Fix 4: Centralize backdate window**
- File: `src/services/pto_service.py:71`
- Action: Use `PolicyEngine.BACKDATE_WINDOW_DAYS` instead of hardcoded `7`
- Estimated scope: 1 line changed

---

## 15. Required Invariant Tests

Create `tests/test_policy_invariants.py` with:

```python
# Test 1: Only one day-counting implementation exists
def test_no_duplicate_day_counting():
    # Grep for 'def count' in nicegui_app/ should find 0 results
    pass

# Test 2: Hard cap types match between UI and PolicyEngine
def test_hard_cap_types_parity():
    from src.services.policy_engine import HARD_CAP_TYPES
    # Assert UI uses same constants
    pass

# Test 3: Balance formulas produce correct results
def test_vacation_available_formula():
    # Create balance, verify vacation_available property
    pass

# Test 4: Working days calculation excludes holidays
def test_working_days_excludes_holidays():
    # Create holiday, verify day count is correct
    pass
```

---

## 16. Phase-Gated Execution Plan

### Phase 1: Verification (COMPLETE)
- Read-only audit
- Produce this report
- **Status:** Complete

### Phase 2: Critical Fixes (REQUIRES APPROVAL)
- Fix duplicate day-counting
- Fix hardcoded constants
- Add invariant tests
- **Blocked until:** User approves this report

### Phase 3: RAG Preparation
- Document extraction
- Chunking strategy
- Index validation
- **Blocked until:** All Critical issues resolved

### Phase 4: MCP Enablement
- Read-only tools first
- Write tools with confirmation
- **Blocked until:** RAG validated

---

## 17. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Day-count divergence | Medium | High | Fix duplicate function |
| Constant drift | Low | Medium | Centralize in PolicyEngine |
| Future formula change breaks parity | Low | High | Invariant tests |

---

## 18. Conclusion

PTO Central has a solid architectural foundation with proper business logic separation. However, **two critical policy parity violations** must be fixed before the system is ready for MCP/RAG:

1. **Duplicate day-counting function** in request_form.py
2. **Hardcoded policy constants** instead of referencing PolicyEngine

**Recommended Action:** Fix Priority 1 issues, add invariant tests, then re-scan.

---

**END OF REPORT**
