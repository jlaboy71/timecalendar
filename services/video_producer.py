"""
PTO Central - Professional Video Producer Service
Creates high-quality training videos from screenshots with audio narration.

Features:
- Screenshot annotation (arrows, circles, highlights, text callouts)
- Element focus highlighting via CSS injection
- Video compilation with MoviePy
- Audio synchronization with per-frame timing
- Director timing system for professional pacing

Sources:
- MoviePy: https://github.com/Zulko/moviepy
- Pillow ImageDraw: https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html
- Playwright Screenshots: https://playwright.dev/python/docs/screenshots
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math

# Image processing
from PIL import Image, ImageDraw, ImageFont, ImageFilter


class VideoEffect(Enum):
    """Video effect types for training videos"""
    NONE = "none"           # Basic video, no effects
    ZOOM = "zoom"           # Ken Burns zoom effect
    HIGHLIGHT = "highlight" # Gold highlight box on action areas
    HYBRID = "hybrid"       # Both zoom and highlight

# Video production
try:
    from moviepy import ImageSequenceClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    from moviepy import ImageClip, VideoFileClip, CompositeAudioClip
    from proglog import ProgressBarLogger
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: MoviePy not available. Video production disabled.")


class CallbackProgressLogger(ProgressBarLogger):
    """
    Custom proglog logger that forwards progress to a callback function.
    This allows MoviePy's encoding progress to be displayed in the GUI.
    """

    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        super().__init__()
        self._progress_callback = progress_callback
        self._last_percent = -1

    def bars_callback(self, bar, attr, value, old_value=None):
        """Called when progress bar updates - this is where we intercept progress"""
        if attr == 'index' and hasattr(bar, 'total') and bar.total > 0:
            percent = int((value / bar.total) * 100)
            if percent != self._last_percent:
                self._last_percent = percent
                # Always print to terminal for visibility
                print(f"\rEncoding: {percent}%", end='', flush=True)
                # Forward to GUI callback if available
                if self._progress_callback:
                    try:
                        self._progress_callback(percent / 100, f"Encoding: {percent}%")
                    except Exception as e:
                        print(f" (GUI update failed: {e})", end='')


# ═══════════════════════════════════════════════════════════════════════════
# PTO CENTRAL BRAND COLORS
# ═══════════════════════════════════════════════════════════════════════════

PTO_GOLD = '#C9A227'
PTO_GOLD_RGB = (201, 162, 39)
PTO_GRAY = '#5A6A72'
PTO_GRAY_RGB = (90, 106, 114)
HIGHLIGHT_RED = '#EF4444'
HIGHLIGHT_RED_RGB = (239, 68, 68)
HIGHLIGHT_BLUE = '#3B82F6'
HIGHLIGHT_BLUE_RGB = (59, 130, 246)
HIGHLIGHT_GREEN = '#22C55E'
HIGHLIGHT_GREEN_RGB = (34, 197, 94)


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AnnotationConfig:
    """Configuration for screenshot annotations"""
    # Highlight box
    highlight_box: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    highlight_color: Tuple[int, int, int] = PTO_GOLD_RGB
    highlight_opacity: int = 50  # 0-255
    highlight_border_width: int = 4

    # Arrow pointing to element
    arrow_from: Optional[Tuple[int, int]] = None  # (x, y) start
    arrow_to: Optional[Tuple[int, int]] = None    # (x, y) end (where it points)
    arrow_color: Tuple[int, int, int] = HIGHLIGHT_RED_RGB
    arrow_width: int = 4

    # Circle around element
    circle_center: Optional[Tuple[int, int]] = None
    circle_radius: int = 50
    circle_color: Tuple[int, int, int] = HIGHLIGHT_RED_RGB
    circle_width: int = 3

    # Text callout
    callout_text: Optional[str] = None
    callout_position: Optional[Tuple[int, int]] = None
    callout_font_size: int = 24
    callout_bg_color: Tuple[int, int, int] = (31, 41, 55)  # Dark gray
    callout_text_color: Tuple[int, int, int] = (255, 255, 255)

    # Step number badge
    step_number: Optional[int] = None
    step_badge_position: Tuple[int, int] = (30, 30)

    # Spotlight (dim everything except focus area)
    spotlight_area: Optional[Tuple[int, int, int, int]] = None
    spotlight_dim_amount: int = 150  # 0-255, how much to dim non-spotlight


@dataclass
class VideoFrame:
    """A single frame in the video production"""
    image_path: Path
    audio_path: Optional[Path] = None
    duration: float = 3.0  # seconds
    script_text: str = ""
    title: str = ""
    annotations: AnnotationConfig = field(default_factory=AnnotationConfig)

    # Director timing
    intro_pause: float = 0.5  # pause before narration starts
    outro_pause: float = 0.5  # pause after narration ends

    # Transition
    transition_type: str = "none"  # "fade", "crossfade", "none"
    transition_duration: float = 0.3


@dataclass
class VideoProject:
    """Complete video project configuration"""
    title: str
    scenario_name: str
    frames: List[VideoFrame] = field(default_factory=list)
    output_path: Optional[Path] = None

    # Video settings
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30

    # Audio settings
    background_music_path: Optional[Path] = None
    background_music_volume: float = 0.1
    narration_volume: float = 1.0

    # Intro/Outro
    intro_duration: float = 2.0
    outro_duration: float = 3.0

    # Branding
    show_logo: bool = True
    show_title_card: bool = True


# ═══════════════════════════════════════════════════════════════════════════
# SCREENSHOT ANNOTATOR
# ═══════════════════════════════════════════════════════════════════════════

class ScreenshotAnnotator:
    """Annotates screenshots with highlights, arrows, circles, and callouts"""

    def __init__(self):
        self.default_font = None
        self._load_fonts()

    def _load_fonts(self):
        """Try to load a good font for text annotations"""
        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    self.default_font = ImageFont.truetype(path, 24)
                    break
                except Exception:
                    continue

    def annotate(self, image_path: Path, config: AnnotationConfig, output_path: Optional[Path] = None) -> Path:
        """Apply annotations to a screenshot"""
        img = Image.open(image_path).convert('RGBA')

        # Create overlay for semi-transparent annotations
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        img_draw = ImageDraw.Draw(img)

        # Apply spotlight first (dims non-focus areas)
        if config.spotlight_area:
            img = self._apply_spotlight(img, config.spotlight_area, config.spotlight_dim_amount)
            img_draw = ImageDraw.Draw(img)

        # Highlight box
        if config.highlight_box:
            self._draw_highlight_box(overlay, draw, config)

        # Circle
        if config.circle_center:
            self._draw_circle(img_draw, config)

        # Arrow
        if config.arrow_from and config.arrow_to:
            self._draw_arrow(img_draw, config)

        # Step number badge
        if config.step_number:
            self._draw_step_badge(img, config)

        # Text callout
        if config.callout_text and config.callout_position:
            self._draw_callout(img, config)

        # Composite overlay onto image
        img = Image.alpha_composite(img, overlay)

        # Convert back to RGB for saving
        final_img = img.convert('RGB')

        # Save
        output = output_path or image_path.parent / f"{image_path.stem}_annotated.png"
        final_img.save(output, 'PNG', quality=95)

        return output

    def _apply_spotlight(self, img: Image.Image, area: Tuple[int, int, int, int], dim: int) -> Image.Image:
        """Dim everything except the spotlight area"""
        # Create a dark overlay
        dark_overlay = Image.new('RGBA', img.size, (0, 0, 0, dim))

        # Cut out the spotlight area (make it transparent)
        mask = Image.new('L', img.size, 255)  # White = show overlay
        mask_draw = ImageDraw.Draw(mask)

        # Make spotlight area black (transparent in mask)
        x1, y1, x2, y2 = area
        # Add padding for softer edge
        padding = 10
        mask_draw.rounded_rectangle(
            [x1 - padding, y1 - padding, x2 + padding, y2 + padding],
            radius=10,
            fill=0
        )

        # Apply blur to mask for soft edges
        mask = mask.filter(ImageFilter.GaussianBlur(radius=5))

        dark_overlay.putalpha(mask)
        return Image.alpha_composite(img, dark_overlay)

    def _draw_highlight_box(self, overlay: Image.Image, draw: ImageDraw.Draw, config: AnnotationConfig):
        """Draw semi-transparent highlight box with border"""
        x1, y1, x2, y2 = config.highlight_box

        # Semi-transparent fill
        r, g, b = config.highlight_color
        draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, config.highlight_opacity))

        # Solid border
        draw.rectangle(
            [x1, y1, x2, y2],
            outline=(r, g, b, 255),
            width=config.highlight_border_width
        )

    def _draw_circle(self, draw: ImageDraw.Draw, config: AnnotationConfig):
        """Draw a circle around an element"""
        cx, cy = config.circle_center
        r = config.circle_radius
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=config.circle_color,
            width=config.circle_width
        )

    def _draw_arrow(self, draw: ImageDraw.Draw, config: AnnotationConfig):
        """Draw an arrow from one point to another"""
        x1, y1 = config.arrow_from
        x2, y2 = config.arrow_to

        # Main line
        draw.line([x1, y1, x2, y2], fill=config.arrow_color, width=config.arrow_width)

        # Arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = 20
        arrow_angle = math.pi / 6  # 30 degrees

        # Calculate arrowhead points
        left_x = x2 - arrow_length * math.cos(angle - arrow_angle)
        left_y = y2 - arrow_length * math.sin(angle - arrow_angle)
        right_x = x2 - arrow_length * math.cos(angle + arrow_angle)
        right_y = y2 - arrow_length * math.sin(angle + arrow_angle)

        # Draw arrowhead
        draw.polygon(
            [(x2, y2), (left_x, left_y), (right_x, right_y)],
            fill=config.arrow_color
        )

    def _draw_step_badge(self, img: Image.Image, config: AnnotationConfig):
        """Draw a step number badge"""
        draw = ImageDraw.Draw(img)
        x, y = config.step_badge_position

        # Badge background
        badge_size = 50
        draw.ellipse(
            [x, y, x + badge_size, y + badge_size],
            fill=PTO_GOLD_RGB,
            outline=(255, 255, 255),
            width=2
        )

        # Step number
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 28)
        except Exception:
            font = self.default_font or ImageFont.load_default()

        text = str(config.step_number)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = x + (badge_size - text_width) // 2
        text_y = y + (badge_size - text_height) // 2 - 2

        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    def _draw_callout(self, img: Image.Image, config: AnnotationConfig):
        """Draw a text callout box"""
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", config.callout_font_size)
        except Exception:
            font = self.default_font or ImageFont.load_default()

        text = config.callout_text
        x, y = config.callout_position

        # Calculate text bounds
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Background rectangle with padding
        padding = 12
        bg_rect = [
            x - padding,
            y - padding,
            x + text_width + padding,
            y + text_height + padding
        ]

        # Draw background with TJM gold border
        draw.rounded_rectangle(bg_rect, radius=8, fill=config.callout_bg_color)
        draw.rounded_rectangle(bg_rect, radius=8, outline=PTO_GOLD_RGB, width=2)

        # Draw text
        draw.text((x, y), text, fill=config.callout_text_color, font=font)


# ═══════════════════════════════════════════════════════════════════════════
# ELEMENT HIGHLIGHTER (for Playwright injection)
# ═══════════════════════════════════════════════════════════════════════════

class ElementHighlighter:
    """
    Provides CSS/JS injection code for Playwright to highlight elements
    before taking screenshots. This creates focused, professional screenshots.
    """

    @staticmethod
    def get_highlight_script(selector: str, style: str = "default") -> str:
        """
        Generate JavaScript to inject CSS highlighting on an element.

        Args:
            selector: CSS selector for the element to highlight
            style: "default", "pulse", "spotlight", "arrow"

        Returns:
            JavaScript code to execute via page.evaluate()
        """
        styles = {
            "default": f"""
                element.style.outline = '4px solid {PTO_GOLD}';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(201, 162, 39, 0.5)';
                element.style.transition = 'all 0.3s ease';
            """,
            "pulse": f"""
                element.style.animation = 'tjm-pulse 1.5s infinite';
                element.style.outline = '3px solid {PTO_GOLD}';
                element.style.outlineOffset = '2px';

                // Add keyframes
                if (!document.getElementById('tjm-pulse-style')) {{
                    const style = document.createElement('style');
                    style.id = 'tjm-pulse-style';
                    style.textContent = `
                        @keyframes tjm-pulse {{
                            0% {{ box-shadow: 0 0 0 0 rgba(201, 162, 39, 0.7); }}
                            70% {{ box-shadow: 0 0 0 15px rgba(201, 162, 39, 0); }}
                            100% {{ box-shadow: 0 0 0 0 rgba(201, 162, 39, 0); }}
                        }}
                    `;
                    document.head.appendChild(style);
                }}
            """,
            "spotlight": """
                // Dim the page
                if (!document.getElementById('tjm-spotlight-overlay')) {
                    const overlay = document.createElement('div');
                    overlay.id = 'tjm-spotlight-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.7);
                        z-index: 9998;
                        pointer-events: none;
                    `;
                    document.body.appendChild(overlay);
                }

                // Bring element to front
                element.style.position = 'relative';
                element.style.zIndex = '9999';
                element.style.boxShadow = '0 0 0 4px #C9A227, 0 0 30px rgba(201, 162, 39, 0.8)';
            """,
            "error": f"""
                element.style.outline = '4px solid {HIGHLIGHT_RED}';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.5)';
            """,
            "success": f"""
                element.style.outline = '4px solid {HIGHLIGHT_GREEN}';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(34, 197, 94, 0.5)';
            """
        }

        style_code = styles.get(style, styles["default"])

        return f"""
            (function() {{
                const element = document.querySelector('{selector}');
                if (element) {{
                    {style_code}

                    // Scroll element into view
                    element.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                }}
            }})();
        """

    @staticmethod
    def get_cleanup_script() -> str:
        """Generate JavaScript to remove all highlight effects"""
        return """
            (function() {
                // Remove spotlight overlay
                const overlay = document.getElementById('tjm-spotlight-overlay');
                if (overlay) overlay.remove();

                // Remove pulse animation style
                const pulseStyle = document.getElementById('tjm-pulse-style');
                if (pulseStyle) pulseStyle.remove();

                // Reset all highlighted elements
                document.querySelectorAll('[style*="outline"]').forEach(el => {
                    el.style.outline = '';
                    el.style.outlineOffset = '';
                    el.style.boxShadow = '';
                    el.style.animation = '';
                    el.style.zIndex = '';
                });
            })();
        """

    @staticmethod
    def get_callout_script(text: str, position: str = "top-right") -> str:
        """
        Add a floating callout/tooltip to the page.

        Args:
            text: The callout text
            position: "top-left", "top-right", "bottom-left", "bottom-right"
        """
        positions = {
            "top-left": "top: 20px; left: 20px;",
            "top-right": "top: 20px; right: 20px;",
            "bottom-left": "bottom: 20px; left: 20px;",
            "bottom-right": "bottom: 20px; right: 20px;",
        }
        pos_style = positions.get(position, positions["top-right"])

        return f"""
            (function() {{
                // Remove existing callout
                const existing = document.getElementById('tjm-callout');
                if (existing) existing.remove();

                const callout = document.createElement('div');
                callout.id = 'tjm-callout';
                callout.textContent = '{text}';
                callout.style.cssText = `
                    position: fixed;
                    {pos_style}
                    background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
                    color: white;
                    padding: 16px 24px;
                    border-radius: 12px;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    font-size: 18px;
                    font-weight: 500;
                    z-index: 10000;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    border: 2px solid #C9A227;
                    max-width: 400px;
                    animation: fadeIn 0.3s ease;
                `;

                // Add animation
                if (!document.getElementById('tjm-callout-style')) {{
                    const style = document.createElement('style');
                    style.id = 'tjm-callout-style';
                    style.textContent = `
                        @keyframes fadeIn {{
                            from {{ opacity: 0; transform: translateY(-10px); }}
                            to {{ opacity: 1; transform: translateY(0); }}
                        }}
                    `;
                    document.head.appendChild(style);
                }}

                document.body.appendChild(callout);
            }})();
        """


# ═══════════════════════════════════════════════════════════════════════════
# VIDEO PRODUCER
# ═══════════════════════════════════════════════════════════════════════════

class VideoProducer:
    """
    Creates professional training videos from screenshots and audio narration.
    Uses MoviePy for video compilation with proper audio synchronization.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.annotator = ScreenshotAnnotator()

        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy is required for video production. Install with: pip install moviepy")

    def create_video(self, project: VideoProject) -> Path:
        """
        Create a complete training video from a project configuration.

        This is the main production pipeline:
        1. Annotate screenshots
        2. Create title card (if enabled)
        3. Compile frames with timing
        4. Sync audio narration
        5. Add transitions
        6. Export final video
        """
        print(f"\n{'='*60}")
        print(f"VIDEO PRODUCTION: {project.title}")
        print(f"{'='*60}\n")

        video_clips = []

        # 1. Create title card
        if project.show_title_card:
            print("Creating title card...")
            title_clip = self._create_title_card(project)
            video_clips.append(title_clip)

        # 2. Process each frame
        for i, frame in enumerate(project.frames):
            print(f"Processing frame {i+1}/{len(project.frames)}: {frame.title}")

            # Annotate screenshot if needed
            if self._has_annotations(frame.annotations):
                annotated_path = self.annotator.annotate(
                    frame.image_path,
                    frame.annotations,
                    self.output_dir / f"frame_{i:03d}_annotated.png"
                )
            else:
                annotated_path = frame.image_path

            # Calculate frame duration based on audio or config
            duration = frame.duration
            if frame.audio_path and frame.audio_path.exists():
                audio_clip = AudioFileClip(str(frame.audio_path))
                # Duration = intro pause + audio + outro pause
                duration = frame.intro_pause + audio_clip.duration + frame.outro_pause
                audio_clip.close()

            # Create image clip
            img_clip = ImageClip(str(annotated_path)).with_duration(duration)

            # Resize to project resolution if needed
            if img_clip.size != project.resolution:
                img_clip = img_clip.resized(project.resolution)

            # Add audio if available
            if frame.audio_path and frame.audio_path.exists():
                audio = AudioFileClip(str(frame.audio_path))
                # Offset audio by intro pause
                if frame.intro_pause > 0:
                    audio = audio.with_start(frame.intro_pause)
                img_clip = img_clip.with_audio(audio)

            video_clips.append(img_clip)
            print(f"  Duration: {duration:.1f}s")

        # 3. Create outro card
        if project.outro_duration > 0:
            print("Creating outro card...")
            outro_clip = self._create_outro_card(project)
            video_clips.append(outro_clip)

        # 4. Concatenate all clips
        print("\nCompiling video...")
        final_video = concatenate_videoclips(video_clips, method="compose")

        # 5. Export
        output_path = project.output_path or (self.output_dir / f"{project.scenario_name}_training.mp4")
        print(f"Exporting to: {output_path}")

        final_video.write_videofile(
            str(output_path),
            fps=project.fps,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='medium',
            bitrate='5000k'
        )

        # Cleanup
        final_video.close()
        for clip in video_clips:
            clip.close()

        print(f"\nVideo production complete!")
        print(f"Output: {output_path}")
        print(f"Duration: {final_video.duration:.1f}s")

        return output_path

    def _has_annotations(self, config: AnnotationConfig) -> bool:
        """Check if any annotations are configured"""
        return any([
            config.highlight_box,
            config.arrow_from,
            config.circle_center,
            config.callout_text,
            config.step_number,
            config.spotlight_area
        ])

    def _create_title_card(self, project: VideoProject) -> ImageClip:
        """Create a professional title card"""
        width, height = project.resolution

        # Create dark background
        img = Image.new('RGB', (width, height), (31, 41, 55))
        draw = ImageDraw.Draw(img)

        # TJM gold accent line
        draw.rectangle([0, height//2 - 100, width, height//2 - 96], fill=PTO_GOLD_RGB)

        # Title
        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 72)
            subtitle_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 36)
        except Exception:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # Draw title centered
        title_bbox = draw.textbbox((0, 0), project.title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, height//2 - 60), project.title, fill=(255, 255, 255), font=title_font)

        # Draw subtitle
        subtitle = "PTO Central Training"
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (width - sub_width) // 2
        draw.text((sub_x, height//2 + 40), subtitle, fill=PTO_GOLD_RGB, font=subtitle_font)

        # Save temp file
        temp_path = self.output_dir / "_title_card.png"
        img.save(temp_path)

        return ImageClip(str(temp_path)).with_duration(project.intro_duration)

    def _create_outro_card(self, project: VideoProject) -> ImageClip:
        """Create an outro card"""
        width, height = project.resolution

        # Create dark background
        img = Image.new('RGB', (width, height), (31, 41, 55))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 48)
            small_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Main text
        text = "Training Complete"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width)//2, height//2 - 40), text, fill=PTO_GOLD_RGB, font=font)

        # Subtitle
        subtitle = "PTO Central"
        sub_bbox = draw.textbbox((0, 0), subtitle, font=small_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        draw.text(((width - sub_width)//2, height//2 + 30), subtitle, fill=(150, 150, 150), font=small_font)

        temp_path = self.output_dir / "_outro_card.png"
        img.save(temp_path)

        return ImageClip(str(temp_path)).with_duration(project.outro_duration)

    def create_video_from_scenario_outputs(
        self,
        scenario_name: str,
        screenshots_dir: Path,
        audio_dir: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Convenience method to create video from existing scenario outputs.
        Automatically pairs screenshots with audio files by naming convention.
        """
        # Find all screenshots
        screenshots = sorted(screenshots_dir.glob("*.png"))
        if not screenshots:
            raise ValueError(f"No screenshots found in {screenshots_dir}")

        # Find all audio files
        audio_files = sorted(audio_dir.glob("*.mp3")) if audio_dir.exists() else []
        audio_map = {a.stem: a for a in audio_files}

        # Build frames
        frames = []
        for i, screenshot in enumerate(screenshots):
            # Try to find matching audio
            audio_path = audio_map.get(screenshot.stem)

            # Extract step info from filename (e.g., "step-01-login.png")
            title = screenshot.stem.replace('-', ' ').replace('_', ' ').title()

            frame = VideoFrame(
                image_path=screenshot,
                audio_path=audio_path,
                duration=4.0 if not audio_path else 0,  # Auto-calculate if audio exists
                title=title,
                annotations=AnnotationConfig(step_number=i + 1)
            )
            frames.append(frame)

        # Create project
        project = VideoProject(
            title=scenario_name.replace('-', ' ').title(),
            scenario_name=scenario_name,
            frames=frames,
            output_path=output_path
        )

        return self.create_video(project)

    def create_video_from_timeline(
        self,
        timeline_path: Path,
        audio_dir: Path,
        output_path: Optional[Path] = None,
        include_intro: bool = True,
        include_outro: bool = True,
        video_effect: VideoEffect = VideoEffect.NONE,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """
        Create training video by overlaying audio on the raw Playwright recording.

        This produces better results because:
        - Uses actual screen recording showing real interactions
        - Audio is synced to exact timestamps when actions occurred
        - Viewer sees what's happening as they hear the narration

        Args:
            timeline_path: Path to the timeline JSON file
            audio_dir: Directory containing audio files
            output_path: Where to save the final video
            include_intro: Add title card at beginning
            include_outro: Add outro card at end
            video_effect: Video effect to apply (zoom, highlight, hybrid, none)
            progress_callback: Callback function(progress: 0-1, status: str) for encoding progress
        """
        import json

        print(f"\n{'='*60}")
        print("VIDEO PRODUCTION: Timeline-Based Audio Overlay")
        print(f"{'='*60}\n")

        # Load timeline
        timeline = json.loads(timeline_path.read_text())
        scenario_name = timeline['scenario_id']
        video_file = Path(timeline['video_file'])

        if not video_file.exists():
            raise FileNotFoundError(f"Raw video not found: {video_file}")

        print(f"Source video: {video_file.name}")
        print(f"Duration: {timeline['total_duration']:.1f}s")
        print(f"Steps: {len(timeline['steps'])}")

        # Load the raw Playwright recording
        video_clip = VideoFileClip(str(video_file))
        print(f"Video loaded: {video_clip.duration:.1f}s")
        print(f"Video effect: {video_effect.value}")

        if progress_callback:
            progress_callback(0.05, "Loading video...")

        # Apply video effects based on selection
        if video_effect in (VideoEffect.ZOOM, VideoEffect.HYBRID):
            print("Applying Ken Burns zoom effect...")
            if progress_callback:
                progress_callback(0.10, "Applying zoom effect...")
            video_clip = self._apply_ken_burns_effect(video_clip, timeline)

        # Build list of audio clips with SEQUENTIAL timing (no overlap)
        # Each audio starts after the previous one ends
        audio_clips = []
        current_audio_time = 0.0  # Track when next audio should start

        for step in timeline['steps']:
            step_num = step['step_number']
            action_timestamp = step['timestamp_start']

            # Find the audio file
            audio_file = audio_dir / f"step-{step_num:02d}-{step['step_id']}.mp3"
            if not audio_file.exists():
                audio_file = audio_dir / f"step-{step_num:02d}.mp3"

            if audio_file.exists():
                audio = AudioFileClip(str(audio_file))

                # Start audio at the later of: action timestamp OR after previous audio ends
                # This prevents overlap while trying to stay close to the action
                start_time = max(action_timestamp, current_audio_time)
                audio = audio.with_start(start_time)
                audio_clips.append(audio)

                print(f"  Step {step_num}: audio at {start_time:.1f}s (action was {action_timestamp:.1f}s, dur: {audio.duration:.1f}s)")
                current_audio_time = start_time + audio.duration
            else:
                print(f"  Step {step_num}: NO AUDIO FOUND")

        total_audio_duration = current_audio_time
        print(f"\nTotal audio duration: {total_audio_duration:.1f}s")
        print(f"Video duration: {video_clip.duration:.1f}s")

        # If audio is longer than video, extend the video by freezing the last frame
        if total_audio_duration > video_clip.duration:
            extension_needed = total_audio_duration - video_clip.duration + 1.0  # +1s buffer
            print(f"Extending video by {extension_needed:.1f}s (freezing last frame)")

            # Create a frozen frame from the last moment of the video
            last_frame = video_clip.to_ImageClip(t=video_clip.duration - 0.1)
            last_frame = last_frame.with_duration(extension_needed)

            # Concatenate original video with frozen frame
            video_clip = concatenate_videoclips([video_clip, last_frame])

        # Apply highlight effect if requested (adds gold boxes on action areas)
        if video_effect in (VideoEffect.HIGHLIGHT, VideoEffect.HYBRID):
            print("Applying highlight box effect...")
            if progress_callback:
                progress_callback(0.20, "Applying highlight effect...")
            video_clip = self._apply_highlight_effect(video_clip, timeline)

        if progress_callback:
            progress_callback(0.25, "Combining audio...")

        # Combine all audio clips into a composite
        if audio_clips:
            composite_audio = CompositeAudioClip(audio_clips)
            video_with_audio = video_clip.with_audio(composite_audio)
        else:
            video_with_audio = video_clip
            print("WARNING: No audio clips found!")

        # Prepare final clips list
        final_clips = []

        # Add intro title card
        if include_intro:
            print("Creating intro card...")
            if progress_callback:
                progress_callback(0.30, "Creating intro card...")
            intro_clip = self._create_title_card_simple(
                title=timeline['scenario_name'],
                description=timeline.get('scenario_description', ''),  # Include description if available
                duration=5.0  # 5 seconds for title card
            )
            final_clips.append(intro_clip)

        # Add main video with audio
        final_clips.append(video_with_audio)

        # Add outro card
        if include_outro:
            print("Creating outro card...")
            outro_clip = self._create_outro_card_simple(duration=5.0)  # 5 seconds for outro
            final_clips.append(outro_clip)

        # Concatenate all clips
        print("\nCompiling final video...")
        if progress_callback:
            progress_callback(0.35, "Compiling video...")
        final_video = concatenate_videoclips(final_clips, method="compose")

        # Determine output path
        if output_path is None:
            output_path = self.output_dir / f"{scenario_name}_training.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting to: {output_path}")
        if progress_callback:
            progress_callback(0.40, "Encoding video (this takes a minute)...")

        # Create progress logger for moviepy
        def moviepy_progress_logger(info):
            """Parse moviepy progress and call our callback"""
            if progress_callback and 't' in info:
                # info contains 't' (current time) and we know total duration
                current = info['t']
                total = final_video.duration
                # Map 0.40 to 0.95 for encoding phase
                encoding_progress = 0.40 + (current / total) * 0.55
                progress_callback(min(encoding_progress, 0.95), f"Encoding: {current:.0f}s / {total:.0f}s")

        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='medium',
            bitrate='5000k',
            logger='bar' if not progress_callback else None
        )

        if progress_callback:
            progress_callback(1.0, "Complete!")

        # Cleanup
        final_video.close()
        video_clip.close()
        for clip in audio_clips:
            clip.close()

        print(f"\nVideo production complete!")
        print(f"Output: {output_path}")

        return output_path

    def _apply_ken_burns_effect(self, clip, timeline: dict):
        """
        Apply Ken Burns (slow zoom) effect to video.
        Zooms towards the element being interacted with at each step.
        Uses element_bbox from timeline for targeted zoom.
        """
        duration = clip.duration
        steps = timeline.get('steps', [])
        video_width, video_height = clip.size  # (width, height)

        # Build zoom targets from timeline with element coordinates
        zoom_targets = []
        for step in steps:
            start = step.get('timestamp_start', 0)
            end = step.get('timestamp_end', start + 2.0)
            bbox = step.get('element_bbox')

            if bbox and bbox.get('x') is not None:
                # Calculate center of element as zoom target (normalized 0-1)
                target_x = (bbox['x'] + bbox['width'] / 2) / video_width
                target_y = (bbox['y'] + bbox['height'] / 2) / video_height
                # Clamp to valid range to avoid edge issues
                target_x = max(0.25, min(0.75, target_x))
                target_y = max(0.25, min(0.75, target_y))
                zoom_targets.append((start, end, target_x, target_y, bbox))
            else:
                zoom_targets.append((start, end, 0.5, 0.5, None))

        # Cache for interpolation
        last_target = (0.5, 0.5)

        def zoom_effect(get_frame, t):
            """Apply smooth targeted zoom effect"""
            nonlocal last_target
            frame = get_frame(t)
            h, w = frame.shape[:2]

            # Find current target based on time with smooth transition
            target_x, target_y = last_target
            for start, end, tx, ty, _ in zoom_targets:
                if start <= t <= end + 0.5:
                    # Smooth interpolation towards target
                    blend = min(1.0, (t - start) / 0.5) if t >= start else 0
                    target_x = last_target[0] + (tx - last_target[0]) * blend
                    target_y = last_target[1] + (ty - last_target[1]) * blend
                    if blend >= 1.0:
                        last_target = (tx, ty)
                    break

            # Gentle zoom factor (1.0 to 1.08 - subtle)
            progress = t / duration
            zoom_factor = 1.0 + (0.08 * progress)

            # Calculate crop dimensions
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)

            # Calculate crop position centered on target
            center_x = int(target_x * w)
            center_y = int(target_y * h)

            x1 = center_x - new_w // 2
            y1 = center_y - new_h // 2

            # Clamp to bounds
            x1 = max(0, min(w - new_w, x1))
            y1 = max(0, min(h - new_h, y1))

            # Crop and resize
            cropped = frame[y1:y1+new_h, x1:x1+new_w]

            from PIL import Image
            import numpy as np
            pil_img = Image.fromarray(cropped)
            pil_img = pil_img.resize((w, h), Image.Resampling.LANCZOS)
            return np.array(pil_img)

        return clip.transform(zoom_effect)

    def _apply_highlight_effect(self, clip, timeline: dict):
        """
        Apply gold highlight box effect around the element being interacted with.
        Uses element_bbox from timeline for targeted highlighting.
        """
        steps = timeline.get('steps', [])
        if not steps:
            return clip

        # Build list of (start_time, end_time, bbox) for action windows
        action_windows = []
        for step in steps:
            start = step.get('timestamp_start', 0)
            end = step.get('timestamp_end', start + 2.0)
            bbox = step.get('element_bbox')
            action_windows.append((start, end, bbox))

        def highlight_frame(get_frame, t):
            """Apply highlight box around the active element"""
            frame = get_frame(t)

            # Check if we're in an action window
            active_bbox = None
            intensity = 0
            for start, end, bbox in action_windows:
                if start <= t <= end + 0.3:  # Extend slightly past end
                    # Calculate intensity based on position in window
                    window_duration = end - start if end > start else 1.0
                    window_progress = (t - start) / window_duration
                    # Fade in/out effect
                    if window_progress < 0.15:
                        intensity = window_progress / 0.15
                    elif window_progress > 0.85:
                        intensity = max(0, (1.0 - window_progress) / 0.15)
                    else:
                        intensity = 1.0
                    active_bbox = bbox
                    break

            if not active_bbox or intensity <= 0:
                return frame

            # Apply gold highlight box around the element
            from PIL import Image, ImageDraw
            import numpy as np

            pil_img = Image.fromarray(frame)
            overlay = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # Get element coordinates with padding
            padding = 8
            x1 = int(active_bbox['x']) - padding
            y1 = int(active_bbox['y']) - padding
            x2 = int(active_bbox['x'] + active_bbox['width']) + padding
            y2 = int(active_bbox['y'] + active_bbox['height']) + padding

            # Clamp to image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(pil_img.width, x2)
            y2 = min(pil_img.height, y2)

            # Gold highlight color with intensity-based alpha
            border_width = 4
            glow_alpha = int(220 * intensity)
            gold_color = (201, 162, 39, glow_alpha)

            # Draw rounded rectangle border around the element
            # Outer glow (thicker, more transparent)
            for i in range(3):
                offset = i * 2
                outer_alpha = int(glow_alpha * (0.3 - i * 0.1))
                draw.rectangle(
                    [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                    outline=(201, 162, 39, outer_alpha),
                    width=2
                )

            # Main border (gold box)
            draw.rectangle(
                [x1, y1, x2, y2],
                outline=gold_color,
                width=border_width
            )

            # Corner accents (small squares at corners)
            corner_size = 12
            corner_color = (201, 162, 39, glow_alpha)
            # Top-left
            draw.rectangle([x1, y1, x1 + corner_size, y1 + border_width], fill=corner_color)
            draw.rectangle([x1, y1, x1 + border_width, y1 + corner_size], fill=corner_color)
            # Top-right
            draw.rectangle([x2 - corner_size, y1, x2, y1 + border_width], fill=corner_color)
            draw.rectangle([x2 - border_width, y1, x2, y1 + corner_size], fill=corner_color)
            # Bottom-left
            draw.rectangle([x1, y2 - border_width, x1 + corner_size, y2], fill=corner_color)
            draw.rectangle([x1, y2 - corner_size, x1 + border_width, y2], fill=corner_color)
            # Bottom-right
            draw.rectangle([x2 - corner_size, y2 - border_width, x2, y2], fill=corner_color)
            draw.rectangle([x2 - border_width, y2 - corner_size, x2, y2], fill=corner_color)

            # Composite
            pil_img = pil_img.convert('RGBA')
            result = Image.alpha_composite(pil_img, overlay)
            return np.array(result.convert('RGB'))

        return clip.transform(highlight_frame)

    def _create_title_card_simple(self, title: str, description: str = "", duration: float = 5.0) -> ImageClip:
        """Create a professional title card with PTO Central logo"""
        width, height = 1280, 1067  # Match 1920x1600 aspect ratio (1.2:1)

        img = Image.new('RGB', (width, height), (31, 41, 55))
        draw = ImageDraw.Draw(img)

        # Load and place PTO Central logo at top center
        try:
            from pathlib import Path
            logo_path = Path(__file__).parent.parent / 'nicegui_app' / 'static' / 'PTOCentralLogo.png'
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                # Resize logo to fit nicely (target height ~120px)
                logo_aspect = logo_img.width / logo_img.height
                logo_height = 120
                logo_width = int(logo_height * logo_aspect)
                logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                # Convert RGBA to RGB if needed
                if logo_img.mode == 'RGBA':
                    logo_bg = Image.new('RGB', logo_img.size, (31, 41, 55))
                    logo_bg.paste(logo_img, mask=logo_img.split()[3])
                    logo_img = logo_bg
                # Center logo at top
                logo_x = (width - logo_width) // 2
                logo_y = 60  # 60px from top
                img.paste(logo_img, (logo_x, logo_y))
        except Exception as e:
            print(f"Could not load logo: {e}")

        # Gold accent line below logo
        draw.rectangle([0, height//2 - 100, width, height//2 - 96], fill=PTO_GOLD_RGB)

        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 48)
            desc_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
            subtitle_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24)
        except Exception:
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # Draw title centered (below the gold line)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, height//2 - 60), title, fill=(255, 255, 255), font=title_font)

        # Draw description (if provided)
        if description:
            desc_bbox = draw.textbbox((0, 0), description, font=desc_font)
            desc_width = desc_bbox[2] - desc_bbox[0]
            desc_x = (width - desc_width) // 2
            draw.text((desc_x, height//2 + 10), description, fill=(156, 163, 175), font=desc_font)  # Gray text

        # Draw subtitle
        subtitle = "PTO Central Training"
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_x = (width - sub_width) // 2
        draw.text((sub_x, height//2 + 60), subtitle, fill=PTO_GOLD_RGB, font=subtitle_font)

        temp_path = self.output_dir / "_intro_card.png"
        img.save(temp_path)

        return ImageClip(str(temp_path)).with_duration(duration)

    def _create_outro_card_simple(self, duration: float = 5.0) -> ImageClip:
        """Create a professional outro card with PTO Central logo"""
        width, height = 1280, 1067  # Match 1920x1600 aspect ratio (1.2:1)

        img = Image.new('RGB', (width, height), (31, 41, 55))
        draw = ImageDraw.Draw(img)

        # Load and place PTO Central logo at top center
        try:
            from pathlib import Path
            logo_path = Path(__file__).parent.parent / 'nicegui_app' / 'static' / 'PTOCentralLogo.png'
            if logo_path.exists():
                logo_img = Image.open(logo_path)
                # Resize logo to fit nicely (target height ~100px for outro)
                logo_aspect = logo_img.width / logo_img.height
                logo_height = 100
                logo_width = int(logo_height * logo_aspect)
                logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                # Convert RGBA to RGB if needed
                if logo_img.mode == 'RGBA':
                    logo_bg = Image.new('RGB', logo_img.size, (31, 41, 55))
                    logo_bg.paste(logo_img, mask=logo_img.split()[3])
                    logo_img = logo_bg
                # Center logo at top
                logo_x = (width - logo_width) // 2
                logo_y = 80
                img.paste(logo_img, (logo_x, logo_y))
        except Exception as e:
            print(f"Could not load logo: {e}")

        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
            small_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18)
        except Exception:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        text = "Training Complete"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width)//2, height//2 + 20), text, fill=PTO_GOLD_RGB, font=font)

        subtitle = "PTO Central"
        sub_bbox = draw.textbbox((0, 0), subtitle, font=small_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        draw.text(((width - sub_width)//2, height//2 + 70), subtitle, fill=(150, 150, 150), font=small_font)

        temp_path = self.output_dir / "_outro_card.png"
        img.save(temp_path)

        return ImageClip(str(temp_path)).with_duration(duration)

    def _draw_cursor_overlay(
        self,
        canvas: Image.Image,
        element_bbox: Dict[str, float],
        original_width: int,
        original_height: int,
        paste_x: int,
        paste_y: int,
        new_width: int,
        new_height: int
    ) -> Image.Image:
        """
        Draw a gold cursor overlay at the center of element_bbox.

        Handles coordinate scaling from original screenshot size to resized/positioned canvas.

        Args:
            canvas: The PIL Image canvas to draw on
            element_bbox: Dict with x, y, width, height from timeline
            original_width: Original screenshot width (usually 1920)
            original_height: Original screenshot height (usually 1080)
            paste_x: X offset where screenshot was pasted on canvas
            paste_y: Y offset where screenshot was pasted on canvas
            new_width: Width of resized screenshot
            new_height: Height of resized screenshot
        """
        if not element_bbox or element_bbox.get('x') is None:
            return canvas

        # Calculate scale factors from original to resized
        scale_x = new_width / original_width
        scale_y = new_height / original_height

        # Calculate center of element in original coordinates
        orig_center_x = element_bbox['x'] + element_bbox['width'] / 2
        orig_center_y = element_bbox['y'] + element_bbox['height'] / 2

        # Scale to resized coordinates and add paste offset
        cursor_x = int(orig_center_x * scale_x) + paste_x
        cursor_y = int(orig_center_y * scale_y) + paste_y

        # Draw cursor (gold circle with glow effect)
        draw = ImageDraw.Draw(canvas, 'RGBA')

        # Cursor size (scaled proportionally)
        cursor_radius = 15
        glow_radius = 25

        # Draw outer glow (semi-transparent gold)
        for r in range(glow_radius, cursor_radius, -2):
            alpha = int(100 * (glow_radius - r) / (glow_radius - cursor_radius))
            draw.ellipse(
                [cursor_x - r, cursor_y - r, cursor_x + r, cursor_y + r],
                fill=(201, 162, 39, alpha)
            )

        # Draw main cursor circle (solid gold with white border)
        draw.ellipse(
            [cursor_x - cursor_radius, cursor_y - cursor_radius,
             cursor_x + cursor_radius, cursor_y + cursor_radius],
            fill=(201, 162, 39, 240),
            outline=(255, 255, 255, 255),
            width=3
        )

        return canvas

    def create_slideshow_from_timeline(
        self,
        timeline_path: Path,
        audio_dir: Path,
        output_path: Optional[Path] = None,
        include_intro: bool = True,
        include_outro: bool = True,
        transition_duration: float = 0.5,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """
        Create training video using static screenshots with crossfade transitions.

        This produces smooth, professional results without flickering because:
        - Uses static screenshots instead of video recording
        - Each slide remains perfectly still during narration
        - Professional crossfade transitions between slides
        - Smaller file sizes than video recording

        Args:
            timeline_path: Path to the timeline JSON file
            audio_dir: Directory containing audio files
            output_path: Where to save the final video
            include_intro: Add title card at beginning
            include_outro: Add outro card at end
            transition_duration: Duration of crossfade between slides (seconds)
            progress_callback: Callback function(progress: 0-1, status: str)
        """
        import json

        print(f"\n{'='*60}")
        print("SLIDESHOW PRODUCTION: Screenshot-Based Training Video")
        print(f"{'='*60}\n")

        # Load timeline
        timeline = json.loads(timeline_path.read_text())
        scenario_name = timeline['scenario_id']

        print(f"Scenario: {scenario_name}")
        print(f"Steps: {len(timeline['steps'])}")
        print(f"Transition: {transition_duration}s crossfade")

        if progress_callback:
            progress_callback(0.05, "Loading timeline...")

        # Output at 1280x1067 (matches 1920x1600 aspect ratio of 1.2:1)
        # This avoids letterboxing while keeping reasonable file size
        target_width, target_height = 1280, 1067

        # Build list of slide clips with audio
        slide_clips = []

        for i, step in enumerate(timeline['steps']):
            step_num = step['step_number']
            # Handle both 'screenshot' and 'screenshot_path' keys for compatibility
            screenshot_key = step.get('screenshot') or step.get('screenshot_path')
            if not screenshot_key:
                print(f"  Step {step_num}: No screenshot path in timeline")
                continue
            screenshot_path = Path(screenshot_key)

            if not screenshot_path.exists():
                print(f"  Step {step_num}: Screenshot not found: {screenshot_path}")
                continue

            # Find matching audio file
            audio_file = audio_dir / f"step-{step_num:02d}-{step['step_id']}.mp3"
            if not audio_file.exists():
                audio_file = audio_dir / f"step-{step_num:02d}.mp3"

            # Determine slide duration from audio or fallback
            if audio_file.exists():
                audio_clip = AudioFileClip(str(audio_file))
                # Duration = audio + small padding for comfortable viewing
                slide_duration = audio_clip.duration + 0.5
                print(f"  Step {step_num}: {step['title']} ({slide_duration:.1f}s)")
            else:
                # No audio - use timeline duration or default
                slide_duration = step.get('duration', 3.0)
                audio_clip = None
                print(f"  Step {step_num}: {step['title']} ({slide_duration:.1f}s) - NO AUDIO")

            # Load and resize screenshot to target resolution
            screenshot_img = Image.open(screenshot_path)

            # Scale to fit 1920x1080 (letterbox if aspect ratio differs)
            img_aspect = screenshot_img.width / screenshot_img.height
            target_aspect = target_width / target_height

            if img_aspect > target_aspect:
                # Image is wider - fit to width, add vertical bars
                new_width = target_width
                new_height = int(target_width / img_aspect)
            else:
                # Image is taller - fit to height, add horizontal bars
                new_height = target_height
                new_width = int(target_height * img_aspect)

            # Store original dimensions before resize for coordinate scaling
            original_width = screenshot_img.width
            original_height = screenshot_img.height

            screenshot_img = screenshot_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Create canvas and paste centered
            canvas = Image.new('RGBA', (target_width, target_height), (31, 41, 55, 255))
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2
            canvas.paste(screenshot_img, (paste_x, paste_y))

            # Draw cursor overlay at element_bbox position (syncs cursor with narration topic)
            element_bbox = step.get('element_bbox')
            if element_bbox:
                canvas = self._draw_cursor_overlay(
                    canvas=canvas,
                    element_bbox=element_bbox,
                    original_width=original_width,
                    original_height=original_height,
                    paste_x=paste_x,
                    paste_y=paste_y,
                    new_width=new_width,
                    new_height=new_height
                )
                print(f"    → Cursor positioned at element ({element_bbox['x']:.0f}, {element_bbox['y']:.0f})")

            # Convert RGBA to RGB for video encoding
            canvas = canvas.convert('RGB')

            # Save processed slide
            slide_path = self.output_dir / f"_slide_{step_num:02d}.png"
            canvas.save(slide_path)

            # Create image clip
            slide_clip = ImageClip(str(slide_path)).with_duration(slide_duration)

            # Add audio if available
            if audio_clip:
                # Start audio slightly after slide appears for natural feel
                audio_with_delay = audio_clip.with_start(0.25)
                slide_clip = slide_clip.with_audio(audio_with_delay)

            slide_clips.append(slide_clip)

            if progress_callback:
                progress_callback(0.05 + (0.30 * (i + 1) / len(timeline['steps'])), f"Processing slide {step_num}...")

        if not slide_clips:
            raise ValueError("No slides could be created from timeline")

        print(f"\nCreated {len(slide_clips)} slides")

        # Apply crossfade transitions between slides
        if transition_duration > 0 and len(slide_clips) > 1:
            print(f"Applying {transition_duration}s crossfade transitions...")
            if progress_callback:
                progress_callback(0.40, "Adding transitions...")

            # Use CompositeVideoClip for overlapping transitions with crossfade
            from moviepy import CompositeVideoClip
            from moviepy.video.fx import CrossFadeIn, CrossFadeOut

            # Calculate proper start times with overlap
            current_time = 0
            clips_positioned = []

            for i, clip in enumerate(slide_clips):
                if i == 0:
                    # First clip starts at 0, with fade out at end
                    clip_with_fx = clip.with_effects([CrossFadeOut(transition_duration)])
                    clips_positioned.append(clip_with_fx.with_start(0))
                    current_time = clip.duration - transition_duration
                elif i == len(slide_clips) - 1:
                    # Last clip - fade in only
                    clip_with_fx = clip.with_effects([CrossFadeIn(transition_duration)])
                    clips_positioned.append(clip_with_fx.with_start(current_time))
                    current_time += clip.duration - transition_duration
                else:
                    # Middle clips - fade in and fade out
                    clip_with_fx = clip.with_effects([
                        CrossFadeIn(transition_duration),
                        CrossFadeOut(transition_duration)
                    ])
                    clips_positioned.append(clip_with_fx.with_start(current_time))
                    current_time += clip.duration - transition_duration

            main_video = CompositeVideoClip(clips_positioned)
        else:
            # No transitions - simple concatenation
            main_video = concatenate_videoclips(slide_clips, method="compose")

        # Prepare final clips list
        final_clips = []

        # Add intro title card
        if include_intro:
            print("Creating intro card...")
            if progress_callback:
                progress_callback(0.50, "Creating intro card...")
            intro_clip = self._create_title_card_simple(
                title=timeline['scenario_name'],
                description=timeline.get('scenario_description', ''),
                duration=5.0
            )
            final_clips.append(intro_clip)

        # Add main slideshow
        final_clips.append(main_video)

        # Add outro card
        if include_outro:
            print("Creating outro card...")
            if progress_callback:
                progress_callback(0.55, "Creating outro card...")
            outro_clip = self._create_outro_card_simple(duration=5.0)
            final_clips.append(outro_clip)

        # Concatenate all clips
        print("\nCompiling final video...")
        if progress_callback:
            progress_callback(0.60, "Compiling video...")
        final_video = concatenate_videoclips(final_clips, method="compose")

        # Determine output path
        if output_path is None:
            output_path = self.output_dir / f"{scenario_name}_training.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting to: {output_path}")
        print(f"Total duration: {final_video.duration:.1f}s")

        if progress_callback:
            progress_callback(0.60, "Starting encoding...")

        # Use custom progress logger to forward progress to GUI
        custom_logger = CallbackProgressLogger(progress_callback) if progress_callback else 'bar'

        final_video.write_videofile(
            str(output_path),
            fps=24,  # 24fps for training videos
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',  # Fast encoding
            bitrate='3500k',  # Good quality for 1280x800
            logger=custom_logger  # Forward progress to GUI callback
        )
        print()  # New line after encoding

        if progress_callback:
            progress_callback(1.0, "Complete!")

        # Cleanup
        final_video.close()
        main_video.close()
        for clip in slide_clips:
            clip.close()

        # Clean up temp slide files
        for slide_file in self.output_dir.glob("_slide_*.png"):
            try:
                slide_file.unlink()
            except Exception:
                pass

        print(f"\nSlideshow production complete!")
        print(f"Output: {output_path}")
        print(f"File size: {output_path.stat().st_size / (1024*1024):.1f} MB")

        return output_path

    def create_video_from_raw_recording(
        self,
        raw_video_path: Path,
        timeline_path: Path,
        audio_dir: Path,
        output_path: Optional[Path] = None,
        include_intro: bool = True,
        include_outro: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """
        Create training video from raw Playwright recording with audio narration.

        This produces authentic recordings showing real mouse movements, clicks,
        and typing - like watching someone actually use the application.

        Args:
            raw_video_path: Path to the raw Playwright .webm recording
            timeline_path: Path to the timeline JSON file (for audio timing)
            audio_dir: Directory containing audio files
            output_path: Where to save the final video
            include_intro: Add title card at beginning
            include_outro: Add outro card at end
            progress_callback: Callback function(progress: 0-1, status: str)
        """
        import json

        print(f"\n{'='*60}")
        print("RAW RECORDING PRODUCTION: Authentic Interactive Video")
        print(f"{'='*60}\n")

        # Verify raw video exists
        if not raw_video_path.exists():
            raise FileNotFoundError(f"Raw video not found: {raw_video_path}")

        print(f"Raw video: {raw_video_path}")
        print(f"File size: {raw_video_path.stat().st_size / (1024*1024):.1f} MB")

        # Load timeline for audio synchronization
        timeline = json.loads(timeline_path.read_text())
        scenario_name = timeline['scenario_id']

        print(f"Scenario: {scenario_name}")
        print(f"Steps: {len(timeline['steps'])}")

        if progress_callback:
            progress_callback(0.05, "Loading raw recording...")

        # Load the raw video
        raw_video = VideoFileClip(str(raw_video_path))
        print(f"Raw video duration: {raw_video.duration:.1f}s")
        print(f"Raw video size: {raw_video.size}")

        if progress_callback:
            progress_callback(0.15, "Processing audio...")

        # Build audio tracks - SEQUENTIAL placement to avoid overlap
        # Each audio clip starts after the previous one ends
        audio_clips = []
        current_audio_time = 0.0  # Track where next audio should start
        audio_gap = 0.5  # Small gap between audio clips

        for step in timeline['steps']:
            step_num = step['step_number']

            # Find matching audio file
            audio_file = audio_dir / f"step-{step_num:02d}-{step['step_id']}.mp3"
            if not audio_file.exists():
                audio_file = audio_dir / f"step-{step_num:02d}.mp3"

            if audio_file.exists():
                audio_clip = AudioFileClip(str(audio_file))
                # Position audio SEQUENTIALLY (no overlap)
                audio_clip = audio_clip.with_start(current_audio_time)
                audio_clips.append(audio_clip)
                print(f"  Step {step_num}: Audio at {current_audio_time:.1f}s ({audio_clip.duration:.1f}s)")
                # Move to next position after this clip ends
                current_audio_time += audio_clip.duration + audio_gap
            else:
                print(f"  Step {step_num}: No audio file found")

        if progress_callback:
            progress_callback(0.30, "Combining audio tracks...")

        # Combine all audio clips
        if audio_clips:
            combined_audio = CompositeAudioClip(audio_clips)
            # Add audio to video
            video_with_audio = raw_video.with_audio(combined_audio)
            print(f"\nCombined {len(audio_clips)} audio tracks")
        else:
            video_with_audio = raw_video
            print("\nNo audio files found - using video only")

        # Output at 1280x1067 (matches 1920x1600 aspect ratio of 1.2:1)
        target_width, target_height = 1280, 1067

        # Calculate scaling to fit target resolution
        scale_x = target_width / raw_video.size[0]
        scale_y = target_height / raw_video.size[1]
        scale = min(scale_x, scale_y)  # Use smaller scale to fit

        new_width = int(raw_video.size[0] * scale)
        new_height = int(raw_video.size[1] * scale)

        if new_width != target_width or new_height != target_height:
            # Need to resize and pad - use .resized() method
            video_resized = video_with_audio.resized((new_width, new_height))

            # Create black background and composite
            from moviepy import ColorClip
            background = ColorClip(size=(target_width, target_height), color=(31, 41, 55))
            background = background.with_duration(video_resized.duration)

            # Center the video on the background
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2

            video_with_audio = CompositeVideoClip([
                background,
                video_resized.with_position((x_offset, y_offset))
            ])

            if audio_clips:
                video_with_audio = video_with_audio.with_audio(combined_audio)

        if progress_callback:
            progress_callback(0.40, "Adding intro/outro...")

        # Prepare final clips list
        final_clips = []

        # Add intro title card
        if include_intro:
            print("Creating intro card...")
            intro_clip = self._create_title_card_simple(
                title=timeline['scenario_name'],
                description=timeline.get('scenario_description', ''),
                duration=5.0
            )
            final_clips.append(intro_clip)

        # Add main video
        final_clips.append(video_with_audio)

        # Add outro card
        if include_outro:
            print("Creating outro card...")
            outro_clip = self._create_outro_card_simple(duration=5.0)
            final_clips.append(outro_clip)

        if progress_callback:
            progress_callback(0.50, "Compiling final video...")

        # Concatenate all clips
        print("\nCompiling final video...")
        final_video = concatenate_videoclips(final_clips, method="compose")

        # Determine output path
        if output_path is None:
            output_path = self.output_dir / f"{scenario_name}_training.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting to: {output_path}")
        print(f"Total duration: {final_video.duration:.1f}s")

        if progress_callback:
            progress_callback(0.60, "Encoding video (this may take a few minutes)...")

        # Use ultrafast preset for quick encoding
        print(f"\nEncoding video... (1280x800, ultrafast preset)")

        final_video.write_videofile(
            str(output_path),
            fps=24,  # 24fps is fine for training videos
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',  # Fastest encoding
            bitrate='3500k',  # Good quality for 1280x800
            logger='bar'  # Always show progress bar in console
        )

        if progress_callback:
            progress_callback(1.0, "Complete!")

        # Cleanup
        final_video.close()
        raw_video.close()
        for clip in audio_clips:
            clip.close()

        # Get final video details
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n{'='*60}")
        print("VIDEO PRODUCTION COMPLETE")
        print(f"{'='*60}")
        print(f"Output: {output_path}")
        print(f"")
        print(f"VIDEO SPECIFICATIONS:")
        print(f"  Resolution:  {target_width} x {target_height}")
        print(f"  Frame Rate:  24 fps")
        print(f"  Bitrate:     3000 kbps")
        print(f"  Codec:       H.264 (libx264)")
        print(f"  Audio:       AAC")
        print(f"  Duration:    {final_video.duration:.1f} seconds")
        print(f"  File Size:   {file_size_mb:.1f} MB")
        print(f"")
        print(f"SOURCE RECORDING:")
        print(f"  Raw Video:   {raw_video_path.name}")
        print(f"  Input Size:  {raw_video.size[0]} x {raw_video.size[1]}")
        print(f"  Audio Tracks: {len(audio_clips)}")
        print(f"{'='*60}\n")

        return output_path


# ═══════════════════════════════════════════════════════════════════════════
# DIRECTOR TIMING CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class DirectorTiming:
    """
    Calculates professional timing for video pacing.
    Based on industry standards for e-learning content.
    """

    # Reading speed (words per minute) for narration
    NARRATION_WPM = 150

    # Minimum screen time for viewers to process content
    MIN_VISUAL_TIME = 2.0  # seconds

    # Pause durations
    INTRO_PAUSE = 0.5  # Before narration starts
    OUTRO_PAUSE = 0.8  # After narration ends
    SECTION_PAUSE = 1.5  # Between major sections
    STEP_PAUSE = 0.3  # Between steps

    @classmethod
    def calculate_narration_duration(cls, text: str) -> float:
        """Calculate how long it takes to read the narration text"""
        word_count = len(text.split())
        duration = (word_count / cls.NARRATION_WPM) * 60
        return max(duration, cls.MIN_VISUAL_TIME)

    @classmethod
    def calculate_frame_duration(cls, script_text: str, is_section_start: bool = False) -> Tuple[float, float, float]:
        """
        Calculate optimal frame timing.

        Returns:
            (intro_pause, content_duration, outro_pause)
        """
        content_duration = cls.calculate_narration_duration(script_text)

        intro_pause = cls.INTRO_PAUSE
        outro_pause = cls.SECTION_PAUSE if is_section_start else cls.OUTRO_PAUSE

        return intro_pause, content_duration, outro_pause

    @classmethod
    def get_timing_for_step(cls, step_data: Dict[str, Any]) -> VideoFrame:
        """
        Create a VideoFrame with optimized timing from step data.

        Args:
            step_data: Dictionary with keys like 'title', 'script', 'image_path', etc.
        """
        script = step_data.get('script', '')

        intro, content, outro = cls.calculate_frame_duration(script)

        return VideoFrame(
            image_path=Path(step_data.get('image_path', '')),
            audio_path=Path(step_data.get('audio_path', '')) if step_data.get('audio_path') else None,
            duration=intro + content + outro,
            script_text=script,
            title=step_data.get('title', ''),
            intro_pause=intro,
            outro_pause=outro
        )


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_element_bounds_script(selector: str) -> str:
    """
    JavaScript to get element bounds for annotation positioning.
    Run this via page.evaluate() to get coordinates for annotations.
    """
    return f"""
        (function() {{
            const element = document.querySelector('{selector}');
            if (!element) return null;

            const rect = element.getBoundingClientRect();
            return {{
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                centerX: rect.x + rect.width / 2,
                centerY: rect.y + rect.height / 2
            }};
        }})();
    """


def create_annotation_from_element_bounds(bounds: Dict, annotation_type: str = "highlight") -> AnnotationConfig:
    """
    Create an AnnotationConfig from element bounds returned by JavaScript.

    Args:
        bounds: Dict with x, y, width, height, centerX, centerY
        annotation_type: "highlight", "circle", "spotlight", "arrow"
    """
    if not bounds:
        return AnnotationConfig()

    x, y = int(bounds['x']), int(bounds['y'])
    w, h = int(bounds['width']), int(bounds['height'])
    cx, cy = int(bounds['centerX']), int(bounds['centerY'])

    # Add padding
    padding = 10

    if annotation_type == "highlight":
        return AnnotationConfig(
            highlight_box=(x - padding, y - padding, x + w + padding, y + h + padding)
        )
    elif annotation_type == "circle":
        radius = max(w, h) // 2 + padding * 2
        return AnnotationConfig(
            circle_center=(cx, cy),
            circle_radius=radius
        )
    elif annotation_type == "spotlight":
        return AnnotationConfig(
            spotlight_area=(x - padding, y - padding, x + w + padding, y + h + padding)
        )
    elif annotation_type == "arrow":
        # Arrow from top-left corner pointing to element
        return AnnotationConfig(
            arrow_from=(x - 100, y - 80),
            arrow_to=(x, y)
        )

    return AnnotationConfig()
