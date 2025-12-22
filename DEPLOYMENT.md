# PTO Central - Deployment Guide

## Server Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10+ | Windows 11 |
| Python | 3.10 | 3.11+ |
| RAM | 2 GB | 4 GB |
| Storage | 1 GB | 5 GB (with backups) |
| Network | Intranet access | Static IP |

## Quick Start (Development)

```powershell
# Clone repository
git clone https://github.com/your-org/timecalendar.git
cd TimeCalendar

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
copy .env.example .env

# Edit .env with your settings (Required: DATABASE_URL, SECRET_KEY)
notepad .env

# Run application
python nicegui_app/main.py
```

## Production Setup

### 1. Environment Configuration

Create `.env` in the project root with production settings:

```env
# Database
DATABASE_URL=sqlite:///pto_central.db

# Security - Generate a strong random key!
SECRET_KEY=your-very-long-random-secret-key-here

# Environment
ENVIRONMENT=production
DEBUG=False

# Server
PTO_HOST=0.0.0.0
PTO_PORT=8080

# SSL (Optional - for HTTPS)
PTO_SSL_CERT=certs/server.crt
PTO_SSL_KEY=certs/server.key

# Email (Optional)
EMAIL_ENABLED=true
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourcompany.com
EMAIL_FROM_NAME=PTO Central

# Notification Scheduler
ENABLE_DIGEST_SCHEDULER=true
```

### 2. Generate Secure Secret Key

```python
# Run in Python console:
import secrets
print(secrets.token_hex(32))
```

Or use PowerShell:
```powershell
[guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
```

### 3. SSL Certificate Installation

#### Self-Signed Certificate (Intranet)

```powershell
# Create certs directory
mkdir certs

# Generate self-signed certificate (requires OpenSSL)
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes -subj "/CN=localhost"
```

#### Using Existing Certificate

1. Place your `.crt` and `.key` files in the `certs/` directory
2. Update `.env`:
   ```env
   PTO_SSL_CERT=certs/your-certificate.crt
   PTO_SSL_KEY=certs/your-certificate.key
   ```

### 4. Windows Service Installation

#### Option A: Using NSSM (Recommended)

1. Download NSSM from https://nssm.cc/download
2. Extract to a permanent location (e.g., `C:\Tools\nssm`)
3. Install service:

```powershell
# Run as Administrator
C:\Tools\nssm\win64\nssm.exe install PTOCentral

# In the GUI that opens:
# Path: C:\path\to\TimeCalendar\venv\Scripts\python.exe
# Startup directory: C:\path\to\TimeCalendar
# Arguments: nicegui_app\main.py
# Service name: PTOCentral
```

4. Configure service:
```powershell
nssm set PTOCentral DisplayName "PTO Central"
nssm set PTOCentral Description "Employee PTO Management System"
nssm set PTOCentral Start SERVICE_AUTO_START

# Start the service
nssm start PTOCentral
```

#### Option B: Task Scheduler

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task:
   - Name: `PTO Central`
   - Trigger: At startup
   - Action: Start a program
   - Program: `C:\path\to\TimeCalendar\venv\Scripts\python.exe`
   - Arguments: `nicegui_app\main.py`
   - Start in: `C:\path\to\TimeCalendar`
3. Edit task properties:
   - Run whether user is logged on or not
   - Run with highest privileges

### 5. Firewall Configuration

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="PTO Central HTTP" dir=in action=allow protocol=tcp localport=8080

# For HTTPS
netsh advfirewall firewall add rule name="PTO Central HTTPS" dir=in action=allow protocol=tcp localport=443
```

Or use Windows Defender Firewall GUI:
1. Open "Windows Defender Firewall with Advanced Security"
2. Inbound Rules → New Rule
3. Port → TCP → 8080 → Allow connection
4. Apply to Domain/Private/Public as needed

### 6. Database Backup Procedures

#### Manual Backup

```powershell
# Create backup directory
mkdir C:\Backups\PTOCentral

# Copy database with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
Copy-Item "pto_central.db" "C:\Backups\PTOCentral\pto_central_$timestamp.db"
```

#### Automated Daily Backup

Create `scripts\backup.ps1`:
```powershell
$backupDir = "C:\Backups\PTOCentral"
$sourceDb = "C:\path\to\TimeCalendar\pto_central.db"
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$backupFile = "$backupDir\pto_central_$timestamp.db"

# Create backup
Copy-Item $sourceDb $backupFile

# Keep only last 7 days
Get-ChildItem $backupDir -Filter "*.db" |
    Sort-Object CreationTime -Descending |
    Select-Object -Skip 7 |
    Remove-Item -Force

# Log
Add-Content "$backupDir\backup.log" "$(Get-Date): Backup created - $backupFile"
```

Schedule with Task Scheduler:
- Trigger: Daily at 2:00 AM
- Action: `powershell.exe -ExecutionPolicy Bypass -File C:\path\to\scripts\backup.ps1`

### 7. Monitoring Setup

#### Health Check

The application exposes `/health` endpoint:
```
https://localhost:8080/health
```

Returns JSON with:
- `status`: "healthy" or "unhealthy"
- `database`: "connected" or error message
- `timestamp`: Current server time

#### Log Monitoring

Application logs to stdout. When running as a service with NSSM:
```powershell
# View live logs
nssm status PTOCentral

# Check Windows Event Viewer for service issues
eventvwr.msc
```

## Troubleshooting

### Application Won't Start

1. **Check .env file exists and has required variables**
   ```powershell
   type .env
   ```

2. **Verify database file exists**
   ```powershell
   dir pto_central.db
   ```

3. **Check port availability**
   ```powershell
   netstat -an | findstr :8080
   ```

4. **Run manually to see errors**
   ```powershell
   venv\Scripts\python.exe nicegui_app/main.py
   ```

### SSL Certificate Issues

1. **Certificate not trusted**
   - For self-signed: Add to Windows trusted root certificates
   - For browser warning: Add exception or use proper CA-signed cert

2. **Permission denied**
   - Ensure certificate files are readable by the service account

### Session Issues

1. **Delete session storage and restart**
   ```powershell
   Remove-Item -Recurse -Force .nicegui\
   ```

2. **Verify SECRET_KEY hasn't changed between deployments**

### Email Not Sending

1. **Verify EMAIL_ENABLED=true in .env**
2. **Check SMTP credentials**
3. **For Gmail**: Use App Password, not regular password
4. **Test manually**:
   ```python
   from src.services.email_service import email_service
   email_service.send_test_email("test@example.com")
   ```

### Database Errors

1. **Check integrity**
   ```powershell
   sqlite3 pto_central.db "PRAGMA integrity_check;"
   ```

2. **Run migrations**
   ```powershell
   venv\Scripts\python.exe -m alembic upgrade head
   ```

## Updating the Application

```powershell
# Stop service
nssm stop PTOCentral

# Backup database
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
Copy-Item pto_central.db "pto_central_backup_$timestamp.db"

# Pull updates
git pull origin main

# Install any new dependencies
venv\Scripts\pip.exe install -r requirements.txt

# Run database migrations
venv\Scripts\python.exe -m alembic upgrade head

# Restart service
nssm start PTOCentral
```

## Security Checklist

- [ ] Strong SECRET_KEY (64+ characters, randomly generated)
- [ ] DEBUG=False in production .env
- [ ] ENVIRONMENT=production in .env
- [ ] HTTPS enabled (SSL certificates configured)
- [ ] Database file permissions restricted
- [ ] Regular database backups scheduled
- [ ] Firewall configured (only required ports open)
- [ ] Service runs under limited user account
- [ ] Audit logs enabled and monitored

---

**Last Updated**: December 2025
**Version**: 1.0.0
