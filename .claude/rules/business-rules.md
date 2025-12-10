# Business Rules

## PTO Balance System

### Front-Loaded Allocation
- Full year's PTO allocated on January 1st
- No monthly accrual - employees get full balance upfront
- Year-end processing creates new year balances automatically

### Vacation Tiers (Based on Tenure)
| Years of Service | Annual Days |
|-----------------|-------------|
| 0-1 years       | 10 days     |
| 2-4 years       | 12 days     |
| 5-9 years       | 15 days     |
| 10+ years       | 20 days     |

### Default Allocations
- Sick: 5 days/year
- Personal: 2 days/year

## Request Workflow

### Employee Requests
1. Employee submits request (status: `pending`)
2. Vacation hours added to `vacation_pending`
3. Manager reviews and approves/denies
4. On approval: `pending` moves to `used`
5. On denial: `pending` removed

### Manager/Admin Requests
- Auto-approved immediately (no pending state)
- Hours go directly to `used`

### Balance Validation
- Warnings shown when request exceeds available balance
- Submission NOT blocked - manager discretion on approval
- Future year requests allowed (up to 5 years ahead)
- Warning shown if future year balance not yet allocated

## Carryover Rules
- Employees must request carryover before year-end
- Manager approval required
- Maximum carryover varies by state policy
- Approved carryover added to `vacation_carryover` in new year

## Leave Types

### Accruing (tracked in PTOBalance)
- **Vacation**: Primary PTO, pending tracking, carryover eligible
- **Sick**: No pending tracking, state-specific policies
- **Personal**: No pending tracking, use-it-or-lose-it

### Non-Accruing (no balance limits)
- **Bereavement**: Immediate family 5 days, extended 3 days
- **FMLA**: Up to 12 weeks unpaid, job-protected
- **Jury Duty**: Paid time for service
- **Voting**: Up to 2 hours if needed
- **Military**: Per USERRA requirements

## Multi-State Policy Support

### Policy Resolution Order
1. City-specific (e.g., Chicago, IL)
2. State-specific (e.g., IL)
3. Default (no location)

### Key State Variations
- Different sick leave accrual rates
- Different carryover maximums
- Different waiting periods for new employees

## Year-End Processing
Runs automatically on first app access of new year:
1. Create new year balances for all active employees
2. Apply approved carryover from previous year
3. Generate federal holidays for new year

## Federal Holidays (Auto-Generated)
- New Year's Day
- MLK Day
- Presidents Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving
- Christmas Day

Weekend holidays observed on nearest weekday.
