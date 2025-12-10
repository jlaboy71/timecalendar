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
