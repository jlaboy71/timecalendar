# MCPRAGv2.md

**PTO Central – Final Pre-MCP / Pre-RAG Governance & Execution Plan**

**Version:** 2.0
**Status:** Authoritative
**Applies To:** PTO Central
**Audience:** Claude Code, MCP agents, human reviewers
**Change Control:** Any modification requires explicit approval and version bump

---

## 0. Purpose and Non-Negotiable Principle

PTO Central is a **policy-driven system**.
All calculations, approvals, balances, and eligibility rules must behave **identically across every surface**.

> There is no "UI logic," "calendar logic," or "API logic."
> There is **one policy**, enforced everywhere.

This document defines the **only allowed sequence** for:

* Verifying correctness
* Locking invariants
* Preparing the system for MCP agents
* Preparing the system for RAG ingestion

No MCP or RAG activation is permitted until **all Phase 1 blockers are resolved**.

---

## 1. PHASE 1 – Deep Application Verification (READ-ONLY)

### 1.1 Operating Mode

* **READ-ONLY**
* No code edits
* No migrations
* No formatting
* No refactors
* No "fix while scanning"

If a change is required, it must be **documented only**, not implemented.

---

## 2. Canonical Policy Domains (Must Be Verified)

These domains are **non-optional** and must be audited exhaustively.

### 2.1 Balance Formula Integrity

Verify:

* Accrual formulas
* Carryover formulas
* Chicago Leave 16-hour cap
* Separation of carryover vs current-year accrual
* Negative balances where allowed

Source of truth:

* `task/formulalogic.md`
* `src/models/pto_balance.py`
* `src/services/balance_service.py`

---

### 2.2 Status Transition Integrity

Verify valid and invalid transitions:

* pending → approved
* pending → denied
* approved → cancelled
* trusted auto-approve paths
* WFH swap transitions

No surface may bypass these rules.

---

### 2.3 Chargeable Date Logic (CRITICAL)

Verify **one and only one** chargeable-date algorithm exists.

Must exclude:

* Weekends
* Market holidays
* Exchange floor close days

Must be applied identically in:

* Request Form
* Calendar
* Manager approvals
* API validation
* Reporting
* Balance deduction

Any duplicate or divergent implementation is a **critical defect**.

---

### 2.4 PTO Type Enforcement Matrix (Must Be Extracted From Code)

For **each PTO type**, extract actual behavior from code, not assumptions:

| PTO Type | Allow Negative | Manager Override | Trusted Auto-Approve | Holiday Excluded | Weekend Excluded |
| -------- | -------------- | ---------------- | -------------------- | ---------------- | ---------------- |

Special rules:

* **Sick, Personal, Leave**

  * NEVER allow oversubscription
  * NEVER allow negative
  * NEVER allow manager override
* Vacation may allow negative and/or override if policy allows
* Chicago Leave strictly capped

---

### 2.5 Warning vs Blocking Rules

Verify correctness of:

* Requested vs available math
* Overage calculation
* Units consistency (days vs hours)
* Messaging accuracy

Rules:

* Hard caps → **block submit**
* Soft limits → **warn but allow**
* No modal may loop without resolving state

---

### 2.6 Backdating and Future Requests

Verify:

* Definition of "present day"
* 7-day backdating rule
* Timezone consistency
* Manager approval requirements
* Trusted employee limitations
* Future borrowing behavior

---

### 2.7 Trusted Employee Automation

Verify:

* Which PTO types allow trusted auto-approval
* Notification/reporting to manager
* Audit logging of auto-approval
* No privilege escalation via trust

---

### 2.8 WFH Day Swap

Verify:

* No balance impact
* Peer-to-peer enforcement
* No manager approval
* Proper audit logging
* UI and API parity

---

### 2.9 Year-End Processing

Verify:

* Carryover allocation timing
* Availability on Jan 1
* No double-counting
* Year boundary requests (Dec 31 → Jan 1)
* Accrual reset behavior

---

## 3. Cross-Surface Policy Parity (MANDATORY)

For **every rule above**, compare behavior across:

* Request Form
* Calendar
* Manager UI
* API/services
* Reports

Produce a **Policy Parity Matrix** showing:

* Rule
* Surface A behavior
* Surface B behavior
* Match or mismatch
* Severity

Any mismatch is a **blocker**.

---

## 4. Known Defect Family Scan (Must Be Explicit)

You must explicitly verify the absence or presence of:

1. Holiday exclusion claimed but not applied
2. Sick/Personal/Leave oversubscription allowed
3. Modal acknowledgment loops
4. Multiple day-counting functions
5. Unit mismatches (hours vs days)
6. UI blocking without API enforcement
7. API enforcement without UI visibility

---

## 5. Deterministic Time Rules

Document:

* Server timezone
* User timezone handling
* "Today" definition
* Whether tests freeze time
* Where time must be frozen but is not

---

## 6. Phase 1 Output (ONE FILE)

Produce:

### `final_pre_mcp_rag_scan_report.md`

Must include:

1. Executive summary (PROCEED or HOLD)
2. Balance verification
3. Status transitions
4. Chargeable date logic
5. PTO type enforcement table
6. Policy parity matrix
7. Defect family findings
8. Year-end readiness
9. Audit logging completeness
10. WFH swap verification
11. Risk assessment
12. **Minimal fix plan (NO CODE)**:

* Smallest fixes first
* Exact files/functions
* Required invariant tests

13. Phase-gated execution plan

---

## 7. PHASE 2 – Critical Fixes Only (AFTER APPROVAL)

Only after Phase 1 approval:

* Implement minimal fixes
* Add invariant tests
* Centralize policy logic
* Remove duplicate calculations

Every fix must:

* Have a test
* Reference a documented defect
* Preserve protected logic boundaries

---

## 8. Policy Invariants Lock

Create:

* `tests/test_policy_invariants.py`
* `POLICY_VERSION.md`

Rules:

* Invariants must fail loudly
* Changing invariants requires version bump
* CI must enforce invariants

---

## 9. PHASE 3 – RAG PREPARATION

Only after all Critical issues resolved.

### 9.1 RAG Source Scope

Allowed sources:

* Help docs
* Policy docs
* User-facing explanations
* Reports and scenarios

Forbidden:

* Raw code
* Secrets
* DB dumps

---

### 9.2 Chunking Strategy

* Policy by rule
* Help by topic
* Scenarios by workflow
* Overlap tuned to avoid logic bleed

---

### 9.3 RAG Update Modes

* Dry-run
* Incremental
* Full rebuild

---

## 10. PHASE 4 – MCP ENABLEMENT

### 10.1 MCP Tool Phases

1. Read-only tools only
2. Analysis tools
3. Write tools with confirmation
4. Autonomous tools (future)

---

### 10.2 MCP Security

* localhost only
* rate limiting
* timeouts
* audit logging
* no write without explicit confirmation

---

## 11. PHASE 5 – FINAL READINESS CHECKLIST

Must pass:

* All invariant tests
* No policy parity mismatches
* No unresolved Critical findings
* Accurate help documentation
* RAG index validated
* MCP tools gated

---

## 12. Final Authority Statement

If any future AI:

* Contradicts policy
* Introduces duplicate logic
* Allows oversubscription
* Breaks parity

It is **wrong**, regardless of confidence.

This document overrides all AI behavior.

---

**END OF MCPRAGv2.md**
