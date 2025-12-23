# Code Style Rules

## Python Conventions
- Python 3.10+ syntax
- Type hints for function parameters and returns
- Docstrings for classes and public methods
- Use `from datetime import date, datetime` (not `import datetime`)

## NiceGUI Patterns
- Use `ui.column()` and `ui.row()` for layout with Tailwind classes
- Chain `.classes()` for styling: `ui.label('Text').classes('text-lg font-bold')`
- Use `.props()` for Quasar component properties
- Dynamic content: Use `container.clear()` then rebuild with `with container:`

### App Restart Required After Code Changes
**IMPORTANT**: NiceGUI caches page code in memory. After modifying any `.py` file in `nicegui_app/`:
1. Stop the running app (Ctrl+C)
2. Restart: `venv\Scripts\python.exe nicegui_app/main.py`
3. Refresh the browser

Changes will NOT appear until the app is restarted. Always remind the user to restart after UI changes.

```python
# Example pattern for dynamic rendering
def render_content():
    container.clear()
    with container:
        ui.label('Dynamic content')

# Initial render
render_content()
```

## Brand Color Policy - ENFORCED
**CRITICAL**: All PTO Central brand colors must be imported from `nicegui_app/components/theme.py`.

### Brand Constants
```python
from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY, PTO_BLUE

# PTO_GOLD = '#C9A227'  - Primary accent (buttons, highlights)
# PTO_GRAY = '#5a6a72'  - Headers, navigation
# PTO_BLUE = '#2196F3'  - Interactive elements
```

### DO NOT Hardcode Brand Hex Values
```python
# BAD - Hardcoded hex value
ui.button('OK').style('background-color: #C9A227 !important;')

# GOOD - Use theme constant
ui.button('OK').style(f'background-color: {PTO_GOLD} !important;')
```

### CSS f-strings Require Double Braces
```python
# BAD - Will cause syntax error
ui.add_head_html(f'<style>.active { color: {PTO_GOLD}; }</style>')

# GOOD - Escaped braces for CSS
ui.add_head_html(f'<style>.active {{ color: {PTO_GOLD}; }}</style>')
```

### Enforcement
Run `python scripts/check_brand_colors.py` to detect violations.

### Exceptions
- `theme.py` is the source of truth (contains the definitions)
- Semantic status colors (green/red/amber) are NOT brand colors

## Service Layer Pattern
- Services receive `db: Session` in constructor
- Use SQLAlchemy `select()` for queries
- Commit at end of operations, not in loops
- Close database sessions in `finally` blocks

```python
class ExampleService:
    def __init__(self, db: Session):
        self.db = db

    def get_item(self, item_id: int) -> Optional[Item]:
        stmt = select(Item).where(Item.id == item_id)
        return self.db.execute(stmt).scalar_one_or_none()
```

## File Organization
- One page per file in `nicegui_app/pages/`
- One model per file in `src/models/`
- Services in `src/services/` with `_service.py` suffix
- Schemas in `src/schemas/` with `_schemas.py` suffix

## Import Order
1. Standard library
2. Third-party (nicegui, sqlalchemy, etc.)
3. Local imports (src.models, src.services, etc.)

### Required Imports - Never Forget These
**CRITICAL**: When adding database queries to any file, ALWAYS ensure these imports are at the TOP of the file:

```python
from sqlalchemy import select  # Required for select() queries
from sqlalchemy.orm import Session  # Required for type hints
```

**DO NOT use inline imports for SQLAlchemy functions.** The `select()` function must be imported at the top of the file, not inside functions.

**Before adding any `select()` query to a file:**
1. Check if `from sqlalchemy import select` exists in the imports
2. If not, ADD IT to the top of the file immediately
3. Never assume it's already imported - verify first

**Common SQLAlchemy imports needed in UI pages:**
```python
from sqlalchemy import select, and_, or_  # Query building
from src.database import get_db  # Session factory
```

This prevents `NameError: name 'select' is not defined` crashes at runtime.

## Validation Order
When validating input, follow this order:
1. **Pydantic schemas** - Request format and type validation
2. **Service business rules** - Logic validation (e.g., date ranges, balance checks)
3. **Database constraints** - Integrity (unique, foreign keys)

This order provides clear error messages at the appropriate level.

## SQLAlchemy Session Safety
- Store plain dicts in lookups, not ORM objects (prevents `DetachedInstanceError`)
- Access all needed attributes before the session closes
- Use `db.refresh(obj)` if you need updated values after commit

```python
# BAD - ORM object may become detached
user_lookup = {u.id: u for u in users}

# GOOD - Plain dict remains valid
user_lookup = {u.id: {'name': u.full_name, 'email': u.email} for u in users}
```

## Common Development Scenarios

### Adding a New Page
```python
from nicegui import ui, app
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from src.database import get_db

@ui.page('/new-feature')
def new_feature_page():
    if not require_auth():
        return

    apply_dark_mode()

    db = next(get_db())
    try:
        current_user = app.storage.general.get('user')

        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='NEW FEATURE', show_back=True)
            # Your content here
    finally:
        db.close()
```

### Adding Audit Logging to PTO Operations
```python
from src.services.audit_service import AuditService

# After changing PTO request status:
request.status = 'cancelled'
db.commit()

# Log the action
current_user = app.storage.general.get('user', {})
AuditService.log_pto_cancel(
    db=db,
    user_id=current_user.get('id'),
    username=current_user.get('username'),
    request_id=request.id,
    employee_name=employee_name,
    cancelled_by_self=True
)
```

### Creating a Dark Mode Dialog
```python
with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
    ui.label('Dialog Title').classes('text-lg font-bold mb-4')
    # Content here
    with ui.row().classes('w-full justify-end gap-2 mt-4'):
        ui.button('Cancel', on_click=dialog.close).props('flat')
        ui.button('OK', on_click=confirm).style('background-color: #C9A227 !important; color: white !important;')
```

### PTO Overdraft Policy Enforcement
**CRITICAL**: When modifying PTO balance validation in `request_form.py`, follow this policy:

**Hard Cap Types (BLOCK submission when over balance):**
```python
hard_cap_types = ['chicago_leave', 'sick', 'personal']
```
- These have fixed annual allocations - NO manager override allowed
- Submit button is DISABLED when request exceeds balance
- User sees red blocking message

**Soft Cap Types (WARNING only, allow submission):**
- `vacation` - Manager can approve overdraft requests
- Submit button remains ENABLED
- User sees amber warning message

**Code Location:** `nicegui_app/pages/request_form.py` lines 1012-1052

**DO NOT:**
- Allow overdraft for Sick, Personal, or Chicago Leave
- Add new accruing types without deciding their cap policy
- Change this logic without updating `business-rules.md`

### Vacation Rollover Balance Handling
**CRITICAL**: When vacation rollover is involved (`carryover_from_year` is set), ALWAYS use that year for balance operations, NOT `start_date.year`.

**The Pattern:**
```python
# CORRECT - Check carryover_from_year first
balance_year = request.carryover_from_year if request.carryover_from_year else request.start_date.year
balance = balance_service.get_or_create_balance(request.user_id, balance_year)

# WRONG - Using start_date.year directly
balance = balance_service.get_or_create_balance(request.user_id, request.start_date.year)
```

**Files that handle vacation balance (ALL must use this pattern):**
- `src/services/pto_service.py` - create_request, approve_request, deny_request, cancel_request
- `nicegui_app/pages/dashboard.py` - cancel_request, cancel_pending_request, delete_request_direct, delete_approved_request_employee
- `nicegui_app/pages/requests.py` - cancel_user_request, cancel_approved_request
- `nicegui_app/pages/manager_request_detail.py` - approve_cancellation
- `nicegui_app/pages/request_form.py` - get_leave_balance, update_warning

**Why this matters:**
- Vacation rollover requests are for January 2026 but use 2025 balance
- If you use `start_date.year` (2026), pending/used goes to wrong year
- This causes phantom pending days and corrupted balance data

**When modifying ANY vacation balance code:**
1. Search for `carryover_from_year` usage in that file
2. Verify the pattern is applied consistently
3. Test with a vacation rollover request

### Modifying Email Templates
**CRITICAL**: When modifying email templates, you MUST update ALL THREE locations that contain email template code.

**Files to update together:**
1. `src/services/email_service.py` - Actual email sending functions
2. `nicegui_app/pages/admin_email_preview.py` - Standalone preview page
3. `nicegui_app/pages/admin_system.py` - **EMBEDDED preview** in System Administration (lines ~1006-1150)

**Shared helpers** (import in all files that render email templates):
```python
from src.services.email_service import _get_email_template, _get_pto_type_icon, _format_date_range_with_days
```
- `_get_pto_type_icon(pto_type)` - Returns emoji for PTO type
- `_format_date_range_with_days(start, end)` - Formats dates with day of week
- `_get_email_template(title, title_color, content, footer_text)` - Base template

**After changes**: Always restart the app and verify at System Administration → Email Config

## General Rules

### Verify Interactive Elements Before Testing
**CRITICAL**: Before telling the user to test any UI changes:
1. **Verify syntax** - Run `py_compile` on all modified files
2. **Review click handlers** - Ensure all buttons/links have proper closures
3. **Check closure capture** - When using lambdas in loops, use default arguments: `lambda d=dept: handler(d)`
4. **Trace navigation** - Confirm click handlers navigate to correct destinations
5. **Test error handling** - Wrap handlers in try/except to prevent silent failures

**Common closure bug pattern:**
```python
# BAD - All buttons will reference the last item
for item in items:
    ui.button('Click', on_click=lambda: handle(item))

# BAD - Missing event parameter 'e' (NiceGUI passes click event)
for item in items:
    ui.button('Click', on_click=lambda i=item: handle(i))

# GOOD - Include 'e' for event AND capture value with default arg
for item in items:
    ui.button('Click', on_click=lambda e, i=item: handle(i))

# ALSO GOOD for card.on('click') - same pattern
for item in items:
    item_copy = dict(item)
    card.on('click', lambda e, i=item_copy: handle(i))
```

**CRITICAL**: NiceGUI click handlers pass an event argument. Always include `e` as the first lambda parameter!

**Nested dialog pattern (opening dialog from dialog):**
```python
from nicegui import context

def open_edit_dialog(item):
    # Use context.client.content to create at root level
    with context.client.content:
        with ui.dialog() as dialog, ui.card():
            # dialog content here
        dialog.open()
```
Without `context.client.content`, the new dialog is created inside the parent dialog's context and gets hidden when the parent closes!

**Opening dialog from slide-out panel (CRITICAL timing):**
When opening a dialog after closing a slide-out panel, you MUST:
1. Capture `context.client` BEFORE closing the panel
2. Create the timer BEFORE calling `panel.close()`
3. Use the captured client in the timer callback

```python
def edit_handler():
    item_copy = dict(item)  # Capture data
    client = context.client  # Capture client BEFORE closing

    def delayed_open():
        with client.content:
            with ui.dialog() as dialog, ui.card():
                # dialog content using item_copy
            dialog.open()

    # Create timer FIRST, then close panel
    ui.timer(0.15, delayed_open, once=True)
    panel.close()  # Close AFTER timer is created
```
If you close the panel before creating the timer, the timer may not fire properly!

### Check Existing Patterns First - THE WHEEL IS ALREADY INVENTED
**MANDATORY**: Before adding ANY UI element, ALWAYS search the codebase first. Do not assume - verify.

**For ANY new UI element (buttons, dialogs, cards, labels, etc.):**
1. **STOP** - Do not write code yet
2. **SEARCH** - Use Grep to find existing examples of that element type
3. **COPY** - Use the exact same pattern (props, classes, styles)
4. **ADAPT** - Only change what's necessary for your specific use case

**Common elements - ALWAYS search first:**
| Element | Search Pattern |
|---------|---------------|
| Back button | `Grep: 'Back.*arrow_back'` |
| Dialog | `Grep: 'ui.dialog'` |
| Card styling | `Grep: 'ui.card().classes'` |
| Status badges | `Grep: 'ui.badge'` |
| Gold styling | `Grep: 'C9A227'` |
| Notifications | `Grep: 'ui.notify'` |

**Example - Back Button (CORRECT approach):**
```bash
# FIRST: Search for existing back buttons
Grep: 'Back.*arrow_back'
```
Result shows pattern:
```python
ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6').style('border-color: #C9A227 !important; color: #C9A227 !important;')
```
Use THIS pattern. Don't invent your own.

**Example - Adding icons:**
- First run: `Grep` for `type_icons`, `icon`, or relevant patterns
- Check [ui-patterns.md](ui-patterns.md) for documented standards
- If existing pattern can't be reused (e.g., Material icons in emails), explain WHY and propose alternatives

**NEVER assume** - the codebase already has established patterns. Find them and use them.
