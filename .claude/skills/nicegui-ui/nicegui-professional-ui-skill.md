# NiceGUI Professional UI Enhancement Skill

## Purpose
Transform NiceGUI applications from functional to **enterprise-grade professional** with sophisticated styling, animations, typography, and modern UI/UX patterns. This skill is designed for the **TJM Time Calendar** PTO management system.

---

## Brand Foundation

### TJM Brand Identity
```python
# Core Brand Colors (DO NOT CHANGE)
TJM_GOLD = "#c9a227"      # Primary accent - highlights, CTAs, active states
TJM_GRAY = "#5a6a72"      # Navigation, headers, professional elements
TJM_BLUE = "#2196F3"      # Interactive elements, links

# Extended Professional Palette
COLORS = {
    'background': {
        'light': '#f8fafc',      # Soft off-white (not pure white)
        'dark': '#0f172a',       # Rich navy-black
        'card_light': '#ffffff',
        'card_dark': '#1e293b',
    },
    'accent': {
        'gold': '#c9a227',
        'gold_light': '#d4af37',
        'gold_dark': '#a68521',
    },
    'semantic': {
        'success': '#10b981',    # Emerald green
        'warning': '#f59e0b',    # Amber
        'error': '#ef4444',      # Red
        'info': '#3b82f6',       # Blue
    },
    'neutral': {
        '50': '#f8fafc',
        '100': '#f1f5f9',
        '200': '#e2e8f0',
        '300': '#cbd5e1',
        '400': '#94a3b8',
        '500': '#64748b',
        '600': '#475569',
        '700': '#334155',
        '800': '#1e293b',
        '900': '#0f172a',
    }
}
```

---

## Typography System

### Google Fonts Integration
```python
def inject_professional_fonts():
    """Inject premium Google Fonts for professional typography."""
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    ''')
    
    # Apply font stack globally
    ui.add_css('''
        :root {
            --font-heading: 'Plus Jakarta Sans', system-ui, sans-serif;
            --font-body: 'DM Sans', system-ui, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }
        
        body, .nicegui-content {
            font-family: var(--font-body);
            font-size: 15px;
            line-height: 1.6;
            letter-spacing: -0.01em;
            -webkit-font-smoothing: antialiased;
        }
        
        h1, h2, h3, h4, h5, h6, .heading {
            font-family: var(--font-heading);
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        code, pre, .mono {
            font-family: var(--font-mono);
        }
    ''')
```

### Typography Classes
```python
# Use with .classes() method
TYPOGRAPHY = {
    'display': 'text-4xl font-semibold tracking-tight',
    'heading_1': 'text-2xl font-semibold tracking-tight',
    'heading_2': 'text-xl font-medium',
    'heading_3': 'text-lg font-medium',
    'body': 'text-base',
    'body_small': 'text-sm',
    'caption': 'text-xs text-gray-500',
    'label': 'text-sm font-medium uppercase tracking-wide',
}
```

---

## CSS Foundation

### Global Stylesheet
```python
def inject_global_styles():
    """Inject comprehensive global styles for professional appearance."""
    ui.add_css('''
        /* ========== RESET & FOUNDATION ========== */
        * {
            box-sizing: border-box;
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Remove default button styling inconsistencies */
        button {
            font-family: inherit;
        }
        
        /* ========== CUSTOM PROPERTIES ========== */
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
            
            /* TJM Brand */
            --tjm-gold: #c9a227;
            --tjm-gray: #5a6a72;
        }
        
        /* ========== CARD ENHANCEMENTS ========== */
        .q-card {
            border-radius: var(--radius-lg) !important;
            box-shadow: var(--shadow-md) !important;
            border: 1px solid rgba(0, 0, 0, 0.05);
            transition: all var(--transition-base);
        }
        
        .q-card:hover {
            box-shadow: var(--shadow-lg) !important;
            transform: translateY(-2px);
        }
        
        /* Glass morphism card variant */
        .glass-card {
            background: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        /* ========== BUTTON ENHANCEMENTS ========== */
        .q-btn {
            border-radius: var(--radius-md) !important;
            font-weight: 500 !important;
            letter-spacing: 0.01em;
            transition: all var(--transition-fast) !important;
        }
        
        .q-btn:hover {
            transform: translateY(-1px);
        }
        
        .q-btn:active {
            transform: translateY(0);
        }
        
        /* Primary gold button */
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
        
        .q-field--outlined .q-field__control:before {
            border-color: #e2e8f0 !important;
        }
        
        .q-field--outlined.q-field--focused .q-field__control:after {
            border-color: var(--tjm-gold) !important;
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
            padding: 4px 10px;
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
        
        /* ========== DARK MODE OVERRIDES ========== */
        body.body--dark {
            background: #0f172a !important;
        }
        
        body.body--dark .q-card {
            background: #1e293b !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
        }
        
        body.body--dark .glass-card {
            background: rgba(30, 41, 59, 0.8) !important;
        }
        
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
```

---

## Component Library

### Professional Page Header
```python
def page_header_pro(title: str, subtitle: str = None, show_back: bool = True):
    """Create a professional page header with optional subtitle."""
    with ui.row().classes('w-full items-center mb-6 pb-4 border-b border-gray-200'):
        if show_back:
            ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')) \
                .props('flat round').classes('mr-2')
        
        with ui.column().classes('gap-0'):
            ui.label(title).classes('text-2xl font-semibold tracking-tight text-gray-900')
            if subtitle:
                ui.label(subtitle).classes('text-sm text-gray-500 mt-1')
```

### Stat Card Component
```python
def stat_card(
    title: str,
    value: str | int,
    icon: str,
    color: str = 'blue',
    change: str = None,
    change_positive: bool = True
):
    """Create a professional statistics card."""
    color_classes = {
        'gold': 'from-amber-500 to-yellow-600',
        'blue': 'from-blue-500 to-blue-600',
        'green': 'from-emerald-500 to-emerald-600',
        'purple': 'from-purple-500 to-purple-600',
        'gray': 'from-slate-500 to-slate-600',
    }
    
    with ui.card().classes('p-5 relative overflow-hidden'):
        # Background gradient accent
        ui.element('div').classes(
            f'absolute top-0 right-0 w-32 h-32 -mr-8 -mt-8 rounded-full '
            f'bg-gradient-to-br {color_classes.get(color, color_classes["blue"])} opacity-10'
        )
        
        with ui.row().classes('items-start justify-between relative z-10'):
            with ui.column().classes('gap-1'):
                ui.label(title).classes('text-sm font-medium text-gray-500 uppercase tracking-wide')
                ui.label(str(value)).classes('text-3xl font-bold text-gray-900 mt-1')
                
                if change:
                    change_color = 'text-emerald-600' if change_positive else 'text-red-600'
                    change_icon = 'trending_up' if change_positive else 'trending_down'
                    with ui.row().classes('items-center gap-1 mt-2'):
                        ui.icon(change_icon).classes(f'{change_color} text-sm')
                        ui.label(change).classes(f'{change_color} text-sm font-medium')
            
            with ui.element('div').classes(
                f'p-3 rounded-xl bg-gradient-to-br {color_classes.get(color, color_classes["blue"])}'
            ):
                ui.icon(icon).classes('text-white text-2xl')
```

### Enhanced Data Table
```python
def pro_table(columns: list, rows: list, title: str = None):
    """Create a professionally styled data table."""
    with ui.card().classes('w-full overflow-hidden'):
        if title:
            with ui.row().classes('p-4 border-b border-gray-100 items-center justify-between'):
                ui.label(title).classes('text-lg font-semibold text-gray-900')
                ui.button(icon='more_vert').props('flat round dense')
        
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id'
        ).classes('w-full')
        
        # Apply enhanced styling
        table.props('flat bordered separator=cell')
        
        return table
```

### Status Badge Component
```python
def status_badge(status: str):
    """Create a professionally styled status badge."""
    status_config = {
        'pending': {'color': 'amber', 'bg': 'bg-amber-100', 'text': 'text-amber-800', 'icon': 'schedule'},
        'approved': {'color': 'green', 'bg': 'bg-emerald-100', 'text': 'text-emerald-800', 'icon': 'check_circle'},
        'denied': {'color': 'red', 'bg': 'bg-red-100', 'text': 'text-red-800', 'icon': 'cancel'},
        'cancelled': {'color': 'gray', 'bg': 'bg-gray-100', 'text': 'text-gray-600', 'icon': 'block'},
    }
    
    config = status_config.get(status.lower(), status_config['pending'])
    
    with ui.row().classes(f'items-center gap-1.5 px-3 py-1 rounded-full {config["bg"]}'):
        ui.icon(config['icon']).classes(f'{config["text"]} text-sm')
        ui.label(status.title()).classes(f'{config["text"]} text-sm font-medium')
```

### Action Button Group
```python
def action_button_group(actions: list):
    """Create a group of action buttons.
    
    actions: list of dicts with 'label', 'icon', 'on_click', 'color' (optional)
    """
    with ui.row().classes('gap-2'):
        for action in actions:
            color = action.get('color', 'primary')
            variant = action.get('variant', 'flat')
            
            btn = ui.button(
                action.get('label', ''),
                icon=action.get('icon'),
                on_click=action.get('on_click')
            )
            
            if variant == 'gold':
                btn.classes('btn-gold')
            else:
                btn.props(f'{variant} color={color}')
```

### Empty State Component
```python
def empty_state(
    icon: str,
    title: str,
    description: str,
    action_label: str = None,
    action_click: callable = None
):
    """Create an empty state placeholder."""
    with ui.column().classes('w-full py-16 items-center text-center'):
        with ui.element('div').classes('p-6 rounded-full bg-gray-100 mb-4'):
            ui.icon(icon).classes('text-4xl text-gray-400')
        
        ui.label(title).classes('text-xl font-semibold text-gray-900 mb-2')
        ui.label(description).classes('text-gray-500 max-w-md')
        
        if action_label and action_click:
            ui.button(action_label, on_click=action_click) \
                .classes('mt-6 btn-gold')
```

---

## Layout Patterns

### Dashboard Grid
```python
def dashboard_grid():
    """Create a responsive dashboard grid layout."""
    with ui.element('div').classes(
        'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 stagger-children'
    ):
        # Add stat cards here
        pass
```

### Split Layout (Sidebar + Main)
```python
def split_layout(sidebar_width: str = 'w-80'):
    """Create a split layout with sidebar and main content."""
    with ui.row().classes('w-full min-h-screen'):
        # Sidebar
        with ui.column().classes(f'{sidebar_width} bg-gray-50 border-r border-gray-200 p-6'):
            yield 'sidebar'
        
        # Main content
        with ui.column().classes('flex-1 p-6'):
            yield 'main'
```

### Content Section
```python
def content_section(title: str, description: str = None):
    """Create a content section with title and optional description."""
    with ui.column().classes('w-full mb-8'):
        with ui.row().classes('items-center justify-between mb-4'):
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-xl font-semibold text-gray-900')
                if description:
                    ui.label(description).classes('text-sm text-gray-500 mt-1')
```

---

## Calendar-Specific Patterns

### PTO Type Buttons (Enhanced)
```python
PTO_COLORS = {
    'vacation': {'gradient': 'from-blue-500 to-blue-600', 'icon': 'beach_access'},
    'sick': {'gradient': 'from-emerald-500 to-emerald-600', 'icon': 'medical_services'},
    'personal': {'gradient': 'from-purple-500 to-purple-600', 'icon': 'person'},
    'bereavement': {'gradient': 'from-amber-600 to-amber-700', 'icon': 'sentiment_very_dissatisfied'},
    'fmla': {'gradient': 'from-teal-500 to-teal-600', 'icon': 'family_restroom'},
    'jury_duty': {'gradient': 'from-indigo-500 to-indigo-600', 'icon': 'gavel'},
    'voting': {'gradient': 'from-cyan-500 to-cyan-600', 'icon': 'how_to_vote'},
    'military': {'gradient': 'from-orange-500 to-orange-600', 'icon': 'military_tech'},
}

def pto_type_button(pto_type: str, on_click: callable, selected: bool = False):
    """Create a styled PTO type selection button."""
    config = PTO_COLORS.get(pto_type.lower(), PTO_COLORS['vacation'])
    
    base_classes = 'px-4 py-3 rounded-xl transition-all duration-200 cursor-pointer'
    
    if selected:
        btn_classes = f'{base_classes} bg-gradient-to-r {config["gradient"]} text-white shadow-lg'
    else:
        btn_classes = f'{base_classes} bg-white border-2 border-gray-200 hover:border-gray-300'
    
    with ui.element('div').classes(btn_classes).on('click', on_click):
        with ui.row().classes('items-center gap-2'):
            ui.icon(config['icon']).classes('text-lg' if not selected else 'text-lg text-white')
            ui.label(pto_type.replace('_', ' ').title()).classes(
                'font-medium' if not selected else 'font-medium text-white'
            )
```

### Balance Display Card
```python
def balance_display(balances: dict):
    """Create a professional PTO balance display."""
    with ui.card().classes('w-full p-6'):
        ui.label('Your Balances').classes('text-lg font-semibold text-gray-900 mb-4')
        
        with ui.element('div').classes('grid grid-cols-2 md:grid-cols-4 gap-4'):
            for leave_type, data in balances.items():
                config = PTO_COLORS.get(leave_type.lower(), PTO_COLORS['vacation'])
                
                with ui.column().classes('p-4 rounded-xl bg-gray-50'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon(config['icon']).classes('text-gray-600')
                        ui.label(leave_type.replace('_', ' ').title()).classes(
                            'text-sm font-medium text-gray-600'
                        )
                    
                    ui.label(f"{data['available']:.1f}").classes(
                        'text-2xl font-bold text-gray-900'
                    )
                    ui.label(f"of {data['total']:.1f} days").classes(
                        'text-xs text-gray-500'
                    )
```

---

## Initialization Template

### Complete Setup Function
```python
def initialize_professional_ui():
    """Initialize all professional UI enhancements.
    Call this at app startup or in app.on_startup hook.
    """
    inject_professional_fonts()
    inject_global_styles()

# In your main.py:
app.on_startup(initialize_professional_ui)

# Or per-page:
@ui.page('/dashboard')
def dashboard():
    inject_professional_fonts()
    inject_global_styles()
    # ... rest of page
```

---

## Quick Reference - Tailwind Classes for NiceGUI

### Spacing
- `p-4` / `px-4` / `py-4` - Padding (4 = 16px)
- `m-4` / `mx-4` / `my-4` - Margin
- `gap-4` - Flex/Grid gap
- `space-y-4` - Vertical spacing between children

### Layout
- `w-full` - Full width
- `max-w-5xl mx-auto` - Centered container
- `flex` / `flex-col` / `flex-row` - Flexbox
- `items-center` / `justify-between` - Alignment
- `grid grid-cols-4` - CSS Grid

### Typography
- `text-sm` / `text-base` / `text-lg` / `text-xl` / `text-2xl` - Font sizes
- `font-medium` / `font-semibold` / `font-bold` - Font weights
- `text-gray-500` / `text-gray-900` - Text colors
- `tracking-tight` - Letter spacing

### Visual
- `rounded-lg` / `rounded-xl` / `rounded-full` - Border radius
- `shadow-md` / `shadow-lg` - Box shadows
- `border` / `border-gray-200` - Borders
- `bg-gray-50` / `bg-white` - Backgrounds

### Animation (use with ui.add_css above)
- `animate-fade-in-up` - Fade in from below
- `stagger-children` - Stagger child animations
- `transition-all duration-200` - Smooth transitions

---

## Usage Instructions for Claude

When enhancing NiceGUI applications with this skill:

1. **Always inject fonts and global styles first** - Call `inject_professional_fonts()` and `inject_global_styles()` at page load or app startup.

2. **Use the component library** - Replace basic NiceGUI elements with the professional components defined here.

3. **Follow the brand colors** - Maintain TJM Gold (#c9a227) and TJM Gray (#5a6a72) as primary accent colors.

4. **Apply typography system** - Use Plus Jakarta Sans for headings, DM Sans for body text.

5. **Leverage animations** - Add `.classes('animate-fade-in-up')` or `.classes('stagger-children')` for polish.

6. **Maintain dark mode support** - All components should work in both light and dark modes.

7. **Use semantic color meanings**:
   - Gold = Primary action, brand highlight
   - Blue = Interactive elements
   - Green = Success, approved states
   - Amber = Warning, pending states
   - Red = Error, denied states

---

## File Organization Recommendation

```
nicegui_app/
├── components/
│   ├── __init__.py
│   ├── theme.py           # inject_professional_fonts(), inject_global_styles()
│   ├── cards.py           # stat_card(), balance_display(), etc.
│   ├── buttons.py         # action_button_group(), pto_type_button()
│   ├── tables.py          # pro_table()
│   ├── badges.py          # status_badge()
│   ├── layout.py          # page_header_pro(), content_section()
│   └── empty_states.py    # empty_state()
└── pages/
    └── ... (your page files)
```
