"""
Help documentation service for providing searchable instructional content.
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
# System Overview

The TJM Time Calendar is a comprehensive PTO (Paid Time Off) and leave management system designed for efficient workforce time tracking.

## Key Features

- **PTO Request Management**: Submit, track, and manage time-off requests
- **Calendar View**: Visual calendar showing approved time off and market holidays
- **Balance Tracking**: Real-time PTO balance updates
- **Manager Approval Workflow**: Streamlined approval process for managers
- **Admin Dashboard**: Full system control for administrators

## User Roles

1. **Employee**: Can submit PTO requests and view their balances
2. **Manager**: Can approve/deny requests for their department
3. **Admin**: Full system access including user management
"""
                },
                {
                    "id": "first-login",
                    "title": "First Login",
                    "content": """
# First Login Guide

## Step 1: Access the System

Navigate to the system URL provided by your administrator.

## Step 2: Enter Credentials

Use the credentials provided by your HR department or system administrator:
- **Username**: Your assigned username (usually your email)
- **Password**: Your temporary password

## Step 3: Change Your Password

On first login, you should change your password:
1. Click on your username in the top right corner
2. Select "Change Password"
3. Enter your current password
4. Enter and confirm your new password
5. Click "Save"

## Step 4: Verify Your Information

Review your profile to ensure:
- Your department is correct
- Your manager is properly assigned
- Your PTO balances are accurate
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

## How to Submit

1. Navigate to **My PTO** from the main menu
2. Click the **New Request** button
3. Fill in the request form:
   - **Leave Type**: Select Vacation, Sick, Personal, etc.
   - **Start Date**: First day of your leave
   - **End Date**: Last day of your leave
   - **Notes**: Add any relevant information for your manager
4. Click **Submit Request**

## Important Notes

- Requests require manager approval before they're confirmed
- You cannot request time off if your balance is insufficient
- Overlapping requests are automatically detected
- Weekend days are automatically excluded from business day calculations

## Request Status

- **Pending**: Awaiting manager approval
- **Approved**: Request has been approved
- **Denied**: Request was not approved (check notes for reason)
- **Cancelled**: You cancelled the request
"""
                },
                {
                    "id": "view-balance",
                    "title": "Viewing Your PTO Balance",
                    "content": """
# Viewing Your PTO Balance

## Accessing Your Balance

Your PTO balance is displayed on the **My PTO** page. You can see:

- **Available**: Hours/days currently available to use
- **Used**: Hours/days already taken this year
- **Pending**: Hours/days in pending requests
- **Total Accrued**: Total time earned this year

## Balance Types

Depending on your company's policy, you may see different leave types:

- **Vacation**: Annual vacation time
- **Sick**: Sick leave allocation
- **Personal**: Personal days
- **Floating Holiday**: Flexible holiday days

## Understanding Accrual

Your vacation time accrues based on your tenure:
- Accrual rates increase with years of service
- Check with HR for your specific accrual tier
"""
                },
                {
                    "id": "cancel-request",
                    "title": "Cancelling a Request",
                    "content": """
# Cancelling a PTO Request

## How to Cancel

You can cancel a pending request before it's been approved:

1. Go to **My PTO**
2. Find the request you want to cancel
3. Click the **Cancel** button
4. Confirm the cancellation

## Important Notes

- You can only cancel **Pending** requests
- Once approved, contact your manager to discuss changes
- Cancelled requests restore your balance immediately
"""
                }
            ]
        },
        "calendar": {
            "title": "Calendar",
            "icon": "calendar_month",
            "order": 3,
            "articles": [
                {
                    "id": "calendar-view",
                    "title": "Using the Calendar",
                    "content": """
# Using the Calendar

## Calendar Features

The calendar provides a visual overview of:
- Your approved time off (green)
- Pending requests (yellow)
- Market holidays (red)
- Team members' time off (if enabled)

## Navigation

- Use **<** and **>** arrows to change months
- Click **Today** to return to current date
- Click on a date to see detailed events

## Team Calendar

If you have access to the Team Calendar:
- View all team members' approved time off
- Plan around team availability
- Identify coverage gaps
"""
                },
                {
                    "id": "market-holidays",
                    "title": "Market Holidays",
                    "content": """
# Market Holidays

## What Are Market Holidays?

Market holidays are days when financial markets are closed. These are automatically marked on your calendar.

## Federal Holidays Included

- New Year's Day
- Martin Luther King Jr. Day
- Presidents Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

## How They Affect PTO

- Market holidays don't count against your PTO balance
- When requesting time off, market holidays are automatically excluded
"""
                }
            ]
        },
        "managers": {
            "title": "For Managers",
            "icon": "supervisor_account",
            "order": 4,
            "articles": [
                {
                    "id": "approve-requests",
                    "title": "Approving PTO Requests",
                    "content": """
# Approving PTO Requests

## Accessing Pending Requests

1. Navigate to **Manager Dashboard**
2. View the list of pending requests from your team
3. Click on a request to see details

## Approving a Request

1. Review the request details:
   - Employee name
   - Dates requested
   - Leave type
   - Current balance impact
2. Click **Approve** to approve
3. Optionally add notes for the employee

## Denying a Request

1. Click **Deny** on the request
2. **Required**: Add a reason for denial
3. The employee will be notified

## Best Practices

- Review requests promptly (within 24-48 hours)
- Consider team coverage when approving
- Communicate with employees about any concerns
"""
                },
                {
                    "id": "team-overview",
                    "title": "Team Overview",
                    "content": """
# Team Overview

## Viewing Your Team

The Manager Dashboard shows:
- All employees in your department
- Their current PTO balances
- Upcoming approved time off
- Pending requests

## Team Calendar

Use the Team Calendar to:
- See all approved time off at a glance
- Plan around team availability
- Ensure adequate coverage

## Running Reports

Generate reports on:
- Team PTO usage
- Pending balances
- Historical trends
"""
                }
            ]
        },
        "admin": {
            "title": "Administration",
            "icon": "admin_panel_settings",
            "order": 5,
            "articles": [
                {
                    "id": "user-management",
                    "title": "User Management",
                    "content": """
# User Management

## Adding New Employees

1. Go to **Admin** > **Manage Employees**
2. Click **Add Employee**
3. Fill in the required information:
   - First Name, Last Name
   - Email (used for login)
   - Department
   - Manager (for approval workflow)
   - Role (Employee, Manager, Admin)
   - Start Date
4. Click **Save**

## Editing Employees

1. Find the employee in the list
2. Click **Edit**
3. Modify the necessary fields
4. Click **Save**

## Deactivating Employees

When an employee leaves:
1. Find the employee
2. Click **Deactivate**
3. Confirm the action

Note: Deactivated employees cannot log in but their records are preserved.
"""
                },
                {
                    "id": "department-management",
                    "title": "Department Management",
                    "content": """
# Department Management

## Adding Departments

1. Go to **Admin** > **Departments**
2. Click **Add Department**
3. Enter the department name
4. Click **Save**

## Editing Departments

1. Click **Edit** next to the department
2. Update the name
3. Click **Save**

## Department Considerations

- Employees must belong to a department
- Managers approve requests for their department only
- Consider your org structure when setting up departments
"""
                },
                {
                    "id": "year-end-processing",
                    "title": "Year-End Processing",
                    "content": """
# Year-End Processing

## What Is Year-End Processing?

At the end of each year, the system needs to:
1. Create new PTO balances for the new year
2. Apply approved carryover from the previous year
3. Generate market holidays for the new year

## Running Year-End Processing

1. Go to **Admin** > **Year-End Processing**
2. Click **Check Status** to see current state
3. Review what will be processed
4. Click **Run Year-End Processing** to execute

## Important Notes

- Run this in January of the new year
- Ensure all carryover requests are approved/denied first
- Backup your database before running
- This process creates new balance records for all active employees
"""
                },
                {
                    "id": "handbook-management",
                    "title": "Handbook Management",
                    "content": """
# Handbook Management

## Updating the Handbook

When company policies change:

1. Go to **Admin** > **Handbook Management**
2. Click the **Update Handbook** tab
3. Paste your new handbook content (in Markdown format)
4. Click **Save New Version**

## What Happens

The system will:
- Compare the new content with the current version
- Detect all changes (additions, deletions, modifications)
- Generate an AI-powered summary of changes
- Create a new version number automatically

## Viewing History

The **Revision History** tab shows:
- All previous versions
- Change summaries for each version
- Who made the changes and when

## Best Practices

- Review the AI-generated summary for accuracy
- Notify employees of significant policy changes
- Keep records of why changes were made
"""
                }
            ]
        },
        "technical": {
            "title": "Technical Setup",
            "icon": "settings",
            "order": 6,
            "articles": [
                {
                    "id": "email-setup",
                    "title": "Email (SMTP) Setup",
                    "content": """
# Email (SMTP) Setup

## Why Configure Email?

Email notifications are sent for:
- PTO request approvals/denials
- Password reset requests
- Important system announcements

## Configuration Steps

1. Open your `.env` file (or environment variables)
2. Set the following values:

```
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@company.com
```

## Common SMTP Providers

### Gmail
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```
Note: Use an "App Password" not your regular password.

### Microsoft 365
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
```

### Amazon SES
```
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
```

## Testing

After configuration:
1. Try a password reset to test
2. Check server logs for any errors
3. Verify emails are received
"""
                },
                {
                    "id": "database-backup",
                    "title": "Database Backup",
                    "content": """
# Database Backup

## Why Backup?

Regular backups protect against:
- Data loss from hardware failure
- Accidental deletions
- Corruption issues

## Running a Backup

From the command line:

```bash
python scripts/backup_db.py
```

Options:
- `--keep 30`: Keep last 30 backups (default: 7)
- Output: Creates timestamped backup in `backups/` folder

## Automating Backups

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 2 AM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `scripts/backup_db.py --keep 30`

### Linux Cron
```bash
# Add to crontab (crontab -e)
0 2 * * * cd /path/to/app && python scripts/backup_db.py --keep 30
```

## Restoring from Backup

1. Stop the application
2. Copy backup file to replace `pto_calendar.db`
3. Restart the application
"""
                },
                {
                    "id": "environment-config",
                    "title": "Environment Configuration",
                    "content": """
# Environment Configuration

## The .env File

The application uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

## Required Settings

```
# Security
SECRET_KEY=your-secret-key-here
DEBUG=false

# Database
DATABASE_URL=sqlite:///pto_calendar.db
```

## Optional Settings

```
# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
SMTP_FROM=noreply@example.com

# AI Features (for handbook diff)
ANTHROPIC_API_KEY=your-api-key

# Session
SESSION_TIMEOUT_MINUTES=30
```

## Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Generate a strong `SECRET_KEY`
- [ ] Configure SMTP for notifications
- [ ] Set up database backups
- [ ] Configure HTTPS (via reverse proxy)
"""
                },
                {
                    "id": "troubleshooting",
                    "title": "Troubleshooting",
                    "content": """
# Troubleshooting

## Common Issues

### Can't Log In
- Verify username/email is correct
- Check Caps Lock
- Try password reset
- Contact admin if account may be deactivated

### Email Not Sending
- Check SMTP configuration in `.env`
- Verify SMTP credentials are correct
- Check server logs for errors
- Ensure firewall allows outbound SMTP

### PTO Balance Incorrect
- Check if requests are pending approval
- Verify carryover was applied (new year)
- Contact admin for balance adjustment

### Calendar Not Showing Events
- Refresh the page
- Clear browser cache
- Check if you're viewing the correct month

## Checking Logs

Server logs are located in the `logs/` folder:
- `tjm_calendar.log`: Main application log
- Check for error messages with timestamps

## Getting Help

If issues persist:
1. Note the exact error message
2. Note what steps you took
3. Check the logs
4. Contact your system administrator
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
