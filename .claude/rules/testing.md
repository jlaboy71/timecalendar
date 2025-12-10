# Testing Guidelines

## Test Framework
- pytest for unit tests
- Located in `tests/` directory

## Running Tests
```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe -m pytest tests/ -v
```

## Syntax Verification
Quick compile check without running:
```bash
venv\Scripts\python.exe -m py_compile path/to/file.py
```

No output = success.

## Test Database
- Use separate test database or in-memory SQLite
- Don't test against production `tjm_calendar.db`

## Service Testing Pattern
```python
def test_balance_service():
    db = next(get_db())
    try:
        service = BalanceService(db)
        balance = service.get_or_create_balance(user_id=1, year=2025)
        assert balance is not None
        assert balance.year == 2025
    finally:
        db.close()
```

## Model Testing
```python
def test_user_model():
    user = User(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        role='employee'
    )
    assert user.full_name == 'Test User'
```

## UI Testing
- NiceGUI pages are harder to unit test
- Focus on service layer testing
- Manual testing for UI workflows

## Key Test Scenarios

### PTO Request Flow
1. Create request -> status is 'pending'
2. Approve request -> status is 'approved', balance updated
3. Deny request -> status is 'denied', pending returned
4. Cancel request -> status is 'cancelled', pending returned

### Balance Calculations
1. New user gets zero balance
2. Year-end processing creates correct allocations
3. Carryover applied correctly to new year
4. Available = total + carryover - used - pending

### Multi-Year Support
1. Can create requests up to 5 years ahead
2. Balance lookup uses request start_date year
3. Year switcher shows correct data per year

### Role-Based Access
1. Employees can only see own requests
2. Managers see team requests
3. Admins see all requests
4. Manager requests auto-approve

## Pre-Commit Checks
Before committing changes:
1. Run syntax check on modified files
2. Verify application starts without errors
3. Test affected user workflows manually
