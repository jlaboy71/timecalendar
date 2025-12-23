# PTO Central - RAG Source Manifest

**Version:** 1.0
**Date:** 2025-12-22
**Status:** Phase 3 - RAG Preparation
**Reference:** task/MCPRAGv2.md Section 9

---

## 1. Source Scope

### Allowed Sources (per MCPRAGv2 Section 9.1)

| Category | Source | Purpose |
|----------|--------|---------|
| Help Docs | `data/help/**/*.md` | User-facing documentation |
| Policy Docs | `handbook/handbook.md` | Official company policies |
| Business Rules | `.claude/rules/business-rules.md` | Encoded policy logic |
| Formula Logic | `task/formulalogic.md` | Balance calculations |
| UI Patterns | `.claude/rules/ui-patterns.md` | UI/UX standards |
| **Scenario Transcripts** | `nicegui_app/static/help/videos/*.srt` | Training video narrations |
| **Scenario Timelines** | `nicegui_app/static/help/videos/*.timeline.json` | Step-by-step workflow scripts |

### Forbidden Sources (NEVER include)

| Type | Reason |
|------|--------|
| `*.py` files | Raw code - implementation details |
| `*.db` files | Database dumps - contains PII |
| `.env`, `*credentials*` | Secrets |
| `venv/` | Third-party code |
| `alembic/versions/` | Migration code |
| `tests/` | Test code |

---

## 2. Help Documentation Inventory

### Getting Started (3 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/getting-started/overview.md` | System overview | Single chunk |
| `data/help/getting-started/first-login.md` | Login process | Single chunk |
| `data/help/getting-started/dashboard.md` | Dashboard navigation | Section-based |

### PTO Requests (4 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/pto-requests/submit-request.md` | Creating requests | Step-based |
| `data/help/pto-requests/view-requests.md` | Viewing history | Single chunk |
| `data/help/pto-requests/view-balance.md` | Balance checking | Single chunk |
| `data/help/pto-requests/cancel-request.md` | Cancellation | Single chunk |

### Calendar (4 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/calendar/calendar-overview.md` | Calendar features | Section-based |
| `data/help/calendar/calendar-filters.md` | Filtering options | Single chunk |
| `data/help/calendar/calendar-export.md` | Export to iCal | Single chunk |
| `data/help/calendar/market-holidays.md` | Holiday reference | Single chunk |

### Carryover (3 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/carryover/carryover-overview.md` | Carryover policy | Single chunk |
| `data/help/carryover/submit-carryover.md` | Request process | Step-based |
| `data/help/carryover/carryover-status.md` | Tracking status | Single chunk |

### Managers (7 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/managers/approve-requests.md` | Approval workflow | Step-based |
| `data/help/managers/carryover-approvals.md` | Exception approval | Single chunk |
| `data/help/managers/team-overview.md` | Team management | Section-based |
| `data/help/managers/handbook-ai.md` | AI assistance | Single chunk |
| `data/help/managers/trusted-employees.md` | Trust status | Single chunk |
| `data/help/managers/auto-notify-reports.md` | Notifications | Single chunk |
| `data/help/managers/manager-settings.md` | Settings config | Section-based |

### Admin (6 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/admin/employee-management.md` | User CRUD | Section-based |
| `data/help/admin/department-management.md` | Department setup | Single chunk |
| `data/help/admin/pending-approvals.md` | Approval queue | Single chunk |
| `data/help/admin/handbook-management.md` | Policy editing | Single chunk |
| `data/help/admin/system-settings.md` | System config | Section-based |
| `data/help/admin/year-end-processing.md` | Year-end ops | Step-based |

### Reports (2 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/reports/reports-overview.md` | Report types | Section-based |
| `data/help/reports/analytics-dashboard.md` | Analytics | Section-based |
| `data/help/reports/export-reports.md` | Export options | Single chunk |

### WFH Swap (3 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/wfh-swap/wfh-swap-overview.md` | Feature overview | Single chunk |
| `data/help/wfh-swap/requesting-swap.md` | Request process | Step-based |
| `data/help/wfh-swap/responding-to-swaps.md` | Response workflow | Step-based |

### Technical (2 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/technical/troubleshooting.md` | Common issues | FAQ-based |
| `data/help/technical/keyboard-shortcuts.md` | Shortcuts | Single chunk |

### Scenario Transcripts / Training Videos (5 documents)
| File | Topic | Chunk Strategy |
|------|-------|----------------|
| `data/help/scenarios/scenario_transcripts.md` | **All 18 scenario narrations** | Step-based (by numbered step) |
| `nicegui_app/static/help/videos/pto-request.srt` | PTO request workflow narration | Step-based (by subtitle segment) |
| `nicegui_app/static/help/videos/pto-request.timeline.json` | Detailed step scripts with titles | Step-based (extract "script" + "title" fields) |
| `nicegui_app/static/help/videos/wfh-swap.srt` | WFH swap workflow narration | Step-based (by subtitle segment) |
| `nicegui_app/static/help/videos/wfh-swap.timeline.json` | Detailed step scripts with titles | Step-based (extract "script" + "title" fields) |

**Consolidated Transcript Coverage (18 scenarios):**

| Role | Scenario ID | Topic |
|------|-------------|-------|
| Employee | `pto-request` | Submit PTO request |
| Employee | `balance-dashboard` | Understanding balances |
| Employee | `calendar-navigation` | Calendar usage |
| Employee | `filter-requests` | Filtering requests |
| Employee | `employee-cancel-request` | Cancelling requests |
| Employee | `wfh-request` | WFH special circumstances |
| Employee | `wfh-swap` | Peer-to-peer WFH swap |
| Employee | `leave-type-rules` | Policy rules training |
| Manager | `manager-approval` | Approval workflow |
| Manager | `team-calendar` | Team calendar view |
| Manager | `pto-reports` | PTO reporting |
| Manager | `manager-carryover` | Carryover approvals |
| Manager | `manager-team-overview` | Team management |
| Manager | `manager-backdated-requests` | Backdated requests |
| Manager | `manager-deny-request` | Denying requests |
| Admin | `admin-user-management` | User management |
| Admin | `admin-departments` | Department management |
| Admin | `admin-system-settings` | System configuration |

**Note:** Timeline JSON files contain rich metadata including:
- `title`: Step title (e.g., "Login to Application")
- `description`: Step description
- `script`: Narration text (user-facing language)

Extract only `title`, `description`, and `script` fields for RAG indexing.
Do NOT include: `screenshot_path`, `element_bbox`, or file system paths.

---

## 3. Policy Documentation Inventory

| File | Content Type | Chunk Strategy |
|------|--------------|----------------|
| `handbook/handbook.md` | Official PTO policies | Section-based (Holidays, Vacation, Sick, etc.) |
| `.claude/rules/business-rules.md` | Technical policy rules | Rule-based (each ## heading) |
| `task/formulalogic.md` | Balance formulas | Formula-based |

---

## 4. Chunking Strategy

### Strategy Definitions

| Strategy | Description | Overlap |
|----------|-------------|---------|
| **Single chunk** | Entire document as one chunk | None |
| **Section-based** | Split on `##` headings | 1 sentence |
| **Step-based** | Split on numbered lists | None |
| **Rule-based** | Split on policy rules | 1 sentence |
| **Formula-based** | Each formula as separate chunk | Include context |
| **FAQ-based** | Each Q&A as separate chunk | Include category |

### Overlap Guidelines

- **Policy chunks**: Include 1-2 sentences overlap to preserve context
- **How-to chunks**: No overlap (steps are self-contained)
- **Formula chunks**: Include variable definitions in each chunk

---

## 5. Metadata Schema

Each chunk should include:

```json
{
  "source_file": "data/help/pto-requests/submit-request.md",
  "category": "help",
  "subcategory": "pto-requests",
  "topic": "submit-request",
  "chunk_type": "step-based",
  "chunk_index": 1,
  "total_chunks": 5,
  "audience": ["employee", "manager", "admin"],
  "last_updated": "2025-12-22"
}
```

---

## 6. Validation Checklist

Before indexing, verify each source:

- [ ] No code snippets (unless explaining to users)
- [ ] No database field names
- [ ] No API endpoints
- [ ] No secrets or credentials
- [ ] No employee names (use "[Employee]" placeholder)
- [ ] No internal URLs (except help links)

---

## 7. Update Modes

### Dry-Run
- Parse all sources
- Generate chunk previews
- Report statistics
- No actual indexing

### Incremental
- Detect changed files (git diff)
- Re-index only changed chunks
- Preserve unchanged embeddings

### Full Rebuild
- Clear existing index
- Re-process all sources
- Generate fresh embeddings
- Validate against schema

---

## 8. Statistics

| Metric | Count |
|--------|-------|
| Total help documents | 35 |
| Total policy documents | 3 |
| Scenario transcripts/timelines | 5 |
| **Scenarios covered** | **18** |
| Estimated chunks (help) | ~80 |
| Estimated chunks (policy) | ~25 |
| Estimated chunks (scenarios) | ~150 (18 scenarios × ~8 steps avg) |
| **Total estimated chunks** | **~255** |

---

## 9. Next Steps

1. **Validate sources** - Run forbidden content check
2. **Create chunking script** - Implement strategy per source type
3. **Generate embeddings** - Use appropriate embedding model
4. **Test retrieval** - Validate relevance with sample queries
5. **Deploy index** - Configure for MCP agent access

---

**END OF MANIFEST**
