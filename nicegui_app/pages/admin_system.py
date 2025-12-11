"""Super Admin system administration page."""
import os
import platform
import sys as sys_module
from datetime import datetime
from pathlib import Path
from nicegui import ui, app
from src.database import get_db
from src.config import config
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode


def admin_system_page():
    """System administration page content."""
    apply_dark_mode()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role != 'superadmin':
        ui.notify('Access denied - Super Admin only', type='negative')
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        # Header
        page_header(title='SYSTEM ADMINISTRATION', show_back=False)

        # System Status Overview - Quick health check at a glance
        db_url = config.DATABASE_URL
        if db_url.startswith('sqlite:///'):
            db_filename = db_url.replace('sqlite:///', '')
            db_path = Path(__file__).parent.parent.parent / db_filename
        else:
            db_path = Path(__file__).parent.parent.parent / 'tjm_calendar.db'
        db_exists = db_path.exists()

        smtp_configured = os.getenv('SMTP_HOST') is not None
        ai_configured = os.getenv('ANTHROPIC_API_KEY') is not None
        logs_dir = Path(__file__).parent.parent.parent / 'logs'
        has_errors = (logs_dir / 'tjm_calendar_errors.log').exists() and (logs_dir / 'tjm_calendar_errors.log').stat().st_size > 0

        with ui.card().classes('w-full p-4 mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('monitor_heart', size='md', color='blue')
                    ui.label('System Health').classes('text-lg font-bold')

                with ui.row().classes('gap-6'):
                    # Database status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('storage', color='green' if db_exists else 'red')
                        ui.label('Database').classes('text-sm')
                        ui.badge('Online' if db_exists else 'Offline', color='green' if db_exists else 'red')

                    # Email status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('email', color='green' if smtp_configured else 'amber')
                        ui.label('Email').classes('text-sm')
                        ui.badge('Ready' if smtp_configured else 'Not Set', color='green' if smtp_configured else 'amber')

                    # AI status
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('smart_toy', color='green' if ai_configured else 'amber')
                        ui.label('AI').classes('text-sm')
                        ui.badge('Ready' if ai_configured else 'Not Set', color='green' if ai_configured else 'amber')

                    # Errors indicator
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('error_outline', color='red' if has_errors else 'green')
                        ui.label('Errors').classes('text-sm')
                        ui.badge('Check Logs' if has_errors else 'None', color='red' if has_errors else 'green')

        # Tabs for different sections
        with ui.tabs().classes('w-full').props('dense active-color=primary indicator-color=primary') as tabs:
            database_tab = ui.tab('Database', icon='storage')
            email_tab = ui.tab('Email Config', icon='email')
            logs_tab = ui.tab('System Logs', icon='description')
            settings_tab = ui.tab('Settings', icon='tune')

        with ui.tab_panels(tabs, value=database_tab).classes('w-full'):
            # ========== DATABASE TAB ==========
            with ui.tab_panel(database_tab):
                db_size = db_path.stat().st_size / (1024 * 1024) if db_exists else 0  # MB

                # Database Status Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('storage', size='sm', color='blue')
                        ui.label('Database Status').classes('text-lg font-semibold')

                    with ui.row().classes('gap-8 flex-wrap'):
                        # Status indicator
                        with ui.column().classes('min-w-32'):
                            ui.label('Status').classes('text-xs text-gray-500 uppercase tracking-wide')
                            with ui.row().classes('items-center gap-2 mt-1'):
                                ui.icon('check_circle' if db_exists else 'error', color='green' if db_exists else 'red', size='xs')
                                ui.label('Online' if db_exists else 'Offline').classes('font-semibold')

                        # File info
                        with ui.column().classes('min-w-32'):
                            ui.label('File').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(str(db_path.name)).classes('font-mono text-sm mt-1')

                        # Size
                        with ui.column().classes('min-w-32'):
                            ui.label('Size').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(f'{db_size:.2f} MB').classes('font-mono text-sm mt-1')

                        # Location
                        with ui.column().classes('flex-1'):
                            ui.label('Location').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(str(db_path.parent)).classes('font-mono text-xs mt-1 opacity-70 truncate')

                # Backup Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('backup', size='sm', color='green')
                        ui.label('Backup Management').classes('text-lg font-semibold')

                    # Backup info box
                    with ui.row().classes('w-full gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                        with ui.column().classes('flex-1'):
                            ui.label('Backup creates a complete copy of your database').classes('text-sm')
                            with ui.row().classes('gap-4 mt-2'):
                                ui.label(f'Format: {db_path.stem}_YYYYMMDD_HHMMSS.db').classes('text-xs font-mono opacity-70')
                                ui.label('Destination: dbbackup/').classes('text-xs font-mono opacity-70')

                    backup_status = ui.label('').classes('text-sm mb-2')

                    def run_backup():
                        try:
                            backup_status.set_text('Running backup...')
                            backup_dir = Path(__file__).parent.parent.parent / 'dbbackup'
                            backup_dir.mkdir(exist_ok=True)

                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            db_name = db_path.stem  # Get filename without extension
                            backup_file = backup_dir / f'{db_name}_{timestamp}.db'

                            import shutil
                            shutil.copy2(db_path, backup_file)

                            # Verify the backup was created and has the same size
                            if backup_file.exists() and backup_file.stat().st_size == db_path.stat().st_size:
                                backup_status.set_text(f'Backup created: {backup_file.name} ({backup_file.stat().st_size / 1024:.1f} KB)')
                                ui.notify(f'Backup successful: {backup_file.name}', type='positive')
                            else:
                                backup_status.set_text('Warning: Backup size mismatch')
                                ui.notify('Backup created but size differs from source', type='warning')

                            refresh_backups()
                        except Exception as e:
                            backup_status.set_text(f'Error: {str(e)}')
                            ui.notify(f'Backup failed: {str(e)}', type='negative')

                    ui.button('Create Backup Now', icon='backup', on_click=run_backup).props('color=primary')

                # Existing Backups Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('folder_open', size='sm', color='amber')
                            ui.label('Backup History').classes('text-lg font-semibold')
                        ui.button('Refresh', icon='refresh', on_click=lambda: refresh_backups()).props('flat dense')

                    backups_container = ui.column().classes('w-full')

                    def refresh_backups():
                        backups_container.clear()
                        backup_dir = Path(__file__).parent.parent.parent / 'dbbackup'
                        if not backup_dir.exists():
                            with backups_container:
                                with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                                    with ui.column().classes('items-center gap-2'):
                                        ui.icon('folder_off', size='lg', color='gray')
                                        ui.label('No backups yet').classes('text-gray-500')
                                        ui.label('Create your first backup using the button above').classes('text-sm text-gray-400')
                            return

                        backup_files = sorted(backup_dir.glob('*.db'), key=lambda x: x.stat().st_mtime, reverse=True)
                        if not backup_files:
                            with backups_container:
                                with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                                    with ui.column().classes('items-center gap-2'):
                                        ui.icon('folder_off', size='lg', color='gray')
                                        ui.label('No backups found').classes('text-gray-500')
                            return

                        with backups_container:
                            # Summary row with stats
                            total_size = sum(bf.stat().st_size for bf in backup_files)
                            oldest = datetime.fromtimestamp(backup_files[-1].stat().st_mtime).strftime('%Y-%m-%d')
                            newest = datetime.fromtimestamp(backup_files[0].stat().st_mtime).strftime('%Y-%m-%d')
                            with ui.row().classes('w-full items-center justify-between p-3 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg mb-4'):
                                with ui.row().classes('items-center gap-4'):
                                    ui.icon('inventory_2', color='green')
                                    ui.label(f'{len(backup_files)} backup{"s" if len(backup_files) != 1 else ""}').classes('font-semibold')
                                with ui.row().classes('gap-6 text-sm'):
                                    ui.label(f'Total: {total_size / (1024 * 1024):.2f} MB').classes('opacity-70')
                                    ui.label(f'Oldest: {oldest}').classes('opacity-70')
                                    ui.label(f'Latest: {newest}').classes('opacity-70')

                            # Backup list with improved styling
                            for idx, bf in enumerate(backup_files):
                                size_mb = bf.stat().st_size / (1024 * 1024)
                                mtime = datetime.fromtimestamp(bf.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                                is_latest = idx == 0
                                with ui.row().classes(f'w-full items-center gap-4 p-3 border rounded-lg mb-2 {"border-green-300 bg-green-50/50 dark:bg-green-900/10" if is_latest else "hover:bg-gray-50 dark:hover:bg-gray-800"}'):
                                    ui.icon('backup', color='green' if is_latest else 'blue')
                                    with ui.column().classes('flex-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(bf.name).classes('font-mono text-sm')
                                            if is_latest:
                                                ui.badge('Latest', color='green').props('dense')
                                        ui.label(f'{mtime} | {size_mb:.2f} MB').classes('text-xs opacity-70')

                                    # Action buttons
                                    with ui.row().classes('gap-1'):
                                        def create_restore_handler(backup_file):
                                            def restore():
                                                with ui.dialog() as dialog, ui.card().classes('p-6'):
                                                    ui.label('Restore Database').classes('text-lg font-semibold mb-2')
                                                    ui.label(f'Restore from: {backup_file.name}').classes('mb-2')
                                                    with ui.card().classes('w-full p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 mb-4'):
                                                        ui.label('WARNING: This will overwrite the current database!').classes('text-red-600 dark:text-red-400 font-semibold')
                                                        ui.label('Make sure to create a backup of the current database first.').classes('text-sm')

                                                    def confirm_restore():
                                                        try:
                                                            import shutil
                                                            shutil.copy2(backup_file, db_path)
                                                            ui.notify('Database restored successfully. Please restart the application.', type='positive')
                                                            dialog.close()
                                                        except Exception as e:
                                                            ui.notify(f'Restore failed: {str(e)}', type='negative')

                                                    with ui.row().classes('gap-2 justify-end'):
                                                        ui.button('Cancel', on_click=dialog.close).props('flat')
                                                        ui.button('Restore', on_click=confirm_restore, icon='restore').props('color=red')
                                                dialog.open()
                                            return restore

                                        def create_delete_handler(backup_file):
                                            def delete():
                                                with ui.dialog() as dialog, ui.card().classes('p-6'):
                                                    ui.label('Delete Backup').classes('text-lg font-semibold mb-2')
                                                    ui.label(f'Delete: {backup_file.name}').classes('mb-2')
                                                    ui.label('This action cannot be undone.').classes('text-sm opacity-70 mb-4')

                                                    def confirm_delete():
                                                        try:
                                                            backup_file.unlink()
                                                            ui.notify(f'Deleted: {backup_file.name}', type='positive')
                                                            dialog.close()
                                                            refresh_backups()
                                                        except Exception as e:
                                                            ui.notify(f'Delete failed: {str(e)}', type='negative')

                                                    with ui.row().classes('gap-2 justify-end'):
                                                        ui.button('Cancel', on_click=dialog.close).props('flat')
                                                        ui.button('Delete', on_click=confirm_delete, icon='delete').props('color=red')
                                                dialog.open()
                                            return delete

                                        ui.button(icon='restore', on_click=create_restore_handler(bf)).props('flat dense aria-label="Restore this backup"').tooltip('Restore this backup')
                                        ui.button(icon='delete', on_click=create_delete_handler(bf)).props('flat dense color=red aria-label="Delete this backup"').tooltip('Delete this backup')

                    refresh_backups()

                # Market Calendar Sync Card
                with ui.card().classes('w-full p-4 mt-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('event', size='sm', color='purple')
                        ui.label('Market Calendar Sync').classes('text-lg font-semibold')

                    ui.label('Sync market holidays for NYSE, CME, CBOE, and Federal holidays.').classes('text-sm opacity-70 mb-4')

                    # Current year and next year
                    current_year = datetime.now().year
                    sync_status_label = ui.label('').classes('text-sm mb-2')
                    sync_results_container = ui.column().classes('w-full')

                    def show_holidays_dialog(year: int):
                        """Show dialog with all holidays for the selected year."""
                        from src.models.market_holiday import MarketHoliday
                        db_session = next(get_db())
                        try:
                            holidays = db_session.query(MarketHoliday).filter(
                                MarketHoliday.year == year
                            ).order_by(MarketHoliday.holiday_date, MarketHoliday.market).all()

                            # Group by date
                            from collections import defaultdict
                            holidays_by_date = defaultdict(list)
                            for h in holidays:
                                holidays_by_date[h.holiday_date].append(h)

                            with ui.dialog() as dialog, ui.card().classes('min-w-[600px] max-h-[80vh]'):
                                with ui.row().classes('w-full justify-between items-center mb-4'):
                                    ui.label(f'{year} Holidays ({len(holidays)} records)').classes('text-xl font-bold')
                                    ui.button(icon='close', on_click=dialog.close).props('flat round')

                                with ui.scroll_area().classes('w-full max-h-[60vh]'):
                                    with ui.column().classes('w-full gap-2'):
                                        for holiday_date in sorted(holidays_by_date.keys()):
                                            h_list = holidays_by_date[holiday_date]
                                            markets = [h.market for h in h_list]
                                            name = h_list[0].name

                                            with ui.card().classes('w-full p-3'):
                                                with ui.row().classes('w-full items-center justify-between'):
                                                    with ui.column().classes('gap-0'):
                                                        ui.label(name).classes('font-semibold')
                                                        ui.label(holiday_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                    with ui.row().classes('gap-1'):
                                                        for market in markets:
                                                            color = 'red' if market == 'Federal' else 'blue' if market == 'NYSE' else 'green' if market == 'CME' else 'purple'
                                                            ui.badge(market, color=color).classes('text-xs')

                                with ui.row().classes('w-full justify-end mt-4'):
                                    ui.button('Close', on_click=dialog.close).props('flat')

                            dialog.open()
                        finally:
                            db_session.close()

                    def sync_market_holidays(year: int):
                        """Sync market holidays for a specific year."""
                        sync_status_label.set_text(f'Syncing {year} holidays...')
                        try:
                            from src.services.market_calendar_service import MarketCalendarService
                            db_session = next(get_db())
                            service = MarketCalendarService(db_session=db_session)
                            result = service.sync_market_holidays(year)
                            db_session.close()

                            if result.success:
                                source_display = result.source.value.replace('_', ' ').title()
                                msg = f'{year}: Synced {result.count} holidays from {source_display}'
                                if result.warning:
                                    msg += f' (Warning: {result.warning})'
                                    ui.notify(msg, type='warning')
                                else:
                                    ui.notify(msg, type='positive')
                                sync_status_label.set_text(msg)
                            else:
                                ui.notify(f'Sync failed: {result.error}', type='negative')
                                sync_status_label.set_text(f'Error: {result.error}')

                            refresh_holiday_stats()
                        except Exception as e:
                            sync_status_label.set_text(f'Error: {str(e)}')
                            ui.notify(f'Sync error: {str(e)}', type='negative')

                    def refresh_holiday_stats():
                        """Refresh the holiday statistics display."""
                        sync_results_container.clear()
                        try:
                            from src.models.market_holiday import MarketHoliday
                            db_session = next(get_db())
                            with sync_results_container:
                                # Show stats for current and next year
                                for year in [current_year, current_year + 1]:
                                    count = db_session.query(MarketHoliday).filter(MarketHoliday.year == year).count()
                                    markets = db_session.query(MarketHoliday.market).filter(
                                        MarketHoliday.year == year
                                    ).distinct().all()
                                    market_list = ', '.join([m[0] for m in markets]) if markets else 'None'

                                    color = 'green' if count > 0 else 'gray'
                                    with ui.row().classes(f'w-full items-center gap-4 p-3 bg-{color}-50 dark:bg-{color}-900/20 rounded-lg mb-2'):
                                        ui.icon('calendar_month', color=color)
                                        with ui.column().classes('flex-1'):
                                            ui.label(f'{year}').classes('font-semibold')
                                            ui.label(f'{count} holidays | Markets: {market_list}').classes('text-xs opacity-70')
                                        with ui.row().classes('gap-1'):
                                            if count > 0:
                                                ui.button('View', icon='visibility', on_click=lambda y=year: show_holidays_dialog(y)).props('flat dense color=primary')
                                            ui.button('Sync', icon='sync', on_click=lambda y=year: sync_market_holidays(y)).props('flat dense')
                            db_session.close()
                        except Exception as e:
                            with sync_results_container:
                                ui.label(f'Error loading stats: {e}').classes('text-red-500')

                    # Sync buttons
                    with ui.row().classes('gap-2 mb-4'):
                        ui.button(f'Sync {current_year}', icon='sync', on_click=lambda: sync_market_holidays(current_year)).props('color=primary')
                        ui.button(f'Sync {current_year + 1}', icon='sync', on_click=lambda: sync_market_holidays(current_year + 1)).props('color=secondary')

                    refresh_holiday_stats()

            # ========== EMAIL CONFIG TAB ==========
            with ui.tab_panel(email_tab):
                # Current config values
                smtp_host = os.getenv('SMTP_HOST', '')
                smtp_port = os.getenv('SMTP_PORT', '')
                smtp_user = os.getenv('SMTP_USER', '')
                smtp_from = os.getenv('SMTP_FROM', '')
                email_configured = bool(smtp_host)

                # Status Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('email', size='sm', color='blue')
                        ui.label('Email Service Status').classes('text-lg font-semibold')

                    # Status banner
                    if email_configured:
                        with ui.row().classes('w-full p-4 bg-green-50 dark:bg-green-900/20 rounded-lg items-center gap-3'):
                            ui.icon('check_circle', color='green', size='md')
                            with ui.column().classes('flex-1'):
                                ui.label('Email service is configured').classes('font-semibold text-green-700 dark:text-green-400')
                                ui.label('Your application can send notification emails').classes('text-sm opacity-70')
                    else:
                        with ui.row().classes('w-full p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg items-center gap-3'):
                            ui.icon('warning', color='amber', size='md')
                            with ui.column().classes('flex-1'):
                                ui.label('Email service not configured').classes('font-semibold text-amber-700 dark:text-amber-400')
                                ui.label('Configure SMTP settings to enable email notifications').classes('text-sm opacity-70')

                # Configuration Details Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings', size='sm', color='gray')
                        ui.label('SMTP Configuration').classes('text-lg font-semibold')

                    with ui.row().classes('gap-8 flex-wrap'):
                        with ui.column().classes('min-w-40'):
                            ui.label('Host').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_host or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_host else ""}')

                        with ui.column().classes('min-w-20'):
                            ui.label('Port').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_port or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_port else ""}')

                        with ui.column().classes('min-w-40'):
                            ui.label('User').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_user or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_user else ""}')

                        with ui.column().classes('flex-1'):
                            ui.label('From Address').classes('text-xs text-gray-500 uppercase tracking-wide')
                            ui.label(smtp_from or 'Not set').classes(f'font-mono text-sm mt-1 {"opacity-50" if not smtp_from else ""}')

                # Test Email Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('send', size='sm', color='green')
                        ui.label('Test Email').classes('text-lg font-semibold')

                    ui.label('Send a test email to verify your configuration').classes('text-sm opacity-70 mb-4')

                    with ui.row().classes('items-center gap-4'):
                        test_email_input = ui.input(placeholder='Enter recipient email address').props('outlined dense').classes('w-80')

                        def send_test_email():
                            if not test_email_input.value:
                                ui.notify('Please enter an email address', type='warning')
                                return
                            if not email_configured:
                                ui.notify('SMTP not configured. Set environment variables first.', type='negative')
                                return

                            ui.notify('Sending test email...', type='info')
                            try:
                                from src.services.email_service import email_service
                                success = email_service.send_email(
                                    to_email=test_email_input.value,
                                    subject='TJM Calendar - Test Email',
                                    body='This is a test email from the TJM Time Calendar system.\n\nIf you received this, your email configuration is working correctly!'
                                )
                                if success:
                                    ui.notify('Test email sent successfully!', type='positive')
                                else:
                                    ui.notify('Failed to send email - check logs', type='negative')
                            except Exception as e:
                                ui.notify(f'Error: {str(e)}', type='negative')

                        ui.button('Send Test', icon='send', on_click=send_test_email).props('color=primary')

                # Setup Guide Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('help_outline', size='sm', color='blue')
                        ui.label('Setup Guide').classes('text-lg font-semibold')

                    with ui.expansion('How to Configure Email', icon='menu_book').classes('w-full'):
                        ui.markdown('''
**Add these to your `.env` file:**

```
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@company.com
```

**Common SMTP Providers:**

| Provider | Host | Port |
|----------|------|------|
| Gmail | smtp.gmail.com | 587 |
| Microsoft 365 | smtp.office365.com | 587 |
| Amazon SES | email-smtp.us-east-1.amazonaws.com | 587 |

*Restart the application after updating `.env`*
                        ''')

            # ========== LOGS TAB ==========
            with ui.tab_panel(logs_tab):
                # Log file paths (reuse logs_dir from status overview)
                main_log_path = logs_dir / 'tjm_calendar.log'
                error_log_path = logs_dir / 'tjm_calendar_errors.log'

                # State for current log and AI analysis
                log_state = {'current_log': 'main', 'current_content': ''}

                # Log Files Overview Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('description', size='sm', color='blue')
                        ui.label('Log Files').classes('text-lg font-semibold')

                    # Container for log file cards (will be refreshed dynamically)
                    log_cards_container = ui.row().classes('w-full gap-4')

                    # AI Analysis results container (declared early for refresh_log_cards reference)
                    ai_analysis_container = ui.column().classes('w-full')
                    ai_analysis_container.set_visibility(False)

                    def refresh_log_cards():
                        """Refresh the log file cards with current sizes."""
                        log_cards_container.clear()

                        # Get current file info
                        main_exists = main_log_path.exists()
                        main_size = main_log_path.stat().st_size / 1024 if main_exists else 0
                        error_exists = error_log_path.exists()
                        error_size = error_log_path.stat().st_size / 1024 if error_exists else 0

                        with log_cards_container:
                            # Main log card
                            def switch_to_main():
                                log_state['current_log'] = 'main'
                                refresh_logs()
                                refresh_log_cards()
                                ai_analysis_container.clear()
                                ai_analysis_container.set_visibility(False)

                            with ui.card().classes('p-4 cursor-pointer hover:shadow-md transition-shadow flex-1').on('click', switch_to_main):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('article', color='blue', size='md')
                                    with ui.column().classes('flex-1'):
                                        ui.label('Application Log').classes('font-semibold')
                                        ui.label('General application events and info').classes('text-xs opacity-70')
                                    with ui.column().classes('items-end'):
                                        ui.label(f'{main_size:.1f} KB').classes('font-mono text-sm')
                                        ui.badge('Active' if main_exists and main_size > 0 else 'Empty', color='green' if main_exists and main_size > 0 else 'gray').props('dense')

                            # Error log card
                            def switch_to_errors():
                                log_state['current_log'] = 'errors'
                                refresh_logs()
                                refresh_log_cards()
                                ai_analysis_container.clear()
                                ai_analysis_container.set_visibility(False)

                            error_has_content = error_exists and error_size > 0
                            with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow flex-1 {"border-red-300 border-2" if error_has_content else ""}').on('click', switch_to_errors):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('error_outline', color='red', size='md')
                                    with ui.column().classes('flex-1'):
                                        ui.label('Error Log').classes('font-semibold')
                                        ui.label('Errors and exceptions only').classes('text-xs opacity-70')
                                    with ui.column().classes('items-end'):
                                        ui.label(f'{error_size:.1f} KB').classes('font-mono text-sm')
                                        if error_has_content:
                                            ui.badge('Has Errors', color='red').props('dense')
                                        else:
                                            ui.badge('Clear', color='green').props('dense')

                    # Initial render
                    refresh_log_cards()

                # Log Viewer Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('terminal', size='sm', color='gray')
                            current_log_label = ui.label('Viewing: Application Log').classes('text-lg font-semibold')

                        def refresh_all():
                            refresh_logs()
                            refresh_log_cards()

                        # Auto-refresh state
                        auto_refresh_state = {'enabled': False, 'timer': None}

                        def toggle_auto_refresh():
                            auto_refresh_state['enabled'] = not auto_refresh_state['enabled']
                            if auto_refresh_state['enabled']:
                                auto_refresh_btn.props('color=green')
                                auto_refresh_label.set_text('Live')
                                # Start auto-refresh timer
                                auto_refresh_state['timer'] = ui.timer(2.0, refresh_all)
                            else:
                                auto_refresh_btn.props('color=gray')
                                auto_refresh_label.set_text('Auto')
                                # Stop timer
                                if auto_refresh_state['timer']:
                                    auto_refresh_state['timer'].cancel()
                                    auto_refresh_state['timer'] = None

                        with ui.row().classes('gap-2 items-center'):
                            with ui.row().classes('items-center gap-1'):
                                auto_refresh_btn = ui.button(icon='sync', on_click=toggle_auto_refresh).props('flat dense round color=gray aria-label="Toggle auto-refresh"')
                                auto_refresh_label = ui.label('Auto').classes('text-xs')
                            ui.button('Refresh', icon='refresh', on_click=refresh_all).props('flat dense')

                    # Log viewer (tall to fill the viewing area)
                    log_display = ui.textarea('').props('outlined readonly').classes('w-full font-mono text-xs bg-gray-50 dark:bg-gray-900').style('height: 380px;')

                    def get_current_log_path():
                        return error_log_path if log_state['current_log'] == 'errors' else main_log_path

                    def refresh_logs(lines=100):
                        log_path = get_current_log_path()
                        # Update the label
                        if log_state['current_log'] == 'errors':
                            current_log_label.set_text('Viewing: Error Log')
                        else:
                            current_log_label.set_text('Viewing: Application Log')

                        if not log_path.exists():
                            log_display.value = 'Log file not found. Logs will appear after application activity.'
                            log_state['current_content'] = ''
                            return
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                                all_lines = f.readlines()
                                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                                content = ''.join(recent)
                                log_display.value = content
                                log_state['current_content'] = content
                        except Exception as e:
                            log_display.value = f'Error reading log: {str(e)}'
                            log_state['current_content'] = ''

                    # Controls row
                    with ui.row().classes('w-full justify-between items-center mt-3'):
                        with ui.row().classes('gap-2'):
                            ui.label('Show:').classes('text-sm opacity-70')
                            ui.button('50 lines', on_click=lambda: refresh_logs(50)).props('flat dense size=sm')
                            ui.button('100 lines', on_click=lambda: refresh_logs(100)).props('flat dense size=sm')
                            ui.button('500 lines', on_click=lambda: refresh_logs(500)).props('flat dense size=sm')

                        def clear_current_log():
                            log_path = get_current_log_path()
                            if log_path.exists():
                                try:
                                    with open(log_path, 'w') as f:
                                        f.write('')
                                    ui.notify('Log cleared', type='positive')
                                    refresh_logs()
                                    refresh_log_cards()  # Update the file size display
                                except Exception as e:
                                    ui.notify(f'Error: {str(e)}', type='negative')

                        ui.button('Clear Log', icon='delete_sweep', on_click=clear_current_log).props('flat dense color=red')

                    refresh_logs()

                # AI Analysis Section
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('smart_toy', size='sm', color='purple')
                        ui.label('AI Log Analysis').classes('text-lg font-semibold')
                        if ai_configured:
                            ui.badge('Ready', color='green').props('dense')
                        else:
                            ui.badge('Not Configured', color='amber').props('dense')

                    ui.label('Get an AI-powered summary of your logs or analyze specific sections.').classes('text-sm opacity-70 mb-4')

                    # Two equal cards - using table layout for perfect alignment
                    with ui.element('div').style('display: table; width: 100%; table-layout: fixed;'):
                        with ui.element('div').style('display: table-row;'):
                            # Full log analysis card (left cell)
                            with ui.element('div').style('display: table-cell; width: 50%; padding-right: 8px; vertical-align: top;'):
                                with ui.card().classes('w-full p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20').style('height: 240px;'):
                                    with ui.column().classes('h-full'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('analytics', color='blue')
                                            ui.label('Full Log Analysis').classes('font-semibold')
                                        ui.label('Analyze the entire visible log content').classes('text-xs opacity-70 mb-2')
                                        # Spacer to match the textarea height in the right card
                                        ui.element('div').classes('flex-grow').style('min-height: 56px;')

                                        def analyze_full_log():
                                            if not log_state['current_content']:
                                                ui.notify('No log content to analyze', type='warning')
                                                return
                                            run_ai_analysis(log_state['current_content'], is_selection=False)

                                        ui.button('Analyze Log', icon='play_arrow', on_click=analyze_full_log).props('color=primary')

                            # Selection analysis card (right cell)
                            with ui.element('div').style('display: table-cell; width: 50%; padding-left: 8px; vertical-align: top;'):
                                with ui.card().classes('w-full p-4 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20').style('height: 240px;'):
                                    with ui.column().classes('h-full'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('highlight_alt', color='purple')
                                            ui.label('Selection Analysis').classes('font-semibold')
                                        ui.label('Paste a specific section for focused analysis').classes('text-xs opacity-70 mb-2')
                                        selection_input = ui.textarea(
                                            placeholder='Paste log content here...'
                                        ).classes('w-full').props('outlined dense rows=2').style('width: 100%;')

                                        def analyze_selection():
                                            if not selection_input.value.strip():
                                                ui.notify('Please paste some log content to analyze', type='warning')
                                                return
                                            run_ai_analysis(selection_input.value.strip(), is_selection=True)

                                        ui.button('Analyze Selection', icon='psychology', on_click=analyze_selection).props('color=secondary')

                    def run_ai_analysis(content: str, is_selection: bool = False):
                        """Run AI analysis on log content."""
                        ai_analysis_container.clear()
                        ai_analysis_container.set_visibility(True)

                        # Show loading state
                        with ai_analysis_container:
                            with ui.card().classes('w-full p-4 border-l-4 border-blue-500'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.spinner('dots', size='sm')
                                    ui.label('Analyzing logs... This may take a moment.').classes('text-sm')

                        try:
                            import anthropic
                            api_key = os.getenv('ANTHROPIC_API_KEY')

                            if not api_key:
                                ai_analysis_container.clear()
                                with ai_analysis_container:
                                    with ui.card().classes('w-full p-4 border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20'):
                                        ui.label('AI Analysis Unavailable').classes('font-semibold text-amber-700 dark:text-amber-400')
                                        ui.label('ANTHROPIC_API_KEY not configured in .env file.').classes('text-sm')
                                return

                            client = anthropic.Anthropic(api_key=api_key)

                            # Truncate if too long
                            max_chars = 8000
                            truncated = False
                            analysis_content = content
                            if len(analysis_content) > max_chars:
                                analysis_content = analysis_content[-max_chars:]
                                truncated = True

                            context = "a specific selection from the" if is_selection else "the recent"

                            prompt = f"""Analyze {context} application log below and provide a concise summary for a system administrator.

Your analysis should include:
1. **Overview**: Brief summary of what's happening in the log (1-2 sentences)
2. **Key Events**: Important events or activities (logins, requests, database operations)
3. **Errors/Warnings**: Any errors, warnings, or concerning patterns (highlight severity)
4. **Recommendations**: Any suggested actions if issues are found

Keep it concise and actionable. Use bullet points. If the log shows normal operation with no issues, say so briefly.

{"Note: Log was truncated to last " + str(max_chars) + " characters." if truncated else ""}

LOG CONTENT:
{analysis_content}"""

                            response = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1024,
                                messages=[{"role": "user", "content": prompt}]
                            )

                            analysis_text = response.content[0].text

                            ai_analysis_container.clear()
                            with ai_analysis_container:
                                with ui.card().classes('w-full p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-900/10'):
                                    with ui.row().classes('w-full justify-between items-center mb-3'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('check_circle', color='green')
                                            ui.label('AI Analysis Complete').classes('font-semibold text-green-700 dark:text-green-400')
                                        ui.label(f'{"Selection" if is_selection else "Full Log"} Analysis').classes('text-xs opacity-60')

                                    ui.markdown(analysis_text).classes('text-sm')

                                    with ui.row().classes('w-full justify-end mt-3'):
                                        ui.button('Close', icon='close', on_click=lambda: ai_analysis_container.set_visibility(False)).props('flat dense')

                            ui.notify('Analysis complete', type='positive')

                        except Exception as e:
                            ai_analysis_container.clear()
                            with ai_analysis_container:
                                with ui.card().classes('w-full p-4 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20'):
                                    ui.label('Analysis Failed').classes('font-semibold text-red-700 dark:text-red-400')
                                    ui.label(f'Error: {str(e)}').classes('text-sm')
                            ui.notify(f'Analysis failed: {str(e)}', type='negative')

            # ========== SETTINGS TAB ==========
            with ui.tab_panel(settings_tab):
                # Security Settings Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('security', size='sm', color='blue')
                        ui.label('Security Settings').classes('text-lg font-semibold')

                    debug_val = os.getenv('DEBUG', 'false')
                    secret = os.getenv('SECRET_KEY', '')
                    timeout = os.getenv('SESSION_TIMEOUT_MINUTES', '30')

                    with ui.row().classes('gap-4 flex-wrap'):
                        # Debug Mode
                        with ui.card().classes(f'p-4 flex-1 min-w-48 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if debug_val.lower() == "true" else "bg-green-50 dark:bg-green-900/20"}'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('bug_report', color='red' if debug_val.lower() == 'true' else 'green')
                                ui.label('Debug Mode').classes('font-semibold')
                            if debug_val.lower() == 'true':
                                ui.badge('ENABLED', color='red')
                                ui.label('Disable in production!').classes('text-xs text-red-600 dark:text-red-400 mt-1')
                            else:
                                ui.badge('Disabled', color='green')
                                ui.label('Production ready').classes('text-xs opacity-70 mt-1')

                        # Secret Key
                        with ui.card().classes(f'p-4 flex-1 min-w-48 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if not (secret and len(secret) > 20) else "bg-green-50 dark:bg-green-900/20"}'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('key', color='green' if secret and len(secret) > 20 else 'red')
                                ui.label('Secret Key').classes('font-semibold')
                            if secret and len(secret) > 20:
                                ui.badge('Configured', color='green')
                                ui.label(f'{len(secret)} characters').classes('text-xs opacity-70 mt-1')
                            else:
                                ui.badge('Weak/Missing', color='red')
                                ui.label('Set a strong key in .env').classes('text-xs text-red-600 dark:text-red-400 mt-1')

                        # Session Timeout
                        with ui.card().classes('p-4 flex-1 min-w-48 bg-gray-50 dark:bg-gray-800'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('timer', color='blue')
                                ui.label('Session Timeout').classes('font-semibold')
                            ui.label(f'{timeout} minutes').classes('font-mono text-lg')
                            ui.label('User inactivity limit').classes('text-xs opacity-70 mt-1')

                # Environment Variables Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings_applications', size='sm', color='amber')
                        ui.label('Environment Configuration').classes('text-lg font-semibold')

                    # Environment vars as a cleaner table
                    env_vars = [
                        ('SECRET_KEY', os.getenv('SECRET_KEY'), 'Security', 'key'),
                        ('DEBUG', os.getenv('DEBUG', 'false'), 'Development', 'bug_report'),
                        ('DATABASE_URL', os.getenv('DATABASE_URL'), 'Database', 'storage'),
                        ('SMTP_HOST', os.getenv('SMTP_HOST'), 'Email', 'email'),
                        ('ANTHROPIC_API_KEY', os.getenv('ANTHROPIC_API_KEY'), 'AI', 'smart_toy'),
                        ('LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO'), 'Logging', 'description'),
                    ]

                    with ui.element('div').classes('w-full rounded-lg overflow-hidden border'):
                        for i, (var_name, var_val, category, icon) in enumerate(env_vars):
                            is_set = bool(var_val)
                            display_val = 'Configured' if var_val and var_name in ['SECRET_KEY', 'ANTHROPIC_API_KEY', 'DATABASE_URL'] else (var_val or 'Not set')
                            with ui.row().classes(f'w-full justify-between items-center p-3 {"bg-gray-50 dark:bg-gray-800" if i % 2 == 0 else ""}'):
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon(icon, color='green' if is_set else 'gray', size='xs')
                                    with ui.column():
                                        ui.label(var_name).classes('font-mono text-sm')
                                        ui.label(category).classes('text-xs opacity-50')
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(display_val).classes(f'text-sm {"font-mono" if var_val else "opacity-50"}')
                                    ui.icon('check_circle' if is_set else 'cancel', color='green' if is_set else 'gray', size='xs')

                # System Information Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('computer', size='sm', color='gray')
                        ui.label('System Information').classes('text-lg font-semibold')

                    with ui.row().classes('gap-4 flex-wrap'):
                        # Python
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-blue-50 dark:bg-blue-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('code', color='blue')
                                ui.label('Python').classes('font-semibold')
                            ui.label(sys_module.version.split()[0]).classes('font-mono text-lg')

                        # Platform
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-green-50 dark:bg-green-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('laptop', color='green')
                                ui.label('Platform').classes('font-semibold')
                            ui.label(platform.system()).classes('font-mono text-lg')

                        # Architecture
                        with ui.card().classes('p-4 flex-1 min-w-40 bg-purple-50 dark:bg-purple-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('memory', color='purple')
                                ui.label('Architecture').classes('font-semibold')
                            ui.label(platform.machine()).classes('font-mono text-lg')

                        # NiceGUI Version
                        try:
                            import nicegui
                            nicegui_version = nicegui.__version__
                        except Exception:
                            nicegui_version = 'Unknown'

                        with ui.card().classes('p-4 flex-1 min-w-40 bg-amber-50 dark:bg-amber-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('web', color='amber')
                                ui.label('NiceGUI').classes('font-semibold')
                            ui.label(nicegui_version).classes('font-mono text-lg')

        # Back button
        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline')
