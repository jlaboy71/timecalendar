"""
Theme utilities for the NiceGUI app.

BRAND COLOR POLICY
==================
This file is the SINGLE SOURCE OF TRUTH for all PTO Central brand colors.

ENFORCEMENT RULES:
1. NEVER hardcode brand hex values (#C9A227, #5a6a72, #2196F3) anywhere in the codebase
2. ALWAYS import and use the constants: PTO_GOLD, PTO_GRAY, PTO_BLUE
3. For CSS in f-strings, use: f'color: {PTO_GOLD};'
4. For HTML templates, import constants and embed with f-strings
5. Semantic colors (green for success, red for error) are NOT brand colors - keep those as-is

IMPORT PATTERN:
    from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY, PTO_BLUE

CONVERTING HARDCODED HEX:
    Before: .style('color: #C9A227;')
    After:  .style(f'color: {PTO_GOLD};')

    Before: background-color: #5a6a72
    After:  background-color: {PTO_GRAY}  (in f-string)

CSS f-string GOTCHA:
    When converting CSS blocks to f-strings, use double braces for literal braces:
    Before: @keyframes pulse { 0% { opacity: 1; } }
    After:  @keyframes pulse {{ 0% {{ opacity: 1; }} }}  (in f-string)
"""
from nicegui import ui, app

# =============================================================================
# PTO CENTRAL BRAND COLORS - Single Source of Truth
# =============================================================================
# DO NOT add hardcoded hex values elsewhere in the codebase.
# Always import and use these constants.
# =============================================================================
BRAND_COLORS = {
    'gold': '#C9A227',      # Primary accent - buttons, highlights, important actions
    'gray': '#5a6a72',      # Navigation/headers - professional gray
    'blue': '#2196F3',      # UI interactive elements - links, secondary buttons
    'dark_bg': '#1E2328',   # Dark mode background
    'light_bg': '#E8E6E1',  # Light mode background (warm gray)
    'dark_card': '#1f2937', # Dark mode card/dialog background
}

# Shorthand aliases for common use - ALWAYS use these, never hardcode hex values
PTO_GOLD = BRAND_COLORS['gold']
PTO_GRAY = BRAND_COLORS['gray']
PTO_BLUE = BRAND_COLORS['blue']

# Mobile responsive CSS injection
# REVERT INSTRUCTIONS: If mobile CSS causes issues, remove this import and the
# inject_mobile_css() call in apply_dark_mode() below. See mobile_responsive.py for details.
from nicegui_app.components.mobile_responsive import inject_mobile_css

# =============================================================================
# PROFESSIONAL UI ENHANCEMENT - Phase 0 Foundation
# REVERT INSTRUCTIONS: If professional styles cause issues, comment out calls to
# inject_professional_fonts() and inject_global_styles() in apply_dark_mode() below.
# =============================================================================

# Track if professional styles have been injected (prevents duplicate injection)
_professional_styles_injected = {'fonts': False, 'styles': False}


def inject_professional_fonts():
    """Inject premium Google Fonts for professional typography.

    Fonts loaded:
    - Plus Jakarta Sans: Headings (modern, clean)
    - DM Sans: Body text (readable, professional)
    - JetBrains Mono: Code/monospace
    """
    if _professional_styles_injected['fonts']:
        return
    _professional_styles_injected['fonts'] = True

    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --font-heading: 'Plus Jakarta Sans', system-ui, sans-serif;
                --font-body: 'DM Sans', system-ui, sans-serif;
                --font-mono: 'JetBrains Mono', monospace;
            }

            body, .nicegui-content {
                font-family: var(--font-body);
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }

            h1, h2, h3, h4, h5, h6, .heading {
                font-family: var(--font-heading);
                font-weight: 600;
                letter-spacing: -0.02em;
            }

            code, pre, .mono {
                font-family: var(--font-mono);
            }
        </style>
    ''')


def inject_global_styles():
    """Inject comprehensive global styles for professional appearance.

    Includes: CSS custom properties, card/button/table enhancements, animations.
    """
    if _professional_styles_injected['styles']:
        return
    _professional_styles_injected['styles'] = True

    ui.add_css('''
        /* ========== CSS CUSTOM PROPERTIES ========== */
        :root {
            /* Shadows */
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
            --shadow-gold: 0 4px 14px 0 rgba(201, 162, 39, 0.25);

            /* Transitions */
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);

            /* Border Radius */
            --radius-sm: 6px;
            --radius-md: 8px;
            --radius-lg: 12px;
            --radius-xl: 16px;

            /* PTO Central Brand */
            --pto-gold: #c9a227;
            --pto-gray: #5a6a72;
        }

        /* ========== CARD ENHANCEMENTS ========== */
        .q-card {
            border-radius: var(--radius-lg) !important;
            transition: all var(--transition-base);
        }

        /* ========== BUTTON ENHANCEMENTS ========== */
        .q-btn {
            border-radius: var(--radius-md) !important;
            font-weight: 500 !important;
        }

        /* Gold button class */
        .btn-gold {
            background: linear-gradient(135deg, #c9a227 0%, #d4af37 100%) !important;
            color: white !important;
            box-shadow: var(--shadow-gold) !important;
        }

        .btn-gold:hover {
            background: linear-gradient(135deg, #d4af37 0%, #c9a227 100%) !important;
        }

        /* ========== INPUT ENHANCEMENTS ========== */
        .q-field__control {
            border-radius: var(--radius-md) !important;
        }

        .q-field--outlined.q-field--focused .q-field__control:after {
            border-color: var(--pto-gold) !important;
            border-width: 2px !important;
        }

        /* ========== TABLE ENHANCEMENTS ========== */
        .q-table {
            border-radius: var(--radius-lg) !important;
            overflow: hidden;
        }

        .q-table thead tr {
            background: linear-gradient(135deg, #5a6a72 0%, #4a5a62 100%);
        }

        .q-table thead th {
            color: white !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }

        .q-table tbody tr:hover {
            background: rgba(201, 162, 39, 0.05) !important;
        }

        /* ========== BADGE ENHANCEMENTS ========== */
        .q-badge {
            font-weight: 500;
            letter-spacing: 0.02em;
            border-radius: 9999px;
        }

        /* ========== DIALOG ENHANCEMENTS ========== */
        .q-dialog__inner > .q-card {
            border-radius: var(--radius-xl) !important;
            box-shadow: var(--shadow-xl) !important;
        }

        /* ========== ANIMATIONS ========== */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes pulse-gold {
            0%, 100% { box-shadow: 0 0 0 0 rgba(201, 162, 39, 0.4); }
            50% { box-shadow: 0 0 0 10px rgba(201, 162, 39, 0); }
        }

        .animate-fade-in-up {
            animation: fadeInUp 0.4s ease-out forwards;
        }

        .animate-fade-in {
            animation: fadeIn 0.3s ease-out forwards;
        }

        .animate-pulse-gold {
            animation: pulse-gold 2s infinite;
        }

        /* Stagger children animations */
        .stagger-children > * {
            opacity: 0;
            animation: fadeInUp 0.4s ease-out forwards;
        }

        .stagger-children > *:nth-child(1) { animation-delay: 0.05s; }
        .stagger-children > *:nth-child(2) { animation-delay: 0.1s; }
        .stagger-children > *:nth-child(3) { animation-delay: 0.15s; }
        .stagger-children > *:nth-child(4) { animation-delay: 0.2s; }
        .stagger-children > *:nth-child(5) { animation-delay: 0.25s; }
        .stagger-children > *:nth-child(6) { animation-delay: 0.3s; }

        /* ========== DARK MODE TABLE OVERRIDE ========== */
        body.body--dark .q-table thead tr {
            background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
        }

        /* ========== SCROLLBAR STYLING ========== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        body.body--dark ::-webkit-scrollbar-thumb {
            background: #475569;
        }
    ''')


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

    # Inject professional fonts and global styles (Phase 0 Foundation)
    # REVERT: comment out these lines if professional styles cause issues
    inject_professional_fonts()
    inject_global_styles()

    # Apply PTO Central Brand Colors to Quasar theme
    # Colors defined at module level: PTO_GOLD, PTO_GRAY, PTO_BLUE
    ui.colors(
        primary=PTO_GOLD,      # Gold - main brand accent
        secondary=PTO_GRAY,    # Gray - navigation/headers
        accent=PTO_BLUE        # Blue - interactive elements
    )

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

        /* PTO Central Brand Color Accents */
        /* Header/Navigation bar */
        .q-header, .q-toolbar {{
            background-color: {PTO_GRAY} !important;
        }}

        /* Card headers and titles - gold accent */
        .text-xl.font-bold, .text-2xl.font-bold {{
            color: {PTO_GOLD} !important;
        }}

        /* Primary buttons use PTO Gold (handled by ui.colors) */

        /* Links and interactive elements */
        a:not(.q-btn) {{
            color: {PTO_GOLD};
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
                ui.button('OK', on_click=handle_close).style(f'background-color: {PTO_GOLD} !important; color: white !important;')
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
    """Show a success dialog with PTO Central gold/amber styling.

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
        with ui.row().classes('w-full p-4 text-white items-center').style(f'background-color: {PTO_GOLD}'):
            ui.icon('check_circle', size='md').classes('mr-2')
            ui.label(title).classes('text-lg font-bold')
        with ui.column().classes('p-4 gap-3'):
            ui.label(message).classes('text-base whitespace-pre-line')
            with ui.row().classes('w-full justify-end mt-2'):
                ui.button('OK', on_click=handle_close).style(f'background-color: {PTO_GOLD} !important; color: white !important;')
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
            ui.button('OK', on_click=dialog.close).style(f'background-color: {PTO_GOLD} !important; color: white !important;')
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


# =============================================================================
# PROFESSIONAL UI COMPONENTS - Reusable UI elements
# =============================================================================

def stat_card(title: str, value, icon: str = 'analytics', color: str = 'blue', subtitle: str = None):
    """Create a stat card with icon, value, and title.

    Args:
        title: Card title (e.g., 'Departments')
        value: Main value to display (number or string)
        icon: Material icon name
        color: Tailwind color name (blue, green, amber, purple, red, gray)
        subtitle: Optional subtitle text

    Returns:
        The card element
    """
    # Map color names to hex for icon styling
    color_map = {
        'blue': '#3b82f6',
        'green': '#22c55e',
        'amber': '#f59e0b',
        'gold': '#c9a227',
        'purple': '#a855f7',
        'red': '#ef4444',
        'gray': '#6b7280',
        'indigo': '#6366f1',
    }
    icon_color = color_map.get(color, color_map['blue'])

    with ui.card().classes('p-5 hover:shadow-lg transition-all') as card:
        with ui.row().classes('items-center gap-4'):
            # Icon container with background
            with ui.element('div').classes(f'w-12 h-12 rounded-xl bg-{color}-100 flex items-center justify-center'):
                ui.icon(icon, size='md').style(f'color: {icon_color};')

            with ui.column().classes('gap-0'):
                ui.label(str(value)).classes('text-2xl font-bold')
                ui.label(title).classes('text-sm opacity-60')
                if subtitle:
                    ui.label(subtitle).classes('text-xs opacity-40')

    return card


def status_badge(status: str):
    """Create a professionally styled status badge.

    Args:
        status: Status key (active, inactive, needs_manager, empty, pending, approved, denied)

    Returns:
        The badge row element
    """
    status_config = {
        'active': {
            'bg': 'bg-emerald-100',
            'text': 'text-emerald-800',
            'icon': 'check_circle',
            'label': 'Active'
        },
        'inactive': {
            'bg': 'bg-gray-100',
            'text': 'text-gray-600',
            'icon': 'block',
            'label': 'Inactive'
        },
        'needs_manager': {
            'bg': 'bg-amber-100',
            'text': 'text-amber-800',
            'icon': 'warning',
            'label': 'Needs Manager'
        },
        'empty': {
            'bg': 'bg-blue-100',
            'text': 'text-blue-800',
            'icon': 'group_off',
            'label': 'No Employees'
        },
        'pending': {
            'bg': 'bg-amber-100',
            'text': 'text-amber-800',
            'icon': 'pending',
            'label': 'Pending'
        },
        'approved': {
            'bg': 'bg-emerald-100',
            'text': 'text-emerald-800',
            'icon': 'check_circle',
            'label': 'Approved'
        },
        'denied': {
            'bg': 'bg-red-100',
            'text': 'text-red-800',
            'icon': 'cancel',
            'label': 'Denied'
        },
    }

    config = status_config.get(status.lower(), status_config['active'])

    with ui.row().classes(f'items-center gap-1.5 px-3 py-1 rounded-full {config["bg"]}') as badge:
        ui.icon(config['icon'], size='xs').classes(config['text'])
        ui.label(config['label']).classes(f'{config["text"]} text-sm font-medium')

    return badge


def empty_state(icon: str, title: str, description: str, action_label: str = None, action_click=None):
    """Create an empty state placeholder with icon, text, and optional action.

    Args:
        icon: Material icon name
        title: Main title text
        description: Description text
        action_label: Optional button label
        action_click: Optional button click handler

    Returns:
        The column element
    """
    with ui.column().classes('w-full items-center py-12 gap-4') as container:
        with ui.element('div').classes('w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center'):
            ui.icon(icon, size='xl').classes('text-gray-400')

        ui.label(title).classes('text-xl font-semibold text-gray-600')
        ui.label(description).classes('text-sm text-gray-400 text-center max-w-md')

        if action_label and action_click:
            ui.button(action_label, icon='add', on_click=action_click).classes('btn-gold mt-4')

    return container


def action_button_group(buttons: list):
    """Create a row of action buttons.

    Args:
        buttons: List of button configs, each with:
            - label (optional): Button text
            - icon: Material icon name
            - variant: 'flat', 'outline', or 'filled' (default: 'flat')
            - color: Button color (default: 'primary')
            - on_click: Click handler

    Returns:
        The row element
    """
    with ui.row().classes('w-full justify-end gap-2') as row:
        for btn in buttons:
            label = btn.get('label')
            icon = btn.get('icon')
            variant = btn.get('variant', 'flat')
            color = btn.get('color', 'primary')
            on_click = btn.get('on_click')

            if label:
                button = ui.button(label, icon=icon, on_click=on_click)
            else:
                button = ui.button(icon=icon, on_click=on_click)

            if variant == 'flat':
                button.props(f'flat color={color}')
            elif variant == 'outline':
                button.props(f'outline color={color}')
            else:
                button.props(f'color={color}')

    return row
