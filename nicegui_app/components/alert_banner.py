"""
Alert Banner Component
======================
Displays proactive PTO alerts in dismissible banners.
"""

from nicegui import ui
from typing import List, Optional, Callable
from dataclasses import dataclass


@dataclass
class AlertData:
    """Alert display data."""
    id: str
    urgency: str  # critical, high, medium, low
    title: str
    message: str
    days: float
    days_left: int
    action_url: Optional[str] = None


class AlertBanner:
    """
    Displays year-end and proactive alerts.

    Usage:
        alerts = [AlertData(...), ...]
        banner = AlertBanner(alerts)
        banner.render()
    """

    STYLES = {
        "critical": {"bg": "bg-red-100", "border": "border-red-500", "text": "text-red-800", "icon": "error"},
        "high": {"bg": "bg-orange-100", "border": "border-orange-500", "text": "text-orange-800", "icon": "warning"},
        "medium": {"bg": "bg-yellow-100", "border": "border-yellow-400", "text": "text-yellow-800", "icon": "info"},
        "low": {"bg": "bg-blue-50", "border": "border-blue-400", "text": "text-blue-800", "icon": "tips_and_updates"},
    }

    def __init__(
        self,
        alerts: List[AlertData],
        on_dismiss: Optional[Callable[[str], None]] = None,
        on_action: Optional[Callable[[AlertData], None]] = None,
    ):
        self.alerts = alerts
        self.on_dismiss = on_dismiss
        self.on_action = on_action
        self._dismissed = set()

    def render(self):
        """Render all alert banners."""
        with ui.column().classes("w-full gap-2") as self._container:
            for alert in self.alerts:
                if alert.id not in self._dismissed:
                    self._render_alert(alert)

    def _render_alert(self, alert: AlertData):
        """Render a single alert."""
        style = self.STYLES.get(alert.urgency, self.STYLES["low"])

        with ui.card().classes(f"w-full p-3 {style['bg']} border-l-4 {style['border']}") as card:
            with ui.row().classes("w-full items-start justify-between"):
                # Content
                with ui.row().classes("items-start gap-3 flex-grow"):
                    ui.icon(style["icon"]).classes(f"text-xl {style['text']}")

                    with ui.column().classes("gap-1"):
                        ui.label(alert.title).classes(f"font-semibold {style['text']}")
                        ui.markdown(alert.message).classes(f"text-sm {style['text']}")

                        with ui.row().classes("gap-2 mt-2"):
                            if alert.action_url:
                                ui.button(
                                    "Take Action",
                                    icon="event",
                                    on_click=lambda e, a=alert: self._handle_action(a)
                                ).props("size=sm")

                            ui.button(
                                "Dismiss",
                                on_click=lambda e, a=alert, c=card: self._handle_dismiss(a, c)
                            ).props("size=sm flat")

                # Badge
                with ui.column().classes("items-end"):
                    color = "red" if alert.urgency == "critical" else "orange"
                    ui.badge(f"{alert.days} days", color=color)
                    ui.label(f"{alert.days_left} days left").classes("text-xs text-gray-500")

    def _handle_dismiss(self, alert: AlertData, card):
        """Dismiss an alert."""
        self._dismissed.add(alert.id)
        card.delete()
        if self.on_dismiss:
            self.on_dismiss(alert.id)

    def _handle_action(self, alert: AlertData):
        """Handle action click."""
        if self.on_action:
            self.on_action(alert)
        elif alert.action_url:
            ui.navigate.to(alert.action_url)


def render_alerts_for_user(user_id: int):
    """
    Convenience function to render alerts for a user.

    Usage in any page:
        render_alerts_for_user(current_user.id)
    """
    try:
        from src.database import get_db
        from src.services.alert_service import AlertService

        db = next(get_db())
        try:
            service = AlertService(db)
            alerts = service.get_alerts_for_user(user_id)

            if alerts:
                alert_data = [
                    AlertData(
                        id=f"{a.alert_type.value}_{user_id}",
                        urgency=a.urgency.value,
                        title=a.title,
                        message=a.message,
                        days=a.days_affected,
                        days_left=a.days_until_expiry,
                        action_url=a.action_url
                    )
                    for a in alerts
                ]
                banner = AlertBanner(alert_data)
                banner.render()
        finally:
            db.close()
    except Exception:
        # Silently fail - alerts are non-critical
        pass
