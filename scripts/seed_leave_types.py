"""
Seed script for leave types based on Haventech handbook.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.models.leave_type import LeaveType


LEAVE_TYPES = [
    {
        "code": "VACATION",
        "name": "Vacation",
        "description": "Paid time off for personal use",
        "category": "accrued",
        "requires_approval": True,
        "requires_documentation": False,
        "deducts_from_balance": True,
        "is_paid": True,
        "sort_order": 1,
    },
    {
        "code": "SICK",
        "name": "Sick Time",
        "description": "Paid time off for illness or medical appointments",
        "category": "accrued",
        "requires_approval": True,
        "requires_documentation": True,  # After 3 consecutive days
        "deducts_from_balance": True,
        "is_paid": True,
        "sort_order": 2,
    },
    {
        "code": "PERSONAL",
        "name": "Personal Day",
        "description": "Paid time off for personal matters (2 days/year)",
        "category": "allocated",
        "requires_approval": True,
        "requires_documentation": False,
        "deducts_from_balance": True,
        "is_paid": True,
        "sort_order": 3,
    },
    {
        "code": "BEREAVEMENT",
        "name": "Bereavement Leave",
        "description": "Time off for death of immediate family member",
        "category": "tracking_only",
        "requires_approval": True,
        "requires_documentation": True,
        "deducts_from_balance": False,
        "is_paid": True,  # 2-3 days paid per handbook
        "sort_order": 4,
    },
    {
        "code": "FMLA",
        "name": "Family & Medical Leave",
        "description": "Unpaid job-protected leave (up to 12 weeks)",
        "category": "tracking_only",
        "requires_approval": True,
        "requires_documentation": True,
        "deducts_from_balance": False,
        "is_paid": False,
        "sort_order": 5,
    },
    {
        "code": "JURY_DUTY",
        "name": "Jury Duty",
        "description": "Time off for jury service",
        "category": "tracking_only",
        "requires_approval": True,
        "requires_documentation": True,
        "deducts_from_balance": False,
        "is_paid": True,  # Per state law
        "sort_order": 6,
    },
    {
        "code": "VOTING",
        "name": "Voting Time",
        "description": "Time off to vote (if work hours don't allow)",
        "category": "tracking_only",
        "requires_approval": True,
        "requires_documentation": False,
        "deducts_from_balance": False,
        "is_paid": True,
        "sort_order": 7,
    },
    {
        "code": "MILITARY",
        "name": "Military Leave",
        "description": "Leave for military service or training",
        "category": "tracking_only",
        "requires_approval": True,
        "requires_documentation": True,
        "deducts_from_balance": False,
        "is_paid": False,
        "sort_order": 8,
    },
]


def seed_leave_types():
    """Insert leave types into database."""
    db = next(get_db())

    for lt_data in LEAVE_TYPES:
        existing = db.query(LeaveType).filter_by(code=lt_data["code"]).first()
        if not existing:
            leave_type = LeaveType(**lt_data)
            db.add(leave_type)
            print(f"Created leave type: {lt_data['code']}")
        else:
            print(f"Leave type exists: {lt_data['code']}")

    db.commit()
    db.close()
    print("\nLeave types seeding complete!")


if __name__ == "__main__":
    seed_leave_types()
