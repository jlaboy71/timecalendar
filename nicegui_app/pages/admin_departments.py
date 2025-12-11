"""Admin page for managing departments with dropdown filter and table display."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, validate_required
from src.services.department_service import DepartmentService
from src.services.user_service import UserService
from src.models.user import User


def admin_departments_page():
    """Admin departments management page content."""
    apply_dark_mode()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # State for selected department
    view_state = {'selected_dept_id': None, 'employee_filter': ''}

    def load_department_data():
        """Load all department data with members."""
        db = next(get_db())
        try:
            managers = UserService.get_users_by_role(db, 'manager')
            manager_options = {0: 'No Manager'}
            manager_options.update({m.id: f'{m.first_name} {m.last_name}' for m in managers})
            departments = DepartmentService.get_all_departments(db)

            dept_data = []
            for dept in departments:
                manager_name = 'No Manager'
                if dept.manager_id:
                    manager = UserService(db).get_user_by_id(dept.manager_id)
                    if manager:
                        manager_name = f'{manager.first_name} {manager.last_name}'

                # Get employees in this department
                employees = db.query(User).filter(
                    User.department_id == dept.id,
                    User.is_active == True
                ).order_by(User.last_name, User.first_name).all()

                dept_data.append({
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code,
                    'manager_id': dept.manager_id or 0,
                    'manager_name': manager_name,
                    'is_active': dept.is_active,
                    'employee_count': len(employees),
                    'employees': [{'id': e.id, 'name': f'{e.first_name} {e.last_name}', 'email': e.email, 'role': e.role} for e in employees]
                })
            return dept_data, manager_options
        finally:
            db.close()

    dept_data, manager_options = load_department_data()

    # Build dropdown options for department filter
    dept_dropdown_options = {0: '-- Select Department --'}
    dept_dropdown_options.update({d['id']: f"{d['name']} ({d['employee_count']} employees)" for d in dept_data})

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_header(title='DEPARTMENT MANAGEMENT', show_back=False)

        # Create New Department Card (collapsible)
        with ui.expansion('Create New Department', icon='add_business').classes('w-full mb-4'):
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('w-full gap-4 items-end'):
                    name_input = ui.input('Department Name').props('outlined dense').classes('flex-1')
                    code_input = ui.input('Department Code').props('outlined dense').classes('flex-1')
                    create_manager_select = ui.select(manager_options, label='Manager', value=0).props('outlined dense').classes('flex-1')

                    def create_dept():
                        valid = True
                        if not validate_required(name_input, 'Department Name'):
                            valid = False
                        if not validate_required(code_input, 'Department Code'):
                            valid = False
                        if not valid:
                            ui.notify('Please fix the highlighted errors', type='warning')
                            return
                        db = next(get_db())
                        try:
                            mgr_id = None if create_manager_select.value == 0 else create_manager_select.value
                            DepartmentService.create_department(db, name_input.value, code_input.value, mgr_id)
                            ui.notify(f'Department "{name_input.value}" created successfully', type='positive')
                            ui.navigate.to('/admin/departments')
                        except ValueError as e:
                            ui.notify(str(e), type='negative')
                        finally:
                            db.close()

                    ui.button('Create', icon='add', on_click=create_dept).props('color=primary')

        # Department Filter Card
        with ui.card().classes('w-full mb-4 p-4'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('filter_list', color='primary').classes('text-xl')
                ui.label('Filter by Department').classes('font-semibold')

            with ui.row().classes('w-full items-center gap-4 mt-3'):
                dept_select = ui.select(
                    dept_dropdown_options,
                    label='Select Department',
                    value=0,
                    on_change=lambda e: on_dept_change(e.value)
                ).props('outlined dense').classes('flex-1')

                employee_filter_input = ui.input(
                    placeholder='Filter employees by name or email...'
                ).props('outlined dense clearable debounce="300"').classes('flex-1')
                employee_filter_input.set_visibility(False)

        # Results Container
        results_container = ui.column().classes('w-full')

        def on_dept_change(dept_id):
            view_state['selected_dept_id'] = dept_id if dept_id != 0 else None
            view_state['employee_filter'] = ''
            employee_filter_input.value = ''
            employee_filter_input.set_visibility(dept_id != 0)
            render_department_view()

        def filter_employees():
            view_state['employee_filter'] = employee_filter_input.value or ''
            render_department_view()

        employee_filter_input.on('keydown.enter', lambda: filter_employees())
        employee_filter_input.on('clear', lambda: filter_employees())
        employee_filter_input.on('update:model-value', lambda: filter_employees())  # Real-time filtering with debounce

        def render_department_view():
            results_container.clear()
            selected_id = view_state['selected_dept_id']
            emp_filter = view_state['employee_filter'].lower().strip()

            with results_container:
                if not selected_id:
                    # Show summary of all departments
                    with ui.card().classes('w-full p-4'):
                        ui.label('All Departments').classes('text-lg font-semibold mb-3')
                        ui.label(f'{len(dept_data)} department(s) total').classes('text-sm opacity-70 mb-4')

                        # Summary table
                        columns = [
                            {'name': 'name', 'label': 'Department', 'field': 'name', 'align': 'left', 'sortable': True},
                            {'name': 'code', 'label': 'Code', 'field': 'code', 'align': 'left'},
                            {'name': 'manager', 'label': 'Manager', 'field': 'manager_name', 'align': 'left'},
                            {'name': 'employees', 'label': 'Employees', 'field': 'employee_count', 'align': 'center', 'sortable': True},
                            {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                        ]
                        rows = [
                            {
                                'id': d['id'],
                                'name': d['name'],
                                'code': d['code'],
                                'manager_name': d['manager_name'],
                                'employee_count': d['employee_count'],
                                'status': 'Active' if d['is_active'] else 'Inactive'
                            }
                            for d in dept_data
                        ]

                        def on_row_click(e):
                            # e.args is [evt, row, index] - row is the second element
                            row_data = e.args[1] if len(e.args) > 1 else None
                            if row_data and 'id' in row_data:
                                dept_select.value = row_data['id']
                                on_dept_change(row_data['id'])

                        ui.table(
                            columns=columns,
                            rows=rows,
                            row_key='id',
                            pagination={'rowsPerPage': 10}
                        ).classes('w-full cursor-pointer').on('row-click', on_row_click).props('dense')

                        ui.label('Click a row to view department details').classes('text-xs opacity-50 mt-2')
                else:
                    # Show selected department details
                    dept = next((d for d in dept_data if d['id'] == selected_id), None)
                    if not dept:
                        ui.label('Department not found').classes('text-red-500')
                        return

                    # Department header card
                    with ui.card().classes('w-full p-4 mb-4 border-l-4 border-indigo-500'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(dept['name']).classes('text-xl font-bold')
                                    if dept['is_active']:
                                        ui.badge('Active', color='green').props('outline')
                                    else:
                                        ui.badge('Inactive', color='grey').props('outline')

                                with ui.row().classes('gap-6 text-sm opacity-70 mt-1'):
                                    ui.label(f"Code: {dept['code']}")
                                    ui.label(f"Manager: {dept['manager_name']}")
                                    ui.label(f"Total Employees: {dept['employee_count']}")

                            # Action buttons
                            with ui.row().classes('gap-2'):
                                def create_edit_handler(d):
                                    def open_edit():
                                        with ui.dialog() as edit_dialog, ui.card().classes('p-6 min-w-96'):
                                            ui.label(f"Edit: {d['name']}").classes('text-lg font-semibold mb-4')
                                            edit_name = ui.input('Department Name', value=d['name']).props('outlined').classes('w-full mb-2')
                                            edit_code = ui.input('Department Code', value=d['code']).props('outlined').classes('w-full mb-2')
                                            edit_manager = ui.select(manager_options, label='Manager', value=d['manager_id']).props('outlined').classes('w-full mb-4')

                                            def save_changes():
                                                valid = True
                                                if not validate_required(edit_name, 'Department Name'):
                                                    valid = False
                                                if not validate_required(edit_code, 'Department Code'):
                                                    valid = False
                                                if not valid:
                                                    ui.notify('Please fix the highlighted errors', type='warning')
                                                    return
                                                db = next(get_db())
                                                try:
                                                    mgr_id = None if edit_manager.value == 0 else edit_manager.value
                                                    DepartmentService.update_department(db, d['id'], name=edit_name.value, code=edit_code.value, manager_id=mgr_id)
                                                    ui.notify('Department updated', type='positive')
                                                    edit_dialog.close()
                                                    ui.navigate.to('/admin/departments')
                                                except ValueError as e:
                                                    ui.notify(str(e), type='negative')
                                                finally:
                                                    db.close()

                                            with ui.row().classes('w-full justify-end gap-2'):
                                                ui.button('Cancel', on_click=edit_dialog.close).props('flat')
                                                ui.button('Save', on_click=save_changes).props('color=primary')
                                        edit_dialog.open()
                                    return open_edit

                                ui.button('Edit', icon='edit', on_click=create_edit_handler(dept)).props('flat')

                                def create_delete_handler(d):
                                    def open_delete():
                                        with ui.dialog() as delete_dialog, ui.card().classes('p-6'):
                                            ui.label('Delete Department').classes('text-lg font-semibold mb-2')
                                            if d['employee_count'] > 0:
                                                ui.label(f"Cannot delete: {d['employee_count']} employee(s) assigned").classes('text-red-600 mb-4')
                                                ui.button('Close', on_click=delete_dialog.close).props('flat')
                                            else:
                                                ui.label(f'Delete "{d["name"]}"? This cannot be undone.').classes('mb-4')
                                                with ui.row().classes('gap-2'):
                                                    ui.button('Cancel', on_click=delete_dialog.close).props('flat')
                                                    def confirm():
                                                        db = next(get_db())
                                                        try:
                                                            DepartmentService.delete_department(db, d['id'])
                                                            ui.notify('Deleted', type='positive')
                                                            delete_dialog.close()
                                                            ui.navigate.to('/admin/departments')
                                                        except ValueError as e:
                                                            ui.notify(str(e), type='negative')
                                                        finally:
                                                            db.close()
                                                    ui.button('Delete', on_click=confirm).props('color=red')
                                        delete_dialog.open()
                                    return open_delete

                                ui.button('Delete', icon='delete', on_click=create_delete_handler(dept)).props('flat color=red')

                    # Employees table
                    employees = dept['employees']

                    # Apply employee filter if set
                    if emp_filter:
                        employees = [e for e in employees if emp_filter in e['name'].lower() or emp_filter in e['email'].lower()]

                    with ui.card().classes('w-full p-4'):
                        with ui.row().classes('items-center gap-2 mb-3'):
                            ui.icon('people', color='indigo')
                            ui.label('Department Members').classes('text-lg font-semibold')
                            ui.badge(f'{len(employees)}', color='indigo')

                        if not employees:
                            if emp_filter:
                                ui.label(f'No employees match "{emp_filter}"').classes('opacity-60')
                            else:
                                ui.label('No employees in this department').classes('opacity-60')
                        else:
                            # Employee table - clean rows, not cards
                            emp_columns = [
                                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                                {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'},
                                {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'center'},
                            ]
                            emp_rows = [
                                {'id': e['id'], 'name': e['name'], 'email': e['email'], 'role': e['role'].title()}
                                for e in employees
                            ]

                            ui.table(
                                columns=emp_columns,
                                rows=emp_rows,
                                row_key='id',
                                pagination={'rowsPerPage': 15}
                            ).classes('w-full').props('dense')

        # Initial render
        render_department_view()

        # Back to Dashboard button
        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')
