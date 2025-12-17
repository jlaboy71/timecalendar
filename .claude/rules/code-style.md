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

```python
# Example pattern for dynamic rendering
def render_content():
    container.clear()
    with container:
        ui.label('Dynamic content')

# Initial render
render_content()
```

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

### Check Existing Patterns First
**BEFORE proposing any new visual elements (icons, colors, styles, formats):**
1. Search the codebase for existing usage of similar elements
2. Document what patterns already exist
3. Explain any differences between existing patterns and what you're proposing
4. Ask the user before introducing inconsistencies

**Example - Adding icons:**
- First run: `Grep` for `type_icons`, `icon`, or relevant patterns
- Check [ui-patterns.md](ui-patterns.md) for documented standards
- If existing pattern can't be reused (e.g., Material icons in emails), explain WHY and propose alternatives

**Never assume** - always verify against the existing codebase first.
