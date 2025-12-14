#!/usr/bin/env python3
"""
Database backup script for TJM Time Calendar.

Creates timestamped backups of the SQLite database.
Retains the last N backups and deletes older ones.

Usage:
    python scripts/backup_db.py
    python scripts/backup_db.py --keep 10
"""
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_db_path() -> Path:
    """Get the database path from environment or default."""
    from dotenv import load_dotenv
    load_dotenv()

    db_url = os.getenv('DATABASE_URL', 'sqlite:///tjm_calendar.db')

    if not db_url.startswith('sqlite:///'):
        print("Error: Backup script only supports SQLite databases")
        sys.exit(1)

    # Extract path from sqlite:///path
    db_file = db_url.replace('sqlite:///', '')

    # Handle relative paths
    if not os.path.isabs(db_file):
        db_file = PROJECT_ROOT / db_file

    return Path(db_file)


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    """Create a timestamped backup of the database."""
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    # Create backup directory if needed
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"tjm_calendar_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name

    # Copy the database
    shutil.copy2(db_path, backup_path)

    print(f"Backup created: {backup_path}")
    return backup_path


def cleanup_old_backups(backup_dir: Path, keep: int):
    """Delete old backups, keeping only the most recent N."""
    backups = sorted(
        backup_dir.glob("tjm_calendar_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if len(backups) <= keep:
        return

    for old_backup in backups[keep:]:
        old_backup.unlink()
        print(f"Deleted old backup: {old_backup.name}")


def main():
    parser = argparse.ArgumentParser(description="Backup TJM Time Calendar database")
    parser.add_argument(
        '--keep', '-k',
        type=int,
        default=7,
        help="Number of backups to keep (default: 7)"
    )
    parser.add_argument(
        '--backup-dir', '-d',
        type=str,
        default=None,
        help="Backup directory (default: PROJECT_ROOT/dbbackup)"
    )

    args = parser.parse_args()

    db_path = get_db_path()
    backup_dir = Path(args.backup_dir) if args.backup_dir else PROJECT_ROOT / 'dbbackup'

    print(f"Database: {db_path}")
    print(f"Backup directory: {backup_dir}")
    print(f"Keeping last {args.keep} backups")
    print("-" * 40)

    create_backup(db_path, backup_dir)
    cleanup_old_backups(backup_dir, args.keep)

    print("-" * 40)
    print("Backup complete!")


if __name__ == '__main__':
    main()
