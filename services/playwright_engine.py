"""
PTO Central - Playwright Automation Engine
Handles browser automation for testing and documentation generation.

This service:
- Manages browser sessions for different test users
- Captures screenshots at defined steps
- Records video of test scenarios
- Collects timing metadata for audio synchronization

NOTE: Uses synchronous Playwright API to avoid Windows asyncio subprocess issues.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import json
import time
import threading
import concurrent.futures

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

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
    element_bbox: Optional[Dict[str, float]] = None  # {x, y, width, height} of interacted element
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
            'element_bbox': self.element_bbox,
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
class SetupAction:
    """
    Pre-scenario setup action to create required test data.
    Runs before the browser automation starts.
    """
    action_type: str  # 'create_pto_request', 'create_user', 'create_carryover_request', etc.
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""  # Human-readable description of what this does


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

    # Professional screenshot options
    highlight_element: bool = True  # Highlight the target element before screenshot
    highlight_style: str = "default"  # "default", "pulse", "spotlight", "error", "success"
    callout_text: Optional[str] = None  # Optional callout text to display
    callout_position: str = "top-right"  # "top-left", "top-right", "bottom-left", "bottom-right"
    focus_element: bool = True  # Scroll element into view and center it


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
    # Setup actions run before browser automation to create required test data
    setup_actions: List[SetupAction] = field(default_factory=list)
    # Whether to clean up test data after scenario completes
    cleanup_after: bool = True


class PlaywrightEngine:
    """
    Browser automation engine for testing and documentation.
    Uses synchronous API run in a thread pool to avoid Windows asyncio issues.

    Usage:
        engine = PlaywrightEngine()
        result = engine.run_scenario_sync(scenario, 'ptouser01')
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

    def _run_in_thread(self, scenario: Scenario, account: TestAccount) -> ScenarioResult:
        """Run the scenario in a separate thread with its own Playwright instance"""
        print(f"[PLAYWRIGHT] Starting scenario: {scenario.name}")
        print(f"[PLAYWRIGHT] Account: {account.username}")
        self.config.ensure_directories()

        # Initialize result tracking
        self._current_result = ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            scenario_description=scenario.description,
            user_account=account.username,
            started_at=datetime.now()
        )

        try:
            print("[PLAYWRIGHT] Launching sync_playwright()...")
            # ════════════════════════════════════════════════════════════════════
            # DEBUG: Print ALL critical settings at runtime to verify configuration
            # ════════════════════════════════════════════════════════════════════
            print(f"\n{'='*60}")
            print("PLAYWRIGHT CONFIGURATION (RUNTIME VALUES)")
            print(f"{'='*60}")
            print(f"  headless:        {self.config.headless}")
            print(f"  viewport:        {self.config.viewport_width}x{self.config.viewport_height}")
            print(f"  video_size:      {self.config.video_width}x{self.config.video_height}")
            print(f"  video_enabled:   {self.config.video_enabled}")
            print(f"  slow_mo:         {self.config.slow_mo}ms")
            print(f"  base_url:        {self.config.base_url}")
            print(f"{'='*60}\n")

            if not self.config.headless:
                print("⚠️  WARNING: headless=False - video may be clipped by monitor size!")
                print("    Set headless=True in config/testing_config.py for reliable recording.")
            # ════════════════════════════════════════════════════════════════════

            with sync_playwright() as playwright:
                print("[PLAYWRIGHT] Playwright context created")
                self.playwright = playwright
                print(f"[PLAYWRIGHT] Launching chromium (headless={self.config.headless})...")
                # CRITICAL: Set window-size to match viewport to prevent clipping
                # In non-headless mode, the browser window must be at least as large as the viewport
                # Add extra space for window chrome (title bar, borders) - ~100px typically
                window_width = self.config.viewport_width + 16  # Side borders
                window_height = self.config.viewport_height + 100  # Title bar + bottom border
                self.browser = playwright.chromium.launch(
                    headless=self.config.headless,
                    slow_mo=self.config.slow_mo,
                    args=[
                        f'--window-size={window_width},{window_height}',
                        '--window-position=0,0',  # Position at top-left to maximize usable space
                    ]
                )
                print(f"[PLAYWRIGHT] Browser launched with window size {window_width}x{window_height}")

                # Video recording setup
                video_dir = None
                if self.config.generate_video and self.config.video_enabled:
                    video_dir = self.config.videos_dir / scenario.scenario_id
                    video_dir.mkdir(parents=True, exist_ok=True)

                # Create browser context
                # CRITICAL: device_scale_factor=1 forces 100% DPI rendering
                # This prevents Windows display scaling from shrinking content
                context_options = {
                    'viewport': {
                        'width': self.config.viewport_width,
                        'height': self.config.viewport_height
                    },
                    'device_scale_factor': 1,  # Force 100% DPI - fixes Windows scaling
                    'ignore_https_errors': self.config.ignore_https_errors,
                }

                if video_dir:
                    context_options['record_video_dir'] = str(video_dir)
                    context_options['record_video_size'] = {
                        'width': self.config.video_width,
                        'height': self.config.video_height
                    }

                self.context = self.browser.new_context(**context_options)
                print(f"[PLAYWRIGHT] Context created with options: {context_options}")
                self.page = self.context.new_page()
                self.page.set_default_timeout(self.config.default_timeout)
                print(f"[PLAYWRIGHT] Page created, viewport set to {self.config.viewport_width}x{self.config.viewport_height}")

                # Store cursor script for injection after each navigation
                self._cursor_script = """
                    (function() {
                        // Only run in top-level frame
                        if (window.self !== window.top) return;

                        // Remove existing cursor if any (prevents duplicates)
                        var existing = document.getElementById('pw-cursor');
                        if (existing) existing.remove();

                        // Create cursor element
                        var cursor = document.createElement('div');
                        cursor.id = 'pw-cursor';
                        cursor.style.cssText = 'position:fixed;width:30px;height:30px;background:rgba(201,162,39,0.95);border:4px solid #fff;border-radius:50%;pointer-events:none;z-index:2147483647;transform:translate(-50%,-50%);box-shadow:0 0 20px rgba(201,162,39,1),0 0 40px rgba(201,162,39,0.6),0 0 8px rgba(0,0,0,0.8);left:50%;top:50%;transition:transform 0.15s,background 0.15s;';

                        // Append to body (wait for body if needed)
                        function appendCursor() {
                            if (document.body) {
                                document.body.appendChild(cursor);
                                console.log('[CURSOR] Injected successfully');
                            } else {
                                setTimeout(appendCursor, 50);
                            }
                        }
                        appendCursor();

                        // Track mouse - use capture phase
                        window.addEventListener('mousemove', function(e) {
                            cursor.style.left = e.clientX + 'px';
                            cursor.style.top = e.clientY + 'px';
                        }, true);

                        // Click feedback
                        window.addEventListener('mousedown', function() {
                            cursor.style.transform = 'translate(-50%,-50%) scale(0.6)';
                            cursor.style.background = 'rgba(255,255,255,0.95)';
                        }, true);
                        window.addEventListener('mouseup', function() {
                            cursor.style.transform = 'translate(-50%,-50%) scale(1)';
                            cursor.style.background = 'rgba(201,162,39,0.95)';
                        }, true);
                    })();
                """

                # Helper to inject cursor (only if cursor animation is enabled)
                def inject_cursor():
                    if not self.config.cursor_animation_enabled:
                        return
                    try:
                        self.page.evaluate(self._cursor_script)
                    except Exception as e:
                        print(f"[CURSOR] Injection failed: {e}")

                # Inject on every navigation (only if enabled)
                if self.config.cursor_animation_enabled:
                    self.page.on("load", lambda: inject_cursor())
                    self.page.on("domcontentloaded", lambda: inject_cursor())

                # Login
                login_success = self._login(account)
                if not login_success:
                    raise Exception(f"Failed to login as {account.username}")

                # Explicitly inject cursor after login (dashboard is now loaded)
                if self.config.cursor_animation_enabled:
                    time.sleep(1)  # Wait for page to stabilize
                    inject_cursor()

                    # Verify cursor was injected
                    cursor_exists = self.page.evaluate("!!document.getElementById('pw-cursor')")
                    print(f"[CURSOR] Injection verified: {cursor_exists}")

                # Activate cursor by moving mouse to center of viewport
                # This triggers the mousemove listener and makes cursor visible
                if self.config.cursor_animation_enabled:
                    try:
                        center_x = self.config.viewport_width / 2
                        center_y = self.config.viewport_height / 2
                        self.page.mouse.move(center_x, center_y, steps=20)
                        time.sleep(0.5)  # Let cursor settle
                        print(f"[CURSOR] Mouse moved to center ({center_x}, {center_y})")
                    except Exception as e:
                        print(f"[CURSOR] Mouse move failed: {e}")

                # Record scenario start time
                self._scenario_start_time = time.time()

                # Execute each step
                for i, step in enumerate(scenario.steps, 1):
                    step_result = self._execute_step(step, i, scenario.scenario_id)
                    self._current_result.steps.append(step_result)

                    if not step_result.success:
                        self._current_result.success = False
                        self._current_result.error_message = f"Step {i} failed: {step_result.error_message}"
                        break

                # Finalize
                self._current_result.completed_at = datetime.now()
                self._current_result.total_duration = time.time() - self._scenario_start_time

                # Get video path if recorded
                if video_dir and self.page.video:
                    video_path = self.page.video.path()
                    if video_path:
                        self._current_result.video_path = Path(video_path)

                # Close context
                self.context.close()
                self.browser.close()

        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[PLAYWRIGHT ERROR] {error_detail}")
            self._current_result.success = False
            self._current_result.error_message = str(e)
            self._current_result.completed_at = datetime.now()

        # Callback
        if self.on_scenario_complete:
            self.on_scenario_complete(self._current_result)

        return self._current_result

    def _login(self, account: TestAccount) -> bool:
        """Log into the application with the given account."""
        try:
            # Navigate to the login page with longer timeout
            print(f"[LOGIN] Navigating to {self.config.base_url}...")
            self.page.goto(self.config.base_url, wait_until='domcontentloaded', timeout=60000)
            print(f"[LOGIN] Navigation complete, URL: {self.page.url}")

            # Wait a moment for NiceGUI to initialize
            print("[LOGIN] Waiting for NiceGUI to initialize...")
            time.sleep(3)

            # Wait for login form to be visible - use Quasar input selector
            # NiceGUI/Quasar inputs have class q-field__native
            print("[LOGIN] Waiting for login form...")
            self.page.wait_for_selector(
                '.q-field__native, input[type="text"], input[aria-label*="user" i]',
                timeout=20000
            )
            print("[LOGIN] Login form found")

            # Fill username - Quasar inputs are the first q-field__native element
            print(f"[LOGIN] Filling username: {account.username}")
            username_input = self.page.locator('.q-field__native').first
            username_input.fill(account.username)
            print("[LOGIN] Username filled")

            # Fill password - second q-field__native or type=password
            print("[LOGIN] Filling password...")
            password_input = self.page.locator('input[type="password"], .q-field__native >> nth=1').first
            password_input.fill(account.password)
            print("[LOGIN] Password filled")

            # Click login button
            print("[LOGIN] Clicking login button...")
            login_button = self.page.locator(
                'button:has-text("Login"), button:has-text("Sign In"), button[type="submit"]'
            ).first
            login_button.click()
            print("[LOGIN] Login button clicked")

            # Wait for navigation to complete
            print("[LOGIN] Waiting for navigation...")
            self.page.wait_for_load_state('domcontentloaded', timeout=30000)

            # Brief wait for any redirects
            time.sleep(2)
            print(f"[LOGIN] Login completed successfully, URL: {self.page.url}")

            return True

        except Exception as e:
            print(f"[LOGIN ERROR] Login failed for {account.username}: {e}")
            # Try to capture current state for debugging
            try:
                print(f"[LOGIN ERROR] Current URL: {self.page.url}")
                print(f"[LOGIN ERROR] Page title: {self.page.title()}")
            except:
                pass
            return False

    def _execute_step(self, step: ScenarioStep, step_number: int, scenario_id: str) -> StepResult:
        """Execute a single scenario step with professional highlighting"""
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
            # Capture element bounding box before action (for video effects)
            if step.selector:
                try:
                    locator = self.page.locator(step.selector).first
                    if locator.count() > 0:
                        bbox = locator.bounding_box()
                        if bbox:
                            result.element_bbox = {
                                'x': bbox['x'],
                                'y': bbox['y'],
                                'width': bbox['width'],
                                'height': bbox['height']
                            }
                except Exception:
                    pass  # Element may not be visible yet

            # Execute the action
            if step.action == 'navigate':
                url = step.url or self.config.base_url
                self.page.goto(url, wait_until='domcontentloaded')
                time.sleep(1)  # Allow NiceGUI to render

            elif step.action == 'click':
                if step.selector:
                    # Focus and highlight element before clicking
                    if step.focus_element:
                        self._focus_element(step.selector)

                    # Smooth mouse movement to element center (for visible cursor in video)
                    if self.config.cursor_animation_enabled:
                        try:
                            locator = self.page.locator(step.selector).first
                            if locator.count() > 0:
                                bbox = locator.bounding_box()
                                if bbox:
                                    # Calculate element center
                                    center_x = bbox['x'] + bbox['width'] / 2
                                    center_y = bbox['y'] + bbox['height'] / 2
                                    # Move mouse smoothly to center (50 interpolated steps)
                                    self.page.mouse.move(center_x, center_y, steps=50)
                                    print(f"[CURSOR] → Click target ({center_x:.0f}, {center_y:.0f})")
                                    time.sleep(0.3)  # Pause so viewer sees cursor arrive
                        except Exception as e:
                            print(f"[CURSOR] Mouse move failed: {e}")

                    self.page.click(step.selector)
                    time.sleep(1)  # Allow page to update
                    # Re-capture bbox after click in case element moved
                    try:
                        locator = self.page.locator(step.selector).first
                        if locator.count() > 0:
                            bbox = locator.bounding_box()
                            if bbox:
                                result.element_bbox = {
                                    'x': bbox['x'],
                                    'y': bbox['y'],
                                    'width': bbox['width'],
                                    'height': bbox['height']
                                }
                    except Exception:
                        pass

            elif step.action == 'fill':
                if step.selector and step.value is not None:
                    if step.focus_element:
                        self._focus_element(step.selector)

                    # Smooth mouse movement to input field
                    if self.config.cursor_animation_enabled:
                        try:
                            locator = self.page.locator(step.selector).first
                            if locator.count() > 0:
                                bbox = locator.bounding_box()
                                if bbox:
                                    center_x = bbox['x'] + bbox['width'] / 2
                                    center_y = bbox['y'] + bbox['height'] / 2
                                    self.page.mouse.move(center_x, center_y, steps=50)
                                    print(f"[CURSOR] → Fill target ({center_x:.0f}, {center_y:.0f})")
                                    time.sleep(0.3)
                        except Exception as e:
                            print(f"[CURSOR] Mouse move failed: {e}")

                    self.page.fill(step.selector, step.value)

            elif step.action == 'select':
                if step.selector and step.value:
                    if step.focus_element:
                        self._focus_element(step.selector)

                    # Smooth mouse movement to select field
                    if self.config.cursor_animation_enabled:
                        try:
                            locator = self.page.locator(step.selector).first
                            if locator.count() > 0:
                                bbox = locator.bounding_box()
                                if bbox:
                                    center_x = bbox['x'] + bbox['width'] / 2
                                    center_y = bbox['y'] + bbox['height'] / 2
                                    self.page.mouse.move(center_x, center_y, steps=50)
                                    print(f"[CURSOR] → Select target ({center_x:.0f}, {center_y:.0f})")
                                    time.sleep(0.3)
                        except Exception as e:
                            print(f"[CURSOR] Mouse move failed: {e}")

                    self.page.select_option(step.selector, step.value)

            elif step.action == 'wait':
                time.sleep(step.wait_time)

            elif step.action == 'press_key':
                # Press a keyboard key (e.g., Escape, Enter, Tab)
                key = step.value or 'Escape'
                self.page.keyboard.press(key)
                time.sleep(0.5)

            elif step.action == 'screenshot':
                # Scroll to element if specified (critical for capturing full page sections)
                if step.selector and step.focus_element:
                    self._focus_element(step.selector)
                    time.sleep(0.5)  # Wait for scroll animation to complete

            # Wait after action
            if step.wait_time > 0:
                time.sleep(step.wait_time)

            # Take screenshot if enabled (with professional highlighting)
            if step.screenshot and self.config.generate_screenshots:
                screenshot_dir = self.config.screenshots_dir / scenario_id
                screenshot_dir.mkdir(parents=True, exist_ok=True)

                screenshot_path = screenshot_dir / f"step-{step_number:02d}-{step.step_id}.png"

                # Apply highlighting before screenshot if element exists
                if step.selector and step.highlight_element:
                    self._highlight_element(step.selector, step.highlight_style)

                # Add callout if specified
                if step.callout_text:
                    self._add_callout(step.callout_text, step.callout_position)

                # Small pause for highlight to render
                time.sleep(0.3)

                # Take the screenshot
                self.page.screenshot(path=str(screenshot_path), full_page=False)
                result.screenshot_path = screenshot_path

                # Clean up highlighting
                self._cleanup_highlights()

            result.success = True

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            # Try to cleanup highlights on error
            try:
                self._cleanup_highlights()
            except Exception:
                pass

        # Record timing
        step_end = time.time() - self._scenario_start_time
        result.timestamp_end = step_end
        result.duration = step_end - step_start

        # Callback
        if self.on_step_complete:
            self.on_step_complete(result)

        return result

    def _focus_element(self, selector: str):
        """Scroll element into view and center it on screen using Playwright locator"""
        try:
            # Use Playwright's locator which supports :has-text() and other special selectors
            locator = self.page.locator(selector).first
            if locator.count() > 0:
                locator.scroll_into_view_if_needed()
                time.sleep(0.3)
        except Exception as e:
            # Fallback to JavaScript for simple CSS selectors
            try:
                self.page.evaluate(f"""
                    (function() {{
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            element.scrollIntoView({{ behavior: 'instant', block: 'center', inline: 'center' }});
                        }}
                    }})();
                """)
                time.sleep(0.2)
            except Exception:
                pass  # Element might not exist yet

    def _highlight_element(self, selector: str, style: str = "default"):
        """Inject CSS to highlight an element before screenshot"""
        styles = {
            "default": """
                element.style.outline = '4px solid #C9A227';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(201, 162, 39, 0.5)';
                element.style.transition = 'all 0.2s ease';
            """,
            "pulse": """
                element.style.animation = 'tjm-pulse 1s infinite';
                element.style.outline = '3px solid #C9A227';
                element.style.outlineOffset = '2px';

                if (!document.getElementById('tjm-pulse-style')) {
                    const style = document.createElement('style');
                    style.id = 'tjm-pulse-style';
                    style.textContent = `
                        @keyframes tjm-pulse {
                            0% { box-shadow: 0 0 0 0 rgba(201, 162, 39, 0.7); }
                            70% { box-shadow: 0 0 0 15px rgba(201, 162, 39, 0); }
                            100% { box-shadow: 0 0 0 0 rgba(201, 162, 39, 0); }
                        }
                    `;
                    document.head.appendChild(style);
                }
            """,
            "spotlight": """
                if (!document.getElementById('tjm-spotlight-overlay')) {
                    const overlay = document.createElement('div');
                    overlay.id = 'tjm-spotlight-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.6);
                        z-index: 9998;
                        pointer-events: none;
                    `;
                    document.body.appendChild(overlay);
                }
                element.style.position = 'relative';
                element.style.zIndex = '9999';
                element.style.boxShadow = '0 0 0 4px #C9A227, 0 0 40px rgba(201, 162, 39, 0.8)';
            """,
            "error": """
                element.style.outline = '4px solid #EF4444';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.5)';
            """,
            "success": """
                element.style.outline = '4px solid #22C55E';
                element.style.outlineOffset = '4px';
                element.style.boxShadow = '0 0 20px rgba(34, 197, 94, 0.5)';
            """
        }

        style_code = styles.get(style, styles["default"])

        try:
            # Use Playwright locator to get the element handle, then evaluate on it
            locator = self.page.locator(selector).first
            if locator.count() > 0:
                locator.evaluate(f"""
                    (element) => {{
                        {style_code}
                        element.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                    }}
                """)
        except Exception:
            # Fallback to querySelector for simple selectors
            try:
                self.page.evaluate(f"""
                    (function() {{
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            {style_code}
                            element.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                        }}
                    }})();
                """)
            except Exception:
                pass  # Element might not exist

    def _add_callout(self, text: str, position: str = "top-right"):
        """Add a floating callout/tooltip to the page"""
        positions = {
            "top-left": "top: 20px; left: 20px;",
            "top-right": "top: 20px; right: 20px;",
            "bottom-left": "bottom: 20px; left: 20px;",
            "bottom-right": "bottom: 20px; right: 20px;",
        }
        pos_style = positions.get(position, positions["top-right"])

        # Escape single quotes in text
        safe_text = text.replace("'", "\\'")

        try:
            self.page.evaluate(f"""
                (function() {{
                    const existing = document.getElementById('tjm-callout');
                    if (existing) existing.remove();

                    const callout = document.createElement('div');
                    callout.id = 'tjm-callout';
                    callout.textContent = '{safe_text}';
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
                    `;
                    document.body.appendChild(callout);
                }})();
            """)
        except Exception:
            pass

    def _cleanup_highlights(self):
        """Remove all highlighting effects from the page"""
        try:
            self.page.evaluate("""
                (function() {
                    // Remove spotlight overlay
                    const overlay = document.getElementById('tjm-spotlight-overlay');
                    if (overlay) overlay.remove();

                    // Remove callout
                    const callout = document.getElementById('tjm-callout');
                    if (callout) callout.remove();

                    // Remove pulse animation style
                    const pulseStyle = document.getElementById('tjm-pulse-style');
                    if (pulseStyle) pulseStyle.remove();

                    // Reset all highlighted elements
                    document.querySelectorAll('[style*="outline"], [style*="box-shadow"]').forEach(el => {
                        el.style.outline = '';
                        el.style.outlineOffset = '';
                        el.style.boxShadow = '';
                        el.style.animation = '';
                        if (el.style.zIndex === '9999') el.style.zIndex = '';
                    });
                })();
            """)
        except Exception:
            pass

    def run_scenario_sync(
        self,
        scenario: Scenario,
        account_username: str = None,
        custom_credentials: Dict[str, str] = None
    ) -> ScenarioResult:
        """
        Run a complete test scenario synchronously in a thread pool.

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

        # Run in thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_in_thread, scenario, account)
            return future.result()


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
        default_account="ptouser01",
        tags=["employee", "pto", "request", "core-workflow"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access PTO Central and log in",
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
                title="Click Request Time Off",
                description="Click the Request Time Off button to start a PTO request",
                script="To submit a new request, click the Request Time Off button.",
                action="click",
                selector="button:has-text('Request Time Off'), button:has-text('Submit Time Off'), button:has-text('Time Off')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="request-form",
                title="PTO Request Form",
                description="The request form allows you to specify leave type and dates",
                script="The request form appears. Here you'll select your leave type and choose your dates.",
                action="screenshot",
                selector=":has-text('Select Leave Type')",  # Scroll to top of form
                wait_time=1.5,
                focus_element=True
            ),
            ScenarioStep(
                step_id="select-leave-type",
                title="Select Leave Type",
                description="Choose the type of leave (vacation, sick, personal)",
                script="First, select your leave type. Options include vacation, sick time, and personal days.",
                action="click",
                selector=".border-l-4.border-blue-500, :has-text('VACATION')",  # Click vacation card
                wait_time=1.5,
                focus_element=True,
                highlight_element=True
            ),
            ScenarioStep(
                step_id="select-dates",
                title="Select Dates",
                description="Choose start and end dates for your time off",
                script="Next, select your start and end dates using the calendar picker.",
                action="screenshot",
                selector=":has-text('Select Date')",  # Scroll to date section
                wait_time=1.5,
                focus_element=True
            ),
            ScenarioStep(
                step_id="add-notes",
                title="Add Notes (Optional)",
                description="Add private notes for your own reference",
                script="You can add private notes for your own reference. These notes are only visible to you, not your manager.",
                action="screenshot",
                selector=":has-text('Notes (optional)'), textarea",  # Scroll to notes section
                wait_time=1.5,
                focus_element=True
            ),
            ScenarioStep(
                step_id="submit-request",
                title="Submit Request",
                description="Review and submit the request",
                script="Review your request details, then click Submit to send it to your manager for approval.",
                action="screenshot",
                selector="button:has-text('Submit Request')",  # Scroll to submit button
                wait_time=2.0,
                focus_element=True,
                highlight_element=True
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
    Requires: A pending PTO request from a team member
    """
    return Scenario(
        scenario_id="manager-approval",
        name="Manager Approval Workflow",
        description="Manager reviews pending requests and approves or denies them",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "approval", "workflow"],
        # Setup: Create a pending request for the manager to approve
        setup_actions=[
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'vacation',
                    'days': 2,
                    'status': 'pending',
                    'start_offset': 14  # Two weeks from now
                },
                description="Create pending vacation request from employee"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Manager logs into the application",
                script="Welcome to PTO Central. As a manager, you'll review and approve time-off requests from your team. Let's log in.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="Manager dashboard shows pending approvals count",
                script="Your manager dashboard shows you have a pending vacation request awaiting your review. Notice the pending count indicator.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-approvals",
                title="Access Pending Requests",
                description="Navigate to the pending requests section",
                script="Click on the Pending Requests section to see the full details of requests awaiting your decision.",
                action="click",
                selector="button:has-text('View All'), button:has-text('Pending'), .cursor-pointer:has-text('Pending')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approval-queue",
                title="View Pending Requests",
                description="List of all pending PTO requests from team members",
                script="Here's the approval queue. You can see a two-day vacation request from a team member scheduled for two weeks from now.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-request",
                title="Select Request to Review",
                description="Click on a request to view details",
                script="Click on the request to review the complete details, including the employee's current balance and team coverage.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-details",
                title="Review Request Details",
                description="Review employee details, dates, and team coverage",
                script="Review the employee's available balance, the requested dates, and check if there are any coverage conflicts with other team members.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approve-action",
                title="Approve or Deny",
                description="Make approval decision",
                script="Once you've reviewed the request, click Approve to grant the time off, or Deny if there's a coverage issue.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="confirmation",
                title="Decision Confirmed",
                description="Confirmation of the approval action",
                script="Your decision has been recorded. The employee receives an automatic email notification with your response.",
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
        default_account="ptoadmin",
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
                title="Access Employee Management",
                description="Navigate to employee management section",
                script="Click on Manage Employees to view and manage employee accounts.",
                action="click",
                selector="button:has-text('Manage Employees'), button:has-text('Employees'), a:has-text('Employees')",
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


def get_calendar_navigation_scenario() -> Scenario:
    """
    Scenario: Navigate and use the PTO calendar
    """
    return Scenario(
        scenario_id="calendar-navigation",
        name="Calendar Navigation",
        description="Learn how to view, navigate, and understand the PTO calendar",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "calendar", "navigation", "tutorial"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the TJM Time Calendar",
                script="Welcome to TJM Time Calendar. Log in with your credentials to access the calendar.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="open-calendar",
                title="Open Calendar View",
                description="Navigate to the calendar page",
                script="Click on Calendar in the navigation to view the full calendar interface.",
                action="click",
                selector="a:has-text('Calendar'), button:has-text('Calendar'), .q-tab:has-text('Calendar')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="calendar-overview",
                title="Calendar Overview",
                description="The main calendar view showing all PTO events",
                script="The calendar displays all approved time off. Your requests appear in blue, and team members are shown in different colors.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="month-navigation",
                title="Navigate Between Months",
                description="Use the arrows to move between months",
                script="Use the left and right arrows to navigate between months. The current month is highlighted.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-next-month",
                title="Go to Next Month",
                description="Click to advance to the next month",
                script="Click the forward arrow to see upcoming scheduled time off.",
                action="click",
                selector="button:has-text('chevron_right'), button[aria-label='Next month'], .q-btn:has(i:has-text('chevron_right'))",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="view-event-details",
                title="View Event Details",
                description="Click on a calendar event to see details",
                script="Click on any event in the calendar to see the full details including dates and status.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="today-button",
                title="Return to Today",
                description="Click Today to return to current month",
                script="Click the Today button to quickly return to the current month view.",
                action="click",
                selector="button:has-text('Today'), button:has-text('today')",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="calendar-legend",
                title="Understanding the Legend",
                description="Color coding and legend explanation",
                script="The legend shows color codes for different leave types and statuses. Approved appears solid, pending appears faded.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_filter_requests_scenario() -> Scenario:
    """
    Scenario: Filter PTO requests by type and status
    Requires: Multiple historical requests to filter
    """
    return Scenario(
        scenario_id="filter-requests",
        name="Filter PTO Requests",
        description="Learn how to filter and search PTO requests by type, status, and date range",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "filter", "search", "requests"],
        # Setup: Create multiple requests with different types and statuses to demonstrate filtering
        setup_actions=[
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'vacation',
                    'days': 3,
                    'status': 'approved',
                    'start_offset': -30  # Past request
                },
                description="Create past approved vacation"
            ),
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'sick',
                    'days': 1,
                    'status': 'approved',
                    'start_offset': -14
                },
                description="Create past approved sick day"
            ),
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'vacation',
                    'days': 2,
                    'status': 'pending',
                    'start_offset': 21
                },
                description="Create future pending vacation"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the PTO Central",
                script="Welcome to PTO Central. Let's learn how to filter and search through your request history.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="open-requests",
                title="Open My Requests",
                description="Navigate to the requests page",
                script="Click on My Requests to view your complete request history.",
                action="click",
                selector="a:has-text('My Requests'), button:has-text('My Requests'), .cursor-pointer:has-text('Requests')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="requests-list",
                title="Request History",
                description="View all your PTO requests",
                script="Here's your request history. You can see a mix of vacation, sick, and other leave types with different statuses.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-section",
                title="Filter Controls",
                description="The filtering options at the top",
                script="The filter controls at the top let you quickly find specific requests. Let's try filtering by leave type.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-type",
                title="Filter by Leave Type",
                description="Select a specific leave type to filter",
                script="Click the Leave Type dropdown to see your options. You can filter by Vacation, Sick, Personal, or other leave types.",
                action="click",
                selector=".q-select:has-text('Type'), .q-select:has-text('Leave'), select[name*='type']",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-vacation",
                title="Select Vacation Type",
                description="Choose Vacation to see only vacation requests",
                script="Select Vacation to filter the list. This is helpful when you want to see only your vacation days.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filtered-results",
                title="Filtered Results",
                description="View the filtered request list",
                script="Now you see only vacation requests. The count at the top updates to show how many match your filter.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-status",
                title="Filter by Status",
                description="Add status filter to narrow further",
                script="You can combine filters. Add a status filter to see only Pending, Approved, or Denied vacation requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="clear-filters",
                title="Clear All Filters",
                description="Reset filters to see all requests",
                script="To see all requests again, click Clear or remove individual filters using the X buttons.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_team_calendar_scenario() -> Scenario:
    """
    Scenario: Manager views team calendar and coverage
    Requires: Approved and pending requests from team members to display
    """
    return Scenario(
        scenario_id="team-calendar",
        name="Team Calendar View",
        description="Manager views team calendar to check coverage and plan approvals",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "calendar", "team", "coverage"],
        # Setup: Create team requests so the calendar has data to display
        setup_actions=[
            SetupAction(
                action_type='create_team_requests',
                params={
                    'manager_username': 'ptomanager',
                    'count': 3
                },
                description="Create mix of approved and pending team requests"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Log in with manager credentials",
                script="Welcome to PTO Central. As a manager, you can view your entire team's time-off schedule in one place. Let's log in.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="View team status from dashboard",
                script="Your dashboard shows team activity at a glance. You can see several team members have upcoming time off scheduled.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-team-calendar",
                title="Open Team Calendar",
                description="Navigate to the team calendar view",
                script="Click on Team Calendar to see a visual overview of all scheduled time off for your team.",
                action="click",
                selector="a:has-text('Team Calendar'), button:has-text('Team'), .cursor-pointer:has-text('Team')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="team-calendar-view",
                title="Team Calendar Overview",
                description="View all team members' PTO on one calendar",
                script="Here's the team calendar. Notice the mix of vacation, sick, and personal time shown with different colors for each employee.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="coverage-indicator",
                title="Coverage Indicators",
                description="Check team coverage levels",
                script="Coverage indicators help you spot days when multiple team members are scheduled off. This helps prevent understaffing.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-employee",
                title="Filter by Employee",
                description="Show only specific team members",
                script="Use the employee filter to focus on specific team members' schedules when planning projects or approving requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="hover-details",
                title="View Request Details",
                description="Hover or click for request details",
                script="Click on any time-off event to see full details including the leave type, dates, and any notes the employee added.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="conflict-detection",
                title="Conflict Detection",
                description="Identify scheduling conflicts",
                script="Days highlighted in red indicate potential coverage issues. Use this to make informed approval decisions.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_reporting_scenario() -> Scenario:
    """
    Scenario: Access and use PTO reports
    """
    return Scenario(
        scenario_id="pto-reports",
        name="PTO Reporting",
        description="Learn how to access and generate PTO reports for analysis",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "reports", "analytics", "export"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Log in to access reporting features",
                script="Log in with manager or admin credentials to access the reporting dashboard.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="open-reports",
                title="Open Reports Section",
                description="Navigate to the reports page",
                script="Click on Reports in the navigation to access the reporting dashboard.",
                action="click",
                selector="a:has-text('Reports'), button:has-text('Reports'), .q-tab:has-text('Reports')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="reports-dashboard",
                title="Reports Dashboard",
                description="Overview of available reports",
                script="The reports dashboard shows various report types and quick statistics.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="utilization-report",
                title="PTO Utilization Report",
                description="View how PTO is being used across the team",
                script="The utilization report shows how much PTO has been used versus available for each team member.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-date-range",
                title="Select Date Range",
                description="Choose the reporting period",
                script="Select a date range to analyze PTO patterns over specific periods.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="department-breakdown",
                title="Department Breakdown",
                description="View PTO by department",
                script="The department breakdown shows PTO usage patterns across different teams.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="trend-charts",
                title="Usage Trends",
                description="Visual charts showing PTO trends",
                script="Charts display usage trends over time, helping identify peak vacation periods.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="export-options",
                title="Export Report",
                description="Export data for external use",
                script="Click Export to download the report as CSV or PDF for sharing or further analysis.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="balance-report",
                title="Balance Summary",
                description="View current balance status for all employees",
                script="The balance report shows everyone's current PTO balances and carryover status.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_balance_dashboard_scenario() -> Scenario:
    """
    Scenario: Understanding the employee dashboard and balances
    """
    return Scenario(
        scenario_id="balance-dashboard",
        name="Understanding Your Balances",
        description="Learn how to read and understand your PTO balances on the dashboard",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "dashboard", "balances", "tutorial"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the TJM Time Calendar",
                script="Log in to view your personal PTO dashboard and balances.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard-overview",
                title="Dashboard Overview",
                description="The main employee dashboard",
                script="Your dashboard is the home screen showing all your PTO information at a glance.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="balance-cards",
                title="Balance Cards",
                description="Understanding the balance cards",
                script="Each card shows a leave type: Available hours, Pending requests, and Used time.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="vacation-balance",
                title="Vacation Balance",
                description="Understanding vacation allocation",
                script="Your vacation balance shows total allocated days, minus used and pending requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="sick-balance",
                title="Sick Leave Balance",
                description="Sick leave accumulation",
                script="Sick leave accrues according to policy and can carry over to the next year.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="personal-balance",
                title="Personal Days",
                description="Personal day allocation",
                script="Personal days are use-it-or-lose-it and do not carry over to the next year.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="pending-section",
                title="Pending Requests",
                description="View your pending requests",
                script="The pending section shows requests awaiting manager approval.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="quick-actions",
                title="Quick Actions",
                description="Dashboard quick action buttons",
                script="Quick actions let you submit new requests or view your calendar without navigating.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="year-toggle",
                title="Year Selector",
                description="Switch between years",
                script="Use the year toggle to view balances for different years and plan ahead.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# WFH AND LEAVE TYPE RULES SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def get_wfh_request_scenario() -> Scenario:
    """
    Scenario: Employee submits a Work From Home request
    Explains WFH rules: single-day only, within 7 days, for special circumstances
    """
    return Scenario(
        scenario_id="wfh-request",
        name="Work From Home Request",
        description="Submit a WFH request for special circumstances like train delays or emergencies",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "wfh", "remote", "special-circumstances", "training"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the TJM Time Calendar",
                script="Welcome to TJM Time Calendar. Let's learn how to submit a Work From Home request for special circumstances.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="wfh-intro",
                title="Understanding WFH Requests",
                description="When to use Work From Home",
                script="Work From Home requests are designed for unexpected special circumstances only, such as train delays, weather emergencies, or home repairs. They are NOT for regular remote work scheduling.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="click-request",
                title="Start Request",
                description="Click Request Time Off",
                script="Click Request Time Off to begin. We'll select Work From Home as the leave type.",
                action="click",
                selector="button:has-text('Request Time Off'), button:has-text('Submit Time Off')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="select-wfh",
                title="Select WFH Type",
                description="Choose Work From Home from Other Leave Types",
                script="Click the Other Leave Types dropdown and select Work From Home. Notice the red color indicating this is a special request type.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="wfh-rules-display",
                title="WFH Rules",
                description="Key rules for WFH requests",
                script="Important rules for WFH: First, WFH is single-day only - you cannot request multiple days. Second, requests must be within 7 days - you cannot schedule WFH far in advance.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="select-date",
                title="Select Date",
                description="Choose the WFH date",
                script="Select a date within the next 7 days. The system will prevent you from choosing dates further out.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="reason-required",
                title="Reason Required",
                description="WFH requires a reason",
                script="Unlike other leave types, WFH REQUIRES a reason. Explain your special circumstance - for example, 'Train delays due to weather' or 'Emergency home repair appointment'.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="submit-wfh",
                title="Submit for Approval",
                description="WFH always requires manager approval",
                script="WFH requests always require manager approval. Your manager will review the reason and circumstances before approving.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="wfh-summary",
                title="WFH Summary",
                description="Key takeaways",
                script="Remember: WFH is for unexpected special circumstances only. It's single-day, within 7 days, requires a reason, and needs manager approval. For regular remote work, speak with your manager about scheduling.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_wfh_swap_scenario() -> Scenario:
    """
    Scenario: WFH Day Swap - peer-to-peer WFH day exchange

    Demonstrates how employees can swap their designated WFH days with teammates.
    This is a peer-to-peer system - no manager approval required.

    INTERACTIVE VERSION: Uses real clicks, fills, and navigation for authentic recording.
    """
    return Scenario(
        scenario_id="wfh-swap",
        name="WFH Day Swap",
        description="Exchange your WFH day with a teammate - no manager approval needed",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "wfh", "swap", "remote", "peer-to-peer", "training"],
        steps=[
            # Step 1: Show dashboard (already logged in)
            ScenarioStep(
                step_id="dashboard",
                title="Dashboard",
                description="Starting from the dashboard",
                script="Welcome to PTO Central. Let's learn how to swap your Work From Home day with a teammate.",
                action="wait",
                wait_time=2.0
            ),
            # Step 2: Click the WFH Day Swap button
            ScenarioStep(
                step_id="click-swap-button",
                title="Click WFH Swap",
                description="Click the WFH Day Swap button",
                script="From the dashboard, click the Work From Home Day Swap button. This is a peer-to-peer feature - no manager approval required.",
                action="click",
                selector="button:has-text('WFH Day Swap')",
                wait_time=3.0,
                highlight_element=True
            ),
            # Step 3: View the swap page
            ScenarioStep(
                step_id="view-swap-page",
                title="Swap Page",
                description="View the WFH Swap page",
                script="The page shows five day columns from Monday through Friday. Each column lists teammates who work from home that day. Your day is marked with a gold star.",
                action="wait",
                wait_time=3.0
            ),
            # Step 4: Click on a teammate to open dialog
            ScenarioStep(
                step_id="click-teammate",
                title="Select Teammate",
                description="Click a teammate's name",
                script="Click on a teammate's name to open the swap request dialog. Let's click on PTO Manager who works from home on Wednesday.",
                action="click",
                selector=".employee-item >> nth=0",
                wait_time=2.0
            ),
            # Step 5: View the dialog
            ScenarioStep(
                step_id="view-dialog",
                title="Swap Dialog",
                description="View the swap request dialog",
                script="The dialog shows the teammate's information and available dates. You can select from the next two occurrences of their Work From Home day.",
                action="wait",
                wait_time=2.0
            ),
            # Step 6: Type a message
            ScenarioStep(
                step_id="type-message",
                title="Enter Message",
                description="Type your swap reason",
                script="Enter your reason for the swap request. This helps your teammate understand why you need to swap days.",
                action="fill",
                selector="textarea",
                value="Hi! I have a doctor appointment on my usual WFH day. Would you be willing to swap with me this week?",
                wait_time=2.0
            ),
            # Step 7: Show the filled form
            ScenarioStep(
                step_id="review-request",
                title="Review Request",
                description="Review before sending",
                script="Review your request. When ready, click Send Request. Your teammate will receive an email notification immediately.",
                action="wait",
                wait_time=3.0
            ),
            # Step 8: Close dialog (don't actually send for demo)
            ScenarioStep(
                step_id="close-dialog",
                title="Close Dialog",
                description="Close the dialog",
                script="For this demo, we'll close the dialog. In practice, you would click Send Request to submit.",
                action="press_key",
                value="Escape",
                wait_time=2.0
            ),
            # Step 9: Show incoming requests section
            ScenarioStep(
                step_id="incoming-requests",
                title="Incoming Requests",
                description="View incoming swap requests",
                script="When teammates request a swap with you, their requests appear in the Incoming Requests section at the top. You can accept or decline with a response message.",
                action="wait",
                wait_time=3.0
            ),
            # Step 10: Summary
            ScenarioStep(
                step_id="summary",
                title="Summary",
                description="Key takeaways",
                script="Work From Home Day Swap is peer-to-peer with no manager approval. Click a teammate, enter your reason, and send your request. They have three business days to respond.",
                action="wait",
                wait_time=3.0
            )
        ],
        setup_actions=[
            # Set up WFH days for test users
            SetupAction(
                action_type='set_wfh_day',
                params={
                    'username': 'ptouser01',
                    'wfh_day': 'monday'
                },
                description="Set ptouser01 WFH day to Monday"
            ),
            SetupAction(
                action_type='set_wfh_day',
                params={
                    'username': 'ptomanager',
                    'wfh_day': 'wednesday'
                },
                description="Set ptomanager WFH day to Wednesday"
            ),
            # NOTE: Removed sample incoming swap request (Dec 22, 2025)
            # The "Proactive Weekly Limit Warning" feature now blocks users who have
            # pending/accepted swaps from initiating new swaps. For the training video
            # to demonstrate initiating a swap, the user must start with 0 swaps.
            # See: nicegui_app/pages/wfh_swap.py - limit_warning_container
        ]
    )


def get_leave_type_rules_scenario() -> Scenario:
    """
    Scenario: Understanding leave type rules
    Covers carryover, accrual, 7-day backdating, and balance limits
    """
    return Scenario(
        scenario_id="leave-type-rules",
        name="Leave Type Rules & Policies",
        description="Comprehensive guide to leave types, carryover rules, accrual requirements, and date restrictions",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "rules", "policy", "carryover", "training"],
        steps=[
            ScenarioStep(
                step_id="intro",
                title="Understanding Leave Policies",
                description="Overview of leave type rules",
                script="Welcome to TJM's Leave Policy Training. Understanding these rules helps you plan your time off effectively and avoid surprises.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="vacation-rules",
                title="Vacation Rules",
                description="Vacation allocation and limits",
                script="Vacation time is allocated based on your years of service. You can request vacation anytime in the future, and even up to 7 days in the past with manager approval.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="vacation-carryover",
                title="Vacation Carryover",
                description="Vacation does NOT automatically carry over",
                script="Important: Vacation does NOT automatically carry over to the next year. You must use it or request an exception carryover from your manager BEFORE year end.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="vacation-rollover",
                title="December Rollover",
                description="Special December to January scenario",
                script="In December, you can request January vacation that deducts from your CURRENT year balance. This 'vacation rollover' requires manager approval even for managers.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="sick-rules",
                title="Sick Leave Rules",
                description="Sick leave accrual and carryover",
                script="Sick leave automatically carries over up to the policy maximum. Unlike vacation, you don't need to request carryover - it happens automatically at year end.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="sick-accrual",
                title="Sick Leave Usage",
                description="Using sick time appropriately",
                script="Sick time is for illness, medical appointments, or caring for sick family members. You cannot overdraft sick leave - you can only use what you've accrued.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="personal-rules",
                title="Personal Day Rules",
                description="Personal days are use-it-or-lose-it",
                script="Personal days are fixed allocation per year and do NOT carry over. Any unused personal days are lost at year end. Plan to use them!",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="personal-notice",
                title="Personal Day Notice",
                description="24-hour advance notice preferred",
                script="While personal days don't require a reason, please try to give 24 hours notice when possible to help with team scheduling.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="chicago-leave",
                title="Chicago Leave (If Applicable)",
                description="Chicago Paid Leave rules",
                script="Chicago employees have Chicago Paid Leave with a 40-hour annual max and 16-hour carryover limit. It can be used for ANY reason.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="backdating-rule",
                title="7-Day Backdating Rule",
                description="Past date requests",
                script="Critical rule: You can only request time off up to 7 days in the past. Beyond 7 days, you must contact your manager directly for assistance.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="balance-limits",
                title="Balance Limits",
                description="Hard cap vs soft cap types",
                script="Sick, Personal, and Chicago Leave have HARD caps - you cannot submit requests exceeding your balance. Vacation has a soft cap - you'll see a warning but can still submit for manager discretion.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="summary",
                title="Policy Summary",
                description="Key takeaways",
                script="Remember: Vacation needs exception carryover, sick auto-carries, personal is use-or-lose. All leave has a 7-day backdating limit. Check your balances before requesting!",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# MANAGER-SPECIFIC TRAINING SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def get_manager_carryover_scenario() -> Scenario:
    """
    Scenario: Manager approves carryover exception requests
    Requires: Pending carryover requests from team members
    """
    return Scenario(
        scenario_id="manager-carryover",
        name="Carryover Exception Approvals",
        description="Review and approve employee vacation carryover exception requests",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "carryover", "approvals", "year-end", "training"],
        # Setup: Create a pending carryover request for the manager to review
        setup_actions=[
            SetupAction(
                action_type='create_carryover_request',
                params={
                    'employee_username': 'ptouser01',
                    'hours_requested': 24,
                    'status': 'pending'
                },
                description="Create pending carryover exception request"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access the management dashboard",
                script="Welcome to PTO Central. As a manager, you can approve carryover exception requests from employees who need to carry unused vacation into the next year.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="carryover-intro",
                title="Understanding Carryover",
                description="What is carryover",
                script="Carryover exceptions allow employees to carry unused vacation days into the next year as a BONUS. It doesn't reduce their new year allocation.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="View pending carryover requests",
                script="Your dashboard shows you have a pending carryover request. An employee is requesting to carry over 24 hours of unused vacation.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-carryover",
                title="Access Carryover Queue",
                description="Navigate to carryover management",
                script="Click on the Carryover section to review the exception request details.",
                action="click",
                selector="a:has-text('Carryover'), button:has-text('Carryover'), .cursor-pointer:has-text('Carryover')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="carryover-queue",
                title="Carryover Request Queue",
                description="View all pending carryover requests",
                script="Here's the carryover queue. You can see the employee's request for 24 hours of exception carryover from this year to next.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-request",
                title="Review Request Details",
                description="Evaluate the carryover request",
                script="Review the employee's current balance, requested hours, and reason. Consider their workload and why they couldn't use the time this year.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="partial-approval",
                title="Partial Approval Option",
                description="You can approve partial hours",
                script="You have flexibility here. You can approve all 24 hours, a partial amount like 16 hours, or deny the request entirely.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="approve-deny",
                title="Approve or Deny",
                description="Make your decision",
                script="Click Approve to grant the carryover exception, or Deny with a reason. The employee receives an automatic notification of your decision.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="carryover-impact",
                title="Understanding Impact",
                description="How carryover appears",
                script="Approved hours appear as Exception Carryover in the employee's next year balance. This is a bonus on top of their regular allocation.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_manager_team_overview_scenario() -> Scenario:
    """
    Scenario: Manager views and manages team overview
    Requires: Team members with balances and some requests
    """
    return Scenario(
        scenario_id="manager-team-overview",
        name="Team Management Overview",
        description="View team balances, usage patterns, and manage employee time off",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "team", "balances", "management", "training"],
        # Setup: Create team requests to show meaningful data
        setup_actions=[
            SetupAction(
                action_type='create_team_requests',
                params={
                    'manager_username': 'ptomanager',
                    'count': 4
                },
                description="Create team request data for overview"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access management features",
                script="As a manager, you have access to your team's PTO balances, usage patterns, and approval workflows.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="Manager-specific dashboard view",
                script="Your manager dashboard shows team statistics, pending approvals, and who's currently out.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="team-balances",
                title="View Team Balances",
                description="Access team balance overview",
                script="Click on Team Balances to see each team member's current PTO balances and usage.",
                action="click",
                selector="button:has-text('Team'), a:has-text('Team'), .cursor-pointer:has-text('Balances')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="balance-grid",
                title="Team Balance Grid",
                description="Overview of all team balances",
                script="The team balance grid shows vacation, sick, and personal balances for each team member. Use this to identify who might need to use time off.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="identify-risks",
                title="Identify Carryover Risks",
                description="Employees at risk of losing time",
                script="Employees with high unused balances near year end may lose time. Encourage them to schedule time off or request carryover.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="employee-detail",
                title="View Employee Detail",
                description="Drill into individual employee",
                script="Click on an employee name to see their full history, including all requests, approvals, and balance changes.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="auto-approve-rules",
                title="Manager Auto-Approve",
                description="Your requests are auto-approved",
                script="As a manager, your vacation, sick, and personal requests are auto-approved. However, backdated requests and vacation rollover still require approval.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="coverage-planning",
                title="Coverage Planning",
                description="Plan team coverage",
                script="Use the team calendar to ensure adequate coverage. Days with too many people out are highlighted for attention.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_manager_backdated_scenario() -> Scenario:
    """
    Scenario: Manager handles backdated request approvals
    Requires: Pending backdated request from team member
    """
    return Scenario(
        scenario_id="manager-backdated-requests",
        name="Backdated Request Approvals",
        description="Handle requests for past dates within the 7-day window",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "backdated", "approvals", "policy", "training"],
        # Setup: Create a backdated pending request
        setup_actions=[
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'sick',
                    'days': 1,
                    'status': 'pending',
                    'start_offset': -3  # 3 days ago (within 7-day window)
                },
                description="Create backdated sick day request"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access approval queue",
                script="Welcome to PTO Central. Backdated requests require special attention. Let's learn how to handle time-off requests for past dates.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="backdating-rule",
                title="7-Day Backdating Rule",
                description="Understanding the policy",
                script="Employees can submit requests up to 7 calendar days in the past. This sick day request is from 3 days ago, so it's within the allowed window.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approval-queue",
                title="Pending Approvals",
                description="View pending requests",
                script="You can see a backdated sick day request in your queue. Notice how it's flagged as backdated to draw your attention.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="identify-backdated",
                title="Identify Backdated Requests",
                description="Recognize backdated requests",
                script="Look for the Backdated badge or past date indicator. These requests always require your review, even for trusted employees.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-reason",
                title="Review the Reason",
                description="Why was it submitted late",
                script="Consider why this sick day request is backdated. Common valid reasons include illness preventing immediate access, or simply forgetting to submit.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="verify-absence",
                title="Verify the Absence",
                description="Confirm the employee was actually out",
                script="Verify the employee was actually out sick that day. Check your memory of team attendance or any communications from that date.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="approve-backdated",
                title="Approve or Deny",
                description="Make your decision",
                script="If the sick day was legitimate, click Approve. If you have concerns, you can Deny with an explanation.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="beyond-7-days",
                title="Beyond 7 Days",
                description="Handling older requests",
                script="For requests beyond 7 days ago, employees must contact you directly. You can submit on their behalf through admin functions if needed.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN-SPECIFIC TRAINING SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def get_admin_department_scenario() -> Scenario:
    """
    Scenario: Admin manages departments
    """
    return Scenario(
        scenario_id="admin-departments",
        name="Department Management",
        description="Create, edit, and manage organizational departments",
        required_role="admin",
        default_account="ptoadmin",
        tags=["admin", "departments", "organization", "training"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Admin Login",
                description="Access admin features",
                script="As an administrator, you can manage the organizational structure including departments and their managers.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="admin-menu",
                title="Admin Menu",
                description="Access administration section",
                script="Click on Administration to access department management, user management, and system settings.",
                action="click",
                selector="a:has-text('Admin'), button:has-text('Admin'), .cursor-pointer:has-text('Administration')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="department-list",
                title="Department List",
                description="View all departments",
                script="The department list shows all organizational units with their assigned managers and employee counts.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="create-dept",
                title="Create Department",
                description="Add a new department",
                script="Click Create Department to add a new organizational unit. Provide a name and optionally assign a manager.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="assign-manager",
                title="Assign Manager",
                description="Set department manager",
                script="Assign a manager who will approve PTO requests for employees in this department.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="edit-dept",
                title="Edit Department",
                description="Modify existing department",
                script="Click Edit to modify department details, change the manager, or update settings.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="employee-assignment",
                title="View Employees",
                description="See department members",
                script="View which employees are assigned to each department. Employees are assigned during user creation or editing.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_admin_system_settings_scenario() -> Scenario:
    """
    Scenario: Admin configures system settings
    """
    return Scenario(
        scenario_id="admin-system-settings",
        name="System Administration",
        description="Configure system-wide settings, policies, and email notifications",
        required_role="admin",
        default_account="ptoadmin",
        tags=["admin", "settings", "configuration", "training"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Admin Login",
                description="Access system settings",
                script="System administration allows you to configure company-wide settings, policies, and notification preferences.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="admin-panel",
                title="Admin Panel",
                description="Access administration",
                script="Navigate to the Administration section to access system settings.",
                action="click",
                selector="a:has-text('System'), a:has-text('Admin'), button:has-text('Administration')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="system-overview",
                title="System Overview",
                description="System status and settings",
                script="The system overview shows current configuration, active users, and system health indicators.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="email-settings",
                title="Email Configuration",
                description="Configure email notifications",
                script="Email settings control how notifications are sent for request submissions, approvals, and denials.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="policy-settings",
                title="Policy Configuration",
                description="Leave policy settings",
                script="Policy settings define default allocations, carryover limits, and state-specific rules for different locations.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="year-end",
                title="Year-End Processing",
                description="Annual balance rollover",
                script="Year-end processing automatically creates new year balances, applies carryover, and generates holidays.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="audit-log",
                title="Audit Log",
                description="System activity tracking",
                script="The audit log tracks all system activities including logins, request changes, and administrative actions.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="backup-data",
                title="Data Management",
                description="Database and backup options",
                script="Data management options include database backup, integrity checks, and data export capabilities.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


# ═══════════════════════════════════════════════════════════════════════════
# ADDITIONAL TRAINING SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def get_employee_cancel_scenario() -> Scenario:
    """
    Scenario: Employee cancels their pending PTO request
    Requires: A pending PTO request to cancel
    """
    return Scenario(
        scenario_id="employee-cancel-request",
        name="Cancel Pending Request",
        description="Employee cancels their own pending PTO request before approval",
        required_role="employee",
        default_account="ptouser01",
        tags=["employee", "cancel", "pending", "training"],
        # Setup: Create a pending request for the employee to cancel
        setup_actions=[
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'vacation',
                    'days': 2,
                    'status': 'pending',
                    'start_offset': 21  # Three weeks from now
                },
                description="Create pending vacation request to cancel"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access your dashboard",
                script="Welcome to PTO Central. Let's learn how to cancel a pending vacation request before your manager reviews it.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="View Dashboard",
                description="Dashboard shows pending requests",
                script="Your dashboard shows you have a two-day vacation request pending approval. Let's say your plans changed and you need to cancel it.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-requests",
                title="Open My Requests",
                description="Navigate to request history",
                script="Click on My Requests to see all your submitted requests and find the one to cancel.",
                action="click",
                selector="a:has-text('My Requests'), button:has-text('My Requests'), .cursor-pointer:has-text('Requests')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="find-pending",
                title="Find Pending Request",
                description="Locate the request to cancel",
                script="Here's your request history. Find the pending vacation request - it has an amber status badge showing it's still awaiting approval.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-cancel",
                title="Click Cancel Button",
                description="Cancel the pending request",
                script="Click the Cancel button next to your pending request. You can only cancel requests before they're approved by your manager.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="confirm-cancel",
                title="Confirm Cancellation",
                description="Confirm you want to cancel",
                script="Confirm the cancellation. Your 16 pending hours will be immediately returned to your available vacation balance.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="cancellation-complete",
                title="Request Cancelled",
                description="Cancellation confirmed",
                script="Done! Your request status now shows Cancelled and your vacation balance has been restored. Your manager won't see this in their queue anymore.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_manager_deny_scenario() -> Scenario:
    """
    Scenario: Manager denies a PTO request with a reason
    Requires: A pending PTO request to deny
    """
    return Scenario(
        scenario_id="manager-deny-request",
        name="Deny PTO Request",
        description="Manager reviews and denies a PTO request, providing a reason",
        required_role="manager",
        default_account="ptomanager",
        tags=["manager", "deny", "approval", "training"],
        # Setup: Create a pending request for the manager to deny
        setup_actions=[
            SetupAction(
                action_type='create_pto_request',
                params={
                    'employee_username': 'ptouser01',
                    'pto_type': 'vacation',
                    'days': 5,
                    'status': 'pending',
                    'start_offset': 7  # One week from now
                },
                description="Create pending vacation request to deny"
            )
        ],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access the approval queue",
                script="Welcome to PTO Central. Sometimes you need to deny a PTO request. Let's learn how to do this professionally.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="View pending approvals",
                script="You have a five-day vacation request in your queue. After reviewing, you've determined there's a coverage issue for those dates.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-approvals",
                title="Open Approval Queue",
                description="Navigate to pending requests",
                script="Click on Pending Requests to review the full details before making your decision.",
                action="click",
                selector="button:has-text('View All'), button:has-text('Pending'), .cursor-pointer:has-text('Pending')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="select-request",
                title="Select Request",
                description="Choose the request to deny",
                script="Review the five-day vacation request. The dates conflict with a critical project deadline and another team member's approved leave.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-coverage",
                title="Review Team Coverage",
                description="Check team availability",
                script="The team coverage check shows too many people would be out during this period. This is a valid reason for denial.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="click-deny",
                title="Click Deny Button",
                description="Initiate the denial",
                script="Click Deny to open the denial dialog. Always provide a clear, helpful reason.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="enter-reason",
                title="Enter Denial Reason",
                description="Provide explanation for the denial",
                script="Enter a constructive reason like: Team coverage issue - please try different dates. Suggest alternative dates if possible.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="confirm-deny",
                title="Confirm Denial",
                description="Submit the denial",
                script="Click Confirm to submit the denial. The employee receives an automatic notification with your reason.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="denial-complete",
                title="Request Denied",
                description="Denial confirmed",
                script="The request is denied. The employee's 40 pending hours are restored to their balance and they can resubmit for different dates.",
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
        'calendar-navigation': get_calendar_navigation_scenario(),
        'filter-requests': get_filter_requests_scenario(),
        'team-calendar': get_team_calendar_scenario(),
        'pto-reports': get_reporting_scenario(),
        'balance-dashboard': get_balance_dashboard_scenario(),
        # New training scenarios
        'wfh-request': get_wfh_request_scenario(),
        'wfh-swap': get_wfh_swap_scenario(),
        'leave-type-rules': get_leave_type_rules_scenario(),
        'manager-carryover': get_manager_carryover_scenario(),
        'manager-team-overview': get_manager_team_overview_scenario(),
        'manager-backdated-requests': get_manager_backdated_scenario(),
        'admin-departments': get_admin_department_scenario(),
        'admin-system-settings': get_admin_system_settings_scenario(),
        # Additional scenarios
        'employee-cancel-request': get_employee_cancel_scenario(),
        'manager-deny-request': get_manager_deny_scenario(),
    }


def get_scenarios_by_role() -> Dict[str, Dict[str, Scenario]]:
    """
    Get scenarios organized by required role.
    Returns a dict with role keys and scenario dicts as values.
    """
    all_scenarios = get_all_scenarios()

    grouped = {
        'employee': {},
        'manager': {},
        'admin': {},
    }

    for scenario_id, scenario in all_scenarios.items():
        role = scenario.required_role
        if role in grouped:
            grouped[role][scenario_id] = scenario
        else:
            # Default unknown roles to employee
            grouped['employee'][scenario_id] = scenario

    return grouped
