from nicegui import ui, app
import sys
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

        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')

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
                    ui.button('Coming Soon', color='gray', disabled=True)
        
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
        
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).classes('mt-4')

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
                columns = [
                    {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
                    {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'},
                    {'name': 'department', 'label': 'Department', 'field': 'department', 'align': 'left'},
                    {'name': 'role', 'label': 'Role', 'field': 'role', 'align': 'left'},
                    {'name': 'hire_date', 'label': 'Hire Date', 'field': 'hire_date', 'align': 'left'},
                    {'name': 'active', 'label': 'Active', 'field': 'active', 'align': 'center'},
                ]
                
                rows = []
                for user in users:
                    department_name = 'No Department'
                    if user.department_id:
                        department_name = dept_lookup.get(user.department_id, 'Unknown Department')
                    
                    rows.append({
                        'id': user.id,
                        'name': f'{user.first_name} {user.last_name}',
                        'email': user.email,
                        'department': department_name,
                        'role': user.role.title(),
                        'hire_date': user.hire_date.strftime('%Y-%m-%d') if user.hire_date else 'Not Set',
                        'active': 'Yes' if user.is_active else 'No'
                    })
                
                table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')
                
                # Make rows clickable
                def on_row_click(e):
                    user_id = e.args[1]['id']
                    ui.navigate.to(f'/admin/employees/edit/{user_id}')
                
                table.on('rowClick', on_row_click)
        
        finally:
            db.close()
        
        ui.button('Back to Admin Panel', on_click=lambda: ui.navigate.to('/admin')).classes('mt-4')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8080, host='0.0.0.0', storage_secret='your-secret-key-change-in-production')
