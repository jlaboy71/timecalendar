"""
Generate sample auto-notify reports for testing.

Creates sample HTML reports for the Technology department covering
September through December 2025 with weekly, bi-weekly, and monthly frequencies.

Run with: python scripts/generate_sample_reports.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
from src.services.report_storage_service import ReportStorageService


def generate_report_html(frequency: str, report_date: date, department: str) -> str:
    """Generate sample HTML report content."""

    # Sample employee data
    employees = [
        {'name': 'John Smith', 'pto_type': 'vacation', 'days': 3, 'dates': 'Dec 20-22'},
        {'name': 'Jane Doe', 'pto_type': 'sick', 'days': 1, 'dates': 'Dec 18'},
        {'name': 'Mike Johnson', 'pto_type': 'personal', 'days': 0.5, 'dates': 'Dec 19 (AM)'},
        {'name': 'Sarah Wilson', 'pto_type': 'wfh', 'days': 2, 'dates': 'Dec 16-17'},
    ]

    # Color mapping
    colors = {
        'vacation': '#3b82f6',
        'sick': '#22c55e',
        'personal': '#a855f7',
        'wfh': '#ef4444'
    }

    # Build employee rows
    rows = ""
    for emp in employees:
        color = colors.get(emp['pto_type'], '#6b7280')
        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">{emp['name']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">
                <span style="background-color: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                    {emp['pto_type'].upper()}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #374151;">{emp['dates']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #374151; text-align: center;">{emp['days']}</td>
        </tr>
        """

    # Generate date range based on frequency
    if frequency == 'weekly':
        end_date = report_date
        start_date = report_date - timedelta(days=6)
        period = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    elif frequency == 'bi-weekly':
        end_date = report_date
        start_date = report_date - timedelta(days=13)
        period = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    else:  # monthly
        period = report_date.strftime('%B %Y')

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
                        <td style="color: #e5e7eb;">{report_date.strftime('%B %d, %Y')}</td>
                    </tr>
                </table>
            </div>

            <!-- Summary Stats -->
            <div style="background-color: #1f2937; padding: 20px;">
                <table style="width: 100%; border-collapse: separate; border-spacing: 15px 0;">
                    <tr>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #C9A227;">4</div>
                            <div style="color: #9ca3af; font-size: 12px;">Auto-Approved</div>
                        </td>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #22c55e;">6.5</div>
                            <div style="color: #9ca3af; font-size: 12px;">Total Days</div>
                        </td>
                        <td style="text-align: center; padding: 15px; background-color: #374151; border-radius: 8px; width: 33%;">
                            <div style="font-size: 28px; font-weight: bold; color: #3b82f6;">3</div>
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
                    PTO Central - Auto-Notify System
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


def main():
    """Generate sample reports for testing."""

    department = "Technology"
    year = 2025

    # Generate reports for September through December
    reports_created = 0

    for month in range(9, 13):  # September to December
        # Get month end date
        if month == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # Weekly reports (every Sunday)
        week_date = date(year, month, 1)
        # Find first Sunday
        while week_date.weekday() != 6:  # Sunday
            week_date += timedelta(days=1)

        while week_date.month == month:
            html = generate_report_html('weekly', week_date, department)
            if ReportStorageService.save_report(department, 'weekly', week_date, html):
                reports_created += 1
                print(f"Created weekly report for {week_date}")
            week_date += timedelta(days=7)

        # Bi-weekly reports (1st and 15th, or nearest weekday)
        for day in [1, 15]:
            bi_weekly_date = date(year, month, day)
            # Adjust if weekend
            if bi_weekly_date.weekday() == 5:  # Saturday
                bi_weekly_date += timedelta(days=2)
            elif bi_weekly_date.weekday() == 6:  # Sunday
                bi_weekly_date += timedelta(days=1)

            html = generate_report_html('bi-weekly', bi_weekly_date, department)
            if ReportStorageService.save_report(department, 'bi-weekly', bi_weekly_date, html):
                reports_created += 1
                print(f"Created bi-weekly report for {bi_weekly_date}")

        # Monthly report (last day of month)
        html = generate_report_html('monthly', month_end, department)
        if ReportStorageService.save_report(department, 'monthly', month_end, html):
            reports_created += 1
            print(f"Created monthly report for {month_end}")

    print(f"\nCreated {reports_created} sample reports for {department} department")
    print(f"  Reports stored in: admin_reports/{department}/")


if __name__ == '__main__':
    main()
