"""Policy & Formula Reference Viewer for System Administration."""
from nicegui import ui, app
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, create_help_button, show_help_dialog, PTO_GOLD, PTO_GRAY
from src.services.policy_engine import PolicyEngine, PolicySection, PolicyHelp


def admin_policy_viewer_page():
    """Policy & Formula Reference page for superadmins."""
    apply_dark_mode()

    # Add custom CSS for the policy viewer
    ui.add_head_html(f'''
    <style>
        .policy-section {{
            transition: all 0.2s ease;
        }}
        .policy-section:hover {{
            border-color: {PTO_GOLD} !important;
        }}
        .formula-box {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(0, 0, 0, 0.3);
            border-left: 3px solid {PTO_GOLD};
            padding: 12px 16px;
            border-radius: 6px;
            margin: 8px 0;
        }}
        .policy-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .policy-table th {{
            background: linear-gradient(135deg, {PTO_GRAY} 0%, #4a5a62 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        .policy-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .policy-table tbody tr:hover {{
            background: rgba(201, 162, 39, 0.1);
        }}
        .flow-step {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 0;
        }}
        .flow-step-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: {PTO_GOLD};
            flex-shrink: 0;
        }}
        .flow-step-line {{
            width: 2px;
            height: 30px;
            background: rgba(201, 162, 39, 0.3);
            margin-left: 5px;
        }}
        .rule-item {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 6px 0;
        }}
        .rule-check {{
            color: #22c55e;
            flex-shrink: 0;
        }}
        .section-header {{
            border-bottom: 2px solid {PTO_GOLD};
            padding-bottom: 8px;
            margin-bottom: 16px;
        }}
    </style>
    ''')

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role != 'superadmin':
        ui.label('Access Denied - Superadmin role required').classes('text-red-500 text-xl')
        ui.navigate.to('/')
        return

    policy_engine = PolicyEngine()
    sections = policy_engine.get_policy_documentation()

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header
        page_header(title='POLICY & FORMULA REFERENCE', show_back=True)

        # Subtitle
        with ui.row().classes('w-full items-center gap-2 mb-4'):
            ui.icon('menu_book', size='sm', color='amber')
            ui.label('Comprehensive reference for all PTO policies, formulas, and business rules.').classes('text-sm opacity-70')

        # Quick actions bar
        with ui.card().classes('w-full p-3 mb-4').style(f'background: linear-gradient(135deg, #1E2328 0%, #2a3036 100%); border-bottom: 2px solid {PTO_GOLD};'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('verified', color='amber')
                    ui.label('Policy Engine v1.0').classes('font-semibold')
                    ui.badge(f'{len(sections)} sections', color='amber').props('dense')

                with ui.row().classes('gap-2'):
                    expand_all_btn = ui.button('Expand All', icon='unfold_more', on_click=lambda: toggle_all(True)).props('flat dense')
                    collapse_all_btn = ui.button('Collapse All', icon='unfold_less', on_click=lambda: toggle_all(False)).props('flat dense')

        # Track expansion panels for expand/collapse all
        expansion_panels = []

        def toggle_all(expand: bool):
            """Toggle all expansion panels."""
            for panel in expansion_panels:
                if expand:
                    panel.open()
                else:
                    panel.close()

        # Render each policy section as an expansion panel
        for section in sections:
            with ui.expansion(text='', value=False).classes('w-full policy-section mb-2').style('border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; overflow: hidden;') as panel:
                expansion_panels.append(panel)

                # Custom header slot
                with panel.add_slot('header'):
                    with ui.row().classes('w-full items-center gap-3 py-1'):
                        ui.icon(section.icon, size='md', color='amber')
                        ui.label(section.title).classes('text-lg font-semibold')

                # Section content
                with ui.column().classes('w-full gap-4 p-2'):
                    render_section_content(section)

                    # Help items at the bottom (no title)
                    if section.help_items:
                        ui.separator().classes('my-4')
                        for help_item in section.help_items:
                            render_help_item(help_item)


def render_section_content(section: PolicySection):
    """Render the content items for a policy section."""
    for item in section.content:
        content_type = item.get('type')

        if content_type == 'formula':
            render_formula(item)
        elif content_type == 'table':
            render_table(item)
        elif content_type == 'flow':
            render_flow(item)
        elif content_type == 'rules':
            render_rules(item)
        elif content_type == 'list':
            render_list(item)
        elif content_type == 'note':
            render_note(item)
        elif content_type == 'heading':
            render_heading(item)


def render_formula(item: dict):
    """Render a formula display box."""
    with ui.column().classes('w-full gap-1'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('functions', size='xs', color='amber')
            ui.label(item.get('label', 'Formula')).classes('font-semibold text-sm')

        with ui.element('div').classes('formula-box'):
            ui.label(item.get('formula', '')).classes('text-sm')

        if item.get('description'):
            ui.label(item['description']).classes('text-xs opacity-60 ml-4')


def render_table(item: dict):
    """Render a policy table."""
    headers = item.get('headers', [])
    rows = item.get('rows', [])

    with ui.element('div').classes('w-full overflow-x-auto rounded-lg').style('background: rgba(0,0,0,0.2);'):
        with ui.element('table').classes('policy-table'):
            with ui.element('thead'):
                with ui.element('tr'):
                    for header in headers:
                        with ui.element('th'):
                            ui.label(header)

            with ui.element('tbody'):
                for row in rows:
                    with ui.element('tr'):
                        for cell in row:
                            with ui.element('td'):
                                ui.label(cell).classes('text-sm')


def render_flow(item: dict):
    """Render a flow/process diagram."""
    steps = item.get('steps', [])

    with ui.column().classes('w-full gap-0 ml-2'):
        for i, step in enumerate(steps):
            with ui.column().classes('gap-0'):
                with ui.element('div').classes('flow-step'):
                    ui.element('div').classes('flow-step-dot')
                    with ui.column().classes('gap-0'):
                        ui.label(step.get('label', '')).classes('font-semibold text-sm')
                        if step.get('description'):
                            ui.label(step['description']).classes('text-xs opacity-60')

                # Add connecting line except for last step
                if i < len(steps) - 1:
                    ui.element('div').classes('flow-step-line')


def render_rules(item: dict):
    """Render a rules/requirements list."""
    title = item.get('title', 'Rules')
    rules = item.get('items', [])

    with ui.column().classes('w-full gap-2'):
        ui.label(title).classes('font-semibold text-sm mb-1')

        for rule in rules:
            with ui.element('div').classes('rule-item'):
                ui.icon('check_circle', size='xs').classes('rule-check')
                ui.label(rule).classes('text-sm')


def render_list(item: dict):
    """Render a simple list."""
    title = item.get('title', '')
    items = item.get('items', [])

    with ui.column().classes('w-full gap-2'):
        if title:
            ui.label(title).classes('font-semibold text-sm mb-1')

        with ui.row().classes('flex-wrap gap-2'):
            for list_item in items:
                ui.badge(list_item.replace('_', ' ').title(), color='gray').props('outline')


def render_note(item: dict):
    """Render a note/callout box."""
    text = item.get('text', '')

    with ui.element('div').classes('w-full p-3 rounded-lg').style('background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b;'):
        with ui.row().classes('items-start gap-2'):
            ui.icon('info', size='xs', color='amber')
            ui.label(text).classes('text-sm')


def render_heading(item: dict):
    """Render a section heading."""
    text = item.get('text', '')

    with ui.row().classes('items-center gap-2 mt-4 mb-2 section-header'):
        ui.label(text).classes('font-bold text-base')


def render_help_item(help_item: PolicyHelp):
    """Render a help/tip item as a clickable card."""

    def show_full_help():
        """Show the full help dialog."""
        content = f'''
        <div style="margin-bottom: 16px;">
            <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">In Plain English</p>
            <p style="margin: 0;">{help_item.plain_english}</p>
        </div>
        <div style="margin-bottom: 16px;">
            <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Why This Exists</p>
            <p style="margin: 0;">{help_item.business_reason}</p>
        </div>
        <div style="margin-bottom: 16px;">
            <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Example</p>
            <p style="margin: 0; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 6px; font-style: italic;">{help_item.example}</p>
        </div>
        '''
        if help_item.related_rules:
            related = ', '.join(help_item.related_rules)
            content += f'''
            <div>
                <p style="color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Related Topics</p>
                <p style="margin: 0;">{related}</p>
            </div>
            '''
        show_help_dialog(help_item.title, content)

    with ui.card().classes('w-full p-3 cursor-pointer hover:shadow-lg transition-all').style('background: rgba(201, 162, 39, 0.05); border: 1px solid rgba(201, 162, 39, 0.2);').on('click', show_full_help):
        with ui.row().classes('items-center gap-2'):
            ui.icon('help_outline', size='xs', color='amber')
            ui.label(help_item.title).classes('font-semibold text-sm')
            ui.icon('chevron_right', size='xs').classes('ml-auto opacity-50')

        ui.label(help_item.plain_english).classes('text-xs opacity-70 mt-1 line-clamp-2')
