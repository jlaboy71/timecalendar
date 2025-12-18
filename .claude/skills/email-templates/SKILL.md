# Email Templates Skill

This skill provides patterns for email template consistency in TJM Time Calendar notifications.

---

## 1. Files to Update Together

**CRITICAL**: When modifying email templates, update ALL THREE locations:

| File | Purpose |
|------|---------|
| `src/services/email_service.py` | Actual email sending functions |
| `nicegui_app/pages/admin_email_preview.py` | Standalone preview page |
| `nicegui_app/pages/admin_system.py` | Embedded preview in System Admin (~line 1006-1150) |

---

## 2. Shared Helper Functions

Import these from `email_service.py` in all files that render emails:

```python
from src.services.email_service import (
    _get_email_template,
    _get_pto_type_icon,
    _format_date_range_with_days
)
```

### Helper Function Reference

#### `_get_pto_type_icon(pto_type: str) -> str`
Returns emoji for PTO type:
```python
icons = {
    'vacation': '🏖️',
    'sick': '🏥',
    'personal': '👤',
    'bereavement': '🕯️',
    'fmla': '👨‍👩‍👧',
    'jury_duty': '⚖️',
    'voting': '🗳️',
    'military': '🎖️',
    'chicago_paid_leave': '📍',
    'chicago_leave': '📍',
}
# Default: '📅'
```

#### `_format_date_range_with_days(start_date, end_date) -> str`
Formats dates with day of week:
- Single day: `"Monday, December 16, 2024"`
- Range: `"Monday, December 16 - Wednesday, December 18, 2024"`

#### `_get_email_template(title, title_color, content, footer_text) -> str`
Generates the dark-themed HTML template.

---

## 3. Brand Colors for Emails

```python
# Status colors
STATUS_COLORS = {
    'pending': '#f59e0b',    # Amber
    'approved': '#22c55e',   # Green
    'denied': '#ef4444',     # Red
    'cancelled': '#6b7280',  # Gray
}

# PTO type colors
TYPE_COLORS = {
    'vacation': '#3b82f6',   # Blue
    'sick': '#22c55e',       # Green
    'personal': '#a855f7',   # Purple
    'bereavement': '#78350f', # Brown
    'chicago_leave': '#f59e0b', # Amber
}

# TJM Brand
TJM_GOLD = '#c9a227'
TJM_GRAY = '#5a6a72'
```

---

## 4. Email Template Structure

```html
<!-- Dark theme base colors -->
Background: #111827 (outer)
Card: #1f2937 (content area)
Footer: #374151 (bottom bar)
Text: #e5e7eb (primary)
Muted: #9ca3af (secondary)
```

### Template Pattern
```python
def send_notification(to_email: str, data: dict) -> bool:
    # 1. Determine title and color based on action
    title = "PTO Request Approved"
    title_color = STATUS_COLORS['approved']

    # 2. Build content HTML
    icon = _get_pto_type_icon(data['pto_type'])
    date_range = _format_date_range_with_days(data['start_date'], data['end_date'])

    content = f"""
    <p style="font-size: 16px; margin-bottom: 20px;">
        Your {icon} <strong>{data['pto_type'].title()}</strong> request has been approved.
    </p>

    <div style="background-color: #374151; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin: 0 0 10px 0;"><strong>Dates:</strong> {date_range}</p>
        <p style="margin: 0;"><strong>Duration:</strong> {data['total_days']} day(s)</p>
    </div>
    """

    # 3. Generate full template
    html_body = _get_email_template(title, title_color, content)

    # 4. Send
    return self._send_email(to_email, f"PTO {title}", html_body)
```

---

## 5. Email Types & Titles

| Event | Title | Color | Recipient |
|-------|-------|-------|-----------|
| Request Submitted | "New PTO Request" | Amber | Manager |
| Request Approved | "PTO Request Approved" | Green | Employee |
| Request Denied | "PTO Request Denied" | Red | Employee |
| Request Cancelled | "PTO Request Cancelled" | Gray | Manager |
| Trusted Auto-Approve | "PTO Auto-Approved" | Green | Manager (FYI) |
| Carryover Requested | "Carryover Request" | Amber | Manager |
| Carryover Approved | "Carryover Approved" | Green | Employee |
| Year-End Summary | "Year-End Processing" | TJM Gold | Admin |

---

## 6. Content Block Styles

### Info Box (Gray Background)
```html
<div style="background-color: #374151; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
    <p style="margin: 0;">Content here</p>
</div>
```

### Status Badge
```html
<span style="background-color: {status_color}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: 600;">
    {status.upper()}
</span>
```

### Left Border Accent
```html
<div style="border-left: 4px solid {color}; padding-left: 15px; margin-bottom: 15px;">
    <p style="margin: 0;">Highlighted content</p>
</div>
```

### Action Button
```html
<a href="{url}" style="display: inline-block; background-color: #c9a227; color: #111827; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
    View Request
</a>
```

---

## 7. Table Formatting

```html
<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
    <tr style="border-bottom: 1px solid #374151;">
        <td style="padding: 10px 0; color: #9ca3af; width: 40%;">Employee</td>
        <td style="padding: 10px 0; color: #e5e7eb;">{employee_name}</td>
    </tr>
    <tr style="border-bottom: 1px solid #374151;">
        <td style="padding: 10px 0; color: #9ca3af;">Type</td>
        <td style="padding: 10px 0; color: #e5e7eb;">{icon} {pto_type}</td>
    </tr>
    <tr>
        <td style="padding: 10px 0; color: #9ca3af;">Dates</td>
        <td style="padding: 10px 0; color: #e5e7eb;">{date_range}</td>
    </tr>
</table>
```

---

## 8. Environment Configuration

```bash
# .env file settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@tjm.com
SMTP_PASSWORD=secret
EMAIL_FROM=noreply@tjm.com
EMAIL_FROM_NAME=TJM Calendar
EMAIL_ENABLED=true
```

### Configuration Check
```python
def is_configured(self) -> bool:
    return bool(
        self.enabled and
        self.smtp_host and
        self.smtp_user and
        self.smtp_password
    )
```

---

## 9. Testing Email Templates

### Preview in Admin UI
1. Navigate to System Administration
2. Click "Email Config" tab
3. Use template preview dropdown
4. Verify appearance matches expected

### Send Test Email
```python
email_service = EmailService()
if email_service.is_configured():
    email_service.send_pto_submitted_notification(
        to_email="test@example.com",
        employee_name="Test User",
        pto_type="vacation",
        start_date=date.today(),
        end_date=date.today(),
        total_days=Decimal("1.00"),
        notes="Test request"
    )
```

---

## 10. Common Pitfalls

### 1. Inconsistent Updates
```python
# WRONG: Only updating email_service.py
# Other preview locations will show old template

# RIGHT: Update all 3 files together
# 1. email_service.py
# 2. admin_email_preview.py
# 3. admin_system.py (embedded preview)
```

### 2. Missing Icons for New Types
```python
# When adding new PTO type, update _get_pto_type_icon:
icons['new_type'] = '🆕'  # Add entry
# Default '📅' used if missing
```

### 3. Hard-coded Colors
```python
# WRONG: Hard-coded hex in content
content = '<p style="color: #22c55e;">Approved</p>'

# RIGHT: Use status color variable
content = f'<p style="color: {STATUS_COLORS["approved"]};">Approved</p>'
```

### 4. Missing Null Checks
```python
# WRONG: Assuming notes exist
content = f"<p>Notes: {data['notes']}</p>"

# RIGHT: Handle optional fields
if data.get('notes'):
    content += f"<p>Notes: {data['notes']}</p>"
```
