---
name: pto-policy-validator
description: Skill for validating PTO requests against business rules and policies. Use when checking handbook compliance, state/city-specific rules (Chicago ordinance), balance overdraft policies, and carryover limits. Triggers on "policy validation", "handbook rules", "Chicago leave", "overdraft", "hard cap", "soft cap".
---

# PTO Policy Validator Skill

## Purpose

This skill provides expertise for validating PTO requests against Haventech business rules and multi-state policies.

## Key Concepts

### Hard Cap vs Soft Cap Types
- **Hard Cap** (blocked): Sick, Personal, Chicago Paid Leave
- **Soft Cap** (warning): Vacation

### Policy Resolution Order
1. City-specific (e.g., Chicago, IL)
2. State-specific (e.g., IL)
3. Default (no location)

### Chicago Paid Leave Compliance
- 40 hours annual allocation
- 16 hours maximum carryover
- Per Chicago ordinance requirements

## References

- See `references/handbook-rules.md` for Haventech policy
- See `references/chicago-ordinance.md` for Chicago leave requirements
- See `references/validation-rules.md` for policy engine logic
