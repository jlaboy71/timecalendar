# Advanced Analytics Dashboard

The Analytics Dashboard provides comprehensive workforce intelligence and insights for PTO usage, attendance patterns, and coverage planning.

## Accessing Analytics

Navigate to **Analytics** from the Dashboard (Managers/Admins only).

**Note for Managers:** You will only see analytics for your own department. Admins and Superadmins see company-wide data.

## Dashboard Tabs

The analytics dashboard has three main tabs:

### Overview Tab
Quick metrics and visual summaries for at-a-glance insights.

### Trends Tab
Detailed charts and patterns over time.

### Insights Tab
AI-powered recommendations and risk analysis.

---

## Overview Tab Features

### Key Metrics Cards

Quick stats for the selected year:
- **Total Requests** - All PTO requests submitted
- **Approved** - Successfully approved requests
- **Pending** - Requests awaiting approval
- **Days Taken** - Total PTO days used
- **Avg Days/Employee** - Average usage per person

### Attendance Heatmap

Interactive calendar heatmap showing:
- Color-coded attendance rates (green = high, red = low)
- Last 60 days plus 14 days ahead
- Hover for specific date details
- Identify patterns at a glance

### Leave Type Breakdown (Pie Chart)

Distribution of leave types:
- Vacation (blue) vs. Sick (red) vs. Personal (green)
- Interactive donut chart
- Percentage breakdown

### Best Days for All-Hands Meetings

Smart scheduling suggestions:
- Shows top 3 dates with highest expected attendance
- Filters for 80%+ attendance threshold
- Displays day of week and exact percentage
- Plan company meetings with maximum participation

### PTO Utilization Gauge

Company-wide utilization:
- Large percentage display
- Progress bar visualization
- Used vs. allocated comparison
- Employee count tracked

### Coverage Gap Analysis

For each department:
- Analyze next 30 days
- Identify potential coverage issues
- Shows who's out when
- Warning for 30%+ absence rate
- Managers see their department only

---

## Trends Tab Features

### Monthly PTO Trends Chart

Interactive Plotly chart showing:
- Stacked area chart by leave type
- Vacation, Sick, Personal breakdown
- Month-by-month visualization
- Click legends to toggle types

### PTO by Day of Week

Pattern analysis:
- Bar chart showing average PTO per weekday
- Detects Monday/Friday clustering
- Orange highlighting for suspicious patterns
- Helps identify potential abuse patterns

### Department Utilization Rates

Horizontal bar chart showing:
- Utilization rate by department
- Color-coded health status:
  - Green (70-90%) = Healthy
  - Yellow (50-70%) = Low
  - Red (<50%) = Burnout risk
  - Orange (>90%) = Coverage risk
- Target line at 75%

### Department Comparison Table

Sortable table with:
- Employee count per department
- Total requests made
- Total days used
- Average days per employee
- Click columns to sort

### Top PTO Users

Rankings of employees by PTO usage:
- Medal icons for top 3
- Shows name and department
- Days taken displayed
- Helps identify patterns

---

## Insights Tab Features

### AI-Powered Recommendations

Automatically generated actionable insights:

**HIGH Priority (Red)**
- Employees at high carryover risk
- Critical coverage gaps detected

**MEDIUM Priority (Amber)**
- Departments with low utilization
- Work-life balance concerns

**LOW Priority (Blue)**
- Pattern anomalies detected
- Minor attention items

**INFO (Green)**
- Optimal meeting date suggestions
- Positive trends

Each recommendation shows:
- Title and category
- Suggested action
- Affected employees/departments

### Carryover Risk Analysis

#### Risk Gauge
Visual gauge showing:
- Number of employees at risk
- Threshold indicators
- Color zones for severity

#### Risk Table
Detailed breakdown of at-risk employees:
- Employee name and department
- Remaining vs. total vacation
- Risk level (HIGH/MEDIUM/LOW)

Risk levels calculated based on:
- HIGH: 80%+ remaining with 60 or fewer days until year-end
- MEDIUM: 60%+ remaining with 90 or fewer days until year-end
- LOW: Other at-risk employees

### Coverage Forecast Timeline

Line chart showing:
- 30-day forward projection
- Coverage percentage by date
- Critical threshold line at 70%
- Red dots indicate critical days
- Blue line shows trend

---

## Export Features

### Export PDF
Click **"Export PDF"** to generate a professional report including:
- Key metrics summary
- Recommendations
- Carryover risk employees
- Optimal meeting dates
- TJM Holdings branded footer

### Export CSV
Click **"Export CSV"** to download:
- Carryover risk employee list
- Spreadsheet compatible
- For further analysis in Excel/Google Sheets

---

## Filters and Controls

### Year Selector
- Choose year to analyze
- Range: current year +/- 2 years
- All data updates automatically

### Refresh Button
- Manually refresh all data
- Useful after new requests are submitted

### Tab Navigation
- Overview: Quick summary
- Trends: Detailed charts
- Insights: Recommendations

---

## Navigation

At the bottom of the page:
- **Back to Dashboard** - Return to main dashboard
- **View Reports** - Go to detailed reports page

---

## For Managers

As a manager, your analytics are **scoped to your department**:
- All metrics filtered to your team
- Coverage gaps show your department
- Recommendations focus on your employees
- Title shows "ANALYTICS - [YOUR DEPARTMENT]"

## For Admins/Superadmins

Full company-wide access:
- See all departments
- Department selector for coverage analysis
- Company-wide recommendations
- Cross-department comparisons
