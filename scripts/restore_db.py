#!/usr/bin/env python3
"""
Database restore script for PTO Central.

Restores the SQLite database from a backup file.

Usage:
    python scripts/restore_db.py <backup_file>
    python scripts/restore_db.py --list
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

    db_url = os.getenv('DATABASE_URL', 'sqlite:///pto_central.db')

    if not db_url.startswith('sqlite:///'):
        print("Error: Restore script only supports SQLite databases")
        sys.exit(1)

    # Extract path from sqlite:///path
    db_file = db_url.replace('sqlite:///', '')

    # Handle relative paths
    if not os.path.isabs(db_file):
        db_file = PROJECT_ROOT / db_file

    return Path(db_file)


def list_backups(backup_dir: Path):
    """List all available backups."""
    backups = sorted(
        backup_dir.glob("pto_central_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("No backups found.")
        return

    print(f"\nAvailable backups in {backup_dir}:")
    print("-" * 60)
    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"{i}. {backup.name}")
        print(f"   Size: {size_mb:.2f} MB | Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)


def restore_backup(backup_path: Path, db_path: Path, create_safety_backup: bool = True):
    """Restore database from a backup file."""
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}")
        sys.exit(1)

    # Create safety backup of current database before restore
    if create_safety_backup and db_path.exists():
        safety_dir = PROJECT_ROOT / 'dbbackup' / 'pre_restore'
        safety_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_path = safety_dir / f"pre_restore_{timestamp}.db"
        shutil.copy2(db_path, safety_path)
        print(f"Safety backup created: {safety_path}")

    # Restore the backup
    shutil.copy2(backup_path, db_path)
    print(f"Database restored from: {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Restore PTO Central database")
    parser.add_argument(
        'backup_file',
        type=str,
        nargs='?',
        help="Path to backup file to restore"
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help="List available backups"
    )
    parser.add_argument(
        '--backup-dir', '-d',
        type=str,
        default=None,
        help="Backup directory (default: PROJECT_ROOT/dbbackup)"
    )
    parser.add_argument(
        '--no-safety-backup',
        action='store_true',
        help="Skip creating safety backup before restore"
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    backup_dir = Path(args.backup_dir) if args.backup_dir else PROJECT_ROOT / 'dbbackup'

    if args.list:
        list_backups(backup_dir)
        return

    if not args.backup_file:
        parser.print_help()
        print("\nUse --list to see available backups")
        sys.exit(1)

    backup_path = Path(args.backup_file)
    if not backup_path.is_absolute():
        # Check if it's just a filename in backup_dir
        if (backup_dir / args.backup_file).exists():
            backup_path = backup_dir / args.backup_file
        else:
            backup_path = Path(args.backup_file).resolve()

    db_path = get_db_path()

    print(f"Backup file: {backup_path}")
    print(f"Target database: {db_path}")
    print("-" * 40)

    if not args.yes:
        confirm = input("This will overwrite the current database. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Restore cancelled.")
            sys.exit(0)

    restore_backup(backup_path, db_path, not args.no_safety_backup)

    print("-" * 40)
    print("Restore complete!")


if __name__ == '__main__':
    main()
