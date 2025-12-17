# TJM Time Calendar - Backup Setup Guide

## Overview

This guide explains how to set up automated database backups for the TJM Time Calendar application.

## Backup Script

The backup script is located at `scripts/backup.ps1`. It:

- Creates timestamped copies of `tjm_calendar.db`
- Stores backups in a configurable directory
- Automatically removes backups older than the retention period
- Logs all operations to `backup.log`

## Manual Backup

Run a manual backup from PowerShell:

```powershell
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
.\scripts\backup.ps1
```

With custom options:

```powershell
.\scripts\backup.ps1 -BackupDir "D:\Backups\TJMCalendar" -RetentionDays 14
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-BackupDir` | `C:\Backups\TJMCalendar` | Directory to store backups |
| `-RetentionDays` | `7` | Days to keep old backups |

## Automated Scheduling (Windows Task Scheduler)

### Option 1: Using Task Scheduler GUI

1. Open Task Scheduler (`taskschd.msc`)
2. Click "Create Basic Task"
3. Name: "TJM Calendar Daily Backup"
4. Trigger: Daily at 2:00 AM (or preferred time)
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "c:\Users\jlaboy\codelab\projects\TimeCalendar\scripts\backup.ps1"`
6. Finish and test with "Run"

### Option 2: Using PowerShell

Run as Administrator:

```powershell
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-ExecutionPolicy Bypass -File "c:\Users\jlaboy\codelab\projects\TimeCalendar\scripts\backup.ps1"'

$Trigger = New-ScheduledTaskTrigger -Daily -At "2:00AM"

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "TJM Calendar Daily Backup" `
    -Action $Action -Trigger $Trigger -Principal $Principal `
    -Description "Daily backup of TJM Time Calendar database"
```

To remove the scheduled task:

```powershell
Unregister-ScheduledTask -TaskName "TJM Calendar Daily Backup" -Confirm:$false
```

## Backup Verification

Check the backup log:

```powershell
Get-Content "C:\Backups\TJMCalendar\backup.log" -Tail 20
```

List existing backups:

```powershell
Get-ChildItem "C:\Backups\TJMCalendar" -Filter "tjm_calendar_*.db" |
    Sort-Object LastWriteTime -Descending |
    Format-Table Name, Length, LastWriteTime
```

## Restore from Backup

To restore from a backup:

1. Stop the application
2. Copy the backup file over the original:

```powershell
# Stop the app first, then:
Copy-Item "C:\Backups\TJMCalendar\tjm_calendar_20250115_020000.db" `
          "c:\Users\jlaboy\codelab\projects\TimeCalendar\tjm_calendar.db" -Force
```

3. Restart the application

## Backup Storage Recommendations

- **Local**: Fast, but vulnerable to disk failure
- **Network share**: Better for team environments
- **Cloud sync**: Use OneDrive/Dropbox for automatic off-site backup

Example with network share:

```powershell
.\scripts\backup.ps1 -BackupDir "\\fileserver\backups\TJMCalendar"
```

## Monitoring

The script returns exit codes:
- `0`: Backup successful
- `1`: Backup failed

Use these in monitoring systems or check `backup.log` for details.
