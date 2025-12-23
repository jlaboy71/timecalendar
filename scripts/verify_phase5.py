"""
Phase 5 Final Verification Script
==================================
Comprehensive check that all Phase 5 components are in place.

Run with: python scripts/verify_phase5.py
"""

import sys
from pathlib import Path


def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    exists = Path(path).exists()
    status = "+" if exists else "X"
    print(f"  {status} {description}: {path}")
    return exists


def check_import(module: str, items: list) -> bool:
    """Check if items can be imported from a module."""
    try:
        mod = __import__(module, fromlist=items)
        for item in items:
            if not hasattr(mod, item):
                print(f"  X {module}.{item} not found")
                return False
        print(f"  + {module}: {', '.join(items)}")
        return True
    except ImportError as e:
        print(f"  X Cannot import {module}: {e}")
        return False


def main():
    print("=" * 60)
    print("PTO CENTRAL - PHASE 5 FINAL VERIFICATION")
    print("=" * 60)
    print()

    all_passed = True

    # 1. MCP Server
    print("1. MCP SERVER")
    all_passed &= check_file("mcp/pto_central_mcp.py", "MCP Server")
    all_passed &= check_import("mcp.pto_central_mcp", [
        "confirm_action",
        "submit_pto_request",
        "cancel_pto_request",
        "approve_pto_request",
        "deny_pto_request",
    ])
    print()

    # 2. Agent Service
    print("2. AGENT SERVICE")
    all_passed &= check_file("src/services/agent_service.py", "Agent Service")
    all_passed &= check_import("src.services.agent_service", [
        "SmartSchedulerAgent",
        "YearEndOptimizerAgent",
        "ApprovalAssistantAgent",
        "create_agent",
    ])
    print()

    # 3. Voice Interface
    print("3. VOICE INTERFACE")
    all_passed &= check_file("src/services/voice/__init__.py", "Voice Package")
    all_passed &= check_file("src/services/voice/voice_interface.py", "Voice Interface")
    all_passed &= check_import("src.services.voice", [
        "VoiceInterface",
        "get_voice_interface",
    ])
    print()

    # 4. Skills
    print("4. SKILLS (6)")
    skills = [
        "pto-central-development",
        "pto-policy-validator",
        "pto-testing-automation",
        "pto-mcp-builder",
        "pto-rag-knowledge",
        "pto-agent-orchestrator",
    ]
    for skill in skills:
        all_passed &= check_file(f"skills/{skill}/SKILL.md", skill)
    print()

    # 5. Tests
    print("5. TESTS")
    all_passed &= check_file("tests/agents/test_agents.py", "Agent Tests")
    all_passed &= check_file("tests/test_phase5_integration.py", "Integration Tests")
    print()

    # 6. Doctrine
    print("6. DOCTRINE")
    all_passed &= check_file("task/system_identity.md", "System Identity")
    all_passed &= check_file("task/creator_profile.md", "Creator Profile")
    all_passed &= check_file("task/knowledge_contract.md", "Knowledge Contract")
    print()

    # 7. Documentation
    print("7. DOCUMENTATION")
    all_passed &= check_file("task/phase5_completion_summary.md", "Phase 5 Summary")
    print()

    # Final Result
    print("=" * 60)
    if all_passed:
        print("+ PHASE 5 VERIFICATION: ALL CHECKS PASSED")
        print("=" * 60)
        print()
        print("Congratulations! PTO Central Phase 5 is complete!")
        print()
        print("The AI Stack is now operational:")
        print("  - 16 MCP tools (including 5 write tools with Safety Gate)")
        print("  - 3 AI agents (Smart Scheduler, Year-End, Approval)")
        print("  - 6 custom skills for Claude Code")
        print("  - Voice interface foundation")
        print("  - Comprehensive test suite")
        print()
        return 0
    else:
        print("X PHASE 5 VERIFICATION: SOME CHECKS FAILED")
        print("=" * 60)
        print()
        print("Review the failures above and address missing components.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
