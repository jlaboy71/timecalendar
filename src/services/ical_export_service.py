"""
iCal export service for PTO and market holiday calendar export.

Generates .ics files compatible with Outlook, Google Calendar, Apple Calendar, etc.
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from io import BytesIO
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ICalExportService:
    """Service for exporting calendar data to iCal (.ics) format."""

    def __init__(self, db_session=None):
        """Initialize the iCal export service."""
        self._db_session = db_session

    def generate_ical(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        department_id: Optional[int] = None,
        include_holidays: bool = True,
        include_pto: bool = True,
        calendar_name: str = "PTO Central"
    ) -> str:
        """
        Generate iCal content for the specified date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            user_id: If provided, only include PTO for this user
            department_id: If provided, only include PTO for this department
            include_holidays: Whether to include market holidays
            include_pto: Whether to include PTO requests
            calendar_name: Name for the calendar

        Returns:
            iCal formatted string
        """
        events = []

        if include_holidays:
            events.extend(self._get_holiday_events(start_date, end_date))

        if include_pto:
            events.extend(self._get_pto_events(start_date, end_date, user_id, department_id))

        return self._build_ical(events, calendar_name)

    def _get_holiday_events(self, start_date: date, end_date: date) -> List[dict]:
        """Get market holiday events."""
        if not self._db_session:
            return []

        from src.models.market_holiday import MarketHoliday

        stmt = select(MarketHoliday).where(
            MarketHoliday.holiday_date >= start_date,
            MarketHoliday.holiday_date <= end_date
        )
        holidays = self._db_session.execute(stmt).scalars().all()

        # Group by date and name to avoid duplicates
        holiday_map = {}
        for h in holidays:
            key = (h.holiday_date, h.name)
            if key not in holiday_map:
                holiday_map[key] = {
                    'date': h.holiday_date,
                    'name': h.name,
                    'markets': []
                }
            holiday_map[key]['markets'].append(h.market)

        events = []
        for key, data in holiday_map.items():
            markets_str = ', '.join(sorted(data['markets']))
            events.append({
                'uid': f"holiday-{data['date'].isoformat()}-{data['name'].replace(' ', '-').lower()}@tjm.com",
                'summary': f"[HOLIDAY] {data['name']}",
                'description': f"Market Holiday: {data['name']}\\nExchanges Closed: {markets_str}",
                'start_date': data['date'],
                'end_date': data['date'],
                'all_day': True,
                'category': 'HOLIDAY'
            })

        return events

    def _get_pto_events(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[int] = None,
        department_id: Optional[int] = None
    ) -> List[dict]:
        """Get PTO request events."""
        if not self._db_session:
            return []

        from src.models.pto_request import PTORequest
        from src.models.user import User

        stmt = select(PTORequest).where(
            PTORequest.status == 'approved',
            PTORequest.start_date <= end_date,
            PTORequest.end_date >= start_date
        )

        if user_id:
            # Personal calendar: show all requests including private ones
            stmt = stmt.where(PTORequest.user_id == user_id)
        elif department_id:
            # Team/department calendar: exclude private requests for privacy
            user_stmt = select(User).where(
                User.department_id == department_id,
                User.is_active == True
            )
            dept_users = self._db_session.execute(user_stmt).scalars().all()
            dept_user_ids = [u.id for u in dept_users]
            if dept_user_ids:
                stmt = stmt.where(
                    PTORequest.user_id.in_(dept_user_ids),
                    PTORequest.is_private == False  # Exclude private requests from team calendar
                )

        pto_requests = self._db_session.execute(stmt).scalars().all()

        # Get user info
        pto_user_ids = set(p.user_id for p in pto_requests)
        if pto_user_ids:
            user_stmt = select(User).where(User.id.in_(pto_user_ids))
            user_list = self._db_session.execute(user_stmt).scalars().all()
            users = {u.id: u for u in user_list}
        else:
            users = {}

        events = []
        for pto in pto_requests:
            user = users.get(pto.user_id)
            if not user:
                continue

            employee_name = f"{user.first_name} {user.last_name}"
            pto_type = pto.pto_type.title()

            events.append({
                'uid': f"pto-{pto.id}@tjm.com",
                'summary': f"[{pto_type}] {employee_name}",
                'description': f"Employee: {employee_name}\\nType: {pto_type}\\nDays: {pto.total_days}\\nNotes: {pto.notes or 'None'}",
                'start_date': pto.start_date,
                'end_date': pto.end_date,
                'all_day': True,
                'category': pto.pto_type.upper()
            })

        return events

    def _build_ical(self, events: List[dict], calendar_name: str) -> str:
        """Build iCal file content from events."""
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Haventech Solutions//PTO Central//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            f'X-WR-CALNAME:{calendar_name}',
            f'X-WR-TIMEZONE:America/New_York',
        ]

        for event in events:
            # For all-day events, end date should be the day AFTER
            # iCal uses exclusive end dates for all-day events
            end_date = event['end_date'] + timedelta(days=1)

            lines.extend([
                'BEGIN:VEVENT',
                f'UID:{event["uid"]}',
                f'DTSTAMP:{now}',
                f'DTSTART;VALUE=DATE:{event["start_date"].strftime("%Y%m%d")}',
                f'DTEND;VALUE=DATE:{end_date.strftime("%Y%m%d")}',
                f'SUMMARY:{self._escape_ical(event["summary"])}',
                f'DESCRIPTION:{self._escape_ical(event["description"])}',
                f'CATEGORIES:{event["category"]}',
                'TRANSP:TRANSPARENT',
                'END:VEVENT',
            ])

        lines.append('END:VCALENDAR')

        return '\r\n'.join(lines)

    def _escape_ical(self, text: str) -> str:
        """Escape special characters for iCal format."""
        if not text:
            return ''
        # iCal requires escaping of certain characters
        text = text.replace('\\', '\\\\')
        text = text.replace('\n', '\\n')
        text = text.replace(',', '\\,')
        text = text.replace(';', '\\;')
        return text

    def generate_my_calendar(self, user_id: int, year: int) -> str:
        """Generate iCal for a single user's PTO for a year."""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        return self.generate_ical(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            include_holidays=True,
            include_pto=True,
            calendar_name=f"My PTO Calendar {year}"
        )

    def generate_team_calendar(
        self,
        department_id: Optional[int],
        year: int,
        department_name: str = "Team"
    ) -> str:
        """Generate iCal for a department's PTO for a year."""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        return self.generate_ical(
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            include_holidays=True,
            include_pto=True,
            calendar_name=f"{department_name} Calendar {year}"
        )

    def generate_holidays_only(self, year: int) -> str:
        """Generate iCal with only market holidays."""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        return self.generate_ical(
            start_date=start_date,
            end_date=end_date,
            include_holidays=True,
            include_pto=False,
            calendar_name=f"Market Holidays {year}"
        )
