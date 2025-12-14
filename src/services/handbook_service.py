"""
Handbook service for AI-powered handbook Q&A using Claude API.
"""
import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)


class HandbookService:
    """Service for interacting with the employee handbook via Claude AI."""

    def __init__(self, db_session=None):
        """
        Initialize the handbook service with Claude API client.

        Args:
            db_session: Optional database session to fetch active handbook content
        """
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        self._db_session = db_session
        self._handbook_content = None

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def _get_handbook_content(self) -> str:
        """
        Get the current handbook content from database or fall back to static file.

        Returns:
            The handbook content as a string
        """
        if self._handbook_content:
            return self._handbook_content

        # Try to get from database first
        try:
            if self._db_session:
                from src.models.handbook_revision import HandbookRevision
                active = self._db_session.query(HandbookRevision).filter(
                    HandbookRevision.is_active == True
                ).first()
                if active:
                    self._handbook_content = active.content
                    logger.debug(f"Loaded handbook version {active.version} from database")
                    return self._handbook_content
        except Exception as e:
            logger.warning(f"Could not load handbook from database: {e}")

        # Fall back to static content
        try:
            from nicegui_app.static.handbook_content import HANDBOOK_CONTENT
            self._handbook_content = HANDBOOK_CONTENT
            logger.debug("Loaded handbook from static file")
            return self._handbook_content
        except ImportError:
            logger.error("Could not load handbook content from any source")
            return "Handbook content unavailable."

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current handbook content."""
        content = self._get_handbook_content()
        return f"""You are a helpful HR assistant for Haventech LLC. Your role is to answer questions about company policies based ONLY on the employee handbook provided below.

IMPORTANT RULES:
1. Only answer questions based on the handbook content provided
2. If information is not in the handbook, say "I don't have that information in the handbook. Please contact HR for assistance."
3. Be concise and professional
4. Quote specific policies when relevant
5. If asked about state-specific policies, mention the employee should verify their location with HR
6. Never make up policies or information not in the handbook

EMPLOYEE HANDBOOK:
{content}

Remember: You can ONLY provide information from this handbook. For anything else, direct them to HR."""

    def is_available(self) -> bool:
        """Check if the Claude API is configured and available."""
        return self.client is not None

    def get_handbook_version(self) -> Optional[str]:
        """Get the current handbook version if loaded from database."""
        try:
            if self._db_session:
                from src.models.handbook_revision import HandbookRevision
                active = self._db_session.query(HandbookRevision).filter(
                    HandbookRevision.is_active == True
                ).first()
                if active:
                    return active.version
        except Exception:
            pass
        return None

    async def ask_question(self, question: str, conversation_history: list = None) -> str:
        """
        Ask a question about the handbook.

        Args:
            question: The user's question
            conversation_history: Optional list of previous messages for context

        Returns:
            The AI response as a string
        """
        if not self.is_available():
            return "AI assistant is not configured. Please add ANTHROPIC_API_KEY to your .env file."

        try:
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add the current question
            messages.append({
                "role": "user",
                "content": question
            })

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self._build_system_prompt(),
                messages=messages
            )

            return response.content[0].text

        except anthropic.APIError as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def ask_question_sync(self, question: str, conversation_history: list = None) -> str:
        """
        Synchronous version of ask_question for use in non-async contexts.

        Args:
            question: The user's question
            conversation_history: Optional list of previous messages for context

        Returns:
            The AI response as a string
        """
        if not self.is_available():
            return "AI assistant is not configured. Please add ANTHROPIC_API_KEY to your .env file."

        try:
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add the current question
            messages.append({
                "role": "user",
                "content": question
            })

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self._build_system_prompt(),
                messages=messages
            )

            return response.content[0].text

        except anthropic.APIError as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
