# UI Patterns & Components

## NiceGUI Framework
- Version: 2.x
- Built on Quasar (Vue.js components)
- Tailwind CSS for styling

## Theme & Branding

### Brand Colors
- **Primary Accent**: Gold (#c9a227) - highlights, active states, important actions
- **Navigation/Headers**: Gray (#5a6a72)
- **General UI**: Blue (#2196F3) - buttons, links, interactive elements
- Logo: Stored as base64 data URL in `nicegui_app/logo.py`

### Dark Mode
- Toggle stored in `app.storage.general['dark_mode']`
- Apply on page load: `apply_dark_mode()` from `components/theme.py`
- **Dialog backgrounds**: Use `#1f2937` for dark mode dialog cards

```python
from nicegui_app.components.theme import apply_dark_mode
apply_dark_mode()

# Dark mode dialog example
with ui.dialog() as dialog, ui.card().style('background-color: #1f2937'):
    ui.label('Dialog content')
```

## Page Structure

### Standard Page Template
```python
@ui.page('/example')
def example_page():
    if not require_auth():
        return

    apply_dark_mode()

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='PAGE TITLE', show_back=True)

        # Page content here
```

### Header Component
```python
from nicegui_app.components.header import page_header
page_header(title='DASHBOARD', show_back=False)
```

## Common UI Patterns

### Cards with Color Borders
```python
with ui.card().classes('w-full p-4 border-l-4 border-blue-500'):
    ui.label('Vacation').classes('font-semibold text-blue-600')
```

### Status Badges
```python
status_colors = {
    'pending': 'amber',
    'approved': 'green',
    'denied': 'red',
    'cancelled': 'grey'
}
ui.badge(status.title(), color=status_colors.get(status, 'grey'))
```

### Button Groups
```python
with ui.button_group().props('outline rounded'):
    ui.button('Option 1', on_click=handler1)
    ui.button('Option 2', on_click=handler2)
```

### Dynamic Content Refresh
```python
container = ui.column().classes('w-full')

def render():
    container.clear()
    with container:
        # Build dynamic content

render()  # Initial render
```

### Year Toggle Pattern
```python
current_year = date.today().year
next_year = current_year + 1
selected_year = {'value': current_year}

with ui.button_group().props('outline rounded'):
    btn_current = ui.button(str(current_year), on_click=lambda: switch(current_year))
    btn_next = ui.button(str(next_year), on_click=lambda: switch(next_year))
```

## Type-Specific Colors
```python
type_colors = {
    'vacation': 'blue',
    'sick': 'green',
    'personal': 'purple',
    'bereavement': 'brown',
    'fmla': 'teal',
    'jury_duty': 'indigo',
    'voting': 'cyan',
    'military': 'deep-orange'
}

type_icons = {
    'vacation': 'beach_access',
    'sick': 'medical_services',
    'personal': 'person',
    'bereavement': 'sentiment_very_dissatisfied',
    'fmla': 'family_restroom',
    'jury_duty': 'gavel',
    'voting': 'how_to_vote',
    'military': 'military_tech'
}
```

## Form Patterns

### Date Picker
```python
ui.date(
    value=date.today().isoformat(),
    on_change=lambda e: handle_date(e.value)
).classes('w-full')
```

### Select with Search
```python
ui.select(
    options={'key': 'Display Value'},
    with_input=True,
    on_change=handler
).props('dense outlined use-input')
```

## Notifications
```python
ui.notify('Success message', type='positive')
ui.notify('Warning message', type='warning')
ui.notify('Error message', type='negative')
```

## Navigation
```python
ui.navigate.to('/dashboard')
ui.navigate.to(f'/manager/request/{request_id}')
```

## Storage
```python
# Session storage (persists across page loads)
app.storage.general['user'] = user_data
user = app.storage.general.get('user')
```
