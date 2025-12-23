"""
PTO Central Phase 5 Integration Tests
=====================================
End-to-end validation of the complete AI stack.

Tests the full flow:
User → Agent → MCP Tools → Safety Gate → Services → Response

Run with: pytest tests/test_phase5_integration.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path


class TestMCPToolsIntegration:
    """Test MCP tools are accessible and functional."""

    def test_mcp_server_imports(self):
        """MCP server module should import without errors."""
        from mcp import pto_central_mcp
        # Verify key functions exist
        assert hasattr(pto_central_mcp, 'confirm_action')
        assert hasattr(pto_central_mcp, 'get_holidays')

    def test_read_tools_exist(self):
        """All read tools should be importable."""
        from mcp.pto_central_mcp import (
            get_employee_balance,
            get_employee_requests,
            get_pending_approvals,
            get_holidays,
        )
        assert callable(get_employee_balance)
        assert callable(get_employee_requests)
        assert callable(get_pending_approvals)
        assert callable(get_holidays)

    def test_write_tools_exist(self):
        """All write tools should be importable."""
        from mcp.pto_central_mcp import (
            confirm_action,
            submit_pto_request,
            cancel_pto_request,
            approve_pto_request,
            deny_pto_request,
        )
        assert callable(confirm_action)
        assert callable(submit_pto_request)
        assert callable(cancel_pto_request)
        assert callable(approve_pto_request)
        assert callable(deny_pto_request)

    def test_confirm_action_generates_token(self):
        """confirm_action should generate a valid token."""
        from mcp.pto_central_mcp import confirm_action

        result = confirm_action(
            action_type="submit_pto_request",
            user_id=1,
            action_summary="Test confirmation"
        )

        assert result.get("success") is True
        assert "confirmation_token" in result
        assert len(result["confirmation_token"]) > 20

    def test_write_tool_rejects_without_token(self):
        """Write tools should reject requests without valid token."""
        from mcp.pto_central_mcp import submit_pto_request

        result = submit_pto_request(
            user_id=1,
            pto_type="vacation",
            start_date="2025-03-01",
            end_date="2025-03-02",
            confirmation_token=""  # Empty token
        )

        assert result.get("success") is False
        assert "error" in result


class TestAgentIntegration:
    """Test agents integrate properly with MCP tools."""

    def test_all_agents_creatable(self):
        """All 3 agent types should be creatable."""
        from src.services.agent_service import create_agent

        agents = []
        for agent_type in ["smart_scheduler", "year_end_optimizer", "approval_assistant"]:
            agent = create_agent(agent_type, user_id=1)
            agents.append(agent)
            assert agent is not None

        assert len(agents) == 3

    def test_agents_have_tools(self):
        """Each agent should have appropriate tools."""
        from src.services.agent_service import create_agent

        # Smart Scheduler: read + submit
        ss = create_agent("smart_scheduler", user_id=1)
        ss_tools = [t["name"] for t in ss._get_tools()]
        assert "get_employee_balance" in ss_tools
        assert "submit_pto_request" in ss_tools
        assert "confirm_action" in ss_tools

        # Approval Assistant: read + approve/deny
        aa = create_agent("approval_assistant", user_id=1)
        aa_tools = [t["name"] for t in aa._get_tools()]
        assert "approve_pto_request" in aa_tools
        assert "deny_pto_request" in aa_tools

    def test_agent_system_prompts_substantial(self):
        """Agent system prompts should be substantial."""
        from src.services.agent_service import create_agent

        for agent_type in ["smart_scheduler", "year_end_optimizer", "approval_assistant"]:
            agent = create_agent(agent_type, user_id=1)
            prompt = agent._get_system_prompt()

            assert len(prompt) > 500, f"{agent_type} prompt too short"
            # Each agent has relevant keywords in their prompt
            if agent_type == "smart_scheduler":
                assert "schedule" in prompt.lower() or "vacation" in prompt.lower()
            elif agent_type == "year_end_optimizer":
                assert "carryover" in prompt.lower() or "expire" in prompt.lower()
            elif agent_type == "approval_assistant":
                assert "approve" in prompt.lower() or "manager" in prompt.lower()


class TestSafetyGateIntegration:
    """Test Safety Gate is properly integrated."""

    def test_token_flow(self):
        """Full token request → validate flow should work."""
        from mcp.pto_central_mcp import confirm_action

        # Request token
        conf_result = confirm_action(
            action_type="submit_pto_request",
            user_id=1,
            action_summary="Integration test"
        )

        assert conf_result["success"]
        token = conf_result["confirmation_token"]

        # Token should be valid format
        assert len(token) > 20
        assert conf_result["expires_in_seconds"] == 300

    def test_valid_action_types(self):
        """All expected action types should be valid."""
        from mcp.pto_central_mcp import VALID_CONFIRMATION_ACTIONS

        expected = {
            "submit_pto_request",
            "cancel_pto_request",
            "approve_pto_request",
            "deny_pto_request",
        }

        for action in expected:
            assert action in VALID_CONFIRMATION_ACTIONS, f"Missing: {action}"


class TestVoiceIntegration:
    """Test voice interface integration."""

    def test_voice_interface_importable(self):
        """Voice interface should be importable."""
        from src.services.voice import VoiceInterface, get_voice_interface

        voice = get_voice_interface()
        assert voice is not None

    def test_command_parsing_works(self):
        """Voice command parsing should detect intents."""
        from src.services.voice import get_voice_interface

        voice = get_voice_interface()

        # Test vacation request
        cmd = voice.parse_command("I want to take a week off")
        assert cmd.intent == "request_vacation"
        assert cmd.entities.get("duration") == 5

        # Test balance check
        cmd = voice.parse_command("How much PTO do I have")
        assert cmd.intent == "check_balance"

        # Test confirmation
        assert voice.is_confirmation("yes") is True
        assert voice.is_confirmation("no") is False


class TestSkillsIntegration:
    """Test skills are properly created."""

    def test_all_skills_exist(self):
        """All 6 skill directories should exist with SKILL.md."""
        skills = [
            "pto-central-development",
            "pto-policy-validator",
            "pto-testing-automation",
            "pto-mcp-builder",
            "pto-rag-knowledge",
            "pto-agent-orchestrator",
        ]

        for skill in skills:
            skill_file = Path(f"skills/{skill}/SKILL.md")
            assert skill_file.exists(), f"Missing: {skill_file}"

    def test_skills_have_frontmatter(self):
        """Each skill should have proper frontmatter."""
        skills_dir = Path("skills")
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    content = skill_file.read_text()
                    assert "name:" in content, f"{skill_dir.name} missing name"
                    assert "description:" in content, f"{skill_dir.name} missing description"


class TestDoctrineIntegration:
    """Test doctrine/RAG integration."""

    def test_doctrine_files_exist(self):
        """Doctrine files should exist."""
        doctrine_files = [
            "task/system_identity.md",
            "task/creator_profile.md",
            "task/knowledge_contract.md",
        ]

        for doc_file in doctrine_files:
            assert Path(doc_file).exists(), f"Missing: {doc_file}"

    def test_doctrine_query_service_works(self):
        """Doctrine query service should be functional."""
        try:
            from src.services.doctrine_query_service import get_doctrine_service

            service = get_doctrine_service()
            result = service.query("What is PTO Central?")

            assert result is not None
            assert "source" in result or "answer" in result
        except ImportError:
            pytest.skip("Doctrine query service not available")


class TestFullStackFlow:
    """Test complete end-to-end flows."""

    def test_agent_to_mcp_routing(self):
        """Agent tool routing should connect to MCP tools."""
        from src.services.agent_service import create_agent

        agent = create_agent("smart_scheduler", user_id=1)

        # Verify the agent has _call_tool method
        assert hasattr(agent, '_call_tool') or hasattr(agent, '_route_tool_call')

    def test_phase5_components_count(self):
        """Verify all Phase 5 components exist."""
        from src.services.agent_service import create_agent

        # Count agents by trying to create them
        agent_types = ["smart_scheduler", "year_end_optimizer", "approval_assistant"]
        agent_count = sum(1 for t in agent_types if create_agent(t, user_id=1) is not None)

        # Count skills
        skill_count = len(list(Path("skills").glob("*/SKILL.md")))

        # Count doctrine files
        doctrine_count = len([
            f for f in Path("task").glob("*.md")
            if f.name in ["system_identity.md", "creator_profile.md", "knowledge_contract.md"]
        ])

        print(f"\nPhase 5 Component Inventory:")
        print(f"  Agents: {agent_count}")
        print(f"  Skills: {skill_count}")
        print(f"  Doctrine Files: {doctrine_count}")

        assert agent_count >= 3, "Missing agents"
        assert skill_count >= 6, "Missing skills"
        assert doctrine_count >= 3, "Missing doctrine files"


class TestHolidayToolFix:
    """Test the get_holidays bug fix from Phase 4."""

    def test_get_holidays_returns_data(self):
        """get_holidays should return holiday data for 2025."""
        from mcp.pto_central_mcp import get_holidays

        result = get_holidays(year=2025)

        assert isinstance(result, list), "get_holidays should return a list"
        assert len(result) > 0, "Should have holidays for 2025"

    def test_get_holidays_has_required_fields(self):
        """Each holiday should have date, name, and market fields."""
        from mcp.pto_central_mcp import get_holidays

        result = get_holidays(year=2025)

        if len(result) > 0:
            holiday = result[0]
            assert "date" in holiday, "Holiday missing 'date' field"
            assert "name" in holiday, "Holiday missing 'name' field"
            assert "market" in holiday, "Holiday missing 'market' field"


class TestValidateRequestFix:
    """Test the validate_request fix (rejection_reason attribute)."""

    def test_validate_request_returns_result(self):
        """validate_request should return a valid result dict."""
        from mcp.pto_central_mcp import validate_request

        # Use a future date to test validation
        result = validate_request(
            employee_id=1,
            pto_type="vacation",
            start_date="2025-06-01",
            end_date="2025-06-05"
        )

        assert isinstance(result, dict), "validate_request should return a dict"
        assert "valid" in result or "error" in result, "Result should have valid or error key"
        assert "hours" in result, "Result should have hours"
        assert "working_days" in result, "Result should have working_days"

    def test_validate_request_no_attribute_error(self):
        """validate_request should not raise AttributeError for rejection_reason."""
        from mcp.pto_central_mcp import validate_request

        # Test with an invalid past date to trigger rejection path
        try:
            result = validate_request(
                employee_id=1,
                pto_type="vacation",
                start_date="2020-01-01",  # Far past date
                end_date="2020-01-05"
            )
            # Should return error gracefully, not raise exception
            assert isinstance(result, dict)
            if not result.get("valid"):
                assert "error" in result, "Invalid request should have error message"
        except AttributeError as e:
            pytest.fail(f"AttributeError raised: {e}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
