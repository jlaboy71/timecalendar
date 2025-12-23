"""
Voice Integration Package
=========================
Provides voice interface capabilities for PTO Central.

Features:
- Text-to-speech using OpenAI TTS API
- Voice command parsing
- Confirmation handling

Usage:
    from src.services.voice import VoiceInterface, get_voice_interface

    voice = get_voice_interface()
    command = voice.parse_command("I want a week off")
"""

from .voice_interface import (
    VoiceInterface,
    VoiceStyle,
    VoiceCommand,
    get_voice_interface,
)

__all__ = [
    "VoiceInterface",
    "VoiceStyle",
    "VoiceCommand",
    "get_voice_interface",
]
