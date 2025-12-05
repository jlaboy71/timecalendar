"""
Seed script for state-specific leave policies based on Haventech handbook.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from decimal import Decimal
from src.database import get_db
from src.models.leave_type import LeaveType
from src.models.leave_policy import LeavePolicy


def seed_leave_policies():
    """Insert leave policies for IL, NY, CT, FL."""
    db = next(get_db())

    # Get leave type IDs
    vacation = db.query(LeaveType).filter_by(code="VACATION").first()
    sick = db.query(LeaveType).filter_by(code="SICK").first()
    personal = db.query(LeaveType).filter_by(code="PERSONAL").first()
    bereavement = db.query(LeaveType).filter_by(code="BEREAVEMENT").first()

    if not all([vacation, sick, personal, bereavement]):
        print("Error: Run seed_leave_types.py first!")
        db.close()
        return

    policies = [
        # ===============================================================
        # VACATION POLICIES (same across all states, tenure-based)
        # ===============================================================
        {
            "leave_type_id": vacation.id,
            "location_state": None,  # Default
            "location_city": None,
            "accrual_period": "monthly",
            "max_carryover_hours": Decimal("0"),  # No carryover without approval
            "waiting_period_days": 0,  # Can use as earned
            "min_increment_hours": Decimal("4"),  # Half day minimum
            "max_increment_hours": Decimal("40"),  # 1 week max
            "advance_notice_days": 14,
            "effective_date": date(2024, 1, 1),
        },
        # Chicago: 16 hours automatic carryover
        {
            "leave_type_id": vacation.id,
            "location_state": "IL",
            "location_city": "Chicago",
            "accrual_period": "monthly",
            "max_carryover_hours": Decimal("16"),  # Chicago ordinance
            "waiting_period_days": 90,  # Per Chicago ordinance
            "min_increment_hours": Decimal("4"),
            "advance_notice_days": 7,  # Chicago: 7 days foreseeable
            "effective_date": date(2024, 7, 1),  # Effective July 1, 2024
        },

        # ===============================================================
        # SICK TIME POLICIES
        # ===============================================================
        # Default (FL uses this)
        {
            "leave_type_id": sick.id,
            "location_state": None,
            "location_city": None,
            "accrual_rate": Decimal("1"),
            "accrual_period": "per_hours_worked",
            "accrual_hours_divisor": 40,  # 1 hr per 40 hrs worked
            "max_annual_hours": Decimal("40"),
            "max_carryover_hours": Decimal("60"),
            "waiting_period_days": 90,
            "min_increment_hours": Decimal("4"),
            "effective_date": date(2024, 1, 1),
        },
        # Chicago (IL)
        {
            "leave_type_id": sick.id,
            "location_state": "IL",
            "location_city": "Chicago",
            "accrual_rate": Decimal("1"),
            "accrual_period": "per_hours_worked",
            "accrual_hours_divisor": 35,  # 1 hr per 35 hrs worked
            "max_annual_hours": Decimal("40"),
            "max_carryover_hours": Decimal("80"),  # Chicago: 80 hrs
            "waiting_period_days": 30,  # Chicago: 30 days
            "min_increment_hours": Decimal("2"),  # Chicago: 2 hr minimum
            "effective_date": date(2024, 7, 1),
        },
        # New York
        {
            "leave_type_id": sick.id,
            "location_state": "NY",
            "location_city": None,
            "accrual_rate": Decimal("1"),
            "accrual_period": "per_hours_worked",
            "accrual_hours_divisor": 30,  # 1 hr per 30 hrs worked
            "max_annual_hours": Decimal("56"),  # NY: 56 hours
            "max_carryover_hours": Decimal("56"),
            "waiting_period_days": 0,  # NY: Immediate use
            "min_increment_hours": Decimal("4"),
            "effective_date": date(2024, 1, 1),
        },
        # Connecticut
        {
            "leave_type_id": sick.id,
            "location_state": "CT",
            "location_city": None,
            "accrual_rate": Decimal("1"),
            "accrual_period": "per_hours_worked",
            "accrual_hours_divisor": 40,  # 1 hr per 40 hrs worked
            "max_annual_hours": Decimal("40"),
            "max_carryover_hours": Decimal("60"),
            "waiting_period_days": 90,
            "min_increment_hours": Decimal("4"),
            "effective_date": date(2024, 1, 1),
        },

        # ===============================================================
        # PERSONAL DAYS (same all locations)
        # ===============================================================
        {
            "leave_type_id": personal.id,
            "location_state": None,
            "location_city": None,
            "max_annual_hours": Decimal("16"),  # 2 days = 16 hours
            "max_carryover_hours": Decimal("0"),  # No carryover
            "waiting_period_days": 90,
            "min_increment_hours": Decimal("8"),  # Full day only
            "effective_date": date(2024, 1, 1),
        },

        # ===============================================================
        # BEREAVEMENT (IL has extended policy)
        # ===============================================================
        {
            "leave_type_id": bereavement.id,
            "location_state": None,
            "location_city": None,
            "max_annual_hours": Decimal("16"),  # 2 days standard
            "effective_date": date(2024, 1, 1),
        },
        {
            "leave_type_id": bereavement.id,
            "location_state": "IL",
            "location_city": None,
            "max_annual_hours": Decimal("80"),  # IL: up to 10 days
            "effective_date": date(2024, 1, 1),
        },
    ]

    for policy_data in policies:
        # Check for existing
        query = db.query(LeavePolicy).filter_by(
            leave_type_id=policy_data["leave_type_id"],
            location_state=policy_data.get("location_state"),
            location_city=policy_data.get("location_city"),
        )
        existing = query.first()

        if not existing:
            policy = LeavePolicy(**policy_data)
            db.add(policy)
            loc = f"{policy_data.get('location_city') or ''}, {policy_data.get('location_state') or 'DEFAULT'}".strip(", ")
            print(f"Created policy: Leave Type {policy_data['leave_type_id']} @ {loc}")
        else:
            print(f"Policy exists: Leave Type {policy_data['leave_type_id']}")

    db.commit()
    db.close()
    print("\nLeave policies seeding complete!")


if __name__ == "__main__":
    seed_leave_policies()
