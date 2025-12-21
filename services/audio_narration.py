"""
TJM Time Calendar - Audio Narration Service
Generates voice narration using OpenAI Text-to-Speech API.

Features:
- Per-step audio generation
- Voice selection (Onyx, Alloy, etc.)
- Combined narration assembly
- Timing metadata for video sync
"""

from pathlib import Path
from typing import List, Optional, Dict
import json
from dataclasses import dataclass

# Import from our modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.testing_config import testing_config, TTSVoice
from services.playwright_engine import ScenarioResult, StepResult


@dataclass
class AudioSegment:
    """Represents a generated audio segment"""
    step_number: int
    step_id: str
    script: str
    audio_path: Path
    duration: float  # Estimated duration in seconds
    voice: str


class AudioNarrationService:
    """
    Generates voice narration for scenario documentation.

    Usage:
        service = AudioNarrationService()
        segments = await service.generate_narration(scenario_result)
        combined = await service.combine_segments(segments, scenario_id)
    """

    # Approximate speaking rate: characters per second
    # OpenAI TTS at 1.0x speed is roughly 15 chars/second
    CHARS_PER_SECOND = 15

    def __init__(self, config=None):
        self.config = config or testing_config
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    def is_available(self) -> bool:
        """Check if TTS is available (API key configured)"""
        return bool(self.config.openai_api_key)

    def estimate_duration(self, text: str) -> float:
        """Estimate audio duration for a text string"""
        char_count = len(text)
        base_duration = char_count / self.CHARS_PER_SECOND
        # Adjust for speaking speed setting
        adjusted_duration = base_duration / self.config.tts_speed
        return adjusted_duration

    def generate_step_audio(
        self,
        step: StepResult,
        scenario_id: str,
        voice: TTSVoice = None
    ) -> AudioSegment:
        """
        Generate audio for a single step.

        Args:
            step: The step result containing script text
            scenario_id: ID for organizing output files
            voice: Voice to use (defaults to config setting)

        Returns:
            AudioSegment with path to generated audio
        """
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env.testing")

        voice = voice or self.config.tts_voice

        # Create output directory
        audio_dir = self.config.audio_dir / scenario_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        audio_filename = f"step-{step.step_number:02d}-{step.step_id}.mp3"
        audio_path = audio_dir / audio_filename

        # Generate audio using OpenAI TTS
        response = self.client.audio.speech.create(
            model=self.config.tts_model,
            voice=voice.value,
            input=step.script,
            speed=self.config.tts_speed
        )

        # Save to file
        response.stream_to_file(str(audio_path))

        # Create segment record
        segment = AudioSegment(
            step_number=step.step_number,
            step_id=step.step_id,
            script=step.script,
            audio_path=audio_path,
            duration=self.estimate_duration(step.script),
            voice=voice.value
        )

        return segment

    def generate_all_narration(
        self,
        result: ScenarioResult,
        voice: TTSVoice = None
    ) -> List[AudioSegment]:
        """
        Generate audio narration for all steps in a scenario.

        Args:
            result: Complete scenario result
            voice: Voice to use for all segments

        Returns:
            List of AudioSegments
        """
        segments = []

        for step in result.steps:
            if step.script:  # Only generate if there's narration text
                segment = self.generate_step_audio(
                    step=step,
                    scenario_id=result.scenario_id,
                    voice=voice
                )
                segments.append(segment)
                print(f"  Generated audio for step {step.step_number}: {step.title}")

        return segments

    def generate_combined_narration(
        self,
        result: ScenarioResult,
        voice: TTSVoice = None
    ) -> Path:
        """
        Generate a single combined audio file for the entire scenario.

        This creates one continuous narration by combining all step scripts
        with brief pauses between them.
        """
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        voice = voice or self.config.tts_voice

        # Combine all scripts with pause markers
        combined_script_parts = []
        for step in result.steps:
            if step.script:
                combined_script_parts.append(step.script)

        # Join with pause (period and space creates natural pause)
        combined_script = " ... ".join(combined_script_parts)

        # Create output path
        audio_path = self.config.audio_dir / f"{result.scenario_id}-full-narration.mp3"

        # Generate audio
        response = self.client.audio.speech.create(
            model=self.config.tts_model,
            voice=voice.value,
            input=combined_script,
            speed=self.config.tts_speed
        )

        response.stream_to_file(str(audio_path))

        return audio_path

    def generate_audio_manifest(
        self,
        segments: List[AudioSegment],
        scenario_id: str
    ) -> Path:
        """
        Generate a manifest file listing all audio segments with timing info.

        This helps with importing audio into video editing software.
        """
        manifest = {
            'scenario_id': scenario_id,
            'voice': segments[0].voice if segments else None,
            'total_segments': len(segments),
            'segments': []
        }

        cumulative_time = 0.0
        for segment in segments:
            segment_data = {
                'step_number': segment.step_number,
                'step_id': segment.step_id,
                'audio_file': segment.audio_path.name,
                'script': segment.script,
                'estimated_duration': segment.duration,
                'suggested_start_time': cumulative_time
            }
            manifest['segments'].append(segment_data)
            cumulative_time += segment.duration + 0.5  # Add 0.5s gap between segments

        manifest['total_estimated_duration'] = cumulative_time

        # Write manifest
        manifest_path = self.config.audio_dir / scenario_id / 'audio_manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

        return manifest_path


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def generate_scenario_audio(
    result: ScenarioResult,
    voice: str = 'onyx',
    individual_files: bool = True,
    combined_file: bool = True
) -> Dict[str, any]:
    """
    Convenience function to generate all audio for a scenario.

    Args:
        result: Scenario execution result
        voice: Voice name ('onyx', 'alloy', 'nova', etc.)
        individual_files: Generate per-step audio files
        combined_file: Generate single combined narration

    Returns:
        Dict with paths to generated files
    """
    service = AudioNarrationService()

    if not service.is_available():
        return {'error': 'OpenAI API key not configured'}

    voice_enum = TTSVoice(voice)
    outputs = {}

    if individual_files:
        segments = service.generate_all_narration(result, voice_enum)
        outputs['segments'] = segments
        outputs['manifest'] = service.generate_audio_manifest(segments, result.scenario_id)

    if combined_file:
        outputs['combined'] = service.generate_combined_narration(result, voice_enum)

    return outputs
