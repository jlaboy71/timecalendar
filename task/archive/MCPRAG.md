# PTO Central - MCP & RAG Pre-Implementation Review

**Document Version**: 1.0  
**Created**: December 22, 2025  
**Purpose**: Final deep-scan review before implementing local MCP server and RAG knowledge base  
**For**: Claude Code (VS Code IDE)

---

## CRITICAL: Read This First

Before implementing MCP or RAG, you must perform a **comprehensive validation** of PTO Central to ensure:
1. All business logic is correctly implemented
2. All validation rules are enforced consistently
3. All balance calculations are mathematically correct
4. All status transitions follow the defined lifecycle
5. All audit logging is complete
6. No orphaned code or dead paths exist

**This document is your instruction set. Follow it sequentially.**

---

## PHASE 1: Deep Application Scan

### 1.1 Balance Formula Verification

**Objective**: Confirm all four balance formulas are implemented identically across ALL surfaces.

**The Canonical Formulas** (from `formulalogic.md`):
```
VACATION_AVAILABLE = vacation_total + vacation_carryover - vacation_used - vacation_pending
SICK_AVAILABLE     = sick_total + sick_carryover - sick_used - sick_pending
PERSONAL_AVAILABLE = personal_total + personal_carryover - personal_used - personal_pending
CHICAGO_LEAVE_AVAILABLE = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
```

**Files to Scan**:
```
src/models/pto_balance.py          # @property methods for *_available
src/services/balance_service.py    # Any balance calculations
src/services/pto_service.py        # Balance updates on submit/approve/deny/cancel
nicegui_app/pages/dashboard.py     # Display calculations
nicegui_app/pages/request_form.py  # Validation calculations
nicegui_app/pages/requests.py      # Any balance display
nicegui_app/pages/calendar.py      # Any balance display
```

**Verification Checklist**:
- [ ] `pto_balance.py` has `@property` for each `*_available` using exact formula
- [ ] No hardcoded calculations exist outside the model properties
- [ ] All UI pages call the model properties, not recalculating
- [ ] balance_service.py uses the model properties for validation
- [ ] No division by 8 errors (hours vs days confusion)

**Report Format**:
```
BALANCE FORMULA VERIFICATION
============================
Location: [file:line]
Formula Type: [vacation|sick|personal|chicago]
Status: [CORRECT|INCORRECT|MISSING]
Issue: [description if not correct]
```

---

### 1.2 Status Transition Validation

**Objective**: Confirm PTO request status transitions follow the defined lifecycle.

**Valid Transitions**:
```
PENDING  --> APPROVED   (via approve_request)
PENDING  --> DENIED     (via deny_request)
PENDING  --> CANCELLED  (via cancel_request, employee cancels own)
APPROVED --> CANCELLED  (via cancel_request, requires manager for approved)
```

**Invalid Transitions** (should be blocked):
```
APPROVED --> PENDING    (cannot un-approve)
DENIED   --> APPROVED   (cannot approve denied)
DENIED   --> PENDING    (cannot un-deny)
CANCELLED --> *         (terminal state)
```

**Files to Scan**:
```
src/services/pto_service.py        # approve_request, deny_request, cancel_request
src/constants.py                   # PTOStatus enum
nicegui_app/pages/requests.py      # UI actions available per status
nicegui_app/pages/manager_request_detail.py  # Manager actions per status
```

**Verification Checklist**:
- [ ] `approve_request()` only accepts PENDING requests
- [ ] `deny_request()` only accepts PENDING requests
- [ ] `cancel_request()` accepts PENDING (anyone) or APPROVED (with permission check)
- [ ] UI buttons are disabled/hidden for invalid transitions
- [ ] No direct status assignment bypassing service methods

**Report Format**:
```
STATUS TRANSITION VERIFICATION
==============================
Method: [method_name]
From Status: [status]
To Status: [status]
Guard Check: [present|missing]
Issue: [description if any]
```

---

### 1.3 Balance Update Verification

**Objective**: Confirm balance fields are updated correctly for each action.

**Expected Updates**:

| Action | Employee/Regular | Manager/Admin/Trusted |
|--------|------------------|----------------------|
| Submit | `pending += hours` | `used += hours` (auto-approve) |
| Approve | `pending -= hours`, `used += hours` | N/A |
| Deny | `pending -= hours` | N/A |
| Cancel (pending) | `pending -= hours` | `pending -= hours` |
| Cancel (approved) | `used -= hours` | `used -= hours` |

**Files to Scan**:
```
src/services/pto_service.py        # create_request, approve_request, deny_request, cancel_request
src/services/balance_service.py    # add_pending, remove_pending, move_pending_to_used, remove_used
```

**Verification Checklist**:
- [ ] `create_request()` adds to `pending` for regular employees
- [ ] `create_request()` adds to `used` for auto-approve cases
- [ ] `approve_request()` moves from `pending` to `used`
- [ ] `deny_request()` removes from `pending` only
- [ ] `cancel_request()` removes from correct field based on prior status
- [ ] All updates use the correct leave type field (vacation_pending vs sick_pending etc.)
- [ ] Chicago leave updates are conditional on user eligibility

**Report Format**:
```
BALANCE UPDATE VERIFICATION
===========================
Action: [submit|approve|deny|cancel]
Leave Type: [vacation|sick|personal|chicago]
Expected: [field] [+|-]= [hours]
Actual Code: [code snippet]
Status: [CORRECT|INCORRECT]
```

---

### 1.4 Auto-Approve Logic Verification

**Objective**: Confirm auto-approve triggers correctly and ONLY for correct conditions.

**Auto-Approve Conditions**:
```python
# Should auto-approve:
- User role is manager, admin, or superadmin
- AND leave type is in {vacation, sick, personal}
- AND NOT a vacation rollover request

# Should also auto-approve:
- User has is_trusted = True
- AND leave type is in {vacation, sick, personal}
- AND NOT a vacation rollover request

# Should NEVER auto-approve:
- Leave types: bereavement, fmla, jury_duty, voting, military, wfh
- ANY vacation rollover (carryover_from_year is set)
```

**Files to Scan**:
```
src/services/pto_service.py        # create_request auto-approve logic
src/models/user.py                 # is_trusted field
src/constants.py                   # TRUSTED_AUTO_APPROVE_TYPES, ALWAYS_REQUIRES_APPROVAL
```

**Verification Checklist**:
- [ ] Auto-approve checks user role correctly
- [ ] Auto-approve checks is_trusted correctly
- [ ] Auto-approve checks leave type against allowed set
- [ ] Vacation rollover detection works (carryover_from_year check)
- [ ] Vacation rollover NEVER auto-approves even for managers
- [ ] Auto-approved requests get status='approved' immediately
- [ ] Auto-approved requests update `used` not `pending`

---

### 1.5 Year-End Processing Verification

**Objective**: Confirm year-end processing handles all carryover rules correctly.

**Required Steps**:
1. Create new year balance for each active user
2. Calculate vacation_total based on tenure tier
3. Auto-carryover sick leave (up to policy max)
4. Auto-carryover Chicago paid leave (up to 16 hours)
5. Apply approved vacation carryover exceptions
6. Generate federal holidays for new year
7. Update year_end_status record

**Files to Scan**:
```
src/services/year_end_service.py   # run_year_end_processing and helpers
src/services/accrual_service.py    # Vacation tier calculation
src/models/year_end_status.py      # Status tracking
```

**Verification Checklist**:
- [ ] Sick carryover uses correct formula: `min(unused, max_carryover)`
- [ ] Chicago leave carryover caps at 16 hours
- [ ] Vacation does NOT auto-carryover
- [ ] Approved CarryoverRequest items are applied correctly
- [ ] Tenure tier lookup uses hire_date correctly
- [ ] New balance has correct initial values
- [ ] Year-end status prevents duplicate processing

---

### 1.6 Audit Logging Completeness

**Objective**: Confirm all auditable actions are logged.

**Required Audit Events**:
```
- pto_request_created
- pto_request_approved
- pto_request_denied
- pto_request_cancelled
- balance_adjusted (manual admin adjustment)
- carryover_approved
- carryover_denied
- user_created
- user_updated
- user_deleted
- wfh_swap_requested
- wfh_swap_accepted
- wfh_swap_declined
- wfh_swap_cancelled
- year_end_processed
```

**Files to Scan**:
```
src/services/audit_service.py      # log_action method and event types
src/services/pto_service.py        # Audit calls in each method
src/services/wfh_swap_service.py   # Audit calls for swap actions
src/services/year_end_service.py   # Audit call for year-end
```

**Verification Checklist**:
- [ ] Every service method that modifies data calls audit_service.log_action
- [ ] Audit includes: action_type, user_id, target_id, details dict
- [ ] Details dict contains before/after values where applicable
- [ ] No silent failures (audit in try block but action outside)

---

### 1.7 WFH Day Swap Verification

**Objective**: Confirm WFH swap feature follows its rules.

**WFH Swap Rules**:
- Peer-to-peer only (no manager approval)
- Both users must be wfh_swap_eligible
- Cannot swap same day
- Cannot swap with self
- Initiator can cancel pending
- Responder accepts or declines
- Status: pending → accepted/declined/cancelled

**Files to Scan**:
```
src/models/wfh_day_swap.py         # Model and status
src/services/wfh_swap_service.py   # All swap operations
src/services/audit_service.py      # Swap audit methods
nicegui_app/pages/wfh_swap.py      # UI implementation
.claude/rules/wfh-swap-rules.md    # Business rules
```

**Verification Checklist**:
- [ ] Eligibility check on both users
- [ ] Self-swap prevention
- [ ] Same-day swap prevention
- [ ] Only initiator can cancel
- [ ] Only responder can accept/decline
- [ ] Status transitions are correct
- [ ] Audit logging for all actions

---

### 1.8 Policy Resolution Verification

**Objective**: Confirm location-based policies resolve in correct order.

**Resolution Order**:
```
1. City-specific (e.g., location_city='Chicago', location_state='IL')
2. State-specific (e.g., location_state='IL', location_city=NULL)
3. Default (location_state=NULL, location_city=NULL)
```

**Files to Scan**:
```
src/services/accrual_service.py    # get_policy_for_employee
src/models/leave_policy.py         # Policy model
src/services/balance_service.py    # Chicago leave applicability
```

**Verification Checklist**:
- [ ] City+State match checked first
- [ ] State-only match checked second
- [ ] Default policy exists and is used as fallback
- [ ] Chicago employees get Chicago-specific sick carryover (80hrs)
- [ ] Chicago employees get Chicago Paid Leave allocation

---

## PHASE 2: RAG Knowledge Base Design

### 2.1 Directory-Based Auto-Discovery

**IMPORTANT**: RAG uses directory watching, NOT individual file indexing. This means:
- ✅ New files in watched directories are auto-discovered
- ✅ Modified files are auto-detected via hash comparison
- ✅ Deleted files are auto-removed from index
- ❌ Files outside watched directories are NOT discovered

**Watched Directories Configuration** (`rag_config.py`):

```python
# rag_config.py - RAG Directory Configuration

RAG_WATCHED_DIRECTORIES = [
    # Core Policy Documents (HIGHEST PRIORITY)
    {
        "path": "task/",
        "pattern": "*.md",
        "doc_type": "business_logic",
        "priority": 1,
        "description": "Business rules, formulas, specifications"
    },
    {
        "path": ".claude/rules/",
        "pattern": "*.md",
        "doc_type": "policy_rules",
        "priority": 1,
        "description": "Protected logic and business rules"
    },
    
    # Help Articles (HIGH PRIORITY)
    {
        "path": "data/help/",
        "pattern": "**/*.md",           # Recursive - all subdirectories
        "doc_type": "help_article",
        "priority": 2,
        "description": "User-facing help documentation"
    },
    
    # Training Transcripts (MEDIUM PRIORITY)
    {
        "path": "nicegui_app/static/help/videos/",
        "pattern": "**/transcript.txt",  # All transcript files in scenario folders
        "doc_type": "training_transcript",
        "priority": 3,
        "description": "Video training transcripts"
    },
    {
        "path": "nicegui_app/static/help/audio/",
        "pattern": "**/transcript.txt",
        "doc_type": "audio_transcript",
        "priority": 3,
        "description": "Audio narration transcripts"
    },
    
    # Technical Documentation (LOWER PRIORITY)
    {
        "path": ".",
        "pattern": "DEPLOYMENT.md",
        "doc_type": "technical_doc",
        "priority": 4,
        "description": "Deployment procedures"
    },
    {
        "path": ".",
        "pattern": "BACKUP_SETUP.md",
        "doc_type": "technical_doc",
        "priority": 4,
        "description": "Backup procedures"
    }
]

# Files to EXCLUDE (even if in watched directories)
RAG_EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.git/**",
    "**/venv/**",
    "**/*.pyc",
    "**/test_*.md",           # Test files
    "**/*_backup.md",         # Backup files
    "**/CHANGELOG*.md"        # Changelogs (too noisy)
]
```

### 2.2 What Gets Indexed

**Documents Automatically Discovered**:

| Directory | Pattern | Count | Content |
|-----------|---------|-------|---------|
| `task/` | `*.md` | ~10 | formulalogic, dayswap, media01, etc. |
| `.claude/rules/` | `*.md` | 7 | business-rules, wfh-swap-rules, etc. |
| `data/help/` | `**/*.md` | 38 | All help articles (recursive) |
| `static/help/videos/` | `**/transcript.txt` | TBD | Training transcripts (as you create them) |
| `static/help/audio/` | `**/transcript.txt` | TBD | Audio transcripts (as you create them) |

**Total Estimated**: ~55 files initially, growing as you add transcripts

### 2.3 Auto-Update System

**The Core Principle**: You run ONE command, it handles everything.

```bash
python scripts/rag_update.py
```

**What This Command Does**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Update Process                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: Scan Watched Directories                               │
│  ─────────────────────────────────────────────────────────────  │
│  For each directory in RAG_WATCHED_DIRECTORIES:                 │
│    - Find all files matching pattern                            │
│    - Exclude files matching RAG_EXCLUDE_PATTERNS                │
│    - Build list of current files                                │
│                                                                  │
│  STEP 2: Compare with Manifest                                  │
│  ─────────────────────────────────────────────────────────────  │
│  For each file found:                                           │
│    - If NOT in manifest → NEW file (needs indexing)             │
│    - If hash differs → MODIFIED file (needs re-indexing)        │
│    - If in manifest but not found → DELETED (remove from index) │
│                                                                  │
│  STEP 3: Process Changes                                        │
│  ─────────────────────────────────────────────────────────────  │
│    - Index new files (chunk + embed + store)                    │
│    - Re-index modified files (remove old chunks, add new)       │
│    - Remove deleted files from vector DB                        │
│    - Update manifest with new hashes                            │
│                                                                  │
│  STEP 4: Report                                                 │
│  ─────────────────────────────────────────────────────────────  │
│    - Show summary of changes                                    │
│    - Total chunks in knowledge base                             │
│    - Any errors encountered                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 RAG Manager Implementation

```python
# scripts/rag_update.py

"""
RAG Knowledge Base Update Script
Run this after adding/modifying content files.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions

class RAGManager:
    def __init__(self, 
                 project_root: str = ".",
                 vector_db_path: str = "data/vector_db",
                 manifest_path: str = "data/vector_db/index_manifest.json"):
        self.project_root = Path(project_root)
        self.vector_db_path = Path(vector_db_path)
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()
        
        # Initialize ChromaDB (local, no server needed)
        self.client = chromadb.PersistentClient(path=str(self.vector_db_path))
        self.collection = self.client.get_or_create_collection(
            name="pto_central_knowledge",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
    
    def _load_manifest(self) -> dict:
        """Load or create the index manifest."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "files": {}
        }
    
    def _save_manifest(self):
        """Save the manifest to disk."""
        self.manifest["last_updated"] = datetime.now().isoformat()
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _hash_file(self, file_path: Path) -> str:
        """Generate SHA256 hash of file contents."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _discover_files(self, config: list[dict]) -> dict[str, dict]:
        """Discover all files in watched directories."""
        from rag_config import RAG_EXCLUDE_PATTERNS
        import fnmatch
        
        discovered = {}
        
        for watch in config:
            base_path = self.project_root / watch["path"]
            pattern = watch["pattern"]
            
            if not base_path.exists():
                print(f"  ⚠️  Directory not found: {watch['path']}")
                continue
            
            # Find matching files
            if "**" in pattern:
                files = base_path.rglob(pattern.replace("**/", ""))
            else:
                files = base_path.glob(pattern)
            
            for file_path in files:
                # Check exclusions
                rel_path = str(file_path.relative_to(self.project_root))
                excluded = any(fnmatch.fnmatch(rel_path, exc) for exc in RAG_EXCLUDE_PATTERNS)
                
                if not excluded and file_path.is_file():
                    discovered[rel_path] = {
                        "doc_type": watch["doc_type"],
                        "priority": watch["priority"],
                        "current_hash": self._hash_file(file_path)
                    }
        
        return discovered
    
    def check_status(self) -> dict:
        """Check what needs to be updated without making changes."""
        from rag_config import RAG_WATCHED_DIRECTORIES
        
        current_files = self._discover_files(RAG_WATCHED_DIRECTORIES)
        indexed_files = set(self.manifest.get("files", {}).keys())
        current_file_set = set(current_files.keys())
        
        new_files = current_file_set - indexed_files
        deleted_files = indexed_files - current_file_set
        
        modified_files = []
        for file_path in current_file_set & indexed_files:
            if current_files[file_path]["current_hash"] != self.manifest["files"][file_path].get("hash"):
                modified_files.append(file_path)
        
        return {
            "new": list(new_files),
            "modified": modified_files,
            "deleted": list(deleted_files),
            "unchanged": len(current_file_set) - len(new_files) - len(modified_files),
            "total_indexed": len(indexed_files),
            "total_discovered": len(current_files),
            "is_stale": bool(new_files or modified_files or deleted_files)
        }
    
    def update(self, dry_run: bool = False) -> dict:
        """Perform the update, indexing new/modified files."""
        from rag_config import RAG_WATCHED_DIRECTORIES
        
        status = self.check_status()
        results = {"indexed": [], "reindexed": [], "removed": [], "errors": []}
        
        if dry_run:
            print("\n🔍 DRY RUN - No changes will be made\n")
            return status
        
        current_files = self._discover_files(RAG_WATCHED_DIRECTORIES)
        
        # Index new files
        for file_path in status["new"]:
            try:
                self._index_file(file_path, current_files[file_path])
                results["indexed"].append(file_path)
                print(f"  ✅ Indexed: {file_path}")
            except Exception as e:
                results["errors"].append({"file": file_path, "error": str(e)})
                print(f"  ❌ Error indexing {file_path}: {e}")
        
        # Re-index modified files
        for file_path in status["modified"]:
            try:
                self._remove_file_chunks(file_path)
                self._index_file(file_path, current_files[file_path])
                results["reindexed"].append(file_path)
                print(f"  🔄 Re-indexed: {file_path}")
            except Exception as e:
                results["errors"].append({"file": file_path, "error": str(e)})
                print(f"  ❌ Error re-indexing {file_path}: {e}")
        
        # Remove deleted files
        for file_path in status["deleted"]:
            try:
                self._remove_file_chunks(file_path)
                del self.manifest["files"][file_path]
                results["removed"].append(file_path)
                print(f"  🗑️  Removed: {file_path}")
            except Exception as e:
                results["errors"].append({"file": file_path, "error": str(e)})
        
        self._save_manifest()
        return results
    
    def _index_file(self, file_path: str, file_info: dict):
        """Index a single file into the vector database."""
        full_path = self.project_root / file_path
        content = full_path.read_text(encoding='utf-8')
        
        # Chunk the content
        chunks = self._chunk_content(content, file_info["doc_type"])
        
        # Add to vector DB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path}::chunk_{i}"
            self.collection.add(
                ids=[chunk_id],
                documents=[chunk["text"]],
                metadatas=[{
                    "source_file": file_path,
                    "doc_type": file_info["doc_type"],
                    "priority": file_info["priority"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "section": chunk.get("section", ""),
                    "indexed_at": datetime.now().isoformat()
                }]
            )
        
        # Update manifest
        self.manifest["files"][file_path] = {
            "hash": file_info["current_hash"],
            "indexed_at": datetime.now().isoformat(),
            "chunk_count": len(chunks),
            "doc_type": file_info["doc_type"]
        }
    
    def _remove_file_chunks(self, file_path: str):
        """Remove all chunks for a file from the vector database."""
        # Get chunk count from manifest
        file_info = self.manifest["files"].get(file_path, {})
        chunk_count = file_info.get("chunk_count", 100)  # Default high if unknown
        
        # Remove chunks
        chunk_ids = [f"{file_path}::chunk_{i}" for i in range(chunk_count)]
        try:
            self.collection.delete(ids=chunk_ids)
        except:
            pass  # Chunks may not exist
    
    def _chunk_content(self, content: str, doc_type: str) -> list[dict]:
        """Split content into chunks based on document type."""
        chunks = []
        
        if doc_type in ["business_logic", "policy_rules"]:
            # Chunk by markdown sections
            sections = content.split("\n## ")
            for i, section in enumerate(sections):
                if section.strip():
                    section_title = section.split("\n")[0] if i > 0 else "Introduction"
                    chunks.append({
                        "text": ("## " + section) if i > 0 else section,
                        "section": section_title.strip("#").strip()
                    })
        
        elif doc_type == "training_transcript":
            # Chunk by timestamp markers or paragraphs
            paragraphs = content.split("\n\n")
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) < 1500:  # ~500 tokens
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append({"text": current_chunk.strip()})
                    current_chunk = para + "\n\n"
            if current_chunk.strip():
                chunks.append({"text": current_chunk.strip()})
        
        else:
            # Default: chunk by paragraphs with overlap
            paragraphs = content.split("\n\n")
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) < 1500:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk.strip():
                        chunks.append({"text": current_chunk.strip()})
                    current_chunk = para + "\n\n"
            if current_chunk.strip():
                chunks.append({"text": current_chunk.strip()})
        
        return chunks if chunks else [{"text": content}]


def main():
    """Main entry point for RAG update script."""
    import sys
    
    print("=" * 60)
    print("PTO Central - RAG Knowledge Base Update")
    print("=" * 60)
    
    manager = RAGManager()
    
    # Check status first
    print("\n📊 Checking knowledge base status...\n")
    status = manager.check_status()
    
    print(f"  Total files discovered: {status['total_discovered']}")
    print(f"  Currently indexed: {status['total_indexed']}")
    print(f"  New files: {len(status['new'])}")
    print(f"  Modified files: {len(status['modified'])}")
    print(f"  Deleted files: {len(status['deleted'])}")
    print(f"  Unchanged: {status['unchanged']}")
    
    if not status["is_stale"]:
        print("\n✅ Knowledge base is up to date. No changes needed.")
        return
    
    # Show what will change
    if status["new"]:
        print("\n📁 New files to index:")
        for f in status["new"]:
            print(f"    + {f}")
    
    if status["modified"]:
        print("\n📝 Modified files to re-index:")
        for f in status["modified"]:
            print(f"    ~ {f}")
    
    if status["deleted"]:
        print("\n🗑️  Deleted files to remove:")
        for f in status["deleted"]:
            print(f"    - {f}")
    
    # Confirm and run
    if "--yes" in sys.argv or "-y" in sys.argv:
        confirm = "y"
    else:
        confirm = input("\n🔄 Proceed with update? [y/N]: ").strip().lower()
    
    if confirm == "y":
        print("\n⏳ Updating knowledge base...\n")
        results = manager.update()
        
        print("\n" + "=" * 60)
        print("Update Complete")
        print("=" * 60)
        print(f"  Indexed: {len(results['indexed'])} files")
        print(f"  Re-indexed: {len(results['reindexed'])} files")
        print(f"  Removed: {len(results['removed'])} files")
        if results["errors"]:
            print(f"  Errors: {len(results['errors'])}")
            for err in results["errors"]:
                print(f"    ❌ {err['file']}: {err['error']}")
        
        # Final count
        final_status = manager.check_status()
        print(f"\n  Total chunks in knowledge base: {manager.collection.count()}")
    else:
        print("\n❌ Update cancelled.")


if __name__ == "__main__":
    main()
```

### 2.5 Startup Stale Check (Optional)

Add this to `nicegui_app/main.py` to alert admins when RAG needs updating:

```python
# In nicegui_app/main.py - add to startup

def check_rag_freshness() -> Optional[dict]:
    """Check if RAG knowledge base needs updating."""
    try:
        from scripts.rag_update import RAGManager
        manager = RAGManager()
        status = manager.check_status()
        
        if status["is_stale"]:
            return {
                "stale": True,
                "new_files": len(status["new"]),
                "modified_files": len(status["modified"]),
                "deleted_files": len(status["deleted"]),
                "message": (
                    f"Knowledge base needs update: "
                    f"{len(status['new'])} new, "
                    f"{len(status['modified'])} modified, "
                    f"{len(status['deleted'])} deleted files"
                )
            }
        return {"stale": False}
    except Exception as e:
        # RAG not configured yet - that's OK
        return None

# Store result for admin dashboard
app.storage.general['rag_status'] = check_rag_freshness()
```

**Admin Dashboard Alert** (add to `admin_dashboard.py`):

```python
# Show RAG status alert if stale
rag_status = app.storage.general.get('rag_status')
if rag_status and rag_status.get('stale'):
    with ui.card().classes('w-full bg-amber-50 border-l-4 border-amber-500 p-4 mb-4'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('warning', color='amber-600')
            ui.label('Knowledge Base Needs Update').classes('font-semibold text-amber-800')
        ui.label(rag_status['message']).classes('text-amber-700 text-sm mt-1')
        ui.label('Run: python scripts/rag_update.py').classes('text-amber-600 text-xs font-mono mt-2')
```

### 2.6 When You Need to Intervene

| Scenario | Auto-Handled? | Your Action |
|----------|---------------|-------------|
| Edit existing help file | ✅ YES | Run `rag_update.py` |
| Add new help file to `data/help/` | ✅ YES | Run `rag_update.py` |
| Add new transcript to `static/help/videos/*/` | ✅ YES | Run `rag_update.py` |
| Delete a file | ✅ YES | Run `rag_update.py` |
| Add file to NEW directory | ❌ NO | Add directory to `rag_config.py`, then run update |
| Rename a file | ✅ YES | Run `rag_update.py` (treats as delete + add) |

### 2.7 Manifest File Structure

Location: `data/vector_db/index_manifest.json`

```json
{
  "created_at": "2025-12-22T10:30:00Z",
  "last_updated": "2025-12-22T14:45:00Z",
  "files": {
    "task/formulalogic.md": {
      "hash": "a1b2c3d4e5f6...",
      "indexed_at": "2025-12-22T10:30:00Z",
      "chunk_count": 45,
      "doc_type": "business_logic"
    },
    "data/help/getting-started/welcome.md": {
      "hash": "f6e5d4c3b2a1...",
      "indexed_at": "2025-12-22T10:30:00Z",
      "chunk_count": 8,
      "doc_type": "help_article"
    },
    "nicegui_app/static/help/videos/submit-request/transcript.txt": {
      "hash": "1a2b3c4d5e6f...",
      "indexed_at": "2025-12-22T14:45:00Z",
      "chunk_count": 12,
      "doc_type": "training_transcript"
    }
  }
}
```

### 2.8 Chunking Strategy

| Document Type | Strategy | Chunk Size | Overlap |
|---------------|----------|------------|---------|
| `business_logic` | By ## section headers | Variable | None (sections are atomic) |
| `policy_rules` | By ## section headers | Variable | None |
| `help_article` | By paragraph | ~500 tokens | 50 tokens |
| `training_transcript` | By paragraph/timestamp | ~500 tokens | 50 tokens |
| `technical_doc` | By paragraph | ~500 tokens | 50 tokens |

### 2.9 Quick Reference Commands

```bash
# Check status without making changes
python scripts/rag_update.py --dry-run

# Update with confirmation prompt
python scripts/rag_update.py

# Update without confirmation (for scripts/automation)
python scripts/rag_update.py --yes

# Full rebuild (delete everything and re-index)
python scripts/rag_update.py --rebuild
```

---

## PHASE 3: MCP Server Design (Read-Only First)

### 3.1 Read-Only Tools (Safe to Implement)

```python
@mcp.tool()
def get_employee_balance(user_id: int, year: int = 2025) -> dict:
    """Get PTO balance for an employee. READ-ONLY."""
    pass

@mcp.tool()
def get_team_calendar(department_id: int, month: int, year: int) -> dict:
    """Get team calendar showing who is out. READ-ONLY."""
    pass

@mcp.tool()
def get_pending_requests(manager_id: int) -> list[dict]:
    """Get pending requests for a manager to review. READ-ONLY."""
    pass

@mcp.tool()
def get_market_holidays(year: int) -> list[dict]:
    """Get market holidays for a year. READ-ONLY."""
    pass

@mcp.tool()
def check_coverage(department_id: int, start_date: str, end_date: str) -> dict:
    """Check team coverage for a date range. READ-ONLY."""
    pass

@mcp.tool()
def get_policy_info(location_state: str, location_city: str = None) -> dict:
    """Get leave policy for a location. READ-ONLY."""
    pass
```

### 3.2 Write Tools (Implement LATER with Confirmation)

```python
# PHASE 2 - Require UI confirmation before execution
@mcp.tool()
def submit_pto_request(...) -> dict:
    """Submit a PTO request. REQUIRES CONFIRMATION."""
    pass

@mcp.tool()
def approve_request(request_id: int, approver_id: int) -> dict:
    """Approve a pending request. REQUIRES CONFIRMATION."""
    pass
```

### 3.3 Security Configuration

```python
# mcp_server/config.py

MCP_CONFIG = {
    # Bind to localhost ONLY
    "host": "127.0.0.1",
    "port": 8765,
    
    # No external connections
    "allow_remote": False,
    
    # Read-only mode (Phase 1)
    "read_only": True,
    
    # Logging
    "log_all_requests": True,
    "log_path": "logs/mcp_access.log",
    
    # Rate limiting (prevent runaway queries)
    "max_requests_per_minute": 60,
    
    # Timeout
    "request_timeout_seconds": 30
}
```

---

## PHASE 4: Final Review Checklist

Before implementing MCP/RAG, confirm ALL items are checked:

### Logic Verification
- [ ] All 4 balance formulas verified in all locations
- [ ] All status transitions verified
- [ ] All balance updates verified
- [ ] Auto-approve logic verified
- [ ] Year-end processing verified
- [ ] WFH swap logic verified
- [ ] Policy resolution verified

### Data Integrity
- [ ] No orphaned requests (requests without valid user)
- [ ] No negative balances where not allowed (sick, personal, chicago)
- [ ] All pending requests have corresponding pending balance
- [ ] All approved requests have corresponding used balance
- [ ] Audit log has no gaps

### Code Quality
- [ ] No hardcoded values that should be in constants.py
- [ ] No duplicate logic (DRY principle)
- [ ] All imports resolve
- [ ] No syntax errors (py_compile all files)
- [ ] Tests pass (pytest)

### Security
- [ ] No SQL injection vulnerabilities
- [ ] No XSS in UI templates
- [ ] Password hashing verified (bcrypt)
- [ ] Session management secure
- [ ] Rate limiting on login

### RAG Readiness
- [ ] All help files exist and are complete
- [ ] formulalogic.md is current
- [ ] business-rules.md is current
- [ ] No contradictions between documents

### MCP Readiness
- [ ] Database schema is stable
- [ ] Service methods have clear interfaces
- [ ] No circular dependencies
- [ ] Error handling is consistent

---

## PHASE 5: Scan Execution Commands

Run these commands to perform the scan:

```bash
# 1. Syntax check all Python files
find . -name "*.py" -exec python -m py_compile {} \;

# 2. Run test suite
python -m pytest tests/ -v --tb=short

# 3. Check for TODO/FIXME comments (potential incomplete work)
grep -rn "TODO\|FIXME\|XXX\|HACK" src/ nicegui_app/ --include="*.py"

# 4. Check for print statements (should use logging)
grep -rn "print(" src/ nicegui_app/ --include="*.py" | grep -v "__pycache__"

# 5. Check for hardcoded values
grep -rn "= 8\|= 40\|= 16\|= 80" src/ --include="*.py"

# 6. Verify all imports
python -c "import src.services.pto_service; import src.services.balance_service; import src.services.year_end_service; print('All critical imports OK')"

# 7. Database integrity check
python -c "
from src.database import get_db
from src.models import PTORequest, PTOBalance, User
db = next(get_db())
orphaned = db.query(PTORequest).filter(~PTORequest.user_id.in_(db.query(User.id))).count()
print(f'Orphaned requests: {orphaned}')
"
```

---

## PHASE 6: Output Report Template

After completing the scan, generate a report in this format:

```markdown
# PTO Central Pre-Implementation Scan Report

**Scan Date**: [DATE]
**Scanned By**: Claude Code
**PTO Central Version**: [from currentcore.md]

## Executive Summary
- Total Issues Found: [N]
- Critical: [N]
- Warning: [N]
- Info: [N]
- Ready for MCP/RAG: [YES/NO]

## Balance Formula Verification
| Location | Formula | Status |
|----------|---------|--------|
| pto_balance.py:vacation_available | CORRECT | ✅ |
| ... | ... | ... |

## Status Transition Verification
| Method | Guards | Status |
|--------|--------|--------|
| approve_request | Checks PENDING | ✅ |
| ... | ... | ... |

## Issues Found

### Critical (Must Fix)
1. [Issue description]
   - File: [path]
   - Line: [number]
   - Fix: [recommendation]

### Warnings (Should Fix)
1. [Issue description]
   - File: [path]
   - Recommendation: [suggestion]

### Info (Nice to Have)
1. [Issue description]

## RAG Indexing Plan
- Files to index: [N]
- Estimated chunks: [N]
- Storage estimate: [X MB]

## MCP Implementation Plan
- Read-only tools: [N]
- Write tools (Phase 2): [N]
- Estimated development time: [X hours]

## Recommendation
[PROCEED / HOLD - with reasoning]
```

---

## Appendix: Key File Locations Quick Reference

```
BUSINESS LOGIC
==============
task/formulalogic.md                    # Source of truth for all formulas
.claude/rules/business-rules.md         # Policy documentation
.claude/rules/wfh-swap-rules.md         # WFH swap specification
.claude/rules/protected-logic.md        # Files requiring approval to modify

CORE SERVICES (Protected)
=========================
src/services/pto_service.py             # Request lifecycle
src/services/balance_service.py         # Balance calculations
src/services/year_end_service.py        # Year-end processing
src/services/accrual_service.py         # Tenure/policy resolution
src/services/wfh_swap_service.py        # WFH swap operations

MODELS
======
src/models/pto_balance.py               # Balance model with @property formulas
src/models/pto_request.py               # Request model
src/models/user.py                      # User model with roles
src/models/wfh_day_swap.py              # WFH swap model

CONSTANTS
=========
src/constants.py                        # Enums and constants

HELP CONTENT
============
data/help/                              # 38 help article files

DATABASE
========
pto_central.db                          # SQLite database (DO NOT COMMIT)
alembic/versions/                       # Migration scripts
```

---

**END OF DOCUMENT**

When you complete the scan, report findings in the format specified in Phase 6.
Do not proceed with MCP/RAG implementation until all Critical issues are resolved.
