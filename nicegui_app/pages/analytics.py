"""Analytics Dashboard page for PTO insights and trends."""
from nicegui import ui, app
from src.database import get_db
from src.services.analytics_service import AnalyticsService
from src.services.department_service import DepartmentService
from src.services.export_service import ExportService
from datetime import date, timedelta
import base64
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_error_dialog, show_success_dialog, PTO_GOLD
from nicegui_app.components.charts import (
    monthly_trend_chart,
    department_utilization_bars,
    day_of_week_pattern
)


def show_help_tip(title: str, message: str):
    """Show a help tip dialog with OK button."""
    with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px;'):
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('help', color='amber', size='md')
            ui.label(title).classes('text-lg font-bold')
        ui.label(message).classes('text-sm opacity-80')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('OK', on_click=dialog.close).style(f'background-color: {PTO_GOLD} !important; color: white !important;')
    dialog.open()


def analytics_page():
    """Analytics dashboard with PTO trends and insights."""

    apply_dark_mode()

    # Check if user is logged in and has access
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')
    if user_role not in ['manager', 'admin', 'superadmin']:
        show_error_dialog('Access Denied', 'Manager or higher role is required to access analytics.')
        ui.navigate.to('/dashboard')
        return

    # Manager and Admin are restricted to their department; only SuperAdmin sees all
    is_department_restricted = user_role in ['manager', 'admin']
    is_superadmin = user_role == 'superadmin'

    # Get user's department if applicable (for manager/admin)
    # Also load all departments for superadmin dropdown
    user_department_id = None
    user_department_name = None
    all_departments = []

    db = next(get_db())
    try:
        from src.services.user_service import UserService
        from src.models.department import Department

        if is_department_restricted:
            user_service = UserService(db)
            current_user = user_service.get_user_by_id(user_id)
            if current_user and current_user.department_id:
                user_department_id = current_user.department_id
                dept = db.query(Department).filter(Department.id == user_department_id).first()
                if dept:
                    user_department_name = dept.name

        # Load all departments for superadmin filter
        if is_superadmin:
            all_departments = db.query(Department).order_by(Department.name).all()
    finally:
        db.close()

    # Keep backward compatibility with existing variable names
    is_manager_only = is_department_restricted
    manager_department_id = user_department_id
    manager_department_name = user_department_name

    # Superadmin department filter state - default to Technology department
    default_dept_id = None
    for dept in all_departments:
        if 'technology' in dept.name.lower():
            default_dept_id = dept.id
            break
    selected_department = {'value': default_dept_id}

    # State
    current_year = date.today().year
    selected_year = {'value': current_year}

    def get_dept_filter():
        """Get current department filter based on user role."""
        if is_manager_only:
            return manager_department_id
        elif is_superadmin:
            return selected_department['value']  # None = all departments
        return None

    active_tab = {'value': 'overview'}

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 animate-fade-in'):
        # Show department scope for managers
        if is_manager_only and manager_department_name:
            page_header(title=f'ANALYTICS - {manager_department_name.upper()}', show_back=False)
        else:
            page_header(title='WORKFORCE ANALYTICS', show_back=False)

        # Controls row
        with ui.row().classes('w-full items-center justify-between mb-6'):
            # Tab buttons for different views
            with ui.row().classes('gap-2 items-center'):
                overview_btn = ui.button('Overview', icon='dashboard')
                trends_btn = ui.button('Trends', icon='trending_up')
                insights_btn = ui.button('Insights', icon='lightbulb')
                ui.button(icon='help_outline', on_click=lambda: show_help_tip(
                    'Analytics Dashboard',
                    'Overview: Key metrics at a glance - total days used, pending requests, utilization rates, and leave type breakdown.\n\n'
                    'Trends: Monthly PTO usage charts showing patterns throughout the year. See which months have highest/lowest usage.\n\n'
                    'Insights: Actionable intelligence - high utilization employees, unusual patterns, and department comparisons.'
                )).props('flat dense round size=sm').style('color: #f59e0b')

                def update_tab_button_styles():
                    """Update tab button styles based on active tab."""
                    tab = active_tab['value']
                    # Overview button
                    if tab == 'overview':
                        overview_btn.props(remove='flat outline')
                        overview_btn.props('color=primary unelevated')
                    else:
                        overview_btn.props(remove='color=primary unelevated')
                        overview_btn.props('flat')
                    # Trends button
                    if tab == 'trends':
                        trends_btn.props(remove='flat outline')
                        trends_btn.props('color=primary unelevated')
                    else:
                        trends_btn.props(remove='color=primary unelevated')
                        trends_btn.props('flat')
                    # Insights button
                    if tab == 'insights':
                        insights_btn.props(remove='flat outline')
                        insights_btn.props('color=primary unelevated')
                    else:
                        insights_btn.props(remove='color=primary unelevated')
                        insights_btn.props('flat')

                def set_tab(tab):
                    active_tab['value'] = tab
                    update_tab_button_styles()
                    refresh_dashboard()

                overview_btn.on('click', lambda: set_tab('overview'))
                trends_btn.on('click', lambda: set_tab('trends'))
                insights_btn.on('click', lambda: set_tab('insights'))

                # Set initial styles
                update_tab_button_styles()

            # Year selector, department filter (superadmin only), export, and refresh
            with ui.row().classes('items-center gap-4'):
                # Department filter for superadmins
                if is_superadmin and all_departments:
                    ui.label('Department:').classes('font-medium')
                    dept_options = {None: 'All Departments'}
                    for dept in all_departments:
                        dept_options[dept.id] = dept.name

                    def on_dept_change(e):
                        selected_department['value'] = e.value
                        refresh_dashboard()

                    ui.select(dept_options, value=selected_department['value'], on_change=on_dept_change).classes('w-48')

                ui.label('Year:').classes('font-medium')
                year_options = {y: str(y) for y in range(current_year - 2, current_year + 2)}

                def on_year_change(e):
                    selected_year['value'] = e.value
                    refresh_dashboard()

                ui.select(year_options, value=selected_year['value'], on_change=on_year_change).classes('w-32')

                async def export_pdf():
                    """Export analytics to PDF."""
                    db = next(get_db())
                    try:
                        analytics = AnalyticsService(db)
                        year = selected_year['value']
                        dept_filter = get_dept_filter()

                        overview = analytics.get_company_overview(year, department_id=dept_filter)
                        recommendations = analytics.generate_recommendations(year, department_id=dept_filter)
                        days_until_year_end = (date(year, 12, 31) - date.today()).days
                        carryover_risk = analytics.get_carryover_risk_employees(year, days_until_year_end, 50.0, department_id=dept_filter)
                        optimal_dates = analytics.get_optimal_meeting_dates(days_ahead=30, department_id=dept_filter)

                        pdf_bytes = ExportService.generate_analytics_pdf(
                            overview, recommendations, carryover_risk, optimal_dates
                        )

                        # Download using data URL
                        b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                        filename = f"analytics_report_{date.today().isoformat()}.pdf"
                        ui.download(pdf_bytes, filename)
                        show_success_dialog('Download Complete', 'PDF report downloaded')
                    except Exception as e:
                        show_error_dialog('Export Failed', f'Error exporting PDF: {str(e)}')
                    finally:
                        db.close()

                async def export_csv():
                    """Export carryover risk to CSV."""
                    db = next(get_db())
                    try:
                        analytics = AnalyticsService(db)
                        year = selected_year['value']
                        dept_filter = get_dept_filter()

                        days_until_year_end = (date(year, 12, 31) - date.today()).days
                        carryover_risk = analytics.get_carryover_risk_employees(year, days_until_year_end, 50.0, department_id=dept_filter)

                        csv_str = ExportService.generate_carryover_csv(carryover_risk)
                        filename = f"carryover_risk_{date.today().isoformat()}.csv"
                        ui.download(csv_str.encode('utf-8'), filename)
                        show_success_dialog('Download Complete', 'CSV report downloaded')
                    except Exception as e:
                        show_error_dialog('Export Failed', f'Error exporting CSV: {str(e)}')
                    finally:
                        db.close()

                ui.button('Export PDF', icon='picture_as_pdf', on_click=export_pdf).props('flat')
                ui.button('Export CSV', icon='table_chart', on_click=export_csv).props('flat')
                ui.button('Refresh', icon='refresh', on_click=lambda: refresh_dashboard()).props('flat')

        # Helper function for help dialogs
        def show_help_dialog(title: str, message: str):
            """Show a dark-themed help dialog with OK button."""
            with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px; max-width: 500px'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('help', color='amber', size='md')
                    ui.label(title).classes('text-lg font-bold')
                ui.label(message).classes('text-sm leading-relaxed mb-4')
                with ui.row().classes('w-full justify-end'):
                    ui.button('OK', on_click=dialog.close).props('color=primary')
            dialog.open()

        def help_button(title: str, message: str):
            """Create a gold help button that shows a dialog."""
            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(title, message)).props('flat dense round size=sm').style('color: #f59e0b')

        # Dashboard container
        dashboard_container = ui.column().classes('w-full gap-6')

        def refresh_dashboard():
            """Refresh all dashboard components."""
            dashboard_container.clear()
            year = selected_year['value']
            tab = active_tab['value']

            db = next(get_db())
            try:
                analytics = AnalyticsService(db)

                with dashboard_container:
                    # Get department filter using the helper function
                    dept_filter = get_dept_filter()

                    if tab == 'overview':
                        render_overview_tab(analytics, year, dept_filter, db, is_manager_only, manager_department_id)
                    elif tab == 'trends':
                        render_trends_tab(analytics, year, dept_filter)
                    elif tab == 'insights':
                        render_insights_tab(analytics, year, dept_filter, db, is_manager_only, manager_department_id)

            finally:
                db.close()

        def render_overview_tab(analytics, year, dept_filter, db, is_manager_only, manager_department_id):
            """Render the overview tab with key metrics."""
            # ===== ROW 1: Overview Cards (First Row) =====
            overview = analytics.get_company_overview(year, department_id=dept_filter)

            # KPI section header
            with ui.row().classes('items-center gap-2 mb-2'):
                ui.icon('dashboard', color='blue')
                ui.label('Key Metrics').classes('text-lg font-semibold')
                ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                    'Key Metrics',
                    'These cards show the main PTO statistics for the selected year: '
                    'Total Requests (how many were submitted), Approved/Pending/Denied (request status breakdown), '
                    'Days Taken (total PTO used), Avg Days/Employee (average per person), '
                    'Active Employees (current workforce), Approval Rate (% of requests approved).'
                )).props('flat dense round size=sm').style('color: #f59e0b')

            # KPI cards - full width, equal spacing edge to edge
            with ui.element('div').classes('w-full grid grid-cols-2 md:grid-cols-4 gap-4'):
                # Total Requests Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('How many time-off requests were submitted this year')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('description', size='lg', color='blue')
                        ui.label(str(overview['total_requests'])).classes('text-3xl font-bold')
                        ui.label('Total Requests').classes('text-sm opacity-70')

                # Approved Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Requests that managers said "yes" to')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('check_circle', size='lg', color='green')
                        ui.label(str(overview['approved'])).classes('text-3xl font-bold text-green-600')
                        ui.label('Approved').classes('text-sm opacity-70')

                # Pending Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Requests waiting for a manager to approve or deny')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('pending', size='lg', color='amber')
                        ui.label(str(overview['pending'])).classes('text-3xl font-bold text-amber-600')
                        ui.label('Pending').classes('text-sm opacity-70')

                # Denied Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Requests that managers said "no" to')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('cancel', size='lg', color='red')
                        ui.label(str(overview['denied'])).classes('text-3xl font-bold text-red-600')
                        ui.label('Denied').classes('text-sm opacity-70')

            # ===== ROW 2: Overview Cards (Second Row) =====
            with ui.element('div').classes('w-full grid grid-cols-2 md:grid-cols-4 gap-4 mt-4'):
                # Days Taken Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Total PTO days used by all employees combined')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('event_available', size='lg', color='purple')
                        ui.label(str(overview['total_days_taken'])).classes('text-3xl font-bold text-purple-600')
                        ui.label('Days Taken').classes('text-sm opacity-70')

                # Avg Per Employee Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('On average, how many days each person has taken off')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('person', size='lg', color='cyan')
                        ui.label(str(overview['avg_days_per_employee'])).classes('text-3xl font-bold')
                        ui.label('Avg Days/Employee').classes('text-sm opacity-70')

                # Active Employees Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Number of employees currently working at the company')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('groups', size='lg', color='indigo')
                        ui.label(str(overview['active_employees'])).classes('text-3xl font-bold text-indigo-600')
                        ui.label('Active Employees').classes('text-sm opacity-70')

                # Approval Rate Card
                with ui.card().classes('p-4 shadow-md'):
                    ui.tooltip('Percentage of requests that get approved (higher is better for employees)')
                    with ui.column().classes('items-center w-full'):
                        ui.icon('verified', size='lg', color='teal')
                        ui.label(f"{overview['approval_rate']}%").classes('text-3xl font-bold text-teal-600')
                        ui.label('Approval Rate').classes('text-sm opacity-70')

            # ===== ROW 3: Attendance Heatmap & Leave Type Breakdown =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-5 gap-4 mt-4'):
                # Attendance Heatmap - with modern multi-view toggle
                with ui.card().classes('lg:col-span-3 p-4 shadow-md'):
                    # View state - grid is default, also store data in state for closure
                    heatmap_state = {
                        'current': 'grid',
                        'data': analytics.get_attendance_by_date_range(
                            date.today() - timedelta(days=60),
                            date.today() + timedelta(days=14),
                            department_id=dept_filter
                        )
                    }

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('calendar_month', color='blue')
                            ui.label('Attendance Overview').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'Attendance Overview',
                                'This heatmap shows how many people are at work each day. '
                                'Green = high attendance (most people are in), Red = low attendance (many people are out). '
                                'Use the toggle buttons to switch between Grid view (GitHub-style) and Week Cards view. '
                                'Hover over any cell to see the exact date and attendance percentage.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons
                        with ui.button_group().props('flat dense'):
                            grid_btn = ui.button(icon='grid_view', on_click=lambda: switch_heatmap_view('grid')).props('flat dense color=primary')
                            with grid_btn:
                                ui.tooltip('GitHub-style Grid')
                            cards_btn = ui.button(icon='view_agenda', on_click=lambda: switch_heatmap_view('cards')).props('flat dense')
                            with cards_btn:
                                ui.tooltip('Week Cards')

                    # Content container
                    heatmap_content = ui.column().classes('w-full')

                    def switch_heatmap_view(view: str):
                        heatmap_state['current'] = view
                        grid_btn.props('color=primary' if view == 'grid' else '', remove='color' if view != 'grid' else '')
                        cards_btn.props('color=primary' if view == 'cards' else '', remove='color' if view != 'cards' else '')
                        render_heatmap_view()

                    def get_heatmap_color(pct: float) -> str:
                        """Get color based on attendance percentage."""
                        if pct >= 95:
                            return '#166534'  # dark green
                        elif pct >= 90:
                            return '#22c55e'  # green
                        elif pct >= 80:
                            return '#84cc16'  # lime
                        elif pct >= 70:
                            return '#eab308'  # yellow
                        else:
                            return '#ef4444'  # red

                    def render_grid_view():
                        """GitHub-style contribution grid - only shows dates with data."""
                        attendance_data = heatmap_state['data']
                        if not attendance_data:
                            ui.label('No attendance data available').classes('opacity-50')
                            return

                        # Build date lookup for weekdays only - only dates with actual data
                        weekday_data = [d for d in attendance_data if d['date'].weekday() < 5 and d['attendance_rate'] > 0]
                        date_lookup = {d['date']: d['attendance_rate'] for d in weekday_data}

                        if not weekday_data:
                            ui.label('No attendance data available').classes('opacity-50')
                            return

                        # Get date range - only from actual data, up to today
                        min_date = min(d['date'] for d in weekday_data)
                        max_date = min(max(d['date'] for d in weekday_data), date.today())

                        # Adjust to start of week (Monday)
                        days_since_monday = min_date.weekday()
                        week_start = min_date - timedelta(days=days_since_monday)

                        # Calculate weeks needed - only for actual data range
                        total_days = (max_date - week_start).days + 1
                        num_weeks = (total_days // 7) + 1

                        # Grid container with flexible layout
                        with ui.column().classes('w-full gap-2'):
                            # Month/week headers row
                            with ui.row().classes('w-full gap-2 pl-10'):
                                for week in range(min(num_weeks, 12)):
                                    week_date = week_start + timedelta(days=week * 7)
                                    if week % 4 == 0:
                                        ui.label(week_date.strftime('%b')).classes('text-xs opacity-50 flex-1 text-center')
                                    else:
                                        ui.element('div').classes('flex-1')

                            # Day rows (Mon-Fri) - horizontal layout
                            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
                            for day_idx, day_name in enumerate(day_names):
                                with ui.row().classes('w-full items-center gap-2'):
                                    # Day label
                                    ui.label(day_name).classes('text-xs opacity-60 w-8')

                                    # Week cells for this day
                                    for week in range(min(num_weeks, 12)):
                                        week_date = week_start + timedelta(days=week * 7)
                                        current_date = week_date + timedelta(days=day_idx)
                                        pct = date_lookup.get(current_date, 0)

                                        # Only show cells with data or within the data range
                                        if current_date > max_date or current_date > date.today():
                                            # Skip future dates entirely
                                            ui.element('div').classes('flex-1 h-8 min-w-8')
                                        elif pct > 0:
                                            bg_color = get_heatmap_color(pct)
                                            cell = ui.element('div').classes('flex-1 h-8 rounded cursor-pointer min-w-8').style(f'background-color: {bg_color}')
                                            with cell:
                                                ui.tooltip(f'{current_date.strftime("%b %d")}: {pct:.0f}%')
                                        else:
                                            # No data for this date - show subtle placeholder
                                            ui.element('div').classes('flex-1 h-8 rounded min-w-8').style('background-color: #374151; opacity: 0.3')

                        # Legend
                        with ui.row().classes('w-full justify-center gap-4 mt-4'):
                            ui.label('Less').classes('text-xs opacity-50')
                            for pct_range, color in [(95, '#166534'), (90, '#22c55e'), (80, '#84cc16'), (70, '#eab308'), (50, '#ef4444')]:
                                ui.element('div').classes('w-4 h-4 rounded-sm').style(f'background-color: {color}')
                            ui.label('More').classes('text-xs opacity-50')

                    def render_cards_view():
                        """Week summary cards with mini progress bars."""
                        attendance_data = heatmap_state['data']
                        if not attendance_data:
                            ui.label('No attendance data available').classes('opacity-50')
                            return

                        # Group by week
                        week_data = {}
                        for day in attendance_data:
                            if day['date'].weekday() >= 5:  # Skip weekends
                                continue
                            week_num = day['date'].isocalendar()[1]
                            year = day['date'].year

                            key = (year, week_num)
                            if key not in week_data:
                                week_data[key] = {'days': [], 'week_start': None}

                            week_data[key]['days'].append(day)
                            if week_data[key]['week_start'] is None or day['date'] < week_data[key]['week_start']:
                                week_data[key]['week_start'] = day['date'] - timedelta(days=day['date'].weekday())

                        # Sort by week and display
                        sorted_weeks = sorted(week_data.items(), key=lambda x: x[0], reverse=True)

                        with ui.element('div').classes('w-full max-h-80 overflow-y-auto'):
                            for (year, week_num), data in sorted_weeks[:8]:  # Show last 8 weeks
                                days = data['days']
                                avg_pct = sum(d['attendance_rate'] for d in days) / len(days) if days else 0
                                week_start = data['week_start']
                                week_end = week_start + timedelta(days=4)

                                # Card color based on average
                                if avg_pct >= 90:
                                    border_color = '#22c55e'
                                    bg_class = 'bg-green-900/10'
                                elif avg_pct >= 80:
                                    border_color = '#84cc16'
                                    bg_class = 'bg-lime-900/10'
                                else:
                                    border_color = '#eab308'
                                    bg_class = 'bg-amber-900/10'

                                with ui.card().classes(f'w-full p-3 mb-2 {bg_class}').style(f'border-left: 4px solid {border_color}'):
                                    with ui.row().classes('w-full items-center justify-between'):
                                        # Week label
                                        with ui.column().classes('gap-0'):
                                            ui.label(f'{week_start.strftime("%b %d")} - {week_end.strftime("%b %d")}').classes('font-medium')
                                            ui.label(f'Week {week_num}').classes('text-xs opacity-50')

                                        # Mini day bars
                                        with ui.row().classes('gap-1 items-end'):
                                            day_lookup = {d['date'].weekday(): d['attendance_rate'] for d in days}
                                            for dow in range(5):  # Mon-Fri
                                                pct = day_lookup.get(dow, 0)
                                                bar_height = max(8, pct / 100 * 40)
                                                color = get_heatmap_color(pct) if pct > 0 else '#374151'
                                                bar = ui.element('div').classes('w-3 rounded-t').style(f'height: {bar_height}px; background-color: {color}')
                                                with bar:
                                                    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][dow]
                                                    if pct > 0:
                                                        ui.tooltip(f'{day_name}: {pct:.0f}%')

                                        # Average badge
                                        with ui.element('div').classes('px-3 py-1 rounded-full').style(f'background-color: {border_color}'):
                                            ui.label(f'{avg_pct:.0f}%').classes('text-sm font-bold text-white')

                    def render_heatmap_view():
                        heatmap_content.clear()
                        with heatmap_content:
                            view = heatmap_state['current']
                            if view == 'grid':
                                render_grid_view()
                            else:
                                render_cards_view()

                    # Initial render
                    render_heatmap_view()

                # Leave Type Breakdown - Modern multi-view
                with ui.card().classes('lg:col-span-2 p-4 shadow-md'):
                    # View state - donut is default
                    leave_view_state = {'current': 'donut'}  # 'donut', 'bars'

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('pie_chart', color='purple')
                            ui.label('By Leave Type').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'By Leave Type',
                                'This chart shows the breakdown of time off by category: '
                                'Vacation (planned time off), Sick (illness), Personal (errands/appointments), WFH (work from home). '
                                'Toggle between Donut and Bar views. The center number shows total days taken across all types.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons
                        with ui.button_group().props('flat dense'):
                            donut_leave_btn = ui.button(icon='donut_large', on_click=lambda: switch_leave_view('donut')).props('flat dense color=primary')
                            with donut_leave_btn:
                                ui.tooltip('Donut Chart')
                            bars_leave_btn = ui.button(icon='bar_chart', on_click=lambda: switch_leave_view('bars')).props('flat dense')
                            with bars_leave_btn:
                                ui.tooltip('Bar Chart')

                    type_data = analytics.get_leave_type_breakdown(year, department_id=dept_filter)

                    # Content container
                    leave_content = ui.column().classes('w-full')

                    def switch_leave_view(view: str):
                        leave_view_state['current'] = view
                        donut_leave_btn.props('color=primary' if view == 'donut' else '', remove='color' if view != 'donut' else '')
                        bars_leave_btn.props('color=primary' if view == 'bars' else '', remove='color' if view != 'bars' else '')
                        render_leave_view()

                    # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                    leave_colors = {
                        'vacation': '#3b82f6',
                        'sick': '#22c55e',
                        'personal': '#a855f7',
                        'wfh': '#ef4444',
                        'work_from_home': '#ef4444'
                    }

                    def render_leave_donut():
                        """Render multi-segment donut chart."""
                        if not type_data:
                            ui.label('No data available').classes('opacity-50 text-center')
                            return

                        total_days = sum(item['days'] for item in type_data)
                        if total_days == 0:
                            ui.label('No leave data for this period').classes('opacity-50 text-center')
                            return

                        # SVG donut chart
                        size = 160
                        stroke_width = 24
                        radius = (size - stroke_width) / 2
                        circumference = 2 * 3.14159 * radius
                        center = size / 2

                        # Build segments
                        segments = []
                        current_offset = 0
                        for item in type_data:
                            pct = item['days'] / total_days if total_days > 0 else 0
                            dash_length = pct * circumference
                            color = leave_colors.get(item['type'].lower(), '#6b7280')
                            segments.append({
                                'color': color,
                                'dash': dash_length,
                                'gap': circumference - dash_length,
                                'offset': current_offset,
                                'type': item['type'],
                                'days': item['days'],
                                'pct': pct * 100
                            })
                            current_offset += dash_length

                        # Build SVG circles for each segment
                        circles_svg = ''
                        for seg in segments:
                            circles_svg += f'''
                            <circle cx="{center}" cy="{center}" r="{radius}"
                                fill="none" stroke="{seg['color']}" stroke-width="{stroke_width}"
                                stroke-dasharray="{seg['dash']} {seg['gap']}"
                                stroke-dashoffset="-{seg['offset']}"
                                transform="rotate(-90 {center} {center})"/>
                            '''

                        svg = f'''
                        <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
                            <!-- Background circle -->
                            <circle cx="{center}" cy="{center}" r="{radius}"
                                fill="none" stroke="#374151" stroke-width="{stroke_width}"/>
                            {circles_svg}
                            <!-- Center text -->
                            <text x="{center}" y="{center - 5}" text-anchor="middle"
                                fill="#e5e7eb" font-size="24" font-weight="bold">{total_days}</text>
                            <text x="{center}" y="{center + 15}" text-anchor="middle"
                                fill="#e5e7eb" font-size="11" opacity="0.8">days</text>
                        </svg>
                        '''

                        with ui.row().classes('w-full items-center justify-center gap-6'):
                            # Donut chart
                            ui.html(svg, sanitize=False)

                            # Legend
                            with ui.column().classes('gap-2'):
                                for item in type_data:
                                    color = leave_colors.get(item['type'].lower(), '#6b7280')
                                    pct = (item['days'] / total_days * 100) if total_days > 0 else 0
                                    # Short label for WFH and Leave
                                    type_lower = item['type'].lower()
                                    if type_lower in ('work_from_home', 'wfh'):
                                        label = 'WFH'
                                    elif type_lower in ('chicago_leave', 'leave'):
                                        label = 'Leave'
                                    else:
                                        label = item['type'].replace('_', ' ').title()
                                    with ui.row().classes('items-center gap-2'):
                                        ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                        ui.label(label).classes('text-sm w-20')
                                        ui.label(f"{item['days']}d").classes('text-sm font-bold')
                                        ui.label(f"({pct:.0f}%)").classes('text-xs opacity-60')

                    def get_leave_label(leave_type: str) -> str:
                        """Get display label for leave type."""
                        lower = leave_type.lower()
                        if lower in ('work_from_home', 'wfh'):
                            return 'WFH'
                        if lower in ('chicago_leave', 'leave'):
                            return 'Leave'
                        return leave_type.replace('_', ' ').title()

                    def render_leave_bars():
                        """Render horizontal bar breakdown."""
                        if not type_data:
                            ui.label('No data available').classes('opacity-50 text-center')
                            return

                        total_days = sum(item['days'] for item in type_data)
                        max_days = max(item['days'] for item in type_data) if type_data else 1

                        with ui.column().classes('w-full gap-4'):
                            for item in type_data:
                                color = leave_colors.get(item['type'].lower(), '#6b7280')
                                pct = (item['days'] / max_days * 100) if max_days > 0 else 0
                                total_pct = (item['days'] / total_days * 100) if total_days > 0 else 0

                                with ui.row().classes('w-full items-center gap-3'):
                                    # Type label with color
                                    with ui.row().classes('w-28 items-center gap-2'):
                                        ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                        ui.label(get_leave_label(item['type'])).classes('text-sm font-medium')

                                    # Progress bar
                                    with ui.element('div').classes('flex-1 h-8 rounded relative').style('background-color: #374151'):
                                        ui.element('div').classes('h-full rounded').style(f'width: {pct}%; background-color: {color}')
                                        # Label inside
                                        with ui.element('div').classes('absolute inset-0 flex items-center justify-end pr-3'):
                                            ui.label(f'{item["days"]} days ({total_pct:.0f}%)').classes('text-xs font-bold text-white')

                            # Total
                            with ui.row().classes('w-full justify-between pt-3 mt-2').style('border-top: 1px solid #374151'):
                                ui.label('Total').classes('font-semibold')
                                ui.label(f'{total_days} days').classes('font-bold')

                    def render_leave_view():
                        leave_content.clear()
                        with leave_content:
                            view = leave_view_state['current']
                            if view == 'donut':
                                render_leave_donut()
                            else:
                                render_leave_bars()

                    # Initial render
                    render_leave_view()

            # ===== ROW 4: Optimal Meeting Dates & Utilization =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4'):
                # Optimal Meeting Dates - with view toggle
                with ui.card().classes('p-4 shadow-md'):
                    # View state
                    meeting_view_state = {'current': 'calendar'}  # 'calendar', 'list', 'timeline'

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('event', color='green')
                            ui.label('Best Days for All-Hands').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'Best Days for All-Hands',
                                'This shows upcoming days when most people will be in the office - perfect for scheduling team meetings! '
                                'Green dates have 90%+ attendance expected. Toggle between Calendar, List, and Timeline views. '
                                'Stars indicate the very best days for scheduling important meetings.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons
                        with ui.button_group().props('flat dense'):
                            calendar_btn = ui.button(icon='calendar_view_month', on_click=lambda: switch_meeting_view('calendar')).props('flat dense color=primary')
                            with calendar_btn:
                                ui.tooltip('Calendar View')
                            list_btn = ui.button(icon='view_list', on_click=lambda: switch_meeting_view('list')).props('flat dense')
                            with list_btn:
                                ui.tooltip('List View')
                            timeline_btn = ui.button(icon='view_timeline', on_click=lambda: switch_meeting_view('timeline')).props('flat dense')
                            with timeline_btn:
                                ui.tooltip('Timeline View')

                    # Get attendance data for all 30 days
                    attendance_data = analytics.get_attendance_by_date_range(
                        date.today(),
                        date.today() + timedelta(days=30),
                        department_id=dept_filter
                    )

                    optimal_dates = analytics.get_optimal_meeting_dates(
                        days_ahead=30,
                        min_attendance_pct=80,
                        max_results=10,
                        department_id=dept_filter
                    )

                    # Content container
                    meeting_content = ui.column().classes('w-full')

                    def switch_meeting_view(view: str):
                        meeting_view_state['current'] = view
                        # Update button styles
                        calendar_btn.props('color=primary' if view == 'calendar' else '', remove='color' if view != 'calendar' else '')
                        list_btn.props('color=primary' if view == 'list' else '', remove='color' if view != 'list' else '')
                        timeline_btn.props('color=primary' if view == 'timeline' else '', remove='color' if view != 'timeline' else '')
                        render_meeting_view()

                    def get_attendance_color(pct: float) -> str:
                        """Get background color based on attendance percentage."""
                        if pct >= 95:
                            return '#166534'  # dark green
                        elif pct >= 90:
                            return '#22c55e'  # green
                        elif pct >= 80:
                            return '#84cc16'  # lime
                        elif pct >= 70:
                            return '#eab308'  # yellow
                        else:
                            return '#6b7280'  # gray

                    def render_calendar_view():
                        """Render mini calendar heat map (weekdays only)."""
                        # Build date lookup
                        date_lookup = {d['date']: d['attendance_rate'] for d in attendance_data}

                        # Create calendar starting from today, weekdays only
                        start_date = date.today()
                        # Adjust to start of week (Monday)
                        days_since_monday = start_date.weekday()
                        week_start = start_date - timedelta(days=days_since_monday)

                        # Day headers - weekdays only
                        with ui.row().classes('w-full justify-between mb-1'):
                            for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
                                ui.label(day).classes('text-xs opacity-50 w-12 text-center')

                        # Calendar weeks - weekdays only (5 days per row)
                        for week in range(6):  # 6 weeks to cover ~30 days
                            with ui.row().classes('w-full justify-between gap-1 mb-1'):
                                for day_offset in range(5):  # Mon-Fri only
                                    current_date = week_start + timedelta(days=week * 7 + day_offset)
                                    pct = date_lookup.get(current_date, 0)
                                    is_past = current_date < date.today()

                                    # Determine cell styling
                                    if is_past:
                                        bg_color = '#374151'  # dark gray for past
                                        opacity = '0.3'
                                    else:
                                        bg_color = get_attendance_color(pct)
                                        opacity = '1'

                                    with ui.element('div').classes('w-12 h-10 rounded flex flex-col items-center justify-center cursor-pointer').style(f'background-color: {bg_color}; opacity: {opacity}'):
                                        ui.label(str(current_date.day)).classes('text-xs font-bold text-white')
                                        if not is_past and pct > 0:
                                            ui.label(f'{pct:.0f}%').classes('text-[8px] text-white opacity-80')

                        # Legend
                        with ui.row().classes('w-full justify-center gap-3 mt-3'):
                            for label, color in [('95%+', '#166534'), ('90%+', '#22c55e'), ('80%+', '#84cc16'), ('<80%', '#eab308')]:
                                with ui.row().classes('items-center gap-1'):
                                    ui.element('div').classes('w-3 h-3 rounded').style(f'background-color: {color}')
                                    ui.label(label).classes('text-xs opacity-60')

                    def render_list_view():
                        """Render expanded card-based list view filling available space."""
                        if optimal_dates:
                            # Use a 2-column grid to show more dates (no scroll)
                            with ui.element('div').classes('w-full grid grid-cols-2 gap-2'):
                                for meeting in optimal_dates[:8]:  # Show up to 8 dates (4 rows)
                                    pct = meeting['expected_attendance']
                                    # Color based on attendance
                                    if pct >= 95:
                                        border_color = '#166534'
                                        bg_class = 'bg-green-900/30'
                                    elif pct >= 90:
                                        border_color = '#22c55e'
                                        bg_class = 'bg-green-900/20'
                                    else:
                                        border_color = '#84cc16'
                                        bg_class = 'bg-lime-900/20'

                                    with ui.card().classes(f'{bg_class} p-3').style(f'border-left: 3px solid {border_color}'):
                                        with ui.row().classes('items-center justify-between gap-2'):
                                            with ui.column().classes('gap-0 flex-1'):
                                                ui.label(meeting['date_str']).classes('font-bold text-sm')
                                                ui.label(meeting['day_of_week']).classes('text-xs opacity-70')
                                            with ui.element('div').classes('px-2 py-1 rounded').style(f'background-color: {border_color}'):
                                                ui.label(f"{pct:.0f}%").classes('text-sm font-bold text-white')
                        else:
                            ui.label('No optimal dates found (attendance threshold: 80%)').classes('opacity-50')

                    def render_timeline_view():
                        """Render horizontal progress bar timeline."""
                        # Sort by date and show next 8 weekdays
                        weekday_data = [d for d in attendance_data if d['date'].weekday() < 5][:8]
                        best_dates = {d['date'] for d in optimal_dates[:3]} if optimal_dates else set()

                        if weekday_data:
                            for day in weekday_data:
                                pct = day['attendance_rate']
                                is_best = day['date'] in best_dates
                                bar_color = '#22c55e' if pct >= 90 else '#84cc16' if pct >= 80 else '#eab308' if pct >= 70 else '#6b7280'

                                with ui.row().classes('w-full items-center gap-2 mb-2'):
                                    # Date label
                                    with ui.column().classes('w-20 gap-0'):
                                        ui.label(day['date'].strftime('%a %d')).classes('text-xs font-medium')
                                        ui.label(day['date'].strftime('%b')).classes('text-[10px] opacity-50')

                                    # Progress bar
                                    with ui.element('div').classes('flex-1 h-6 rounded relative').style('background-color: #374151'):
                                        ui.element('div').classes('h-full rounded').style(f'width: {pct}%; background-color: {bar_color}')
                                        # Percentage label inside bar
                                        with ui.element('div').classes('absolute inset-0 flex items-center justify-end pr-2'):
                                            ui.label(f'{pct:.0f}%').classes('text-xs font-bold text-white')

                                    # Star for best dates
                                    if is_best:
                                        ui.icon('star', color='amber', size='sm')
                                    else:
                                        ui.element('div').classes('w-5')  # spacer
                        else:
                            ui.label('No data available').classes('opacity-50')

                    def render_meeting_view():
                        meeting_content.clear()
                        with meeting_content:
                            view = meeting_view_state['current']
                            if view == 'calendar':
                                render_calendar_view()
                            elif view == 'list':
                                render_list_view()
                            else:
                                render_timeline_view()

                    # Initial render
                    render_meeting_view()

                # PTO Utilization - with view toggle
                with ui.card().classes('p-4 shadow-md'):
                    # View state - donut is default
                    util_view_state = {'current': 'donut'}  # 'donut', 'gauge', 'breakdown'

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('speed', color='green')
                            ui.label('PTO Utilization').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'PTO Utilization',
                                'Shows what percentage of allocated PTO has been used. Higher % means employees are taking their breaks! '
                                'Green (80%+) = healthy usage, Yellow (50-80%) = moderate, Red (<50%) = low usage (burnout risk). '
                                'Toggle between Donut, Gauge, and Type Breakdown views.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons - donut first as default
                        with ui.button_group().props('flat dense'):
                            donut_btn = ui.button(icon='donut_large', on_click=lambda: switch_util_view('donut')).props('flat dense color=primary')
                            with donut_btn:
                                ui.tooltip('Donut Chart')
                            gauge_btn = ui.button(icon='speed', on_click=lambda: switch_util_view('gauge')).props('flat dense')
                            with gauge_btn:
                                ui.tooltip('Gauge View')
                            breakdown_btn = ui.button(icon='bar_chart', on_click=lambda: switch_util_view('breakdown')).props('flat dense')
                            with breakdown_btn:
                                ui.tooltip('Type Breakdown')

                    utilization = analytics.get_utilization_rate(year, department_id=dept_filter)
                    type_breakdown = analytics.get_leave_type_breakdown(year, department_id=dept_filter)

                    # Content container
                    util_content = ui.column().classes('w-full')

                    def switch_util_view(view: str):
                        util_view_state['current'] = view
                        # Update button styles
                        gauge_btn.props('color=primary' if view == 'gauge' else '', remove='color' if view != 'gauge' else '')
                        donut_btn.props('color=primary' if view == 'donut' else '', remove='color' if view != 'donut' else '')
                        breakdown_btn.props('color=primary' if view == 'breakdown' else '', remove='color' if view != 'breakdown' else '')
                        render_util_view()

                    def render_gauge_view():
                        """Render original gauge with progress bar."""
                        rate = round(utilization['utilization_rate'])
                        with ui.column().classes('items-center w-full'):
                            ui.label(f"{rate}%").classes('text-5xl font-bold')
                            ui.label('of allocated PTO used').classes('text-sm opacity-70 mb-4')

                            with ui.linear_progress(value=rate / 100).classes('w-full'):
                                pass

                            with ui.row().classes('w-full justify-between text-xs opacity-60 mt-2'):
                                ui.label(f"Used: {utilization['total_used_days']} days")
                                ui.label(f"Allocated: {utilization['total_allocated_days']} days")

                            # PTO Type Legend with values
                            # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                            type_colors = {'vacation': '#3b82f6', 'sick': '#22c55e', 'personal': '#a855f7', 'wfh': '#ef4444', 'work_from_home': '#ef4444'}
                            type_days = {item['type'].lower(): item['days'] for item in type_breakdown} if type_breakdown else {}
                            with ui.row().classes('w-full justify-center gap-4 mt-4'):
                                for type_name, color in [('vacation', '#3b82f6'), ('sick', '#22c55e'), ('personal', '#a855f7')]:
                                    days = type_days.get(type_name, 0)
                                    with ui.row().classes('items-center gap-1'):
                                        ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                        ui.label(f'{type_name.title()}: {days}d').classes('text-xs')

                    def render_donut_view():
                        """Render donut/arc chart visualization."""
                        rate = round(utilization['utilization_rate'])
                        used = utilization['total_used_days']
                        allocated = utilization['total_allocated_days']
                        remaining = allocated - used

                        with ui.column().classes('items-center w-full'):
                            # SVG donut chart
                            size = 180
                            stroke_width = 20
                            radius = (size - stroke_width) / 2
                            circumference = 2 * 3.14159 * radius
                            used_dash = (rate / 100) * circumference
                            remaining_dash = circumference - used_dash

                            # Color based on utilization
                            if rate >= 80:
                                used_color = '#22c55e'  # green - healthy usage
                            elif rate >= 50:
                                used_color = '#eab308'  # yellow - moderate
                            else:
                                used_color = '#ef4444'  # red - low usage

                            # Text color that works in both light and dark modes
                            text_color = '#e5e7eb'  # light gray for visibility

                            svg = f'''
                            <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
                                <!-- Background circle -->
                                <circle cx="{size/2}" cy="{size/2}" r="{radius}"
                                    fill="none" stroke="#374151" stroke-width="{stroke_width}"/>
                                <!-- Used portion -->
                                <circle cx="{size/2}" cy="{size/2}" r="{radius}"
                                    fill="none" stroke="{used_color}" stroke-width="{stroke_width}"
                                    stroke-dasharray="{used_dash} {remaining_dash}"
                                    stroke-linecap="round"
                                    transform="rotate(-90 {size/2} {size/2})"/>
                                <!-- Center text -->
                                <text x="{size/2}" y="{size/2 - 5}" text-anchor="middle"
                                    fill="{text_color}" font-size="32" font-weight="bold">{rate}%</text>
                                <text x="{size/2}" y="{size/2 + 20}" text-anchor="middle"
                                    fill="{text_color}" font-size="14" opacity="0.8">used</text>
                            </svg>
                            '''
                            ui.html(svg, sanitize=False)

                            # Legend - Used/Remaining
                            with ui.row().classes('w-full justify-center gap-6 mt-4'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {used_color}')
                                    ui.label(f'Used: {used} days').classes('text-sm')
                                with ui.row().classes('items-center gap-2'):
                                    ui.element('div').classes('w-3 h-3 rounded-full').style('background-color: #374151')
                                    ui.label(f'Remaining: {remaining} days').classes('text-sm')

                            # PTO Type breakdown legend
                            # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                            type_days = {item['type'].lower(): item['days'] for item in type_breakdown} if type_breakdown else {}
                            with ui.row().classes('w-full justify-center gap-4 mt-2'):
                                for type_name, color in [('vacation', '#3b82f6'), ('sick', '#22c55e'), ('personal', '#a855f7')]:
                                    days = type_days.get(type_name, 0)
                                    with ui.row().classes('items-center gap-1'):
                                        ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                        ui.label(f'{type_name.title()}: {days}d').classes('text-xs')

                    def render_breakdown_view():
                        """Render breakdown by leave type with bars."""
                        if type_breakdown:
                            total_days = sum(item['days'] for item in type_breakdown)
                            # Color code: Vacation=Blue, Sick=Green, Personal=Purple, WFH=Red
                            colors = {'vacation': '#3b82f6', 'sick': '#22c55e', 'personal': '#a855f7', 'wfh': '#ef4444'}

                            with ui.column().classes('w-full gap-3'):
                                for item in type_breakdown:
                                    leave_type = item['type'].lower()
                                    days = item['days']
                                    pct = (days / total_days * 100) if total_days > 0 else 0
                                    color = colors.get(leave_type, '#6b7280')

                                    with ui.row().classes('w-full items-center gap-3'):
                                        # Type label with color indicator
                                        with ui.row().classes('w-24 items-center gap-2'):
                                            ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                            # Use WFH for work_from_home, Leave for chicago_leave
                                            if leave_type in ('work_from_home', 'wfh'):
                                                label = 'WFH'
                                            elif leave_type in ('chicago_leave', 'leave'):
                                                label = 'Leave'
                                            else:
                                                label = item['type'].replace('_', ' ').title()
                                            ui.label(label).classes('text-sm font-medium')

                                        # Progress bar
                                        with ui.element('div').classes('flex-1 h-6 rounded relative').style('background-color: #374151'):
                                            ui.element('div').classes('h-full rounded').style(f'width: {pct}%; background-color: {color}')

                                        # Days count
                                        ui.label(f'{days} days').classes('w-16 text-right text-sm font-bold')

                                # Total summary
                                with ui.row().classes('w-full justify-between mt-3 pt-3').style('border-top: 1px solid #374151'):
                                    ui.label('Total Used').classes('font-semibold')
                                    ui.label(f"{utilization['total_used_days']} / {utilization['total_allocated_days']} days").classes('font-bold')
                        else:
                            ui.label('No PTO data available').classes('opacity-50 text-center')

                    def render_util_view():
                        util_content.clear()
                        with util_content:
                            view = util_view_state['current']
                            if view == 'gauge':
                                render_gauge_view()
                            elif view == 'donut':
                                render_donut_view()
                            else:
                                render_breakdown_view()

                    # Initial render
                    render_util_view()

        def render_trends_tab(analytics, year, dept_filter):
            """Render the trends tab with charts."""
            import calendar

            # ===== ROW 1: Monthly PTO by Type =====
            with ui.card().classes('w-full p-4 shadow-md'):
                # Header
                with ui.row().classes('items-center justify-between w-full mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('trending_up', color='blue')
                        ui.label(f'Monthly PTO Trends ({year})').classes('text-lg font-semibold')
                    ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                        'Monthly PTO Trends',
                        'This chart shows how many PTO days were taken each month, broken down by type (Vacation, Sick, Personal). '
                        'Look for seasonal patterns - summer months and holidays often show higher vacation usage, while sick days may spike in winter. '
                        'Click the colored legend items to show/hide each line. Click any data point to see its exact value.'
                    )).props('flat dense round size=sm').style('color: #f59e0b')

                monthly_by_type = analytics.get_monthly_pto_by_type(year, department_id=dept_filter)

                def render_lines_view():
                    """Render line chart for each PTO type - full year Jan-Dec with toggle."""
                    # Build full year data (Jan-Dec) with 0s for missing months
                    full_year_data = []
                    month_lookup = {m['month']: m for m in monthly_by_type} if monthly_by_type else {}
                    for month_num in range(1, 13):
                        if month_num in month_lookup:
                            full_year_data.append(month_lookup[month_num])
                        else:
                            full_year_data.append({'month': month_num, 'vacation_days': 0, 'sick_days': 0, 'personal_days': 0})

                    # Line visibility state
                    line_visibility = {'vacation': True, 'sick': True, 'personal': True}

                    # Calculate totals
                    total_vac = sum(m.get('vacation_days', 0) for m in full_year_data)
                    total_sick = sum(m.get('sick_days', 0) for m in full_year_data)
                    total_personal = sum(m.get('personal_days', 0) for m in full_year_data)

                    # Fixed max value for consistent scale - calculated once from ALL data
                    fixed_max_val = max(
                        1,
                        max(m.get('vacation_days', 0) for m in full_year_data) or 1,
                        max(m.get('sick_days', 0) for m in full_year_data) or 1,
                        max(m.get('personal_days', 0) for m in full_year_data) or 1
                    )

                    # Chart container
                    chart_container = ui.element('div').classes('w-full')

                    # Click info display
                    click_info_state = {'text': 'Click a data point to see value'}

                    def build_chart_svg():
                        """Build SVG with visible lines only."""
                        # Use fixed max value so scale never changes
                        max_val = fixed_max_val

                        # SVG dimensions - edge to edge
                        width = 900
                        height = 180
                        left_padding = 10
                        right_padding = 10
                        top_padding = 25
                        bottom_padding = 15

                        chart_width = width - left_padding - right_padding
                        chart_height = height - top_padding - bottom_padding
                        x_step = chart_width / 11

                        # Month labels at top
                        month_labels_svg = ''
                        for i in range(12):
                            x = left_padding + i * x_step
                            month_labels_svg += f'<text x="{x}" y="15" text-anchor="middle" fill="#9ca3af" font-size="11">{calendar.month_abbr[i+1]}</text>'

                        def build_line(data_key: str, color: str, type_name: str):
                            values = [m.get(data_key, 0) for m in full_year_data]
                            points = []
                            dots = ''
                            for i, val in enumerate(values):
                                x = left_padding + i * x_step
                                y = top_padding + chart_height - (val / max_val * chart_height) if max_val > 0 else top_padding + chart_height
                                points.append(f'{x},{y}')
                                # Larger circles with hover effect and click handler
                                dots += f'''<circle cx="{x}" cy="{y}" r="6" fill="{color}"
                                    style="cursor: pointer; transition: r 0.2s, stroke-width 0.2s;"
                                    onmouseover="this.setAttribute('r', '9'); this.setAttribute('stroke', 'white'); this.setAttribute('stroke-width', '2');"
                                    onmouseout="this.setAttribute('r', '6'); this.setAttribute('stroke', 'none'); this.setAttribute('stroke-width', '0');"
                                    onclick="document.dispatchEvent(new CustomEvent('chart-point-click', {{detail: {{month: '{calendar.month_abbr[i+1]}', value: {val}, type: '{type_name}'}}}}));">
                                    <title>{calendar.month_abbr[i+1]}: {val} days ({type_name})</title>
                                </circle>'''
                            return f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>{dots}'

                        # Build visible lines
                        lines_svg = ''
                        if line_visibility['vacation']:
                            lines_svg += build_line('vacation_days', '#3b82f6', 'Vacation')
                        if line_visibility['sick']:
                            lines_svg += build_line('sick_days', '#22c55e', 'Sick')
                        if line_visibility['personal']:
                            lines_svg += build_line('personal_days', '#a855f7', 'Personal')

                        svg = f'''
                        <svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
                            {month_labels_svg}
                            {lines_svg}
                        </svg>
                        '''
                        return svg

                    def refresh_chart():
                        chart_container.clear()
                        with chart_container:
                            ui.html(build_chart_svg(), sanitize=False).classes('w-full')

                    def toggle_line(line_type: str):
                        line_visibility[line_type] = not line_visibility[line_type]
                        # Update button appearance
                        if line_type == 'vacation':
                            if line_visibility['vacation']:
                                vac_btn.style('opacity: 1')
                            else:
                                vac_btn.style('opacity: 0.4')
                        elif line_type == 'sick':
                            if line_visibility['sick']:
                                sick_btn.style('opacity: 1')
                            else:
                                sick_btn.style('opacity: 0.4')
                        elif line_type == 'personal':
                            if line_visibility['personal']:
                                personal_btn.style('opacity: 1')
                            else:
                                personal_btn.style('opacity: 0.4')
                        refresh_chart()

                    # Legend with clickable toggles
                    with ui.row().classes('w-full justify-center gap-6 mb-2'):
                        vac_btn = ui.element('div').classes('flex items-center gap-2 cursor-pointer px-3 py-1 rounded hover:bg-gray-700')
                        with vac_btn:
                            ui.element('div').classes('w-4 h-4 rounded-full').style('background-color: #3b82f6')
                            ui.label('Vacation').classes('text-sm font-medium')
                            ui.label(f'{total_vac}d').classes('text-sm font-bold text-blue-400')
                        vac_btn.on('click', lambda: toggle_line('vacation'))

                        sick_btn = ui.element('div').classes('flex items-center gap-2 cursor-pointer px-3 py-1 rounded hover:bg-gray-700')
                        with sick_btn:
                            ui.element('div').classes('w-4 h-4 rounded-full').style('background-color: #22c55e')
                            ui.label('Sick').classes('text-sm font-medium')
                            ui.label(f'{total_sick}d').classes('text-sm font-bold text-green-400')
                        sick_btn.on('click', lambda: toggle_line('sick'))

                        personal_btn = ui.element('div').classes('flex items-center gap-2 cursor-pointer px-3 py-1 rounded hover:bg-gray-700')
                        with personal_btn:
                            ui.element('div').classes('w-4 h-4 rounded-full').style('background-color: #a855f7')
                            ui.label('Personal').classes('text-sm font-medium')
                            ui.label(f'{total_personal}d').classes('text-sm font-bold text-purple-400')
                        personal_btn.on('click', lambda: toggle_line('personal'))

                    # Click info display
                    click_info_label = ui.label('Click a point to see details').classes('text-xs text-gray-400 text-center w-full')

                    # JavaScript to handle chart point clicks
                    ui.run_javascript('''
                        document.addEventListener('chart-point-click', function(e) {
                            const info = e.detail;
                            const colorMap = {'Vacation': '#3b82f6', 'Sick': '#22c55e', 'Personal': '#a855f7'};
                            const elem = document.querySelector('[data-click-info]');
                            if (elem) {
                                elem.textContent = info.month + ': ' + info.value + ' days (' + info.type + ')';
                                elem.style.color = colorMap[info.type] || '#9ca3af';
                                elem.style.fontWeight = 'bold';
                            }
                        });
                    ''')
                    click_info_label._props['data-click-info'] = 'true'

                    # Initial chart render
                    refresh_chart()

                # Render the line chart
                render_lines_view()

            # ===== ROW 2: Day of Week Pattern & Department Utilization =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-2 gap-4'):
                # Day of Week Pattern
                with ui.card().classes('p-4 shadow-md'):
                    # View state - horizontal is default
                    dow_view_state = {'current': 'horizontal'}

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('date_range', color='amber')
                            ui.label('PTO by Day of Week').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'PTO by Day of Week',
                                'This chart shows the AVERAGE number of PTO days taken on each weekday across the year. '
                                'For example, if Monday shows "2.5", it means on average 2.5 days of PTO were taken on Mondays each week. '
                                'Orange bars indicate "weekend extending" - when Monday or Friday have significantly higher PTO than mid-week days, '
                                'suggesting employees prefer long weekends.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons
                        with ui.button_group().props('flat dense'):
                            horiz_btn = ui.button(icon='align_horizontal_left', on_click=lambda: switch_dow_view('horizontal')).props('flat dense color=primary')
                            with horiz_btn:
                                ui.tooltip('Horizontal Bars')
                            vert_btn = ui.button(icon='bar_chart', on_click=lambda: switch_dow_view('vertical')).props('flat dense')
                            with vert_btn:
                                ui.tooltip('Vertical Bars')

                    dow_data = analytics.get_day_of_week_patterns(year, department_id=dept_filter)

                    # Content container
                    dow_content = ui.column().classes('w-full')

                    def switch_dow_view(view: str):
                        dow_view_state['current'] = view
                        horiz_btn.props('color=primary' if view == 'horizontal' else '', remove='color' if view != 'horizontal' else '')
                        vert_btn.props('color=primary' if view == 'vertical' else '', remove='color' if view != 'vertical' else '')
                        render_dow_view()

                    def render_horizontal_view():
                        """Render horizontal bars."""
                        if not dow_data:
                            ui.label('No data available').classes('opacity-50')
                            return

                        days = list(dow_data.keys())
                        values = list(dow_data.values())
                        max_val = max(values) if values else 1

                        # Detect Mon/Fri clustering
                        avg_mid_week = sum(values[1:4]) / 3 if len(values) >= 5 and sum(values[1:4]) > 0 else 1

                        with ui.column().classes('w-full gap-3'):
                            for i, (day, val) in enumerate(zip(days, values)):
                                # Highlight Mon/Fri if clustering
                                is_cluster = i in [0, 4] and val > avg_mid_week * 1.3
                                bar_color = '#f97316' if is_cluster else '#3b82f6'

                                with ui.row().classes('w-full items-center gap-2'):
                                    ui.label(day).classes('w-12 text-sm font-medium')
                                    with ui.element('div').classes('flex-1 h-8 rounded relative').style('background-color: #374151'):
                                        pct = (val / max_val * 100) if max_val > 0 else 0
                                        ui.element('div').classes('h-full rounded').style(f'width: {pct}%; background-color: {bar_color}')
                                    ui.label(f'{val:.1f}').classes('w-10 text-sm font-bold text-right')

                            # Clustering note
                            if len(values) >= 5:
                                mon_fri_avg = (values[0] + values[4]) / 2
                                if mon_fri_avg > avg_mid_week * 1.3:
                                    with ui.row().classes('items-center gap-2 mt-2'):
                                        ui.icon('info', size='xs', color='amber')
                                        ui.label('Monday/Friday clustering detected').classes('text-amber-500 text-xs')

                    def render_vertical_view():
                        """Render vertical bars."""
                        if not dow_data:
                            ui.label('No data available').classes('opacity-50')
                            return

                        days = list(dow_data.keys())
                        values = list(dow_data.values())
                        max_val = max(values) if values else 1

                        # Detect Mon/Fri clustering
                        avg_mid_week = sum(values[1:4]) / 3 if len(values) >= 5 and sum(values[1:4]) > 0 else 1

                        with ui.column().classes('w-full items-center'):
                            # Bars container
                            with ui.row().classes('w-full justify-around items-end gap-2').style('height: 150px'):
                                for i, (day, val) in enumerate(zip(days, values)):
                                    # Highlight Mon/Fri if clustering
                                    is_cluster = i in [0, 4] and val > avg_mid_week * 1.3
                                    bar_color = '#f97316' if is_cluster else '#3b82f6'
                                    bar_height = (val / max_val * 120) if max_val > 0 else 0

                                    with ui.column().classes('items-center gap-1'):
                                        ui.label(f'{val:.1f}').classes('text-xs font-bold')
                                        bar = ui.element('div').classes('w-12 rounded-t').style(f'height: {bar_height}px; background-color: {bar_color}')
                                        with bar:
                                            ui.tooltip(f'{day}: {val:.1f} days')

                            # Day labels
                            with ui.row().classes('w-full justify-around gap-2 mt-2'):
                                for day in days:
                                    ui.label(day).classes('w-12 text-center text-xs font-medium')

                            # Clustering note
                            if len(values) >= 5:
                                mon_fri_avg = (values[0] + values[4]) / 2
                                if mon_fri_avg > avg_mid_week * 1.3:
                                    with ui.row().classes('items-center gap-2 mt-4'):
                                        ui.icon('info', size='xs', color='amber')
                                        ui.label('Monday/Friday clustering detected').classes('text-amber-500 text-xs')

                    def render_dow_view():
                        dow_content.clear()
                        with dow_content:
                            if dow_view_state['current'] == 'horizontal':
                                render_horizontal_view()
                            else:
                                render_vertical_view()

                    # Initial render
                    render_dow_view()

                # Department Utilization
                with ui.card().classes('p-4 shadow-md'):
                    # View state - donut is default
                    dept_view_state = {'current': 'donut'}

                    # Header with view toggle
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('business', color='purple')
                            ui.label('Department Utilization Rates').classes('text-lg font-semibold')
                            ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                                'Department Utilization Rates',
                                'This chart shows the percentage of allocated PTO that each department has actually used. '
                                '70-90% is considered healthy - it means employees are taking their time off. '
                                'Below 50% (red) suggests burnout risk - people aren\'t taking enough breaks. '
                                'Above 90% (orange) may indicate coverage challenges.'
                            )).props('flat dense round size=sm').style('color: #f59e0b')

                        # View toggle buttons
                        with ui.button_group().props('flat dense'):
                            donut_btn = ui.button(icon='donut_large', on_click=lambda: switch_dept_view('donut')).props('flat dense color=primary')
                            with donut_btn:
                                ui.tooltip('Donut Chart')
                            bars_btn = ui.button(icon='bar_chart', on_click=lambda: switch_dept_view('bars')).props('flat dense')
                            with bars_btn:
                                ui.tooltip('Horizontal Bars')

                    all_dept_util = analytics.get_department_utilization_rates(year)
                    # Filter to selected department if one is selected
                    if dept_filter:
                        dept_util = [d for d in all_dept_util if d['department_id'] == dept_filter]
                    else:
                        dept_util = all_dept_util

                    # Content container
                    dept_content = ui.column().classes('w-full')

                    # Color palette for departments
                    dept_colors = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6', '#ef4444', '#06b6d4', '#eab308']

                    def switch_dept_view(view: str):
                        dept_view_state['current'] = view
                        donut_btn.props('color=primary' if view == 'donut' else '', remove='color' if view != 'donut' else '')
                        bars_btn.props('color=primary' if view == 'bars' else '', remove='color' if view != 'bars' else '')
                        render_dept_view()

                    def render_donut_view():
                        """Render donut chart."""
                        if not dept_util:
                            ui.label('No data available').classes('opacity-50')
                            return

                        total_util = sum(d.get('utilization_rate', 0) for d in dept_util)
                        if total_util == 0:
                            ui.label('No utilization data').classes('opacity-50')
                            return

                        size = 160
                        stroke_width = 20
                        radius = (size - stroke_width) / 2
                        circumference = 2 * 3.14159 * radius
                        center = size / 2

                        # Build segments
                        segments = []
                        current_offset = 0
                        for idx, d in enumerate(dept_util):
                            rate = d.get('utilization_rate', 0)
                            pct = rate / total_util if total_util > 0 else 0
                            dash_length = pct * circumference
                            color = dept_colors[idx % len(dept_colors)]
                            segments.append({
                                'name': d['department_name'],
                                'rate': rate,
                                'color': color,
                                'dash': dash_length,
                                'gap': circumference - dash_length,
                                'offset': current_offset
                            })
                            current_offset += dash_length

                        # Build SVG
                        circles_svg = ''
                        for seg in segments:
                            circles_svg += f'''
                            <circle cx="{center}" cy="{center}" r="{radius}"
                                fill="none" stroke="{seg['color']}" stroke-width="{stroke_width}"
                                stroke-dasharray="{seg['dash']} {seg['gap']}"
                                stroke-dashoffset="-{seg['offset']}"
                                transform="rotate(-90 {center} {center})"/>
                            '''

                        avg_util = total_util / len(dept_util) if dept_util else 0
                        svg = f'''
                        <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
                            <circle cx="{center}" cy="{center}" r="{radius}"
                                fill="none" stroke="#374151" stroke-width="{stroke_width}"/>
                            {circles_svg}
                            <text x="{center}" y="{center - 5}" text-anchor="middle"
                                fill="#e5e7eb" font-size="24" font-weight="bold">{avg_util:.0f}%</text>
                            <text x="{center}" y="{center + 15}" text-anchor="middle"
                                fill="#e5e7eb" font-size="10" opacity="0.8">avg util</text>
                        </svg>
                        '''

                        with ui.row().classes('w-full items-center justify-center gap-6'):
                            ui.html(svg, sanitize=False)

                            # Legend
                            with ui.column().classes('gap-1'):
                                for idx, d in enumerate(dept_util[:5]):  # Show top 5
                                    color = dept_colors[idx % len(dept_colors)]
                                    with ui.row().classes('items-center gap-2'):
                                        ui.element('div').classes('w-3 h-3 rounded-full').style(f'background-color: {color}')
                                        ui.label(d['department_name'][:12]).classes('text-xs w-20')
                                        ui.label(f"{d.get('utilization_rate', 0):.0f}%").classes('text-xs font-bold')

                    def render_bars_view():
                        """Render horizontal bars."""
                        if not dept_util:
                            ui.label('No data available').classes('opacity-50')
                            return

                        with ui.column().classes('w-full gap-2'):
                            for idx, d in enumerate(dept_util):
                                rate = d.get('utilization_rate', 0)
                                dept_name = d['department_name']
                                color = dept_colors[idx % len(dept_colors)]

                                # Color based on utilization health
                                if rate < 50:
                                    bar_color = '#ef4444'  # Red - too low
                                elif rate < 70:
                                    bar_color = '#eab308'  # Yellow - low
                                elif rate <= 90:
                                    bar_color = '#22c55e'  # Green - healthy
                                else:
                                    bar_color = '#f97316'  # Orange - high

                                with ui.row().classes('w-full items-center gap-2'):
                                    ui.label(dept_name[:10]).classes('w-20 text-xs font-medium truncate')
                                    with ui.element('div').classes('flex-1 h-6 rounded relative').style('background-color: #374151'):
                                        ui.element('div').classes('h-full rounded').style(f'width: {min(rate, 100)}%; background-color: {bar_color}')
                                    ui.label(f'{rate:.0f}%').classes('w-12 text-xs font-bold text-right')

                            # Target line note
                            with ui.row().classes('w-full justify-center items-center gap-2 mt-3 pt-2').style('border-top: 1px solid #374151'):
                                ui.element('div').classes('w-3 h-0.5').style('background-color: #22c55e')
                                ui.label('70-90% = Healthy utilization').classes('text-xs opacity-60')

                    def render_dept_view():
                        dept_content.clear()
                        with dept_content:
                            if dept_view_state['current'] == 'donut':
                                render_donut_view()
                            else:
                                render_bars_view()

                    # Initial render
                    render_dept_view()

            # ===== ROW 3: Department Comparison Table =====
            with ui.card().classes('w-full p-4 shadow-md'):
                with ui.row().classes('items-center justify-between w-full mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('compare', color='blue')
                        ui.label('Department Comparison').classes('text-lg font-semibold')
                    ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                        'Department Comparison',
                        'This table shows a side-by-side breakdown of PTO usage across all departments. '
                        'Columns explained: Employees = team size, Requests = number of PTO requests submitted, '
                        'Total Days = all PTO days taken by the department, Avg/Person = average days per employee. '
                        'Use this to identify teams that may need encouragement to take time off.'
                    )).props('flat dense round size=sm').style('color: #f59e0b')

                dept_data = analytics.get_department_comparison(year, department_id=dept_filter)

                if dept_data:
                    columns = [
                        {'name': 'department_name', 'label': 'Department', 'field': 'department_name', 'sortable': True},
                        {'name': 'employee_count', 'label': 'Employees', 'field': 'employee_count', 'sortable': True},
                        {'name': 'total_requests', 'label': 'Requests', 'field': 'total_requests', 'sortable': True},
                        {'name': 'total_days', 'label': 'Total Days', 'field': 'total_days', 'sortable': True},
                        {'name': 'avg_days_per_employee', 'label': 'Avg/Person', 'field': 'avg_days_per_employee', 'sortable': True},
                    ]
                    ui.table(columns=columns, rows=dept_data).classes('w-full')
                else:
                    ui.label('No department data available').classes('opacity-50')

            # ===== ROW 4: Top PTO Users =====
            with ui.card().classes('w-full p-4 shadow-md'):
                with ui.row().classes('items-center justify-between w-full mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('emoji_events', color='amber')
                        ui.label('Top PTO Users').classes('text-lg font-semibold')
                    ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                        'Top PTO Users',
                        'This section shows the employees who have taken the most PTO days this year. '
                        'This is not necessarily bad - it often means they\'re using their allocated time wisely! '
                        'The number shown is total days taken across all PTO types (vacation, sick, personal).'
                    )).props('flat dense round size=sm').style('color: #f59e0b')

                top_users = analytics.get_top_users_by_pto(year, limit=8, department_id=dept_filter)

                if top_users:
                    # Grid layout: 4 columns, stretches full width
                    with ui.element('div').classes('w-full grid grid-cols-2 md:grid-cols-4 gap-4'):
                        for idx, user_data in enumerate(top_users):
                            medal_color = 'amber' if idx == 0 else 'gray' if idx == 1 else 'orange' if idx == 2 else None

                            with ui.card().classes('p-3'):
                                with ui.row().classes('items-center gap-2'):
                                    if medal_color:
                                        ui.icon('emoji_events', size='sm', color=medal_color)
                                    else:
                                        ui.label(f'#{idx + 1}').classes('text-sm opacity-50 w-5')

                                    with ui.column().classes('gap-0 flex-1'):
                                        ui.label(user_data['name']).classes('font-medium truncate')
                                        ui.label(user_data['department']).classes('text-xs opacity-60')

                                ui.label(f"{user_data['days_taken']} days").classes('text-xl font-bold')
                else:
                    ui.label('No data available').classes('opacity-50')

        def render_insights_tab(analytics, year, dept_filter, db, is_manager_only, manager_department_id):
            """Render the insights tab with recommendations and risks."""
            # ===== Recommendations =====
            with ui.card().classes('w-full p-4 shadow-md'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('lightbulb', color='amber')
                    ui.label('Recommendations').classes('text-lg font-semibold')
                    ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                        'Recommendations',
                        'Smart, actionable tips based on your team\'s PTO data. '
                        'HIGH priority (red) = urgent issues needing immediate attention. '
                        'MEDIUM (yellow) = should address soon. LOW (blue) = good to know. '
                        'Examples: reminding employees to use vacation, flagging low utilization, etc.'
                    )).props('flat dense round size=sm').style('color: #f59e0b')

                recommendations = analytics.generate_recommendations(year, department_id=dept_filter)

                if recommendations:
                    # Sort: INFO/LOW (green) first, then MEDIUM (yellow), then HIGH (red)
                    priority_order = {'INFO': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
                    sorted_recs = sorted(recommendations, key=lambda r: priority_order.get(r['priority'], 4))

                    # Color schemes for each priority
                    color_styles = {
                        'HIGH': {'bg': '#7f1d1d', 'border': '#ef4444', 'badge': 'red'},
                        'MEDIUM': {'bg': '#78350f', 'border': '#f59e0b', 'badge': 'amber'},
                        'LOW': {'bg': '#1e3a5f', 'border': '#3b82f6', 'badge': 'blue'},
                        'INFO': {'bg': '#14532d', 'border': '#22c55e', 'badge': 'green'}
                    }

                    # Horizontal grid - edge to edge
                    num_recs = len(sorted_recs)
                    grid_cols = f'grid-cols-{min(num_recs, 3)}'

                    with ui.element('div').classes(f'w-full grid {grid_cols} gap-4'):
                        for rec in sorted_recs:
                            style = color_styles.get(rec['priority'], color_styles['INFO'])

                            with ui.card().classes('p-4 h-full').style(f"background-color: {style['bg']}; border-top: 4px solid {style['border']}"):
                                ui.label(rec['title']).classes('font-bold text-sm mb-1')
                                ui.badge(rec['priority'], color=style['badge'])
                                ui.label(f"Category: {rec['category']}").classes('text-xs opacity-70 mt-2')
                                ui.label(rec['action']).classes('text-sm mt-2')
                                if rec['affected']:
                                    ui.label(f"Affected: {', '.join(rec['affected'][:3])}{'...' if len(rec['affected']) > 3 else ''}").classes('text-xs opacity-60 mt-1')
                else:
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle', color='green')
                        ui.label('No recommendations at this time - everything looks good!').classes('text-green-600')

            # ===== Carryover Risk Analysis =====
            days_until_year_end = (date(year, 12, 31) - date.today()).days
            carryover_risk = analytics.get_carryover_risk_employees(
                year, days_until_year_end, 50.0, department_id=dept_filter
            )

            from src.models.user import User
            if dept_filter:
                emp_count = db.query(User).filter(User.is_active == True, User.department_id == dept_filter).count()
            else:
                emp_count = db.query(User).filter(User.is_active == True).count()

            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4'):
                # Carryover Risk Gauge - Custom SVG
                with ui.card().classes('p-4 shadow-md'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('warning', color='red')
                        ui.label('Carryover Risk').classes('text-lg font-semibold')
                        ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                            'Carryover Risk',
                            'This gauge shows how many employees have significant unused vacation that may be lost at year-end. '
                            'The red indicator shows employees at risk vs total workforce. '
                            'If many employees are at risk, consider encouraging them to schedule time off soon!'
                        )).props('flat dense round size=sm').style('color: #f59e0b')

                    # Custom SVG donut gauge
                    at_risk = len(carryover_risk)
                    total = emp_count if emp_count > 0 else 1
                    risk_pct = (at_risk / total) * 100

                    # Determine color based on risk level
                    if risk_pct <= 10:
                        gauge_color = '#22c55e'  # green - low risk
                    elif risk_pct <= 25:
                        gauge_color = '#eab308'  # yellow - moderate
                    else:
                        gauge_color = '#ef4444'  # red - high risk

                    size = 160
                    stroke_width = 20
                    radius = (size - stroke_width) / 2
                    circumference = 2 * 3.14159 * radius
                    risk_dash = (at_risk / total) * circumference if total > 0 else 0
                    remaining_dash = circumference - risk_dash

                    gauge_svg = f'''
                    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
                        <!-- Background circle -->
                        <circle cx="{size/2}" cy="{size/2}" r="{radius}"
                            fill="none" stroke="#374151" stroke-width="{stroke_width}"/>
                        <!-- Risk portion -->
                        <circle cx="{size/2}" cy="{size/2}" r="{radius}"
                            fill="none" stroke="{gauge_color}" stroke-width="{stroke_width}"
                            stroke-dasharray="{risk_dash} {remaining_dash}"
                            stroke-linecap="round"
                            transform="rotate(-90 {size/2} {size/2})"/>
                        <!-- Center text -->
                        <text x="{size/2}" y="{size/2 - 10}" text-anchor="middle"
                            fill="#e5e7eb" font-size="28" font-weight="bold">{at_risk} / {total}</text>
                        <text x="{size/2}" y="{size/2 + 15}" text-anchor="middle"
                            fill="#e5e7eb" font-size="12" opacity="0.8">at risk</text>
                    </svg>
                    '''

                    with ui.column().classes('items-center w-full'):
                        ui.html(gauge_svg, sanitize=False)
                        # Risk level indicator
                        risk_label = 'Low Risk' if risk_pct <= 10 else 'Moderate Risk' if risk_pct <= 25 else 'High Risk'
                        ui.label(risk_label).classes('text-sm mt-2').style(f'color: {gauge_color}')

                # Carryover Risk Table
                with ui.card().classes('lg:col-span-2 p-4 shadow-md'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('people', color='red')
                        ui.label('Employees at Carryover Risk').classes('text-lg font-semibold')
                        ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                            'Employees at Carryover Risk',
                            'This table lists employees with lots of unused vacation who may lose days at year-end. '
                            'Columns: Employee name, Department, Remaining days (unused), Total allocated, Risk Level. '
                            'Consider reaching out to these employees to encourage them to schedule time off.'
                        )).props('flat dense round size=sm').style('color: #f59e0b')

                    if carryover_risk:
                        columns = [
                            {'name': 'name', 'label': 'Employee', 'field': 'name'},
                            {'name': 'department', 'label': 'Department', 'field': 'department'},
                            {'name': 'vacation_remaining', 'label': 'Remaining', 'field': 'vacation_remaining'},
                            {'name': 'vacation_total', 'label': 'Total', 'field': 'vacation_total'},
                            {'name': 'risk_level', 'label': 'Risk', 'field': 'risk_level'},
                        ]
                        ui.table(columns=columns, rows=carryover_risk[:10]).classes('w-full')
                    else:
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('check_circle', color='green')
                            ui.label('No employees at carryover risk').classes('text-green-600')

            # ===== Coverage Forecast Chart =====
            with ui.card().classes('w-full p-4 shadow-md'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('timeline', color='blue')
                    ui.label('Coverage Forecast (Next 30 Days)').classes('text-lg font-semibold')
                    ui.button(icon='help_outline', on_click=lambda: show_help_dialog(
                        'Coverage Forecast',
                        'This timeline shows predicted staffing levels for the next 30 days based on approved PTO requests. '
                        'Green markers = good coverage (70%+), Red markers = low coverage (watch out!). '
                        'The 70% line indicates the minimum recommended staffing level. '
                        'Use this to plan ahead and avoid understaffing on critical days.'
                    )).props('flat dense round size=sm').style('color: #f59e0b')

                # Get coverage data for timeline chart
                # Default to Technology department, or use manager's department if restricted
                if is_manager_only and manager_department_id:
                    dept_id = manager_department_id
                else:
                    # Find Technology department as default
                    from src.models.department import Department
                    tech_dept = db.query(Department).filter(Department.name.ilike('%technology%')).first()
                    if tech_dept:
                        dept_id = tech_dept.id
                    else:
                        departments = DepartmentService.get_all_departments(db)
                        dept_id = departments[0].id if departments else None

                if dept_id:
                    from src.models.user import User
                    team_size = db.query(User).filter(
                        User.department_id == dept_id,
                        User.is_active == True
                    ).count()

                    if team_size > 0:
                        start = date.today()
                        end = start + timedelta(days=30)
                        attendance_data = analytics.get_attendance_by_date_range(start, end, dept_id)

                        # Filter to weekdays only and limit to ~21 business days
                        weekday_data = [d for d in attendance_data if d['date'].weekday() < 5][:21]

                        if weekday_data:
                            # Custom SVG line chart - edge to edge
                            width = 900
                            height = 160
                            left_padding = 10
                            right_padding = 10
                            top_padding = 15
                            bottom_padding = 25

                            chart_width = width - left_padding - right_padding
                            chart_height = height - top_padding - bottom_padding

                            num_points = len(weekday_data)
                            x_step = chart_width / (num_points - 1) if num_points > 1 else chart_width

                            # Build line path and dots
                            points = []
                            dots_svg = ''
                            for i, day in enumerate(weekday_data):
                                x = left_padding + i * x_step
                                pct = day['attendance_rate']
                                y = top_padding + chart_height - (pct / 100 * chart_height)
                                points.append(f'{x},{y}')

                                # Color based on coverage
                                dot_color = '#22c55e' if pct >= 70 else '#ef4444'
                                date_str = day['date'].strftime('%b %d')
                                dots_svg += f'''<circle cx="{x}" cy="{y}" r="5" fill="{dot_color}"
                                    style="cursor: pointer;"
                                    onmouseover="this.setAttribute('r', '8');"
                                    onmouseout="this.setAttribute('r', '5');"
                                    onclick="document.dispatchEvent(new CustomEvent('coverage-point-click', {{detail: {{date: '{date_str}', coverage: {pct:.0f}}}}}));">
                                    <title>{date_str}: {pct:.0f}%</title>
                                </circle>'''

                            # 70% threshold line only
                            y_70 = top_padding + chart_height - (70 / 100 * chart_height)
                            grid_svg = f'<line x1="{left_padding}" y1="{y_70}" x2="{width - right_padding}" y2="{y_70}" stroke="#ef4444" stroke-width="1" stroke-dasharray="4"/>'

                            # X-axis date labels (every 4th day)
                            x_labels_svg = ''
                            for i, day in enumerate(weekday_data):
                                if i % 4 == 0 or i == len(weekday_data) - 1:
                                    x = left_padding + i * x_step
                                    x_labels_svg += f'<text x="{x}" y="{height - 5}" text-anchor="middle" fill="#9ca3af" font-size="10">{day["date"].strftime("%m/%d")}</text>'

                            line_svg = f'''
                            <svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
                                {grid_svg}
                                <!-- 70% threshold annotation -->
                                <text x="{width - right_padding}" y="{y_70 - 5}" text-anchor="end" fill="#ef4444" font-size="10">Min: 70%</text>
                                <!-- Line path -->
                                <polyline points="{' '.join(points)}" fill="none" stroke="#3b82f6" stroke-width="2"/>
                                {dots_svg}
                                {x_labels_svg}
                            </svg>
                            '''

                            ui.html(line_svg, sanitize=False).classes('w-full')

                            # Click info display
                            coverage_click_label = ui.label('Click a point to see details').classes('text-xs text-gray-400 text-center w-full mt-2')

                            # JavaScript to handle coverage point clicks
                            ui.run_javascript('''
                                document.addEventListener('coverage-point-click', function(e) {
                                    const info = e.detail;
                                    const elem = document.querySelector('[data-coverage-click-info]');
                                    if (elem) {
                                        const color = info.coverage >= 70 ? '#22c55e' : '#ef4444';
                                        elem.textContent = info.date + ': ' + info.coverage + '% coverage';
                                        elem.style.color = color;
                                        elem.style.fontWeight = 'bold';
                                    }
                                });
                            ''')
                            coverage_click_label._props['data-coverage-click-info'] = 'true'

                            # Legend
                            with ui.row().classes('w-full justify-center gap-6 mt-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.element('div').classes('w-3 h-3 rounded-full').style('background-color: #22c55e')
                                    ui.label('Good Coverage (70%+)').classes('text-xs')
                                with ui.row().classes('items-center gap-2'):
                                    ui.element('div').classes('w-3 h-3 rounded-full').style('background-color: #ef4444')
                                    ui.label('Low Coverage (<70%)').classes('text-xs')
                        else:
                            ui.label('No forecast data available').classes('opacity-50')
                    else:
                        ui.label('No employees in selected department').classes('opacity-50')
                else:
                    ui.label('No departments configured').classes('opacity-50')

        # Initial load
        refresh_dashboard()

        # Navigation buttons
        with ui.row().classes('w-full justify-between mt-6'):
            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline')
            ui.button('View Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline')
