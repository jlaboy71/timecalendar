"""WFH Day Swap page - peer-to-peer WFH day exchange between employees."""
import logging
from nicegui import ui, app
from datetime import date, timedelta

logger = logging.getLogger(__name__)
from sqlalchemy import select, or_, and_
from src.database import get_db
from src.services.wfh_swap_service import WFHSwapService
from src.models.wfh_day_swap import WFHDaySwapRequest
from src.models.market_holiday import MarketHoliday
from src.services.user_service import UserService
from src.services.audit_service import AuditService
from src.services.email_service import email_service
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_error_dialog, show_success_dialog, show_warning_dialog, show_info_dialog

# Brand color
PTO_GOLD = '#C9A227'

# Day configuration with colors matching dashboard theme
WEEKDAYS = [
    {'key': 'monday', 'label': 'MONDAY', 'color': 'blue-500', 'hex': '#3b82f6'},
    {'key': 'tuesday', 'label': 'TUESDAY', 'color': 'green-500', 'hex': '#22c55e'},
    {'key': 'wednesday', 'label': 'WEDNESDAY', 'color': 'purple-500', 'hex': '#a855f7'},
    {'key': 'thursday', 'label': 'THURSDAY', 'color': 'amber-500', 'hex': '#f59e0b'},
    {'key': 'friday', 'label': 'FRIDAY', 'color': 'red-500', 'hex': '#ef4444'},
]

# Status colors and icons
STATUS_STYLES = {
    'pending': {'color': 'amber', 'icon': 'hourglass_empty', 'text': 'Pending'},
    'accepted': {'color': 'green', 'icon': 'check_circle', 'text': 'Accepted'},
    'declined': {'color': 'red', 'icon': 'cancel', 'text': 'Declined'},
    'cancelled': {'color': 'grey', 'icon': 'block', 'text': 'Cancelled'},
    'expired': {'color': 'grey', 'icon': 'schedule', 'text': 'Expired'},
}

# Swap pair colors - distinct colors for different swap pairs
SWAP_PAIR_COLORS = [
    '#f59e0b',  # Amber
    '#22c55e',  # Green
    '#3b82f6',  # Blue
    '#a855f7',  # Purple
    '#ef4444',  # Red
    '#06b6d4',  # Cyan
    '#ec4899',  # Pink
    '#84cc16',  # Lime
]


def wfh_swap_page():
    """WFH Day Swap page - request and respond to WFH day swaps."""

    apply_dark_mode()

    # Add custom styles
    ui.add_head_html('''
    <style>
        @keyframes fade-in-up {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .days-row {
            display: flex !important;
            align-items: stretch !important;
        }
        .day-column {
            transition: all 0.2s ease;
            min-height: 180px;
            display: flex;
            flex-direction: column;
        }
        .day-column:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        }
        .day-column.my-day {
            box-shadow: 0 0 0 2px #C9A227 !important;
        }
        .employee-item {
            transition: all 0.15s ease;
            cursor: pointer;
            padding: 6px 8px;
            border-radius: 4px;
            margin: 1px 0;
        }
        .employee-item:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            padding-left: 12px;
        }
        .swap-dialog {
            animation: fade-in-up 0.2s ease-out;
        }
    </style>
    ''')

    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    db = next(get_db())
    try:
        swap_service = WFHSwapService(db)
        user_service = UserService(db)

        current_user = user_service.get_user_by_id(user['id'])
        if not current_user:
            ui.navigate.to('/')
            return

        # Get user's WFH day
        user_wfh_day = swap_service._get_wfh_day(current_user)

        # Week selection state - 0 = this week, 1 = next week
        selected_week = {'value': 0}

        def get_week_dates(week_offset: int = 0) -> dict:
            """
            Get the date for each weekday of the selected week.

            Args:
                week_offset: 0 for current week, 1 for next week

            Returns:
                dict mapping day key to date object
            """
            today = date.today()
            # Get Monday of current week
            current_week_monday = today - timedelta(days=today.weekday())
            # Add week offset
            target_monday = current_week_monday + timedelta(weeks=week_offset)

            week_dates = {}
            for i, day_info in enumerate(WEEKDAYS):
                week_dates[day_info['key']] = target_monday + timedelta(days=i)
            return week_dates

        def get_holidays_for_week(week_offset: int = 0) -> dict:
            """
            Get federal holidays for the selected week.

            Args:
                week_offset: 0 for current week, 1 for next week

            Returns:
                dict with two keys:
                - 'blocking': {date: name} - Full holidays where swaps are blocked
                - 'early_close': {date: name} - Early close half-days (informational, swaps allowed)
            """
            week_dates = get_week_dates(week_offset)
            week_start = week_dates['monday']
            week_end = week_dates['friday']

            stmt = select(MarketHoliday).where(
                MarketHoliday.holiday_date >= week_start,
                MarketHoliday.holiday_date <= week_end,
                MarketHoliday.market == 'Federal'  # Only federal holidays
            )
            holidays = db.execute(stmt).scalars().all()

            # Separate blocking holidays from early close (informational only)
            blocking = {h.holiday_date: h.name for h in holidays if 'Early Close' not in h.name}
            early_close = {h.holiday_date: h.name for h in holidays if 'Early Close' in h.name}

            return {'blocking': blocking, 'early_close': early_close}

        def get_accepted_swaps_for_week(week_offset: int = 0) -> dict:
            """
            Get accepted swaps for the selected week.

            Returns:
                dict with two mappings:
                - 'by_original_day': {day_key: [(user_who_swapped_away, user_who_swapped_in), ...]}
                - 'user_swapped_day': {user_id: swapped_to_day_key}
            """
            week_dates = get_week_dates(week_offset)
            week_start = week_dates['monday']
            week_end = week_dates['friday']

            stmt = select(WFHDaySwapRequest).where(
                WFHDaySwapRequest.status == 'accepted',
                WFHDaySwapRequest.swap_date >= week_start,
                WFHDaySwapRequest.swap_date <= week_end
            )
            swaps = db.execute(stmt).scalars().all()

            user_swapped_day = {}  # user_id -> day_key they swapped TO

            for swap in swaps:
                # The swap_date is the target's WFH day
                # Requester is swapping TO the target's day
                # Target is swapping TO the requester's day
                target_day_key = swap.swap_date.strftime('%A').lower()

                # Get requester's original WFH day
                requester = user_service.get_user_by_id(swap.requester_id)
                requester_original_day = swap_service._get_wfh_day(requester).lower() if requester else None

                if requester_original_day:
                    # Requester moves to target's day (swap_date)
                    user_swapped_day[swap.requester_id] = target_day_key
                    # Target moves to requester's original day
                    user_swapped_day[swap.target_user_id] = requester_original_day

            return user_swapped_day

        def get_employees_by_day_for_week(week_offset: int = 0) -> dict:
            """
            Get employees for each day, accounting for accepted swaps.

            Returns:
                dict mapping day_key to list of employees who WFH that day for the week
            """
            # Get all employees with their default WFH days
            all_employees_by_default_day = {}
            for day_info in WEEKDAYS:
                employees = list(swap_service.get_users_with_wfh_day(day_info['key'], exclude_user_id=None))
                all_employees_by_default_day[day_info['key']] = {emp.id: emp for emp in employees}

            # Get accepted swaps for this week
            user_swapped_day = get_accepted_swaps_for_week(week_offset)

            # Build the final employees_by_day with swaps applied
            employees_by_day = {day['key']: [] for day in WEEKDAYS}

            # Track which users have been placed (to avoid duplicates)
            placed_users = set()

            # First, place swapped users on their swapped days
            for user_id, swapped_to_day in user_swapped_day.items():
                # Find the user object from any day's default list
                user_obj = None
                for day_employees in all_employees_by_default_day.values():
                    if user_id in day_employees:
                        user_obj = day_employees[user_id]
                        break
                if user_obj and swapped_to_day in employees_by_day:
                    employees_by_day[swapped_to_day].append(user_obj)
                    placed_users.add(user_id)

            # Then, place non-swapped users on their default days
            for day_key, day_employees in all_employees_by_default_day.items():
                for emp_id, emp in day_employees.items():
                    if emp_id not in placed_users:
                        employees_by_day[day_key].append(emp)

            return employees_by_day

        def get_users_with_swaps_for_week(week_offset: int = 0) -> tuple:
            """
            Get users with swaps for a specific week and their paired colors.

            Args:
                week_offset: 0 for current week, 1 for next week

            Returns:
                tuple: (set of user IDs with swaps, dict mapping user_id -> color, dict mapping swap_id -> color)
            """
            week_dates = get_week_dates(week_offset)
            week_start = week_dates['monday']
            week_end = week_dates['friday']

            stmt = select(WFHDaySwapRequest).where(
                WFHDaySwapRequest.status.in_(['pending', 'accepted']),
                WFHDaySwapRequest.swap_date >= week_start,
                WFHDaySwapRequest.swap_date <= week_end
            )
            swaps = db.execute(stmt).scalars().all()

            # Collect all user IDs and assign matching colors to pairs
            users_with_swaps = set()
            user_swap_colors = {}  # user_id -> color
            swap_id_colors = {}  # swap_id -> color (for audit log matching)

            for i, swap in enumerate(swaps):
                # Both users in this swap get the same color
                color = SWAP_PAIR_COLORS[i % len(SWAP_PAIR_COLORS)]
                users_with_swaps.add(swap.requester_id)
                users_with_swaps.add(swap.target_user_id)
                user_swap_colors[swap.requester_id] = color
                user_swap_colors[swap.target_user_id] = color
                swap_id_colors[swap.id] = color  # Map swap ID to color for audit log

            return users_with_swaps, user_swap_colors, swap_id_colors

        def get_all_swaps_for_week(week_offset: int = 0) -> list:
            """
            Get all swap requests for a specific week (for display in history).

            Args:
                week_offset: 0 for current week, 1 for next week

            Returns:
                List of swap requests for the week
            """
            week_dates = get_week_dates(week_offset)
            week_start = week_dates['monday']
            week_end = week_dates['friday']

            stmt = select(WFHDaySwapRequest).where(
                WFHDaySwapRequest.swap_date >= week_start,
                WFHDaySwapRequest.swap_date <= week_end
            ).order_by(WFHDaySwapRequest.requested_at.desc())

            return list(db.execute(stmt).scalars().all())

        # Track users who already have swaps for the current week (will be updated per week)
        # Also track swap_id_colors for audit log color matching
        users_with_swaps, user_swap_colors, swap_id_colors = get_users_with_swaps_for_week(0)
        # Build combined swap_id_colors for both this week and next week (for audit log)
        _, _, next_week_swap_colors = get_users_with_swaps_for_week(1)
        swap_id_colors.update(next_week_swap_colors)

        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='WFH SWAP', show_back=False)

            # Subtitle with user's current WFH day
            with ui.row().classes('items-center gap-3 mb-0'):
                if user_wfh_day:
                    ui.icon('home_work', size='sm').style('color: #3b82f6;')
                    ui.label(f'Your WFH day is').classes('opacity-70')
                    ui.label(user_wfh_day.upper()).classes('font-bold text-blue-400')
                else:
                    ui.icon('info', size='sm').style('color: #f59e0b;')
                    ui.label('No WFH day assigned - contact your manager').classes('text-amber-400')

            # ════════════════════════════════════════════════════════════════
            # WEEK TOGGLE - Switch between This Week and Next Week
            # ════════════════════════════════════════════════════════════════
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('SELECT A TEAMMATE TO REQUEST A SWAP').classes('text-xs font-bold tracking-widest opacity-50')

                # Week toggle buttons
                week_toggle_container = ui.row().classes('gap-0')

            # Weekly limit warning indicator container
            limit_warning_container = ui.row().classes('w-full justify-center mb-2')

            def render_limit_warning():
                """Render weekly limit warning if current user already has a swap this week."""
                limit_warning_container.clear()
                # Check if current user has a swap for the selected week
                current_user_has_swap = user['id'] in users_with_swaps
                if current_user_has_swap:
                    with limit_warning_container:
                        with ui.row().classes('items-center gap-2 p-2 px-4 rounded-lg').style('background-color: #f59e0b20; border: 1px solid #f59e0b;'):
                            ui.icon('warning', size='xs').style('color: #f59e0b;')
                            ui.label('Weekly Limit Reached').classes('text-sm font-semibold').style('color: #f59e0b;')
                            ui.label('— You already have a swap request for this week').classes('text-sm opacity-70')

            def render_week_toggle():
                week_toggle_container.clear()
                with week_toggle_container:
                    with ui.button_group().props('outline rounded'):
                        # This Week button
                        this_week_btn = ui.button('This Week', on_click=lambda: switch_week(0))
                        if selected_week['value'] == 0:
                            this_week_btn.style(f'background-color: {PTO_GOLD} !important; color: white !important;')
                        else:
                            this_week_btn.props('flat')

                        # Next Week button
                        next_week_btn = ui.button('Next Week', on_click=lambda: switch_week(1))
                        if selected_week['value'] == 1:
                            next_week_btn.style(f'background-color: {PTO_GOLD} !important; color: white !important;')
                        else:
                            next_week_btn.props('flat')

            def switch_week(week_offset: int):
                selected_week['value'] = week_offset
                render_week_toggle()
                render_day_columns()
                render_history()

            # ════════════════════════════════════════════════════════════════
            # SWAP DETAIL DIALOG - Full details of a swap request
            # ════════════════════════════════════════════════════════════════
            def show_swap_detail_dialog(swap_req):
                """Show detailed view of a swap request."""
                # Get fresh db for dialog data
                dialog_db = next(get_db())
                try:
                    dialog_user_service = UserService(dialog_db)
                    requester = dialog_user_service.get_user_by_id(swap_req.requester_id)
                    target = dialog_user_service.get_user_by_id(swap_req.target_user_id)
                finally:
                    dialog_db.close()

                requester_name = f"{requester.first_name} {requester.last_name}" if requester else "Unknown"
                target_name = f"{target.first_name} {target.last_name}" if target else "Unknown"
                style = STATUS_STYLES.get(swap_req.status, STATUS_STYLES['pending'])

                with ui.dialog() as detail_dialog, ui.card().classes('p-0').style('background-color: #1f2937; min-width: 480px; max-width: 560px;'):
                    # Header with status color
                    status_colors = {'pending': '#f59e0b', 'accepted': '#22c55e', 'declined': '#ef4444', 'cancelled': '#6b7280', 'expired': '#6b7280'}
                    header_color = status_colors.get(swap_req.status, '#6b7280')

                    with ui.row().classes('w-full p-4 items-center gap-3').style(f'background: linear-gradient(135deg, {header_color}, {header_color}dd);'):
                        ui.icon('swap_horiz', size='md').classes('text-white')
                        ui.label('Swap Request Details').classes('text-xl font-bold text-white')
                        ui.badge(style['text'].upper(), color='white').props('outline')

                    with ui.column().classes('p-6 gap-4'):
                        # Participants Section
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                            ui.label('Participants').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                            with ui.row().classes('w-full gap-4'):
                                # Requester
                                with ui.column().classes('flex-1 gap-1'):
                                    ui.label('Requester').classes('text-xs opacity-50')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('person', size='sm').style('color: #3b82f6;')
                                        ui.label(requester_name).classes('font-semibold')
                                    if requester:
                                        ui.label(f'WFH Day: {swap_req.requester_original_day.title()}').classes('text-xs opacity-60')
                                        if requester.email:
                                            ui.label(requester.email).classes('text-xs opacity-50')

                                # Arrow
                                ui.icon('swap_horiz', size='md').classes('opacity-30 self-center')

                                # Target
                                with ui.column().classes('flex-1 gap-1'):
                                    ui.label('Target').classes('text-xs opacity-50')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('person', size='sm').style('color: #22c55e;')
                                        ui.label(target_name).classes('font-semibold')
                                    if target:
                                        ui.label(f'WFH Day: {swap_req.target_original_day.title()}').classes('text-xs opacity-60')
                                        if target.email:
                                            ui.label(target.email).classes('text-xs opacity-50')

                        # Swap Details Section
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                            ui.label('Swap Details').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                            with ui.row().classes('gap-6'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Swap Date').classes('text-xs opacity-50')
                                    ui.label(swap_req.swap_date.strftime('%A, %B %d, %Y')).classes('font-semibold').style(f'color: {header_color};')

                                with ui.column().classes('gap-1'):
                                    ui.label('Status').classes('text-xs opacity-50')
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon(style['icon'], size='sm').style(f'color: {header_color};')
                                        ui.label(style['text']).classes('font-semibold').style(f'color: {header_color};')

                        # Messages Section
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                            ui.label('Messages').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                            # Request message
                            with ui.column().classes('gap-1 mb-3'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('send', size='xs').style('color: #3b82f6;')
                                    ui.label(f'{requester_name if requester else "Requester"}:').classes('text-xs font-semibold')
                                ui.label(f'"{swap_req.request_message}"').classes('text-sm italic opacity-80 pl-6').style('color: #60a5fa;')

                            # Response message (if exists)
                            if swap_req.response_message:
                                with ui.column().classes('gap-1'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('reply', size='xs').style('color: #22c55e;')
                                        ui.label(f'{target_name if target else "Target"}:').classes('text-xs font-semibold')
                                    ui.label(f'"{swap_req.response_message}"').classes('text-sm italic opacity-80 pl-6').style('color: #22c55e;')

                        # Timestamps Section
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                            ui.label('Timeline').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                            with ui.column().classes('gap-2'):
                                # Requested
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('schedule', size='xs').classes('opacity-50')
                                    ui.label('Requested:').classes('text-xs opacity-50 w-20')
                                    ui.label(swap_req.requested_at.strftime('%A, %B %d, %Y at %I:%M %p')).classes('text-sm')

                                # Responded (if applicable)
                                if swap_req.responded_at:
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('check_circle' if swap_req.status == 'accepted' else 'cancel', size='xs').style(f'color: {header_color};')
                                        ui.label('Responded:').classes('text-xs opacity-50 w-20')
                                        ui.label(swap_req.responded_at.strftime('%A, %B %d, %Y at %I:%M %p')).classes('text-sm')

                                # Expires (if pending)
                                if swap_req.status == 'pending' and swap_req.expires_at:
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('timer', size='xs').style('color: #f59e0b;')
                                        ui.label('Expires:').classes('text-xs opacity-50 w-20')
                                        ui.label(swap_req.expires_at.strftime('%A, %B %d, %Y at %I:%M %p')).classes('text-sm').style('color: #f59e0b;')

                        # Record ID (for admins)
                        if user.get('role') in ['admin', 'superadmin']:
                            ui.label(f'Record ID: {swap_req.id}').classes('text-xs opacity-30 mt-2')

                    # Footer
                    with ui.row().classes('w-full p-4 justify-end').style('background-color: #111827;'):
                        ui.button('Close', on_click=detail_dialog.close).props('flat')

                detail_dialog.open()

            # ════════════════════════════════════════════════════════════════
            # DAY COLUMNS - Each day shows employees who WFH that day
            # ════════════════════════════════════════════════════════════════
            days_container = ui.row().classes('w-full gap-4 mb-6 days-row')

            # ════════════════════════════════════════════════════════════════
            # INCOMING REQUESTS (Below days, no dropdown)
            # ════════════════════════════════════════════════════════════════
            incoming_container = ui.column().classes('w-full')

            def render_incoming():
                incoming_container.clear()
                pending = swap_service.get_pending_for_user(user['id'])

                if pending:
                    with incoming_container:
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('notification_important', size='sm').style('color: #f59e0b;')
                            ui.label(f'Incoming Requests ({len(pending)})').classes('text-lg font-bold text-amber-400')
                        for swap_req in pending:
                            render_incoming_card(swap_req)

            def render_incoming_card(swap_req):
                requester = user_service.get_user_by_id(swap_req.requester_id)
                requester_name = f"{requester.first_name} {requester.last_name}" if requester else "Unknown"

                with ui.card().classes('w-full p-3 mb-2 border-l-4 border-orange-400').style('background-color: #374151;'):
                    with ui.row().classes('w-full justify-between items-start gap-4'):
                        # Left: Request info
                        with ui.column().classes('gap-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('person', size='sm').style('color: #f97316;')
                                ui.label(requester_name).classes('font-semibold')
                                ui.badge('Swap Request', color='orange').props('outline')
                            ui.label(f'Wants to swap for {swap_req.swap_date.strftime("%A, %B %d")}').classes('text-sm opacity-80')
                            if swap_req.request_message:
                                with ui.row().classes('items-start gap-1 mt-1'):
                                    ui.icon('format_quote', size='xs').classes('opacity-50')
                                    ui.label(f'"{swap_req.request_message}"').classes('text-sm italic opacity-70')

                        # Right: Response input and buttons in column
                        with ui.column().classes('gap-2'):
                            response_input = ui.input(placeholder='Response...').props('dense outlined').style('min-width: 280px;')

                            def do_accept(e, req=swap_req, resp=response_input):
                                if not resp.value or not resp.value.strip():
                                    show_warning_dialog('Response Required', 'Please enter a response message.')
                                    return
                                # Get fresh db session for callback (page session may be closed)
                                callback_db = next(get_db())
                                try:
                                    callback_swap_service = WFHSwapService(callback_db)
                                    callback_user_service = UserService(callback_db)
                                    callback_swap_service.accept_swap(req.id, user['id'], resp.value.strip())
                                    req_user = callback_user_service.get_user_by_id(req.requester_id)
                                    requester_name = f"{req_user.first_name} {req_user.last_name}" if req_user else "Unknown"
                                    AuditService.log_wfh_swap_accept(
                                        db=callback_db, user_id=user['id'], username=user.get('username', ''),
                                        swap_id=req.id, requester_name=requester_name,
                                        swap_date=str(req.swap_date)
                                    )
                                    if req_user and req_user.email:
                                        try:
                                            email_service.send_wfh_swap_accepted(
                                                requester_email=req_user.email, requester_name=req_user.first_name,
                                                target_name=f"{current_user.first_name} {current_user.last_name}",
                                                swap_date=req.swap_date, message=resp.value.strip()
                                            )
                                        except Exception:
                                            pass  # Email failure shouldn't block the accept
                                    show_success_dialog('Swap Accepted', 'The WFH day swap has been accepted.')
                                    refresh_all()
                                except ValueError as err:
                                    show_error_dialog('Error', str(err))
                                except Exception as err:
                                    logger.error(f"Error accepting swap: {err}")
                                    show_error_dialog('Error', f'An unexpected error occurred: {str(err)}')
                                finally:
                                    callback_db.close()

                            def do_decline(e, req=swap_req, resp=response_input):
                                if not resp.value or not resp.value.strip():
                                    show_warning_dialog('Response Required', 'Please enter a response message.')
                                    return
                                # Get fresh db session for callback
                                callback_db = next(get_db())
                                try:
                                    callback_swap_service = WFHSwapService(callback_db)
                                    callback_user_service = UserService(callback_db)
                                    callback_swap_service.decline_swap(req.id, user['id'], resp.value.strip())
                                    req_user = callback_user_service.get_user_by_id(req.requester_id)
                                    requester_name = f"{req_user.first_name} {req_user.last_name}" if req_user else "Unknown"
                                    AuditService.log_wfh_swap_decline(
                                        db=callback_db, user_id=user['id'], username=user.get('username', ''),
                                        swap_id=req.id, requester_name=requester_name,
                                        swap_date=str(req.swap_date)
                                    )
                                    if req_user and req_user.email:
                                        try:
                                            email_service.send_wfh_swap_declined(
                                                requester_email=req_user.email, requester_name=req_user.first_name,
                                                target_name=f"{current_user.first_name} {current_user.last_name}",
                                                swap_date=req.swap_date, message=resp.value.strip()
                                            )
                                        except Exception:
                                            pass  # Email failure shouldn't block the decline
                                    show_info_dialog('Request Declined', 'The swap request has been declined.')
                                    refresh_all()
                                except ValueError as err:
                                    show_error_dialog('Error', str(err))
                                except Exception as err:
                                    logger.error(f"Error declining swap: {err}")
                                    show_error_dialog('Error', f'An unexpected error occurred: {str(err)}')
                                finally:
                                    callback_db.close()

                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Accept', on_click=do_accept, icon='check').props('color=positive dense size=sm')
                                ui.button('Decline', on_click=do_decline, icon='close').props('color=negative dense size=sm')

            # Store holidays for current view (will be updated per week)
            week_holidays = {}

            def render_day_columns():
                """Render all 5 day columns with employees listed under each."""
                nonlocal users_with_swaps, user_swap_colors, swap_id_colors, week_holidays
                days_container.clear()

                # Get week-specific data
                week_offset = selected_week['value']
                week_dates = get_week_dates(week_offset)
                employees_by_day = get_employees_by_day_for_week(week_offset)
                user_swapped_day = get_accepted_swaps_for_week(week_offset)
                holidays_data = get_holidays_for_week(week_offset)
                blocking_holidays = holidays_data['blocking']
                early_close_days = holidays_data['early_close']

                # Update users_with_swaps to be week-specific
                users_with_swaps, user_swap_colors, week_swap_colors = get_users_with_swaps_for_week(week_offset)
                swap_id_colors.update(week_swap_colors)  # Merge into main mapping

                # Update weekly limit warning display
                render_limit_warning()

                # Determine user's effective day for this week (swapped or default)
                effective_user_day = user_wfh_day.lower() if user_wfh_day else None
                if user['id'] in user_swapped_day:
                    effective_user_day = user_swapped_day[user['id']]

                with days_container:
                    for day_info in WEEKDAYS:
                        day_key = day_info['key']
                        day_date = week_dates[day_key]
                        is_my_day = effective_user_day and effective_user_day == day_key
                        employees = employees_by_day.get(day_key, [])
                        day_color = day_info['hex']

                        # Check if this day is a blocking holiday (office closed) or early close (half-day, swaps allowed)
                        is_holiday = day_date in blocking_holidays
                        is_early_close = day_date in early_close_days
                        holiday_name = blocking_holidays.get(day_date, '')
                        early_close_name = early_close_days.get(day_date, '')

                        # Build column classes
                        col_classes = f'day-column rounded-lg flex-1 min-w-0 border-l-4 border-{day_info["color"]}'
                        if is_my_day and not is_holiday:
                            col_classes += ' my-day'

                        # Grey out background for blocking holidays only
                        card_style = 'background-color: #1f2937;'
                        if is_holiday:
                            card_style = 'background-color: #374151; opacity: 0.7;'

                        with ui.card().classes(col_classes).style(card_style):
                            with ui.column().classes('w-full h-full'):
                                # Day Header with colored accent, date, and gold star for user's day
                                with ui.column().classes('items-center justify-center gap-0 p-3 border-b border-gray-700'):
                                    with ui.row().classes('items-center gap-1').style('flex-wrap: nowrap;'):
                                        if is_holiday:
                                            ui.icon('event_busy', size='xs').style('color: #ef4444;')
                                        elif is_early_close:
                                            ui.icon('schedule', size='xs').style('color: #f59e0b;')
                                        elif is_my_day:
                                            ui.icon('star', size='xs').style(f'color: {PTO_GOLD};')
                                        header_style = f'color: {day_color};' if not is_holiday else 'color: #9ca3af;'
                                        ui.label(day_info['label']).classes('text-base font-black tracking-wider').style(header_style)
                                    # Date under day name
                                    ui.label(day_date.strftime('%b %d')).classes('text-xs opacity-60')

                                # Employees List
                                with ui.column().classes('w-full p-2 flex-grow'):
                                    if is_holiday:
                                        # Show holiday message and greyed out employees
                                        for emp in employees:
                                            render_employee_name(emp, day_info, user_swapped_day, is_holiday=True, holiday_name=holiday_name)
                                    elif not employees:
                                        ui.label('—').classes('text-center opacity-30 py-4')
                                    else:
                                        for emp in employees:
                                            render_employee_name(emp, day_info, user_swapped_day)

                                # Holiday indicator at bottom - click any employee for details
                                if is_holiday:
                                    ui.label(f'🎄 {holiday_name}').classes('text-xs text-center opacity-60 mt-auto pt-2').style('color: #ef4444;')
                                # Early close indicator (informational - swaps still allowed)
                                elif is_early_close:
                                    ui.label(f'⏰ {early_close_name}').classes('text-xs text-center opacity-60 mt-auto pt-2').style('color: #f59e0b;')

            def format_work_time(t):
                """Format time object to readable string like '9 AM' or '5 PM'."""
                if not t:
                    return None
                hour = t.hour
                minute = t.minute
                am_pm = 'AM' if hour < 12 else 'PM'
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                if minute == 0:
                    return f'{display_hour} {am_pm}'
                else:
                    return f'{display_hour}:{minute:02d} {am_pm}'

            def render_employee_name(emp, day_info, user_swapped_day_for_week=None, is_holiday=False, holiday_name=''):
                """Render a single employee name as a clickable item (or disabled for self/already swapped/holiday)."""
                emp_name = f"{emp.first_name} {emp.last_name}"
                day_color = day_info['hex']
                is_self = emp.id == user['id']
                has_swap = emp.id in users_with_swaps
                # Check if this user is swapped for the selected week
                is_swapped_this_week = user_swapped_day_for_week and emp.id in user_swapped_day_for_week
                # Get paired color for this user's swap (matching their swap partner)
                swap_color = user_swap_colors.get(emp.id, '#f59e0b')

                # Get work schedule
                start_time = format_work_time(getattr(emp, 'work_start_time', None))
                end_time = format_work_time(getattr(emp, 'work_end_time', None))
                schedule_text = f'{start_time} - {end_time}' if start_time and end_time else None

                # If it's a holiday, show greyed out employee - clickable to show holiday info
                if is_holiday:
                    def show_holiday_info(e, h_name=holiday_name):
                        show_info_dialog(
                            f'🎄 Office Closed - Federal Holiday',
                            f'{h_name}\n\nThis day is not available for WFH swaps as the office is closed.'
                        )

                    with ui.element('div').classes('p-1.5 rounded opacity-40 employee-item').style('cursor: pointer;').on('click', show_holiday_info):
                        with ui.row().classes('items-center gap-2'):
                            ui.element('div').classes('w-2 h-2 rounded-full').style('background-color: #6b7280;')
                            with ui.column().classes('gap-0'):
                                ui.label(emp_name).classes('text-sm').style('color: #9ca3af;')
                                if schedule_text:
                                    ui.label(schedule_text).classes('text-xs opacity-50')
                    return

                if is_self:
                    # Show self like others but not clickable
                    with ui.element('div').classes('p-1.5 rounded opacity-60').style('cursor: default;'):
                        with ui.row().classes('items-center gap-2'):
                            if is_swapped_this_week:
                                # Show swap icon - user is on swapped day this week
                                ui.icon('swap_horiz', size='xs').style(f'color: {swap_color}; font-size: 14px;')
                            elif has_swap:
                                # Show swap icon with paired color (pending swap)
                                ui.icon('swap_horiz', size='xs').style(f'color: {swap_color}; font-size: 14px;')
                            else:
                                ui.element('div').classes('w-2 h-2 rounded-full').style(f'background-color: {day_color};')
                            with ui.column().classes('gap-0'):
                                # Color the name if swapped, always show schedule
                                if is_swapped_this_week:
                                    ui.label(emp_name).classes('text-sm font-semibold').style(f'color: {swap_color};')
                                else:
                                    ui.label(emp_name).classes('text-sm')
                                if schedule_text:
                                    ui.label(schedule_text).classes('text-xs opacity-50')
                elif is_swapped_this_week:
                    # Employee is on a swapped day this week - show swap icon, not clickable
                    with ui.element('div').classes('p-1.5 rounded').style('cursor: default;'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('swap_horiz', size='xs').style(f'color: {swap_color}; font-size: 14px;')
                            with ui.column().classes('gap-0'):
                                # Color the name with swap color, always show schedule
                                ui.label(emp_name).classes('text-sm font-semibold').style(f'color: {swap_color};')
                                if schedule_text:
                                    ui.label(schedule_text).classes('text-xs opacity-50')
                elif has_swap:
                    # Employee already has a swap - show swap icon with paired color, not clickable
                    with ui.element('div').classes('p-1.5 rounded opacity-60').style('cursor: not-allowed;').tooltip('Already has a swap this week'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('swap_horiz', size='xs').style(f'color: {swap_color}; font-size: 14px;')
                            with ui.column().classes('gap-0'):
                                ui.label(emp_name).classes('text-sm')
                                if schedule_text:
                                    ui.label(schedule_text).classes('text-xs opacity-50')
                else:
                    # Check if current user has reached their weekly limit
                    current_user_has_swap = user['id'] in users_with_swaps

                    if current_user_has_swap:
                        # Current user has a swap - can't initiate another one this week
                        with ui.element('div').classes('p-1.5 rounded opacity-60').style('cursor: not-allowed;').tooltip('You already have a swap this week'):
                            with ui.row().classes('items-center gap-2'):
                                ui.element('div').classes('w-2 h-2 rounded-full').style(f'background-color: {day_color};')
                                with ui.column().classes('gap-0'):
                                    ui.label(emp_name).classes('text-sm')
                                    if schedule_text:
                                        ui.label(schedule_text).classes('text-xs opacity-50')
                    else:
                        # Normal clickable employee (no swap yet)
                        def open_swap_dialog(e, employee=emp, day=day_info):
                            show_swap_dialog(employee, day)

                        with ui.element('div').classes('employee-item').on('click', open_swap_dialog):
                            with ui.row().classes('items-center gap-2'):
                                # Small colored dot indicator
                                ui.element('div').classes('w-2 h-2 rounded-full').style(f'background-color: {day_color};')
                                with ui.column().classes('gap-0'):
                                    ui.label(emp_name).classes('text-sm')
                                    if schedule_text:
                                        ui.label(schedule_text).classes('text-xs opacity-50')

            def show_swap_dialog(employee, day_info):
                """Show modern swap request dialog."""
                emp_name = f"{employee.first_name} {employee.last_name}"

                # Calculate next occurrence of this day
                today = date.today()
                target_weekday = WEEKDAYS.index(day_info)
                days_ahead = (target_weekday - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week if today
                next_date = today + timedelta(days=days_ahead)

                with ui.dialog() as dialog, ui.card().classes('swap-dialog p-0').style('background-color: #1f2937; min-width: 420px; max-width: 500px;'):
                    # Header
                    with ui.row().classes('w-full p-4 items-center gap-3').style(f'background: linear-gradient(135deg, {PTO_GOLD}, #d4a84b);'):
                        ui.icon('swap_horiz', size='md').classes('text-white')
                        ui.label('Request WFH Swap').classes('text-xl font-bold text-white')

                    with ui.column().classes('p-6 gap-4'):
                        # Target employee info
                        with ui.row().classes('items-center gap-4 p-4 rounded-lg').style('background-color: #374151;'):
                            initials = f"{employee.first_name[0]}{employee.last_name[0]}"
                            with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style(f'background: linear-gradient(135deg, {PTO_GOLD}, #d4a84b);'):
                                ui.label(initials).classes('font-bold text-white')
                            with ui.column().classes('gap-0'):
                                ui.label(emp_name).classes('font-bold')
                                ui.label(f'Works from home on {day_info["label"].title()}s').classes('text-sm opacity-60')
                                # Show work schedule
                                start_time = format_work_time(getattr(employee, 'work_start_time', None))
                                end_time = format_work_time(getattr(employee, 'work_end_time', None))
                                if start_time and end_time:
                                    ui.label(f'Schedule: {start_time} - {end_time}').classes('text-sm opacity-60')

                        # Date selector
                        ui.label('Select Date').classes('font-semibold text-sm opacity-70')

                        # Get blocking holidays for both weeks to filter them out (early close days are allowed)
                        holidays_0 = get_holidays_for_week(0)
                        holidays_1 = get_holidays_for_week(1)
                        all_holidays = {**holidays_0['blocking'], **holidays_1['blocking']}

                        # Show next 2 occurrences of this day (current week + next week only)
                        # Filter out holiday dates
                        date_options = {}
                        check_date = next_date
                        # Calculate end of next week
                        days_until_sunday = 6 - today.weekday()
                        end_of_next_week = today + timedelta(days=days_until_sunday + 7)
                        first_valid_date = None
                        for _ in range(2):
                            if check_date <= end_of_next_week:
                                # Skip if this date is a holiday
                                if check_date not in all_holidays:
                                    date_options[check_date.isoformat()] = check_date.strftime('%A, %B %d, %Y')
                                    if first_valid_date is None:
                                        first_valid_date = check_date
                            check_date += timedelta(weeks=1)

                        date_select = ui.select(
                            options=date_options,
                            value=first_valid_date.isoformat() if first_valid_date else None,
                            label='Choose a date'
                        ).classes('w-full').props('outlined dense')

                        # Show warning if no dates available
                        if not date_options:
                            with ui.row().classes('items-center gap-2 p-3 rounded').style('background-color: rgba(239, 68, 68, 0.2);'):
                                ui.icon('warning', size='xs').style('color: #ef4444;')
                                ui.label('No available dates - all days are holidays').classes('text-sm').style('color: #ef4444;')

                        # Message input
                        ui.label('Your Message').classes('font-semibold text-sm opacity-70')
                        message_input = ui.textarea(
                            placeholder='Explain why you need to swap WFH days...',
                        ).classes('w-full').props('outlined rows=3')

                        # Info note
                        with ui.row().classes('items-start gap-2 p-3 rounded').style('background-color: #374151;'):
                            ui.icon('info', size='xs').style('color: #60a5fa;')
                            ui.label('Your teammate will receive an email notification and can accept or decline.').classes('text-xs opacity-70')

                    # Footer buttons
                    with ui.row().classes('w-full p-4 justify-end gap-3').style('background-color: #111827;'):
                        ui.button('Cancel', on_click=dialog.close).props('flat')

                        def send_request():
                            if not date_select.value:
                                show_warning_dialog('Date Required', 'Please select a date for the swap.')
                                return
                            if not message_input.value or not message_input.value.strip():
                                show_warning_dialog('Message Required', 'Please enter a message explaining why you need to swap.')
                                return

                            # Get fresh db session for callback
                            callback_db = next(get_db())
                            try:
                                swap_date = date.fromisoformat(date_select.value)
                                callback_swap_service = WFHSwapService(callback_db)
                                swap_req = callback_swap_service.create_swap_request(
                                    requester_id=user['id'],
                                    target_user_id=employee.id,
                                    swap_date=swap_date,
                                    message=message_input.value.strip()
                                )

                                # Log audit with the same session
                                try:
                                    AuditService.log_wfh_swap_request(
                                        db=callback_db, user_id=user['id'], username=user.get('username', ''),
                                        swap_id=swap_req.id, target_name=emp_name, swap_date=str(swap_date)
                                    )
                                except Exception:
                                    pass  # Audit failure shouldn't break flow

                                # Swap created successfully - close dialog and refresh UI
                                dialog.close()
                                show_success_dialog('Request Sent', f'Swap request sent to {emp_name}!')
                                refresh_all()

                                # Try email (non-critical - don't block on failures)
                                try:
                                    if employee.email:
                                        email_service.send_wfh_swap_request(
                                            target_email=employee.email, target_name=employee.first_name,
                                            requester_name=f"{current_user.first_name} {current_user.last_name}",
                                            swap_date=swap_date, message=message_input.value.strip()
                                        )
                                except Exception:
                                    show_warning_dialog('Email Failed', 'Email notification could not be sent.')

                            except ValueError as err:
                                show_error_dialog('Validation Error', str(err))
                            except Exception as err:
                                logger.error(f"Error sending swap request: {err}")
                                show_error_dialog('Error', str(err))
                            finally:
                                callback_db.close()

                        ui.button('Send Request', on_click=send_request, icon='send').style(
                            f'background-color: {PTO_GOLD} !important; color: white !important;'
                        )

                dialog.open()

            # ════════════════════════════════════════════════════════════════
            # SWAP HISTORY (All swaps for the selected week)
            # ════════════════════════════════════════════════════════════════
            history_container = ui.column().classes('w-full mt-6')

            def render_history():
                history_container.clear()
                # Get ALL swaps for the selected week (visible to everyone)
                week_offset = selected_week['value']
                week_swaps = get_all_swaps_for_week(week_offset)
                week_label = "This Week" if week_offset == 0 else "Next Week"

                with history_container:
                    with ui.row().classes('items-center gap-2 mb-3'):
                        ui.icon('history', size='sm').classes('opacity-70')
                        ui.label(f'Swaps {week_label} ({len(week_swaps)})').classes('text-lg font-bold opacity-70')
                    if not week_swaps:
                        ui.label('No swap requests for this week').classes('opacity-50')
                    else:
                        for swap_req in week_swaps:
                            render_history_card(swap_req)

            def render_history_card(swap_req):
                # Get both users involved in the swap
                requester = user_service.get_user_by_id(swap_req.requester_id)
                target = user_service.get_user_by_id(swap_req.target_user_id)
                requester_name = f"{requester.first_name} {requester.last_name}" if requester else "Unknown"
                target_name = f"{target.first_name} {target.last_name}" if target else "Unknown"

                # Determine if current user is involved
                is_sent = swap_req.requester_id == user['id']

                # Get paired swap color for this swap
                swap_color = user_swap_colors.get(swap_req.requester_id, '#f59e0b')

                style = STATUS_STYLES[swap_req.status]

                # Build friendly narrative based on status
                if swap_req.status == 'pending':
                    if is_sent:
                        narrative = f"You → {target_name}"
                    else:
                        narrative = f"{requester_name} → You"
                elif swap_req.status == 'accepted':
                    narrative = f"{requester_name} ↔ {target_name}"
                elif swap_req.status == 'declined':
                    if is_sent:
                        narrative = f"{target_name} declined"
                    else:
                        narrative = f"You declined {requester_name}"
                elif swap_req.status == 'cancelled':
                    narrative = f"{requester_name} cancelled"
                else:  # expired
                    narrative = f"{requester_name} → {target_name} (expired)"

                # Click handler for showing details
                def open_details(e, req=swap_req):
                    show_swap_detail_dialog(req)

                with ui.card().classes('w-full p-2 mb-2 border-l-4').style(f'background-color: #374151; border-left-color: {swap_color}; cursor: pointer; transition: all 0.15s ease;').on('click', open_details):
                    # Single compact row with all info
                    with ui.row().classes('w-full justify-between items-center gap-2'):
                        # Left: swap icon, narrative, messages (clickable area)
                        with ui.row().classes('items-center gap-2 flex-grow min-w-0'):
                            ui.icon('swap_horiz', size='xs').style(f'color: {swap_color};')
                            ui.label(narrative).classes('font-semibold text-sm whitespace-nowrap')
                            ui.badge(style['text'], color=style['color']).props('outline dense')
                            # Inline request message (truncated)
                            if swap_req.request_message:
                                req_msg = swap_req.request_message[:30] + '...' if len(swap_req.request_message) > 30 else swap_req.request_message
                                ui.label(f'"{req_msg}"').classes('text-xs opacity-60 italic').style('color: #60a5fa;')
                            # Arrow and reply message if exists
                            if swap_req.response_message:
                                ui.label('→').classes('text-xs opacity-40')
                                resp_msg = swap_req.response_message[:30] + '...' if len(swap_req.response_message) > 30 else swap_req.response_message
                                ui.label(f'"{resp_msg}"').classes('text-xs opacity-60 italic').style('color: #22c55e;')

                        # Right: Date and action buttons
                        with ui.row().classes('items-center gap-2 flex-shrink-0'):
                            ui.label(f'{swap_req.swap_date.strftime("%b %d")}').classes('text-xs opacity-70')
                            # Info button for clarity
                            ui.button(icon='info', on_click=lambda e, req=swap_req: show_swap_detail_dialog(req)).props('flat round dense size=xs').style('color: #60a5fa;').tooltip('View Details')

                            # Cancel button for pending requests I sent (requester only)
                            if swap_req.status == 'pending' and is_sent:
                                def cancel_req(e, req=swap_req):
                                    # Get fresh db session for callback
                                    callback_db = next(get_db())
                                    try:
                                        callback_swap_service = WFHSwapService(callback_db)
                                        callback_swap_service.cancel_swap(req.id, user['id'])
                                        AuditService.log_wfh_swap_cancel(
                                            db=callback_db, user_id=user['id'], username=user.get('username', ''), swap_id=req.id
                                        )
                                        show_info_dialog('Request Cancelled', 'Your swap request has been cancelled.')
                                        refresh_all()
                                    except ValueError as err:
                                        show_error_dialog('Error', str(err))
                                    except Exception as err:
                                        logger.error(f"Error cancelling swap: {err}")
                                        show_error_dialog('Error', f'An unexpected error occurred: {str(err)}')
                                    finally:
                                        callback_db.close()

                                ui.button(icon='cancel', on_click=cancel_req).props('flat round dense color=red size=xs').tooltip('Cancel Request')

                            # Delete button for admin and superadmin
                            if user.get('role') in ['admin', 'superadmin']:
                                def delete_req(e, req=swap_req):
                                    # Get fresh db session for callback
                                    callback_db = next(get_db())
                                    try:
                                        callback_swap_service = WFHSwapService(callback_db)
                                        callback_swap_service.delete_swap(req.id)
                                        # Log admin delete action
                                        AuditService.log(
                                            db=callback_db,
                                            action='wfh_swap_admin_delete',
                                            user_id=user['id'],
                                            username=user.get('username', ''),
                                            entity_type='wfh_swap',
                                            entity_id=req.id,
                                            details={'deleted_swap_id': req.id, 'swap_date': str(req.swap_date)}
                                        )
                                        show_info_dialog('Request Deleted', 'The swap request has been deleted.')
                                        refresh_all()
                                    except Exception as err:
                                        logger.error(f"Error deleting swap: {err}")
                                        show_error_dialog('Error', str(err))
                                    finally:
                                        callback_db.close()

                                ui.button(icon='delete', on_click=delete_req).props('flat round dense color=grey size=xs').tooltip('Delete Request')

            # ════════════════════════════════════════════════════════════════
            # AUDIT HISTORY (Managers/Admins only)
            # ════════════════════════════════════════════════════════════════
            audit_container = ui.column().classes('w-full mt-6')

            # Filter state for audit log
            audit_filter = {'value': 'all'}  # 'all', 'wfh_swap_request', 'wfh_swap_accept', 'wfh_swap_decline', 'wfh_swap_cancel'

            # Filter definitions with display info
            AUDIT_FILTERS = [
                {'key': 'all', 'label': 'All', 'icon': 'list', 'color': '#6b7280'},
                {'key': 'wfh_swap_request', 'label': 'Requested', 'icon': 'send', 'color': '#3b82f6'},
                {'key': 'wfh_swap_accept', 'label': 'Accepted', 'icon': 'check_circle', 'color': '#22c55e'},
                {'key': 'wfh_swap_decline', 'label': 'Declined', 'icon': 'cancel', 'color': '#ef4444'},
                {'key': 'wfh_swap_cancel', 'label': 'Cancelled', 'icon': 'block', 'color': '#6b7280'},
            ]

            def format_audit_description(log) -> str:
                """Convert audit log details to user-friendly plain English description."""
                import json

                action = log.action
                username = log.username or 'Someone'
                details_str = log.details or ''

                # Try to parse JSON details
                details = {}
                if details_str:
                    try:
                        details = json.loads(details_str)
                    except json.JSONDecodeError:
                        # Not JSON, use as-is
                        return details_str

                # Extract common fields
                target_name = details.get('target_employee', details.get('requester_name', ''))
                swap_date_str = details.get('swap_date', '')

                # Format the swap date nicely
                formatted_date = ''
                if swap_date_str:
                    try:
                        from datetime import datetime
                        swap_dt = datetime.strptime(swap_date_str, '%Y-%m-%d').date()
                        formatted_date = swap_dt.strftime('%A, %B %d, %Y')  # e.g., "Monday, December 22, 2025"
                    except ValueError:
                        formatted_date = swap_date_str

                # Generate user-friendly descriptions based on action type
                if action == 'wfh_swap_request':
                    if target_name and formatted_date:
                        return f'Sent a swap request to {target_name} for {formatted_date}'
                    elif target_name:
                        return f'Sent a swap request to {target_name}'
                    else:
                        return 'Sent a swap request'

                elif action == 'wfh_swap_accept':
                    # Handle both old 'requester' key and new 'requester_name' key
                    requester = details.get('requester_name', details.get('requester', ''))
                    if requester and formatted_date:
                        return f'Accepted swap request from {requester} for {formatted_date}'
                    elif requester:
                        return f'Accepted swap request from {requester}'
                    else:
                        return 'Accepted a swap request'

                elif action == 'wfh_swap_decline':
                    # Handle both old 'requester' key and new 'requester_name' key
                    requester = details.get('requester_name', details.get('requester', ''))
                    if requester and formatted_date:
                        return f'Declined swap request from {requester} for {formatted_date}'
                    elif requester:
                        return f'Declined swap request from {requester}'
                    else:
                        return 'Declined a swap request'

                elif action == 'wfh_swap_cancel':
                    return 'Cancelled their swap request'

                # Fallback - return original details
                return details_str if details_str else 'No details available'

            def render_audit_history():
                """Render audit trail for WFH swaps - visible to all users with role-based filtering."""
                import json
                audit_container.clear()

                # Determine date range based on role
                is_manager_or_above = user.get('role') in ['manager', 'admin', 'superadmin']

                if is_manager_or_above:
                    # Managers see the whole year
                    audit_logs = AuditService.get_logs_by_entity_type(db, 'wfh_swap', limit=100)
                    scope_label = f'{date.today().year} Activity'
                else:
                    # Employees see this week and next week only
                    audit_logs = AuditService.get_logs_by_entity_type(db, 'wfh_swap', limit=50)
                    # Filter to this week and next week by checking swap_date in details
                    week_dates_0 = get_week_dates(0)
                    week_dates_1 = get_week_dates(1)
                    week_start = week_dates_0['monday']
                    week_end = week_dates_1['friday']

                    def is_in_week_range(log):
                        """Check if log's swap_date is within this/next week."""
                        try:
                            details = json.loads(log.details or '{}')
                            swap_date_str = details.get('swap_date', '')
                            if swap_date_str:
                                from datetime import datetime
                                swap_dt = datetime.strptime(swap_date_str, '%Y-%m-%d').date()
                                return week_start <= swap_dt <= week_end
                        except (json.JSONDecodeError, ValueError):
                            pass
                        # If we can't parse the date, check if log was created within the weeks
                        return week_start <= log.created_at.date() <= week_end

                    audit_logs = [log for log in audit_logs if is_in_week_range(log)]
                    scope_label = 'This & Next Week'

                if not audit_logs:
                    with audit_container:
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('history_edu', size='sm').style('color: #6b7280;')
                            ui.label('Swap Activity Log').classes('text-lg font-bold opacity-50')
                        ui.label('No swap activity found').classes('opacity-50')
                    return

                # Apply action type filter
                if audit_filter['value'] != 'all':
                    filtered_logs = [log for log in audit_logs if log.action == audit_filter['value']]
                else:
                    filtered_logs = audit_logs

                with audit_container:
                    # Header with title and scope
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('history_edu', size='sm').style('color: #6b7280;')
                            ui.label('Swap Activity Log').classes('text-lg font-bold opacity-50')
                            ui.badge(scope_label, color='grey').props('outline')
                        ui.label(f'{len(filtered_logs)} of {len(audit_logs)}').classes('text-sm opacity-50')

                    # Filter buttons row
                    with ui.row().classes('w-full gap-2 mb-4 flex-wrap'):
                        for filter_def in AUDIT_FILTERS:
                            filter_key = filter_def['key']
                            is_active = audit_filter['value'] == filter_key

                            # Count for this filter
                            if filter_key == 'all':
                                count = len(audit_logs)
                            else:
                                count = len([log for log in audit_logs if log.action == filter_key])

                            def set_filter(e, key=filter_key):
                                audit_filter['value'] = key
                                render_audit_history()

                            # Active filter gets gold styling
                            if is_active:
                                btn = ui.button(f'{filter_def["label"]} ({count})', icon=filter_def['icon'], on_click=set_filter)
                                btn.style(f'background-color: {PTO_GOLD} !important; color: white !important;')
                            else:
                                btn = ui.button(f'{filter_def["label"]} ({count})', icon=filter_def['icon'], on_click=set_filter)
                                btn.props('flat').style(f'color: {filter_def["color"]};')

                    # Action icons and colors
                    action_styles = {
                        'wfh_swap_request': {'icon': 'send', 'color': '#3b82f6', 'label': 'Requested'},
                        'wfh_swap_accept': {'icon': 'check_circle', 'color': '#22c55e', 'label': 'Accepted'},
                        'wfh_swap_decline': {'icon': 'cancel', 'color': '#ef4444', 'label': 'Declined'},
                        'wfh_swap_cancel': {'icon': 'block', 'color': '#6b7280', 'label': 'Cancelled'},
                    }

                    def show_audit_detail(log_entry):
                        """Show audit log detail and try to find related swap if it exists."""
                        import json

                        # Parse log details
                        details = {}
                        if log_entry.details:
                            try:
                                details = json.loads(log_entry.details)
                            except json.JSONDecodeError:
                                pass

                        style = action_styles.get(log_entry.action, {'icon': 'info', 'color': '#6b7280', 'label': log_entry.action})

                        # Try to find the related swap request
                        swap_req = None
                        if log_entry.entity_id:
                            detail_db = next(get_db())
                            try:
                                swap_service_detail = WFHSwapService(detail_db)
                                swap_req = swap_service_detail.get_swap_by_id(log_entry.entity_id)
                            finally:
                                detail_db.close()

                        with ui.dialog() as audit_dialog, ui.card().classes('p-0').style('background-color: #1f2937; min-width: 450px; max-width: 520px;'):
                            # Header
                            with ui.row().classes('w-full p-4 items-center gap-3').style(f'background: linear-gradient(135deg, {style["color"]}, {style["color"]}dd);'):
                                ui.icon(style['icon'], size='md').classes('text-white')
                                ui.label('Activity Details').classes('text-xl font-bold text-white')
                                ui.badge(style['label'].upper(), color='white').props('outline')

                            with ui.column().classes('p-6 gap-4'):
                                # Activity Info
                                with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                                    ui.label('Activity').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                                    with ui.column().classes('gap-2'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('person', size='sm').style(f'color: {style["color"]};')
                                            ui.label(log_entry.username or 'Unknown').classes('font-semibold')

                                        ui.label(format_audit_description(log_entry)).classes('text-sm opacity-80')

                                        ui.label(log_entry.created_at.strftime('%A, %B %d, %Y at %I:%M %p')).classes('text-xs opacity-50 mt-2')

                                # Details from JSON
                                if details:
                                    with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                                        ui.label('Details').classes('text-xs font-bold tracking-widest opacity-50 mb-3')

                                        for key, value in details.items():
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(f'{key.replace("_", " ").title()}:').classes('text-xs opacity-50 w-28')
                                                ui.label(str(value)).classes('text-sm')

                                # Related Swap (if exists and found)
                                if swap_req:
                                    with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #374151;'):
                                        with ui.row().classes('w-full justify-between items-center mb-3'):
                                            ui.label('Related Swap Request').classes('text-xs font-bold tracking-widest opacity-50')
                                            swap_style = STATUS_STYLES.get(swap_req.status, STATUS_STYLES['pending'])
                                            ui.badge(swap_style['text'], color=swap_style['color']).props('outline dense')

                                        def view_swap_details(e, req=swap_req):
                                            """Open swap detail dialog (keeps audit dialog open underneath)."""
                                            show_swap_detail_dialog(req)

                                        ui.button('View Full Swap Details', icon='open_in_new',
                                                  on_click=view_swap_details).props('outline dense').style(f'color: {PTO_GOLD}; border-color: {PTO_GOLD};')

                                elif log_entry.entity_id:
                                    with ui.element('div').classes('w-full p-3 rounded-lg').style('background-color: #374151;'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('info', size='xs').classes('opacity-50')
                                            ui.label('Related swap request no longer exists (may have been deleted)').classes('text-xs opacity-50')

                                # Record ID (for admins)
                                if user.get('role') in ['admin', 'superadmin']:
                                    ui.label(f'Audit Log ID: {log_entry.id} | Entity ID: {log_entry.entity_id or "N/A"}').classes('text-xs opacity-30 mt-2')

                            # Footer
                            with ui.row().classes('w-full p-4 justify-end').style('background-color: #111827;'):
                                ui.button('Close', on_click=audit_dialog.close).props('flat')

                        audit_dialog.open()

                    if not filtered_logs:
                        filter_label = next((f['label'] for f in AUDIT_FILTERS if f['key'] == audit_filter['value']), 'selected')
                        ui.label(f'No {filter_label.lower()} activity').classes('opacity-50')
                    else:
                        for log in filtered_logs:
                            style = action_styles.get(log.action, {'icon': 'info', 'color': '#6b7280', 'label': log.action})

                            # Get user-friendly description
                            friendly_description = format_audit_description(log)

                            # Format the timestamp nicely
                            log_date = log.created_at.strftime('%A, %B %d, %Y at %I:%M %p')  # e.g., "Monday, December 22, 2025 at 2:30 PM"

                            # Click handler for audit detail
                            def open_audit_detail(e, log_entry=log):
                                show_audit_detail(log_entry)

                            # Use swap pair color for border to match the Swaps This Week section
                            # Look up the color from swap_id_colors (same as used in Swaps This Week)
                            # Falls back to action-based color if swap not in current/next week mapping
                            border_color = swap_id_colors.get(log.entity_id, style["color"]) if log.entity_id else style["color"]

                            # Add colored left border matching the swap pair - make clickable
                            with ui.card().classes('w-full p-3 mb-2 border-l-4').style(f'background-color: #1f2937; border-left-color: {border_color}; cursor: pointer; transition: all 0.15s ease;').on('click', open_audit_detail):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('items-center gap-3'):
                                        ui.icon(style['icon'], size='sm').style(f'color: {style["color"]};')
                                        with ui.column().classes('gap-0'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(log.username or 'Unknown').classes('font-semibold')
                                                ui.badge(style['label']).style(f'background-color: {style["color"]} !important;')
                                            ui.label(friendly_description).classes('text-sm opacity-70')

                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(log_date).classes('text-xs opacity-50')
                                        # Info button for clarity
                                        ui.button(icon='info', on_click=lambda e, log_entry=log: show_audit_detail(log_entry)).props('flat round dense size=xs').style('color: #60a5fa;').tooltip('View Details')

                                        # Admin and superadmin can delete audit entries
                                        if user.get('role') in ['admin', 'superadmin']:
                                            def delete_log(e, log_id=log.id):
                                                # Get fresh db session for callback
                                                callback_db = next(get_db())
                                                try:
                                                    AuditService.delete_audit_log(callback_db, log_id)
                                                    show_info_dialog('Entry Deleted', 'The audit entry has been deleted.')
                                                    render_audit_history()
                                                except Exception as err:
                                                    logger.error(f"Error deleting audit log: {err}")
                                                    show_error_dialog('Error', str(err))
                                                finally:
                                                    callback_db.close()

                                            ui.button(icon='delete', on_click=delete_log).props('flat round dense size=xs color=red').tooltip('Delete audit entry')

            def refresh_all():
                """Refresh all sections."""
                nonlocal users_with_swaps, user_swap_colors, swap_id_colors, week_holidays

                # Re-fetch users who have swaps for the selected week
                users_with_swaps, user_swap_colors, week_swap_colors = get_users_with_swaps_for_week(selected_week['value'])
                swap_id_colors.update(week_swap_colors)
                week_holidays = get_holidays_for_week(selected_week['value'])

                # render_day_columns now fetches employees internally with swap logic
                render_day_columns()
                render_incoming()
                render_history()
                render_audit_history()

            # Initial render
            render_week_toggle()
            render_day_columns()
            render_incoming()
            render_history()
            render_audit_history()

            # Auto-refresh timer - checks for swap changes every 5 seconds
            last_swap_state = {'ids': frozenset(users_with_swaps)}

            def check_for_updates():
                """Check if swap data has changed and refresh if needed."""
                nonlocal last_swap_state
                current_swaps, _, _ = get_users_with_swaps_for_week(selected_week['value'])
                current_state = frozenset(current_swaps)

                if current_state != last_swap_state['ids']:
                    last_swap_state['ids'] = current_state
                    refresh_all()

            # Create auto-refresh timer (5 second interval)
            ui.timer(5.0, check_for_updates)

            # Back button at bottom left
            ui.button('Back', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6').style(f'border-color: {PTO_GOLD} !important; color: {PTO_GOLD} !important;')

    finally:
        db.close()
