"""Admin panel landing page with navigation to admin functions."""
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, PTO_GOLD, PTO_GRAY, BRAND_COLORS


def admin_dashboard_page():
    """Admin panel landing page content."""
    apply_dark_mode()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='ADMIN PANEL', show_back=False)

        # Navigation cards (flex-wrap for mobile responsive)
        with ui.row().classes('w-full gap-4 justify-center flex-wrap stagger-children'):
            # Manage Departments card
            with ui.card().classes('p-6 cursor-pointer shadow-md hover:shadow-xl transition-all'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('business', size='3rem').classes('text-primary')
                    ui.label('Manage Departments').classes('text-xl font-semibold')
                    ui.label('Create and manage organizational departments').classes('text-gray-600 text-center')
                    ui.button('Go to Departments', on_click=lambda: ui.navigate.to('/admin/departments'), color='primary')

            # Manage Employees card
            with ui.card().classes('p-6 cursor-pointer shadow-md hover:shadow-xl transition-all'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('people', size='3rem').classes('text-primary')
                    ui.label('Manage Employees').classes('text-xl font-semibold')
                    ui.label('Add, edit, and manage employee accounts').classes('text-gray-600 text-center')
                    ui.button('Go to Employees', on_click=lambda: ui.navigate.to('/admin/employees'), color='primary')

            # Carryover Approvals card
            with ui.card().classes('p-6 cursor-pointer shadow-md hover:shadow-xl transition-all'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('approval', size='3rem').classes('text-primary')
                    ui.label('Carryover Approvals').classes('text-xl font-semibold')
                    ui.label('Review and approve employee carryover requests').classes('text-gray-600 text-center')
                    ui.button('Go to Approvals', on_click=lambda: ui.navigate.to('/manager/carryover'), color='primary')

            # PTO Assistant card - AI scheduling assistant
            with ui.card().classes('p-6 cursor-pointer shadow-md hover:shadow-xl transition-all border-2').style(f'border-color: {PTO_GOLD};'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('smart_toy', size='3rem').style(f'color: {PTO_GOLD};')
                    ui.label('PTO ASSISTANT').classes('text-xl font-semibold')
                    ui.label('AI-powered scheduling assistant for PTO planning').classes('text-gray-600 text-center')
                    ui.button('Launch', on_click=lambda: ui.navigate.to('/assistant')).style(f'background-color: {PTO_GOLD} !important; color: white !important;')

        # Second row - Super Admin only (flex-wrap for mobile responsive)
        if user_role == 'superadmin':
            with ui.row().classes('w-full gap-4 justify-center mt-6 flex-wrap stagger-children'):
                # System Administration card
                with ui.card().classes('p-6 cursor-pointer shadow-md hover:shadow-xl transition-all border-2 border-amber-500'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('settings_applications', size='3rem').classes('text-amber-600')
                        ui.label('System Administration').classes('text-xl font-semibold')
                        ui.label('Database, email config, logs, and system settings').classes('text-gray-600 text-center')
                        ui.button('System Settings', on_click=lambda: ui.navigate.to('/admin/system'), color='warning')

        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-8')
