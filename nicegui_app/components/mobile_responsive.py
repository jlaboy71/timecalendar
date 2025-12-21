"""
Mobile responsive CSS utilities for PTO Central.
Provides comprehensive mobile-first responsive styling for NiceGUI/Quasar applications.

BACKUP/REVERT INSTRUCTIONS:
If this causes issues, revert by:
1. Remove the import in theme.py: from nicegui_app.components.mobile_responsive import inject_mobile_css
2. Remove the call in theme.py: inject_mobile_css()
3. Remove exports from __init__.py
4. Optionally delete this file
"""
from nicegui import ui


def inject_mobile_css():
    """
    Inject comprehensive mobile-responsive CSS into the page.
    Call this function in apply_dark_mode() to ensure it loads on every page.

    This uses CSS media queries to progressively enhance the layout:
    - Mobile first (< 640px): Single column, stacked layouts
    - Tablet (640px - 1024px): 2-column grids
    - Desktop (> 1024px): Full multi-column layouts (UNCHANGED)
    """
    ui.add_head_html('''
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        /* ============================================
           PTO CENTRAL - MOBILE RESPONSIVE CSS
           ============================================ */

        /* ===== VIEWPORT FIX ===== */
        @viewport {
            width: device-width;
        }

        /* ===== MOBILE BASE RULES (< 640px) ===== */
        @media (max-width: 640px) {
            /* Container width fixes - prevent horizontal overflow */
            .max-w-5xl, .max-w-6xl, .max-w-4xl, .max-w-3xl {
                max-width: 100% !important;
                padding-left: 12px !important;
                padding-right: 12px !important;
            }

            /* Force rows to wrap on mobile */
            .q-row, [class*="flex"], .flex {
                flex-wrap: wrap !important;
            }

            /* Reduce gaps on mobile */
            .gap-6 { gap: 0.75rem !important; }
            .gap-4 { gap: 0.5rem !important; }
            .gap-3 { gap: 0.375rem !important; }

            /* Full-width cards on mobile */
            .q-card {
                width: 100% !important;
                min-width: 0 !important;
                max-width: 100% !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
            }

            /* Responsive text sizing */
            .text-3xl { font-size: 1.5rem !important; line-height: 2rem !important; }
            .text-2xl { font-size: 1.25rem !important; line-height: 1.75rem !important; }
            .text-xl { font-size: 1.125rem !important; line-height: 1.5rem !important; }
            .text-lg { font-size: 1rem !important; line-height: 1.5rem !important; }

            /* Reduce padding on mobile */
            .p-6 { padding: 1rem !important; }
            .p-4 { padding: 0.75rem !important; }
            .px-6 { padding-left: 1rem !important; padding-right: 1rem !important; }
            .py-6 { padding-top: 1rem !important; padding-bottom: 1rem !important; }

            /* Page header adjustments */
            .page-header-title {
                font-size: 1.25rem !important;
            }

            /* Main content area */
            .nicegui-content, .q-page {
                padding: 8px !important;
            }
        }

        /* ===== RESPONSIVE CSS GRID OVERRIDES ===== */
        /* These override inline style grids that use repeat() */

        @media (max-width: 640px) {
            /* 4-column grids become 2 columns */
            [style*="grid-template-columns: repeat(4"] {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 8px !important;
            }

            /* 6-column grids become 2 columns */
            [style*="grid-template-columns: repeat(6"] {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 8px !important;
            }

            /* 3-column grids become 1 column */
            [style*="grid-template-columns: repeat(3"] {
                grid-template-columns: 1fr !important;
                gap: 8px !important;
            }

            /* 5-column grids become 2 columns */
            [style*="grid-template-columns: repeat(5"] {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 8px !important;
            }
        }

        @media (max-width: 400px) {
            /* Very small phones: everything single column */
            [style*="grid-template-columns: repeat(4"],
            [style*="grid-template-columns: repeat(6"],
            [style*="grid-template-columns: repeat(3"],
            [style*="grid-template-columns: repeat(2"] {
                grid-template-columns: 1fr !important;
            }
        }

        /* ===== TABLET RULES (641px - 1024px) ===== */
        @media (min-width: 641px) and (max-width: 1024px) {
            .max-w-5xl, .max-w-6xl {
                max-width: 95% !important;
                padding-left: 16px !important;
                padding-right: 16px !important;
            }

            /* 6-column grids become 3 columns on tablet */
            [style*="grid-template-columns: repeat(6"] {
                grid-template-columns: repeat(3, 1fr) !important;
            }

            /* 4-column grids stay 4 on tablet */
            [style*="grid-template-columns: repeat(4"] {
                grid-template-columns: repeat(4, 1fr) !important;
            }
        }

        /* ===== CALENDAR YEAR VIEW ===== */
        @media (max-width: 768px) {
            /* Year view: 3 columns on tablet */
            .calendar-year-grid {
                grid-template-columns: repeat(3, 1fr) !important;
            }

            /* Mini calendar cells smaller */
            .mini-calendar-table {
                font-size: 0.55rem !important;
            }
            .mini-calendar-table td,
            .mini-calendar-table th {
                padding: 1px !important;
                width: 12px !important;
                height: 12px !important;
            }
        }

        @media (max-width: 480px) {
            /* Year view: 2 columns on phone */
            .calendar-year-grid {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            /* Even smaller mini calendars */
            .mini-calendar-table {
                font-size: 0.5rem !important;
            }
            .mini-calendar-table td,
            .mini-calendar-table th {
                padding: 0 !important;
                width: 10px !important;
                height: 10px !important;
            }
        }

        /* ===== DASHBOARD SPECIFIC ===== */
        @media (max-width: 640px) {
            /* Balance cards stack vertically */
            .balance-card-grid {
                grid-template-columns: 1fr !important;
            }

            /* Dashboard action buttons full width */
            .dashboard-actions .q-btn,
            .flex-1.min-w-fit {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                width: 100% !important;
            }

            /* Quick actions wrap properly */
            .quick-actions-row {
                flex-direction: column !important;
            }
            .quick-actions-row .q-btn {
                width: 100% !important;
            }
        }

        /* ===== TABLE RESPONSIVE ===== */
        @media (max-width: 640px) {
            .q-table {
                font-size: 0.7rem !important;
            }
            .q-table__container {
                overflow-x: auto !important;
            }
            .q-table thead th {
                padding: 6px 4px !important;
                font-size: 0.65rem !important;
                white-space: nowrap !important;
            }
            .q-table tbody td {
                padding: 4px 4px !important;
            }

            /* Hide columns marked for mobile hiding */
            .q-table .hide-mobile,
            .q-table [data-hide-mobile="true"] {
                display: none !important;
            }
        }

        /* ===== DIALOG/MODAL RESPONSIVE ===== */
        @media (max-width: 640px) {
            .q-dialog__inner {
                padding: 8px !important;
            }
            .q-dialog .q-card {
                max-width: calc(100vw - 16px) !important;
                max-height: calc(100vh - 32px) !important;
                margin: 8px !important;
                width: calc(100vw - 16px) !important;
            }
            .q-dialog .q-card-section {
                padding: 12px !important;
            }

            /* Dialog titles */
            .q-dialog .text-lg,
            .q-dialog .text-xl {
                font-size: 1rem !important;
            }
        }

        /* ===== BUTTON RESPONSIVE ===== */
        @media (max-width: 640px) {
            /* Buttons in rows stack */
            .button-row, .btn-row {
                flex-direction: column !important;
                gap: 8px !important;
            }
            .button-row .q-btn,
            .btn-row .q-btn {
                width: 100% !important;
            }

            /* Reduce button padding */
            .q-btn {
                padding: 8px 12px !important;
            }
            .q-btn--dense {
                padding: 4px 8px !important;
            }

            /* Icon-only buttons keep their size */
            .q-btn--round {
                padding: 8px !important;
            }
        }

        /* ===== ANALYTICS PAGE ===== */
        @media (max-width: 768px) {
            /* KPI cards: 2 columns on tablet */
            .kpi-grid, .grid-cols-4 {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            /* Chart containers */
            .chart-container {
                min-height: 200px !important;
                height: auto !important;
            }
        }

        @media (max-width: 480px) {
            /* KPI cards: 1 column on small phones */
            .kpi-grid {
                grid-template-columns: 1fr !important;
            }
        }

        /* ===== FORM INPUTS ===== */
        @media (max-width: 640px) {
            .q-field {
                width: 100% !important;
                min-width: 0 !important;
            }
            .q-select, .q-input {
                min-width: 0 !important;
                width: 100% !important;
            }
            .q-field__control {
                min-height: 44px !important;
            }

            /* Form rows stack */
            .form-row {
                flex-direction: column !important;
            }
            .form-row > * {
                width: 100% !important;
            }

            /* Min width overrides */
            .min-w-\\[140px\\], .min-w-\\[200px\\], .min-w-\\[180px\\] {
                min-width: 100% !important;
            }
        }

        /* ===== HEADER COMPONENT ===== */
        @media (max-width: 640px) {
            .header-nav-buttons {
                flex-wrap: wrap !important;
                gap: 4px !important;
            }
            .header-nav-buttons .q-btn {
                font-size: 0.7rem !important;
                padding: 4px 8px !important;
            }

            /* Logo smaller on mobile */
            .header-logo {
                height: 32px !important;
            }

            /* User info condensed */
            .header-user-info {
                font-size: 0.75rem !important;
            }
        }

        /* ===== EXPANSION PANELS ===== */
        @media (max-width: 640px) {
            .q-expansion-item {
                padding: 0 !important;
            }
            .q-expansion-item__container {
                padding: 8px !important;
            }
        }

        /* ===== iOS SPECIFIC FIXES ===== */
        @supports (-webkit-touch-callout: none) {
            /* Prevent iOS auto-zoom on input focus (requires 16px min) */
            input, select, textarea, .q-field__native {
                font-size: 16px !important;
            }

            /* iOS safe area padding for notched devices */
            .q-page, .q-layout__page {
                padding-bottom: env(safe-area-inset-bottom, 0) !important;
                padding-left: env(safe-area-inset-left, 0) !important;
                padding-right: env(safe-area-inset-right, 0) !important;
            }

            /* Fix iOS momentum scrolling */
            .q-scrollarea, .scroll-area {
                -webkit-overflow-scrolling: touch !important;
            }

            /* Fix position:fixed on iOS */
            .q-dialog__inner--minimized {
                position: fixed !important;
            }
        }

        /* ===== TOUCH DEVICE IMPROVEMENTS ===== */
        @media (hover: none) and (pointer: coarse) {
            /* Larger touch targets (Apple HIG: 44px minimum) */
            .q-btn {
                min-height: 44px !important;
            }
            .q-btn--dense {
                min-height: 36px !important;
            }

            /* Clickable rows need padding */
            .clickable-row, [onclick], [data-clickable] {
                min-height: 44px !important;
                padding: 8px !important;
            }

            /* Remove hover effects that don't work on touch */
            .hover\\:shadow-lg:hover {
                box-shadow: none !important;
            }

            /* Active state for touch feedback */
            .q-btn:active {
                transform: scale(0.97) !important;
            }
            .q-card:active {
                transform: scale(0.99) !important;
            }
        }

        /* ===== SCROLL BEHAVIOR ===== */
        @media (max-width: 640px) {
            /* Smooth scrolling on mobile */
            html {
                scroll-behavior: smooth;
            }

            /* Horizontal scroll areas */
            .scroll-x-mobile {
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
            }

            /* Hide scrollbars on mobile but keep functionality */
            .hide-scrollbar::-webkit-scrollbar {
                display: none !important;
            }
            .hide-scrollbar {
                -ms-overflow-style: none !important;
                scrollbar-width: none !important;
            }
        }

        /* ===== UTILITY CLASSES FOR MOBILE ===== */
        @media (max-width: 640px) {
            .mobile-hidden { display: none !important; }
            .mobile-full-width { width: 100% !important; }
            .mobile-stack { flex-direction: column !important; }
            .mobile-center { justify-content: center !important; align-items: center !important; }
            .mobile-text-sm { font-size: 0.875rem !important; }
            .mobile-text-xs { font-size: 0.75rem !important; }
            .mobile-p-2 { padding: 0.5rem !important; }
            .mobile-p-3 { padding: 0.75rem !important; }
            .mobile-gap-2 { gap: 0.5rem !important; }
        }

        @media (min-width: 641px) {
            .desktop-hidden { display: none !important; }
        }

        /* ===== PRINT STYLES (keep existing) ===== */
        @media print {
            /* Mobile styles should not affect print */
            .mobile-hidden { display: block !important; }
        }
    </style>
    ''')


def get_responsive_grid_classes(cols_mobile: int = 1, cols_tablet: int = 2, cols_desktop: int = 4) -> str:
    """
    Return Tailwind responsive grid classes.

    Args:
        cols_mobile: Number of columns on mobile (< 640px)
        cols_tablet: Number of columns on tablet (640px - 1024px)
        cols_desktop: Number of columns on desktop (> 1024px)

    Returns:
        String of Tailwind classes for responsive grid

    Usage:
        with ui.element('div').classes(get_responsive_grid_classes(1, 2, 4)):
            # grid items
    """
    return f'grid grid-cols-{cols_mobile} sm:grid-cols-{cols_tablet} lg:grid-cols-{cols_desktop} gap-4 w-full'


def get_responsive_container_classes() -> str:
    """
    Return standard responsive container classes.

    Returns:
        String of Tailwind classes for responsive container

    Usage:
        with ui.column().classes(get_responsive_container_classes()):
            # page content
    """
    return 'w-full max-w-6xl mx-auto px-3 sm:px-4 lg:px-6'
