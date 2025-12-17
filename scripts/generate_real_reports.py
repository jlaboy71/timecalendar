"""
Generate auto-notify reports from real trusted employee PTO data.

Queries PTO data for trusted employees and generates weekly, bi-weekly,
and monthly reports based on actual approved time off requests.

Run with: python scripts/generate_real_reports.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
from collections import defaultdict
from src.services.report_storage_service import ReportStorageService
from src.database import get_db
from src.models.pto_request import PTORequest
from src.models.user import User
from src.models.department import Department
from sqlalchemy import and_


def get_day_name(d: date) -> str:
    """Get abbreviated day name for a date."""
    return d.strftime('%a')  # Mon, Tue, Wed, etc.


def format_date_with_day(d: date) -> str:
    """Format date with day name (e.g., 'Mon Dec 16')."""
    return d.strftime('%a %b %d')


def format_date_range_with_days(start: date, end: date) -> str:
    """Format date range with day names."""
    if start == end:
        return format_date_with_day(start)
    elif start.month == end.month:
        return f"{format_date_with_day(start)} - {get_day_name(end)} {end.day}"
    else:
        return f"{format_date_with_day(start)} - {format_date_with_day(end)}"


def generate_report_html(frequency: str, report_date: date, department: str,
                         requests: list, trusted_count: int) -> str:
    """Generate HTML report content from actual PTO data."""

    # Color mapping for PTO types
    colors = {
        'vacation': '#3b82f6',
        'sick': '#22c55e',
        'personal': '#a855f7',
        'wfh': '#ef4444',
        'work_from_home': '#ef4444'
    }

    # Calculate totals
    total_requests = len(requests)
    total_days = sum(float(r['total_days']) for r in requests)

    # Build employee rows
    rows = ""
    for req in requests:
        color = colors.get(req['pto_type'], '#6b7280')
        pto_display = req['pto_type'].replace('_', ' ').upper()
        days_display = f"{req['total_days']:.1f}" if req['total_days'] != int(req['total_days']) else str(int(req['total_days']))

        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">{req['employee_name']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">
                <span style="background-color: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                    {pto_display}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">{req['date_range']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #374151; text-align: center;">{days_display}</td>
        </tr>
        """

    # Generate date range based on frequency
    if frequency == 'weekly':
        end_date = report_date
        start_date = report_date - timedelta(days=6)
        period = f"{format_date_with_day(start_date)} - {format_date_with_day(end_date)}, {end_date.year}"
    elif frequency == 'bi-weekly':
        end_date = report_date
        start_date = report_date - timedelta(days=13)
        period = f"{format_date_with_day(start_date)} - {format_date_with_day(end_date)}, {end_date.year}"
    else:  # monthly
        period = report_date.strftime('%B %Y')

    # Format totals for display
    total_days_display = f"{total_days:.1f}" if total_days != int(total_days) else str(int(total_days))

    # No data message if empty
    if not requests:
        rows = """
        <tr>
            <td colspan="4" style="padding: 20px; text-align: center; color: #9ca3af;">
                No auto-approved requests during this period
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Auto-Notify Report - {frequency.title()}</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background-color: #111827; color: #e5e7eb;">
        <div style="width: 100%; padding: 20px; box-sizing: border-box;">
            <!-- Header -->
            <div style="background-color: #1f2937; padding: 20px; border-radius: 8px 8px 0 0; border-bottom: 3px solid #C9A227;">
                <h1 style="margin: 0; color: #C9A227; font-size: 24px;">
                    Trusted Employee Auto-Approve Report
                </h1>
                <p style="margin: 5px 0 0; color: #9ca3af; font-size: 14px;">
                    {frequency.replace('-', ' ').title()} Summary - {period}
                </p>
            </div>

            <!-- Department Info -->
            <div style="background-color: #1f2937; padding: 15px 20px; border-bottom: 1px solid #374151;">
                <table style="width: 100%;">
                    <tr>
                        <td style="color: #9ca3af;">Department:</td>
                        <td style="color: #e5e7eb; font-weight: bold;">{department}</td>
                        <td style="color: #9ca3af;">Generated:</td>
                        <td style="color: #e5e7eb;">{format_date_with_day(report_date)}, {report_date.year}</td>
                    </tr>
                </table>
            </div>

            <!-- Summary Stats -->
            <div style="background-color: #1f2937; padding: 20px;">
                <table style="width: 100%; border-collapse: separate; border-spacing: 15px 0;">
                    <tr>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #C9A227;">{total_requests}</div>
                            <div style="color: #9ca3af; font-size: 12px;">Auto-Approved</div>
                        </td>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #22c55e;">{total_days_display}</div>
                            <div style="color: #9ca3af; font-size: 12px;">Total Days</div>
                        </td>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #3b82f6;">{trusted_count}</div>
                            <div style="color: #9ca3af; font-size: 12px;">Trusted Employees</div>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Request Table -->
            <div style="background-color: #1f2937; padding: 20px;">
                <h2 style="margin: 0 0 15px; color: #e5e7eb; font-size: 16px; border-bottom: 1px solid #374151; padding-bottom: 10px;">
                    Auto-Approved Requests
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #374151;">
                            <th style="padding: 12px; text-align: left; color: #C9A227;">Employee</th>
                            <th style="padding: 12px; text-align: left; color: #C9A227;">Type</th>
                            <th style="padding: 12px; text-align: left; color: #C9A227;">Dates</th>
                            <th style="padding: 12px; text-align: center; color: #C9A227;">Days</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>

            <!-- Footer -->
            <div style="background-color: #374151; padding: 15px 20px; border-radius: 0 0 8px 8px; text-align: center;">
                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                    TJM Time Calendar - Auto-Notify System
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def get_requests_in_period(all_requests: list, start_date: date, end_date: date) -> list:
    """Filter requests that overlap with the given period."""
    results = []
    for req in all_requests:
        # Check if request overlaps with period
        if req['start_date'] <= end_date and req['end_date'] >= start_date:
            results.append(req)
    return results


def main():
    """Generate reports from real trusted employee PTO data."""

    db = next(get_db())
    try:
        # Get trusted employees and their PTO requests
        trusted_users = db.query(User).filter(User.is_trusted == True).all()

        if not trusted_users:
            print("No trusted employees found!")
            return

        print(f"Found {len(trusted_users)} trusted employees:")
        for u in trusted_users:
            print(f"  - {u.first_name} {u.last_name} (ID: {u.id})")

        # Get all approved PTO requests for trusted employees
        trusted_user_ids = [u.id for u in trusted_users]

        all_pto_requests = db.query(PTORequest).filter(
            and_(
                PTORequest.user_id.in_(trusted_user_ids),
                PTORequest.status == 'approved'
            )
        ).all()

        print(f"\nFound {len(all_pto_requests)} approved PTO requests")

        if not all_pto_requests:
            print("No approved PTO requests found for trusted employees!")
            return

        # Build lookup for user names and department
        user_lookup = {u.id: f"{u.first_name} {u.last_name}" for u in trusted_users}

        # Get department name (assuming all trusted users are in same dept)
        first_user = trusted_users[0]
        dept = db.query(Department).filter(Department.id == first_user.department_id).first()
        department_name = dept.name if dept else "Technology"

        print(f"Department: {department_name}")

        # Convert PTO requests to dict format
        pto_data = []
        for req in all_pto_requests:
            pto_data.append({
                'employee_name': user_lookup.get(req.user_id, 'Unknown'),
                'pto_type': req.pto_type,
                'start_date': req.start_date,
                'end_date': req.end_date,
                'total_days': float(req.total_days),
                'date_range': format_date_range_with_days(req.start_date, req.end_date)
            })

        # Sort by start date
        pto_data.sort(key=lambda x: x['start_date'])

        # Determine date range from data
        min_date = min(r['start_date'] for r in pto_data)
        max_date = max(r['end_date'] for r in pto_data)

        print(f"Date range: {min_date} to {max_date}")

        year = 2025
        reports_created = 0
        trusted_count = len(trusted_users)

        # Generate reports for all months that have data
        for month in range(1, 13):
            # Get month boundaries
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            # Skip months outside our data range (with some buffer)
            if month_end < min_date - timedelta(days=14) or month_start > max_date + timedelta(days=14):
                continue

            print(f"\nProcessing {month_start.strftime('%B %Y')}...")

            # Weekly reports (every Sunday)
            week_date = month_start
            while week_date.weekday() != 6:  # Find first Sunday
                week_date += timedelta(days=1)

            while week_date <= month_end:
                week_start = week_date - timedelta(days=6)
                requests = get_requests_in_period(pto_data, week_start, week_date)

                html = generate_report_html('weekly', week_date, department_name, requests, trusted_count)
                if ReportStorageService.save_report(department_name, 'weekly', week_date, html):
                    reports_created += 1
                    print(f"  Created weekly report for {week_date} ({len(requests)} requests)")
                week_date += timedelta(days=7)

            # Bi-weekly reports (1st and 15th)
            for day in [1, 15]:
                bi_weekly_date = date(year, month, day)
                # Adjust if weekend
                if bi_weekly_date.weekday() == 5:  # Saturday
                    bi_weekly_date += timedelta(days=2)
                elif bi_weekly_date.weekday() == 6:  # Sunday
                    bi_weekly_date += timedelta(days=1)

                bi_weekly_start = bi_weekly_date - timedelta(days=13)
                requests = get_requests_in_period(pto_data, bi_weekly_start, bi_weekly_date)

                html = generate_report_html('bi-weekly', bi_weekly_date, department_name, requests, trusted_count)
                if ReportStorageService.save_report(department_name, 'bi-weekly', bi_weekly_date, html):
                    reports_created += 1
                    print(f"  Created bi-weekly report for {bi_weekly_date} ({len(requests)} requests)")

            # Monthly report (last day of month)
            requests = get_requests_in_period(pto_data, month_start, month_end)

            html = generate_report_html('monthly', month_end, department_name, requests, trusted_count)
            if ReportStorageService.save_report(department_name, 'monthly', month_end, html):
                reports_created += 1
                print(f"  Created monthly report for {month_end} ({len(requests)} requests)")

        print(f"\n{'='*50}")
        print(f"Created {reports_created} reports for {department_name} department")
        print(f"Reports stored in: admin_reports/{department_name}/")

    finally:
        db.close()


if __name__ == '__main__':
    main()
