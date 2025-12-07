"""Analytics Dashboard page for PTO insights and trends."""
from nicegui import ui, app
from src.database import get_db
from src.services.analytics_service import AnalyticsService
from src.services.department_service import DepartmentService
from datetime import date, timedelta
from nicegui_app.components.header import page_header


def analytics_page():
    """Analytics dashboard with PTO trends and insights."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    # Check if user is logged in and has access
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_role = user.get('role')
    if user_role not in ['manager', 'admin', 'superadmin']:
        ui.notify('Access denied. Manager or higher role required.', type='negative')
        ui.navigate.to('/dashboard')
        return

    # State
    current_year = date.today().year
    selected_year = {'value': current_year}

    with ui.column().classes('w-full max-w-7xl mx-auto mt-8 p-6'):
        page_header(title='ANALYTICS DASHBOARD', show_back=False)

        # Year selector
        with ui.row().classes('w-full items-center gap-4 mb-6'):
            ui.label('Year:').classes('font-medium')
            year_options = {y: str(y) for y in range(current_year - 2, current_year + 2)}

            def on_year_change(e):
                selected_year['value'] = e.value
                refresh_dashboard()

            ui.select(year_options, value=selected_year['value'], on_change=on_year_change).classes('w-32')
            ui.button('Refresh', icon='refresh', on_click=lambda: refresh_dashboard()).props('flat')

        # Dashboard container
        dashboard_container = ui.column().classes('w-full gap-6')

        def refresh_dashboard():
            """Refresh all dashboard components."""
            dashboard_container.clear()
            year = selected_year['value']

            db = next(get_db())
            try:
                analytics = AnalyticsService(db)

                with dashboard_container:
                    # ===== ROW 1: Overview Cards =====
                    overview = analytics.get_company_overview(year)

                    with ui.row().classes('w-full gap-4 flex-wrap'):
                        # Total Requests Card
                        with ui.card().classes('flex-1 min-w-48 p-4'):
                            with ui.column().classes('items-center'):
                                ui.icon('description', size='lg', color='blue')
                                ui.label(str(overview['total_requests'])).classes('text-3xl font-bold')
                                ui.label('Total Requests').classes('text-sm opacity-70')

                        # Approved Card
                        with ui.card().classes('flex-1 min-w-48 p-4'):
                            with ui.column().classes('items-center'):
                                ui.icon('check_circle', size='lg', color='green')
                                ui.label(str(overview['approved'])).classes('text-3xl font-bold text-green-600')
                                ui.label('Approved').classes('text-sm opacity-70')

                        # Pending Card
                        with ui.card().classes('flex-1 min-w-48 p-4'):
                            with ui.column().classes('items-center'):
                                ui.icon('pending', size='lg', color='amber')
                                ui.label(str(overview['pending'])).classes('text-3xl font-bold text-amber-600')
                                ui.label('Pending').classes('text-sm opacity-70')

                        # Days Taken Card
                        with ui.card().classes('flex-1 min-w-48 p-4'):
                            with ui.column().classes('items-center'):
                                ui.icon('event_available', size='lg', color='purple')
                                ui.label(str(overview['total_days_taken'])).classes('text-3xl font-bold text-purple-600')
                                ui.label('Days Taken').classes('text-sm opacity-70')

                        # Avg Per Employee Card
                        with ui.card().classes('flex-1 min-w-48 p-4'):
                            with ui.column().classes('items-center'):
                                ui.icon('person', size='lg', color='cyan')
                                ui.label(str(overview['avg_days_per_employee'])).classes('text-3xl font-bold')
                                ui.label('Avg Days/Employee').classes('text-sm opacity-70')

                    # ===== ROW 2: Monthly Trends & Leave Type Breakdown =====
                    with ui.row().classes('w-full gap-4'):
                        # Monthly Trends Chart
                        with ui.card().classes('flex-1 p-4'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('trending_up', color='blue')
                                ui.label('Monthly PTO Trends').classes('text-lg font-semibold')

                            monthly_data = analytics.get_monthly_trends(year)

                            # Simple bar chart using divs
                            max_days = max((m['days_taken'] for m in monthly_data), default=1)
                            if max_days == 0:
                                max_days = 1

                            with ui.row().classes('w-full items-end gap-1 h-48'):
                                for month in monthly_data:
                                    height_pct = (month['days_taken'] / max_days * 100) if max_days > 0 else 0
                                    with ui.column().classes('flex-1 items-center'):
                                        # Bar
                                        bar_height = max(4, int(height_pct * 1.5))
                                        ui.element('div').classes('w-full bg-blue-500 rounded-t').style(f'height: {bar_height}px;').tooltip(f"{month['days_taken']} days")
                                        # Label
                                        ui.label(month['month_abbr']).classes('text-xs mt-1')

                            # Legend
                            with ui.row().classes('w-full justify-center mt-4'):
                                ui.label(f'Total: {sum(m["days_taken"] for m in monthly_data)} days').classes('text-sm opacity-70')

                        # Leave Type Breakdown
                        with ui.card().classes('w-80 p-4'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('pie_chart', color='purple')
                                ui.label('By Leave Type').classes('text-lg font-semibold')

                            type_data = analytics.get_leave_type_breakdown(year)

                            if type_data:
                                for item in type_data:
                                    color = 'blue' if 'vacation' in item['type'].lower() else \
                                            'green' if 'sick' in item['type'].lower() else \
                                            'purple' if 'personal' in item['type'].lower() else 'gray'

                                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                                        ui.element('div').classes(f'w-3 h-3 rounded-full bg-{color}-500')
                                        ui.label(item['type']).classes('flex-1')
                                        ui.label(f"{item['days']} days").classes('font-mono text-sm')
                                        ui.label(f"({item['percentage']}%)").classes('text-xs opacity-60')
                            else:
                                ui.label('No data available').classes('opacity-50')

                    # ===== ROW 3: Department Comparison & Top Users =====
                    with ui.row().classes('w-full gap-4'):
                        # Department Comparison
                        with ui.card().classes('flex-1 p-4'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('business', color='amber')
                                ui.label('Department Comparison').classes('text-lg font-semibold')

                            dept_data = analytics.get_department_comparison(year)

                            if dept_data:
                                # Table header
                                with ui.row().classes('w-full border-b pb-2 mb-2'):
                                    ui.label('Department').classes('flex-1 font-semibold text-sm')
                                    ui.label('Employees').classes('w-20 text-center font-semibold text-sm')
                                    ui.label('Total Days').classes('w-24 text-center font-semibold text-sm')
                                    ui.label('Avg/Person').classes('w-24 text-center font-semibold text-sm')

                                for dept in dept_data[:8]:  # Show top 8
                                    with ui.row().classes('w-full items-center py-1 hover:bg-gray-50 dark:hover:bg-gray-800'):
                                        ui.label(dept['department_name']).classes('flex-1 text-sm')
                                        ui.label(str(dept['employee_count'])).classes('w-20 text-center text-sm')
                                        ui.label(str(dept['total_days'])).classes('w-24 text-center text-sm')
                                        ui.label(str(dept['avg_days_per_employee'])).classes('w-24 text-center text-sm font-semibold')
                            else:
                                ui.label('No department data available').classes('opacity-50')

                        # Top PTO Users
                        with ui.card().classes('w-96 p-4'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('emoji_events', color='amber')
                                ui.label('Top PTO Users').classes('text-lg font-semibold')

                            top_users = analytics.get_top_users_by_pto(year, limit=8)

                            if top_users:
                                for idx, user_data in enumerate(top_users):
                                    medal_color = 'amber' if idx == 0 else 'gray' if idx == 1 else 'orange' if idx == 2 else None

                                    with ui.row().classes('w-full items-center gap-2 py-1'):
                                        if medal_color:
                                            ui.icon('emoji_events', size='xs', color=medal_color)
                                        else:
                                            ui.label(f'{idx + 1}.').classes('w-5 text-sm opacity-50')

                                        with ui.column().classes('flex-1 gap-0'):
                                            ui.label(user_data['name']).classes('text-sm font-medium')
                                            ui.label(user_data['department']).classes('text-xs opacity-60')

                                        ui.label(f"{user_data['days_taken']} days").classes('font-mono text-sm')
                            else:
                                ui.label('No data available').classes('opacity-50')

                    # ===== ROW 4: Coverage Gaps (Admin/Superadmin only) =====
                    if user_role in ['admin', 'superadmin']:
                        with ui.card().classes('w-full p-4'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('warning', color='red')
                                ui.label('Coverage Gap Analysis').classes('text-lg font-semibold')
                                ui.label('(Next 30 days)').classes('text-sm opacity-60')

                            # Department selector for gap analysis
                            departments = DepartmentService.get_all_departments(db)
                            dept_options = {d.id: d.name for d in departments}

                            gap_container = ui.column().classes('w-full')

                            def analyze_gaps(dept_id: int):
                                gap_container.clear()
                                start = date.today()
                                end = start + timedelta(days=30)
                                gaps = analytics.get_coverage_gaps(dept_id, start, end, threshold=0.3)

                                with gap_container:
                                    if gaps:
                                        ui.label(f'Found {len(gaps)} potential coverage issues:').classes('mb-2 text-amber-600')
                                        for gap in gaps[:10]:  # Show first 10
                                            with ui.row().classes('w-full items-center gap-4 p-2 bg-red-50 dark:bg-red-900/20 rounded mb-1'):
                                                ui.icon('warning', color='red', size='xs')
                                                ui.label(f"{gap['day_name']}, {gap['date_str']}").classes('font-medium')
                                                ui.label(f"{gap['absent_count']}/{gap['team_size']} out ({gap['absence_rate']}%)").classes('text-sm')
                                                ui.label(', '.join(gap['absent_employees'][:3])).classes('text-xs opacity-70')
                                    else:
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('check_circle', color='green')
                                            ui.label('No coverage gaps detected in the next 30 days').classes('text-green-600')

                            if dept_options:
                                first_dept_id = list(dept_options.keys())[0]

                                with ui.row().classes('gap-4 mb-4'):
                                    ui.label('Select Department:').classes('self-center')
                                    ui.select(
                                        dept_options,
                                        value=first_dept_id,
                                        on_change=lambda e: analyze_gaps(e.value)
                                    ).classes('w-48')

                                # Initial analysis
                                analyze_gaps(first_dept_id)
                            else:
                                ui.label('No departments configured').classes('opacity-50')

                    # ===== ROW 5: Utilization Rate =====
                    with ui.card().classes('w-full p-4'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('speed', color='green')
                            ui.label('PTO Utilization').classes('text-lg font-semibold')

                        utilization = analytics.get_utilization_rate(year)

                        with ui.row().classes('w-full gap-8 items-center'):
                            # Progress bar
                            with ui.column().classes('flex-1'):
                                ui.label(f"Utilization Rate: {utilization['utilization_rate']}%").classes('mb-2')
                                with ui.linear_progress(value=utilization['utilization_rate'] / 100).classes('w-full'):
                                    pass
                                with ui.row().classes('w-full justify-between text-xs opacity-60 mt-1'):
                                    ui.label(f"Used: {utilization['total_used_days']} days")
                                    ui.label(f"Allocated: {utilization['total_allocated_days']} days")

                            # Stats
                            with ui.column().classes('gap-1'):
                                ui.label(f"Tracking {utilization['employees_tracked']} employees").classes('text-sm')

            finally:
                db.close()

        # Initial load
        refresh_dashboard()

        # Back button
        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat').classes('mt-6')
