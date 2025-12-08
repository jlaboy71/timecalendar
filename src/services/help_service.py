"""
Help documentation service for providing searchable instructional content.
Comprehensive documentation for the TJM Time Calendar system.
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class HelpService:
    """Service for managing help documentation content."""

    # Help content organized by chapters
    CHAPTERS = {
        "getting-started": {
            "title": "Getting Started",
            "icon": "play_circle",
            "order": 1,
            "articles": [
                {
                    "id": "overview",
                    "title": "System Overview",
                    "content": """
# TJM Time Calendar - System Overview

Welcome to the TJM Time Calendar! This is your complete system for managing paid time off (PTO), tracking leave balances, and coordinating team schedules.

## What Can You Do?

### For All Employees
- **Submit PTO Requests** - Request vacation, sick, or personal time off
- **View Your Balances** - See how much leave you have available
- **Track Request Status** - Monitor pending, approved, and denied requests
- **Team Calendar** - See when colleagues are out (approved time off)
- **Request Carryover** - Carry unused leave into the next year
- **Access Employee Handbook** - View company policies

### For Managers (Additional Features)
- **Approve/Deny Requests** - Review and process team PTO requests
- **Team Calendar View** - See your entire department's schedule
- **Reports & Analytics** - Generate team balance and usage reports
- **AI Handbook Assistant** - Ask questions about company policies
- **Carryover Approvals** - Process carryover requests for your team

### For Administrators (Full Access)
- **Employee Management** - Add, edit, and manage all employees
- **Department Management** - Create and organize departments
- **Bulk Approvals** - Process multiple pending requests at once
- **Year-End Processing** - Initialize balances for new year
- **System Reports** - Complete audit logs and analytics
- **Handbook Management** - Update company policy documents

## User Roles Explained

| Role | Description |
|------|-------------|
| **Employee** | Standard user - can manage their own PTO |
| **Manager** | Department lead - approves team requests |
| **Admin** | System administrator - full management access |
| **Superadmin** | Complete system access across all departments |

## Leave Types Available

- **Vacation** - Annual vacation time (balance tracked)
- **Sick Leave** - Sick time allocation (balance tracked)
- **Personal Days** - Personal time off (balance tracked)
- **Other** - Additional leave types as configured

## Quick Start Checklist

1. Log in with your credentials
2. Check your PTO balances on the Dashboard
3. Review the Team Calendar for planning
4. Submit your first PTO request when needed
5. Bookmark this Help Center for reference
"""
                },
                {
                    "id": "first-login",
                    "title": "Logging In",
                    "content": """
# Logging In to TJM Time Calendar

## How to Log In

1. **Navigate to the Login Page**
   - Open your web browser
   - Go to the system URL provided by your administrator

2. **Enter Your Credentials**
   - **Username**: Your assigned username (usually your email address)
   - **Password**: Your password (temporary if first time)

3. **Click "Sign In"**
   - You'll be taken to your Dashboard

## First Time Login

If this is your first time logging in:
1. Use the temporary password provided by HR or your administrator
2. You may be prompted to change your password
3. Review your profile information on the Dashboard

## Forgot Password?

If you've forgotten your password:

1. Click the **"Forgot Password?"** link on the login page
2. Enter your email address
3. Check your email for a password reset link
4. Click the link and create a new password
5. Log in with your new password

**Note**: Reset links expire after 1 hour for security.

## Session Timeout

For security, your session will automatically expire after a period of inactivity:
- A warning will appear before your session expires
- Click "Stay Logged In" to extend your session
- If your session expires, you'll be redirected to login

## Trouble Logging In?

- **Check Caps Lock** - Passwords are case-sensitive
- **Verify Username** - Make sure you're using the correct username
- **Clear Browser Cache** - Try clearing cookies and cache
- **Contact Administrator** - Your account may be deactivated
"""
                },
                {
                    "id": "dashboard",
                    "title": "Understanding Your Dashboard",
                    "content": """
# Understanding Your Dashboard

The Dashboard is your home base in TJM Time Calendar. Here's everything you'll see:

## PTO Balance Cards

At the top of your dashboard, you'll see your current leave balances:

### Vacation Balance
- **Total**: Your annual vacation allocation (plus any carryover)
- **Used**: Days already taken
- **Pending**: Days in pending requests
- **Available**: What you can still use

### Sick Leave Balance
- Shows your sick time allocation and usage
- Typically doesn't require approval for short absences

### Personal Days Balance
- Your personal day allocation
- Track usage throughout the year

## Quick Actions

Easy access to common tasks:
- **New PTO Request** - Submit a new time off request
- **View Calendar** - See the team calendar
- **My Requests** - View your request history
- **Request Carryover** - Request to carry over unused leave

## Pending Requests

If you have requests waiting for approval:
- Shows status of each pending request
- Click to view details
- Option to cancel pending requests

## For Managers

Additional sections appear for managers:
- **Pending Approvals** - Requests awaiting your review
- Quick approve/deny buttons
- Link to full approval dashboard

## For Administrators

Admins see additional quick links:
- Employee Management
- Department Management
- System Settings
- Reports & Analytics

## Dark Mode Toggle

Click the moon/sun icon in the header to switch between:
- **Light Mode** - Bright background
- **Dark Mode** - Dark background (easier on eyes)

Your preference is saved automatically.
"""
                }
            ]
        },
        "pto-requests": {
            "title": "PTO Requests",
            "icon": "event_available",
            "order": 2,
            "articles": [
                {
                    "id": "submit-request",
                    "title": "Submitting a PTO Request",
                    "content": """
# Submitting a PTO Request

Follow these steps to request time off:

## Step 1: Select Leave Type

Choose your leave type:
- **Vacation** - Annual vacation time
- **Sick** - Sick leave
- **Personal** - Personal days

Your available balance for the selected type will display immediately.

## Step 2: Select Date(s)

Choose between two modes:

### Single Day Mode
- Select one day from the calendar
- Quick buttons: "Today", "Tomorrow", "Next Monday"
- **Half Day Option**: Toggle for 4-hour (half day) requests

### Date Range Mode
- Select start and end dates
- Quick buttons: "Rest of Week", "Next Week (Mon-Fri)"
- Calendar shows your selection

## Step 3: Add Notes (Optional)

- Provide context for your manager
- Some leave types may require notes
- Keep notes professional and brief

## Step 4: Review and Submit

The summary shows:
- **Dates Selected** - Your requested dates
- **Days Requested** - Total days/hours
- **Balance After** - Your remaining balance

Click **"Submit Request"** to send for approval.

## What Happens Next?

1. Your manager receives a notification
2. Request appears in your "Pending" list
3. Balance shows as "Pending" (for vacation)
4. You'll be notified when approved/denied

## Auto-Approval (Managers/Admins)

If you're a manager or admin, your requests are **auto-approved** since you approve your own time.

## Tips for Success

- Submit requests with advance notice when possible
- Check the team calendar for coverage first
- Add helpful notes for your manager
- Avoid requesting more than your available balance
"""
                },
                {
                    "id": "view-requests",
                    "title": "Viewing Your Requests",
                    "content": """
# Viewing Your PTO Requests

Access your complete request history from the Dashboard or navigation.

## Request History Page

### Summary Cards
At the top, you'll see:
- **Total Approved** - All approved requests
- **Pending** - Requests awaiting approval
- **Denied** - Requests that were denied

### Filtering Options

**By Leave Type:**
- Click "Vacation", "Sick", or "Personal" to filter
- Click again or "Show All" to clear filter

**By Status (Employees):**
- Show Pending - Only pending requests
- Show Denied - Only denied requests

### Request Details

Each request shows:
- **Leave Type** - Color-coded (blue=vacation, green=sick, purple=personal)
- **Date(s)** - Single day or date range
- **Total Days** - How many days requested
- **Status** - Pending, Approved, Denied, or Cancelled
- **Submitted Date** - When you made the request
- **Notes** - Any notes you added

### For Denied Requests

If a request was denied:
- The denial reason is displayed
- Contact your manager for clarification
- You can submit a new request for different dates

## Request Statuses Explained

| Status | Meaning |
|--------|---------|
| **Pending** | Awaiting manager approval |
| **Approved** | Request approved - time is confirmed |
| **Denied** | Request was not approved |
| **Cancelled** | You cancelled the request |

## Quick Actions

From the request list:
- **Cancel** - Cancel pending requests
- View detailed information by clicking on entries
"""
                },
                {
                    "id": "cancel-request",
                    "title": "Cancelling a Request",
                    "content": """
# Cancelling a PTO Request

Need to cancel a time off request? Here's how:

## From the Dashboard

1. Find your pending request in the "Pending Requests" section
2. Click the **"Cancel"** button
3. Confirm the cancellation in the dialog

## From Request History

1. Go to **"My Requests"** or **"Request History"**
2. Filter by "Pending" status if needed
3. Click the **"Cancel"** button next to the request
4. Confirm the cancellation

## What Happens When You Cancel

1. Request status changes to "Cancelled"
2. Your balance is restored immediately (for vacation)
3. Your manager is notified
4. The request remains in your history

## Important Notes

**You can only cancel PENDING requests**

Once a request is approved:
- You cannot cancel it yourself
- Contact your manager to discuss changes
- They may need to manually adjust your balance

## Re-submitting After Cancellation

If you cancelled by mistake or want different dates:
1. Go to "New PTO Request"
2. Submit a new request
3. The cancelled request stays in your history

## Automatic Balance Restoration

When you cancel a vacation request:
- Pending hours are immediately restored
- Your available balance updates automatically
- No manual intervention needed
"""
                },
                {
                    "id": "view-balance",
                    "title": "Understanding Your Balance",
                    "content": """
# Understanding Your PTO Balance

Your PTO balance is tracked throughout the year. Here's how to read it:

## Balance Components

### Total Allocation
- Your annual leave entitlement
- Based on company policy and tenure
- May include carryover from previous year

### Used
- Days/hours already taken (approved and completed)
- Deducted from your total

### Pending
- Days/hours in pending requests
- Reserved but not yet approved
- Only applies to vacation (other types don't reserve)

### Available
- What you can still request
- Calculated as: Total + Carryover - Used - Pending

## Viewing Your Balance

### On the Dashboard
Balance cards show at a glance:
- Current available for each leave type
- Color coding: Green (good), Amber (low), Red (none)

### In Reports
Go to **Reports** > **My Balance Summary** for detailed view:
- Complete breakdown by leave type
- Hours and days display
- Year-over-year comparison

### When Submitting Requests
The request form shows:
- Current available balance
- Impact of your request
- Warning if exceeding balance

## Balance Colors

| Color | Meaning |
|-------|---------|
| Green | Healthy balance (16+ hours) |
| Amber | Getting low (1-15 hours) |
| Red | No balance or negative |

## Carryover Hours

If you have carryover from last year:
- Shows as part of your total
- Usually must be used first
- Subject to company policy

## Questions About Your Balance?

If your balance seems incorrect:
1. Check for pending requests
2. Review your request history
3. Contact HR or your administrator
4. Balance adjustments can be made by admins
"""
                }
            ]
        },
        "calendar": {
            "title": "Team Calendar",
            "icon": "calendar_month",
            "order": 3,
            "articles": [
                {
                    "id": "calendar-overview",
                    "title": "Calendar Overview",
                    "content": """
# Team Calendar Overview

The Team Calendar provides a visual overview of time off and market holidays.

## Calendar Views

### Month View
- Traditional calendar grid
- Shows individual days with events
- Color-coded entries for easy scanning
- Click any day for details

### Year View
- 12-month overview at a glance
- Shows PTO density per month
- Click a month to zoom in
- Great for annual planning

## What You'll See

### Your Time Off
- Your approved PTO requests
- Color-coded by leave type:
  - Blue = Vacation
  - Green = Sick
  - Purple = Personal
  - Gray = Other

### Market Holidays
- Shown in red
- Indicates market closures
- Click for holiday details

### Team Members (Managers/Admins)
- See approved time off for your team
- Plan around team availability
- Identify coverage gaps

## Navigation

- **Left/Right arrows**: Change months
- **Today** button: Jump to current date
- **Month/Year** toggle: Switch views
- **Filters**: Expand to customize view

## Quick Request Feature

**For Employees:**
- Click on an empty day
- Quick popup to start a PTO request
- Pre-fills the selected date
"""
                },
                {
                    "id": "calendar-filters",
                    "title": "Calendar Filters",
                    "content": """
# Calendar Filters & Options

Customize your calendar view with filters:

## View Mode Toggle (Managers/Admins)

**My Calendar**
- Shows only YOUR approved time off
- Personal planning view

**Team Calendar**
- Shows all team members' time off
- Coverage planning view

## Leave Type Filters

Check/uncheck to show or hide:
- Vacation
- Sick
- Personal
- Other

## Display Options

**Show Market Holidays**
- Toggle holiday display on/off
- Useful when focusing on PTO only

**Show Weekends**
- Toggle Saturday/Sunday visibility
- Hide for business-day focus

## Department Filter (Admins Only)

- Filter by specific department
- Or view "All Departments"
- Helps focus on specific teams

## Saving Your Preferences

Your filter settings are **automatically saved**:
- Persists between sessions
- Each user has their own preferences
- Reset by changing filters

## Tips for Effective Filtering

- Use "Team Calendar" view for planning coverage
- Filter by department when managing specific teams
- Toggle off weekends for cleaner business view
- Keep holidays visible for accurate planning
"""
                },
                {
                    "id": "calendar-export",
                    "title": "Calendar Export",
                    "content": """
# Exporting Calendar Data

Export your calendar data for external use.

## Export Options

Click the **"Export"** dropdown button to see options:

### My PTO Calendar
- Exports YOUR approved time off
- Includes dates, leave types, and days
- Useful for personal records

### Team Calendar (Managers/Admins)
- Exports all team time off
- Can be filtered by department
- Great for team planning

### Market Holidays
- Exports all market holidays for the year
- Includes holiday names and dates
- Useful for planning tools

## Export Format

All exports are in **CSV format**:
- Compatible with Excel, Google Sheets
- Easy to import into other systems
- Clean, organized data

## Using Exported Data

**In Excel:**
1. Open the downloaded .csv file
2. Data auto-formats into columns
3. Create charts or pivot tables
4. Share with stakeholders

**In Google Calendar:**
1. Import the CSV
2. Map date fields
3. Events appear on your calendar

## Best Practices

- Export at the end of each quarter for records
- Use team exports for capacity planning
- Share holiday exports with the team
- Archive exports for compliance
"""
                },
                {
                    "id": "market-holidays",
                    "title": "Market Holidays",
                    "content": """
# Market Holidays

Market holidays are days when financial markets are closed. These are tracked in the calendar for planning purposes.

## Standard Market Holidays

The following holidays are typically observed:

| Holiday | Typical Date |
|---------|-------------|
| New Year's Day | January 1 |
| Martin Luther King Jr. Day | Third Monday in January |
| Presidents Day | Third Monday in February |
| Good Friday | Friday before Easter |
| Memorial Day | Last Monday in May |
| Juneteenth | June 19 |
| Independence Day | July 4 |
| Labor Day | First Monday in September |
| Thanksgiving | Fourth Thursday in November |
| Christmas Day | December 25 |

## How Holidays Appear

On the calendar:
- Marked in **red**
- Display the holiday name
- Click for details about which markets are closed

## Holidays and PTO

**Important:**
- Market holidays do NOT automatically deduct from your PTO
- If you take time off around a holiday, holidays don't count as PTO days
- Plan accordingly when requesting time around holidays

## Half Days & Early Closes

Some days have early market closes:
- Day before Independence Day
- Day after Thanksgiving
- Christmas Eve

These are noted but may not affect your PTO.

## Holiday Calendar for New Year

Administrators run **Year-End Processing** to generate the next year's holiday calendar based on standard market holiday rules.
"""
                }
            ]
        },
        "carryover": {
            "title": "Leave Carryover",
            "icon": "sync",
            "order": 4,
            "articles": [
                {
                    "id": "carryover-overview",
                    "title": "Carryover Overview",
                    "content": """
# Leave Carryover Overview

At the end of the year, you may be able to carry over unused leave into the next year.

## What is Carryover?

- Unused PTO from the current year
- Transferred to next year's balance
- Subject to company policy and approval

## Who Can Request Carryover?

All employees can request to carry over unused leave, but:
- Some hours may auto-approve based on policy
- Hours above the limit require manager approval
- Company policy determines maximum carryover

## Carryover Timeline

**Best Practice:**
1. Review your unused balance in Q4
2. Submit carryover requests before year-end
3. Await manager approval
4. Carryover applies when new year starts

## Types of Leave That Can Carry Over

Typically includes:
- Vacation time
- Sick leave (policy dependent)
- Personal days (policy dependent)

Check your company handbook for specific policies.

## Accessing Carryover Requests

From your Dashboard:
1. Click **"Request Carryover"** quick action
2. Or navigate to the Carryover page from the menu
"""
                },
                {
                    "id": "submit-carryover",
                    "title": "Submitting a Carryover Request",
                    "content": """
# Submitting a Carryover Request

Here's how to request unused leave carryover:

## Step 1: Review Your Unused Balances

The carryover page shows:
- Your current year unused balances
- Hours available for each leave type
- Visual progress bars

## Step 2: Select Leave Type

Choose which leave type to carry over:
- Only types with unused balance are available
- Each type must be requested separately

## Step 3: Check Policy Context

The system shows your applicable policy:
- **Auto-approved limit**: Hours that don't need approval
- **Requires approval**: Hours above the limit

## Step 4: Enter Hours

Specify how many hours to carry over:
- Use the number input or quick buttons
- Quick buttons: "1 Day (8h)", "2 Days (16h)", "3 Days (24h)", "All Unused"
- Must be in full-day (8-hour) increments

## Step 5: Provide Justification

Enter a reason for your carryover request:
- Required for all requests
- Examples: "Planned vacation in Q1", "Project deadline prevented use"

## Step 6: Submit

Click **"Submit Request"** to send for processing.

## Request Summary

Before submitting, you'll see:
- Currently unused hours
- Hours requesting to carry over
- Hours that will expire if not carried over

## Auto-Approval

Some requests auto-approve:
- Managers/Admins: All requests auto-approve
- Within policy limit: May auto-approve
- Above limit: Requires manager approval
"""
                },
                {
                    "id": "carryover-status",
                    "title": "Tracking Carryover Status",
                    "content": """
# Tracking Your Carryover Requests

Monitor the status of your carryover requests.

## Your Carryover Requests Table

At the bottom of the Carryover page, you'll see:
- All your requests for the current year
- Status of each request
- Hours requested vs. approved

## Status Meanings

| Status | Meaning |
|--------|---------|
| Pending | Awaiting manager review |
| Approved | Approved - will apply next year |
| Denied | Not approved - see notes |

## Approved Requests

When a request is approved:
- Hours carry over automatically on Jan 1
- Shows "Approved" amount (may differ from requested)
- Carryover appears in next year's balance

## Denied Requests

If your request is denied:
- Manager notes explain the reason
- You can discuss with your manager
- Unused hours will expire at year-end

## Multiple Requests

You can submit multiple carryover requests:
- Different leave types
- Additional requests if balance increases
- Each is tracked separately

## Best Practices

- Submit requests early (November/December)
- Provide clear justification
- Monitor status and follow up if pending
- Use denied hours before year-end if possible
"""
                }
            ]
        },
        "managers": {
            "title": "For Managers",
            "icon": "supervisor_account",
            "order": 5,
            "articles": [
                {
                    "id": "approve-requests",
                    "title": "Approving PTO Requests",
                    "content": """
# Approving PTO Requests

As a manager, you're responsible for approving time off requests from your team.

## Accessing Pending Requests

**From Dashboard:**
- Pending requests appear in the "Pending Approvals" card
- Shows count and quick preview
- Click to see full details

**From Request Detail Page:**
- Click on any pending request
- View complete information
- Make approval decision

## Request Detail View

When reviewing a request, you'll see:

### Employee Information
- Name and email
- Department assignment

### Request Details
- Leave type
- Start and end dates
- Total days requested
- Status and submission date
- Employee notes

### Balance Impact
- Employee's current PTO balance
- Impact of this request
- Ensures sufficient balance

### Conflict Detection
If other team members have overlapping time off:
- Warning appears with conflict details
- Shows who else is out
- Helps with coverage decisions

## Approving a Request

1. Review the request details
2. Check for conflicts
3. Click **"Approve"**
4. Request is immediately approved
5. Employee is notified by email

## Denying a Request

1. Review the request details
2. Click **"Deny"**
3. **Required**: Enter a denial reason
4. Click "Confirm Deny"
5. Employee is notified with your reason

## Denial Reasons

Always provide a clear reason:
- "Insufficient coverage during this period"
- "Please coordinate with [colleague] first"
- "Business needs require your presence"

## Best Practices

- Review requests within 24-48 hours
- Check team calendar before approving
- Communicate with employees about denials
- Be consistent with approval decisions
- Consider employee balance remaining
"""
                },
                {
                    "id": "carryover-approvals",
                    "title": "Carryover Approvals",
                    "content": """
# Approving Carryover Requests

Managers review and approve carryover requests from their team.

## Accessing Carryover Approvals

Navigate to **Manager > Carryover Approvals** from the Dashboard.

## Pending Requests View

For each pending request, you'll see:

### Employee Information
- Name and department
- Location (affects policy)

### Request Details
- Leave type being carried over
- Hours requested
- Submission date
- Employee's justification

### Policy Context
- Auto-carryover limit (if applicable)
- Current unused balance

## Processing a Request

### Approving

1. Review the request details
2. Adjust "Hours to Approve" if needed
   - Can approve less than requested
   - Cannot approve more than requested
3. Add optional manager notes
4. Click **"Approve"**

### Denying

1. Review the request
2. Add manager notes (recommended)
3. Click **"Deny"**

## Partial Approval

You can approve fewer hours than requested:
- Change the "Hours to Approve" field
- Approved hours carry over
- Remaining hours expire

## Recently Processed

The "Recently Processed" section shows:
- Your recent approval decisions
- Approved vs. requested amounts
- Processing dates

## Carryover Impact

When approved:
- Hours automatically transfer on January 1st
- Appears in employee's next-year balance
- Recorded in system audit log

## Best Practices

- Process requests before year-end
- Be consistent with policy application
- Communicate partial denials to employees
- Consider team balance remaining
"""
                },
                {
                    "id": "team-overview",
                    "title": "Team Calendar & Overview",
                    "content": """
# Team Calendar & Overview

Managers have special views to monitor their team's time off.

## Team Calendar View

Access via **Calendar** page, select "Team Calendar" mode.

### What You'll See
- All approved time off for your department
- Color-coded by leave type
- Coverage gaps highlighted
- Click any entry for details

### Planning Features
- Month and year views
- Filter by leave type
- Export for planning

## Team Balance Information

From **Reports** > **Team Balance Summary**:
- All team members' current balances
- Vacation, sick, and personal for each
- Identify who has low balance
- Export to spreadsheet

## Team Usage Reports

From **Reports** > **Team Usage Report**:
- Historical usage data
- Filter by date range
- See patterns and trends
- Export for records

## Conflict Management

When reviewing requests:
- System alerts you to overlapping time off
- Shows who else is out during requested dates
- Helps ensure adequate coverage

## Coverage Planning Tips

- Review team calendar weekly
- Encourage advance notice for PTO
- Balance approvals across the team
- Plan around busy periods
- Ensure minimum coverage always
"""
                },
                {
                    "id": "handbook-ai",
                    "title": "Handbook AI Assistant",
                    "content": """
# Handbook AI Assistant

Managers and administrators have access to an AI-powered assistant that can answer questions about the employee handbook and company policies.

## Accessing the AI Assistant

Navigate to **Handbook** from the Dashboard.

## How It Works

1. **Ask Your Question**
   - Type a question in the chat input
   - Examples: "How much vacation do I get?", "What are the holidays?"
   - Press Enter or click Send

2. **Get AI Response**
   - The assistant searches the handbook
   - Provides relevant policy information
   - Cites handbook sections

3. **Follow-Up Questions**
   - Continue the conversation
   - Ask for clarification
   - Dive deeper into topics

## Quick Question Buttons

Pre-built questions for common topics:
- "How much vacation do I get?"
- "What are the holidays?"
- "How does sick time work?"

Click any button to get instant answers.

## What It Can Answer

- PTO policies and accrual rates
- Holiday schedules
- Sick leave rules
- Benefits information
- Company policies and procedures
- Carryover rules

## What It Cannot Do

- Make policy decisions
- Process requests
- Override manager decisions
- Access your personal information

## Configuration Required

The AI assistant requires an API key to function. If you see "API Key Required", contact your system administrator.

## Full Handbook Access

Below the AI chat, click **"View Full Handbook"** to read the complete handbook document.
"""
                }
            ]
        },
        "reports": {
            "title": "Reports & Analytics",
            "icon": "analytics",
            "order": 6,
            "articles": [
                {
                    "id": "reports-overview",
                    "title": "Reports Overview",
                    "content": """
# Reports Overview

The Reports page provides comprehensive data about PTO usage and balances.

## Accessing Reports

Navigate to **Reports** from the Dashboard or menu.

## Report Types

### My Reports (All Users)

**My PTO History**
- Complete history of your requests
- Filter by status (all, approved, pending, denied)
- Shows dates, days, and notes
- Summary statistics

**My Balance Summary**
- Current balance for all leave types
- Total, used, pending, available
- Visual breakdown

**My Year at a Glance**
- Calendar view of approved time off
- Organized by month
- Quick reference for planning

### Team Reports (Managers/Admins)

**Team Balance Summary**
- All team members' balances
- Sortable table
- Filter by department
- Identify balance issues

**Team Usage Report**
- Historical usage data
- Filter by year and department
- Summary by leave type
- Exportable data

**Audit Log**
- System activity tracking
- Filter by action type and date
- Who did what and when
- Compliance records

## Filters

Most reports support:
- **Year** - Select which year to view
- **Status** - Filter by request status
- **Department** - Filter by team (managers/admins)
"""
                },
                {
                    "id": "export-reports",
                    "title": "Exporting Reports",
                    "content": """
# Exporting Reports

Export your report data in multiple formats.

## Download Options

Click the **"Download"** dropdown to see:

### Download CSV
- Spreadsheet format
- Compatible with Excel, Google Sheets
- Contains all visible data
- Great for further analysis

### Download PDF
- Opens browser print dialog
- Use "Save as PDF" option
- Formatted for printing
- Professional appearance

## Print Preview

Click **"Print Preview"** to:
- See how the report will print
- Full-screen preview
- Click Print to send to printer
- Formatted headers and footers

## Email Report

Click **"Email Report"** to send via email:

1. Enter recipient email address
2. Customize subject line
3. Choose attachment format:
   - PDF (Print Format)
   - CSV (Data Export)
   - HTML (Web Format)
4. Add optional message
5. Click Send

**Note**: Requires email configuration in your system.

## Best Practices

- Export monthly for records
- Use CSV for data analysis
- Use PDF for formal documentation
- Archive exports for compliance
- Share team reports with stakeholders
"""
                },
                {
                    "id": "analytics-dashboard",
                    "title": "Analytics Dashboard",
                    "content": """
# Advanced Analytics Dashboard

The Analytics Dashboard provides comprehensive workforce intelligence and insights for PTO usage, attendance patterns, and coverage planning.

## Accessing Analytics

Navigate to **Analytics** from the Dashboard (Managers/Admins only).

**Note for Managers:** You will only see analytics for your own department. Admins and Superadmins see company-wide data.

## Dashboard Tabs

The analytics dashboard has three main tabs:

### Overview Tab
Quick metrics and visual summaries for at-a-glance insights.

### Trends Tab
Detailed charts and patterns over time.

### Insights Tab
AI-powered recommendations and risk analysis.

---

## Overview Tab Features

### Key Metrics Cards

Quick stats for the selected year:
- **Total Requests** - All PTO requests submitted
- **Approved** - Successfully approved requests
- **Pending** - Requests awaiting approval
- **Days Taken** - Total PTO days used
- **Avg Days/Employee** - Average usage per person

### Attendance Heatmap

Interactive calendar heatmap showing:
- Color-coded attendance rates (green = high, red = low)
- Last 60 days plus 14 days ahead
- Hover for specific date details
- Identify patterns at a glance

### Leave Type Breakdown (Pie Chart)

Distribution of leave types:
- Vacation (blue) vs. Sick (red) vs. Personal (green)
- Interactive donut chart
- Percentage breakdown

### Best Days for All-Hands Meetings

Smart scheduling suggestions:
- Shows top 3 dates with highest expected attendance
- Filters for 80%+ attendance threshold
- Displays day of week and exact percentage
- Plan company meetings with maximum participation

### PTO Utilization Gauge

Company-wide utilization:
- Large percentage display
- Progress bar visualization
- Used vs. allocated comparison
- Employee count tracked

### Coverage Gap Analysis

For each department:
- Analyze next 30 days
- Identify potential coverage issues
- Shows who's out when
- Warning for 30%+ absence rate
- Managers see their department only

---

## Trends Tab Features

### Monthly PTO Trends Chart

Interactive Plotly chart showing:
- Stacked area chart by leave type
- Vacation, Sick, Personal breakdown
- Month-by-month visualization
- Click legends to toggle types

### PTO by Day of Week

Pattern analysis:
- Bar chart showing average PTO per weekday
- Detects Monday/Friday clustering
- Orange highlighting for suspicious patterns
- Helps identify potential abuse patterns

### Department Utilization Rates

Horizontal bar chart showing:
- Utilization rate by department
- Color-coded health status:
  - Green (70-90%) = Healthy
  - Yellow (50-70%) = Low
  - Red (<50%) = Burnout risk
  - Orange (>90%) = Coverage risk
- Target line at 75%

### Department Comparison Table

Sortable table with:
- Employee count per department
- Total requests made
- Total days used
- Average days per employee
- Click columns to sort

### Top PTO Users

Rankings of employees by PTO usage:
- Medal icons for top 3
- Shows name and department
- Days taken displayed
- Helps identify patterns

---

## Insights Tab Features

### AI-Powered Recommendations

Automatically generated actionable insights:

**HIGH Priority (Red)**
- Employees at high carryover risk
- Critical coverage gaps detected

**MEDIUM Priority (Amber)**
- Departments with low utilization
- Work-life balance concerns

**LOW Priority (Blue)**
- Pattern anomalies detected
- Minor attention items

**INFO (Green)**
- Optimal meeting date suggestions
- Positive trends

Each recommendation shows:
- Title and category
- Suggested action
- Affected employees/departments

### Carryover Risk Analysis

#### Risk Gauge
Visual gauge showing:
- Number of employees at risk
- Threshold indicators
- Color zones for severity

#### Risk Table
Detailed breakdown of at-risk employees:
- Employee name and department
- Remaining vs. total vacation
- Risk level (HIGH/MEDIUM/LOW)

Risk levels calculated based on:
- HIGH: 80%+ remaining with 60 or fewer days until year-end
- MEDIUM: 60%+ remaining with 90 or fewer days until year-end
- LOW: Other at-risk employees

### Coverage Forecast Timeline

Line chart showing:
- 30-day forward projection
- Coverage percentage by date
- Critical threshold line at 70%
- Red dots indicate critical days
- Blue line shows trend

---

## Export Features

### Export PDF
Click **"Export PDF"** to generate a professional report including:
- Key metrics summary
- Recommendations
- Carryover risk employees
- Optimal meeting dates
- TJM Holdings branded footer

### Export CSV
Click **"Export CSV"** to download:
- Carryover risk employee list
- Spreadsheet compatible
- For further analysis in Excel/Google Sheets

---

## Filters and Controls

### Year Selector
- Choose year to analyze
- Range: current year +/- 2 years
- All data updates automatically

### Refresh Button
- Manually refresh all data
- Useful after new requests are submitted

### Tab Navigation
- Overview: Quick summary
- Trends: Detailed charts
- Insights: Recommendations

---

## Navigation

At the bottom of the page:
- **Back to Dashboard** - Return to main dashboard
- **View Reports** - Go to detailed reports page

---

## For Managers

As a manager, your analytics are **scoped to your department**:
- All metrics filtered to your team
- Coverage gaps show your department
- Recommendations focus on your employees
- Title shows "ANALYTICS - [YOUR DEPARTMENT]"

## For Admins/Superadmins

Full company-wide access:
- See all departments
- Department selector for coverage analysis
- Company-wide recommendations
- Cross-department comparisons
"""
                }
            ]
        },
        "admin": {
            "title": "Administration",
            "icon": "admin_panel_settings",
            "order": 7,
            "articles": [
                {
                    "id": "employee-management",
                    "title": "Employee Management",
                    "content": """
# Employee Management

Administrators can manage all employee records in the system.

## Accessing Employee Management

From Dashboard: **Admin** > **Manage Employees**

## Employee List

The main view shows:
- All employees (paginated)
- Search/filter by name, email, department
- Status indicators (active/inactive)
- Quick action buttons

## Adding a New Employee

1. Click **"Add Employee"**
2. Fill in required information:

**Personal Information:**
- First Name (required)
- Last Name (required)
- Email (required, must be unique)
- Username (auto-generated or custom)

**Employment Details:**
- Department (select from list)
- Role (Employee, Manager, Admin)
- Hire Date (required)
- Location State (for policy application)
- Location City (optional)

**Authentication:**
- Password (temporary or custom)
- Must be at least 8 characters

3. Click **"Save"** to create

## Editing an Employee

1. Find the employee in the list
2. Click **"Edit"** button
3. Modify any fields
4. Click **"Save Changes"**

**Editable Fields:**
- Personal information
- Department assignment
- Role/access level
- Remote schedule
- Location information
- Active status

## Deactivating an Employee

When an employee leaves:
1. Find their record
2. Click **"Deactivate"** (or toggle Active status)
3. Confirm the action

**What Happens:**
- Employee cannot log in
- Records are preserved
- Historical data intact
- Can be reactivated if needed

## Deleting an Employee

**Use with caution** - Soft delete is preferred

Deletion is only possible if:
- No PTO requests exist
- No associated records

## Best Practices

- Keep employee records up to date
- Deactivate instead of delete when possible
- Set correct roles for access control
- Verify email addresses are correct
- Update department assignments promptly
"""
                },
                {
                    "id": "department-management",
                    "title": "Department Management",
                    "content": """
# Department Management

Organize your company structure with departments.

## Accessing Department Management

From Dashboard: **Admin** > **Departments**

## Department List

Shows all departments with:
- Department name
- Department code
- Manager assigned
- Employee count
- Status (active/inactive)

Click any row to see department details.

## Creating a Department

1. Expand **"Create New Department"**
2. Enter details:
   - **Department Name** - Full name (required)
   - **Department Code** - Short code (required)
   - **Manager** - Select from user list (optional)
3. Click **"Create"**

## Department Detail View

When viewing a department:

**Header Information:**
- Department name and code
- Status badge
- Manager assigned
- Total employee count

**Action Buttons:**
- Edit - Modify department details
- Delete - Remove department (if empty)

**Employee List:**
- All employees in the department
- Name, email, role displayed
- Filterable by name

## Editing a Department

1. Select the department
2. Click **"Edit"**
3. Modify:
   - Department name
   - Department code
   - Manager assignment
4. Click **"Save"**

## Deleting a Department

**Departments can only be deleted if empty**

1. Reassign or deactivate all employees first
2. Select the department
3. Click **"Delete"**
4. Confirm deletion

## Department & Approval Workflow

Departments control the approval workflow:
- Employees are approved by their department's manager
- No manager = no direct approver (admin required)
- Managers can only approve their own department

## Best Practices

- Assign a manager to every department
- Use meaningful department codes
- Keep department structure current
- Don't leave employees without departments
"""
                },
                {
                    "id": "pending-approvals",
                    "title": "Bulk Pending Approvals",
                    "content": """
# Bulk Pending Approvals

Admins can view and process all pending PTO requests across the organization.

## Accessing Bulk Approvals

From Dashboard: **Admin** > **Pending Approvals**

## Overview

Shows all pending requests:
- Total count
- Filterable by department
- Checkbox selection for bulk actions

## Filtering

**By Department:**
- Select a department from dropdown
- Or view "All Departments"
- Helps focus on specific teams

## Individual Request Actions

Each request card shows:
- Employee name and department
- Leave type and dates
- Days requested
- Checkbox for selection

Click to expand for more details.

## Bulk Actions

### Select Multiple Requests
1. Check the checkbox on each request
2. Or use "Select All" for visible requests
3. Selection count shows at top

### Bulk Approve
1. Select requests to approve
2. Click **"Approve Selected"**
3. All selected are approved instantly
4. Employees notified

### Bulk Deny
1. Select requests to deny
2. Click **"Deny Selected"**
3. Enter a denial reason (applies to all)
4. Confirm denial
5. Employees notified with reason

## Conflict Warnings

When viewing individual requests:
- System shows if others have overlapping time off
- Helps make informed decisions
- Coverage considerations highlighted

## Best Practices

- Process bulk requests by department
- Review conflicts before bulk approve
- Provide meaningful denial reasons
- Process requests promptly (daily if possible)
- Communicate unusual situations directly
"""
                },
                {
                    "id": "year-end-processing",
                    "title": "Year-End Processing",
                    "content": """
# Year-End Processing

At the end of each year, admins must initialize the system for the new year.

## What Year-End Processing Does

1. **Creates New Balance Records**
   - Initializes balances for all active employees
   - Applies annual allocations per policy
   - Applies approved carryover amounts

2. **Generates Market Holidays**
   - Creates holiday calendar for new year
   - Based on standard market holiday rules
   - Considers observed dates

3. **Applies Carryover**
   - Approved carryover requests transfer
   - Shows in new year's balance

## When to Run

**Recommended timing:**
- Early January of the new year
- After all carryover requests are processed
- Before employees submit new year requests

## How to Run

1. Navigate to **Admin** > **Year-End Processing**
2. Click **"Check Status"** to see:
   - Current year status
   - Carryover requests pending
   - Employees to process
3. Review the checklist
4. Click **"Run Year-End Processing"**
5. Confirm the action
6. Wait for completion

## Pre-Processing Checklist

Before running:
- All carryover requests approved/denied
- Database backed up
- Holiday dates verified
- Policy allocations confirmed

## After Processing

Verify:
- New balances show for all employees
- Carryover amounts applied correctly
- Holiday calendar populated
- No error messages

## Troubleshooting

**Processing Fails:**
- Check error log for details
- Verify database connectivity
- Contact system administrator

**Missing Balances:**
- May indicate inactive employees
- Manually create if needed
- Check employee status

## Best Practices

- Always backup before processing
- Run during low-usage period
- Verify results thoroughly
- Communicate to employees when complete
"""
                },
                {
                    "id": "handbook-management",
                    "title": "Handbook Management",
                    "content": """
# Handbook Management

Admins can update the employee handbook through the system.

## Accessing Handbook Management

From Dashboard: **Admin** > **Handbook Management**

## Updating the Handbook

### Step 1: Prepare Content
- Write or update content in Markdown format
- Organize with headings (#, ##, ###)
- Include all policy information

### Step 2: Upload New Version
1. Go to the **"Update Handbook"** tab
2. Paste your new handbook content
3. Content is in Markdown format
4. Click **"Save New Version"**

### Step 3: Review Changes
The system automatically:
- Compares new vs. current version
- Detects additions, deletions, changes
- Generates AI-powered change summary
- Creates new version number

## Version History

The **"Revision History"** tab shows:
- All previous versions
- Version numbers and dates
- Who made changes
- Change summaries

### Viewing a Version
- Click any version to see full content
- Compare with current version
- Revert if needed

## AI Change Detection

When you save a new version:
- AI analyzes differences
- Summarizes what changed
- Highlights key policy updates
- Makes review easier

## Best Practices

- Review AI summary for accuracy
- Keep version history for compliance
- Notify employees of significant changes
- Use clear Markdown formatting
- Back up before major updates

## Markdown Quick Reference

```
# Main Heading
## Subheading
### Section Header

**Bold text**
*Italic text*

- Bullet point
- Another point

1. Numbered list
2. Second item

| Column 1 | Column 2 |
|----------|----------|
| Data     | More data|
```
"""
                },
                {
                    "id": "system-settings",
                    "title": "System Settings & Backup",
                    "content": """
# System Settings & Backup

Admins have access to system configuration and database management.

## System Page

Access via **Admin** > **System** from the Dashboard.

## Database Backup

### Creating a Backup
1. Go to System settings
2. Click **"Backup Now"**
3. Backup file is created
4. Download for safekeeping

### Backup Best Practices
- Backup before major changes
- Backup before year-end processing
- Schedule regular backups
- Store backups securely offsite

## Email Configuration

Email is used for:
- PTO request notifications
- Password reset requests
- Report delivery

### Configuration
Set in environment variables:
```
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=username
SMTP_PASSWORD=password
SMTP_FROM=noreply@company.com
```

### Testing Email
1. Try password reset function
2. Verify emails are received
3. Check server logs for errors

## Session Settings

Control user session behavior:
- **Timeout Duration** - How long before automatic logout
- Default is typically 30 minutes
- Warning appears before expiration

## Audit Log

Track system activity:
- User logins
- PTO submissions and approvals
- Admin actions
- System changes

Access via **Reports** > **Audit Log**

## Troubleshooting

### Common Issues

**Users Can't Log In:**
- Check account is active
- Verify credentials
- Check for account lockout

**Emails Not Sending:**
- Verify SMTP configuration
- Check firewall allows outbound SMTP
- Review server logs

**Performance Issues:**
- Check database size
- Clear old audit logs
- Review system resources

## Getting Help

For system issues:
1. Check this Help documentation
2. Review error logs
3. Contact your IT support
4. Report issues to system vendor
"""
                }
            ]
        },
        "technical": {
            "title": "Technical Reference",
            "icon": "settings",
            "order": 8,
            "articles": [
                {
                    "id": "environment-setup",
                    "title": "Environment Configuration",
                    "content": """
# Environment Configuration

The TJM Time Calendar uses environment variables for configuration.

## The .env File

Create a `.env` file in the application root with these settings:

## Required Settings

```
# Security - Generate a unique secret key
SECRET_KEY=your-unique-secret-key-here

# Debug Mode - Set to false in production
DEBUG=false

# Database - SQLite is default
DATABASE_URL=sqlite:///tjm_calendar.db
```

## Email Settings (Optional)

For notifications and password reset:

```
# SMTP Configuration
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=email@company.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@company.com
```

### Provider Examples

**Gmail:**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```
Note: Use App Passwords, not your regular password.

**Microsoft 365:**
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
```

## AI Features (Optional)

For Handbook AI Assistant:

```
# Anthropic API Key
ANTHROPIC_API_KEY=your-api-key-here
```

## Session Settings

```
# Session timeout in minutes (default: 30)
SESSION_TIMEOUT_MINUTES=30
```

## Production Checklist

- Set DEBUG=false
- Generate strong SECRET_KEY
- Configure HTTPS (via reverse proxy)
- Configure SMTP for notifications
- Schedule database backup
- Configure log rotation
"""
                },
                {
                    "id": "troubleshooting",
                    "title": "Troubleshooting Guide",
                    "content": """
# Troubleshooting Guide

Common issues and their solutions.

## Login Issues

### Can't Log In
- **Check username**: Is it your email?
- **Check Caps Lock**: Passwords are case-sensitive
- **Try password reset**: Link on login page
- **Account deactivated?**: Contact admin

### Session Expired Frequently
- Check SESSION_TIMEOUT_MINUTES setting
- Clear browser cookies
- Check for clock sync issues

### Password Reset Not Working
- Check email spam folder
- Verify SMTP configuration
- Reset link expires after 1 hour

## Display Issues

### Page Not Loading
- Clear browser cache (Ctrl+Shift+Delete)
- Try different browser
- Check network connectivity
- Review server logs

### Dark Mode Issues
- Toggle dark mode off/on
- Clear browser storage
- Try different browser

### Calendar Not Showing Events
- Refresh the page (F5)
- Check date filters
- Verify data exists for the period

## Data Issues

### Balance Seems Wrong
- Check pending requests (reserved but not approved)
- Review recent approvals
- Check carryover amounts
- Contact admin for adjustment

### Request Not Appearing
- Refresh the page
- Check filter settings
- Verify it was submitted successfully
- Check for error messages

### Reports Empty
- Verify year selection
- Check department filter
- Ensure data exists for period

## Email Issues

### Not Receiving Notifications
- Check spam/junk folder
- Verify email address is correct
- Check SMTP configuration
- Review server error logs

### Password Reset Email Not Received
- Check all email folders
- Try again (generates new link)
- Verify email is in system
- Check SMTP settings

## Error Messages

### "Access Denied"
- You don't have permission for this action
- Check your user role
- Contact admin if incorrect

### "Session Expired"
- Log in again
- Increase timeout if frequent

### "Request Failed"
- Check network connection
- Try again
- Contact admin if persists

## Getting More Help

1. **Check this documentation** thoroughly
2. **Review server logs** for error details
3. **Contact your IT administrator**
4. **Document the issue**: Steps to reproduce, error messages, screenshots
"""
                },
                {
                    "id": "keyboard-shortcuts",
                    "title": "Keyboard Shortcuts",
                    "content": """
# Keyboard Shortcuts

Navigate the system efficiently with keyboard shortcuts.

## Login Page
- **Enter** - Submit login form
- **Tab** - Move between fields

## General Navigation
- **Escape** - Close dialogs and popups
- **Enter** - Submit forms / Confirm actions
- **Tab** - Navigate between elements

## Dialog Windows
- **Escape** - Close dialog
- **Enter** - Confirm default action
- **Tab** - Navigate buttons

## Forms
- **Tab** - Next field
- **Shift+Tab** - Previous field
- **Enter** - Submit (where applicable)

## Calendar
- **Arrow buttons** - Navigate months
- **Click** - Select dates

## Tables
- **Click column header** - Sort by column
- **Click row** - Select/view details

## Accessibility Features

The system includes:
- Proper focus indicators
- Screen reader support
- ARIA labels on buttons
- Keyboard-accessible controls
- Tab order for forms

## Tips

- Use Tab to navigate forms quickly
- Press Enter to submit after filling forms
- Use Escape to cancel dialogs
- Use browser back button cautiously (may lose data)
"""
                }
            ]
        }
    }

    @classmethod
    def get_all_chapters(cls) -> List[Dict]:
        """Get all chapters with metadata (without full content)."""
        chapters = []
        for chapter_id, chapter in cls.CHAPTERS.items():
            chapters.append({
                "id": chapter_id,
                "title": chapter["title"],
                "icon": chapter["icon"],
                "order": chapter["order"],
                "article_count": len(chapter["articles"]),
                "articles": [
                    {"id": a["id"], "title": a["title"]}
                    for a in chapter["articles"]
                ]
            })
        return sorted(chapters, key=lambda x: x["order"])

    @classmethod
    def get_chapter(cls, chapter_id: str) -> Optional[Dict]:
        """Get a specific chapter with all articles."""
        chapter = cls.CHAPTERS.get(chapter_id)
        if not chapter:
            return None
        return {
            "id": chapter_id,
            "title": chapter["title"],
            "icon": chapter["icon"],
            "articles": chapter["articles"]
        }

    @classmethod
    def get_article(cls, chapter_id: str, article_id: str) -> Optional[Dict]:
        """Get a specific article."""
        chapter = cls.CHAPTERS.get(chapter_id)
        if not chapter:
            return None
        for article in chapter["articles"]:
            if article["id"] == article_id:
                return {
                    "chapter_id": chapter_id,
                    "chapter_title": chapter["title"],
                    **article
                }
        return None

    @classmethod
    def search(cls, query: str) -> List[Dict]:
        """
        Search all help content for matching articles.

        Args:
            query: Search term

        Returns:
            List of matching articles with snippets
        """
        if not query or len(query) < 2:
            return []

        query_lower = query.lower()
        results = []

        for chapter_id, chapter in cls.CHAPTERS.items():
            for article in chapter["articles"]:
                # Search in title and content
                title_match = query_lower in article["title"].lower()
                content_match = query_lower in article["content"].lower()

                if title_match or content_match:
                    # Extract snippet around match
                    snippet = ""
                    if content_match:
                        content_lower = article["content"].lower()
                        idx = content_lower.find(query_lower)
                        start = max(0, idx - 50)
                        end = min(len(article["content"]), idx + len(query) + 50)
                        snippet = "..." + article["content"][start:end].strip() + "..."

                    results.append({
                        "chapter_id": chapter_id,
                        "chapter_title": chapter["title"],
                        "article_id": article["id"],
                        "article_title": article["title"],
                        "snippet": snippet,
                        "relevance": 2 if title_match else 1
                    })

        # Sort by relevance (title matches first)
        return sorted(results, key=lambda x: -x["relevance"])
