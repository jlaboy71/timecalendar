"""Manager team management page."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode
from src.services.user_service import UserService
from src.services.department_service import DepartmentService


def manager_team_page():
    """Manager team management page content."""
    apply_dark_mode()

    current_user = app.storage.user.get('user', {})
    user_role = current_user.get('role')
    department_id = current_user.get('department_id')

    # Only managers can access this page
    if user_role != 'manager':
        ui.navigate.to('/dashboard')
        return

    if not department_id:
        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='MY TEAM', show_back=False)
            ui.label('You are not assigned to a department').classes('text-lg text-center')
        return

    # Load team data
    db = next(get_db())
    try:
        user_service = UserService(db)
        department = DepartmentService.get_department_by_id(db, department_id)
        dept_name = department.name if department else 'Unknown'

        # Get all employees in the manager's department (excluding the manager)
        team_members = user_service.get_users_by_department(department_id)
        # Filter to only employees (not other managers/admins) and active users
        team_members = [m for m in team_members if m.id != current_user.get('id') and m.role == 'employee' and m.is_active]

    finally:
        db.close()

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title=f'MY TEAM - {dept_name.upper()}', show_back=False)

        if not team_members:
            with ui.card().classes('w-full p-6 text-center'):
                ui.icon('group_off', size='xl').classes('opacity-40')
                ui.label('No team members found').classes('text-lg mt-2')
                ui.label('Employees in your department will appear here').classes('text-sm opacity-60')
        else:
            # Filter controls
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                ui.label(f'{len(team_members)} team members').classes('text-sm opacity-60')
                ui.space()

                # Employee filter dropdown
                filter_options = {0: 'All Employees'}
                for m in sorted(team_members, key=lambda x: x.full_name):
                    filter_options[m.id] = m.full_name

                selected_filter = {'value': 0}

                def on_filter_change(e):
                    selected_filter['value'] = e.value
                    render_team_list()

                ui.select(filter_options, value=0, on_change=on_filter_change, label='Filter').props('outlined dense').classes('w-48')

            # Team list container
            team_container = ui.column().classes('w-full gap-3')

            def render_team_list():
                team_container.clear()
                with team_container:
                    # Filter members based on selection
                    filtered_members = team_members
                    if selected_filter['value'] != 0:
                        filtered_members = [m for m in team_members if m.id == selected_filter['value']]

                    for member in sorted(filtered_members, key=lambda x: x.full_name):
                        with ui.card().classes('w-full p-4 hover:shadow-md transition-shadow'):
                            with ui.row().classes('w-full justify-between items-center'):
                                # Employee info
                                with ui.column().classes('gap-1'):
                                    ui.label(member.full_name).classes('text-lg font-semibold')
                                    with ui.row().classes('gap-3 items-center'):
                                        ui.label(f'@{member.username}').classes('text-sm opacity-60')
                                        ui.label(f'• {member.email}').classes('text-sm opacity-60')
                                    if member.hire_date:
                                        ui.label(f'Hired: {member.hire_date.strftime("%A, %B %d, %Y")}').classes('text-xs opacity-50')

                                # Actions
                                with ui.row().classes('gap-2'):
                                    def create_edit_handler(user_id):
                                        def edit():
                                            ui.navigate.to(f'/admin/employees/edit/{user_id}')
                                        return edit
                                    ui.button('Edit', icon='edit', on_click=create_edit_handler(member.id)).props('flat dense color=primary')

            # Initial render
            render_team_list()

        # Navigation buttons
        with ui.row().classes('w-full justify-start mt-6'):
            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline')
