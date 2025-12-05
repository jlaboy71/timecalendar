"""
Seed script for vacation accrual tiers based on Haventech handbook.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from decimal import Decimal
from src.database import get_db
from src.models.vacation_accrual_tier import VacationAccrualTier


TIERS = [
    {
        "min_years_service": 0,
        "max_years_service": 4,
        "annual_days": Decimal("10"),
        "monthly_accrual_rate": Decimal("0.83"),
        "effective_date": date(2024, 1, 1),
    },
    {
        "min_years_service": 5,
        "max_years_service": 9,
        "annual_days": Decimal("15"),
        "monthly_accrual_rate": Decimal("1.25"),
        "effective_date": date(2024, 1, 1),
    },
    {
        "min_years_service": 10,
        "max_years_service": None,  # No upper limit
        "annual_days": Decimal("20"),
        "monthly_accrual_rate": Decimal("1.67"),
        "effective_date": date(2024, 1, 1),
    },
]


def seed_vacation_tiers():
    """Insert vacation accrual tiers."""
    db = next(get_db())

    for tier_data in TIERS:
        existing = db.query(VacationAccrualTier).filter_by(
            min_years_service=tier_data["min_years_service"]
        ).first()

        if not existing:
            tier = VacationAccrualTier(**tier_data)
            db.add(tier)
            max_yrs = tier_data["max_years_service"] or "+"
            print(f"Created tier: {tier_data['min_years_service']}-{max_yrs} years = {tier_data['annual_days']} days")
        else:
            print(f"Tier exists: {tier_data['min_years_service']}+ years")

    db.commit()
    db.close()
    print("\nVacation tiers seeding complete!")


if __name__ == "__main__":
    seed_vacation_tiers()
