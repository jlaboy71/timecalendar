# TJM Time Calendar - 2025 Historical PTO Data Migration

## Overview

This document provides complete instructions for migrating 2025 historical PTO data into the TJM Time Calendar system. This includes creating user accounts and importing 104 PTO events with automatic approval (since this is historical data).

---

## PHASE 1: User Account Creation

### Employee Data

Create the following 7 user accounts in the Technology department:

| First Name | Last Name | Username  | Email            | Hire Date  | Role     | State    | City    | Remote Day |
|------------|-----------|-----------|------------------|------------|----------|----------|---------|------------|
| Jose       | Laboy     | jlaboy    | jose@tjmit.com   | 2006-01-30 | manager  | Illinois | Chicago | Friday     |
| Daryn      | Obrien    | dobrien   | daryn@tjmit.com  | 2008-10-15 | employee | Illinois | Chicago | Friday     |
| Johnny     | Laluz     | jlaluz    | johnny@tjmit.com | 2005-06-15 | employee | Illinois | Chicago | Wednesday  |
| Omil       | Andujar   | oandujar  | omil@tjmit.com   | 2013-11-04 | employee | Illinois | Chicago | Monday     |
| Brad       | Garrett   | bgarrett  | Brad@tjmit.com   | 2021-12-20 | employee | Illinois | Chicago | Thursday   |
| Miguel     | Zavala    | mzavala   | miguel@tjmit.com | 2022-10-31 | employee | Illinois | Chicago | Tuesday    |
| Matt       | Weisbaum  | mweisbaum | matt@tjmit.com   | 2023-09-01 | employee | Illinois | Chicago | Wednesday  |

### Vacation Tier Calculations (as of Jan 1, 2025)

Based on the Haventech Handbook vacation policy and years of service:

| Employee | Hire Date  | Years of Service (as of 2025) | Vacation Days/Year |
|----------|------------|-------------------------------|-------------------|
| Johnny   | 2005-06-15 | 19+ years                     | 20 days           |
| Jose     | 2006-01-30 | 18+ years                     | 20 days           |
| Daryn    | 2008-10-15 | 16+ years                     | 20 days           |
| Omil     | 2013-11-04 | 11+ years                     | 20 days           |
| Brad     | 2021-12-20 | 3+ years                      | 10 days           |
| Miguel   | 2022-10-31 | 2+ years                      | 10 days           |
| Matt     | 2023-09-01 | 1+ years                      | 10 days           |

### Standard Allocations (per Haventech Handbook)
- Sick Days: 5 days/year (all employees)
- Personal Days: 2 days/year (all employees)

### Implementation Steps

1. **Create Technology Department** (if not exists)
   - Name: "Technology"
   - Manager: Jose Laboy (assign after user creation)

2. **Create Admin/Superadmin Account First**
   - This is needed to run the migration script
   - May already exist in system

3. **Create Users via Service Layer**
   ```python
   # Example structure - adapt to your UserService
   user_data = {
       'username': 'jlaboy',
       'email': 'jose@tjmit.com',
       'first_name': 'Jose',
       'last_name': 'Laboy',
       'role': 'manager',
       'department_id': <technology_dept_id>,
       'hire_date': date(2006, 1, 30),
       'location_state': 'Illinois',
       'location_city': 'Chicago',
       'is_active': True
   }
   ```

4. **Set Passwords**
   - Default password: `2ez4me!!` (hash before storing)
   - Recommend forcing password change on first login

5. **Create 2025 PTO Balances**
   - Run year-end processing or manually create PTOBalance records
   - Set vacation_total based on tier calculations above
   - Set sick_total = 5 days, personal_total = 2 days

---

## PHASE 2: PTO Event Import

### Leave Type Mapping

The Excel data uses informal naming conventions. Map as follows:

| Excel Reason    | System pto_type | Notes                              |
|-----------------|-----------------|-----------------------------------|
| Vacation        | vacation        | Standard vacation days            |
| Half Day        | vacation        | Half vacation day (0.5 days)      |
| Sick Day        | sick            | Full sick day                     |
| 1/2 Sick        | sick            | Half sick day (0.5 days)          |
| Sick/Half       | sick            | Half sick day (0.5 days)          |
| Personal Day    | personal        | Personal day                      |
| Other           | personal        | Treat as personal (e.g., chaperone)|

### Owner Name Mapping

Map Excel "Owner" names to system usernames:

| Excel Owner      | System Username |
|------------------|-----------------|
| Jose M. Laboy    | jlaboy          |
| Daryn O'Brien    | dobrien         |
| Johnny La Luz    | jlaluz          |
| Omil Andujar     | oandujar        |
| Brad Garrett     | bgarrett        |
| Miguel Zavala    | mzavala         |
| Matthew Weisbaum | mweisbaum       |

### Complete PTO Events Data (104 Records)

```python
# PTO Events to Import
# Format: (name, owner_username, pto_type, start_date, end_date, notes, total_days)

PTO_EVENTS = [
    # Omil Andujar (7 events, 22 days total)
    ("Omil V-Day", "oandujar", "vacation", "2025-12-01", "2025-12-05", None, 5.0),
    ("Omil Half Day", "oandujar", "vacation", "2025-06-10", "2025-06-10", None, 0.5),  # Half day
    ("Omil V-Day 8-13", "oandujar", "vacation", "2025-06-11", "2025-06-18", None, 6.0),
    ("Omil V-Day 1-7", "oandujar", "vacation", "2025-01-30", "2025-02-07", None, 7.0),
    ("Omil S-Day 1", "oandujar", "sick", "2025-03-11", "2025-03-11", None, 1.0),
    ("Omil S-Day 2", "oandujar", "sick", "2025-05-06", "2025-05-06", None, 1.0),
    ("Omil S-Day", "oandujar", "sick", "2025-08-07", "2025-08-07", None, 1.0),

    # Jose M. Laboy (11 events, 22 days total)
    ("Jose V-Day 1", "jlaboy", "vacation", "2025-01-17", "2025-01-17", None, 1.0),
    ("Jose V-Day 2", "jlaboy", "vacation", "2025-02-14", "2025-02-14", None, 1.0),
    ("Jose V-Day 3", "jlaboy", "vacation", "2025-04-04", "2025-04-04", None, 1.0),
    ("Jose V-Day 4", "jlaboy", "vacation", "2025-05-22", "2025-05-26", "Tuscon Arizona", 3.0),
    ("Jose V-Day 5", "jlaboy", "vacation", "2025-07-03", "2025-07-03", None, 1.0),
    ("Jose V-Day 6-11", "jlaboy", "vacation", "2025-08-01", "2025-08-10", "Caribbean Cruise", 6.0),
    ("Jose V-Day 12", "jlaboy", "vacation", "2025-10-16", "2025-10-16", None, 1.0),
    ("Jose - Florida", "jlaboy", "vacation", "2025-10-06", "2025-10-10", "Florida Trip", 5.0),
    ("Jose S-Day 1", "jlaboy", "sick", "2025-01-08", "2025-01-08", "Wife Shoulder Surgery", 1.0),
    ("Jose S-Day 2", "jlaboy", "sick", "2025-09-22", "2025-09-22", None, 1.0),
    ("Jose - 1/2 day", "jlaboy", "personal", "2025-05-05", "2025-05-05", "Chaparone", 0.5),  # Other -> personal

    # Daryn O'Brien (21 events, 28 days total)
    ("Daryn S-Day 1 1/2", "dobrien", "sick", "2025-01-10", "2025-01-10", "PT for surgery", 0.5),
    ("Daryn P-Day 1 1/2", "dobrien", "personal", "2025-01-14", "2025-01-14", "PT for surgery", 0.5),
    ("Daryn S-Day 1 1/2", "dobrien", "sick", "2025-01-21", "2025-01-21", None, 0.5),
    ("Daryn S-Day 2", "dobrien", "sick", "2025-01-28", "2025-01-28", None, 1.0),
    ("Daryn S-Day 3", "dobrien", "sick", "2025-01-29", "2025-01-29", None, 1.0),
    ("Daryn S-Day 4", "dobrien", "sick", "2025-03-24", "2025-03-24", None, 1.0),
    ("Daryn P-day 1 1/2", "dobrien", "personal", "2025-03-27", "2025-03-27", None, 0.5),
    ("Daryn V-Day 1-4", "dobrien", "vacation", "2025-04-01", "2025-04-04", None, 4.0),
    ("Daryn P-Day 2 (1/2)", "dobrien", "personal", "2025-05-05", "2025-05-05", None, 0.5),
    ("Daryn P-Day 2 (1/2)", "dobrien", "personal", "2025-05-15", "2025-05-15", None, 0.5),
    ("Daryn P-Day 3 (1/2)", "dobrien", "personal", "2025-06-04", "2025-06-04", None, 0.5),
    ("Daryn V-Day 5-6", "dobrien", "vacation", "2025-07-02", "2025-07-03", None, 2.0),
    ("Daryn P-day 3 (1/2)", "dobrien", "personal", "2025-07-15", "2025-07-15", None, 0.5),
    ("Daryn V-day 7-9", "dobrien", "vacation", "2025-08-06", "2025-08-08", None, 3.0),
    ("Daryn V-Day 7", "dobrien", "vacation", "2025-10-13", "2025-10-13", None, 1.0),
    ("Daryn V-day 10", "dobrien", "vacation", "2025-11-07", "2025-11-07", None, 1.0),
    ("Daryn V-day 14", "dobrien", "vacation", "2025-11-17", "2025-11-17", None, 1.0),
    ("Daryn V-Day 11", "dobrien", "vacation", "2025-11-28", "2025-11-28", None, 1.0),
    ("Daryn V-Day 15 (1/2)", "dobrien", "vacation", "2025-12-11", "2025-12-11", None, 0.5),
    ("Daryn V-Day 12-13", "dobrien", "vacation", "2025-12-22", "2025-12-23", None, 2.0),
    ("Daryn V-Day 1 (2026)", "dobrien", "vacation", "2026-01-05", "2026-01-05", None, 1.0),

    # Johnny La Luz (12 events, 24 days total)
    ("Johnny V-Day 1-5", "jlaluz", "vacation", "2025-02-08", "2025-02-15", "Mission's Trip to DR", 5.0),
    ("Johnny S-Day 1", "jlaluz", "sick", "2025-02-20", "2025-02-20", None, 1.0),
    ("Johnny V-Day 6-9", "jlaluz", "vacation", "2025-04-11", "2025-04-16", None, 4.0),
    ("Johnny P-Day 1", "jlaluz", "personal", "2025-04-30", "2025-04-30", None, 1.0),
    ("Johnny S-Day 2", "jlaluz", "sick", "2025-05-09", "2025-05-09", None, 1.0),
    ("Johnny V-Day 10-11", "jlaluz", "vacation", "2025-07-21", "2025-07-22", None, 2.0),
    ("Johnny S-Day 3", "jlaluz", "sick", "2025-09-29", "2025-09-29", None, 1.0),
    ("Johnny V-Day 12-13", "jlaluz", "vacation", "2025-12-15", "2025-12-16", None, 2.0),
    ("Johnny V-Day 14-15", "jlaluz", "vacation", "2025-12-18", "2025-12-19", None, 2.0),
    ("Johnny V-Day 16-17", "jlaluz", "vacation", "2025-12-22", "2025-12-23", None, 2.0),
    ("Johnny V-Day 18", "jlaluz", "vacation", "2025-12-26", "2025-12-26", None, 1.0),
    ("Johnny V-Day 19-20", "jlaluz", "vacation", "2025-12-29", "2025-12-30", None, 2.0),

    # Brad Garrett (22 events, 23 days total)
    ("Brad P-Day 1 1/2", "bgarrett", "personal", "2025-01-13", "2025-01-13", "Driving Wife to Airport", 0.5),
    ("Brad S-Day 1 1/2", "bgarrett", "sick", "2025-01-14", "2025-01-14", None, 0.5),
    ("Brad S-Day 1 1/2", "bgarrett", "sick", "2025-01-15", "2025-01-15", None, 0.5),
    ("Brad P-Day 1 1/2", "bgarrett", "personal", "2025-01-16", "2025-01-16", "Picking Wife up from Airport", 0.5),
    ("Brad V-Day 1", "bgarrett", "vacation", "2025-02-14", "2025-02-14", "Kids off School", 1.0),
    ("Brad S-Day 2 1/2", "bgarrett", "sick", "2025-03-18", "2025-03-18", None, 0.5),
    ("Brad V-Day 2", "bgarrett", "vacation", "2025-03-27", "2025-03-27", "Spring Break", 1.0),
    ("Brad V-Day 3", "bgarrett", "vacation", "2025-03-28", "2025-03-28", "Spring Break", 1.0),
    ("Brad V-Day 4", "bgarrett", "vacation", "2025-03-31", "2025-03-31", "Spring Break", 1.0),
    ("Brad S-Day 2 1/2", "bgarrett", "sick", "2025-05-06", "2025-05-06", None, 0.5),
    ("Brad P-Day 2 1/2", "bgarrett", "personal", "2025-05-15", "2025-05-15", "Daughters School Event", 0.5),
    ("Brad P-Day 2 1/2", "bgarrett", "personal", "2025-05-23", "2025-05-23", "Kids Last day of school", 0.5),
    ("Brad S-Day 3", "bgarrett", "sick", "2025-06-11", "2025-06-11", "Taking wife for her Surgery", 1.0),
    ("Brad V-Day 5", "bgarrett", "vacation", "2025-07-18", "2025-07-18", None, 1.0),
    ("Brad V-Day 6", "bgarrett", "vacation", "2025-08-08", "2025-08-08", "Daughters Birthday", 1.0),
    ("Brad S-Day 4", "bgarrett", "sick", "2025-09-03", "2025-09-03", None, 1.0),
    ("Brad S-Day 5", "bgarrett", "sick", "2025-09-29", "2025-09-29", None, 1.0),
    ("Brad V-Day 7", "bgarrett", "vacation", "2025-10-24", "2025-10-24", "Kids off School", 1.0),
    ("Brad V-Day 8", "bgarrett", "vacation", "2025-11-03", "2025-11-03", None, 1.0),
    ("Brad V-Day 9-10", "bgarrett", "vacation", "2025-11-18", "2025-11-19", None, 2.0),
    ("Brad V-Day 1 (2026)", "bgarrett", "vacation", "2026-01-02", "2026-01-02", None, 1.0),
    ("Brad V-Day 2 (2026)", "bgarrett", "vacation", "2026-01-05", "2026-01-05", None, 1.0),

    # Miguel Zavala (17 events, 18 days total)
    ("Miguel P-Day 1-2", "mzavala", "personal", "2025-03-06", "2025-03-07", None, 2.0),
    ("Miguel S-Day 1", "mzavala", "sick", "2025-03-28", "2025-03-28", None, 1.0),
    ("Miguel V-Day 1", "mzavala", "vacation", "2025-04-21", "2025-04-21", None, 1.0),
    ("Miguel S-Day 1/2", "mzavala", "sick", "2025-05-08", "2025-05-08", None, 0.5),
    ("Miguel V-Day 2", "mzavala", "vacation", "2025-06-20", "2025-06-20", None, 1.0),
    ("Miguel V-Day 3", "mzavala", "vacation", "2025-06-23", "2025-06-23", None, 1.0),
    ("Miguel S-Day 2", "mzavala", "sick", "2025-07-24", "2025-07-24", None, 1.0),
    ("Miguel S-Day 2 1/2", "mzavala", "sick", "2025-10-09", "2025-10-09", None, 0.5),
    ("Miguel S-Day 3", "mzavala", "sick", "2025-10-20", "2025-10-20", None, 0.5),
    ("Miguel S-Day 4", "mzavala", "sick", "2025-10-27", "2025-10-27", None, 1.0),
    ("Miguel V-Day 4", "mzavala", "vacation", "2025-11-24", "2025-11-24", None, 1.0),
    ("Miguel V-Day 9", "mzavala", "vacation", "2025-11-26", "2025-11-26", None, 1.0),
    ("Miguel V-Day 5", "mzavala", "vacation", "2025-11-28", "2025-11-28", None, 1.0),
    ("Miguel V-Day 6", "mzavala", "vacation", "2025-12-26", "2025-12-26", None, 1.0),
    ("Miguel V-Day 7", "mzavala", "vacation", "2025-12-29", "2025-12-29", None, 1.0),
    ("Miguel V-Day 8", "mzavala", "vacation", "2025-12-31", "2025-12-31", None, 1.0),
    ("Miguel V-Day 10 (2026)", "mzavala", "vacation", "2026-01-02", "2026-01-02", None, 1.0),

    # Matthew Weisbaum (14 events, 19 days total)
    ("Matt S-Day 1 1/2", "mweisbaum", "sick", "2025-03-31", "2025-03-31", None, 0.5),
    ("Matt V-Day 1", "mweisbaum", "vacation", "2025-05-30", "2025-05-30", None, 1.0),
    ("Matt S-Day 1 2/2", "mweisbaum", "sick", "2025-06-04", "2025-06-04", None, 0.5),
    ("Matt S-Day 2 1/2", "mweisbaum", "sick", "2025-07-07", "2025-07-07", None, 0.5),
    ("Matt S-Day 2 2/2", "mweisbaum", "sick", "2025-07-14", "2025-07-14", None, 0.5),
    ("Matt S-Day 3 1/2", "mweisbaum", "sick", "2025-07-21", "2025-07-21", None, 0.5),
    ("Matt S-Day 3 2/2", "mweisbaum", "sick", "2025-08-21", "2025-08-21", None, 0.5),
    ("Matt V-Day 2", "mweisbaum", "vacation", "2025-09-02", "2025-09-02", None, 1.0),
    ("Matt S-Day 4", "mweisbaum", "sick", "2025-09-23", "2025-09-23", None, 1.0),
    ("Matt St Croix", "mweisbaum", "personal", "2025-11-06", "2025-11-07", None, 2.0),
    ("Matt V-Day 3", "mweisbaum", "vacation", "2025-11-10", "2025-11-10", None, 1.0),
    ("Matt V-Day 8-9", "mweisbaum", "vacation", "2025-12-08", "2025-12-09", None, 2.0),
    ("Matt V-Day 4-7", "mweisbaum", "vacation", "2025-12-22", "2025-12-26", None, 5.0),
]
```

### Auto-Approval Logic

Since this is historical data, all PTO requests should be automatically approved:

1. **For Manager (Jose)**: Manager requests auto-approve per system rules
2. **For Employees**: Set status to 'approved' directly, skip pending workflow
3. **Set approved_by**: Use Jose (manager) or system admin user ID
4. **Set approved_at**: Use the start_date of the request (or import timestamp)
5. **Update Balances**: Move hours directly to `_used` columns, skip `_pending`

### Implementation Script Structure

```python
"""
2025 PTO Historical Data Migration Script
Run from project root: python migrate_2025_pto.py
"""
from datetime import date, datetime
from decimal import Decimal
from src.database import get_db
from src.models.user import User
from src.models.department import Department
from src.models.pto_request import PTORequest
from src.models.pto_balance import PTOBalance
from src.services.balance_service import BalanceService
from src.services.user_service import UserService
from sqlalchemy import select

# Owner name to username mapping
OWNER_MAP = {
    "Jose M. Laboy": "jlaboy",
    "Daryn O'Brien": "dobrien",
    "Johnny La Luz": "jlaluz",
    "Omil Andujar": "oandujar",
    "Brad Garrett": "bgarrett",
    "Miguel Zavala": "mzavala",
    "Matthew Weisbaum": "mweisbaum",
}

def migrate_users(db):
    """Create all user accounts"""
    # Implementation here
    pass

def migrate_pto_events(db, manager_id):
    """Import PTO events with auto-approval"""
    for event in PTO_EVENTS:
        name, username, pto_type, start, end, notes, days = event
        
        # Get user
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        
        if not user:
            print(f"WARNING: User {username} not found, skipping {name}")
            continue
        
        # Determine year for balance
        start_date = date.fromisoformat(start)
        year = start_date.year
        
        # Create approved PTO request
        request = PTORequest(
            user_id=user.id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=date.fromisoformat(end),
            total_days=Decimal(str(days)),
            status='approved',  # Historical = approved
            submitted_at=datetime.now(),
            approved_at=datetime.now(),
            approved_by=manager_id,
            notes=notes
        )
        db.add(request)
        
        # Update balance (add to used, not pending)
        balance_service = BalanceService(db)
        balance = balance_service.get_or_create_balance(user.id, year)
        
        if pto_type == 'vacation':
            balance.vacation_used += Decimal(str(days))
        elif pto_type == 'sick':
            balance.sick_used += Decimal(str(days))
        elif pto_type == 'personal':
            balance.personal_used += Decimal(str(days))
    
    db.commit()

if __name__ == "__main__":
    db = next(get_db())
    try:
        # Run migrations
        migrate_users(db)
        manager = db.execute(
            select(User).where(User.username == 'jlaboy')
        ).scalar_one()
        migrate_pto_events(db, manager.id)
        print("Migration complete!")
    finally:
        db.close()
```

---

## PHASE 3: Validation Checklist

After migration, verify:

### User Accounts
- [ ] All 7 users created
- [ ] Jose has manager role
- [ ] All others have employee role
- [ ] All in Technology department
- [ ] Hire dates correct
- [ ] Remote schedules set

### 2025 PTO Balances
- [ ] Johnny, Jose, Daryn, Omil: 20 vacation days allocated
- [ ] Brad, Miguel, Matt: 10 vacation days allocated
- [ ] All: 5 sick days allocated
- [ ] All: 2 personal days allocated

### PTO Events
- [ ] 104 total events imported
- [ ] All events have 'approved' status
- [ ] Balance `_used` columns updated correctly
- [ ] No `_pending` balances (historical = approved)

### Balance Verification by Employee

| Employee | Vacation Used | Sick Used | Personal Used |
|----------|--------------|-----------|---------------|
| Omil     | ~18.5 days   | 3 days    | 0 days        |
| Jose     | ~19 days     | 2 days    | 0.5 days      |
| Daryn    | ~20 days     | ~4.5 days | ~3.5 days     |
| Johnny   | 22 days      | 3 days    | 1 day         |
| Brad     | 12 days      | ~5 days   | ~2 days       |
| Miguel   | 11 days      | ~4.5 days | 2 days        |
| Matt     | 10 days      | ~4.5 days | 2 days        |

---

## PHASE 4: Additional Considerations

### 2026 Events

The data includes some 2026 events:
- Daryn V-Day 1 (2026): 2026-01-05
- Brad V-Day 1-2 (2026): 2026-01-02, 2026-01-05
- Miguel V-Day 10 (2026): 2026-01-02

**Recommendation**: Create 2026 PTOBalance records for users with 2026 events, OR run year-end processing before importing these events.

### Half-Day Tracking

The Excel data shows extensive use of half-days (0.5 days). Ensure your system:
- Supports Decimal/float days in total_days field
- UI displays half-days correctly
- Balance calculations handle fractional days

### Event Naming Convention

The Excel uses a naming convention: `[Name] [Type]-Day [Number] [Optional: 1/2]`

Examples:
- `Jose V-Day 1` = Jose's 1st vacation day
- `Brad S-Day 2 1/2` = Brad's 2nd half sick day
- `Daryn P-Day 2 (1/2)` = Daryn's 2nd half personal day

This convention is useful for tracking but not required in the system. The `name` field in PTORequest can store this for reference.

### Data Quality Notes

1. **Row 42 (Matt S-Day 1/2)**: Has NaT dates - SKIP this record
2. **Duplicate names**: Some events have duplicate display names but different dates (e.g., two "Brad P-Day 1 1/2" entries) - import both
3. **Year mismatch**: Events span Jan 2025 to Jan 2026

---

## Quick Reference Commands

```bash
# Run migration script
cd c:\Users\jlaboy\codelab\projects\TimeCalendar
venv\Scripts\python.exe migrate_2025_pto.py

# Verify in database
venv\Scripts\python.exe -c "
from src.database import get_db
from sqlalchemy import select, func
from src.models.user import User
from src.models.pto_request import PTORequest
db = next(get_db())
print('Users:', db.execute(select(func.count(User.id))).scalar())
print('PTO Requests:', db.execute(select(func.count(PTORequest.id))).scalar())
db.close()
"

# Start application for verification
venv\Scripts\python.exe nicegui_app/main.py
```

---

## Summary

| Phase | Task | Records |
|-------|------|---------|
| 1 | Create Users | 7 |
| 1 | Create Department | 1 |
| 1 | Create 2025 Balances | 7 |
| 2 | Import PTO Events | 103 (skip 1 bad record) |
| 3 | Validation | - |
| 4 | 2026 Setup (optional) | 4 events |

**Total estimated time**: 30-60 minutes with automated scripts
