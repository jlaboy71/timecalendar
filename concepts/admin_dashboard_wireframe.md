# Enhanced Admin Dashboard - Wireframe Concept

## Key Enhancements Over Current Design

### 1. Richer Stats Cards
```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ 🔵               │ 🟣               │ 🟠               │ 🟢               │
│  ┌───┐           │  ┌───┐           │  ┌───┐           │  ┌───┐           │
│  │👥 │  10       │  │🏢 │  2        │  │⏰ │  3        │  │📅 │  4        │
│  └───┘           │  └───┘           │  └───┘  ⚠️      │  └───┘           │
│ Active Employees │ Departments      │ Pending Requests │ PTO This Week   │
│ ↑ +2 this month  │                  │ Action Required  │ employees out   │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```
- Gradient icon circles (not flat)
- Trend indicators with direction arrows
- Warning badges for actionable items
- Left border accent matching icon color

### 2. NEW: Quick Insights Panel
```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│ 📅 Upcoming Time Off                │ 📊 Department PTO Usage             │
├─────────────────────────────────────┼─────────────────────────────────────┤
│ 🔵 John Smith                       │                                     │
│    Vacation • Dec 16-20             │ Technology  ████████████░░░░ 75%   │
│                                     │                                     │
│ 🟣 Jane Doe                         │ Operations  ██████░░░░░░░░░░ 45%   │
│    Personal • Dec 18                │                                     │
│                                     │ % of allocated PTO used this year   │
│ 🔴 Mike Johnson                     │                                     │
│    WFH • Dec 19-20                  │                                     │
├─────────────────────────────────────┤                                     │
│ → View Full Calendar                │                                     │
└─────────────────────────────────────┴─────────────────────────────────────┘
```
- Shows upcoming time off at a glance
- Department usage visualization
- Quick access without leaving dashboard

### 3. Action Buttons with Badges
```
┌────────────────────────────────────────────────────────────────────────────┐
│ ✅ APPROVALS                                                               │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐   ┌─────────────────────────────────┐    │
│  │ 📋 PTO APPROVALS        🔴3 │   │ 🔄 CARRYOVER APPROVALS      🟠1 │    │
│  └─────────────────────────────┘   └─────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────┘
```
- Notification badges showing pending counts
- Visual urgency indicators

### 4. Section Headers with Icons
```
⚙️  MANAGEMENT
📋 APPROVALS
📁 RESOURCES
🔧 SYSTEM
```
- Icons provide quick visual identification
- Uppercase with letter-spacing
- Muted color for hierarchy

## Color System

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Navy | `#111827` |
| Cards | Dark Gray | `#1f2937` |
| Borders | Medium Gray | `#374151` |
| Gold Accent | TJM Gold | `#C9A227` |
| Blue | Primary | `#3b82f6` |
| Green | Success | `#22c55e` |
| Orange | Warning | `#f59e0b` |
| Purple | Secondary | `#8b5cf6` |
| Red | Danger | `#ef4444` |

## Button Styles

### Outline Buttons (Most actions)
```css
border: 1px solid [color];
background: transparent;
color: [color];
hover: subtle glow effect
```

### Filled Buttons (Primary actions)
```css
background: [color];
color: white;
hover: darken
```

### Gold Accent (Special/Featured)
```css
border: 1px solid #C9A227;
color: #C9A227;
box-shadow: 0 0 10px rgba(201, 162, 39, 0.3);
```

## Implementation Notes

1. **Stats Cards**: Add `border-left-4` with accent color, gradient backgrounds for icons
2. **Insight Cards**: New component, shows live data from dashboard queries
3. **Badges**: Use Quasar `q-badge` with floating position on buttons
4. **Charts**: Simple CSS progress bars, no external library needed
5. **Responsive**: Stack cards on mobile, maintain 4-column on desktop

## Files Generated

- `admin_dashboard_concept.json` - Structured JSON for programmatic use
- `admin_dashboard_prompt.txt` - Text prompt for AI image generation
- `admin_dashboard_wireframe.md` - This documentation file
