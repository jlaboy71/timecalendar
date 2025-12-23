# Database Schema & Models

## Database
- SQLite file: `pto_central.db`
- ORM: SQLAlchemy 2.0
- Migrations: Alembic

## Core Models

### User (`src/models/user.py`)
```python
- id: Integer (PK)
- username: String (unique)
- email: String (unique)
- first_name, last_name: String
- role: Enum ['employee', 'manager', 'admin', 'superadmin']
- department_id: FK to Department
- hire_date: Date
- location_state, location_city: String (for policy lookup)
- is_active: Boolean (soft delete)
- remote_schedule: JSON (weekly remote days)
```

### PTORequest (`src/models/pto_request.py`)
```python
- id: Integer (PK)
- user_id: FK to User
- pto_type: String ['vacation', 'sick', 'personal', 'bereavement', etc.]
- start_date, end_date: Date
- total_days: Decimal
- status: Enum ['pending', 'approved', 'denied', 'cancelled']
- submitted_at, approved_at: DateTime
- approved_by: FK to User (nullable)
- denial_reason: String (nullable)
- notes: String (nullable)
```

### PTOBalance (`src/models/pto_balance.py`)
```python
- id: Integer (PK)
- user_id: FK to User
- year: Integer
- vacation_total, vacation_used, vacation_pending, vacation_carryover: Decimal
- sick_total, sick_used, sick_carryover: Decimal
- personal_total, personal_used, personal_carryover: Decimal
- remote_weekly_used: Integer
```

### Department (`src/models/department.py`)
```python
- id: Integer (PK)
- name: String
- manager_id: FK to User (nullable)
```

### CarryoverRequest (`src/models/carryover_request.py`)
```python
- id: Integer (PK)
- employee_id: FK to User
- from_year, to_year: Integer
- hours_requested, hours_approved: Decimal
- status: Enum ['pending', 'approved', 'denied']
```

### LeaveType (`src/models/leave_type.py`)
```python
- id: Integer (PK)
- code: String ['VACATION', 'SICK', 'PERSONAL', etc.]
- name: String
- is_accruing: Boolean
- requires_documentation: Boolean
- sort_order: Integer
```

### LeavePolicy (`src/models/leave_policy.py`)
```python
- id: Integer (PK)
- leave_type_id: FK to LeaveType
- location_state, location_city: String (nullable for default)
- max_annual_hours, max_carryover_hours: Decimal
- waiting_period_days, advance_notice_days: Integer
- effective_date, end_date: Date
```

## Key Relationships
- User belongs to Department
- Department has one manager (User)
- PTORequest belongs to User
- PTOBalance belongs to User (one per year)
- LeavePolicy applies to LeaveType with location hierarchy

## Balance Calculation
```python
available = total + carryover - used - pending
```

## Year Handling
- Balances are per-user, per-year
- Requests use start_date.year for balance lookup
- Support for requests up to 5 years in advance

## Migration Checklist
Before adding or modifying model fields:
1. **Create migration**: `venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"`
2. **Review generated file**: Check `alembic/versions/` for the new migration
3. **Test upgrade**: `venv\Scripts\python.exe -m alembic upgrade head`
4. **Test downgrade**: `venv\Scripts\python.exe -m alembic downgrade -1` (then upgrade again)
5. **Update model docstring** if the field purpose isn't obvious

**Never modify models without considering migration impact.**
