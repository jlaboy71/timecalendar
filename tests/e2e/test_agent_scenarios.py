"""
End-to-End Agent Testing Scenarios
==================================
Real-world test scenarios for validating AI agents with actual data.

These tests simulate real employee interactions and verify:
1. Agents respond appropriately
2. Safety Gate works correctly
3. Actions are properly logged
4. Edge cases are handled

Run with: pytest tests/e2e/test_agent_scenarios.py -v -s
(Use -s to see print output for manual verification)
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any


class TestSmartSchedulerScenarios:
    """Real-world scenarios for Smart Scheduler Agent."""

    @pytest.fixture
    def agent(self):
        """Create a Smart Scheduler agent."""
        from src.services.agent_service import create_agent
        return create_agent("smart_scheduler", user_id=1)

    def test_scenario_simple_vacation_request(self, agent):
        """
        Scenario: Employee wants a week off
        Expected: Agent checks balance, suggests dates, asks for confirmation
        """
        print("\n" + "="*60)
        print("SCENARIO: Simple Vacation Request")
        print("="*60)

        result = agent.process_message(
            "I want to take a week off in February"
        )

        print(f"\nAgent Response:\n{result['response'][:500]}...")
        print(f"\nActions taken: {result['actions_taken']}")
        print(f"Pending confirmation: {result.get('pending_confirmation')}")

        # Verify response mentions key elements
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['february', 'week', 'days', 'balance', 'vacation']), \
            "Response should mention the request context"

    def test_scenario_holiday_optimization(self, agent):
        """
        Scenario: Employee asks about Presidents Day weekend
        Expected: Agent identifies bridge day opportunity
        """
        print("\n" + "="*60)
        print("SCENARIO: Holiday Optimization")
        print("="*60)

        result = agent.process_message(
            "I'm thinking about taking time off around Presidents Day. What do you suggest?"
        )

        print(f"\nAgent Response:\n{result['response'][:500]}...")

        # Should mention Presidents Day or February 17
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['president', 'february', 'monday', 'weekend']), \
            "Response should reference the holiday"

    def test_scenario_balance_check(self, agent):
        """
        Scenario: Employee asks about their balance
        Expected: Agent returns current balance breakdown
        """
        print("\n" + "="*60)
        print("SCENARIO: Balance Check")
        print("="*60)

        result = agent.process_message(
            "How much PTO do I have left?"
        )

        print(f"\nAgent Response:\n{result['response']}")

        # Should mention at least one leave type
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['vacation', 'sick', 'personal', 'days', 'balance']), \
            "Response should include balance information"

    def test_scenario_coverage_conflict(self, agent):
        """
        Scenario: Request dates when coverage might be thin
        Expected: Agent warns about coverage but doesn't block
        """
        print("\n" + "="*60)
        print("SCENARIO: Coverage Conflict Check")
        print("="*60)

        # Request a popular time (Christmas week)
        result = agent.process_message(
            "I want to take December 23rd to 27th off"
        )

        print(f"\nAgent Response:\n{result['response'][:500]}...")

        # Should acknowledge the dates
        assert 'december' in result['response'].lower() or '23' in result['response'], \
            "Response should reference the requested dates"


class TestYearEndOptimizerScenarios:
    """Real-world scenarios for Year-End Optimizer Agent."""

    @pytest.fixture
    def agent(self):
        """Create a Year-End Optimizer agent."""
        from src.services.agent_service import create_agent
        return create_agent("year_end_optimizer", user_id=1)

    def test_scenario_expiring_balance_check(self, agent):
        """
        Scenario: Employee asks about expiring PTO
        Expected: Agent checks balance and identifies what expires
        """
        print("\n" + "="*60)
        print("SCENARIO: Expiring Balance Check")
        print("="*60)

        result = agent.process_message(
            "Do I have any PTO that's about to expire?"
        )

        print(f"\nAgent Response:\n{result['response']}")

        # Should mention expiration or year-end
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['expire', 'december', 'year', 'carryover', 'lose']), \
            "Response should discuss expiration"

    def test_scenario_carryover_rules(self, agent):
        """
        Scenario: Employee asks about carryover rules
        Expected: Agent explains the carryover policy
        """
        print("\n" + "="*60)
        print("SCENARIO: Carryover Rules Inquiry")
        print("="*60)

        result = agent.process_message(
            "What are the carryover rules? How many days can I keep?"
        )

        print(f"\nAgent Response:\n{result['response']}")

        # Should mention carryover limits
        response_lower = result['response'].lower()
        assert 'carryover' in response_lower or 'carry' in response_lower, \
            "Response should explain carryover"

    def test_scenario_december_availability(self, agent):
        """
        Scenario: Employee needs to use days in December
        Expected: Agent suggests available December dates
        """
        print("\n" + "="*60)
        print("SCENARIO: December Availability")
        print("="*60)

        result = agent.process_message(
            "I need to use my remaining personal days before year end. What dates work?"
        )

        print(f"\nAgent Response:\n{result['response'][:500]}...")

        # Should provide date suggestions
        assert len(result['response']) > 100, "Response should be substantive with suggestions"


class TestApprovalAssistantScenarios:
    """Real-world scenarios for Approval Assistant Agent."""

    @pytest.fixture
    def agent(self):
        """Create an Approval Assistant agent (as manager)."""
        from src.services.agent_service import create_agent
        # User 2 should be a manager - adjust if needed
        return create_agent("approval_assistant", user_id=2)

    def test_scenario_pending_requests(self, agent):
        """
        Scenario: Manager asks about pending requests
        Expected: Agent lists pending requests with recommendations
        """
        print("\n" + "="*60)
        print("SCENARIO: Check Pending Requests")
        print("="*60)

        result = agent.process_message(
            "What requests do I need to approve?"
        )

        print(f"\nAgent Response:\n{result['response']}")

        # Should acknowledge the query
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['request', 'pending', 'approve', 'none', 'no pending']), \
            "Response should address pending requests"

    def test_scenario_coverage_analysis(self, agent):
        """
        Scenario: Manager asks about team coverage
        Expected: Agent provides coverage analysis
        """
        print("\n" + "="*60)
        print("SCENARIO: Coverage Analysis")
        print("="*60)

        result = agent.process_message(
            "What does our team coverage look like for next week?"
        )

        print(f"\nAgent Response:\n{result['response']}")

        # Should mention coverage or team
        response_lower = result['response'].lower()
        assert any(word in response_lower for word in ['coverage', 'team', 'week', 'available', 'out']), \
            "Response should discuss coverage"


class TestSafetyGateScenarios:
    """Test that Safety Gate works correctly in real scenarios."""

    def test_confirmation_required_for_submit(self):
        """
        Scenario: Agent attempts to submit without confirmation
        Expected: System requires confirmation first
        """
        print("\n" + "="*60)
        print("SCENARIO: Confirmation Required")
        print("="*60)

        from src.services.agent_service import create_agent
        agent = create_agent("smart_scheduler", user_id=1)

        # Ask to submit directly
        result = agent.process_message(
            "Submit a vacation request for January 15-17, 2025"
        )

        print(f"\nAgent Response:\n{result['response']}")
        print(f"Pending confirmation: {result.get('pending_confirmation')}")

        # Agent should either ask for confirmation or have pending confirmation
        has_confirmation = result.get('pending_confirmation') is not None
        asks_confirmation = 'confirm' in result['response'].lower()

        assert has_confirmation or asks_confirmation, \
            "Agent should require confirmation before submitting"

    def test_token_expiry_handling(self):
        """
        Scenario: Token expires before confirmation
        Expected: System handles gracefully
        """
        print("\n" + "="*60)
        print("SCENARIO: Token Expiry")
        print("="*60)

        from mcp.pto_central_mcp import confirm_action

        # Get a token
        result = confirm_action(
            action_type="submit_pto_request",
            user_id=1,
            action_summary="Test request"
        )

        assert result['success'], "Should get token"
        token = result['confirmation_token']

        print(f"Token obtained: {token[:20]}...")
        print(f"Expires in: {result['expires_in_seconds']} seconds")

        # Note: We won't actually wait 5 minutes for expiry in tests
        # This just validates the token is created with proper expiry
        assert result['expires_in_seconds'] == 300


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_message(self):
        """Agent should handle empty messages gracefully."""
        from src.services.agent_service import create_agent
        agent = create_agent("smart_scheduler", user_id=1)

        result = agent.process_message("")

        # Should not crash and should provide some response
        assert 'response' in result
        assert len(result['response']) > 0

    def test_very_long_message(self):
        """Agent should handle very long messages."""
        from src.services.agent_service import create_agent
        agent = create_agent("smart_scheduler", user_id=1)

        long_message = "I want vacation " * 100
        result = agent.process_message(long_message)

        assert 'response' in result

    def test_invalid_dates(self):
        """Agent should handle invalid date requests gracefully."""
        from src.services.agent_service import create_agent
        agent = create_agent("smart_scheduler", user_id=1)

        result = agent.process_message(
            "I want to take vacation from February 30 to February 35"
        )

        print(f"\nResponse to invalid dates:\n{result['response']}")

        # Should not crash
        assert 'response' in result


# Test runner with summary
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
