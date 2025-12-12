# TJM Time Calendar - Production Readiness Roadmap

## Purpose
This document provides step-by-step instructions to transition the TJM Time Calendar application from development to a secure, production-ready deployment. Follow each phase sequentially. Do not proceed to the next phase until all verification checkpoints pass.

## Critical Rules
1. **No functionality regression** - Every change must preserve existing features
2. **Verify before proceeding** - Run all checkpoints before moving to next phase
3. **Minimal changes** - Impact as little code as possible per change
4. **Backup first** - Create backups before any destructive operations
5. **Test after each change** - Confirm the app starts and basic navigation works

---

## Pre-Flight Checklist

Before beginning any work, complete these steps:

### 1. Create Project Backup
```bash
cd c:\Users\jlaboy\codelab\projects
xcopy /E /I TimeCalendar TimeCalendar_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%
```

### 2. Verify Current State
```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe -m py_compile nicegui_app/main.py
venv\Scripts\python.exe nicegui_app/main.py
```
- Confirm app starts without errors
- Confirm you can access http://localhost:8080
- Confirm login works
- Confirm navigation to dashboard, calendar, and admin pages works

### 3. Document Current Behavior
Create a checklist of current working features to verify after each phase:
- [ ] Login/logout functionality
- [ ] Dashboard displays correctly
- [ ] PTO request submission works
- [ ] PTO request approval/denial works (manager/admin)
- [ ] Balance calculations display correctly
- [ ] Calendar view renders
- [ ] Admin user management works
- [ ] Year toggle functionality works

---

## Phase 1: Bug Audit & Code Health

**Objective:** Identify and fix any existing bugs before making security changes.

### Step 1.1: Syntax Verification
Run syntax checks on all Python files:
```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar

# Check all nicegui_app files
for /R nicegui_app %%f in (*.py) do venv\Scripts\python.exe -m py_compile "%%f"

# Check all src files
for /R src %%f in (*.py) do venv\Scripts\python.exe -m py_compile "%%f"
```
**Expected:** No output means no syntax errors.

### Step 1.2: Import Verification
Create and run a test script to verify all imports work:
```python
# test_imports.py - Create in project root
import sys
sys.path.insert(0, '.')

try:
    # Models
    from src.models.user import User
    from src.models.pto_request import PTORequest
    from src.models.pto_balance import PTOBalance
    from src.models.department import Department
    print("✓ Models import successfully")
except Exception as e:
    print(f"✗ Model import error: {e}")

try:
    # Services
    from src.services.balance_service import BalanceService
    from src.services.request_service import RequestService
    print("✓ Services import successfully")
except Exception as e:
    print(f"✗ Service import error: {e}")

try:
    # Database
    from src.database import get_db, engine
    print("✓ Database imports successfully")
except Exception as e:
    print(f"✗ Database import error: {e}")

print("\nImport verification complete.")
```

Run it:
```bash
venv\Scripts\python.exe test_imports.py
```

### Step 1.3: Database Integrity Check
```python
# test_database.py - Create in project root
from src.database import get_db
from src.models.user import User
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from sqlalchemy import select

db = next(get_db())
try:
    # Count records
    users = db.execute(select(User)).scalars().all()
    print(f"✓ Users table: {len(users)} records")
    
    balances = db.execute(select(PTOBalance)).scalars().all()
    print(f"✓ PTOBalance table: {len(balances)} records")
    
    requests = db.execute(select(PTORequest)).scalars().all()
    print(f"✓ PTORequest table: {len(requests)} records")
    
    # Verify relationships
    for user in users[:3]:  # Check first 3 users
        print(f"  - User {user.username}: role={user.role}, active={user.is_active}")
    
    print("\n✓ Database integrity check passed")
except Exception as e:
    print(f"✗ Database error: {e}")
finally:
    db.close()
```

### Step 1.4: Review Console Output for Warnings
Start the application and monitor console output:
```bash
venv\Scripts\python.exe nicegui_app/main.py 2>&1 | findstr /i "warning error exception"
```
Document any warnings or errors found.

### Step 1.5: Test Core User Workflows
Manually verify these workflows work:

**Employee Workflow:**
1. Login as employee
2. View dashboard and balances
3. Submit a new PTO request
4. View submitted request in list
5. Logout

**Manager Workflow:**
1. Login as manager
2. View team pending requests
3. Approve one request
4. Deny one request (with reason)
5. Submit own PTO request (should auto-approve)
6. Logout

**Admin Workflow:**
1. Login as admin
2. Access admin panel
3. View user list
4. Edit a user's details
5. View all PTO requests
6. Logout

### Phase 1 Verification Checkpoint ✓
Before proceeding, confirm:
- [ ] All syntax checks pass (no output)
- [ ] All imports work (test_imports.py passes)
- [ ] Database integrity check passes
- [ ] No critical console warnings/errors
- [ ] All user workflows complete successfully
- [ ] App starts and stops cleanly

**If any check fails:** Fix the issue before proceeding. Document the fix.

---

## Phase 2: Security Audit

**Objective:** Identify security vulnerabilities and document them for remediation.

### Step 2.1: Authentication Security Audit

Review these files and document findings:

**File: `nicegui_app/pages/login.py`**
Check for:
- [ ] Password comparison method (plaintext vs hashed?)
- [ ] Session token generation method
- [ ] Login attempt rate limiting
- [ ] Account lockout after failed attempts

**File: `src/models/user.py`**
Check for:
- [ ] Password field type and storage
- [ ] Password hashing function used
- [ ] Any plaintext password handling

**File: `nicegui_app/main.py`**
Check for:
- [ ] Session secret key (hardcoded vs environment variable?)
- [ ] Debug mode setting
- [ ] Host binding (localhost vs 0.0.0.0)

### Step 2.2: Database Security Audit

**File: `src/database.py`**
Check for:
- [ ] Database connection string location (hardcoded?)
- [ ] Any raw SQL queries (SQL injection risk)
- [ ] Database file path and permissions

**File: `alembic.ini`**
Check for:
- [ ] Database URL in config (should use environment variable)

### Step 2.3: Input Validation Audit

Review PTO request handling:
- [ ] Date range validation (end >= start?)
- [ ] Hours/days validation (positive numbers only?)
- [ ] Status field validation (only valid enum values?)
- [ ] User ID validation (can users submit for others?)

### Step 2.4: Create Security Findings Report

Create file `SECURITY_FINDINGS.md` with this template:
```markdown
# Security Findings Report
Date: [DATE]
Auditor: Claude Code

## Critical Issues (Must Fix Before Production)
1. [Issue description]
   - Location: [file:line]
   - Risk: [description]
   - Remediation: [fix description]

## High Priority Issues
1. ...

## Medium Priority Issues
1. ...

## Low Priority / Recommendations
1. ...
```

### Phase 2 Verification Checkpoint ✓
Before proceeding, confirm:
- [ ] All authentication files reviewed
- [ ] All database files reviewed
- [ ] Input validation reviewed
- [ ] SECURITY_FINDINGS.md created
- [ ] Issues categorized by severity

---

## Phase 3: Security Remediation

**Objective:** Fix identified security issues without breaking functionality.

### Step 3.1: Environment Configuration

Create `config.py` in project root:
```python
# config.py
import os
from pathlib import Path

class Config:
    """Base configuration."""
    BASE_DIR = Path(__file__).parent
    
    # Database
    DATABASE_PATH = os.getenv('TJM_DATABASE_PATH', str(BASE_DIR / 'tjm_calendar.db'))
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    
    # Security
    SECRET_KEY = os.getenv('TJM_SECRET_KEY', 'CHANGE-THIS-IN-PRODUCTION')
    
    # Server
    HOST = os.getenv('TJM_HOST', '127.0.0.1')
    PORT = int(os.getenv('TJM_PORT', '8080'))
    DEBUG = os.getenv('TJM_DEBUG', 'false').lower() == 'true'
    
    # SSL (for HTTPS)
    SSL_CERTFILE = os.getenv('TJM_SSL_CERT', None)
    SSL_KEYFILE = os.getenv('TJM_SSL_KEY', None)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    HOST = '0.0.0.0'  # Allow external connections


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('TJM_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
```

Create `.env.example` file:
```
# TJM Time Calendar Environment Variables
# Copy this to .env and modify values

TJM_ENV=development
TJM_SECRET_KEY=your-secure-random-key-here
TJM_DATABASE_PATH=./tjm_calendar.db
TJM_HOST=127.0.0.1
TJM_PORT=8080
TJM_DEBUG=false

# For HTTPS (optional)
TJM_SSL_CERT=
TJM_SSL_KEY=
```

### Step 3.2: Password Hashing Implementation

If passwords are stored in plaintext, implement hashing:

```python
# src/utils/security.py
import hashlib
import secrets
import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)
```

**Migration Strategy for Existing Users:**
1. Add `password_hash` column alongside existing password field
2. On next login, hash and store password, clear plaintext
3. After all users have logged in, remove plaintext column

### Step 3.3: Session Security

Update session handling in `main.py`:
```python
from config import get_config

config = get_config()

# Use secure secret key
app.storage.secret = config.SECRET_KEY

# Set session expiration (e.g., 8 hours)
# Implementation depends on current session handling
```

### Step 3.4: Input Validation Enhancement

Add validation helpers:
```python
# src/utils/validators.py
from datetime import date
from decimal import Decimal

def validate_date_range(start_date: date, end_date: date) -> tuple[bool, str]:
    """Validate that end_date is not before start_date."""
    if end_date < start_date:
        return False, "End date cannot be before start date"
    return True, ""

def validate_pto_days(days: Decimal) -> tuple[bool, str]:
    """Validate PTO days value."""
    if days <= 0:
        return False, "Days must be greater than zero"
    if days > 365:
        return False, "Days cannot exceed 365"
    return True, ""

def validate_pto_type(pto_type: str) -> tuple[bool, str]:
    """Validate PTO type is allowed."""
    valid_types = ['vacation', 'sick', 'personal', 'bereavement', 'fmla', 'jury_duty', 'voting', 'military']
    if pto_type not in valid_types:
        return False, f"Invalid PTO type. Must be one of: {', '.join(valid_types)}"
    return True, ""
```

### Phase 3 Verification Checkpoint ✓

After each security fix:
1. Run syntax check on modified files
2. Start the application
3. Test the affected functionality
4. Verify no regression in other features

Before proceeding, confirm:
- [ ] config.py created and working
- [ ] Environment variables documented
- [ ] Password hashing implemented (if needed)
- [ ] Session security enhanced
- [ ] Input validation added
- [ ] All existing functionality still works
- [ ] App starts without errors

---

## Phase 4: HTTPS Implementation

**Objective:** Enable secure HTTPS connections.

### Step 4.1: Generate Self-Signed Certificate (For Internal Use)

```bash
cd c:\Users\jlaboy\codelab\projects\TimeCalendar

# Create certs directory
mkdir certs

# Generate self-signed certificate (requires OpenSSL)
# If OpenSSL not available, use Python:
```

Python certificate generation:
```python
# generate_cert.py
from OpenSSL import crypto
from pathlib import Path

def generate_self_signed_cert(cert_dir: str = "certs"):
    """Generate a self-signed certificate for development/internal use."""
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(exist_ok=True)
    
    # Generate key
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    
    # Generate certificate
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "Illinois"
    cert.get_subject().L = "Chicago"
    cert.get_subject().O = "TJM Holdings"
    cert.get_subject().OU = "Haventech"
    cert.get_subject().CN = "tjm-calendar.local"
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    
    # Save certificate
    cert_path = cert_dir / "server.crt"
    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    # Save private key
    key_path = cert_dir / "server.key"
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    
    print(f"Certificate generated: {cert_path}")
    print(f"Private key generated: {key_path}")
    return str(cert_path), str(key_path)

if __name__ == "__main__":
    generate_self_signed_cert()
```

Install required package first:
```bash
venv\Scripts\pip.exe install pyOpenSSL
```

### Step 4.2: Configure NiceGUI for HTTPS

Update `nicegui_app/main.py`:
```python
from config import get_config

config = get_config()

# At the end of the file, modify ui.run():
ui.run(
    host=config.HOST,
    port=config.PORT,
    title="TJM Time Calendar",
    favicon="🗓️",
    ssl_certfile=config.SSL_CERTFILE,
    ssl_keyfile=config.SSL_KEYFILE,
    reload=config.DEBUG
)
```

### Step 4.3: Update Environment for HTTPS

Add to `.env`:
```
TJM_SSL_CERT=./certs/server.crt
TJM_SSL_KEY=./certs/server.key
```

### Step 4.4: Test HTTPS

```bash
# Start with HTTPS
set TJM_SSL_CERT=./certs/server.crt
set TJM_SSL_KEY=./certs/server.key
venv\Scripts\python.exe nicegui_app/main.py
```

Access via: https://localhost:8080

**Note:** Browser will show certificate warning for self-signed cert. This is expected for internal use.

### Phase 4 Verification Checkpoint ✓
- [ ] Certificate generated successfully
- [ ] App starts with HTTPS enabled
- [ ] Can access https://localhost:8080
- [ ] Login works over HTTPS
- [ ] All navigation works over HTTPS
- [ ] No mixed content warnings

---

## Phase 5: Production Hardening

**Objective:** Remove debug features and prepare for production deployment.

### Step 5.1: Disable Debug Mode

Ensure `config.py` ProductionConfig has:
```python
DEBUG = False
```

### Step 5.2: Configure Logging

Create `src/utils/logging_config.py`:
```python
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str = "logs"):
    """Configure application logging."""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create log filename with date
    log_file = log_path / f"tjm_calendar_{datetime.now():%Y%m%d}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    # Reduce noise from libraries
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('nicegui').setLevel(logging.WARNING)
    
    return logging.getLogger('tjm_calendar')
```

Add to `main.py`:
```python
from src.utils.logging_config import setup_logging

logger = setup_logging()
logger.info("TJM Time Calendar starting...")
```

### Step 5.3: Error Handling

Create generic error handler that doesn't expose stack traces:
```python
# In main.py or separate error_handlers.py
from nicegui import ui

def handle_exception(e: Exception):
    """Handle exceptions without exposing details to users."""
    logger.exception("Unhandled exception occurred")
    ui.notify("An error occurred. Please try again or contact support.", type='negative')
```

### Step 5.4: Windows Service Setup (Optional)

For running without a terminal window, create `run_service.py`:
```python
# run_service.py
"""
Run TJM Time Calendar as a background process.
For true Windows Service, consider using NSSM or pywin32.
"""
import subprocess
import sys
from pathlib import Path

def main():
    project_dir = Path(__file__).parent
    python_exe = project_dir / "venv" / "Scripts" / "python.exe"
    main_script = project_dir / "nicegui_app" / "main.py"
    
    # Set production environment
    env = {
        "TJM_ENV": "production",
        "TJM_HOST": "0.0.0.0",
        "TJM_PORT": "8080",
    }
    
    # Run as subprocess
    subprocess.Popen(
        [str(python_exe), str(main_script)],
        env={**dict(os.environ), **env},
        creationflags=subprocess.CREATE_NO_WINDOW
    )

if __name__ == "__main__":
    main()
```

### Phase 5 Verification Checkpoint ✓
- [ ] Debug mode disabled in production config
- [ ] Logging writes to file
- [ ] Error messages don't expose stack traces
- [ ] App runs without console window (if service setup used)
- [ ] All functionality still works

---

## Phase 6: Final Verification

### Complete System Test

Run through all user workflows one final time:

**As Employee:**
- [ ] Login
- [ ] View dashboard
- [ ] Check balances
- [ ] Submit PTO request
- [ ] View request status
- [ ] Logout

**As Manager:**
- [ ] Login
- [ ] View team requests
- [ ] Approve request
- [ ] Deny request with reason
- [ ] Submit own request (auto-approve)
- [ ] Logout

**As Admin:**
- [ ] Login
- [ ] Access admin panel
- [ ] Manage users
- [ ] View all requests
- [ ] Logout

**Security Verification:**
- [ ] HTTPS working
- [ ] Session expires appropriately
- [ ] Cannot access admin pages as employee
- [ ] Cannot submit requests for other users

### Performance Check
- [ ] App loads within 3 seconds
- [ ] No memory leaks after extended use
- [ ] Database queries complete quickly

### Documentation Update
- [ ] CLAUDE.md updated with production info
- [ ] .env.example includes all variables
- [ ] README has deployment instructions

---

## Rollback Procedure

If anything goes wrong, restore from backup:
```bash
cd c:\Users\jlaboy\codelab\projects

# Remove broken version
rmdir /S /Q TimeCalendar

# Restore backup
xcopy /E /I TimeCalendar_backup_[DATE] TimeCalendar
```

---

## Post-Deployment Checklist

After successful deployment:
- [ ] Backup database regularly
- [ ] Monitor log files for errors
- [ ] Renew SSL certificate before expiration
- [ ] Review security settings quarterly
- [ ] Test backup restoration procedure

---

## Summary of New Files Created

| File | Purpose |
|------|---------|
| `config.py` | Environment-based configuration |
| `.env.example` | Environment variable template |
| `src/utils/security.py` | Password hashing utilities |
| `src/utils/validators.py` | Input validation helpers |
| `src/utils/logging_config.py` | Logging configuration |
| `certs/server.crt` | SSL certificate |
| `certs/server.key` | SSL private key |
| `SECURITY_FINDINGS.md` | Security audit results |

---

## Contact

Questions about this document should be directed to the CTO (Jose Laboy).
