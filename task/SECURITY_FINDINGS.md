# Security Findings Report

**Date**: December 11, 2024
**Auditor**: Claude Code
**Application**: TJM Time Calendar
**Version**: Production Security Readiness - Phase 2

---

## Executive Summary

The TJM Time Calendar application has **strong security fundamentals** already in place. Password hashing (bcrypt), rate limiting, session management, and audit logging are all properly implemented. However, there are some items that need attention before production deployment.

---

## Critical Issues (Must Fix Before Production)

### 1. Exposed Secrets in .env File

**Location**: `.env` (lines 6, 15, 26)
**Risk**: HIGH - API keys and passwords visible in repository

**Current State**:
- `SECRET_KEY` is set (good, but verify it's unique per environment)
- `ANTHROPIC_API_KEY` contains a real API key
- `SMTP_PASSWORD` contains a real app password

**Remediation**:
1. **NEVER commit `.env` to version control** - add to `.gitignore`
2. Rotate all exposed credentials immediately:
   - Generate new Anthropic API key
   - Generate new Gmail app password
3. For production: Use environment variables set on server, not file

**Verification**:
```bash
# Check if .env is in .gitignore
grep -q "^\.env$" .gitignore && echo "OK" || echo "ADD .env to .gitignore"
```

---

## High Priority Issues

### 2. DEBUG Mode Enabled

**Location**: `.env` (line 12)
**Risk**: MEDIUM - Debug mode may expose sensitive information

**Current State**: `DEBUG=True`

**Remediation**:
- Set `DEBUG=False` in production `.env`
- The `src/config.py` already reads this correctly
- Consider adding a warning in `main.py` if DEBUG is enabled

---

### 3. Host Binding is 0.0.0.0

**Location**: `nicegui_app/main.py` (line 334)
**Risk**: LOW (if behind firewall) to MEDIUM (if exposed to internet)

**Current State**: `host='0.0.0.0'` - accepts connections from any IP

**Remediation**:
- For internal network deployment: This is acceptable if behind corporate firewall
- For internet-facing: Use a reverse proxy (nginx) with proper SSL termination
- Document the deployment architecture

---

## Medium Priority Issues

### 4. No HTTPS Configured

**Location**: `nicegui_app/main.py`
**Risk**: MEDIUM - Data transmitted in plaintext on network

**Current State**: No SSL certificate configuration

**Remediation** (Phase 4 of roadmap):
1. Generate or obtain SSL certificate
2. Configure NiceGUI with `ssl_certfile` and `ssl_keyfile` parameters
3. For internal use: Self-signed certificate is acceptable
4. For production: Use proper CA-signed certificate or Let's Encrypt

---

### 5. Session Secret Key Source

**Location**: `nicegui_app/main.py` (line 335)
**Risk**: LOW - Currently using environment variable correctly

**Current State**: `storage_secret=config.SECRET_KEY`

**Verification Needed**:
- Ensure SECRET_KEY is unique per deployment
- Should be at least 32 characters of random data
- Current key appears to be a proper 64-character hex string (good)

---

## Low Priority / Recommendations

### 6. Pydantic Schema Deprecation Warnings

**Location**: `src/schemas/user_schemas.py:63`, `src/schemas/pto_schemas.py:33`
**Risk**: NONE (cosmetic)

**Current State**: Using deprecated class-based `Config`

**Remediation** (optional):
```python
# Replace:
class Config:
    from_attributes = True

# With:
model_config = ConfigDict(from_attributes=True)
```

---

### 7. Input Validation Enhancements (Optional)

**Location**: `src/services/pto_service.py`
**Risk**: LOW - Current validation is adequate

**Current Validation** (already implemented):
- Start date not in past (line 54)
- Start date <= end date (line 58)
- User exists validation (line 50)
- Future date limit (5 years max) (line 68)

**Already Good**:
- User ownership check on cancel (line 351)
- Status check before approve/deny (lines 263, 311)
- No raw SQL queries (uses SQLAlchemy ORM throughout)

---

## Security Features Already Implemented

| Feature | Status | Location |
|---------|--------|----------|
| Password Hashing | bcrypt with 12 rounds | `src/utils/password.py` |
| Rate Limiting | 5 attempts, 15 min lockout | `src/services/rate_limiter.py` |
| Session Timeout | 30 minutes inactivity | `src/services/session_manager.py` |
| Audit Logging | Login, PTO actions | `src/services/audit_service.py` |
| Auth Guards | `require_auth()` on all pages | `nicegui_app/main.py` |
| Environment Config | dotenv-based | `src/config.py` |
| Password Field | Stored as hash only | `src/models/user.py:32` |
| SQL Injection Prevention | SQLAlchemy ORM | All services |
| User Deactivation | Soft delete preserves data | `src/services/user_service.py:206` |

---

## Pre-Production Checklist

Before deploying to production:

- [ ] Add `.env` to `.gitignore`
- [ ] Rotate Anthropic API key
- [ ] Rotate Gmail app password
- [ ] Set `DEBUG=False`
- [ ] Set `ENVIRONMENT=production`
- [ ] Generate unique SECRET_KEY for production
- [ ] Configure HTTPS (Phase 4)
- [ ] Document network architecture (firewall, reverse proxy)
- [ ] Test login with rate limiting enabled
- [ ] Verify session timeout works correctly
- [ ] Remove or secure test accounts

---

## Conclusion

The application has a **solid security foundation**. The primary concerns are:

1. **Credential exposure** in `.env` - needs immediate rotation
2. **DEBUG mode** - must be disabled for production
3. **HTTPS** - should be configured before production use

All critical authentication and authorization mechanisms are properly implemented. The codebase follows security best practices for password storage, session management, and input validation.

**Recommendation**: Proceed to Phase 3 (Security Remediation) after addressing the credential exposure issue.
