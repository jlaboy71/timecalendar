"""Theme utilities for the NiceGUI app."""
from nicegui import ui, app


def skeleton_loader(rows: int = 3, width: str = '100%'):
    """
    Display a skeleton loader placeholder while content loads.

    Args:
        rows: Number of skeleton rows to display
        width: Width of the skeleton container
    """
    with ui.column().classes('w-full gap-3').style(f'width: {width};'):
        for i in range(rows):
            # Vary widths for more natural look
            row_width = '100%' if i == 0 else f'{85 - (i * 10)}%'
            ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4').style(f'width: {row_width};')


def skeleton_table(rows: int = 5, cols: int = 4):
    """
    Display a skeleton table placeholder while data loads.

    Args:
        rows: Number of skeleton rows
        cols: Number of columns
    """
    with ui.column().classes('w-full gap-2'):
        # Header row
        with ui.row().classes('w-full gap-4'):
            for _ in range(cols):
                ui.element('div').classes('animate-pulse bg-gray-300 dark:bg-gray-600 rounded h-6 flex-1')
        # Data rows
        for _ in range(rows):
            with ui.row().classes('w-full gap-4'):
                for _ in range(cols):
                    ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-5 flex-1')


def skeleton_card():
    """Display a skeleton card placeholder."""
    with ui.card().classes('w-full p-4'):
        ui.element('div').classes('animate-pulse bg-gray-300 dark:bg-gray-600 rounded h-6 w-1/3 mb-4')
        ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-full mb-2')
        ui.element('div').classes('animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-4/5')


def apply_dark_mode():
    """
    Apply dark mode based on user's stored preference.

    Call this at the start of each page to ensure consistent dark mode behavior.
    Returns the dark_mode object in case the page needs to toggle it.
    """
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()
    return dark_mode


class FormValidator:
    """
    Helper class for form validation with visual feedback.

    Usage:
        validator = FormValidator()
        validator.add_field(username_input, 'username', [
            ('required', 'Username is required'),
            ('min_length:3', 'Username must be at least 3 characters'),
        ])
        if validator.validate():
            # All fields valid
    """

    def __init__(self):
        self.fields = {}
        self.errors = {}

    def add_field(self, input_element, name: str, rules: list):
        """
        Add a field with validation rules.

        Args:
            input_element: The NiceGUI input element
            name: Field identifier
            rules: List of (rule, message) tuples
        """
        self.fields[name] = {'element': input_element, 'rules': rules}

    def validate(self) -> bool:
        """Validate all fields and show error messages. Returns True if all valid."""
        self.errors = {}
        all_valid = True

        for name, field in self.fields.items():
            element = field['element']
            value = element.value if hasattr(element, 'value') else ''
            value = str(value).strip() if value else ''

            for rule, message in field['rules']:
                valid = self._check_rule(rule, value)
                if not valid:
                    self.errors[name] = message
                    element.props('error error-message="{}"'.format(message))
                    all_valid = False
                    break
            else:
                # Clear error state if valid
                element.props(remove='error error-message')

        return all_valid

    def _check_rule(self, rule: str, value: str) -> bool:
        """Check a single validation rule."""
        if rule == 'required':
            return bool(value)
        elif rule.startswith('min_length:'):
            min_len = int(rule.split(':')[1])
            return len(value) >= min_len
        elif rule.startswith('max_length:'):
            max_len = int(rule.split(':')[1])
            return len(value) <= max_len
        elif rule == 'email':
            import re
            return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', value))
        elif rule == 'numeric':
            return value.replace('.', '').replace('-', '').isdigit()
        elif rule.startswith('min:'):
            try:
                min_val = float(rule.split(':')[1])
                return float(value) >= min_val
            except (ValueError, TypeError):
                return False
        elif rule.startswith('max:'):
            try:
                max_val = float(rule.split(':')[1])
                return float(value) <= max_val
            except (ValueError, TypeError):
                return False
        return True

    def clear_errors(self):
        """Clear all error states from fields."""
        for name, field in self.fields.items():
            field['element'].props(remove='error error-message')
        self.errors = {}


def validate_required(input_element, field_name: str = 'This field') -> bool:
    """
    Simple required field validation with visual feedback.

    Args:
        input_element: The NiceGUI input element
        field_name: Name to show in error message

    Returns:
        True if valid, False if empty
    """
    value = input_element.value if hasattr(input_element, 'value') else ''
    if not value or not str(value).strip():
        input_element.props(f'error error-message="{field_name} is required"')
        return False
    input_element.props(remove='error error-message')
    return True


def validate_email(input_element) -> bool:
    """
    Email format validation with visual feedback.

    Returns:
        True if valid email format, False otherwise
    """
    import re
    value = input_element.value if hasattr(input_element, 'value') else ''
    if not value:
        return True  # Use validate_required for empty check
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', str(value)):
        input_element.props('error error-message="Invalid email format"')
        return False
    input_element.props(remove='error error-message')
    return True


def validate_min_length(input_element, min_len: int, field_name: str = 'This field') -> bool:
    """
    Minimum length validation with visual feedback.

    Returns:
        True if meets minimum length, False otherwise
    """
    value = input_element.value if hasattr(input_element, 'value') else ''
    if value and len(str(value)) < min_len:
        input_element.props(f'error error-message="{field_name} must be at least {min_len} characters"')
        return False
    input_element.props(remove='error error-message')
    return True
