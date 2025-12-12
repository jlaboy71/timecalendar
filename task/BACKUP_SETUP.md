# TJM Time Calendar - Automated Backup Setup

## Quick Start

### Manual Backup (Test First)
```cmd
cd C:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe scripts\backup_db.py
```

### Verify Backup Created
```cmd
dir dbbackup\*.db
```

---

## Windows Task Scheduler Setup

### Step 1: Open Task Scheduler
- Press `Win + R`, type `taskschd.msc`, press Enter

### Step 2: Create Basic Task
1. Click **Create Basic Task...** in the right panel
2. Name: `TJM Calendar Daily Backup`
3. Description: `Automated daily backup of TJM Time Calendar database`
4. Click **Next**

### Step 3: Set Trigger
1. Select **Daily**
2. Click **Next**
3. Set time to `2:00:00 AM` (or preferred off-hours time)
4. Recur every: `1` days
5. Click **Next**

### Step 4: Set Action
1. Select **Start a program**
2. Click **Next**
3. Program/script: `C:\Users\jlaboy\codelab\projects\TimeCalendar\scripts\scheduled_backup.bat`
4. Start in: `C:\Users\jlaboy\codelab\projects\TimeCalendar`
5. Click **Next**

### Step 5: Finish
1. Check **Open the Properties dialog** before finishing
2. Click **Finish**

### Step 6: Configure Properties
1. In the General tab, check **Run whether user is logged on or not**
2. Check **Run with highest privileges**
3. Click **OK**
4. Enter your Windows password when prompted

---

## Verify Scheduled Task

### Test Run
1. In Task Scheduler, find `TJM Calendar Daily Backup`
2. Right-click > **Run**
3. Check `dbbackup\` folder for new backup file
4. Check `logs\backup_log.txt` for completion entry

### Check Task History
1. Select the task
2. Click **History** tab at bottom
3. Verify "Task completed" entries

---

## Backup Retention

- **Default retention:** 14 days (configurable in `scheduled_backup.bat`)
- **Location:** `C:\Users\jlaboy\codelab\projects\TimeCalendar\dbbackup\`
- **Naming:** `tjm_calendar_backup_YYYYMMDD_HHMMSS.db`

---

## Restore from Backup

```cmd
cd C:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe scripts\restore_db.py dbbackup\tjm_calendar_backup_20251212_020000.db
```

Or use the BackupService in Python:
```python
from src.services.backup_service import backup_service
backups = backup_service.list_backups()
backup_service.restore_backup(backups[0]['filename'])
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Task doesn't run | Check "Run whether user is logged on or not" is enabled |
| Permission denied | Run Task Scheduler as Administrator |
| Backup not created | Check `logs\backup_log.txt` for errors |
| Path not found | Verify paths in `scheduled_backup.bat` match your install |
