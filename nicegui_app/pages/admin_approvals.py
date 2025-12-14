"""Admin page for viewing and approving all pending PTO requests."""
from nicegui import ui, app
from src.database import get_db
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog
from nicegui_app.components.formatting import fmt_days
from src.services.pto_service import PTOService
from src.services.department_service import DepartmentService


def admin_approvals_page():
    """Admin approvals page content."""
    apply_dark_mode()

    current_user = app.storage.general.get('user', {})
    user_role = current_user.get('role')

    if user_role not in ['admin', 'superadmin']:
        ui.label('Access denied - Admin only').classes('text-red-500')
        return

    db = next(get_db())
    try:
        # Get all pending requests
        pending_requests = PTOService.get_pending_requests_with_employee_info(db)

        # Get all departments for filtering
        all_departments = DepartmentService.get_all_departments(db)

        with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
            page_header(title='PENDING PTO APPROVALS', show_back=False)

            if not pending_requests:
                with ui.card().classes('w-full p-6 text-center'):
                    ui.icon('check_circle', color='green').classes('text-4xl mb-2')
                    ui.label('No pending requests').classes('text-lg font-semibold text-green-600')
                    ui.label('All PTO requests have been processed.').classes('text-sm opacity-70')
            else:
                # Track selected requests for bulk actions
                selected_requests = set()

                # Summary
                ui.label(f'{len(pending_requests)} request(s) awaiting approval').classes('text-sm opacity-70 mb-4')

                # Filter and bulk action row
                with ui.row().classes('w-full gap-4 items-end mb-4 flex-wrap'):
                    # Filter by department
                    dept_options = {'all': 'All Departments'}
                    for dept in all_departments:
                        dept_options[dept.id] = dept.name

                    selected_dept = ui.select(
                        options=dept_options,
                        value='all',
                        label='Filter by Department'
                    ).classes('w-64')

                    # Spacer
                    ui.element('div').classes('flex-grow')

                    # Bulk action buttons (hidden until selection)
                    bulk_actions = ui.row().classes('gap-2')
                    bulk_actions.set_visibility(False)

                    with bulk_actions:
                        selection_label = ui.label('0 selected').classes('text-sm opacity-70 mr-2')

                        def bulk_approve():
                            if not selected_requests:
                                show_warning_dialog('No Selection', 'Please select at least one request to approve.')
                                return
                            approve_btn.props('loading disabled')
                            count = len(selected_requests)
                            for req_id in selected_requests:
                                try:
                                    PTOService.approve_request(db, req_id, current_user.get('id'))
                                except Exception:
                                    pass
                            db.commit()
                            ui.notify(f'Approved {count} request(s)', type='positive')
                            ui.navigate.to('/admin/approvals')  # Refresh page

                        def bulk_deny():
                            if not selected_requests:
                                show_warning_dialog('No Selection', 'Please select at least one request to deny.')
                                return
                            # Show denial reason dialog
                            with ui.dialog() as deny_dialog, ui.card().classes('p-4').style('min-width: 350px;'):
                                ui.label(f'Deny {len(selected_requests)} Request(s)').classes('text-lg font-semibold mb-4')
                                reason_input = ui.textarea(label='Denial Reason (optional)').classes('w-full mb-4')

                                def confirm_deny():
                                    deny_confirm_btn.props('loading disabled')
                                    count = len(selected_requests)
                                    reason = reason_input.value or 'Denied via bulk action'
                                    for req_id in selected_requests:
                                        try:
                                            PTOService.deny_request(db, req_id, current_user.get('id'), reason)
                                        except Exception:
                                            pass
                                    db.commit()
                                    deny_dialog.close()
                                    ui.notify(f'Denied {count} request(s)', type='info')
                                    ui.navigate.to('/admin/approvals')  # Refresh page

                                with ui.row().classes('w-full justify-end gap-2'):
                                    ui.button('Cancel', on_click=deny_dialog.close).props('flat')
                                    deny_confirm_btn = ui.button('Deny All', on_click=confirm_deny).props('color=red')

                            deny_dialog.open()

                        approve_btn = ui.button('Approve Selected', icon='check', on_click=bulk_approve).props('color=green')
                        ui.button('Deny Selected', icon='close', on_click=bulk_deny).props('color=red outline')

                # Select all checkbox
                select_all_container = ui.row().classes('w-full items-center gap-2 mb-2')

                # Request list container
                request_container = ui.column().classes('w-full gap-3')

                # Store checkbox references for select all functionality
                checkboxes = {}

                def update_selection_ui():
                    count = len(selected_requests)
                    selection_label.set_text(f'{count} selected')
                    bulk_actions.set_visibility(count > 0)

                def render_requests(filter_dept=None):
                    request_container.clear()
                    select_all_container.clear()
                    selected_requests.clear()
                    checkboxes.clear()
                    update_selection_ui()

                    filtered = pending_requests
                    if filter_dept and filter_dept != 'all':
                        filtered = [r for r in pending_requests if r.get('employee_department_id') == filter_dept]

                    if not filtered:
                        with request_container:
                            with ui.column().classes('w-full items-center py-8'):
                                ui.icon('check_circle', size='3rem', color='green').classes('opacity-50 mb-2')
                                ui.label('No pending requests in this department').classes('opacity-70')
                        return

                    # Select all checkbox
                    with select_all_container:
                        def toggle_all(e):
                            if e.value:
                                for req in filtered:
                                    selected_requests.add(req['request_id'])
                                    if req['request_id'] in checkboxes:
                                        checkboxes[req['request_id']].value = True
                            else:
                                selected_requests.clear()
                                for cb in checkboxes.values():
                                    cb.value = False
                            update_selection_ui()

                        select_all_cb = ui.checkbox('Select All', on_change=toggle_all)
                        ui.label(f'({len(filtered)} requests)').classes('text-sm opacity-60')

                    # Type colors
                    type_colors = {'vacation': 'blue', 'sick': 'green', 'personal': 'purple', 'work_from_home': 'red'}
                    type_icons = {'vacation': 'beach_access', 'sick': 'medical_services', 'personal': 'person', 'work_from_home': 'home_work'}

                    # Pre-compute conflicts
                    pto_service = PTOService(db)
                    request_conflicts = {}
                    for req in filtered:
                        conflicts = pto_service.get_department_conflicts(
                            req['user_id'],
                            req['start_date'],
                            req['end_date'],
                            exclude_request_id=req['request_id']
                        )
                        if conflicts:
                            request_conflicts[req['request_id']] = len(conflicts)

                    with request_container:
                        for req in filtered:
                            pto_type_lower = req['pto_type'].lower()
                            border_color = type_colors.get(pto_type_lower, 'gray')
                            has_conflict = req['request_id'] in request_conflicts

                            with ui.card().classes(f'w-full p-4 border-l-4 border-{border_color}-500'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.row().classes('gap-3 items-center'):
                                        # Checkbox for selection
                                        def make_toggle(req_id):
                                            def toggle(e):
                                                if e.value:
                                                    selected_requests.add(req_id)
                                                else:
                                                    selected_requests.discard(req_id)
                                                update_selection_ui()
                                            return toggle

                                        cb = ui.checkbox(on_change=make_toggle(req['request_id']))
                                        checkboxes[req['request_id']] = cb

                                        ui.icon(type_icons.get(pto_type_lower, 'event')).classes(f'text-{border_color}-500 text-2xl')
                                        with ui.column().classes('gap-1'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(req['employee_name']).classes('font-semibold text-lg')
                                                if req.get('department_name'):
                                                    ui.badge(req['department_name'], color='grey').props('outline')
                                                if has_conflict:
                                                    conflict_count = request_conflicts[req['request_id']]
                                                    ui.icon('warning', color='amber').classes('text-lg').tooltip(
                                                        f'{conflict_count} other team member(s) off on same date(s)'
                                                    )
                                            with ui.row().classes('gap-2 items-center'):
                                                ui.label(req['pto_type'].title()).classes('text-sm')
                                                ui.label('•').classes('text-xs opacity-50')
                                                if req['start_date'] == req['end_date']:
                                                    ui.label(req['start_date'].strftime('%A, %B %d, %Y')).classes('text-sm opacity-70')
                                                else:
                                                    ui.label(f"{req['start_date'].strftime('%A, %B %d')} - {req['end_date'].strftime('%A, %B %d, %Y')}").classes('text-sm opacity-70')
                                                ui.label('•').classes('text-xs opacity-50')
                                                days = float(req['total_days'])
                                                ui.label(f'{fmt_days(days)} days').classes('text-sm font-medium')

                                    ui.button('Review', icon='visibility',
                                             on_click=lambda r=req: ui.navigate.to(f"/manager/request/{r['request_id']}")).props('color=primary')

                # Initial render
                render_requests()

                # Update on filter change
                selected_dept.on('update:model-value', lambda e: render_requests(e.args))

            # Back to Dashboard button
            ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')

    finally:
        db.close()
