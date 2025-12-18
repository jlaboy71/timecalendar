---
name: nicegui-ui
description: Use when building or modifying NiceGUI pages, components, dialogs, charts, or any UI work. Provides TJM brand patterns, imports, page structure, validation, dialogs, charts, audit logging, and error handling.
---

# TJM NiceGUI UI Patterns - Complete Reference

## 1. Required Imports

### Standard Page Imports
```python
from nicegui import ui, app
from datetime import date, datetime
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import (
    apply_dark_mode,
    show_success_dialog,
    show_error_dialog,
    show_warning_dialog,
    show_help_dialog,
    create_help_button,
    skeleton_loader,
    skeleton_card,
    skeleton_table,
)
from nicegui_app.components.formatting import format_days_hours, fmt_days
from src.database import get_db
```

### For Pages with Audit Logging
```python
from src.services.audit_service import AuditService
```

### For Pages with Charts
```python
from nicegui_app.components.charts import (
    attendance_heatmap,
    monthly_trend_chart,
    department_utilization_bars,
    coverage_timeline,
    day_of_week_pattern,
    carryover_risk_gauge,
    year_comparison_chart,
    simple_pie_chart,
)
```

---

## 2. TJM Brand Colors

```python
# Primary colors
TJM_GOLD = '#C9A227'      # Primary accent, buttons, active states
TJM_GRAY = '#5a6a72'      # Headers, navigation

# Background colors
DARK_BG = '#1f2937'       # Dialog backgrounds (dark mode)
DARK_PAGE_BG = '#1E2328'  # Page background (dark mode)
LIGHT_PAGE_BG = '#E8E6E1' # Page background (light mode)

# Leave type colors
TYPE_COLORS = {
    'vacation': '#3b82f6',    # blue
    'sick': '#22c55e',        # green
    'personal': '#a855f7',    # purple
    'bereavement': '#78350f', # brown
    'fmla': '#0d9488',        # teal
    'jury_duty': '#4f46e5',   # indigo
    'voting': '#06b6d4',      # cyan
    'military': '#ea580c',    # deep-orange
}

# Status colors (Quasar color names)
STATUS_COLORS = {
    'pending': 'amber',
    'approved': 'green',
    'denied': 'red',
    'cancelled': 'grey',
}

# Material icons
TYPE_ICONS = {
    'vacation': 'beach_access',
    'sick': 'medical_services',
    'personal': 'person',
    'bereavement': 'sentiment_very_dissatisfied',
    'fmla': 'family_restroom',
    'jury_duty': 'gavel',
    'voting': 'how_to_vote',
    'military': 'military_tech',
}
```

---

## 3. Standard Page Structure

```python
@ui.page('/my-page')
def my_page():
    # 1. Authentication check
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    # 2. Apply dark mode (ALWAYS)
    apply_dark_mode()

    # 3. Database session with proper cleanup
    db = next(get_db())
    try:
        user_role = user.get('role', 'employee')
        user_id = user.get('id')

        # 4. Page container
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            # 5. Header
            page_header(title='PAGE TITLE', show_back=True)

            # 6. Content
            with ui.card().classes('w-full p-4'):
                ui.label('Content here')

    finally:
        db.close()
```

### Role-Restricted Page
```python
@ui.page('/admin/settings')
def admin_settings():
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    # Role check
    user_role = user.get('role', 'employee')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/dashboard')
        ui.notify('Access denied', type='negative')
        return

    apply_dark_mode()
    # ... rest of page
```

---

## 4. Cards and Layout

### Card with Left Color Border
```python
with ui.card().classes('w-full p-4').style(f'border-left: 4px solid {TYPE_COLORS["vacation"]};'):
    ui.label('VACATION').classes('font-bold text-blue-500')
    ui.label('10 days available').classes('text-sm opacity-70')
```

### Horizontal Stats Row
```python
with ui.row().classes('w-full gap-4'):
    with ui.card().classes('p-4 text-center flex-1'):
        ui.label('24').classes('text-2xl font-bold text-blue-500')
        ui.label('Available').classes('text-xs opacity-60')

    with ui.card().classes('p-4 text-center flex-1'):
        ui.label('8').classes('text-2xl font-bold text-green-500')
        ui.label('Used').classes('text-xs opacity-60')
```

### Section with Header
```python
with ui.card().classes('w-full'):
    with ui.card_section().classes('p-4'):
        with ui.row().classes('items-center gap-2 mb-3'):
            ui.icon('beach_access', size='md').style('color: #3b82f6;')
            ui.label('VACATION BALANCE').classes('text-lg font-bold')
            create_help_button('Vacation Info', 'Your vacation balance includes...')
        # Section content here
```

---

## 5. Buttons

### TJM Gold Primary Button
```python
ui.button('Submit', on_click=handler).style('background-color: #C9A227 !important; color: white !important;')
```

### TJM Gold Outline Button
```python
ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').style('border-color: #C9A227 !important; color: #C9A227 !important;')
```

### Button Group (Toggle)
```python
with ui.button_group().props('outline rounded'):
    ui.button('2024', on_click=lambda: switch_year(2024))
    ui.button('2025', on_click=lambda: switch_year(2025))
```

### Icon Button
```python
ui.button(icon='edit', on_click=edit_handler).props('flat round dense').style('color: #C9A227;')
```

---

## 6. Dialogs

### Success Dialog
```python
show_success_dialog('Request Submitted', 'Your PTO request has been submitted.')
```

### Success with Navigation
```python
show_success_dialog(
    'Request Approved',
    'The request has been approved.',
    on_close=lambda: ui.navigate.to('/dashboard')
)
```

### Error Dialog
```python
show_error_dialog('Cannot Submit', 'Insufficient balance for this request.')
```

### Warning Dialog
```python
show_warning_dialog('Low Balance', 'You only have 8 hours remaining.')
```

### Help Dialog (Dark themed, HTML content)
```python
show_help_dialog(
    'How Carryover Works',
    '''
    <b>Sick Leave:</b> Rolls over automatically (up to 80 hours)<br><br>
    <b>Vacation:</b> Use-it-or-lose-it by default<br>
    Exception carryover requires manager approval<br><br>
    <b>Personal:</b> Does NOT carry over
    '''
)
```

### Help Button (? icon)
```python
with ui.row().classes('items-center gap-2'):
    ui.label('VACATION').classes('text-lg font-bold')
    create_help_button('Vacation Info', '<b>Available:</b> Hours you can request<br>...')
```

### Custom Confirmation Dialog
```python
with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
    ui.label('Confirm Action').classes('text-lg font-bold mb-4')
    ui.label('Are you sure you want to proceed?').classes('mb-4')

    with ui.row().classes('w-full justify-end gap-2'):
        ui.button('Cancel', on_click=dialog.close).props('flat')
        ui.button('Confirm', on_click=do_action).style('background-color: #C9A227 !important; color: white !important;')

dialog.open()
```

### Double Confirmation (Destructive Actions)
```python
def show_delete_confirm():
    with ui.dialog() as confirm1, ui.card().classes('p-4 max-w-sm'):
        ui.label('Delete this request?').classes('text-lg font-semibold mb-2')
        ui.label('This will restore your PTO balance.').classes('text-sm opacity-70 mb-4')
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('No, Keep It', on_click=confirm1.close).props('flat')
            def show_second_confirm():
                confirm1.close()
                with ui.dialog() as confirm2, ui.card().classes('p-4 max-w-sm'):
                    ui.label('Are you sure?').classes('text-lg font-semibold mb-2 text-red-600')
                    ui.label('This cannot be undone.').classes('text-sm opacity-70 mb-4')
                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancel', on_click=confirm2.close).props('flat')
                        ui.button('Yes, Delete', on_click=lambda: do_delete(confirm2)).props('color=negative')
                confirm2.open()
            ui.button('Yes, Delete', on_click=show_second_confirm).props('color=negative')
    confirm1.open()
```

### Info Dialog (Type/Status Info)
```python
with ui.dialog() as info_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
    with ui.row().classes('items-center gap-3 mb-4'):
        ui.icon('beach_access', size='lg').style('color: #3b82f6;')
        ui.label('Vacation').classes('text-lg font-bold').style('color: #3b82f6;')
    ui.label('Use for personal time off, travel, or relaxation.').classes('text-sm opacity-80')
    with ui.row().classes('w-full justify-end mt-4'):
        ui.button('OK', on_click=info_dialog.close).style('background-color: #C9A227 !important; color: white !important;')
info_dialog.open()
```

---

## 7. Dynamic Content Pattern

```python
container = ui.column().classes('w-full')

def render_content():
    container.clear()
    with container:
        for item in items:
            with ui.card().classes('w-full p-3 mb-2'):
                ui.label(item.name)

render_content()  # Initial render
```

### With Loading State
```python
loading = {'value': True}
container = ui.column().classes('w-full')

async def load_data():
    loading['value'] = True
    render_content()
    # Fetch data...
    data = await fetch_data()
    loading['value'] = False
    render_content()

def render_content():
    container.clear()
    with container:
        if loading['value']:
            skeleton_loader(rows=5)
        else:
            for item in data:
                ui.label(item.name)
```

---

## 8. Tables

### Basic Table
```python
columns = [
    {'name': 'name', 'label': 'Employee', 'field': 'name', 'align': 'left', 'sortable': True},
    {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left'},
    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
]

rows = [
    {'name': 'John Doe', 'type': 'Vacation', 'status': 'Approved'},
]

ui.table(columns=columns, rows=rows, row_key='name').classes('w-full')
```

### Table with Row Actions
```python
def create_table():
    columns = [
        {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
        {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
    ]

    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')

    table.add_slot('body-cell-actions', '''
        <q-td :props="props">
            <q-btn flat round dense icon="edit" @click="$parent.$emit('edit', props.row)" />
            <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete', props.row)" />
        </q-td>
    ''')

    table.on('edit', lambda e: handle_edit(e.args))
    table.on('delete', lambda e: handle_delete(e.args))
```

---

## 9. Forms

### Input with Validation
```python
email_input = ui.input('Email').props('outlined dense').classes('w-full')

def validate_and_submit():
    if not email_input.value:
        email_input.props('error error-message="Email is required"')
        return
    email_input.props(remove='error error-message')
    # Submit...
```

### Select Dropdown
```python
options = {'vacation': 'Vacation', 'sick': 'Sick Leave', 'personal': 'Personal'}

ui.select(
    options=options,
    value='vacation',
    on_change=lambda e: handle_change(e.value)
).props('outlined dense').classes('w-full')
```

### Date Picker
```python
ui.date(
    value=date.today().isoformat(),
    on_change=lambda e: set_date(e.value)
).props('outlined dense').classes('w-full')
```

### Textarea
```python
ui.textarea('Notes', value='').props('outlined autogrow').classes('w-full')
```

---

## 10. Audit Logging

### After PTO Request Submission
```python
from src.services.audit_service import AuditService

# After creating request
db.commit()

user = app.storage.general.get('user', {})
AuditService.log_pto_request(
    db=db,
    user_id=user.get('id'),
    username=user.get('username'),
    request_id=new_request.id,
    details={
        'type': pto_type,
        'start': str(start_date),
        'end': str(end_date),
        'days': float(total_days)
    }
)
```

### After PTO Approval
```python
AuditService.log_pto_approve(
    db=db,
    approver_id=user.get('id'),
    approver_name=user.get('username'),
    request_id=request.id,
    employee_name=employee.full_name
)
```

### After PTO Denial
```python
AuditService.log_pto_deny(
    db=db,
    approver_id=user.get('id'),
    approver_name=user.get('username'),
    request_id=request.id,
    employee_name=employee.full_name,
    reason=denial_reason
)
```

### After PTO Cancellation
```python
AuditService.log_pto_cancel(
    db=db,
    user_id=user.get('id'),
    username=user.get('username'),
    request_id=request.id,
    employee_name=employee.full_name,
    cancelled_by_self=True
)
```

### Available Audit Methods
- `log_login(db, user_id, username, success=True)`
- `log_logout(db, user_id, username)`
- `log_pto_request(db, user_id, username, request_id, details)`
- `log_pto_approve(db, approver_id, approver_name, request_id, employee_name)`
- `log_pto_deny(db, approver_id, approver_name, request_id, employee_name, reason)`
- `log_pto_cancel(db, user_id, username, request_id, employee_name, cancelled_by_self)`
- `log_user_create(db, admin_id, admin_name, new_user_id, new_username)`
- `log_user_update(db, admin_id, admin_name, target_user_id, changes)`
- `log_user_deactivate(db, admin_id, admin_name, target_user_id, target_username)`
- `log_carryover_request(db, user_id, username, request_id, hours, from_year, to_year)`
- `log_carryover_approve(db, approver_id, approver_name, request_id, employee_name, hours)`
- `log_carryover_deny(db, approver_id, approver_name, request_id, employee_name, reason)`

---

## 11. Charts (Plotly)

### Monthly Trend Chart
```python
from nicegui_app.components.charts import monthly_trend_chart

monthly_data = [
    {'month': 1, 'vacation_days': 45, 'sick_days': 12, 'personal_days': 8},
    {'month': 2, 'vacation_days': 38, 'sick_days': 15, 'personal_days': 6},
    # ...
]
monthly_trend_chart(monthly_data, title='PTO Usage by Month')
```

### Department Utilization Bars
```python
from nicegui_app.components.charts import department_utilization_bars

dept_data = [
    {'department_name': 'Engineering', 'utilization_rate': 78.5},
    {'department_name': 'Sales', 'utilization_rate': 65.2},
]
department_utilization_bars(dept_data)
```

### Simple Pie Chart
```python
from nicegui_app.components.charts import simple_pie_chart

data = [
    {'label': 'Vacation', 'value': 120, 'color': '#3b82f6'},
    {'label': 'Sick', 'value': 45, 'color': '#22c55e'},
    {'label': 'Personal', 'value': 30, 'color': '#a855f7'},
]
simple_pie_chart(data, title='PTO Distribution')
```

### Carryover Risk Gauge
```python
from nicegui_app.components.charts import carryover_risk_gauge

carryover_risk_gauge(at_risk_count=12, total_employees=50, title='Employees at Carryover Risk')
```

---

## 12. Formatting Utilities

### Format Days/Hours
```python
from nicegui_app.components.formatting import format_days_hours

hours = 22.4
display, tooltip = format_days_hours(hours)
# display = "2 days and 6 hours"
# tooltip = "2.8 days (22 hours)"

ui.label(display).tooltip(tooltip)
```

### Format Days Only
```python
from nicegui_app.components.formatting import fmt_days

days = 2.5
result = fmt_days(days)  # "2 days and 4 hours"
```

---

## 13. Navigation

```python
# Navigate to page
ui.navigate.to('/dashboard')
ui.navigate.to(f'/manager/request/{request_id}')

# Browser back
def go_back():
    ui.run_javascript('window.history.back()')

# Or import from header
from nicegui_app.components.header import go_back
```

---

## 14. Notifications

```python
ui.notify('Request submitted', type='positive')
ui.notify('Please fill all fields', type='warning')
ui.notify('Error saving', type='negative')
ui.notify('Loading...', type='info')
```

---

## 15. Status Badges

```python
status = 'approved'
ui.badge(status.title(), color=STATUS_COLORS.get(status, 'grey'))

# With size
ui.badge('Pending', color='amber').classes('text-lg px-4 py-1')
```

---

## 16. Skeleton Loaders

```python
# Simple lines
skeleton_loader(rows=3)

# Card placeholder
skeleton_card()

# Table placeholder
skeleton_table(rows=5, cols=4)
```

---

## 17. Print Styles

Add `no-print` class to elements that should not print:
```python
ui.button('Print', on_click=lambda: ui.run_javascript('window.print()')).classes('no-print')
```

---

## 18. Year Toggle Pattern

```python
current_year = date.today().year
selected_year = {'value': current_year}

def switch_year(year: int):
    selected_year['value'] = year
    render_content()

with ui.button_group().props('outline rounded'):
    btn_current = ui.button(str(current_year), on_click=lambda: switch_year(current_year))
    btn_next = ui.button(str(current_year + 1), on_click=lambda: switch_year(current_year + 1))

# Highlight selected
def update_button_styles():
    if selected_year['value'] == current_year:
        btn_current.style('background-color: #C9A227 !important; color: white !important;')
        btn_next.style(remove='background-color; color')
    else:
        btn_next.style('background-color: #C9A227 !important; color: white !important;')
        btn_current.style(remove='background-color; color')
```

---

## 19. Role Check Patterns

```python
user = app.storage.general.get('user', {})
user_role = user.get('role', 'employee')

# Manager+ access
if user_role in ['manager', 'admin', 'superadmin']:
    # Show manager features
    pass

# Admin+ access
if user_role in ['admin', 'superadmin']:
    # Show admin features
    pass

# SuperAdmin only
if user_role == 'superadmin':
    # Show superadmin features
    pass

# Check if user is a manager (has direct reports)
is_manager = user_role in ['manager', 'admin', 'superadmin']
```

---

## 20. Error Handling Pattern

```python
@ui.page('/my-page')
def my_page():
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    apply_dark_mode()

    db = next(get_db())
    try:
        # Page logic here
        pass
    except Exception as e:
        show_error_dialog('Error', f'An error occurred: {str(e)}')
    finally:
        db.close()  # ALWAYS close the session
```

---

## 21. Storage Patterns

```python
# Get current user
user = app.storage.general.get('user')
user_id = user.get('id')
username = user.get('username')
role = user.get('role')

# Get dark mode preference
is_dark = app.storage.general.get('dark_mode', True)

# Store temporary state
app.storage.general['selected_employee_id'] = employee_id
```
