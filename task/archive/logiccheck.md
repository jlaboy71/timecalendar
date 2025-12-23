# TJM Time Calendar - Policy Engine Unification

## Context
I have a PTO management system where date validation and auto-approval logic is implemented inconsistently across:
- Calendar UI (blocks all past dates)
- Request Form (allows 7-day backdating)
- API endpoints (unknown current state)

This causes user confusion and potential policy violations. I need to unify all validation through a single policy engine.

## Reference Documents
- `task/formulalogic.md` - Canonical business logic (PROTECTED, do not modify formulas)
- `task/currentcore.md` - Core files reference
- `.claude/rules/protected-logic.md` - Protected files list
- `.claude/rules/business-rules.md` - PTO policies reference

## Non-Negotiable Requirements
1. **Do not modify** the core balance formulas in `task/formulalogic.md`
2. **Do not change** existing auto-approve types (vacation, sick, personal)
3. **Create new files** rather than heavily modifying existing ones where possible
4. **Preserve all existing functionality** — this is additive/corrective only
5. **Follow existing patterns** in `nicegui_app/components/theme.py` for styling

---

## Policy Requirements to Implement

### 1. Date Eligibility Rules
```python
BACKDATE_WINDOW_DAYS = 7  # Calendar days, not business days
FUTURE_LIMIT_YEARS = 5
TIMEZONE = 'America/Chicago'  # Server timezone for all calculations

# Backdating rules:
# - Requests up to 7 calendar days in the past: ALLOWED, but requires manager approval
# - Requests more than 7 days in the past: REJECTED
# - Backdating rule applies to Calendar AND Request Form identically
# - Trusted employees do NOT bypass backdating approval requirement
```

### 2. Auto-Approve Rules (preserve existing + add backdating exception)
```python
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}

# Auto-approve if ALL conditions met:
# 1. User is manager/admin/superadmin OR user.is_trusted
# 2. PTO type is in TRUSTED_AUTO_APPROVE_TYPES
# 3. Request is NOT a vacation rollover
# 4. Request is NOT backdated (start_date < today)
#
# If backdated: ALWAYS requires manager approval, even for trusted/managers
```

### 3. Negative Balance Rules (preserve existing)
```python
# Per formulalogic.md:
# - Vacation: Warning only, negative allowed (manager discretion)
# - Sick: Hard block, cannot exceed available
# - Personal: Hard block, cannot exceed available
# - Chicago Leave: Hard block, cannot exceed available
```

---

## Policy Documentation Viewer (System Administration)

### Requirements
Create an interactive Policy & Logic Viewer accessible from the System Administration panel (`nicegui_app/pages/admin_system.py`). This provides administrators with a friendly, readable view of all business logic and calculations without needing to read code.

### Location
Add as a new card/section in System Administration (`admin_system.py`), titled **"Policy & Formula Reference"** or accessible via a dedicated sub-page at `nicegui_app/pages/admin_policy_viewer.py`.

### Design Specifications

#### Layout Structure
Use an accordion or tabbed interface with these sections:

1. **Balance Formulas** - Core calculation formulas
2. **Vacation Tiers** - Tenure-based allocation table
3. **Request Lifecycle** - Status transitions and balance impacts
4. **Carryover Rules** - By leave type with auto vs. exception
5. **Auto-Approve Rules** - Who qualifies, which types, exceptions
6. **Date Validation Rules** - Backdating, future limits, weekends/holidays
7. **Location Policies** - Chicago-specific rules, state variations
8. **Year-End Processing** - What happens automatically

#### Help Button Pattern
Each section and individual rule should have a `?` icon button that opens a tooltip or modal with:
- **Plain English explanation** of what the rule does
- **Why it exists** (business/legal reason)
- **Example scenario** showing the rule in action

#### Visual Elements
- Use TJM brand colors (gold #c9a227 for headers, gray #5a6a72 for secondary)
- Follow patterns from `nicegui_app/components/theme.py`
- Display formulas in a code-style font but with clear variable labels
- Use tables for tier systems and type comparisons
- Use flow diagrams or step indicators for lifecycle/process rules
- Include "Last Updated" timestamp from formulalogic.md

#### Implementation Approach

Create `nicegui_app/pages/admin_policy_viewer.py` with:

```python
class PolicyViewer:
    """
    Interactive policy documentation viewer for System Administration.
    
    Reads policy constants from policy_engine.py and formulalogic definitions
    to display current system behavior in a user-friendly format.
    """
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.sections = self._build_sections()
    
    def _build_sections(self) -> List[PolicySection]:
        """Build all policy documentation sections."""
        return [
            self._build_balance_formulas_section(),
            self._build_vacation_tiers_section(),
            self._build_request_lifecycle_section(),
            self._build_carryover_rules_section(),
            self._build_auto_approve_section(),
            self._build_date_validation_section(),
            self._build_location_policies_section(),
            self._build_year_end_section(),
        ]
    
    def render(self, container):
        """Render the policy viewer in the given NiceGUI container."""
        pass
```

#### Help Content Structure

For each policy item, define help content as:

```python
@dataclass
class PolicyHelp:
    title: str
    plain_english: str      # What it does in simple terms
    business_reason: str    # Why this rule exists
    example: str            # Concrete scenario
    related_rules: List[str]  # Cross-references
```

Example help content:

```python
BACKDATE_HELP = PolicyHelp(
    title="7-Day Backdating Window",
    plain_english="Employees can submit PTO requests for dates up to 7 days in the past, but these always require manager approval.",
    business_reason="Allows correction of forgotten time-off entries while maintaining oversight. The 7-day limit prevents abuse and ensures timely record-keeping.",
    example="Today is December 19th. An employee forgot to log sick time from December 15th. They can submit the request, but their manager must approve it. A request for December 10th (9 days ago) would be rejected.",
    related_rules=["Auto-Approve Rules", "Manager Approval Workflow"]
)

VACATION_NEGATIVE_HELP = PolicyHelp(
    title="Vacation Negative Balance (Manager Discretion)",
    plain_english="Vacation requests can be approved even if the employee doesn't have enough hours. The balance can go negative.",
    business_reason="Per company policy, vacation is front-loaded but managers have discretion to approve time off in advance of accrual for special circumstances.",
    example="An employee has 16 hours of vacation remaining but requests 24 hours. The system shows a warning but allows the manager to approve. If approved, the balance shows -8 hours.",
    related_rules=["Balance Formulas", "Vacation Tier System"]
)

TRUSTED_EMPLOYEE_HELP = PolicyHelp(
    title="Trusted Employee Auto-Approval",
    plain_english="Trusted employees can submit Vacation, Sick, and Personal time without waiting for manager approval. The request is immediately approved.",
    business_reason="Reduces administrative burden for reliable employees while maintaining records. Managers are still notified of all time off.",
    example="A trusted employee submits 8 hours of sick time. The request is immediately approved and their sick balance is reduced. Their manager receives a notification but didn't need to click 'Approve'.",
    related_rules=["Auto-Approve Rules", "Manager Notifications"]
)
```

#### Interactive Features

1. **Expand/Collapse All** button for accordion sections
2. **Search/Filter** to find specific rules by keyword
3. **Print/Export** button to generate a PDF of all policies (for handbook reference)
4. **"View in Code"** link (superadmin only) that shows the actual file/line reference

#### Data Source
The viewer should read from:
1. `policy_engine.py` constants (single source of truth)
2. `task/formulalogic.md` for reference documentation
3. Database for dynamic values (vacation tiers, location policies)

This ensures the viewer always shows **actual system behavior**, not outdated documentation.

---

## Task Steps

### Step 1: Audit Current Implementation
Scan these locations and document current behavior:
- `nicegui_app/pages/calendar.py` - Calendar date validation
- `nicegui_app/pages/request_form.py` - Request form validation
- `src/services/pto_service.py` - API-level validation (PROTECTED)
- `src/services/balance_service.py` - Balance checking (PROTECTED)
- `src/constants.py` - Existing constants

Create a report showing:
- File, function, line number
- Current validation logic
- Discrepancy with policy requirements

### Step 2: Create Policy Engine Module
Create `src/services/policy_engine.py` with:

```python
class PolicyEngine:
    """Centralized policy evaluation for PTO requests.
    
    All UI and API validations MUST call this engine rather than
    implementing their own rules.
    """
    
    # Policy constants (used by PolicyViewer for documentation)
    BACKDATE_WINDOW_DAYS = 7
    FUTURE_LIMIT_YEARS = 5
    TIMEZONE = 'America/Chicago'
    TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}
    ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military', 'wfh'}
    
    def validate_request_dates(
        self, 
        start_date: date, 
        end_date: date,
        user: User,
        pto_type: str
    ) -> PolicyResult:
        """
        Returns PolicyResult with:
        - is_valid: bool
        - requires_manager_approval: bool
        - rejection_reason: Optional[str]
        - warnings: List[str]
        """
        pass
    
    def determine_auto_approve(
        self,
        user: User,
        pto_type: str,
        start_date: date,
        is_vacation_rollover: bool = False
    ) -> AutoApproveResult:
        """
        Returns AutoApproveResult with:
        - auto_approve: bool
        - reason: str (for audit log)
        - notify_manager: bool
        """
        pass
    
    def validate_balance(
        self,
        user_id: int,
        pto_type: str,
        hours_requested: float,
        year: int
    ) -> BalanceValidationResult:
        """
        Returns BalanceValidationResult with:
        - is_valid: bool
        - is_warning_only: bool (True for vacation)
        - available_hours: float
        - shortfall_hours: float
        """
        pass
    
    def get_policy_documentation(self) -> Dict[str, PolicySection]:
        """
        Returns all policy rules in a structured format for the PolicyViewer.
        This ensures documentation always matches actual implementation.
        """
        pass
```

### Step 3: Create Policy Documentation Viewer
Create `nicegui_app/pages/admin_policy_viewer.py` implementing the Policy & Formula Reference viewer as specified above.

Integrate into System Administration panel by:
- Adding a card or menu item in `nicegui_app/pages/admin_system.py` labeled "Policy & Formula Reference"
- Link to the new policy viewer page
- Use TJM brand styling (gold headers, professional appearance)
- Follow component patterns from `nicegui_app/components/theme.py`
- Accordion sections for each policy area
- `?` help buttons with tooltips/modals for each rule
- Mobile-responsive layout (follow patterns in `nicegui_app/components/mobile_responsive.py`)

### Step 4: Update Calendar UI
Modify `nicegui_app/pages/calendar.py` validation to:
1. Call `policy_engine.validate_request_dates()`
2. Allow backdated requests within 7 days
3. Show indicator that backdated requests require approval

### Step 5: Update Request Form
Modify `nicegui_app/pages/request_form.py` validation to:
1. Call `policy_engine.validate_request_dates()`
2. Match calendar behavior exactly

### Step 6: Update PTO Service
Modify `src/services/pto_service.py:create_request()` to:
1. Call policy engine for all validation
2. Use policy engine for auto-approve determination
3. Ensure API is the final enforcement gate
4. Note: This is a PROTECTED file - document all changes clearly

### Step 7: Add Audit Logging
Use existing `src/services/audit_service.py` to ensure all policy decisions are logged:
- Auto-approve reason
- Backdating detection
- Manager notification triggers

### Step 8: Create Tests
Add tests in `tests/test_policy_engine.py`:
- Backdating within 7 days: allowed with approval flag
- Backdating beyond 7 days: rejected
- Trusted employee auto-approve: works for allowed types
- Trusted employee backdated: does NOT auto-approve
- Vacation negative balance: warning only
- Sick negative balance: hard block
- Calendar and Request Form produce identical validation results

### Step 9: Update Route Registration
Register the new policy viewer page in `nicegui_app/main.py` following existing patterns.

---

## Deliverables

1. **`task/policy_reconciliation_report.md`** in task folder:
   - Current behavior inventory (file, function, behavior)
   - Discrepancy matrix
   - Changes made
   - Test coverage summary

2. **`src/services/policy_engine.py`** - New centralized policy module

3. **`nicegui_app/pages/admin_policy_viewer.py`** - Policy documentation viewer UI

4. **Updated files** with policy engine integration:
   - `nicegui_app/pages/calendar.py`
   - `nicegui_app/pages/request_form.py`
   - `src/services/pto_service.py` (PROTECTED - document changes)
   - `nicegui_app/pages/admin_system.py` (add policy viewer link)
   - `nicegui_app/main.py` (register new route)

5. **`tests/test_policy_engine.py`** - Comprehensive test suite

---

## Stop Conditions
- Do NOT modify balance formulas in `src/models/pto_balance.py`
- Do NOT change vacation tier calculations in `src/services/accrual_service.py`
- Do NOT modify carryover logic in `src/services/year_end_service.py`
- Do NOT add new PTO types
- Do NOT change database schema
- If existing code contradicts these requirements, document it in the report BEFORE changing
- Reference `.claude/rules/protected-logic.md` for full protected files list

---

## Verification Checkpoints
After each major step, verify:
1. All existing tests still pass
2. Application starts without errors: `python -m nicegui_app.main`
3. Basic PTO request flow works (submit, approve, cancel)
4. Policy Viewer displays correctly and help buttons function
5. No regressions in existing functionality

---

## Progress Tracking

### Status: COMPLETE

| Step | Status | Notes |
|------|--------|-------|
| Step 1: Audit | ✅ | Created `task/policy_reconciliation_report.md` |
| Step 2: Policy Engine | ✅ | Created `src/services/policy_engine.py` |
| Step 3: Policy Viewer | ✅ | Created `nicegui_app/pages/admin_policy_viewer.py` |
| Step 4: Calendar UI | ✅ | Updated `calendar.py` to use PolicyEngine |
| Step 5: Request Form | ✅ | Updated `request_form.py` to use PolicyEngine |
| Step 6: PTO Service | ✅ | Added backdating check to auto-approve logic |
| Step 7: Audit Logging | ✅ | Existing logging is sufficient |
| Step 8: Tests | ✅ | Created `tests/test_policy_engine.py` (37 tests, all passing) |
| Step 9: Route Registration | ✅ | Added route and nav link in admin_system.py |

---

**END OF TASK**
