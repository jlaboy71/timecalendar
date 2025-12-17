"""Formatting utilities for consistent display across the app."""


def fmt_days(value: float) -> str:
    """Format days value in compact 'Xd' or 'Xd Yh' format.

    Examples:
        fmt_days(2.0) -> "2d"
        fmt_days(2.5) -> "2d 4h"
        fmt_days(1.0) -> "1d"
    """
    # Value is in days, convert to hours for calculation
    hours = value * 8
    whole_days = int(hours // 8)
    remaining_hours = int(hours % 8)
    if remaining_hours > 0:
        return f"{whole_days}d {remaining_hours}h"
    return f"{whole_days}d"


def format_days_hours(hours: float) -> tuple[str, str]:
    """Convert hours to compact 'Xd Yh' format with tooltip.

    Returns a tuple of (display_text, tooltip_text).

    Examples:
        22.4 hours → ("2d 6h", "2.8 days (22 hours)")
        24 hours → ("3d", "3.0 days (24 hours)")
        4 hours → ("0d 4h", "0.5 days (4 hours)")
        8 hours → ("1d", "1.0 days (8 hours)")
        0 hours → ("0d", "0.0 days (0 hours)")
    """
    if hours == 0:
        return ("0d", "0.0 days (0 hours)")

    # Handle negative (overdrawn) balances
    is_negative = hours < 0
    abs_hours = abs(hours)

    whole_days = int(abs_hours // 8)
    remaining_hours = int(abs_hours % 8)

    # Build compact display
    if remaining_hours > 0:
        display_text = f"{whole_days}d {remaining_hours}h"
    else:
        display_text = f"{whole_days}d"

    if is_negative:
        display_text = f"-{display_text}"

    # Tooltip shows actual decimal values
    actual_days = hours / 8
    tooltip_text = f"{actual_days:.1f} days ({hours:.0f} hours)"

    return (display_text, tooltip_text)
