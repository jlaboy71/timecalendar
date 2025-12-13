"""Manager settings page for notification preferences."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_error_dialog, show_info_dialog
from src.services.notification_service import NotificationService


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
                                # Hour selector
                                hour_options = {h: f"{h:02d}:00 {'AM' if h < 12 else 'PM'}" for h in range(24)}
                                nonlocal hour_select
                                hour_select = ui.select(
                                    options=hour_options,
                                    value=current_hour,
                                    label='Preferred Hour'
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
                        show_info_dialog('Success', 'Your notification preferences have been saved.')
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
                            show_info_dialog('Digest Sent', f'Your digest email has been sent with {sent_count} notification(s).')
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
