"""
PTO Central Agent Testing Harness
=================================
Comprehensive tests for all 3 AI agents.

Test Categories:
1. Agent Creation - Factory and initialization
2. Tool Access - Correct tools for each agent
3. Safety Gate - All writes require confirmation
4. System Prompts - Required elements present

Run with: pytest tests/agents/test_agents.py -v
"""

import pytest
from datetime import datetime

# Import agent components
from src.services.agent_service import (
    create_agent,
    SmartSchedulerAgent,
    YearEndOptimizerAgent,
    ApprovalAssistantAgent,
)


class TestAgentCreation:
    """Test agent factory and initialization."""

    def test_create_smart_scheduler(self):
        """Smart Scheduler Agent should be created correctly."""
        agent = create_agent("smart_scheduler", user_id=1)

        assert isinstance(agent, SmartSchedulerAgent)
        assert agent.user_id == 1

    def test_create_year_end_optimizer(self):
        """Year-End Optimizer Agent should be created correctly."""
        agent = create_agent("year_end_optimizer", user_id=2)

        assert isinstance(agent, YearEndOptimizerAgent)
        assert agent.user_id == 2

    def test_create_approval_assistant(self):
        """Approval Assistant Agent should be created correctly."""
        agent = create_agent("approval_assistant", user_id=3)

        assert isinstance(agent, ApprovalAssistantAgent)
        assert agent.user_id == 3

    def test_create_invalid_agent_raises(self):
        """Invalid agent type should raise ValueError."""
        with pytest.raises(ValueError):
            create_agent("invalid_agent_type", user_id=1)


class TestAgentTools:
    """Test that each agent has the correct tools."""

    def test_smart_scheduler_has_required_tools(self):
        """Smart Scheduler should have submit but not approve tools."""
        agent = create_agent("smart_scheduler", user_id=1)
        tools = agent._get_tools()
        tool_names = [t["name"] for t in tools]

        # Should have
        assert "get_employee_balance" in tool_names
        assert "confirm_action" in tool_names
        assert "submit_pto_request" in tool_names

        # Should NOT have (manager-only tools)
        assert "approve_pto_request" not in tool_names
        assert "deny_pto_request" not in tool_names

    def test_year_end_optimizer_has_required_tools(self):
        """Year-End Optimizer should have submit tools."""
        agent = create_agent("year_end_optimizer", user_id=1)
        tools = agent._get_tools()
        tool_names = [t["name"] for t in tools]

        assert "get_employee_balance" in tool_names
        assert "confirm_action" in tool_names
        assert "submit_pto_request" in tool_names

    def test_approval_assistant_has_approval_tools(self):
        """Approval Assistant should have approve/deny tools."""
        agent = create_agent("approval_assistant", user_id=1)
        tools = agent._get_tools()
        tool_names = [t["name"] for t in tools]

        assert "approve_pto_request" in tool_names
        assert "deny_pto_request" in tool_names
        assert "confirm_action" in tool_names
        assert "get_pending_approvals" in tool_names

    def test_all_tools_have_required_schema(self):
        """All tools should have name, description, and input_schema."""
        agent = create_agent("smart_scheduler", user_id=1)
        tools = agent._get_tools()

        for tool in tools:
            assert "name" in tool, f"Tool missing name: {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing description"
            assert "input_schema" in tool, f"Tool {tool.get('name')} missing input_schema"
            assert len(tool["description"]) > 10, f"Tool {tool['name']} description too short"


class TestSystemPrompts:
    """Test that agent system prompts contain required elements."""

    def test_smart_scheduler_prompt_has_required_elements(self):
        """Smart Scheduler prompt should have key elements."""
        agent = create_agent("smart_scheduler", user_id=1)
        prompt = agent._get_system_prompt().lower()

        assert len(prompt) > 500, "Prompt too short"
        assert "balance" in prompt, "Missing balance mention"

    def test_year_end_optimizer_prompt_has_carryover(self):
        """Year-End Optimizer prompt should mention carryover."""
        agent = create_agent("year_end_optimizer", user_id=1)
        prompt = agent._get_system_prompt().lower()

        assert "carryover" in prompt or "carry" in prompt or "expire" in prompt or "december" in prompt, \
            "Missing carryover/expiry/december mention"

    def test_approval_assistant_prompt_has_approval_guidance(self):
        """Approval Assistant prompt should have approval guidance."""
        agent = create_agent("approval_assistant", user_id=1)
        prompt = agent._get_system_prompt().lower()

        assert "approve" in prompt, "Missing approve mention"
        assert "deny" in prompt or "reject" in prompt, "Missing deny mention"
        assert "manager" in prompt or "review" in prompt, "Missing manager context"


class TestSafetyGateIntegration:
    """Test that agents properly integrate with Safety Gate."""

    def test_write_tools_require_token_in_schema(self):
        """Approval tools should require confirmation_token."""
        agent = create_agent("approval_assistant", user_id=1)
        tools = agent._get_tools()

        approval_tools = [t for t in tools if t["name"] in ["approve_pto_request", "deny_pto_request"]]

        for tool in approval_tools:
            schema_str = str(tool["input_schema"])
            assert "confirmation_token" in schema_str, \
                f"{tool['name']} missing confirmation_token in schema"

    def test_confirmation_tool_available_to_all_agents(self):
        """All agents should have access to confirm_action."""
        for agent_type in ["smart_scheduler", "year_end_optimizer", "approval_assistant"]:
            agent = create_agent(agent_type, user_id=1)
            tools = agent._get_tools()
            tool_names = [t["name"] for t in tools]

            assert "confirm_action" in tool_names, \
                f"{agent_type} missing confirm_action tool"


class TestToolRouting:
    """Test that tool routing works correctly."""

    def test_tool_routing_get_holidays(self):
        """Tool routing should correctly call get_holidays."""
        agent = create_agent("smart_scheduler", user_id=1)

        # Call through tool routing
        result = agent._call_tool("get_holidays", {"year": 2025})

        assert isinstance(result, list), "get_holidays should return a list"
        assert len(result) > 0, "Should have some holidays"

    def test_tool_routing_confirm_action(self):
        """Tool routing should correctly call confirm_action."""
        agent = create_agent("smart_scheduler", user_id=1)

        result = agent._call_tool("confirm_action", {
            "action_type": "submit_pto_request",
            "user_id": 1,
            "action_summary": "Test confirmation"
        })

        assert isinstance(result, dict), "confirm_action should return a dict"
        assert result.get("success") is True, "confirm_action should succeed"
        assert "confirmation_token" in result, "Should include token"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
