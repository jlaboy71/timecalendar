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

## WFH Day Swap Rules

### Overview
Employees can swap their designated WFH (Work From Home) days with teammates. This is a peer-to-peer system - no manager approval required.

### Weekly Limit (CRITICAL)
**Each user can only participate in ONE swap per week** (Monday-Sunday):
- This applies whether you are the **requester** OR the **respondee**
- Once a swap is pending or accepted for a week, that user cannot:
  - Request another swap for that week
  - Be the target of another swap request for that week

### Validation Rules (Service Layer - ENFORCED)
All validations are enforced in `create_swap_request()` at the service layer:

1. **Self-swap blocked**: Cannot swap with yourself
2. **Weekdays only**: Swap date must be a weekday (Mon-Fri)
3. **Future dates only**: Swap date must be in the future
4. **Two-week window**: Swap date must be within current week or next week
5. **Federal holiday blocked**: Cannot swap on full federal holidays (office closed); "Early Close" half-days ARE allowed
6. **Active users only**: Both requester and target must have `is_active = True`
7. **Eligibility required**: Both requester and target must have `wfh_swap_eligible = True`
8. **WFH day required**: Both requester and target must have a designated WFH day
9. **Day match**: The swap date must be the target's WFH day
10. **Message required**: All requests and responses require a message
11. **Weekly limit**: Only ONE swap per user per week (as requester OR target)

### Request Lifecycle
1. **pending**: Request created, awaiting response
2. **accepted**: Target accepted the swap
3. **declined**: Target declined the swap
4. **cancelled**: Requester cancelled before response
5. **expired**: No response within 3 business days

### UI Display Rules

#### Week Navigation
- Page displays one week at a time (Monday-Friday)
- Toggle between "This Week" and "Next Week"
- Each day column shows the actual date under the day name (e.g., "MONDAY" with "Dec 23" below)
- Dates update dynamically when toggling between weeks

#### Employee Position Display (CRITICAL)
**Swaps are about which day the employee works from home, NOT about covering duties.**

For any given week being viewed:
1. **No accepted swap**: Employee appears under their DEFAULT WFH day
2. **Accepted swap for that week**: Employee appears under their SWAPPED day

**Example:** Alice (default: Monday WFH) and Bob (default: Wednesday WFH) have an accepted swap for week of Dec 23.
- **Week of Dec 23 view**:
  - Monday column: Shows **Bob** (swapped to Monday)
  - Wednesday column: Shows **Alice** (swapped to Wednesday)
- **Week of Dec 30 view** (no swap):
  - Monday column: Shows **Alice** (default)
  - Wednesday column: Shows **Bob** (default)

#### Visual Indicators
- Users with pending/accepted swaps show a swap icon with paired color
- User's own WFH day column has a gold star and border highlight
- Employees already swapped for a week are not clickable (can't double-swap)
- **Swapped users**: Name displayed in swap pair color (NOT "(Swapped)" text) with work hours shown underneath

#### Federal Holiday Handling (CRITICAL)
**Swaps are NOT allowed on full federal holidays** where the office is closed.

**Exception: "Early Close" Days ARE Working Days**
- Days with "Early Close" in the name (e.g., "Christmas Eve (Early Close)") are half-days
- Employees work on these days, just with reduced hours
- WFH swaps ARE ALLOWED on Early Close days
- UI Display:
  - Orange clock icon (⏰) in header instead of red X
  - Employees remain clickable (not greyed out)
  - Amber label at bottom: "⏰ Christmas Eve (Early Close)"
  - Serves as informational notice to employees

**Full Holidays (Office Closed):**
1. **Day Column Display**:
   - Holiday days are greyed out (reduced opacity)
   - Red "event_busy" icon replaces the day color
   - Day name shown in grey instead of day color
   - Holiday name displayed at bottom of column with celebration icon

2. **Employee Display on Holidays**:
   - All employees greyed out
   - Clickable to show holiday info popup
   - Work hours still visible but faded

3. **Swap Dialog**:
   - Full holiday dates excluded from date picker
   - Warning shown if all available dates are full holidays

4. **Holiday Detection Logic**:
   - Query: `MarketHoliday` where `market = 'Federal'` (case-sensitive!)
   - Filter: Exclude holidays where name contains "Early Close"
   - Checks both current week and next week

### Swap Activity Log

#### Role-Based Filtering
- **Employees**: See activity for "This Week" and "Next Week" only
- **Managers/Admins/Superadmins**: See full year activity (labeled with year badge)

#### Display Format
- Each log entry has colored left border matching action type:
  - Blue (#3b82f6) - Requested
  - Green (#22c55e) - Accepted
  - Red (#ef4444) - Declined
  - Grey (#6b7280) - Cancelled
- Timestamps: "Monday, December 22, 2025 at 2:30 PM"
- Descriptions in plain English with formatted dates

#### Audit Log Messages
- Request: "Sent a swap request to [Name] for [Day, Month Date, Year]"
- Accept: "Accepted swap request from [Name] for [Day, Month Date, Year]"
- Decline: "Declined swap request from [Name] for [Day, Month Date, Year]"
- Cancel: "Cancelled their swap request"

### Code Location
`src/services/wfh_swap_service.py` - All validation in `create_swap_request()`
`nicegui_app/pages/wfh_swap.py` - UI rendering and display logic
`src/services/audit_service.py` - Audit logging with swap_date parameter
