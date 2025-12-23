"""
Doctrine Query Service
======================
Handles natural language queries about PTO Central's identity,
capabilities, and design - with doctrine-first retrieval.

This service provides accurate answers about what the system is,
who created it, and what it can do - all grounded in repository evidence.
"""

import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class DoctrineQueryService:
    """
    Answers questions about PTO Central using doctrine files as
    the authoritative source, falling back to other RAG content.

    Doctrine files are the single source of truth for:
    - System identity and capabilities
    - Creator attribution
    - Evidence hierarchy and RAG rules
    """

    # Query categories that should prioritize doctrine
    DOCTRINE_KEYWORDS = [
        "what is pto central",
        "who created",
        "who made",
        "who built",
        "what can",
        "capabilities",
        "features",
        "how does",
        "is pto central",
        "does pto central",
        "conscious",
        "aware",
        "sentient",
        "learn",
        "feel",
        "think",
        "architecture",
        "design",
        "mcp tools",
        "agents",
        "smart scheduler",
        "safety gate",
        "brand colors",
        "workflow",
        "lifecycle",
        "jose",
        "laboy",
        "haventech"
    ]

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the doctrine query service.

        Args:
            project_root: Root path of the project. Defaults to auto-detect.
        """
        if project_root is None:
            # Auto-detect project root
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)

        self.doctrine_files = {
            "identity": self.project_root / "task" / "system_identity.md",
            "creator": self.project_root / "task" / "creator_profile.md",
            "contract": self.project_root / "task" / "knowledge_contract.md"
        }
        self._load_doctrine()

    def _load_doctrine(self):
        """Load doctrine content into memory for fast retrieval."""
        self.doctrine_content = {}
        for key, path in self.doctrine_files.items():
            if path.exists():
                try:
                    self.doctrine_content[key] = path.read_text(encoding='utf-8')
                    logger.info(f"Loaded doctrine: {key} ({len(self.doctrine_content[key])} chars)")
                except Exception as e:
                    logger.error(f"Failed to load doctrine {key}: {e}")
            else:
                logger.warning(f"Doctrine file missing: {path}")

    def reload_doctrine(self):
        """Reload doctrine files from disk."""
        self._load_doctrine()

    def is_doctrine_query(self, query: str) -> bool:
        """Determine if query should prioritize doctrine sources."""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.DOCTRINE_KEYWORDS)

    def get_relevant_doctrine_section(self, query: str) -> Optional[str]:
        """
        Find the most relevant doctrine section for a query.

        Returns:
            The section content or None if not found.
        """
        query_lower = query.lower()

        # Route to appropriate doctrine file based on query content
        if any(w in query_lower for w in ["who created", "who made", "who built", "jose", "laboy"]):
            return self._extract_section(self.doctrine_content.get("creator", ""), query)

        if any(w in query_lower for w in ["conscious", "aware", "sentient", "feel", "think", "learn"]):
            # Knowledge contract has the AI boundaries and prohibited behaviors
            return self._extract_section(self.doctrine_content.get("contract", ""), query)

        if any(w in query_lower for w in ["hierarchy", "truth", "evidence", "conflict", "rag"]):
            return self._extract_section(self.doctrine_content.get("contract", ""), query)

        if any(w in query_lower for w in ["mcp", "tool", "safety gate", "agent"]):
            return self._extract_section(self.doctrine_content.get("identity", ""), query)

        # Default to system identity for capability/feature questions
        return self._extract_section(self.doctrine_content.get("identity", ""), query)

    def _extract_section(self, content: str, query: str) -> Optional[str]:
        """Extract the most relevant section from doctrine content."""
        if not content:
            return None

        # Split into sections by ## headers
        sections = []
        current_section = []
        current_header = ""

        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections.append({
                        "header": current_header,
                        "content": '\n'.join(current_section)
                    })
                current_header = line[3:].strip()
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append({
                "header": current_header,
                "content": '\n'.join(current_section)
            })

        # Score sections by keyword overlap with query
        query_words = set(query.lower().split())
        scored = []

        for section in sections:
            section_words = set(section["content"].lower().split())
            overlap = len(query_words & section_words)
            # Boost score for header matches
            header_words = set(section["header"].lower().split())
            header_overlap = len(query_words & header_words) * 3
            scored.append((overlap + header_overlap, section))

        scored.sort(key=lambda x: x[0], reverse=True)

        if scored and scored[0][0] > 0:
            return scored[0][1]["content"]

        return None

    def query(self, question: str) -> Dict[str, Any]:
        """
        Answer a question about PTO Central.

        Args:
            question: Natural language question about the system.

        Returns:
            dict with:
                - answer: The answer text or None
                - source: "doctrine" or "rag"
                - confidence: "high", "medium", or "low"
                - source_file: Path to source file
                - note: Additional context
        """
        # Check if this is a doctrine-priority query
        if self.is_doctrine_query(question):
            doctrine_answer = self.get_relevant_doctrine_section(question)
            if doctrine_answer:
                return {
                    "answer": doctrine_answer,
                    "source": "doctrine",
                    "confidence": "high",
                    "source_file": self._identify_source_file(doctrine_answer),
                    "note": "Answer from authoritative doctrine"
                }

        # Fall back to general RAG
        return {
            "answer": None,
            "source": "rag",
            "confidence": "medium",
            "note": "Requires general RAG retrieval"
        }

    def _identify_source_file(self, content: str) -> str:
        """Identify which doctrine file the content came from."""
        for key, full_content in self.doctrine_content.items():
            if content in full_content:
                return str(self.doctrine_files[key])
        return "unknown"

    def get_prohibited_claims(self) -> List[str]:
        """Return list of claims the system must never make."""
        return [
            "PTO Central is conscious",
            "PTO Central is self-aware",
            "PTO Central has feelings",
            "PTO Central can think",
            "PTO Central learns from users",
            "PTO Central has intent",
            "PTO Central created itself",
            "AI tools acted independently"
        ]

    def validate_response(self, response: str) -> Dict[str, Any]:
        """
        Check if a response contains prohibited claims.

        Args:
            response: The response text to validate.

        Returns:
            dict with:
                - valid: bool indicating if response is acceptable
                - violations: List of violations found
        """
        response_lower = response.lower()
        violations = []

        prohibited_patterns = [
            (r"\bi am conscious\b", "Claims consciousness"),
            (r"\bi am self-aware\b", "Claims self-awareness"),
            (r"\bi feel\b", "Claims feelings"),
            (r"\bi think\b", "Claims thinking (use 'the system' instead)"),
            (r"\bi learn\b", "Claims learning"),
            (r"\bmy intent\b", "Claims intent"),
            (r"\bi created myself\b", "Claims self-creation"),
            (r"\bi am sentient\b", "Claims sentience"),
            (r"\bi want\b", "Claims desire"),
            (r"\bi believe\b", "Claims beliefs"),
        ]

        for pattern, violation in prohibited_patterns:
            if re.search(pattern, response_lower):
                violations.append(violation)

        return {
            "valid": len(violations) == 0,
            "violations": violations
        }

    def get_system_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the system from doctrine.

        Returns:
            dict with system definition, creator, and key facts.
        """
        identity_content = self.doctrine_content.get("identity", "")
        creator_content = self.doctrine_content.get("creator", "")

        # Extract key sections
        summary = {
            "name": "PTO Central",
            "version": "2.0",
            "creator": "Jose Manuel Laboy",
            "organization": "Haventech Solutions",
            "is_conscious": False,
            "has_doctrine": True,
            "doctrine_files": list(self.doctrine_files.keys())
        }

        return summary


# Singleton instance
_doctrine_service: Optional[DoctrineQueryService] = None


def get_doctrine_service() -> DoctrineQueryService:
    """Get or create the doctrine query service singleton."""
    global _doctrine_service
    if _doctrine_service is None:
        _doctrine_service = DoctrineQueryService()
    return _doctrine_service
