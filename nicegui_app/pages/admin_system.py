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
from src.models.vacation_accrual_tier import VacationAccrualTier
from src.models.leave_policy import LeavePolicy
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog, show_info_dialog, create_help_button


def admin_system_page():
    """System administration page content."""
    apply_dark_mode()

    # Add custom CSS for pulse animation and hover effects
    ui.add_head_html('''
    <style>
        @keyframes pulse-attention {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        }
        .pulse-attention {
            animation: pulse-attention 2s ease-in-out infinite;
        }
        .nav-hub-card {
            transition: all 0.2s ease;
            border: 2px solid transparent;
        }
        .nav-hub-card:hover {
            border-color: #C9A227 !important;
            transform: translateY(-2px);
        }
        .stat-card {
            transition: all 0.2s ease;
        }
        .stat-card:hover {
            transform: scale(1.02);
        }
        .activity-item {
            transition: background-color 0.2s ease;
        }
        .activity-item:hover {
            background-color: rgba(201, 162, 39, 0.1);
        }
    </style>
    ''')

    # Track page load time for "last refreshed" display
    page_load_time = datetime.now()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role != 'superadmin':
        show_error_dialog('Access Denied', 'Super Admin role is required to access this page.')
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 animate-fade-in'):
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
        db_size = db_path.stat().st_size / (1024 * 1024) if db_exists else 0

        smtp_configured = os.getenv('SMTP_HOST') is not None
        ai_configured = os.getenv('ANTHROPIC_API_KEY') is not None
        logs_dir = Path(__file__).parent.parent.parent / 'logs'
        has_errors = (logs_dir / 'tjm_calendar_errors.log').exists() and (logs_dir / 'tjm_calendar_errors.log').stat().st_size > 0

        with ui.card().classes('w-full p-4 mb-4').style('background: linear-gradient(135deg, #1E2328 0%, #2a3036 100%); border-bottom: 2px solid #C9A227;'):
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

        # Tabs for different sections (consolidated: 4 logical groups)
        with ui.tabs().classes('w-full').props('dense active-color=primary indicator-color=primary') as tabs:
            overview_tab = ui.tab('Overview', icon='dashboard')
            data_tab = ui.tab('Data', icon='storage')
            comms_tab = ui.tab('Communications', icon='email')
            system_tab = ui.tab('System', icon='settings')

        with ui.tab_panels(tabs, value=overview_tab).classes('w-full'):
            # ========== OVERVIEW TAB (Command Center Dashboard) ==========
            with ui.tab_panel(overview_tab):
                # Quick Stats Row
                from src.models.pto_request import PTORequest
                from src.models.user import User
                from src.services.backup_service import BackupService

                db_overview = next(get_db())
                try:
                    active_employees = db_overview.query(User).filter(User.is_active == True).count()
                    pending_requests = db_overview.query(PTORequest).filter(PTORequest.status == 'pending').count()
                    backups = BackupService.list_backups()
                    last_backup = backups[0]['date'] if backups else 'Never'
                except Exception:
                    active_employees = 0
                    pending_requests = 0
                    last_backup = 'Unknown'
                finally:
                    db_overview.close()

                with ui.element('div').classes('w-full').style('display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;'):
                    # Card 1: Active Employees
                    with ui.card().classes('p-4 stat-card').style('border-left: 4px solid #C9A227;'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('people', size='lg', color='primary')
                            with ui.column().classes('gap-0'):
                                ui.label(str(active_employees)).classes('text-3xl font-bold')
                                ui.label('Active Employees').classes('text-xs opacity-60 uppercase')
                        ui.tooltip('Total active user accounts in the system')

                    # Card 2: Pending Requests (with pulse animation when > 0)
                    pending_classes = 'p-4 stat-card cursor-pointer'
                    if pending_requests > 0:
                        pending_classes += ' pulse-attention'
                    with ui.card().classes(pending_classes).style('border-left: 4px solid #ef4444;').on('click', lambda: ui.navigate.to('/admin/approvals')):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('pending_actions', size='lg', color='red')
                            with ui.column().classes('gap-0'):
                                ui.label(str(pending_requests)).classes('text-3xl font-bold text-red-500')
                                ui.label('Pending Approvals').classes('text-xs opacity-60 uppercase')
                        ui.tooltip('Click to review pending PTO requests')

                    # Card 3: Database Size
                    with ui.card().classes('p-4 stat-card').style('border-left: 4px solid #22c55e;'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('storage', size='lg', color='green')
                            with ui.column().classes('gap-0'):
                                ui.label(f'{db_size:.2f} MB' if db_exists else 'N/A').classes('text-3xl font-bold')
                                ui.label('Database Size').classes('text-xs opacity-60 uppercase')
                        db_tooltip = f'SQLite database: {db_path.name}' if db_exists else 'Database not found'
                        ui.tooltip(db_tooltip)

                    # Card 4: Last Backup
                    with ui.card().classes('p-4 stat-card').style('border-left: 4px solid #3b82f6;'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('backup', size='lg', color='blue')
                            with ui.column().classes('gap-0'):
                                ui.label(last_backup if isinstance(last_backup, str) else last_backup.strftime('%b %d')).classes('text-3xl font-bold')
                                ui.label('Last Backup').classes('text-xs opacity-60 uppercase')
                        ui.tooltip('Most recent database backup date')

                # Alerts & Quick Actions Row
                with ui.row().classes('w-full gap-4 mb-6'):
                    # Alerts Card
                    with ui.card().classes('flex-1 p-4'):
                        ui.label('Alerts & Warnings').classes('text-lg font-semibold mb-4')
                        if pending_requests > 0:
                            with ui.element('div').classes('w-full p-3 rounded-lg mb-2').style('background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b;'):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('warning', color='amber')
                                        ui.label(f'{pending_requests} PTO request(s) pending review')
                                    ui.button('Review', on_click=lambda: ui.navigate.to('/admin/approvals')).props('flat dense color=amber')
                        if has_errors:
                            with ui.element('div').classes('w-full p-3 rounded-lg mb-2').style('background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444;'):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('error', color='red')
                                        ui.label('Error log contains entries')
                                    ui.button('View Logs', on_click=lambda: tabs.set_value(system_tab)).props('flat dense color=red')
                        if not pending_requests and not has_errors:
                            with ui.element('div').classes('w-full p-3 rounded-lg').style('background: rgba(34, 197, 94, 0.1); border-left: 4px solid #22c55e;'):
                                with ui.row().classes('w-full items-center gap-2'):
                                    ui.icon('check_circle', color='green')
                                    ui.label('All clear - no pending items or errors')

                    # Quick Actions Card
                    with ui.card().classes('flex-1 p-4'):
                        ui.label('Quick Actions').classes('text-lg font-semibold mb-4')
                        with ui.column().classes('w-full gap-3'):
                            with ui.row().classes('w-full gap-3'):
                                ui.button('Create Backup', icon='backup', on_click=lambda: tabs.set_value(data_tab)).props('outline color=primary').classes('flex-1')
                                ui.button('Send Test Email', icon='send', on_click=lambda: tabs.set_value(comms_tab)).props('outline color=primary').classes('flex-1')
                            with ui.row().classes('w-full gap-3'):
                                ui.button('View Audit Log', icon='security', on_click=lambda: tabs.set_value(system_tab)).props('outline color=primary').classes('flex-1')
                                ui.button('Sync Holidays', icon='sync', on_click=lambda: tabs.set_value(data_tab)).props('outline color=primary').classes('flex-1')

                # Navigation Hub
                with ui.card().classes('w-full p-4'):
                    with ui.row().classes('items-center justify-between mb-4'):
                        ui.label('Administration Hub').classes('text-lg font-semibold')
                        ui.label(f'Last refreshed: {page_load_time.strftime("%I:%M %p")}').classes('text-xs opacity-50')
                    with ui.element('div').classes('grid grid-cols-4 gap-4 w-full'):
                        nav_items = [
                            ('people', 'Employees', 'Manage employee accounts', '/admin/employees'),
                            ('business', 'Departments', 'Organizational structure', '/admin/departments'),
                            ('menu_book', 'Handbook', 'Policy documents', '/admin/handbook'),
                            ('event_repeat', 'Year-End', 'EOY processing status', '/admin/year-end'),
                            ('analytics', 'Analytics', 'Usage insights', '/analytics'),
                            ('assessment', 'Reports', 'Generate reports', '/reports'),
                            ('approval', 'Approvals', 'Pending requests', '/admin/approvals'),
                            ('help_outline', 'Help Center', 'Documentation', '/help'),
                        ]
                        for icon, title, desc, url in nav_items:
                            with ui.card().classes('w-full p-3 cursor-pointer nav-hub-card').on('click', lambda u=url: ui.navigate.to(u)):
                                with ui.row().classes('w-full items-center gap-3'):
                                    ui.icon(icon, size='md').style('color: #C9A227;')
                                    with ui.column().classes('flex-1 gap-0'):
                                        ui.label(title).classes('font-semibold')
                                        ui.label(desc).classes('text-xs opacity-60')

                # System Info Footer
                with ui.element('div').classes('w-full mt-6 pt-4').style('border-top: 1px solid rgba(255,255,255,0.1);'):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.row().classes('items-center gap-4'):
                            # Python version
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('code', size='xs').classes('opacity-40')
                                ui.label(f'Python {platform.python_version()}').classes('text-xs opacity-40')
                            # Platform
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('computer', size='xs').classes('opacity-40')
                                ui.label(f'{platform.system()} {platform.release()}').classes('text-xs opacity-40')
                            # App version
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('info', size='xs').classes('opacity-40')
                                ui.label('TJM Calendar v1.0').classes('text-xs opacity-40')
                        # Refresh button
                        ui.button('Refresh Dashboard', icon='refresh', on_click=lambda: ui.navigate.to('/admin/system')).props('flat dense size=sm').style('color: #C9A227 !important;')

            # ========== DATA TAB (Database + EOY + Market Calendar) ==========
            with ui.tab_panel(data_tab):
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

            # ========== COMMUNICATIONS TAB (Email Config + Auto Notify) ==========
            with ui.tab_panel(comms_tab):
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

            # ========== SYSTEM TAB (Logs + Settings + Policy) ==========
            with ui.tab_panel(system_tab):
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
                                elif filter_val == 'cancellations':
                                    query = query.filter(AuditLog.action == 'pto_cancel')
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
                                'cancellations': 'Cancellations',
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

                # ========== SETTINGS SECTION ==========
                ui.separator().classes('my-6')
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('settings', size='md', color='primary')
                    ui.label('System Settings').classes('text-lg font-semibold')

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
                                        setting.updated_by = app.storage.user.get('user', {}).get('id')
                                    else:
                                        # Create setting if it doesn't exist
                                        new_setting = SystemSetting(
                                            key='chicago.safe_leave_enabled',
                                            value='true' if e.value else 'false',
                                            description='Enable Chicago Paid Sick and Safe Leave feature for Chicago employees',
                                            updated_by=app.storage.user.get('user', {}).get('id')
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

                # ========== POLICY REFERENCE SECTION ==========
                ui.separator().classes('my-6')
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('policy', size='md', color='amber')
                    ui.label('Policy Quick Reference').classes('text-lg font-semibold')

                # 1. Vacation Tiers
                with ui.expansion('Vacation Tiers (Tenure-Based)', icon='beach_access').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Annual vacation allocation based on years of service:').classes('text-sm opacity-70 mb-3')
                        tiers = [
                            ('0-1 years', '10 days (80 hrs)'),
                            ('2-4 years', '12 days (96 hrs)'),
                            ('5-9 years', '15 days (120 hrs)'),
                            ('10+ years', '20 days (160 hrs)'),
                        ]
                        for years, days in tiers:
                            with ui.row().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                ui.label(years).classes('flex-1 font-medium')
                                ui.label(days).classes('text-sm opacity-70')

                # 2. Annual Leave Allocations
                with ui.expansion('Annual Leave Allocations', icon='calendar_today').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Front-loaded allocation on January 1st each year:').classes('text-sm opacity-70 mb-3')
                        allocations = [
                            ('Vacation', 'Based on tenure tier (see above)'),
                            ('Sick', '5 days (40 hrs) per year'),
                            ('Personal', '2 days (16 hrs) per year'),
                        ]
                        for leave_type, amount in allocations:
                            with ui.row().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                ui.label(leave_type).classes('w-24 font-medium')
                                ui.label(amount).classes('flex-1 text-sm opacity-70')
                        ui.label('No monthly accrual - employees get full balance upfront.').classes('text-xs opacity-50 italic mt-3')

                # 3. Carryover Rules
                with ui.expansion('Carryover Rules', icon='sync').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        carryover_rules = [
                            ('Vacation', 'NO auto-carryover (use-it-or-lose-it)', 'Exception requests may be approved by manager as BONUS'),
                            ('Sick', 'AUTO-carryover', 'Up to 56-80 hrs based on location policy'),
                            ('Personal', 'NO carryover', 'Use-it-or-lose-it, does not roll over'),
                        ]
                        for leave_type, rule, detail in carryover_rules:
                            with ui.column().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                with ui.row().classes('w-full items-center'):
                                    ui.label(leave_type).classes('w-24 font-medium')
                                    ui.label(rule).classes('font-semibold')
                                ui.label(detail).classes('text-sm opacity-70 pl-24')

                # 4. Leave Types (Accruing vs Non-Accruing)
                with ui.expansion('Leave Types & Policies', icon='event_available').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Accruing Leave (tracked in balance):').classes('font-semibold mb-2')
                        accruing = [
                            ('Vacation', 'Primary PTO, requires approval, pending tracking'),
                            ('Sick', 'No pending tracking, auto-carryover up to policy max'),
                            ('Personal', '24hr advance notice preferred when possible'),
                        ]
                        for leave_type, desc in accruing:
                            with ui.row().classes('w-full py-1'):
                                ui.label(f'• {leave_type}:').classes('w-24 font-medium')
                                ui.label(desc).classes('flex-1 text-sm opacity-70')

                        ui.separator().classes('my-3')
                        ui.label('Non-Accruing Leave (no balance limits):').classes('font-semibold mb-2')
                        non_accruing = [
                            ('Bereavement', 'Immediate family: 5 days | Extended family: 3 days'),
                            ('FMLA', 'Up to 12 weeks unpaid, job-protected'),
                            ('Jury Duty', 'Paid time for service'),
                            ('Voting', 'Up to 2 hours if needed'),
                            ('Military', 'Per USERRA requirements'),
                        ]
                        for leave_type, desc in non_accruing:
                            with ui.row().classes('w-full py-1'):
                                ui.label(f'• {leave_type}:').classes('w-28 font-medium')
                                ui.label(desc).classes('flex-1 text-sm opacity-70')

                # 5. Request Workflow & Auto-Approval
                with ui.expansion('Request Workflow & Approvals', icon='approval').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Employee Requests:').classes('font-semibold mb-2')
                        employee_flow = [
                            '1. Employee submits request (status: pending)',
                            '2. Vacation hours added to pending balance',
                            '3. Manager reviews and approves/denies',
                            '4. On approval: pending moves to used',
                            '5. On denial: pending hours returned',
                        ]
                        for step in employee_flow:
                            ui.label(step).classes('text-sm opacity-70 py-1')

                        ui.separator().classes('my-3')
                        ui.label('Auto-Approval (No Manager Review):').classes('font-semibold mb-2')
                        ui.label('The following roles can self-approve their own PTO:').classes('text-sm opacity-70 mb-2')
                        auto_approve_roles = ['Managers', 'Admins', 'SuperAdmins']
                        for role in auto_approve_roles:
                            ui.label(f'• {role}').classes('text-sm opacity-70 pl-4')
                        ui.label('Hours go directly to used (no pending state).').classes('text-xs opacity-50 italic mt-2')

                # 6. Federal Holidays
                with ui.expansion('Federal Holidays (10 per year)', icon='celebration').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Auto-generated each year. Weekend holidays observed on nearest weekday.').classes('text-sm opacity-70 mb-3')
                        with ui.row().classes('w-full gap-8'):
                            with ui.column().classes('flex-1'):
                                holidays_col1 = ["New Year's Day", 'MLK Day', 'Presidents Day', 'Good Friday', 'Memorial Day']
                                for holiday in holidays_col1:
                                    ui.label(f'• {holiday}').classes('text-sm py-1')
                            with ui.column().classes('flex-1'):
                                holidays_col2 = ['Juneteenth', 'Independence Day', 'Labor Day', 'Thanksgiving', 'Christmas Day']
                                for holiday in holidays_col2:
                                    ui.label(f'• {holiday}').classes('text-sm py-1')

                # 7. Year-End Processing
                with ui.expansion('Year-End Processing', icon='event_repeat').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Runs automatically on first app access of new year:').classes('text-sm opacity-70 mb-3')
                        year_end_steps = [
                            ('1. Create new year balances', 'For all active employees'),
                            ('2. Auto-carryover sick leave', 'Up to policy maximum (varies by location)'),
                            ('3. Apply exception carryover', 'Approved vacation carryover as BONUS'),
                            ('4. Generate federal holidays', 'For the new year'),
                        ]
                        for step, desc in year_end_steps:
                            with ui.row().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                ui.label(step).classes('w-48 font-medium')
                                ui.label(desc).classes('flex-1 text-sm opacity-70')
                        ui.label('Note: Personal days do NOT carry over.').classes('text-xs opacity-50 italic mt-3')

                # 8. Location-Based Policies
                with ui.expansion('Location-Based Policy Overrides', icon='location_on').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('Policy Resolution Order (highest to lowest priority):').classes('text-sm opacity-70 mb-3')
                        policy_order = [
                            ('1. City-specific', 'e.g., Chicago, IL'),
                            ('2. State-specific', 'e.g., IL'),
                            ('3. Default', 'No location specified'),
                        ]
                        for priority, example in policy_order:
                            with ui.row().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                ui.label(priority).classes('w-32 font-medium')
                                ui.label(example).classes('flex-1 text-sm opacity-70')

                        ui.separator().classes('my-3')
                        ui.label('Key State Variations:').classes('font-semibold mb-2')
                        variations = [
                            'Different sick leave accrual rates',
                            'Different carryover maximums',
                            'Different waiting periods for new employees',
                        ]
                        for v in variations:
                            ui.label(f'• {v}').classes('text-sm opacity-70 py-1')

                # 9. Quick FAQ
                with ui.expansion('Quick FAQ', icon='help_outline').classes('w-full mb-2'):
                    with ui.card().classes('w-full p-4'):
                        qa_items = [
                            ('Who can self-approve PTO?', 'Managers, Admins, and SuperAdmins'),
                            ('When does year-end processing run?', 'Automatically on first login after January 1st'),
                            ('How many federal holidays are there?', '10 per year'),
                            ('Can I request time off for next year?', 'Yes, up to 5 years in advance'),
                            ('What if my request exceeds my balance?', 'Warning shown, but submission NOT blocked - manager discretion'),
                            ('How does vacation carryover work?', 'Exception only - must be approved by manager as a BONUS'),
                            ('Does sick leave carry over?', 'Yes, automatically up to the location policy maximum'),
                        ]
                        for q, a in qa_items:
                            with ui.column().classes('w-full py-2').style('border-bottom: 1px solid rgba(255,255,255,0.1)'):
                                ui.label(q).classes('font-medium')
                                ui.label(a).classes('text-sm opacity-70 mt-1')

                ui.label('For full policy details, see the Employee Handbook.').classes('text-xs opacity-50 italic mt-4')

        # Back button - returns to Overview tab first, then to previous page
        def handle_back():
            """If on a non-Overview tab, go to Overview first. Otherwise use browser history."""
            if tabs.value != overview_tab:
                tabs.set_value(overview_tab)
            else:
                go_back()

        with ui.row().classes('w-full mt-6'):
            ui.button('Back', icon='arrow_back', on_click=handle_back).props('outline')
