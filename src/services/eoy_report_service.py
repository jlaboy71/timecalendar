"""
End-of-Year Assessment Report Service for PTO Central.

Generates comprehensive CEO-level PTO analytics including:
- Executive Summary with overall PTO health score
- Utilization Analysis by leave type
- Department Comparisons
- Carryover Summary
- Employee Burnout Risk Alerts
- Year-over-Year Trends
- Policy Compliance Metrics
- New Year Projections
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from src.models.user import User
from src.models.pto_balance import PTOBalance
from src.models.pto_request import PTORequest
from src.models.carryover_request import CarryoverRequest
from src.models.department import Department
from nicegui_app.components.theme import PTO_GOLD
from src.models.year_end_status import YearEndStatus
from src.services.year_end_service import YearEndService

logger = logging.getLogger(__name__)


class EOYReportService:
    """Service for generating End-of-Year Assessment Reports."""

    # Burnout risk threshold - employees with >= this % unused PTO are flagged
    BURNOUT_RISK_THRESHOLD = 80  # 80% or more unused = risk

    def __init__(self, db: Session):
        self.db = db

    def generate_report(self, year: int) -> Dict[str, Any]:
        """
        Generate a comprehensive EOY Assessment Report.

        Args:
            year: The year to generate the report for

        Returns:
            Dictionary containing all report sections
        """
        is_preview = year >= date.today().year
        generated_at = datetime.now()

        report = {
            'meta': {
                'year': year,
                'generated_at': generated_at,
                'generated_at_formatted': generated_at.strftime('%A, %B %d, %Y at %I:%M %p'),
                'is_preview': is_preview,
                'report_type': 'Preview (Pre-EOY Processing)' if is_preview else 'Final Report'
            },
            'executive_summary': self._generate_executive_summary(year, is_preview),
            'utilization_analysis': self._generate_utilization_analysis(year),
            'department_comparison': self._generate_department_comparison(year),
            'carryover_summary': self._generate_carryover_summary(year),
            'burnout_risk': self._generate_burnout_risk_analysis(year),
            'policy_compliance': self._generate_policy_compliance(year),
            'new_year_projections': self._generate_new_year_projections(year),
            'year_over_year': self._generate_year_over_year(year),
        }

        logger.info(f"Generated EOY Assessment Report for {year}")
        return report

    def _generate_executive_summary(self, year: int, is_preview: bool) -> Dict:
        """Generate executive summary with overall PTO health score."""
        # Get active employees
        stmt = select(func.count()).select_from(User).where(User.is_active == True)
        total_employees = self.db.execute(stmt).scalar() or 0

        # Get balances for the year
        stmt = select(PTOBalance).where(PTOBalance.year == year)
        balances = self.db.execute(stmt).scalars().all()

        if not balances:
            return {
                'health_score': 'N/A',
                'health_grade': 'No Data',
                'total_employees': total_employees,
                'employees_with_balances': 0,
                'key_observations': ['No PTO balance data available for this year.'],
                'recommendations': ['Ensure year-end processing has been completed.'],
            }

        # Calculate overall utilization
        total_vacation_allocated = sum(float(b.vacation_total or 0) for b in balances)
        total_vacation_used = sum(float(b.vacation_used or 0) for b in balances)
        total_sick_allocated = sum(float(b.sick_total or 0) for b in balances)
        total_sick_used = sum(float(b.sick_used or 0) for b in balances)
        total_personal_allocated = sum(float(b.personal_total or 0) for b in balances)
        total_personal_used = sum(float(b.personal_used or 0) for b in balances)

        # Calculate utilization rates
        vacation_util = (total_vacation_used / total_vacation_allocated * 100) if total_vacation_allocated > 0 else 0
        sick_util = (total_sick_used / total_sick_allocated * 100) if total_sick_allocated > 0 else 0
        personal_util = (total_personal_used / total_personal_allocated * 100) if total_personal_allocated > 0 else 0

        # Health score calculation (0-100)
        # Ideal utilization: Vacation 70-90%, Sick <50%, Personal 60-80%
        vacation_score = self._calculate_utilization_score(vacation_util, ideal_min=70, ideal_max=90)
        sick_score = self._calculate_utilization_score(sick_util, ideal_min=0, ideal_max=50, inverse=True)
        personal_score = self._calculate_utilization_score(personal_util, ideal_min=60, ideal_max=80)

        health_score = int((vacation_score * 0.5) + (sick_score * 0.3) + (personal_score * 0.2))

        # Determine grade
        if health_score >= 90:
            health_grade = 'Excellent'
        elif health_score >= 75:
            health_grade = 'Good'
        elif health_score >= 60:
            health_grade = 'Fair'
        else:
            health_grade = 'Needs Attention'

        # Generate observations
        observations = []
        recommendations = []

        if vacation_util < 50:
            observations.append(f'Low vacation utilization ({vacation_util:.1f}%) - employees may be at risk of burnout.')
            recommendations.append('Encourage employees to use their vacation time for work-life balance.')
        elif vacation_util > 95:
            observations.append(f'Very high vacation utilization ({vacation_util:.1f}%) - consider reviewing allocation policies.')

        if sick_util > 60:
            observations.append(f'High sick leave usage ({sick_util:.1f}%) - may indicate workplace health concerns.')
            recommendations.append('Review workplace wellness programs and ergonomic assessments.')

        if personal_util < 40:
            observations.append(f'Low personal day usage ({personal_util:.1f}%) - employees may not be aware of this benefit.')
            recommendations.append('Remind employees about personal day availability in company communications.')

        if not observations:
            observations.append('PTO utilization is within healthy ranges across all leave types.')

        if is_preview:
            observations.insert(0, 'This is a preview report. Final metrics will be available after year-end processing.')

        return {
            'health_score': health_score,
            'health_grade': health_grade,
            'total_employees': total_employees,
            'employees_with_balances': len(balances),
            'vacation_utilization': round(vacation_util, 1),
            'sick_utilization': round(sick_util, 1),
            'personal_utilization': round(personal_util, 1),
            'key_observations': observations,
            'recommendations': recommendations,
        }

    def _calculate_utilization_score(self, actual: float, ideal_min: float, ideal_max: float, inverse: bool = False) -> float:
        """Calculate a score (0-100) based on how close actual is to ideal range."""
        if ideal_min <= actual <= ideal_max:
            return 100

        if inverse:
            # For sick leave - lower is better
            if actual < ideal_min:
                return 100
            elif actual > ideal_max:
                # Penalize as it goes over
                over = actual - ideal_max
                return max(0, 100 - (over * 2))
        else:
            # For vacation/personal - want to be in range
            if actual < ideal_min:
                under = ideal_min - actual
                return max(0, 100 - (under * 1.5))
            else:
                over = actual - ideal_max
                return max(0, 100 - (over * 2))

        return 50

    def _generate_utilization_analysis(self, year: int) -> Dict:
        """Generate detailed utilization analysis by leave type."""
        stmt = select(PTOBalance).where(PTOBalance.year == year)
        balances = self.db.execute(stmt).scalars().all()

        if not balances:
            return {'vacation': {}, 'sick': {}, 'personal': {}, 'chicago_leave': {}}

        def analyze_leave_type(total_attr: str, used_attr: str, pending_attr: str = None):
            allocated = sum(float(getattr(b, total_attr) or 0) for b in balances)
            used = sum(float(getattr(b, used_attr) or 0) for b in balances)
            pending = sum(float(getattr(b, pending_attr) or 0) for b in balances) if pending_attr else 0

            return {
                'total_allocated_days': round(allocated, 1),
                'total_allocated_hours': round(allocated * 8, 1),
                'total_used_days': round(used, 1),
                'total_used_hours': round(used * 8, 1),
                'total_pending_days': round(pending, 1),
                'total_pending_hours': round(pending * 8, 1),
                'total_unused_days': round(allocated - used - pending, 1),
                'total_unused_hours': round((allocated - used - pending) * 8, 1),
                'utilization_rate': round((used / allocated * 100) if allocated > 0 else 0, 1),
            }

        return {
            'vacation': analyze_leave_type('vacation_total', 'vacation_used', 'vacation_pending'),
            'sick': analyze_leave_type('sick_total', 'sick_used'),
            'personal': analyze_leave_type('personal_total', 'personal_used'),
            'chicago_leave': analyze_leave_type('chicago_paid_leave_total', 'chicago_paid_leave_used', 'chicago_paid_leave_pending'),
        }

    def _generate_department_comparison(self, year: int) -> List[Dict]:
        """Generate department-level PTO utilization comparison."""
        # Get all departments with their users
        stmt = select(Department)
        departments = self.db.execute(stmt).scalars().all()

        results = []
        for dept in departments:
            # Get users in this department
            stmt = select(User.id).where(
                User.department_id == dept.id,
                User.is_active == True
            )
            user_ids = [row[0] for row in self.db.execute(stmt).all()]

            if not user_ids:
                continue

            # Get balances for these users
            stmt = select(PTOBalance).where(
                PTOBalance.user_id.in_(user_ids),
                PTOBalance.year == year
            )
            balances = self.db.execute(stmt).scalars().all()

            if not balances:
                continue

            total_vacation = sum(float(b.vacation_total or 0) for b in balances)
            used_vacation = sum(float(b.vacation_used or 0) for b in balances)
            total_sick = sum(float(b.sick_total or 0) for b in balances)
            used_sick = sum(float(b.sick_used or 0) for b in balances)

            results.append({
                'department_name': dept.name,
                'employee_count': len(balances),
                'vacation_utilization': round((used_vacation / total_vacation * 100) if total_vacation > 0 else 0, 1),
                'sick_utilization': round((used_sick / total_sick * 100) if total_sick > 0 else 0, 1),
                'avg_vacation_days_used': round(used_vacation / len(balances), 1) if balances else 0,
                'avg_sick_days_used': round(used_sick / len(balances), 1) if balances else 0,
            })

        # Sort by vacation utilization
        results.sort(key=lambda x: x['vacation_utilization'], reverse=True)
        return results

    def _generate_carryover_summary(self, year: int) -> Dict:
        """Generate summary of carryover activity."""
        previous_year = year - 1

        # Count carryover requests by status
        statuses = ['pending', 'approved', 'denied']
        counts = {}

        for status in statuses:
            stmt = select(func.count()).select_from(CarryoverRequest).where(
                CarryoverRequest.from_year == previous_year,
                CarryoverRequest.status == status
            )
            counts[status] = self.db.execute(stmt).scalar() or 0

        # Get total hours requested and approved
        stmt = select(
            func.sum(CarryoverRequest.hours_requested),
            func.sum(CarryoverRequest.hours_approved)
        ).where(
            CarryoverRequest.from_year == previous_year,
            CarryoverRequest.status == 'approved'
        )
        result = self.db.execute(stmt).one()
        hours_requested = float(result[0] or 0)
        hours_approved = float(result[1] or 0)

        # Calculate sick auto-carryover (from balances)
        stmt = select(PTOBalance).where(PTOBalance.year == year)
        balances = self.db.execute(stmt).scalars().all()
        total_sick_carryover_hours = sum(float(b.sick_carryover or 0) * 8 for b in balances)
        total_chicago_carryover_hours = sum(float(b.chicago_paid_leave_carryover or 0) for b in balances)

        return {
            'pending_requests': counts.get('pending', 0),
            'approved_requests': counts.get('approved', 0),
            'denied_requests': counts.get('denied', 0),
            'vacation_hours_requested': round(hours_requested, 1),
            'vacation_hours_approved': round(hours_approved, 1),
            'sick_auto_carryover_hours': round(total_sick_carryover_hours, 1),
            'chicago_auto_carryover_hours': round(total_chicago_carryover_hours, 1),
            'total_carryover_hours': round(hours_approved + total_sick_carryover_hours + total_chicago_carryover_hours, 1),
        }

    def _generate_burnout_risk_analysis(self, year: int) -> Dict:
        """
        Identify employees at risk of burnout based on low PTO usage.

        Employees with >= 80% unused vacation are flagged as at-risk.
        """
        stmt = select(PTOBalance, User).join(User, PTOBalance.user_id == User.id).where(
            PTOBalance.year == year,
            User.is_active == True
        )
        results = self.db.execute(stmt).all()

        at_risk_employees = []
        for balance, user in results:
            vacation_total = float(balance.vacation_total or 0)
            vacation_used = float(balance.vacation_used or 0)
            vacation_pending = float(balance.vacation_pending or 0)

            if vacation_total > 0:
                unused_pct = ((vacation_total - vacation_used - vacation_pending) / vacation_total) * 100

                if unused_pct >= self.BURNOUT_RISK_THRESHOLD:
                    at_risk_employees.append({
                        'employee_name': f"{user.first_name} {user.last_name}",
                        'department': user.department.name if user.department else 'Unassigned',
                        'vacation_total_days': vacation_total,
                        'vacation_used_days': vacation_used,
                        'vacation_unused_days': round(vacation_total - vacation_used - vacation_pending, 1),
                        'unused_percentage': round(unused_pct, 1),
                        'gentle_note': self._get_gentle_burnout_message(unused_pct, vacation_total - vacation_used - vacation_pending),
                    })

        # Sort by unused percentage (highest risk first)
        at_risk_employees.sort(key=lambda x: x['unused_percentage'], reverse=True)

        return {
            'threshold_percentage': self.BURNOUT_RISK_THRESHOLD,
            'total_at_risk': len(at_risk_employees),
            'employees': at_risk_employees[:20],  # Top 20 at-risk
            'summary_message': self._get_burnout_summary_message(len(at_risk_employees)),
        }

    def _get_gentle_burnout_message(self, unused_pct: float, unused_days: float) -> str:
        """Generate a gentle, supportive message for at-risk employees."""
        if unused_pct >= 95:
            return f"Has {unused_days:.1f} days remaining. Consider encouraging time off for rest and recharge."
        elif unused_pct >= 85:
            return f"Has significant unused vacation ({unused_days:.1f} days). A well-deserved break may help maintain productivity."
        else:
            return f"Has {unused_days:.1f} vacation days remaining. May benefit from scheduling upcoming time off."

    def _get_burnout_summary_message(self, count: int) -> str:
        """Generate summary message for burnout risk section."""
        if count == 0:
            return "All employees are utilizing their vacation time appropriately. No burnout risk flags."
        elif count <= 3:
            return f"{count} employee(s) may benefit from encouragement to take time off."
        elif count <= 10:
            return f"{count} employees have significant unused vacation. Consider a company-wide reminder about work-life balance."
        else:
            return f"{count} employees are flagged for high unused vacation. This may indicate cultural or workload issues requiring attention."

    def _generate_policy_compliance(self, year: int) -> Dict:
        """Generate policy compliance metrics."""
        # Get all approved requests for the year
        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            func.extract('year', PTORequest.start_date) == year
        )
        approved_requests = self.db.execute(stmt).scalars().all()

        # Analyze advance notice (requests submitted at least 2 weeks before start)
        advance_notice_compliant = 0
        short_notice = 0

        for req in approved_requests:
            if req.submitted_at and req.start_date:
                days_notice = (req.start_date - req.submitted_at.date()).days
                if days_notice >= 14:
                    advance_notice_compliant += 1
                elif days_notice < 3:
                    short_notice += 1

        total_requests = len(approved_requests)
        compliance_rate = (advance_notice_compliant / total_requests * 100) if total_requests > 0 else 0

        # Count denied requests (potential overdraft attempts)
        stmt = select(func.count()).select_from(PTORequest).where(
            PTORequest.status == 'denied',
            func.extract('year', PTORequest.start_date) == year
        )
        denied_count = self.db.execute(stmt).scalar() or 0

        return {
            'total_approved_requests': total_requests,
            'advance_notice_compliant': advance_notice_compliant,
            'short_notice_requests': short_notice,
            'compliance_rate': round(compliance_rate, 1),
            'denied_requests': denied_count,
            'compliance_status': 'Good' if compliance_rate >= 70 else 'Needs Improvement',
        }

    def _generate_new_year_projections(self, year: int) -> Dict:
        """Generate projections for the upcoming year."""
        next_year = year + 1
        year_end_service = YearEndService(self.db)

        # Get active employees
        stmt = select(User).where(User.is_active == True)
        active_users = self.db.execute(stmt).scalars().all()

        # Calculate vacation tier distribution
        tier_10 = 0  # 0-1 years
        tier_12 = 0  # 2-4 years
        tier_15 = 0  # 5-9 years
        tier_20 = 0  # 10+ years

        total_vacation_days = 0
        today = date.today()

        for user in active_users:
            if not user.hire_date:
                tier_10 += 1
                total_vacation_days += 10
                continue

            years_of_service = (today - user.hire_date).days // 365
            if years_of_service >= 10:
                tier_20 += 1
                total_vacation_days += 20
            elif years_of_service >= 5:
                tier_15 += 1
                total_vacation_days += 15
            elif years_of_service >= 2:
                tier_12 += 1
                total_vacation_days += 12
            else:
                tier_10 += 1
                total_vacation_days += 10

        total_employees = len(active_users)

        return {
            'projected_year': next_year,
            'total_employees': total_employees,
            'vacation_tier_distribution': {
                '10_days_tier': tier_10,
                '12_days_tier': tier_12,
                '15_days_tier': tier_15,
                '20_days_tier': tier_20,
            },
            'total_vacation_days_allocated': total_vacation_days,
            'total_vacation_hours_allocated': total_vacation_days * 8,
            'total_sick_days_allocated': total_employees * 5,
            'total_personal_days_allocated': total_employees * 2,
            'employees_advancing_tiers': self._count_tier_advances(active_users, next_year),
        }

    def _count_tier_advances(self, users: List[User], next_year: int) -> int:
        """Count how many employees will advance to a higher vacation tier next year."""
        milestone_years = [2, 5, 10]  # Years where tier changes
        advances = 0
        jan_1_next = date(next_year, 1, 1)

        for user in users:
            if not user.hire_date:
                continue

            current_years = (date.today() - user.hire_date).days // 365
            next_years = (jan_1_next - user.hire_date).days // 365

            for milestone in milestone_years:
                if current_years < milestone <= next_years:
                    advances += 1
                    break

        return advances

    def _generate_year_over_year(self, year: int) -> Dict:
        """Generate year-over-year comparison if previous year data exists."""
        previous_year = year - 1

        # Check if previous year data exists
        stmt = select(PTOBalance).where(PTOBalance.year == previous_year)
        prev_balances = self.db.execute(stmt).scalars().all()

        if not prev_balances:
            return {
                'has_previous_data': False,
                'message': f'No data available for {previous_year} comparison.',
            }

        stmt = select(PTOBalance).where(PTOBalance.year == year)
        curr_balances = self.db.execute(stmt).scalars().all()

        if not curr_balances:
            return {
                'has_previous_data': False,
                'message': f'No data available for {year}.',
            }

        # Calculate metrics for both years
        def calc_utilization(balances):
            total_vac = sum(float(b.vacation_total or 0) for b in balances)
            used_vac = sum(float(b.vacation_used or 0) for b in balances)
            total_sick = sum(float(b.sick_total or 0) for b in balances)
            used_sick = sum(float(b.sick_used or 0) for b in balances)
            return {
                'vacation_util': (used_vac / total_vac * 100) if total_vac > 0 else 0,
                'sick_util': (used_sick / total_sick * 100) if total_sick > 0 else 0,
                'employee_count': len(balances),
            }

        prev_metrics = calc_utilization(prev_balances)
        curr_metrics = calc_utilization(curr_balances)

        return {
            'has_previous_data': True,
            'previous_year': previous_year,
            'current_year': year,
            'vacation_utilization_change': round(curr_metrics['vacation_util'] - prev_metrics['vacation_util'], 1),
            'sick_utilization_change': round(curr_metrics['sick_util'] - prev_metrics['sick_util'], 1),
            'employee_count_change': curr_metrics['employee_count'] - prev_metrics['employee_count'],
            'previous_vacation_util': round(prev_metrics['vacation_util'], 1),
            'current_vacation_util': round(curr_metrics['vacation_util'], 1),
            'previous_sick_util': round(prev_metrics['sick_util'], 1),
            'current_sick_util': round(curr_metrics['sick_util'], 1),
        }

    def format_report_as_html(self, report: Dict) -> str:
        """Format the report as HTML for email or display."""
        meta = report['meta']
        summary = report['executive_summary']
        utilization = report['utilization_analysis']
        departments = report['department_comparison']
        carryover = report['carryover_summary']
        burnout = report['burnout_risk']
        compliance = report['policy_compliance']
        projections = report['new_year_projections']
        yoy = report['year_over_year']

        html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, {PTO_GOLD}, #d4a84b); padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h1 style="color: white; margin: 0;">PTO Central - End of Year Assessment Report</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">{meta['year']} | {meta['report_type']}</p>
                <p style="color: rgba(255,255,255,0.7); margin: 5px 0 0 0; font-size: 12px;">Generated: {meta['generated_at_formatted']}</p>
            </div>

            <!-- Executive Summary -->
            <div style="background: #1f2937; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid {PTO_GOLD};">
                <h2 style="color: {PTO_GOLD}; margin-top: 0;">Executive Summary</h2>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="background: #374151; padding: 15px; border-radius: 8px; text-align: center; min-width: 120px;">
                        <div style="font-size: 36px; font-weight: bold; color: #22c55e;">{summary['health_score']}</div>
                        <div style="color: #9ca3af; font-size: 12px;">Health Score</div>
                        <div style="color: #22c55e; font-size: 14px;">{summary['health_grade']}</div>
                    </div>
                    <div style="background: #374151; padding: 15px; border-radius: 8px; text-align: center; min-width: 120px;">
                        <div style="font-size: 36px; font-weight: bold; color: #3b82f6;">{summary.get('vacation_utilization', 0)}%</div>
                        <div style="color: #9ca3af; font-size: 12px;">Vacation Used</div>
                    </div>
                    <div style="background: #374151; padding: 15px; border-radius: 8px; text-align: center; min-width: 120px;">
                        <div style="font-size: 36px; font-weight: bold; color: #22c55e;">{summary.get('sick_utilization', 0)}%</div>
                        <div style="color: #9ca3af; font-size: 12px;">Sick Used</div>
                    </div>
                    <div style="background: #374151; padding: 15px; border-radius: 8px; text-align: center; min-width: 120px;">
                        <div style="font-size: 36px; font-weight: bold; color: #a855f7;">{summary.get('personal_utilization', 0)}%</div>
                        <div style="color: #9ca3af; font-size: 12px;">Personal Used</div>
                    </div>
                </div>

                <h3 style="color: white; margin-top: 20px;">Key Observations</h3>
                <ul style="color: #d1d5db;">
                    {''.join(f'<li>{obs}</li>' for obs in summary['key_observations'])}
                </ul>

                {'<h3 style="color: white;">Recommendations</h3><ul style="color: #d1d5db;">' + ''.join(f'<li>{rec}</li>' for rec in summary['recommendations']) + '</ul>' if summary['recommendations'] else ''}
            </div>

            <!-- Utilization Analysis -->
            <div style="background: #1f2937; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #3b82f6;">
                <h2 style="color: #3b82f6; margin-top: 0;">Utilization Analysis</h2>
                <table style="width: 100%; color: white; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #374151;">
                        <th style="text-align: left; padding: 10px;">Leave Type</th>
                        <th style="text-align: right; padding: 10px;">Allocated (Days)</th>
                        <th style="text-align: right; padding: 10px;">Used (Days)</th>
                        <th style="text-align: right; padding: 10px;">Unused (Days)</th>
                        <th style="text-align: right; padding: 10px;">Utilization</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px;">Vacation</td>
                        <td style="text-align: right; padding: 10px;">{utilization['vacation'].get('total_allocated_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['vacation'].get('total_used_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['vacation'].get('total_unused_days', 0)}</td>
                        <td style="text-align: right; padding: 10px; color: #3b82f6;">{utilization['vacation'].get('utilization_rate', 0)}%</td>
                    </tr>
                    <tr style="background: #374151;">
                        <td style="padding: 10px;">Sick</td>
                        <td style="text-align: right; padding: 10px;">{utilization['sick'].get('total_allocated_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['sick'].get('total_used_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['sick'].get('total_unused_days', 0)}</td>
                        <td style="text-align: right; padding: 10px; color: #22c55e;">{utilization['sick'].get('utilization_rate', 0)}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px;">Personal</td>
                        <td style="text-align: right; padding: 10px;">{utilization['personal'].get('total_allocated_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['personal'].get('total_used_days', 0)}</td>
                        <td style="text-align: right; padding: 10px;">{utilization['personal'].get('total_unused_days', 0)}</td>
                        <td style="text-align: right; padding: 10px; color: #a855f7;">{utilization['personal'].get('utilization_rate', 0)}%</td>
                    </tr>
                </table>
            </div>

            <!-- Burnout Risk -->
            <div style="background: #1f2937; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <h2 style="color: #f59e0b; margin-top: 0;">Employee Wellness Insights</h2>
                <p style="color: #9ca3af; font-size: 14px;">{burnout['summary_message']}</p>
                {'<p style="color: #f59e0b; font-size: 14px;">Employees with ' + str(burnout['threshold_percentage']) + '%+ unused vacation:</p>' if burnout['total_at_risk'] > 0 else ''}
                <ul style="color: #d1d5db;">
                    {''.join(f"<li><strong>{emp['employee_name']}</strong> ({emp['department']}) - {emp['gentle_note']}</li>" for emp in burnout['employees'][:10])}
                </ul>
                {f'<p style="color: #9ca3af; font-size: 12px;">...and {burnout["total_at_risk"] - 10} more</p>' if burnout['total_at_risk'] > 10 else ''}
            </div>

            <!-- Carryover Summary -->
            <div style="background: #1f2937; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #a855f7;">
                <h2 style="color: #a855f7; margin-top: 0;">Carryover Summary</h2>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="background: #374151; padding: 15px; border-radius: 8px; min-width: 150px;">
                        <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{carryover['approved_requests']}</div>
                        <div style="color: #9ca3af; font-size: 12px;">Vacation Carryovers Approved</div>
                    </div>
                    <div style="background: #374151; padding: 15px; border-radius: 8px; min-width: 150px;">
                        <div style="font-size: 24px; font-weight: bold; color: #3b82f6;">{carryover['sick_auto_carryover_hours']} hrs</div>
                        <div style="color: #9ca3af; font-size: 12px;">Sick Leave Auto-Carried</div>
                    </div>
                    <div style="background: #374151; padding: 15px; border-radius: 8px; min-width: 150px;">
                        <div style="font-size: 24px; font-weight: bold; color: #14b8a6;">{carryover['chicago_auto_carryover_hours']} hrs</div>
                        <div style="color: #9ca3af; font-size: 12px;">Chicago Leave Carried</div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
                <p>PTO Central - Haventech Solutions</p>
                <p>This report is confidential and intended for management use only.</p>
            </div>
        </div>
        '''
        return html
