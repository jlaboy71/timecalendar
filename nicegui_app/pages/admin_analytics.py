"""
Agent Analytics Dashboard
=========================
Admin-only page for viewing AI agent usage analytics.

URL: /admin/analytics
Access: admin, superadmin only
"""

from nicegui import ui, app
from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY


def admin_analytics_page():
    """Render the analytics dashboard."""
    # Check auth
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/login')
        return

    # Check admin access
    role = user.get('role', '')
    if role not in ['admin', 'superadmin']:
        ui.notify("Admin access required", type="negative")
        ui.navigate.to('/dashboard')
        return

    # Load stats
    stats = _load_stats(days=30)

    with ui.column().classes("w-full min-h-screen bg-gray-50"):
        # Header
        with ui.row().classes("w-full p-4 bg-white shadow items-center justify-between"):
            with ui.row().classes("items-center gap-3"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props("flat")
                ui.label("AI Agent Analytics").classes("text-2xl font-bold")

            ui.select(
                options={"7": "7 days", "30": "30 days", "90": "90 days"},
                value="30",
                on_change=lambda e: _reload_stats(int(e.value))
            ).props("dense")

        # Content
        with ui.column().classes("p-6 gap-6 w-full max-w-7xl mx-auto"):
            # Summary cards
            _render_summary(stats.get("summary", {}))

            # Charts row
            with ui.row().classes("w-full gap-6"):
                with ui.card().classes("flex-1 p-4"):
                    ui.label("Usage Trend").classes("font-semibold mb-2")
                    _render_trend_chart(stats.get("trends", []))

                with ui.card().classes("w-80 p-4"):
                    ui.label("By Agent").classes("font-semibold mb-2")
                    _render_agent_pie(stats.get("by_agent", {}))

            # Bottom row
            with ui.row().classes("w-full gap-6"):
                with ui.card().classes("w-80 p-4"):
                    ui.label("Confirmation Rate").classes("font-semibold mb-2")
                    _render_confirmation_gauge(stats.get("confirmation_rate", {}))

                with ui.card().classes("flex-1 p-4"):
                    ui.label("Actions").classes("font-semibold mb-2")
                    _render_actions_bar(stats.get("by_action", {}))

                with ui.card().classes("w-80 p-4"):
                    ui.label("Top Users").classes("font-semibold mb-2")
                    _render_top_users(stats.get("top_users", []))


def _load_stats(days: int = 30):
    """Load analytics data."""
    try:
        from src.database import get_db
        from src.services.analytics_service import AnalyticsService

        db = next(get_db())
        try:
            service = AnalyticsService(db)
            return service.get_dashboard_stats(days=days)
        finally:
            db.close()
    except Exception:
        return {
            "summary": {"total_interactions": 0, "unique_users": 0, "successful_actions": 0, "avg_per_user": 0},
            "trends": [],
            "by_agent": {},
            "by_action": {},
            "confirmation_rate": {"acceptance_rate": 0, "accepted": 0, "rejected": 0},
            "top_users": []
        }


def _reload_stats(days: int):
    """Reload page with new time range."""
    ui.navigate.to(f"/admin/analytics?days={days}")


def _render_summary(summary: dict):
    """Render summary cards."""
    with ui.row().classes("w-full gap-4"):
        _stat_card("Total Interactions", summary.get("total_interactions", 0), "chat")
        _stat_card("Unique Users", summary.get("unique_users", 0), "people")
        _stat_card("Successful Actions", summary.get("successful_actions", 0), "check_circle", "green")
        _stat_card("Avg/User", summary.get("avg_per_user", 0), "analytics")


def _stat_card(label: str, value, icon: str, color: str = None):
    """Single stat card."""
    with ui.card().classes("flex-1 p-4"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon(icon, color=color or PTO_GRAY)
            ui.label(label).classes("text-sm text-gray-500")
        color_class = f"text-{color}-600" if color else ""
        ui.label(str(value)).classes(f"text-3xl font-bold {color_class}")


def _render_trend_chart(trends: list):
    """Render line chart."""
    if not trends:
        ui.label("No data yet").classes("text-gray-400 py-8 text-center")
        return

    ui.echart({
        "xAxis": {"type": "category", "data": [t["date"][-5:] for t in trends]},
        "yAxis": {"type": "value"},
        "series": [{
            "data": [t["interactions"] for t in trends],
            "type": "line",
            "smooth": True,
            "areaStyle": {"opacity": 0.3},
            "itemStyle": {"color": PTO_GOLD}
        }],
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 40, "right": 20, "bottom": 30, "top": 20}
    }).classes("w-full h-64")


def _render_agent_pie(by_agent: dict):
    """Render pie chart."""
    if not by_agent:
        ui.label("No data yet").classes("text-gray-400 py-8 text-center")
        return

    ui.echart({
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "data": [{"value": v, "name": k.replace("_", " ").title()} for k, v in by_agent.items()]
        }],
        "tooltip": {"trigger": "item"},
        "legend": {"bottom": 0, "type": "scroll"}
    }).classes("w-full h-48")


def _render_confirmation_gauge(conf: dict):
    """Render gauge chart."""
    rate = conf.get("acceptance_rate", 0)

    ui.echart({
        "series": [{
            "type": "gauge",
            "startAngle": 180,
            "endAngle": 0,
            "min": 0,
            "max": 100,
            "progress": {"show": True, "width": 12},
            "axisLine": {"lineStyle": {"width": 12}},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "pointer": {"show": False},
            "detail": {"formatter": "{value}%", "fontSize": 20, "offsetCenter": [0, 0]},
            "data": [{"value": rate}]
        }]
    }).classes("w-full h-32")

    with ui.row().classes("justify-around text-center"):
        with ui.column():
            ui.label(str(conf.get("accepted", 0))).classes("font-bold text-green-600")
            ui.label("Yes").classes("text-xs")
        with ui.column():
            ui.label(str(conf.get("rejected", 0))).classes("font-bold text-red-600")
            ui.label("No").classes("text-xs")


def _render_actions_bar(by_action: dict):
    """Render horizontal bar chart."""
    if not by_action:
        ui.label("No data yet").classes("text-gray-400 py-8 text-center")
        return

    sorted_actions = sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:6]

    ui.echart({
        "xAxis": {"type": "value"},
        "yAxis": {"type": "category", "data": [a[0] for a in sorted_actions]},
        "series": [{"type": "bar", "data": [a[1] for a in sorted_actions], "itemStyle": {"color": PTO_GOLD}}],
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 100, "right": 20, "bottom": 20, "top": 10}
    }).classes("w-full h-48")


def _render_top_users(users: list):
    """Render top users list."""
    if not users:
        ui.label("No data yet").classes("text-gray-400 py-4 text-center")
        return

    for i, u in enumerate(users[:5], 1):
        with ui.row().classes("w-full items-center justify-between py-1"):
            with ui.row().classes("items-center gap-2"):
                ui.badge(str(i), color="primary")
                ui.label(u.get("username", "Unknown"))
            ui.label(str(u.get("interactions", 0))).classes("text-gray-500")
