"""
Doctrine Path Validation Script
Verifies all file paths referenced in system_identity.md actually exist.
"""

import re
import os
from pathlib import Path


def validate_doctrine_paths():
    """Verify all file paths in system_identity.md actually exist."""

    doctrine_path = Path("task/system_identity.md")
    if not doctrine_path.exists():
        print("ERROR: system_identity.md not found")
        return False, [], []

    content = doctrine_path.read_text(encoding='utf-8')

    # Extract file paths (various patterns)
    patterns = [
        r'`([a-zA-Z_./]+\.py)`',           # Python files
        r'`([a-zA-Z_./]+\.md)`',           # Markdown files
        r'`(src/[^`\s]+)`',                # src/ paths
        r'`(nicegui_app/[^`\s]+)`',        # UI paths
        r'`(mcp/[^`\s]+)`',                # MCP paths
        r'`(\.claude/[^`\s]+)`',           # Rules paths
        r'`(data/[^`\s]+)`',               # Data paths
        r'`(scripts/[^`\s]+)`',            # Scripts paths
        r'`(alembic/[^`\s]+)`',            # Migration paths
        r'`(task/[^`\s]+)`',               # Task paths
    ]

    all_paths = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Clean up the path
            clean_path = match.strip('`').strip()
            # Skip patterns that are clearly not file paths
            if clean_path and not clean_path.startswith('//') and '`' not in clean_path:
                # Skip code examples like function calls
                if '(' not in clean_path and ')' not in clean_path:
                    all_paths.add(clean_path)

    print(f"Found {len(all_paths)} file path references")
    print("=" * 60)

    valid = []
    invalid = []

    for path in sorted(all_paths):
        # Handle paths that might have line numbers
        clean_path = path.split(':')[0] if ':' in path else path

        if os.path.exists(clean_path):
            valid.append(path)
            print(f"  [OK] {path}")
        else:
            # Check if it's a directory pattern
            if '*' in path or path.endswith('/'):
                parent = Path(path.rstrip('/*'))
                if parent.exists():
                    valid.append(path)
                    print(f"  [OK] {path} (directory pattern)")
                    continue
            invalid.append(path)
            print(f"  [!!] {path} - NOT FOUND")

    print("=" * 60)
    print(f"\nSummary: {len(valid)} valid | {len(invalid)} invalid")

    if invalid:
        print("\n[WARNING] Invalid paths require review:")
        for p in invalid:
            print(f"  - {p}")
        return False, valid, invalid

    print("\n[SUCCESS] All file paths validated")
    return True, valid, invalid


def validate_capability_entry_points():
    """Verify claimed capability entry points exist."""

    print("\n" + "=" * 60)
    print("Capability Entry Point Verification")
    print("=" * 60)

    # Entry points claimed in the doctrine
    entry_points = {
        "PTO Request Submission": "nicegui_app/pages/request_form.py",
        "Balance Dashboard": "nicegui_app/pages/dashboard.py",
        "WFH Day Swap": "nicegui_app/pages/wfh_swap.py",
        "Manager Approvals": "nicegui_app/pages/manager_request_detail.py",
        "Year-End Processing": "nicegui_app/pages/admin_year_end.py",
        "MCP Tools": "mcp/pto_central_mcp.py",
        "Smart Scheduler Agent": "src/services/agent_service.py",
        "Team Calendar": "nicegui_app/pages/calendar.py",
        "Reports": "nicegui_app/pages/reports.py",
        "Help Center": "nicegui_app/pages/help.py",
        "Admin Dashboard": "nicegui_app/pages/admin_dashboard.py",
        "Email Service": "src/services/email_service.py",
        "Audit Service": "src/services/audit_service.py",
        "Balance Service": "src/services/balance_service.py",
        "PTO Service": "src/services/pto_service.py",
    }

    valid = []
    invalid = []

    for capability, path in entry_points.items():
        if os.path.exists(path):
            valid.append((capability, path))
            print(f"  [OK] {capability}: {path}")
        else:
            invalid.append((capability, path))
            print(f"  [!!] {capability}: {path} - NOT FOUND")

    print("=" * 60)
    print(f"\nCapabilities: {len(valid)} verified | {len(invalid)} missing")

    return len(invalid) == 0, valid, invalid


if __name__ == "__main__":
    print("=" * 60)
    print("PTO Central Doctrine Path Validation")
    print("=" * 60 + "\n")

    # Run path validation
    paths_ok, valid_paths, invalid_paths = validate_doctrine_paths()

    # Run capability verification
    caps_ok, valid_caps, invalid_caps = validate_capability_entry_points()

    # Final result
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    if paths_ok and caps_ok:
        print("\n[PASS] All doctrine validations passed")
        exit(0)
    else:
        print("\n[FAIL] Some validations failed - review required")
        exit(1)
