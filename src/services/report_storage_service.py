"""
Service for storing and retrieving auto-notify reports.
Reports are stored as HTML files in admin_reports/{DepartmentName}/{YYYY-MM}/
"""
import os
import shutil
import logging
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Base directory for reports (at project root)
REPORTS_BASE_DIR = Path(__file__).parent.parent.parent / 'admin_reports'


class ReportStorageService:
    """Service for managing auto-notify report storage."""

    @staticmethod
    def _get_department_path(department_name: str) -> Path:
        """Get the path for a department's reports directory."""
        # Sanitize department name for filesystem
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in department_name)
        safe_name = safe_name.strip().replace(' ', '_')
        return REPORTS_BASE_DIR / safe_name

    @staticmethod
    def _get_month_path(department_name: str, year: int, month: int) -> Path:
        """Get the path for a specific month's reports."""
        dept_path = ReportStorageService._get_department_path(department_name)
        return dept_path / f"{year}-{month:02d}"

    @staticmethod
    def save_report(
        department_name: str,
        frequency: str,
        report_date: date,
        html_content: str
    ) -> bool:
        """
        Save a report to the filesystem.

        Args:
            department_name: Name of the department
            frequency: Report frequency (weekly, bi-weekly, monthly)
            report_date: Date of the report
            html_content: HTML content of the report

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            month_path = ReportStorageService._get_month_path(
                department_name, report_date.year, report_date.month
            )
            month_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            if frequency == 'monthly':
                filename = f"{frequency}_{report_date.year}-{report_date.month:02d}.html"
            else:
                filename = f"{frequency}_{report_date.strftime('%Y-%m-%d')}.html"

            file_path = month_path / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Report saved: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")
            return False

    @staticmethod
    def list_reports(
        department_name: str,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict]:
        """
        List available reports for a department.

        Args:
            department_name: Name of the department
            year: Optional year filter
            month: Optional month filter (requires year)

        Returns:
            List of report metadata dictionaries
        """
        reports = []
        dept_path = ReportStorageService._get_department_path(department_name)

        if not dept_path.exists():
            return reports

        try:
            # Get all month directories
            for month_dir in sorted(dept_path.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                # Parse year-month from directory name
                try:
                    dir_parts = month_dir.name.split('-')
                    dir_year = int(dir_parts[0])
                    dir_month = int(dir_parts[1])
                except (ValueError, IndexError):
                    continue

                # Apply year filter
                if year and dir_year != year:
                    continue

                # Apply month filter
                if month and dir_month != month:
                    continue

                # List HTML files in this month directory
                for file in sorted(month_dir.glob('*.html'), reverse=True):
                    # Parse filename: {frequency}_{date}.html
                    name_parts = file.stem.split('_', 1)
                    if len(name_parts) != 2:
                        continue

                    frequency = name_parts[0]
                    date_str = name_parts[1]

                    # Parse date from filename
                    try:
                        if frequency == 'monthly':
                            # Format: monthly_2025-12.html
                            report_date = datetime.strptime(date_str, '%Y-%m').date()
                        else:
                            # Format: weekly_2025-12-01.html
                            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        continue

                    # Format display date with day name
                    if frequency == 'monthly':
                        display_date = report_date.strftime('%B %Y')
                    else:
                        display_date = report_date.strftime('%a %b %d, %Y')  # e.g., "Sun Dec 14, 2025"

                    reports.append({
                        'department': department_name,
                        'filename': file.name,
                        'frequency': frequency,
                        'date': report_date,
                        'year': dir_year,
                        'month': dir_month,
                        'day': report_date.day,
                        'path': str(file),
                        'display_date': display_date
                    })

        except Exception as e:
            logger.error(f"Failed to list reports: {str(e)}")

        return reports

    @staticmethod
    def get_report(department_name: str, year: int, month: int, filename: str) -> Optional[str]:
        """
        Get the content of a specific report.

        Args:
            department_name: Name of the department
            year: Year of the report
            month: Month of the report
            filename: Name of the report file

        Returns:
            HTML content of the report or None if not found
        """
        try:
            month_path = ReportStorageService._get_month_path(department_name, year, month)
            file_path = month_path / filename

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Failed to read report: {str(e)}")
            return None

    @staticmethod
    def delete_report(department_name: str, year: int, month: int, filename: str) -> bool:
        """
        Delete a specific report.

        Args:
            department_name: Name of the department
            year: Year of the report
            month: Month of the report
            filename: Name of the report file

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            month_path = ReportStorageService._get_month_path(department_name, year, month)
            file_path = month_path / filename

            if not file_path.exists():
                return False

            file_path.unlink()
            logger.info(f"Report deleted: {file_path}")

            # Clean up empty directories
            if not any(month_path.iterdir()):
                month_path.rmdir()
                dept_path = ReportStorageService._get_department_path(department_name)
                if not any(dept_path.iterdir()):
                    dept_path.rmdir()

            return True

        except Exception as e:
            logger.error(f"Failed to delete report: {str(e)}")
            return False

    @staticmethod
    def get_departments_with_reports() -> List[str]:
        """
        Get list of departments that have reports stored.

        Returns:
            List of department names
        """
        departments = []

        if not REPORTS_BASE_DIR.exists():
            return departments

        try:
            for dept_dir in sorted(REPORTS_BASE_DIR.iterdir()):
                if dept_dir.is_dir():
                    # Convert filesystem name back to display name
                    display_name = dept_dir.name.replace('_', ' ')
                    departments.append(display_name)

        except Exception as e:
            logger.error(f"Failed to list departments: {str(e)}")

        return departments

    @staticmethod
    def purge_year_reports(year: int) -> int:
        """
        Delete all reports for a specific year (used in year-end processing).

        Args:
            year: Year to purge

        Returns:
            Number of reports deleted
        """
        deleted_count = 0

        if not REPORTS_BASE_DIR.exists():
            return deleted_count

        try:
            for dept_dir in REPORTS_BASE_DIR.iterdir():
                if not dept_dir.is_dir():
                    continue

                for month_dir in list(dept_dir.iterdir()):
                    if not month_dir.is_dir():
                        continue

                    # Check if this is for the target year
                    try:
                        dir_year = int(month_dir.name.split('-')[0])
                        if dir_year == year:
                            # Count and delete files
                            for file in month_dir.glob('*.html'):
                                file.unlink()
                                deleted_count += 1

                            # Remove empty directory
                            if not any(month_dir.iterdir()):
                                month_dir.rmdir()

                    except (ValueError, IndexError):
                        continue

                # Clean up empty department directory
                if dept_dir.exists() and not any(dept_dir.iterdir()):
                    dept_dir.rmdir()

            logger.info(f"Purged {deleted_count} reports for year {year}")

        except Exception as e:
            logger.error(f"Failed to purge reports: {str(e)}")

        return deleted_count
