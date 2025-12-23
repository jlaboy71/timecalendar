"""
Doctrine Freshness Check Script
Compares doctrine file dates against source file dates.
Flags doctrine as STALE if source files are newer.
"""

import os
import json
from datetime import datetime
from pathlib import Path


DOCTRINE_FILES = [
    "task/system_identity.md",
    "task/creator_profile.md",
    "task/knowledge_contract.md"
]

SOURCE_FILES = [
    ".claude/rules/business-rules.md",
    ".claude/rules/protected-logic.md",
    ".claude/rules/wfh-swap-rules.md",
    ".claude/rules/database.md",
    ".claude/rules/code-style.md",
    ".claude/rules/ui-patterns.md",
    "src/services/pto_service.py",
    "src/services/balance_service.py",
    "src/services/wfh_swap_service.py",
    "src/services/agent_service.py",
    "src/models/pto_balance.py",
    "src/models/pto_request.py",
    "src/models/user.py",
    "mcp/pto_central_mcp.py",
    "mcp/mcp_server.py",
    "nicegui_app/components/theme.py",
    "task/JoseMLaboy.md"
]


def check_freshness():
    """Check if doctrine is fresher than all source files."""

    results = {
        "status": "FRESH",
        "doctrine_date": None,
        "details": [],
        "stale_sources": []
    }

    # Get oldest doctrine file date
    doctrine_dates = []
    for df in DOCTRINE_FILES:
        if os.path.exists(df):
            mtime = os.path.getmtime(df)
            doctrine_dates.append((df, mtime))
        else:
            results["status"] = "MISSING"
            results["details"].append(f"Doctrine file not found: {df}")

    if not doctrine_dates:
        results["status"] = "MISSING"
        results["details"].append("No doctrine files found")
        return results

    # Find oldest doctrine date
    oldest_doctrine_file, oldest_doctrine = min(doctrine_dates, key=lambda x: x[1])
    oldest_doctrine_dt = datetime.fromtimestamp(oldest_doctrine)
    results["doctrine_date"] = oldest_doctrine_dt.isoformat()
    results["oldest_doctrine_file"] = oldest_doctrine_file

    # Check each source file
    stale_sources = []
    for sf in SOURCE_FILES:
        if os.path.exists(sf):
            mtime = os.path.getmtime(sf)
            if mtime > oldest_doctrine:
                source_dt = datetime.fromtimestamp(mtime)
                stale_sources.append({
                    "file": sf,
                    "modified": source_dt.isoformat(),
                    "doctrine_date": oldest_doctrine_dt.isoformat(),
                    "hours_newer": round((mtime - oldest_doctrine) / 3600, 2)
                })

    if stale_sources:
        results["status"] = "STALE"
        results["stale_sources"] = stale_sources
        results["recommendation"] = "Re-run System Identity Doctrine Genesis"
    else:
        results["details"].append("All source files are older than doctrine")

    return results


def print_report(result):
    """Print a human-readable freshness report."""

    print("=" * 60)
    print("PTO Central Doctrine Freshness Check")
    print("=" * 60)
    print()

    status_icon = {
        "FRESH": "[OK]",
        "STALE": "[!!]",
        "MISSING": "[XX]"
    }

    print(f"Status: {status_icon.get(result['status'], '[??]')} {result['status']}")
    print()

    if result.get("doctrine_date"):
        print(f"Doctrine Date: {result['doctrine_date']}")
        print(f"Oldest File: {result.get('oldest_doctrine_file', 'N/A')}")
        print()

    if result.get("details"):
        print("Details:")
        for detail in result["details"]:
            print(f"  - {detail}")
        print()

    if result.get("stale_sources"):
        print("STALE SOURCE FILES (modified after doctrine generation):")
        print("-" * 60)
        for source in result["stale_sources"]:
            print(f"  File: {source['file']}")
            print(f"  Modified: {source['modified']}")
            print(f"  Hours newer: {source['hours_newer']}")
            print()

    if result.get("recommendation"):
        print("=" * 60)
        print(f"RECOMMENDATION: {result['recommendation']}")
        print("=" * 60)


if __name__ == "__main__":
    result = check_freshness()

    # Print human-readable report
    print_report(result)

    # Also output JSON for programmatic use
    print("\n--- JSON Output ---")
    print(json.dumps(result, indent=2))

    # Exit code
    if result["status"] == "STALE":
        print("\n[WARNING] Doctrine is STALE - Source files have been modified since generation")
        exit(1)
    elif result["status"] == "MISSING":
        print("\n[ERROR] Doctrine files are MISSING")
        exit(2)
    else:
        print("\n[OK] Doctrine is FRESH")
        exit(0)
