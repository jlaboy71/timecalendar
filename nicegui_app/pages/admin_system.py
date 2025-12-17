"""Super Admin system administration page."""
import os
import platform
import sys as sys_module
from datetime import datetime
from pathlib import Path
from nicegui import ui, app
from src.database import get_db
from src.config import config
from src.services.audit_service import AuditService
from src.models.audit_log import AuditLog
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog, show_info_dialog, create_help_button


def admin_system_page():
    """System administration page content."""
    apply_dark_mode()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role != 'superadmin':
        show_error_dialog('Access Denied', 'Super Admin role is required to access this page.')
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

        # Tabs for different sections (logical order: data, policies, operations, reporting, config)
        with ui.tabs().classes('w-full').props('dense active-color=primary indicator-color=primary') as tabs:
            database_tab = ui.tab('Database', icon='storage')
            handbook_tab = ui.tab('Handbook', icon='menu_book')
            eoy_tab = ui.tab('EOY Processing', icon='event_repeat')
            analytics_tab = ui.tab('Analytics', icon='analytics')
            autonotify_tab = ui.tab('Auto Notify', icon='notifications_active')
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
                        create_help_button(
                            'Database Status',
                            'Shows the current state of the application database.<br><br>'
                            '<b>Status:</b> Whether the database file exists and is accessible.<br>'
                            '<b>File:</b> The database filename (SQLite .db file).<br>'
                            '<b>Size:</b> Current size of the database file.<br>'
                            '<b>Location:</b> Full path to where the database is stored.<br><br>'
                            '<i>A healthy database shows "Online" status with a green indicator.</i>'
                        )

                    # Use CSS grid for perfect edge-to-edge alignment (4 columns)
                    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;'):
                        # Status indicator
                        with ui.card().classes(f'p-4 {"bg-green-50 dark:bg-green-900/20" if db_exists else "bg-red-50 dark:bg-red-900/20"}'):
                            ui.label('Status').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('check_circle' if db_exists else 'error', color='green' if db_exists else 'red', size='sm')
                                ui.label('Online' if db_exists else 'Offline').classes('font-semibold text-lg')

                        # File info
                        with ui.card().classes('p-4 bg-blue-50 dark:bg-blue-900/20'):
                            ui.label('File').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            ui.label(str(db_path.name)).classes('font-mono text-sm')

                        # Size
                        with ui.card().classes('p-4 bg-purple-50 dark:bg-purple-900/20'):
                            ui.label('Size').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            ui.label(f'{db_size:.2f} MB').classes('font-mono text-lg font-semibold')

                        # Location
                        with ui.card().classes('p-4 bg-gray-50 dark:bg-gray-800'):
                            ui.label('Location').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            ui.label(str(db_path.parent)).classes('font-mono text-xs opacity-70 truncate').tooltip(str(db_path.parent))

                # Backup Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('backup', size='sm', color='green')
                        ui.label('Backup Management').classes('text-lg font-semibold')
                        create_help_button(
                            'Backup Management',
                            'Create complete copies of your database for disaster recovery.<br><br>'
                            '<b>How it works:</b><br>'
                            '• Click "Create Backup Now" to make an instant copy<br>'
                            '• Backups are timestamped (YYYYMMDD_HHMMSS format)<br>'
                            '• Stored in the <code style="background: #374151; padding: 2px 6px; border-radius: 4px;">dbbackup/</code> folder<br><br>'
                            '<b>Best practices:</b><br>'
                            '• Create a backup before major changes<br>'
                            '• Create a backup before year-end processing<br>'
                            '• Periodically download backups to external storage<br><br>'
                            '<i>Backups include all employee data, PTO records, and settings.</i>'
                        )

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
                                show_success_dialog('Backup Complete', f'Backup successful: {backup_file.name}')
                            else:
                                backup_status.set_text('Warning: Backup size mismatch')
                                show_warning_dialog('Backup Warning', 'Backup was created but the size differs from the source database.')

                            refresh_backups()
                        except Exception as e:
                            backup_status.set_text(f'Error: {str(e)}')
                            show_error_dialog('Backup Failed', f'Error creating backup: {str(e)}')

                    ui.button('Create Backup Now', icon='backup', on_click=run_backup).props('color=primary')

                # Existing Backups Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('folder_open', size='sm', color='amber')
                            ui.label('Backup History').classes('text-lg font-semibold')
                            create_help_button(
                                'Backup History',
                                'View and manage all database backups.<br><br>'
                                '<b>Actions available:</b><br>'
                                '• <b>Restore</b> - Replace current database with a backup (requires app restart)<br>'
                                '• <b>Delete</b> - Remove a backup file permanently<br><br>'
                                '<b>Tips:</b><br>'
                                '• The "Latest" badge indicates the most recent backup<br>'
                                '• Always create a new backup before restoring an old one<br>'
                                '• Summary shows total backups, storage used, and date range<br><br>'
                                '<span style="color: #ef4444;"><b>Warning:</b> Restoring a backup will overwrite all current data!</span>'
                            )
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
                                                            show_success_dialog('Restore Complete', 'Database restored successfully. Please restart the application.')
                                                            dialog.close()
                                                        except Exception as e:
                                                            show_error_dialog('Restore Failed', f'Error restoring database: {str(e)}')

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
                                                            show_success_dialog('Deleted', f'Deleted: {backup_file.name}')
                                                            dialog.close()
                                                            refresh_backups()
                                                        except Exception as e:
                                                            show_error_dialog('Delete Failed', f'Error deleting backup: {str(e)}')

                                                    with ui.row().classes('gap-2 justify-end'):
                                                        ui.button('Cancel', on_click=dialog.close).props('flat')
                                                        ui.button('Delete', on_click=confirm_delete, icon='delete').props('color=red')
                                                dialog.open()
                                            return delete

                                        ui.button(icon='restore', on_click=create_restore_handler(bf)).props('flat dense aria-label="Restore this backup"').tooltip('Restore this backup')
                                        ui.button(icon='delete', on_click=create_delete_handler(bf)).props('flat dense color=red aria-label="Delete this backup"').tooltip('Delete this backup')

                    refresh_backups()

                # Market Calendar Sync Card with Visual Feedback
                with ui.card().classes('w-full p-4 mt-4'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('event', size='sm', color='purple')
                        ui.label('Market Calendar Sync').classes('text-lg font-semibold')
                        create_help_button(
                            'Market Calendar Sync',
                            'Import market holidays for NYSE, CME, CBOE, and Federal calendars.<br><br>'
                            '<b>Data Sources (in priority order):</b><br>'
                            '1. <b>pandas_market_calendars</b> - Official exchange data (primary)<br>'
                            '2. <b>Web Sources</b> - Fallback to exchange websites (planned)<br>'
                            '3. <b>Static Calculation</b> - Algorithm-based dates (works offline)<br><br>'
                            '<b>How to use:</b><br>'
                            '• Click "Sync" to preview holidays before importing<br>'
                            '• Review all dates in the preview dialog<br>'
                            '• Confirm to save holidays to the database<br><br>'
                            '<b>Important:</b> Market holidays affect PTO calendar display - dates marked as closures show differently on the calendar.'
                        )

                    ui.label('Sync market holidays for NYSE, CME, CBOE, and Federal holidays with preview before import.').classes('text-sm opacity-70 mb-4')

                    # Current year and next year
                    current_year = datetime.now().year
                    sync_results_container = ui.column().classes('w-full')

                    def show_holidays_dialog(year: int):
                        """Show dialog with all holidays for the selected year (grouped by date)."""
                        from src.models.market_holiday import MarketHoliday
                        from collections import defaultdict
                        db_session = next(get_db())
                        try:
                            holidays = db_session.query(MarketHoliday).filter(
                                MarketHoliday.year == year
                            ).order_by(MarketHoliday.holiday_date, MarketHoliday.market).all()

                            # Group by date
                            holidays_by_date = defaultdict(list)
                            for h in holidays:
                                holidays_by_date[h.holiday_date].append(h)

                            # Count unique holiday dates
                            unique_dates = len(holidays_by_date)
                            trading_floor_markets = {'NYSE', 'CME', 'CBOE'}

                            with ui.dialog() as dialog, ui.card().classes('min-w-[750px] max-h-[85vh] p-0'):
                                # Header
                                with ui.row().classes('w-full p-4 items-center justify-between').style('background-color: #7c3aed'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'{year} Holidays').classes('text-xl font-bold text-white')
                                        ui.label(f'{unique_dates} unique dates ({len(holidays)} market records)').classes('text-sm text-white opacity-80')
                                    ui.button(icon='close', on_click=dialog.close).props('flat round').style('color: white')

                                with ui.column().classes('w-full p-4'):
                                    # Legend
                                    with ui.row().classes('w-full items-center gap-4 mb-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg'):
                                        ui.icon('info', color='gray', size='xs')
                                        ui.label('Markets:').classes('text-sm font-semibold')
                                        with ui.row().classes('items-center gap-1'):
                                            ui.element('div').classes('w-3 h-3 rounded').style('background-color: #3b82f6')
                                            ui.label('NYSE').classes('text-xs')
                                        with ui.row().classes('items-center gap-1'):
                                            ui.element('div').classes('w-3 h-3 rounded').style('background-color: #22c55e')
                                            ui.label('CME').classes('text-xs')
                                        with ui.row().classes('items-center gap-1'):
                                            ui.element('div').classes('w-3 h-3 rounded').style('background-color: #a855f7')
                                            ui.label('CBOE').classes('text-xs')
                                        with ui.row().classes('items-center gap-1'):
                                            ui.element('div').classes('w-3 h-3 rounded').style('background-color: #ef4444')
                                            ui.label('Federal').classes('text-xs')
                                        ui.element('div').classes('flex-1')
                                        ui.icon('storefront', color='blue', size='xs')
                                        ui.label('= Trading floor closed').classes('text-xs opacity-70')

                                    # Grouped holidays list - ~8 rows visible
                                    with ui.scroll_area().classes('w-full').style('height: 450px'):
                                        with ui.column().classes('w-full gap-2'):
                                            for holiday_date in sorted(holidays_by_date.keys()):
                                                h_list = holidays_by_date[holiday_date]
                                                markets = [h.market for h in h_list]
                                                name = h_list[0].name

                                                # Check if any trading floor is closed
                                                has_trading_floor = any(m in trading_floor_markets for m in markets)

                                                # Highlight rows with trading floor closures
                                                row_classes = 'w-full p-3 rounded'
                                                if has_trading_floor:
                                                    row_classes += ' border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                else:
                                                    row_classes += ' bg-gray-50 dark:bg-gray-800/50'

                                                with ui.card().classes(row_classes):
                                                    with ui.row().classes('w-full items-center justify-between'):
                                                        with ui.row().classes('items-center gap-3 flex-1'):
                                                            if has_trading_floor:
                                                                ui.icon('storefront', color='blue', size='sm').tooltip('Trading Floor Closed')
                                                            else:
                                                                ui.icon('flag', color='red', size='sm').tooltip('Federal Holiday Only')

                                                            with ui.column().classes('gap-0'):
                                                                ui.label(name).classes('font-semibold')
                                                                ui.label(holiday_date.strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')

                                                        with ui.row().classes('items-center gap-1'):
                                                            for market in sorted(markets):
                                                                color = 'blue' if market == 'NYSE' else 'green' if market == 'CME' else 'purple' if market == 'CBOE' else 'red'
                                                                ui.badge(market, color=color).classes('text-xs')

                                    # Footer with summary
                                    trading_floor_days = sum(1 for h_list in holidays_by_date.values() if any(h.market in trading_floor_markets for h in h_list))
                                    with ui.row().classes('w-full justify-between items-center mt-4 pt-4 border-t border-gray-200 dark:border-gray-700'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('storefront', color='blue', size='xs')
                                            ui.label(f'{trading_floor_days} days with market closures').classes('text-sm opacity-70')
                                        ui.button('Close', on_click=dialog.close).props('flat')

                            dialog.open()
                        finally:
                            db_session.close()

                    def show_sync_preview_dialog(year: int):
                        """Show preview dialog before syncing holidays."""
                        import time
                        start_time = time.time()

                        with ui.dialog() as preview_dialog, ui.card().classes('min-w-[700px] max-h-[85vh] p-0'):
                            # Header
                            with ui.row().classes('w-full p-4 items-center justify-between').style('background-color: #7c3aed'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('preview', size='md', color='white')
                                    ui.label(f'Sync Preview: {year} Holidays').classes('text-lg font-bold text-white')
                                ui.button(icon='close', on_click=preview_dialog.close).props('flat round').style('color: white')

                            preview_content = ui.column().classes('w-full p-4')

                            with preview_content:
                                # Step 1: Fetching data
                                with ui.card().classes('w-full p-4 mb-4 border-l-4 border-blue-500'):
                                    with ui.row().classes('items-center gap-3'):
                                        fetch_spinner = ui.spinner('dots', size='sm')
                                        with ui.column().classes('flex-1'):
                                            fetch_status = ui.label('Fetching holiday data...').classes('font-semibold')
                                            fetch_detail = ui.label('Connecting to data source...').classes('text-xs opacity-70')

                            preview_dialog.open()

                            # Perform the actual fetch
                            try:
                                from src.services.market_calendar_service import MarketCalendarService, DataSource
                                from src.models.market_holiday import MarketHoliday

                                db_session = next(get_db())
                                service = MarketCalendarService(db_session=None)  # Don't save yet

                                # Check which tier will be used
                                if service._pandas_available:
                                    fetch_detail.set_text('Using pandas_market_calendars library...')
                                    holidays = service._get_from_pandas(year)
                                    source = DataSource.PANDAS_MARKET_CALENDARS
                                    source_display = 'pandas_market_calendars (Official Exchange Data)'
                                    confidence = 'High - Verified'
                                    confidence_color = 'green'
                                else:
                                    fetch_detail.set_text('Library unavailable, using static calculation...')
                                    holidays = service._calculate_static_holidays(year)
                                    source = DataSource.STATIC_CALCULATION
                                    source_display = 'Static Calculation (Algorithm-based)'
                                    confidence = 'Medium - Calculated'
                                    confidence_color = 'amber'

                                fetch_time = time.time() - start_time

                                # Update status
                                fetch_spinner.delete()
                                fetch_status.set_text(f'Data fetched successfully ({fetch_time:.2f}s)')
                                fetch_detail.set_text(f'Source: {source_display}')

                                # Check existing holidays
                                existing_holidays = db_session.query(MarketHoliday).filter(
                                    MarketHoliday.year == year
                                ).all()
                                existing_dates = {(h.holiday_date, h.market) for h in existing_holidays}

                                with preview_content:
                                    # Step 2: Source information
                                    with ui.card().classes(f'w-full p-4 mb-4 border-l-4 border-{confidence_color}-500'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('source', color=confidence_color)
                                            ui.label('Data Source').classes('font-semibold')
                                            ui.badge(confidence, color=confidence_color).classes('ml-2')
                                        with ui.column().classes('gap-1'):
                                            ui.label(f'Source: {source_display}').classes('text-sm')
                                            ui.label(f'Response time: {fetch_time:.2f} seconds').classes('text-xs opacity-70')
                                            if source == DataSource.STATIC_CALCULATION:
                                                with ui.row().classes('items-center gap-1 mt-2 p-2 bg-amber-100 dark:bg-amber-900/30 rounded'):
                                                    ui.icon('warning', color='amber', size='xs')
                                                    ui.label('Static calculation used - verify dates manually for accuracy').classes('text-xs text-amber-700 dark:text-amber-400')

                                    # Step 3: Preview holidays
                                    with ui.card().classes('w-full p-4 mb-4'):
                                        with ui.row().classes('items-center justify-between mb-4'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('calendar_month', color='purple')
                                                ui.label(f'{len(holidays)} Holidays Found').classes('font-semibold')
                                            if existing_holidays:
                                                ui.badge(f'{len(existing_holidays)} existing', color='blue').props('outline')

                                        # Group by date for display
                                        from collections import defaultdict
                                        holidays_by_date = defaultdict(list)
                                        for h in holidays:
                                            holidays_by_date[h.date].append(h)

                                        with ui.scroll_area().classes('w-full').style('max-height: 300px'):
                                            with ui.column().classes('w-full gap-2'):
                                                for holiday_date in sorted(holidays_by_date.keys()):
                                                    h_list = holidays_by_date[holiday_date]
                                                    name = h_list[0].name

                                                    # Check if this is new or existing
                                                    is_new = not any((holiday_date, h.exchange) in existing_dates for h in h_list)

                                                    with ui.row().classes('w-full items-center justify-between p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800'):
                                                        with ui.row().classes('items-center gap-3'):
                                                            if is_new:
                                                                ui.icon('add_circle', color='green', size='xs')
                                                            else:
                                                                ui.icon('check_circle', color='blue', size='xs')
                                                            with ui.column().classes('gap-0'):
                                                                ui.label(name).classes('text-sm font-medium')
                                                                ui.label(holiday_date.strftime('%A, %B %d, %Y')).classes('text-xs opacity-60')
                                                        with ui.row().classes('gap-1'):
                                                            for h in h_list:
                                                                market = h.exchange if hasattr(h, 'exchange') else 'ALL'
                                                                color = 'red' if market == 'Federal' else 'blue' if market == 'NYSE' else 'green' if market == 'CME' else 'purple'
                                                                ui.badge(market, color=color).classes('text-xs')
                                                            if is_new:
                                                                ui.badge('NEW', color='green').props('outline dense')

                                    # Summary
                                    new_count = sum(1 for h in holidays if not any((h.date, m) in existing_dates for m in [h.exchange] if hasattr(h, 'exchange')))
                                    with ui.row().classes('w-full items-center gap-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg mb-4'):
                                        ui.icon('summarize', color='purple')
                                        ui.label(f'Summary: {len(holidays)} holidays will be synced for {year}').classes('text-sm')
                                        if existing_holidays:
                                            ui.label(f'({len(existing_holidays)} existing records will be updated)').classes('text-xs opacity-60')

                                    # Action buttons
                                    def confirm_sync():
                                        try:
                                            sync_service = MarketCalendarService(db_session=db_session)
                                            result = sync_service.sync_market_holidays(year)
                                            db_session.close()

                                            if result.success:
                                                show_success_dialog('Holidays Synced', f'Successfully synced {result.count} holidays for {year}!')
                                                preview_dialog.close()
                                                refresh_holiday_stats()
                                            else:
                                                show_error_dialog('Sync Failed', f'Error: {result.error}')
                                        except Exception as e:
                                            show_error_dialog('Sync Error', f'Error: {str(e)}')

                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button('Cancel', on_click=preview_dialog.close).props('flat')
                                        ui.button('Confirm & Import', icon='check', on_click=confirm_sync).props('color=primary')

                            except Exception as e:
                                with preview_content:
                                    # Error state
                                    fetch_spinner.delete()
                                    fetch_status.set_text('Failed to fetch data')
                                    fetch_detail.set_text(str(e))

                                    with ui.card().classes('w-full p-4 border-l-4 border-red-500 mt-4'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('error', color='red')
                                            ui.label('Fetch Failed').classes('font-semibold text-red-500')
                                        ui.label(f'Error: {str(e)}').classes('text-sm')

                                        # Offer fallback option
                                        ui.label('Would you like to try using static calculation instead?').classes('text-sm mt-4')
                                        with ui.row().classes('gap-2 mt-2'):
                                            ui.button('Cancel', on_click=preview_dialog.close).props('flat')
                                            ui.button('Use Static Calculation', icon='calculate', on_click=lambda: use_fallback(year, preview_dialog)).props('color=amber')

                    def use_fallback(year: int, dialog):
                        """Use static calculation as fallback."""
                        try:
                            from src.services.market_calendar_service import MarketCalendarService
                            db_session = next(get_db())
                            service = MarketCalendarService(db_session=db_session)

                            # Force static calculation
                            holidays = service._calculate_static_holidays(year)
                            service._save_to_database(holidays, service.DataSource.STATIC_CALCULATION)
                            db_session.commit()
                            db_session.close()

                            show_success_dialog('Holidays Imported', f'Imported {len(holidays)} holidays using static calculation')
                            dialog.close()
                            refresh_holiday_stats()
                        except Exception as e:
                            show_error_dialog('Error', f'Fallback failed: {str(e)}')

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
                                            ui.button('Sync', icon='sync', on_click=lambda y=year: show_sync_preview_dialog(y)).props('flat dense color=purple')
                            db_session.close()
                        except Exception as e:
                            with sync_results_container:
                                ui.label(f'Error loading stats: {e}').classes('text-red-500')

                    # Sync buttons with preview
                    with ui.row().classes('gap-2 mb-4'):
                        ui.button(f'Sync {current_year}', icon='sync', on_click=lambda: show_sync_preview_dialog(current_year)).props('color=primary')
                        ui.button(f'Sync {current_year + 1}', icon='sync', on_click=lambda: show_sync_preview_dialog(current_year + 1)).props('color=secondary')

                    refresh_holiday_stats()

            # ========== HANDBOOK TAB ==========
            with ui.tab_panel(handbook_tab):
                # Handbook Management Header Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('menu_book', size='sm', color='amber')
                        ui.label('Handbook Management').classes('text-lg font-semibold')
                        create_help_button(
                            'Handbook Management',
                            'Manage your employee handbook and track policy changes over time.<br><br>'
                            '<b>Features:</b><br>'
                            '• View current handbook content<br>'
                            '• Upload new handbook versions<br>'
                            '• AI-powered policy extraction<br>'
                            '• Version history with rollback<br>'
                            '• 30-day change indicators<br><br>'
                            '<i>Changes are tracked and communicated to all employees.</i>'
                        )

                    ui.label('View and manage your employee handbook. Policy changes are automatically tracked and communicated.').classes('text-sm opacity-70')

                # Action buttons
                with ui.row().classes('w-full gap-4 mb-4'):
                    ui.button('View Handbook', icon='visibility', on_click=lambda: ui.navigate.to('/admin/handbook')).props('color=primary')
                    ui.button('Upload New Version', icon='upload_file', on_click=lambda: ui.navigate.to('/admin/handbook?action=upload')).props('color=secondary outline')

                # Current Handbook Status
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('article', size='sm', color='blue')
                        ui.label('Current Handbook').classes('text-lg font-semibold')
                        create_help_button(
                            'Current Handbook',
                            'Shows the currently active handbook version.<br><br>'
                            '<b>Version:</b> The handbook version identifier<br>'
                            '<b>Published:</b> When this version became active<br>'
                            '<b>Sections:</b> Number of policy sections defined<br><br>'
                            '<i>Click "View Handbook" to see the full content.</i>'
                        )

                    # Get current handbook info
                    from src.models.handbook_upload import HandbookUpload
                    db_handbook = next(get_db())
                    try:
                        current_handbook = db_handbook.query(HandbookUpload).filter(
                            HandbookUpload.status == 'published'
                        ).order_by(HandbookUpload.published_at.desc()).first()

                        # Use CSS grid for status cards
                        with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;'):
                            # Version
                            with ui.card().classes('p-4 bg-amber-50 dark:bg-amber-900/20'):
                                ui.label('Version').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                if current_handbook:
                                    ui.label(current_handbook.version).classes('font-mono text-lg font-semibold')
                                else:
                                    ui.label('v1.0 (Default)').classes('font-mono text-lg font-semibold')

                            # Published Date
                            with ui.card().classes('p-4 bg-blue-50 dark:bg-blue-900/20'):
                                ui.label('Published').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                if current_handbook and current_handbook.published_at:
                                    ui.label(current_handbook.published_at.strftime('%b %d, %Y')).classes('text-lg font-semibold')
                                else:
                                    ui.label('Built-in').classes('text-lg font-semibold')

                            # Status
                            with ui.card().classes('p-4 bg-green-50 dark:bg-green-900/20'):
                                ui.label('Status').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('check_circle', color='green', size='sm')
                                    ui.label('Active').classes('text-lg font-semibold')
                    finally:
                        db_handbook.close()

                # Recent Policy Changes
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('history', size='sm', color='purple')
                        ui.label('Recent Policy Changes').classes('text-lg font-semibold')
                        create_help_button(
                            'Recent Policy Changes',
                            'Shows policy changes from the last 30 days.<br><br>'
                            '<b>Change indicators:</b><br>'
                            '• <span style="color: #22c55e;">Green badge</span> - New or increased value<br>'
                            '• <span style="color: #f59e0b;">Amber badge</span> - Reverted change<br><br>'
                            'These changes are displayed throughout the app with tooltips showing the old and new values.<br><br>'
                            '<i>Indicators automatically expire after 30 days.</i>'
                        )

                    # Get recent changes
                    from src.models.policy_change_log import PolicyChangeLog
                    db_changes = next(get_db())
                    try:
                        from datetime import timedelta
                        thirty_days_ago = datetime.now() - timedelta(days=30)
                        recent_changes = db_changes.query(PolicyChangeLog).filter(
                            PolicyChangeLog.created_at >= thirty_days_ago
                        ).order_by(PolicyChangeLog.created_at.desc()).limit(5).all()

                        if recent_changes:
                            for change in recent_changes:
                                days_left = (change.expires_at - datetime.now()).days if change.expires_at else 0
                                with ui.card().classes('w-full p-3 mb-2 bg-gray-50 dark:bg-gray-800'):
                                    with ui.row().classes('w-full items-center justify-between'):
                                        with ui.row().classes('items-center gap-3'):
                                            icon_name = 'undo' if change.is_revert else 'update'
                                            icon_color = 'amber' if change.is_revert else 'green'
                                            ui.icon(icon_name, color=icon_color)
                                            with ui.column().classes('gap-0'):
                                                ui.label(change.policy_type.replace('_', ' ').title()).classes('font-semibold')
                                                ui.label(change.ai_summary or 'Policy updated').classes('text-sm opacity-70')
                                        with ui.column().classes('items-end gap-1'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(change.old_value_display).classes('line-through opacity-50 text-sm')
                                                ui.icon('arrow_forward', size='xs')
                                                ui.label(change.new_value_display).classes('font-bold text-green-500')
                                            ui.label(f'{days_left}d left').classes('text-xs opacity-50')
                        else:
                            with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                                with ui.column().classes('items-center gap-2'):
                                    ui.icon('check_circle', size='lg', color='green')
                                    ui.label('No recent changes').classes('text-gray-500')
                                    ui.label('Policy changes from the last 30 days will appear here').classes('text-sm text-gray-400')
                    finally:
                        db_changes.close()

            # ========== EOY PROCESSING TAB ==========
            with ui.tab_panel(eoy_tab):
                # EOY Header Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('event_repeat', size='sm', color='red')
                        ui.label('End of Year Processing').classes('text-lg font-semibold')
                        create_help_button(
                            'End of Year Processing',
                            'Year-end processing manages PTO balance transitions between calendar years.<br><br>'
                            '<b>What happens during EOY:</b><br>'
                            '• Sick time carryover is calculated per policy limits<br>'
                            '• Vacation balances reset to new allocations<br>'
                            '• Unused personal time is forfeited<br>'
                            '• Historical records are preserved<br><br>'
                            '<b>Important:</b> Create a database backup before running EOY processing!'
                        )

                    ui.label('Manage year-end balance transitions, carryover calculations, and new year allocations.').classes('text-sm opacity-70')

                # Quick Actions
                with ui.row().classes('w-full gap-4 mb-4'):
                    ui.button('Go to EOY Processing', icon='open_in_new', on_click=lambda: ui.navigate.to('/admin/year-end')).props('color=primary')
                    ui.button('Go to Carryover', icon='sync', on_click=lambda: ui.navigate.to('/carryover')).props('color=secondary outline')

                # Current Status Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('assessment', size='sm', color='blue')
                        ui.label('Processing Status').classes('text-lg font-semibold')

                    current_year = datetime.now().year
                    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;'):
                        with ui.card().classes('p-4 bg-blue-50 dark:bg-blue-900/20'):
                            ui.label('Current Year').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            ui.label(str(current_year)).classes('text-2xl font-bold')
                        with ui.card().classes('p-4 bg-amber-50 dark:bg-amber-900/20'):
                            ui.label('Next EOY').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                            ui.label(f'Dec 31, {current_year}').classes('font-semibold')

                    ui.label('Use the EOY Processing page to run year-end balance transitions when ready.').classes('text-sm opacity-70 mt-4')

            # ========== ANALYTICS TAB ==========
            with ui.tab_panel(analytics_tab):
                # Analytics Header Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('analytics', size='sm', color='green')
                        ui.label('Analytics & Insights').classes('text-lg font-semibold')
                        create_help_button(
                            'Analytics & Insights',
                            'View usage patterns and insights about PTO across the organization.<br><br>'
                            '<b>Available analytics:</b><br>'
                            '• Department-level PTO usage<br>'
                            '• Trending request patterns<br>'
                            '• Approval rate metrics<br>'
                            '• Balance distribution<br><br>'
                            '<i>Use these insights to improve workforce planning.</i>'
                        )

                    ui.label('Explore PTO usage trends, department patterns, and organizational insights.').classes('text-sm opacity-70')

                # Quick Actions
                with ui.row().classes('w-full gap-4 mb-4'):
                    ui.button('Go to Analytics', icon='open_in_new', on_click=lambda: ui.navigate.to('/analytics')).props('color=primary')
                    ui.button('Go to Reports', icon='summarize', on_click=lambda: ui.navigate.to('/reports')).props('color=secondary outline')

                # Analytics Summary Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('trending_up', size='sm', color='blue')
                        ui.label('Quick Stats').classes('text-lg font-semibold')

                    from src.models.pto_request import PTORequest
                    from src.models.user import User
                    db_analytics = next(get_db())
                    try:
                        total_requests = db_analytics.query(PTORequest).count()
                        pending_requests = db_analytics.query(PTORequest).filter(PTORequest.status == 'pending').count()
                        total_employees = db_analytics.query(User).filter(User.role.in_(['employee', 'manager'])).count()

                        with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;'):
                            with ui.card().classes('p-4 bg-blue-50 dark:bg-blue-900/20'):
                                ui.label('Total Requests').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                ui.label(str(total_requests)).classes('text-2xl font-bold')
                            with ui.card().classes('p-4 bg-amber-50 dark:bg-amber-900/20'):
                                ui.label('Pending').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                ui.label(str(pending_requests)).classes('text-2xl font-bold')
                            with ui.card().classes('p-4 bg-green-50 dark:bg-green-900/20'):
                                ui.label('Employees').classes('text-xs text-gray-500 uppercase tracking-wide mb-2')
                                ui.label(str(total_employees)).classes('text-2xl font-bold')
                    except Exception:
                        ui.label('Unable to load analytics').classes('text-sm opacity-70')
                    finally:
                        db_analytics.close()

            # ========== AUTO NOTIFY TAB ==========
            with ui.tab_panel(autonotify_tab):
                # Auto Notify Header Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('notifications_active', size='sm', color='amber')
                        ui.label('Auto Notify Reports').classes('text-lg font-semibold')
                        create_help_button(
                            'Auto Notify Reports',
                            'Configure automatic report delivery to department heads and administrators.<br><br>'
                            '<b>Features:</b><br>'
                            '• Schedule daily/weekly report emails<br>'
                            '• Select recipients by department<br>'
                            '• Choose which reports to include<br>'
                            '• View delivery history<br><br>'
                            '<i>Reports are sent based on configured schedules.</i>'
                        )

                    ui.label('Manage automated report scheduling and delivery preferences.').classes('text-sm opacity-70')

                # Quick Actions
                with ui.row().classes('w-full gap-4 mb-4'):
                    ui.button('Go to Auto Notify Settings', icon='open_in_new', on_click=lambda: ui.navigate.to('/admin/auto-notify-reports')).props('color=primary')

                # Scheduled Reports Card
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('schedule', size='sm', color='blue')
                        ui.label('Report Scheduling').classes('text-lg font-semibold')

                    with ui.row().classes('w-full justify-center p-6 bg-gray-50 dark:bg-gray-800 rounded-lg'):
                        with ui.column().classes('items-center gap-2'):
                            ui.icon('schedule_send', size='lg', color='amber')
                            ui.label('Auto Notify Reports').classes('font-semibold')
                            ui.label('Configure automated report delivery to department heads').classes('text-sm text-gray-400')
                            ui.label('Click the button above to manage schedules').classes('text-xs opacity-60 mt-2')

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
                        create_help_button(
                            'Email Service Status',
                            'Shows whether the email system is properly configured and ready to send notifications.<br><br>'
                            '<b>Green status:</b> All SMTP settings are configured and the system can send emails.<br>'
                            '<b>Amber status:</b> SMTP is not configured - emails will not be sent until you set up the environment variables.'
                        )

                    # Status banner
                    if email_configured:
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #14532d; border-left: 4px solid #22c55e'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('check_circle', size='md').style('color: #22c55e')
                                with ui.column().classes('flex-1'):
                                    ui.label('Email service is configured').classes('font-semibold').style('color: #22c55e')
                                    ui.label('Your application can send notification emails').classes('text-sm opacity-70')
                    else:
                        with ui.element('div').classes('w-full p-4 rounded-lg').style('background-color: #78350f; border-left: 4px solid #f59e0b'):
                            with ui.row().classes('items-center gap-3'):
                                ui.icon('warning', size='md').style('color: #f59e0b')
                                with ui.column().classes('flex-1'):
                                    ui.label('Email service not configured').classes('font-semibold').style('color: #f59e0b')
                                    ui.label('Configure SMTP settings to enable email notifications').classes('text-sm opacity-70')

                # Configuration Details Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings', size='sm', color='gray')
                        ui.label('SMTP Configuration').classes('text-lg font-semibold')
                        create_help_button(
                            'SMTP Configuration',
                            'SMTP (Simple Mail Transfer Protocol) settings are required to send emails.<br><br>'
                            '<b>Add these to your .env file:</b><br>'
                            '<code style="background: #374151; padding: 2px 6px; border-radius: 4px;">SMTP_HOST=smtp.your-provider.com</code><br>'
                            '<code style="background: #374151; padding: 2px 6px; border-radius: 4px;">SMTP_PORT=587</code><br>'
                            '<code style="background: #374151; padding: 2px 6px; border-radius: 4px;">SMTP_USER=your-email@company.com</code><br>'
                            '<code style="background: #374151; padding: 2px 6px; border-radius: 4px;">SMTP_PASSWORD=your-app-password</code><br>'
                            '<code style="background: #374151; padding: 2px 6px; border-radius: 4px;">SMTP_FROM=noreply@company.com</code><br><br>'
                            '<b>Common SMTP Providers:</b><br>'
                            '• Gmail: smtp.gmail.com (port 587)<br>'
                            '• Microsoft 365: smtp.office365.com (port 587)<br>'
                            '• Amazon SES: email-smtp.us-east-1.amazonaws.com (port 587)<br><br>'
                            '<i>Restart the application after updating .env</i>'
                        )

                    with ui.element('div').classes('w-full grid grid-cols-4 gap-4'):
                        with ui.element('div').classes('p-3 rounded-lg').style('background-color: #374151'):
                            ui.label('HOST').classes('text-xs opacity-60 mb-1')
                            ui.label(smtp_host or 'Not set').classes(f'font-mono text-sm {"opacity-50" if not smtp_host else ""}')

                        with ui.element('div').classes('p-3 rounded-lg').style('background-color: #374151'):
                            ui.label('PORT').classes('text-xs opacity-60 mb-1')
                            ui.label(smtp_port or 'Not set').classes(f'font-mono text-sm {"opacity-50" if not smtp_port else ""}')

                        with ui.element('div').classes('p-3 rounded-lg').style('background-color: #374151'):
                            ui.label('USER').classes('text-xs opacity-60 mb-1')
                            ui.label(smtp_user or 'Not set').classes(f'font-mono text-sm {"opacity-50" if not smtp_user else ""}')

                        with ui.element('div').classes('p-3 rounded-lg').style('background-color: #374151'):
                            ui.label('FROM ADDRESS').classes('text-xs opacity-60 mb-1')
                            ui.label(smtp_from or 'Not set').classes(f'font-mono text-sm {"opacity-50" if not smtp_from else ""}')

                # Email Template Preview Card - Embedded directly
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('preview', size='sm', color='purple')
                        ui.label('Email Template Preview').classes('text-lg font-semibold')
                        create_help_button(
                            'Email Template Preview',
                            'Preview how emails will appear to recipients before they are sent.<br><br>'
                            '<b>EMP:</b> Emails sent to employees<br>'
                            '• Request Submitted - Confirmation when employee submits PTO<br>'
                            '• Request Approved - Notification when manager approves<br>'
                            '• Request Denied - Notification when manager denies<br><br>'
                            '<b>MAN:</b> Emails sent to managers<br>'
                            '• Request Arrived - Alert when employee submits new PTO request<br><br>'
                            '<b>ADMIN:</b> System emails<br>'
                            '• Report Email - Format for emailed reports'
                        )

                    # Email preview - embedded from admin_email_preview.py
                    from datetime import date as date_type, timedelta
                    from src.services.email_service import _get_email_template, _get_pto_type_icon, _format_date_range_with_days

                    sample_employee = "John Smith"
                    sample_manager = "Jane Doe"
                    sample_pto_type = "Vacation"
                    sample_start = date_type.today() + timedelta(days=7)
                    sample_end = date_type.today() + timedelta(days=10)
                    sample_days = 4.0
                    pto_icon = _get_pto_type_icon('vacation')
                    date_range = _format_date_range_with_days(sample_start, sample_end)

                    email_types = {
                        'submitted': 'EMP: REQUEST SUBMITTED',
                        'approved': 'EMP: REQUEST APPROVED',
                        'denied': 'EMP: REQUEST DENIED',
                        'pending': 'MAN: REQUEST ARRIVED',
                        'cancelled': 'MAN: PTO CANCELLED',
                        'chicago': 'CHICAGO SAFE LEAVE',
                        'report': 'ADMIN: REPORT EMAIL'
                    }

                    selected_type = {'value': 'approved'}
                    preview_container = ui.element('div').classes('w-full')

                    def generate_email_preview(email_type: str) -> str:
                        days_display = str(int(sample_days)) if sample_days == int(sample_days) else f"{sample_days:.1f}"

                        if email_type == 'submitted':
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
                            <p style="margin-bottom: 25px;">Your time off request has been submitted and is <span style="color: #f59e0b; font-weight: 600;">pending approval</span>.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="Request Submitted", title_color="#f59e0b", content=content, footer_text="You will receive another email once your request has been reviewed.")

                        elif email_type == 'approved':
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
                            <p style="margin-bottom: 25px;">Great news! Your time off request has been <span style="color: #22c55e; font-weight: 600;">approved</span>.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #22c55e;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600; color: #22c55e;">{days_display}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Approved by:</td><td style="padding: 8px 0; font-weight: 600;">{sample_manager}</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="Request Approved", title_color="#22c55e", content=content, footer_text="Enjoy your time off!")

                        elif email_type == 'denied':
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
                            <p style="margin-bottom: 25px;">Unfortunately, your time off request has been <span style="color: #ef4444; font-weight: 600;">denied</span>.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600;">{days_display}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Reviewed by:</td><td style="padding: 8px 0; font-weight: 600;">{sample_manager}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af; vertical-align: top;">Reason:</td><td style="padding: 8px 0; font-weight: 600; color: #fca5a5;">Team coverage needed during this period.</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="Request Denied", title_color="#ef4444", content=content, footer_text="If you have questions, please speak with your manager.")

                        elif email_type == 'pending':
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_manager},</p>
                            <p style="margin-bottom: 25px;">A new time off request requires your review.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Employee:</td><td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{sample_employee}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="New Request Pending", title_color="#f59e0b", content=content, footer_text="Please log in to TJM Time Calendar to approve or deny this request.")

                        elif email_type == 'cancelled':
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_manager},</p>
                            <p style="margin-bottom: 25px;">An employee has <span style="color: #ef4444; font-weight: 600;">cancelled</span> their previously approved time off.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Employee:</td><td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{sample_employee}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600; color: #ef4444;">{days_display}</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="Approved PTO Cancelled", title_color="#ef4444", content=content, footer_text="The employee's PTO balance has been restored automatically.")

                        elif email_type == 'chicago':
                            # Chicago Safe Leave submitted email preview
                            content = f"""
                            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
                            <p style="margin-bottom: 25px;">Your time off request has been submitted and is <span style="color: #f59e0b; font-weight: 600;">pending approval</span>.</p>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                <table style="width: 100%; color: #e5e7eb;">
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Type:</td><td style="padding: 8px 0; font-weight: 600;">Chicago Safe Leave</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Location:</td><td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">📍 Chicago (Paid Sick &amp; Safe Leave)</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Dates:</td><td style="padding: 8px 0; font-weight: 600;">{date_range}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #9ca3af;">Total Days:</td><td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td></tr>
                                </table>
                            </div>
                            """
                            return _get_email_template(title="Request Submitted", title_color="#f59e0b", content=content, footer_text="You will receive another email once your request has been reviewed.")

                        elif email_type == 'report':
                            content = """
                            <p style="font-size: 16px; margin-bottom: 20px; color: #e5e7eb;">Please find the report below:</p>
                            <div style="background-color: #374151; padding: 15px; border-radius: 8px; border-left: 4px solid #C9A227; margin-bottom: 20px;">
                                <p style="margin: 0; color: #e5e7eb; font-style: italic;">Here is the monthly PTO summary you requested.</p>
                            </div>
                            <div style="background-color: #374151; padding: 20px; border-radius: 8px; margin-top: 20px;">
                                <p style="color: #e5e7eb; margin: 0;">Sample report content would appear here...</p>
                            </div>
                            """
                            return _get_email_template(title="Report", title_color="#C9A227", content=content)
                        return ""

                    def render_email_preview():
                        preview_container.clear()
                        with preview_container:
                            html_content = generate_email_preview(selected_type['value'])
                            ui.html(f'''
                                <iframe
                                    srcdoc="{html_content.replace('"', '&quot;')}"
                                    style="width: 100%; height: 780px; border: 1px solid #374151; border-radius: 8px; background: #111827;"
                                ></iframe>
                            ''', sanitize=False)

                    # Email type buttons - edge to edge
                    with ui.row().classes('w-full gap-2 mb-4'):
                        for key, label in email_types.items():
                            def make_preview_handler(k=key):
                                def handler():
                                    selected_type['value'] = k
                                    render_email_preview()
                                return handler

                            colors = {'submitted': '#f59e0b', 'approved': '#22c55e', 'denied': '#ef4444', 'pending': '#f59e0b', 'cancelled': '#ef4444', 'chicago': '#a855f7', 'report': '#C9A227'}
                            color = colors.get(key, '#6b7280')
                            ui.button(label, on_click=make_preview_handler()).props('outline').classes('flex-1').style(f'border-color: {color}; color: {color}; font-size: 11px; padding: 8px 4px; font-weight: 600;')

                    # Initial preview
                    render_email_preview()

                # Test Email Card - Moved to bottom
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('send', size='sm', color='green')
                        ui.label('Test Email').classes('text-lg font-semibold')
                        create_help_button(
                            'Test Email',
                            'Send a test email to verify your SMTP configuration is working correctly.<br><br>'
                            'Enter any email address (including your own) and click Send Test. '
                            'If successful, you\'ll receive a test email confirming the configuration works.<br><br>'
                            '<b>Note:</b> SMTP must be configured in your .env file before testing.'
                        )

                    with ui.row().classes('items-center gap-4 w-full'):
                        test_email_input = ui.input(placeholder='Enter recipient email address').props('outlined dense').classes('flex-1')

                        def send_test_email():
                            if not test_email_input.value:
                                show_warning_dialog('Email Required', 'Please enter an email address to send the test to.')
                                return
                            if not email_configured:
                                show_error_dialog('SMTP Not Configured', 'SMTP is not configured. Please set the environment variables first.')
                                return

                            show_info_dialog('Sending', 'Sending test email...')
                            try:
                                from src.services.email_service import email_service
                                success = email_service.send_email(
                                    to_email=test_email_input.value,
                                    subject='TJM Calendar - Test Email',
                                    body='This is a test email from the TJM Time Calendar system.\n\nIf you received this, your email configuration is working correctly!'
                                )
                                if success:
                                    show_success_dialog('Email Sent', 'Test email sent successfully!')
                                else:
                                    show_error_dialog('Email Failed', 'Failed to send email. Please check the logs for more details.')
                            except Exception as e:
                                show_error_dialog('Error', f'Error sending email: {str(e)}')

                        ui.button('Send Test', icon='send', on_click=send_test_email).props('color=primary')

            # ========== LOGS TAB ==========
            with ui.tab_panel(logs_tab):
                # Log file paths (reuse logs_dir from status overview)
                main_log_path = logs_dir / 'tjm_calendar.log'
                error_log_path = logs_dir / 'tjm_calendar_errors.log'

                # State for current log and AI analysis
                # Options: 'main', 'errors', 'audit'
                log_state = {'current_log': 'main', 'current_content': '', 'audit_filter': 'all', 'filter_select': None}

                # Log Files Overview Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('description', size='sm', color='blue')
                        ui.label('Log Files').classes('text-lg font-semibold')

                    # Container for log file cards (will be refreshed dynamically)
                    log_cards_container = ui.row().classes('w-full gap-4 items-stretch')

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
                                if log_state.get('filter_select'):
                                    log_state['filter_select'].set_visibility(False)

                            with ui.card().classes('p-4 cursor-pointer hover:shadow-md transition-shadow flex-1').style('min-height: 100px;').on('click', switch_to_main):
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
                                if log_state.get('filter_select'):
                                    log_state['filter_select'].set_visibility(False)

                            error_has_content = error_exists and error_size > 0
                            with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow flex-1 {"border-red-300 border-2" if error_has_content else ""}').style('min-height: 100px;').on('click', switch_to_errors):
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

                            # Audit log card
                            def switch_to_audit():
                                log_state['current_log'] = 'audit'
                                refresh_logs()
                                refresh_log_cards()
                                ai_analysis_container.clear()
                                ai_analysis_container.set_visibility(False)
                                if log_state.get('filter_select'):
                                    log_state['filter_select'].set_visibility(True)

                            # Get audit log count
                            audit_db = next(get_db())
                            try:
                                audit_count = audit_db.query(AuditLog).count()
                            finally:
                                audit_db.close()

                            with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow flex-1 {"border-l-4 border-purple-500" if log_state["current_log"] == "audit" else ""}').style('min-height: 100px;').on('click', switch_to_audit):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon('security', color='purple', size='md')
                                    with ui.column().classes('flex-1'):
                                        ui.label('Audit Log').classes('font-semibold')
                                        ui.label('User actions and security events').classes('text-xs opacity-70')
                                    with ui.column().classes('items-end'):
                                        ui.label(f'{audit_count} entries').classes('font-mono text-sm')
                                        ui.badge('Database', color='purple').props('dense')

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

                    # Log viewer - use rows prop for reliable height control
                    log_display = ui.textarea('').props('outlined readonly rows=30').classes('w-full font-mono text-xs bg-gray-50 dark:bg-gray-900')

                    def get_current_log_path():
                        return error_log_path if log_state['current_log'] == 'errors' else main_log_path

                    def refresh_logs(lines=100):
                        # Handle audit logs separately (from database)
                        if log_state['current_log'] == 'audit':
                            current_log_label.set_text('Viewing: Audit Log')
                            audit_db = next(get_db())
                            try:
                                # Build query based on filter
                                query = audit_db.query(AuditLog)

                                # Apply filter
                                filter_val = log_state.get('audit_filter', 'all')
                                if filter_val == 'login':
                                    query = query.filter(AuditLog.action.like('login%'))
                                elif filter_val == 'pto':
                                    query = query.filter(AuditLog.action.like('pto%'))
                                elif filter_val == 'user':
                                    query = query.filter(AuditLog.action.like('user%'))
                                elif filter_val == 'carryover':
                                    query = query.filter(AuditLog.action.like('carryover%'))

                                audit_logs = query.order_by(AuditLog.created_at.desc()).limit(lines).all()

                                if not audit_logs:
                                    log_display.value = 'No audit log entries found.'
                                    log_state['current_content'] = ''
                                    return

                                # Format audit logs for display with better formatting
                                log_lines = []
                                log_lines.append(f"{'Timestamp':<20} | {'User':<20} | {'Action':<20} | {'Entity':<20} | Details")
                                log_lines.append("-" * 120)
                                for log in audit_logs:
                                    timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else 'N/A'
                                    username = (log.username or 'System')[:20]
                                    action = (log.action or 'unknown')[:20]
                                    entity = f"{log.entity_type}:{log.entity_id}" if log.entity_type else ''
                                    entity = entity[:20]
                                    details = log.details or ''
                                    log_lines.append(f"{timestamp:<20} | {username:<20} | {action:<20} | {entity:<20} | {details}")

                                content = '\n'.join(log_lines)
                                log_display.value = content
                                log_state['current_content'] = content
                            except Exception as e:
                                log_display.value = f'Error reading audit log: {str(e)}'
                                log_state['current_content'] = ''
                            finally:
                                audit_db.close()
                            return

                        # Handle file-based logs
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
                        with ui.row().classes('gap-2 items-center'):
                            ui.label('Show:').classes('text-sm opacity-70')
                            ui.button('50 entries', on_click=lambda: refresh_logs(50)).props('flat dense size=sm')
                            ui.button('100 entries', on_click=lambda: refresh_logs(100)).props('flat dense size=sm')
                            ui.button('500 entries', on_click=lambda: refresh_logs(500)).props('flat dense size=sm')

                            # Audit log filter dropdown (only visible for audit logs)
                            audit_filter_options = {
                                'all': 'All Actions',
                                'login': 'Logins',
                                'pto': 'PTO Actions',
                                'user': 'User Changes',
                                'carryover': 'Carryover'
                            }

                            def on_filter_change(e):
                                log_state['audit_filter'] = e.value
                                refresh_logs()

                            audit_filter_select = ui.select(
                                options=audit_filter_options,
                                value='all',
                                on_change=on_filter_change
                            ).props('dense outlined').classes('ml-4').style('min-width: 140px;')
                            audit_filter_select.set_visibility(log_state['current_log'] == 'audit')
                            log_state['filter_select'] = audit_filter_select

                        def clear_current_log():
                            if log_state['current_log'] == 'audit':
                                show_warning_dialog('Cannot Clear', 'Audit logs cannot be cleared - they are permanent records.')
                                return
                            log_path = get_current_log_path()
                            if log_path.exists():
                                try:
                                    with open(log_path, 'w') as f:
                                        f.write('')
                                    show_success_dialog('Log Cleared', 'Log file has been cleared')
                                    refresh_logs()
                                    refresh_log_cards()  # Update the file size display
                                except Exception as e:
                                    show_error_dialog('Error', f'Error clearing log: {str(e)}')

                        clear_btn = ui.button('Clear Log', icon='delete_sweep', on_click=clear_current_log).props('flat dense color=red')

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
                                                show_warning_dialog('No Content', 'There is no log content to analyze.')
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
                                                show_warning_dialog('No Content', 'Please paste some log content to analyze.')
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
                            log_type = log_state.get('current_log', 'main')

                            if log_type == 'audit':
                                prompt = f"""Analyze {context} audit log below and provide a concise summary for a system administrator.

This is a security audit log tracking user actions in a PTO (time-off) management system.

Your analysis should include:
1. **Overview**: Brief summary of activity patterns (1-2 sentences)
2. **User Activity**: Which users are most active and what actions they're taking
3. **Security Events**: Login patterns, failed attempts, unusual activity times
4. **PTO Operations**: Request submissions, approvals, denials, cancellations
5. **Concerns**: Any suspicious patterns (unusual hours, bulk operations, failed logins)

Keep it concise and actionable. Use bullet points."""
                            else:
                                prompt = f"""Analyze {context} application log below and provide a concise summary for a system administrator.

Your analysis should include:
1. **Overview**: Brief summary of what's happening in the log (1-2 sentences)
2. **Key Events**: Important events or activities (logins, requests, database operations)
3. **Errors/Warnings**: Any errors, warnings, or concerning patterns (highlight severity)
4. **Recommendations**: Any suggested actions if issues are found

Keep it concise and actionable. Use bullet points. If the log shows normal operation with no issues, say so briefly."""

                            # Add truncation note and content to prompt
                            truncation_note = f"\nNote: Log was truncated to last {max_chars} characters.\n" if truncated else ""
                            prompt = f"{prompt}{truncation_note}\n\nLOG CONTENT:\n{analysis_content}"

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

                            show_success_dialog('Analysis Complete', 'Storage analysis completed')

                        except Exception as e:
                            ai_analysis_container.clear()
                            with ai_analysis_container:
                                with ui.card().classes('w-full p-4 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20'):
                                    ui.label('Analysis Failed').classes('font-semibold text-red-700 dark:text-red-400')
                                    ui.label(f'Error: {str(e)}').classes('text-sm')
                            show_error_dialog('Analysis Failed', f'Error during log analysis: {str(e)}')

            # ========== SETTINGS TAB ==========
            with ui.tab_panel(settings_tab):
                # Security Settings Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('security', size='sm', color='blue')
                        ui.label('Security Settings').classes('text-lg font-semibold')
                        create_help_button(
                            'Security Settings',
                            'These settings control application security and session management.<br><br>'
                            '<b>Debug Mode:</b> Should be <span style="color: #22c55e;">disabled</span> in production. '
                            'When enabled, detailed error messages are shown which could expose sensitive information.<br><br>'
                            '<b>Secret Key:</b> A strong, random key used for encrypting session data. '
                            'Should be at least 32 characters. Generate with: <code style="background: #374151; padding: 2px 6px; border-radius: 4px;">python -c "import secrets; print(secrets.token_hex(32))"</code><br><br>'
                            '<b>Session Timeout:</b> How long users stay logged in without activity. '
                            'Default is 30 minutes. Adjust in .env with SESSION_TIMEOUT_MINUTES.'
                        )

                    debug_val = os.getenv('DEBUG', 'false')
                    secret = os.getenv('SECRET_KEY', '')
                    timeout = os.getenv('SESSION_TIMEOUT_MINUTES', '30')

                    # Use CSS grid for perfect edge-to-edge alignment
                    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;'):
                        # Debug Mode
                        with ui.card().classes(f'p-4 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if debug_val.lower() == "true" else "bg-green-50 dark:bg-green-900/20"}'):
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
                        with ui.card().classes(f'p-4 {"bg-red-50 dark:bg-red-900/20 border border-red-300" if not (secret and len(secret) > 20) else "bg-green-50 dark:bg-green-900/20"}'):
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
                        with ui.card().classes('p-4 bg-gray-50 dark:bg-gray-800'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('timer', color='blue')
                                ui.label('Session Timeout').classes('font-semibold')
                            ui.label(f'{timeout} minutes').classes('font-mono text-lg')
                            ui.label('User inactivity limit').classes('text-xs opacity-70 mt-1')

                # Location Policies Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('location_city', size='sm', color='purple')
                        ui.label('Location Policies').classes('text-lg font-semibold')
                        create_help_button(
                            'Location Policies',
                            'Configure location-specific policies that override default settings.<br><br>'
                            '<b>Chicago Paid Sick and Safe Leave:</b><br>'
                            'Required by Chicago city ordinance (effective July 1, 2024). When enabled, employees '
                            'assigned to Chicago locations will see an additional leave type with:<br>'
                            '• Separate 80-hour (10 days) annual allocation<br>'
                            '• Maximum carryover of 80 hours<br>'
                            '• Can be used for sick time or "safe" purposes (domestic violence, stalking, etc.)<br><br>'
                            '<i>Employees must have their location set to Chicago to see this option.</i>'
                        )

                    # Chicago Safe Leave Toggle
                    with ui.card().classes('p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-300'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('flex-1'):
                                with ui.row().classes('items-center gap-2 mb-2'):
                                    ui.icon('location_on', color='purple')
                                    ui.label('Chicago Paid Sick and Safe Leave').classes('font-semibold')
                                ui.label('Enable separate leave bank for Chicago employees per city ordinance (effective July 1, 2024).').classes('text-sm opacity-70 mb-2')
                                ui.label('Employees in Chicago will see an additional leave type with 80-hour (10 days) carryover limit.').classes('text-xs opacity-60')

                            # Toggle switch
                            from src.models.system_setting import SystemSetting

                            def get_chicago_setting():
                                """Get Chicago Safe Leave setting from database."""
                                db_session = next(get_db())
                                try:
                                    setting = db_session.query(SystemSetting).filter(
                                        SystemSetting.key == 'chicago.safe_leave_enabled'
                                    ).first()
                                    return setting.bool_value if setting else False
                                finally:
                                    db_session.close()

                            def toggle_chicago_setting(e):
                                """Toggle Chicago Safe Leave setting."""
                                db_session = next(get_db())
                                try:
                                    setting = db_session.query(SystemSetting).filter(
                                        SystemSetting.key == 'chicago.safe_leave_enabled'
                                    ).first()
                                    if setting:
                                        setting.value = 'true' if e.value else 'false'
                                        setting.updated_by = app.storage.general.get('user', {}).get('id')
                                    else:
                                        # Create setting if it doesn't exist
                                        new_setting = SystemSetting(
                                            key='chicago.safe_leave_enabled',
                                            value='true' if e.value else 'false',
                                            description='Enable Chicago Paid Sick and Safe Leave feature for Chicago employees',
                                            updated_by=app.storage.general.get('user', {}).get('id')
                                        )
                                        db_session.add(new_setting)
                                    db_session.commit()
                                    status = 'enabled' if e.value else 'disabled'
                                    show_success_dialog('Setting Updated', f'Chicago Safe Leave {status}')
                                except Exception as ex:
                                    db_session.rollback()
                                    show_error_dialog('Error', f'Failed to update setting: {str(ex)}')
                                finally:
                                    db_session.close()

                            chicago_enabled = get_chicago_setting()
                            with ui.column().classes('items-center'):
                                chicago_toggle = ui.switch(value=chicago_enabled, on_change=toggle_chicago_setting)
                                ui.label('Enabled' if chicago_enabled else 'Disabled').classes('text-xs mt-1').bind_text_from(
                                    chicago_toggle, 'value', backward=lambda v: 'Enabled' if v else 'Disabled'
                                )

                # Environment Variables Card
                with ui.card().classes('w-full p-4 mb-4'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('settings_applications', size='sm', color='amber')
                        ui.label('Environment Configuration').classes('text-lg font-semibold')
                        create_help_button(
                            'Environment Configuration',
                            'Environment variables control application behavior. Set these in your <code style="background: #374151; padding: 2px 6px; border-radius: 4px;">.env</code> file.<br><br>'
                            '<b>SECRET_KEY:</b> Required for session security. Generate a strong key.<br>'
                            '<b>DEBUG:</b> Set to "false" in production to hide error details.<br>'
                            '<b>DATABASE_URL:</b> Connection string for the database.<br>'
                            '<b>SMTP_HOST:</b> Email server for sending notifications.<br>'
                            '<b>ANTHROPIC_API_KEY:</b> API key for AI features (log analysis, etc.).<br>'
                            '<b>LOG_LEVEL:</b> Controls logging verbosity (DEBUG, INFO, WARNING, ERROR).<br><br>'
                            '<i>Restart the application after changing environment variables.</i>'
                        )

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
                        create_help_button(
                            'System Information',
                            'Technical details about the server environment running this application.<br><br>'
                            '<b>Python:</b> The Python version running the application.<br>'
                            '<b>Platform:</b> Operating system (Windows, Linux, macOS).<br>'
                            '<b>Architecture:</b> CPU architecture (x64, ARM, etc.).<br>'
                            '<b>NiceGUI:</b> Version of the web framework powering the UI.<br><br>'
                            '<i>This information is useful for troubleshooting and support requests.</i>'
                        )

                    # Get NiceGUI version
                    try:
                        import nicegui
                        nicegui_version = nicegui.__version__
                    except Exception:
                        nicegui_version = 'Unknown'

                    # Use CSS grid for perfect edge-to-edge alignment (4 columns)
                    with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;'):
                        # Python
                        with ui.card().classes('p-4 bg-blue-50 dark:bg-blue-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('code', color='blue')
                                ui.label('Python').classes('font-semibold')
                            ui.label(sys_module.version.split()[0]).classes('font-mono text-lg')

                        # Platform
                        with ui.card().classes('p-4 bg-green-50 dark:bg-green-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('laptop', color='green')
                                ui.label('Platform').classes('font-semibold')
                            ui.label(platform.system()).classes('font-mono text-lg')

                        # Architecture
                        with ui.card().classes('p-4 bg-purple-50 dark:bg-purple-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('memory', color='purple')
                                ui.label('Architecture').classes('font-semibold')
                            ui.label(platform.machine()).classes('font-mono text-lg')

                        # NiceGUI Version
                        with ui.card().classes('p-4 bg-amber-50 dark:bg-amber-900/20'):
                            with ui.row().classes('items-center gap-2 mb-2'):
                                ui.icon('web', color='amber')
                                ui.label('NiceGUI').classes('font-semibold')
                            ui.label(nicegui_version).classes('font-mono text-lg')

        # Back button
        with ui.row().classes('w-full mt-6'):
            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline')
