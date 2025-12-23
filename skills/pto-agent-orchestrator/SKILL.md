---
name: pto-agent-orchestrator
description: Skill for managing AI agents in PTO Central. Use when working with SmartSchedulerAgent, YearEndOptimizerAgent, ApprovalAssistantAgent, MCP tool integration, or human-in-the-loop confirmation flows. Triggers on "agent", "smart scheduler", "year-end optimizer", "approval assistant", "confirmation token", "MCP write".
---

# PTO Agent Orchestrator Skill

## Purpose

This skill provides expertise for building and orchestrating AI agents that interact with PTO Central via MCP tools.

## Available Agents

### SmartSchedulerAgent
Helps employees find optimal vacation dates by checking balances, team coverage, and market holidays.

### YearEndOptimizerAgent
Proactively prevents December chaos by alerting users about expiring PTO and suggesting optimal dates.

### ApprovalAssistantAgent
Helps managers make faster approval decisions by checking coverage and generating recommendations.

## Key Concepts

### Human-in-the-Loop (Safety Gate)
All write operations require:
1. Call `confirm_action` to get token
2. Present summary to user
3. User explicitly confirms
4. Use token in write call

### MCP Tool Categories
- **Read-only**: get_employee_balance, get_holidays, get_team_calendar
- **Analysis**: check_team_coverage, validate_request
- **Write (requires token)**: submit_pto_request, cancel_pto_request, approve_pto_request

## References

- See `references/agent-specs.md` for agent implementation details
- See `references/guardrails.md` for safety and security constraints
