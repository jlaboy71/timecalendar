"""Formatting utilities for consistent display across the app."""


def fmt_days(value: float) -> str:
    """Format days value in readable format.

    Examples:
        fmt_days(2.0) -> "2 days"
        fmt_days(2.5) -> "2 days and 4 hours"
        fmt_days(1.0) -> "1 day"
        fmt_days(0.5) -> "4 hours"
    """
    # Value is in days, convert to hours for calculation
    hours = value * 8
    whole_days = int(hours // 8)
    remaining_hours = int(hours % 8)

    day_str = "day" if whole_days == 1 else "days"
    hour_str = "hour" if remaining_hours == 1 else "hours"

    if whole_days > 0 and remaining_hours > 0:
        return f"{whole_days} {day_str} and {remaining_hours} {hour_str}"
    elif whole_days > 0:
        return f"{whole_days} {day_str}"
    elif remaining_hours > 0:
        return f"{remaining_hours} {hour_str}"
    return "0 days"


def format_days_hours(hours: float) -> tuple[str, str]:
    """Convert hours to readable format with tooltip.

    Returns a tuple of (display_text, tooltip_text).

    Examples:
        22.4 hours → ("2 days and 6 hours", "2.8 days (22 hours)")
        24 hours → ("3 days", "3.0 days (24 hours)")
        4 hours → ("4 hours", "0.5 days (4 hours)")
        8 hours → ("1 day", "1.0 days (8 hours)")
        0 hours → ("0 days", "0.0 days (0 hours)")
    """
    if hours == 0:
        return ("0 days", "0.0 days (0 hours)")

    # Handle negative (overdrawn) balances
    is_negative = hours < 0
    abs_hours = abs(hours)

    whole_days = int(abs_hours // 8)
    remaining_hours = int(abs_hours % 8)

    day_str = "day" if whole_days == 1 else "days"
    hour_str = "hour" if remaining_hours == 1 else "hours"

    # Build readable display
    if whole_days > 0 and remaining_hours > 0:
        display_text = f"{whole_days} {day_str} and {remaining_hours} {hour_str}"
    elif whole_days > 0:
        display_text = f"{whole_days} {day_str}"
    elif remaining_hours > 0:
        display_text = f"{remaining_hours} {hour_str}"
    else:
        display_text = "0 days"

    if is_negative:
        display_text = f"-{display_text}"

    # Tooltip shows actual decimal values
    actual_days = hours / 8
    tooltip_text = f"{actual_days:.1f} days ({hours:.0f} hours)"

    return (display_text, tooltip_text)
