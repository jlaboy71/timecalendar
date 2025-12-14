"""Manager settings page for notification preferences."""
from datetime import date, timedelta
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_error_dialog, show_info_dialog, show_success_dialog
from src.services.notification_service import NotificationService


def format_hour_12h(hour: int) -> str:
    """Convert 24-hour to 12-hour AM/PM format."""
    if hour == 0:
        return '12:00 AM'
    elif hour < 12:
        return f'{hour}:00 AM'
    elif hour == 12:
        return '12:00 PM'
    else:
        return f'{hour - 12}:00 PM'


def manager_settings_page():
    """Manager settings including notification preferences."""
    apply_dark_mode()

    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_role = user.get('role')
    if user_role not in ['manager', 'admin', 'superadmin']:
        show_error_dialog('Access Denied', 'Only managers can access this page.')
        ui.navigate.to('/dashboard')
        return

    user_id = user.get('id')

    # Load current preferences
    db = next(get_db())
    try:
        notification_service = NotificationService(db)
        prefs = notification_service.get_manager_preferences(user_id)
        current_frequency = prefs.digest_frequency
        current_hour = prefs.preferred_hour
        current_day = prefs.preferred_day
        current_format = prefs.export_format
    finally:
        db.close()

    with ui.column().classes('w-full max-w-3xl mx-auto p-4'):
        page_header(title='MANAGER SETTINGS', show_back=True)

        # Notification Preferences Card
        with ui.card().classes('w-full p-6 mb-4'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('notifications', size='md').style('color: #c9a227')
                ui.label('PTO Notification Preferences').classes('text-xl font-semibold')

            ui.label('Configure how you receive notifications when team members submit PTO requests.').classes('text-sm opacity-60 mb-6')

            # Digest Frequency
            ui.label('Email Frequency').classes('font-semibold mb-2')
            ui.label('Choose how often you want to receive PTO request notifications').classes('text-xs opacity-60 mb-2')

            frequency_options = {
                'immediate': 'Immediate - Send email for each request',
                'daily': 'Daily Digest - One summary email per day',
                'weekly': 'Weekly Digest - One summary email per week',
                'biweekly': 'Bi-weekly Digest - Summary on 1st and 15th',
                'monthly': 'Monthly Digest - Summary on 1st of month'
            }
            frequency_select = ui.select(
                options=frequency_options,
                value=current_frequency,
                label='Notification Frequency'
            ).classes('w-full mb-6').props('outlined')

            # Time preferences container (shown/hidden based on frequency)
            time_prefs_container = ui.column().classes('w-full')

            def update_time_visibility():
                time_prefs_container.clear()
                freq = frequency_select.value

                if freq in ['daily', 'weekly', 'biweekly', 'monthly']:
                    with time_prefs_container:
                        with ui.card().classes('w-full p-4 mb-4').style('border-left: 4px solid #c9a227'):
                            ui.label('Delivery Schedule').classes('font-semibold mb-3')

                            with ui.row().classes('w-full gap-4'):
                                # Hour selector with proper 12-hour AM/PM format
                                hour_options = {h: format_hour_12h(h) for h in range(24)}
                                nonlocal hour_select
                                hour_select = ui.select(
                                    options=hour_options,
                                    value=current_hour,
                                    label='Preferred Time'
                                ).classes('flex-1').props('outlined')

                                # Day selector (only for weekly)
                                if freq == 'weekly':
                                    day_options = {
                                        0: 'Monday',
                                        1: 'Tuesday',
                                        2: 'Wednesday',
                                        3: 'Thursday',
                                        4: 'Friday',
                                        5: 'Saturday',
                                        6: 'Sunday'
                                    }
                                    nonlocal day_select
                                    day_select = ui.select(
                                        options=day_options,
                                        value=current_day,
                                        label='Preferred Day'
                                    ).classes('flex-1').props('outlined')

            # Initialize selectors
            hour_select = None
            day_select = None
            update_time_visibility()
            frequency_select.on('update:model-value', lambda e: update_time_visibility())

            ui.separator().classes('my-4')

            # Export Format
            ui.label('Report Format').classes('font-semibold mb-2')
            ui.label('Choose the format for digest report attachments').classes('text-xs opacity-60 mb-2')

            format_options = {
                'pdf': 'PDF - Formatted report for printing/archiving',
                'csv': 'CSV - Spreadsheet data for analysis',
                'html': 'HTML - Web format for viewing in browser'
            }
            format_select = ui.select(
                options=format_options,
                value=current_format,
                label='Export Format'
            ).classes('w-full mb-4').props('outlined')

            # Save button
            with ui.row().classes('w-full justify-end mt-4'):
                def save_preferences():
                    save_btn.props('loading disabled')
                    db = next(get_db())
                    try:
                        notification_service = NotificationService(db)
                        notification_service.update_preferences(
                            manager_id=user_id,
                            digest_frequency=frequency_select.value,
                            preferred_hour=hour_select.value if hour_select else current_hour,
                            preferred_day=day_select.value if day_select else current_day,
                            export_format=format_select.value
                        )
                        show_success_dialog('Success', 'Your notification preferences have been saved.')
                    except Exception as e:
                        show_error_dialog('Error', f'Failed to save preferences: {str(e)}')
                    finally:
                        db.close()
                        save_btn.props(remove='loading disabled')

                save_btn = ui.button('Save Preferences', icon='save', on_click=save_preferences).props('color=primary')

        # Digest Queue Info Card
        with ui.card().classes('w-full p-6 mb-4'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('pending_actions', size='md').style('color: #5a6a72')
                ui.label('Pending Notifications').classes('text-lg font-semibold')

            # Get pending count
            db = next(get_db())
            try:
                from sqlalchemy import select, func
                from src.models.pending_notification import PendingNotification
                count_stmt = select(func.count()).select_from(PendingNotification).where(
                    PendingNotification.manager_id == user_id,
                    PendingNotification.sent == False
                )
                pending_count = db.execute(count_stmt).scalar() or 0
            finally:
                db.close()

            if pending_count > 0:
                ui.label(f'You have {pending_count} notification(s) queued for your next digest.').classes('mb-4')

                def send_now():
                    send_btn.props('loading disabled')
                    db = next(get_db())
                    try:
                        notification_service = NotificationService(db)
                        sent_count = notification_service.force_send_digest(user_id)
                        if sent_count > 0:
                            show_success_dialog('Digest Sent', f'Your digest email has been sent with {sent_count} notification(s).')
                        else:
                            show_info_dialog('No Pending', 'There are no pending notifications to send.')
                    except Exception as e:
                        show_error_dialog('Error', f'Failed to send digest: {str(e)}')
                    finally:
                        db.close()
                        send_btn.props(remove='loading disabled')

                send_btn = ui.button('Send Digest Now', icon='send', on_click=send_now).props('outline')
            else:
                ui.label('No pending notifications. All caught up!').classes('text-sm opacity-60')

        # On-Demand Report Generation Card
        with ui.card().classes('w-full p-6 mb-4'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('assessment', size='md').style('color: #c9a227')
                ui.label('Generate Report On-Demand').classes('text-lg font-semibold')

            ui.label('Preview or download a PTO report for your team without waiting for the scheduled digest.').classes('text-sm opacity-60 mb-4')

            # Date range presets
            today = date.today()
            preset_options = {
                'last_7': 'Last 7 Days',
                'last_30': 'Last 30 Days',
                'this_month': 'This Month',
                'last_month': 'Last Month',
                'custom': 'Custom Date Range'
            }
            preset_select = ui.select(
                options=preset_options,
                value='last_30',
                label='Time Period'
            ).classes('w-full mb-4').props('outlined')

            # Custom date range container (shown/hidden based on preset)
            custom_dates_container = ui.column().classes('w-full')

            report_start_date = None
            report_end_date = None

            def update_date_visibility():
                nonlocal report_start_date, report_end_date
                custom_dates_container.clear()

                if preset_select.value == 'custom':
                    with custom_dates_container:
                        with ui.row().classes('w-full gap-4 mb-4'):
                            report_start_date = ui.date(value=today - timedelta(days=30)).props('outlined label="Start Date"').classes('flex-1')
                            report_end_date = ui.date(value=today).props('outlined label="End Date"').classes('flex-1')

            update_date_visibility()
            preset_select.on('update:model-value', lambda e: update_date_visibility())

            # Format selection for download
            report_format_options = {
                'pdf': 'PDF',
                'csv': 'CSV',
                'html': 'HTML'
            }
            report_format_select = ui.select(
                options=report_format_options,
                value=current_format,
                label='Download Format'
            ).classes('w-full mb-4').props('outlined')

            # Preview container
            preview_container = ui.column().classes('w-full')

            def get_date_range():
                """Get start and end dates based on preset selection."""
                preset = preset_select.value
                if preset == 'last_7':
                    return today - timedelta(days=7), today
                elif preset == 'last_30':
                    return today - timedelta(days=30), today
                elif preset == 'this_month':
                    return today.replace(day=1), today
                elif preset == 'last_month':
                    first_of_this_month = today.replace(day=1)
                    last_month_end = first_of_this_month - timedelta(days=1)
                    last_month_start = last_month_end.replace(day=1)
                    return last_month_start, last_month_end
                else:  # custom
                    start = report_start_date.value if report_start_date else today - timedelta(days=30)
                    end = report_end_date.value if report_end_date else today
                    # Handle string dates from date picker
                    if isinstance(start, str):
                        start = date.fromisoformat(start)
                    if isinstance(end, str):
                        end = date.fromisoformat(end)
                    return start, end

            def generate_preview():
                preview_btn.props('loading disabled')
                preview_container.clear()

                start_date, end_date = get_date_range()

                db = next(get_db())
                try:
                    from sqlalchemy import select, and_
                    from src.models.pto_request import PTORequest
                    from src.models.user import User
                    from src.models.department import Department

                    # Get manager's department
                    manager = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
                    if not manager or not manager.department_id:
                        show_error_dialog('Error', 'Unable to determine your department.')
                        return

                    # Get team members in manager's department
                    team_stmt = select(User.id).where(User.department_id == manager.department_id)
                    team_ids = [r[0] for r in db.execute(team_stmt).fetchall()]

                    # Get PTO requests in date range for team
                    requests_stmt = select(PTORequest).where(
                        and_(
                            PTORequest.user_id.in_(team_ids),
                            PTORequest.start_date >= start_date,
                            PTORequest.end_date <= end_date
                        )
                    ).order_by(PTORequest.start_date.desc())

                    requests = db.execute(requests_stmt).scalars().all()

                    with preview_container:
                        with ui.card().classes('w-full p-4').style('border: 1px solid #c9a227'):
                            ui.label(f'Report Preview: {start_date.strftime("%b %d, %Y")} - {end_date.strftime("%b %d, %Y")}').classes('font-semibold mb-3')

                            if not requests:
                                ui.label('No PTO requests found in this date range.').classes('text-sm opacity-60')
                            else:
                                ui.label(f'{len(requests)} request(s) found').classes('text-sm opacity-60 mb-3')

                                # Summary table
                                columns = [
                                    {'name': 'employee', 'label': 'Employee', 'field': 'employee', 'align': 'left'},
                                    {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left'},
                                    {'name': 'dates', 'label': 'Dates', 'field': 'dates', 'align': 'left'},
                                    {'name': 'days', 'label': 'Days', 'field': 'days', 'align': 'center'},
                                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                                ]
                                rows = []
                                for req in requests:
                                    trusted_badge = '✓ ' if req.user.is_trusted else ''
                                    rows.append({
                                        'employee': f'{trusted_badge}{req.user.full_name}',
                                        'type': req.pto_type.title(),
                                        'dates': f'{req.start_date.strftime("%m/%d")} - {req.end_date.strftime("%m/%d")}',
                                        'days': float(req.total_days),
                                        'status': req.status.title()
                                    })

                                ui.table(columns=columns, rows=rows, row_key='employee').classes('w-full').props('dense flat')

                except Exception as e:
                    show_error_dialog('Error', f'Failed to generate preview: {str(e)}')
                finally:
                    db.close()
                    preview_btn.props(remove='loading disabled')

            def download_report():
                download_btn.props('loading disabled')
                start_date, end_date = get_date_range()
                export_format = report_format_select.value

                # Redirect to export endpoint
                ui.navigate.to(f'/api/reports/team-pto?start={start_date.isoformat()}&end={end_date.isoformat()}&format={export_format}', new_tab=True)
                download_btn.props(remove='loading disabled')

            with ui.row().classes('w-full gap-4'):
                preview_btn = ui.button('Preview Report', icon='visibility', on_click=generate_preview).props('outline')
                download_btn = ui.button('Download Report', icon='download', on_click=download_report).props('color=primary')

        # Help Card
        with ui.card().classes('w-full p-6').style('border-left: 4px solid #5a6a72'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon('info', size='sm').classes('opacity-60')
                ui.label('About Notifications').classes('font-semibold')

            ui.markdown('''
**Immediate**: You'll receive an email as soon as any team member submits a PTO request.

**Digest Options**: Notifications are collected and sent as a single summary email at your preferred time. This is useful if you have a large team or prefer batch processing.

**Trusted Employees**: Employees marked as "trusted" have their standard PTO (Vacation, Sick, Personal) auto-approved. You still receive notifications for all requests regardless of auto-approval status.
            ''').classes('text-sm opacity-80')

        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-4')
