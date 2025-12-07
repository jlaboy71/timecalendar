"""
Backup and restore service for TJM Time Calendar.

Provides programmatic access to database backup and restore operations.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class BackupService:
    """Service for database backup and restore operations."""

    def __init__(self, backup_dir: Optional[Path] = None, keep_backups: int = 7):
        """
        Initialize the backup service.

        Args:
            backup_dir: Directory to store backups (default: PROJECT_ROOT/dbbackup)
            keep_backups: Number of backups to retain
        """
        self.backup_dir = backup_dir or (PROJECT_ROOT / 'dbbackup')
        self.keep_backups = keep_backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_db_path(self) -> Path:
        """Get the database path from environment or default."""
        from dotenv import load_dotenv
        load_dotenv()

        db_url = os.getenv('DATABASE_URL', 'sqlite:///tjm_calendar.db')

        if not db_url.startswith('sqlite:///'):
            raise ValueError("Backup service only supports SQLite databases")

        db_file = db_url.replace('sqlite:///', '')

        if not os.path.isabs(db_file):
            db_file = PROJECT_ROOT / db_file

        return Path(db_file)

    def create_backup(self, description: str = "") -> Dict:
        """
        Create a timestamped backup of the database.

        Args:
            description: Optional description for the backup

        Returns:
            Dict with backup details
        """
        db_path = self.get_db_path()

        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"tjm_calendar_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        # Copy the database
        shutil.copy2(db_path, backup_path)

        # Create metadata file if description provided
        if description:
            meta_path = backup_path.with_suffix('.meta')
            meta_path.write_text(description)

        logger.info(f"Backup created: {backup_path}")

        # Cleanup old backups
        self._cleanup_old_backups()

        return {
            'success': True,
            'filename': backup_name,
            'path': str(backup_path),
            'size_bytes': backup_path.stat().st_size,
            'timestamp': timestamp,
            'description': description
        }

    def list_backups(self) -> List[Dict]:
        """
        List all available backups.

        Returns:
            List of backup info dictionaries
        """
        backups = sorted(
            self.backup_dir.glob("tjm_calendar_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        result = []
        for backup in backups:
            stat = backup.stat()

            # Try to read description from metadata file
            description = ""
            meta_path = backup.with_suffix('.meta')
            if meta_path.exists():
                description = meta_path.read_text().strip()

            result.append({
                'filename': backup.name,
                'path': str(backup),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created_at': datetime.fromtimestamp(stat.st_mtime),
                'description': description
            })

        return result

    def restore_backup(self, backup_filename: str, create_safety_backup: bool = True) -> Dict:
        """
        Restore database from a backup file.

        Args:
            backup_filename: Name of backup file to restore
            create_safety_backup: Whether to create safety backup before restore

        Returns:
            Dict with restore details
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        db_path = self.get_db_path()

        # Create safety backup before restore
        safety_path = None
        if create_safety_backup and db_path.exists():
            safety_dir = self.backup_dir / 'pre_restore'
            safety_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safety_path = safety_dir / f"pre_restore_{timestamp}.db"
            shutil.copy2(db_path, safety_path)
            logger.info(f"Safety backup created: {safety_path}")

        # Restore the backup
        shutil.copy2(backup_path, db_path)
        logger.info(f"Database restored from: {backup_path}")

        return {
            'success': True,
            'restored_from': backup_filename,
            'safety_backup': str(safety_path) if safety_path else None
        }

    def delete_backup(self, backup_filename: str) -> Dict:
        """
        Delete a specific backup file.

        Args:
            backup_filename: Name of backup file to delete

        Returns:
            Dict with deletion result
        """
        backup_path = self.backup_dir / backup_filename

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        backup_path.unlink()

        # Also delete metadata file if exists
        meta_path = backup_path.with_suffix('.meta')
        if meta_path.exists():
            meta_path.unlink()

        logger.info(f"Backup deleted: {backup_filename}")

        return {
            'success': True,
            'deleted': backup_filename
        }

    def get_backup_stats(self) -> Dict:
        """
        Get backup statistics.

        Returns:
            Dict with backup stats
        """
        backups = self.list_backups()

        total_size = sum(b['size_bytes'] for b in backups)

        return {
            'backup_count': len(backups),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'backup_dir': str(self.backup_dir),
            'oldest_backup': backups[-1]['created_at'] if backups else None,
            'newest_backup': backups[0]['created_at'] if backups else None
        }

    def _cleanup_old_backups(self):
        """Delete old backups, keeping only the most recent N."""
        backups = sorted(
            self.backup_dir.glob("tjm_calendar_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if len(backups) <= self.keep_backups:
            return

        for old_backup in backups[self.keep_backups:]:
            old_backup.unlink()
            # Also delete metadata file
            meta_path = old_backup.with_suffix('.meta')
            if meta_path.exists():
                meta_path.unlink()
            logger.info(f"Deleted old backup: {old_backup.name}")


# Singleton instance
backup_service = BackupService()
