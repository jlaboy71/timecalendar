from nicegui import ui, app
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.database import get_db
from nicegui_app.pages.login import login_page
from nicegui_app.pages.dashboard import dashboard_page
from nicegui_app.pages.request_form import request_form_page

# Set up basic app configuration
app.title = "TJM Time Calendar"

@ui.page('/')
def home():
    """Home page with login interface."""
    login_page()

@ui.page('/dashboard')
def dashboard():
    """Dashboard page for logged-in users."""
    dashboard_page()

@ui.page('/submit-request')
def submit_request():
    """PTO Request submission page."""
    request_form_page()

@ui.page('/calendar')
def calendar():
    """Calendar view page."""
    ui.label('Calendar View - Coming in Session 5').classes('text-2xl')
    ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))

@ui.page('/requests')
def requests():
    """User's PTO request history page."""
    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return
    
    user = app.storage.general.get('user')
    
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('My PTO Request History').classes('text-3xl font-bold mb-6')
        
        db = next(get_db())
        try:
            from src.services.pto_service import PTOService
            user_requests = PTOService.get_user_requests(db, user['id'])
            
            if not user_requests:
                ui.label('No requests yet').classes('text-xl text-gray-500 text-center mt-8')
            else:
                columns = [
                    {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left'},
                    {'name': 'start_date', 'label': 'Start Date', 'field': 'start_date', 'align': 'left'},
                    {'name': 'end_date', 'label': 'End Date', 'field': 'end_date', 'align': 'left'},
                    {'name': 'days', 'label': 'Days', 'field': 'days', 'align': 'center'},
                    {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'left'},
                    {'name': 'submitted', 'label': 'Submitted', 'field': 'submitted', 'align': 'left'}
                ]
                
                rows = []
                for req in user_requests:
                    status_display = req.status.title()
                    if req.status == 'denied' and req.denial_reason:
                        status_display += f' ({req.denial_reason})'
                    
                    rows.append({
                        'id': req.id,
                        'type': req.pto_type.title(),
                        'start_date': req.start_date.strftime('%Y-%m-%d'),
                        'end_date': req.end_date.strftime('%Y-%m-%d'),
                        'days': req.total_days,
                        'status': status_display,
                        'submitted': req.submitted_at.strftime('%Y-%m-%d %H:%M')
                    })
                
                ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
        
        finally:
            db.close()
        
        ui.button('Back to Admin Panel', on_click=lambda: ui.navigate.to('/admin')).classes('mt-4')

@ui.page('/manager')
def manager():
    """Manager dashboard page for viewing pending PTO requests."""
    # Check if user is logged in and has manager role
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'manager':
        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            ui.label('Access denied. Manager role required.').classes('text-xl text-red-500')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
        return

    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('Manager Dashboard - Pending PTO Requests').classes('text-3xl font-bold mb-6')

        # Get pending requests
        db = next(get_db())
        try:
            from src.services.pto_service import PTOService
            pending_requests = PTOService.get_pending_requests_with_employee_info(db)

            if not pending_requests:
                ui.label('No pending requests').classes('text-xl text-gray-500 text-center mt-8')
            else:
                # Create table with pending requests
                columns = [
                    {'name': 'employee_name', 'label': 'Employee', 'field': 'employee_name', 'align': 'left'},
                    {'name': 'pto_type', 'label': 'Type', 'field': 'pto_type', 'align': 'left'},
                    {'name': 'start_date', 'label': 'Start Date', 'field': 'start_date', 'align': 'left'},
                    {'name': 'end_date', 'label': 'End Date', 'field': 'end_date', 'align': 'left'},
                    {'name': 'total_days', 'label': 'Days', 'field': 'total_days', 'align': 'center'},
                    {'name': 'submitted_at', 'label': 'Submitted', 'field': 'submitted_at', 'align': 'left'}
                ]

                # Format dates for display
                formatted_requests = []
                for req in pending_requests:
                    formatted_requests.append({
                        'request_id': req['request_id'],
                        'employee_name': req['employee_name'],
                        'pto_type': req['pto_type'].title(),
                        'start_date': req['start_date'].strftime('%Y-%m-%d'),
                        'end_date': req['end_date'].strftime('%Y-%m-%d'),
                        'total_days': req['total_days'],
                        'submitted_at': req['submitted_at'].strftime('%Y-%m-%d %H:%M')
                    })

                table = ui.table(columns=columns, rows=formatted_requests, row_key='request_id')
                table.classes('w-full')

                # Make rows clickable
                def on_row_click(e):
                    request_id = e.args[1]['request_id']
                    ui.navigate.to(f'/manager/request/{request_id}')

                table.on('rowClick', on_row_click)

        finally:
            db.close()

        ui.button('Back to Admin Panel', on_click=lambda: ui.navigate.to('/admin')).classes('mt-4')

@ui.page('/manager/request/{request_id}')
def manager_request_detail(request_id: int):
    """Request detail page for approval/denial"""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'manager':
        ui.label('Access denied').classes('text-red-500')
        return
    
    db = next(get_db())
    try:
        from src.services.pto_service import PTOService
        detail = PTOService.get_request_detail(db, request_id)
        
        if not detail:
            ui.label('Request not found').classes('text-red-500')
            return
        
        request = detail['request']
        balance = detail['balance']
        
        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            ui.label('PTO Request Detail').classes('text-3xl font-bold mb-6')
            
            # Employee Info Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Employee Information').classes('text-xl font-bold mb-2')
                ui.label(f"Name: {detail['employee_name']}")
                ui.label(f"Email: {detail['employee_email']}")
            
            # Request Details Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Request Details').classes('text-xl font-bold mb-2')
                ui.label(f"Type: {request.pto_type.title()}")
                ui.label(f"Start Date: {request.start_date.strftime('%Y-%m-%d')}")
                ui.label(f"End Date: {request.end_date.strftime('%Y-%m-%d')}")
                ui.label(f"Total Days: {request.total_days}")
                ui.label(f"Status: {request.status.title()}")
                ui.label(f"Submitted: {request.submitted_at.strftime('%Y-%m-%d %H:%M')}")
                if request.notes:
                    ui.label(f"Notes: {request.notes}")
            
            # Current Balance Card
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label('Current PTO Balance').classes('text-xl font-bold mb-2')
                ui.label(f"Vacation: {balance.vacation_total - balance.vacation_used:.1f} available")
                ui.label(f"Sick: {balance.sick_total - balance.sick_used:.1f} available")
                ui.label(f"Personal: {balance.personal_total - balance.personal_used:.1f} available")
            
            # Approval Actions
            if request.status == 'pending':
                with ui.row().classes('gap-4 mt-6'):
                    def approve():
                        db = next(get_db())
                        try:
                            user_id = app.storage.general.get('user').get('id')
                            if PTOService.approve_request(db, request_id, user_id):
                                ui.notify('Request approved!', type='positive')
                                ui.navigate.to('/manager')
                            else:
                                ui.notify('Error approving request', type='negative')
                        finally:
                            db.close()
                    
                    def deny():
                        db = next(get_db())
                        try:
                            reason = denial_input.value or 'No reason provided'
                            user_id = app.storage.general.get('user').get('id')
                            if PTOService.deny_request(db, request_id, user_id, reason):
                                ui.notify('Request denied', type='warning')
                                ui.navigate.to('/manager')
                            else:
                                ui.notify('Error denying request', type='negative')
                        finally:
                            db.close()
                    
                    ui.button('Approve', on_click=approve, color='positive')
                    denial_input = ui.input('Denial Reason (optional)').classes('flex-1')
                    ui.button('Deny', on_click=deny, color='negative')
            
            ui.button('Back to Manager Dashboard', on_click=lambda: ui.navigate.to('/manager')).classes('mt-4')
    
    finally:
        db.close()

@ui.page('/admin')
def admin_panel():
    """Admin panel landing page with navigation to admin functions."""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'admin':
        ui.navigate.to('/')
        return
    
    with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
        ui.label('Admin Panel').classes('text-3xl font-bold mb-6')
        
        # Navigation cards
        with ui.row().classes('w-full gap-6 justify-center'):
            # Manage Departments card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('business', size='3rem').classes('text-primary')
                    ui.label('Manage Departments').classes('text-xl font-semibold')
                    ui.label('Create and manage organizational departments').classes('text-gray-600 text-center')
                    ui.button('Go to Departments', on_click=lambda: ui.navigate.to('/admin/departments'), color='primary')
            
            # Manage Employees card
            with ui.card().classes('p-6 cursor-pointer hover:shadow-lg transition-shadow'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('people', size='3rem').classes('text-primary')
                    ui.label('Manage Employees').classes('text-xl font-semibold')
                    ui.label('Add, edit, and manage employee accounts').classes('text-gray-600 text-center')
                    ui.button('Go to Employees', on_click=lambda: ui.navigate.to('/admin/employees'), color='primary')
            
            # Reports card (disabled)
            with ui.card().classes('p-6 opacity-50'):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('assessment', size='3rem').classes('text-gray-400')
                    ui.label('Reports').classes('text-xl font-semibold text-gray-400')
                    ui.label('View PTO usage and analytics').classes('text-gray-400 text-center')
                    ui.label('Coming Soon').classes('text-gray-400 font-semibold')
        
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-8')

@ui.page('/admin/departments')
def admin_departments():
    """Admin page for managing departments."""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'admin':
        ui.navigate.to('/')
        return
    
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('Department Management').classes('text-3xl font-bold mb-6')
        
        with ui.card().classes('w-full mb-6 p-4'):
            ui.label('Create New Department').classes('text-xl font-semibold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                name_input = ui.input('Department Name').classes('flex-1')
                code_input = ui.input('Department Code').classes('flex-1')
            
            with ui.row().classes('w-full gap-4 mt-4'):
                db = next(get_db())
                try:
                    from src.services.user_service import UserService
                    managers = UserService.get_users_by_role(db, 'manager')
                    manager_options = {0: 'No Manager'}
                    manager_options.update({m.id: f'{m.first_name} {m.last_name}' for m in managers})
                finally:
                    db.close()
                
                manager_select = ui.select(manager_options, label='Manager', value=0).classes('flex-1')
                
                def create_dept():
                    if not name_input.value or not code_input.value:
                        ui.notify('Name and code are required', type='negative')
                        return
                    
                    db = next(get_db())
                    try:
                        from src.services.department_service import DepartmentService
                        mgr_id = None if manager_select.value == 0 else manager_select.value
                        DepartmentService.create_department(db, name_input.value, code_input.value, mgr_id)
                        ui.notify(f'Department "{name_input.value}" created successfully', type='positive')
                        ui.navigate.to('/admin/departments')
                    except ValueError as e:
                        ui.notify(str(e), type='negative')
                    finally:
                        db.close()
                
                ui.button('Create Department', on_click=create_dept, color='primary')
        
        db = next(get_db())
        try:
            from src.services.department_service import DepartmentService
            departments = DepartmentService.get_all_departments(db)
            
            if not departments:
                ui.label('No departments yet').classes('text-xl text-gray-500 text-center mt-8')
            else:
                columns = [
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
                    {'name': 'code', 'label': 'Code', 'field': 'code', 'align': 'left'},
                    {'name': 'manager', 'label': 'Manager', 'field': 'manager', 'align': 'left'},
                    {'name': 'active', 'label': 'Active', 'field': 'active', 'align': 'center'},
                ]
                
                rows = []
                for dept in departments:
                    manager_name = 'No Manager'
                    if dept.manager_id:
                        from src.services.user_service import UserService
                        manager = UserService(db).get_user_by_id(dept.manager_id)
                        if manager:
                            manager_name = f'{manager.first_name} {manager.last_name}'
                    
                    rows.append({
                        'id': dept.id,
                        'name': dept.name,
                        'code': dept.code,
                        'manager': manager_name,
                        'active': 'Yes' if dept.is_active else 'No'
                    })
                
                ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
        
        finally:
            db.close()
        
        ui.button('Back to Admin Panel', on_click=lambda: ui.navigate.to('/admin')).classes('mt-4')

@ui.page('/admin/employees')
def admin_employees():
    """Admin page for managing employees."""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'admin':
        ui.navigate.to('/')
        return
    
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 p-6'):
        ui.label('Employee Management').classes('text-3xl font-bold mb-6')
        
        # Add New Employee button
        ui.button('Add New Employee', on_click=lambda: ui.navigate.to('/admin/employees/add'), color='primary').classes('mb-6')
        
        db = next(get_db())
        try:
            from src.services.user_service import UserService
            from src.services.department_service import DepartmentService
            
            # Get all users and departments
            users = UserService(db).get_all_users()
            departments = DepartmentService.get_all_departments(db)
            
            # Create department lookup
            dept_lookup = {dept.id: dept.name for dept in departments}
            
            if not users:
                ui.label('No employees yet').classes('text-xl text-gray-500 text-center mt-8')
            else:
                def confirm_deactivate(user_id: int, user_name: str):
                    with ui.dialog() as dialog, ui.card():
                        ui.label(f'Are you sure you want to deactivate {user_name}?').classes('text-lg mb-4')
                        ui.label('This will set the employee as inactive but preserve their records.').classes('text-sm text-gray-500 mb-4')
                        with ui.row().classes('gap-4'):
                            async def do_deactivate():
                                from src.services.user_service import UserService
                                db = next(get_db())
                                try:
                                    user_service = UserService(db)
                                    if user_service.deactivate_user(user_id):
                                        ui.notify(f'Employee "{user_name}" deactivated successfully', type='positive')
                                        dialog.close()
                                        await ui.run_javascript('window.location.reload()')
                                    else:
                                        ui.notify('Error deactivating employee', type='negative')
                                finally:
                                    db.close()

                            ui.button('Yes', on_click=do_deactivate, color='orange')
                            ui.button('No', on_click=dialog.close, color='secondary')
                    dialog.open()

                def confirm_delete(user_id: int, user_name: str):
                    with ui.dialog() as dialog, ui.card():
                        ui.label(f'PERMANENTLY DELETE {user_name}?').classes('text-lg font-bold text-red-600 mb-2')
                        ui.label('This will permanently remove the employee and ALL their PTO records.').classes('text-sm text-red-500 mb-2')
                        ui.label('This action cannot be undone!').classes('text-sm font-bold text-red-600 mb-4')
                        with ui.row().classes('gap-4'):
                            async def do_delete():
                                from src.services.user_service import UserService
                                db = next(get_db())
                                try:
                                    user_service = UserService(db)
                                    if user_service.delete_user(user_id):
                                        ui.notify(f'Employee "{user_name}" permanently deleted', type='positive')
                                        dialog.close()
                                        await ui.run_javascript('window.location.reload()')
                                    else:
                                        ui.notify('Error deleting employee', type='negative')
                                finally:
                                    db.close()

                            ui.button('Yes, Delete Permanently', on_click=do_delete, color='red')
                            ui.button('Cancel', on_click=dialog.close, color='secondary')
                    dialog.open()
                
                with ui.card().classes('w-full'):
                    # Header row
                    with ui.row().classes('w-full bg-gray-100 p-3 font-bold'):
                        ui.label('Name').classes('w-1/6')
                        ui.label('Email').classes('w-1/5')
                        ui.label('Department').classes('w-1/6')
                        ui.label('Role').classes('w-1/12')
                        ui.label('Hire Date').classes('w-1/8')
                        ui.label('Active').classes('w-1/12')
                        ui.label('Actions').classes('w-1/6')
                    
                    # Data rows
                    for user in users:
                        department_name = 'No Department'
                        if user.department_id:
                            department_name = dept_lookup.get(user.department_id, 'Unknown Department')
                        
                        with ui.row().classes('w-full p-3 border-b items-center'):
                            ui.label(f'{user.first_name} {user.last_name}').classes('w-1/6')
                            ui.label(user.email).classes('w-1/5')
                            ui.label(department_name).classes('w-1/6')
                            ui.label(user.role.title()).classes('w-1/12')
                            ui.label(user.hire_date.strftime('%Y-%m-%d') if user.hire_date else 'Not Set').classes('w-1/8')
                            ui.label('Yes' if user.is_active else 'No').classes('w-1/12')
                            with ui.row().classes('w-1/6 gap-1'):
                                user_full_name = f'{user.first_name} {user.last_name}'
                                ui.button('Edit', on_click=lambda u=user: ui.navigate.to(f'/admin/employees/edit/{u.id}'), color='primary').props('size=sm dense')
                                if user.is_active:
                                    ui.button('Deactivate', on_click=lambda uid=user.id, uname=user_full_name: confirm_deactivate(uid, uname), color='orange').props('size=sm dense')
                                ui.button('Delete', on_click=lambda uid=user.id, uname=user_full_name: confirm_delete(uid, uname), color='red').props('size=sm dense')
        
        finally:
            db.close()
        
        ui.button('Back to Admin Panel', on_click=lambda: ui.navigate.to('/admin')).classes('mt-4')

@ui.page('/admin/employees/add')
def admin_employees_add():
    """Admin page for adding a new employee."""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'admin':
        ui.navigate.to('/')
        return
    
    with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
        ui.label('Add New Employee').classes('text-3xl font-bold mb-6')
        
        with ui.card().classes('w-full p-6'):
            ui.label('Employee Information').classes('text-xl font-semibold mb-4')
            
            # Row 1: First Name | Last Name
            with ui.row().classes('w-full gap-4'):
                first_name_input = ui.input('First Name').classes('flex-1')
                last_name_input = ui.input('Last Name').classes('flex-1')
            
            # Row 2: Username | Email
            with ui.row().classes('w-full gap-4'):
                username_input = ui.input('Username').classes('flex-1')
                email_input = ui.input('Email', validation={'Invalid email format': lambda v: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)) if v else False}).classes('flex-1')
            
            # Row 3: Password (with note below)
            password_input = ui.input('Password', password=True).classes('w-full')
            ui.label('Minimum 8 characters required').classes('text-sm text-gray-500 -mt-2 mb-2')
            
            # Row 4: Hire Date
            with ui.row().classes('w-full gap-2'):
                ui.label('Hire Date').classes('font-semibold mb-2')
            with ui.row().classes('w-full gap-2'):
                hire_month_select = ui.select({1:'January', 2:'February', 3:'March', 4:'April', 5:'May', 6:'June', 7:'July', 8:'August', 9:'September', 10:'October', 11:'November', 12:'December'}, label='Month', value=None).classes('flex-1')
                hire_day_select = ui.select({i:str(i) for i in range(1, 32)}, label='Day', value=None).classes('flex-1')
                hire_year_select = ui.select({i:str(i) for i in range(1980, 2051)}, label='Year', value=None).classes('flex-1')
            
            # Row 5: Department | Role
            with ui.row().classes('w-full gap-4'):
                # Get departments for dropdown
                db = next(get_db())
                try:
                    from src.services.department_service import DepartmentService
                    departments = DepartmentService.get_all_departments(db)
                    dept_options = {None: 'No Department'}
                    dept_options.update({dept.id: dept.name for dept in departments})
                finally:
                    db.close()
                
                department_select = ui.select(dept_options, label='Department', value=None).classes('flex-1')
                
                role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin'}
                role_select = ui.select(role_options, label='Role', value='employee').classes('flex-1')
            
            # Remote Work Days Section
            ui.label('Remote Work Days').classes('text-lg font-semibold mt-6 mb-2')
            with ui.row().classes('gap-4'):
                monday_check = ui.checkbox('Monday')
                tuesday_check = ui.checkbox('Tuesday')
                wednesday_check = ui.checkbox('Wednesday')
                thursday_check = ui.checkbox('Thursday')
                friday_check = ui.checkbox('Friday')
            
            is_active_check = ui.checkbox('Is Active', value=True).classes('mt-4')
            
            # Action buttons
            with ui.row().classes('gap-4 mt-6'):
                def create_employee():
                    # Validate required fields
                    if not username_input.value:
                        ui.notify('Username is required', type='negative')
                        return
                    if not password_input.value:
                        ui.notify('Password is required', type='negative')
                        return
                    if len(password_input.value) < 8:
                        ui.notify('Password must be at least 8 characters', type='negative')
                        return
                    if not email_input.value:
                        ui.notify('Email is required', type='negative')
                        return
                    
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, email_input.value):
                        ui.notify('Please enter a valid email address (e.g., user@domain.com)', type='negative')
                        return
                    if not first_name_input.value:
                        ui.notify('First Name is required', type='negative')
                        return
                    if not last_name_input.value:
                        ui.notify('Last Name is required', type='negative')
                        return
                    if not hire_month_select.value or not hire_day_select.value or not hire_year_select.value:
                        ui.notify('All hire date fields (Month, Day, Year) are required', type='negative')
                        return
                    
                    # Validate and create hire date
                    from datetime import datetime
                    
                    try:
                        hire_date_str = f"{hire_year_select.value}-{hire_month_select.value:02d}-{hire_day_select.value:02d}"
                        hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        ui.notify('Invalid hire date - please check the date is valid', type='negative')
                        return
                    
                    anniversary_date = None
                    
                    # Build remote schedule JSON
                    import json
                    remote_schedule = {
                        "monday": monday_check.value,
                        "tuesday": tuesday_check.value,
                        "wednesday": wednesday_check.value,
                        "thursday": thursday_check.value,
                        "friday": friday_check.value
                    }
                    
                    db = next(get_db())
                    try:
                        from src.services.user_service import UserService
                        from src.schemas.user_schemas import UserCreate
                        
                        user_data = UserCreate(
                            username=username_input.value,
                            password=password_input.value,
                            email=email_input.value,
                            first_name=first_name_input.value,
                            last_name=last_name_input.value,
                            department_id=department_select.value,
                            role=role_select.value,
                            hire_date=hire_date,
                            anniversary_date=anniversary_date,
                            remote_schedule=json.dumps(remote_schedule),
                            is_active=is_active_check.value
                        )
                        
                        user_service = UserService(db)
                        new_user = user_service.create_user(user_data)
                        
                        ui.notify(f'Employee "{new_user.first_name} {new_user.last_name}" created successfully', type='positive')
                        ui.navigate.to('/admin/employees')
                        
                    except Exception as e:
                        ui.notify(f'Error creating employee: {str(e)}', type='negative')
                    finally:
                        db.close()
                
                ui.button('Create Employee', on_click=create_employee, color='positive')
                ui.button('Cancel', on_click=lambda: ui.navigate.to('/admin/employees'), color='secondary')

@ui.page('/admin/employees/edit/{user_id}')
def admin_employees_edit(user_id: int):
    """Admin page for editing an existing employee."""
    if not app.storage.general.get('user') or app.storage.general.get('user').get('role') != 'admin':
        ui.navigate.to('/')
        return
    
    # Fetch the user by ID
    db = next(get_db())
    try:
        from src.services.user_service import UserService
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            ui.notify('Employee not found', type='negative')
            ui.navigate.to('/admin/employees')
            return
        
        # Parse remote schedule if it exists
        import json
        remote_schedule = {}
        if user.remote_schedule:
            try:
                remote_schedule = json.loads(user.remote_schedule)
            except:
                remote_schedule = {}
        
        with ui.column().classes('w-full max-w-4xl mx-auto mt-8 p-6'):
            ui.label('Edit Employee').classes('text-3xl font-bold mb-6')
            
            with ui.card().classes('w-full p-6'):
                ui.label('Employee Information').classes('text-xl font-semibold mb-4')
                
                # Row 1: First Name | Last Name
                with ui.row().classes('w-full gap-4'):
                    first_name_input = ui.input('First Name', value=user.first_name).classes('flex-1')
                    last_name_input = ui.input('Last Name', value=user.last_name).classes('flex-1')
                
                # Row 2: Username | Email
                with ui.row().classes('w-full gap-4'):
                    username_input = ui.input('Username', value=user.username).classes('flex-1')
                    email_input = ui.input('Email', value=user.email, validation={'Invalid email format': lambda v: bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v)) if v else False}).classes('flex-1')
                
                # Row 3: Password (with note below)
                password_input = ui.input('Password', password=True).classes('w-full')
                ui.label('Leave blank to keep current password. Minimum 8 characters if changing.').classes('text-sm text-gray-500 -mt-2 mb-2')
                
                # Row 4: Hire Date
                with ui.row().classes('w-full gap-2'):
                    ui.label('Hire Date').classes('font-semibold mb-2')
                with ui.row().classes('w-full gap-2'):
                    hire_month_select = ui.select({1:'January', 2:'February', 3:'March', 4:'April', 5:'May', 6:'June', 7:'July', 8:'August', 9:'September', 10:'October', 11:'November', 12:'December'}, label='Month', value=user.hire_date.month if user.hire_date else None).classes('flex-1')
                    hire_day_select = ui.select({i:str(i) for i in range(1, 32)}, label='Day', value=user.hire_date.day if user.hire_date else None).classes('flex-1')
                    hire_year_select = ui.select({i:str(i) for i in range(1980, 2051)}, label='Year', value=user.hire_date.year if user.hire_date else None).classes('flex-1')
                
                # Row 5: Department | Role
                with ui.row().classes('w-full gap-4'):
                    # Get departments for dropdown
                    from src.services.department_service import DepartmentService
                    departments = DepartmentService.get_all_departments(db)
                    dept_options = {None: 'No Department'}
                    dept_options.update({dept.id: dept.name for dept in departments})
                    
                    department_select = ui.select(dept_options, label='Department', value=user.department_id).classes('flex-1')
                    
                    role_options = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin'}
                    role_select = ui.select(role_options, label='Role', value=user.role).classes('flex-1')
                
                # Remote Work Days Section
                ui.label('Remote Work Days').classes('text-lg font-semibold mt-6 mb-2')
                with ui.row().classes('gap-4'):
                    monday_check = ui.checkbox('Monday', value=remote_schedule.get('monday', False))
                    tuesday_check = ui.checkbox('Tuesday', value=remote_schedule.get('tuesday', False))
                    wednesday_check = ui.checkbox('Wednesday', value=remote_schedule.get('wednesday', False))
                    thursday_check = ui.checkbox('Thursday', value=remote_schedule.get('thursday', False))
                    friday_check = ui.checkbox('Friday', value=remote_schedule.get('friday', False))
                
                is_active_check = ui.checkbox('Is Active', value=user.is_active).classes('mt-4')
                
                # Action buttons
                with ui.row().classes('gap-4 mt-6'):
                    def save_changes():
                        # Validate required fields
                        if not username_input.value:
                            ui.notify('Username is required', type='negative')
                            return
                        if password_input.value and len(password_input.value) < 8:
                            ui.notify('Password must be at least 8 characters if changing', type='negative')
                            return
                        if not email_input.value:
                            ui.notify('Email is required', type='negative')
                            return
                        
                        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                        if not re.match(email_pattern, email_input.value):
                            ui.notify('Please enter a valid email address (e.g., user@domain.com)', type='negative')
                            return
                        if not first_name_input.value:
                            ui.notify('First Name is required', type='negative')
                            return
                        if not last_name_input.value:
                            ui.notify('Last Name is required', type='negative')
                            return
                        if not hire_month_select.value or not hire_day_select.value or not hire_year_select.value:
                            ui.notify('All hire date fields (Month, Day, Year) are required', type='negative')
                            return
                        
                        # Validate and create hire date
                        from datetime import datetime
                        
                        try:
                            hire_date_str = f"{hire_year_select.value}-{hire_month_select.value:02d}-{hire_day_select.value:02d}"
                            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            ui.notify('Invalid hire date - please check the date is valid', type='negative')
                            return
                        
                        # Build remote schedule JSON
                        import json
                        remote_schedule = {
                            "monday": monday_check.value,
                            "tuesday": tuesday_check.value,
                            "wednesday": wednesday_check.value,
                            "thursday": thursday_check.value,
                            "friday": friday_check.value
                        }
                        
                        db = next(get_db())
                        try:
                            from src.services.user_service import UserService
                            from src.schemas.user_schemas import UserUpdate
                            
                            # Build update data - only include password if provided
                            update_data = {
                                'username': username_input.value,
                                'email': email_input.value,
                                'first_name': first_name_input.value,
                                'last_name': last_name_input.value,
                                'department_id': department_select.value,
                                'role': role_select.value,
                                'hire_date': hire_date,
                                'remote_schedule': json.dumps(remote_schedule),
                                'is_active': is_active_check.value
                            }
                            
                            # Only include password if provided
                            if password_input.value:
                                update_data['password'] = password_input.value
                            
                            user_update = UserUpdate(**update_data)
                            
                            user_service = UserService(db)
                            updated_user = user_service.update_user(user_id, user_update)
                            
                            if updated_user:
                                ui.notify(f'Employee "{updated_user.first_name} {updated_user.last_name}" updated successfully', type='positive')
                                ui.navigate.to('/admin/employees')
                            else:
                                ui.notify('Error updating employee', type='negative')
                            
                        except Exception as e:
                            ui.notify(f'Error updating employee: {str(e)}', type='negative')
                        finally:
                            db.close()
                    
                    ui.button('Save Changes', on_click=save_changes, color='positive')
                    ui.button('Cancel', on_click=lambda: ui.navigate.to('/admin/employees'), color='secondary')
    
    finally:
        db.close()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0', storage_secret='your-secret-key-change-in-production')
