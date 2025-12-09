"""Analytics Dashboard page for PTO insights and trends."""
from nicegui import ui, app
from src.database import get_db
from src.services.analytics_service import AnalyticsService
from src.services.department_service import DepartmentService
from src.services.export_service import ExportService
from datetime import date, timedelta
import base64
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from nicegui_app.components.charts import (
    attendance_heatmap,
    monthly_trend_chart,
    department_utilization_bars,
    coverage_timeline,
    day_of_week_pattern,
    carryover_risk_gauge,
    simple_pie_chart
)


def analytics_page():
    """Analytics dashboard with PTO trends and insights."""

    apply_dark_mode()

    # Check if user is logged in and has access
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_id = user.get('id')
    user_role = user.get('role')
    if user_role not in ['manager', 'admin', 'superadmin']:
        ui.notify('Access denied. Manager or higher role required.', type='negative')
        ui.navigate.to('/dashboard')
        return

    # Manager and Admin are restricted to their department; only SuperAdmin sees all
    is_department_restricted = user_role in ['manager', 'admin']

    # Get user's department if applicable (for manager/admin)
    user_department_id = None
    user_department_name = None
    if is_department_restricted:
        db = next(get_db())
        try:
            from src.services.user_service import UserService
            from src.models.department import Department
            user_service = UserService(db)
            current_user = user_service.get_user_by_id(user_id)
            if current_user and current_user.department_id:
                user_department_id = current_user.department_id
                dept = db.query(Department).filter(Department.id == user_department_id).first()
                if dept:
                    user_department_name = dept.name
        finally:
            db.close()

    # Keep backward compatibility with existing variable names
    is_manager_only = is_department_restricted
    manager_department_id = user_department_id
    manager_department_name = user_department_name

    # State
    current_year = date.today().year
    selected_year = {'value': current_year}
    active_tab = {'value': 'overview'}

    with ui.column().classes('w-full max-w-7xl mx-auto mt-8 p-6'):
        # Show department scope for managers
        if is_manager_only and manager_department_name:
            page_header(title=f'ANALYTICS - {manager_department_name.upper()}', show_back=False)
        else:
            page_header(title='WORKFORCE ANALYTICS', show_back=False)

        # Controls row
        with ui.row().classes('w-full items-center justify-between mb-6'):
            # Tab buttons for different views
            with ui.row().classes('gap-2'):
                def set_tab(tab):
                    active_tab['value'] = tab
                    refresh_dashboard()

                ui.button('Overview', icon='dashboard', on_click=lambda: set_tab('overview')).props('flat')
                ui.button('Trends', icon='trending_up', on_click=lambda: set_tab('trends')).props('flat')
                ui.button('Insights', icon='lightbulb', on_click=lambda: set_tab('insights')).props('flat')

            # Year selector, export, and refresh
            with ui.row().classes('items-center gap-4'):
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
                        dept_filter = manager_department_id if is_manager_only else None

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
                        ui.notify('PDF report downloaded', type='positive')
                    except Exception as e:
                        ui.notify(f'Export failed: {str(e)}', type='negative')
                    finally:
                        db.close()

                async def export_csv():
                    """Export carryover risk to CSV."""
                    db = next(get_db())
                    try:
                        analytics = AnalyticsService(db)
                        year = selected_year['value']
                        dept_filter = manager_department_id if is_manager_only else None

                        days_until_year_end = (date(year, 12, 31) - date.today()).days
                        carryover_risk = analytics.get_carryover_risk_employees(year, days_until_year_end, 50.0, department_id=dept_filter)

                        csv_str = ExportService.generate_carryover_csv(carryover_risk)
                        filename = f"carryover_risk_{date.today().isoformat()}.csv"
                        ui.download(csv_str.encode('utf-8'), filename)
                        ui.notify('CSV report downloaded', type='positive')
                    except Exception as e:
                        ui.notify(f'Export failed: {str(e)}', type='negative')
                    finally:
                        db.close()

                ui.button('Export PDF', icon='picture_as_pdf', on_click=export_pdf).props('flat')
                ui.button('Export CSV', icon='table_chart', on_click=export_csv).props('flat')
                ui.button('Refresh', icon='refresh', on_click=lambda: refresh_dashboard()).props('flat')

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
                    # Department filter for managers (None for admins = all departments)
                    dept_filter = manager_department_id if is_manager_only else None

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
            # ===== ROW 1: Overview Cards =====
            overview = analytics.get_company_overview(year, department_id=dept_filter)

            with ui.element('div').classes('w-full grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4'):
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

            # ===== ROW 2: Attendance Heatmap & Leave Type Breakdown =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4'):
                # Attendance Heatmap
                with ui.card().classes('lg:col-span-2 p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('calendar_month', color='blue')
                        ui.label('Attendance Heatmap (Last 60 Days)').classes('text-lg font-semibold')

                    attendance_data = analytics.get_attendance_by_date_range(
                        date.today() - timedelta(days=60),
                        date.today() + timedelta(days=14),
                        department_id=dept_filter
                    )
                    attendance_heatmap(attendance_data, "")

                # Leave Type Breakdown (Pie Chart)
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('pie_chart', color='purple')
                        ui.label('By Leave Type').classes('text-lg font-semibold')

                    type_data = analytics.get_leave_type_breakdown(year, department_id=dept_filter)

                    if type_data:
                        # Convert to pie chart format
                        pie_data = []
                        colors = {'vacation': '#3b82f6', 'sick': '#ef4444', 'personal': '#22c55e'}
                        for item in type_data:
                            pie_data.append({
                                'label': item['type'],
                                'value': item['days'],
                                'color': colors.get(item['type'].lower(), '#6b7280')
                            })
                        simple_pie_chart(pie_data, "")
                    else:
                        ui.label('No data available').classes('opacity-50')

            # ===== ROW 3: Optimal Meeting Dates & Utilization =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-2 gap-4'):
                # Optimal Meeting Dates
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('event', color='green')
                        ui.label('Best Days for All-Hands (Next 30 Days)').classes('text-lg font-semibold')

                    optimal_dates = analytics.get_optimal_meeting_dates(
                        days_ahead=30,
                        min_attendance_pct=80,
                        max_results=5,
                        department_id=dept_filter
                    )

                    if optimal_dates:
                        for meeting in optimal_dates[:3]:
                            with ui.card().classes('bg-green-50 dark:bg-green-900/20 p-3 mb-2'):
                                with ui.row().classes('items-center justify-between'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(meeting['date_str']).classes('font-bold')
                                        ui.label(meeting['day_of_week']).classes('text-sm opacity-70')
                                    ui.label(f"{meeting['expected_attendance']:.0f}%").classes('text-2xl font-bold text-green-600')
                    else:
                        ui.label('No optimal dates found (attendance threshold: 80%)').classes('opacity-50')

                # Utilization Gauge
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('speed', color='green')
                        ui.label('PTO Utilization').classes('text-lg font-semibold')

                    utilization = analytics.get_utilization_rate(year, department_id=dept_filter)

                    with ui.column().classes('items-center'):
                        ui.label(f"{utilization['utilization_rate']}%").classes('text-5xl font-bold')
                        ui.label('of allocated PTO used').classes('text-sm opacity-70 mb-4')

                        with ui.linear_progress(value=utilization['utilization_rate'] / 100).classes('w-full'):
                            pass

                        with ui.row().classes('w-full justify-between text-xs opacity-60 mt-2'):
                            ui.label(f"Used: {utilization['total_used_days']} days")
                            ui.label(f"Allocated: {utilization['total_allocated_days']} days")

            # ===== ROW 4: Coverage Gaps =====
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('warning', color='red')
                    ui.label('Coverage Gap Analysis').classes('text-lg font-semibold')
                    ui.label('(Next 30 days)').classes('text-sm opacity-60')

                gap_container = ui.column().classes('w-full')

                def analyze_gaps(dept_id: int):
                    gap_container.clear()
                    start = date.today()
                    end = start + timedelta(days=30)
                    gaps = analytics.get_coverage_gaps(dept_id, start, end, threshold=0.3)

                    with gap_container:
                        if gaps:
                            ui.label(f'Found {len(gaps)} potential coverage issues:').classes('mb-2 text-amber-600')
                            for gap in gaps[:10]:
                                with ui.row().classes('w-full items-center gap-4 p-2 bg-red-50 dark:bg-red-900/20 rounded mb-1'):
                                    ui.icon('warning', color='red', size='xs')
                                    ui.label(f"{gap['day_name']}, {gap['date_str']}").classes('font-medium')
                                    ui.label(f"{gap['absent_count']}/{gap['team_size']} out ({gap['absence_rate']}%)").classes('text-sm')
                                    ui.label(', '.join(gap['absent_employees'][:3])).classes('text-xs opacity-70')
                        else:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('check_circle', color='green')
                                ui.label('No coverage gaps detected in the next 30 days').classes('text-green-600')

                if is_manager_only and manager_department_id:
                    analyze_gaps(manager_department_id)
                else:
                    departments = DepartmentService.get_all_departments(db)
                    dept_options = {d.id: d.name for d in departments}

                    if dept_options:
                        first_dept_id = list(dept_options.keys())[0]

                        with ui.row().classes('gap-4 mb-4'):
                            ui.label('Select Department:').classes('self-center')
                            ui.select(
                                dept_options,
                                value=first_dept_id,
                                on_change=lambda e: analyze_gaps(e.value)
                            ).classes('w-48')

                        analyze_gaps(first_dept_id)
                    else:
                        ui.label('No departments configured').classes('opacity-50')

        def render_trends_tab(analytics, year, dept_filter):
            """Render the trends tab with charts."""
            # ===== ROW 1: Monthly PTO by Type =====
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('trending_up', color='blue')
                    ui.label(f'Monthly PTO Trends ({year})').classes('text-lg font-semibold')

                monthly_by_type = analytics.get_monthly_pto_by_type(year, department_id=dept_filter)
                monthly_trend_chart(monthly_by_type, "")

            # ===== ROW 2: Day of Week Pattern & Department Utilization =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-2 gap-4'):
                # Day of Week Pattern
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('date_range', color='amber')
                        ui.label('PTO by Day of Week').classes('text-lg font-semibold')

                    dow_data = analytics.get_day_of_week_patterns(year, department_id=dept_filter)
                    day_of_week_pattern(dow_data, "")

                    # Analysis note
                    values = list(dow_data.values())
                    if len(values) >= 5:
                        mon_fri_avg = (values[0] + values[4]) / 2
                        mid_week_avg = sum(values[1:4]) / 3 if sum(values[1:4]) > 0 else 1
                        if mon_fri_avg > mid_week_avg * 1.3:
                            ui.label('Note: Monday/Friday clustering detected').classes('text-amber-600 text-sm mt-2')

                # Department Utilization Bars
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('business', color='purple')
                        ui.label('Department Utilization Rates').classes('text-lg font-semibold')

                    dept_util = analytics.get_department_utilization_rates(year)
                    department_utilization_bars(dept_util, "")

            # ===== ROW 3: Department Comparison Table =====
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('compare', color='blue')
                    ui.label('Department Comparison').classes('text-lg font-semibold')

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
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('emoji_events', color='amber')
                    ui.label('Top PTO Users').classes('text-lg font-semibold')

                top_users = analytics.get_top_users_by_pto(year, limit=10, department_id=dept_filter)

                if top_users:
                    with ui.row().classes('flex-wrap gap-4'):
                        for idx, user_data in enumerate(top_users):
                            medal_color = 'amber' if idx == 0 else 'gray' if idx == 1 else 'orange' if idx == 2 else None

                            with ui.card().classes('p-3 min-w-48'):
                                with ui.row().classes('items-center gap-2'):
                                    if medal_color:
                                        ui.icon('emoji_events', size='sm', color=medal_color)
                                    else:
                                        ui.label(f'#{idx + 1}').classes('text-sm opacity-50')

                                    with ui.column().classes('gap-0'):
                                        ui.label(user_data['name']).classes('font-medium')
                                        ui.label(user_data['department']).classes('text-xs opacity-60')

                                ui.label(f"{user_data['days_taken']} days").classes('text-xl font-bold text-right')
                else:
                    ui.label('No data available').classes('opacity-50')

        def render_insights_tab(analytics, year, dept_filter, db, is_manager_only, manager_department_id):
            """Render the insights tab with recommendations and risks."""
            # ===== Recommendations =====
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('lightbulb', color='amber')
                    ui.label('Recommendations').classes('text-lg font-semibold')

                recommendations = analytics.generate_recommendations(year, department_id=dept_filter)

                if recommendations:
                    for rec in recommendations:
                        color_map = {
                            'HIGH': 'bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500',
                            'MEDIUM': 'bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500',
                            'LOW': 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500',
                            'INFO': 'bg-green-50 dark:bg-green-900/20 border-l-4 border-green-500'
                        }
                        badge_color = {
                            'HIGH': 'red', 'MEDIUM': 'amber', 'LOW': 'blue', 'INFO': 'green'
                        }

                        with ui.card().classes(f'{color_map.get(rec["priority"], "")} p-4 mb-3'):
                            with ui.row().classes('items-center justify-between mb-2'):
                                ui.label(rec['title']).classes('font-bold')
                                ui.badge(rec['priority'], color=badge_color.get(rec['priority'], 'gray'))
                            ui.label(f"Category: {rec['category']}").classes('text-sm opacity-70')
                            ui.label(rec['action']).classes('text-sm mt-2')
                            if rec['affected']:
                                ui.label(f"Affected: {', '.join(rec['affected'][:3])}{'...' if len(rec['affected']) > 3 else ''}").classes('text-xs opacity-60 mt-1')
                else:
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle', color='green')
                        ui.label('No recommendations at this time - everything looks good!').classes('text-green-600')

            # ===== Carryover Risk Analysis =====
            with ui.element('div').classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-4'):
                # Carryover Risk Gauge
                with ui.card().classes('p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('warning', color='red')
                        ui.label('Carryover Risk').classes('text-lg font-semibold')

                    days_until_year_end = (date(year, 12, 31) - date.today()).days
                    carryover_risk = analytics.get_carryover_risk_employees(
                        year, days_until_year_end, 50.0, department_id=dept_filter
                    )

                    from src.models.user import User
                    emp_count = db.query(User).filter(User.is_active == True).count()

                    carryover_risk_gauge(len(carryover_risk), emp_count, "Employees at Risk")

                # Carryover Risk Table
                with ui.card().classes('lg:col-span-2 p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('people', color='red')
                        ui.label('Employees at Carryover Risk').classes('text-lg font-semibold')

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
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('timeline', color='blue')
                    ui.label('Coverage Forecast (Next 30 Days)').classes('text-lg font-semibold')

                # Get coverage data for timeline chart
                if is_manager_only and manager_department_id:
                    dept_id = manager_department_id
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

                        # Convert to coverage format for timeline
                        coverage_data = []
                        for day in attendance_data:
                            coverage_rate = day['attendance_rate']
                            coverage_data.append({
                                'date': day['date'],
                                'coverage_rate': coverage_rate,
                                'is_critical': coverage_rate < 70
                            })

                        coverage_timeline(coverage_data, "")
                    else:
                        ui.label('No employees in selected department').classes('opacity-50')
                else:
                    ui.label('No departments configured').classes('opacity-50')

        # Initial load
        refresh_dashboard()

        # Navigation buttons
        with ui.row().classes('w-full justify-between mt-6'):
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline')
            ui.button('View Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline')
