"""
TJM Brokerage Employee Handbook - Time Off Policies
Only verified PTO-related policies are included.
"""

HANDBOOK_CONTENT = """
# TJM Brokerage - Time Off Policies

## Holidays

TJM Brokerage observes the following 10 market holidays:

1. **New Year's Day** - January 1
2. **Martin Luther King Jr. Day** - Third Monday in January
3. **Presidents' Day** - Third Monday in February
4. **Good Friday** - Friday before Easter Sunday
5. **Memorial Day** - Last Monday in May
6. **Juneteenth** - June 19
7. **Independence Day** - July 4
8. **Labor Day** - First Monday in September
9. **Thanksgiving Day** - Fourth Thursday in November
10. **Christmas Day** - December 25

When a holiday falls on a Saturday, it will be observed on the preceding Friday. When a holiday falls on a Sunday, it will be observed on the following Monday.

---

## Vacation Policy

Vacation time is based on years of service:

| Years of Service | Annual Vacation Days | Hours |
|-----------------|---------------------|-------|
| 0-4 years | 10 days | 80 hours |
| 5-9 years | 15 days | 120 hours |
| 10+ years | 20 days | 160 hours |

**Guidelines:**
- Vacation requests should be submitted at least 2 weeks in advance
- Half-day (4 hours) minimum, one-week (40 hours) maximum per request
- Vacation does not carry over to the next year without management approval
- Carryover requests must be in full-day (8-hour) increments

---

## Personal Days

- All employees receive 2 personal days (16 hours) per calendar year
- Personal days do not carry over to the next year
- Request personal days at least 24 hours in advance when possible

---

## Sick Time

**Default Policy:**
- Maximum annual accrual: 40 hours (5 days)
- Maximum carryover: 60 hours
- Minimum increment: 4 hours (half day)

**State-Specific Policies:**

**Chicago, IL:**
- Accrual: 1 hour for every 35 hours worked
- Maximum carryover: 80 hours
- Minimum increment: 2 hours

**New York:**
- Accrual: 1 hour for every 30 hours worked
- Maximum annual accrual: 56 hours (7 days)
- Minimum increment: 4 hours

**New Jersey:**
- Accrual: 1 hour for every 30 hours worked
- Maximum annual accrual: 40 hours (5 days)
- Maximum carryover: 60 hours

**Connecticut:**
- Accrual: 1 hour for every 40 hours worked
- Maximum annual accrual: 40 hours (5 days)
- Maximum carryover: 60 hours

**Usage:**
- May be used for personal illness, medical appointments, or caring for sick family members
- Notify your supervisor as soon as possible when using sick time
- A doctor's note may be required for absences of 3 or more consecutive days

---

## Remote Work

- Employees may request remote work days through the system
- Remote work arrangements require manager approval
- Track remote days used through the Time Calendar system

---

## Other Leave Types

The following leave types are available and do not deduct from PTO balances:

- **Jury Duty** - Full pay for time spent on jury duty
- **Bereavement** - Time off for loss of family members
- **Military Leave** - Per USERRA requirements
- **FMLA** - Family and Medical Leave Act protected leave
- **Voting** - Time off to vote in elections

These leave types require manager approval and appropriate documentation.

---

*For questions about time off policies, contact your manager or HR.*
"""

# Structured sections for the styled viewer
HANDBOOK_SECTIONS = [
    {
        "id": "holidays",
        "title": "Holidays",
        "icon": "celebration",
        "content": """
TJM Brokerage observes **10 market holidays**:

1. New Year's Day - January 1
2. Martin Luther King Jr. Day - Third Monday in January
3. Presidents' Day - Third Monday in February
4. Good Friday - Friday before Easter Sunday
5. Memorial Day - Last Monday in May
6. Juneteenth - June 19
7. Independence Day - July 4
8. Labor Day - First Monday in September
9. Thanksgiving Day - Fourth Thursday in November
10. Christmas Day - December 25

When a holiday falls on Saturday, it's observed Friday. When on Sunday, observed Monday.
        """
    },
    {
        "id": "vacation",
        "title": "Vacation Policy",
        "icon": "beach_access",
        "content": """
Vacation time is based on years of service:

| Years of Service | Annual Days | Hours |
|-----------------|-------------|-------|
| 0-4 years | 10 days | 80 hours |
| 5-9 years | 15 days | 120 hours |
| 10+ years | 20 days | 160 hours |

**Guidelines:**
- Submit requests at least **2 weeks in advance**
- Half-day (4 hours) minimum, one-week (40 hours) maximum per request
- No carryover without management approval
- Carryover must be in full-day (8-hour) increments
        """
    },
    {
        "id": "personal",
        "title": "Personal Days",
        "icon": "person",
        "content": """
All employees receive **2 personal days** (16 hours) per calendar year.

**Rules:**
- Do not carry over to next year
- Request at least 24 hours in advance when possible
        """
    },
    {
        "id": "sick",
        "title": "Sick Time",
        "icon": "medical_services",
        "content": """
**Default Policy:**
- Max annual: 40 hours (5 days)
- Max carryover: 60 hours
- Minimum increment: 4 hours (half day)

**State-Specific Variations:**

**Chicago, IL:** 1 hr/35 hrs worked, 80 hr carryover, 2-hr minimum

**New York:** 1 hr/30 hrs worked, 56 hr max annual

**New Jersey:** 1 hr/30 hrs worked, 40 hr max, 60 hr carryover

**Connecticut:** 1 hr/40 hrs worked, 40 hr max, 60 hr carryover
        """
    },
    {
        "id": "remote",
        "title": "Remote Work",
        "icon": "home_work",
        "content": """
- Employees may request remote work days through the system
- Remote work arrangements require manager approval
- Track remote days used through the Time Calendar system
        """
    },
    {
        "id": "other_leave",
        "title": "Other Leave Types",
        "icon": "event_available",
        "content": """
The following leave types do not deduct from PTO balances:

- **Jury Duty** - Full pay for jury service
- **Bereavement** - Loss of family members
- **Military Leave** - Per USERRA requirements
- **FMLA** - Family and Medical Leave Act
- **Voting** - Time off to vote

These require manager approval and documentation.
        """
    }
]
