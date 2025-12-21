"""
PTO Central - Custom Scenario Manager
Handles storage, parsing, and management of custom test scenarios.

Scenarios can be:
1. Created via the UI form
2. Imported from .md files (Claude Desktop format)
3. Loaded from JSON history
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

# Import the base scenario types
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.playwright_engine import Scenario, ScenarioStep


# ═══════════════════════════════════════════════════════════════════════════
# STORAGE PATHS
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS_DIR = Path(__file__).parent.parent / 'config' / 'scenarios'
CUSTOM_SCENARIOS_FILE = SCENARIOS_DIR / 'custom_scenarios.json'
SCENARIO_HISTORY_FILE = SCENARIOS_DIR / 'scenario_history.json'
TEMPLATES_DIR = SCENARIOS_DIR / 'templates'


def ensure_directories():
    """Create scenario storage directories if they don't exist"""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM SCENARIO DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CustomScenario:
    """A user-defined or imported test scenario"""
    id: str
    name: str
    description: str
    required_role: str
    steps: List[Dict[str, Any]]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = 'manual'  # 'manual', 'markdown_import', 'template'
    source_file: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    run_count: int = 0
    last_run: Optional[str] = None
    last_success: bool = False

    def to_scenario(self) -> Scenario:
        """Convert to a Playwright Scenario object"""
        scenario_steps = []
        for i, step_data in enumerate(self.steps):
            scenario_steps.append(ScenarioStep(
                step_id=step_data.get('step_id', f'step-{i+1}'),
                title=step_data.get('title', f'Step {i+1}'),
                description=step_data.get('description', ''),
                script=step_data.get('script', step_data.get('description', '')),
                action=step_data.get('action', 'screenshot'),
                selector=step_data.get('selector'),
                value=step_data.get('value'),
                url=step_data.get('url'),
                wait_time=step_data.get('wait_time', 1.0)
            ))

        return Scenario(
            id=self.id,
            name=self.name,
            description=self.description,
            required_role=self.required_role,
            steps=scenario_steps
        )


@dataclass
class ScenarioRunHistory:
    """Record of a scenario execution"""
    scenario_id: str
    scenario_name: str
    run_at: str
    success: bool
    duration: float
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None
    outputs: Dict[str, str] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ═══════════════════════════════════════════════════════════════════════════

class MarkdownScenarioParser:
    """
    Parse test scenarios from markdown files.

    Expected format:

    # Scenario: [Name]

    **Description:** [description]
    **Role:** [employee|manager|admin|superadmin]
    **Tags:** [tag1, tag2]

    ## Steps

    ### Step 1: [Title]
    - **Action:** [click|fill|select|navigate|screenshot|wait]
    - **Selector:** [CSS selector] (optional)
    - **Value:** [value for fill/select] (optional)
    - **URL:** [URL for navigate] (optional)
    - **Script:** [Narration text]
    - **Description:** [Step description]

    ### Step 2: [Title]
    ...
    """

    @staticmethod
    def parse(content: str, source_file: str = None) -> Optional[CustomScenario]:
        """Parse markdown content into a CustomScenario"""
        try:
            lines = content.strip().split('\n')

            # Extract scenario name from first H1
            name = None
            description = ''
            role = 'employee'
            tags = []
            steps = []

            current_step = None
            in_steps_section = False

            for line in lines:
                line = line.strip()

                # Scenario title
                if line.startswith('# Scenario:') or line.startswith('# Test:'):
                    name = line.split(':', 1)[1].strip()
                    continue

                # H1 without prefix - use as name
                if line.startswith('# ') and not name:
                    name = line[2:].strip()
                    continue

                # Description
                if line.startswith('**Description:**') or line.startswith('- Description:'):
                    description = line.split(':', 1)[1].strip().strip('*')
                    continue

                # Role
                if line.startswith('**Role:**') or line.startswith('- Role:'):
                    role_text = line.split(':', 1)[1].strip().strip('*').lower()
                    if role_text in ['employee', 'manager', 'admin', 'superadmin']:
                        role = role_text
                    continue

                # Tags
                if line.startswith('**Tags:**') or line.startswith('- Tags:'):
                    tags_text = line.split(':', 1)[1].strip().strip('*')
                    tags = [t.strip() for t in tags_text.split(',')]
                    continue

                # Steps section
                if line.lower() == '## steps' or line.lower() == '## test steps':
                    in_steps_section = True
                    continue

                # New step (H3)
                if in_steps_section and line.startswith('### '):
                    # Save previous step
                    if current_step:
                        steps.append(current_step)

                    # Parse step title
                    step_title = line[4:].strip()
                    # Remove "Step N:" prefix if present
                    if re.match(r'^Step \d+:', step_title):
                        step_title = step_title.split(':', 1)[1].strip()

                    current_step = {
                        'step_id': f'step-{len(steps)+1}',
                        'title': step_title,
                        'action': 'screenshot',
                        'description': '',
                        'script': ''
                    }
                    continue

                # Step properties
                if current_step and line.startswith('- **'):
                    match = re.match(r'- \*\*(\w+):\*\*\s*(.*)', line)
                    if match:
                        key = match.group(1).lower()
                        value = match.group(2).strip()

                        if key == 'action':
                            current_step['action'] = value.lower()
                        elif key == 'selector':
                            current_step['selector'] = value
                        elif key == 'value':
                            current_step['value'] = value
                        elif key == 'url':
                            current_step['url'] = value
                        elif key == 'script':
                            current_step['script'] = value
                        elif key == 'description':
                            current_step['description'] = value
                        elif key == 'wait' or key == 'wait_time':
                            try:
                                current_step['wait_time'] = float(value)
                            except ValueError:
                                current_step['wait_time'] = 1.0

            # Save last step
            if current_step:
                steps.append(current_step)

            if not name:
                return None

            # Generate ID from name
            scenario_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

            return CustomScenario(
                id=scenario_id,
                name=name,
                description=description or f'Custom scenario: {name}',
                required_role=role,
                steps=steps,
                source='markdown_import',
                source_file=source_file,
                tags=tags
            )

        except Exception as e:
            print(f"Error parsing markdown: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO STORAGE
# ═══════════════════════════════════════════════════════════════════════════

class CustomScenarioManager:
    """Manages storage and retrieval of custom scenarios"""

    def __init__(self):
        ensure_directories()
        self._scenarios: Dict[str, CustomScenario] = {}
        self._history: List[ScenarioRunHistory] = []
        self._load()

    def _load(self):
        """Load scenarios and history from disk"""
        # Load custom scenarios
        if CUSTOM_SCENARIOS_FILE.exists():
            try:
                with open(CUSTOM_SCENARIOS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('scenarios', []):
                        scenario = CustomScenario(**item)
                        self._scenarios[scenario.id] = scenario
            except Exception as e:
                print(f"Error loading custom scenarios: {e}")

        # Load history
        if SCENARIO_HISTORY_FILE.exists():
            try:
                with open(SCENARIO_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data.get('history', []):
                        self._history.append(ScenarioRunHistory(**item))
            except Exception as e:
                print(f"Error loading scenario history: {e}")

    def _save_scenarios(self):
        """Save scenarios to disk"""
        try:
            data = {
                'scenarios': [asdict(s) for s in self._scenarios.values()],
                'updated_at': datetime.now().isoformat()
            }
            with open(CUSTOM_SCENARIOS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving scenarios: {e}")

    def _save_history(self):
        """Save history to disk"""
        try:
            data = {
                'history': [asdict(h) for h in self._history[-100:]],  # Keep last 100
                'updated_at': datetime.now().isoformat()
            }
            with open(SCENARIO_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_scenario(self, scenario: CustomScenario) -> bool:
        """Add or update a custom scenario"""
        self._scenarios[scenario.id] = scenario
        self._save_scenarios()
        return True

    def remove_scenario(self, scenario_id: str) -> bool:
        """Remove a custom scenario"""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            self._save_scenarios()
            return True
        return False

    def get_scenario(self, scenario_id: str) -> Optional[CustomScenario]:
        """Get a scenario by ID"""
        return self._scenarios.get(scenario_id)

    def get_all_scenarios(self) -> List[CustomScenario]:
        """Get all custom scenarios"""
        return list(self._scenarios.values())

    def import_from_markdown(self, content: str, source_file: str = None) -> Optional[CustomScenario]:
        """Import a scenario from markdown content"""
        scenario = MarkdownScenarioParser.parse(content, source_file)
        if scenario:
            self.add_scenario(scenario)
        return scenario

    def import_from_file(self, file_path: Path) -> Optional[CustomScenario]:
        """Import a scenario from a markdown file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            return self.import_from_markdown(content, str(file_path))
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def record_run(self, result: 'ScenarioResult', scenario_id: str, scenario_name: str):
        """Record a scenario execution in history"""
        history = ScenarioRunHistory(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            run_at=datetime.now().isoformat(),
            success=result.success,
            duration=result.total_duration,
            steps_completed=len([s for s in result.steps if s.success]),
            total_steps=len(result.steps),
            error_message=result.error_message
        )
        self._history.append(history)
        self._save_history()

        # Update scenario stats
        if scenario_id in self._scenarios:
            scenario = self._scenarios[scenario_id]
            scenario.run_count += 1
            scenario.last_run = history.run_at
            scenario.last_success = result.success
            self._save_scenarios()

    def get_history(self, limit: int = 50) -> List[ScenarioRunHistory]:
        """Get recent run history"""
        return sorted(self._history, key=lambda h: h.run_at, reverse=True)[:limit]

    def get_scenario_history(self, scenario_id: str) -> List[ScenarioRunHistory]:
        """Get history for a specific scenario"""
        return [h for h in self._history if h.scenario_id == scenario_id]


# Global manager instance
scenario_manager = CustomScenarioManager()


# ═══════════════════════════════════════════════════════════════════════════
# QUICK SCENARIO BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def create_quick_scenario(
    name: str,
    steps_text: str,
    role: str = 'employee',
    description: str = None
) -> Optional[CustomScenario]:
    """
    Create a scenario from a simple text format.

    Format:
    Each line is a step. Format: action: details

    Examples:
    - click: button:has-text('Submit')
    - fill: #username | myuser
    - navigate: /dashboard
    - screenshot: Dashboard view
    - wait: 2
    """
    steps = []

    for i, line in enumerate(steps_text.strip().split('\n')):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Remove leading dash/bullet
        if line.startswith('-'):
            line = line[1:].strip()

        # Parse action: details
        if ':' not in line:
            continue

        action, details = line.split(':', 1)
        action = action.strip().lower()
        details = details.strip()

        step = {
            'step_id': f'step-{len(steps)+1}',
            'title': f'Step {len(steps)+1}',
            'action': 'screenshot',
            'description': details
        }

        if action == 'click':
            step['action'] = 'click'
            step['selector'] = details
            step['title'] = f'Click {details[:30]}'

        elif action == 'fill':
            step['action'] = 'fill'
            if '|' in details:
                selector, value = details.split('|', 1)
                step['selector'] = selector.strip()
                step['value'] = value.strip()
            else:
                step['selector'] = details
                step['value'] = ''
            step['title'] = f'Fill {step["selector"][:20]}'

        elif action == 'navigate' or action == 'goto':
            step['action'] = 'navigate'
            step['url'] = details
            step['title'] = f'Navigate to {details}'

        elif action == 'screenshot' or action == 'capture':
            step['action'] = 'screenshot'
            step['title'] = details or f'Capture Step {len(steps)+1}'

        elif action == 'wait':
            step['action'] = 'wait'
            try:
                step['wait_time'] = float(details)
            except:
                step['wait_time'] = 1.0
            step['title'] = f'Wait {step["wait_time"]}s'

        elif action == 'select':
            step['action'] = 'select'
            if '|' in details:
                selector, value = details.split('|', 1)
                step['selector'] = selector.strip()
                step['value'] = value.strip()
            step['title'] = f'Select {details[:20]}'

        steps.append(step)

    if not steps:
        return None

    scenario_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    return CustomScenario(
        id=scenario_id,
        name=name,
        description=description or f'Quick scenario: {name}',
        required_role=role,
        steps=steps,
        source='manual',
        tags=['quick', 'custom']
    )
