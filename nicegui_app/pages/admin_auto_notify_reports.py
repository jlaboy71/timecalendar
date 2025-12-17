"""Auto Notify Reports page for viewing trusted employee auto-approve reports."""
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_success_dialog, show_warning_dialog, show_error_dialog
from src.services.report_storage_service import ReportStorageService
from src.services.user_service import UserService
from src.services.department_service import DepartmentService
from src.services.email_service import email_service
from src.database import get_db
from datetime import date


def get_day_name(d: date) -> str:
    """Get abbreviated day name for a date."""
    return d.strftime('%a')


def format_date_with_day(d: date) -> str:
    """Format date with day name (e.g., 'Mon Dec 16')."""
    return d.strftime('%a %b %d')


def auto_notify_reports_page():
    """Display auto-notify reports for trusted employee auto-approvals."""
    apply_dark_mode()

    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_role = user.get('role', 'employee')
    user_id = user.get('id')

    # Only managers, admins, and superadmins can access
    if user_role not in ['manager', 'admin', 'superadmin']:
        ui.navigate.to('/dashboard')
        return

    page_header(title='Auto Notify Reports', show_back=False)

    db = next(get_db())
    try:
        user_service = UserService(db)
        current_user = user_service.get_user_by_id(user_id)

        # Determine which department(s) the user can view
        user_department_name = None
        if user_role in ['manager', 'admin'] and current_user and current_user.department_id:
            dept = DepartmentService.get_department_by_id(db, current_user.department_id)
            if dept:
                user_department_name = dept.name

        # Get all departments with reports (for superadmin dropdown)
        all_departments = ReportStorageService.get_departments_with_reports()

        # State for filters - default to "Recent" (current + previous month)
        current_year = date.today().year
        current_month = date.today().month
        filter_state = {
            'department': user_department_name if user_department_name else (all_departments[0] if all_departments else None),
            'year': current_year,
            'month': 'recent',  # Special value for current + previous month
            'frequency': None  # None means all frequencies
        }

        # Container placeholder - will be created in page structure
        report_container = None

        def get_recent_months():
            """Get current and previous month as list of (year, month) tuples."""
            today = date.today()
            current = (today.year, today.month)
            if today.month == 1:
                previous = (today.year - 1, 12)
            else:
                previous = (today.year, today.month - 1)
            return [previous, current]

        def refresh_reports():
            """Refresh the report list based on current filters."""
            nonlocal report_container
            if report_container is None:
                return
            report_container.clear()

            with report_container:
                if not filter_state['department']:
                    with ui.card().classes('w-full p-8 text-center'):
                        ui.icon('folder_off', size='4rem').classes('opacity-30 mb-4')
                        ui.label('No reports available').classes('text-xl opacity-60')
                        ui.label('Reports will appear here when trusted employees submit auto-approved time off.').classes('text-sm opacity-40')
                    return

                # Get reports based on filter
                all_reports = []
                if filter_state['month'] == 'recent':
                    # Get reports for current and previous month
                    for yr, mo in get_recent_months():
                        reports = ReportStorageService.list_reports(
                            department_name=filter_state['department'],
                            year=yr,
                            month=mo
                        )
                        all_reports.extend(reports)
                else:
                    all_reports = ReportStorageService.list_reports(
                        department_name=filter_state['department'],
                        year=filter_state['year'],
                        month=filter_state['month']
                    )

                if not all_reports:
                    with ui.card().classes('w-full p-8 text-center'):
                        ui.icon('description', size='4rem').classes('opacity-30 mb-4')
                        ui.label('No reports found').classes('text-xl opacity-60')
                        filter_text = f"for {filter_state['department']}"
                        if filter_state['month'] == 'recent':
                            filter_text += " (Recent)"
                        elif filter_state['year']:
                            filter_text += f" in {filter_state['year']}"
                            if filter_state['month']:
                                filter_text += f" ({date(2000, filter_state['month'], 1).strftime('%B')})"
                        ui.label(filter_text).classes('text-sm opacity-40')
                    return

                # Filter by frequency if selected
                if filter_state['frequency']:
                    all_reports = [r for r in all_reports if r['frequency'] == filter_state['frequency']]

                if not all_reports:
                    with ui.card().classes('w-full p-8 text-center'):
                        ui.icon('description', size='4rem').classes('opacity-30 mb-4')
                        ui.label('No reports found').classes('text-xl opacity-60')
                        ui.label('Try adjusting your filters').classes('text-sm opacity-40')
                    return

                # Sort reports: by month (newest first), then by frequency (weekly, bi-weekly, monthly), then by date (earliest first)
                freq_order = {'weekly': 1, 'bi-weekly': 2, 'monthly': 3}
                all_reports.sort(key=lambda r: (-r['year'], -r['month'], freq_order.get(r['frequency'], 9), r.get('day', 1)))

                # Group reports by month for better organization
                current_month_key = None

                for report in all_reports:
                    # Add month separator
                    month_key = f"{report['year']}-{report['month']:02d}"
                    if month_key != current_month_key:
                        current_month_key = month_key
                        month_name = date(report['year'], report['month'], 1).strftime('%B %Y')
                        ui.label(month_name).classes('text-lg font-semibold mt-4 mb-2').style('color: #C9A227')

                    # Report card with day names
                    create_report_card(report, filter_state['department'])

        def create_report_card(report: dict, department_name: str):
            """Create a card for a single report."""
            # Frequency colors
            freq_colors = {
                'weekly': '#3b82f6',
                'bi-weekly': '#a855f7',
                'monthly': '#22c55e'
            }
            color = freq_colors.get(report['frequency'], '#6b7280')

            # Format display date with day name
            display_date = report['display_date']
            # Parse the date and add day name if possible
            try:
                # display_date format is like "Dec 14, 2025" or "Dec 01 - Dec 14, 2025"
                if ' - ' in display_date:
                    # Date range - add day names to both
                    parts = display_date.split(' - ')
                    start_str = parts[0]  # "Dec 01"
                    end_str = parts[1]    # "Dec 14, 2025"
                    # Parse the year from end
                    year = int(end_str.split(', ')[1])
                    # Create dates to get day names
                    # This is a simplified version - keeping original display for now
                    display_with_days = display_date
                else:
                    # Single date
                    display_with_days = display_date
            except Exception:
                display_with_days = display_date

            with ui.card().classes('w-full p-4').style(f'border-left: 4px solid {color}'):
                with ui.row().classes('w-full justify-between items-center'):
                    # Left side - Report info
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('description', size='lg').style(f'color: {color}')
                        with ui.column().classes('gap-0'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(report['frequency'].replace('-', ' ').title()).classes('font-semibold')
                                ui.badge(display_with_days, color='grey').props('outline')
                            ui.label(report['filename']).classes('text-xs opacity-50')

                    # Right side - Action buttons
                    with ui.row().classes('gap-2'):
                        # View button
                        def make_view_handler(r=report, dept=department_name):
                            return lambda: show_report_dialog(r, dept)
                        ui.button(icon='visibility', on_click=make_view_handler()).props('flat round').tooltip('View Report')

                        # Print button
                        def make_print_handler(r=report, dept=department_name):
                            return lambda: open_print_preview(r, dept)
                        ui.button(icon='print', on_click=make_print_handler()).props('flat round').tooltip('Print Preview')

                        # Email button
                        def make_email_handler(r=report, dept=department_name):
                            return lambda: show_email_dialog(r, dept)
                        ui.button(icon='email', on_click=make_email_handler()).props('flat round').tooltip('Email Report')

                        # Delete button
                        def make_delete_handler(r=report, dept=department_name):
                            return lambda: show_delete_confirmation(r, dept)
                        ui.button(icon='delete', on_click=make_delete_handler()).props('flat round color=negative').tooltip('Delete Report')

        def show_report_dialog(report: dict, department_name: str):
            """Show report content in a dialog."""
            content = ReportStorageService.get_report(
                department_name,
                report['year'],
                report['month'],
                report['filename']
            )

            if not content:
                show_error_dialog('Error', 'Failed to load report')
                return

            with ui.dialog() as dialog, ui.card().classes('w-full p-0').style('width: 95vw; max-width: 1100px;'):
                # Header
                with ui.row().classes('w-full justify-between items-center p-4').style('background-color: #1f2937; border-bottom: 3px solid #C9A227;'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('description').style('color: #C9A227')
                        ui.label(f'{report["frequency"].title()} Report - {report["display_date"]}').classes('text-lg font-bold')
                    ui.button(icon='close', on_click=dialog.close).props('flat round color=white')

                # Content - direct HTML rendering in scrollable container
                with ui.scroll_area().classes('w-full').style('height: 70vh; background: #111827;'):
                    ui.html(content, sanitize=False).classes('w-full')

                # Footer with actions
                with ui.row().classes('w-full justify-end gap-2 p-4').style('background-color: #374151;'):
                    ui.button('Close', on_click=dialog.close).props('flat')

            dialog.open()

        def open_print_preview(report: dict, department_name: str):
            """Open report in new window for printing."""
            content = ReportStorageService.get_report(
                department_name,
                report['year'],
                report['month'],
                report['filename']
            )

            if not content:
                show_error_dialog('Error', 'Failed to load report')
                return

            # Create a print-friendly dialog
            with ui.dialog() as dialog, ui.card().classes('w-full p-0').style('width: 95vw; max-width: 1100px;'):
                # Header with print button
                with ui.row().classes('w-full justify-between items-center p-4 no-print').style('background-color: #1f2937; border-bottom: 3px solid #C9A227;'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('print').style('color: #C9A227')
                        ui.label('Print Preview').classes('text-lg font-bold')
                    with ui.row().classes('gap-2'):
                        ui.button('Print', icon='print', on_click=lambda: ui.run_javascript('window.print()')).props('color=primary')
                        ui.button(icon='close', on_click=dialog.close).props('flat round color=white')

                # Content - direct HTML rendering
                with ui.scroll_area().classes('w-full').style('height: 70vh; background: #111827;'):
                    ui.html(content, sanitize=False).classes('w-full')

            dialog.open()

        def show_email_dialog(report: dict, department_name: str):
            """Show dialog to email the report."""
            with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 450px;'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('email').style('color: #C9A227')
                    ui.label('Email Report').classes('text-lg font-bold')

                ui.label(f'{report["frequency"].title()} Report - {report["display_date"]}').classes('text-sm opacity-70 mb-4')

                email_input = ui.input(
                    label='Recipient Email',
                    placeholder='Enter email address...',
                    validation={'Invalid email': lambda v: '@' in v and '.' in v}
                ).props('outlined').classes('w-full mb-4')

                message_input = ui.textarea(
                    label='Message (optional)',
                    placeholder='Add a message to include with the report...'
                ).props('outlined autogrow').classes('w-full mb-4')

                async def send_email():
                    if not email_input.value or '@' not in email_input.value:
                        show_warning_dialog('Invalid Email', 'Please enter a valid email address')
                        return

                    content = ReportStorageService.get_report(
                        department_name,
                        report['year'],
                        report['month'],
                        report['filename']
                    )

                    if not content:
                        show_error_dialog('Error', 'Failed to load report')
                        return

                    subject = f"TJM Time Calendar: {report['frequency'].title()} Auto-Notify Report - {report['display_date']}"

                    success = email_service.send_report_email(
                        to_email=email_input.value,
                        subject=subject,
                        html_content=content,
                        message=message_input.value.strip() if message_input.value else None
                    )

                    if success:
                        show_success_dialog('Email Sent', f'Report sent to {email_input.value}')
                        dialog.close()
                    else:
                        show_error_dialog('Email Failed', 'Failed to send email. Check email configuration.')

                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    ui.button('Send', icon='send', on_click=send_email).props('color=primary')

            dialog.open()

        def show_delete_confirmation(report: dict, department_name: str):
            """Show delete confirmation dialog."""
            with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('warning', color='red', size='md')
                    ui.label('Delete Report?').classes('text-lg font-bold')

                ui.label(f'Are you sure you want to delete this report?').classes('mb-2')
                ui.label(f'{report["frequency"].title()} - {report["display_date"]}').classes('text-sm opacity-70 mb-4')
                ui.label('This action cannot be undone.').classes('text-sm text-red-400')

                def confirm_delete():
                    success = ReportStorageService.delete_report(
                        department_name,
                        report['year'],
                        report['month'],
                        report['filename']
                    )

                    if success:
                        show_success_dialog('Deleted', 'Report deleted successfully')
                        dialog.close()
                        refresh_reports()
                    else:
                        show_error_dialog('Error', 'Failed to delete report')

                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    ui.button('Delete', icon='delete', on_click=confirm_delete).props('color=negative')

            dialog.open()

        def show_help_dialog():
            """Show help tips dialog."""
            with ui.dialog() as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 500px; max-width: 600px;'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('help_outline').style('color: #C9A227')
                    ui.label('Auto Notify Reports Help').classes('text-lg font-bold')

                with ui.column().classes('gap-4'):
                    # What are these reports
                    with ui.card().classes('w-full p-3').style('background-color: #374151;'):
                        ui.label('What are Auto Notify Reports?').classes('font-semibold mb-2').style('color: #C9A227')
                        ui.label('These reports summarize time off requests that were automatically approved for trusted employees. Managers receive notifications about these auto-approvals to maintain visibility.').classes('text-sm opacity-80')

                    # Report frequencies
                    with ui.card().classes('w-full p-3').style('background-color: #374151;'):
                        ui.label('Report Frequencies').classes('font-semibold mb-2').style('color: #C9A227')
                        with ui.column().classes('gap-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.badge('Weekly', color='blue').props('outline')
                                ui.label('Generated every Sunday, covering the past 7 days').classes('text-sm opacity-80')
                            with ui.row().classes('items-center gap-2'):
                                ui.badge('Bi-Weekly', color='purple').props('outline')
                                ui.label('Generated on 1st and 15th of each month').classes('text-sm opacity-80')
                            with ui.row().classes('items-center gap-2'):
                                ui.badge('Monthly', color='green').props('outline')
                                ui.label('Generated on the last day of each month').classes('text-sm opacity-80')

                    # Actions
                    with ui.card().classes('w-full p-3').style('background-color: #374151;'):
                        ui.label('Available Actions').classes('font-semibold mb-2').style('color: #C9A227')
                        with ui.column().classes('gap-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('visibility', size='sm')
                                ui.label('View - Open the full report in a dialog').classes('text-sm opacity-80')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('print', size='sm')
                                ui.label('Print - Open print preview for the report').classes('text-sm opacity-80')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('email', size='sm')
                                ui.label('Email - Send the report to a recipient').classes('text-sm opacity-80')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('delete', size='sm', color='red')
                                ui.label('Delete - Permanently remove the report').classes('text-sm opacity-80')

                    # Filters tip
                    with ui.card().classes('w-full p-3').style('background-color: #374151;'):
                        ui.label('Filtering Reports').classes('font-semibold mb-2').style('color: #C9A227')
                        ui.label('Use "Recent" to view only the current and previous month. Select a specific month to see all reports from that period.').classes('text-sm opacity-80')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Got it', on_click=dialog.close).props('color=primary')

            dialog.open()

        # Build the page UI - filters at top edge-to-edge
        with ui.column().classes('w-full gap-0'):
            # Filter bar - edge to edge at TOP
            with ui.row().classes('w-full gap-4 items-end flex-wrap p-4').style('background-color: #1f2937; border-bottom: 2px solid #374151;'):
                # Department dropdown (only for superadmin)
                if user_role == 'superadmin':
                    if all_departments:
                        dept_options = {d: d for d in all_departments}

                        def on_dept_change(e):
                            filter_state['department'] = e.value
                            refresh_reports()

                        ui.select(
                            options=dept_options,
                            value=filter_state['department'],
                            label='Department',
                            on_change=on_dept_change
                        ).props('outlined dense').classes('min-w-[200px]')
                    else:
                        ui.label('No departments with reports').classes('opacity-60')
                else:
                    # Show department name for managers/admins
                    with ui.column().classes('gap-0'):
                        ui.label('Department').classes('text-xs opacity-60')
                        ui.label(filter_state['department'] or 'Not assigned').classes('font-semibold').style('color: #C9A227')

                # Year dropdown
                year_options = {y: str(y) for y in range(current_year, current_year - 3, -1)}

                def on_year_change(e):
                    filter_state['year'] = int(e.value)
                    # If changing year, switch from 'recent' to 'all'
                    if filter_state['month'] == 'recent':
                        filter_state['month'] = None
                    refresh_reports()

                ui.select(
                    options=year_options,
                    value=filter_state['year'],
                    label='Year',
                    on_change=on_year_change
                ).props('outlined dense').classes('min-w-[120px]')

                # Month dropdown with "Recent" option
                month_options = {'recent': 'Recent (Last 2 months)', None: 'All Months'}
                month_options.update({m: date(2000, m, 1).strftime('%B') for m in range(1, 13)})

                def on_month_change(e):
                    filter_state['month'] = e.value
                    refresh_reports()

                ui.select(
                    options=month_options,
                    value=filter_state['month'],
                    label='Month',
                    on_change=on_month_change
                ).props('outlined dense').classes('min-w-[180px]')

                # Frequency dropdown
                freq_options = {None: 'All Types', 'weekly': 'Weekly', 'bi-weekly': 'Bi-Weekly', 'monthly': 'Monthly'}

                def on_freq_change(e):
                    filter_state['frequency'] = e.value
                    refresh_reports()

                ui.select(
                    options=freq_options,
                    value=filter_state['frequency'],
                    label='Type',
                    on_change=on_freq_change
                ).props('outlined dense').classes('min-w-[140px]')

                # Spacer
                ui.element('div').classes('flex-grow')

                # Help button
                ui.button(icon='help_outline', on_click=show_help_dialog).props('flat round').tooltip('Help & Tips')

                # Refresh button
                ui.button('Refresh', icon='refresh', on_click=refresh_reports).props('outline')

            # Report list container - AFTER the filter bar
            with ui.column().classes('w-full max-w-5xl mx-auto px-4 py-4'):
                # Create the report container here
                report_container = ui.column().classes('w-full gap-4')
                refresh_reports()

                # Back button
                ui.button('Back', icon='arrow_back', on_click=go_back).classes('mt-4')

    finally:
        db.close()
