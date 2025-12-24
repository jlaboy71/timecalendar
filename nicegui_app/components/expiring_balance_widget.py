"""
Expiring Balance Widget
=======================
Dashboard widget showing expiring PTO at a glance.
"""

from nicegui import ui
from typing import Dict, Any


class ExpiringBalanceWidget:
    """
    Compact dashboard widget for expiring balances.

    Usage:
        widget = ExpiringBalanceWidget(user_id)
        widget.render()
    """

    URGENCY_COLORS = {
        "critical": {"color": "red", "pulse": True},
        "high": {"color": "orange", "pulse": True},
        "medium": {"color": "amber", "pulse": False},
        "low": {"color": "blue", "pulse": False},
        "none": {"color": "green", "pulse": False},
    }

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.summary = self._load_summary()

    def _load_summary(self) -> Dict[str, Any]:
        """Load expiring balance summary."""
        try:
            from src.database import get_db
            from src.services.alert_service import AlertService

            db = next(get_db())
            try:
                service = AlertService(db)
                return service.get_expiring_summary(self.user_id)
            finally:
                db.close()
        except Exception:
            return {"total_expiring": 0, "urgency": "none", "by_type": {}}

    def render(self):
        """Render the widget."""
        total = self.summary.get("total_expiring", 0)
        urgency = self.summary.get("urgency", "none")
        days_left = self.summary.get("days_until_expiry", 0)
        by_type = self.summary.get("by_type", {})

        style = self.URGENCY_COLORS.get(urgency, self.URGENCY_COLORS["none"])

        with ui.card().classes("w-full cursor-pointer hover:shadow-lg").on(
            "click", lambda: ui.navigate.to("/ai-assistant")
        ):
            # Header
            with ui.row().classes("items-center justify-between mb-2"):
                with ui.row().classes("items-center gap-2"):
                    icon_class = "animate-pulse" if style["pulse"] else ""
                    ui.icon("event_busy", color=style["color"]).classes(icon_class)
                    ui.label("Expiring PTO").classes("font-semibold")

                if total > 0:
                    ui.badge(f"{days_left}d left", color=style["color"])

            if total > 0:
                # Main stat
                with ui.row().classes("items-end gap-1 mb-2"):
                    ui.label(f"{total}").classes("text-3xl font-bold")
                    ui.label("days at risk").classes("text-gray-500")

                # Breakdown
                for leave_type, days in by_type.items():
                    if days > 0:
                        with ui.row().classes("justify-between text-sm"):
                            ui.label(leave_type.replace("_", " ").title())
                            ui.label(f"{days}d")

                # Hint
                ui.label("Click to get help").classes("text-xs text-blue-500 mt-2")
            else:
                # All good
                with ui.column().classes("items-center py-2"):
                    ui.icon("check_circle", color="green", size="lg")
                    ui.label("No expiring PTO!").classes("text-green-600")


def render_expiring_widget(user_id: int):
    """Quick render function."""
    widget = ExpiringBalanceWidget(user_id)
    widget.render()
