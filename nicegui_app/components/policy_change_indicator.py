"""
Policy Change Indicator Components.

Provides reusable UI components for displaying policy change badges,
tooltips, and the "What's New" dashboard section.
"""
from typing import Optional, List, Dict, Any
from nicegui import ui
from src.models.policy_change_log import PolicyChangeLog
from src.models.user import User
from src.services.policy_change_service import PolicyChangeService


# PTO Central Brand Colors
PTO_GOLD = '#c9a227'


def policy_change_badge(change: PolicyChangeLog) -> None:
    """
    Display [UPDATED] or [REVERTED] badge next to a policy value.

    Args:
        change: The PolicyChangeLog entry to display badge for
    """
    if change.is_revert:
        badge_text = "REVERTED"
        badge_color = "orange"
    else:
        badge_text = "UPDATED"
        badge_color = "green"

    ui.badge(badge_text, color=badge_color).classes('ml-2 text-xs font-semibold')


def policy_change_tooltip(change: PolicyChangeLog) -> str:
    """
    Generate tooltip content for a changed policy value.

    Args:
        change: The PolicyChangeLog entry

    Returns:
        Formatted tooltip text
    """
    lines = [
        f"Changed: {change.old_value_display} → {change.new_value_display}",
        f"Effective: {change.effective_date.strftime('%b %d, %Y')}"
    ]

    if change.reason:
        lines.append(f"Reason: {change.reason}")

    if change.ai_summary:
        lines.append(f"Summary: {change.ai_summary}")

    return "\n".join(lines)


def policy_value_with_change(
    label: str,
    value: str,
    policy_type: str,
    user: User,
    policy_change_service: PolicyChangeService,
    label_classes: str = 'text-sm opacity-70',
    value_classes: str = 'font-semibold text-lg'
) -> Optional[PolicyChangeLog]:
    """
    Display a policy value with change indicator if recently changed.

    Use this component wherever policy values are displayed to automatically
    show change badges and tooltips when values have been updated in the
    last 30 days.

    Args:
        label: The label text (e.g., "Policy Maximum")
        value: The value to display (e.g., "80 hrs")
        policy_type: The policy type code (e.g., "sick_carryover_max")
        user: The current user (for location-based policy resolution)
        policy_change_service: Service instance for querying changes
        label_classes: CSS classes for the label
        value_classes: CSS classes for the value

    Returns:
        The PolicyChangeLog if a change was found, None otherwise
    """
    change = policy_change_service.get_change_for_field(policy_type, user)

    # Label row with optional badge
    with ui.row().classes('items-center gap-2'):
        ui.label(label).classes(label_classes)
        if change:
            policy_change_badge(change)

    # Value with optional tooltip
    value_label = ui.label(value).classes(value_classes)
    if change:
        value_label.tooltip(policy_change_tooltip(change))

    return change


def whats_new_section(
    user: User,
    policy_change_service: PolicyChangeService,
    limit: int = 5
) -> bool:
    """
    Display recent policy changes relevant to this user on dashboard.

    Args:
        user: The current user
        policy_change_service: Service instance for querying changes
        limit: Maximum number of changes to show

    Returns:
        True if changes were displayed, False if no recent changes
    """
    changes = policy_change_service.get_whats_new(user, limit=limit)

    if not changes:
        return False

    with ui.card().classes('w-full mb-6').style('border-left: 4px solid #22c55e;'):
        with ui.card_section().classes('p-4'):
            # Header
            with ui.row().classes('items-center gap-2 mb-4'):
                ui.icon('new_releases', size='1.5rem', color='green')
                ui.label("What's New").classes('text-lg font-bold')
                ui.badge(f'{len(changes)} updates', color='green').classes('ml-2')

            # Change list
            for i, change in enumerate(changes):
                # Add divider between items (not after last)
                border_class = 'border-b border-gray-700' if i < len(changes) - 1 else ''

                with ui.row().classes(f'items-start gap-3 py-2 {border_class}'):
                    # Icon based on revert status
                    icon = 'undo' if change['is_revert'] else 'update'
                    icon_color = 'orange' if change['is_revert'] else 'green'
                    ui.icon(icon, size='sm', color=icon_color)

                    with ui.column().classes('gap-1 flex-1'):
                        # Summary or fallback text
                        summary_text = change['ai_summary']
                        if not summary_text:
                            policy_name = policy_change_service.format_policy_type_name(change['policy_type'])
                            summary_text = f"{policy_name} changed from {change['old_value_display']} to {change['new_value_display']}"

                        ui.label(summary_text).classes('text-sm')

                        # Metadata row
                        with ui.row().classes('gap-2 items-center'):
                            ui.label(
                                f"Effective {change['effective_date'].strftime('%b %d, %Y')}"
                            ).classes('text-xs opacity-60')

                            # Days remaining indicator
                            days_left = change['days_remaining']
                            if days_left <= 7:
                                ui.label(f'{days_left}d left').classes('text-xs text-orange-400')

    return True


def whats_new_badge(
    user: User,
    policy_change_service: PolicyChangeService
) -> Optional[int]:
    """
    Display a badge with count of recent policy changes.

    Use this on navigation items to indicate new changes.

    Args:
        user: The current user
        policy_change_service: Service instance

    Returns:
        Count of changes if any, None otherwise
    """
    count = policy_change_service.get_change_count_for_user(user)

    if count > 0:
        ui.badge(str(count), color='green').classes('ml-1')
        return count

    return None


def policy_change_details_dialog(change: PolicyChangeLog) -> None:
    """
    Show a dialog with full details of a policy change.

    Args:
        change: The PolicyChangeLog to display
    """
    with ui.dialog() as dialog, ui.card().classes('w-96'):
        with ui.card_section():
            # Header
            with ui.row().classes('items-center gap-2 mb-4'):
                icon = 'undo' if change.is_revert else 'update'
                icon_color = 'orange' if change.is_revert else 'green'
                ui.icon(icon, size='md', color=icon_color)
                ui.label('Policy Change Details').classes('text-lg font-bold')

            # Change summary
            with ui.column().classes('gap-3'):
                # Old vs New
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('items-center'):
                        ui.label('Previous').classes('text-xs opacity-60')
                        ui.label(change.old_value_display).classes('text-lg line-through opacity-70')

                    ui.icon('arrow_forward', color='gray')

                    with ui.column().classes('items-center'):
                        ui.label('New').classes('text-xs opacity-60')
                        ui.label(change.new_value_display).classes('text-lg font-bold text-green-500')

                # Effective date
                ui.label(
                    f"Effective: {change.effective_date.strftime('%B %d, %Y')}"
                ).classes('text-sm')

                # Reason
                if change.reason:
                    with ui.column().classes('gap-1'):
                        ui.label('Reason').classes('text-xs opacity-60 font-semibold')
                        ui.label(change.reason).classes('text-sm')

                # AI Summary
                if change.ai_summary:
                    with ui.column().classes('gap-1 p-3 bg-green-900/20 rounded'):
                        ui.label(change.ai_summary).classes('text-sm')

                # Revert info
                if change.is_revert and change.reverted_to_version:
                    ui.label(
                        f"Reverted to version {change.reverted_to_version}"
                    ).classes('text-xs text-orange-400')

        with ui.card_actions().classes('justify-end'):
            ui.button('Close', on_click=dialog.close).props('flat')

    dialog.open()


def inline_change_indicator(
    value: str,
    change: Optional[PolicyChangeLog],
    value_classes: str = 'font-medium'
) -> None:
    """
    Simple inline display of value with optional change indicator.

    Use when you already have the change object and just need the display.

    Args:
        value: The value to display
        change: Optional PolicyChangeLog (None = no indicator)
        value_classes: CSS classes for the value
    """
    with ui.row().classes('items-center gap-2'):
        label_el = ui.label(value).classes(value_classes)

        if change:
            policy_change_badge(change)
            label_el.tooltip(policy_change_tooltip(change))
