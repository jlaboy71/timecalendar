"""
AI Agent Analytics Dashboard
============================
Admin-only page for viewing AI agent usage analytics.
Styled to match PTO Central's dark theme and UI patterns.

URL: /admin/analytics
Access: admin, superadmin only
"""

from nicegui import ui, app, context
from datetime import datetime
import pytz

# Import theme and components
from nicegui_app.components.theme import apply_dark_mode, PTO_GOLD, PTO_GRAY
from nicegui_app.logo import LOGO_DATA_URL
from src.database import get_db


def get_time_based_greeting() -> str:
    """Get appropriate greeting based on Chicago time."""
    chicago_tz = pytz.timezone('America/Chicago')
    hour = datetime.now(chicago_tz).hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def create_help_button(title: str, message: str):
    """Create a gold help button that shows a dark-themed dialog."""
    def show_help():
        # Create dialog at root level using context.client.content
        with context.client.content:
            with ui.dialog() as dialog, ui.card().classes('p-5 max-w-md').style('background-color: #1f2937;'):
                with ui.row().classes('items-center gap-2 mb-3'):
                    ui.icon('help_outline', size='sm').style(f'color: {PTO_GOLD};')
                    ui.label(title).classes('text-lg font-bold').style(f'color: {PTO_GOLD};')
                ui.html(message, sanitize=False).classes('text-gray-300 text-sm leading-relaxed')
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Got it', on_click=dialog.close).style(f'background-color: {PTO_GOLD} !important; color: black !important;')
            dialog.open()

    return ui.button(icon='help_outline', on_click=show_help).props('flat dense round size=sm').style(f'color: {PTO_GOLD};')


def render_header(user: dict, selected_days: dict):
    """Render the page header matching PTO Central style."""
    greeting = get_time_based_greeting()
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('username', 'User')
    is_dark = app.storage.general.get('dark_mode', True)
    greeting_color = PTO_GOLD if is_dark else PTO_GRAY

    with ui.row().classes('w-full justify-between items-start mb-6'):
        # Left side: Logo and title
        with ui.column().classes('gap-1'):
            # Logo
            ui.element('img').props(f'src="{LOGO_DATA_URL}"').style(
                'height: 50px; width: auto; cursor: pointer;'
            ).on('click', lambda: ui.navigate.to('/dashboard'))

            # Title with back button
            with ui.row().classes('items-center gap-2'):
                ui.button(
                    icon='arrow_back',
                    on_click=lambda: ui.navigate.to('/analytics')
                ).props('flat round dense').tooltip('Back to Workforce Analytics')
                ui.label('AI AGENT ANALYTICS').classes('text-lg font-bold uppercase').style(f'color: {greeting_color};')

        # Right side: Greeting and controls
        with ui.column().classes('items-end gap-1'):
            ui.label(f'{greeting}, {user_name}').classes('text-base font-medium uppercase').style(f'color: {greeting_color};')

            with ui.row().classes('items-center gap-2'):
                # Time period selector
                ui.select(
                    options={'7': '7 days', '30': '30 days', '90': '90 days'},
                    value=str(selected_days['value']),
                    on_change=lambda e: update_period(e.value, selected_days)
                ).props('dense borderless').classes('min-w-24').style(f'color: {PTO_GOLD};')

                # Dark mode toggle
                dark_mode = ui.dark_mode()
                is_dark = app.storage.general.get('dark_mode', True)
                if is_dark:
                    dark_mode.enable()

                def toggle_dark():
                    current = app.storage.general.get('dark_mode', True)
                    app.storage.general['dark_mode'] = not current
                    if not current:
                        dark_mode.enable()
                    else:
                        dark_mode.disable()

                ui.button(
                    icon='dark_mode',
                    on_click=toggle_dark
                ).props('flat round').style(f'color: {PTO_GOLD} !important;').tooltip('Toggle Dark Mode')

                # Logout
                def logout():
                    app.storage.general.clear()
                    ui.navigate.to('/login')

                ui.button(
                    'LOGOUT',
                    on_click=logout
                ).props('flat color=red').classes('text-xs')


def update_period(days: str, selected_days: dict):
    """Update the selected time period and refresh."""
    selected_days['value'] = int(days)
    ui.navigate.to(f'/admin/analytics?days={days}')


def load_stats(days: int = 30) -> dict:
    """Load analytics data from service."""
    try:
        from src.services.analytics_service import AnalyticsService
        db = next(get_db())
        try:
            service = AnalyticsService(db)
            return service.get_dashboard_stats(days=days)
        finally:
            db.close()
    except Exception as e:
        print(f"Error loading stats: {e}")
        return {
            "summary": {"total_interactions": 0, "unique_users": 0, "successful_actions": 0, "avg_per_user": 0, "avg_response_time": 0, "error_rate": 0},
            "trends": [],
            "by_agent": {},
            "by_action": {},
            "confirmation_rate": {"acceptance_rate": 0, "accepted": 0, "rejected": 0},
            "top_users": [],
            "hourly_distribution": {}
        }


def render_summary_cards(summary: dict):
    """Render the top summary metric cards."""
    with ui.row().classes('items-center gap-2 mb-2'):
        ui.icon('dashboard', color='blue')
        ui.label('Key Metrics').classes('text-lg font-semibold')
        create_help_button(
            'AI Agent Metrics',
            '<b>Total Interactions:</b> Number of conversations with AI agents<br><br>'
            '<b>Unique Users:</b> How many different employees used AI features<br><br>'
            '<b>Successful Actions:</b> PTO requests submitted/approved via AI<br><br>'
            '<b>Avg Response:</b> How fast the AI responds (in seconds)<br><br>'
            '<b>Error Rate:</b> Percentage of interactions that had issues<br><br>'
            '<b>Avg/User:</b> Average interactions per user'
        )

    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px;'):
        # Total Interactions
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('chat', size='md', color='blue')
                ui.label(str(summary.get('total_interactions', 0))).classes('text-2xl font-bold text-blue-500')
                ui.label('Interactions').classes('text-xs opacity-70')

        # Unique Users
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('people', size='md', color='purple')
                ui.label(str(summary.get('unique_users', 0))).classes('text-2xl font-bold text-purple-500')
                ui.label('Unique Users').classes('text-xs opacity-70')

        # Successful Actions
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('check_circle', size='md', color='green')
                ui.label(str(summary.get('successful_actions', 0))).classes('text-2xl font-bold text-green-500')
                ui.label('Successful').classes('text-xs opacity-70')

        # Avg Response Time
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('speed', size='md', color='cyan')
                avg_time = summary.get('avg_response_time', 0)
                ui.label(f'{avg_time:.1f}s').classes('text-2xl font-bold text-cyan-500')
                ui.label('Avg Response').classes('text-xs opacity-70')

        # Error Rate
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('error_outline', size='md', color='red')
                error_rate = summary.get('error_rate', 0)
                ui.label(f'{error_rate:.1f}%').classes('text-2xl font-bold text-red-500')
                ui.label('Error Rate').classes('text-xs opacity-70')

        # Avg per User
        with ui.card().classes('p-3'):
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('analytics', size='md').style(f'color: {PTO_GOLD};')
                ui.label(str(summary.get('avg_per_user', 0))).classes('text-2xl font-bold').style(f'color: {PTO_GOLD};')
                ui.label('Avg/User').classes('text-xs opacity-70')


def render_usage_trend(trends: list):
    """Render the usage trend line chart."""
    with ui.card().classes('p-4 h-full'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('trending_up', color='blue')
            ui.label('Usage Trend').classes('text-lg font-semibold')
            create_help_button(
                'Usage Trend',
                'Shows daily AI agent interactions over the selected time period.<br><br>'
                'Higher points indicate more AI usage on that day.<br><br>'
                '<i>Tip: Look for patterns - are certain days busier?</i>'
            )

        if not trends:
            with ui.column().classes('items-center justify-center py-12 opacity-50'):
                ui.icon('show_chart', size='xl')
                ui.label('No data yet').classes('text-lg')
                ui.label('AI interactions will appear here').classes('text-sm')
        else:
            ui.echart({
                'backgroundColor': 'transparent',
                'xAxis': {
                    'type': 'category',
                    'data': [t['date'][-5:] for t in trends],
                    'axisLabel': {'color': '#9ca3af'},
                    'axisLine': {'lineStyle': {'color': '#374151'}}
                },
                'yAxis': {
                    'type': 'value',
                    'axisLabel': {'color': '#9ca3af'},
                    'splitLine': {'lineStyle': {'color': '#374151'}}
                },
                'series': [{
                    'data': [t['interactions'] for t in trends],
                    'type': 'line',
                    'smooth': True,
                    'areaStyle': {'opacity': 0.3, 'color': PTO_GOLD},
                    'lineStyle': {'color': PTO_GOLD, 'width': 3},
                    'itemStyle': {'color': PTO_GOLD}
                }],
                'tooltip': {'trigger': 'axis', 'backgroundColor': '#1f2937', 'borderColor': PTO_GOLD},
                'grid': {'left': 50, 'right': 20, 'bottom': 30, 'top': 20}
            }).classes('w-full').style('height: 220px;')


def render_agent_breakdown(by_agent: dict):
    """Render the agent usage pie chart."""
    with ui.card().classes('p-4 h-full'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('smart_toy', color='purple')
            ui.label('By Agent').classes('text-lg font-semibold')
            create_help_button(
                'Agent Usage',
                '<b>Smart Scheduler:</b> Helps find optimal vacation dates<br><br>'
                '<b>Year-End Optimizer:</b> Prevents PTO loss before Dec 31<br><br>'
                '<b>Approval Assistant:</b> Helps managers process requests'
            )

        if not by_agent:
            with ui.column().classes('items-center justify-center py-12 opacity-50'):
                ui.icon('donut_large', size='xl')
                ui.label('No data yet').classes('text-lg')
        else:
            # Agent colors
            colors = ['#3b82f6', '#f59e0b', '#22c55e']
            ui.echart({
                'backgroundColor': 'transparent',
                'series': [{
                    'type': 'pie',
                    'radius': ['40%', '70%'],
                    'data': [
                        {'value': v, 'name': k.replace('_', ' ').title(), 'itemStyle': {'color': colors[i % len(colors)]}}
                        for i, (k, v) in enumerate(by_agent.items())
                    ],
                    'label': {'color': '#9ca3af'},
                    'emphasis': {'itemStyle': {'shadowBlur': 10, 'shadowColor': 'rgba(201, 162, 39, 0.5)'}}
                }],
                'tooltip': {'trigger': 'item', 'backgroundColor': '#1f2937', 'borderColor': PTO_GOLD},
                'legend': {'bottom': 0, 'textStyle': {'color': '#9ca3af'}}
            }).classes('w-full').style('height: 220px;')


def render_confirmation_gauge(conf: dict):
    """Render the confirmation rate gauge."""
    rate = conf.get('acceptance_rate', 0)
    accepted = conf.get('accepted', 0)
    rejected = conf.get('rejected', 0)

    with ui.card().classes('p-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('verified', color='teal')
            ui.label('Confirmation Rate').classes('text-lg font-semibold')
            create_help_button(
                'Confirmation Rate',
                'Shows how often users confirm AI-suggested actions vs cancel.<br><br>'
                '<b>Yes:</b> User confirmed the action<br>'
                '<b>No:</b> User cancelled the action<br><br>'
                '<i>Higher rates indicate users trust AI suggestions.</i>'
            )

        ui.echart({
            'backgroundColor': 'transparent',
            'series': [{
                'type': 'gauge',
                'startAngle': 180,
                'endAngle': 0,
                'min': 0,
                'max': 100,
                'progress': {'show': True, 'width': 14, 'itemStyle': {'color': PTO_GOLD}},
                'axisLine': {'lineStyle': {'width': 14, 'color': [[1, '#374151']]}},
                'axisTick': {'show': False},
                'splitLine': {'show': False},
                'axisLabel': {'show': False},
                'pointer': {'show': False},
                'detail': {
                    'formatter': '{value}%',
                    'fontSize': 24,
                    'fontWeight': 'bold',
                    'color': PTO_GOLD,
                    'offsetCenter': [0, 0]
                },
                'data': [{'value': rate}]
            }]
        }).classes('w-full h-32')

        with ui.row().classes('justify-around text-center mt-2'):
            with ui.column():
                ui.label(str(accepted)).classes('font-bold text-xl text-green-500')
                ui.label('Yes').classes('text-xs opacity-70')
            with ui.column():
                ui.label(str(rejected)).classes('font-bold text-xl text-red-500')
                ui.label('No').classes('text-xs opacity-70')


def render_actions_chart(by_action: dict):
    """Render the actions breakdown bar chart."""
    with ui.card().classes('p-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('bolt', color='amber')
            ui.label('Actions').classes('text-lg font-semibold')
            create_help_button(
                'AI Actions',
                'Breakdown of actions taken through AI agents:<br><br>'
                '<b>Submit Request:</b> PTO requests created via AI<br>'
                '<b>Approve/Deny:</b> Manager decisions via AI<br>'
                '<b>Cancel:</b> Requests cancelled via AI<br>'
                '<b>Tool Calls:</b> AI tool usage (balance checks, etc.)'
            )

        if not by_action:
            with ui.column().classes('items-center justify-center py-8 opacity-50'):
                ui.icon('bar_chart', size='xl')
                ui.label('No data yet').classes('text-lg')
        else:
            sorted_actions = sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:6]
            ui.echart({
                'backgroundColor': 'transparent',
                'xAxis': {
                    'type': 'value',
                    'axisLabel': {'color': '#9ca3af'},
                    'splitLine': {'lineStyle': {'color': '#374151'}}
                },
                'yAxis': {
                    'type': 'category',
                    'data': [a[0] for a in sorted_actions],
                    'axisLabel': {'color': '#9ca3af'}
                },
                'series': [{
                    'type': 'bar',
                    'data': [a[1] for a in sorted_actions],
                    'itemStyle': {'color': PTO_GOLD, 'borderRadius': [0, 4, 4, 0]}
                }],
                'tooltip': {'trigger': 'axis', 'backgroundColor': '#1f2937', 'borderColor': PTO_GOLD},
                'grid': {'left': 120, 'right': 20, 'bottom': 20, 'top': 10}
            }).classes('w-full h-48')


def render_top_users(users: list):
    """Render the top users leaderboard."""
    with ui.card().classes('p-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('leaderboard', color='amber')
            ui.label('Top Users').classes('text-lg font-semibold')
            create_help_button(
                'Top AI Users',
                'Employees who use AI agents the most.<br><br>'
                'High usage indicates comfort with AI features.<br><br>'
                '<i>Consider these users for feedback on AI improvements.</i>'
            )

        if not users:
            with ui.column().classes('items-center justify-center py-8 opacity-50'):
                ui.icon('emoji_events', size='xl')
                ui.label('No data yet').classes('text-lg')
        else:
            for i, u in enumerate(users[:5], 1):
                medal_colors = {1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32'}
                medal_color = medal_colors.get(i, '#6b7280')

                with ui.row().classes('w-full items-center justify-between py-2 px-2 rounded hover:bg-gray-700/30'):
                    with ui.row().classes('items-center gap-3'):
                        ui.badge(str(i)).style(f'background-color: {medal_color}; color: black;')
                        ui.label(u.get('username', 'Unknown')).classes('font-medium')
                    ui.label(str(u.get('interactions', 0))).classes('text-gray-400')


def render_hourly_distribution(hourly: dict):
    """Render the hourly usage heatmap."""
    with ui.card().classes('p-4'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('schedule', color='cyan')
            ui.label('Peak Usage Hours').classes('text-lg font-semibold')
            create_help_button(
                'Peak Usage Hours',
                'Shows when employees use AI agents the most during the day.<br><br>'
                'Taller bars = more usage during that hour.<br><br>'
                '<i>Helps identify when AI assistance is most needed.</i>'
            )

        if not hourly:
            with ui.column().classes('items-center justify-center py-8 opacity-50'):
                ui.icon('access_time', size='xl')
                ui.label('No data yet').classes('text-lg')
        else:
            # Create hourly data (0-23)
            hours = [str(h) for h in range(24)]
            values = [hourly.get(str(h), 0) for h in range(24)]

            ui.echart({
                'backgroundColor': 'transparent',
                'xAxis': {
                    'type': 'category',
                    'data': ['12a', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
                             '12p', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'],
                    'axisLabel': {'color': '#9ca3af', 'fontSize': 10},
                    'axisLine': {'lineStyle': {'color': '#374151'}}
                },
                'yAxis': {
                    'type': 'value',
                    'axisLabel': {'color': '#9ca3af'},
                    'splitLine': {'lineStyle': {'color': '#374151'}}
                },
                'series': [{
                    'type': 'bar',
                    'data': values,
                    'itemStyle': {
                        'color': {
                            'type': 'linear',
                            'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                            'colorStops': [
                                {'offset': 0, 'color': PTO_GOLD},
                                {'offset': 1, 'color': '#92400e'}
                            ]
                        },
                        'borderRadius': [4, 4, 0, 0]
                    }
                }],
                'tooltip': {'trigger': 'axis', 'backgroundColor': '#1f2937', 'borderColor': PTO_GOLD},
                'grid': {'left': 40, 'right': 10, 'bottom': 30, 'top': 10}
            }).classes('w-full h-40')


def render_ai_education_section():
    """Render the AI educational explanation section."""
    with ui.card().classes('p-6 mt-6').style(f'border: 1px solid {PTO_GOLD}33; background-color: #1f293766;'):
        # Header
        with ui.row().classes('items-center gap-3 mb-4'):
            ui.icon('school', size='md').style(f'color: {PTO_GOLD};')
            ui.label('Understanding Your AI Assistants').classes('text-xl font-bold').style(f'color: {PTO_GOLD};')

        # Introduction
        ui.html('''
            <p class="text-gray-300 mb-4">
                PTO Central uses <b>three specialized AI agents</b> that work together to make managing
                time off easier for everyone. Think of them as smart assistants that understand your
                company's PTO policies and can help with specific tasks.
            </p>
        ''', sanitize=False)

        # The Three Agents
        with ui.element('div').classes('grid grid-cols-1 md:grid-cols-3 gap-4 mb-6'):
            # Smart Scheduler
            with ui.card().classes('p-4').style('background-color: #1e3a5f; border-left: 4px solid #3b82f6;'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('event_available', color='blue')
                    ui.label('Smart Scheduler').classes('font-bold text-blue-400')
                ui.html('''
                    <p class="text-sm text-gray-300 mb-2">
                        <b>What it does:</b> Helps you find the best dates for your vacation.
                    </p>
                    <p class="text-sm text-gray-300 mb-2">
                        <b>How it helps:</b> Checks your balance, looks at team coverage,
                        avoids holidays, and suggests optimal dates.
                    </p>
                    <p class="text-sm text-gray-400 italic">
                        "I want to take a week off in March" → Suggests best available dates
                    </p>
                ''', sanitize=False)

            # Year-End Optimizer
            with ui.card().classes('p-4').style('background-color: #3d2e1f; border-left: 4px solid #f59e0b;'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('calendar_month', color='amber')
                    ui.label('Year-End Optimizer').classes('font-bold text-amber-400')
                ui.html('''
                    <p class="text-sm text-gray-300 mb-2">
                        <b>What it does:</b> Prevents you from losing unused PTO at year end.
                    </p>
                    <p class="text-sm text-gray-300 mb-2">
                        <b>How it helps:</b> Analyzes your remaining balance, calculates
                        expiring time, and creates a plan to use it before December 31st.
                    </p>
                    <p class="text-sm text-gray-400 italic">
                        "How much PTO will I lose?" → Shows expiring balance + usage plan
                    </p>
                ''', sanitize=False)

            # Approval Assistant
            with ui.card().classes('p-4').style('background-color: #1f3d2e; border-left: 4px solid #22c55e;'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('approval', color='green')
                    ui.label('Approval Assistant').classes('font-bold text-green-400')
                ui.html('''
                    <p class="text-sm text-gray-300 mb-2">
                        <b>What it does:</b> Helps managers review and process PTO requests faster.
                    </p>
                    <p class="text-sm text-gray-300 mb-2">
                        <b>How it helps:</b> Summarizes pending requests, checks for conflicts,
                        and enables batch approvals with policy compliance checks.
                    </p>
                    <p class="text-sm text-gray-400 italic">
                        "Show me pending requests" → Lists all with recommendations
                    </p>
                ''', sanitize=False)

        # How They Work Together
        with ui.expansion('How Do They Work Together?', icon='sync_alt').classes('w-full mb-4').style(f'background-color: #374151; border-radius: 8px;'):
            ui.html(f'''
                <div class="p-3">
                    <p class="text-gray-300 mb-3">
                        All three agents share the same knowledge about your company's PTO policies
                        and have access to real-time data. Here's how a typical workflow might look:
                    </p>
                    <ol class="text-gray-300 text-sm space-y-2 list-decimal list-inside">
                        <li><b>Employee</b> asks Smart Scheduler: "I need 3 days off next month"</li>
                        <li><b>Smart Scheduler</b> checks balance, team calendar, and suggests March 15-17</li>
                        <li><b>Employee</b> confirms and submits the request</li>
                        <li><b>Manager</b> opens Approval Assistant to review pending requests</li>
                        <li><b>Approval Assistant</b> shows the request with a coverage analysis</li>
                        <li><b>Manager</b> approves with one click (AI already verified policy compliance)</li>
                    </ol>
                    <p class="text-gray-400 text-sm mt-3 italic">
                        The AI handles the policy checking and calendar analysis so humans can focus on decisions.
                    </p>
                </div>
            ''', sanitize=False)

        # Understanding the Metrics
        with ui.expansion('What Do These Metrics Mean?', icon='insights').classes('w-full mb-4').style(f'background-color: #374151; border-radius: 8px;'):
            ui.html('''
                <div class="p-3">
                    <table class="w-full text-sm">
                        <tr class="border-b border-gray-600">
                            <td class="py-2 text-blue-400 font-medium">Total Interactions</td>
                            <td class="py-2 text-gray-300">Every time someone sends a message to an AI agent, that's one interaction. More interactions = more AI adoption.</td>
                        </tr>
                        <tr class="border-b border-gray-600">
                            <td class="py-2 text-purple-400 font-medium">Unique Users</td>
                            <td class="py-2 text-gray-300">How many different employees have used AI features. Helps track adoption across the organization.</td>
                        </tr>
                        <tr class="border-b border-gray-600">
                            <td class="py-2 text-green-400 font-medium">Successful Actions</td>
                            <td class="py-2 text-gray-300">PTO requests that were actually submitted or approved through AI. This is the "real work" getting done.</td>
                        </tr>
                        <tr class="border-b border-gray-600">
                            <td class="py-2 text-cyan-400 font-medium">Avg Response Time</td>
                            <td class="py-2 text-gray-300">How fast the AI responds. Lower is better. Should typically be under 3 seconds.</td>
                        </tr>
                        <tr class="border-b border-gray-600">
                            <td class="py-2 text-red-400 font-medium">Error Rate</td>
                            <td class="py-2 text-gray-300">Percentage of interactions where something went wrong. Lower is better. Under 5% is healthy.</td>
                        </tr>
                        <tr>
                            <td class="py-2 font-medium" style="color: #C9A227;">Confirmation Rate</td>
                            <td class="py-2 text-gray-300">When AI suggests an action, how often users say "yes" vs "cancel". High rates mean users trust the AI's suggestions.</td>
                        </tr>
                    </table>
                </div>
            ''', sanitize=False)

        # Safety & Privacy
        with ui.expansion('Safety & Privacy', icon='security').classes('w-full').style(f'background-color: #374151; border-radius: 8px;'):
            ui.html(f'''
                <div class="p-3">
                    <p class="text-gray-300 mb-3">
                        <b>Human-in-the-Loop:</b> AI agents can <i>suggest</i> actions, but they always ask for
                        confirmation before making changes. No PTO request is submitted or approved without
                        explicit user confirmation.
                    </p>
                    <p class="text-gray-300 mb-3">
                        <b>Safety Gate:</b> All write operations (submit, approve, deny, cancel) require a
                        confirmation step. The AI generates a unique token that expires in 5 minutes,
                        ensuring you're always in control.
                    </p>
                    <p class="text-gray-300 mb-3">
                        <b>Audit Trail:</b> Every AI action is logged with timestamps, user info, and
                        what action was taken. Admins can review the complete history.
                    </p>
                    <p class="text-gray-300">
                        <b>Data Privacy:</b> AI agents only access PTO-related data needed for their task.
                        Conversations are not stored beyond the current session.
                    </p>
                </div>
            ''', sanitize=False)


def admin_analytics_page():
    """Main AI Agent Analytics page."""
    # Apply dark mode theme
    apply_dark_mode()

    # Get user from storage
    user = app.storage.user.get('user', {})

    # State for time period
    selected_days = {'value': 30}

    # Load data
    stats = load_stats(selected_days['value'])

    # Main container
    with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
        # Header
        render_header(user, selected_days)

        # Summary cards row
        render_summary_cards(stats.get('summary', {}))

        # Charts row 1: Trend + Agent breakdown + Peak Hours (3x3 layout)
        with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4'):
            render_usage_trend(stats.get('trends', []))
            render_agent_breakdown(stats.get('by_agent', {}))
            render_hourly_distribution(stats.get('hourly_distribution', {}))

        # Charts row 2: Confirmation + Actions + Top Users
        with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4'):
            render_confirmation_gauge(stats.get('confirmation_rate', {}))
            render_actions_chart(stats.get('by_action', {}))
            render_top_users(stats.get('top_users', []))

        # AI Education Section
        render_ai_education_section()

        # Footer with back button
        with ui.row().classes('w-full justify-between items-center mt-8'):
            ui.button(
                'Back to Analytics',
                icon='arrow_back',
                on_click=lambda: ui.navigate.to('/analytics')
            ).props('outline').style(f'border-color: {PTO_GOLD} !important; color: {PTO_GOLD} !important;')
            ui.label('Powered by Claude AI').classes('text-sm opacity-50')
