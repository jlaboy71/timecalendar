# TJM Time Calendar - Deployment Guide

## Prerequisites

- Python 3.10+
- Git

## Quick Start (Development)

```bash
# Clone repository
git clone https://github.com/jlaboy71/timecalendar.git
cd timecalendar

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env with your settings
# Required: DATABASE_URL, SECRET_KEY

# Initialize database
python -c "from src.database import init_db; init_db()"

# Run application
python nicegui_app/main.py
```

## Production Setup

### 1. Environment Configuration

Create `.env` with production settings:

```env
# Database
DATABASE_URL=sqlite:///tjm_calendar.db

# Security - Generate a strong random key!
SECRET_KEY=your-very-long-random-secret-key-here

# Environment
ENVIRONMENT=production
DEBUG=False

# Email (optional)
EMAIL_ENABLED=true
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourcompany.com

# Anthropic API (for AI handbook assistant)
ANTHROPIC_API_KEY=your-key-here
```

### 2. Generate Secure Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

### 3. Database Backups

Run daily backups via cron or Task Scheduler:

```bash
# Linux cron (daily at 2 AM)
0 2 * * * /path/to/venv/bin/python /path/to/scripts/backup_db.py --keep 30

# Windows Task Scheduler
python scripts\backup_db.py --keep 30
```

### 4. Running with Systemd (Linux)

Create `/etc/systemd/system/tjm-calendar.service`:

```ini
[Unit]
Description=TJM Time Calendar
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/tjm-calendar
Environment="PATH=/opt/tjm-calendar/venv/bin"
ExecStart=/opt/tjm-calendar/venv/bin/python nicegui_app/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable tjm-calendar
sudo systemctl start tjm-calendar
```

### 5. Reverse Proxy with Nginx (HTTPS)

```nginx
server {
    listen 80;
    server_name calendar.yourcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name calendar.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/calendar.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d calendar.yourcompany.com
```

## Security Checklist

- [ ] Strong SECRET_KEY (64+ characters)
- [ ] DEBUG=False in production
- [ ] ENVIRONMENT=production
- [ ] HTTPS enabled via reverse proxy
- [ ] Database file permissions restricted
- [ ] Regular database backups configured
- [ ] Firewall configured (only 80/443 open)

## Monitoring

### Application Logs

NiceGUI logs to stdout. With systemd:

```bash
journalctl -u tjm-calendar -f
```

### Database Health

```bash
# Check database size
ls -lh tjm_calendar.db

# Verify integrity
sqlite3 tjm_calendar.db "PRAGMA integrity_check;"
```

## Updating

```bash
# Stop service
sudo systemctl stop tjm-calendar

# Pull updates
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run database migrations if needed
alembic upgrade head

# Restart service
sudo systemctl start tjm-calendar
```

## Troubleshooting

### Application won't start
- Check `.env` file exists and has required variables
- Verify database file exists and is readable
- Check port 8080 is not in use

### Session issues
- Delete `.nicegui/` folder and restart
- Verify SECRET_KEY hasn't changed

### Email not sending
- Verify EMAIL_ENABLED=true
- Check SMTP credentials
- Test with Gmail app password (not regular password)
