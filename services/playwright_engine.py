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


class PlaywrightEngine:
    """
    Browser automation engine for testing and documentation.
    Uses synchronous API run in a thread pool to avoid Windows asyncio issues.

    Usage:
        engine = PlaywrightEngine()
        result = engine.run_scenario_sync(scenario, 'techuser')
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
            with sync_playwright() as playwright:
                self.playwright = playwright
                self.browser = playwright.chromium.launch(
                    headless=self.config.headless,
                    slow_mo=self.config.slow_mo
                )

                # Video recording setup
                video_dir = None
                if self.config.generate_video and self.config.video_enabled:
                    video_dir = self.config.videos_dir / scenario.scenario_id
                    video_dir.mkdir(parents=True, exist_ok=True)

                # Create browser context
                context_options = {
                    'viewport': {
                        'width': self.config.viewport_width,
                        'height': self.config.viewport_height
                    },
                    'ignore_https_errors': self.config.ignore_https_errors,
                }

                if video_dir:
                    context_options['record_video_dir'] = str(video_dir)
                    context_options['record_video_size'] = {
                        'width': self.config.video_width,
                        'height': self.config.video_height
                    }

                self.context = self.browser.new_context(**context_options)
                self.page = self.context.new_page()
                self.page.set_default_timeout(self.config.default_timeout)

                # Login
                login_success = self._login(account)
                if not login_success:
                    raise Exception(f"Failed to login as {account.username}")

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
            print(f"Navigating to {self.config.base_url}...")
            self.page.goto(self.config.base_url, wait_until='domcontentloaded', timeout=60000)

            # Wait a moment for NiceGUI to initialize
            time.sleep(2)

            # Wait for login form to be visible
            print("Waiting for login form...")
            self.page.wait_for_selector(
                'input[type="text"], input[name="username"], input[placeholder*="user" i]',
                timeout=15000
            )

            # Fill username
            print(f"Filling username: {account.username}")
            username_input = self.page.locator(
                'input[type="text"], input[name="username"], input[placeholder*="user" i]'
            ).first
            username_input.fill(account.username)

            # Fill password
            print("Filling password...")
            password_input = self.page.locator('input[type="password"]').first
            password_input.fill(account.password)

            # Click login button
            print("Clicking login button...")
            login_button = self.page.locator(
                'button[type="submit"], button:has-text("Login"), button:has-text("Sign In"), button:has-text("Log In")'
            ).first
            login_button.click()

            # Wait for navigation to complete
            self.page.wait_for_load_state('domcontentloaded', timeout=30000)

            # Brief wait for any redirects
            time.sleep(2)
            print("Login completed successfully")

            return True

        except Exception as e:
            print(f"Login failed for {account.username}: {e}")
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
                    self.page.click(step.selector)
                    time.sleep(1)  # Allow page to update

            elif step.action == 'fill':
                if step.selector and step.value is not None:
                    if step.focus_element:
                        self._focus_element(step.selector)
                    self.page.fill(step.selector, step.value)

            elif step.action == 'select':
                if step.selector and step.value:
                    if step.focus_element:
                        self._focus_element(step.selector)
                    self.page.select_option(step.selector, step.value)

            elif step.action == 'wait':
                time.sleep(step.wait_time)

            elif step.action == 'screenshot':
                pass  # Just take screenshot, handled below

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
        default_account="techuser",
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
                title="Access Pending Requests",
                description="Navigate to the pending requests section",
                script="Click on the Pending Requests section to view requests awaiting your decision.",
                action="click",
                selector="button:has-text('View All'), button:has-text('Pending'), .cursor-pointer:has-text('Pending')",
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
        default_account="techuser",
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
    """
    return Scenario(
        scenario_id="filter-requests",
        name="Filter PTO Requests",
        description="Learn how to filter and search PTO requests by type, status, and date range",
        required_role="employee",
        default_account="techuser",
        tags=["employee", "filter", "search", "requests"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Login to Application",
                description="Access the TJM Time Calendar",
                script="Log in to access your request history and filtering options.",
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
                script="Your request history shows all submitted requests with their current status.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-section",
                title="Filter Controls",
                description="The filtering options at the top",
                script="Use the filter controls at the top to narrow down your request list.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-type",
                title="Filter by Leave Type",
                description="Select a specific leave type to filter",
                script="Click the Leave Type dropdown to filter by Vacation, Sick, Personal, or other leave types.",
                action="click",
                selector=".q-select:has-text('Type'), .q-select:has-text('Leave'), select[name*='type']",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="select-vacation",
                title="Select Vacation Type",
                description="Choose Vacation to see only vacation requests",
                script="Select Vacation to filter the list to show only your vacation requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filtered-results",
                title="Filtered Results",
                description="View the filtered request list",
                script="The list now shows only vacation requests. Notice the count updates to reflect the filter.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-status",
                title="Filter by Status",
                description="Add status filter to narrow further",
                script="You can also filter by status to see only Pending, Approved, or Denied requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="clear-filters",
                title="Clear All Filters",
                description="Reset filters to see all requests",
                script="Click Clear or the X buttons to remove filters and see all requests again.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_team_calendar_scenario() -> Scenario:
    """
    Scenario: Manager views team calendar and coverage
    """
    return Scenario(
        scenario_id="team-calendar",
        name="Team Calendar View",
        description="Manager views team calendar to check coverage and plan approvals",
        required_role="manager",
        default_account="techmanager",
        tags=["manager", "calendar", "team", "coverage"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Log in with manager credentials",
                script="Log in as a manager to access the team calendar and coverage views.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="View team status from dashboard",
                script="Your dashboard shows who's currently out and upcoming absences for your team.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-team-calendar",
                title="Open Team Calendar",
                description="Navigate to the team calendar view",
                script="Click on Team Calendar to see all team members' scheduled time off.",
                action="click",
                selector="a:has-text('Team Calendar'), button:has-text('Team'), .cursor-pointer:has-text('Team')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="team-calendar-view",
                title="Team Calendar Overview",
                description="View all team members' PTO on one calendar",
                script="The team calendar shows everyone's approved and pending time off color-coded by employee.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="coverage-indicator",
                title="Coverage Indicators",
                description="Check team coverage levels",
                script="Coverage indicators show days where too many team members are scheduled off.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="filter-by-employee",
                title="Filter by Employee",
                description="Show only specific team members",
                script="Use the employee filter to focus on specific team members' schedules.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="hover-details",
                title="View Request Details",
                description="Hover or click for request details",
                script="Hover over or click any event to see the full request details including leave type and notes.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="conflict-detection",
                title="Conflict Detection",
                description="Identify scheduling conflicts",
                script="Days highlighted in red indicate potential coverage issues that need attention.",
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
        default_account="techmanager",
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
        default_account="techuser",
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
        default_account="techuser",
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
        default_account="techuser",
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
    """
    return Scenario(
        scenario_id="manager-carryover",
        name="Carryover Exception Approvals",
        description="Review and approve employee vacation carryover exception requests",
        required_role="manager",
        default_account="techmanager",
        tags=["manager", "carryover", "approvals", "year-end", "training"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access the management dashboard",
                script="As a manager, you'll approve carryover exception requests from employees who need to carry unused vacation into the next year.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="carryover-intro",
                title="Understanding Carryover",
                description="What is carryover",
                script="Carryover exceptions allow employees to carry unused vacation days into the next year as a BONUS - it doesn't reduce their new allocation.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="dashboard",
                title="Manager Dashboard",
                description="View pending carryover requests",
                script="Your dashboard shows any pending carryover requests awaiting your approval, separate from regular PTO requests.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="open-carryover",
                title="Access Carryover Queue",
                description="Navigate to carryover management",
                script="Click on the Carryover section to view pending exception requests from your team.",
                action="click",
                selector="a:has-text('Carryover'), button:has-text('Carryover'), .cursor-pointer:has-text('Carryover')",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="carryover-queue",
                title="Carryover Request Queue",
                description="View all pending carryover requests",
                script="The carryover queue shows each employee's request with the hours they want to carry over and their reason.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-request",
                title="Review Request Details",
                description="Evaluate the carryover request",
                script="Review the employee's current balance, requested hours, and reason. Consider workload and why they couldn't use the time.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="partial-approval",
                title="Partial Approval Option",
                description="You can approve partial hours",
                script="You can approve the full amount or a partial amount. For example, approve 16 hours out of 24 requested.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="approve-deny",
                title="Approve or Deny",
                description="Make your decision",
                script="Click Approve to grant the carryover exception, or Deny with a reason. The employee will be notified of your decision.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="carryover-impact",
                title="Understanding Impact",
                description="How carryover appears",
                script="Approved carryover hours appear as 'Exception Carryover' in the employee's balance for the next year - it's a BONUS on top of their regular allocation.",
                action="screenshot",
                wait_time=2.0
            )
        ]
    )


def get_manager_team_overview_scenario() -> Scenario:
    """
    Scenario: Manager views and manages team overview
    """
    return Scenario(
        scenario_id="manager-team-overview",
        name="Team Management Overview",
        description="View team balances, usage patterns, and manage employee time off",
        required_role="manager",
        default_account="techmanager",
        tags=["manager", "team", "balances", "management", "training"],
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
    """
    return Scenario(
        scenario_id="manager-backdated-requests",
        name="Backdated Request Approvals",
        description="Handle requests for past dates within the 7-day window",
        required_role="manager",
        default_account="techmanager",
        tags=["manager", "backdated", "approvals", "policy", "training"],
        steps=[
            ScenarioStep(
                step_id="login",
                title="Manager Login",
                description="Access approval queue",
                script="Backdated requests require special attention. Let's learn how to handle time-off requests for past dates.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="backdating-rule",
                title="7-Day Backdating Rule",
                description="Understanding the policy",
                script="Employees can submit requests up to 7 calendar days in the past. Beyond 7 days, they must contact you directly for manual entry.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="approval-queue",
                title="Pending Approvals",
                description="View pending requests",
                script="Backdated requests appear in your regular approval queue but are flagged with a special indicator showing they're for past dates.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="identify-backdated",
                title="Identify Backdated Requests",
                description="Recognize backdated requests",
                script="Look for the 'Backdated' badge or past date indicator. These requests always require your approval, even for trusted employees.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="review-reason",
                title="Review the Reason",
                description="Why was it submitted late",
                script="Consider why the request is backdated. Common valid reasons include: forgot to submit, emergency situations, or system access issues.",
                action="screenshot",
                wait_time=2.0
            ),
            ScenarioStep(
                step_id="verify-absence",
                title="Verify the Absence",
                description="Confirm the employee was actually out",
                script="Verify that the employee was actually absent on those dates. Check attendance records or your memory of that period.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="approve-backdated",
                title="Approve or Deny",
                description="Make your decision",
                script="Approve if the absence was legitimate, or deny with explanation if there are concerns about the request.",
                action="screenshot",
                wait_time=1.5
            ),
            ScenarioStep(
                step_id="beyond-7-days",
                title="Beyond 7 Days",
                description="Handling older requests",
                script="For requests beyond 7 days ago, employees must contact you directly. As manager, you can submit on their behalf if needed through admin functions.",
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
        default_account="netadmin",
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
        default_account="netadmin",
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
        'leave-type-rules': get_leave_type_rules_scenario(),
        'manager-carryover': get_manager_carryover_scenario(),
        'manager-team-overview': get_manager_team_overview_scenario(),
        'manager-backdated-requests': get_manager_backdated_scenario(),
        'admin-departments': get_admin_department_scenario(),
        'admin-system-settings': get_admin_system_settings_scenario(),
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
