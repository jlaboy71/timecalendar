"""Team Calendar page showing market holidays and approved PTO."""
from nicegui import ui, app
from src.database import get_db
from src.models.market_holiday import MarketHoliday
from src.models.pto_request import PTORequest
from src.models.user import User
from src.models.department import Department
from src.services.user_service import UserService
from src.services.department_service import DepartmentService
from datetime import date, timedelta
from calendar import monthcalendar, month_name
from collections import defaultdict


def calendar_page():
    """Team calendar page with monthly view of holidays and PTO."""

    # Check if user is logged in
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')

    # State for current month/year view
    today = date.today()
    current_month = {'month': today.month, 'year': today.year}

    # Load persisted preferences from session or use defaults
    calendar_prefs = app.storage.general.get('calendar_prefs', {})

    # State for filters with persistence
    selected_department = {'id': calendar_prefs.get('department_id', None)}
    view_mode = {'mode': calendar_prefs.get('view_mode', 'team' if user_role in ['manager', 'admin'] else 'my')}
    show_holidays = {'value': calendar_prefs.get('show_holidays', True)}
    show_weekends = {'value': calendar_prefs.get('show_weekends', True)}
    leave_type_filters = {
        'vacation': calendar_prefs.get('filter_vacation', True),
        'sick': calendar_prefs.get('filter_sick', True),
        'personal': calendar_prefs.get('filter_personal', True),
        'other': calendar_prefs.get('filter_other', True)
    }
    current_view = {'view': calendar_prefs.get('current_view', 'month')}  # 'month' or 'year'

    # Store PTO request details for click handlers
    pto_requests_cache = {}

    def save_preferences():
        """Save current filter preferences to session."""
        app.storage.general['calendar_prefs'] = {
            'department_id': selected_department['id'],
            'view_mode': view_mode['mode'],
            'show_holidays': show_holidays['value'],
            'show_weekends': show_weekends['value'],
            'filter_vacation': leave_type_filters['vacation'],
            'filter_sick': leave_type_filters['sick'],
            'filter_personal': leave_type_filters['personal'],
            'filter_other': leave_type_filters['other'],
            'current_view': current_view['view']
        }

    # Main container
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('Team Calendar').classes('text-3xl font-bold mb-4')

        # ===== VIEW TOGGLE (managers/admins only) =====
        if user_role in ['manager', 'admin']:
            with ui.row().classes('w-full mb-4 gap-2'):
                ui.label('View:').classes('font-medium self-center')

                def set_view_mode(mode):
                    view_mode['mode'] = mode
                    save_preferences()
                    render_current_view()

                my_btn = ui.button(
                    'My Calendar',
                    on_click=lambda: set_view_mode('my')
                ).props('flat' if view_mode['mode'] != 'my' else '')
                if view_mode['mode'] == 'my':
                    my_btn.props('color=primary')

                team_btn = ui.button(
                    'Team Calendar',
                    on_click=lambda: set_view_mode('team')
                ).props('flat' if view_mode['mode'] != 'team' else '')
                if view_mode['mode'] == 'team':
                    team_btn.props('color=primary')

        # ===== FILTERS ROW =====
        with ui.expansion('Filters & Options', icon='filter_list').classes('w-full mb-4'):
            with ui.column().classes('w-full gap-4 p-2'):
                # Row 1: Department filter (admin only) and Leave Type filters
                with ui.row().classes('w-full gap-6 flex-wrap'):
                    # Department filter (admin only, team view only)
                    if user_role == 'admin':
                        with ui.column().classes('gap-1'):
                            ui.label('Department').classes('text-sm font-medium')
                            db = next(get_db())
                            try:
                                departments = DepartmentService.get_all_departments(db)
                                dept_options = {None: 'All Departments'}
                                dept_options.update({dept.id: dept.name for dept in departments})
                            finally:
                                db.close()

                            def on_dept_change(e):
                                selected_department['id'] = e.value
                                save_preferences()
                                render_current_view()

                            dept_select = ui.select(
                                dept_options,
                                value=selected_department['id'],
                                on_change=on_dept_change
                            ).classes('w-48')

                            # Disable when in "My Calendar" mode
                            if view_mode['mode'] == 'my':
                                dept_select.disable()

                    # Leave Type Filters
                    with ui.column().classes('gap-1'):
                        ui.label('Leave Types').classes('text-sm font-medium')
                        with ui.row().classes('gap-4'):
                            def create_leave_filter_handler(leave_type):
                                def handler(e):
                                    leave_type_filters[leave_type] = e.value
                                    save_preferences()
                                    render_current_view()
                                return handler

                            ui.checkbox(
                                'Vacation',
                                value=leave_type_filters['vacation'],
                                on_change=create_leave_filter_handler('vacation')
                            ).classes('text-blue-600')
                            ui.checkbox(
                                'Sick',
                                value=leave_type_filters['sick'],
                                on_change=create_leave_filter_handler('sick')
                            ).classes('text-green-600')
                            ui.checkbox(
                                'Personal',
                                value=leave_type_filters['personal'],
                                on_change=create_leave_filter_handler('personal')
                            ).classes('text-purple-600')
                            ui.checkbox(
                                'Other',
                                value=leave_type_filters['other'],
                                on_change=create_leave_filter_handler('other')
                            ).classes('text-gray-600')

                # Row 2: Show/Hide options
                with ui.row().classes('w-full gap-6'):
                    with ui.column().classes('gap-1'):
                        ui.label('Display Options').classes('text-sm font-medium')
                        with ui.row().classes('gap-4'):
                            def on_holidays_change(e):
                                show_holidays['value'] = e.value
                                save_preferences()
                                render_current_view()

                            def on_weekends_change(e):
                                show_weekends['value'] = e.value
                                save_preferences()
                                render_current_view()

                            ui.checkbox(
                                'Show Market Holidays',
                                value=show_holidays['value'],
                                on_change=on_holidays_change
                            )
                            ui.checkbox(
                                'Show Weekends',
                                value=show_weekends['value'],
                                on_change=on_weekends_change
                            )

        # ===== NAVIGATION ROW =====
        with ui.row().classes('w-full justify-between items-center mb-4'):
            # Month/Year navigation
            with ui.row().classes('gap-2 items-center'):
                ui.button(icon='chevron_left', on_click=lambda: navigate_month(-1)).props('flat')

                month_label = ui.label().classes('text-xl font-semibold min-w-48 text-center')

                ui.button(icon='chevron_right', on_click=lambda: navigate_month(1)).props('flat')

                ui.button('Today', on_click=lambda: go_to_today()).props('flat')

            # View toggle (Month / Year)
            with ui.row().classes('gap-2'):
                def set_month_view():
                    current_view['view'] = 'month'
                    save_preferences()
                    render_current_view()

                def set_year_view():
                    current_view['view'] = 'year'
                    save_preferences()
                    render_current_view()

                month_view_btn = ui.button('Month', on_click=set_month_view)
                if current_view['view'] == 'month':
                    month_view_btn.props('color=primary')
                else:
                    month_view_btn.props('flat')

                year_view_btn = ui.button('Year', on_click=set_year_view)
                if current_view['view'] == 'year':
                    year_view_btn.props('color=primary')
                else:
                    year_view_btn.props('flat')

        # Calendar container
        calendar_container = ui.column().classes('w-full')

        # Legend
        with ui.row().classes('w-full gap-6 mt-6 flex-wrap'):
            ui.label('Legend:').classes('font-semibold')
            if show_holidays['value']:
                with ui.row().classes('gap-1 items-center'):
                    ui.element('div').classes('w-4 h-4 bg-red-200 border border-red-400 rounded')
                    ui.label('Market Holiday').classes('text-sm')
            if leave_type_filters['vacation']:
                with ui.row().classes('gap-1 items-center'):
                    ui.element('div').classes('w-4 h-4 bg-blue-200 border border-blue-400 rounded')
                    ui.label('Vacation').classes('text-sm')
            if leave_type_filters['sick']:
                with ui.row().classes('gap-1 items-center'):
                    ui.element('div').classes('w-4 h-4 bg-green-200 border border-green-400 rounded')
                    ui.label('Sick').classes('text-sm')
            if leave_type_filters['personal']:
                with ui.row().classes('gap-1 items-center'):
                    ui.element('div').classes('w-4 h-4 bg-purple-200 border border-purple-400 rounded')
                    ui.label('Personal').classes('text-sm')
            if leave_type_filters['other']:
                with ui.row().classes('gap-1 items-center'):
                    ui.element('div').classes('w-4 h-4 bg-gray-200 border border-gray-400 rounded')
                    ui.label('Other').classes('text-sm')

        # Back button
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-6')

        # ===== MODAL FUNCTIONS =====

        def show_pto_detail_modal(request_id: int):
            """Show modal with PTO request details."""
            db = next(get_db())
            try:
                pto_request = db.query(PTORequest).filter(PTORequest.id == request_id).first()
                if not pto_request:
                    ui.notify('Request not found', type='negative')
                    return

                pto_user = db.query(User).filter(User.id == pto_request.user_id).first()
                employee_name = f"{pto_user.first_name} {pto_user.last_name}" if pto_user else "Unknown"

                with ui.dialog() as dialog, ui.card().classes('min-w-96'):
                    ui.label('PTO Request Details').classes('text-xl font-bold mb-4')

                    with ui.column().classes('gap-2'):
                        ui.label(f'Employee: {employee_name}').classes('font-medium')
                        ui.label(f'Leave Type: {pto_request.pto_type.title()}')
                        ui.label(f'Date Range: {pto_request.start_date.strftime("%m/%d/%Y")} - {pto_request.end_date.strftime("%m/%d/%Y")}')
                        ui.label(f'Total Days: {pto_request.total_days}')
                        ui.label(f'Status: {pto_request.status.title()}')

                        if pto_request.notes:
                            ui.separator()
                            ui.label('Notes:').classes('font-medium')
                            ui.label(pto_request.notes).classes('text-gray-600')

                    ui.separator()

                    with ui.row().classes('w-full justify-end gap-2'):
                        if user_role in ['manager', 'admin'] and pto_request.user_id != user_id:
                            ui.button(
                                'View Full Request',
                                on_click=lambda: (dialog.close(), ui.navigate.to(f'/manager/request/{request_id}'))
                            ).props('color=primary')

                        ui.button('Close', on_click=dialog.close).props('flat')

                dialog.open()
            finally:
                db.close()

        def show_holiday_modal(holiday_date: date, holidays: list):
            """Show modal with market holiday details."""
            holiday_info = {}
            for h in holidays:
                if h.name not in holiday_info:
                    holiday_info[h.name] = []
                holiday_info[h.name].append(h.market)

            with ui.dialog() as dialog, ui.card().classes('min-w-80'):
                ui.label('Market Holiday').classes('text-xl font-bold mb-4')

                with ui.column().classes('gap-3'):
                    ui.label(f'Date: {holiday_date.strftime("%A, %B %d, %Y")}').classes('font-medium')

                    for h_name, markets in holiday_info.items():
                        with ui.card().classes('w-full bg-red-50 p-3'):
                            ui.label(h_name).classes('font-semibold text-red-800')

                            major_exchanges = {'NYSE', 'CME', 'CBOE'}
                            closed_exchanges = set(markets)

                            if major_exchanges.issubset(closed_exchanges):
                                ui.label('All major exchanges closed').classes('text-sm text-red-700')
                            else:
                                ui.label(f'Exchanges closed: {", ".join(markets)}').classes('text-sm text-red-700')

                    ui.separator()
                    ui.label('Company offices may be closed on this day.').classes('text-sm text-gray-600 italic')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=dialog.close).props('flat')

            dialog.open()

        def show_all_pto_modal(click_date: date, pto_entries: list):
            """Show modal listing all PTO entries for a day."""
            with ui.dialog() as dialog, ui.card().classes('min-w-96'):
                ui.label(f'PTO on {click_date.strftime("%B %d, %Y")}').classes('text-xl font-bold mb-4')

                with ui.column().classes('gap-2 max-h-96 overflow-y-auto'):
                    for entry in pto_entries:
                        color_class = get_pto_color(entry['type'])

                        def create_click_handler(req_id):
                            return lambda: (dialog.close(), show_pto_detail_modal(req_id))

                        with ui.card().classes(f'w-full p-3 cursor-pointer hover:shadow-md {color_class}').on('click', create_click_handler(entry['request_id'])):
                            ui.label(entry['full_name']).classes('font-semibold')
                            ui.label(entry['type'].title()).classes('text-sm')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=dialog.close).props('flat')

            dialog.open()

        def show_quick_request_popup(click_date: date):
            """Show popup for quick PTO request on empty day (employees only)."""
            if user_role != 'employee':
                return

            if click_date < today:
                ui.notify('Cannot request time off for past dates', type='warning')
                return

            with ui.dialog() as dialog, ui.card().classes('min-w-80'):
                ui.label('Request Time Off').classes('text-xl font-bold mb-2')
                ui.label(f'{click_date.strftime("%A, %B %d, %Y")}').classes('text-gray-600 mb-4')

                ui.label('Would you like to submit a PTO request for this date?').classes('mb-4')

                with ui.row().classes('w-full justify-end gap-2'):
                    def go_to_request():
                        dialog.close()
                        app.storage.general['prefill_pto_date'] = click_date.isoformat()
                        ui.navigate.to('/submit-request')

                    ui.button('Submit Request', on_click=go_to_request).props('color=primary')
                    ui.button('Cancel', on_click=dialog.close).props('flat')

            dialog.open()

        # ===== HELPER FUNCTIONS =====

        def navigate_month(delta):
            """Navigate to previous or next month."""
            new_month = current_month['month'] + delta
            new_year = current_month['year']

            if new_month > 12:
                new_month = 1
                new_year += 1
            elif new_month < 1:
                new_month = 12
                new_year -= 1

            current_month['month'] = new_month
            current_month['year'] = new_year
            render_current_view()

        def go_to_today():
            """Jump to current month."""
            current_month['month'] = today.month
            current_month['year'] = today.year
            render_current_view()

        def get_pto_color(pto_type: str) -> str:
            """Get color class based on PTO type."""
            pto_type_lower = pto_type.lower()
            if 'vacation' in pto_type_lower:
                return 'bg-blue-200 border-blue-400 text-blue-800'
            elif 'sick' in pto_type_lower:
                return 'bg-green-200 border-green-400 text-green-800'
            elif 'personal' in pto_type_lower:
                return 'bg-purple-200 border-purple-400 text-purple-800'
            else:
                return 'bg-gray-200 border-gray-400 text-gray-800'

        def get_leave_type_category(pto_type: str) -> str:
            """Categorize leave type for filtering."""
            pto_type_lower = pto_type.lower()
            if 'vacation' in pto_type_lower:
                return 'vacation'
            elif 'sick' in pto_type_lower:
                return 'sick'
            elif 'personal' in pto_type_lower:
                return 'personal'
            else:
                return 'other'

        def should_show_pto(pto_type: str) -> bool:
            """Check if PTO type should be shown based on filters."""
            category = get_leave_type_category(pto_type)
            return leave_type_filters.get(category, True)

        def render_current_view():
            """Render either month or year view based on current selection."""
            if current_view['view'] == 'year':
                render_year_view()
            else:
                render_calendar()

        def render_year_view():
            """Render compact 12-month year overview."""
            calendar_container.clear()
            year = current_month['year']

            month_label.text = str(year)

            db = next(get_db())
            try:
                # Query all holidays and PTO for the year
                year_start = date(year, 1, 1)
                year_end = date(year, 12, 31)

                holidays = db.query(MarketHoliday).filter(
                    MarketHoliday.holiday_date >= year_start,
                    MarketHoliday.holiday_date <= year_end
                ).all() if show_holidays['value'] else []

                holidays_by_month = defaultdict(set)
                for h in holidays:
                    holidays_by_month[h.holiday_date.month].add(h.holiday_date.day)

                # Query PTO based on view mode
                pto_query = db.query(PTORequest).filter(
                    PTORequest.status == 'approved',
                    PTORequest.start_date <= year_end,
                    PTORequest.end_date >= year_start
                )

                if view_mode['mode'] == 'my':
                    pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role == 'manager' and view_mode['mode'] == 'team':
                    user_service = UserService(db)
                    manager = user_service.get_user_by_id(user_id)
                    if manager and manager.department_id:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == manager.department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))
                elif user_role == 'admin' and view_mode['mode'] == 'team':
                    if selected_department['id']:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == selected_department['id'],
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))

                approved_pto = pto_query.all()

                # Count PTO days per month
                pto_by_month = defaultdict(int)
                for pto in approved_pto:
                    if not should_show_pto(pto.pto_type):
                        continue
                    current_date = max(pto.start_date, year_start)
                    end = min(pto.end_date, year_end)
                    while current_date <= end:
                        pto_by_month[current_date.month] += 1
                        current_date += timedelta(days=1)

            finally:
                db.close()

            with calendar_container:
                with ui.element('div').classes('grid grid-cols-4 gap-4'):
                    for month_num in range(1, 13):
                        holiday_count = len(holidays_by_month[month_num])
                        pto_count = pto_by_month[month_num]

                        def create_month_click_handler(m):
                            def handler():
                                current_month['month'] = m
                                current_view['view'] = 'month'
                                save_preferences()
                                render_current_view()
                            return handler

                        with ui.card().classes('p-3 cursor-pointer hover:shadow-lg transition-shadow').on('click', create_month_click_handler(month_num)):
                            ui.label(month_name[month_num]).classes('font-semibold text-center')

                            # Show density indicators
                            with ui.row().classes('justify-center gap-2 mt-2'):
                                if holiday_count > 0 and show_holidays['value']:
                                    ui.badge(str(holiday_count), color='red').tooltip(f'{holiday_count} holidays')
                                if pto_count > 0:
                                    ui.badge(str(pto_count), color='blue').tooltip(f'{pto_count} PTO days')

                            # Highlight current month
                            if month_num == today.month and year == today.year:
                                ui.element('div').classes('w-full h-1 bg-primary mt-2 rounded')

        def render_calendar():
            """Render the calendar grid for the current month."""
            calendar_container.clear()
            pto_requests_cache.clear()

            month = current_month['month']
            year = current_month['year']

            month_label.text = f'{month_name[month]} {year}'

            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            db = next(get_db())
            try:
                # Query market holidays
                holidays_by_date = defaultdict(list)
                if show_holidays['value']:
                    holidays = db.query(MarketHoliday).filter(
                        MarketHoliday.holiday_date >= first_day,
                        MarketHoliday.holiday_date <= last_day
                    ).all()
                    for holiday in holidays:
                        holidays_by_date[holiday.holiday_date].append(holiday)

                # Query approved PTO based on view mode
                pto_query = db.query(PTORequest).filter(
                    PTORequest.status == 'approved',
                    PTORequest.start_date <= last_day,
                    PTORequest.end_date >= first_day
                )

                # Apply view mode filtering
                if view_mode['mode'] == 'my':
                    pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role == 'employee':
                    pto_query = pto_query.filter(PTORequest.user_id == user_id)
                elif user_role == 'manager' and view_mode['mode'] == 'team':
                    user_service = UserService(db)
                    manager = user_service.get_user_by_id(user_id)
                    if manager and manager.department_id:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == manager.department_id,
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))
                elif user_role == 'admin' and view_mode['mode'] == 'team':
                    if selected_department['id']:
                        dept_user_ids = [u.id for u in db.query(User).filter(
                            User.department_id == selected_department['id'],
                            User.is_active == True
                        ).all()]
                        pto_query = pto_query.filter(PTORequest.user_id.in_(dept_user_ids))

                approved_pto = pto_query.all()

                for pto in approved_pto:
                    pto_requests_cache[pto.id] = pto

                # Build PTO lookup by date with filtering
                pto_by_date = defaultdict(list)
                user_ids = set(pto.user_id for pto in approved_pto)
                users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

                for pto in approved_pto:
                    if not should_show_pto(pto.pto_type):
                        continue

                    current_date = max(pto.start_date, first_day)
                    end = min(pto.end_date, last_day)
                    while current_date <= end:
                        pto_user = users.get(pto.user_id)
                        if pto_user:
                            initials = f"{pto_user.first_name[0]}{pto_user.last_name[0]}"
                            pto_by_date[current_date].append({
                                'request_id': pto.id,
                                'user': pto_user,
                                'initials': initials,
                                'type': pto.pto_type,
                                'full_name': f"{pto_user.first_name} {pto_user.last_name}"
                            })
                        current_date += timedelta(days=1)

            finally:
                db.close()

            # Generate calendar grid
            weeks = monthcalendar(year, month)

            # Determine which days to show
            if show_weekends['value']:
                day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                day_indices = list(range(7))
            else:
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
                day_indices = [1, 2, 3, 4, 5]  # Monday=0 in Python, but our week starts Sun

            with calendar_container:
                with ui.element('div').classes('w-full border border-gray-300 rounded-lg overflow-hidden'):
                    # Header row
                    with ui.row().classes('w-full bg-gray-100'):
                        for day_name in day_names:
                            with ui.element('div').classes('flex-1 p-2 text-center font-semibold border-r border-gray-300 last:border-r-0'):
                                ui.label(day_name).classes('text-sm')

                    # Calendar weeks
                    for week in weeks:
                        # Filter days if hiding weekends
                        if show_weekends['value']:
                            display_days = week
                        else:
                            # week is [Sun, Mon, Tue, Wed, Thu, Fri, Sat] - we want Mon-Fri (indices 1-5)
                            display_days = week[1:6]

                        # Skip weeks that are all zeros after filtering
                        if all(d == 0 for d in display_days):
                            continue

                        with ui.row().classes('w-full border-t border-gray-300'):
                            for idx, day_num in enumerate(display_days):
                                cell_classes = 'flex-1 min-h-24 p-1 border-r border-gray-300 last:border-r-0 relative'

                                if day_num == 0:
                                    cell_classes += ' bg-gray-50'
                                    with ui.element('div').classes(cell_classes):
                                        pass
                                else:
                                    current_date = date(year, month, day_num)
                                    is_today = current_date == today
                                    is_weekend = current_date.weekday() >= 5
                                    has_holiday = current_date in holidays_by_date and show_holidays['value']
                                    has_pto = current_date in pto_by_date

                                    if has_holiday:
                                        cell_classes += ' bg-red-50'
                                    elif is_weekend:
                                        cell_classes += ' bg-gray-50'
                                    else:
                                        cell_classes += ' bg-white'

                                    if user_role == 'employee' and not has_holiday and not has_pto:
                                        cell_classes += ' cursor-pointer hover:bg-blue-50'

                                    def create_empty_day_handler(d):
                                        return lambda: show_quick_request_popup(d)

                                    cell_element = ui.element('div').classes(cell_classes)

                                    if user_role == 'employee' and not has_holiday and not has_pto:
                                        cell_element.on('click', create_empty_day_handler(current_date))

                                    with cell_element:
                                        day_classes = 'text-sm font-medium'
                                        if is_today:
                                            with ui.element('div').classes('w-6 h-6 bg-primary rounded-full flex items-center justify-center'):
                                                ui.label(str(day_num)).classes('text-white text-sm font-bold')
                                        else:
                                            if is_weekend:
                                                day_classes += ' text-gray-400'
                                            ui.label(str(day_num)).classes(day_classes)

                                        # Show holidays
                                        if has_holiday:
                                            holiday_list = holidays_by_date[current_date]
                                            holiday_names_map = {}
                                            for h in holiday_list:
                                                if h.name not in holiday_names_map:
                                                    holiday_names_map[h.name] = []
                                                holiday_names_map[h.name].append(h.market)

                                            def create_holiday_handler(d, h_list):
                                                return lambda: show_holiday_modal(d, h_list)

                                            for h_name, markets in holiday_names_map.items():
                                                tooltip_text = f"{h_name} ({', '.join(markets)}) - Click for details"
                                                holiday_el = ui.element('div').classes(
                                                    'text-xs bg-red-200 text-red-800 px-1 rounded mt-1 truncate cursor-pointer hover:bg-red-300'
                                                ).tooltip(tooltip_text)
                                                holiday_el.on('click', create_holiday_handler(current_date, holiday_list))
                                                with holiday_el:
                                                    ui.label(h_name[:15] + ('...' if len(h_name) > 15 else '')).classes('text-xs')

                                        # Show PTO entries
                                        if has_pto:
                                            pto_entries = pto_by_date[current_date]

                                            def create_pto_handler(req_id):
                                                return lambda e: (e.stop_propagation(), show_pto_detail_modal(req_id))

                                            for pto_entry in pto_entries[:3]:
                                                color_class = get_pto_color(pto_entry['type'])
                                                tooltip_text = f"{pto_entry['full_name']} - {pto_entry['type'].title()} - Click for details"
                                                pto_el = ui.element('div').classes(
                                                    f'text-xs {color_class} px-1 rounded mt-1 truncate border cursor-pointer hover:opacity-80'
                                                ).tooltip(tooltip_text)
                                                pto_el.on('click', create_pto_handler(pto_entry['request_id']))
                                                with pto_el:
                                                    ui.label(f"{pto_entry['initials']} {pto_entry['type'][:3].upper()}").classes('text-xs')

                                            if len(pto_entries) > 3:
                                                extra_count = len(pto_entries) - 3

                                                def create_more_handler(d, entries):
                                                    return lambda e: (e.stop_propagation(), show_all_pto_modal(d, entries))

                                                more_el = ui.element('div').classes(
                                                    'text-xs text-gray-500 mt-1 cursor-pointer hover:text-blue-600 hover:underline'
                                                )
                                                more_el.on('click', create_more_handler(current_date, pto_entries))
                                                with more_el:
                                                    ui.label(f'+{extra_count} more')

        # Initial render
        render_current_view()
