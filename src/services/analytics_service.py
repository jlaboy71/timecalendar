"""
Analytics service for PTO usage trends and insights.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating PTO analytics and insights."""

    def __init__(self, db: Session):
        self.db = db

    def get_company_overview(self, year: int) -> Dict:
        """
        Get company-wide PTO overview for a year.

        Returns:
            Dict with total requests, approved, denied, pending counts
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Total requests for the year
        base_query = self.db.query(PTORequest).filter(
            extract('year', PTORequest.start_date) == year
        )

        total = base_query.count()
        approved = base_query.filter(PTORequest.status == 'approved').count()
        denied = base_query.filter(PTORequest.status == 'denied').count()
        pending = base_query.filter(PTORequest.status == 'pending').count()
        cancelled = base_query.filter(PTORequest.status == 'cancelled').count()

        # Total days taken
        approved_requests = base_query.filter(PTORequest.status == 'approved').all()
        total_days = sum(float(r.total_days) for r in approved_requests)

        # Active employees
        active_employees = self.db.query(User).filter(User.is_active == True).count()

        # Average days per employee
        avg_days = total_days / active_employees if active_employees > 0 else 0

        return {
            'year': year,
            'total_requests': total,
            'approved': approved,
            'denied': denied,
            'pending': pending,
            'cancelled': cancelled,
            'total_days_taken': round(total_days, 1),
            'active_employees': active_employees,
            'avg_days_per_employee': round(avg_days, 1),
            'approval_rate': round((approved / total * 100) if total > 0 else 0, 1)
        }

    def get_monthly_trends(self, year: int) -> List[Dict]:
        """
        Get monthly PTO trends for a year.

        Returns:
            List of monthly data with request counts and days taken
        """
        from src.models.pto_request import PTORequest

        monthly_data = []

        for month in range(1, 13):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            # Requests that overlap with this month
            requests = self.db.query(PTORequest).filter(
                PTORequest.status == 'approved',
                PTORequest.start_date <= month_end,
                PTORequest.end_date >= month_start
            ).all()

            # Calculate days actually in this month
            days_in_month = 0
            for req in requests:
                start = max(req.start_date, month_start)
                end = min(req.end_date, month_end)
                days_in_month += (end - start).days + 1

            monthly_data.append({
                'month': month,
                'month_name': month_start.strftime('%B'),
                'month_abbr': month_start.strftime('%b'),
                'request_count': len(requests),
                'days_taken': days_in_month
            })

        return monthly_data

    def get_leave_type_breakdown(self, year: int, department_id: Optional[int] = None) -> List[Dict]:
        """
        Get breakdown of PTO by leave type.

        Returns:
            List of leave types with counts and percentages
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        query = self.db.query(PTORequest).filter(
            PTORequest.status == 'approved',
            extract('year', PTORequest.start_date) == year
        )

        if department_id:
            user_ids = [u.id for u in self.db.query(User).filter(
                User.department_id == department_id
            ).all()]
            query = query.filter(PTORequest.user_id.in_(user_ids))

        requests = query.all()

        # Group by type
        type_data = defaultdict(lambda: {'count': 0, 'days': 0})
        for req in requests:
            pto_type = req.pto_type.lower()
            type_data[pto_type]['count'] += 1
            type_data[pto_type]['days'] += float(req.total_days)

        total_days = sum(d['days'] for d in type_data.values())

        result = []
        for pto_type, data in sorted(type_data.items(), key=lambda x: x[1]['days'], reverse=True):
            result.append({
                'type': pto_type.title(),
                'count': data['count'],
                'days': round(data['days'], 1),
                'percentage': round((data['days'] / total_days * 100) if total_days > 0 else 0, 1)
            })

        return result

    def get_department_comparison(self, year: int) -> List[Dict]:
        """
        Compare PTO usage across departments.

        Returns:
            List of departments with usage statistics
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User
        from src.models.department import Department

        departments = self.db.query(Department).all()

        result = []
        for dept in departments:
            # Get users in department
            users = self.db.query(User).filter(
                User.department_id == dept.id,
                User.is_active == True
            ).all()

            if not users:
                continue

            user_ids = [u.id for u in users]

            # Get approved requests
            requests = self.db.query(PTORequest).filter(
                PTORequest.user_id.in_(user_ids),
                PTORequest.status == 'approved',
                extract('year', PTORequest.start_date) == year
            ).all()

            total_days = sum(float(r.total_days) for r in requests)
            avg_days = total_days / len(users) if users else 0

            result.append({
                'department_id': dept.id,
                'department_name': dept.name,
                'employee_count': len(users),
                'total_requests': len(requests),
                'total_days': round(total_days, 1),
                'avg_days_per_employee': round(avg_days, 1)
            })

        # Sort by average days descending
        result.sort(key=lambda x: x['avg_days_per_employee'], reverse=True)

        return result

    def get_top_users_by_pto(self, year: int, limit: int = 10) -> List[Dict]:
        """
        Get employees with most PTO taken.

        Returns:
            List of top users by PTO days
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User
        from src.models.department import Department

        # Get all approved requests for the year
        requests = self.db.query(PTORequest).filter(
            PTORequest.status == 'approved',
            extract('year', PTORequest.start_date) == year
        ).all()

        # Aggregate by user
        user_days = defaultdict(float)
        for req in requests:
            user_days[req.user_id] += float(req.total_days)

        # Sort and get top N
        sorted_users = sorted(user_days.items(), key=lambda x: x[1], reverse=True)[:limit]

        result = []
        for user_id, days in sorted_users:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                dept_name = user.department.name if user.department else 'N/A'
                result.append({
                    'user_id': user_id,
                    'name': f"{user.first_name} {user.last_name}",
                    'department': dept_name,
                    'days_taken': round(days, 1)
                })

        return result

    def get_coverage_gaps(self, department_id: int, start_date: date, end_date: date, threshold: float = 0.5) -> List[Dict]:
        """
        Identify dates where department coverage may be low.

        Args:
            department_id: Department to analyze
            start_date: Start of date range
            end_date: End of date range
            threshold: Fraction of team out that triggers a gap warning (0.5 = 50%)

        Returns:
            List of dates with potential coverage issues
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Get active users in department
        users = self.db.query(User).filter(
            User.department_id == department_id,
            User.is_active == True
        ).all()

        if not users:
            return []

        user_ids = [u.id for u in users]
        team_size = len(users)

        # Get approved PTO in date range
        requests = self.db.query(PTORequest).filter(
            PTORequest.user_id.in_(user_ids),
            PTORequest.status == 'approved',
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date
        ).all()

        # Build daily absence count
        daily_absences = defaultdict(set)
        for req in requests:
            current = max(req.start_date, start_date)
            end = min(req.end_date, end_date)
            while current <= end:
                # Skip weekends
                if current.weekday() < 5:
                    daily_absences[current].add(req.user_id)
                current += timedelta(days=1)

        # Find gap days
        gaps = []
        for day, absent_users in sorted(daily_absences.items()):
            absence_rate = len(absent_users) / team_size
            if absence_rate >= threshold:
                # Get names of absent users
                absent_names = []
                for uid in absent_users:
                    user = next((u for u in users if u.id == uid), None)
                    if user:
                        absent_names.append(f"{user.first_name} {user.last_name}")

                gaps.append({
                    'date': day,
                    'date_str': day.strftime('%Y-%m-%d'),
                    'day_name': day.strftime('%A'),
                    'absent_count': len(absent_users),
                    'team_size': team_size,
                    'absence_rate': round(absence_rate * 100, 1),
                    'absent_employees': absent_names
                })

        return gaps

    def get_pending_requests_summary(self) -> Dict:
        """
        Get summary of pending requests for managers.

        Returns:
            Dict with pending request counts by department
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User
        from src.models.department import Department

        pending = self.db.query(PTORequest).filter(
            PTORequest.status == 'pending'
        ).all()

        # Group by department
        dept_counts = defaultdict(int)
        for req in pending:
            user = self.db.query(User).filter(User.id == req.user_id).first()
            if user and user.department:
                dept_counts[user.department.name] += 1
            else:
                dept_counts['Unassigned'] += 1

        return {
            'total_pending': len(pending),
            'by_department': dict(dept_counts),
            'oldest_request': min((r.submitted_at for r in pending), default=None)
        }

    def get_utilization_rate(self, year: int) -> Dict:
        """
        Calculate PTO utilization rate (used vs allocated).

        Returns:
            Dict with utilization statistics
        """
        from src.models.pto_balance import PTOBalance
        from src.models.user import User

        balances = self.db.query(PTOBalance).filter(
            PTOBalance.year == year
        ).all()

        total_allocated = 0
        total_used = 0
        users_with_balance = 0

        for bal in balances:
            # Check if user is active
            user = self.db.query(User).filter(User.id == bal.user_id, User.is_active == True).first()
            if not user:
                continue

            users_with_balance += 1
            total_allocated += float(bal.vacation_total) + float(bal.personal_total) + float(bal.sick_total)
            total_used += float(bal.vacation_used) + float(bal.personal_used) + float(bal.sick_used)

        utilization_rate = (total_used / total_allocated * 100) if total_allocated > 0 else 0

        return {
            'year': year,
            'total_allocated_days': round(total_allocated, 1),
            'total_used_days': round(total_used, 1),
            'utilization_rate': round(utilization_rate, 1),
            'employees_tracked': users_with_balance
        }
