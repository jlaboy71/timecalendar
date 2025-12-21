# Database Migrations Skill

This skill provides patterns for safe Alembic migrations in PTO Central.

---

## 1. Migration Commands

```bash
# Create new migration (auto-detect changes)
venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"

# Create empty migration (manual)
venv\Scripts\python.exe -m alembic revision -m "description"

# Apply all pending migrations
venv\Scripts\python.exe -m alembic upgrade head

# Downgrade one step
venv\Scripts\python.exe -m alembic downgrade -1

# View current revision
venv\Scripts\python.exe -m alembic current

# View migration history
venv\Scripts\python.exe -m alembic history
```

---

## 2. Migration Checklist

Before creating/running any migration:

- [ ] **Read existing model** - Understand current state
- [ ] **Create migration** - Use autogenerate or manual
- [ ] **Review generated file** - Check `alembic/versions/` for new file
- [ ] **Test upgrade** - Run `alembic upgrade head`
- [ ] **Test downgrade** - Run `alembic downgrade -1`
- [ ] **Re-upgrade** - Run `alembic upgrade head` again
- [ ] **Update model docstring** - Document new fields

---

## 3. Safe Migration Pattern (SQLite)

SQLite has limitations - always check if tables/columns exist:

```python
"""add_new_column

Revision ID: abc123xyz
Revises: previous_id
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'abc123xyz'
down_revision: Union[str, None] = 'previous_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get connection to check existing state
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'target_table' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('target_table')]

        if 'new_column' not in existing_columns:
            op.add_column('target_table', sa.Column(
                'new_column',
                sa.String(50),
                nullable=True,
                server_default='default_value',
                comment='Description of the column'
            ))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'target_table' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('target_table')]

        if 'new_column' in existing_columns:
            op.drop_column('target_table', 'new_column')
```

---

## 4. Common Column Types

```python
# String columns
sa.Column('name', sa.String(100), nullable=False)
sa.Column('code', sa.String(20), unique=True)
sa.Column('description', sa.Text, nullable=True)

# Numeric columns
sa.Column('amount', sa.Numeric(10, 2), nullable=False, server_default='0.00')
sa.Column('count', sa.Integer, nullable=False, server_default='0')

# Boolean columns
sa.Column('is_active', sa.Boolean, nullable=False, server_default='1')

# Date/Time columns
sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
sa.Column('hire_date', sa.Date, nullable=False)

# Foreign Key columns
sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False)
```

---

## 5. Adding Balance Fields Pattern

When adding new PTO balance tracking fields:

```python
def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'pto_balances' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('pto_balances')]

        # Always add all 4 fields together for new leave type
        new_columns = [
            ('new_type_total', 'Hours allocated for the year'),
            ('new_type_used', 'Hours used'),
            ('new_type_pending', 'Hours in pending requests'),
            ('new_type_carryover', 'Hours carried over from previous year'),
        ]

        for col_name, comment in new_columns:
            if col_name not in existing_columns:
                op.add_column('pto_balances', sa.Column(
                    col_name,
                    sa.Numeric(5, 2),
                    nullable=False,
                    server_default='0.00',
                    comment=comment
                ))
```

---

## 6. Index Migrations

```python
# Add index
def upgrade() -> None:
    op.create_index(
        'ix_pto_requests_user_status',
        'pto_requests',
        ['user_id', 'status'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_pto_requests_user_status', table_name='pto_requests')
```

### Index Naming Convention
- Single column: `ix_{table}_{column}`
- Composite: `ix_{table}_{col1}_{col2}`
- Unique: `uq_{table}_{column}`

---

## 7. Table Creation

```python
def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'new_table' not in existing_tables:
        op.create_table(
            'new_table',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index('ix_new_table_user_id', 'new_table', ['user_id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'new_table' in existing_tables:
        op.drop_index('ix_new_table_user_id', table_name='new_table')
        op.drop_table('new_table')
```

---

## 8. SQLite Limitations

SQLite does NOT support:
- `ALTER TABLE ... DROP COLUMN` (before SQLite 3.35.0)
- `ALTER TABLE ... RENAME COLUMN` (before SQLite 3.25.0)
- `ALTER TABLE ... ALTER COLUMN` (changing type/constraints)
- Adding NOT NULL without default

### Workaround: Batch Operations
```python
def upgrade() -> None:
    # For complex alterations, use batch_alter_table
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('old_name', new_column_name='new_name')
        batch_op.drop_column('deprecated_column')
```

---

## 9. Data Migrations

When migrations need to transform data:

```python
def upgrade() -> None:
    bind = op.get_bind()

    # Add new column first
    op.add_column('users', sa.Column('full_name', sa.String(100), nullable=True))

    # Populate with existing data
    bind.execute(sa.text(
        "UPDATE users SET full_name = first_name || ' ' || last_name"
    ))

    # Now make NOT NULL if needed
    # (SQLite may require batch_alter_table for this)
```

---

## 10. Revision ID Conventions

```python
# Auto-generated (random hex)
revision: str = 'abc123def456'

# Manual (descriptive)
revision: str = 'a1b2c3d4e5f6'  # Incrementing pattern
revision: str = 'd4e5f6g7h8i9'  # Next in sequence
```

### Existing Revision Chain
```
d1d45e7991f9  # Initial migration
    ↓
7a10c44fef3f  # Add composite indexes
    ↓
...
    ↓
h8i9j0k1l2m3  # Latest
```

---

## 11. Testing Migrations

```bash
# Full migration cycle test
venv\Scripts\python.exe -m alembic downgrade base
venv\Scripts\python.exe -m alembic upgrade head

# Single migration test
venv\Scripts\python.exe -m alembic upgrade +1
venv\Scripts\python.exe -m alembic downgrade -1
venv\Scripts\python.exe -m alembic upgrade +1
```

### Verify Application Works
```bash
# After migration, check app starts
venv\Scripts\python.exe -c "from src.database import get_db; print('OK')"
```

---

## 12. Common Pitfalls

### 1. Not Checking Existing State
```python
# WRONG: Crashes if column exists
op.add_column('users', sa.Column('email', sa.String(100)))

# RIGHT: Check first
if 'email' not in existing_columns:
    op.add_column('users', sa.Column('email', sa.String(100)))
```

### 2. Forgetting server_default
```python
# WRONG: NOT NULL without default fails on existing rows
op.add_column('users', sa.Column('is_active', sa.Boolean, nullable=False))

# RIGHT: Provide default
op.add_column('users', sa.Column('is_active', sa.Boolean, nullable=False, server_default='1'))
```

### 3. Missing Downgrade
```python
# WRONG: Empty downgrade
def downgrade() -> None:
    pass

# RIGHT: Reverse the upgrade
def downgrade() -> None:
    op.drop_column('users', 'new_column')
```

### 4. Model/Migration Mismatch
```python
# After adding column to model, MUST create migration
# After running migration, MUST update model to match

# Check sync:
venv\Scripts\python.exe -m alembic check
```

---

## 13. File Structure

```
alembic/
├── env.py              # Alembic environment config
├── script.py.mako      # Migration template
└── versions/           # Migration files
    ├── d1d45e7991f9_initial.py
    ├── abc123_add_feature.py
    └── xyz789_latest.py

alembic.ini             # Alembic configuration
```

---

## 14. Emergency Recovery

If migrations get corrupted:

```bash
# Check current state
venv\Scripts\python.exe -m alembic current

# Force stamp to specific revision (skip migrations)
venv\Scripts\python.exe -m alembic stamp abc123

# Reset to clean state (DESTRUCTIVE)
venv\Scripts\python.exe -m alembic downgrade base
venv\Scripts\python.exe -m alembic upgrade head
```
