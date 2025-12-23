"""
PTO Central MCP Server - Inspector Agent (Read-Only Tools)

Phase 4 Read-Only MCP Tools per MCPRAGv2.md governance.
These tools provide INSPECTION capabilities only - NO write operations.

Tools:
1. query_rag_corpus - Semantic search of Safe Corpus index
2. check_balance_integrity - Live verified math check (read-only)
3. verify_policy_parity - Compare policy docs vs implementation

Security:
- All tools are READ-ONLY
- No database modifications allowed
- Audit logging for all invocations
"""

import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import wraps
import time

# Rate limiting state
_rate_limits: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_CALLS = 30  # max calls per window

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAG_INDEX_PATH = PROJECT_ROOT / "data" / "rag_index.json"
BUSINESS_RULES_PATH = PROJECT_ROOT / ".claude" / "rules" / "business-rules.md"
FORMULA_LOGIC_PATH = PROJECT_ROOT / "task" / "formulalogic.md"


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


def rate_limit(tool_name: str):
    """Decorator to enforce rate limiting on tools."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if tool_name not in _rate_limits:
                _rate_limits[tool_name] = []

            # Remove old timestamps
            _rate_limits[tool_name] = [
                ts for ts in _rate_limits[tool_name]
                if now - ts < RATE_LIMIT_WINDOW
            ]

            if len(_rate_limits[tool_name]) >= RATE_LIMIT_MAX_CALLS:
                raise RateLimitError(
                    f"Rate limit exceeded for {tool_name}. "
                    f"Max {RATE_LIMIT_MAX_CALLS} calls per {RATE_LIMIT_WINDOW}s."
                )

            _rate_limits[tool_name].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def audit_log(tool_name: str, params: Dict[str, Any], result: Any):
    """Log tool invocation for audit trail."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.database import get_db
        from src.services.audit_service import AuditService

        db = next(get_db())
        try:
            AuditService.log(
                db=db,
                action=f"mcp_inspector_{tool_name}",
                user_id=None,
                username="mcp_inspector",
                details=json.dumps({
                    "tool": tool_name,
                    "params": {k: str(v) for k, v in params.items()},
                    "result_summary": str(result)[:200]
                })
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to log MCP audit: {e}")


# =============================================================================
# TOOL 1: query_rag_corpus
# =============================================================================

@rate_limit("query_rag_corpus")
def query_rag_corpus(natural_language_query: str) -> Dict[str, Any]:
    """
    Semantic search of the Safe Corpus index.

    Returns relevant chunks from policies and help documentation.
    This is READ-ONLY - no modifications to any data.

    Args:
        natural_language_query: Natural language search query

    Returns:
        Dict with matching chunks and relevance scores
    """
    params = {"query": natural_language_query}

    try:
        # Load RAG index
        if not RAG_INDEX_PATH.exists():
            return {
                "success": False,
                "error": "RAG index not found. Run scripts/rag_indexer.py first.",
                "chunks": []
            }

        with open(RAG_INDEX_PATH, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        chunks = index_data.get('chunks', [])
        query_lower = natural_language_query.lower()
        query_terms = set(query_lower.split())

        # Simple keyword matching (replace with embeddings for production)
        scored_chunks = []

        # Define high-priority source files for policy questions
        policy_sources = [
            'business-rules.md',
            'wfh-swap-rules.md',
            'formulalogic.md',
            'protected-logic.md'
        ]

        for chunk in chunks:
            content_lower = chunk['content'].lower()
            source_file = chunk['metadata'].get('source_file', '')

            # Calculate relevance score
            score = 0

            # Exact phrase match (highest weight)
            if query_lower in content_lower:
                score += 10

            # Individual term matches
            for term in query_terms:
                if len(term) > 2:  # Skip very short terms
                    score += content_lower.count(term)

            # Boost based on category (fix: check for 'Policy' prefix, not exact 'policy')
            category = chunk['metadata'].get('category', '')
            if category.startswith('Policy'):
                score *= 2.0  # Strong boost for policy documents

            # Boost for core policy source files
            for policy_src in policy_sources:
                if policy_src in source_file:
                    score *= 2.5  # Even stronger boost for core handbook rules
                    break

            # Boost for skills knowledge files (contain structured policy info)
            if 'skills/' in source_file and '/references/' in source_file:
                score *= 1.5

            # Penalize scenario transcripts (noisy, not authoritative)
            if 'scenario' in source_file.lower() or 'transcript' in content_lower[:100]:
                score *= 0.3

            if score > 0:
                scored_chunks.append({
                    'content': chunk['content'][:500] + ('...' if len(chunk['content']) > 500 else ''),
                    'source': chunk['metadata'].get('source_file', 'unknown'),
                    'category': chunk['metadata'].get('category', 'unknown'),
                    'topic': chunk['metadata'].get('topic', 'unknown'),
                    'relevance_score': round(score, 2)
                })

        # Sort by relevance and take top 5
        scored_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_chunks = scored_chunks[:5]

        result = {
            "success": True,
            "query": natural_language_query,
            "total_matches": len(scored_chunks),
            "top_results": top_chunks,
            "index_stats": {
                "total_chunks": len(chunks),
                "index_version": index_data.get('version', 'unknown')
            }
        }

        audit_log("query_rag_corpus", params, result)
        return result

    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return {
            "success": False,
            "error": str(e),
            "chunks": []
        }


# =============================================================================
# TOOL 2: check_balance_integrity
# =============================================================================

@rate_limit("check_balance_integrity")
def check_balance_integrity(user_id: int) -> Dict[str, Any]:
    """
    Live verified math check for a specific user's balance.

    Loads the user's balance from DB, runs formulas from formulalogic.md,
    and returns calculated results. READ-ONLY - no DB modifications.

    Args:
        user_id: The user ID to check

    Returns:
        Dict with balance verification results
    """
    params = {"user_id": user_id}

    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.database import get_db
        from src.models.user import User
        from src.models.pto_balance import PTOBalance
        from sqlalchemy import select

        db = next(get_db())
        try:
            # Get user (READ-ONLY)
            user = db.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()

            if not user:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "verified": False
                }

            # Get current year balance (READ-ONLY)
            current_year = datetime.now().year
            balance = db.execute(
                select(PTOBalance).where(
                    PTOBalance.user_id == user_id,
                    PTOBalance.year == current_year
                )
            ).scalar_one_or_none()

            if not balance:
                return {
                    "success": False,
                    "error": f"No balance found for user {user_id} in year {current_year}",
                    "verified": False
                }

            # Calculate using canonical formulas from formulalogic.md
            # VACATION_AVAILABLE = vacation_total + vacation_carryover - vacation_used - vacation_pending
            calculated_vacation = (
                float(balance.vacation_total or 0) +
                float(balance.vacation_carryover or 0) -
                float(balance.vacation_used or 0) -
                float(balance.vacation_pending or 0)
            )

            # SICK_AVAILABLE = sick_total + sick_carryover - sick_used - sick_pending
            calculated_sick = (
                float(balance.sick_total or 0) +
                float(balance.sick_carryover or 0) -
                float(balance.sick_used or 0) -
                float(getattr(balance, 'sick_pending', 0) or 0)
            )

            # PERSONAL_AVAILABLE = personal_total + personal_carryover - personal_used - personal_pending
            calculated_personal = (
                float(balance.personal_total or 0) +
                float(balance.personal_carryover or 0) -
                float(balance.personal_used or 0) -
                float(getattr(balance, 'personal_pending', 0) or 0)
            )

            # CHICAGO_LEAVE_AVAILABLE = chicago_paid_leave_total + chicago_paid_leave_carryover - chicago_paid_leave_used - chicago_paid_leave_pending
            calculated_chicago = (
                float(getattr(balance, 'chicago_paid_leave_total', 0) or 0) +
                float(getattr(balance, 'chicago_paid_leave_carryover', 0) or 0) -
                float(getattr(balance, 'chicago_paid_leave_used', 0) or 0) -
                float(getattr(balance, 'chicago_paid_leave_pending', 0) or 0)
            )

            # Get model's computed properties
            model_vacation = float(balance.vacation_available)
            model_sick = float(balance.sick_available)
            model_personal = float(balance.personal_available)
            model_chicago = float(getattr(balance, 'chicago_paid_leave_available', 0) or 0)

            # Verify matches
            vacation_match = abs(calculated_vacation - model_vacation) < 0.01
            sick_match = abs(calculated_sick - model_sick) < 0.01
            personal_match = abs(calculated_personal - model_personal) < 0.01
            chicago_match = abs(calculated_chicago - model_chicago) < 0.01

            all_match = vacation_match and sick_match and personal_match and chicago_match

            result = {
                "success": True,
                "verified": all_match,
                "user": {
                    "id": user_id,
                    "name": user.full_name,
                    "year": current_year
                },
                "balances": {
                    "vacation": {
                        "total": float(balance.vacation_total or 0),
                        "carryover": float(balance.vacation_carryover or 0),
                        "used": float(balance.vacation_used or 0),
                        "pending": float(balance.vacation_pending or 0),
                        "calculated_available": calculated_vacation,
                        "model_available": model_vacation,
                        "formula_match": vacation_match
                    },
                    "sick": {
                        "total": float(balance.sick_total or 0),
                        "carryover": float(balance.sick_carryover or 0),
                        "used": float(balance.sick_used or 0),
                        "calculated_available": calculated_sick,
                        "model_available": model_sick,
                        "formula_match": sick_match
                    },
                    "personal": {
                        "total": float(balance.personal_total or 0),
                        "carryover": float(balance.personal_carryover or 0),
                        "used": float(balance.personal_used or 0),
                        "calculated_available": calculated_personal,
                        "model_available": model_personal,
                        "formula_match": personal_match
                    },
                    "chicago_leave": {
                        "total": float(getattr(balance, 'chicago_paid_leave_total', 0) or 0),
                        "carryover": float(getattr(balance, 'chicago_paid_leave_carryover', 0) or 0),
                        "used": float(getattr(balance, 'chicago_paid_leave_used', 0) or 0),
                        "calculated_available": calculated_chicago,
                        "model_available": model_chicago,
                        "formula_match": chicago_match
                    }
                },
                "formula_source": "task/formulalogic.md"
            }

            audit_log("check_balance_integrity", params, result)
            return result

        finally:
            db.close()  # READ-ONLY - no commit needed

    except Exception as e:
        logger.error(f"Balance integrity check error: {e}")
        return {
            "success": False,
            "error": str(e),
            "verified": False
        }


# =============================================================================
# TOOL 3: verify_policy_parity
# =============================================================================

@rate_limit("verify_policy_parity")
def verify_policy_parity(policy_domain: str) -> Dict[str, Any]:
    """
    Auditor tool to compare Policy documentation vs Implementation.

    Reads the rule from business-rules.md and checks if policy_engine.py
    has a corresponding logic block. READ-ONLY operation.

    Args:
        policy_domain: Policy domain to verify (e.g., "Chicago Sick Leave",
                      "Vacation Tiers", "Hard Cap Types", "Auto-Approve")

    Returns:
        Dict with Pass/Fail status and explanation
    """
    params = {"policy_domain": policy_domain}

    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        # Define policy domain mappings
        policy_checks = {
            "hard cap types": {
                "rule_keywords": ["hard cap", "blocked when over balance", "sick", "personal", "chicago"],
                "implementation_keywords": ["HARD_CAP_TYPES", "frozenset", "sick", "personal", "chicago_leave"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "soft cap types": {
                "rule_keywords": ["soft cap", "warning", "vacation", "manager discretion"],
                "implementation_keywords": ["SOFT_CAP_TYPES", "frozenset", "vacation"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "auto-approve": {
                "rule_keywords": ["auto-approve", "manager", "admin", "trusted"],
                "implementation_keywords": ["TRUSTED_AUTO_APPROVE_TYPES", "determine_auto_approve", "is_trusted"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "vacation tiers": {
                "rule_keywords": ["vacation tier", "years of service", "10 days", "12 days", "15 days", "20 days"],
                "implementation_keywords": ["vacation_tiers", "years_of_service", "80", "96", "120", "160"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "chicago leave": {
                "rule_keywords": ["chicago", "paid leave", "40 hours", "16 hours carryover"],
                "implementation_keywords": ["chicago", "paid_leave", "40", "16"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "carryover rules": {
                "rule_keywords": ["carryover", "sick", "personal", "vacation", "use-it-or-lose-it"],
                "implementation_keywords": ["carryover", "sick_carryover", "chicago_paid_leave_carryover"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "backdate window": {
                "rule_keywords": ["backdate", "7 days", "past"],
                "implementation_keywords": ["BACKDATE_WINDOW_DAYS", "7", "backdated"],
                "implementation_file": "src/services/policy_engine.py"
            },
            "balance formulas": {
                "rule_keywords": ["available", "total", "carryover", "used", "pending"],
                "implementation_keywords": ["vacation_available", "sick_available", "personal_available"],
                "implementation_file": "src/models/pto_balance.py"
            },
            "wfh swap": {
                "rule_keywords": ["peer-to-peer", "no manager approval", "wfh_swap_eligible", "weekly limit"],
                "implementation_keywords": ["peer-to-peer", "no manager approval", "wfh_swap_eligible", "one swap per week"],
                "implementation_file": "src/services/wfh_swap_service.py",
                "policy_file": ".claude/rules/wfh-swap-rules.md"
            }
        }

        # Normalize input
        domain_lower = policy_domain.lower().strip()

        # Find matching domain
        matched_domain = None
        for domain_key in policy_checks:
            if domain_key in domain_lower or domain_lower in domain_key:
                matched_domain = domain_key
                break

        if not matched_domain:
            # List available domains
            return {
                "success": True,
                "passed": None,
                "policy_domain": policy_domain,
                "error": "Unknown policy domain",
                "available_domains": list(policy_checks.keys()),
                "suggestion": "Try one of the available domains listed above"
            }

        check_config = policy_checks[matched_domain]

        # Read policy rules (use custom policy_file if specified, else default)
        policy_path = PROJECT_ROOT / check_config.get("policy_file", ".claude/rules/business-rules.md")
        with open(policy_path, 'r', encoding='utf-8') as f:
            rules_content = f.read().lower()

        # Read implementation
        impl_path = PROJECT_ROOT / check_config["implementation_file"]
        with open(impl_path, 'r', encoding='utf-8') as f:
            impl_content = f.read().lower()

        # Check rule keywords in policy
        rule_matches = []
        rule_missing = []
        for keyword in check_config["rule_keywords"]:
            if keyword.lower() in rules_content:
                rule_matches.append(keyword)
            else:
                rule_missing.append(keyword)

        # Check implementation keywords
        impl_matches = []
        impl_missing = []
        for keyword in check_config["implementation_keywords"]:
            if keyword.lower() in impl_content:
                impl_matches.append(keyword)
            else:
                impl_missing.append(keyword)

        # Determine pass/fail
        rule_coverage = len(rule_matches) / len(check_config["rule_keywords"]) if check_config["rule_keywords"] else 0
        impl_coverage = len(impl_matches) / len(check_config["implementation_keywords"]) if check_config["implementation_keywords"] else 0

        passed = rule_coverage >= 0.7 and impl_coverage >= 0.7

        # Generate explanation
        if passed:
            explanation = f"Policy '{matched_domain}' is properly documented in business-rules.md ({len(rule_matches)}/{len(check_config['rule_keywords'])} keywords) and implemented in {check_config['implementation_file']} ({len(impl_matches)}/{len(check_config['implementation_keywords'])} keywords)."
        else:
            issues = []
            if rule_coverage < 0.7:
                issues.append(f"Policy documentation incomplete (missing: {', '.join(rule_missing[:3])})")
            if impl_coverage < 0.7:
                issues.append(f"Implementation incomplete (missing: {', '.join(impl_missing[:3])})")
            explanation = f"Policy parity FAILED for '{matched_domain}'. Issues: {'; '.join(issues)}"

        result = {
            "success": True,
            "passed": passed,
            "policy_domain": matched_domain,
            "explanation": explanation,
            "details": {
                "policy_file": check_config.get("policy_file", ".claude/rules/business-rules.md"),
                "implementation_file": check_config["implementation_file"],
                "rule_coverage": f"{rule_coverage*100:.0f}%",
                "implementation_coverage": f"{impl_coverage*100:.0f}%",
                "rule_keywords_found": rule_matches,
                "rule_keywords_missing": rule_missing,
                "impl_keywords_found": impl_matches,
                "impl_keywords_missing": impl_missing
            }
        }

        audit_log("verify_policy_parity", params, result)
        return result

    except Exception as e:
        logger.error(f"Policy parity check error: {e}")
        return {
            "success": False,
            "passed": False,
            "error": str(e)
        }


# =============================================================================
# MCP TOOL REGISTRY
# =============================================================================

MCP_INSPECTOR_TOOLS = {
    "query_rag_corpus": {
        "handler": query_rag_corpus,
        "description": "Semantic search of Safe Corpus (policies & help docs)",
        "read_only": True,
        "parameters": {
            "natural_language_query": {"type": "string", "required": True}
        }
    },
    "check_balance_integrity": {
        "handler": check_balance_integrity,
        "description": "Live verified math check for user balance",
        "read_only": True,
        "parameters": {
            "user_id": {"type": "integer", "required": True}
        }
    },
    "verify_policy_parity": {
        "handler": verify_policy_parity,
        "description": "Compare policy docs vs implementation",
        "read_only": True,
        "parameters": {
            "policy_domain": {"type": "string", "required": True}
        }
    }
}


def get_inspector_tools() -> List[Dict[str, Any]]:
    """Get list of available Inspector tools."""
    return [
        {
            "name": name,
            "description": tool["description"],
            "read_only": tool["read_only"],
            "parameters": tool["parameters"]
        }
        for name, tool in MCP_INSPECTOR_TOOLS.items()
    ]


def invoke_inspector_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Invoke an Inspector tool."""
    if tool_name not in MCP_INSPECTOR_TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}

    tool = MCP_INSPECTOR_TOOLS[tool_name]

    try:
        return tool["handler"](**kwargs)
    except RateLimitError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Inspector tool {tool_name} error: {e}")
        return {"error": f"Tool execution failed: {str(e)}"}


# =============================================================================
# CONNECTION TEST
# =============================================================================

def run_connection_test():
    """Run connection test to verify tools are accessible."""
    print("=" * 60)
    print("PTO Central MCP Server - Inspector Agent")
    print("Phase 4: Read-Only Tools")
    print("=" * 60)
    print()

    print("Available Tools:")
    print("-" * 60)
    for tool in get_inspector_tools():
        print(f"\n  Tool: {tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Read-Only: {tool['read_only']}")
        print(f"  Parameters: {list(tool['parameters'].keys())}")

    print()
    print("-" * 60)
    print("Running Quick Tests...")
    print("-" * 60)

    # Test 1: RAG Query
    print("\n[Test 1] query_rag_corpus('vacation balance')...")
    result = invoke_inspector_tool("query_rag_corpus", natural_language_query="vacation balance")
    if result.get("success"):
        print(f"  SUCCESS: Found {result.get('total_matches', 0)} matches")
    else:
        print(f"  RESULT: {result.get('error', 'Unknown')}")

    # Test 2: Policy Parity
    print("\n[Test 2] verify_policy_parity('hard cap types')...")
    result = invoke_inspector_tool("verify_policy_parity", policy_domain="hard cap types")
    if result.get("success"):
        status = "PASS" if result.get("passed") else "FAIL"
        print(f"  SUCCESS: Parity check {status}")
        print(f"  Explanation: {result.get('explanation', '')[:80]}...")
    else:
        print(f"  ERROR: {result.get('error', 'Unknown')}")

    # Test 3: Balance Integrity (requires DB)
    print("\n[Test 3] check_balance_integrity(user_id=1)...")
    result = invoke_inspector_tool("check_balance_integrity", user_id=1)
    if result.get("success"):
        verified = "VERIFIED" if result.get("verified") else "MISMATCH"
        print(f"  SUCCESS: Balance {verified}")
    else:
        print(f"  RESULT: {result.get('error', 'Unknown')}")

    print()
    print("=" * 60)
    print("CONNECTION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_connection_test()
