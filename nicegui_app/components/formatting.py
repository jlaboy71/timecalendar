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
