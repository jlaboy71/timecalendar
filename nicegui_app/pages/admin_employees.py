"""Admin pages for managing employees - list, add, and edit."""
import re
import json
from datetime import datetime
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, validate_required, validate_email, validate_min_length, show_warning_dialog, show_error_dialog, show_success_dialog
from src.services.user_service import UserService
from src.services.department_service import DepartmentService
from src.services.audit_service import AuditService
from src.services.balance_service import BalanceService
from src.schemas.user_schemas import UserCreate, UserUpdate


def admin_employees_list_page():
    """Admin page for managing employees - list view."""
    apply_dark_mode()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    # Load data
    db = next(get_db())
    try:
        # Get all users and departments
        all_users = UserService(db).get_all_users()
        departments = DepartmentService.get_all_departments(db)

        # Create department lookup
        dept_lookup = {dept.id: dept.name for dept in departments}

        # Build complete row data for all users
        all_rows = []
        for user in all_users:
            department_name = 'No Department'
            if user.department_id:
                department_name = dept_lookup.get(user.department_id, 'Unknown Department')

            all_rows.append({
                'id': user.id,
                'name': f'{user.first_name} {user.last_name}',
                'username': user.username,
                'department': department_name,
                'department_id': user.department_id,
                'role': user.role.title(),
                'role_raw': user.role,
                'hire_date': user.hire_date.strftime('%m-%d-%Y') if user.hire_date else 'Not Set',
                'active': 'Yes' if user.is_active else 'No',
                'is_active': user.is_active,
                'trusted': '✓' if user.is_trusted else '',
                'is_trusted': user.is_trusted,
            })

        # Build autocomplete options from employee names
        employee_names = [row['name'] for row in all_rows]

    finally:
        db.close()

    # Filter state
    filter_state = {
        'search': '',
        'department_id': None,
        'status': 'all',
        'role': None,
    }

    # Pagination state
    pagination_state = {
        'page': 1,
        'per_page': 25,
    }

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='EMPLOYEE MANAGEMENT', show_back=False)

        # Add New Employee button
        ui.button('Add New Employee', icon='person_add', on_click=lambda: ui.navigate.to('/admin/employees/add')).props('color=primary').classes('mb-4')

        # Filters card
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label('Search & Filter').classes('text-sm font-semibold uppercase opacity-60 mb-3')

            with ui.row().classes('w-full gap-4 items-end flex-wrap'):
                # Search input with autocomplete
                search_input = ui.input(
                    placeholder='Search by name or username...',
                    autocomplete=employee_names
                ).classes('flex-grow min-w-48').props('clearable outlined dense debounce="300"')

                # Department filter
                dept_options = {None: 'All Departments'}
                dept_options.update({dept.id: dept.name for dept in departments})
                dept_select = ui.select(
                    dept_options,
                    label='Department',
                    value=None
                ).classes('w-48').props('outlined dense')

                # Role filter
                role_options = {None: 'All Roles', 'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Superadmin'}
                role_select = ui.select(
                    role_options,
                    label='Role',
                    value=None
                ).classes('w-40').props('outlined dense')

                # Status filter
                status_options = {'all': 'All Status', 'active': 'Active Only', 'inactive': 'Inactive Only'}
                status_select = ui.select(
                    status_options,
                    label='Status',
                    value='all'
                ).classes('w-36').props('outlined dense')

        # Results count
        results_label = ui.label('').classes('text-sm opacity-60 mb-2')

        # Table container
        table_container = ui.column().classes('w-full')

        # Table columns
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
            {'name': 'username', 'label': 'Username', 'field': 'username', 'align': 'left', 'sortable': True},
            {'name': 'department', 'label': 'Department', 'field': 'department', 'align': 'left', 'sortable': True},
            {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left', 'sortable': True},
            {'name': 'hire_date', 'label': 'Hire Date', 'field': 'hire_date', 'align': 'left', 'sortable': True},
            {'name': 'active', 'label': 'Active', 'field': 'active', 'align': 'center', 'sortable': True},
            {'name': 'trusted', 'label': 'Trusted', 'field': 'trusted', 'align': 'center', 'sortable': True},
        ]

        def has_any_filter():
            return (
                filter_state['search'].strip() != '' or
                filter_state['department_id'] is not None or
                filter_state['role'] is not None or
                filter_state['status'] != 'all'
            )

        def filter_and_render():
            table_container.clear()

            filtered_rows = all_rows.copy()

            search_term = filter_state['search'].lower().strip()
            if search_term:
                filtered_rows = [r for r in filtered_rows if search_term in r['name'].lower() or search_term in r['username'].lower()]

            if filter_state['department_id'] is not None:
                filtered_rows = [r for r in filtered_rows if r['department_id'] == filter_state['department_id']]

            if filter_state['role'] is not None:
                filtered_rows = [r for r in filtered_rows if r['role_raw'] == filter_state['role']]

            if filter_state['status'] == 'active':
                filtered_rows = [r for r in filtered_rows if r['is_active']]
            elif filter_state['status'] == 'inactive':
                filtered_rows = [r for r in filtered_rows if not r['is_active']]

            total_rows = len(filtered_rows)
            per_page = pagination_state['per_page']
            total_pages = max(1, (total_rows + per_page - 1) // per_page)

            if pagination_state['page'] > total_pages:
                pagination_state['page'] = total_pages
            if pagination_state['page'] < 1:
                pagination_state['page'] = 1

            start_idx = (pagination_state['page'] - 1) * per_page
            end_idx = start_idx + per_page
            page_rows = filtered_rows[start_idx:end_idx]

            if total_rows > 0:
                results_label.text = f'Showing {start_idx + 1}-{min(end_idx, total_rows)} of {total_rows} employees'
            else:
                results_label.text = f'0 employees found'

            with table_container:
                if not filtered_rows:
                    with ui.column().classes('w-full items-center py-8'):
                        ui.icon('person_search', size='3rem').classes('opacity-30 mb-2')
                        ui.label('No employees match your filters').classes('text-gray-500')
                else:
                    table = ui.table(columns=columns, rows=page_rows, row_key='id').classes('w-full')
                    table.on('row-click', lambda e: ui.navigate.to(f'/admin/employees/edit/{e.args[1]["id"]}'))

                    if total_pages > 1:
                        with ui.row().classes('w-full justify-between items-center mt-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label('Show:').classes('text-sm')

                                def on_per_page_change(e):
                                    pagination_state['per_page'] = e.value
                                    pagination_state['page'] = 1
                                    filter_and_render()

                                ui.select(
                                    {10: '10', 25: '25', 50: '50', 100: '100'},
                                    value=per_page,
                                    on_change=on_per_page_change
                                ).props('dense outlined').classes('w-20')
                                ui.label('per page').classes('text-sm')

                            with ui.row().classes('items-center gap-1'):
                                def go_to_page(page_num):
                                    pagination_state['page'] = page_num
                                    filter_and_render()

                                ui.button(icon='chevron_left', on_click=lambda: go_to_page(pagination_state['page'] - 1)).props('flat dense').set_enabled(pagination_state['page'] > 1)
                                ui.label(f'Page {pagination_state["page"]} of {total_pages}').classes('text-sm mx-2')
                                ui.button(icon='chevron_right', on_click=lambda: go_to_page(pagination_state['page'] + 1)).props('flat dense').set_enabled(pagination_state['page'] < total_pages)

        def on_search_change(e):
            filter_state['search'] = search_input.value or ''
            pagination_state['page'] = 1
            filter_and_render()

        def on_dept_change(e):
            filter_state['department_id'] = dept_select.value
            pagination_state['page'] = 1
            filter_and_render()

        def on_role_change(e):
            filter_state['role'] = role_select.value
            pagination_state['page'] = 1
            filter_and_render()

        def on_status_change(e):
            filter_state['status'] = status_select.value
            pagination_state['page'] = 1
            filter_and_render()

        search_input.on('update:model-value', on_search_change)
        dept_select.on('update:model-value', on_dept_change)
        role_select.on('update:model-value', on_role_change)
        status_select.on('update:model-value', on_status_change)

        filter_and_render()

        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-4')


def admin_employees_add_page():
    """Admin page for adding a new employee."""
    apply_dark_mode()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    db = next(get_db())
    try:
        departments = DepartmentService.get_all_departments(db)
        dept_options = {None: 'No Department'}
        dept_options.update({dept.id: dept.name for dept in departments})
    finally:
        db.close()

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        page_header(title='ADD NEW EMPLOYEE', show_back=False)

        # Basic Information Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Basic Information').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4'):
                first_name_input = ui.input('First Name').props('outlined').classes('flex-1')
                last_name_input = ui.input('Last Name').props('outlined').classes('flex-1')

            with ui.row().classes('w-full gap-4 mt-2'):
                username_input = ui.input('Username').props('outlined').classes('flex-1')
                email_input = ui.input('Email', validation={'Invalid email format': lambda v: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)) if v else False}).props('outlined').classes('flex-1')

            # Password fields with visibility toggle
            password_visible = {'value': False}

            with ui.row().classes('w-full gap-4 mt-2'):
                password_input = ui.input('Password', password=True).props('outlined').classes('flex-1')
                confirm_password_input = ui.input('Confirm Password', password=True).props('outlined').classes('flex-1')

            with ui.row().classes('w-full items-center gap-2 -mt-1'):
                def toggle_password_visibility():
                    password_visible['value'] = not password_visible['value']
                    password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                    confirm_password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                    visibility_icon.props(f'name={"visibility_off" if password_visible["value"] else "visibility"}')

                visibility_icon = ui.icon('visibility', size='sm').classes('cursor-pointer opacity-60 hover:opacity-100')
                visibility_icon.on('click', toggle_password_visibility)
                ui.label('Show passwords').classes('text-xs opacity-60')

            ui.label('Minimum 8 characters with at least one letter and one number').classes('text-xs opacity-60 -mt-1')

        # Employment Details Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Employment Details').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4 items-end'):
                with ui.column().classes('flex-1'):
                    ui.label('Hire Date').classes('text-sm font-medium mb-1')
                    with ui.input('Select date').props('outlined readonly').classes('w-full') as hire_date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date(mask='YYYY-MM-DD').bind_value(hire_date_input):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menu.close).props('flat')
                        with hire_date_input.add_slot('append'):
                            ui.icon('event').on('click', menu.open).classes('cursor-pointer')

                with ui.column().classes('flex-1'):
                    department_select = ui.select(dept_options, label='Department', value=None).props('outlined').classes('w-full')

            # Manager display (auto-filled based on department selection)
            manager_display_container = ui.row().classes('w-full mt-2')

            def update_manager_display():
                manager_display_container.clear()
                dept_id = department_select.value
                if dept_id:
                    mgr_db = next(get_db())
                    try:
                        dept = DepartmentService.get_department_by_id(mgr_db, dept_id)
                        if dept and dept.manager_id:
                            manager = UserService(mgr_db).get_user_by_id(dept.manager_id)
                            if manager:
                                with manager_display_container:
                                    with ui.card().classes('w-full p-3 border-l-4 border-teal-500'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('supervisor_account', color='teal').classes('text-lg')
                                            ui.label('Department Manager:').classes('text-sm font-medium opacity-70')
                                            ui.label(f'{manager.first_name} {manager.last_name}').classes('font-semibold')
                        else:
                            with manager_display_container:
                                with ui.card().classes('w-full p-3 border-l-4 border-amber-500'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('warning', color='amber').classes('text-lg')
                                        ui.label('No manager assigned to this department').classes('text-amber-600 font-medium')
                                        ui.label('(Required for employee role)').classes('text-xs opacity-60')
                    finally:
                        mgr_db.close()

            department_select.on('update:model-value', lambda e: update_manager_display())

            with ui.row().classes('w-full gap-4 mt-2'):
                role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Super Admin'}
                role_select = ui.select(role_options, label='Role', value='employee').props('outlined').classes('flex-1')
                is_active_check = ui.checkbox('Active Employee', value=True).classes('self-center')
                is_trusted_check = ui.checkbox('Trusted Employee', value=False).classes('self-center')

                # Add tooltip for trusted employee
                with ui.element('div').classes('self-center'):
                    with ui.tooltip():
                        ui.label('Auto-approves Vacation, Sick, Personal PTO').classes('text-xs')
                    ui.icon('help_outline', size='xs').classes('cursor-pointer opacity-60')

        # Work Location Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Work Location').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

            with ui.row().classes('w-full gap-4'):
                state_options = {None: 'Select State', 'IL': 'Illinois', 'NY': 'New York', 'CT': 'Connecticut', 'FL': 'Florida'}
                location_state_select = ui.select(state_options, label='State', value=None).props('outlined').classes('flex-1')

                city_options = {None: 'Select City'}
                location_city_select = ui.select(city_options, label='City', value=None).props('outlined').classes('flex-1')

                def update_city_options():
                    state = location_state_select.value
                    if state == 'IL':
                        location_city_select.options = {None: 'Select City', 'Chicago': 'Chicago'}
                    elif state == 'NY':
                        location_city_select.options = {None: 'Select City', 'New York': 'New York'}
                    elif state == 'CT':
                        location_city_select.options = {None: 'Select City', 'Rowayton': 'Rowayton'}
                    elif state == 'FL':
                        location_city_select.options = {None: 'Select City', 'Boca': 'Boca'}
                    else:
                        location_city_select.options = {None: 'Select City'}
                    location_city_select.value = None
                    location_city_select.update()

                location_state_select.on('update:model-value', lambda e: update_city_options())

        # Remote Work Schedule Section
        with ui.card().classes('w-full p-6 mb-4'):
            ui.label('Remote Work Schedule').classes('text-lg font-semibold mb-2').style('color: #5a6a72;')
            ui.label('Select the days this employee works remotely').classes('text-sm opacity-60 mb-4')

            with ui.row().classes('w-full gap-6 justify-center'):
                monday_check = ui.checkbox('Mon').classes('text-center')
                tuesday_check = ui.checkbox('Tue').classes('text-center')
                wednesday_check = ui.checkbox('Wed').classes('text-center')
                thursday_check = ui.checkbox('Thu').classes('text-center')
                friday_check = ui.checkbox('Fri').classes('text-center')

        # Action Buttons
        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Cancel', on_click=lambda: ui.run_javascript('history.back()')).props('flat')

            def create_employee():
                # Collect all missing fields
                missing_fields = []

                # Validate required text fields
                if not first_name_input.value or not first_name_input.value.strip():
                    first_name_input.props('error')
                    missing_fields.append('First Name')
                else:
                    first_name_input.props(remove='error')

                if not last_name_input.value or not last_name_input.value.strip():
                    last_name_input.props('error')
                    missing_fields.append('Last Name')
                else:
                    last_name_input.props(remove='error')

                if not username_input.value or not username_input.value.strip():
                    username_input.props('error')
                    missing_fields.append('Username')
                else:
                    username_input.props(remove='error')

                if not email_input.value or not email_input.value.strip():
                    email_input.props('error')
                    missing_fields.append('Email')
                elif not validate_email(email_input):
                    missing_fields.append('Email (invalid format)')
                else:
                    email_input.props(remove='error')

                if not password_input.value:
                    password_input.props('error')
                    missing_fields.append('Password')
                elif len(password_input.value) < 8:
                    password_input.props('error')
                    missing_fields.append('Password (minimum 8 characters)')
                else:
                    password_input.props(remove='error')

                if password_input.value != confirm_password_input.value:
                    confirm_password_input.props('error')
                    missing_fields.append('Confirm Password (passwords must match)')
                else:
                    confirm_password_input.props(remove='error')

                if not hire_date_input.value:
                    hire_date_input.props('error')
                    missing_fields.append('Hire Date')
                else:
                    hire_date_input.props(remove='error')

                # Validate Department
                if not department_select.value:
                    department_select.props('error')
                    missing_fields.append('Department')
                else:
                    department_select.props(remove='error')
                    # Check if department has a manager (for employees)
                    if role_select.value == 'employee':
                        check_db = next(get_db())
                        try:
                            dept = DepartmentService.get_department_by_id(check_db, department_select.value)
                            if not dept or not dept.manager_id:
                                missing_fields.append('Department (must have a manager assigned)')
                        finally:
                            check_db.close()

                # Validate Role
                if not role_select.value:
                    role_select.props('error')
                    missing_fields.append('Role')
                else:
                    role_select.props(remove='error')

                # Validate State
                if not location_state_select.value:
                    location_state_select.props('error')
                    missing_fields.append('State')
                else:
                    location_state_select.props(remove='error')

                # Validate City
                if not location_city_select.value:
                    location_city_select.props('error')
                    missing_fields.append('City')
                else:
                    location_city_select.props(remove='error')

                # Show error dialog if any fields are missing
                if missing_fields:
                    field_list = '\n• '.join(missing_fields)
                    show_error_dialog(
                        'Required Fields Missing',
                        f'Please complete the following required fields:\n\n• {field_list}'
                    )
                    create_btn.props(remove='loading disabled')
                    return

                try:
                    hire_date = datetime.strptime(hire_date_input.value, '%Y-%m-%d').date()
                except ValueError:
                    show_error_dialog('Invalid Date', 'The hire date format is invalid. Please select a valid date.')
                    create_btn.props(remove='loading disabled')
                    return

                remote_schedule = {
                    "monday": monday_check.value,
                    "tuesday": tuesday_check.value,
                    "wednesday": wednesday_check.value,
                    "thursday": thursday_check.value,
                    "friday": friday_check.value
                }

                db = next(get_db())
                try:
                    user_data = UserCreate(
                        username=username_input.value,
                        password=password_input.value,
                        email=email_input.value,
                        first_name=first_name_input.value,
                        last_name=last_name_input.value,
                        department_id=department_select.value,
                        role=role_select.value,
                        hire_date=hire_date,
                        remote_schedule=json.dumps(remote_schedule),
                        is_active=is_active_check.value,
                        location_state=location_state_select.value,
                        location_city=location_city_select.value if location_city_select.value else None
                    )

                    user_service = UserService(db)
                    new_user = user_service.create_user(user_data)

                    # Allocate standard PTO balance for the new employee
                    balance_service = BalanceService(db)
                    balance_service.allocate_standard_balance(new_user.id)

                    # Set trusted status if checkbox was checked (only for employees)
                    current_user = app.storage.user.get('user')
                    if is_trusted_check.value and role_select.value == 'employee':
                        trust_update = UserUpdate(
                            is_trusted=True,
                            trusted_by_id=current_user.get('id'),
                            trusted_at=datetime.now()
                        )
                        user_service.update_user(new_user.id, trust_update)
                    AuditService.log_user_create(
                        db, current_user.get('id'),
                        f"{current_user.get('first_name')} {current_user.get('last_name')}",
                        new_user.id, new_user.username
                    )

                    show_success_dialog('Employee Created', f'Employee "{new_user.first_name} {new_user.last_name}" created successfully', on_close=lambda: ui.navigate.to('/admin/employees'))

                except Exception as e:
                    show_error_dialog('Error', f'Error creating employee: {str(e)}')
                    create_btn.props(remove='loading disabled')
                finally:
                    db.close()

            def on_create_click():
                create_btn.props('loading disabled')
                create_employee()

            create_btn = ui.button('Create Employee', on_click=on_create_click, color='positive', icon='person_add')


def admin_employees_edit_page(user_id: int):
    """Admin page for editing an existing employee."""
    apply_dark_mode()

    current_user = app.storage.user.get('user', {})
    user_role = current_user.get('role')
    current_user_id = current_user.get('id')
    current_department_id = current_user.get('department_id')

    if user_role not in ['admin', 'superadmin', 'manager']:
        ui.navigate.to('/')
        return

    is_manager_editing = user_role == 'manager'

    db = next(get_db())
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        if not user:
            show_error_dialog('Not Found', 'The employee you are looking for was not found.')
            ui.navigate.to('/admin/employees')
            return

        if is_manager_editing:
            if user.department_id != current_department_id:
                show_error_dialog('Access Denied', 'You can only edit employees in your department.')
                ui.navigate.to('/manager/team')
                return
            if user.role in ['manager', 'admin', 'superadmin']:
                show_error_dialog('Access Denied', 'You cannot edit managers or administrators.')
                ui.navigate.to('/manager/team')
                return
            if user.id == current_user_id:
                show_warning_dialog('Use Profile', 'Please use your profile page to edit your own information.')
                ui.navigate.to('/manager/team')
                return

        departments = DepartmentService.get_all_departments(db)
        dept_options = {None: 'No Department'}
        dept_options.update({dept.id: dept.name for dept in departments})

        remote_schedule = {}
        if user.remote_schedule:
            try:
                if isinstance(user.remote_schedule, str):
                    remote_schedule = json.loads(user.remote_schedule)
                elif isinstance(user.remote_schedule, dict):
                    remote_schedule = user.remote_schedule
            except (json.JSONDecodeError, TypeError, ValueError):
                remote_schedule = {}

        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            page_header(title='EDIT EMPLOYEE', show_back=False)

            with ui.row().classes('w-full gap-4 mb-4'):
                with ui.card().classes('flex-1 p-4').style('border-left: 4px solid #5a6a72'):
                    ui.label(f'{user.first_name} {user.last_name}').classes('text-lg font-semibold')
                    ui.label(f'@{user.username} • {user.email}').classes('text-sm opacity-60')

                if is_manager_editing:
                    dept_name = dept_options.get(user.department_id, 'Unknown')
                    with ui.card().classes('p-4').style('border-left: 4px solid #6366f1'):
                        ui.label('Department').classes('text-xs opacity-60 uppercase')
                        ui.label(dept_name).classes('text-lg font-semibold')

            # Basic Information Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Basic Information').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                with ui.row().classes('w-full gap-4'):
                    first_name_input = ui.input('First Name', value=user.first_name).props('outlined').classes('flex-1')
                    last_name_input = ui.input('Last Name', value=user.last_name).props('outlined').classes('flex-1')

                with ui.row().classes('w-full gap-4 mt-2'):
                    username_input = ui.input('Username', value=user.username).props('outlined').classes('flex-1')
                    email_input = ui.input('Email', value=user.email).props('outlined').classes('flex-1')

                # Password fields with visibility toggle (admin only)
                password_input = None
                confirm_password_input = None
                if not is_manager_editing:
                    password_visible = {'value': False}

                    with ui.row().classes('w-full gap-4 mt-2'):
                        password_input = ui.input('New Password', password=True).props('outlined').classes('flex-1')
                        confirm_password_input = ui.input('Confirm Password', password=True).props('outlined').classes('flex-1')

                    with ui.row().classes('w-full items-center gap-2 -mt-1'):
                        def toggle_password_visibility():
                            password_visible['value'] = not password_visible['value']
                            password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                            confirm_password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                            visibility_icon.props(f'name={"visibility_off" if password_visible["value"] else "visibility"}')

                        visibility_icon = ui.icon('visibility', size='sm').classes('cursor-pointer opacity-60 hover:opacity-100')
                        visibility_icon.on('click', toggle_password_visibility)
                        ui.label('Show passwords').classes('text-xs opacity-60')

                    ui.label('Leave blank to keep current password').classes('text-xs opacity-60 -mt-1')

            # Employment Details Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Employment Details').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                with ui.row().classes('w-full gap-4 items-end'):
                    with ui.column().classes('flex-1'):
                        ui.label('Hire Date').classes('text-sm font-medium mb-1')
                        initial_date = user.hire_date.strftime('%Y-%m-%d') if user.hire_date else ''
                        with ui.input('Select date', value=initial_date).props('outlined readonly').classes('w-full') as hire_date_input:
                            with ui.menu().props('no-parent-event') as menu:
                                with ui.date(mask='YYYY-MM-DD', value=initial_date).bind_value(hire_date_input):
                                    with ui.row().classes('justify-end'):
                                        ui.button('Close', on_click=menu.close).props('flat')
                            with hire_date_input.add_slot('append'):
                                ui.icon('event').on('click', menu.open).classes('cursor-pointer')

                    department_select = None
                    if not is_manager_editing:
                        with ui.column().classes('flex-1'):
                            department_select = ui.select(dept_options, label='Department', value=user.department_id).props('outlined').classes('w-full')

                role_select = None
                is_trusted_check = None
                with ui.row().classes('w-full gap-4 mt-2'):
                    if not is_manager_editing:
                        role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Super Admin'}
                        role_select = ui.select(role_options, label='Role', value=user.role).props('outlined').classes('flex-1')

                    is_active_check = ui.checkbox('Active Employee', value=user.is_active).classes('self-center')

                    # Trusted Employee checkbox - only for admins editing employees
                    if not is_manager_editing and user.role == 'employee':
                        is_trusted_check = ui.checkbox('Trusted Employee', value=user.is_trusted).classes('self-center')

                        # Add tooltip for trusted employee
                        with ui.element('div').classes('self-center'):
                            with ui.tooltip():
                                ui.label('Auto-approves Vacation, Sick, Personal PTO').classes('text-xs')
                            ui.icon('help_outline', size='xs').classes('cursor-pointer opacity-60')

                    # Delete button - only for admins (not managers editing their own employees)
                    if not is_manager_editing:
                        def confirm_delete_employee():
                            with ui.dialog() as dialog, ui.card().classes('p-0 max-w-md'):
                                with ui.row().classes('w-full p-4 text-white items-center').style('background-color: #ef4444'):
                                    ui.icon('warning', size='md').classes('mr-2')
                                    ui.label('Delete Employee').classes('text-lg font-bold')
                                with ui.column().classes('p-4 gap-3'):
                                    ui.label(f'Are you sure you want to delete {user.first_name} {user.last_name}?').classes('text-base')
                                    ui.label('This will permanently remove the employee and ALL their PTO records.').classes('text-sm opacity-70')
                                    ui.label('This action cannot be undone!').classes('text-sm font-bold text-red-600')
                                    with ui.row().classes('w-full justify-end gap-3 mt-2'):
                                        ui.button('Cancel', on_click=dialog.close).props('flat')

                                        async def do_delete_employee():
                                            db = next(get_db())
                                            try:
                                                user_service = UserService(db)
                                                if user_service.delete_user(user_id):
                                                    current_user = app.storage.user.get('user')
                                                    AuditService.log(
                                                        db, action='user_delete',
                                                        user_id=current_user.get('id'),
                                                        username=f"{current_user.get('first_name')} {current_user.get('last_name')}",
                                                        entity_type='user', entity_id=user_id,
                                                        details={'deleted_user': user.username}
                                                    )
                                                    dialog.close()
                                                    ui.navigate.to('/admin/employees')
                                                else:
                                                    show_error_dialog('Deletion Failed', 'There was an error deleting the employee.')
                                            finally:
                                                db.close()

                                        ui.button('Delete Permanently', on_click=do_delete_employee).props('color=red')
                            dialog.open()

                        ui.button('Delete', on_click=confirm_delete_employee, icon='delete').props('color=red outline')

            # Work Location Section - only for admins
            location_state_select = None
            location_city_select = None
            if not is_manager_editing:
                with ui.card().classes('w-full p-6 mb-4'):
                    ui.label('Work Location').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')

                    def get_city_options_for_state(state):
                        if state == 'IL':
                            return {None: 'Select City', 'Chicago': 'Chicago'}
                        elif state == 'NY':
                            return {None: 'Select City', 'New York': 'New York'}
                        elif state == 'CT':
                            return {None: 'Select City', 'Rowayton': 'Rowayton'}
                        elif state == 'FL':
                            return {None: 'Select City', 'Boca': 'Boca'}
                        else:
                            return {None: 'Select City'}

                    with ui.row().classes('w-full gap-4'):
                        state_options = {None: 'Select State', 'IL': 'Illinois', 'NY': 'New York', 'CT': 'Connecticut', 'FL': 'Florida'}
                        location_state_select = ui.select(state_options, label='State', value=user.location_state).props('outlined').classes('flex-1')

                        initial_city_options = get_city_options_for_state(user.location_state)
                        location_city_select = ui.select(initial_city_options, label='City', value=user.location_city).props('outlined').classes('flex-1')

                        def update_city_options_edit():
                            state = location_state_select.value
                            location_city_select.options = get_city_options_for_state(state)
                            location_city_select.value = None
                            location_city_select.update()

                        location_state_select.on('update:model-value', lambda e: update_city_options_edit())

            # Remote Work Schedule Section
            with ui.card().classes('w-full p-6 mb-4'):
                ui.label('Remote Work Schedule').classes('text-lg font-semibold mb-2').style('color: #5a6a72;')
                ui.label('Select the days this employee works remotely').classes('text-sm opacity-60 mb-4')

                with ui.row().classes('w-full gap-6 justify-center'):
                    monday_check = ui.checkbox('Mon', value=remote_schedule.get('monday', False)).classes('text-center')
                    tuesday_check = ui.checkbox('Tue', value=remote_schedule.get('tuesday', False)).classes('text-center')
                    wednesday_check = ui.checkbox('Wed', value=remote_schedule.get('wednesday', False)).classes('text-center')
                    thursday_check = ui.checkbox('Thu', value=remote_schedule.get('thursday', False)).classes('text-center')
                    friday_check = ui.checkbox('Fri', value=remote_schedule.get('friday', False)).classes('text-center')

            # Action Buttons
            with ui.row().classes('w-full justify-between mt-4'):
                ui.button('Cancel', on_click=lambda: ui.run_javascript('history.back()')).props('flat')

                def save_changes():
                    valid = True
                    if not validate_required(first_name_input, 'First Name'):
                        valid = False
                    if not validate_required(last_name_input, 'Last Name'):
                        valid = False
                    if not validate_required(username_input, 'Username'):
                        valid = False
                    if not validate_required(email_input, 'Email'):
                        valid = False
                    elif not validate_email(email_input):
                        valid = False
                    if password_input and password_input.value and not validate_min_length(password_input, 8, 'Password'):
                        valid = False
                    if password_input and password_input.value and confirm_password_input:
                        if password_input.value != confirm_password_input.value:
                            confirm_password_input.props('error')
                            show_error_dialog('Password Mismatch', 'The passwords you entered do not match. Please try again.')
                            valid = False
                    if not validate_required(hire_date_input, 'Hire Date'):
                        valid = False

                    if not valid:
                        show_warning_dialog('Form Incomplete', 'Please fix the highlighted errors before continuing.')
                        save_btn.props(remove='loading disabled')
                        return

                    try:
                        hire_date = datetime.strptime(hire_date_input.value, '%Y-%m-%d').date()
                    except ValueError:
                        show_error_dialog('Invalid Date', 'The hire date format is invalid. Please select a valid date.')
                        save_btn.props(remove='loading disabled')
                        return

                    new_remote_schedule = {
                        "monday": monday_check.value,
                        "tuesday": tuesday_check.value,
                        "wednesday": wednesday_check.value,
                        "thursday": thursday_check.value,
                        "friday": friday_check.value
                    }

                    db = next(get_db())
                    try:
                        update_data = {
                            'username': username_input.value,
                            'email': email_input.value,
                            'first_name': first_name_input.value,
                            'last_name': last_name_input.value,
                            'hire_date': hire_date,
                            'remote_schedule': json.dumps(new_remote_schedule),
                            'is_active': is_active_check.value
                        }

                        if not is_manager_editing:
                            update_data['department_id'] = department_select.value
                            update_data['role'] = role_select.value
                            update_data['location_state'] = location_state_select.value
                            update_data['location_city'] = location_city_select.value if location_city_select.value else None

                            # Handle trusted employee status change
                            if is_trusted_check is not None:
                                new_trust_status = is_trusted_check.value
                                if new_trust_status != user.is_trusted:
                                    update_data['is_trusted'] = new_trust_status
                                    if new_trust_status:
                                        # Granting trust - record who and when
                                        update_data['trusted_by_id'] = current_user_id
                                        update_data['trusted_at'] = datetime.now()
                                    else:
                                        # Revoking trust - clear the fields
                                        update_data['trusted_by_id'] = None
                                        update_data['trusted_at'] = None

                        if password_input and password_input.value:
                            update_data['password'] = password_input.value

                        user_update = UserUpdate(**update_data)
                        user_service = UserService(db)
                        updated_user = user_service.update_user(user_id, user_update)

                        if updated_user:
                            logged_user = app.storage.user.get('user')
                            AuditService.log_user_update(
                                db, logged_user.get('id'),
                                f"{logged_user.get('first_name')} {logged_user.get('last_name')}",
                                user_id, {'fields_updated': list(update_data.keys())}
                            )
                            nav_url = '/manager/team' if is_manager_editing else '/admin/employees'
                            show_success_dialog('Employee Updated', 'Employee updated successfully', on_close=lambda: ui.navigate.to(nav_url))
                        else:
                            show_error_dialog('Update Failed', 'There was an error updating the employee. Please try again.')
                            save_btn.props(remove='loading disabled')

                    except Exception as e:
                        show_error_dialog('Error', f'Error updating employee: {str(e)}')
                        save_btn.props(remove='loading disabled')
                    finally:
                        db.close()

                def on_save_click():
                    save_btn.props('loading disabled')
                    save_changes()

                save_btn = ui.button('Save Changes', on_click=on_save_click, color='positive', icon='save')

            ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6')

    finally:
        db.close()
