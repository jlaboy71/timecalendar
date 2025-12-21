# PTO Central - Test Scenario Template

Use this template to create new test scenarios. Copy this format and fill in the details.

---

# Scenario: [Your Scenario Name]

**Description:** [Brief description of what this scenario tests]
**Role:** [employee|manager|admin|superadmin]
**Tags:** [bug-fix, regression, feature, smoke-test, edge-case]

## Steps

### Step 1: [Step Title]
- **Action:** [click|fill|select|navigate|screenshot|wait]
- **Selector:** [CSS selector for click/fill/select actions]
- **Value:** [Value to fill or option to select]
- **URL:** [URL for navigate action]
- **Wait:** [seconds to wait after this step]
- **Script:** [Narration text for audio/video documentation]
- **Description:** [What this step does]

### Step 2: [Next Step Title]
- **Action:** screenshot
- **Description:** Capture the current state

---

## Available Actions

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `click` | Click an element | selector |
| `fill` | Enter text in an input | selector, value |
| `select` | Choose from dropdown | selector, value |
| `navigate` | Go to a URL | url |
| `screenshot` | Capture current screen | (none) |
| `wait` | Pause execution | wait (seconds) |

## Common Selectors

### Buttons
- `button:has-text('Button Text')` - Button with exact text
- `button:has-text('Submit')` - Submit buttons
- `button.q-btn` - Quasar buttons

### Inputs
- `input[type="text"]` - Text inputs
- `input[type="password"]` - Password fields
- `input[placeholder*="search"]` - Inputs with placeholder containing "search"
- `textarea` - Text areas

### Navigation
- `.q-tab:has-text('Tab Name')` - Quasar tabs
- `a:has-text('Link Text')` - Links with text

### Cards & Containers
- `.q-card` - Quasar cards
- `.cursor-pointer:has-text('Clickable Text')` - Clickable elements

---

## Example Scenarios

### Example 1: Bug Regression Test

# Scenario: Verify Vacation Balance After Cancellation

**Description:** Tests that vacation balance is correctly restored when cancelling an approved request (Bug #123)
**Role:** employee
**Tags:** bug-fix, regression, balance

## Steps

### Step 1: Login as Test User
- **Action:** navigate
- **URL:** /
- **Description:** Navigate to login page

### Step 2: View Dashboard
- **Action:** screenshot
- **Description:** Capture initial dashboard with vacation balance

### Step 3: Click My Requests
- **Action:** click
- **Selector:** button:has-text('My Requests'), .cursor-pointer:has-text('Requests')
- **Wait:** 2
- **Description:** Navigate to requests list

### Step 4: Find Approved Request
- **Action:** screenshot
- **Description:** Locate an approved vacation request

### Step 5: Cancel Request
- **Action:** click
- **Selector:** button:has-text('Cancel')
- **Wait:** 1
- **Description:** Click cancel button

### Step 6: Confirm Cancellation
- **Action:** click
- **Selector:** button:has-text('Yes'), button:has-text('Confirm')
- **Wait:** 2
- **Description:** Confirm the cancellation

### Step 7: Verify Balance Restored
- **Action:** navigate
- **URL:** /dashboard
- **Description:** Return to dashboard

### Step 8: Capture Final Balance
- **Action:** screenshot
- **Script:** The vacation balance should now be restored to include the cancelled hours.
- **Description:** Verify balance is correctly updated

---

### Example 2: Feature Smoke Test

# Scenario: PTO Request Form Validation

**Description:** Verify form validation for PTO request submission
**Role:** employee
**Tags:** smoke-test, feature, validation

## Steps

### Step 1: Open Request Form
- **Action:** navigate
- **URL:** /request
- **Wait:** 2

### Step 2: Submit Empty Form
- **Action:** click
- **Selector:** button:has-text('Submit')
- **Wait:** 1
- **Description:** Attempt to submit without filling required fields

### Step 3: Capture Validation Errors
- **Action:** screenshot
- **Script:** The form should display validation errors for required fields.
- **Description:** Verify error messages appear

### Step 4: Fill Leave Type
- **Action:** click
- **Selector:** .q-select:has-text('Leave Type')
- **Wait:** 0.5

### Step 5: Select Vacation
- **Action:** click
- **Selector:** .q-item:has-text('Vacation')
- **Wait:** 1

### Step 6: Capture Partial Form
- **Action:** screenshot
- **Description:** Form with leave type selected

---

## Tips for Claude Desktop

When generating scenarios, consider:

1. **Bug History**: Reference specific bug numbers and what they tested
2. **Edge Cases**: Test boundary conditions (zero balance, date ranges, permissions)
3. **Role Variations**: Same flow may differ by user role
4. **Regression Coverage**: Include steps that verify previously fixed issues
5. **Data States**: Consider empty states, full states, and error states

### Prompt for Claude Desktop:

"Based on the recent bug fixes in our PTO calendar application, generate test scenarios that cover:
1. The vacation balance calculation bug (#123)
2. The manager approval workflow issue (#145)
3. Edge cases for date selection across year boundaries

Use the scenario template format with proper selectors for a NiceGUI/Quasar application."
