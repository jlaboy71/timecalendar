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
