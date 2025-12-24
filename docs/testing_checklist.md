# PTO Central AI Testing Checklist

## Pre-Testing Setup

- [ ] Application running on localhost:8080
- [ ] Database has test users with balances
- [ ] Logged in as test user (ptouser01 / 2ez4me!!)
- [ ] AI Assistant page accessible at /ai-assistant

---

## Smart Scheduler Tests

### Balance Inquiry
- [ ] "How much PTO do I have?" - Shows all leave types
- [ ] "What's my vacation balance?" - Shows vacation days
- [ ] Correct numbers match database

### Date Suggestions
- [ ] "I want a week off" - Suggests dates
- [ ] "Time off around Presidents Day" - Mentions Feb 17 holiday
- [ ] "Vacation in July" - Suggests July 4th optimization
- [ ] Shows coverage information

### Submission Flow
- [ ] Requests confirmation before submitting
- [ ] "Yes" confirms and submits
- [ ] "No" cancels without submitting
- [ ] Confirmation buttons work

### Edge Cases
- [ ] Insufficient balance - Shows warning
- [ ] Past dates - Handles gracefully
- [ ] Overlapping request - Warns user

---

## Year-End Optimizer Tests

### Expiring Balance
- [ ] "What's expiring?" - Shows personal/Chicago days
- [ ] Mentions December 31 deadline
- [ ] Correctly identifies non-carryover types

### Carryover Rules
- [ ] "Carryover rules?" - Explains policy
- [ ] Mentions 5-day vacation limit
- [ ] Mentions March 31 deadline

### December Planning
- [ ] "Help me use my days" - Suggests December dates
- [ ] Checks coverage for suggestions
- [ ] Appropriate urgency based on current date

---

## Approval Assistant Tests (Manager Account)

### Pending Requests
- [ ] "What needs approval?" - Lists pending
- [ ] Shows request details
- [ ] Provides recommendation

### Coverage Analysis
- [ ] "Team coverage next week?" - Shows schedule
- [ ] Identifies conflicts
- [ ] Percentages are accurate

### Approval Flow
- [ ] Can approve with confirmation
- [ ] Can deny with reason
- [ ] Actions logged in audit

---

## Safety Gate Tests

### All Agents
- [ ] No write without confirmation
- [ ] Token required for submission
- [ ] Token expires after 5 minutes
- [ ] Used token cannot be reused

### Confirmation Dialog
- [ ] Summary is clear and accurate
- [ ] "Yes" proceeds
- [ ] "No" cancels
- [ ] Buttons work correctly

---

## Chat Interface Tests

### Agent Switching
- [ ] Can switch between agents
- [ ] Conversation resets on switch
- [ ] Welcome message appears

### Message Display
- [ ] User messages on right (blue)
- [ ] Agent messages on left (gray)
- [ ] Timestamps visible
- [ ] Auto-scrolls to newest

### Input Handling
- [ ] Enter key sends message
- [ ] Send button works
- [ ] Typing indicator shows
- [ ] Input disabled while processing

---

## Error Handling

- [ ] Empty message handled
- [ ] Very long message handled
- [ ] Network error shows message
- [ ] Invalid dates handled
- [ ] Unauthorized action blocked

---

## Sign-Off

Tester: _________________
Date: _________________
All tests passing: [ ] Yes  [ ] No (see notes)

Notes:
_________________________________________
_________________________________________
_________________________________________
