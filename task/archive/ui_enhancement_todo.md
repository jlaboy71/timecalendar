# TJM Time Calendar - Professional UI Enhancement Phases

**Reference Skill:** `nicegui-professional-ui-skill.md`
**Mode:** Phased Implementation with Approval Gates

---

## Phase Index

| Phase | Page | Risk Level | Status |
|-------|------|------------|--------|
| 0 | Foundation (theme.py) | LOW | PENDING APPROVAL |
| 1 | Login | LOW | PENDING |
| 2 | Admin Dashboard | LOW | PENDING |
| 3 | Help Page | LOW | PENDING |
| 4 | Handbook Page | LOW | PENDING |
| 5 | Reports Page | MEDIUM | PENDING |
| 6 | Requests Page | MEDIUM | PENDING |
| 7 | Carryover Page | MEDIUM | PENDING |
| 8 | Admin Employees | MEDIUM | PENDING |
| 9 | Admin Departments | MEDIUM | PENDING |
| 10 | Manager Settings | MEDIUM | PENDING |
| 11 | Request Form | HIGH | PENDING |
| 12 | Dashboard | HIGH | PENDING |
| 13 | Calendar | HIGH | PENDING |
| 14 | Analytics | MEDIUM | PENDING |
| 15 | Admin System | HIGH | PENDING |

---

## PHASE 0: Foundation Layer

### Page: `theme.py` (Component)
### Risk Level: LOW

### Read-Only Findings Summary
- Currently contains `apply_dark_mode()` with basic CSS injection
- TJM brand colors defined but not as CSS custom properties
- No Google Fonts integration
- No animation keyframes defined
- No global styling enhancements

### Proposed UI Interventions
1. Add `inject_professional_fonts()` function
   - Load Plus Jakarta Sans, DM Sans, JetBrains Mono from Google Fonts
   - Set font-family CSS variables
2. Create `inject_global_styles()` function
   - Add CSS custom properties (shadows, transitions, radius)
   - Add animation keyframes (fadeInUp, fadeIn, pulse-gold)
   - Add stagger-children animation
   - Add professional card/button/table/input enhancements
3. Integrate into `apply_dark_mode()` or create separate initialization

### Risks
- CSS may conflict with existing inline styles
- Performance impact from font loading
- Existing mobile_responsive.py CSS may conflict

### Dependencies Required Before Proceeding
- None (foundation layer)

### Tests/Invariants to Verify
- [ ] Application starts without errors
- [ ] Dark mode toggle still works
- [ ] Existing pages render correctly
- [ ] Mobile responsive CSS still applies

### Expected Visible Outcome
- Fonts appear slightly different (more professional)
- Cards may have smoother rounded corners
- Hover effects on cards may be more pronounced

---

## **STOP AND APPROVAL REQUIRED**
Before proceeding to Phase 1, user must confirm:
- [ ] Phase 0 changes reviewed
- [ ] No visual regressions observed
- [ ] Approval to proceed to Phase 1

---

## PHASE 1: Login Page

### Page: `login.py`
### Risk Level: LOW

### Read-Only Findings Summary
- Centered card layout with logo
- Basic input fields without enhanced styling
- Blue login button (not TJM Gold)
- No entry animations
- Error message handling exists

### Proposed UI Interventions
1. Apply professional fonts (requires Phase 0)
2. Change login button to TJM Gold gradient
3. Add subtle card shadow enhancement
4. Add fade-in animation on page load
5. Enhance input field focus states (gold border)

### Risks
- Button color change is cosmetic only
- Animation may feel different to users

### Dependencies Required Before Proceeding
- Phase 0 completed

### Tests/Invariants to Verify
- [ ] Login still works with valid credentials
- [ ] Login fails gracefully with invalid credentials
- [ ] Rate limiting message still displays
- [ ] Session timeout redirect works
- [ ] Forgot password link works

### Expected Visible Outcome
- Gold login button instead of blue
- Smoother card appearance
- Subtle animation on page load

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 2: Admin Dashboard

### Page: `admin_dashboard.py`
### Risk Level: LOW

### Read-Only Findings Summary
- Navigation card grid layout
- Basic card styling with hover:shadow-lg
- Icons using text-primary color
- Role-based visibility (admin/superadmin only)

### Proposed UI Interventions
1. Apply animation classes to card grid
2. Enhance card hover effects
3. Apply typography classes to labels
4. Add gradient accent to SuperAdmin card

### Risks
- LOW - Navigation only, no business logic

### Dependencies Required Before Proceeding
- Phase 0 completed

### Tests/Invariants to Verify
- [ ] All navigation links work
- [ ] SuperAdmin card only visible to superadmin
- [ ] Back button works

### Expected Visible Outcome
- Cards animate in on load
- More pronounced hover effect
- Slightly more polished typography

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 3: Help Page

### Page: `help.py`
### Risk Level: LOW

### Read-Only Findings Summary
- Help content display
- Expansion panels for topics
- No complex business logic

### Proposed UI Interventions
1. Apply typography classes
2. Enhance expansion panel styling
3. Add content section headers

### Risks
- LOW - Read-only content

### Tests/Invariants to Verify
- [ ] All help topics expand/collapse
- [ ] Content is readable
- [ ] Navigation works

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 4: Handbook Page

### Page: `handbook.py`
### Risk Level: LOW

### Read-Only Findings Summary
- Markdown content rendering
- Table of contents navigation
- Document viewer

### Proposed UI Interventions
1. Apply typography enhancements
2. Style table of contents
3. Enhance content card styling

### Risks
- LOW - Document viewing only

### Tests/Invariants to Verify
- [ ] All sections render
- [ ] TOC navigation works
- [ ] Back button works

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 5: Reports Page

### Page: `reports.py`
### Risk Level: MEDIUM

### Read-Only Findings Summary
- Report selection interface
- Data tables for report output
- Export functionality

### Proposed UI Interventions
1. Apply pro_table() styling patterns
2. Enhance button styling
3. Apply typography to section headers

### Risks
- Table changes could affect data display
- Export functionality must remain intact

### Dependencies Required Before Proceeding
- Phase 0 completed

### Tests/Invariants to Verify
- [ ] All report types generate correctly
- [ ] Data displays accurately in tables
- [ ] Export functionality works
- [ ] Date filtering works

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 6: Requests Page

### Page: `requests.py`
### Risk Level: MEDIUM

### Read-Only Findings Summary
- Request history table
- Status badges per request
- Cancel functionality
- Real-time updates enabled

### Proposed UI Interventions
1. Apply status_badge() component pattern
2. Enhance table styling
3. Apply card styling to summary cards

### Risks
- Status display must remain accurate
- Cancel functionality must work
- Real-time updates must continue

### **INVARIANT WARNING:**
- Balance recalculation on cancel must not be affected
- Audit logging must continue

### Tests/Invariants to Verify
- [ ] All requests display with correct status
- [ ] Pending requests show cancel button
- [ ] Cancel works and updates balance
- [ ] Real-time refresh works

---

## **STOP AND APPROVAL REQUIRED**

---

## PHASE 7-10: Medium Risk Pages

Similar structure for:
- Phase 7: Carryover Page
- Phase 8: Admin Employees
- Phase 9: Admin Departments
- Phase 10: Manager Settings

Each requires individual approval checkpoint.

---

## PHASE 11: Request Form

### Page: `request_form.py`
### Risk Level: HIGH

### Read-Only Findings Summary
- PTO type selection buttons
- Date range picker
- Balance preview
- Validation with warnings
- Auto-approval logic for managers

### Proposed UI Interventions
1. Apply pto_type_button() component pattern
2. Enhance date picker styling
3. Apply balance_display() pattern
4. Improve validation message styling

### Risks
- **HIGH** - Core business functionality
- Date calculation must remain accurate
- Balance validation must trigger correctly
- Auto-approval logic must not change

### **CRITICAL INVARIANTS:**
- Working day calculation
- Holiday exclusion
- Balance warning thresholds
- Manager auto-approval

### Tests/Invariants to Verify
- [ ] Date selection calculates correct days
- [ ] Holidays are excluded from count
- [ ] Balance warnings trigger at correct thresholds
- [ ] Submission creates pending request (employee)
- [ ] Submission creates approved request (manager)
- [ ] Email notifications send

---

## **STOP AND APPROVAL REQUIRED - HIGH RISK**

---

## PHASE 12: Dashboard

### Page: `dashboard.py`
### Risk Level: HIGH

### Read-Only Findings Summary
- Balance display cards (4 tiles)
- Quick action buttons
- Recent requests list
- Manager pending requests section
- Real-time updates

### Proposed UI Interventions
1. Apply stat_card() pattern to balance tiles
2. Add stagger animation to card grid
3. Apply status_badge() to request status
4. Enhance typography

### Risks
- **HIGH** - Most critical user page
- Balance display must be accurate
- Role-based sections must remain correct

### **CRITICAL INVARIANTS:**
- Balance calculation: `available = total + carryover - used - pending`
- Manager section visibility
- User identity display

### Tests/Invariants to Verify
- [ ] All 4 balance tiles display correct values
- [ ] Available calculation is correct
- [ ] Quick actions navigate correctly
- [ ] Manager section only shows for manager+
- [ ] Real-time updates work

---

## **STOP AND APPROVAL REQUIRED - HIGH RISK**
**REQUIRES EXPLICIT USER CONSENT per CLAUDE.md rule**

---

## PHASE 13: Calendar

### Page: `calendar.py`
### Risk Level: HIGH

### Read-Only Findings Summary
- Custom calendar grid (HTML tables)
- Color-coded PTO types
- Holiday markers
- Multiple filter options
- Month/year navigation

### Proposed UI Interventions
1. Apply PTO color configuration from skill
2. Enhance filter toggle styling
3. Improve legend styling
4. Add subtle animations to navigation

### Risks
- **HIGH** - Complex custom calendar logic
- Date rendering must not break
- Filter logic must remain accurate

### **CRITICAL INVARIANTS:**
- Date grid accuracy
- Holiday marker placement
- PTO event placement
- Filter combinations

### Tests/Invariants to Verify
- [ ] All months render correctly
- [ ] Holidays display on correct dates
- [ ] PTO events display on correct dates
- [ ] All filters work independently
- [ ] Combined filters work correctly
- [ ] Year view renders all months

---

## **STOP AND APPROVAL REQUIRED - HIGH RISK**

---

## PHASE 14-15: Remaining Pages

- Phase 14: Analytics (MEDIUM)
- Phase 15: Admin System (HIGH - SuperAdmin only)

---

## Execution Checklist

For each phase:
1. [ ] Read todo.md phase requirements
2. [ ] Confirm understanding with user
3. [ ] Apply ONLY listed interventions
4. [ ] Run syntax check
5. [ ] Restart application
6. [ ] Test all invariants listed
7. [ ] Screenshot before/after
8. [ ] Get user approval before next phase

---

## Emergency Rollback

If any phase causes issues:

```bash
# Check what changed
git status
git diff nicegui_app/pages/[file].py

# Revert single file
git checkout HEAD -- nicegui_app/pages/[file].py

# Or revert all unstaged changes
git checkout -- .

# Verify app starts
venv\Scripts\python.exe nicegui_app/main.py
```

---

**END OF PHASED IMPLEMENTATION PLAN**

---

## COMPLETED: Brand Color Centralization (Dec 2024)

### UI Phase 9.3: Global Brand Hex Audit
**Commit**: `b31bf3a refactor(ui): UI Phase 9.3 - Brand color centralization and enforcement`
**Tag**: `ui-phase-9.3-complete`

- [x] Scanned entire codebase for hardcoded brand hex codes
- [x] Fixed all files in `nicegui_app/` and `src/services/`
- [x] Created enforcement script `scripts/check_brand_colors.py`
- [x] Added Brand Color Policy documentation to `theme.py`
- [x] Updated `.claude/rules/code-style.md` with enforcement rules

### UI Phase 10: Dashboard Refactor (PROTECTED)
**Commit**: `be4246e refactor(ui): UI Phase 10 - Dashboard brand color centralization`
**Tag**: `ui-phase-10-complete`

- [x] Replaced 12 hardcoded hex codes in `dashboard.py`
- [x] Converted CSS block to f-string with escaped braces
- [x] Added automation files to enforcement whitelist
- [x] Enforcement script passes with 0 violations

---

## Completion Note

**Project finished on Dec 23, 2024.**

Centralized `nicegui_app/components/theme.py` established as single source of truth for brand colors:
- `PTO_GOLD` (#C9A227) - Primary accent
- `PTO_GRAY` (#5a6a72) - Navigation/headers
- `PTO_BLUE` (#2196F3) - UI interactive elements

Enforcement script `scripts/check_brand_colors.py` active for pre-commit validation.
