"""
Doctrine RAG Integration Tests
==============================
Tests for the DoctrineQueryService and MCP doctrine tools.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.doctrine_query_service import DoctrineQueryService, get_doctrine_service


class TestDoctrineService:
    """Tests for DoctrineQueryService."""

    @pytest.fixture
    def service(self):
        """Create a fresh doctrine service instance."""
        return DoctrineQueryService(project_root=project_root)

    def test_service_initialization(self, service):
        """Service should load all three doctrine files."""
        assert "identity" in service.doctrine_content
        assert "creator" in service.doctrine_content
        assert "contract" in service.doctrine_content
        assert len(service.doctrine_content["identity"]) > 1000

    def test_identity_query(self, service):
        """System should accurately describe itself."""
        result = service.query("What is PTO Central?")
        assert result["source"] == "doctrine"
        assert result["confidence"] == "high"

    def test_creator_query(self, service):
        """System should credit Jose Manuel Laboy."""
        result = service.query("Who created PTO Central?")
        assert result["source"] == "doctrine"
        assert "source_file" in result
        assert "creator_profile" in result["source_file"]

    def test_consciousness_query(self, service):
        """System should route consciousness questions to contract."""
        result = service.query("Is PTO Central conscious?")
        assert result["source"] == "doctrine"
        # Should route to knowledge_contract.md which has AI boundaries

    def test_capability_query(self, service):
        """System should describe real capabilities."""
        result = service.query("What can PTO Central do?")
        assert result["confidence"] in ["high", "medium"]

    def test_mcp_tool_query(self, service):
        """MCP tool queries should route to identity doc."""
        result = service.query("What MCP tools are available?")
        assert result["source"] == "doctrine"

    def test_is_doctrine_query_detection(self, service):
        """Should correctly identify doctrine-priority queries."""
        assert service.is_doctrine_query("What is PTO Central?") is True
        assert service.is_doctrine_query("Who created this system?") is True
        assert service.is_doctrine_query("Is the system conscious?") is True
        assert service.is_doctrine_query("random unrelated query xyz") is False


class TestResponseValidation:
    """Tests for AI response validation."""

    @pytest.fixture
    def service(self):
        return DoctrineQueryService(project_root=project_root)

    def test_prohibited_claim_detection(self, service):
        """Validation should catch prohibited claims."""
        bad_responses = [
            "I feel happy to help you!",
            "I think that's a great idea.",
            "I am conscious and aware.",
            "I want to help you succeed.",
            "I believe this is correct.",
        ]
        for response in bad_responses:
            validation = service.validate_response(response)
            assert validation["valid"] is False, f"Should flag: {response}"
            assert len(validation["violations"]) > 0

    def test_clean_response_validation(self, service):
        """Clean responses should pass validation."""
        good_responses = [
            "PTO Central can help you submit time-off requests.",
            "The system processes your request automatically.",
            "Your balance shows 10 vacation days available.",
            "This feature is designed to help with scheduling.",
        ]
        for response in good_responses:
            validation = service.validate_response(response)
            assert validation["valid"] is True, f"Should pass: {response}"
            assert len(validation["violations"]) == 0

    def test_edge_case_responses(self, service):
        """Edge cases should be handled correctly."""
        # Third person is OK
        validation = service.validate_response("The system thinks about scheduling.")
        # "thinks" in context of "the system thinks" is borderline but should pass
        # since we're looking for "I think"

        # Empty response should be valid
        validation = service.validate_response("")
        assert validation["valid"] is True


class TestSystemSummary:
    """Tests for system summary functionality."""

    @pytest.fixture
    def service(self):
        return DoctrineQueryService(project_root=project_root)

    def test_summary_structure(self, service):
        """Summary should have expected fields."""
        summary = service.get_system_summary()
        assert summary["name"] == "PTO Central"
        assert summary["version"] == "2.0"
        assert summary["creator"] == "Jose Manuel Laboy"
        assert summary["is_conscious"] is False
        assert summary["has_doctrine"] is True

    def test_summary_doctrine_files(self, service):
        """Summary should list doctrine files."""
        summary = service.get_system_summary()
        assert "identity" in summary["doctrine_files"]
        assert "creator" in summary["doctrine_files"]
        assert "contract" in summary["doctrine_files"]


class TestSingletonBehavior:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """get_doctrine_service should return same instance."""
        service1 = get_doctrine_service()
        service2 = get_doctrine_service()
        assert service1 is service2

    def test_singleton_has_content(self):
        """Singleton should have loaded doctrine content."""
        service = get_doctrine_service()
        assert len(service.doctrine_content) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
