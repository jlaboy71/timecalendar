"""Formatting utilities for consistent display across the app."""


def fmt_days(value: float) -> str:
    """Format days value, removing unnecessary decimal for whole numbers.

    Examples:
        fmt_days(2.0) -> "2"
        fmt_days(2.5) -> "2.5"
        fmt_days(1.0) -> "1"
    """
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def format_days_hours(hours: float) -> tuple[str, str]:
    """Convert hours to 'X Days, Y Hours' format with tooltip.

    Returns a tuple of (display_text, tooltip_text).

    Examples:
        22.4 hours → ("2 Days, 6 Hours", "2.8 days (22.4 hours)")
        24 hours → ("3 Days", "3 days (24 hours)")
        4 hours → ("4 Hours", "0.5 days (4 hours)")
        8 hours → ("1 Day", "1 day (8 hours)")
        0 hours → ("0 Hours", "0 days (0 hours)")
    """
    if hours == 0:
        return ("0 Hours", "0 days (0 hours)")

    # Handle negative (overdrawn) balances
    is_negative = hours < 0
    abs_hours = abs(hours)

    total_days = abs_hours / 8
    whole_days = int(total_days)
    remaining_hours = round((total_days - whole_days) * 8)

    # Handle case where rounding gives us 8 hours (should be +1 day)
    if remaining_hours == 8:
        whole_days += 1
        remaining_hours = 0

    parts = []
    if whole_days > 0:
        day_word = "Day" if whole_days == 1 else "Days"
        parts.append(f"{whole_days} {day_word}")
    if remaining_hours > 0:
        hour_word = "Hour" if remaining_hours == 1 else "Hours"
        parts.append(f"{remaining_hours} {hour_word}")

    if not parts:
        parts.append("0 Hours")

    display_text = ", ".join(parts)
    if is_negative:
        display_text = f"-{display_text}"

    # Tooltip shows actual decimal values
    actual_days = hours / 8
    day_word_tooltip = "day" if abs(actual_days) == 1 else "days"
    tooltip_text = f"{actual_days:.1f} {day_word_tooltip} ({hours:.0f} hours)"

    return (display_text, tooltip_text)
