"""Admin page for year-end processing status (automatic processing)."""
from datetime import datetime, date
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from src.services.year_end_service import YearEndService


def admin_year_end_page():
    """Admin year-end processing status page content."""
    apply_dark_mode()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    current_year = datetime.now().year
    next_year = current_year + 1
    today = date.today()

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='YEAR-END STATUS', show_back=False)

        # ========== WHAT IS YEAR-END PROCESSING? ==========
        with ui.expansion('What is Year-End Processing?', icon='help_outline').classes('w-full mb-4').props('default-opened'):
            with ui.card().classes('w-full p-4 bg-blue-50 dark:bg-blue-900/20'):
                ui.label('Purpose & Overview').classes('text-lg font-bold text-blue-700 dark:text-blue-300 mb-2')

                ui.markdown('''
Year-end processing is an **automatic system** that prepares the TJM Time Calendar for each new calendar year.
It runs **once per year**, triggered by the first user login after January 1st.

**Why is this needed?**
- Each employee needs fresh PTO balances for the new year
- Approved carryover requests need to be added to new balances
- Federal and market holidays need to be generated for the new year
- This ensures the system is ready without any manual intervention
''').classes('text-sm')

                ui.separator().classes('my-3')

                ui.label('What Happens During Processing').classes('font-semibold text-blue-700 dark:text-blue-300 mb-2')

                with ui.column().classes('gap-2'):
                    with ui.row().classes('items-start gap-3'):
                        ui.icon('person_add', color='blue').classes('mt-1')
                        with ui.column().classes('gap-0'):
                            ui.label('1. Create PTO Balances').classes('font-medium')
                            ui.label('Every active employee receives their annual PTO allocation based on years of service:').classes('text-sm opacity-70')
                            ui.label('• 0-4 years: 10 vacation days  •  5-9 years: 15 days  •  10+ years: 20 days').classes('text-xs opacity-60 ml-4')
                            ui.label('• Plus: 5 sick days and 2 personal days for everyone').classes('text-xs opacity-60 ml-4')

                    with ui.row().classes('items-start gap-3'):
                        ui.icon('swap_horiz', color='purple').classes('mt-1')
                        with ui.column().classes('gap-0'):
                            ui.label('2. Apply Carryover Requests (Sick Time Only)').classes('font-medium')
                            ui.label('Unused sick time can be carried over to the next year (up to policy limits). Vacation and personal days cannot be carried over.').classes('text-sm opacity-70')
                            ui.label('• Sick Time: Up to 56-80 hours can roll over depending on location').classes('text-xs opacity-60 ml-4')
                            ui.label('• Vacation: Use it or lose it - no carryover allowed').classes('text-xs opacity-60 ml-4')
                            ui.label('• Personal Days: Use it or lose it - no carryover allowed').classes('text-xs opacity-60 ml-4')

                    with ui.row().classes('items-start gap-3'):
                        ui.icon('event', color='teal').classes('mt-1')
                        with ui.column().classes('gap-0'):
                            ui.label('3. Generate Market Holidays').classes('font-medium')
                            ui.label('Federal and exchange holidays (NYSE, CME, CBOE) are automatically calculated for the new year.').classes('text-sm opacity-70')
                            ui.label('Includes: New Year, MLK Day, Presidents Day, Good Friday, Memorial Day, Juneteenth, July 4th, Labor Day, Thanksgiving, Christmas').classes('text-xs opacity-60 ml-4')

                ui.separator().classes('my-3')

                ui.label('When Does It Run?').classes('font-semibold text-blue-700 dark:text-blue-300 mb-2')
                ui.markdown('''
- **Trigger**: First login by any user on or after January 1st of the new year
- **Duration**: Usually completes in a few seconds
- **Frequency**: Once per year (the system tracks if it has already run)
- **No action required**: This is fully automatic - you don't need to do anything
''').classes('text-sm')

        # Status cards container
        status_container = ui.column().classes('w-full gap-4')

        def refresh_status():
            status_container.clear()
            db = next(get_db())
            try:
                service = YearEndService(db)

                # Current year status
                current_status = service.get_year_end_status(current_year)
                processing_record = service.get_processing_record(current_year)

                # Next year status
                next_status = service.get_year_end_status(next_year)
                next_record = service.get_processing_record(next_year)

                with status_container:
                    # ========== CURRENT YEAR STATUS ==========
                    with ui.card().classes('w-full p-4'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label(f'{current_year} Status').classes('text-xl font-bold')
                            if processing_record and processing_record.processed:
                                ui.badge('COMPLETE', color='green').classes('text-sm')
                            else:
                                ui.badge('PENDING', color='orange').classes('text-sm')

                        if processing_record and processing_record.processed:
                            # Show when it was processed
                            with ui.row().classes('items-center gap-2 mb-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg'):
                                ui.icon('check_circle', color='green').classes('text-2xl')
                                with ui.column().classes('gap-0'):
                                    ui.label('Year-End Processing Complete').classes('font-semibold text-green-700 dark:text-green-300')
                                    ui.label(f"Processed on {processing_record.processed_at.strftime('%B %d, %Y at %I:%M %p')}").classes('text-sm opacity-70')

                            # Processing results
                            with ui.row().classes('gap-6 flex-wrap'):
                                with ui.card().classes('p-4 text-center min-w-32'):
                                    ui.label(str(processing_record.balances_created)).classes('text-3xl font-bold text-blue-600')
                                    ui.label('PTO Balances').classes('text-sm opacity-70')
                                    ui.label('Created').classes('text-xs opacity-50')

                                with ui.card().classes('p-4 text-center min-w-32'):
                                    ui.label(str(processing_record.carryovers_applied)).classes('text-3xl font-bold text-purple-600')
                                    ui.label('Carryovers').classes('text-sm opacity-70')
                                    ui.label('Applied').classes('text-xs opacity-50')

                                with ui.card().classes('p-4 text-center min-w-32'):
                                    ui.label(str(processing_record.holidays_created)).classes('text-3xl font-bold text-teal-600')
                                    ui.label('Holidays').classes('text-sm opacity-70')
                                    ui.label('Generated').classes('text-xs opacity-50')
                        else:
                            with ui.row().classes('items-center gap-2 mb-4 p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg'):
                                ui.icon('schedule', color='orange').classes('text-2xl')
                                with ui.column().classes('gap-0'):
                                    ui.label('Awaiting Processing').classes('font-semibold text-orange-700 dark:text-orange-300')
                                    ui.label('Will run automatically on the first login of the new year.').classes('text-sm opacity-70')

                        # Current year details
                        ui.separator().classes('my-4')
                        ui.label('Current Data').classes('font-semibold mb-2')

                        with ui.row().classes('gap-8 flex-wrap'):
                            with ui.column().classes('gap-1'):
                                ui.label('Active Employees').classes('text-xs opacity-60 uppercase')
                                ui.label(str(current_status['active_users'])).classes('text-xl font-semibold')
                            with ui.column().classes('gap-1'):
                                ui.label('PTO Balances').classes('text-xs opacity-60 uppercase')
                                ui.label(str(current_status['balances_created'])).classes('text-xl font-semibold')
                            with ui.column().classes('gap-1'):
                                ui.label('Pending Carryovers').classes('text-xs opacity-60 uppercase')
                                pending = current_status['pending_carryovers']
                                color = 'text-amber-600' if pending > 0 else ''
                                ui.label(str(pending)).classes(f'text-xl font-semibold {color}')
                            with ui.column().classes('gap-1'):
                                ui.label('Holidays').classes('text-xs opacity-60 uppercase')
                                ui.label(str(current_status['holidays_created'])).classes('text-xl font-semibold')

                    # ========== NEXT YEAR PREVIEW ==========
                    with ui.card().classes('w-full p-4'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label(f'{next_year} Preview').classes('text-xl font-bold')
                            if next_record and next_record.processed:
                                ui.badge('ALREADY PROCESSED', color='green').classes('text-sm')
                            else:
                                # Calculate days until new year
                                new_years_day = date(next_year, 1, 1)
                                days_until = (new_years_day - today).days
                                if days_until > 0:
                                    ui.badge(f'{days_until} days until processing', color='blue').props('outline').classes('text-sm')
                                else:
                                    ui.badge('Ready to process on next login', color='blue').classes('text-sm')

                        if next_record and next_record.processed:
                            with ui.row().classes('items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg'):
                                ui.icon('check_circle', color='green')
                                ui.label(f'{next_year} has already been processed. No action needed.').classes('text-sm')
                        else:
                            with ui.row().classes('items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg'):
                                ui.icon('info', color='blue')
                                with ui.column().classes('gap-1'):
                                    ui.label(f'On the first login of {next_year}, the system will automatically:').classes('text-sm font-medium')
                                    ui.label(f'• Create PTO balances for {next_status["active_users"]} active employees').classes('text-xs opacity-70')
                                    ui.label('• Apply any approved carryover requests').classes('text-xs opacity-70')
                                    ui.label('• Generate federal and market holidays').classes('text-xs opacity-70')

                        # Show what's ready vs what will be created
                        ui.separator().classes('my-4')
                        ui.label('Preparation Status').classes('font-semibold mb-2')

                        with ui.row().classes('gap-4 flex-wrap'):
                            # Balances
                            balances_ready = next_status['balances_created']
                            balances_needed = next_status['active_users']
                            with ui.card().classes('p-3 flex-1 min-w-48'):
                                with ui.row().classes('items-center gap-2 mb-2'):
                                    if balances_ready >= balances_needed:
                                        ui.icon('check_circle', color='green')
                                    else:
                                        ui.icon('pending', color='blue')
                                    ui.label('PTO Balances').classes('font-medium')
                                ui.label(f'{balances_ready} / {balances_needed} employees').classes('text-sm opacity-70')
                                if balances_ready < balances_needed:
                                    ui.label(f'{balances_needed - balances_ready} will be created').classes('text-xs text-blue-600')

                            # Holidays
                            holidays_ready = next_status['holidays_created']
                            with ui.card().classes('p-3 flex-1 min-w-48'):
                                with ui.row().classes('items-center gap-2 mb-2'):
                                    if holidays_ready > 0:
                                        ui.icon('check_circle', color='green')
                                    else:
                                        ui.icon('pending', color='blue')
                                    ui.label('Market Holidays').classes('font-medium')
                                if holidays_ready > 0:
                                    ui.label(f'{holidays_ready} holidays ready').classes('text-sm opacity-70')
                                else:
                                    ui.label('Will be generated automatically').classes('text-sm opacity-70')
                                    ui.label('~48 holidays (NYSE, CME, CBOE, Federal)').classes('text-xs text-blue-600')

                    # ========== WARNINGS ==========
                    if current_status['pending_carryovers'] > 0:
                        with ui.card().classes('w-full p-4 border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20'):
                            with ui.row().classes('items-start gap-3'):
                                ui.icon('warning', color='amber').classes('text-2xl')
                                with ui.column().classes('flex-1 gap-2'):
                                    ui.label(f'Action Required: {current_status["pending_carryovers"]} Pending Carryover Requests').classes('font-semibold text-amber-700 dark:text-amber-300')
                                    ui.label('These carryover requests need to be approved or denied before the new year. '
                                             'Only approved requests will be applied to next year\'s balances.').classes('text-sm opacity-80')
                                    ui.button('Review Carryover Requests', icon='approval',
                                              on_click=lambda: ui.navigate.to('/manager/carryover')).props('color=amber').classes('mt-2')

                    # ========== HELPFUL INFO ==========
                    with ui.expansion('Frequently Asked Questions', icon='quiz').classes('w-full mt-4'):
                        with ui.column().classes('gap-4 p-2'):
                            with ui.column().classes('gap-1'):
                                ui.label('Q: What if I add a new employee after year-end processing?').classes('font-medium')
                                ui.label('A: New employees automatically get their PTO balance created when they are added to the system.').classes('text-sm opacity-70')

                            with ui.column().classes('gap-1'):
                                ui.label('Q: Can I manually trigger year-end processing?').classes('font-medium')
                                ui.label('A: No, it runs automatically to prevent errors. However, you can sync holidays manually in System Administration.').classes('text-sm opacity-70')

                            with ui.column().classes('gap-1'):
                                ui.label('Q: What happens to unused PTO at year end?').classes('font-medium')
                                ui.label('A: Vacation and personal days are "use it or lose it" - they cannot be carried over. Sick time can roll over up to policy limits (typically 56-80 hours depending on location).').classes('text-sm opacity-70')

                            with ui.column().classes('gap-1'):
                                ui.label('Q: Will employees be notified when processing completes?').classes('font-medium')
                                ui.label('A: Employees can view their new balances on their dashboard. Email notifications can be configured in System Administration.').classes('text-sm opacity-70')

            finally:
                db.close()

        # Initial load
        refresh_status()

        # Action buttons
        with ui.row().classes('w-full gap-4 mt-4 justify-center'):
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline')
            ui.button('Refresh Status', on_click=refresh_status, icon='refresh')
            if user_role == 'superadmin':
                ui.button('System Administration', icon='settings', on_click=lambda: ui.navigate.to('/admin/system')).props('outline')
