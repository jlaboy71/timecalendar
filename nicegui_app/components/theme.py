"""Theme utilities for the NiceGUI app."""
from nicegui import ui, app

# Mobile responsive CSS injection
# REVERT INSTRUCTIONS: If mobile CSS causes issues, remove this import and the
# inject_mobile_css() call in apply_dark_mode() below. See mobile_responsive.py for details.
from nicegui_app.components.mobile_responsive import inject_mobile_css


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
    # Inject mobile responsive CSS (REVERT: comment out this line if issues occur)
    inject_mobile_css()

    # TJM Brand Colors
    TJM_GOLD = '#c9a227'
    TJM_GRAY = '#5a6a72'

    # Set Quasar primary color to TJM Gold
    ui.colors(primary=TJM_GOLD)

    # Add custom background colors for light and dark modes
    # NiceGUI/Quasar uses body--light and body--dark classes
    ui.add_head_html(f'''
    <style>
        /* Light mode - Warm Gray (1 shade darker than cream) */
        body.body--light {{
            background-color: #E8E6E1 !important;
        }}
        body.body--light .q-page {{
            background-color: #E8E6E1 !important;
        }}
        /* Dark mode - Dark Slate Gray */
        body.body--dark {{
            background-color: #1E2328 !important;
        }}
        body.body--dark .q-page {{
            background-color: #1E2328 !important;
        }}

        /* TJM Brand Color Accents */
        /* Header/Navigation bar */
        .q-header, .q-toolbar {{
            background-color: {TJM_GRAY} !important;
        }}

        /* Card headers and titles - gold accent */
        .text-xl.font-bold, .text-2xl.font-bold {{
            color: {TJM_GOLD} !important;
        }}

        /* Primary buttons use TJM Gold (handled by ui.colors) */

        /* Links and interactive elements */
        a:not(.q-btn) {{
            color: {TJM_GOLD};
        }}
        a:not(.q-btn):hover {{
            color: #b8922a;
        }}

        /* Subtle shadows for light mode - improved depth perception */
        body.body--light .q-card {{
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.06) !important;
            border: 1px solid rgba(0, 0, 0, 0.04);
        }}
        body.body--light .q-card:hover {{
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.08) !important;
        }}

        /* Subtle shadow for inputs and selects in light mode */
        body.body--light .q-field--outlined .q-field__control {{
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }}
        body.body--light .q-field--outlined .q-field__control:hover {{
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }}

        /* Buttons get subtle depth */
        body.body--light .q-btn {{
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
        }}
        body.body--light .q-btn:hover {{
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }}

        /* Tables get subtle container shadow */
        body.body--light .q-table__container {{
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
            border-radius: 4px;
        }}
    </style>
    ''')

    dark_mode = ui.dark_mode()
    is_dark = app.storage.user.get('dark_mode', True)  # Default to dark mode
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


def show_validation_dialog(title: str, message: str, icon: str = 'info', icon_color: str = 'amber', on_close=None):
    """
    Show a friendly validation/warning dialog instead of toast notifications.

    Args:
        title: Dialog title
        message: Message to display
        icon: Material icon name (default: 'info')
        icon_color: Icon color (default: 'amber')
        on_close: Optional callback to execute when OK is clicked (e.g., navigation)
    """
    def handle_close():
        dialog.close()
        if on_close:
            on_close()

    with ui.dialog() as dialog, ui.card().classes('p-0 max-w-sm'):
        with ui.row().classes(f'w-full p-4 bg-{icon_color}-500 text-white items-center'):
            ui.icon(icon, size='md').classes('mr-2')
            ui.label(title).classes('text-lg font-bold')
        with ui.column().classes('p-4 gap-3'):
            ui.label(message).classes('text-base whitespace-pre-line')
            with ui.row().classes('w-full justify-end mt-2'):
                ui.button('OK', on_click=handle_close).style('background-color: #C9A227 !important; color: white !important;')
    dialog.open()


def show_error_dialog(title: str, message: str, on_close=None):
    """Show an error dialog with red styling."""
    show_validation_dialog(title, message, icon='error', icon_color='red', on_close=on_close)


def show_warning_dialog(title: str, message: str, on_close=None):
    """Show a warning dialog with amber styling."""
    show_validation_dialog(title, message, icon='warning', icon_color='amber', on_close=on_close)


def show_info_dialog(title: str, message: str, on_close=None):
    """Show an info dialog with blue styling."""
    show_validation_dialog(title, message, icon='info', icon_color='blue', on_close=on_close)


def show_success_dialog(title: str, message: str, on_close=None):
    """Show a success dialog with TJM gold/amber styling.

    Args:
        title: Dialog title
        message: Message to display
        on_close: Optional callback to execute when OK is clicked (e.g., navigation)
    """
    def handle_close():
        dialog.close()
        if on_close:
            on_close()

    with ui.dialog() as dialog, ui.card().classes('p-0 max-w-sm'):
        with ui.row().classes('w-full p-4 text-white items-center').style('background-color: #C9A227'):
            ui.icon('check_circle', size='md').classes('mr-2')
            ui.label(title).classes('text-lg font-bold')
        with ui.column().classes('p-4 gap-3'):
            ui.label(message).classes('text-base whitespace-pre-line')
            with ui.row().classes('w-full justify-end mt-2'):
                ui.button('OK', on_click=handle_close).style('background-color: #C9A227 !important; color: white !important;')
    dialog.open()


def show_help_dialog(title: str, message: str):
    """Show a dark-themed help dialog with HTML content support.

    Args:
        title: Dialog title
        message: HTML message to display (supports <b>, <br>, <code>, <i>, etc.)
    """
    with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 450px; max-width: 600px;'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('help', color='amber', size='md')
            ui.label(title).classes('text-lg font-bold')
        ui.html(f'<div style="color: #e5e7eb; font-size: 14px; line-height: 1.6;">{message}</div>', sanitize=False)
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('OK', on_click=dialog.close).style('background-color: #C9A227 !important; color: white !important;')
    dialog.open()


def create_help_button(title: str, message: str):
    """Create a help button with consistent styling that opens a help dialog.

    Args:
        title: Dialog title
        message: HTML message to display

    Returns:
        The created button element
    """
    def on_click():
        show_help_dialog(title, message)

    return ui.button(icon='help_outline', on_click=on_click).props('flat dense round size=sm').style('color: #f59e0b')
