---
name: pto-testing-automation
description: Generate and run tests for PTO Central including unit tests, integration tests, and Playwright UI tests. Use when creating tests, running test suites, checking coverage, or debugging test failures. Triggers on "test PTO", "generate test", "run tests", "Playwright test", "coverage report", "test scenario", "pytest", "unit test", "integration test".
---

# PTO Testing Automation Skill

## Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_balance_service.py
│   ├── test_pto_service.py
│   ├── test_policy_engine.py
│   └── test_year_end_service.py
├── integration/             # Service interaction tests
│   ├── test_request_workflow.py
│   ├── test_approval_flow.py
│   └── test_year_end_processing.py
├── ui/                      # Playwright browser tests
│   ├── test_login.py
│   ├── test_submit_request.py
│   ├── test_manager_approval.py
│   └── test_calendar_view.py
├── agents/                  # AI agent tests
│   ├── test_smart_scheduler.py
│   ├── test_year_end_optimizer.py
│   └── test_approval_assistant.py
├── mcp/                     # MCP tool tests
│   └── test_mcp_tools.py
└── conftest.py              # Shared fixtures
```

## Test Fixtures (conftest.py)

```python
import pytest
from src.database import get_db_session, init_db
from src.models import User, PTOBalance

@pytest.fixture
def db_session():
    """Provide a clean database session for each test."""
    init_db(":memory:")  # Use in-memory SQLite
    with get_db_session() as session:
        yield session

@pytest.fixture
def test_user(db_session):
    """Create a standard test employee."""
    user = User(
        username="testuser",
        email="test@haventech.com",
        role="employee",
        department_id=1
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_manager(db_session):
    """Create a test manager."""
    manager = User(
        username="testmanager",
        email="manager@haventech.com",
        role="manager",
        department_id=1
    )
    db_session.add(manager)
    db_session.commit()
    return manager

@pytest.fixture
def test_balance(db_session, test_user):
    """Create standard PTO balance for test user."""
    balance = PTOBalance(
        user_id=test_user.id,
        year=2025,
        vacation_total=10,
        sick_total=5,
        personal_total=3,
        chicago_paid_leave_total=5
    )
    db_session.add(balance)
    db_session.commit()
    return balance
```

## Unit Test Template

```python
import pytest
from src.services.balance_service import BalanceService

class TestBalanceService:
    """Tests for balance calculation service."""

    def test_get_available_balance_no_pending(self, db_session, test_user, test_balance):
        """Available balance equals total when no pending requests."""
        service = BalanceService(db_session)

        available = service.get_available_balance(test_user.id, "vacation")

        assert available == 10  # Full balance

    def test_get_available_balance_with_pending(self, db_session, test_user, test_balance):
        """Available balance deducts pending requests."""
        # Create a pending request for 3 days
        # ... setup code ...

        service = BalanceService(db_session)
        available = service.get_available_balance(test_user.id, "vacation")

        assert available == 7  # 10 - 3 pending

    def test_insufficient_balance_rejected(self, db_session, test_user, test_balance):
        """Requests exceeding balance should be rejected."""
        service = BalanceService(db_session)

        is_valid = service.validate_request(test_user.id, "vacation", days=15)

        assert is_valid is False
```

## Playwright UI Test Template

```python
import pytest
from playwright.sync_api import Page, expect

class TestPTOSubmission:
    """UI tests for PTO request submission."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Login before each test."""
        page.goto("http://localhost:8080/login")
        page.fill("#username", "ptouser01")
        page.fill("#password", "2ez4me!!")
        page.click("button[type='submit']")
        page.wait_for_url("**/dashboard")

    def test_submit_vacation_request(self, page: Page):
        """User can submit a vacation request."""
        page.goto("http://localhost:8080/request/new")

        # Fill the form
        page.select_option("#pto-type", "vacation")
        page.fill("#start-date", "2025-02-01")
        page.fill("#end-date", "2025-02-03")
        page.fill("#notes", "Family trip")

        # Submit
        page.click("button:has-text('Submit Request')")

        # Verify success
        expect(page.locator(".success-message")).to_be_visible()
        expect(page.locator(".success-message")).to_contain_text("submitted")

    def test_insufficient_balance_shows_error(self, page: Page):
        """Submitting without enough balance shows error."""
        page.goto("http://localhost:8080/request/new")

        page.select_option("#pto-type", "vacation")
        page.fill("#start-date", "2025-02-01")
        page.fill("#end-date", "2025-02-28")  # 20 days - too many

        page.click("button:has-text('Submit Request')")

        expect(page.locator(".error-message")).to_be_visible()
        expect(page.locator(".error-message")).to_contain_text("insufficient")
```

## Test Commands

```bash
# Run all tests
venv\Scripts\python.exe -m pytest tests/ -v

# Run specific test file
venv\Scripts\python.exe -m pytest tests/unit/test_balance_service.py -v

# Run tests matching pattern
venv\Scripts\python.exe -m pytest tests/ -k "balance" -v

# Run with coverage
venv\Scripts\python.exe -m pytest tests/ --cov=src --cov-report=html

# Run Playwright tests (headed - see browser)
venv\Scripts\python.exe -m pytest tests/ui/ --headed

# Run Playwright tests (headless)
venv\Scripts\python.exe -m pytest tests/ui/

# Generate coverage report
venv\Scripts\python.exe -m pytest tests/ --cov=src --cov-report=term-missing
```

## Test Data (Standard Test Users)

| Username | Password | Role | Purpose |
|----------|----------|------|---------|
| `ptouser01` | `2ez4me!!` | employee | Standard employee tests |
| `ptomanager` | `2ez4me!!` | manager | Manager approval tests |
| `ptoadmin` | `2ez4me!!` | admin | Admin function tests |

## When to Use This Skill

- Creating new test cases
- Debugging test failures
- Generating test coverage reports
- Writing Playwright UI tests
- Setting up test fixtures
