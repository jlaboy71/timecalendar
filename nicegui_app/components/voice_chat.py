"""
Voice-Enabled Chat Component
============================
Extends the chat interface with voice input/output capabilities.

Features:
- Push-to-talk voice input (browser Web Speech API)
- Text-to-speech for agent responses (OpenAI TTS)
- Visual feedback during recording
- Fallback to text when voice unavailable
"""

import asyncio
from typing import Optional, Callable
from nicegui import ui
import logging

logger = logging.getLogger(__name__)


class VoiceChatMixin:
    """
    Mixin to add voice capabilities to any chat interface.

    Add to your existing chat component:
        class MyChat(VoiceChatMixin, BaseChatInterface):
            pass
    """

    def __init__(self, *args, enable_tts: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_tts = enable_tts
        self.is_recording = False
        self.is_playing = False
        self._mic_button = None
        self._speaker_button = None
        self._recording_indicator = None
        self._voice_interface = None
        self._init_voice()

    def _init_voice(self):
        """Initialize voice interface."""
        try:
            from src.services.voice import get_voice_interface
            self._voice_interface = get_voice_interface("onyx")
        except Exception as e:
            logger.warning(f"Voice interface unavailable: {e}")

    def render_voice_controls(self):
        """Render voice input/output controls."""
        with ui.row().classes("items-center gap-2"):
            # Voice mode toggle
            ui.switch(
                "Voice",
                value=False,
                on_change=self._on_voice_toggle
            ).classes("mr-2").tooltip("Enable voice input")

            # Microphone button
            self._mic_button = ui.button(
                icon="mic",
                on_click=self._toggle_recording
            ).classes("hidden").props("round fab-mini color=grey")

            # Recording indicator
            self._recording_indicator = ui.row().classes("items-center gap-1 hidden")
            with self._recording_indicator:
                ui.spinner("audio", size="sm", color="red")
                ui.label("Listening...").classes("text-red-500 text-sm")

            # Speaker button (replay last response)
            if self.enable_tts:
                self._speaker_button = ui.button(
                    icon="volume_up",
                    on_click=self._replay_last
                ).classes("").props("round fab-mini color=grey")
                self._speaker_button.tooltip("Replay last response")

        # Inject Web Speech API JavaScript
        self._inject_speech_js()

    def _inject_speech_js(self):
        """Inject browser speech recognition."""
        ui.add_body_html("""
        <script>
        window.ptoVoice = {
            recognition: null,
            isRecording: false,

            init: function() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    console.warn('Speech recognition not supported');
                    return false;
                }

                this.recognition = new SpeechRecognition();
                this.recognition.continuous = false;
                this.recognition.interimResults = true;
                this.recognition.lang = 'en-US';

                this.recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    const input = document.querySelector('input[placeholder*="message"]');
                    if (input) {
                        input.value = transcript;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                };

                this.recognition.onend = () => {
                    this.isRecording = false;
                };

                return true;
            },

            start: function() {
                if (!this.recognition && !this.init()) return false;
                try {
                    this.recognition.start();
                    this.isRecording = true;
                    return true;
                } catch (e) {
                    console.error('Speech start failed:', e);
                    return false;
                }
            },

            stop: function() {
                if (this.recognition && this.isRecording) {
                    this.recognition.stop();
                    this.isRecording = false;
                }
            }
        };
        window.ptoVoice.init();
        </script>
        """)

    def _on_voice_toggle(self, e):
        """Handle voice mode toggle."""
        if e.value:
            self._mic_button.classes(remove="hidden")
            ui.notify("Voice mode enabled. Click mic to speak.", type="info")
        else:
            self._mic_button.classes(add="hidden")
            if self.is_recording:
                asyncio.create_task(self._toggle_recording())

    async def _toggle_recording(self):
        """Toggle voice recording."""
        self.is_recording = not self.is_recording

        if self.is_recording:
            await ui.run_javascript("window.ptoVoice.start()")
            self._mic_button.props("color=red")
            self._recording_indicator.classes(remove="hidden")
        else:
            await ui.run_javascript("window.ptoVoice.stop()")
            self._mic_button.props("color=grey")
            self._recording_indicator.classes(add="hidden")

    async def speak_text(self, text: str):
        """Convert text to speech and play."""
        if not self._voice_interface or not self.enable_tts:
            return

        try:
            audio_path = await self._voice_interface.text_to_speech(text)
            if audio_path:
                url = self._voice_interface.get_audio_url(audio_path.name)
                await ui.run_javascript(f"new Audio('{url}').play()")
        except Exception as e:
            logger.error(f"TTS failed: {e}")

    async def _replay_last(self):
        """Replay the last assistant message."""
        # Override in subclass to access messages
        pass


# Standalone function for quick integration
def add_voice_to_chat(container, on_transcript: Callable[[str], None]):
    """
    Add voice controls to any container.

    Args:
        container: NiceGUI container element
        on_transcript: Callback when speech is transcribed
    """
    with container:
        mixin = VoiceChatMixin.__new__(VoiceChatMixin)
        mixin.enable_tts = True
        mixin.is_recording = False
        mixin._voice_interface = None
        mixin._init_voice()
        mixin.render_voice_controls()
    return mixin
