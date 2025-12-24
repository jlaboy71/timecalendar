"""
Voice Settings Component
========================
User preferences for voice interaction.
"""

from nicegui import ui
from typing import Callable, Optional


class VoiceSettings:
    """Settings panel for voice preferences."""

    VOICES = {
        "onyx": "Onyx (Deep, Professional)",
        "alloy": "Alloy (Neutral)",
        "echo": "Echo (Warm)",
        "nova": "Nova (Friendly)",
        "shimmer": "Shimmer (Soft)",
    }

    def __init__(
        self,
        current_voice: str = "onyx",
        auto_play: bool = False,
        on_save: Optional[Callable] = None
    ):
        self.voice = current_voice
        self.auto_play = auto_play
        self.on_save = on_save

    def render(self):
        """Render settings panel."""
        with ui.card().classes("p-4 w-80"):
            ui.label("Voice Settings").classes("font-bold mb-4")

            ui.select(
                label="Voice",
                options=self.VOICES,
                value=self.voice,
                on_change=lambda e: setattr(self, 'voice', e.value)
            ).classes("w-full mb-2")

            ui.switch(
                "Auto-play responses",
                value=self.auto_play,
                on_change=lambda e: setattr(self, 'auto_play', e.value)
            )

            with ui.row().classes("mt-4 gap-2"):
                ui.button("Test", on_click=self._test).props("flat")
                ui.button("Save", on_click=self._save).props("color=primary")

    async def _test(self):
        """Test current voice."""
        try:
            from src.services.voice import get_voice_interface
            voice = get_voice_interface(self.voice)
            if voice.api_key:
                path = await voice.text_to_speech("Hello, I'm your PTO assistant.")
                if path:
                    await ui.run_javascript(f"new Audio('{voice.get_audio_url(path.name)}').play()")
            else:
                ui.notify("OpenAI API key not configured", type="warning")
        except Exception as e:
            ui.notify(f"Test failed: {e}", type="negative")

    def _save(self):
        """Save settings."""
        if self.on_save:
            self.on_save({"voice": self.voice, "auto_play": self.auto_play})
        ui.notify("Settings saved", type="positive")
