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
