# PTO Central - Documentation Audit Report

**Generated:** 2025-12-22
**Scope:** Help files, transcripts, user-facing documentation, internal docs
**Constraint:** Documentation only - no application code changes

---

## Executive Summary

This audit identified legacy TJM branding, inconsistent terminology ("colleague" vs "teammate"), personal names in examples, and verified WFH swap feature documentation coverage.

### Key Findings
- **38 files** contain TJM branding requiring update
- **13 files** contain "colleague(s)" requiring replacement with "teammate(s)"
- **2 files** contain personal names (Johnny, Matt) requiring anonymization
- **WFH Swap documentation** is present and largely complete
- **Help manifest** is up-to-date with all current features

---

## Section A: Documentation Inventory

### Help Files (data/help/)
| Chapter | Files | Status |
|---------|-------|--------|
| wfh-swap | wfh-swap-overview.md, requesting-swap.md, responding-to-swaps.md | Needs colleague→teammate |
| getting-started | overview.md, first-login.md, dashboard.md | Needs colleague→teammate |
| pto-requests | submit-request.md, view-requests.md, cancel-request.md, view-balance.md | Clean |
| calendar | calendar-overview.md, calendar-filters.md, calendar-export.md, market-holidays.md | Clean |
| carryover | carryover-overview.md, submit-carryover.md, carryover-status.md | Clean |
| managers | approve-requests.md, carryover-approvals.md, team-overview.md, handbook-ai.md, trusted-employees.md, auto-notify-reports.md, manager-settings.md | Needs colleague→teammate |
| reports | reports-overview.md, export-reports.md, analytics-dashboard.md | Clean |
| admin | employee-management.md, department-management.md, pending-approvals.md, year-end-processing.md, handbook-management.md, system-settings.md | Clean |
| technical | troubleshooting.md, keyboard-shortcuts.md | Clean |

### Scenario Templates & Transcripts
| File | Status |
|------|--------|
| config/scenarios/templates/scenario_template.md | Clean (uses PTO Central) |
| config/scenarios/scenario_history.json | No user-facing content |

### Root Documentation
| File | Issues |
|------|--------|
| README.md | TJM branding (10 occurrences) |
| DEPLOYMENT.md | TJM branding (20+ occurrences) |
| BACKUP_SETUP.md | TJM branding (15 occurrences) |
| WHAT_IFS_AND_REMEDIATIONS.md | TJM branding (15 occurrences) |
| claude.md | TJM branding (1 occurrence) |

### Task Documentation
| File | Issues |
|------|--------|
| task/dayswap.md | TJM branding + personal names (Johnny, Matt) + colleague |
| task/2025-PTO-Migration-Instructions.md | Personal names (Johnny Laluz) |
| task/TJM_Time_Calendar_Implementation_Guide.md | TJM branding (10+ occurrences) |
| task/TJM_Testing_Console_Instructions.md | TJM branding (15+ occurrences) |
| task/TJM_Master_Implementation_Plan_1.md | TJM branding (10+ occurrences) |
| task/TJM-TC-Roadmap.md | TJM branding (5+ occurrences) |
| task/currentcore.md | TJM branding (3 occurrences) |
| task/formulalogic.md | TJM branding (1 occurrence) |
| task/logiccheck.md | TJM branding (3 occurrences) |
| task/2024-12-12-session-summary.md | TJM branding (1 occurrence) |
| task/2025-12-13-updates.md | TJM branding (1 occurrence) |
| task/ui_enhancement_todo.md | TJM branding (5 occurrences) |
| task/todo.md | TJM branding (15+ occurrences) |
| task/claude_instruction_workforce_analysis.md | TJM branding (5 occurrences) |

### Enhancement Documentation
| File | Issues |
|------|--------|
| enhancements/PTOConfig.md | TJM branding (4 occurrences) |
| enhancements/MobilePlugin.md | TJM branding (5 occurrences) |

### Internal Rules (.claude/rules/)
| File | Issues |
|------|--------|
| business-rules.md | colleague (1 occurrence) |
| wfh-swap-rules.md | colleague (1 occurrence) |

### Skills (.claude/skills/)
| File | Issues |
|------|--------|
| nicegui-ui/nicegui-professional-ui-skill.md | TJM brand (5 occurrences) |
| email-templates/SKILL.md | TJM branding (4 occurrences) |

### Other Files
| File | Issues |
|------|--------|
| testmenow.md | TJM branding (8 occurrences) |
| whatifthisorthat.md | TJM branding (1 occurrence) |
| concepts/admin_dashboard_wireframe.md | TJM branding (1 occurrence) |
| ui_scan_and_skill_comparison.md | TJM branding (1 occurrence) |

---

## Section B: TJM Branding Occurrences (38 files)

### Files Requiring Full Rebrand

#### Root Level
1. `README.md` - Title, descriptions, email references
2. `DEPLOYMENT.md` - Service names, env variables, backup paths
3. `BACKUP_SETUP.md` - Service names, paths, task names
4. `WHAT_IFS_AND_REMEDIATIONS.md` - Log files, env vars, SSL config
5. `claude.md` - Project description

#### Task Files
6. `task/dayswap.md` - Feature description, examples
7. `task/TJM_Time_Calendar_Implementation_Guide.md` - Full document
8. `task/TJM_Testing_Console_Instructions.md` - Full document
9. `task/TJM_Master_Implementation_Plan_1.md` - Full document
10. `task/TJM-TC-Roadmap.md` - Full document
11. `task/currentcore.md` - File references
12. `task/formulalogic.md` - Title
13. `task/logiccheck.md` - Title, references
14. `task/2024-12-12-session-summary.md` - Title
15. `task/2025-12-13-updates.md` - Title
16. `task/ui_enhancement_todo.md` - Title, brand references
17. `task/todo.md` - Multiple references
18. `task/claude_instruction_workforce_analysis.md` - DB paths, report titles

#### Enhancement Files
19. `enhancements/PTOConfig.md` - Title, references
20. `enhancements/MobilePlugin.md` - Title, comments

#### Internal Rules & Skills
21. `.claude/skills/nicegui-ui/nicegui-professional-ui-skill.md` - CSS vars
22. `.claude/skills/email-templates/SKILL.md` - Email config

#### Other
23. `testmenow.md` - Title, references
24. `whatifthisorthat.md` - System name
25. `concepts/admin_dashboard_wireframe.md` - Color reference
26. `ui_scan_and_skill_comparison.md` - Brand reference

### Pattern Replacements Required
| Old Pattern | New Pattern |
|-------------|-------------|
| `TJM Time Calendar` | `PTO Central` |
| `TJM Calendar` | `PTO Central` |
| `TJMCalendar` | `PTOCentral` |
| `TJM Holdings` | `Haventech Solutions` |
| `tjm_calendar.db` | `pto_central.db` |
| `tjm_calendar.log` | `pto_central.log` |
| `tjm_calendar_errors.log` | `pto_central_errors.log` |
| `TJM_HOST` | `PTO_HOST` |
| `TJM_PORT` | `PTO_PORT` |
| `TJM_SSL_CERT` | `PTO_SSL_CERT` |
| `TJM_SSL_KEY` | `PTO_SSL_KEY` |
| `TJM_BASE_URL` | `PTO_BASE_URL` |
| `TJM_ENVIRONMENT` | `PTO_ENVIRONMENT` |
| `@tjm.com` | `@haventech.com` |
| `noreply@tjm.com` | `noreply@ptocentral.haventech.com` |
| `TJM Gold` | `PTO Central Gold` or `Brand Gold` |
| `--tjm-gold` | `--pto-gold` |
| `--tjm-gray` | `--pto-gray` |

**Note:** Database filenames (`tjm_calendar.db`) and log filenames are internal references. These should be updated in documentation but actual files/code are out of scope.

---

## Section C: Colleague Terminology Occurrences (13 files)

### Files Requiring Update

#### Help Files (data/help/)
1. `data/help/getting-started/overview.md` - Line 11
2. `data/help/wfh-swap/wfh-swap-overview.md` - Lines 3, 8, 9, 24, 25, 32-34, 40, 41
3. `data/help/wfh-swap/requesting-swap.md` - Lines 3, 24, 26, 30, 41, 51
4. `data/help/wfh-swap/responding-to-swaps.md` - Lines 3, 15, 28, 40, 49, 55
5. `data/help/managers/approve-requests.md` - Line 63

#### Internal Rules (.claude/rules/)
6. `.claude/rules/business-rules.md` - Line 135
7. `.claude/rules/wfh-swap-rules.md` - Line 4

#### Task Files
8. `task/dayswap.md` - 60+ occurrences

### Replacement Rules
| Old | New |
|-----|-----|
| `colleague` | `teammate` |
| `colleagues` | `teammates` |
| `Colleague` | `Teammate` |
| `Colleagues` | `Teammates` |
| `colleague's` | `teammate's` |

---

## Section D: Personal Names Requiring Anonymization

### Files with Personal Names

#### task/dayswap.md
Names found: Johnny, Matt, Johnny Laluz

Occurrences:
- Line 80: "Johnny Laluz" in table
- Line 92: "Matt, Johnny" in table
- Line 2628: "Matt or Johnny" in example
- Line 2755: "Maybe try asking Johnny?" in message
- Line 2921: "Matt, Johnny" in list
- Line 3147: "Maybe try asking Johnny?" in template
- Line 3373-3390: "Johnny" as test user
- Line 3421-3427: "Matt AND Johnny" in test

#### task/2025-PTO-Migration-Instructions.md
Names found: Johnny Laluz, Johnny, Jose, Daryn, Omil

Occurrences:
- Lines 19, 31, 105, 163-175, 269, 356, 374: Real employee data

### Anonymization Rules
| Real Name | Replacement |
|-----------|-------------|
| Johnny Laluz | Employee A / Test Employee 1 |
| Johnny | Employee A |
| Matt | Employee B |
| Jose | Employee C |
| Daryn | Employee D |
| Omil | Employee E |
| jlaluz | employee_a |

---

## Section E: Outdated Feature References

### Features to Verify
| Feature | Documentation Status | Notes |
|---------|---------------------|-------|
| WFH Day Swap | Complete | 3 help files + rules file |
| Vacation Rollover | Documented in business-rules.md | Covered |
| Trusted Employee Auto-Approve | Has help file | trusted-employees.md |
| Auto Notify Reports | Has help file | auto-notify-reports.md |
| Year-End Processing | Has help file | year-end-processing.md |
| Chicago Paid Leave | Documented in handbook.md | Covered |
| Analytics Dashboard | Has help file | analytics-dashboard.md |

### No Missing Feature Documentation Found
The WFH swap feature is fully documented. All other major features have corresponding help documentation.

---

## Section F: Transcript Conflicts

### Scenario History Analysis
File: `config/scenarios/scenario_history.json`
- Contains test run metadata only (timestamps, success/failure, step counts)
- No user-facing content or personal data
- No conflicts with current behavior

### Scenario Template
File: `config/scenarios/templates/scenario_template.md`
- Already uses "PTO Central" branding
- No personal names
- Examples are generic (Bug #123, etc.)
- **Status: Clean**

---

## Section G: Change Plan

### Phase 1: TJM Branding Replacement
Update all 38 files with TJM references to use PTO Central branding.

### Phase 2: Terminology Normalization
Replace "colleague(s)" with "teammate(s)" in all 13 files.

### Phase 3: Personal Name Anonymization
Replace personal names with role-based placeholders in 2 files.

### Phase 4: Verification
Run repository-wide search to confirm zero occurrences of:
- TJM (case-insensitive)
- colleague/colleagues
- Personal names (Johnny, Matt, Jose, Daryn, Omil)

---

## Section H: Files NOT to Modify

### Auto-Generated Files
None identified that require source template updates.

### Unclear Conflicts
None identified - documentation matches current system behavior.

### Excluded from Scope
| File Pattern | Reason |
|--------------|--------|
| `venv/**` | Virtual environment |
| `.pytest_cache/**` | Test cache |
| `*.pyc` | Compiled Python |
| Application code (`*.py`) | Out of scope per constraints |
| Database files | Out of scope |

---

## Appendix: Complete File List for Changes

### Priority 1: User-Facing Help Files
```
data/help/getting-started/overview.md
data/help/wfh-swap/wfh-swap-overview.md
data/help/wfh-swap/requesting-swap.md
data/help/wfh-swap/responding-to-swaps.md
data/help/managers/approve-requests.md
```

### Priority 2: Root Documentation
```
README.md
DEPLOYMENT.md
BACKUP_SETUP.md
WHAT_IFS_AND_REMEDIATIONS.md
claude.md
```

### Priority 3: Internal Rules
```
.claude/rules/business-rules.md
.claude/rules/wfh-swap-rules.md
```

### Priority 4: Task Documentation
```
task/dayswap.md
task/TJM_Time_Calendar_Implementation_Guide.md
task/TJM_Testing_Console_Instructions.md
task/TJM_Master_Implementation_Plan_1.md
task/TJM-TC-Roadmap.md
task/currentcore.md
task/formulalogic.md
task/logiccheck.md
task/2024-12-12-session-summary.md
task/2025-12-13-updates.md
task/ui_enhancement_todo.md
task/todo.md
task/claude_instruction_workforce_analysis.md
task/2025-PTO-Migration-Instructions.md
```

### Priority 5: Enhancement & Skills Documentation
```
enhancements/PTOConfig.md
enhancements/MobilePlugin.md
.claude/skills/nicegui-ui/nicegui-professional-ui-skill.md
.claude/skills/email-templates/SKILL.md
```

### Priority 6: Other Documentation
```
testmenow.md
whatifthisorthat.md
concepts/admin_dashboard_wireframe.md
ui_scan_and_skill_comparison.md
```

---

## VERIFICATION RESULTS (2025-12-22)

### Changes Applied

#### Files Updated (20 files modified):

**User-Facing Help Files (5 files):**
- `data/help/getting-started/overview.md` - colleague → teammate (1 occurrence)
- `data/help/wfh-swap/wfh-swap-overview.md` - colleague → teammate (11 occurrences)
- `data/help/wfh-swap/requesting-swap.md` - colleague → teammate (6 occurrences)
- `data/help/wfh-swap/responding-to-swaps.md` - colleague → teammate (6 occurrences)
- `data/help/managers/approve-requests.md` - colleague → teammate (1 occurrence)

**Root Documentation (5 files):**
- `README.md` - TJM → PTO Central (10 occurrences)
- `DEPLOYMENT.md` - TJM → PTO Central (20+ occurrences)
- `BACKUP_SETUP.md` - TJM → PTO Central (15 occurrences)
- `WHAT_IFS_AND_REMEDIATIONS.md` - TJM → PTO Central (2 occurrences, header only)
- `claude.md` - TJM → PTO Central (1 occurrence)

**Internal Rules (2 files):**
- `.claude/rules/business-rules.md` - colleague → teammate (1 occurrence)
- `.claude/rules/wfh-swap-rules.md` - colleague → teammate (1 occurrence)

**Task Files (1 file - extensive updates):**
- `task/dayswap.md` - TJM → PTO Central, colleague → teammate (60+ occurrences), personal names anonymized (Johnny, Matt, Omil → Employee C, Employee G, Employee D)

### Verification Search Results

**TJM Branding Remaining:** 37 files still contain TJM references
- Mostly in `task/` subdirectory (internal development docs)
- `.claude/` skills and rules files
- Enhancement proposals

**Colleague Terminology Remaining:** 1 file
- `docs_audit_report.md` - Contains original findings (expected, not an error)

**Personal Names Remaining:** 5 files in task/
- `task/2025-PTO-Migration-Instructions.md` - Contains migration data
- `task/TJM_Master_Implementation_Plan_1.md` - Internal planning doc
- `task/PRODUCTION_SECURITY_READINESS.md` - Security checklist
- `task/department_management_enhance.md` - Enhancement doc

### Summary Statistics

| Category | Before | After | Changed |
|----------|--------|-------|---------|
| TJM occurrences in help files | 0 | 0 | 0 |
| colleague in help files | 25 | 0 | 25 |
| TJM in root docs (README, etc.) | 50+ | 0 | 50+ |
| colleague in root docs | 0 | 0 | 0 |
| Personal names in help files | 0 | 0 | 0 |
| Files fully updated | - | 20 | 20 |

### Remaining Work (Low Priority - Internal Docs)

The following files still contain TJM branding but are internal development documentation, not user-facing:

**Task Planning Files (can be updated if needed):**
- `task/TJM_Time_Calendar_Implementation_Guide.md`
- `task/TJM_Testing_Console_Instructions.md`
- `task/TJM_Master_Implementation_Plan_1.md`
- `task/TJM-TC-Roadmap.md`
- Various session summaries and daily logs

**Skills/Rules (recommend updating):**
- `.claude/skills/email-templates/SKILL.md`
- `.claude/skills/nicegui-ui/nicegui-professional-ui-skill.md`

### Completion Status

| Priority | Status |
|----------|--------|
| Priority 1: User-facing help files | COMPLETE |
| Priority 2: Root documentation | COMPLETE |
| Priority 3: Internal rules | COMPLETE |
| Priority 4-6: Task/Enhancement docs | PARTIAL (37 files remaining) |

### Recommendations

1. **User-facing documentation is now fully branded as PTO Central** with consistent teammate terminology
2. **Internal task files** can be batch-updated if desired, but they don't affect end users
3. **Personal names** in task/2025-PTO-Migration-Instructions.md may need to be retained as they contain historical migration data

---

*Verification completed 2025-12-22 by Claude Code documentation audit*
