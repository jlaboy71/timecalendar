"""
Haventech LLC Employee Handbook - Time Off Policies
Effective: May 1, 2024
Only verified PTO-related policies are included.
"""

HANDBOOK_CONTENT = """
# Haventech LLC - Time Off Policies
**Effective Date: May 1, 2024**

## Holidays

Haventech observes the following 10 holidays:

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

Employees on paid leaves of absence (e.g., short-term disability) are not eligible for holiday pay.

---

## Vacation Policy

Vacation time is based on years of service:

| Years of Service | Annual Vacation Days | Hours |
|-----------------|---------------------|-------|
| 1-4 years | 10 days | 80 hours |
| 5-9 years | 15 days | 120 hours |
| 10+ years | 20 days | 160 hours |

**Guidelines:**
- Vacation requests should be submitted at least 2 weeks in advance
- Half-day (4 hours) minimum, one-week (40 hours) maximum per request
- Vacation does not carry over to the next year without management approval
- Carryover requests must be in full-day (8-hour) increments
- Employees are encouraged to take vacation each year; unused time will not be paid out except where required by state law

---

## Personal Days

- All employees receive **2 paid personal days** (16 hours) per calendar year
- Personal days do not carry over to the next year
- Request personal days at least 24 hours in advance when possible
- Personal days are prorated based on hire date for new employees

---

## Paid Sick Time

**Default Policy:**
- All employees accrue up to **40 hours (5 days)** of paid sick time per year
- Sick time begins accruing from date of hire
- Unused sick time carries over to the following year, up to a maximum of **60 hours**
- Minimum increment: 4 hours (half day)

**Permitted Uses:**
- Personal illness, injury, or medical appointments
- Caring for a sick family member
- Preventive medical care
- Reasons related to domestic violence, sexual assault, or stalking
- Public health emergencies

**Notice Requirements:**
- Provide advance notice when foreseeable
- Notify supervisor as soon as possible for unforeseeable absences
- Documentation may be required for absences of 3+ consecutive days

---

## State-Specific Sick Time Policies

### Chicago, IL (Effective July 1, 2024)
Under the Chicago Paid Leave and Paid Sick and Safe Leave Ordinance:
- **Accrual:** 1 hour for every 35 hours worked
- **Annual Cap:** 40 hours paid sick leave + 40 hours paid leave
- **Carryover:** Up to 80 hours of sick leave; paid leave does not carry over
- **Minimum Increment:** 2 hours (or full shift if shorter)
- **Covered Uses:** Safe leave for domestic violence, sexual assault, stalking, or human trafficking

### New York State
- **Accrual:** 1 hour for every 30 hours worked
- **Annual Cap:** 56 hours (7 days) for employers with 100+ employees
- **Carryover:** Unused time carries over
- **Minimum Increment:** 4 hours

### New Jersey
- **Accrual:** 1 hour for every 30 hours worked
- **Annual Cap:** 40 hours (5 days)
- **Carryover:** Up to 40 hours
- **Minimum Increment:** As needed (no minimum)

### Connecticut
- **Accrual:** 1 hour for every 40 hours worked
- **Annual Cap:** 40 hours (5 days)
- **Carryover:** Up to 40 hours
- **Covered Employees:** Service workers in employers with 50+ employees

---

## Family and Medical Leave (FMLA)

Eligible employees may take up to **12 weeks** of unpaid, job-protected leave per year for:
- Birth and care of a newborn child
- Placement of a child for adoption or foster care
- Care for an immediate family member with a serious health condition
- Medical leave when unable to work due to a serious health condition

**Eligibility:**
- Employed for at least 12 months
- Worked at least 1,250 hours in the previous 12 months
- Work at a location with 50+ employees within 75 miles

**Military Family Leave:**
- Up to 26 weeks to care for a covered servicemember with a serious injury or illness

---

## State Family Leave Laws

### Connecticut Family and Medical Leave
- Up to **12 weeks** of job-protected leave
- Applies to employers with 1+ employees
- Covers same purposes as FMLA plus organ/bone marrow donation

### New Jersey Family Leave
- Up to **12 weeks** of job-protected leave
- Applies to employers with 30+ employees

### New York Paid Family Leave
- Up to **12 weeks** of paid family leave at 67% of average weekly wage
- For bonding with new child, caring for family member, or military family leave

---

## Other Leave Types

### Jury Duty
- Full pay for jury duty service
- Notify your manager as soon as you receive a summons
- Provide documentation upon return

### Voting Leave
- Reasonable time off to vote if polls are not open for 4+ hours outside work hours
- Up to 2 hours of paid time if needed

### Military Leave
- Leave provided per USERRA requirements
- Job-protected leave for uniformed services
- Reemployment rights upon return

### Bereavement Leave
- **Immediate Family:** Up to 5 days paid leave
- **Extended Family:** Up to 3 days paid leave
- Immediate family includes spouse, parent, child, sibling, grandparent, grandchild, in-laws

### Domestic Violence Leave
- Reasonable time off for:
  - Medical attention
  - Legal proceedings
  - Safety planning
  - Counseling
- Documentation may be required

---

## Remote Work

- Employees may request remote work days through the Time Calendar system
- Remote work arrangements require manager approval
- Track remote days used through the system
- Remote work is a privilege and may be modified based on business needs

---

*For questions about time off policies, contact your manager or HR.*
*Haventech LLC reserves the right to modify these policies at any time.*
"""

# Structured sections for the styled viewer
HANDBOOK_SECTIONS = [
    {
        "id": "holidays",
        "title": "Holidays",
        "icon": "celebration",
        "content": """
Haventech observes **10 holidays**:

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
Employees on paid leaves of absence are not eligible for holiday pay.
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
| 1-4 years | 10 days | 80 hours |
| 5-9 years | 15 days | 120 hours |
| 10+ years | 20 days | 160 hours |

**Guidelines:**
- Submit requests at least **2 weeks in advance**
- Half-day (4 hours) minimum, one-week (40 hours) maximum per request
- No carryover without management approval
- Carryover must be in full-day (8-hour) increments
- Unused time will not be paid out except where required by state law
        """
    },
    {
        "id": "personal",
        "title": "Personal Days",
        "icon": "person",
        "content": """
All employees receive **2 paid personal days** (16 hours) per calendar year.

**Rules:**
- Do not carry over to next year
- Request at least 24 hours in advance when possible
- Prorated based on hire date for new employees
        """
    },
    {
        "id": "sick",
        "title": "Paid Sick Time",
        "icon": "medical_services",
        "content": """
**Default Policy:**
- Max annual: 40 hours (5 days)
- Max carryover: 60 hours
- Minimum increment: 4 hours (half day)

**Permitted Uses:** Personal illness, medical appointments, caring for sick family, domestic violence/stalking related, public health emergencies.

**State-Specific Variations:**

**Chicago, IL (July 2024):** 1 hr/35 hrs worked, 40 hr sick + 40 hr paid leave, 80 hr carryover, 2-hr minimum

**New York:** 1 hr/30 hrs worked, 56 hr max annual

**New Jersey:** 1 hr/30 hrs worked, 40 hr max, 40 hr carryover

**Connecticut:** 1 hr/40 hrs worked, 40 hr max, 40 hr carryover
        """
    },
    {
        "id": "fmla",
        "title": "Family & Medical Leave",
        "icon": "family_restroom",
        "content": """
**FMLA (Federal):**
- Up to **12 weeks** unpaid, job-protected leave
- For: newborn care, adoption/foster care, family illness, personal medical leave
- Eligibility: 12 months employed, 1,250 hours worked, 50+ employees within 75 miles
- Military Family Leave: up to 26 weeks for servicemember care

**State Family Leave:**
- **Connecticut:** 12 weeks, employers with 1+ employees
- **New Jersey:** 12 weeks, employers with 30+ employees
- **New York:** 12 weeks paid at 67% of average weekly wage
        """
    },
    {
        "id": "remote",
        "title": "Remote Work",
        "icon": "home_work",
        "content": """
- Request remote work days through the Time Calendar system
- Requires manager approval
- Track remote days used through the system
- Remote work is a privilege and may be modified based on business needs
        """
    },
    {
        "id": "other_leave",
        "title": "Other Leave Types",
        "icon": "event_available",
        "content": """
The following leave types do not deduct from PTO balances:

- **Jury Duty** - Full pay for jury service; notify manager when summoned
- **Voting** - Up to 2 hours paid time if polls not open 4+ hours outside work
- **Military Leave** - Per USERRA requirements; job-protected
- **Bereavement** - Immediate family: 5 days; Extended family: 3 days
- **Domestic Violence Leave** - Reasonable time for medical, legal, safety, counseling

These require manager approval and documentation.
        """
    }
]
