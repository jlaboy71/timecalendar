"""
Report generation service for TJM Time Calendar.

Provides formatted reports with company branding for PDF, print, and email.
"""
import logging
import base64
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Any
from io import BytesIO
from pathlib import Path
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _fmt_days(value: float) -> str:
    """Format days value, removing unnecessary decimal for whole numbers."""
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


# Load TJM logo as base64 at module level
_LOGO_BASE64 = None
_logo_path = Path(__file__).parent.parent.parent / 'nicegui_app' / 'static' / 'TJMLogo.png'
if _logo_path.exists():
    try:
        with open(_logo_path, 'rb') as f:
            _LOGO_BASE64 = base64.b64encode(f.read()).decode('ascii')
    except Exception as e:
        logger.warning(f"Could not load TJM logo: {e}")


class ReportService:
    """Service for generating formatted reports."""

    # Company branding - TJM colors from logo
    COMPANY_NAME = "TJM Holdings / Haventech Solutions"
    TJM_GOLD = "#C5A951"  # Gold/olive color from logo
    TJM_GRAY = "#5A6A72"  # Dark gray/slate from logo text
    LOGO_BASE64 = _LOGO_BASE64

    def __init__(self, db: Session):
        self.db = db

    def get_report_header_html(self, title: str, employee_name: str = None,
                                department: str = None, generated_by: str = None) -> str:
        """
        Generate HTML header for reports with logo and branding.

        Args:
            title: Report title
            employee_name: Name of employee (for personal reports)
            department: Department name
            generated_by: Name of user who generated the report

        Returns:
            HTML string for report header
        """
        now = datetime.now()
        date_str = now.strftime('%B %d, %Y')
        time_str = now.strftime('%I:%M %p')

        # Build employee/department line
        subtitle_parts = []
        if employee_name:
            subtitle_parts.append(f"<strong>{employee_name}</strong>")
        if department:
            subtitle_parts.append(f"Department: {department}")
        subtitle = " | ".join(subtitle_parts) if subtitle_parts else ""

        # Logo HTML - embedded as base64
        logo_html = ""
        if self.LOGO_BASE64:
            logo_html = f'<img src="data:image/png;base64,{self.LOGO_BASE64}" alt="TJM" style="height: 50px; width: auto;">'
        else:
            logo_html = f'<div style="font-size: 24px; font-weight: bold; color: {self.TJM_GRAY};">TJM</div>'

        header_html = f'''
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; border-bottom: 3px solid {self.TJM_GOLD};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div>
                    {logo_html}
                    <div style="font-size: 10px; color: #666; margin-top: 4px;">Time Calendar System</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: #666;">Generated: {date_str}</div>
                    <div style="font-size: 11px; color: #666;">{time_str}</div>
                </div>
            </div>
            <div style="margin-top: 10px;">
                <h1 style="margin: 0; font-size: 20px; color: {self.TJM_GRAY};">{title}</h1>
                {f'<div style="font-size: 14px; color: #555; margin-top: 5px;">{subtitle}</div>' if subtitle else ''}
            </div>
        </div>
        '''
        return header_html

    def get_report_footer_html(self, page_num: int = None, total_pages: int = None) -> str:
        """Generate HTML footer for reports."""
        footer_html = f'''
        <div style="font-family: 'Segoe UI', sans-serif; padding: 15px 20px; border-top: 1px solid #ddd; margin-top: 20px; font-size: 10px; color: #888;">
            <div style="display: flex; justify-content: space-between;">
                <div>{self.COMPANY_NAME}</div>
                <div>Confidential - Internal Use Only</div>
                {f'<div>Page {page_num} of {total_pages}</div>' if page_num else ''}
            </div>
        </div>
        '''
        return footer_html

    def generate_balance_report_html(self, user_id: int, year: int) -> str:
        """
        Generate a formatted balance report for an employee.

        Args:
            user_id: Employee's user ID
            year: Year for the report

        Returns:
            Complete HTML document for the report
        """
        from src.models.user import User
        from src.models.pto_balance import PTOBalance
        from src.models.department import Department

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "<p>User not found</p>"

        balance = self.db.query(PTOBalance).filter(
            PTOBalance.user_id == user_id,
            PTOBalance.year == year
        ).first()

        dept_name = user.department.name if user.department else "No Department"
        employee_name = f"{user.first_name} {user.last_name}"

        # Calculate balances
        if balance:
            vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
            vac_used = float(balance.vacation_used or 0)
            vac_pending = float(balance.vacation_pending or 0)
            vac_avail = vac_total - vac_used - vac_pending

            sick_total = float(balance.sick_total or 0) + float(balance.sick_carryover or 0)
            sick_used = float(balance.sick_used or 0)
            sick_avail = sick_total - sick_used

            personal_total = float(balance.personal_total or 0) + float(balance.personal_carryover or 0)
            personal_used = float(balance.personal_used or 0)
            personal_avail = personal_total - personal_used
        else:
            vac_total = vac_used = vac_pending = vac_avail = 0
            sick_total = sick_used = sick_avail = 0
            personal_total = personal_used = personal_avail = 0

        def hours_to_days(hours):
            return _fmt_days(hours / 8)

        header = self.get_report_header_html(
            title=f"PTO Balance Summary - {year}",
            employee_name=employee_name,
            department=dept_name
        )

        content = f'''
        <div style="padding: 20px; font-family: 'Segoe UI', sans-serif;">
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background: {self.TJM_GRAY}; color: white;">
                        <th style="padding: 12px; text-align: left;">Leave Type</th>
                        <th style="padding: 12px; text-align: center;">Total (Days)</th>
                        <th style="padding: 12px; text-align: center;">Used (Days)</th>
                        <th style="padding: 12px; text-align: center;">Pending (Days)</th>
                        <th style="padding: 12px; text-align: center;">Available (Days)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 12px;"><strong>Vacation</strong></td>
                        <td style="padding: 12px; text-align: center;">{hours_to_days(vac_total)}</td>
                        <td style="padding: 12px; text-align: center; color: #c62828;">{hours_to_days(vac_used)}</td>
                        <td style="padding: 12px; text-align: center; color: #f57c00;">{hours_to_days(vac_pending)}</td>
                        <td style="padding: 12px; text-align: center; color: {'#2e7d32' if vac_avail > 0 else '#c62828'}; font-weight: bold;">{hours_to_days(vac_avail)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd; background: #f9f9f9;">
                        <td style="padding: 12px;"><strong>Sick</strong></td>
                        <td style="padding: 12px; text-align: center;">{hours_to_days(sick_total)}</td>
                        <td style="padding: 12px; text-align: center; color: #c62828;">{hours_to_days(sick_used)}</td>
                        <td style="padding: 12px; text-align: center;">-</td>
                        <td style="padding: 12px; text-align: center; color: {'#2e7d32' if sick_avail > 0 else '#c62828'}; font-weight: bold;">{hours_to_days(sick_avail)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 12px;"><strong>Personal</strong></td>
                        <td style="padding: 12px; text-align: center;">{hours_to_days(personal_total)}</td>
                        <td style="padding: 12px; text-align: center; color: #c62828;">{hours_to_days(personal_used)}</td>
                        <td style="padding: 12px; text-align: center;">-</td>
                        <td style="padding: 12px; text-align: center; color: {'#2e7d32' if personal_avail > 0 else '#c62828'}; font-weight: bold;">{hours_to_days(personal_avail)}</td>
                    </tr>
                </tbody>
            </table>

            <div style="margin-top: 30px; padding: 15px; background: #f5f0e1; border-left: 4px solid {self.TJM_GOLD}; border-radius: 4px;">
                <h3 style="margin: 0 0 10px 0; color: {self.TJM_GRAY};">Summary</h3>
                <p style="margin: 5px 0;">Total PTO Available: <strong>{hours_to_days(vac_avail + sick_avail + personal_avail)} days</strong></p>
                <p style="margin: 5px 0;">Total PTO Used YTD: <strong>{hours_to_days(vac_used + sick_used + personal_used)} days</strong></p>
            </div>
        </div>
        '''

        footer = self.get_report_footer_html()

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>PTO Balance Report - {employee_name}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; }}
                    @page {{ margin: 0.5in; }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; background: white;">
            {header}
            {content}
            {footer}
        </body>
        </html>
        '''

    def generate_history_report_html(self, user_id: int, year: int, status_filter: str = 'all') -> str:
        """
        Generate a formatted PTO history report for an employee.
        """
        from src.models.user import User
        from src.models.pto_request import PTORequest
        from sqlalchemy.orm import joinedload

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "<p>User not found</p>"

        # Load requests with approver relationship
        query = self.db.query(PTORequest).options(
            joinedload(PTORequest.approver)
        ).filter(
            PTORequest.user_id == user_id,
            PTORequest.start_date >= date(year, 1, 1),
            PTORequest.end_date <= date(year, 12, 31)
        )

        if status_filter != 'all':
            query = query.filter(PTORequest.status == status_filter)

        requests = query.order_by(PTORequest.start_date.desc()).all()

        dept_name = user.department.name if user.department else "No Department"
        employee_name = f"{user.first_name} {user.last_name}"

        # Find department manager
        manager_name = "N/A"
        if user.department:
            manager = self.db.query(User).filter(
                User.department_id == user.department_id,
                User.role == 'manager',
                User.is_active == True
            ).first()
            if manager:
                manager_name = f"{manager.first_name} {manager.last_name}"

        header = self.get_report_header_html(
            title=f"PTO Request History - {year}",
            employee_name=employee_name,
            department=dept_name
        )

        # Build employee info section
        hire_date_str = user.hire_date.strftime('%B %d, %Y') if user.hire_date else "N/A"
        employee_info = f'''
        <div style="padding: 15px 20px; background: #f8f9fa; border-bottom: 1px solid #ddd; font-family: 'Segoe UI', sans-serif;">
            <div style="display: flex; gap: 40px; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 11px; color: #666; text-transform: uppercase;">Hire Date</span>
                    <div style="font-size: 14px; font-weight: 500;">{hire_date_str}</div>
                </div>
                <div>
                    <span style="font-size: 11px; color: #666; text-transform: uppercase;">Manager</span>
                    <div style="font-size: 14px; font-weight: 500;">{manager_name}</div>
                </div>
                <div>
                    <span style="font-size: 11px; color: #666; text-transform: uppercase;">Location</span>
                    <div style="font-size: 14px; font-weight: 500;">{user.location_city or ''}{', ' + user.location_state if user.location_state else 'Not Set'}</div>
                </div>
            </div>
        </div>
        '''

        # Build rows with approval details
        rows_html = ""
        total_approved = 0
        total_pending = 0
        total_denied = 0

        status_colors = {
            'approved': '#2e7d32',
            'pending': '#f57c00',
            'denied': '#c62828',
            'cancelled': '#757575'
        }

        for req in requests:
            color = status_colors.get(req.status, '#333')
            if req.status == 'approved':
                total_approved += float(req.total_days or 0)
            elif req.status == 'pending':
                total_pending += float(req.total_days or 0)
            elif req.status == 'denied':
                total_denied += float(req.total_days or 0)

            date_range = req.start_date.strftime('%b %d')
            if req.start_date != req.end_date:
                date_range += f" - {req.end_date.strftime('%b %d, %Y')}"
            else:
                date_range += f", {req.start_date.year}"

            # Build approval/processed info
            processed_info = ""
            if req.status in ['approved', 'denied'] and req.approved_at:
                approver_name = f"{req.approver.first_name} {req.approver.last_name}" if req.approver else "System"
                processed_date = req.approved_at.strftime('%b %d, %Y')
                processed_info = f'<div style="font-size: 10px; color: #888; margin-top: 2px;">By {approver_name} on {processed_date}</div>'
                if req.status == 'denied' and req.denial_reason:
                    processed_info += f'<div style="font-size: 10px; color: #c62828; margin-top: 2px;">Reason: {req.denial_reason}</div>'

            rows_html += f'''
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">{req.pto_type.title()}</td>
                <td style="padding: 10px;">{date_range}</td>
                <td style="padding: 10px; text-align: center;">{_fmt_days(float(req.total_days or 0))}</td>
                <td style="padding: 10px;">
                    <span style="color: {color}; font-weight: bold;">{req.status.upper()}</span>
                    {processed_info}
                </td>
                <td style="padding: 10px; font-style: italic; color: #666;">{req.notes or '-'}</td>
            </tr>
            '''

        content = f'''
        <div style="padding: 20px; font-family: 'Segoe UI', sans-serif;">
            <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 140px; padding: 15px; background: #e8f5e9; border-left: 4px solid #2e7d32; border-radius: 4px;">
                    <div style="font-size: 11px; color: #666;">Approved Days</div>
                    <div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{_fmt_days(total_approved)}</div>
                </div>
                <div style="flex: 1; min-width: 140px; padding: 15px; background: #fff3e0; border-left: 4px solid #f57c00; border-radius: 4px;">
                    <div style="font-size: 11px; color: #666;">Pending Days</div>
                    <div style="font-size: 24px; font-weight: bold; color: #f57c00;">{_fmt_days(total_pending)}</div>
                </div>
                <div style="flex: 1; min-width: 140px; padding: 15px; background: #ffebee; border-left: 4px solid #c62828; border-radius: 4px;">
                    <div style="font-size: 11px; color: #666;">Denied Days</div>
                    <div style="font-size: 24px; font-weight: bold; color: #c62828;">{_fmt_days(total_denied)}</div>
                </div>
                <div style="flex: 1; min-width: 140px; padding: 15px; background: #f5f0e1; border-left: 4px solid {self.TJM_GOLD}; border-radius: 4px;">
                    <div style="font-size: 11px; color: #666;">Total Requests</div>
                    <div style="font-size: 24px; font-weight: bold; color: {self.TJM_GRAY};">{len(requests)}</div>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: {self.TJM_GRAY}; color: white;">
                        <th style="padding: 12px; text-align: left;">Type</th>
                        <th style="padding: 12px; text-align: left;">Dates</th>
                        <th style="padding: 12px; text-align: center;">Days</th>
                        <th style="padding: 12px; text-align: left;">Status</th>
                        <th style="padding: 12px; text-align: left;">Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #666;">No requests found for this period.</td></tr>'}
                </tbody>
            </table>
        </div>
        '''

        footer = self.get_report_footer_html()

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>PTO History Report - {employee_name}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; }}
                    @page {{ margin: 0.5in; }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; background: white;">
            {header}
            {employee_info}
            {content}
            {footer}
        </body>
        </html>
        '''

    def generate_team_balance_report_html(self, year: int, department_id: int = None, employee_id: int = None) -> str:
        """Generate a formatted team balance report.

        Args:
            year: Year for the report
            department_id: Optional department filter
            employee_id: Optional single employee filter (overrides team view)
        """
        from src.models.user import User
        from src.models.pto_balance import PTOBalance
        from src.models.department import Department

        query = self.db.query(User, PTOBalance).outerjoin(
            PTOBalance,
            (PTOBalance.user_id == User.id) & (PTOBalance.year == year)
        ).filter(User.is_active == True)

        dept_name = "All Departments"
        employee_name = None

        # If specific employee is selected, filter to just that employee
        if employee_id:
            query = query.filter(User.id == employee_id)
            emp = self.db.query(User).filter(User.id == employee_id).first()
            if emp:
                employee_name = f"{emp.first_name} {emp.last_name}"
                dept_name = emp.department.name if emp.department else "No Department"
        elif department_id:
            query = query.filter(User.department_id == department_id)
            dept = self.db.query(Department).filter(Department.id == department_id).first()
            dept_name = dept.name if dept else "Unknown Department"

        results = query.order_by(User.last_name, User.first_name).all()

        # Dynamic title based on filter
        if employee_name:
            title = f"{employee_name} Balance Summary - {year}"
        else:
            title = f"Team Balance Summary - {year}"

        header = self.get_report_header_html(
            title=title,
            employee_name=employee_name,
            department=dept_name
        )

        rows_html = ""
        for user_obj, balance in results:
            user_dept = user_obj.department.name if user_obj.department else "No Dept"

            if balance:
                vac_total = float(balance.vacation_total or 0) + float(balance.vacation_carryover or 0)
                vac_used = float(balance.vacation_used or 0)
                vac_avail = vac_total - vac_used - float(balance.vacation_pending or 0)
                sick_total = float(balance.sick_total or 0)
                sick_used = float(balance.sick_used or 0)
                personal_total = float(balance.personal_total or 0)
                personal_used = float(balance.personal_used or 0)
            else:
                vac_total = vac_used = vac_avail = sick_total = sick_used = personal_total = personal_used = 0

            def h2d(h):
                return _fmt_days(h / 8)

            rows_html += f'''
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px;">{user_obj.first_name} {user_obj.last_name}</td>
                <td style="padding: 8px;">{user_dept}</td>
                <td style="padding: 8px; text-align: center;">{h2d(vac_total)}</td>
                <td style="padding: 8px; text-align: center;">{h2d(vac_used)}</td>
                <td style="padding: 8px; text-align: center; color: {'#2e7d32' if vac_avail > 0 else '#c62828'}; font-weight: bold;">{h2d(vac_avail)}</td>
                <td style="padding: 8px; text-align: center;">{h2d(sick_total)}</td>
                <td style="padding: 8px; text-align: center;">{h2d(sick_used)}</td>
                <td style="padding: 8px; text-align: center;">{h2d(personal_total)}</td>
                <td style="padding: 8px; text-align: center;">{h2d(personal_used)}</td>
            </tr>
            '''

        content = f'''
        <div style="padding: 20px; font-family: 'Segoe UI', sans-serif;">
            <p style="color: #666; margin-bottom: 15px;">Total Employees: {len(results)}</p>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                    <tr style="background: {self.TJM_GRAY}; color: white;">
                        <th style="padding: 10px; text-align: left;">Employee</th>
                        <th style="padding: 10px; text-align: left;">Department</th>
                        <th style="padding: 10px; text-align: center;">Vac Total</th>
                        <th style="padding: 10px; text-align: center;">Vac Used</th>
                        <th style="padding: 10px; text-align: center;">Vac Avail</th>
                        <th style="padding: 10px; text-align: center;">Sick Total</th>
                        <th style="padding: 10px; text-align: center;">Sick Used</th>
                        <th style="padding: 10px; text-align: center;">Pers Total</th>
                        <th style="padding: 10px; text-align: center;">Pers Used</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="9" style="padding: 20px; text-align: center;">No employees found.</td></tr>'}
                </tbody>
            </table>

            <div style="margin-top: 15px; font-size: 11px; color: #888;">
                * All values shown in days (1 day = 8 hours)
            </div>
        </div>
        '''

        footer = self.get_report_footer_html()

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Team Balance Report - {year}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; }}
                    @page {{ margin: 0.5in; size: landscape; }}
                    table {{ font-size: 10px; }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; background: white;">
            {header}
            {content}
            {footer}
        </body>
        </html>
        '''

    def generate_calendar_report_html(self, user_id: int, year: int) -> str:
        """
        Generate a formatted year-at-a-glance calendar report for an employee.

        Args:
            user_id: Employee's user ID
            year: Year for the report

        Returns:
            Complete HTML document for the report
        """
        from src.models.user import User
        from src.models.pto_request import PTORequest

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "<p>User not found</p>"

        requests = self.db.query(PTORequest).filter(
            PTORequest.user_id == user_id,
            PTORequest.status == 'approved',
            PTORequest.start_date >= date(year, 1, 1),
            PTORequest.end_date <= date(year, 12, 31)
        ).order_by(PTORequest.start_date).all()

        dept_name = user.department.name if user.department else "No Department"
        employee_name = f"{user.first_name} {user.last_name}"

        header = self.get_report_header_html(
            title=f"Year at a Glance - {year}",
            employee_name=employee_name,
            department=dept_name
        )

        # Group by month
        months = {}
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        for req in requests:
            month_key = req.start_date.month
            if month_key not in months:
                months[month_key] = []
            months[month_key].append(req)

        # Calculate totals by type
        type_totals = {}
        for req in requests:
            pto_type = req.pto_type.lower()
            if pto_type not in type_totals:
                type_totals[pto_type] = 0
            type_totals[pto_type] += float(req.total_days or 0)

        # Type colors
        type_colors = {
            'vacation': '#1976d2',
            'sick': '#2e7d32',
            'personal': '#7b1fa2'
        }

        # Build summary cards
        summary_html = '<div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">'
        total_days = 0
        for pto_type, days in sorted(type_totals.items()):
            color = type_colors.get(pto_type, '#666')
            total_days += days
            summary_html += f'''
            <div style="flex: 1; min-width: 120px; padding: 15px; background: #f5f5f5; border-left: 4px solid {color}; border-radius: 4px;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">{pto_type.title()}</div>
                <div style="font-size: 24px; font-weight: bold; color: {color};">{_fmt_days(days)}</div>
                <div style="font-size: 11px; color: #999;">days</div>
            </div>
            '''
        summary_html += f'''
        <div style="flex: 1; min-width: 120px; padding: 15px; background: #f5f0e1; border-left: 4px solid {self.TJM_GOLD}; border-radius: 4px;">
            <div style="font-size: 11px; color: #666; text-transform: uppercase;">Total</div>
            <div style="font-size: 24px; font-weight: bold; color: {self.TJM_GRAY};">{_fmt_days(total_days)}</div>
            <div style="font-size: 11px; color: #999;">days</div>
        </div>
        '''
        summary_html += '</div>'

        # Build month-by-month content
        months_html = ""
        for month_num in range(1, 13):
            month_name = month_names[month_num - 1]
            month_requests = months.get(month_num, [])

            if month_requests:
                rows_html = ""
                month_total = 0
                for req in month_requests:
                    color = type_colors.get(req.pto_type.lower(), '#666')
                    days = float(req.total_days or 0)
                    month_total += days

                    if req.start_date == req.end_date:
                        date_str = req.start_date.strftime('%d')
                    else:
                        date_str = f"{req.start_date.strftime('%d')} - {req.end_date.strftime('%d')}"

                    rows_html += f'''
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">
                            <span style="display: inline-block; width: 10px; height: 10px; background: {color}; border-radius: 2px; margin-right: 8px;"></span>
                            {req.pto_type.title()}
                        </td>
                        <td style="padding: 8px;">{date_str}</td>
                        <td style="padding: 8px; text-align: right;">{_fmt_days(days)} days</td>
                        <td style="padding: 8px; color: #666; font-style: italic;">{req.notes or '-'}</td>
                    </tr>
                    '''

                months_html += f'''
                <div style="margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden;">
                    <div style="background: {self.TJM_GRAY}; color: white; padding: 10px 15px; display: flex; justify-content: space-between;">
                        <strong>{month_name}</strong>
                        <span>{len(month_requests)} request(s) • {_fmt_days(month_total)} days</span>
                    </div>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                '''

        if not months_html:
            months_html = '''
            <div style="padding: 40px; text-align: center; color: #666;">
                <div style="font-size: 48px; opacity: 0.3; margin-bottom: 10px;">📅</div>
                <p>No approved PTO for this year.</p>
            </div>
            '''

        content = f'''
        <div style="padding: 20px; font-family: 'Segoe UI', sans-serif;">
            {summary_html}
            {months_html}
        </div>
        '''

        footer = self.get_report_footer_html()

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Year at a Glance - {employee_name} - {year}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; }}
                    @page {{ margin: 0.5in; }}
                }}
            </style>
        </head>
        <body style="margin: 0; padding: 0; background: white;">
            {header}
            {content}
            {footer}
        </body>
        </html>
        '''
