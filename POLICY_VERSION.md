# PTO Central Policy Version

**Version:** 1.0.0
**Effective Date:** 2025-12-22
**Last Audit:** 2025-12-22 (MCPRAGv2 Phase 5)

---

## Policy Invariants Lock

This file documents the locked policy version for PTO Central. Any changes to policy invariants require:

1. Version bump in this file
2. Update to `tests/test_policy_invariants.py`
3. CI must pass all invariant tests
4. Documentation update

---

## Locked Invariants (v1.0.0)

### Balance Formulas
```
vacation_available = vacation_total + vacation_carryover - vacation_used - vacation_pending
sick_available = sick_total + sick_carryover - sick_used - sick_pending
personal_available = personal_total + personal_carryover - personal_used - personal_pending
chicago_paid_leave_available = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

### Hard Cap Types (Block Submission)
- `chicago_leave`
- `sick`
- `personal`

### Soft Cap Types (Warning Only)
- `vacation`

### Trusted Auto-Approve Types
- `vacation`
- `sick`
- `personal`

### Always Requires Approval
- `bereavement`
- `fmla`
- `jury_duty`
- `voting`
- `military`
- `wfh`
- `chicago_leave`

### Date Validation Rules
- Backdate Window: 7 calendar days
- Future Limit: 5 years
- Timezone: America/Chicago

### Working Day Calculation
- Excludes weekends (Saturday, Sunday)
- Excludes full federal holidays
- Includes Early Close days (half-days)

---

## Change History

| Version | Date | Changes | Approved By |
|---------|------|---------|-------------|
| 1.0.0 | 2025-12-22 | Initial locked version after MCPRAGv2 audit | Claude Code |

---

## Verification

To verify policy invariants:
```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe -m pytest tests/test_policy_invariants.py -v
```

Expected: 21 tests, 21 passed

---

**This file is the authoritative policy version document per MCPRAGv2.md Section 8.**
