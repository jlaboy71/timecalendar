"""
Input validation helpers for the PTO and Market Calendar System.

These validators provide consistent validation logic that can be used
across services and UI components.
"""
from datetime import date
from decimal import Decimal
from typing import Tuple


def validate_date_range(start_date: date, end_date: date) -> Tuple[bool, str]:
    """
    Validate that end_date is not before start_date.

    Args:
        start_date: Start date of the range
        end_date: End date of the range

    Returns:
        Tuple of (is_valid, error_message)
    """
    if end_date < start_date:
        return False, "End date cannot be before start date"
    return True, ""


def validate_date_not_past(check_date: date) -> Tuple[bool, str]:
    """
    Validate that a date is not in the past.

    Args:
        check_date: Date to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if check_date < date.today():
        return False, "Date cannot be in the past"
    return True, ""


def validate_pto_days(days: Decimal | float) -> Tuple[bool, str]:
    """
    Validate PTO days value is reasonable.

    Args:
        days: Number of days requested

    Returns:
        Tuple of (is_valid, error_message)
    """
    if days <= 0:
        return False, "Days must be greater than zero"
    if days > 365:
        return False, "Days cannot exceed 365"
    return True, ""


def validate_pto_type(pto_type: str) -> Tuple[bool, str]:
    """
    Validate PTO type is an allowed value.

    Args:
        pto_type: Type of PTO request

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_types = [
        'vacation', 'sick', 'personal', 'bereavement',
        'fmla', 'jury_duty', 'voting', 'military'
    ]
    if pto_type.lower() not in valid_types:
        return False, f"Invalid PTO type. Must be one of: {', '.join(valid_types)}"
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Basic email format validation.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not email.strip():
        return False, "Email is required"
    if '@' not in email or '.' not in email:
        return False, "Invalid email format"
    if len(email) > 254:
        return False, "Email address too long"
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username or not username.strip():
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 50:
        return False, "Username cannot exceed 50 characters"
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, ""


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password meets minimum strength requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters"
    return True, ""
