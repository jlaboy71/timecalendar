"""
Voice Interface Service
=======================
Foundation for voice-to-PTO integration.

Provides:
- Text-to-speech for agent responses (OpenAI TTS)
- Voice command parsing
- Conversational shortcuts
- Audio file management

Uses OpenAI TTS API with 'onyx' voice (Jose's preference).

Example Usage:
    from src.services.voice.voice_interface import VoiceInterface

    voice = VoiceInterface()

    # Convert agent response to audio
    audio_path = await voice.text_to_speech(
        "I found a great option! Take February 18-21 for 9 days off.",
        filename="scheduler_response.mp3"
    )

    # Parse voice command
    command = voice.parse_command("I want to take a week off next month")
    print(command.intent)  # "request_vacation"
    print(command.entities)  # {"duration": 5, "timing": "next month"}
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class VoiceStyle(Enum):
    """
    Available TTS voice styles from OpenAI.

    Jose prefers 'onyx' for its professional, deep tone.
    """
    ALLOY = "alloy"       # Neutral, balanced
    ECHO = "echo"         # Warm, conversational
    FABLE = "fable"       # Expressive, British accent
    ONYX = "onyx"         # Deep, professional (DEFAULT)
    NOVA = "nova"         # Friendly, energetic
    SHIMMER = "shimmer"   # Soft, gentle


@dataclass
class VoiceCommand:
    """
    Parsed voice command with intent and entities.

    Attributes:
        intent: The detected action (request_vacation, check_balance, etc.)
        entities: Extracted parameters (dates, duration, leave type)
        confidence: How confident the parse is (0.0 - 1.0)
        raw_text: Original transcribed text
    """
    intent: str
    entities: Dict[str, Any]
    confidence: float
    raw_text: str


class VoiceInterface:
    """
    Handles voice interactions with PTO Central.

    Workflow:
    1. User speaks -> External transcription (Whisper API or browser)
    2. Transcribed text -> parse_command() -> VoiceCommand
    3. VoiceCommand -> Agent processing
    4. Agent response -> text_to_speech() -> Audio file
    5. Audio file -> Played to user

    Note: This service handles TTS output and command parsing.
    Speech-to-text (input) is handled externally.
    """

    # Voice command patterns for intent detection
    INTENT_PATTERNS = {
        "request_vacation": [
            "take vacation",
            "take time off",
            "take a week off",
            "take a day off",
            "schedule vacation",
            "book time off",
            "request vacation",
            "i want vacation",
            "i need time off",
            "plan vacation",
        ],
        "check_balance": [
            "how much pto",
            "how many days",
            "check my balance",
            "what's my balance",
            "pto balance",
            "vacation balance",
            "days remaining",
            "days left",
            "time off balance",
        ],
        "cancel_request": [
            "cancel my request",
            "cancel vacation",
            "cancel time off",
            "don't need that time",
            "nevermind the request",
            "withdraw request",
        ],
        "approve_request": [
            "approve the request",
            "approve it",
            "looks good approve",
            "yes approve",
            "go ahead and approve",
        ],
        "deny_request": [
            "deny the request",
            "deny it",
            "can't approve",
            "reject the request",
        ],
        "confirm_action": [
            "yes",
            "confirm",
            "do it",
            "go ahead",
            "that's right",
            "sounds good",
            "approved",
            "yes please",
        ],
        "cancel_action": [
            "no",
            "cancel",
            "stop",
            "don't",
            "never mind",
            "forget it",
            "wait",
        ],
    }

    def __init__(
        self,
        voice: VoiceStyle = VoiceStyle.ONYX,
        output_dir: Optional[str] = None
    ):
        """
        Initialize Voice Interface.

        Args:
            voice: TTS voice style (default: ONYX)
            output_dir: Where to save audio files
        """
        self.voice = voice
        self.output_dir = Path(output_dir or "nicegui_app/static/audio/voice")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check for API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning(
                "OPENAI_API_KEY not set - TTS will be unavailable. "
                "Set it in .env file or environment."
            )

    async def text_to_speech(
        self,
        text: str,
        filename: Optional[str] = None,
        voice: Optional[VoiceStyle] = None
    ) -> Optional[Path]:
        """
        Convert text to speech audio file.

        Args:
            text: Text to convert to speech
            filename: Output filename (auto-generated if not provided)
            voice: Override default voice style

        Returns:
            Path to audio file, or None if TTS unavailable/failed
        """
        if not self.api_key:
            logger.error("Cannot generate TTS: OPENAI_API_KEY not set")
            return None

        if not text or len(text.strip()) == 0:
            logger.warning("Cannot generate TTS: Empty text")
            return None

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            # Generate filename from text hash if not provided
            if not filename:
                text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
                filename = f"voice_{text_hash}.mp3"

            # Ensure .mp3 extension
            if not filename.endswith(".mp3"):
                filename += ".mp3"

            output_path = self.output_dir / filename

            # Format text for better speech
            formatted_text = self._format_for_speech(text)

            # Generate audio
            response = await client.audio.speech.create(
                model="tts-1",
                voice=(voice or self.voice).value,
                input=formatted_text
            )

            # Save to file
            with open(output_path, "wb") as f:
                async for chunk in response.iter_bytes():
                    f.write(chunk)

            logger.info(f"Generated TTS audio: {output_path}")
            return output_path

        except ImportError:
            logger.error("OpenAI package not installed. Run: pip install openai")
            return None
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None

    def parse_command(self, text: str) -> VoiceCommand:
        """
        Parse natural language into structured command.

        Uses pattern matching to detect intent and extract entities.
        For production, consider using Claude for more sophisticated NLU.

        Args:
            text: Transcribed voice input

        Returns:
            VoiceCommand with intent, entities, and confidence
        """
        if not text:
            return VoiceCommand(
                intent="unknown",
                entities={},
                confidence=0.0,
                raw_text=""
            )

        text_lower = text.lower().strip()

        # Find best matching intent
        best_intent = "unknown"
        best_confidence = 0.0

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Calculate confidence based on pattern coverage
                    confidence = len(pattern) / max(len(text_lower), 1)
                    confidence = min(confidence * 1.5, 1.0)  # Boost but cap at 1.0

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent

        # Extract entities
        entities = self._extract_entities(text_lower)

        return VoiceCommand(
            intent=best_intent,
            entities=entities,
            confidence=round(best_confidence, 2),
            raw_text=text
        )

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities like dates, durations, and leave types."""
        entities = {}

        # Duration extraction
        # "a week" / "one week"
        if re.search(r'\b(a|one)\s+week\b', text):
            entities["duration"] = 5
            entities["duration_unit"] = "business_days"

        # "X days"
        days_match = re.search(r'(\d+)\s*days?\b', text)
        if days_match:
            entities["duration"] = int(days_match.group(1))
            entities["duration_unit"] = "days"

        # "two weeks" / "2 weeks"
        weeks_match = re.search(r'(two|\d+)\s*weeks?\b', text)
        if weeks_match:
            weeks_str = weeks_match.group(1)
            weeks = 2 if weeks_str == "two" else int(weeks_str)
            entities["duration"] = weeks * 5
            entities["duration_unit"] = "business_days"

        # Month extraction
        months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        for i, month in enumerate(months, 1):
            if month in text:
                entities["month"] = month.capitalize()
                entities["month_number"] = i
                break

        # Relative timing
        if "next week" in text:
            entities["timing"] = "next_week"
        elif "next month" in text:
            entities["timing"] = "next_month"
        elif "this week" in text:
            entities["timing"] = "this_week"
        elif "tomorrow" in text:
            entities["timing"] = "tomorrow"

        # Leave type
        if "sick" in text:
            entities["leave_type"] = "sick"
        elif "personal" in text:
            entities["leave_type"] = "personal"
        elif "vacation" in text:
            entities["leave_type"] = "vacation"

        return entities

    def _format_for_speech(self, text: str) -> str:
        """
        Format text to sound more natural when spoken.

        - Expands abbreviations
        - Adds appropriate pauses
        - Makes dates more speakable
        """
        # Expand abbreviations
        replacements = {
            "PTO": "P T O",
            "HR": "H R",
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "and so on",
            "vs.": "versus",
            "#": "number ",
            "Dec": "December",
            "Jan": "January",
            "Feb": "February",
        }

        result = text
        for abbr, expansion in replacements.items():
            result = result.replace(abbr, expansion)

        # Add pauses for bullet points / lists
        result = result.replace("*", "... ")
        result = result.replace(" - ", " ... ")

        # Make dates more natural
        result = re.sub(
            r'(\d{4})-(\d{2})-(\d{2})',
            lambda m: f"{self._month_name(int(m.group(2)))} {int(m.group(3))}, {m.group(1)}",
            result
        )

        return result

    def _month_name(self, month_num: int) -> str:
        """Convert month number to name."""
        months = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return months[month_num] if 1 <= month_num <= 12 else str(month_num)

    def is_confirmation(self, text: str) -> Optional[bool]:
        """
        Check if text is a confirmation or denial.

        Returns:
            True = confirmation, False = denial, None = unclear
        """
        command = self.parse_command(text)

        if command.intent == "confirm_action":
            return True
        elif command.intent == "cancel_action":
            return False
        else:
            return None

    def generate_confirmation_prompt(
        self,
        action_summary: str,
        is_retry: bool = False
    ) -> str:
        """
        Generate a voice-friendly confirmation prompt.

        Args:
            action_summary: What action is being confirmed
            is_retry: True if this is a repeat ask

        Returns:
            Text suitable for TTS
        """
        if is_retry:
            return (
                "I didn't quite catch that. "
                f"Should I {action_summary}? "
                "Just say yes to confirm, or no to cancel."
            )
        else:
            return (
                f"I'm ready to {action_summary}. "
                "Would you like me to go ahead? "
                "Say yes to confirm, or no to cancel."
            )

    def get_audio_url(self, filename: str) -> str:
        """Get the URL path for an audio file."""
        return f"/static/audio/voice/{filename}"

    def cleanup_old_audio(self, max_age_hours: int = 24) -> int:
        """
        Remove audio files older than max_age_hours.

        Returns number of files removed.
        """
        import time

        removed = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        for audio_file in self.output_dir.glob("*.mp3"):
            if now - audio_file.stat().st_mtime > max_age_seconds:
                audio_file.unlink()
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old audio files")

        return removed


# Convenience function
def get_voice_interface(voice: str = "onyx") -> VoiceInterface:
    """Get configured voice interface with specified voice."""
    try:
        voice_style = VoiceStyle(voice)
    except ValueError:
        voice_style = VoiceStyle.ONYX
    return VoiceInterface(voice=voice_style)


# Module exports
__all__ = [
    "VoiceInterface",
    "VoiceStyle",
    "VoiceCommand",
    "get_voice_interface",
]
