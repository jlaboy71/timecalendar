# Testing Guidelines

## CRITICAL: SSL/HTTPS Configuration Sync (NEVER IGNORE)

**If Playwright scenarios fail with "Failed to login" or `net::ERR_EMPTY_RESPONSE`:**

This means HTTP/HTTPS mismatch. The app runs HTTPS but testing uses HTTP.

**These MUST stay in sync:**

| Component | Location | Check |
|-----------|----------|-------|
| SSL Certs | `certs/server.crt` | If exists → App uses HTTPS |
| Testing Config | `config/testing_config.py` | `base_url` must be `https://` |
| App Config | `src/config.py` | `ssl_enabled` auto-detects certs |

**Before debugging Playwright login failures:**
```bash
# Quick check - if this fails with empty response, it's HTTP/HTTPS mismatch
curl -k https://localhost:8080  # Should work if SSL enabled
curl http://localhost:8080      # Will fail if SSL enabled
```

**Fix:** Update `config/testing_config.py`:
```python
base_url = 'https://localhost:8080'  # NOT http://
```

**Root cause (Dec 2024):** SSL certs were added to `certs/` folder, enabling HTTPS automatically. Testing config was still using HTTP, causing all Playwright scenarios to fail with "empty response".

---

## CRITICAL: Video Recording Clipping Prevention (NEVER REMOVE)

**If recorded videos are clipped/cut off (not showing full app screen):**

This means the browser window is smaller than the viewport, causing content to be clipped.

**THESE MUST BE PRESENT in `services/playwright_engine.py` browser launch:**

```python
# In playwright.chromium.launch():
args=[
    f'--window-size={viewport_width + 16},{viewport_height + 100}',  # REQUIRED
    '--window-position=0,0',  # Positions window at top-left
]
```

**Why this is CRITICAL:**
- Non-headless browser windows have chrome (title bar, borders) that reduce viewport
- Without explicit `--window-size`, window defaults to smaller than 1920x1080
- Playwright's `viewport` setting only sets the content area, not the window size
- The video recording captures the viewport, which gets compressed/clipped if window is too small

**Configuration checklist (ALL must match):**
| Setting | Location | Value |
|---------|----------|-------|
| headless | `config/testing_config.py` | **True** (REQUIRED for reliable recording) |
| viewport_width | `config/testing_config.py` | 1920 |
| viewport_height | `config/testing_config.py` | 1600 (very tall to capture headers, dialogs, and full pages) |
| video_width | `config/testing_config.py` | 1920 (MUST match viewport) |
| video_height | `config/testing_config.py` | 1600 (MUST match viewport) |
| --window-size | `services/playwright_engine.py` | 1936,1700 (viewport + chrome, calculated automatically) |
| output resolution | `services/video_producer.py` | 1280x1067 (same 1.2:1 aspect ratio) |

**Why headless=True is REQUIRED:**
- Non-headless mode is limited by your monitor's physical resolution
- If monitor is ≤1920x1080 or Windows scaling is >100%, the window can't be full size
- Headless mode has NO physical constraints - viewport is always exactly 1920x1080
- You won't see the browser window, but the recording will be perfect

**Root cause (Dec 2024):** Browser launched without `--window-size` arg, and later discovered that even with `--window-size`, non-headless mode is unreliable on monitors smaller than the viewport.

---

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

## Test Quality Rules
- Don't hard-code values just to make tests pass - find the real issue
- If a test seems wrong, investigate the code behavior first
- Tests should validate business rules, not implementation details
- Avoid test workarounds - report broken tests rather than coding around them
