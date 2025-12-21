# Feature: Trusted Employee Auto-Approve with Manager Email Digest

**Priority:** High  
**Created:** December 13, 2025  
**Status:** Planned  

---

## Overview

Add a "Trusted Employee" designation that allows managers to grant specific employees the ability to have their **standard PTO requests** (Vacation, Sick, Personal only) auto-approved, while maintaining accountability through mandatory email notifications to managers with configurable digest frequency and export format options.

### Scope Limitations

**AUTO-APPROVE ELIGIBLE (when trusted):**
- ✅ Vacation
- ✅ Sick
- ✅ Personal

**ALWAYS REQUIRES MANAGER APPROVAL (regardless of trust status):**
- ❌ Bereavement
- ❌ FMLA
- ❌ Jury Duty
- ❌ Voting
- ❌ Military Leave
- ❌ Work From Home / Remote Schedule requests

These special leave types require documentation, have legal/compliance implications, or need manager coordination - they cannot be auto-approved even for trusted employees.

---

## Business Requirements

### 1. Trusted Employee Designation

- Managers can mark individual employees as "trusted" via a checkbox in employee management
- Trusted employees' **Vacation, Sick, and Personal** requests auto-approve immediately upon submission
- **All other leave types** (Bereavement, FMLA, Jury Duty, Voting, Military) **always require approval** regardless of trust status
- **Work From Home / Remote Schedule** requests **always require approval** regardless of trust status
- The employee is still expected to submit truthful requests (honor system)
- Trust designation can be revoked at any time by the manager
- Audit trail must track when trust was granted/revoked and by whom

### 2. Mandatory Manager Email Notification

- **ALL** PTO submissions must trigger an email notification to the employee's manager
- This applies to both trusted and non-trusted employees
- Email serves as audit trail and keeps manager informed
- Cannot be disabled - this is a compliance requirement

### 3. Manager Email Digest Preferences

Managers can configure their notification frequency:

| Option | Description |
|--------|-------------|
| Immediate | Email sent instantly upon each submission |
| Daily | Summary email sent once per day (configurable time) |
| Weekly | Summary email sent once per week (configurable day/time) |
| Bi-weekly | Summary email sent every two weeks |
| Monthly | Summary email sent on 1st of each month |

### 4. Email Attachment Format Options

Managers can choose their preferred report format:

| Format | Use Case |
|--------|----------|
| PDF | Formatted report for printing/archiving |
| CSV | Data export for spreadsheet analysis |
| HTML | Inline email content or attachment |

---

## Technical Specification

### Database Changes

#### 1. Add to `User` model (`src/models/user.py`)

```python
# New fields
is_trusted = Column(Boolean, default=False, nullable=False)
trusted_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
trusted_at = Column(DateTime, nullable=True)
```

#### 2. Create new `ManagerNotificationPreference` model

```python
# New file: src/models/manager_notification_preference.py

class ManagerNotificationPreference(Base):
    __tablename__ = 'manager_notification_preferences'
    
    id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # Frequency: 'immediate', 'daily', 'weekly', 'biweekly', 'monthly'
    digest_frequency = Column(String(20), default='immediate', nullable=False)
    
    # For daily/weekly digests - preferred send time (hour in 24h format)
    preferred_hour = Column(Integer, default=8)  # 8 AM default
    
    # For weekly digest - preferred day (0=Monday, 6=Sunday)
    preferred_day = Column(Integer, default=0)  # Monday default
    
    # Export format: 'pdf', 'csv', 'html'
    export_format = Column(String(10), default='pdf', nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manager = relationship('User', back_populates='notification_preference')
```

#### 3. Create `PendingNotification` model for digest queue

```python
# New file: src/models/pending_notification.py

class PendingNotification(Base):
    __tablename__ = 'pending_notifications'
    
    id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    pto_request_id = Column(Integer, ForeignKey('pto_requests.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    manager = relationship('User')
    pto_request = relationship('PTORequest')
```

### Migration File

Create: `alembic/versions/xxxx_add_trusted_employee_and_notifications.py`

```python
"""Add trusted employee and manager notification preferences

Revision ID: xxxx
Revises: 778c50a4fe1c
Create Date: 2025-12-13
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add trusted employee fields to users table
    op.add_column('users', sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('trusted_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('users', sa.Column('trusted_at', sa.DateTime(), nullable=True))
    
    # Create manager notification preferences table
    op.create_table(
        'manager_notification_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('users.id'), unique=True, nullable=False),
        sa.Column('digest_frequency', sa.String(20), nullable=False, server_default='immediate'),
        sa.Column('preferred_hour', sa.Integer(), server_default='8'),
        sa.Column('preferred_day', sa.Integer(), server_default='0'),
        sa.Column('export_format', sa.String(10), nullable=False, server_default='pdf'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Create pending notifications queue table
    op.create_table(
        'pending_notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('manager_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('pto_request_id', sa.Integer(), sa.ForeignKey('pto_requests.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('sent', sa.Boolean(), server_default='0'),
        sa.Column('sent_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_pending_notifications_manager_sent', 'pending_notifications', ['manager_id', 'sent'])

def downgrade():
    op.drop_table('pending_notifications')
    op.drop_table('manager_notification_preferences')
    op.drop_column('users', 'trusted_at')
    op.drop_column('users', 'trusted_by_id')
    op.drop_column('users', 'is_trusted')
```

---

### Service Layer Changes

#### 1. Update `PTOService.create_request()` (`src/services/pto_service.py`)

```python
# PTO types eligible for trusted auto-approve
TRUSTED_AUTO_APPROVE_TYPES = {'vacation', 'sick', 'personal'}

# PTO types that ALWAYS require manager approval
ALWAYS_REQUIRES_APPROVAL = {'bereavement', 'fmla', 'jury_duty', 'voting', 'military'}

def create_request(self, request_data: PTORequestCreate, user_id: int) -> PTORequest:
    """Create PTO request with trusted employee auto-approve logic."""
    
    # ... existing validation code ...
    
    # Get the user and their manager
    user = self.db.execute(select(User).where(User.id == user_id)).scalar_one()
    
    # Determine if auto-approve applies
    auto_approve = False
    pto_type_lower = request_data.pto_type.lower()
    
    # Manager/Admin/Superadmin: auto-approve standard PTO types only
    if user.role in ['manager', 'admin', 'superadmin']:
        if pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
            auto_approve = True
        # Special leave types still need documentation/approval even for managers
    
    # Trusted Employee: auto-approve ONLY for vacation, sick, personal
    elif user.is_trusted and pto_type_lower in TRUSTED_AUTO_APPROVE_TYPES:
        auto_approve = True
    
    # All other combinations: requires approval
    # - Non-trusted employees: always pending
    # - Bereavement, FMLA, Jury Duty, Voting, Military: always pending
    # - Work From Home requests: always pending (handled separately)
    
    # Create the request
    new_request = PTORequest(
        user_id=user_id,
        pto_type=request_data.pto_type,
        start_date=request_data.start_date,
        end_date=request_data.end_date,
        total_days=total_days,
        status='approved' if auto_approve else 'pending',
        submitted_at=datetime.now(),
        approved_at=datetime.now() if auto_approve else None,
        approved_by=user_id if auto_approve else None,  # Self-approved
        notes=request_data.notes
    )
    
    # ... existing balance update code ...
    
    # MANDATORY: Queue notification for manager (ALL requests, regardless of type)
    self._queue_manager_notification(new_request, user)
    
    return new_request

def _queue_manager_notification(self, request: PTORequest, employee: User):
    """Queue or send immediate notification to manager."""
    
    # Get the employee's manager (via department)
    manager = self._get_employee_manager(employee)
    if not manager:
        return  # No manager to notify
    
    # Get manager's notification preferences
    notification_service = NotificationService(self.db)
    prefs = notification_service.get_manager_preferences(manager.id)
    
    if prefs.digest_frequency == 'immediate':
        # Send immediately
        notification_service.send_immediate_notification(manager, request, employee)
    else:
        # Queue for digest
        notification_service.queue_notification(manager.id, request.id)
```

#### 2. Create `NotificationService` (`src/services/notification_service.py`)

```python
"""Manager notification service for PTO request alerts."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.models.user import User
from src.models.pto_request import PTORequest
from src.models.manager_notification_preference import ManagerNotificationPreference
from src.models.pending_notification import PendingNotification
from src.services.email_service import EmailService
from src.services.report_export_service import ReportExportService


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.export_service = ReportExportService(db)
    
    def get_manager_preferences(self, manager_id: int) -> ManagerNotificationPreference:
        """Get or create default notification preferences for manager."""
        stmt = select(ManagerNotificationPreference).where(
            ManagerNotificationPreference.manager_id == manager_id
        )
        prefs = self.db.execute(stmt).scalar_one_or_none()
        
        if not prefs:
            prefs = ManagerNotificationPreference(manager_id=manager_id)
            self.db.add(prefs)
            self.db.commit()
        
        return prefs
    
    def update_preferences(self, manager_id: int, 
                          digest_frequency: str = None,
                          preferred_hour: int = None,
                          preferred_day: int = None,
                          export_format: str = None) -> ManagerNotificationPreference:
        """Update manager notification preferences."""
        prefs = self.get_manager_preferences(manager_id)
        
        if digest_frequency:
            prefs.digest_frequency = digest_frequency
        if preferred_hour is not None:
            prefs.preferred_hour = preferred_hour
        if preferred_day is not None:
            prefs.preferred_day = preferred_day
        if export_format:
            prefs.export_format = export_format
        
        prefs.updated_at = datetime.utcnow()
        self.db.commit()
        return prefs
    
    def queue_notification(self, manager_id: int, pto_request_id: int):
        """Add notification to digest queue."""
        notification = PendingNotification(
            manager_id=manager_id,
            pto_request_id=pto_request_id
        )
        self.db.add(notification)
        self.db.commit()
    
    def send_immediate_notification(self, manager: User, request: PTORequest, employee: User):
        """Send immediate email notification for a single request."""
        subject = f"PTO Request: {employee.full_name} - {request.pto_type.title()}"
        
        status_text = "Auto-Approved (Trusted)" if request.status == 'approved' else "Pending Your Approval"
        
        body = f"""
        New PTO Request Submitted
        
        Employee: {employee.full_name}
        Type: {request.pto_type.title()}
        Dates: {request.start_date} to {request.end_date}
        Days: {request.total_days}
        Status: {status_text}
        
        {'This employee is marked as TRUSTED. Request was auto-approved.' if employee.is_trusted else 'Please review and approve/deny this request.'}
        """
        
        self.email_service.send_email(
            to_email=manager.email,
            subject=subject,
            body=body
        )
    
    def process_digests(self):
        """Process all pending digest notifications. Call from scheduler."""
        # Get all managers with pending notifications
        stmt = select(PendingNotification.manager_id).where(
            PendingNotification.sent == False
        ).distinct()
        
        manager_ids = [row[0] for row in self.db.execute(stmt).fetchall()]
        
        for manager_id in manager_ids:
            prefs = self.get_manager_preferences(manager_id)
            
            if self._should_send_digest(prefs):
                self._send_digest(manager_id, prefs)
    
    def _should_send_digest(self, prefs: ManagerNotificationPreference) -> bool:
        """Check if it's time to send digest based on preferences."""
        now = datetime.now()
        
        if prefs.digest_frequency == 'daily':
            return now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'weekly':
            return now.weekday() == prefs.preferred_day and now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'biweekly':
            # Send on 1st and 15th
            return now.day in [1, 15] and now.hour == prefs.preferred_hour
        elif prefs.digest_frequency == 'monthly':
            return now.day == 1 and now.hour == prefs.preferred_hour
        
        return False
    
    def _send_digest(self, manager_id: int, prefs: ManagerNotificationPreference):
        """Send digest email with all pending notifications."""
        # Get pending notifications
        stmt = select(PendingNotification).where(
            PendingNotification.manager_id == manager_id,
            PendingNotification.sent == False
        )
        pending = self.db.execute(stmt).scalars().all()
        
        if not pending:
            return
        
        # Get manager
        manager = self.db.execute(select(User).where(User.id == manager_id)).scalar_one()
        
        # Get all PTO requests
        request_ids = [p.pto_request_id for p in pending]
        requests = self.db.execute(
            select(PTORequest).where(PTORequest.id.in_(request_ids))
        ).scalars().all()
        
        # Generate report in preferred format
        attachment = self.export_service.generate_pto_digest(
            requests=requests,
            format=prefs.export_format
        )
        
        # Send email
        subject = f"PTO Request Digest - {len(requests)} Request(s)"
        body = f"Please find attached your PTO request digest containing {len(requests)} request(s)."
        
        self.email_service.send_email_with_attachment(
            to_email=manager.email,
            subject=subject,
            body=body,
            attachment=attachment,
            filename=f"pto_digest.{prefs.export_format}"
        )
        
        # Mark as sent
        for notification in pending:
            notification.sent = True
            notification.sent_at = datetime.utcnow()
        
        self.db.commit()
```

#### 3. Create `ReportExportService` (`src/services/report_export_service.py`)

```python
"""Export service for generating PTO reports in various formats."""

from datetime import datetime
from typing import List
from io import BytesIO
from sqlalchemy.orm import Session

from src.models.pto_request import PTORequest


class ReportExportService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_pto_digest(self, requests: List[PTORequest], format: str) -> BytesIO:
        """Generate PTO digest report in specified format."""
        if format == 'pdf':
            return self._generate_pdf(requests)
        elif format == 'csv':
            return self._generate_csv(requests)
        elif format == 'html':
            return self._generate_html(requests)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _generate_pdf(self, requests: List[PTORequest]) -> BytesIO:
        """Generate PDF report."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        elements.append(Paragraph(f"PTO Request Digest - {datetime.now().strftime('%Y-%m-%d')}", styles['Heading1']))
        
        # Table data
        data = [['Employee', 'Type', 'Start Date', 'End Date', 'Days', 'Status']]
        for req in requests:
            data.append([
                req.user.full_name,
                req.pto_type.title(),
                str(req.start_date),
                str(req.end_date),
                str(req.total_days),
                req.status.title()
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def _generate_csv(self, requests: List[PTORequest]) -> BytesIO:
        """Generate CSV report."""
        import csv
        
        buffer = BytesIO()
        # Write as string first, then encode
        import io
        string_buffer = io.StringIO()
        
        writer = csv.writer(string_buffer)
        writer.writerow(['Employee', 'Type', 'Start Date', 'End Date', 'Days', 'Status', 'Trusted'])
        
        for req in requests:
            writer.writerow([
                req.user.full_name,
                req.pto_type,
                req.start_date.isoformat(),
                req.end_date.isoformat(),
                float(req.total_days),
                req.status,
                'Yes' if req.user.is_trusted else 'No'
            ])
        
        buffer.write(string_buffer.getvalue().encode('utf-8'))
        buffer.seek(0)
        return buffer
    
    def _generate_html(self, requests: List[PTORequest]) -> BytesIO:
        """Generate HTML report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PTO Digest - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #5a6a72; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th {{ background-color: #c9a227; color: white; padding: 10px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .trusted {{ color: #2e7d32; font-weight: bold; }}
                .pending {{ color: #f57c00; }}
                .approved {{ color: #2e7d32; }}
            </style>
        </head>
        <body>
            <h1>PTO Request Digest</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <table>
                <tr>
                    <th>Employee</th>
                    <th>Type</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Days</th>
                    <th>Status</th>
                </tr>
        """
        
        for req in requests:
            status_class = req.status
            trusted_badge = ' <span class="trusted">[TRUSTED]</span>' if req.user.is_trusted else ''
            html += f"""
                <tr>
                    <td>{req.user.full_name}{trusted_badge}</td>
                    <td>{req.pto_type.title()}</td>
                    <td>{req.start_date}</td>
                    <td>{req.end_date}</td>
                    <td>{req.total_days}</td>
                    <td class="{status_class}">{req.status.title()}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        buffer = BytesIO()
        buffer.write(html.encode('utf-8'))
        buffer.seek(0)
        return buffer
```

---

### UI Changes

#### 1. Manager Settings Page - Notification Preferences

**File:** `nicegui_app/pages/manager_settings.py` (new file)

Add a new settings section for managers to configure their notification preferences:

```python
@ui.page('/manager/settings')
def manager_settings_page():
    """Manager settings including notification preferences."""
    if not require_auth():
        return
    
    apply_dark_mode()
    user = app.storage.general.get('user')
    
    if user.get('role') not in ['manager', 'admin', 'superadmin']:
        ui.notify('Access denied', type='negative')
        ui.navigate.to('/dashboard')
        return
    
    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
        page_header(title='MANAGER SETTINGS', show_back=True)
        
        # Notification Preferences Card
        with ui.card().classes('w-full p-4'):
            ui.label('PTO Notification Preferences').classes('text-xl font-bold mb-4')
            
            # Digest Frequency
            ui.label('Email Frequency').classes('font-semibold')
            frequency = ui.select(
                options={
                    'immediate': 'Immediate (each request)',
                    'daily': 'Daily Digest',
                    'weekly': 'Weekly Digest',
                    'biweekly': 'Bi-weekly Digest',
                    'monthly': 'Monthly Digest'
                },
                value='immediate'
            ).classes('w-full mb-4')
            
            # Preferred time (for digest options)
            with ui.row().classes('w-full gap-4'):
                preferred_hour = ui.select(
                    label='Preferred Hour',
                    options={str(h): f"{h}:00" for h in range(24)},
                    value='8'
                ).classes('flex-1')
                
                preferred_day = ui.select(
                    label='Preferred Day (for weekly)',
                    options={
                        '0': 'Monday', '1': 'Tuesday', '2': 'Wednesday',
                        '3': 'Thursday', '4': 'Friday', '5': 'Saturday', '6': 'Sunday'
                    },
                    value='0'
                ).classes('flex-1')
            
            # Export Format
            ui.label('Report Format').classes('font-semibold mt-4')
            export_format = ui.select(
                options={
                    'pdf': 'PDF (Formatted Report)',
                    'csv': 'CSV (Spreadsheet Data)',
                    'html': 'HTML (Web Format)'
                },
                value='pdf'
            ).classes('w-full mb-4')
            
            # Save button
            ui.button('Save Preferences', on_click=lambda: save_preferences()).props('color=primary')
```

#### 2. Employee Management - Trust Checkbox

**Update:** `nicegui_app/pages/admin/employees.py`

Add trust toggle in employee edit dialog:

```python
# In the employee edit dialog, add:
with ui.row().classes('w-full items-center gap-2 mt-4 p-3 bg-amber-50 rounded'):
    ui.icon('verified_user', color='amber')
    trust_checkbox = ui.checkbox('Trusted Employee (auto-approve standard PTO)')
    trust_checkbox.value = employee.is_trusted
    
    with ui.tooltip():
        ui.html('''
            <div style="max-width: 300px;">
                <b>Auto-approve applies to:</b><br>
                ✅ Vacation<br>
                ✅ Sick<br>
                ✅ Personal<br><br>
                <b>Still requires approval:</b><br>
                ❌ Bereavement<br>
                ❌ FMLA<br>
                ❌ Jury Duty / Voting / Military<br>
                ❌ Work From Home<br><br>
                Manager still receives email notification for ALL requests.
            </div>
        ''')
```

---

### Scheduler Setup

For digest emails, add to `nicegui_app/main.py`:

```python
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Initialize scheduler
scheduler = AsyncIOScheduler()

def process_notification_digests():
    """Run hourly to check and send digest emails."""
    db = next(get_db())
    try:
        notification_service = NotificationService(db)
        notification_service.process_digests()
    finally:
        db.close()

# Schedule hourly check
scheduler.add_job(process_notification_digests, 'interval', hours=1)
scheduler.start()
```

---

## Testing Checklist

### Trust Designation
- [ ] Trusted employee checkbox saves correctly to database
- [ ] Audit log captures trust grant/revoke actions
- [ ] Revoking trust does not affect existing approved requests

### Auto-Approve Logic (Trusted Employees)
- [ ] ✅ Vacation requests auto-approve for trusted employees
- [ ] ✅ Sick requests auto-approve for trusted employees
- [ ] ✅ Personal requests auto-approve for trusted employees
- [ ] ❌ Bereavement requests remain PENDING for trusted employees
- [ ] ❌ FMLA requests remain PENDING for trusted employees
- [ ] ❌ Jury Duty requests remain PENDING for trusted employees
- [ ] ❌ Voting requests remain PENDING for trusted employees
- [ ] ❌ Military requests remain PENDING for trusted employees
- [ ] ❌ Work From Home requests remain PENDING for trusted employees

### Non-Trusted Employees
- [ ] All PTO requests remain pending for non-trusted employees
- [ ] Standard approval workflow functions correctly

### Manager/Admin Behavior
- [ ] Manager Vacation/Sick/Personal auto-approve (existing behavior)
- [ ] Manager special leave types (Bereavement, FMLA, etc.) remain pending

### Notifications
- [ ] Immediate notifications send on request submission (all types)
- [ ] Daily/weekly/monthly digests accumulate correctly
- [ ] Digest emails send at configured time
- [ ] Manager can update notification preferences

### Export Formats
- [ ] PDF export generates correctly formatted report
- [ ] CSV export contains all required fields
- [ ] HTML export renders properly

---

## Security Considerations

1. **Audit Trail**: All trust designations must be logged with timestamp and granting user
2. **Manager Only**: Only managers/admins can designate trusted employees
3. **Department Scope**: Managers can only trust employees in their department
4. **Notification Integrity**: Managers cannot disable notifications entirely - compliance requirement
5. **Email Security**: Digest attachments should not contain sensitive data beyond what's needed
6. **Special Leave Protection**: Bereavement, FMLA, Jury Duty, Voting, and Military leave types are excluded from auto-approve because:
   - **Bereavement**: May require documentation; manager needs awareness for team coverage
   - **FMLA**: Legal compliance requirements; requires certification and tracking
   - **Jury Duty**: Requires summons documentation; affects scheduling
   - **Voting**: Time-limited by law; manager coordination needed
   - **Military**: USERRA compliance; documentation required
7. **Work From Home**: Remote schedule changes affect team coordination and must be approved

---

## Rollback Plan

If issues arise:
1. Set all `is_trusted` flags to `False`
2. Disable scheduler job
3. Revert PTO service to original approval logic
4. Run downgrade migration if database changes need reverting

---

## Estimated Effort

| Task | Hours |
|------|-------|
| Database migration | 2 |
| Model updates | 2 |
| Notification service | 6 |
| Report export service | 4 |
| UI - Manager settings | 4 |
| UI - Trust checkbox | 2 |
| Scheduler integration | 2 |
| Testing | 6 |
| Documentation | 2 |
| **Total** | **30 hours** |
