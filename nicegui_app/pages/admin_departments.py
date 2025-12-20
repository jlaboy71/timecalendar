"""Admin page for managing departments with row-based UI and professional styling."""
import re
import json
from datetime import datetime
from nicegui import ui, app, context
from src.database import get_db
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import (
    apply_dark_mode,
    validate_required,
    show_warning_dialog,
    show_error_dialog,
    show_success_dialog,
    show_help_dialog,
    create_help_button,
    empty_state,
)
from src.services.department_service import DepartmentService
from src.services.user_service import UserService
from src.services.balance_service import BalanceService
from src.services.audit_service import AuditService
from src.models.user import User
from src.schemas.user_schemas import UserCreate, UserUpdate

# TJM Brand Colors
TJM_GOLD = "#c9a227"
TJM_GRAY = "#5a6a72"

# Department icon mapping - keywords to Material Icons
DEPT_ICON_KEYWORDS = {
    # Time/PTO related
    'pto': 'schedule', 'time': 'schedule', 'leave': 'event_busy', 'vacation': 'beach_access',
    'personal': 'person', 'absence': 'event_busy',
    # Technology
    'tech': 'computer', 'technology': 'computer', 'it': 'devices', 'software': 'code',
    'engineering': 'engineering', 'development': 'code', 'dev': 'code',
    # Business/Admin
    'admin': 'admin_panel_settings', 'hr': 'people', 'human': 'people', 'resources': 'people',
    'finance': 'account_balance', 'accounting': 'calculate', 'legal': 'gavel',
    # Operations
    'operations': 'settings', 'ops': 'settings', 'logistics': 'local_shipping',
    'warehouse': 'warehouse', 'shipping': 'local_shipping', 'supply': 'inventory',
    # Sales/Marketing
    'sales': 'trending_up', 'marketing': 'campaign', 'customer': 'support_agent',
    'support': 'headset_mic', 'service': 'room_service',
    # Financial/Trading - exchanges and trading terms
    'trading': 'show_chart', 'trader': 'show_chart', 'trade': 'show_chart',
    'exchange': 'currency_exchange', 'market': 'storefront', 'markets': 'storefront',
    'cme': 'show_chart', 'cboe': 'show_chart', 'nyse': 'show_chart', 'nasdaq': 'show_chart',
    'nymex': 'show_chart', 'comex': 'show_chart', 'ice': 'show_chart', 'cbot': 'show_chart',
    'options': 'swap_horiz', 'futures': 'timeline', 'equities': 'candlestick_chart',
    'derivatives': 'analytics', 'commodities': 'inventory_2', 'forex': 'currency_exchange',
    'fx': 'currency_exchange', 'softs': 'eco', 'ags': 'grass', 'grains': 'grass',
    'fixed income': 'account_balance', 'bonds': 'account_balance',
    'risk': 'warning', 'compliance': 'verified_user', 'clearing': 'sync_alt',
    'settlement': 'task_alt', 'execution': 'bolt', 'order': 'receipt_long',
    'portfolio': 'pie_chart', 'asset': 'savings', 'wealth': 'savings',
    'investment': 'trending_up', 'investor': 'trending_up', 'brokerage': 'handshake',
    # Leadership/Executive
    'executive': 'star', 'executives': 'star', 'leadership': 'star', 'c-suite': 'star',
    'management': 'supervisor_account', 'director': 'supervisor_account',
    # Locations/Branch offices
    'boca': 'location_on', 'connecticut': 'location_on', 'ct': 'location_on',
    'new york': 'location_on', 'ny': 'location_on', 'chicago': 'location_on',
    'london': 'location_on', 'remote': 'home_work', 'branch': 'store',
    # Other
    'research': 'science', 'quality': 'verified', 'security': 'security',
    'training': 'school', 'education': 'school', 'design': 'brush',
    'creative': 'palette', 'media': 'perm_media', 'communications': 'forum',
}

# Color palette for departments (will cycle through)
DEPT_COLOR_PALETTE = [
    {'bg': '#3b82f6', 'light': '#dbeafe'},  # Blue
    {'bg': '#8b5cf6', 'light': '#ede9fe'},  # Purple
    {'bg': '#06b6d4', 'light': '#cffafe'},  # Cyan
    {'bg': '#f97316', 'light': '#ffedd5'},  # Orange
    {'bg': '#ec4899', 'light': '#fce7f3'},  # Pink
    {'bg': '#14b8a6', 'light': '#ccfbf1'},  # Teal
    {'bg': '#6366f1', 'light': '#e0e7ff'},  # Indigo
    {'bg': '#84cc16', 'light': '#ecfccb'},  # Lime
]


def get_dept_icon(name: str) -> str:
    """Get a Material Icon based on department name keywords."""
    name_lower = name.lower()
    for keyword, icon in DEPT_ICON_KEYWORDS.items():
        if keyword in name_lower:
            return icon
    return 'business'  # Default icon


def get_dept_color(dept_id: int) -> dict:
    """Get a color from palette based on department ID."""
    return DEPT_COLOR_PALETTE[dept_id % len(DEPT_COLOR_PALETTE)]


def admin_departments_page():
    """Admin departments management page with professional row-based UI."""
    apply_dark_mode()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    def load_department_data():
        """Load all department data with members."""
        db = next(get_db())
        try:
            # Include managers, admins, and superadmins as potential department managers
            managers = UserService.get_users_by_role(db, 'manager')
            admins = UserService.get_users_by_role(db, 'admin')
            superadmins = UserService.get_users_by_role(db, 'superadmin')
            all_managers = list(managers) + list(admins) + list(superadmins)
            manager_options = {0: 'No Manager'}
            manager_options.update({m.id: f'{m.first_name} {m.last_name}' for m in all_managers})
            departments = DepartmentService.get_all_departments(db)

            dept_data = []
            for dept in departments:
                manager_name = None
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

    # Calculate stats
    total_employees = sum(d['employee_count'] for d in dept_data)

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 animate-fade-in'):
        # Header with help button
        with ui.row().classes('w-full justify-between items-start mb-6'):
            page_header(title='DEPARTMENT MANAGEMENT', show_back=False)
            create_help_button(
                'Department Management',
                '''
                <b>Overview:</b> Organize employees into departments with assigned managers.<br><br>
                <b>Stats Row:</b> Click any stat tile to see details<br>
                • <b>Departments</b> - View all, click to edit<br>
                • <b>Employees</b> - Distribution by dept, drill down to employees<br>
                • <b>Without Manager</b> - Quick assign managers<br><br>
                <b>Department Rows:</b><br>
                • Green border = Active with manager<br>
                • Amber border = Needs manager assigned<br>
                • Gray border = Inactive<br><br>
                <b>Actions:</b> View Team, Edit, or Delete each department
                '''
            )

        # ============ STATS ROW (Dashboard Style) ============
        with ui.row().classes('w-full gap-4 mb-6'):
            # Total Departments - clickable
            with ui.card().classes('flex-1 p-4 border-l-4 border-blue-500 cursor-pointer admin-stat-card').on('click', lambda: show_all_departments_dialog()):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #3b82f6, #1d4ed8);'):
                        ui.icon('business', color='white').classes('text-xl')
                    with ui.column().classes('gap-0'):
                        ui.label(str(len(dept_data))).classes('text-3xl font-bold')
                        ui.label('Departments').classes('text-xs opacity-60')
                ui.tooltip('Click to view all departments')

            # Total Employees - clickable
            with ui.card().classes('flex-1 p-4 border-l-4 border-green-500 cursor-pointer admin-stat-card').on('click', lambda: show_employee_breakdown_dialog()):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style('background: linear-gradient(135deg, #22c55e, #16a34a);'):
                        ui.icon('groups', color='white').classes('text-xl')
                    with ui.column().classes('gap-0'):
                        ui.label(str(total_employees)).classes('text-3xl font-bold')
                        ui.label('Total Employees').classes('text-xs opacity-60')
                ui.tooltip('Click to view employee distribution')

            # Add Department - action card
            with ui.card().classes('flex-1 p-4 border-l-4 cursor-pointer admin-stat-card').style(f'border-left-color: {TJM_GOLD};').on('click', lambda: open_create_dialog()):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style(f'background: linear-gradient(135deg, {TJM_GOLD}, #b8922a);'):
                        ui.icon('add_business', color='white').classes('text-xl')
                    with ui.column().classes('gap-0'):
                        ui.label('+').classes('text-3xl font-bold')
                        ui.label('Add Department').classes('text-xs opacity-60')
                ui.tooltip('Create a new department')

            # Add Employee - action card (opens slide-out panel)
            with ui.card().classes('flex-1 p-4 border-l-4 cursor-pointer admin-stat-card').style(f'border-left-color: {TJM_GOLD};').on('click', lambda: show_add_employee_panel()):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes('w-12 h-12 rounded-full flex items-center justify-center').style(f'background: linear-gradient(135deg, {TJM_GOLD}, #b8922a);'):
                        ui.icon('person_add', color='white').classes('text-xl')
                    with ui.column().classes('gap-0'):
                        ui.label('+').classes('text-3xl font-bold')
                        ui.label('Add Employee').classes('text-xs opacity-60')
                ui.tooltip('Add a new employee')

        # ============ DEPARTMENT ROWS ============
        rows_container = ui.column().classes('w-full gap-3')

        def render_department_rows():
            rows_container.clear()
            with rows_container:
                if not dept_data:
                    empty_state(
                        icon='business',
                        title='No Departments Yet',
                        description='Create your first department to start organizing employees into teams.',
                        action_label='Create First Department',
                        action_click=lambda: open_create_dialog()
                    )
                else:
                    for dept in dept_data:
                        render_department_row(dept)

        def render_department_row(dept: dict):
            """Render a single department as a horizontal row with action buttons."""
            # Determine border color based on status
            if not dept['is_active']:
                border_color = '#64748b'  # Gray - inactive
            elif not dept['manager_id']:
                border_color = '#f59e0b'  # Amber - needs manager
            else:
                border_color = '#10b981'  # Green - active with manager

            # Get auto-assigned icon and color based on department name/id
            dept_icon = get_dept_icon(dept['name'])
            dept_color = get_dept_color(dept['id'])

            # Make a copy for closure
            dept_copy = dict(dept)

            with ui.card().classes('w-full p-4 hover:shadow-lg transition-all').style(f'border-left: 4px solid {border_color};'):
                with ui.row().classes('w-full items-center'):
                    # LEFT: Icon + Name and Code
                    with ui.row().classes('items-center gap-3').style('width: 280px; flex-shrink: 0;'):
                        # Department icon with auto-assigned color
                        with ui.element('div').classes('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0').style(f'background: {dept_color["bg"]};'):
                            ui.icon(dept_icon, color='white', size='sm')
                        with ui.column().classes('gap-0'):
                            ui.label(dept['name']).classes('text-lg font-semibold')
                            ui.label(f"Code: {dept['code']}").classes('text-xs opacity-50 font-mono')

                    # MIDDLE: Spacer
                    ui.element('div').classes('flex-1')

                    # RIGHT: Info (stacked) + Action buttons
                    with ui.row().classes('items-center gap-4 flex-shrink-0'):
                        # Stacked info: Employees on top, Manager below, icons aligned
                        with ui.column().classes('gap-1 items-end').style('min-width: 140px;'):
                            # Employee count
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('groups', size='xs').classes('opacity-50')
                                count = dept['employee_count']
                                ui.label(f"{count} Employee{'s' if count != 1 else ''}").classes('text-xs')
                            # Manager
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('person', size='xs').classes('opacity-50')
                                if dept['manager_name']:
                                    ui.label(dept['manager_name']).classes('text-xs font-medium')
                                else:
                                    ui.label('No Manager').classes('text-xs text-amber-600 italic')

                        # Action buttons (view team, edit, delete)
                        with ui.row().classes('gap-2'):
                            ui.button(icon='visibility', on_click=lambda e, d=dept_copy: show_team_panel(d)).props('flat dense').tooltip('View Team')
                            ui.button(icon='edit', on_click=lambda e, d=dept_copy: open_edit_dialog(d)).props('flat dense').tooltip('Edit Department')
                            ui.button(icon='delete', on_click=lambda e, d=dept_copy: open_delete_dialog(d)).props('flat color=red dense').tooltip('Delete Department')

        # ============ STAT TILE DETAIL DIALOGS ============

        def show_all_departments_dialog():
            """Show dialog with all departments - clickable to edit."""
            dialog_ref = {'dialog': None}

            def edit_dept(dept_dict):
                """Handler to close dialog and open edit dialog for department."""
                try:
                    if dialog_ref['dialog']:
                        dialog_ref['dialog'].close()
                    open_edit_dialog(dept_dict)
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')

            with ui.dialog() as dialog, ui.card().classes('p-6').style('width: 550px;'):
                dialog_ref['dialog'] = dialog

                with ui.row().classes('w-full items-center justify-between mb-4 pb-4 border-b border-gray-700'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('business', color='blue')
                        ui.label('All Departments').classes('text-xl font-semibold')
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                ui.label('Click any department to edit').classes('text-xs opacity-50 mb-3')

                with ui.column().classes('w-full gap-2'):
                    for dept in dept_data:
                        border = '#10b981' if dept['is_active'] and dept['manager_id'] else '#f59e0b' if dept['is_active'] else '#64748b'
                        # Get department's icon and color
                        dept_icon = get_dept_icon(dept['name'])
                        dept_color = get_dept_color(dept['id'])
                        # Make a copy to ensure proper capture
                        dept_copy = dict(dept)

                        with ui.card().classes('w-full p-3 cursor-pointer hover:shadow-md transition-all').style(f'border-left: 3px solid {border};') as card:
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.row().classes('items-center gap-3'):
                                    # Department icon with color
                                    with ui.element('div').classes('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0').style(f'background: {dept_color["bg"]};'):
                                        ui.icon(dept_icon, color='white', size='xs')
                                    with ui.column().classes('gap-0'):
                                        ui.label(dept['name']).classes('font-semibold')
                                        ui.label(f"{dept['employee_count']} employees • {dept['manager_name'] or 'No Manager'}").classes('text-xs opacity-60')
                                ui.badge('Active' if dept['is_active'] else 'Inactive', color='green' if dept['is_active'] else 'gray').props('dense')

                        # Bind click with captured copy using default argument (e for event)
                        card.on('click', lambda e, d=dept_copy: edit_dept(d))

            dialog.open()

        def show_employee_breakdown_dialog():
            """Show dialog with employee distribution - click dept to see employees."""
            selected_dept = {'value': None}
            dialog_ref = {'dialog': None}

            def select_department(dept_dict):
                """Handler to select a department and show its employees."""
                try:
                    selected_dept['value'] = dept_dict
                    render_distribution()
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')

            def go_back_to_list():
                """Handler to go back to department list."""
                try:
                    selected_dept['value'] = None
                    render_distribution()
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')

            def edit_employee(emp_id):
                """Handler to navigate to employee edit page."""
                try:
                    if dialog_ref['dialog']:
                        dialog_ref['dialog'].close()
                    ui.navigate.to(f'/admin/employees/edit/{emp_id}')
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', type='negative')

            with ui.dialog() as dialog, ui.card().classes('p-6').style('width: 600px; max-height: 80vh;'):
                dialog_ref['dialog'] = dialog

                with ui.row().classes('w-full items-center justify-between mb-4 pb-4 border-b border-gray-700'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('groups', color='green')
                        ui.label('Employee Distribution').classes('text-xl font-semibold')
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                content_container = ui.column().classes('w-full')

                def render_distribution():
                    content_container.clear()
                    with content_container:
                        if selected_dept['value'] is None:
                            # Show department breakdown
                            ui.label(f'Total: {total_employees} employees across {len(dept_data)} departments').classes('text-sm opacity-70 mb-2')
                            ui.label('Click a department to view its employees').classes('text-xs opacity-50 mb-4')

                            sorted_depts = sorted(dept_data, key=lambda d: d['employee_count'], reverse=True)
                            max_count = max(d['employee_count'] for d in dept_data) if dept_data else 1

                            with ui.column().classes('w-full gap-3'):
                                for dept in sorted_depts:
                                    # Get department's icon and color
                                    dept_icon = get_dept_icon(dept['name'])
                                    dept_color = get_dept_color(dept['id'])
                                    # Store dept in default arg to capture current value
                                    dept_copy = dict(dept)  # Make a copy to ensure immutability

                                    with ui.card().classes('w-full p-3 cursor-pointer hover:shadow-md transition-all') as card:
                                        with ui.row().classes('w-full justify-between items-center mb-2'):
                                            with ui.row().classes('items-center gap-3'):
                                                # Department icon with color
                                                with ui.element('div').classes('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0').style(f'background: {dept_color["bg"]};'):
                                                    ui.icon(dept_icon, color='white', size='xs')
                                                ui.label(dept['name']).classes('font-medium')
                                            ui.label(f"{dept['employee_count']}").classes('font-bold')
                                        pct = (dept['employee_count'] / max_count * 100) if max_count > 0 else 0
                                        with ui.element('div').classes('w-full h-2 rounded-full bg-gray-700'):
                                            ui.element('div').classes('h-2 rounded-full').style(f'width: {pct}%; background: {dept_color["bg"]};')

                                    # Bind click handler with captured copy (e for event)
                                    card.on('click', lambda e, d=dept_copy: select_department(d))
                        else:
                            # Show employees for selected department
                            dept = selected_dept['value']
                            # Get department's icon and color
                            dept_icon = get_dept_icon(dept['name'])
                            dept_color = get_dept_color(dept['id'])

                            with ui.row().classes('items-center gap-3 mb-4'):
                                ui.button(icon='arrow_back', on_click=go_back_to_list).props('flat dense')
                                # Department icon with color
                                with ui.element('div').classes('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0').style(f'background: {dept_color["bg"]};'):
                                    ui.icon(dept_icon, color='white', size='xs')
                                ui.label(f"{dept['name']} - {dept['employee_count']} Employees").classes('font-semibold')

                            if not dept['employees']:
                                with ui.column().classes('w-full items-center py-6'):
                                    ui.icon('group_off', size='xl').classes('opacity-30')
                                    ui.label('No employees in this department').classes('opacity-50 mt-2')
                            else:
                                ui.label('Click an employee to edit their account').classes('text-xs opacity-50 mb-3')
                                role_colors = {'employee': 'gray', 'manager': 'blue', 'admin': 'purple', 'superadmin': 'amber'}

                                with ui.scroll_area().style('max-height: 400px;'):
                                    with ui.column().classes('w-full gap-2 pr-2'):
                                        for emp in dept['employees']:
                                            emp_id = emp['id']  # Capture the ID

                                            with ui.card().classes('w-full p-3 cursor-pointer hover:shadow-md transition-all') as emp_card:
                                                with ui.row().classes('w-full items-center gap-3'):
                                                    with ui.element('div').classes('w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0'):
                                                        ui.label(emp['name'][0]).classes('text-blue-600 font-medium')
                                                    with ui.column().classes('flex-1 gap-0 min-w-0'):
                                                        ui.label(emp['name']).classes('font-medium text-sm')
                                                        ui.label(emp['email']).classes('text-xs opacity-50 truncate')
                                                    with ui.row().classes('items-center gap-2 flex-shrink-0'):
                                                        ui.badge(emp['role'].title(), color=role_colors.get(emp['role'], 'gray')).props('dense')
                                                        ui.icon('edit', size='xs').classes('opacity-30')

                                            # Bind click with captured emp_id (e for event)
                                            emp_card.on('click', lambda e, eid=emp_id: edit_employee(eid))

                render_distribution()

            dialog.open()

        # ============ DIALOGS ============

        def open_create_dialog():
            """Open create department dialog with live icon preview."""
            # Use a counter to generate consistent preview color
            preview_dept_id = len(dept_data) + 1

            with ui.dialog() as dialog, ui.card().classes('p-6 w-96 animate-fade-in-up'):
                with ui.row().classes('w-full items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-700'):
                    ui.label('Create Department').classes('text-xl font-semibold')
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                name_input = ui.input('Department Name').props('outlined').classes('w-full mb-2')

                # Icon preview section
                icon_preview_container = ui.column().classes('w-full mb-4')

                def update_icon_preview():
                    """Update the icon preview based on current name."""
                    icon_preview_container.clear()
                    with icon_preview_container:
                        name = name_input.value or ''
                        if name:
                            preview_icon = get_dept_icon(name)
                            preview_color = get_dept_color(preview_dept_id)
                            with ui.row().classes('items-center gap-3 p-3 rounded-lg').style('background: rgba(0,0,0,0.1);'):
                                with ui.element('div').classes('w-10 h-10 rounded-lg flex items-center justify-center').style(f'background: {preview_color["bg"]};'):
                                    ui.icon(preview_icon, color='white', size='sm')
                                with ui.column().classes('gap-0'):
                                    ui.label('Icon Preview').classes('text-xs opacity-50')
                                    ui.label(f'{preview_icon}').classes('text-sm font-medium')
                        else:
                            ui.label('Type a name to see icon preview').classes('text-xs opacity-40 italic')

                # Initial preview
                update_icon_preview()

                # Update preview as user types
                name_input.on('input', lambda: update_icon_preview())

                code_input = ui.input('Department Code').props('outlined').classes('w-full mb-4')
                manager_select = ui.select(manager_options, label='Manager', value=0).props('outlined').classes('w-full mb-4')

                # Hint about icon keywords
                with ui.expansion('Icon Keywords', icon='lightbulb').classes('w-full mb-4').props('dense'):
                    ui.label('Include these words in the name for specific icons:').classes('text-xs opacity-60 mb-2')
                    keyword_examples = [
                        ('CME, CBOE, NYSE, trading', 'show_chart'),
                        ('options, futures, equities', 'swap_horiz/timeline'),
                        ('risk, compliance', 'warning/verified_user'),
                        ('finance, accounting', 'account_balance'),
                        ('tech, IT, software', 'computer/code'),
                        ('HR, human, people', 'people'),
                        ('sales, marketing', 'trending_up'),
                        ('operations, logistics', 'settings'),
                    ]
                    for keywords, icons in keyword_examples:
                        ui.label(f'• {keywords} → {icons}').classes('text-xs opacity-50')

                def auto_code():
                    if name_input.value and not code_input.value:
                        words = name_input.value.split()
                        code_input.value = ''.join(w[0].upper() for w in words[:3])
                name_input.on('blur', auto_code)

                def create_dept():
                    valid = True
                    if not validate_required(name_input, 'Department Name'):
                        valid = False
                    if not validate_required(code_input, 'Department Code'):
                        valid = False
                    if not valid:
                        show_warning_dialog('Form Incomplete', 'Please fix the highlighted errors.')
                        return

                    db = next(get_db())
                    try:
                        mgr_id = None if manager_select.value == 0 else manager_select.value
                        DepartmentService.create_department(db, name_input.value, code_input.value, mgr_id)
                        dialog.close()
                        show_success_dialog('Department Created', f'"{name_input.value}" created successfully', on_close=lambda: ui.navigate.to('/admin/departments'))
                    except ValueError as e:
                        show_error_dialog('Error', str(e))
                    finally:
                        db.close()

                with ui.row().classes('w-full justify-end gap-3'):
                    ui.button('Cancel', on_click=dialog.close).props('flat color=gray')
                    ui.button('Create Department', icon='add', on_click=create_dept).classes('btn-gold')

            dialog.open()

        def open_edit_dialog(dept: dict):
            """Open edit department dialog."""
            try:
                with ui.dialog() as dialog, ui.card().classes('p-6 w-96 animate-fade-in-up'):
                    with ui.row().classes('w-full items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-700'):
                        ui.label(f"Edit: {dept['name']}").classes('text-xl font-semibold')
                        ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                    edit_name = ui.input('Department Name', value=dept['name']).props('outlined').classes('w-full mb-4')
                    edit_code = ui.input('Department Code', value=dept['code']).props('outlined').classes('w-full mb-4')
                    # Use 0 as default if manager_id not in options
                    mgr_value = dept['manager_id'] if dept['manager_id'] in manager_options else 0
                    edit_manager = ui.select(manager_options, label='Manager', value=mgr_value).props('outlined').classes('w-full mb-6')

                    def save_changes():
                        valid = True
                        if not validate_required(edit_name, 'Department Name'):
                            valid = False
                        if not validate_required(edit_code, 'Department Code'):
                            valid = False
                        if not valid:
                            show_warning_dialog('Form Incomplete', 'Please fix the highlighted errors.')
                            return

                        db = next(get_db())
                        try:
                            mgr_id = None if edit_manager.value == 0 else edit_manager.value
                            DepartmentService.update_department(db, dept['id'], name=edit_name.value, code=edit_code.value, manager_id=mgr_id)
                            dialog.close()
                            show_success_dialog('Department Updated', 'Changes saved successfully', on_close=lambda: ui.navigate.to('/admin/departments'))
                        except ValueError as e:
                            show_error_dialog('Error', str(e))
                        finally:
                            db.close()

                    with ui.row().classes('w-full justify-end gap-3'):
                        ui.button('Cancel', on_click=dialog.close).props('flat color=gray')
                        ui.button('Save Changes', icon='save', on_click=save_changes).classes('btn-gold')

                dialog.open()
            except Exception as e:
                ui.notify(f'Error creating dialog: {str(e)}', type='negative')

        def open_delete_dialog(dept: dict):
            """Open delete confirmation dialog."""
            with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
                ui.label('Delete Department').classes('text-lg font-semibold mb-4')

                if dept['employee_count'] > 0:
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('error', color='red')
                        ui.label(f"Cannot delete: {dept['employee_count']} employee(s) are assigned.").classes('text-red-600')
                    ui.label('Reassign employees to another department first.').classes('text-sm opacity-70 mb-4')
                    ui.button('Close', on_click=dialog.close).props('flat')
                else:
                    ui.label(f'Are you sure you want to delete "{dept["name"]}"?').classes('mb-2')
                    ui.label('This action cannot be undone.').classes('text-sm opacity-70 mb-4')

                    def confirm_delete():
                        db = next(get_db())
                        try:
                            DepartmentService.delete_department(db, dept['id'])
                            dialog.close()
                            show_success_dialog('Deleted', 'Department deleted successfully', on_close=lambda: ui.navigate.to('/admin/departments'))
                        except ValueError as e:
                            show_error_dialog('Error', str(e))
                        finally:
                            db.close()

                    with ui.row().classes('w-full justify-end gap-3'):
                        ui.button('Cancel', on_click=dialog.close).props('flat')
                        ui.button('Delete', icon='delete', on_click=confirm_delete).props('color=red')

            dialog.open()

        def show_team_panel(dept: dict):
            """Show slide-out panel with department team members."""
            # Get department's auto-assigned color and icon for header
            dept_color = get_dept_color(dept['id'])
            dept_icon = get_dept_icon(dept['name'])
            header_bg = dept_color['bg']

            with ui.dialog().props('position=right full-height') as panel:
                with ui.card().classes('h-full p-0 animate-fade-in').style('width: 400px;'):
                    # Panel header - uses department's color and icon
                    with ui.element('div').classes('p-5 border-b').style(f'background: linear-gradient(135deg, {header_bg} 0%, {header_bg}dd 100%)'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.row().classes('items-center gap-3'):
                                # Department icon
                                with ui.element('div').classes('w-10 h-10 rounded-lg flex items-center justify-center').style('background: rgba(255,255,255,0.2);'):
                                    ui.icon(dept_icon, color='white', size='sm')
                                with ui.column().classes('gap-1'):
                                    ui.label(dept['name']).classes('text-xl font-semibold text-white')
                                    ui.label(f"{dept['employee_count']} team members").classes('text-sm text-white opacity-70')
                            ui.button(icon='close', on_click=panel.close).props('flat round').classes('text-white')

                    # Manager section
                    with ui.element('div').classes('p-4 border-b'):
                        ui.label('MANAGER').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-3')
                        if dept['manager_name']:
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-10 h-10 rounded-full flex items-center justify-center').style(f'background: {TJM_GOLD}'):
                                    ui.label(dept['manager_name'][0]).classes('text-white font-semibold')
                                ui.label(dept['manager_name']).classes('font-medium')
                        else:
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('warning', color='amber')
                                ui.label('No manager assigned').classes('text-amber-600')
                            ui.label('Use the edit button to assign a manager').classes('text-xs opacity-50 mt-1')

                    # Team members list
                    with ui.scroll_area().classes('flex-1'):
                        with ui.element('div').classes('p-4'):
                            ui.label('TEAM MEMBERS').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-4')

                            if not dept['employees']:
                                with ui.column().classes('items-center py-8'):
                                    ui.icon('group_off', size='xl').classes('opacity-30')
                                    ui.label('No employees yet').classes('opacity-40 mt-2')
                            else:
                                with ui.column().classes('w-full gap-2'):
                                    for emp in dept['employees']:
                                        # Factory function to capture emp value
                                        def make_emp_click(employee):
                                            def handler(event):  # event parameter for NiceGUI
                                                ui.navigate.to(f'/admin/employees/edit/{employee["id"]}')
                                            return handler

                                        with ui.card().classes('w-full p-3 cursor-pointer hover:shadow-md transition-all').style('min-height: 60px;').on('click', make_emp_click(emp)):
                                            with ui.row().classes('w-full items-center gap-3'):
                                                with ui.element('div').classes('w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0'):
                                                    ui.label(emp['name'][0]).classes('text-blue-600 font-medium')
                                                with ui.column().classes('flex-1 gap-0 min-w-0'):
                                                    ui.label(emp['name']).classes('font-medium text-sm truncate')
                                                    ui.label(emp['email']).classes('text-xs opacity-50 truncate')
                                                role_colors = {'employee': 'gray', 'manager': 'blue', 'admin': 'purple', 'superadmin': 'amber'}
                                                with ui.element('div').classes('flex-shrink-0').style('width: 80px;'):
                                                    ui.badge(emp['role'].title(), color=role_colors.get(emp['role'], 'gray')).props('dense')

            panel.open()

        def show_add_employee_panel():
            """Show slide-out panel for adding a new employee."""
            # Load department options
            db = next(get_db())
            try:
                departments = DepartmentService.get_all_departments(db)
                panel_dept_options = {None: 'Select Department'}
                panel_dept_options.update({dept.id: dept.name for dept in departments})
            finally:
                db.close()

            with ui.dialog().props('position=right full-height') as panel:
                with ui.card().classes('h-full p-0 animate-fade-in').style('width: 700px;'):
                    # Panel header
                    with ui.element('div').classes('p-5 border-b').style(f'background: linear-gradient(135deg, {TJM_GOLD} 0%, #b8922a 100%)'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('w-10 h-10 rounded-lg flex items-center justify-center').style('background: rgba(255,255,255,0.2);'):
                                    ui.icon('person_add', color='white', size='sm')
                                with ui.column().classes('gap-1'):
                                    ui.label('Add New Employee').classes('text-xl font-semibold text-white')
                                    ui.label('Quick create from this page').classes('text-sm text-white opacity-70')
                            ui.button(icon='close', on_click=panel.close).props('flat round').classes('text-white')

                    # Scrollable form content
                    with ui.scroll_area().classes('flex-1'):
                        with ui.element('div').classes('p-5'):
                            # Basic Information
                            ui.label('BASIC INFORMATION').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-3')
                            with ui.column().classes('w-full gap-3 mb-6'):
                                with ui.row().classes('w-full gap-3'):
                                    first_name_input = ui.input('First Name').props('outlined dense').classes('flex-1')
                                    last_name_input = ui.input('Last Name').props('outlined dense').classes('flex-1')

                                with ui.row().classes('w-full gap-3'):
                                    username_input = ui.input('Username').props('outlined dense').classes('flex-1')
                                    email_input = ui.input('Email').props('outlined dense').classes('flex-1')

                                # Password fields
                                password_visible = {'value': False}
                                with ui.row().classes('w-full gap-3'):
                                    password_input = ui.input('Password', password=True).props('outlined dense').classes('flex-1')
                                    confirm_password_input = ui.input('Confirm Password', password=True).props('outlined dense').classes('flex-1')

                                with ui.row().classes('items-center gap-2'):
                                    def toggle_password():
                                        password_visible['value'] = not password_visible['value']
                                        password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                                        confirm_password_input.props(f'type={"text" if password_visible["value"] else "password"}')
                                        vis_icon.props(f'name={"visibility_off" if password_visible["value"] else "visibility"}')

                                    vis_icon = ui.icon('visibility', size='xs').classes('cursor-pointer opacity-60 hover:opacity-100')
                                    vis_icon.on('click', toggle_password)
                                    ui.label('Show passwords').classes('text-xs opacity-60')

                            # Employment Details
                            ui.label('EMPLOYMENT DETAILS').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-3')
                            with ui.column().classes('w-full gap-3 mb-6'):
                                # Hire Date - full width row
                                with ui.input('Hire Date').props('outlined dense readonly').classes('w-full') as hire_date_input:
                                    with ui.menu().props('no-parent-event') as date_menu:
                                        with ui.date(mask='YYYY-MM-DD').bind_value(hire_date_input):
                                            with ui.row().classes('justify-end'):
                                                ui.button('Close', on_click=date_menu.close).props('flat dense')
                                    with hire_date_input.add_slot('append'):
                                        ui.icon('event').on('click', date_menu.open).classes('cursor-pointer')

                                # Department - full width with + button
                                with ui.row().classes('w-full items-end gap-2'):
                                    emp_dept_select = ui.select(panel_dept_options, label='Department', value=None).props('outlined dense').classes('flex-grow')

                                    # Quick create department button
                                    def open_quick_dept_dialog():
                                        with context.client.content:
                                            with ui.dialog() as dept_dialog, ui.card().classes('p-5').style('background-color: #1f2937; min-width: 400px;'):
                                                with ui.row().classes('items-center gap-2 mb-4'):
                                                    ui.icon('add_business', size='sm').style(f'color: {TJM_GOLD};')
                                                    ui.label('Quick Create Department').classes('text-lg font-bold')

                                                with ui.row().classes('w-full items-center gap-3'):
                                                    quick_dept_icon = ui.icon('business', size='lg').style(f'color: {TJM_GOLD};')
                                                    quick_dept_name = ui.input('Department Name').props('outlined dense').classes('flex-grow')

                                                def update_quick_icon():
                                                    if quick_dept_name.value:
                                                        icon = get_dept_icon(quick_dept_name.value)
                                                        quick_dept_icon.props(f'name={icon}')
                                                    else:
                                                        quick_dept_icon.props('name=business')

                                                quick_dept_name.on('update:model-value', lambda e: update_quick_icon())
                                                quick_dept_code = ui.input('Code', placeholder='e.g., ACCT').props('outlined dense').classes('w-full mt-2')

                                                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                                                    ui.button('Cancel', on_click=dept_dialog.close).props('flat')

                                                    def create_quick_dept():
                                                        if not quick_dept_name.value or not quick_dept_code.value:
                                                            ui.notify('Name and code required', type='warning')
                                                            return
                                                        qdb = next(get_db())
                                                        try:
                                                            new_dept = DepartmentService.create_department(
                                                                qdb, name=quick_dept_name.value.strip(),
                                                                code=quick_dept_code.value.strip().upper()
                                                            )
                                                            if new_dept:
                                                                panel_dept_options[new_dept.id] = new_dept.name
                                                                emp_dept_select.options = panel_dept_options
                                                                emp_dept_select.value = new_dept.id
                                                                emp_dept_select.update()
                                                                dept_dialog.close()
                                                                ui.notify(f'Department "{new_dept.name}" created!', type='positive')
                                                        except Exception as ex:
                                                            ui.notify(f'Error: {str(ex)}', type='negative')
                                                        finally:
                                                            qdb.close()

                                                    ui.button('Create', on_click=create_quick_dept).style(f'background-color: {TJM_GOLD} !important; color: white !important;')

                                            dept_dialog.open()

                                    ui.button(icon='add', on_click=open_quick_dept_dialog).props('flat dense').tooltip('Quick Create Department')

                                # Department preview
                                dept_preview = ui.row().classes('w-full')

                                def update_dept_preview():
                                    dept_preview.clear()
                                    d_id = emp_dept_select.value
                                    if d_id and d_id in panel_dept_options:
                                        d_name = panel_dept_options[d_id]
                                        d_icon = get_dept_icon(d_name)
                                        d_color = get_dept_color(d_id)
                                        with dept_preview:
                                            with ui.card().classes('w-full p-2').style(f'border-left: 3px solid {d_color["bg"]}; background: {d_color["light"]}15;'):
                                                with ui.row().classes('items-center gap-2'):
                                                    with ui.element('div').classes('w-7 h-7 rounded flex items-center justify-center').style(f'background: {d_color["bg"]};'):
                                                        ui.icon(d_icon, size='xs', color='white')
                                                    ui.label(d_name).classes('text-sm font-medium')

                                emp_dept_select.on('update:model-value', lambda e: update_dept_preview())

                                with ui.row().classes('w-full gap-3'):
                                    role_opts = {'employee': 'Employee', 'manager': 'Manager', 'admin': 'Admin', 'superadmin': 'Super Admin'}
                                    role_select = ui.select(role_opts, label='Role', value='employee').props('outlined dense').classes('flex-1')

                                with ui.row().classes('gap-4'):
                                    is_active_check = ui.checkbox('Active', value=True)
                                    is_trusted_check = ui.checkbox('Trusted', value=False)
                                    with ui.element('div').classes('self-center'):
                                        with ui.tooltip():
                                            ui.label('Auto-approves Vacation, Sick, Personal PTO').classes('text-xs')
                                        ui.icon('help_outline', size='xs').classes('opacity-50')

                            # Work Location
                            ui.label('WORK LOCATION').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-3')
                            with ui.column().classes('w-full gap-3 mb-6'):
                                state_opts = {None: 'Select State', 'IL': 'Illinois', 'NY': 'New York', 'CT': 'Connecticut', 'FL': 'Florida'}
                                city_opts = {None: 'Select City'}

                                with ui.row().classes('w-full gap-3'):
                                    state_select = ui.select(state_opts, label='State', value=None).props('outlined dense').classes('flex-1')
                                    city_select = ui.select(city_opts, label='City', value=None).props('outlined dense').classes('flex-1')

                                def update_cities():
                                    st = state_select.value
                                    city_map = {'IL': {'Chicago': 'Chicago'}, 'NY': {'New York': 'New York'}, 'CT': {'Rowayton': 'Rowayton'}, 'FL': {'Boca': 'Boca'}}
                                    city_select.options = {None: 'Select City', **city_map.get(st, {})}
                                    city_select.value = None
                                    city_select.update()

                                state_select.on('update:model-value', lambda e: update_cities())

                            # Remote Work
                            ui.label('REMOTE SCHEDULE').classes('text-xs font-medium uppercase tracking-wide opacity-50 mb-3')
                            with ui.row().classes('w-full gap-4 justify-center'):
                                mon_check = ui.checkbox('Mon')
                                tue_check = ui.checkbox('Tue')
                                wed_check = ui.checkbox('Wed')
                                thu_check = ui.checkbox('Thu')
                                fri_check = ui.checkbox('Fri')

                    # Panel footer
                    with ui.element('div').classes('p-4 border-t'):
                        def create_employee():
                            # Validation
                            missing = []
                            if not first_name_input.value: missing.append('First Name')
                            if not last_name_input.value: missing.append('Last Name')
                            if not username_input.value: missing.append('Username')
                            if not email_input.value: missing.append('Email')
                            if not password_input.value: missing.append('Password')
                            elif len(password_input.value) < 8: missing.append('Password (min 8 chars)')
                            if password_input.value != confirm_password_input.value: missing.append('Passwords must match')
                            if not hire_date_input.value: missing.append('Hire Date')
                            if not emp_dept_select.value: missing.append('Department')
                            if not state_select.value: missing.append('State')
                            if not city_select.value: missing.append('City')

                            if missing:
                                ui.notify(f'Missing: {", ".join(missing)}', type='warning')
                                return

                            try:
                                hire_date = datetime.strptime(hire_date_input.value, '%Y-%m-%d').date()
                            except ValueError:
                                ui.notify('Invalid date format', type='negative')
                                return

                            remote_schedule = {
                                "monday": mon_check.value, "tuesday": tue_check.value, "wednesday": wed_check.value,
                                "thursday": thu_check.value, "friday": fri_check.value
                            }

                            cdb = next(get_db())
                            try:
                                user_data = UserCreate(
                                    username=username_input.value,
                                    password=password_input.value,
                                    email=email_input.value,
                                    first_name=first_name_input.value,
                                    last_name=last_name_input.value,
                                    department_id=emp_dept_select.value,
                                    role=role_select.value,
                                    hire_date=hire_date,
                                    remote_schedule=json.dumps(remote_schedule),
                                    is_active=is_active_check.value,
                                    location_state=state_select.value,
                                    location_city=city_select.value
                                )

                                user_service = UserService(cdb)
                                new_user = user_service.create_user(user_data)

                                # Allocate PTO balance
                                balance_service = BalanceService(cdb)
                                balance_service.allocate_standard_balance(new_user.id)

                                # Set trusted if needed
                                current_user = app.storage.user.get('user', {})
                                if is_trusted_check.value and role_select.value == 'employee':
                                    trust_update = UserUpdate(
                                        is_trusted=True,
                                        trusted_by_id=current_user.get('id'),
                                        trusted_at=datetime.now()
                                    )
                                    user_service.update_user(new_user.id, trust_update)

                                # Audit log
                                AuditService.log_user_create(
                                    cdb, current_user.get('id'),
                                    f"{current_user.get('first_name')} {current_user.get('last_name')}",
                                    new_user.id, new_user.username
                                )

                                panel.close()
                                ui.notify(f'Employee "{new_user.first_name} {new_user.last_name}" created!', type='positive')

                                # Refresh department data
                                nonlocal dept_data
                                dept_data, _ = load_department_data()
                                render_department_rows()

                            except Exception as ex:
                                ui.notify(f'Error: {str(ex)}', type='negative')
                            finally:
                                cdb.close()

                        with ui.row().classes('w-full gap-3'):
                            ui.button('Cancel', on_click=panel.close).props('flat').classes('flex-1')
                            ui.button('Create', icon='person_add', on_click=create_employee).classes('flex-1').style(f'background-color: {TJM_GOLD} !important; color: white !important;')

            panel.open()

        # Initial render
        render_department_rows()

        # Back button
        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-6').style(f'border-color: {TJM_GOLD} !important; color: {TJM_GOLD} !important;')
