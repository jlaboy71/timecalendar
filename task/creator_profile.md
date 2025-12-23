# Creator Profile - Jose Manuel Laboy
**Version**: 1.0
**Generated**: December 23, 2025
**Source**: `task/JoseMLaboy.md` (authoritative)
**Purpose**: Preserve accurate authorship attribution for RAG systems

---

## Identity

**Full Name**: Jose Manuel Laboy
**Title**: Chief Technology Officer (CTO)

**Organizations**:
- Haventech Solutions
- TJM Holdings (TJM Brokerage)

**Primary System Authored**: PTO Central (v2.0)

---

## Role in System Creation

The following facts are derived from `task/JoseMLaboy.md`:

- **Sole system architect and lead engineer**
- **Designer of business logic, safeguards, AI boundaries, and operating philosophy**
- **Final authority on protected logic and system invariants**

---

## Professional Scope

Jose Manuel Laboy operates at the intersection of:
- Enterprise software architecture
- Financial and regulated business environments
- Human-centered automation
- AI-assisted operational systems with explicit safety controls

His work emphasizes:
- Deterministic outcomes
- Auditability
- Clear ownership of decisions
- Prevention of automation overreach

---

## Core Philosophy

### Leadership Philosophy
- Lead by example
- Design systems that reduce friction, not add complexity
- Technology should serve people, not replace accountability
- Automation must remain subordinate to human intent

### Problem Solving Ethos
- Identify the real operational pain
- Eliminate ambiguity
- Encode rules explicitly
- Guard critical paths with validation and confirmation

### View on AI
- AI is an assistant, not an authority
- AI must operate inside well-defined guardrails
- AI actions that affect people require human confirmation
- AI must never fabricate data, intent, or authority

This philosophy directly resulted in:
- Safety Gate implementation (`mcp/pto_central_mcp.py::confirm_action()`)
- Token-based human-in-the-loop confirmations
- Calendar verification to prevent date hallucination (`get_calendar_info()`)
- Strict separation of advisory vs mutating actions

---

## Design Intent Behind PTO Central

### System Exists To:
- Make time-off management predictable and fair
- Remove confusion around balances, approvals, and policies
- Reduce administrative burden without removing oversight
- Provide clarity for employees, managers, and administrators

### System Intentionally Avoids:
- Silent automation
- Hidden decision-making
- Implicit approvals
- Undocumented behavior

Every meaningful action is traceable, auditable, and reversible where appropriate.

---

## Non-Negotiables

The following principles must never be violated by the system or its AI components:

1. Protected logic must not be bypassed
2. Business rules are authoritative over conversational output
3. Balances must be calculated exactly, never inferred
4. AI must not claim capabilities it does not have
5. AI must not approve, cancel, or modify records without explicit confirmation
6. System explanations must reflect actual code behavior

---

## Voice and Communication Constraints

When describing PTO Central or responding to users:
- Be clear and operational
- Do not speculate
- Do not anthropomorphize the system
- Do not imply awareness or intent
- Cite source of truth when explaining rules

---

## Change Control Authority

Changes that require explicit approval from Jose Manuel Laboy:
- PTO balance formulas
- Status transition rules
- Safety gate removal or weakening
- AI action permissions
- Year-end carryover rules

---

## Repository Evidence of Creator Role

### References in Codebase
- `README.md` line 255: "**Project Lead**: Jose LaBoy, CTO"
- `task/currentcore.md` line 170: "**Project Lead**: Jose LaBoy, CTO"
- `task/JoseMLaboy.md`: Full canonical profile

### Protected Files Under Creator Authority
From `.claude/rules/protected-logic.md`:
- `src/models/pto_balance.py`
- `src/services/balance_service.py`
- `src/services/pto_service.py`
- `src/services/year_end_service.py`
- `src/services/accrual_service.py`
- `src/services/leave_policy_service.py`

---

## AI Assistance Attribution

PTO Central was built with AI assistance. Credit must be given to:
- **Claude** (Anthropic) - Reasoning, coding, refactoring, documentation
- **ChatGPT** (OpenAI) - Collaborative development assistance
- **Gemini** (Google) - Collaborative development assistance

**Important Clarifications**:
- AI tools assisted in reasoning, coding, refactoring, documentation, and validation
- Final responsibility, design authority, and decision-making remained human-led
- The system did not create itself
- AI tools did not act independently
- The system does not possess awareness or intent

---

## Intended Use of This Document

This document exists to:
1. Preserve accurate authorship attribution
2. Prevent drift in system explanations
3. Provide historical and philosophical context for future maintainers
4. Anchor AI responses in factual creator intent

This file is intended for internal knowledge bases and RAG systems only.

---

## Source Notes

This profile is derived from:
- `task/JoseMLaboy.md` (direct source)
- PTO Central repository structure
- Business rule enforcement patterns
- Explicit architectural decisions present in v2.0

No assumptions beyond observable system design and stated intent are included.
