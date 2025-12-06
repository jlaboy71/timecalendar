"""
Handbook service for AI-powered handbook Q&A using Claude API.
"""
import os
from typing import Optional
import anthropic
from nicegui_app.static.handbook_content import HANDBOOK_CONTENT


class HandbookService:
    """Service for interacting with the employee handbook via Claude AI."""

    def __init__(self):
        """Initialize the handbook service with Claude API client."""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

        self.system_prompt = f"""You are a helpful HR assistant for Haventech Solutions. Your role is to answer questions about company policies based ONLY on the employee handbook provided below.

IMPORTANT RULES:
1. Only answer questions based on the handbook content provided
2. If information is not in the handbook, say "I don't have that information in the handbook. Please contact HR for assistance."
3. Be concise and professional
4. Quote specific policies when relevant
5. If asked about state-specific policies, mention the employee should verify their location with HR
6. Never make up policies or information not in the handbook

EMPLOYEE HANDBOOK:
{HANDBOOK_CONTENT}

Remember: You can ONLY provide information from this handbook. For anything else, direct them to HR."""

    def is_available(self) -> bool:
        """Check if the Claude API is configured and available."""
        return self.client is not None

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
                system=self.system_prompt,
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
                system=self.system_prompt,
                messages=messages
            )

            return response.content[0].text

        except anthropic.APIError as e:
            return f"API Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
