# PTO Central - Changelog (December 10-11, 2025)

## Summary
Major UI/UX improvements, TJM branding, reports enhancements, and bug fixes over the last two days.

---

## December 11, 2025

### TJM Brand Colors & Visual Theme
- Applied TJM brand colors throughout the application:
  - **TJM Gold (#c9a227)**: Primary buttons, card headers, section titles, links
  - **TJM Gray (#5a6a72)**: Header/navigation bar
- Added subtle shadows in light mode for improved depth perception:
  - Cards: soft shadow with hover effect
  - Input fields/selects: light shadow
  - Buttons: gentle depth with enhanced hover
  - Tables: subtle container shadow with rounded corners

### Dashboard Improvements
- **Scrollable Recent Approved Time Off**: Changed from 5-item limit to showing all approved requests in a scrollable container (max-height 300px)
- Added request count display in section header
- Fixed manager approval date display in PTO detail dialog

### Reports Enhancements
- **PTO Type Filter**: Added filter for My History, My Calendar, and Team Usage reports
  - Options: All Types, Vacation, Sick, Personal
- **Type-Based Border Colors**: Changed left border color on PTO history cards from status-based to PTO type-based:
  - Vacation: Blue
  - Sick: Green
  - Personal: Purple

---

## December 10, 2025

### Clean Day Formatting
- Improved day display throughout the app - whole numbers show without decimals (e.g., "2" instead of "2.0")
- Applied to dashboard, reports, and all PTO displays

### Sick/Personal Over-Subscription Prevention
- Added hard limits for sick and personal days - employees cannot request more than available
- Vacation days remain flexible (manager discretion on approval)
- Validation added at both request submission and approval stages

### Calendar Half-Day Indicator
- Added "½" indicator on calendar PTO events for half-day requests
- Added "Highlight ½ Days" toggle in calendar display options
- Added half-day legend item to calendar
- Fixed calendar employee select validation error

### Report Improvements
- Fixed team balance report to show days instead of hours
- Added "My Calendar" report HTML generation for print preview
- Added Year at a Glance report with month-by-month breakdown

### Security & Configuration
- Added password confirmation and visibility toggle in Edit Employee
- Added SSL/HTTPS configuration support
- Added security documentation and production readiness guide

### UI Improvements
- Added private PTO option (is_private field) for confidential requests
- Enhanced analytics with additional metrics
- Filter help content by user role
- Removed environment configuration from user-facing help

### Admin & System
- Modularized admin pages for better maintainability
- Cleaned up obsolete files
- Updated year-end documentation
- Improved print preview - removed email button, fixed print, added dashboard navigation

### Multi-Year Support
- Added year switchers throughout the application
- Proper handling of PTO requests across multiple years

---

## Files Changed

### Core UI Files
- `nicegui_app/components/theme.py` - TJM brand colors, subtle shadows
- `nicegui_app/pages/dashboard.py` - Scrollable approved requests, approval date display
- `nicegui_app/pages/reports.py` - PTO type filter, type-based border colors
- `nicegui_app/pages/calendar.py` - Half-day indicators, display options

### Services
- `src/services/pto_service.py` - Sick/personal over-subscription prevention
- `src/services/report_service.py` - Clean day formatting, calendar report HTML
- `src/services/balance_service.py` - Multi-year balance handling

### Documentation
- `task/PRODUCTION_SECURITY_READINESS.md` - Security and SSL documentation
- `task/TJM-TC-Roadmap.md` - Project roadmap
- Various help documentation updates

---

## Technical Notes

### TJM Brand Colors
```css
PTO_GOLD = '#c9a227'  /* Primary accent, buttons, highlights */
PTO_GRAY = '#5a6a72'  /* Headers, navigation, secondary elements */
```

### PTO Type Color Scheme
- **Vacation**: Blue (#1976d2 / border-blue-500)
- **Sick**: Green (#2e7d32 / border-green-500)
- **Personal**: Purple (#7b1fa2 / border-purple-500)

### Balance Storage
- All PTO balances stored in hours (8 hours = 1 day)
- Display formatting converts to days with clean decimal handling

---

## Git Commits (Last 2 Days)
1. `3fe7a0b` feat: TJM brand colors, subtle shadows, reports enhancements
2. `d13eb94` feat: clean day formatting, sick/personal over-subscription prevention
3. `095b64e` feat: calendar half-day indicator, report improvements, SSL support
4. `91130e0` feat: UI improvements, analytics enhancements, and private PTO option
5. `fc7ff14` fix: remove environment configuration from user-facing help
6. `9d7f4e0` feat: filter help content by user role
7. `e9a49a9` docs: update help documentation for accurate carryover policy
8. `c9db998` feat: modularize admin pages, cleanup obsolete files, fix year-end docs
9. `eb2b4c2` fix: improve print preview - remove email button, fix print, add dashboard nav
10. `93acb09` feat: multi-year support, year switchers, Claude rules documentation
11. `155f7a8` feat: fix email from print preview, enhance PDF with employee details
