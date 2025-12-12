@echo off
REM ============================================
REM TJM Time Calendar - Scheduled Backup Script
REM ============================================
REM Run this via Windows Task Scheduler for automated daily backups
REM
REM Setup Instructions:
REM 1. Open Task Scheduler (taskschd.msc)
REM 2. Create Basic Task > Name: "TJM Calendar Daily Backup"
REM 3. Trigger: Daily at 2:00 AM (or preferred time)
REM 4. Action: Start a Program
REM 5. Program: C:\Users\jlaboy\codelab\projects\TimeCalendar\scripts\scheduled_backup.bat
REM 6. Start in: C:\Users\jlaboy\codelab\projects\TimeCalendar
REM ============================================

cd /d C:\Users\jlaboy\codelab\projects\TimeCalendar

REM Activate virtual environment and run backup
call venv\Scripts\activate.bat
python scripts\backup_db.py --keep 14

REM Sync to off-site location if configured
python -c "from src.services.backup_service import backup_service; result = backup_service.sync_to_offsite(); print(f'Off-site sync: {result}')" 2>> logs\backup_log.txt

REM Log completion
echo [%date% %time%] Backup completed >> logs\backup_log.txt

REM Deactivate
deactivate
