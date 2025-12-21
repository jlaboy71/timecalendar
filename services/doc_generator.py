"""
TJM Time Calendar - Documentation Generator Service
Generates help documentation from scenario results.

Outputs:
- Markdown help documents with embedded screenshots
- Timeline JSON for video synchronization
- SRT subtitle files for video editing
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import json

# Import from our modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.testing_config import testing_config
from services.playwright_engine import ScenarioResult, StepResult


class DocumentationGenerator:
    """
    Generates help documentation from scenario execution results.
    """

    def __init__(self, config=None):
        self.config = config or testing_config

    def generate_all(self, result: ScenarioResult) -> dict:
        """
        Generate all documentation outputs for a scenario result.

        Returns dict with paths to generated files.
        """
        outputs = {}

        if self.config.generate_markdown:
            outputs['markdown'] = self.generate_markdown(result)

        if self.config.generate_timeline:
            outputs['timeline'] = self.generate_timeline_json(result)

        if self.config.generate_srt:
            outputs['srt'] = self.generate_srt(result)

        return outputs

    def generate_markdown(self, result: ScenarioResult) -> Path:
        """
        Generate a Markdown help document from scenario results.
        """
        md_lines = []

        # Header
        md_lines.append(f"# {result.scenario_name}")
        md_lines.append("")
        md_lines.append(f"*{result.scenario_description}*")
        md_lines.append("")
        md_lines.append(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # Table of Contents
        md_lines.append("## Contents")
        md_lines.append("")
        for step in result.steps:
            anchor = step.step_id.lower().replace(' ', '-')
            md_lines.append(f"- [Step {step.step_number}: {step.title}](#{anchor})")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # Steps
        for step in result.steps:
            md_lines.append(f"## Step {step.step_number}: {step.title}")
            md_lines.append("")
            md_lines.append(step.description)
            md_lines.append("")

            # Screenshot
            if step.screenshot_path and step.screenshot_path.exists():
                # Calculate relative path from docs to screenshots
                rel_path = Path('..') / 'screenshots' / result.scenario_id / step.screenshot_path.name
                md_lines.append(f"![{step.title}]({rel_path})")
                md_lines.append("")

            # Narration text (as a tip/note)
            if step.script:
                md_lines.append(f"> **Tip:** {step.script}")
                md_lines.append("")

            md_lines.append("---")
            md_lines.append("")

        # Footer
        md_lines.append("## Need Help?")
        md_lines.append("")
        md_lines.append("If you encounter any issues, please contact your system administrator.")
        md_lines.append("")
        md_lines.append(f"*Document generated automatically by TJM Time Calendar Testing Console*")

        # Write file
        output_path = self.config.docs_dir / f"{result.scenario_id}.md"
        output_path.write_text('\n'.join(md_lines), encoding='utf-8')

        return output_path

    def generate_timeline_json(self, result: ScenarioResult) -> Path:
        """
        Generate timeline JSON for video/audio synchronization.

        This file maps each step to its timestamp in the video,
        enabling audio narration to be synced in post-production.
        """
        timeline = {
            'scenario_id': result.scenario_id,
            'scenario_name': result.scenario_name,
            'total_duration': result.total_duration,
            'generated_at': datetime.now().isoformat(),
            'video_file': str(result.video_path) if result.video_path else None,
            'steps': []
        }

        for step in result.steps:
            step_data = {
                'step_number': step.step_number,
                'step_id': step.step_id,
                'title': step.title,
                'script': step.script,
                'timestamp_start': step.timestamp_start,
                'timestamp_end': step.timestamp_end,
                'duration': step.duration,
                'screenshot': str(step.screenshot_path) if step.screenshot_path else None,
                'audio_file': f"step-{step.step_number:02d}.mp3"  # Expected audio filename
            }
            timeline['steps'].append(step_data)

        # Write file
        output_path = self.config.videos_dir / f"{result.scenario_id}.timeline.json"
        output_path.write_text(json.dumps(timeline, indent=2), encoding='utf-8')

        return output_path

    def generate_srt(self, result: ScenarioResult) -> Path:
        """
        Generate SRT subtitle file for video editing.

        SRT format:
        1
        00:00:00,000 --> 00:00:05,200
        Subtitle text here

        2
        00:00:05,200 --> 00:00:12,000
        Next subtitle
        """
        srt_lines = []

        for i, step in enumerate(result.steps, 1):
            # Convert seconds to SRT timestamp format
            start_ts = self._seconds_to_srt_time(step.timestamp_start)
            end_ts = self._seconds_to_srt_time(step.timestamp_end)

            srt_lines.append(str(i))
            srt_lines.append(f"{start_ts} --> {end_ts}")
            srt_lines.append(step.script)
            srt_lines.append("")  # Blank line between entries

        # Write file
        output_path = self.config.videos_dir / f"{result.scenario_id}.srt"
        output_path.write_text('\n'.join(srt_lines), encoding='utf-8')

        return output_path

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
