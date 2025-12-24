"""
AI Agent Analytics Dashboard
============================
Admin-only page for viewing AI agent usage analytics.
Styled to match PTO Central's dark theme and UI patterns.

URL: /admin/analytics
Access: admin, superadmin only
"""

from nicegui import ui, app
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
        with ui.dialog() as dialog, ui.card().classes('p-4 max-w-md').style('background-color: #1f2937;'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('help_outline', color='amber', size='sm')
                ui.label(title).classes('text-lg font-bold').style(f'color: {PTO_GOLD};')
            ui.html(message).classes('text-gray-300 text-sm')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Got it', on_click=dialog.close).props('color=amber')
        dialog.open()

    return ui.button(icon='help_outline', on_click=show_help).props('flat dense round size=sm').style('color: #f59e0b;')


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

                # Help button
                ui.button(
                    icon='help_outline',
                    on_click=lambda: ui.navigate.to('/help')
                ).props('flat round').style(f'color: {PTO_GOLD} !important;').tooltip('Help Center')

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
            "summary": {"total_interactions": 0, "unique_users": 0, "successful_actions": 0, "avg_per_user": 0},
            "trends": [],
            "by_agent": {},
            "by_action": {},
            "confirmation_rate": {"acceptance_rate": 0, "accepted": 0, "rejected": 0},
            "top_users": []
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
            '<b>Avg/User:</b> Average interactions per user'
        )

    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;'):
        # Total Interactions
        with ui.card().classes('p-4'):
            with ui.column().classes('items-center w-full'):
                ui.icon('chat', size='lg', color='blue')
                ui.label(str(summary.get('total_interactions', 0))).classes('text-3xl font-bold text-blue-500')
                ui.label('Total Interactions').classes('text-sm opacity-70')

        # Unique Users
        with ui.card().classes('p-4'):
            with ui.column().classes('items-center w-full'):
                ui.icon('people', size='lg', color='purple')
                ui.label(str(summary.get('unique_users', 0))).classes('text-3xl font-bold text-purple-500')
                ui.label('Unique Users').classes('text-sm opacity-70')

        # Successful Actions
        with ui.card().classes('p-4'):
            with ui.column().classes('items-center w-full'):
                ui.icon('check_circle', size='lg', color='green')
                ui.label(str(summary.get('successful_actions', 0))).classes('text-3xl font-bold text-green-500')
                ui.label('Successful Actions').classes('text-sm opacity-70')

        # Avg per User
        with ui.card().classes('p-4'):
            with ui.column().classes('items-center w-full'):
                ui.icon('analytics', size='lg').style(f'color: {PTO_GOLD};')
                ui.label(str(summary.get('avg_per_user', 0))).classes('text-3xl font-bold').style(f'color: {PTO_GOLD};')
                ui.label('Avg/User').classes('text-sm opacity-70')


def render_usage_trend(trends: list):
    """Render the usage trend line chart."""
    with ui.card().classes('p-4'):
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
            with ui.column().classes('items-center justify-center py-8 opacity-50'):
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
            }).classes('w-full h-64')


def render_agent_breakdown(by_agent: dict):
    """Render the agent usage pie chart."""
    with ui.card().classes('p-4'):
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
            with ui.column().classes('items-center justify-center py-8 opacity-50'):
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
            }).classes('w-full h-48')


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

        # Charts row 1: Trend + Agent breakdown
        with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-5 gap-4 mt-4'):
            with ui.element('div').classes('lg:col-span-3'):
                render_usage_trend(stats.get('trends', []))
            with ui.element('div').classes('lg:col-span-2'):
                render_agent_breakdown(stats.get('by_agent', {}))

        # Charts row 2: Confirmation + Actions + Top Users
        with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4'):
            render_confirmation_gauge(stats.get('confirmation_rate', {}))
            render_actions_chart(stats.get('by_action', {}))
            render_top_users(stats.get('top_users', []))

        # Footer
        with ui.row().classes('w-full justify-center mt-8 opacity-50'):
            ui.label('Powered by Claude AI').classes('text-sm')
