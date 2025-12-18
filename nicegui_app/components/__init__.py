"""Shared UI components for the NiceGUI app."""
from .header import page_header, get_time_based_greeting
from .theme import (
    apply_dark_mode, skeleton_loader, skeleton_table, skeleton_card,
    FormValidator, validate_required, validate_email, validate_min_length
)
from .mobile_responsive import (
    inject_mobile_css,
    get_responsive_grid_classes,
    get_responsive_container_classes
)
