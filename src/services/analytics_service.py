"""
Analytics service for PTO usage trends and insights.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, select

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating PTO analytics and insights."""

    def __init__(self, db: Session):
        self.db = db

    def get_company_overview(self, year: int, department_id: Optional[int] = None) -> Dict:
        """
        Get PTO overview for a year, optionally filtered by department.

        Args:
            year: Year to analyze
            department_id: Optional department filter (for managers)

        Returns:
            Dict with total requests, approved, denied, pending counts
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        # Build base conditions for the year
        base_conditions = [extract('year', PTORequest.start_date) == year]
        if user_ids is not None:
            base_conditions.append(PTORequest.user_id.in_(user_ids))

        # Total requests for the year
        stmt = select(func.count()).select_from(PTORequest).where(*base_conditions)
        total = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(PTORequest).where(*base_conditions, PTORequest.status == 'approved')
        approved = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(PTORequest).where(*base_conditions, PTORequest.status == 'denied')
        denied = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(PTORequest).where(*base_conditions, PTORequest.status == 'pending')
        pending = self.db.execute(stmt).scalar()

        stmt = select(func.count()).select_from(PTORequest).where(*base_conditions, PTORequest.status == 'cancelled')
        cancelled = self.db.execute(stmt).scalar()

        # Total days taken
        stmt = select(PTORequest).where(
            extract('year', PTORequest.start_date) == year,
            PTORequest.status == 'approved'
        )
        if user_ids is not None:
            stmt = stmt.where(PTORequest.user_id.in_(user_ids))
        approved_requests = self.db.execute(stmt).scalars().all()
        total_days = sum(float(r.total_days) for r in approved_requests)

        # Active employees
        emp_conditions = [User.is_active == True]
        if department_id:
            emp_conditions.append(User.department_id == department_id)
        stmt = select(func.count()).select_from(User).where(*emp_conditions)
        active_employees = self.db.execute(stmt).scalar()

        # Average days per employee
        avg_days = total_days / active_employees if active_employees > 0 else 0

        return {
            'year': year,
            'total_requests': total,
            'approved': approved,
            'denied': denied,
            'pending': pending,
            'cancelled': cancelled,
            'total_days_taken': int(round(total_days)),  # Whole days only
            'active_employees': active_employees,
            'avg_days_per_employee': int(round(avg_days)),  # Whole days only
            'approval_rate': round((approved / total * 100) if total > 0 else 0, 1)
        }

    def get_monthly_trends(self, year: int, department_id: Optional[int] = None) -> List[Dict]:
        """
        Get monthly PTO trends for a year, optionally filtered by department.

        Args:
            year: Year to analyze
            department_id: Optional department filter (for managers)

        Returns:
            List of monthly data with request counts and days taken
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        monthly_data = []

        for month in range(1, 13):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            # Requests that overlap with this month
            stmt = select(PTORequest).where(
                PTORequest.status == 'approved',
                PTORequest.start_date <= month_end,
                PTORequest.end_date >= month_start
            )
            if user_ids is not None:
                stmt = stmt.where(PTORequest.user_id.in_(user_ids))
            requests = self.db.execute(stmt).scalars().all()

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

        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            extract('year', PTORequest.start_date) == year
        )

        if department_id:
            user_stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(user_stmt).scalars().all()]
            stmt = stmt.where(PTORequest.user_id.in_(user_ids))

        requests = self.db.execute(stmt).scalars().all()

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
                'days': int(round(data['days'])),  # Whole days only
                'percentage': round((data['days'] / total_days * 100) if total_days > 0 else 0, 1)
            })

        return result

    def get_department_comparison(self, year: int, department_id: Optional[int] = None) -> List[Dict]:
        """
        Compare PTO usage across departments.

        Args:
            year: Year to analyze
            department_id: Optional department filter (for managers - shows only their dept)

        Returns:
            List of departments with usage statistics
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User
        from src.models.department import Department

        # If department_id specified, only show that department
        if department_id:
            stmt = select(Department).where(Department.id == department_id)
        else:
            stmt = select(Department)
        departments = self.db.execute(stmt).scalars().all()

        result = []
        for dept in departments:
            # Get users in department
            stmt = select(User).where(
                User.department_id == dept.id,
                User.is_active == True
            )
            users = self.db.execute(stmt).scalars().all()

            if not users:
                continue

            user_ids = [u.id for u in users]

            # Get approved requests
            stmt = select(PTORequest).where(
                PTORequest.user_id.in_(user_ids),
                PTORequest.status == 'approved',
                extract('year', PTORequest.start_date) == year
            )
            requests = self.db.execute(stmt).scalars().all()

            total_days = sum(float(r.total_days) for r in requests)
            avg_days = total_days / len(users) if users else 0

            result.append({
                'department_id': dept.id,
                'department_name': dept.name,
                'employee_count': len(users),
                'total_requests': len(requests),
                'total_days': int(round(total_days)),  # Whole days only
                'avg_days_per_employee': int(round(avg_days))  # Whole days only
            })

        # Sort by average days descending
        result.sort(key=lambda x: x['avg_days_per_employee'], reverse=True)

        return result

    def get_top_users_by_pto(self, year: int, limit: int = 10, department_id: Optional[int] = None) -> List[Dict]:
        """
        Get employees with most PTO taken.

        Args:
            year: Year to analyze
            limit: Max number of users to return
            department_id: Optional department filter (for managers)

        Returns:
            List of top users by PTO days
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User
        from src.models.department import Department

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        # Get all approved requests for the year
        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            extract('year', PTORequest.start_date) == year
        )
        if user_ids is not None:
            stmt = stmt.where(PTORequest.user_id.in_(user_ids))
        requests = self.db.execute(stmt).scalars().all()

        # Aggregate by user
        user_days = defaultdict(float)
        for req in requests:
            user_days[req.user_id] += float(req.total_days)

        # Sort and get top N
        sorted_users = sorted(user_days.items(), key=lambda x: x[1], reverse=True)[:limit]

        result = []
        for user_id, days in sorted_users:
            stmt = select(User).where(User.id == user_id)
            user = self.db.execute(stmt).scalar_one_or_none()
            if user:
                dept_name = user.department.name if user.department else 'N/A'
                result.append({
                    'user_id': user_id,
                    'name': f"{user.first_name} {user.last_name}",
                    'department': dept_name,
                    'days_taken': int(round(days))  # Whole days only
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
        stmt = select(User).where(
            User.department_id == department_id,
            User.is_active == True
        )
        users = self.db.execute(stmt).scalars().all()

        if not users:
            return []

        user_ids = [u.id for u in users]
        team_size = len(users)

        # Get approved PTO in date range
        stmt = select(PTORequest).where(
            PTORequest.user_id.in_(user_ids),
            PTORequest.status == 'approved',
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date
        )
        requests = self.db.execute(stmt).scalars().all()

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

        stmt = select(PTORequest).where(PTORequest.status == 'pending')
        pending = self.db.execute(stmt).scalars().all()

        # Group by department
        dept_counts = defaultdict(int)
        for req in pending:
            stmt = select(User).where(User.id == req.user_id)
            user = self.db.execute(stmt).scalar_one_or_none()
            if user and user.department:
                dept_counts[user.department.name] += 1
            else:
                dept_counts['Unassigned'] += 1

        return {
            'total_pending': len(pending),
            'by_department': dict(dept_counts),
            'oldest_request': min((r.submitted_at for r in pending), default=None)
        }

    def get_utilization_rate(self, year: int, department_id: Optional[int] = None) -> Dict:
        """
        Calculate PTO utilization rate (used vs allocated).

        Args:
            year: Year to analyze
            department_id: Optional department filter (for managers)

        Returns:
            Dict with utilization statistics
        """
        from src.models.pto_balance import PTOBalance
        from src.models.user import User

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        stmt = select(PTOBalance).where(PTOBalance.year == year)
        if user_ids is not None:
            stmt = stmt.where(PTOBalance.user_id.in_(user_ids))
        balances = self.db.execute(stmt).scalars().all()

        total_allocated = 0
        total_used = 0
        users_with_balance = 0

        for bal in balances:
            # Check if user is active
            user_conditions = [User.id == bal.user_id, User.is_active == True]
            if department_id:
                user_conditions.append(User.department_id == department_id)
            stmt = select(User).where(*user_conditions)
            user = self.db.execute(stmt).scalar_one_or_none()
            if not user:
                continue

            users_with_balance += 1
            total_allocated += float(bal.vacation_total) + float(bal.personal_total) + float(bal.sick_total)
            total_used += float(bal.vacation_used) + float(bal.personal_used) + float(bal.sick_used)

        utilization_rate = (total_used / total_allocated * 100) if total_allocated > 0 else 0

        return {
            'year': year,
            'total_allocated_days': int(round(total_allocated / 8)),  # Convert hours to days (whole numbers)
            'total_used_days': int(round(total_used / 8)),  # Convert hours to days (whole numbers)
            'utilization_rate': round(utilization_rate, 1),
            'employees_tracked': users_with_balance
        }

    def get_attendance_by_date_range(
        self, start_date: date, end_date: date, department_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Calculate attendance for each day in the range.
        Returns list of dicts with attendance rates.
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Get total active employees
        emp_conditions = [User.is_active == True]
        if department_id:
            emp_conditions.append(User.department_id == department_id)
        stmt = select(func.count()).select_from(User).where(*emp_conditions)
        total_employees = self.db.execute(stmt).scalar()

        if total_employees == 0:
            return []

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(*emp_conditions)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        results = []
        current = start_date

        while current <= end_date:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            # Count approved absences for this date
            absence_conditions = [
                PTORequest.status == 'approved',
                PTORequest.start_date <= current,
                PTORequest.end_date >= current
            ]
            if user_ids is not None:
                absence_conditions.append(PTORequest.user_id.in_(user_ids))
            stmt = select(func.count()).select_from(PTORequest).where(*absence_conditions)
            absent_count = self.db.execute(stmt).scalar()

            present_count = total_employees - absent_count
            attendance_rate = (present_count / total_employees * 100) if total_employees > 0 else 0

            results.append({
                'date': current,
                'total_employees': total_employees,
                'absent_count': absent_count,
                'present_count': present_count,
                'attendance_rate': round(attendance_rate, 1)
            })

            current += timedelta(days=1)

        return results

    def get_carryover_risk_employees(
        self, year: int, days_until_expiry: int = 90,
        min_remaining_pct: float = 50.0, department_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Identify employees at risk of losing PTO due to carryover limits.

        Args:
            year: Year to analyze
            days_until_expiry: Days until year end (or policy expiry)
            min_remaining_pct: Minimum % remaining to be considered at risk
            department_id: Optional department filter
        """
        from src.models.pto_balance import PTOBalance
        from src.models.user import User
        from src.models.department import Department

        results = []

        user_conditions = [User.is_active == True]
        if department_id:
            user_conditions.append(User.department_id == department_id)
        stmt = select(User).where(*user_conditions)
        users = self.db.execute(stmt).scalars().all()

        for user in users:
            stmt = select(PTOBalance).where(
                PTOBalance.user_id == user.id,
                PTOBalance.year == year
            )
            balance = self.db.execute(stmt).scalar_one_or_none()

            if not balance:
                continue

            # Convert hours to days (8 hours = 1 day)
            vacation_remaining = float(balance.vacation_total - balance.vacation_used) / 8
            vacation_total = float(balance.vacation_total) / 8

            if vacation_total == 0:
                continue

            pct_remaining = (vacation_remaining / vacation_total) * 100

            if pct_remaining >= min_remaining_pct:
                stmt = select(Department).where(Department.id == user.department_id)
                dept = self.db.execute(stmt).scalar_one_or_none()
                dept_name = dept.name if dept else "Unknown"

                # Calculate risk level
                if pct_remaining >= 80 and days_until_expiry <= 60:
                    risk_level = "HIGH"
                elif pct_remaining >= 60 and days_until_expiry <= 90:
                    risk_level = "MEDIUM"
                else:
                    risk_level = "LOW"

                results.append({
                    'user_id': user.id,
                    'name': f"{user.first_name} {user.last_name}",
                    'department': dept_name,
                    'vacation_remaining': int(round(vacation_remaining)),  # Whole days only
                    'vacation_total': int(round(vacation_total)),  # Whole days only
                    'pct_remaining': round(pct_remaining, 1),
                    'days_until_expiry': days_until_expiry,
                    'risk_level': risk_level
                })

        # Sort by risk level then remaining days
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        results.sort(key=lambda x: (risk_order[x['risk_level']], -x['vacation_remaining']))

        return results

    def get_optimal_meeting_dates(
        self, days_ahead: int = 30, min_attendance_pct: float = 85.0,
        max_results: int = 5, department_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Find the best dates for all-hands meetings based on expected attendance.

        Args:
            days_ahead: How many days into the future to search
            min_attendance_pct: Minimum attendance threshold
            max_results: Maximum number of dates to return
            department_id: Optional department filter
        """
        start = date.today()
        end = start + timedelta(days=days_ahead)

        # Get attendance data
        attendance_data = self.get_attendance_by_date_range(start, end, department_id)

        # Filter and sort by attendance rate
        candidates = []
        for day in attendance_data:
            if day['attendance_rate'] >= min_attendance_pct:
                candidates.append({
                    'date': day['date'],
                    'date_str': day['date'].strftime('%B %d, %Y'),
                    'day_of_week': day['date'].strftime('%A'),
                    'expected_attendance': day['attendance_rate'],
                    'absent_count': day['absent_count']
                })

        # Sort by attendance rate descending
        candidates.sort(key=lambda x: -x['expected_attendance'])

        return candidates[:max_results]

    def get_day_of_week_patterns(self, year: int, department_id: Optional[int] = None) -> Dict[str, float]:
        """
        Analyze PTO patterns by day of week.
        Returns average PTO days taken for each weekday.
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        patterns = {day: 0.0 for day in days}

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            extract('year', PTORequest.start_date) == year
        )
        if user_ids is not None:
            stmt = stmt.where(PTORequest.user_id.in_(user_ids))
        requests = self.db.execute(stmt).scalars().all()

        for req in requests:
            current = req.start_date
            while current <= req.end_date:
                if current.weekday() < 5:  # Weekday
                    day_name = days[current.weekday()]
                    patterns[day_name] += 1
                current += timedelta(days=1)

        # Calculate weekly average (divide by ~52 weeks)
        weeks_in_year = 52
        return {day: int(round(patterns[day] / weeks_in_year)) for day in days}  # Whole numbers only

    def get_monthly_pto_by_type(self, year: int, department_id: Optional[int] = None) -> List[Dict]:
        """
        Get monthly PTO breakdown by type (vacation, sick, personal).
        """
        from src.models.pto_request import PTORequest
        from src.models.user import User

        # Get user IDs if department filter is set
        user_ids = None
        if department_id:
            stmt = select(User).where(User.department_id == department_id)
            user_ids = [u.id for u in self.db.execute(stmt).scalars().all()]

        results = []

        for month in range(1, 13):
            stmt = select(PTORequest).where(
                PTORequest.status == 'approved',
                extract('year', PTORequest.start_date) == year,
                extract('month', PTORequest.start_date) == month
            )
            if user_ids is not None:
                stmt = stmt.where(PTORequest.user_id.in_(user_ids))
            requests = self.db.execute(stmt).scalars().all()

            vacation_days = sum(float(r.total_days) for r in requests if r.pto_type.lower() == 'vacation')
            sick_days = sum(float(r.total_days) for r in requests if r.pto_type.lower() == 'sick')
            personal_days = sum(float(r.total_days) for r in requests if r.pto_type.lower() == 'personal')
            other_days = sum(float(r.total_days) for r in requests if r.pto_type.lower() not in ['vacation', 'sick', 'personal'])

            results.append({
                'month': month,
                'month_name': date(year, month, 1).strftime('%B'),
                'vacation_days': int(round(vacation_days)),  # Whole days only
                'sick_days': int(round(sick_days)),  # Whole days only
                'personal_days': int(round(personal_days)),  # Whole days only
                'other_days': int(round(other_days)),  # Whole days only
                'total_days': int(round(vacation_days + sick_days + personal_days + other_days))  # Whole days only
            })

        return results

    def get_department_utilization_rates(self, year: int) -> List[Dict]:
        """
        Get PTO utilization rates for all departments.
        """
        from src.models.pto_balance import PTOBalance
        from src.models.user import User
        from src.models.department import Department

        stmt = select(Department)
        departments = self.db.execute(stmt).scalars().all()
        results = []

        for dept in departments:
            stmt = select(User).where(
                User.department_id == dept.id,
                User.is_active == True
            )
            users = self.db.execute(stmt).scalars().all()

            if not users:
                continue

            total_allocated = 0.0
            total_used = 0.0

            for user in users:
                stmt = select(PTOBalance).where(
                    PTOBalance.user_id == user.id,
                    PTOBalance.year == year
                )
                balance = self.db.execute(stmt).scalar_one_or_none()

                if balance:
                    total_allocated += float(balance.vacation_total + balance.sick_total + balance.personal_total)
                    total_used += float(balance.vacation_used + balance.sick_used + balance.personal_used)

            utilization_rate = (total_used / total_allocated * 100) if total_allocated > 0 else 0

            results.append({
                'department_id': dept.id,
                'department_name': dept.name,
                'employee_count': len(users),
                'total_allocated': int(round(total_allocated / 8)),  # Convert hours to days
                'total_used': int(round(total_used / 8)),  # Convert hours to days
                'utilization_rate': round(utilization_rate, 1)
            })

        # Sort by utilization rate descending
        results.sort(key=lambda x: x['utilization_rate'], reverse=True)
        return results

    def generate_recommendations(self, year: int, department_id: Optional[int] = None) -> List[Dict]:
        """
        Analyze data and generate actionable recommendations.
        """
        recommendations = []
        days_until_year_end = (date(year, 12, 31) - date.today()).days

        # Check carryover risk
        carryover_risk = self.get_carryover_risk_employees(year, days_until_year_end, department_id=department_id)
        high_risk = [e for e in carryover_risk if e['risk_level'] == "HIGH"]
        if high_risk:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Carryover Risk',
                'title': f'{len(high_risk)} employees at high carryover risk',
                'action': 'Send reminder emails to use PTO before year-end',
                'affected': [e['name'] for e in high_risk[:5]]
            })

        # Check department utilization
        dept_util = self.get_department_utilization_rates(year)
        low_util_depts = [d for d in dept_util if d['utilization_rate'] < 50]
        if low_util_depts:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Work-Life Balance',
                'title': f'{len(low_util_depts)} departments with low PTO utilization',
                'action': 'Consider manager outreach to encourage time off',
                'affected': [d['department_name'] for d in low_util_depts]
            })

        # Check coverage gaps
        gaps = self.get_coverage_gaps(department_id, date.today(), date.today() + timedelta(days=14), 0.4) if department_id else []
        if gaps:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Coverage',
                'title': f'{len(gaps)} days with potential coverage gaps',
                'action': 'Arrange backup coverage or hold pending approvals',
                'affected': [f"{g['date_str']} ({g['absence_rate']}% out)" for g in gaps[:3]]
            })

        # Optimal meeting date suggestion
        optimal = self.get_optimal_meeting_dates(days_ahead=30, department_id=department_id)
        if optimal:
            recommendations.append({
                'priority': 'INFO',
                'category': 'Scheduling',
                'title': f'Best all-hands date: {optimal[0]["date_str"]}',
                'action': f'Schedule meetings for {optimal[0]["expected_attendance"]:.0f}% expected attendance',
                'affected': []
            })

        return recommendations

    def get_department_employee_pto_details(self, department_id: int, year: int) -> List[Dict]:
        """
        Get detailed PTO breakdown for all employees in a department.

        Args:
            department_id: Department to get employees for
            year: Year for PTO balances

        Returns:
            List of employee dicts with PTO details
        """
        from src.models.pto_balance import PTOBalance
        from src.models.user import User

        # Get active employees in department
        stmt = select(User).where(
            User.department_id == department_id,
            User.is_active == True
        ).order_by(User.last_name, User.first_name)
        employees = self.db.execute(stmt).scalars().all()

        results = []
        for emp in employees:
            # Get balance for year
            stmt = select(PTOBalance).where(
                PTOBalance.user_id == emp.id,
                PTOBalance.year == year
            )
            balance = self.db.execute(stmt).scalar_one_or_none()

            if balance:
                # Convert hours to days (divide by 8)
                vacation_total = int(round(float(balance.vacation_total) / 8))
                vacation_used = int(round(float(balance.vacation_used) / 8))
                vacation_pending = int(round(float(balance.vacation_pending) / 8))
                vacation_remaining = vacation_total - vacation_used - vacation_pending

                sick_total = int(round(float(balance.sick_total) / 8))
                sick_used = int(round(float(balance.sick_used) / 8))
                sick_remaining = sick_total - sick_used

                personal_total = int(round(float(balance.personal_total) / 8))
                personal_used = int(round(float(balance.personal_used) / 8))
                personal_remaining = personal_total - personal_used

                total_allocated = vacation_total + sick_total + personal_total
                total_used = vacation_used + sick_used + personal_used
                total_remaining = total_allocated - total_used - vacation_pending
            else:
                vacation_total = vacation_used = vacation_pending = vacation_remaining = 0
                sick_total = sick_used = sick_remaining = 0
                personal_total = personal_used = personal_remaining = 0
                total_allocated = total_used = total_remaining = 0

            results.append({
                'user_id': emp.id,
                'name': f"{emp.first_name} {emp.last_name}",
                'email': emp.email,
                'hire_date': emp.hire_date,
                'vacation': {
                    'total': vacation_total,
                    'used': vacation_used,
                    'pending': vacation_pending,
                    'remaining': vacation_remaining
                },
                'sick': {
                    'total': sick_total,
                    'used': sick_used,
                    'remaining': sick_remaining
                },
                'personal': {
                    'total': personal_total,
                    'used': personal_used,
                    'remaining': personal_remaining
                },
                'totals': {
                    'allocated': total_allocated,
                    'used': total_used,
                    'remaining': total_remaining
                }
            })

        return results
