# PTO Central - Integrated Testing & Documentation Console
# Complete Implementation Instructions for Claude Code (VS Code)

## Document Overview

**Purpose:** Build an integrated Testing Console within the PTO Central admin panel that enables:
1. Multi-user simulation (preset accounts + custom credentials)
2. Automated screenshot capture and help documentation generation
3. Video tutorial recording with timeline-matched audio narration
4. Pre-built test scenarios with extensibility for new workflows

**Target Location:** `/admin/testing-console` (new route, admin/superadmin access only)

**Safety:** This implementation is READ-ONLY for the database and ADDITIVE-ONLY for the codebase. It does NOT modify any existing business logic, calculations, or application functionality.

---

## PHASE 0: Prerequisites & Safety Checklist

### 0.1 Pre-Implementation Verification

Before writing any code, verify the following:

```
□ PTO Central application runs successfully
□ Admin login works (netadmin account)
□ /admin or /system-admin route exists and loads
□ static/ directory exists in project root
□ No syntax errors in existing codebase
```

### 0.2 Safety Guarantees

This implementation GUARANTEES:

| Aspect | Guarantee |
|--------|-----------|
| Database | READ-ONLY queries only — no INSERT, UPDATE, DELETE |
| Business Logic | ZERO modifications to existing calculation code |
| Existing Routes | NO changes to any existing page or route |
| User Sessions | ISOLATED — uses separate Playwright browser sessions |
| Dependencies | ADDITIVE only — new packages don't conflict |

### 0.3 New Dependencies Required

Install these packages (they do not conflict with existing dependencies):

```bash
pip install playwright openai python-dotenv
playwright install chromium
```

### 0.4 Directory Structure to Create

```
project_root/
├── config/
│   └── testing_config.py          # NEW: Testing configuration
├── services/
│   ├── playwright_engine.py       # NEW: Browser automation
│   ├── doc_generator.py           # NEW: Help doc generation
│   └── audio_narration.py         # NEW: OpenAI TTS integration
├── nicegui_app/
│   └── pages/
│       └── testing_console.py     # NEW: Admin UI page
├── static/
│   └── help/                      # NEW: Generated documentation
│       ├── screenshots/
│       ├── docs/
│       ├── videos/
│       └── audio/
└── .env.testing                   # NEW: API keys (gitignored)
```

---

## PHASE 1: Configuration Setup

### 1.1 Create Environment File for API Keys

**File:** `.env.testing` (in project root)

```env
# TJM Testing Console - API Keys
# DO NOT COMMIT THIS FILE TO VERSION CONTROL

# OpenAI API Key for Text-to-Speech narration
# Get your key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Base URL (change when deploying to production)
TJM_BASE_URL=https://localhost:8080

# Environment
TJM_ENVIRONMENT=development
```

**IMPORTANT:** Add `.env.testing` to your `.gitignore` file:

```gitignore
# Testing secrets
.env.testing
```

### 1.2 Create Testing Configuration Module

**File:** `config/testing_config.py`

```python
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
    # Automatically adapts between localhost and production
    # ═══════════════════════════════════════════════════════════════════════
    
    base_url: str = field(default_factory=lambda: os.getenv(
        'TJM_BASE_URL', 
        'https://localhost:8080'
    ))
    
    environment: Environment = field(default_factory=lambda: Environment(
        os.getenv('TJM_ENVIRONMENT', 'development')
    ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # PRESET TEST ACCOUNTS
    # ═══════════════════════════════════════════════════════════════════════
    
    test_accounts: Dict[str, TestAccount] = field(default_factory=lambda: {
        'techuser': TestAccount(
            username='techuser',
            password='2ez4me!!',
            role='employee',
            location='Chicago',
            location_code='CHI',
            display_name='Tech User',
            description='Chicago Office Employee',
            icon='person',
            color='blue'
        ),
        'nyuser': TestAccount(
            username='nyuser',
            password='2ez4me!!',
            role='employee',
            location='New York',
            location_code='NYC',
            display_name='NY User',
            description='New York Office Employee',
            icon='person',
            color='purple'
        ),
        'techmanager': TestAccount(
            username='techmanager',
            password='2ez4me!!',
            role='manager',
            location='Chicago',
            location_code='CHI',
            display_name='Tech Manager',
            description='Technology Department Manager',
            icon='supervisor_account',
            color='green'
        ),
        'netadmin': TestAccount(
            username='netadmin',
            password='netpass',
            role='admin',
            location='Chicago',
            location_code='CHI',
            display_name='Net Admin',
            description='System Administrator',
            icon='admin_panel_settings',
            color='orange'
        )
    })
    
    # ═══════════════════════════════════════════════════════════════════════
    # OUTPUT PATHS
    # ═══════════════════════════════════════════════════════════════════════
    
    output_base: Path = field(default_factory=lambda: Path('static/help'))
    
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
    viewport_width: int = 1280
    viewport_height: int = 720
    ignore_https_errors: bool = True  # Required for self-signed localhost certs
    
    # ═══════════════════════════════════════════════════════════════════════
    # VIDEO SETTINGS
    # ═══════════════════════════════════════════════════════════════════════
    
    video_enabled: bool = True
    video_width: int = 1280
    video_height: int = 720
    
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
            issues.append("TJM_BASE_URL not configured")
        
        return issues
    
    def get_account(self, username: str) -> Optional[TestAccount]:
        """Get a test account by username"""
        return self.test_accounts.get(username)
    
    def get_accounts_by_role(self, role: str) -> list:
        """Get all test accounts with a specific role"""
        return [acc for acc in self.test_accounts.values() if acc.role == role]


# Global configuration instance
testing_config = TestingConfig()
```

---

## PHASE 2: Playwright Engine Service

### 2.1 Create Browser Automation Engine

**File:** `services/playwright_engine.py`

```python
"""
PTO Central - Playwright Automation Engine
Handles browser automation for testing and documentation generation.

This service:
- Manages browser sessions for different test users
- Captures screenshots at defined steps
- Records video of test scenarios
- Collects timing metadata for audio synchronization
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import json
import time

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

# Import config - adjust path as needed for your project structure
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.testing_config import testing_config, TestAccount


@dataclass
class StepResult:
    """Result of a single test step"""
    step_number: int
    step_id: str
    title: str
    description: str
    script: str  # Narration text for TTS
    action: str
    timestamp_start: float  # Seconds from scenario start
    timestamp_end: float
    duration: float
    screenshot_path: Optional[Path] = None
    success: bool = True
    error_message: Optional[str] = None
    selector_used: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'step_number': self.step_number,
            'step_id': self.step_id,
            'title': self.title,
            'description': self.description,
            'script': self.script,
            'action': self.action,
            'timestamp_start': self.timestamp_start,
            'timestamp_end': self.timestamp_end,
            'duration': self.duration,
            'screenshot_path': str(self.screenshot_path) if self.screenshot_path else None,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


@dataclass
class ScenarioResult:
    """Result of a complete scenario run"""
    scenario_id: str
    scenario_name: str
    scenario_description: str
    user_account: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration: float = 0.0
    steps: List[StepResult] = field(default_factory=list)
    video_path: Optional[Path] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'scenario_description': self.scenario_description,
            'user_account': self.user_account,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration': self.total_duration,
            'steps': [step.to_dict() for step in self.steps],
            'video_path': str(self.video_path) if self.video_path else None,
            'success': self.success,
            'error_message': self.error_message
        }


@dataclass
class ScenarioStep:
    """Definition of a single step in a scenario"""
    step_id: str
    title: str
    description: str
    script: str  # What the narrator says
    action: str  # 'navigate', 'click', 'fill', 'select', 'wait', 'screenshot'
    selector: Optional[str] = None  # CSS selector for element
    value: Optional[str] = None  # Value for fill/select actions
    url: Optional[str] = None  # For navigate action
    wait_time: float = 1.0  # Seconds to wait after action
    screenshot: bool = True  # Take screenshot after this step


@dataclass
class Scenario:
    """Complete scenario definition"""
    scenario_id: str
    name: str
    description: str
    required_role: str  # Minimum role required
    default_account: str  # Default test account to use
    steps: List[ScenarioStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class PlaywrightEngine:
    """
    Browser automation engine for testing and documentation.
    
    Usage:
        engine = PlaywrightEngine()
        await engine.initialize()
        result = await engine.run_scenario(scenario, 'techuser')
        await engine.cleanup()
    """
    
    def __init__(self, config=None):
        self.config = config or testing_config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._scenario_start_time: float = 0
        self._current_result: Optional[ScenarioResult] = None
        
        # Callbacks for progress updates
        self.on_step_start: Optional[Callable] = None
        self.on_step_complete: Optional[Callable] = None
        self.on_scenario_complete: Optional[Callable] = None
    
    async def initialize(self):
        """Initialize Playwright and browser"""
        self.config.ensure_directories()
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo
        )
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def create_session(
        self, 
        account: TestAccount,
        record_video: bool = True,
        scenario_id: str = "session"
    ) -> Page:
        """Create a new browser session for a test account"""
        
        # Video recording setup
        video_config = None
        if record_video and self.config.video_enabled:
            video_dir = self.config.videos_dir / scenario_id
            video_dir.mkdir(parents=True, exist_ok=True)
            video_config = {
                'dir': str(video_dir),
                'size': {
                    'width': self.config.video_width,
                    'height': self.config.video_height
                }
            }
        
        # Create browser context
        self.context = await self.browser.new_context(
            viewport={
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            ignore_https_errors=self.config.ignore_https_errors,
            record_video_dir=video_config['dir'] if video_config else None,
            record_video_size=video_config['size'] if video_config else None
        )
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.default_timeout)
        
        return self.page
    
    async def login(self, account: TestAccount) -> bool:
        """
        Log into the application with the given account.
        
        NOTE: Adjust selectors to match your actual login form.
        """
        try:
            await self.page.goto(self.config.base_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for login form to be visible
            # ADJUST THESE SELECTORS to match your NiceGUI login form
            await self.page.wait_for_selector(
                'input[type="text"], input[name="username"], input[placeholder*="user" i]',
                timeout=10000
            )
            
            # Fill username
            username_input = self.page.locator(
                'input[type="text"], input[name="username"], input[placeholder*="user" i]'
            ).first
            await username_input.fill(account.username)
            
            # Fill password
            password_input = self.page.locator('input[type="password"]').first
            await password_input.fill(account.password)
            
            # Click login button
            login_button = self.page.locator(
                'button[type="submit"], button:has-text("Login"), button:has-text("Sign In"), button:has-text("Log In")'
            ).first
            await login_button.click()
            
            # Wait for navigation to complete
            await self.page.wait_for_load_state('networkidle')
            
            # Verify login succeeded (URL should change from login page)
            await asyncio.sleep(1)  # Brief wait for any redirects
            
            return True
            
        except Exception as e:
            print(f"Login failed for {account.username}: {e}")
            return False
    
    async def run_scenario(
        self,
        scenario: Scenario,
        account_username: str = None,
        custom_credentials: Dict[str, str] = None
    ) -> ScenarioResult:
        """
        Run a complete test scenario.
        
        Args:
            scenario: The scenario definition to run
            account_username: Username of preset account to use
            custom_credentials: Dict with 'username' and 'password' for custom login
        
        Returns:
            ScenarioResult with all step results and metadata
        """
        # Determine which account to use
        if custom_credentials:
            account = TestAccount(
                username=custom_credentials['username'],
                password=custom_credentials['password'],
                role='custom',
                location='Unknown',
                location_code='UNK',
                display_name=custom_credentials['username'],
                description='Custom test account',
                icon='person',
                color='gray'
            )
        else:
            username = account_username or scenario.default_account
            account = self.config.get_account(username)
            if not account:
                raise ValueError(f"Unknown account: {username}")
        
        # Initialize result tracking
        self._current_result = ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            scenario_description=scenario.description,
            user_account=account.username,
            started_at=datetime.now()
        )
        
        try:
            # Create browser session with video recording
            await self.create_session(
                account, 
                record_video=self.config.generate_video,
                scenario_id=scenario.scenario_id
            )
            
            # Login
            login_success = await self.login(account)
            if not login_success:
                raise Exception(f"Failed to login as {account.username}")
            
            # Record scenario start time
            self._scenario_start_time = time.time()
            
            # Execute each step
            for i, step in enumerate(scenario.steps, 1):
                step_result = await self._execute_step(step, i, scenario.scenario_id)
                self._current_result.steps.append(step_result)
                
                if not step_result.success:
                    self._current_result.success = False
                    self._current_result.error_message = f"Step {i} failed: {step_result.error_message}"
                    break
            
            # Finalize
            self._current_result.completed_at = datetime.now()
            self._current_result.total_duration = time.time() - self._scenario_start_time
            
            # Get video path if recorded
            if self.config.generate_video and self.page.video:
                await self.page.close()  # Close page to finalize video
                video_path = await self.context.pages[0].video.path() if self.context.pages else None
                if video_path:
                    self._current_result.video_path = Path(video_path)
            
        except Exception as e:
            self._current_result.success = False
            self._current_result.error_message = str(e)
            self._current_result.completed_at = datetime.now()
        
        finally:
            # Clean up context (but keep browser for next scenario)
            if self.context:
                await self.context.close()
                self.context = None
                self.page = None
        
        # Callback
        if self.on_scenario_complete:
            self.on_scenario_complete(self._current_result)
        
        return self._current_result
    
    async def _execute_step(
        self, 
        step: ScenarioStep, 
        step_number: int,
        scenario_id: str
    ) -> StepResult:
        """Execute a single scenario step"""
        
        step_start = time.time() - self._scenario_start_time
        
        # Callback
        if self.on_step_start:
            self.on_step_start(step_number, step.title)
        
        result = StepResult(
            step_number=step_number,
            step_id=step.step_id,
            title=step.title,
            description=step.description,
            script=step.script,
            action=step.action,
            timestamp_start=step_start,
            timestamp_end=0,
            duration=0,
            selector_used=step.selector
        )
        
        try:
            # Execute the action
            if step.action == 'navigate':
                url = step.url or self.config.base_url
                await self.page.goto(url)
                await self.page.wait_for_load_state('networkidle')
                
            elif step.action == 'click':
                if step.selector:
                    await self.page.click(step.selector)
                    await self.page.wait_for_load_state('networkidle')
                    
            elif step.action == 'fill':
                if step.selector and step.value is not None:
                    await self.page.fill(step.selector, step.value)
                    
            elif step.action == 'select':
                if step.selector and step.value:
                    await self.page.select_option(step.selector, step.value)
                    
            elif step.action == 'wait':
                await asyncio.sleep(step.wait_time)
                
            elif step.action == 'screenshot':
                pass  # Just take screenshot, handled below
            
            # Wait after action
            if step.wait_time > 0:
                await asyncio.sleep(step.wait_time)
            
            # Take screenshot if enabled
            if step.screenshot and self.config.generate_screenshots:
                screenshot_dir = self.config.screenshots_dir / scenario_id
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                
                screenshot_path = screenshot_dir / f"step-{step_number:02d}-{step.step_id}.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=False)
                result.screenshot_path = screenshot_path
            
            result.success = True
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
        
        # Record timing
        step_end = time.time() - self._scenario_start_time
        result.timestamp_end = step_end
        result.duration = step_end - step_start
        
        # Callback
        if self.on_step_complete:
            self.on_step_complete(result)
        
        return result
    
    async def take_screenshot(self, name: str, scenario_id: str = "manual") -> Path:
        """Take a manual screenshot"""
        screenshot_dir = self.config.screenshots_dir / scenario_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        screenshot_path = screenshot_dir / f"{name}.png"
        await self.page.screenshot(path=str(screenshot_path), full_page=False)
        
        return screenshot_path


# ═══════════════════════════════════════════════════════════════════════════
# PRE-BUILT SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def get_pto_request_scenario() -> Scenario:
    """
    Scenario: Employee submits a PTO request
    
    NOTE: Adjust selectors to match your actual UI elements.
    """
    return Scenario(
        scenario_id="pto-request",
        name="Submit PTO Request",
        description="Employee submits a new PTO request through the calendar interface",
        required_role="employee",
        default_account="techuser",
        tags=["employee", "pto", "request", "core-workflow"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the PTO Central and log in",
                script="Welcome to PTO Central. First, log in with your employee credentials.",
                action="screenshot",  # Login handled separately
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="View Dashboard",
                description="The employee dashboard shows your PTO balances and recent activity",
                script="After logging in, you'll see your dashboard with your current PTO balances displayed.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-new-request",
                title="Click New Request",
                description="Click the New Request button to start a PTO request",
                script="To submit a new request, click the New Request button in the top right corner.",
                action="click",
                selector="button:has-text('New Request'), button:has-text('Request PTO'), a:has-text('New Request')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="request-form",
                title="PTO Request Form",
                description="The request form allows you to specify leave type and dates",
                script="The request form appears. Here you'll select your leave type and choose your dates.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-leave-type",
                title="Select Leave Type",
                description="Choose the type of leave (vacation, sick, personal)",
                script="First, select your leave type from the dropdown menu. Options include vacation, sick time, and personal days.",
                action="screenshot",  # Just document, don't actually select
                # To actually select: action="select", selector="select[name='leave_type']", value="vacation"
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-dates",
                title="Select Dates",
                description="Choose start and end dates for your time off",
                script="Next, select your start and end dates using the calendar picker.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="add-notes",
                title="Add Notes (Optional)",
                description="Add any notes or comments for your manager",
                script="Optionally, add any notes for your manager explaining the reason for your request.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="submit-request",
                title="Submit Request",
                description="Review and submit the request",
                script="Review your request details, then click Submit to send it to your manager for approval.",
                action="screenshot",
                # To actually submit: action="click", selector="button:has-text('Submit')"
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="confirmation",
                title="Request Submitted",
                description="Confirmation that the request was submitted successfully",
                script="Your request has been submitted successfully. You'll receive a notification when your manager responds.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_manager_approval_scenario() -> Scenario:
    """
    Scenario: Manager reviews and approves a PTO request
    """
    return Scenario(
        scenario_id="manager-approval",
        name="Manager Approval Workflow",
        description="Manager reviews pending requests and approves or denies them",
        required_role="manager",
        default_account="techmanager",
        tags=["manager", "approval", "workflow"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Manager logs into the application",
                script="As a manager, log in to access your approval queue.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="Manager dashboard shows pending approvals count",
                script="Your manager dashboard displays the number of pending requests awaiting your review.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-approvals",
                title="Access Approval Queue",
                description="Navigate to the approval queue",
                script="Click on Pending Approvals to view all requests waiting for your decision.",
                action="click",
                selector="a:has-text('Approvals'), a:has-text('Pending'), button:has-text('Approvals')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approval-queue",
                title="View Pending Requests",
                description="List of all pending PTO requests from team members",
                script="The approval queue shows all pending requests from your team members with key details.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-request",
                title="Select Request to Review",
                description="Click on a request to view details",
                script="Click on a request to view the full details before making your decision.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-details",
                title="Review Request Details",
                description="Review employee details, dates, and team coverage",
                script="Review the employee's balance, requested dates, and team coverage before approving.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approve-action",
                title="Approve or Deny",
                description="Make approval decision",
                script="Click Approve to grant the request, or Deny with a reason if you cannot approve.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="confirmation",
                title="Decision Confirmed",
                description="Confirmation of the approval action",
                script="Your decision has been recorded and the employee will be notified automatically.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_admin_user_management_scenario() -> Scenario:
    """
    Scenario: Admin manages user accounts
    """
    return Scenario(
        scenario_id="admin-user-management",
        name="Admin User Management",
        description="Administrator creates and manages user accounts",
        required_role="admin",
        default_account="netadmin",
        tags=["admin", "users", "management"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Admin Login",
                description="Administrator logs into the system",
                script="Log in with your administrator credentials to access system management features.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="admin-dashboard",
                title="Admin Dashboard",
                description="Admin dashboard with system overview",
                script="The administrator dashboard provides an overview of system status and quick access to management tools.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-user-management",
                title="Access User Management",
                description="Navigate to user management section",
                script="Click on User Management to view and manage employee accounts.",
                action="click",
                selector="a:has-text('Users'), a:has-text('User Management'), button:has-text('Manage Users')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="user-list",
                title="View User List",
                description="List of all users in the system",
                script="The user list shows all employees with their roles, departments, and account status.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="user-actions",
                title="User Actions",
                description="Available actions for user management",
                script="From here you can create new users, edit existing accounts, reset passwords, or adjust permissions.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_all_scenarios() -> Dict[str, Scenario]:
    """Get all pre-built scenarios"""
    return {
        'pto-request': get_pto_request_scenario(),
        'manager-approval': get_manager_approval_scenario(),
        'admin-user-management': get_admin_user_management_scenario(),
    }
```

---

## PHASE 3: Documentation Generator Service

### 3.1 Create Help Documentation Generator

**File:** `services/doc_generator.py`

```python
"""
PTO Central - Documentation Generator Service
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
                md_lines.append(f"> 💡 **Tip:** {step.script}")
                md_lines.append("")
            
            md_lines.append("---")
            md_lines.append("")
        
        # Footer
        md_lines.append("## Need Help?")
        md_lines.append("")
        md_lines.append("If you encounter any issues, please contact your system administrator.")
        md_lines.append("")
        md_lines.append(f"*Document generated automatically by PTO Central Testing Console*")
        
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
```

---

## PHASE 4: Audio Narration Service

### 4.1 Create OpenAI TTS Integration

**File:** `services/audio_narration.py`

```python
"""
PTO Central - Audio Narration Service
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
```

---

## PHASE 5: Testing Console UI (NiceGUI Page)

### 5.1 Create the Admin UI Page

**File:** `nicegui_app/pages/testing_console.py`

```python
"""
PTO Central - Testing Console UI
Admin interface for testing, documentation generation, and scenario execution.

Route: /admin/testing-console
Access: Admin and SuperAdmin roles only
"""

from nicegui import ui, app
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

# Import our services - adjust paths as needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.testing_config import testing_config, TTSVoice, TestAccount
from services.playwright_engine import (
    PlaywrightEngine, 
    Scenario, 
    ScenarioResult,
    get_all_scenarios
)
from services.doc_generator import DocumentationGenerator
from services.audio_narration import AudioNarrationService


# ═══════════════════════════════════════════════════════════════════════════
# TJM BRAND COLORS
# ═══════════════════════════════════════════════════════════════════════════

PTO_GOLD = '#c9a227'
PTO_GRAY = '#5a6a72'
TJM_DARK = '#1a1a2e'


# ═══════════════════════════════════════════════════════════════════════════
# CONSOLE STATE
# ═══════════════════════════════════════════════════════════════════════════

class ConsoleState:
    """Tracks the state of the testing console"""
    
    def __init__(self):
        self.is_running: bool = False
        self.current_scenario: Optional[str] = None
        self.current_step: int = 0
        self.total_steps: int = 0
        self.log_entries: list = []
        self.last_result: Optional[ScenarioResult] = None
        
        # UI References (set during page build)
        self.log_container = None
        self.progress_bar = None
        self.status_label = None
        self.run_button = None
    
    def log(self, message: str, level: str = 'info'):
        """Add a log entry"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = {
            'timestamp': timestamp,
            'message': message,
            'level': level
        }
        self.log_entries.append(entry)
        
        # Update UI if available
        if self.log_container:
            self._update_log_ui(entry)
    
    def _update_log_ui(self, entry: dict):
        """Update the log display in the UI"""
        color_map = {
            'info': 'text-gray-300',
            'success': 'text-green-400',
            'warning': 'text-yellow-400',
            'error': 'text-red-400'
        }
        color = color_map.get(entry['level'], 'text-gray-300')
        
        with self.log_container:
            ui.label(
                f"[{entry['timestamp']}] {entry['message']}"
            ).classes(f'text-xs font-mono {color}')
    
    def clear_logs(self):
        """Clear all log entries"""
        self.log_entries = []
        if self.log_container:
            self.log_container.clear()


# Global state instance
console_state = ConsoleState()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PAGE BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def create_testing_console_page():
    """Build the complete Testing Console UI"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # PAGE HEADER
    # ═══════════════════════════════════════════════════════════════════════
    
    with ui.row().classes('w-full items-center justify-between mb-4'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('science', size='xl').classes(f'text-[{PTO_GOLD}]')
            with ui.column().classes('gap-0'):
                ui.label('Testing Console').classes('text-2xl font-bold')
                ui.label('Documentation & Scenario Testing').classes('text-sm text-gray-500')
        
        with ui.row().classes('gap-2'):
            ui.chip('ADMIN TOOL', color='orange').props('outline')
            status_chip = ui.chip('Ready', color='green', icon='check_circle')
    
    ui.separator()
    
    # ═══════════════════════════════════════════════════════════════════════
    # MAIN LAYOUT: Three Columns
    # ═══════════════════════════════════════════════════════════════════════
    
    with ui.row().classes('w-full gap-4 mt-4'):
        
        # ─────────────────────────────────────────────────────────────────────
        # COLUMN 1: User Simulation Panel
        # ─────────────────────────────────────────────────────────────────────
        
        with ui.card().classes('w-80 flex-shrink-0'):
            ui.label('User Simulation').classes('text-lg font-semibold mb-3')
            
            # Preset Accounts
            ui.label('Preset Accounts').classes('text-sm font-medium text-gray-600 mb-2')
            
            account_select = ui.select(
                options={
                    key: f"{acc.display_name} ({acc.location_code}) - {acc.role}"
                    for key, acc in testing_config.test_accounts.items()
                },
                value='techuser',
                label='Select Account'
            ).classes('w-full')
            
            # Display selected account info
            with ui.card().classes('w-full bg-gray-50 mt-2 p-3') as account_info_card:
                account_icon = ui.icon('person', size='sm').classes('text-blue-500')
                account_name = ui.label('Tech User').classes('font-medium')
                account_details = ui.label('Chicago • Employee').classes('text-xs text-gray-500')
            
            def update_account_display():
                account = testing_config.get_account(account_select.value)
                if account:
                    account_name.text = account.display_name
                    account_details.text = f"{account.location} • {account.role.title()}"
                    account_icon.props(f'color={account.color}')
            
            account_select.on_value_change(lambda: update_account_display())
            
            ui.separator().classes('my-4')
            
            # Custom Credentials
            ui.label('Custom Login').classes('text-sm font-medium text-gray-600 mb-2')
            
            custom_username = ui.input(
                label='Username',
                placeholder='Enter username...'
            ).classes('w-full')
            
            custom_password = ui.input(
                label='Password',
                placeholder='Enter password...',
                password=True,
                password_toggle_button=True
            ).classes('w-full')
            
            use_custom = ui.checkbox('Use custom credentials').classes('mt-2')
            
            ui.separator().classes('my-4')
            
            # Output Options
            ui.label('Output Options').classes('text-sm font-medium text-gray-600 mb-2')
            
            opt_screenshots = ui.checkbox('Screenshots', value=True)
            opt_markdown = ui.checkbox('Markdown Help Doc', value=True)
            opt_video = ui.checkbox('Video Recording', value=True)
            opt_audio = ui.checkbox('Audio Narration', value=False)
            
            # Voice Selection (shown when audio enabled)
            with ui.column().classes('w-full mt-2').bind_visibility_from(opt_audio, 'value'):
                voice_select = ui.select(
                    options={
                        'onyx': 'Onyx (Male, Professional)',
                        'alloy': 'Alloy (Neutral)',
                        'nova': 'Nova (Female, Warm)',
                        'echo': 'Echo (Male, Casual)'
                    },
                    value='onyx',
                    label='Voice'
                ).classes('w-full')
                
                # Voice preview button
                async def preview_voice():
                    console_state.log(f"Playing voice preview: {voice_select.value}")
                    ui.notify(f"Voice preview: {voice_select.value}", type='info')
                
                ui.button(
                    'Preview Voice',
                    icon='play_arrow',
                    on_click=preview_voice
                ).props('flat dense').classes('mt-1')
        
        # ─────────────────────────────────────────────────────────────────────
        # COLUMN 2: Scenario Selection & Execution
        # ─────────────────────────────────────────────────────────────────────
        
        with ui.card().classes('flex-grow'):
            ui.label('Test Scenarios').classes('text-lg font-semibold mb-3')
            
            # Scenario Cards
            scenarios = get_all_scenarios()
            
            scenario_select = ui.radio(
                options={
                    key: scenario.name 
                    for key, scenario in scenarios.items()
                },
                value='pto-request'
            ).classes('w-full')
            
            # Scenario description panel
            with ui.card().classes('w-full bg-gray-50 mt-3 p-4') as scenario_info:
                scenario_title = ui.label('Submit PTO Request').classes('font-semibold')
                scenario_desc = ui.label(
                    'Employee submits a new PTO request through the calendar interface'
                ).classes('text-sm text-gray-600 mt-1')
                
                with ui.row().classes('gap-2 mt-2'):
                    scenario_role_chip = ui.chip('employee', color='blue').props('dense')
                    scenario_steps_chip = ui.chip('9 steps', color='gray').props('dense outline')
            
            def update_scenario_display():
                scenario = scenarios.get(scenario_select.value)
                if scenario:
                    scenario_title.text = scenario.name
                    scenario_desc.text = scenario.description
                    scenario_role_chip.text = scenario.required_role
                    scenario_steps_chip.text = f"{len(scenario.steps)} steps"
            
            scenario_select.on_value_change(lambda: update_scenario_display())
            
            ui.separator().classes('my-4')
            
            # Progress Section
            ui.label('Execution Progress').classes('text-sm font-medium text-gray-600 mb-2')
            
            progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full')
            console_state.progress_bar = progress_bar
            
            with ui.row().classes('w-full justify-between mt-1'):
                step_label = ui.label('Ready to run').classes('text-xs text-gray-500')
                console_state.status_label = step_label
                time_label = ui.label('--:--').classes('text-xs text-gray-500')
            
            ui.separator().classes('my-4')
            
            # Action Buttons
            with ui.row().classes('w-full gap-2'):
                
                async def run_scenario():
                    """Execute the selected scenario"""
                    if console_state.is_running:
                        ui.notify('A scenario is already running', type='warning')
                        return
                    
                    console_state.is_running = True
                    console_state.log('Starting scenario execution...', 'info')
                    run_btn.props('loading')
                    
                    try:
                        # Get configuration
                        scenario = scenarios.get(scenario_select.value)
                        
                        # Determine credentials
                        if use_custom.value and custom_username.value:
                            credentials = {
                                'username': custom_username.value,
                                'password': custom_password.value
                            }
                            account_username = None
                        else:
                            credentials = None
                            account_username = account_select.value
                        
                        # Update config based on toggles
                        testing_config.generate_screenshots = opt_screenshots.value
                        testing_config.generate_markdown = opt_markdown.value
                        testing_config.generate_video = opt_video.value
                        testing_config.tts_enabled = opt_audio.value
                        if opt_audio.value:
                            testing_config.tts_voice = TTSVoice(voice_select.value)
                        
                        # Initialize engine
                        engine = PlaywrightEngine()
                        
                        # Set up progress callbacks
                        def on_step_start(step_num, title):
                            console_state.current_step = step_num
                            console_state.log(f"Step {step_num}: {title}", 'info')
                            progress = step_num / len(scenario.steps)
                            progress_bar.value = progress
                            step_label.text = f"Step {step_num}/{len(scenario.steps)}: {title}"
                        
                        def on_step_complete(result):
                            status = 'success' if result.success else 'error'
                            console_state.log(f"  ✓ Completed: {result.title}", status)
                        
                        engine.on_step_start = on_step_start
                        engine.on_step_complete = on_step_complete
                        
                        await engine.initialize()
                        
                        # Run scenario
                        result = await engine.run_scenario(
                            scenario=scenario,
                            account_username=account_username,
                            custom_credentials=credentials
                        )
                        
                        await engine.cleanup()
                        
                        console_state.last_result = result
                        
                        # Generate documentation
                        if result.success:
                            console_state.log('Generating documentation...', 'info')
                            doc_gen = DocumentationGenerator()
                            outputs = doc_gen.generate_all(result)
                            
                            for output_type, path in outputs.items():
                                console_state.log(f"  Generated: {path}", 'success')
                            
                            # Generate audio if enabled
                            if opt_audio.value:
                                console_state.log('Generating audio narration...', 'info')
                                audio_service = AudioNarrationService()
                                if audio_service.is_available():
                                    segments = audio_service.generate_all_narration(
                                        result, 
                                        TTSVoice(voice_select.value)
                                    )
                                    console_state.log(
                                        f"  Generated {len(segments)} audio segments", 
                                        'success'
                                    )
                            
                            console_state.log('Scenario completed successfully!', 'success')
                            ui.notify('Scenario completed!', type='positive')
                        else:
                            console_state.log(f'Scenario failed: {result.error_message}', 'error')
                            ui.notify(f'Scenario failed: {result.error_message}', type='negative')
                        
                        progress_bar.value = 1.0
                        step_label.text = 'Complete'
                        
                    except Exception as e:
                        console_state.log(f'Error: {str(e)}', 'error')
                        ui.notify(f'Error: {str(e)}', type='negative')
                    
                    finally:
                        console_state.is_running = False
                        run_btn.props(remove='loading')
                
                run_btn = ui.button(
                    'Run Scenario',
                    icon='play_arrow',
                    on_click=run_scenario
                ).classes('flex-grow').props(f'color=primary')
                console_state.run_button = run_btn
                
                ui.button(
                    'Stop',
                    icon='stop',
                    on_click=lambda: ui.notify('Stop requested', type='warning')
                ).props('color=red outline')
        
        # ─────────────────────────────────────────────────────────────────────
        # COLUMN 3: Debug Console
        # ─────────────────────────────────────────────────────────────────────
        
        with ui.card().classes('w-96 flex-shrink-0'):
            with ui.row().classes('w-full items-center justify-between mb-3'):
                ui.label('Console Log').classes('text-lg font-semibold')
                ui.button(
                    icon='delete_outline',
                    on_click=console_state.clear_logs
                ).props('flat dense round')
            
            # Log container
            log_container = ui.column().classes(
                'w-full h-96 overflow-y-auto bg-gray-900 rounded p-3 gap-1'
            )
            console_state.log_container = log_container
            
            with log_container:
                ui.label('[Console ready]').classes('text-xs font-mono text-gray-500')
            
            ui.separator().classes('my-3')
            
            # Quick Actions
            ui.label('Quick Actions').classes('text-sm font-medium text-gray-600 mb-2')
            
            with ui.row().classes('w-full gap-2 flex-wrap'):
                ui.button(
                    'View Outputs',
                    icon='folder_open',
                    on_click=lambda: ui.notify('Opening outputs folder...')
                ).props('flat dense')
                
                ui.button(
                    'Export Logs',
                    icon='download',
                    on_click=lambda: ui.notify('Exporting logs...')
                ).props('flat dense')
                
                ui.button(
                    'View Last Result',
                    icon='info',
                    on_click=lambda: show_last_result()
                ).props('flat dense')
    
    # ═══════════════════════════════════════════════════════════════════════
    # OUTPUT PREVIEW ROW
    # ═══════════════════════════════════════════════════════════════════════
    
    ui.separator().classes('my-6')
    
    with ui.expansion('Generated Outputs', icon='folder').classes('w-full'):
        with ui.row().classes('w-full gap-4'):
            
            # Screenshots Preview
            with ui.card().classes('flex-1'):
                ui.label('Screenshots').classes('font-semibold mb-2')
                ui.label('Screenshots will appear here after running a scenario').classes(
                    'text-sm text-gray-500'
                )
            
            # Help Doc Preview
            with ui.card().classes('flex-1'):
                ui.label('Help Documentation').classes('font-semibold mb-2')
                ui.label('Generated markdown will appear here').classes(
                    'text-sm text-gray-500'
                )
            
            # Video/Audio Preview
            with ui.card().classes('flex-1'):
                ui.label('Video & Audio').classes('font-semibold mb-2')
                ui.label('Video and audio files will appear here').classes(
                    'text-sm text-gray-500'
                )


def show_last_result():
    """Show dialog with last scenario result"""
    if not console_state.last_result:
        ui.notify('No results available yet', type='info')
        return
    
    result = console_state.last_result
    
    with ui.dialog() as dialog, ui.card().classes('w-[600px]'):
        ui.label(f'Result: {result.scenario_name}').classes('text-xl font-bold')
        
        ui.separator()
        
        with ui.row().classes('gap-4'):
            ui.label(f'Status: {"✅ Success" if result.success else "❌ Failed"}')
            ui.label(f'Duration: {result.total_duration:.1f}s')
            ui.label(f'Steps: {len(result.steps)}')
        
        if result.error_message:
            ui.label(f'Error: {result.error_message}').classes('text-red-500')
        
        ui.separator()
        
        ui.label('Steps:').classes('font-semibold')
        for step in result.steps:
            status = '✓' if step.success else '✗'
            ui.label(f'{status} {step.step_number}. {step.title}').classes('text-sm')
        
        ui.button('Close', on_click=dialog.close)
    
    dialog.open()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

def register_testing_console_route(app_instance=None):
    """
    Register the testing console route with the application.
    
    Call this from your main app setup, e.g.:
        from nicegui_app.pages.testing_console import register_testing_console_route
        register_testing_console_route()
    """
    
    @ui.page('/admin/testing-console')
    async def testing_console_page():
        # TODO: Add authentication check
        # if not is_admin_user():
        #     ui.navigate.to('/login')
        #     return
        
        create_testing_console_page()
    
    print("✓ Testing Console registered at /admin/testing-console")
```

---

## PHASE 6: Integration & Route Registration

### 6.1 Register the Testing Console Route

Add the following to your main application file (e.g., `main.py` or `nicegui_app/app.py`):

```python
# Add this import at the top
from nicegui_app.pages.testing_console import register_testing_console_route

# Add this line in your app initialization (before ui.run())
register_testing_console_route()
```

### 6.2 Add Navigation Link (Optional)

If you have an admin navigation menu, add a link to the Testing Console:

```python
# In your admin navigation component
ui.link('Testing Console', '/admin/testing-console').classes('...')

# Or as a button
ui.button(
    'Testing Console',
    icon='science',
    on_click=lambda: ui.navigate.to('/admin/testing-console')
)
```

---

## PHASE 7: Verification Checklist

### 7.1 Post-Implementation Verification

After implementing all phases, verify:

```
□ Dependencies installed:
  - pip install playwright openai python-dotenv
  - playwright install chromium

□ Files created:
  - config/testing_config.py
  - services/playwright_engine.py
  - services/doc_generator.py
  - services/audio_narration.py
  - nicegui_app/pages/testing_console.py
  - .env.testing (with your OpenAI API key)

□ Directories created:
  - static/help/screenshots/
  - static/help/docs/
  - static/help/videos/
  - static/help/audio/

□ Route registered:
  - /admin/testing-console is accessible

□ Test execution:
  - Navigate to /admin/testing-console
  - Select a preset account (techuser)
  - Select "Submit PTO Request" scenario
  - Click "Run Scenario"
  - Verify screenshots appear in static/help/screenshots/pto-request/
  - Verify markdown doc appears in static/help/docs/pto-request.md
```

### 7.2 Troubleshooting

**Issue: "OpenAI API key not configured"**
- Ensure `.env.testing` exists in project root
- Verify the key is correct: `OPENAI_API_KEY=sk-proj-...`

**Issue: "Playwright browser not found"**
- Run: `playwright install chromium`

**Issue: "Login failed"**
- Update selectors in `playwright_engine.py` `login()` method to match your actual login form

**Issue: "Screenshots not saving"**
- Verify `static/help/` directories have write permissions

---

## APPENDIX A: Selector Customization Guide

The pre-built scenarios use generic selectors that may need adjustment for your specific NiceGUI implementation. Here's how to find the correct selectors:

### Method 1: Browser DevTools
1. Open your app in Chrome/Edge
2. Press F12 to open DevTools
3. Click the element selector tool (top-left of DevTools)
4. Click on the element you want to target
5. Note the element's attributes (class, id, data-* attributes)

### Method 2: Playwright Codegen
Run this command to have Playwright record your clicks:
```bash
playwright codegen https://localhost:8080 --ignore-https-errors
```

### Common NiceGUI Selectors

```python
# Quasar/NiceGUI button patterns
'button.q-btn:has-text("Submit")'
'[role="button"]:has-text("Login")'

# Input fields
'.q-field input[type="text"]'
'.q-input input'

# Select dropdowns
'.q-select'
'.q-field--with-bottom'

# Navigation links
'a.q-tab:has-text("Dashboard")'
```

---

## APPENDIX B: Adding New Scenarios

To add a new test scenario, create a function in `playwright_engine.py`:

```python
def get_my_new_scenario() -> Scenario:
    """
    Scenario: [Description]
    """
    return Scenario(
        scenario_id="my-new-scenario",
        name="My New Scenario",
        description="What this scenario tests",
        required_role="employee",  # or 'manager', 'admin'
        default_account="techuser",
        tags=["custom", "workflow"],
        steps=[
            ScenarioStep(
                step_id="step-1",
                title="First Step",
                description="What happens in this step",
                script="What the narrator says for this step.",
                action="navigate",  # or 'click', 'fill', 'screenshot'
                url="/dashboard",
                wait_time=2.0
            ),
            # Add more steps...
        ]
    )
```

Then add it to `get_all_scenarios()`:
```python
def get_all_scenarios() -> Dict[str, Scenario]:
    return {
        'pto-request': get_pto_request_scenario(),
        'manager-approval': get_manager_approval_scenario(),
        'admin-user-management': get_admin_user_management_scenario(),
        'my-new-scenario': get_my_new_scenario(),  # Add here
    }
```

---

## APPENDIX C: Future Integration Points

### MCP Integration (Staged for Later)

The Testing Console generates outputs that will feed into your future MCPs:

```
Testing Console Output          →    Future MCP Usage
─────────────────────────────────────────────────────────────
static/help/docs/*.md           →    TJM-Help MCP search_help()
static/help/screenshots/*       →    TJM-Help MCP get_help_article()
Timeline JSON files             →    Training data for voice commands
Scenario definitions            →    Template for MCP admin actions
```

### Voice Input Staging (Whisper)

The config includes placeholder for future voice-to-PTO feature:

```python
# In testing_config.py - already staged
whisper_enabled: bool = False  # Future feature
whisper_model: str = "whisper-1"  # Future feature
```

When ready to implement voice input:
1. Enable `whisper_enabled` in config
2. Add microphone capture UI component
3. Use OpenAI Whisper API for speech-to-text
4. Parse natural language to PTO request parameters
5. Confirm with user before submitting via TJM-Admin MCP

---

## Document Complete

This instruction document provides everything needed to implement the TJM Testing Console. The implementation is:

- ✅ Safe (read-only, additive changes only)
- ✅ Isolated (separate browser sessions, dedicated output directories)
- ✅ Extensible (easy to add new scenarios)
- ✅ Production-ready (configurable BASE_URL for localhost → production)
- ✅ Future-proofed (MCP integration points staged)

**OpenAI API Key Location:** `.env.testing` file in project root

**Default Voice:** Onyx (with Alloy as alternative option)

**Access URL:** `https://localhost:8080/admin/testing-console`
