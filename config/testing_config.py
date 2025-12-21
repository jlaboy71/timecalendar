"""
PTO Central - Testing Console Configuration
Centralized configuration for testing and documentation generation.

SECURITY NOTE: API keys are loaded from .env.testing file.
Never commit API keys to version control.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env.testing
env_path = Path(__file__).parent.parent / '.env.testing'
load_dotenv(env_path)


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class TTSVoice(Enum):
    """Available OpenAI TTS voices"""
    ONYX = "onyx"      # Deep male, professional - DEFAULT
    ALLOY = "alloy"    # Neutral, balanced
    NOVA = "nova"      # Warm female
    ECHO = "echo"      # Male, conversational
    FABLE = "fable"    # British accent
    SHIMMER = "shimmer"  # Female, expressive


@dataclass
class TestAccount:
    """Represents a test user account"""
    username: str
    password: str
    role: str
    location: str
    location_code: str
    display_name: str
    description: str
    icon: str
    color: str


@dataclass
class TestingConfig:
    """Master configuration for Testing Console"""

    # ═══════════════════════════════════════════════════════════════════════
    # API KEYS (loaded from environment)
    # ═══════════════════════════════════════════════════════════════════════

    openai_api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))

    # ═══════════════════════════════════════════════════════════════════════
    # BASE URL CONFIGURATION
    # Use 127.0.0.1 instead of localhost for Playwright compatibility on Windows
    # ═══════════════════════════════════════════════════════════════════════

    base_url: str = field(default_factory=lambda: os.getenv(
        'PTO_BASE_URL',
        'http://localhost:8080'  # No HTTPS - matches default app config
    ))

    environment: Environment = field(default_factory=lambda: Environment(
        os.getenv('PTO_ENVIRONMENT', 'development')
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # PRESET TEST ACCOUNTS
    # ═══════════════════════════════════════════════════════════════════════

    test_accounts: Dict[str, TestAccount] = field(default_factory=lambda: {
        'ptouser': TestAccount(
            username='ptouser',
            password='2ez4me!!',
            role='employee',
            location='Chicago',
            location_code='CHI',
            display_name='PTO User',
            description='Employee - Submits PTO requests',
            icon='person',
            color='blue'
        ),
        'ptomanager': TestAccount(
            username='ptomanager',
            password='2ez4me!!',
            role='manager',
            location='Chicago',
            location_code='CHI',
            display_name='PTO Manager',
            description='Manager - Approves team requests',
            icon='supervisor_account',
            color='green'
        ),
        'ptoadmin': TestAccount(
            username='ptoadmin',
            password='2ez4me!!',
            role='admin',
            location='Chicago',
            location_code='CHI',
            display_name='PTO Admin',
            description='Admin - System administration',
            icon='admin_panel_settings',
            color='orange'
        )
    })

    # ═══════════════════════════════════════════════════════════════════════
    # OUTPUT PATHS
    # ═══════════════════════════════════════════════════════════════════════

    output_base: Path = field(default_factory=lambda: Path(__file__).parent.parent / 'nicegui_app' / 'static' / 'help')

    @property
    def screenshots_dir(self) -> Path:
        return self.output_base / 'screenshots'

    @property
    def docs_dir(self) -> Path:
        return self.output_base / 'docs'

    @property
    def videos_dir(self) -> Path:
        return self.output_base / 'videos'

    @property
    def audio_dir(self) -> Path:
        return self.output_base / 'audio'

    # ═══════════════════════════════════════════════════════════════════════
    # PLAYWRIGHT SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    browser_type: str = 'chromium'
    headless: bool = False  # Set True for CI/production
    slow_mo: int = 100  # Milliseconds between actions for visibility
    default_timeout: int = 30000  # 30 seconds
    viewport_width: int = 1100  # Fits max-w-5xl (1024px) + padding
    viewport_height: int = 1400  # Extra tall to capture full page content
    ignore_https_errors: bool = True  # Required for self-signed localhost certs

    # ═══════════════════════════════════════════════════════════════════════
    # VIDEO SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    video_enabled: bool = True
    video_width: int = 1100  # Match viewport
    video_height: int = 1400  # Match viewport

    # ═══════════════════════════════════════════════════════════════════════
    # AUDIO/TTS SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    tts_enabled: bool = False  # Toggle for audio narration
    tts_voice: TTSVoice = TTSVoice.ONYX  # Default voice
    tts_model: str = "tts-1-hd"  # High quality model
    tts_speed: float = 1.0  # Speaking rate (0.25 to 4.0)

    # ═══════════════════════════════════════════════════════════════════════
    # DOCUMENTATION SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    generate_markdown: bool = True
    generate_screenshots: bool = True
    generate_video: bool = True
    generate_timeline: bool = True  # JSON timeline for video sync
    generate_srt: bool = True  # Subtitle file

    # ═══════════════════════════════════════════════════════════════════════
    # FUTURE: VOICE INPUT STAGING (Whisper STT)
    # Placeholder for future voice-to-PTO feature
    # ═══════════════════════════════════════════════════════════════════════

    whisper_enabled: bool = False  # Future feature
    whisper_model: str = "whisper-1"  # Future feature

    def ensure_directories(self):
        """Create output directories if they don't exist"""
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list:
        """Validate configuration and return list of issues"""
        issues = []

        if self.tts_enabled and not self.openai_api_key:
            issues.append("TTS enabled but OPENAI_API_KEY not set in .env.testing")

        if not self.base_url:
            issues.append("PTO_BASE_URL not configured")

        return issues

    def get_account(self, username: str) -> Optional[TestAccount]:
        """Get a test account by username"""
        return self.test_accounts.get(username)

    def get_accounts_by_role(self, role: str) -> list:
        """Get all test accounts with a specific role"""
        return [acc for acc in self.test_accounts.values() if acc.role == role]


# Global configuration instance
testing_config = TestingConfig()
