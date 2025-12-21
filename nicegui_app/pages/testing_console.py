"""
TJM Time Calendar - Media Studio
Admin interface for training video production, documentation generation, and scenario execution.

Route: /admin/testing-console
Access: Admin and SuperAdmin roles only
"""

from nicegui import ui, app
from datetime import datetime
from typing import Optional, Dict, Any
import random

# Import our services - adjust paths as needed
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.testing_config import testing_config, TTSVoice, TestAccount
from config.custom_scenarios import (
    scenario_manager,
    CustomScenario,
    create_quick_scenario,
    MarkdownScenarioParser,
    TEMPLATES_DIR
)
from services.playwright_engine import (
    PlaywrightEngine,
    Scenario,
    ScenarioResult,
    get_all_scenarios,
    get_scenarios_by_role
)
from services.doc_generator import DocumentationGenerator
from services.audio_narration import AudioNarrationService


# ═══════════════════════════════════════════════════════════════════════════
# TJM BRAND COLORS
# ═══════════════════════════════════════════════════════════════════════════

TJM_GOLD = '#c9a227'
TJM_GRAY = '#5a6a72'
TJM_DARK = '#1a1a2e'


# ═══════════════════════════════════════════════════════════════════════════
# CONSOLE STATE
# ═══════════════════════════════════════════════════════════════════════════

class ConsoleState:
    """Tracks the state of the testing console"""

    def __init__(self):
        self.is_running: bool = False
        self.cancel_requested: bool = False  # Flag to cancel execution
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
        self.refresh_outputs = None

    def request_cancel(self):
        """Request cancellation of the current scenario"""
        if self.is_running:
            self.cancel_requested = True
            self.log('[CANCEL] Stop requested - will cancel at next checkpoint...', 'warning')
            return True
        return False

    def reset_cancel(self):
        """Reset the cancel flag"""
        self.cancel_requested = False

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


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PAGE BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def create_testing_console_page():
    """Build the complete Media Studio UI - Training video production and documentation"""

    # Create console state for this page instance
    console_state = ConsoleState()

    # ═══════════════════════════════════════════════════════════════════════
    # PIPELINE ANIMATION STYLES
    # ═══════════════════════════════════════════════════════════════════════
    ui.add_head_html('''
    <style>
        /* Pipeline stage animations */
        @keyframes pipeline-pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.15); opacity: 0.8; }
        }
        @keyframes pipeline-glow {
            0%, 100% { box-shadow: 0 0 5px rgba(201, 162, 39, 0.3); }
            50% { box-shadow: 0 0 20px rgba(201, 162, 39, 0.8), 0 0 40px rgba(201, 162, 39, 0.4); }
        }
        @keyframes pipeline-flow {
            0% { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }
        @keyframes pipeline-spark {
            0%, 100% { opacity: 0; transform: scale(0.5) translateY(0); }
            50% { opacity: 1; transform: scale(1) translateY(-10px); }
        }
        @keyframes stage-complete {
            0% { transform: scale(1); }
            50% { transform: scale(1.3); }
            100% { transform: scale(1); }
        }
        @keyframes connector-flow {
            0% { background-position: 0% 0%; }
            100% { background-position: 200% 0%; }
        }
        @keyframes icon-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .pipeline-stage {
            transition: all 0.3s ease;
            position: relative;
        }
        .pipeline-stage.idle {
            opacity: 0.4;
        }
        .pipeline-stage.active {
            animation: pipeline-pulse 1s ease-in-out infinite, pipeline-glow 1.5s ease-in-out infinite;
        }
        .pipeline-stage.complete {
            opacity: 1;
        }
        .pipeline-stage.complete .stage-icon {
            animation: stage-complete 0.5s ease-out;
        }

        .pipeline-connector {
            height: 4px;
            background: linear-gradient(90deg, #374151, #374151);
            transition: all 0.3s ease;
        }
        .pipeline-connector.active {
            background: linear-gradient(90deg, #C9A227, #f59e0b, #C9A227);
            background-size: 200% 100%;
            animation: connector-flow 1s linear infinite;
        }
        .pipeline-connector.complete {
            background: #22c55e;
        }

        .stage-spark {
            position: absolute;
            top: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 8px;
            height: 8px;
            background: #C9A227;
            border-radius: 50%;
            animation: pipeline-spark 1s ease-in-out infinite;
        }

        .icon-spinning {
            animation: icon-spin 1s linear infinite;
        }

        /* Failed state animations */
        @keyframes stage-shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-3px); }
            20%, 40%, 60%, 80% { transform: translateX(3px); }
        }
        @keyframes failed-glow {
            0%, 100% { box-shadow: 0 0 5px rgba(239, 68, 68, 0.3); }
            50% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.8), 0 0 30px rgba(239, 68, 68, 0.4); }
        }
        .pipeline-stage.failed {
            opacity: 1;
            animation: stage-shake 0.5s ease-in-out, failed-glow 1.5s ease-in-out infinite;
        }
        .pipeline-stage.failed .stage-icon {
            color: #ef4444 !important;
        }
        .pipeline-connector.failed {
            background: linear-gradient(90deg, #ef4444, #dc2626, #ef4444);
            background-size: 200% 100%;
            animation: connector-flow 1s linear infinite;
        }
    </style>
    ''')

    # Combine built-in and custom scenarios (shared state)
    builtin_scenarios = get_all_scenarios()
    custom_scenarios_list = scenario_manager.get_all_scenarios()
    custom_scenarios = {f'custom:{s.id}': s.to_scenario() for s in custom_scenarios_list}
    all_scenarios = {**builtin_scenarios, **custom_scenarios}

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN TABBED LAYOUT
    # ═══════════════════════════════════════════════════════════════════════

    with ui.tabs().classes('w-full').style(f'background-color: #1f2937;') as main_tabs:
        run_tab = ui.tab('Run Scenarios', icon='play_circle').style(f'color: {TJM_GOLD};')
        outputs_tab = ui.tab('Generated Outputs', icon='folder_special')
        custom_tab = ui.tab('Custom Scenarios', icon='extension')
        history_tab = ui.tab('Run History', icon='history')

    with ui.tab_panels(main_tabs, value=run_tab).classes('w-full'):

        # ═══════════════════════════════════════════════════════════════════
        # TAB 1: RUN SCENARIOS
        # ═══════════════════════════════════════════════════════════════════
        with ui.tab_panel(run_tab):

            # ═══════════════════════════════════════════════════════════════
            # VISUAL PIPELINE ANIMATION (TOP OF PAGE)
            # ═══════════════════════════════════════════════════════════════
            pipeline_stages = {}
            pipeline_connectors = {}

            with ui.card().classes('w-full p-4 mb-4').style('background-color: #111827; border: 1px solid #374151;'):
                with ui.row().classes('items-center gap-1 mb-3'):
                    ui.icon('auto_awesome', size='xs').style(f'color: {TJM_GOLD};')
                    ui.label('PIPELINE').classes('text-xs font-bold tracking-wider opacity-60')

                with ui.row().classes('w-full items-center justify-between'):
                    # Stage 1: Login
                    with ui.column().classes('items-center pipeline-stage idle') as stage_login:
                        ui.icon('login', size='md').classes('stage-icon').style('color: #60a5fa;')
                        ui.label('Login').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['login'] = stage_login

                    # Connector 1
                    conn1 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['login_steps'] = conn1

                    # Stage 2: Steps
                    with ui.column().classes('items-center pipeline-stage idle') as stage_steps:
                        ui.icon('directions_run', size='md').classes('stage-icon').style('color: #a855f7;')
                        ui.label('Steps').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['steps'] = stage_steps

                    # Connector 2
                    conn2 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['steps_screenshots'] = conn2

                    # Stage 3: Screenshots
                    with ui.column().classes('items-center pipeline-stage idle') as stage_screenshots:
                        ui.icon('photo_camera', size='md').classes('stage-icon').style('color: #3b82f6;')
                        ui.label('Capture').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['screenshots'] = stage_screenshots

                    # Connector 3
                    conn3 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['screenshots_docs'] = conn3

                    # Stage 4: Documentation
                    with ui.column().classes('items-center pipeline-stage idle') as stage_docs:
                        ui.icon('description', size='md').classes('stage-icon').style('color: #22c55e;')
                        ui.label('Docs').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['docs'] = stage_docs

                    # Connector 4
                    conn4 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['docs_audio'] = conn4

                    # Stage 5: Audio
                    with ui.column().classes('items-center pipeline-stage idle') as stage_audio:
                        ui.icon('graphic_eq', size='md').classes('stage-icon').style('color: #f59e0b;')
                        ui.label('Audio').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['audio'] = stage_audio

                    # Connector 5
                    conn5 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['audio_cover'] = conn5

                    # Stage 6: Cover Page (before Video so video can use it)
                    with ui.column().classes('items-center pipeline-stage idle') as stage_cover:
                        ui.icon('image', size='md').classes('stage-icon').style('color: #8b5cf6;')
                        ui.label('Cover').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['cover'] = stage_cover

                    # Connector 6
                    conn6 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['cover_video'] = conn6

                    # Stage 7: Video Production (uses cover + audio + screenshots)
                    with ui.column().classes('items-center pipeline-stage idle') as stage_video:
                        ui.icon('videocam', size='md').classes('stage-icon').style('color: #ec4899;')
                        ui.label('Video').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['video'] = stage_video

                    # Connector 7
                    conn7 = ui.element('div').classes('flex-grow mx-2 pipeline-connector rounded')
                    pipeline_connectors['video_complete'] = conn7

                    # Stage 8: Complete
                    with ui.column().classes('items-center pipeline-stage idle') as stage_complete:
                        ui.icon('check_circle', size='md').classes('stage-icon').style('color: #10b981;')
                        ui.label('Done').classes('text-xs mt-1 opacity-70')
                    pipeline_stages['complete'] = stage_complete

            # Pipeline control functions
            def reset_pipeline():
                """Reset all pipeline stages to idle"""
                for stage in pipeline_stages.values():
                    stage._classes = [c for c in stage._classes if c not in ['active', 'complete', 'failed']]
                    stage._classes.append('idle')
                    stage.update()
                for conn in pipeline_connectors.values():
                    conn._classes = [c for c in conn._classes if c not in ['active', 'complete', 'failed']]
                    conn.update()

            def set_stage_active(stage_name: str):
                """Set a stage to active (glowing)"""
                if stage_name in pipeline_stages:
                    stage = pipeline_stages[stage_name]
                    stage._classes = [c for c in stage._classes if c not in ['idle', 'complete', 'failed']]
                    if 'active' not in stage._classes:
                        stage._classes.append('active')
                    stage.update()

            def set_stage_complete(stage_name: str, next_connector: str = None):
                """Set a stage to complete and optionally activate connector"""
                if stage_name in pipeline_stages:
                    stage = pipeline_stages[stage_name]
                    stage._classes = [c for c in stage._classes if c not in ['idle', 'active', 'failed']]
                    if 'complete' not in stage._classes:
                        stage._classes.append('complete')
                    stage.update()
                if next_connector and next_connector in pipeline_connectors:
                    conn = pipeline_connectors[next_connector]
                    conn._classes = [c for c in conn._classes if c != 'active']
                    if 'complete' not in conn._classes:
                        conn._classes.append('complete')
                    conn.update()

            def activate_connector(conn_name: str):
                """Activate a connector with flowing animation"""
                if conn_name in pipeline_connectors:
                    conn = pipeline_connectors[conn_name]
                    if 'active' not in conn._classes:
                        conn._classes.append('active')
                    conn.update()

            def set_stage_failed(stage_name: str, connector_name: str = None):
                """Mark a stage as failed (red with shake)"""
                if stage_name in pipeline_stages:
                    stage = pipeline_stages[stage_name]
                    stage._classes = [c for c in stage._classes if c not in ['idle', 'active', 'complete']]
                    if 'failed' not in stage._classes:
                        stage._classes.append('failed')
                    stage.update()
                if connector_name and connector_name in pipeline_connectors:
                    conn = pipeline_connectors[connector_name]
                    conn._classes = [c for c in conn._classes if c not in ['active', 'complete']]
                    if 'failed' not in conn._classes:
                        conn._classes.append('failed')
                    conn.update()

            # Store pipeline functions in console state
            console_state.reset_pipeline = reset_pipeline
            console_state.set_stage_active = set_stage_active
            console_state.set_stage_complete = set_stage_complete
            console_state.activate_connector = activate_connector
            console_state.set_stage_failed = set_stage_failed

            # ═══════════════════════════════════════════════════════════════
            # CONSOLE LOG (BELOW PIPELINE - FULL WIDTH)
            # ═══════════════════════════════════════════════════════════════
            with ui.card().classes('w-full p-4 mb-4').style('background-color: #1f2937;'):
                with ui.row().classes('w-full items-center justify-between mb-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('terminal', size='sm').style(f'color: {TJM_GOLD};')
                        ui.label('CONSOLE').classes('text-sm font-bold tracking-wide opacity-80')
                    with ui.row().classes('gap-1'):
                        def clear_logs():
                            console_state.clear_logs()
                            ui.notify('Logs cleared', type='info')

                        def export_logs():
                            if console_state.log_entries:
                                log_file = testing_config.output_base / 'console_log.txt'
                                with open(log_file, 'w') as f:
                                    for entry in console_state.log_entries:
                                        f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")
                                ui.notify(f'Exported to {log_file.name}', type='positive')
                            else:
                                ui.notify('No logs to export', type='warning')

                        ui.button(icon='download', on_click=export_logs).props('flat round dense size=sm').tooltip('Export Logs')
                        ui.button(icon='delete_outline', on_click=clear_logs).props('flat round dense size=sm').tooltip('Clear Logs')

                log_container = ui.column().classes('w-full h-32 overflow-y-auto rounded p-2 gap-0').style('background-color: #111827;')
                console_state.log_container = log_container
                with log_container:
                    ui.label('[Console Ready]').classes('text-xs font-mono text-gray-500')

            # ═══════════════════════════════════════════════════════════════
            # MAIN 3-PANEL LAYOUT: SCENARIO | ACCOUNT | GENERATE
            # ═══════════════════════════════════════════════════════════════
            with ui.row().classes('w-full gap-4 items-stretch'):

                # SCENARIO PANEL
                with ui.card().classes('flex-1 p-4').style('background-color: #1f2937; min-height: 200px;'):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('movie', size='sm').style(f'color: {TJM_GOLD};')
                        ui.label('SCENARIO').classes('text-sm font-bold tracking-wide opacity-80')

                    # Build dropdown options grouped by role
                    scenarios_by_role = get_scenarios_by_role()
                    scenario_options = {}

                    # Employee scenarios first
                    if scenarios_by_role.get('employee'):
                        for key, scenario in scenarios_by_role['employee'].items():
                            scenario_options[key] = f"[Employee] {scenario.name}"

                    # Manager scenarios
                    if scenarios_by_role.get('manager'):
                        for key, scenario in scenarios_by_role['manager'].items():
                            scenario_options[key] = f"[Manager] {scenario.name}"

                    # Admin scenarios
                    if scenarios_by_role.get('admin'):
                        for key, scenario in scenarios_by_role['admin'].items():
                            scenario_options[key] = f"[Admin] {scenario.name}"

                    # Custom scenarios last
                    for key, scenario in custom_scenarios.items():
                        scenario_options[key] = f"[Custom] {scenario.name}"

                    scenario_select = ui.select(
                        options=scenario_options,
                        value='pto-request' if 'pto-request' in scenario_options else (list(scenario_options.keys())[0] if scenario_options else None),
                        label='Choose Scenario'
                    ).props('outlined dense options-dense').classes('w-full mb-3')

                    # Scenario info
                    with ui.row().classes('items-center gap-2'):
                        scenario_role_chip = ui.chip('Employee', color='blue').props('dense size=sm')
                        scenario_steps_chip = ui.chip('9 Steps', color='grey').props('dense outline size=sm')

                    def update_scenario_display():
                        scenario = all_scenarios.get(scenario_select.value)
                        if scenario:
                            scenario_role_chip.text = scenario.required_role.title()
                            scenario_steps_chip.text = f'{len(scenario.steps)} Steps'

                    scenario_select.on_value_change(lambda: update_scenario_display())

                # ACCOUNT PANEL
                with ui.card().classes('flex-1 p-4').style('background-color: #1f2937; min-height: 200px;'):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('person', size='sm').style(f'color: {TJM_GOLD};')
                        ui.label('ACCOUNT').classes('text-sm font-bold tracking-wide opacity-80')

                    account_select = ui.select(
                        options={
                            key: f"{acc.display_name} ({acc.role.title()})"
                            for key, acc in testing_config.test_accounts.items()
                        },
                        value='ptouser',
                        label='Select Account'
                    ).props('outlined dense').classes('w-full mb-3')

                    # Account description
                    account_desc = ui.label('Employee - Submits PTO requests').classes('text-xs opacity-60')

                    def update_account_info():
                        account = testing_config.get_account(account_select.value)
                        if account:
                            account_desc.text = account.description

                    account_select.on_value_change(lambda: update_account_info())

                    # Hidden fields for compatibility (always use account login)
                    use_custom = ui.element('div').style('display: none;')
                    use_custom.value = False
                    custom_username = ui.element('div').style('display: none;')
                    custom_username.value = ''
                    custom_password = ui.element('div').style('display: none;')
                    custom_password.value = ''

                    # Hidden output options (all enabled by default)
                    opt_screenshots = ui.element('div').style('display: none;')
                    opt_screenshots.value = True
                    opt_markdown = ui.element('div').style('display: none;')
                    opt_markdown.value = True
                    opt_video = ui.element('div').style('display: none;')
                    opt_video.value = True
                    opt_audio = ui.element('div').style('display: none;')
                    opt_audio.value = True

                # GENERATE PANEL
                with ui.card().classes('flex-1 p-4').style('background-color: #1f2937; min-height: 200px;'):
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('auto_awesome', size='sm').style(f'color: {TJM_GOLD};')
                        ui.label('GENERATE').classes('text-sm font-bold tracking-wide opacity-80')

                    # Voice selection
                    voice_select = ui.select(
                        options={
                            'onyx': 'Onyx - Professional Male',
                            'alloy': 'Alloy - Neutral',
                            'nova': 'Nova - Warm Female',
                            'echo': 'Echo - Casual Male'
                        },
                        value='onyx',
                        label='Narrator Voice'
                    ).props('outlined dense').classes('w-full mb-2')

                    # Audio generation toggle (costs money - OpenAI API)
                    with ui.row().classes('w-full items-center gap-2 mb-3'):
                        audio_toggle = ui.switch('Generate Audio', value=True).props('dense color=amber')
                        ui.label('(OpenAI API - costs $)').classes('text-xs opacity-50')

                    # Link the visible toggle to the hidden opt_audio
                    def on_audio_toggle(e):
                        opt_audio.value = audio_toggle.value
                    audio_toggle.on('update:model-value', on_audio_toggle)

                    # Progress bar
                    progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full mb-2')
                    console_state.progress_bar = progress_bar

                    step_label = ui.label('Ready').classes('text-xs opacity-60 mb-2')
                    console_state.status_label = step_label

                    # Action buttons
                    with ui.row().classes('w-full gap-2'):
                        async def run_scenario():
                            """Execute the selected scenario with visual pipeline animation and per-stage error handling"""
                            import asyncio
                            import traceback

                            if console_state.is_running:
                                ui.notify('A scenario is already running', type='warning')
                                return

                            console_state.is_running = True
                            console_state.reset_cancel()  # Reset cancel flag
                            console_state.log('═' * 50, 'info')
                            console_state.log('Starting scenario execution...', 'info')
                            run_btn.props('loading')
                            pipeline_failed = False
                            current_stage = 'init'

                            # Helper to check for cancellation
                            def check_cancelled():
                                if console_state.cancel_requested:
                                    console_state.log('[CANCELLED] Execution stopped by user', 'warning')
                                    return True
                                return False

                            # Reset and start pipeline animation
                            reset_pipeline()
                            await asyncio.sleep(0.1)

                            try:
                                # ═══════════════════════════════════════════════════════════
                                # STAGE 0: VALIDATION
                                # ═══════════════════════════════════════════════════════════
                                console_state.log('[VALIDATION] Checking configuration...', 'info')

                                scenario = all_scenarios.get(scenario_select.value)
                                if not scenario:
                                    console_state.log('[ERROR] No scenario selected', 'error')
                                    ui.notify('Please select a scenario', type='warning')
                                    return

                                # Determine credentials
                                if use_custom.value and custom_username.value:
                                    credentials = {'username': custom_username.value, 'password': custom_password.value}
                                    account_username = None
                                    console_state.log(f'[VALIDATION] Using custom credentials: {custom_username.value}', 'info')
                                else:
                                    credentials = None
                                    account_username = account_select.value
                                    if not account_username:
                                        console_state.log('[ERROR] No test account selected', 'error')
                                        ui.notify('Please select a test account', type='warning')
                                        return
                                    console_state.log(f'[VALIDATION] Using test account: {account_username}', 'info')

                                # Update config
                                testing_config.generate_screenshots = opt_screenshots.value
                                testing_config.generate_markdown = opt_markdown.value
                                testing_config.generate_video = opt_video.value
                                testing_config.tts_enabled = opt_audio.value
                                if opt_audio.value:
                                    testing_config.tts_voice = TTSVoice(voice_select.value)

                                console_state.log(f'[VALIDATION] Configuration validated ✓', 'success')
                                console_state.log(f'[INFO] Running: {scenario.name}', 'info')
                                console_state.log(f'[INFO] Target: {testing_config.base_url}', 'info')
                                console_state.log(f'[INFO] Options: Screenshots={opt_screenshots.value}, Docs={opt_markdown.value}, Video={opt_video.value}, Audio={opt_audio.value}', 'info')
                                step_label.text = 'Running (browser will open)...'

                                # Check for cancellation
                                if check_cancelled():
                                    pipeline_failed = True
                                    raise Exception('Cancelled by user')

                                # ═══════════════════════════════════════════════════════════
                                # STAGE 1: LOGIN
                                # ═══════════════════════════════════════════════════════════
                                current_stage = 'login'
                                console_state.log('[LOGIN] Initializing browser and login...', 'info')
                                set_stage_active('login')
                                activate_connector('login_steps')
                                await asyncio.sleep(0.2)

                                try:
                                    def run_playwright():
                                        engine = PlaywrightEngine()
                                        return engine.run_scenario_sync(
                                            scenario=scenario,
                                            account_username=account_username,
                                            custom_credentials=credentials
                                        )

                                    # PIPELINE: Login complete, steps active
                                    set_stage_complete('login', 'login_steps')
                                    console_state.log('[LOGIN] Login stage complete ✓', 'success')

                                except Exception as login_error:
                                    console_state.log(f'[LOGIN ERROR] {str(login_error)}', 'error')
                                    console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                    set_stage_failed('login', 'login_steps')
                                    pipeline_failed = True
                                    raise

                                # Check for cancellation
                                if check_cancelled():
                                    pipeline_failed = True
                                    raise Exception('Cancelled by user')

                                # ═══════════════════════════════════════════════════════════
                                # STAGE 2: STEPS EXECUTION
                                # ═══════════════════════════════════════════════════════════
                                current_stage = 'steps'
                                console_state.log('[STEPS] Executing scenario steps...', 'info')
                                set_stage_active('steps')
                                activate_connector('steps_screenshots')

                                try:
                                    loop = asyncio.get_event_loop()
                                    result = await loop.run_in_executor(None, run_playwright)
                                    console_state.last_result = result

                                    if not result:
                                        raise Exception('Playwright returned no result')

                                    set_stage_complete('steps', 'steps_screenshots')
                                    console_state.log(f'[STEPS] Executed {len(result.steps)} steps', 'success')

                                except Exception as steps_error:
                                    console_state.log(f'[STEPS ERROR] {str(steps_error)}', 'error')
                                    console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                    set_stage_failed('steps', 'steps_screenshots')
                                    pipeline_failed = True
                                    raise

                                # ═══════════════════════════════════════════════════════════
                                # STAGE 3: CAPTURE/SCREENSHOTS
                                # ═══════════════════════════════════════════════════════════
                                current_stage = 'screenshots'
                                console_state.log('[CAPTURE] Processing captured content...', 'info')
                                set_stage_active('screenshots')
                                activate_connector('screenshots_docs')
                                await asyncio.sleep(0.3)

                                try:
                                    step_errors = 0
                                    for step in result.steps:
                                        status = 'success' if step.success else 'error'
                                        console_state.log(f"  Step {step.step_number}: {step.title}", status)
                                        if not step.success:
                                            step_errors += 1

                                    if step_errors > 0:
                                        console_state.log(f'[CAPTURE WARNING] {step_errors} step(s) had errors', 'warning')

                                    set_stage_complete('screenshots', 'screenshots_docs')
                                    console_state.log('[CAPTURE] Screenshot processing complete ✓', 'success')

                                except Exception as capture_error:
                                    console_state.log(f'[CAPTURE ERROR] {str(capture_error)}', 'error')
                                    console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                    set_stage_failed('screenshots', 'screenshots_docs')
                                    pipeline_failed = True
                                    raise

                                # Check if scenario itself succeeded before proceeding
                                if not result.success:
                                    console_state.log(f'[SCENARIO FAILED] {result.error_message}', 'error')
                                    set_stage_failed('docs', 'docs_audio')
                                    ui.notify(f'Scenario failed: {result.error_message}', type='negative')
                                    pipeline_failed = True
                                else:
                                    # ═══════════════════════════════════════════════════════════
                                    # STAGE 4: DOCUMENTATION GENERATION
                                    # ═══════════════════════════════════════════════════════════
                                    current_stage = 'docs'
                                    console_state.log('[DOCS] Generating documentation...', 'info')
                                    set_stage_active('docs')
                                    activate_connector('docs_audio')

                                    try:
                                        console_state.log('[DOCS] This may take a moment...', 'info')

                                        def run_doc_gen():
                                            doc_gen = DocumentationGenerator()
                                            return doc_gen.generate_all(result)

                                        outputs = await loop.run_in_executor(None, run_doc_gen)
                                        for output_type, path in outputs.items():
                                            console_state.log(f"  Generated: {path}", 'success')

                                        set_stage_complete('docs', 'docs_audio')
                                        console_state.log('[DOCS] Documentation generation complete ✓', 'success')
                                        await asyncio.sleep(0.2)

                                    except Exception as docs_error:
                                        console_state.log(f'[DOCS ERROR] {str(docs_error)}', 'error')
                                        console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                        set_stage_failed('docs', 'docs_audio')
                                        pipeline_failed = True
                                        # Continue to audio if possible

                                    # ═══════════════════════════════════════════════════════════
                                    # STAGE 5: AUDIO NARRATION
                                    # ═══════════════════════════════════════════════════════════
                                    current_stage = 'audio'
                                    if opt_audio.value:
                                        console_state.log('[AUDIO] Generating audio narration...', 'info')
                                        set_stage_active('audio')
                                        activate_connector('audio_cover')

                                        try:
                                            audio_service = AudioNarrationService()
                                            if audio_service.is_available():
                                                console_state.log('[AUDIO] Calling OpenAI TTS API (this may take 30-60 seconds)...', 'info')

                                                def run_audio_gen():
                                                    return audio_service.generate_all_narration(result, TTSVoice(voice_select.value))

                                                segments = await loop.run_in_executor(None, run_audio_gen)
                                                console_state.log(f"  Generated {len(segments)} audio segments", 'success')
                                                set_stage_complete('audio', 'audio_cover')
                                                console_state.log('[AUDIO] Audio generation complete ✓', 'success')
                                            else:
                                                console_state.log('[AUDIO WARNING] Audio service not available (OpenAI API key missing?)', 'warning')
                                                set_stage_complete('audio', 'audio_cover')

                                        except Exception as audio_error:
                                            console_state.log(f'[AUDIO ERROR] {str(audio_error)}', 'error')
                                            console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                            set_stage_failed('audio', 'audio_cover')
                                            # Audio failure is non-fatal, continue
                                    else:
                                        console_state.log('[AUDIO] Skipped (disabled in options)', 'info')
                                        set_stage_complete('audio', 'audio_cover')

                                    # ═══════════════════════════════════════════════════════════
                                    # STAGE 6: COVER PAGE GENERATION (before Video so video can use it)
                                    # ═══════════════════════════════════════════════════════════
                                    current_stage = 'cover'
                                    cover_path = None
                                    if not pipeline_failed:
                                        console_state.log('[COVER] Generating cover page...', 'info')
                                        set_stage_active('cover')
                                        activate_connector('cover_video')

                                        try:
                                            from PIL import Image, ImageDraw, ImageFont
                                            from pathlib import Path

                                            # Create cover page in scenario folder
                                            scenario_media_dir = testing_config.output_base / result.scenario_id
                                            scenario_media_dir.mkdir(parents=True, exist_ok=True)

                                            width, height = 1920, 1080
                                            img = Image.new('RGB', (width, height), (31, 41, 55))
                                            draw = ImageDraw.Draw(img)

                                            # TJM gold accent bar
                                            draw.rectangle([0, height//2 - 120, width, height//2 - 114], fill=(201, 162, 39))

                                            # Load fonts
                                            try:
                                                title_font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 64)
                                                subtitle_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 32)
                                                desc_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24)
                                            except Exception:
                                                title_font = ImageFont.load_default()
                                                subtitle_font = ImageFont.load_default()
                                                desc_font = ImageFont.load_default()

                                            # Add PTO Central logo if available
                                            logo_path = Path(__file__).parent.parent / 'static' / 'PTOCentralLogo.png'
                                            if logo_path.exists():
                                                logo = Image.open(logo_path)
                                                # Resize logo to fit
                                                logo_height = 100
                                                aspect = logo.width / logo.height
                                                logo_width = int(logo_height * aspect)
                                                logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                                                # Center horizontally at top
                                                logo_x = (width - logo_width) // 2
                                                img.paste(logo, (logo_x, 80), logo if logo.mode == 'RGBA' else None)

                                            # Draw scenario title
                                            title_text = scenario.name
                                            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
                                            title_width = title_bbox[2] - title_bbox[0]
                                            title_x = (width - title_width) // 2
                                            draw.text((title_x, height//2 - 80), title_text, fill=(255, 255, 255), font=title_font)

                                            # Draw description
                                            desc_text = scenario.description
                                            desc_bbox = draw.textbbox((0, 0), desc_text, font=desc_font)
                                            desc_width = desc_bbox[2] - desc_bbox[0]
                                            desc_x = (width - desc_width) // 2
                                            draw.text((desc_x, height//2 + 20), desc_text, fill=(180, 180, 180), font=desc_font)

                                            # Draw subtitle
                                            subtitle_text = "PTO Central Training"
                                            sub_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
                                            sub_width = sub_bbox[2] - sub_bbox[0]
                                            sub_x = (width - sub_width) // 2
                                            draw.text((sub_x, height//2 + 80), subtitle_text, fill=(201, 162, 39), font=subtitle_font)

                                            # Save cover in scenario folder
                                            cover_path = scenario_media_dir / f"{result.scenario_id}_cover.png"
                                            img.save(cover_path, 'PNG', quality=95)
                                            console_state.log(f"  Generated: {cover_path.name}", 'success')

                                            set_stage_complete('cover', 'cover_video')
                                            console_state.log('[COVER] Cover page generation complete ✓', 'success')

                                        except Exception as cover_error:
                                            console_state.log(f'[COVER ERROR] {str(cover_error)}', 'error')
                                            console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                            set_stage_failed('cover', 'cover_video')
                                            # Cover failure is non-fatal
                                    else:
                                        set_stage_complete('cover', 'cover_video')

                                    # ═══════════════════════════════════════════════════════════
                                    # STAGE 7: VIDEO PRODUCTION (uses cover + audio + screenshots)
                                    # ═══════════════════════════════════════════════════════════
                                    current_stage = 'video'
                                    if opt_video.value and not pipeline_failed:
                                        console_state.log('[VIDEO] Producing training video...', 'info')
                                        set_stage_active('video')
                                        activate_connector('video_complete')

                                        try:
                                            from services.video_producer import VideoProducer, MOVIEPY_AVAILABLE

                                            if MOVIEPY_AVAILABLE:
                                                console_state.log('[VIDEO] Creating training video with synced audio...', 'info')

                                                # All media goes into scenario folder
                                                scenario_media_dir = testing_config.output_base / result.scenario_id
                                                scenario_media_dir.mkdir(parents=True, exist_ok=True)

                                                # Use timeline-based production (raw video + timed audio overlay)
                                                timeline_path = testing_config.videos_dir / f'{result.scenario_id}.timeline.json'
                                                audio_dir = testing_config.audio_dir / result.scenario_id

                                                if timeline_path.exists():
                                                    console_state.log('[VIDEO] Using timeline-based production (best quality)', 'info')

                                                    def run_video_production():
                                                        video_producer = VideoProducer(scenario_media_dir)
                                                        return video_producer.create_video_from_timeline(
                                                            timeline_path=timeline_path,
                                                            audio_dir=audio_dir,
                                                            output_path=scenario_media_dir / f"{result.scenario_id}_training.mp4"
                                                        )
                                                else:
                                                    # Fallback to screenshot-based if no timeline
                                                    console_state.log('[VIDEO] No timeline found, using screenshot-based production', 'warning')
                                                    screenshots_dir = testing_config.screenshots_dir / result.scenario_id

                                                    def run_video_production():
                                                        video_producer = VideoProducer(scenario_media_dir)
                                                        return video_producer.create_video_from_scenario_outputs(
                                                            scenario_name=result.scenario_id,
                                                            screenshots_dir=screenshots_dir,
                                                            audio_dir=audio_dir,
                                                            output_path=scenario_media_dir / f"{result.scenario_id}_training.mp4"
                                                        )

                                                video_path = await loop.run_in_executor(None, run_video_production)
                                                console_state.log(f"  Generated: {video_path.name}", 'success')
                                                set_stage_complete('video', 'video_complete')
                                                console_state.log('[VIDEO] Video production complete ✓', 'success')
                                            else:
                                                console_state.log('[VIDEO WARNING] MoviePy not installed - video production skipped', 'warning')
                                                console_state.log('[VIDEO] Install with: pip install moviepy', 'info')
                                                set_stage_complete('video', 'video_complete')

                                        except Exception as video_error:
                                            console_state.log(f'[VIDEO ERROR] {str(video_error)}', 'error')
                                            console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                            set_stage_failed('video', 'video_complete')
                                            # Video failure is non-fatal
                                    else:
                                        console_state.log('[VIDEO] Skipped (disabled in options)', 'info')
                                        set_stage_complete('video', 'video_complete')

                                    # ═══════════════════════════════════════════════════════════
                                    # STAGE 8: COMPLETION
                                    # ═══════════════════════════════════════════════════════════
                                    current_stage = 'complete'
                                    if not pipeline_failed:
                                        set_stage_active('complete')
                                        await asyncio.sleep(0.3)
                                        set_stage_complete('complete')
                                        console_state.log('═' * 50, 'success')
                                        console_state.log('Scenario completed successfully!', 'success')
                                        ui.notify('Scenario completed!', type='positive')

                                # Record run regardless of success/failure
                                try:
                                    scenario_manager.record_run(result, scenario_select.value, scenario.name)
                                except Exception as record_error:
                                    console_state.log(f'[WARNING] Failed to record run: {str(record_error)}', 'warning')

                                progress_bar.value = 1.0
                                step_label.text = 'Complete' if not pipeline_failed else 'Failed'

                                # Refresh outputs tab
                                if console_state.refresh_outputs:
                                    try:
                                        console_state.refresh_outputs()
                                    except Exception as refresh_error:
                                        console_state.log(f'[WARNING] Failed to refresh outputs: {str(refresh_error)}', 'warning')

                            except Exception as e:
                                if not pipeline_failed:
                                    console_state.log(f'[FATAL ERROR in {current_stage}] {str(e)}', 'error')
                                    console_state.log(f'[TRACEBACK] {traceback.format_exc()}', 'error')
                                ui.notify(f'Error: {str(e)}', type='negative')
                                step_label.text = f'Failed at: {current_stage}'
                            finally:
                                console_state.is_running = False
                                run_btn.props(remove='loading')
                                console_state.log('═' * 50, 'info')

                        run_btn = ui.button('PRODUCE', icon='movie', on_click=run_scenario).classes('flex-grow').style(f'background-color: {TJM_GOLD} !important; color: white !important;')
                        console_state.run_button = run_btn

                        def stop_execution():
                            if console_state.request_cancel():
                                ui.notify('Stop requested - cancelling...', type='warning')
                            else:
                                ui.notify('No scenario running', type='info')

                        ui.button('Stop', icon='stop', on_click=stop_execution).props('outline color=red')

        # ═══════════════════════════════════════════════════════════════════
        # TAB 2: GENERATED OUTPUTS (Organized by Scenario Folder)
        # ═══════════════════════════════════════════════════════════════════
        with ui.tab_panel(outputs_tab):

            def get_scenario_outputs():
                """Scan all output directories and group by scenario name"""
                scenarios = {}

                # Scan screenshots directory
                screenshots_dir = testing_config.screenshots_dir
                if screenshots_dir.exists():
                    for scenario_dir in screenshots_dir.iterdir():
                        if scenario_dir.is_dir():
                            name = scenario_dir.name
                            if name not in scenarios:
                                scenarios[name] = {'screenshots': [], 'audio': [], 'videos': [], 'docs': [], 'mtime': 0}
                            scenarios[name]['screenshots'] = sorted(scenario_dir.glob('*.png'))
                            scenarios[name]['mtime'] = max(scenarios[name]['mtime'], scenario_dir.stat().st_mtime)

                # Scan audio directory
                audio_dir = testing_config.audio_dir
                if audio_dir.exists():
                    for scenario_dir in audio_dir.iterdir():
                        if scenario_dir.is_dir():
                            name = scenario_dir.name
                            if name not in scenarios:
                                scenarios[name] = {'screenshots': [], 'audio': [], 'videos': [], 'docs': [], 'mtime': 0}
                            scenarios[name]['audio'] = sorted(scenario_dir.glob('*.mp3'))
                            scenarios[name]['mtime'] = max(scenarios[name]['mtime'], scenario_dir.stat().st_mtime)

                # Scan videos directory (raw Playwright recordings)
                videos_dir = testing_config.videos_dir
                if videos_dir.exists():
                    for scenario_dir in videos_dir.iterdir():
                        if scenario_dir.is_dir():
                            name = scenario_dir.name
                            if name not in scenarios:
                                scenarios[name] = {'screenshots': [], 'audio': [], 'videos': [], 'docs': [], 'mtime': 0}
                            videos = list(scenario_dir.glob('*.webm')) + list(scenario_dir.glob('*.mp4'))
                            scenarios[name]['videos'] = sorted(videos, key=lambda x: x.stat().st_mtime, reverse=True)
                            if videos:
                                scenarios[name]['mtime'] = max(scenarios[name]['mtime'], scenario_dir.stat().st_mtime)

                # Also check scenario folders under output_base for final training videos
                if testing_config.output_base.exists():
                    reserved_dirs = {'screenshots', 'audio', 'videos', 'docs'}
                    for scenario_dir in testing_config.output_base.iterdir():
                        if scenario_dir.is_dir() and scenario_dir.name not in reserved_dirs:
                            name = scenario_dir.name
                            if name not in scenarios:
                                scenarios[name] = {'screenshots': [], 'audio': [], 'videos': [], 'docs': [], 'mtime': 0}
                            # Find training videos in scenario folder
                            scenario_videos = list(scenario_dir.glob('*_training.mp4'))
                            if scenario_videos:
                                # Prepend training videos to existing list (so they appear first)
                                existing_videos = scenarios[name].get('videos', [])
                                scenarios[name]['videos'] = scenario_videos + existing_videos
                                scenarios[name]['mtime'] = max(scenarios[name]['mtime'], scenario_dir.stat().st_mtime)

                # Scan docs directory (files named with scenario prefix)
                docs_dir = testing_config.docs_dir
                if docs_dir.exists():
                    for md_file in docs_dir.glob('*.md'):
                        # Try to match doc to scenario by name
                        name = md_file.stem.replace('_documentation', '').replace('-documentation', '')
                        if name in scenarios:
                            scenarios[name]['docs'].append(md_file)
                        else:
                            # Create entry for orphan docs
                            if name not in scenarios:
                                scenarios[name] = {'screenshots': [], 'audio': [], 'videos': [], 'docs': [], 'mtime': md_file.stat().st_mtime}
                            scenarios[name]['docs'].append(md_file)

                return scenarios

            # ═══════════════════════════════════════════════════════════════════
            # MEDIA VIEWER DIALOGS
            # ═══════════════════════════════════════════════════════════════════

            def confirm_delete_media(file_path: Path, media_type: str, on_deleted=None):
                """Show confirmation dialog and delete media file"""
                with ui.dialog() as confirm_dlg:
                    with ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
                        # Warning icon and title
                        with ui.row().classes('items-center gap-3 mb-4'):
                            ui.icon('warning', size='lg').style('color: #ef4444;')
                            ui.label('Delete Media File?').classes('text-lg font-bold text-red-400')

                        # File info
                        with ui.card().classes('w-full p-3 mb-4').style('background-color: #374151;'):
                            ui.label(f'{media_type}: {file_path.name}').classes('text-sm font-medium')
                            if file_path.exists():
                                size_kb = file_path.stat().st_size / 1024
                                if size_kb > 1024:
                                    ui.label(f'Size: {size_kb/1024:.1f} MB').classes('text-xs opacity-50')
                                else:
                                    ui.label(f'Size: {size_kb:.1f} KB').classes('text-xs opacity-50')

                        ui.label('This action cannot be undone.').classes('text-sm opacity-70 mb-4')

                        # Buttons
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Cancel', on_click=confirm_dlg.close).props('flat')

                            def do_delete():
                                try:
                                    if file_path.exists():
                                        file_path.unlink()
                                        ui.notify(f'{media_type} deleted', type='positive')
                                        confirm_dlg.close()
                                        if on_deleted:
                                            on_deleted()
                                    else:
                                        ui.notify('File not found', type='warning')
                                        confirm_dlg.close()
                                except Exception as e:
                                    ui.notify(f'Delete failed: {str(e)}', type='negative')

                            ui.button('Delete', icon='delete', on_click=do_delete).props('color=negative')

                confirm_dlg.open()

            def show_image_lightbox(scenario_name: str, images: list, start_index: int = 0):
                """Full-screen image lightbox with navigation"""
                current = {'index': start_index}

                with ui.dialog().props('maximized') as lightbox_dlg:
                    with ui.card().classes('w-full h-full p-0').style('background-color: rgba(0,0,0,0.95);'):
                        # Header bar
                        with ui.row().classes('w-full items-center justify-between p-4').style('background-color: rgba(31,41,55,0.9);'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('photo_library', size='md').style('color: #3b82f6;')
                                lightbox_title = ui.label(images[start_index].stem.replace('-', ' ').title()).classes('text-lg font-semibold')
                            with ui.row().classes('items-center gap-2'):
                                lightbox_counter = ui.label(f'{start_index + 1} / {len(images)}').classes('text-sm opacity-70')

                                def delete_current_image():
                                    img = images[current['index']]
                                    img_path = testing_config.output_base / 'screenshots' / scenario_name / img.name

                                    def on_deleted():
                                        # Remove from list and update view
                                        images.pop(current['index'])
                                        if not images:
                                            # No more images, close lightbox
                                            lightbox_dlg.close()
                                        else:
                                            # Adjust index if needed
                                            if current['index'] >= len(images):
                                                current['index'] = len(images) - 1
                                            update_lightbox_image()
                                            lightbox_counter.text = f"{current['index'] + 1} / {len(images)}"

                                    confirm_delete_media(img_path, 'Screenshot', on_deleted)

                                ui.button(icon='delete', on_click=delete_current_image).props('flat round').style('color: #ef4444;')
                                ui.button(icon='close', on_click=lightbox_dlg.close).props('flat round').style('color: white;')

                        # Main image area with navigation
                        with ui.row().classes('w-full flex-grow items-center justify-center relative').style('min-height: 70vh;'):
                            # Previous button
                            def go_prev():
                                if current['index'] > 0:
                                    current['index'] -= 1
                                    update_lightbox_image()

                            prev_btn = ui.button(icon='chevron_left', on_click=go_prev).props('flat round size=xl').classes('absolute left-4').style(f'color: {TJM_GOLD}; background-color: rgba(0,0,0,0.5);')

                            # Main image
                            lightbox_img = ui.image(f'/static/help/screenshots/{scenario_name}/{images[start_index].name}').classes('max-h-[75vh] max-w-[90vw] rounded-lg shadow-2xl')

                            # Next button
                            def go_next():
                                if current['index'] < len(images) - 1:
                                    current['index'] += 1
                                    update_lightbox_image()

                            next_btn = ui.button(icon='chevron_right', on_click=go_next).props('flat round size=xl').classes('absolute right-4').style(f'color: {TJM_GOLD}; background-color: rgba(0,0,0,0.5);')

                        def update_lightbox_image():
                            img = images[current['index']]
                            lightbox_img.source = f'/static/help/screenshots/{scenario_name}/{img.name}'
                            lightbox_title.text = img.stem.replace('-', ' ').title()
                            lightbox_counter.text = f"{current['index'] + 1} / {len(images)}"
                            # Update button visibility
                            prev_btn.set_visibility(current['index'] > 0)
                            next_btn.set_visibility(current['index'] < len(images) - 1)

                        # Thumbnail strip at bottom
                        with ui.scroll_area().classes('w-full').style('max-height: 120px; background-color: rgba(31,41,55,0.9);'):
                            with ui.row().classes('w-full gap-2 p-3 justify-center'):
                                for i, img in enumerate(images):
                                    def make_thumb_click(idx):
                                        def handler(e):
                                            current['index'] = idx
                                            update_lightbox_image()
                                        return handler
                                    thumb = ui.image(f'/static/help/screenshots/{scenario_name}/{img.name}').classes('w-24 h-16 object-cover rounded cursor-pointer hover:ring-2 transition-all').style(f'ring-color: {TJM_GOLD};')
                                    thumb.on('click', make_thumb_click(i))

                        # Initial button visibility
                        prev_btn.set_visibility(start_index > 0)
                        next_btn.set_visibility(start_index < len(images) - 1)

                lightbox_dlg.open()

            def show_audio_player_dialog(scenario_name: str, audio_path, step_number: int, total_steps: int):
                """Styled audio player dialog"""
                step_name = audio_path.stem.replace('-', ' ').replace('step ', 'Step ').title()

                with ui.dialog() as audio_dlg:
                    with ui.card().classes('p-6').style('background-color: #1f2937; min-width: 450px;'):
                        # Header
                        with ui.row().classes('w-full items-center justify-between mb-4'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('audiotrack', size='lg').style('color: #a855f7;')
                                ui.label('Audio Narration').classes('text-lg font-bold')
                            with ui.row().classes('items-center gap-1'):
                                def delete_audio():
                                    def on_deleted():
                                        audio_dlg.close()
                                    confirm_delete_media(audio_path, 'Audio', on_deleted)
                                ui.button(icon='delete', on_click=delete_audio).props('flat round dense').style('color: #ef4444;')
                                ui.button(icon='close', on_click=audio_dlg.close).props('flat round dense')

                        # Step info
                        with ui.card().classes('w-full p-4 mb-4').style('background-color: #374151;'):
                            with ui.row().classes('items-center gap-3 mb-3'):
                                ui.badge(str(step_number), color='purple').classes('text-lg px-3 py-1')
                                ui.label(step_name).classes('text-lg font-semibold')
                            ui.label(f'Step {step_number} of {total_steps}').classes('text-xs opacity-50')

                        # Audio player (larger, more prominent)
                        with ui.column().classes('w-full items-center mb-4'):
                            ui.icon('graphic_eq', size='3rem').style('color: #a855f7;').classes('mb-2 animate-pulse')
                            ui.audio(f'/static/help/audio/{scenario_name}/{audio_path.name}').classes('w-full').props('controls')

                        # File info
                        file_size = audio_path.stat().st_size / 1024
                        ui.label(f'{audio_path.name} ({file_size:.1f} KB)').classes('text-xs opacity-40 text-center w-full')

                        # Close button
                        with ui.row().classes('w-full justify-end mt-4'):
                            ui.button('Close', on_click=audio_dlg.close).style(f'background-color: {TJM_GOLD} !important; color: white !important;')

                audio_dlg.open()

            def show_video_player_dialog(scenario_name: str, video_path):
                """Full-screen video player dialog"""
                file_size = video_path.stat().st_size / (1024 * 1024)
                rel_path = video_path.relative_to(testing_config.output_base)

                with ui.dialog().props('maximized') as video_dlg:
                    with ui.card().classes('w-full h-full p-0').style('background-color: #000;'):
                        # Header bar
                        with ui.row().classes('w-full items-center justify-between p-4').style('background-color: rgba(31,41,55,0.95);'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('videocam', size='md').style('color: #f59e0b;')
                                ui.label(video_path.stem.replace('-', ' ').replace('_', ' ').title()).classes('text-lg font-semibold')
                            with ui.row().classes('items-center gap-3'):
                                ui.label(f'{file_size:.1f} MB').classes('text-sm opacity-50')

                                def delete_video():
                                    def on_deleted():
                                        video_dlg.close()
                                    confirm_delete_media(video_path, 'Video', on_deleted)

                                ui.button(icon='delete', on_click=delete_video).props('flat round').style('color: #ef4444;')
                                ui.button(icon='close', on_click=video_dlg.close).props('flat round').style('color: white;')

                        # Video player (centered, large)
                        with ui.column().classes('w-full flex-grow items-center justify-center p-4'):
                            ui.video(f'/static/help/{rel_path}').classes('max-h-[80vh] max-w-[95vw] rounded-lg shadow-2xl').props('controls autoplay')

                video_dlg.open()

            def show_scenario_folder(scenario_name: str, data: dict):
                """Open a dialog showing all outputs for a scenario - row-based layout with thumbnails on right"""
                from datetime import datetime

                # Check for final training video in the scenario output folder
                final_video_path = testing_config.output_base / scenario_name / f'{scenario_name}_training.mp4'
                has_final_video = final_video_path.exists()

                with ui.dialog() as folder_dlg:
                    with ui.card().classes('p-0').style('background-color: #1f2937; width: 900px; max-height: 90vh;'):
                        # Header - ALL CAPS title
                        with ui.row().classes('w-full items-center justify-between p-4').style(f'background-color: {TJM_GRAY};'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('folder_open', size='lg').style(f'color: {TJM_GOLD};')
                                ui.label(scenario_name.replace('-', ' ').upper()).classes('text-xl font-bold')
                            with ui.row().classes('items-center gap-2'):
                                # Content counts
                                total_items = len(data['videos']) + len(data['screenshots']) + len(data['audio']) + len(data['docs'])
                                if has_final_video:
                                    total_items += 1
                                ui.badge(f'{total_items} items', color='grey').props('dense outline')
                                ui.button(icon='close', on_click=folder_dlg.close).props('flat round').style('color: white;')

                        with ui.scroll_area().classes('w-full').style('max-height: 70vh;'):
                            with ui.column().classes('w-full p-4 gap-2'):

                                # 0. FINAL TRAINING VIDEO - Prominent at top
                                if has_final_video:
                                    ui.label('FINAL TRAINING VIDEO').classes('text-sm font-bold mb-2').style(f'color: {TJM_GOLD};')
                                    final_size = final_video_path.stat().st_size / (1024 * 1024)
                                    final_mtime = datetime.fromtimestamp(final_video_path.stat().st_mtime)

                                    def make_final_click(vp):
                                        def handler(e):
                                            show_video_player_dialog(scenario_name, vp)
                                        return handler

                                    with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style(f'background: linear-gradient(135deg, rgba(201, 162, 39, 0.15), rgba(201, 162, 39, 0.05)); border: 2px solid {TJM_GOLD}; ring-color: {TJM_GOLD};'):
                                        with ui.row().classes('w-full items-center gap-4'):
                                            # Star icon
                                            ui.icon('star', size='xl').style(f'color: {TJM_GOLD};')
                                            # Info (flex-grow)
                                            with ui.column().classes('flex-grow gap-1'):
                                                ui.label(f'{scenario_name.replace("-", " ").upper()} - READY TO DISTRIBUTE').classes('font-bold text-lg')
                                                with ui.row().classes('gap-4 text-sm opacity-70'):
                                                    ui.label(f'{final_size:.1f} MB')
                                                    ui.label(final_mtime.strftime('%b %d, %Y at %I:%M %p'))
                                            # Play button - prominent
                                            ui.button('PLAY VIDEO', icon='play_circle', on_click=make_final_click(final_video_path)).props('unelevated').style(f'background-color: {TJM_GOLD} !important; color: white !important; font-weight: bold;')

                                    ui.separator().classes('my-4')

                                # 1. RAW RECORDINGS - Row layout (source recordings from Playwright)
                                if data['videos']:
                                    ui.label('RAW RECORDINGS').classes('text-xs font-bold opacity-50 mb-1 mt-2')
                                    for video_path in data['videos']:
                                        file_size = video_path.stat().st_size / (1024 * 1024)
                                        mtime = datetime.fromtimestamp(video_path.stat().st_mtime)
                                        duration_est = file_size * 8  # Rough estimate: ~8 sec per MB

                                        def make_video_click(vp):
                                            def handler(e):
                                                show_video_player_dialog(scenario_name, vp)
                                            return handler

                                        with ui.row().classes('w-full p-3 items-center gap-4 rounded hover:bg-gray-700 transition-all cursor-pointer').style('border: 1px solid rgba(255,255,255,0.1);'):
                                            # Icon
                                            ui.icon('videocam', size='md').style('color: #f59e0b; opacity: 0.7;')
                                            # Info (flex-grow)
                                            with ui.column().classes('flex-grow gap-0'):
                                                ui.label(video_path.stem[:20] + '...' if len(video_path.stem) > 20 else video_path.stem).classes('font-medium text-sm opacity-70')
                                                with ui.row().classes('gap-4 text-xs opacity-50'):
                                                    ui.label(f'{file_size:.1f} MB')
                                                    ui.label(f'~{int(duration_est)}s')
                                                    ui.label(mtime.strftime('%b %d, %I:%M %p'))
                                            # Play button
                                            ui.button(icon='play_arrow', on_click=make_video_click(video_path)).props('flat round dense').style('color: #f59e0b; opacity: 0.7;')

                                # 2. SCREENSHOTS - Row layout with thumbnail on right
                                if data['screenshots']:
                                    ui.label('SCREENSHOTS').classes('text-xs font-bold opacity-50 mb-1 mt-4')
                                    imgs = data['screenshots']
                                    for i, img in enumerate(imgs):
                                        file_size = img.stat().st_size / 1024
                                        step_title = img.stem.replace('-', ' ').replace('step ', 'Step ').title()

                                        def make_img_click(idx):
                                            def handler(e):
                                                show_image_lightbox(scenario_name, imgs, idx)
                                            return handler

                                        with ui.row().classes('w-full p-3 items-center gap-4 rounded hover:bg-gray-700 transition-all cursor-pointer').style('border: 1px solid rgba(255,255,255,0.1);').on('click', make_img_click(i)):
                                            # Step number badge
                                            ui.badge(str(i + 1), color='blue').classes('text-sm')
                                            # Info (flex-grow)
                                            with ui.column().classes('flex-grow gap-0'):
                                                ui.label(step_title.upper()).classes('font-bold text-sm')
                                                ui.label(f'{file_size:.0f} KB • {img.suffix.upper()}').classes('text-xs opacity-60')
                                            # Thumbnail on right
                                            ui.image(f'/static/help/screenshots/{scenario_name}/{img.name}').classes('rounded').style('width: 100px; height: 56px; object-fit: cover;')

                                # 3. AUDIO - Row layout
                                if data['audio']:
                                    ui.label('AUDIO NARRATION').classes('text-xs font-bold opacity-50 mb-1 mt-4')
                                    audio_list = data['audio']
                                    for i, audio_path in enumerate(audio_list):
                                        file_size = audio_path.stat().st_size / 1024
                                        step_title = audio_path.stem.replace('-', ' ').replace('step ', 'Step ').title()
                                        # Estimate duration: ~12KB per second for MP3
                                        duration_est = file_size / 12

                                        def make_audio_click(ap, idx):
                                            def handler(e):
                                                show_audio_player_dialog(scenario_name, ap, idx + 1, len(audio_list))
                                            return handler

                                        with ui.row().classes('w-full p-3 items-center gap-4 rounded hover:bg-gray-700 transition-all cursor-pointer').style('border: 1px solid rgba(255,255,255,0.1);'):
                                            # Step number badge
                                            ui.badge(str(i + 1), color='purple').classes('text-sm')
                                            # Info (flex-grow)
                                            with ui.column().classes('flex-grow gap-0'):
                                                ui.label(step_title.upper()).classes('font-bold text-sm')
                                                ui.label(f'{file_size:.0f} KB • ~{int(duration_est)}s').classes('text-xs opacity-60')
                                            # Play button
                                            ui.button(icon='play_arrow', on_click=make_audio_click(audio_path, i)).props('flat round').style('color: #a855f7;')

                                # 4. DOCUMENTATION - Row layout
                                if data['docs']:
                                    ui.label('DOCUMENTATION').classes('text-xs font-bold opacity-50 mb-1 mt-4')
                                    for doc_path in data['docs']:
                                        file_size = doc_path.stat().st_size / 1024
                                        content = doc_path.read_text(encoding='utf-8')
                                        line_count = len(content.split('\n'))

                                        with ui.column().classes('w-full p-3 rounded').style('border: 1px solid rgba(255,255,255,0.1);'):
                                            with ui.expansion(doc_path.stem.upper(), icon='description').classes('w-full'):
                                                with ui.row().classes('text-xs opacity-60 mb-2'):
                                                    ui.label(f'{file_size:.1f} KB')
                                                    ui.label(f'{line_count} lines')
                                                ui.markdown(content).classes('prose prose-invert max-w-none')

                                # Empty state
                                if not any([data['videos'], data['screenshots'], data['audio'], data['docs'], has_final_video]):
                                    with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                                        ui.icon('folder_off', size='xl')
                                        ui.label('No outputs found for this scenario').classes('text-lg')

                        # Footer with Generate Video button
                        with ui.row().classes('w-full justify-between p-4').style('border-top: 1px solid rgba(255,255,255,0.1);'):
                            # Generate Video button (only if screenshots and audio exist)
                            if data['screenshots'] and data['audio']:
                                def generate_training_video(sname=scenario_name, sdata=data):
                                    generate_video_from_outputs(sname, sdata, folder_dlg)
                                ui.button('Generate Training Video', icon='movie', on_click=generate_training_video).props('outline').style(f'border-color: {TJM_GOLD}; color: {TJM_GOLD};')
                            else:
                                ui.label('Need screenshots + audio to generate video').classes('text-xs opacity-50')
                            ui.button('Close', on_click=folder_dlg.close).style(f'background-color: {TJM_GOLD} !important; color: white !important;')

                folder_dlg.open()

            def generate_video_from_outputs(scenario_name: str, data: dict, parent_dialog):
                """Generate a training video using timeline-based audio overlay on raw video"""
                try:
                    from services.video_producer import VideoProducer, MOVIEPY_AVAILABLE

                    if not MOVIEPY_AVAILABLE:
                        ui.notify('MoviePy not installed', type='negative')
                        return

                    # Show progress dialog
                    with ui.dialog() as progress_dlg:
                        with ui.card().classes('p-6').style('background-color: #1f2937; min-width: 500px;'):
                            with ui.row().classes('items-center gap-3 mb-4'):
                                ui.icon('movie', size='lg').style('color: #f59e0b;')
                                ui.label('Generating Training Video').classes('text-xl font-bold')

                            progress_label = ui.label('Initializing...').classes('text-sm opacity-70 mb-4')
                            progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full')

                            status_container = ui.column().classes('w-full mt-4')

                    progress_dlg.open()

                    async def do_generate():
                        try:
                            # Check for timeline file (preferred method)
                            timeline_path = testing_config.videos_dir / f'{scenario_name}.timeline.json'
                            audio_dir = testing_config.audio_dir / scenario_name
                            scenario_output_dir = testing_config.output_base / scenario_name
                            scenario_output_dir.mkdir(parents=True, exist_ok=True)

                            producer = VideoProducer(scenario_output_dir)

                            if timeline_path.exists():
                                progress_label.text = 'Using timeline-based production (raw video + synced audio)...'
                                progress_bar.value = 0.3
                                await asyncio.sleep(0.1)

                                # Run timeline-based video creation
                                import concurrent.futures
                                def run_production():
                                    return producer.create_video_from_timeline(
                                        timeline_path=timeline_path,
                                        audio_dir=audio_dir,
                                        output_path=scenario_output_dir / f'{scenario_name}_training.mp4'
                                    )

                                progress_label.text = 'Compiling video with synced narration (1-2 min)...'
                                progress_bar.value = 0.5

                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(run_production)
                                    output_path = future.result()
                            else:
                                # Fallback to screenshot-based if no timeline
                                progress_label.text = 'No timeline found - using screenshot-based production...'
                                progress_bar.value = 0.3
                                await asyncio.sleep(0.1)

                                from services.video_producer import VideoProject, VideoFrame, AnnotationConfig

                                screenshots = sorted(data['screenshots'], key=lambda x: x.name)
                                audio_files = sorted(data['audio'], key=lambda x: x.name)

                                # Create audio map
                                import re
                                audio_map = {}
                                for audio in audio_files:
                                    match = re.search(r'step-(\d+)', audio.stem)
                                    if match:
                                        audio_map[int(match.group(1))] = audio

                                frames = []
                                for i, screenshot in enumerate(screenshots):
                                    step_num = i + 1
                                    frame = VideoFrame(
                                        image_path=screenshot,
                                        audio_path=audio_map.get(step_num),
                                        duration=4.0 if step_num not in audio_map else 0,
                                        title=screenshot.stem.replace('-', ' ').title(),
                                        annotations=AnnotationConfig(step_number=step_num)
                                    )
                                    frames.append(frame)

                                project = VideoProject(
                                    title=scenario_name.replace('-', ' ').title(),
                                    scenario_name=scenario_name,
                                    frames=frames,
                                    output_path=scenario_output_dir / f'{scenario_name}_training.mp4'
                                )

                                progress_label.text = 'Compiling video (1-2 min)...'
                                progress_bar.value = 0.5

                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(producer.create_video, project)
                                    output_path = future.result()

                            progress_bar.value = 1.0
                            progress_label.text = 'Video generated successfully!'

                            with status_container:
                                status_container.clear()
                                with ui.card().classes('w-full p-4').style('background-color: #22c55e20; border: 1px solid #22c55e;'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('check_circle', size='md').style('color: #22c55e;')
                                        ui.label('Training video created!').classes('font-semibold')
                                    ui.label(f'Output: {output_path.name}').classes('text-sm opacity-70 mt-2')

                                with ui.row().classes('w-full justify-end mt-4 gap-2'):
                                    ui.button('Close', on_click=progress_dlg.close).props('flat')

                        except Exception as e:
                            import traceback
                            progress_bar.value = 0
                            progress_label.text = f'Error: {str(e)}'
                            print(f"Video generation error: {traceback.format_exc()}")
                            with status_container:
                                status_container.clear()
                                with ui.card().classes('w-full p-4').style('background-color: #ef444420; border: 1px solid #ef4444;'):
                                    ui.label(f'Failed: {str(e)}').classes('text-sm text-red-400')
                                ui.button('Close', on_click=progress_dlg.close).props('flat').classes('mt-4')

                    import asyncio
                    asyncio.create_task(do_generate())

                except Exception as e:
                    ui.notify(f'Error: {e}', type='negative')

            # Outputs display container
            outputs_container = ui.column().classes('w-full')

            def open_output_folder():
                """Open the output folder in file explorer"""
                import subprocess
                import platform
                folder_path = str(testing_config.output_base)
                try:
                    if platform.system() == 'Windows':
                        subprocess.Popen(['explorer', folder_path])
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.Popen(['open', folder_path])
                    else:  # Linux
                        subprocess.Popen(['xdg-open', folder_path])
                    ui.notify(f'Opened: {folder_path}', type='positive')
                except Exception as e:
                    ui.notify(f'Could not open folder: {e}', type='negative')

            # ═══════════════════════════════════════════════════════════════════
            # DIRECTORY-STYLE MEDIA BROWSER
            # Drill-down navigation: Scenarios → Media Types → Files
            # ═══════════════════════════════════════════════════════════════════

            # Navigation state
            nav_state = {
                'level': 'root',  # 'root', 'scenario', 'media_type'
                'scenario': None,
                'media_type': None,
            }

            # Main content container
            browser_container = ui.column().classes('w-full')

            def get_video_url(video_path: Path, scenario_name: str) -> str:
                """Get the correct URL for a video file"""
                # Check if it's in the videos subdirectory
                if 'videos' in str(video_path):
                    return f'/static/help/videos/{scenario_name}/{video_path.name}'
                # Otherwise it's in the scenario folder under output_base
                else:
                    rel_path = video_path.relative_to(testing_config.output_base)
                    return f'/static/help/{rel_path}'

            def generate_vtt_from_timeline(scenario_name: str) -> str:
                """Generate WebVTT content from timeline JSON and save to file"""
                import json
                timeline_path = testing_config.videos_dir / f'{scenario_name}.timeline.json'
                vtt_path = testing_config.videos_dir / f'{scenario_name}.vtt'

                if not timeline_path.exists():
                    return None

                try:
                    timeline_data = json.loads(timeline_path.read_text())
                    lines = ['WEBVTT', '']

                    for step in timeline_data.get('steps', []):
                        step_num = step.get('step_number', 0)
                        start = step.get('timestamp_start', 0)
                        end = step.get('timestamp_end', start + 2)
                        script = step.get('script', '')

                        # Format as VTT timestamps (HH:MM:SS.mmm)
                        def to_vtt_time(secs):
                            h = int(secs // 3600)
                            m = int((secs % 3600) // 60)
                            s = int(secs % 60)
                            ms = int((secs - int(secs)) * 1000)
                            return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'

                        lines.append(str(step_num))
                        lines.append(f'{to_vtt_time(start)} --> {to_vtt_time(end)}')
                        lines.append(script)
                        lines.append('')

                    vtt_content = '\n'.join(lines)
                    vtt_path.write_text(vtt_content, encoding='utf-8')
                    return f'/static/help/videos/{scenario_name}.vtt'
                except Exception as e:
                    print(f'Error generating VTT: {e}')
                    return None

            def render_breadcrumb():
                """Render breadcrumb navigation"""
                # Capture current state for closures
                current_scenario = nav_state['scenario']
                current_media_type = nav_state['media_type']

                with ui.row().classes('items-center gap-2 mb-4'):
                    # Home/Root
                    if nav_state['level'] == 'root':
                        ui.icon('folder', size='sm').style(f'color: {TJM_GOLD};')
                        ui.label('MEDIA LIBRARY').classes('font-bold')
                    else:
                        ui.button('MEDIA LIBRARY', icon='folder', on_click=lambda e: navigate_to('root')).props('flat dense no-caps').style(f'color: {TJM_GOLD};')

                    # Scenario level
                    if nav_state['level'] in ['scenario', 'media_type'] and current_scenario:
                        ui.icon('chevron_right', size='xs').classes('opacity-50')
                        if nav_state['level'] == 'scenario':
                            ui.icon('folder_open', size='sm').style('color: #3b82f6;')
                            ui.label(current_scenario.replace('-', ' ').upper()).classes('font-bold')
                        else:
                            # Capture scenario for closure
                            def go_to_scenario(e, sn=current_scenario):
                                navigate_to('scenario', sn)
                            ui.button(current_scenario.replace('-', ' ').upper(), icon='folder_open', on_click=go_to_scenario).props('flat dense no-caps').style('color: #3b82f6;')

                    # Media type level
                    if nav_state['level'] == 'media_type' and current_media_type:
                        ui.icon('chevron_right', size='xs').classes('opacity-50')
                        type_icons = {'videos': 'videocam', 'screenshots': 'photo_library', 'audio': 'audiotrack', 'docs': 'description', 'training': 'star'}
                        type_colors = {'videos': '#f59e0b', 'screenshots': '#3b82f6', 'audio': '#a855f7', 'docs': '#22c55e', 'training': TJM_GOLD}
                        ui.icon(type_icons.get(current_media_type, 'folder'), size='sm').style(f"color: {type_colors.get(current_media_type, '#888')};")
                        ui.label(current_media_type.upper()).classes('font-bold')

            def navigate_to(level: str, scenario: str = None, media_type: str = None):
                """Navigate to a specific level"""
                nav_state['level'] = level
                nav_state['scenario'] = scenario
                nav_state['media_type'] = media_type
                render_browser()

            def delete_scenario(scenario_name: str):
                """Delete all files for a scenario"""
                import shutil

                async def do_delete():
                    try:
                        # Delete screenshots folder
                        screenshots_dir = testing_config.screenshots_dir / scenario_name
                        if screenshots_dir.exists():
                            shutil.rmtree(screenshots_dir)

                        # Delete audio folder
                        audio_dir = testing_config.audio_dir / scenario_name
                        if audio_dir.exists():
                            shutil.rmtree(audio_dir)

                        # Delete video folder
                        video_dir = testing_config.videos_dir / scenario_name
                        if video_dir.exists():
                            shutil.rmtree(video_dir)

                        # Delete timeline, srt, vtt files
                        for ext in ['.timeline.json', '.srt', '.vtt']:
                            file_path = testing_config.videos_dir / f'{scenario_name}{ext}'
                            if file_path.exists():
                                file_path.unlink()

                        # Delete training video
                        training_path = testing_config.videos_dir / f'{scenario_name}_training.mp4'
                        if training_path.exists():
                            training_path.unlink()

                        # Delete docs
                        docs_path = testing_config.docs_dir / f'{scenario_name}.md'
                        if docs_path.exists():
                            docs_path.unlink()

                        ui.notify(f'Deleted scenario: {scenario_name}', type='positive')
                        navigate_to('root')
                    except Exception as e:
                        ui.notify(f'Delete failed: {e}', type='negative')
                    dialog.close()

                with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
                    ui.label('Delete Scenario?').classes('text-xl font-bold mb-4')
                    ui.label(f'This will permanently delete all files for "{scenario_name}":').classes('mb-2')
                    ui.label('• Screenshots, Audio, Videos, Documentation').classes('text-sm opacity-60 ml-4')
                    ui.label('This action cannot be undone.').classes('text-sm text-red-400 mt-4')
                    with ui.row().classes('w-full justify-end gap-2 mt-6'):
                        ui.button('Cancel', on_click=dialog.close).props('flat')
                        ui.button('Delete', on_click=do_delete).props('color=negative').style('background-color: #dc2626 !important;')
                dialog.open()

            def delete_file(file_path, file_type: str, scenario_name: str):
                """Delete a single file"""
                async def do_delete():
                    try:
                        if file_path.exists():
                            file_path.unlink()
                            ui.notify(f'Deleted: {file_path.name}', type='positive')
                        render_browser()
                    except Exception as e:
                        ui.notify(f'Delete failed: {e}', type='negative')
                    dialog.close()

                with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 350px;'):
                    ui.label('Delete File?').classes('text-xl font-bold mb-4')
                    ui.label(f'Delete "{file_path.name}"?').classes('mb-2')
                    ui.label('This action cannot be undone.').classes('text-sm text-red-400 mt-2')
                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dialog.close).props('flat')
                        ui.button('Delete', on_click=do_delete).props('color=negative').style('background-color: #dc2626 !important;')
                dialog.open()

            def render_browser():
                """Render the directory browser based on current navigation state"""
                browser_container.clear()
                scenarios = get_scenario_outputs()

                with browser_container:
                    # Breadcrumb
                    render_breadcrumb()

                    # ═══════════════════════════════════════════════════════════
                    # ROOT LEVEL - Show all scenarios as folders
                    # ═══════════════════════════════════════════════════════════
                    if nav_state['level'] == 'root':
                        if not scenarios:
                            with ui.card().classes('w-full p-8').style('background-color: #1f2937;'):
                                with ui.column().classes('w-full items-center justify-center'):
                                    ui.icon('folder_off', size='xl').style('color: #6b7280;')
                                    ui.label('No scenarios yet').classes('text-lg opacity-60 mt-2')
                                    ui.label('Run a scenario to generate media').classes('text-sm opacity-40')
                            return

                        # Sort by most recent
                        sorted_scenarios = sorted(scenarios.items(), key=lambda x: x[1]['mtime'], reverse=True)

                        with ui.column().classes('w-full gap-2'):
                            for scenario_name, data in sorted_scenarios:
                                # Count items
                                video_count = len(data['videos'])
                                screenshot_count = len(data['screenshots'])
                                audio_count = len(data['audio'])
                                doc_count = len(data['docs'])

                                # Check for training video (check all possible locations)
                                training_path = testing_config.output_base / scenario_name / f'{scenario_name}_training.mp4'
                                if not training_path.exists():
                                    training_path = testing_config.output_base / scenario_name / 'training_video.mp4'
                                if not training_path.exists():
                                    training_path = testing_config.videos_dir / f'{scenario_name}_training.mp4'
                                has_training = training_path.exists()
                                if has_training:
                                    video_count += 1

                                total = video_count + screenshot_count + audio_count + doc_count
                                from datetime import datetime
                                mtime = datetime.fromtimestamp(data['mtime'])

                                # Folder card
                                def make_click(sn):
                                    return lambda e: navigate_to('scenario', sn)

                                def make_delete(sn):
                                    return lambda e: (e.stop_propagation(), delete_scenario(sn))

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style(f'background-color: #1f2937; ring-color: {TJM_GOLD};').on('click', make_click(scenario_name)):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        # Folder icon with training star
                                        with ui.column().classes('items-center'):
                                            if has_training:
                                                ui.icon('star_rate', size='lg').style(f'color: {TJM_GOLD};')
                                            else:
                                                ui.icon('folder', size='lg').style('color: #3b82f6;')

                                        # Scenario name and info
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label(scenario_name.replace('-', ' ').upper()).classes('font-bold text-lg')
                                            ui.label(mtime.strftime('%b %d, %Y %I:%M %p')).classes('text-xs opacity-50')

                                        # Content counts
                                        with ui.row().classes('gap-2'):
                                            if video_count:
                                                ui.badge(f'{video_count}', color='amber').props('dense').tooltip('Videos')
                                            if screenshot_count:
                                                ui.badge(f'{screenshot_count}', color='blue').props('dense').tooltip('Screenshots')
                                            if audio_count:
                                                ui.badge(f'{audio_count}', color='purple').props('dense').tooltip('Audio')
                                            if doc_count:
                                                ui.badge(f'{doc_count}', color='green').props('dense').tooltip('Docs')

                                        ui.label(f'{total} items').classes('text-sm opacity-50')

                                        # Delete button
                                        ui.button(icon='delete', on_click=make_delete(scenario_name)).props('flat round dense').classes('opacity-50 hover:opacity-100').style('color: #ef4444;').tooltip('Delete Scenario')

                                        ui.icon('chevron_right').classes('opacity-50')

                    # ═══════════════════════════════════════════════════════════
                    # SCENARIO LEVEL - Show media type folders
                    # ═══════════════════════════════════════════════════════════
                    elif nav_state['level'] == 'scenario':
                        scenario_name = nav_state['scenario']
                        data = scenarios.get(scenario_name, {'videos': [], 'screenshots': [], 'audio': [], 'docs': []})

                        # Check for training video (check all possible locations)
                        training_path = testing_config.output_base / scenario_name / f'{scenario_name}_training.mp4'
                        if not training_path.exists():
                            training_path = testing_config.output_base / scenario_name / 'training_video.mp4'
                        if not training_path.exists():
                            training_path = testing_config.videos_dir / f'{scenario_name}_training.mp4'
                        has_training = training_path.exists()

                        with ui.column().classes('w-full gap-2'):
                            # Training Video - special prominent folder
                            if has_training:
                                def open_training():
                                    navigate_to('media_type', scenario_name, 'training')

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style(f'background: linear-gradient(135deg, rgba(201, 162, 39, 0.15), rgba(201, 162, 39, 0.05)); border: 2px solid {TJM_GOLD}; ring-color: {TJM_GOLD};').on('click', open_training):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('star', size='lg').style(f'color: {TJM_GOLD};')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label('TRAINING VIDEO').classes('font-bold text-lg')
                                            file_size = training_path.stat().st_size / (1024 * 1024)
                                            ui.label(f'Ready to distribute • {file_size:.1f} MB').classes('text-xs opacity-60')
                                        ui.badge('FINAL', color='amber').props('dense')
                                        ui.icon('chevron_right').style(f'color: {TJM_GOLD};')

                            # Videos folder
                            if data['videos']:
                                def open_videos():
                                    navigate_to('media_type', scenario_name, 'videos')

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style('background-color: #1f2937; ring-color: #f59e0b;').on('click', open_videos):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('videocam', size='lg').style('color: #f59e0b;')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label('RAW RECORDINGS').classes('font-bold')
                                            ui.label('Playwright screen recordings').classes('text-xs opacity-50')
                                        ui.badge(f'{len(data["videos"])}', color='amber').props('dense')
                                        ui.icon('chevron_right').classes('opacity-50')

                            # Screenshots folder
                            if data['screenshots']:
                                def open_screenshots():
                                    navigate_to('media_type', scenario_name, 'screenshots')

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style('background-color: #1f2937; ring-color: #3b82f6;').on('click', open_screenshots):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('photo_library', size='lg').style('color: #3b82f6;')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label('SCREENSHOTS').classes('font-bold')
                                            ui.label('Step-by-step captures').classes('text-xs opacity-50')
                                        ui.badge(f'{len(data["screenshots"])}', color='blue').props('dense')
                                        ui.icon('chevron_right').classes('opacity-50')

                            # Audio folder
                            if data['audio']:
                                def open_audio():
                                    navigate_to('media_type', scenario_name, 'audio')

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style('background-color: #1f2937; ring-color: #a855f7;').on('click', open_audio):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('audiotrack', size='lg').style('color: #a855f7;')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label('AUDIO NARRATION').classes('font-bold')
                                            ui.label('TTS voice narration files').classes('text-xs opacity-50')
                                        ui.badge(f'{len(data["audio"])}', color='purple').props('dense')
                                        ui.icon('chevron_right').classes('opacity-50')

                            # Docs folder
                            if data['docs']:
                                def open_docs():
                                    navigate_to('media_type', scenario_name, 'docs')

                                with ui.card().classes('w-full p-4 cursor-pointer hover:ring-2 transition-all').style('background-color: #1f2937; ring-color: #22c55e;').on('click', open_docs):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('description', size='lg').style('color: #22c55e;')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label('DOCUMENTATION').classes('font-bold')
                                            ui.label('Markdown guides').classes('text-xs opacity-50')
                                        ui.badge(f'{len(data["docs"])}', color='green').props('dense')
                                        ui.icon('chevron_right').classes('opacity-50')

                    # ═══════════════════════════════════════════════════════════
                    # MEDIA TYPE LEVEL - Show actual files
                    # ═══════════════════════════════════════════════════════════
                    elif nav_state['level'] == 'media_type':
                        scenario_name = nav_state['scenario']
                        media_type = nav_state['media_type']
                        data = scenarios.get(scenario_name, {'videos': [], 'screenshots': [], 'audio': [], 'docs': []})

                        # Training Video - inline player
                        if media_type == 'training':
                            # Check all possible training video locations
                            training_path = testing_config.output_base / scenario_name / f'{scenario_name}_training.mp4'
                            if not training_path.exists():
                                training_path = testing_config.output_base / scenario_name / 'training_video.mp4'
                            if not training_path.exists():
                                training_path = testing_config.videos_dir / f'{scenario_name}_training.mp4'

                            if training_path.exists():
                                file_size = training_path.stat().st_size / (1024 * 1024)
                                from datetime import datetime
                                mtime = datetime.fromtimestamp(training_path.stat().st_mtime)

                                def delete_training(tp, sn):
                                    return lambda e: delete_file(tp, 'training', sn)

                                with ui.card().classes('w-full p-4').style(f'background: linear-gradient(135deg, rgba(201, 162, 39, 0.15), rgba(201, 162, 39, 0.05)); border: 2px solid {TJM_GOLD};'):
                                    with ui.row().classes('w-full items-center justify-between mb-4'):
                                        with ui.row().classes('items-center gap-3'):
                                            ui.icon('star', size='lg').style(f'color: {TJM_GOLD};')
                                            with ui.column().classes('gap-0'):
                                                ui.label('TRAINING VIDEO').classes('font-bold text-lg')
                                                ui.label(f'{file_size:.1f} MB • {mtime.strftime("%b %d, %Y %I:%M %p")}').classes('text-xs opacity-60')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.badge('READY TO DISTRIBUTE', color='amber').props('dense')
                                            ui.button(icon='delete', on_click=delete_training(training_path, scenario_name)).props('flat round dense').style('color: #ef4444;').tooltip('Delete Training Video')

                                    # Inline video player - build URL with forward slashes
                                    rel_path = training_path.relative_to(testing_config.output_base)
                                    video_url = f'/static/help/{rel_path.as_posix()}'
                                    ui.video(video_url).classes('w-full rounded-lg').style('max-height: 500px;').props('controls')

                        # Raw Videos with Timeline Captions
                        elif media_type == 'videos':
                            # Try to load timeline for captions
                            import json
                            timeline_path = testing_config.videos_dir / f'{scenario_name}.timeline.json'
                            timeline_data = None
                            total_duration = 0
                            if timeline_path.exists():
                                try:
                                    timeline_data = json.loads(timeline_path.read_text())
                                    total_duration = timeline_data.get('total_duration', 0)
                                except:
                                    pass

                            # Filter out training videos (they have their own section)
                            raw_videos = [v for v in data['videos'] if '_training' not in v.name]

                            if not raw_videos:
                                with ui.card().classes('w-full p-6').style('background-color: #1f2937;'):
                                    with ui.column().classes('w-full items-center'):
                                        ui.icon('videocam_off', size='xl').classes('opacity-40')
                                        ui.label('No raw recordings found').classes('opacity-60 mt-2')
                                        ui.label('Run scenario to generate recordings').classes('text-xs opacity-40')

                            for video_path in raw_videos:
                                file_size = video_path.stat().st_size / (1024 * 1024)
                                from datetime import datetime
                                mtime = datetime.fromtimestamp(video_path.stat().st_mtime)

                                # Format duration as MM:SS
                                dur_mins = int(total_duration // 60)
                                dur_secs = int(total_duration % 60)
                                duration_str = f'{dur_mins}:{dur_secs:02d}' if total_duration > 0 else ''

                                # Build video URL directly
                                video_url = f'/static/help/videos/{scenario_name}/{video_path.name}'

                                with ui.card().classes('w-full mb-4 p-4').style('background-color: #1f2937;'):
                                    # Header row with info
                                    with ui.row().classes('w-full items-center justify-between mb-4'):
                                        with ui.row().classes('items-center gap-3'):
                                            ui.icon('videocam', size='md').style('color: #f59e0b;')
                                            with ui.column().classes('gap-0'):
                                                ui.label(video_path.name).classes('font-medium')
                                                info_parts = [f'{file_size:.1f} MB']
                                                if duration_str:
                                                    info_parts.append(duration_str)
                                                info_parts.append(mtime.strftime('%b %d, %I:%M %p'))
                                                ui.label(' • '.join(info_parts)).classes('text-xs opacity-50')
                                        with ui.row().classes('items-center gap-2'):
                                            if duration_str:
                                                ui.badge(duration_str, color='amber').props('dense').tooltip('Duration')
                                            if timeline_data:
                                                ui.badge('CAPTIONS', color='green').props('dense outline')

                                            # Delete button for video
                                            def make_video_delete(vp, sn):
                                                return lambda e: delete_file(vp, 'video', sn)
                                            ui.button(icon='delete', on_click=make_video_delete(video_path, scenario_name)).props('flat round dense').style('color: #ef4444;').tooltip('Delete Video')

                                    # VIDEO PLAYER - simple and clear
                                    ui.video(video_url).classes('w-full rounded-lg').style(
                                        'height: 400px; background: #000; border: 2px solid #374151;'
                                    ).props('controls')

                                    # Transcript timing below video
                                    if timeline_data:
                                        ui.separator().classes('my-4')
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('subtitles', size='sm').style(f'color: {TJM_GOLD};')
                                            ui.label('TRANSCRIPT TIMING').classes('text-sm font-bold').style(f'color: {TJM_GOLD};')
                                        ui.label('Compare these timestamps to the video playback').classes('text-xs opacity-50 mb-3')

                                        with ui.scroll_area().classes('w-full').style('max-height: 180px; background: #374151; border-radius: 8px; padding: 12px;'):
                                            for step in timeline_data.get('steps', []):
                                                step_num = step.get('step_number', 0)
                                                start_time = step.get('timestamp_start', 0)
                                                script = step.get('script', '')

                                                mins = int(start_time // 60)
                                                secs = int(start_time % 60)
                                                time_str = f'{mins}:{secs:02d}'

                                                with ui.row().classes('w-full items-start gap-3 mb-2 pb-2').style('border-bottom: 1px solid rgba(255,255,255,0.1);'):
                                                    ui.badge(time_str, color='amber').props('dense').style('min-width: 50px;')
                                                    ui.label(f'Step {step_num}: {script}').classes('text-sm opacity-80')

                        # Screenshots
                        elif media_type == 'screenshots':
                            with ui.row().classes('w-full flex-wrap gap-3'):
                                for i, img_path in enumerate(data['screenshots']):
                                    img_name = img_path.name

                                    def make_lightbox(idx):
                                        return lambda e: show_image_lightbox(scenario_name, data['screenshots'], idx)

                                    def make_img_delete(ip, sn):
                                        return lambda e: (e.stop_propagation(), delete_file(ip, 'screenshot', sn))

                                    with ui.card().classes('p-2 cursor-pointer hover:ring-2 transition-all relative').style(f'background-color: #1f2937; ring-color: {TJM_GOLD};').on('click', make_lightbox(i)):
                                        ui.image(f'/static/help/screenshots/{scenario_name}/{img_name}').classes('rounded').style('width: 200px; height: 113px; object-fit: cover;')
                                        with ui.row().classes('w-full items-center justify-between mt-1'):
                                            ui.label(img_path.stem.replace('-', ' ').title()).classes('text-xs opacity-70 flex-grow')
                                            ui.button(icon='delete', on_click=make_img_delete(img_path, scenario_name)).props('flat round dense size=xs').style('color: #ef4444;').tooltip('Delete')

                        # Audio
                        elif media_type == 'audio':
                            for audio_path in data['audio']:
                                file_size = audio_path.stat().st_size / 1024

                                def make_audio_delete(ap, sn):
                                    return lambda e: delete_file(ap, 'audio', sn)

                                with ui.card().classes('w-full mb-2 p-4').style('background-color: #1f2937;'):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        ui.icon('audiotrack', size='md').style('color: #a855f7;')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label(audio_path.stem.replace('-', ' ').title()).classes('font-medium')
                                            ui.label(f'{file_size:.0f} KB').classes('text-xs opacity-50')
                                        # Inline audio player
                                        ui.audio(f'/static/help/audio/{scenario_name}/{audio_path.name}').props('controls').style('height: 40px;')
                                        # Delete button
                                        ui.button(icon='delete', on_click=make_audio_delete(audio_path, scenario_name)).props('flat round dense').style('color: #ef4444;').tooltip('Delete Audio')

                        # Documentation
                        elif media_type == 'docs':
                            for doc_path in data['docs']:
                                content = doc_path.read_text(encoding='utf-8')
                                line_count = len(content.split('\n'))

                                def make_doc_delete(dp, sn):
                                    return lambda e: delete_file(dp, 'doc', sn)

                                with ui.card().classes('w-full mb-3 p-0').style('background-color: #1f2937;'):
                                    with ui.row().classes('w-full items-center justify-between p-2').style('border-bottom: 1px solid #374151;'):
                                        with ui.expansion(f'{doc_path.stem.upper()} ({line_count} lines)', icon='description').classes('flex-grow'):
                                            ui.markdown(content).classes('prose prose-invert max-w-none p-4')
                                        ui.button(icon='delete', on_click=make_doc_delete(doc_path, scenario_name)).props('flat round dense').style('color: #ef4444;').tooltip('Delete Doc')

            def refresh_outputs():
                """Refresh the browser"""
                render_browser()

            # ═══════════════════════════════════════════════════════════════════
            # HEADER
            # ═══════════════════════════════════════════════════════════════════
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('folder_special', size='lg').style(f'color: {TJM_GOLD};')
                    ui.label('MEDIA BROWSER').classes('text-xl font-bold')

                with ui.row().classes('items-center gap-2'):
                    ui.button('Open Folder', icon='folder_open', on_click=open_output_folder).props('outline dense').style(f'border-color: {TJM_GOLD}; color: {TJM_GOLD};')
                    ui.button('Refresh', icon='refresh', on_click=refresh_outputs).props('flat dense').style(f'color: {TJM_GOLD};')

            # ═══════════════════════════════════════════════════════════════════
            # BROWSER CONTENT (Scrollable)
            # ═══════════════════════════════════════════════════════════════════
            with ui.scroll_area().classes('w-full').style('max-height: calc(100vh - 300px);'):
                render_browser()

            console_state.refresh_outputs = refresh_outputs

        # ═══════════════════════════════════════════════════════════════════
        # TAB 3: CUSTOM SCENARIOS
        # ═══════════════════════════════════════════════════════════════════
        with ui.tab_panel(custom_tab):

            def show_template_dialog():
                """Show the markdown template in a dialog"""
                template_file = TEMPLATES_DIR / 'scenario_template.md'
                if template_file.exists():
                    content = template_file.read_text(encoding='utf-8')
                else:
                    content = "Template file not found. Check config/scenarios/templates/"
                with ui.dialog() as dlg:
                    with ui.card().classes('p-6').style('background-color: #1f2937; min-width: 900px; max-width: 1100px; max-height: 85vh;'):
                        with ui.row().classes('w-full items-center justify-between mb-4'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('description', size='lg').style(f'color: {TJM_GOLD};')
                                ui.label('Scenario Template').classes('text-xl font-bold')
                            ui.button(icon='close', on_click=dlg.close).props('flat round')
                        ui.label('Use this template with Claude Desktop to generate test scenarios').classes('text-sm opacity-60 mb-4')
                        ui.separator()
                        with ui.scroll_area().classes('w-full').style('max-height: 55vh;'):
                            with ui.card().classes('w-full p-4').style('background-color: #374151;'):
                                ui.markdown(content).classes('w-full prose prose-invert max-w-none')
                        ui.separator().classes('my-4')
                        with ui.row().classes('w-full justify-between items-center'):
                            def copy_template():
                                ui.run_javascript(f'navigator.clipboard.writeText({repr(content)})')
                                ui.notify('Template copied to clipboard!', type='positive')
                            ui.button('Copy to Clipboard', icon='content_copy', on_click=copy_template).props('outline').style(f'border-color: {TJM_GOLD}; color: {TJM_GOLD};')
                            ui.button('Close', on_click=dlg.close).style(f'background-color: {TJM_GOLD} !important; color: white !important;')
                dlg.open()

            def show_scenario_details(scenario: CustomScenario):
                """Show detailed view of a custom scenario"""
                with ui.dialog() as dlg:
                    with ui.card().classes('p-6').style('background-color: #1f2937; min-width: 600px; max-width: 800px; max-height: 85vh;'):
                        with ui.row().classes('w-full items-center justify-between mb-4'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('science', size='lg').style(f'color: {TJM_GOLD};')
                                ui.label(scenario.name).classes('text-xl font-bold')
                            ui.button(icon='close', on_click=dlg.close).props('flat round')
                        with ui.row().classes('gap-2 mb-4'):
                            ui.badge(scenario.required_role, color='blue')
                            ui.badge(scenario.source, color='purple')
                            for tag in scenario.tags[:3]:
                                ui.badge(tag, color='grey').props('outline')
                        ui.label(scenario.description).classes('text-sm opacity-70 mb-4')
                        ui.separator()
                        ui.label('Steps').classes('font-semibold mt-4 mb-2')
                        with ui.scroll_area().classes('w-full').style('max-height: 300px;'):
                            for i, step in enumerate(scenario.steps):
                                with ui.card().classes('w-full mb-2 p-3').style('background-color: #374151;'):
                                    with ui.row().classes('items-center gap-3'):
                                        ui.badge(str(i + 1), color='amber').classes('text-sm')
                                        with ui.column().classes('gap-0 flex-grow'):
                                            ui.label(step.get('title', f'Step {i+1}')).classes('font-medium')
                                            with ui.row().classes('gap-2'):
                                                ui.badge(step.get('action', 'screenshot'), color='grey').props('dense outline')
                                                if step.get('selector'):
                                                    selector_text = step['selector'][:40] + '...' if len(step.get('selector', '')) > 40 else step.get('selector', '')
                                                    ui.label(selector_text).classes('text-xs opacity-50')
                        ui.separator().classes('my-4')
                        with ui.row().classes('w-full justify-end'):
                            ui.button('Close', on_click=dlg.close).style(f'background-color: {TJM_GOLD} !important; color: white !important;')
                dlg.open()

            # Custom scenarios container
            custom_container = ui.column().classes('w-full')

            def refresh_custom_scenarios():
                """Refresh the custom scenarios display"""
                custom_container.clear()
                with custom_container:
                    with ui.row().classes('w-full items-center justify-between mb-4'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('extension', size='lg').style(f'color: {TJM_GOLD};')
                            ui.label('CUSTOM SCENARIOS').classes('text-xl font-bold')
                        ui.button('View Template', icon='description', on_click=show_template_dialog).props('flat').style(f'color: {TJM_GOLD};')

                    with ui.row().classes('w-full gap-4'):

                        # Left: Create new scenario
                        with ui.card().classes('flex-1 p-4').style('background-color: #1f2937; min-width: 400px;'):
                            with ui.tabs().classes('w-full') as inner_tabs:
                                quick_tab = ui.tab('Quick Builder', icon='bolt')
                                import_tab = ui.tab('Import Markdown', icon='upload_file')

                            with ui.tab_panels(inner_tabs, value=quick_tab).classes('w-full'):

                                with ui.tab_panel(quick_tab):
                                    ui.label('Quick Scenario Builder').classes('font-semibold mb-2')
                                    ui.label('Create a simple scenario with one step per line').classes('text-xs opacity-60 mb-3')

                                    scenario_name_input = ui.input('Scenario Name', placeholder='e.g., Test Login Flow').classes('w-full mb-2')
                                    scenario_role_select = ui.select(
                                        options={'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'SuperAdmin'},
                                        value='employee',
                                        label='Required Role'
                                    ).classes('w-full mb-2')
                                    scenario_steps_input = ui.textarea(
                                        'Steps (one per line)',
                                        placeholder="click: button:has-text('Login')\nscreenshot: Dashboard loaded\nfill: #email | user@example.com\nnavigate: /dashboard\nwait: 2"
                                    ).props('outlined autogrow').classes('w-full mb-3').style('min-height: 150px;')

                                    with ui.row().classes('w-full gap-2'):
                                        ui.label('Format: action: details').classes('text-xs opacity-50 flex-grow')

                                        def create_quick_scenario_handler():
                                            name = scenario_name_input.value
                                            steps = scenario_steps_input.value
                                            role = scenario_role_select.value
                                            if not name or not steps:
                                                ui.notify('Please enter a name and steps', type='warning')
                                                return
                                            scenario = create_quick_scenario(name, steps, role)
                                            if scenario:
                                                scenario_manager.add_scenario(scenario)
                                                ui.notify(f'Scenario "{name}" created with {len(scenario.steps)} steps!', type='positive')
                                                scenario_name_input.value = ''
                                                scenario_steps_input.value = ''
                                                refresh_custom_scenarios()
                                            else:
                                                ui.notify('Failed to parse steps. Check format.', type='negative')

                                        ui.button('Create Scenario', icon='add', on_click=create_quick_scenario_handler).style(f'background-color: {TJM_GOLD} !important; color: white !important;')

                                with ui.tab_panel(import_tab):
                                    ui.label('Import from Markdown').classes('font-semibold mb-2')
                                    ui.label('Paste markdown content or upload a .md file').classes('text-xs opacity-60 mb-3')

                                    md_content_input = ui.textarea(
                                        'Markdown Content',
                                        placeholder="# Scenario: My Test\n\n**Description:** Test description\n**Role:** employee\n**Tags:** regression, bug-fix\n\n## Steps\n\n### Step 1: Login\n- **Action:** navigate\n- **URL:** /\n- **Description:** Go to login page"
                                    ).props('outlined autogrow').classes('w-full mb-3').style('min-height: 200px;')

                                    with ui.row().classes('w-full gap-2 items-center'):
                                        def import_markdown_handler():
                                            content = md_content_input.value
                                            if not content:
                                                ui.notify('Please enter markdown content', type='warning')
                                                return
                                            scenario = scenario_manager.import_from_markdown(content)
                                            if scenario:
                                                ui.notify(f'Imported "{scenario.name}" with {len(scenario.steps)} steps!', type='positive')
                                                md_content_input.value = ''
                                                refresh_custom_scenarios()
                                            else:
                                                ui.notify('Failed to parse markdown. Check format.', type='negative')

                                        ui.button('Import', icon='download', on_click=import_markdown_handler).style(f'background-color: {TJM_GOLD} !important; color: white !important;')
                                        ui.label('or').classes('opacity-50')

                                        async def handle_upload(e):
                                            if e.content:
                                                content = e.content.read().decode('utf-8')
                                                scenario = scenario_manager.import_from_markdown(content, e.name)
                                                if scenario:
                                                    ui.notify(f'Imported "{scenario.name}" from {e.name}!', type='positive')
                                                    refresh_custom_scenarios()
                                                else:
                                                    ui.notify('Failed to parse uploaded file', type='negative')

                                        ui.upload(label='Upload .md', on_upload=handle_upload, auto_upload=True).props('accept=".md,.txt" flat dense').classes('w-32')

                        # Right: Saved scenarios list
                        with ui.card().classes('flex-1 p-4').style('background-color: #1f2937; min-width: 400px;'):
                            ui.label('Saved Scenarios').classes('font-semibold mb-3')

                            custom_list = scenario_manager.get_all_scenarios()
                            if custom_list:
                                with ui.scroll_area().classes('w-full max-h-[400px]'):
                                    for scenario in sorted(custom_list, key=lambda s: s.created_at, reverse=True):
                                        with ui.card().classes('w-full mb-2 p-3').style('background-color: #374151;'):
                                            with ui.row().classes('w-full items-center gap-3'):
                                                icon_name = 'upload_file' if scenario.source == 'markdown_import' else 'bolt'
                                                ui.icon(icon_name, size='sm').style(f'color: {TJM_GOLD};')
                                                with ui.column().classes('flex-grow gap-0'):
                                                    ui.label(scenario.name).classes('font-medium')
                                                    with ui.row().classes('gap-2 items-center'):
                                                        ui.badge(scenario.required_role, color='blue').props('dense')
                                                        ui.label(f'{len(scenario.steps)} steps').classes('text-xs opacity-50')
                                                        if scenario.run_count > 0:
                                                            color = 'green' if scenario.last_success else 'red'
                                                            ui.badge(f'{scenario.run_count} runs', color=color).props('dense outline')
                                                with ui.row().classes('gap-1'):
                                                    def view_fn(s=scenario):
                                                        show_scenario_details(s)
                                                    def delete_fn(s=scenario):
                                                        scenario_manager.remove_scenario(s.id)
                                                        ui.notify(f'Deleted: {s.name}', type='info')
                                                        refresh_custom_scenarios()
                                                    ui.button(icon='visibility', on_click=lambda e, s=scenario: show_scenario_details(s)).props('flat round dense').style('color: #60a5fa;')
                                                    ui.button(icon='delete', on_click=lambda e, s=scenario: (scenario_manager.remove_scenario(s.id), ui.notify(f'Deleted: {s.name}', type='info'), refresh_custom_scenarios())).props('flat round dense').style('color: #ef4444;')
                            else:
                                with ui.column().classes('items-center justify-center py-8 opacity-50'):
                                    ui.icon('folder_open', size='xl')
                                    ui.label('No custom scenarios yet').classes('text-sm')
                                    ui.label('Create one using the builder or import markdown').classes('text-xs')

            refresh_custom_scenarios()

        # ═══════════════════════════════════════════════════════════════════
        # TAB 4: RUN HISTORY
        # ═══════════════════════════════════════════════════════════════════
        with ui.tab_panel(history_tab):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('history', size='lg').style(f'color: {TJM_GOLD};')
                    ui.label('RUN HISTORY').classes('text-xl font-bold')

            history_container = ui.column().classes('w-full')

            def refresh_history():
                history_container.clear()
                with history_container:
                    history = scenario_manager.get_history(50)
                    if history:
                        with ui.scroll_area().classes('w-full').style('max-height: 600px;'):
                            for run in history:
                                with ui.card().classes('w-full mb-2 p-4').style('background-color: #1f2937;'):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        icon_name = 'check_circle' if run.success else 'error'
                                        icon_color = '#22c55e' if run.success else '#ef4444'
                                        ui.icon(icon_name, size='md').style(f'color: {icon_color};')
                                        with ui.column().classes('flex-grow gap-0'):
                                            ui.label(run.scenario_name).classes('font-medium text-lg')
                                            with ui.row().classes('gap-4 items-center mt-1'):
                                                try:
                                                    run_date = datetime.fromisoformat(run.run_at)
                                                    formatted = run_date.strftime('%b %d, %Y at %H:%M')
                                                except:
                                                    formatted = run.run_at[:16]
                                                ui.label(formatted).classes('text-sm opacity-60')
                                                ui.label(f'{run.steps_completed}/{run.total_steps} steps').classes('text-sm opacity-60')
                                                ui.label(f'{run.duration:.1f}s').classes('text-sm opacity-60')
                                        if run.success:
                                            ui.badge('Success', color='green')
                                        else:
                                            ui.badge('Failed', color='red')
                                    if run.error_message:
                                        with ui.row().classes('w-full mt-2 pl-10'):
                                            ui.label(f'Error: {run.error_message}').classes('text-sm text-red-400')
                    else:
                        with ui.column().classes('items-center justify-center py-16 opacity-50'):
                            ui.icon('history', size='3rem')
                            ui.label('No run history yet').classes('text-lg mt-4')
                            ui.label('Run some scenarios to see history here').classes('text-sm')

            refresh_history()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE FUNCTION FOR MAIN.PY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

def testing_console_page():
    """Page function to be called from main.py route"""
    from nicegui_app.components.theme import apply_dark_mode
    from nicegui_app.components.header import page_header

    apply_dark_mode()

    with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
        page_header(title='MEDIA STUDIO', show_back=False)
        create_testing_console_page()
