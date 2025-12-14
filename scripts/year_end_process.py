#!/usr/bin/env python3
"""
Year-end processing script for TJM Time Calendar.

Run this script at the start of each new year to:
1. Create PTO balances for all active employees
2. Apply approved carryover from previous year
3. Generate federal holidays for the new year

Usage:
    python scripts/year_end_process.py                    # Process current year
    python scripts/year_end_process.py --year 2026        # Process specific year
    python scripts/year_end_process.py --status           # Check status only
    python scripts/year_end_process.py --dry-run          # Preview without changes
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from src.database import get_db
from src.services.year_end_service import YearEndService
from src.logging_config import setup_logging

setup_logging()


def main():
    parser = argparse.ArgumentParser(
        description="Year-end processing for TJM Time Calendar"
    )
    parser.add_argument(
        '--year', '-y',
        type=int,
        default=datetime.now().year,
        help=f"Year to process (default: {datetime.now().year})"
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help="Check status only, don't process"
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Preview changes without applying them"
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help="Force processing even if already complete"
    )

    args = parser.parse_args()

    db = next(get_db())
    service = YearEndService(db)

    print("=" * 60)
    print(f"TJM Time Calendar - Year-End Processing")
    print(f"Target Year: {args.year}")
    print("=" * 60)

    # Check current status
    status = service.get_year_end_status(args.year)

    print(f"\nCurrent Status for {args.year}:")
    print(f"  Active Employees: {status['active_users']}")
    print(f"  Balances Created: {status['balances_created']}")
    print(f"  Balances Complete: {'Yes' if status['balances_complete'] else 'No'}")
    print(f"  Pending Carryovers: {status['pending_carryovers']}")
    print(f"  Approved Carryovers: {status['approved_carryovers']}")
    print(f"  Holidays Created: {status['holidays_created']}")
    print(f"  Ready for Transition: {'Yes' if status['ready_for_transition'] else 'No'}")

    if args.status:
        db.close()
        return

    if status['pending_carryovers'] > 0:
        print(f"\n⚠️  WARNING: {status['pending_carryovers']} carryover requests are still pending!")
        print("   These should be approved or denied before year-end processing.")
        if not args.force:
            print("   Use --force to process anyway.")
            db.close()
            return

    if status['balances_complete'] and status['holidays_created'] > 0 and not args.force:
        print(f"\n✓ Year-end processing appears complete for {args.year}.")
        print("  Use --force to re-run anyway.")
        db.close()
        return

    if args.dry_run:
        print("\n[DRY RUN] Would perform the following actions:")
        print(f"  - Create balances for {status['active_users'] - status['balances_created']} employees")
        print(f"  - Apply {status['approved_carryovers']} approved carryovers")
        print(f"  - Generate federal holidays for {args.year}")
        db.close()
        return

    # Confirm before processing
    print(f"\nReady to process year-end transition to {args.year}.")
    confirm = input("Continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("Cancelled.")
        db.close()
        return

    print("\nProcessing...")
    results = service.process_year_transition(args.year)

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"  Balances Created: {results['balances_created']}")
    print(f"  Carryovers Applied: {results['carryovers_applied']}")
    print(f"  Holidays Created: {results['holidays_created']}")

    if results['errors']:
        print(f"\n  Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"    - {error}")
    else:
        print("\n✓ Year-end processing completed successfully!")

    db.close()


if __name__ == '__main__':
    main()
