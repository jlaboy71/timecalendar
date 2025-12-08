"""
Chart components for TJM Time Calendar Analytics Dashboard.
Uses Plotly for interactive visualizations integrated with NiceGUI.
"""

from nicegui import ui
import plotly.graph_objects as go
from datetime import date, timedelta
from typing import List, Dict, Optional
import calendar


def attendance_heatmap(
    attendance_data: List[Dict],
    title: str = "Attendance Heatmap"
) -> None:
    """
    Render a calendar heatmap showing attendance rates.
    Green = high attendance, Red = low attendance.

    attendance_data: List of dicts with keys: date, attendance_rate, absent_count
    """
    if not attendance_data:
        ui.label("No data available").classes('text-gray-500')
        return

    # Group by week
    week_data = {}
    for day in attendance_data:
        d = day['date']
        week_num = d.isocalendar()[1]
        day_of_week = d.weekday()

        if week_num not in week_data:
            week_data[week_num] = [None] * 5  # Mon-Fri

        if day_of_week < 5:
            week_data[week_num][day_of_week] = day

    # Convert to matrix format
    z_data = []
    y_labels = []
    hover_texts = []

    for week_num in sorted(week_data.keys()):
        week = week_data[week_num]
        row = []
        hover_row = []
        for day in week:
            if day:
                row.append(day['attendance_rate'])
                hover_row.append(f"{day['date'].strftime('%b %d')}: {day['attendance_rate']:.1f}%")
            else:
                row.append(None)
                hover_row.append('')
        z_data.append(row)
        hover_texts.append(hover_row)
        y_labels.append(f"Week {week_num}")

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        y=y_labels,
        colorscale=[
            [0, '#ef4444'],      # Red - low attendance
            [0.5, '#fbbf24'],    # Yellow - medium
            [1, '#22c55e']       # Green - high attendance
        ],
        zmin=50,
        zmax=100,
        hovertemplate='%{text}<extra></extra>',
        text=hover_texts,
        colorbar=dict(title='Attendance %')
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Day of Week',
        yaxis_title='Week',
        height=350,
        margin=dict(l=60, r=20, t=40, b=40)
    )

    ui.plotly(fig).classes('w-full')


def monthly_trend_chart(
    monthly_data: List[Dict],
    title: str = "PTO Usage by Month"
) -> None:
    """
    Render a stacked area chart showing PTO trends across months.

    monthly_data: List of dicts with keys: month, vacation_days, sick_days, personal_days
    """
    if not monthly_data:
        ui.label("No data available").classes('text-gray-500')
        return

    months = [calendar.month_abbr[m['month']] for m in monthly_data]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=months,
        y=[m.get('vacation_days', 0) for m in monthly_data],
        mode='lines',
        name='Vacation',
        fill='tozeroy',
        line=dict(color='#3b82f6'),
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=[m.get('sick_days', 0) for m in monthly_data],
        mode='lines',
        name='Sick',
        fill='tozeroy',
        line=dict(color='#ef4444'),
        fillcolor='rgba(239, 68, 68, 0.3)'
    ))

    fig.add_trace(go.Scatter(
        x=months,
        y=[m.get('personal_days', 0) for m in monthly_data],
        mode='lines',
        name='Personal',
        fill='tozeroy',
        line=dict(color='#22c55e'),
        fillcolor='rgba(34, 197, 94, 0.3)'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Month',
        yaxis_title='Days',
        height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=50, r=20, t=60, b=40)
    )

    ui.plotly(fig).classes('w-full')


def department_utilization_bars(
    dept_data: List[Dict],
    title: str = "PTO Utilization by Department"
) -> None:
    """
    Render horizontal bar chart comparing department utilization rates.
    Color-coded: Green = healthy (70-90%), Yellow = low (<70%), Red = high (>90%).

    dept_data: List of dicts with keys: department_name, utilization_rate
    """
    if not dept_data:
        ui.label("No data available").classes('text-gray-500')
        return

    departments = [d['department_name'] for d in dept_data]
    utilization = [d.get('utilization_rate', 0) for d in dept_data]

    # Color based on utilization
    colors = []
    for u in utilization:
        if u < 50:
            colors.append('#ef4444')  # Red - too low (burnout risk)
        elif u < 70:
            colors.append('#fbbf24')  # Yellow - low
        elif u <= 90:
            colors.append('#22c55e')  # Green - healthy
        else:
            colors.append('#f97316')  # Orange - high (coverage risk)

    fig = go.Figure(go.Bar(
        x=utilization,
        y=departments,
        orientation='h',
        marker_color=colors,
        text=[f'{u:.1f}%' for u in utilization],
        textposition='outside',
        hovertemplate='%{y}<br>Utilization: %{x:.1f}%<extra></extra>'
    ))

    # Add target line
    fig.add_vline(x=75, line_dash="dash", line_color="gray",
                  annotation_text="Target: 75%")

    fig.update_layout(
        title=title,
        xaxis_title='Utilization %',
        yaxis_title='',
        height=max(250, len(departments) * 40),
        xaxis=dict(range=[0, 110]),
        margin=dict(l=120, r=60, t=40, b=40)
    )

    ui.plotly(fig).classes('w-full')


def coverage_timeline(
    forecast_data: List[Dict],
    title: str = "Coverage Forecast"
) -> None:
    """
    Render a timeline showing expected coverage with critical thresholds.

    forecast_data: List of dicts with keys: date, coverage_rate, is_critical
    """
    if not forecast_data:
        ui.label("No data available").classes('text-gray-500')
        return

    dates = [f['date'].strftime('%m/%d') for f in forecast_data]
    coverage = [f['coverage_rate'] for f in forecast_data]

    # Color points by criticality
    colors = ['#ef4444' if f.get('is_critical', False) else '#22c55e' for f in forecast_data]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=coverage,
        mode='lines+markers',
        name='Coverage',
        line=dict(color='#3b82f6', width=2),
        marker=dict(color=colors, size=8),
        hovertemplate='%{x}<br>Coverage: %{y:.1f}%<extra></extra>'
    ))

    # Add minimum threshold line at 70%
    fig.add_hline(y=70, line_dash="dash", line_color="red",
                  annotation_text="Min: 70%")

    fig.update_layout(
        title=title,
        xaxis_title='Date',
        yaxis_title='Coverage %',
        height=280,
        yaxis=dict(range=[0, 110]),
        margin=dict(l=50, r=20, t=40, b=40)
    )

    ui.plotly(fig).classes('w-full')


def day_of_week_pattern(
    pattern_data: Dict[str, float],
    title: str = "PTO by Day of Week"
) -> None:
    """
    Render bar chart showing average PTO by day of week.
    Highlights Monday/Friday clustering if detected.

    pattern_data: Dict with keys Mon, Tue, Wed, Thu, Fri and float values
    """
    if not pattern_data:
        ui.label("No data available").classes('text-gray-500')
        return

    days = list(pattern_data.keys())
    values = list(pattern_data.values())

    # Highlight Mon/Fri if they're notably higher
    if len(values) >= 5:
        avg_mid_week = sum(values[1:4]) / 3 if values[1:4] else 1
        colors = []
        for i, v in enumerate(values):
            if i in [0, 4] and avg_mid_week > 0 and v > avg_mid_week * 1.3:
                colors.append('#f97316')  # Orange - potential pattern
            else:
                colors.append('#3b82f6')  # Blue - normal
    else:
        colors = ['#3b82f6'] * len(values)

    fig = go.Figure(go.Bar(
        x=days,
        y=values,
        marker_color=colors,
        text=[f'{v:.1f}' for v in values],
        textposition='outside'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Day',
        yaxis_title='Avg PTO Days',
        height=280,
        margin=dict(l=50, r=20, t=40, b=40)
    )

    ui.plotly(fig).classes('w-full')


def carryover_risk_gauge(
    at_risk_count: int,
    total_employees: int,
    title: str = "Carryover Risk"
) -> None:
    """
    Render a gauge chart showing percentage of employees at carryover risk.
    """
    if total_employees == 0:
        ui.label("No employee data").classes('text-gray-500')
        return

    risk_pct = (at_risk_count / total_employees * 100)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=at_risk_count,
        title={'text': title},
        number={'suffix': f' / {total_employees}'},
        gauge={
            'axis': {'range': [0, total_employees]},
            'bar': {'color': "#ef4444"},
            'steps': [
                {'range': [0, total_employees * 0.1], 'color': "#dcfce7"},
                {'range': [total_employees * 0.1, total_employees * 0.25], 'color': "#fef9c3"},
                {'range': [total_employees * 0.25, total_employees], 'color': "#fee2e2"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': total_employees * 0.2
            }
        }
    ))

    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=20))
    ui.plotly(fig).classes('w-full')


def year_comparison_chart(
    multi_year_data: Dict[int, List[Dict]],
    title: str = "Year-over-Year Comparison"
) -> None:
    """
    Render line chart comparing PTO patterns across multiple years.

    multi_year_data: Dict with year keys and list of monthly data dicts
    """
    if not multi_year_data:
        ui.label("No data available").classes('text-gray-500')
        return

    fig = go.Figure()

    colors = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6']

    for idx, (year, monthly_data) in enumerate(multi_year_data.items()):
        months = [calendar.month_abbr[m.get('month', idx+1)] for m in monthly_data]
        totals = [m.get('total_days', 0) for m in monthly_data]

        fig.add_trace(go.Scatter(
            x=months,
            y=totals,
            mode='lines+markers',
            name=str(year),
            line=dict(color=colors[idx % len(colors)], width=2)
        ))

    fig.update_layout(
        title=title,
        xaxis_title='Month',
        yaxis_title='Total PTO Days',
        height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=50, r=20, t=60, b=40)
    )

    ui.plotly(fig).classes('w-full')


def simple_pie_chart(
    data: List[Dict],
    title: str = "Distribution"
) -> None:
    """
    Render a simple pie chart.

    data: List of dicts with keys: label, value, color (optional)
    """
    if not data:
        ui.label("No data available").classes('text-gray-500')
        return

    labels = [d['label'] for d in data]
    values = [d['value'] for d in data]
    colors = [d.get('color', None) for d in data]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors if all(colors) else None
    )])

    fig.update_layout(
        title=title,
        height=280,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    ui.plotly(fig).classes('w-full')
