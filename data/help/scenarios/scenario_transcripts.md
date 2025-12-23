# PTO Central - Training Scenario Transcripts

**Generated:** 2025-12-22
**Source:** services/playwright_engine.py scenario definitions
**Purpose:** RAG-ready narration scripts for help/training AI responses

---

## Employee Scenarios

### Submit PTO Request (`pto-request`)

**Description:** Employee submits a new PTO request through the calendar interface

1. **Login to Application** - Welcome to PTO Central. First, log in with your employee credentials.

2. **View Dashboard** - After logging in, you'll see your dashboard with your current PTO balances displayed.

3. **Click Request Time Off** - To submit a new request, click the Request Time Off button.

4. **PTO Request Form** - The request form appears. Here you'll select your leave type and choose your dates.

5. **Select Leave Type** - First, select your leave type. Options include vacation, sick time, and personal days.

6. **Select Dates** - Next, select your start and end dates using the calendar picker.

7. **Add Notes (Optional)** - You can add private notes for your own reference. These notes are only visible to you, not your manager.

8. **Submit Request** - Review your request details, then click Submit to send it to your manager for approval.

9. **Request Submitted** - Your request has been submitted successfully. You'll receive a notification when your manager responds.

---

### Understanding Your Balances (`balance-dashboard`)

**Description:** Learn how to read and understand your PTO balances on the dashboard

1. **Login to Application** - Log in to view your personal PTO dashboard and balances.

2. **Dashboard Overview** - Your dashboard is the home screen showing all your PTO information at a glance.

3. **Balance Cards** - Each card shows a leave type: Available hours, Pending requests, and Used time.

4. **Vacation Balance** - Your vacation balance shows total allocated days, minus used and pending requests.

5. **Sick Leave Balance** - Sick leave accrues according to policy and can carry over to the next year.

6. **Personal Days** - Personal days are use-it-or-lose-it and do not carry over to the next year.

7. **Pending Requests** - The pending section shows requests awaiting manager approval.

8. **Quick Actions** - Quick actions let you submit new requests or view your calendar without navigating.

9. **Year Selector** - Use the year toggle to view balances for different years and plan ahead.

---

### Calendar Navigation (`calendar-navigation`)

**Description:** Learn how to view, navigate, and understand the PTO calendar

1. **Login to Application** - Welcome to TJM Time Calendar. Log in with your credentials to access the calendar.

2. **Open Calendar View** - Click on Calendar in the navigation to view the full calendar interface.

3. **Calendar Overview** - The calendar displays all approved time off. Your requests appear in blue, and team members are shown in different colors.

4. **Navigate Between Months** - Use the left and right arrows to navigate between months. The current month is highlighted.

5. **Go to Next Month** - Click the forward arrow to see upcoming scheduled time off.

6. **View Event Details** - Click on any event in the calendar to see the full details including dates and status.

7. **Return to Today** - Click the Today button to quickly return to the current month view.

8. **Understanding the Legend** - The legend shows color codes for different leave types and statuses. Approved appears solid, pending appears faded.

---

### Filter PTO Requests (`filter-requests`)

**Description:** Learn how to filter and search PTO requests by type, status, and date range

1. **Login to Application** - Welcome to PTO Central. Let's learn how to filter and search through your request history.

2. **Open My Requests** - Click on My Requests to view your complete request history.

3. **Request History** - Here's your request history. You can see a mix of vacation, sick, and other leave types with different statuses.

4. **Filter Controls** - The filter controls at the top let you quickly find specific requests. Let's try filtering by leave type.

5. **Filter by Leave Type** - Click the Leave Type dropdown to see your options. You can filter by Vacation, Sick, Personal, or other leave types.

6. **Select Vacation Type** - Select Vacation to filter the list. This is helpful when you want to see only your vacation days.

7. **Filtered Results** - Now you see only vacation requests. The count at the top updates to show how many match your filter.

8. **Filter by Status** - You can combine filters. Add a status filter to see only Pending, Approved, or Denied vacation requests.

9. **Clear All Filters** - To see all requests again, click Clear or remove individual filters using the X buttons.

---

### Cancel Pending Request (`employee-cancel-request`)

**Description:** Employee cancels their own pending PTO request before approval

1. **Login to Application** - Welcome to PTO Central. Let's learn how to cancel a pending vacation request before your manager reviews it.

2. **View Dashboard** - Your dashboard shows you have a two-day vacation request pending approval. Let's say your plans changed and you need to cancel it.

3. **Open My Requests** - Click on My Requests to see all your submitted requests and find the one to cancel.

4. **Find Pending Request** - Here's your request history. Find the pending vacation request - it has an amber status badge showing it's still awaiting approval.

5. **Click Cancel Button** - Click the Cancel button next to your pending request. You can only cancel requests before they're approved by your manager.

6. **Confirm Cancellation** - Confirm the cancellation. Your 16 pending hours will be immediately returned to your available vacation balance.

7. **Request Cancelled** - Done! Your request status now shows Cancelled and your vacation balance has been restored. Your manager won't see this in their queue anymore.

---

### Work From Home Request (`wfh-request`)

**Description:** Submit a WFH request for special circumstances like train delays or emergencies

1. **Login to Application** - Welcome to TJM Time Calendar. Let's learn how to submit a Work From Home request for special circumstances.

2. **Understanding WFH Requests** - Work From Home requests are designed for unexpected special circumstances only, such as train delays, weather emergencies, or home repairs. They are NOT for regular remote work scheduling.

3. **Start Request** - Click Request Time Off to begin. We'll select Work From Home as the leave type.

4. **Select WFH Type** - Click the Other Leave Types dropdown and select Work From Home. Notice the red color indicating this is a special request type.

5. **WFH Rules** - Important rules for WFH: First, WFH is single-day only - you cannot request multiple days. Second, requests must be within 7 days - you cannot schedule WFH far in advance.

6. **Select Date** - Select a date within the next 7 days. The system will prevent you from choosing dates further out.

7. **Reason Required** - Unlike other leave types, WFH REQUIRES a reason. Explain your special circumstance - for example, 'Train delays due to weather' or 'Emergency home repair appointment'.

8. **Submit for Approval** - WFH requests always require manager approval. Your manager will review the reason and circumstances before approving.

9. **WFH Summary** - Remember: WFH is for unexpected special circumstances only. It's single-day, within 7 days, requires a reason, and needs manager approval. For regular remote work, speak with your manager about scheduling.

---

### WFH Day Swap (`wfh-swap`)

**Description:** Exchange your WFH day with a teammate - no manager approval needed

1. **Dashboard** - Welcome to PTO Central. Let's learn how to swap your Work From Home day with a teammate.

2. **Click WFH Swap** - From the dashboard, click the Work From Home Day Swap button. This is a peer-to-peer feature - no manager approval required.

3. **Swap Page** - The page shows five day columns from Monday through Friday. Each column lists teammates who work from home that day. Your day is marked with a gold star.

4. **Select Teammate** - Click on a teammate's name to open the swap request dialog. Let's click on PTO Manager who works from home on Wednesday.

5. **Swap Dialog** - The dialog shows the teammate's information and available dates. You can select from the next two occurrences of their Work From Home day.

6. **Enter Message** - Enter your reason for the swap request. This helps your teammate understand why you need to swap days.

7. **Review Request** - Review your request. When ready, click Send Request. Your teammate will receive an email notification immediately.

8. **Close Dialog** - For this demo, we'll close the dialog. In practice, you would click Send Request to submit.

9. **Incoming Requests** - When teammates request a swap with you, their requests appear in the Incoming Requests section at the top. You can accept or decline with a response message.

10. **Summary** - Work From Home Day Swap is peer-to-peer with no manager approval. Click a teammate, enter your reason, and send your request. They have three business days to respond.

---

### Leave Type Rules & Policies (`leave-type-rules`)

**Description:** Comprehensive guide to leave types, carryover rules, accrual requirements, and date restrictions

1. **Understanding Leave Policies** - Welcome to TJM's Leave Policy Training. Understanding these rules helps you plan your time off effectively and avoid surprises.

2. **Vacation Rules** - Vacation time is allocated based on your years of service. You can request vacation anytime in the future, and even up to 7 days in the past with manager approval.

3. **Vacation Carryover** - Important: Vacation does NOT automatically carry over to the next year. You must use it or request an exception carryover from your manager BEFORE year end.

4. **December Rollover** - In December, you can request January vacation that deducts from your CURRENT year balance. This 'vacation rollover' requires manager approval even for managers.

5. **Sick Leave Rules** - Sick leave automatically carries over up to the policy maximum. Unlike vacation, you don't need to request carryover - it happens automatically at year end.

6. **Sick Leave Usage** - Sick time is for illness, medical appointments, or caring for sick family members. You cannot overdraft sick leave - you can only use what you've accrued.

7. **Personal Day Rules** - Personal days are fixed allocation per year and do NOT carry over. Any unused personal days are lost at year end. Plan to use them!

8. **Personal Day Notice** - While personal days don't require a reason, please try to give 24 hours notice when possible to help with team scheduling.

9. **Chicago Leave (If Applicable)** - Chicago employees have Chicago Paid Leave with a 40-hour annual max and 16-hour carryover limit. It can be used for ANY reason.

10. **7-Day Backdating Rule** - Critical rule: You can only request time off up to 7 days in the past. Beyond 7 days, you must contact your manager directly for assistance.

11. **Balance Limits** - Sick, Personal, and Chicago Leave have HARD caps - you cannot submit requests exceeding your balance. Vacation has a soft cap - you'll see a warning but can still submit for manager discretion.

12. **Policy Summary** - Remember: Vacation needs exception carryover, sick auto-carries, personal is use-or-lose. All leave has a 7-day backdating limit. Check your balances before requesting!

---

## Manager Scenarios

### Manager Approval Workflow (`manager-approval`)

**Description:** Manager reviews pending requests and approves or denies them

1. **Manager Login** - Welcome to PTO Central. As a manager, you'll review and approve time-off requests from your team. Let's log in.

2. **Manager Dashboard** - Your manager dashboard shows you have a pending vacation request awaiting your review. Notice the pending count indicator.

3. **Access Pending Requests** - Click on the Pending Requests section to see the full details of requests awaiting your decision.

4. **View Pending Requests** - Here's the approval queue. You can see a two-day vacation request from a team member scheduled for two weeks from now.

5. **Select Request to Review** - Click on the request to review the complete details, including the employee's current balance and team coverage.

6. **Review Request Details** - Review the employee's available balance, the requested dates, and check if there are any coverage conflicts with other team members.

7. **Approve or Deny** - Once you've reviewed the request, click Approve to grant the time off, or Deny if there's a coverage issue.

8. **Decision Confirmed** - Your decision has been recorded. The employee receives an automatic email notification with your response.

---

### Team Calendar View (`team-calendar`)

**Description:** Manager views team calendar to check coverage and plan approvals

1. **Manager Login** - Welcome to PTO Central. As a manager, you can view your entire team's time-off schedule in one place. Let's log in.

2. **Manager Dashboard** - Your dashboard shows team activity at a glance. You can see several team members have upcoming time off scheduled.

3. **Open Team Calendar** - Click on Team Calendar to see a visual overview of all scheduled time off for your team.

4. **Team Calendar Overview** - Here's the team calendar. Notice the mix of vacation, sick, and personal time shown with different colors for each employee.

5. **Coverage Indicators** - Coverage indicators help you spot days when multiple team members are scheduled off. This helps prevent understaffing.

6. **Filter by Employee** - Use the employee filter to focus on specific team members' schedules when planning projects or approving requests.

7. **View Request Details** - Click on any time-off event to see full details including the leave type, dates, and any notes the employee added.

8. **Conflict Detection** - Days highlighted in red indicate potential coverage issues. Use this to make informed approval decisions.

---

### PTO Reporting (`pto-reports`)

**Description:** Learn how to access and generate PTO reports for analysis

1. **Manager Login** - Log in with manager or admin credentials to access the reporting dashboard.

2. **Open Reports Section** - Click on Reports in the navigation to access the reporting dashboard.

3. **Reports Dashboard** - The reports dashboard shows various report types and quick statistics.

4. **PTO Utilization Report** - The utilization report shows how much PTO has been used versus available for each team member.

5. **Select Date Range** - Select a date range to analyze PTO patterns over specific periods.

6. **Department Breakdown** - The department breakdown shows PTO usage patterns across different teams.

7. **Usage Trends** - Charts display usage trends over time, helping identify peak vacation periods.

8. **Export Report** - Click Export to download the report as CSV or PDF for sharing or further analysis.

9. **Balance Summary** - The balance report shows everyone's current PTO balances and carryover status.

---

### Carryover Exception Approvals (`manager-carryover`)

**Description:** Review and approve employee vacation carryover exception requests

1. **Manager Login** - Welcome to PTO Central. As a manager, you can approve carryover exception requests from employees who need to carry unused vacation into the next year.

2. **Understanding Carryover** - Carryover exceptions allow employees to carry unused vacation days into the next year as a BONUS. It doesn't reduce their new year allocation.

3. **Manager Dashboard** - Your dashboard shows you have a pending carryover request. An employee is requesting to carry over 24 hours of unused vacation.

4. **Access Carryover Queue** - Click on the Carryover section to review the exception request details.

5. **Carryover Request Queue** - Here's the carryover queue. You can see the employee's request for 24 hours of exception carryover from this year to next.

6. **Review Request Details** - Review the employee's current balance, requested hours, and reason. Consider their workload and why they couldn't use the time this year.

7. **Partial Approval Option** - You have flexibility here. You can approve all 24 hours, a partial amount like 16 hours, or deny the request entirely.

8. **Approve or Deny** - Click Approve to grant the carryover exception, or Deny with a reason. The employee receives an automatic notification of your decision.

9. **Understanding Impact** - Approved hours appear as Exception Carryover in the employee's next year balance. This is a bonus on top of their regular allocation.

---

### Team Management Overview (`manager-team-overview`)

**Description:** View team balances, usage patterns, and manage employee time off

1. **Manager Login** - As a manager, you have access to your team's PTO balances, usage patterns, and approval workflows.

2. **Manager Dashboard** - Your manager dashboard shows team statistics, pending approvals, and who's currently out.

3. **View Team Balances** - Click on Team Balances to see each team member's current PTO balances and usage.

4. **Team Balance Grid** - The team balance grid shows vacation, sick, and personal balances for each team member. Use this to identify who might need to use time off.

5. **Identify Carryover Risks** - Employees with high unused balances near year end may lose time. Encourage them to schedule time off or request carryover.

6. **View Employee Detail** - Click on an employee name to see their full history, including all requests, approvals, and balance changes.

7. **Manager Auto-Approve** - As a manager, your vacation, sick, and personal requests are auto-approved. However, backdated requests and vacation rollover still require approval.

8. **Coverage Planning** - Use the team calendar to ensure adequate coverage. Days with too many people out are highlighted for attention.

---

### Backdated Request Approvals (`manager-backdated-requests`)

**Description:** Handle requests for past dates within the 7-day window

1. **Manager Login** - Welcome to PTO Central. Backdated requests require special attention. Let's learn how to handle time-off requests for past dates.

2. **7-Day Backdating Rule** - Employees can submit requests up to 7 calendar days in the past. This sick day request is from 3 days ago, so it's within the allowed window.

3. **Pending Approvals** - You can see a backdated sick day request in your queue. Notice how it's flagged as backdated to draw your attention.

4. **Identify Backdated Requests** - Look for the Backdated badge or past date indicator. These requests always require your review, even for trusted employees.

5. **Review the Reason** - Consider why this sick day request is backdated. Common valid reasons include illness preventing immediate access, or simply forgetting to submit.

6. **Verify the Absence** - Verify the employee was actually out sick that day. Check your memory of team attendance or any communications from that date.

7. **Approve or Deny** - If the sick day was legitimate, click Approve. If you have concerns, you can Deny with an explanation.

8. **Beyond 7 Days** - For requests beyond 7 days ago, employees must contact you directly. You can submit on their behalf through admin functions if needed.

---

### Deny PTO Request (`manager-deny-request`)

**Description:** Manager reviews and denies a PTO request, providing a reason

1. **Manager Login** - Welcome to PTO Central. Sometimes you need to deny a PTO request. Let's learn how to do this professionally.

2. **Manager Dashboard** - You have a five-day vacation request in your queue. After reviewing, you've determined there's a coverage issue for those dates.

3. **Open Approval Queue** - Click on Pending Requests to review the full details before making your decision.

4. **Select Request** - Review the five-day vacation request. The dates conflict with a critical project deadline and another team member's approved leave.

5. **Review Team Coverage** - The team coverage check shows too many people would be out during this period. This is a valid reason for denial.

6. **Click Deny Button** - Click Deny to open the denial dialog. Always provide a clear, helpful reason.

7. **Enter Denial Reason** - Enter a constructive reason like: Team coverage issue - please try different dates. Suggest alternative dates if possible.

8. **Confirm Denial** - Click Confirm to submit the denial. The employee receives an automatic notification with your reason.

9. **Request Denied** - The request is denied. The employee's 40 pending hours are restored to their balance and they can resubmit for different dates.

---

## Admin Scenarios

### Admin User Management (`admin-user-management`)

**Description:** Administrator creates and manages user accounts

1. **Admin Login** - Log in with your administrator credentials to access system management features.

2. **Admin Dashboard** - The administrator dashboard provides an overview of system status and quick access to management tools.

3. **Access Employee Management** - Click on Manage Employees to view and manage employee accounts.

4. **View User List** - The user list shows all employees with their roles, departments, and account status.

5. **User Actions** - From here you can create new users, edit existing accounts, reset passwords, or adjust permissions.

---

### Department Management (`admin-departments`)

**Description:** Create, edit, and manage organizational departments

1. **Admin Login** - As an administrator, you can manage the organizational structure including departments and their managers.

2. **Admin Menu** - Click on Administration to access department management, user management, and system settings.

3. **Department List** - The department list shows all organizational units with their assigned managers and employee counts.

4. **Create Department** - Click Create Department to add a new organizational unit. Provide a name and optionally assign a manager.

5. **Assign Manager** - Assign a manager who will approve PTO requests for employees in this department.

6. **Edit Department** - Click Edit to modify department details, change the manager, or update settings.

7. **View Employees** - View which employees are assigned to each department. Employees are assigned during user creation or editing.

---

### System Administration (`admin-system-settings`)

**Description:** Configure system-wide settings, policies, and email notifications

1. **Admin Login** - System administration allows you to configure company-wide settings, policies, and notification preferences.

2. **Admin Panel** - Navigate to the Administration section to access system settings.

3. **System Overview** - The system overview shows current configuration, active users, and system health indicators.

4. **Email Configuration** - Email settings control how notifications are sent for request submissions, approvals, and denials.

5. **Policy Configuration** - Policy settings define default allocations, carryover limits, and state-specific rules for different locations.

6. **Year-End Processing** - Year-end processing automatically creates new year balances, applies carryover, and generates holidays.

7. **Audit Log** - The audit log tracks all system activities including logins, request changes, and administrative actions.

8. **Data Management** - Data management options include database backup, integrity checks, and data export capabilities.

---

## RAG Metadata

**Total Scenarios:** 18
**Role Breakdown:**
- Employee: 8 scenarios
- Manager: 7 scenarios
- Admin: 3 scenarios

**Key Topics Covered:**
- PTO request submission and cancellation
- Balance understanding and dashboard navigation
- Calendar usage and filtering
- WFH requests and peer-to-peer swaps
- Leave type policies and carryover rules
- Manager approval workflows
- Team management and coverage planning
- Admin user and department management
- System configuration

**Chunking Strategy:** Step-based (each numbered step is a natural chunk)
**Average Steps per Scenario:** 8 steps

---

**END OF TRANSCRIPTS**
