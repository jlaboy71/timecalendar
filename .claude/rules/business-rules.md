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

#### Hard Cap Types (BLOCKED when over balance)
These types have fixed annual allocations. **Overdraft is NOT allowed.**
| Type | Reason |
|------|--------|
| **Sick** | 5 days/year - fixed allocation, no manager override |
| **Personal** | 2 days/year - fixed allocation, no manager override |
| **Chicago Leave** | Per Chicago ordinance, only accrued time can be used |

#### Soft Cap Types (WARNING when over balance)
| Type | Behavior |
|------|----------|
| **Vacation** | Warning shown, but submission allowed. Manager discretion on approval. |

#### Future Year Requests
- **Sick, Personal, Chicago Leave**: NOT allowed for future years
- **Non-balance types (bereavement, fmla, jury_duty, etc.)**: Allowed for future years
- **Vacation Rollover**: Special handling (see below)

#### Vacation Rollover (December → January)
Employees can request vacation for January of next year in December:
1. **When**: Only in December, for January dates only
2. **Balance Check**: Must have vacation balance in current year
3. **No Auto-Approve**: Even managers go to pending (requires approval)
4. **Deduction**: Hours deducted from current year (e.g., 2025), NOT next year
5. **Cancel Restriction**: Approved rollover can only be cancelled by manager
6. **Tagged**: Request has `carryover_from_year` set to identify it as rollover

## Carryover Rules

### Automatic Carryover (No Approval Required)
- **Sick Leave**: Unused hours automatically carry over up to policy maximum
- Applied during year-end processing (no employee action needed)

### Personal Leave (Use-It-Or-Lose-It)
- All employees receive 2 paid personal days (16 hours) per calendar year
- Personal days do NOT carry over to next year
- Request at least 24 hours in advance when possible
- Prorated based on hire date for new employees

### Vacation Carryover (Use-It-Or-Lose-It by Default)
- Vacation does NOT automatically carry over
- **Exception requests**: Manager can approve exceptional carryover as a BONUS
- **Key behavior**: When carryover is USED, it deducts from the FROM year's balance (e.g., 2025)
- The new year's allocation (e.g., 2026) remains completely untouched
- Exception carryover tracked via `CarryoverRequest.hours_used` field
- Displayed in "Other Leave Types" dropdown on dashboard
- Employee must request exception before year-end

## Leave Types

### Accruing (tracked in PTOBalance)
- **Vacation**: Primary PTO, pending tracking, NO auto-carryover (exception requests only)
- **Sick**: No pending tracking, AUTO-carryover up to policy max
- **Personal**: No pending tracking, NO carryover (use-it-or-lose-it), 24hr advance notice preferred

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
2. Auto-carryover unused Sick (up to policy max) - Personal does NOT carry over
3. Apply approved vacation exception carryover as BONUS
4. Generate federal holidays for new year

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
