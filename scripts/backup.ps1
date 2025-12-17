# TJM Time Calendar Database Backup Script
# Purpose: Creates timestamped backups of the SQLite database
# Usage: .\backup.ps1 [-BackupDir "path"] [-RetentionDays 7]

param(
    [string]$BackupDir = "C:\Backups\TJMCalendar",
    [int]$RetentionDays = 7
)

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DatabasePath = Join-Path $ProjectRoot "tjm_calendar.db"
$LogFile = Join-Path $BackupDir "backup.log"

# Ensure backup directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    Write-Host $LogMessage
}

function Backup-Database {
    try {
        # Verify source database exists
        if (-not (Test-Path $DatabasePath)) {
            Write-Log "ERROR: Database not found at $DatabasePath"
            return $false
        }

        # Create timestamped backup filename
        $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $BackupFileName = "tjm_calendar_$Timestamp.db"
        $BackupPath = Join-Path $BackupDir $BackupFileName

        # Copy database file
        Copy-Item -Path $DatabasePath -Destination $BackupPath -Force

        # Verify backup was created
        if (Test-Path $BackupPath) {
            $BackupSize = (Get-Item $BackupPath).Length
            $SourceSize = (Get-Item $DatabasePath).Length

            if ($BackupSize -eq $SourceSize) {
                Write-Log "SUCCESS: Backup created at $BackupPath ($BackupSize bytes)"
                return $true
            } else {
                Write-Log "WARNING: Backup size ($BackupSize) differs from source ($SourceSize)"
                return $true  # Still consider it a success, but log the warning
            }
        } else {
            Write-Log "ERROR: Backup file was not created"
            return $false
        }
    }
    catch {
        Write-Log "ERROR: Backup failed - $_"
        return $false
    }
}

function Remove-OldBackups {
    try {
        $CutoffDate = (Get-Date).AddDays(-$RetentionDays)
        $OldBackups = Get-ChildItem -Path $BackupDir -Filter "tjm_calendar_*.db" |
                      Where-Object { $_.LastWriteTime -lt $CutoffDate }

        foreach ($Backup in $OldBackups) {
            Remove-Item -Path $Backup.FullName -Force
            Write-Log "CLEANUP: Removed old backup $($Backup.Name)"
        }

        $RemainingCount = (Get-ChildItem -Path $BackupDir -Filter "tjm_calendar_*.db").Count
        Write-Log "INFO: $RemainingCount backup(s) remaining after cleanup"
    }
    catch {
        Write-Log "WARNING: Cleanup failed - $_"
    }
}

# Main execution
Write-Log "=========================================="
Write-Log "Starting TJM Calendar database backup"
Write-Log "Source: $DatabasePath"
Write-Log "Destination: $BackupDir"
Write-Log "Retention: $RetentionDays days"

$BackupSuccess = Backup-Database

if ($BackupSuccess) {
    Remove-OldBackups
    Write-Log "Backup process completed successfully"
    exit 0
} else {
    Write-Log "Backup process failed"
    exit 1
}
