"""Admin page for managing employee handbook revisions and policy changes."""
import os
import asyncio
from datetime import datetime, date
from pathlib import Path
from nicegui import ui, app
from src.database import get_db
from src.config import config
from src.logging_config import get_logger
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog, show_success_dialog
from src.services.handbook_revision_service import HandbookRevisionService
from src.services.handbook_analysis_service import HandbookAnalysisService, POLICY_TYPES
from src.services.policy_change_service import PolicyChangeService
from src.models.handbook_upload import HandbookUpload
from src.models.policy_change_log import PolicyChangeLog
from nicegui_app.static.handbook_content import HANDBOOK_CONTENT

logger = get_logger(__name__)

# PTO Central Brand Colors
PTO_GOLD = '#C9A227'

# Upload directory for handbooks
UPLOAD_DIR = 'uploads/handbooks'


def admin_handbook_page():
    """Admin handbook management page with integrated policy change tracking."""
    apply_dark_mode()

    user_role = app.storage.user.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    current_user = app.storage.user.get('user')

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_header(title='HANDBOOK MANAGEMENT', show_back=False)

        # Stats bar at top
        render_stats_bar()

        # Main tabs for different views
        with ui.tabs().classes('w-full') as tabs:
            current_tab = ui.tab('current', label='Current Version', icon='visibility')
            upload_tab = ui.tab('upload', label='Upload & Analyze', icon='cloud_upload')
            policy_tab = ui.tab('policies', label='Policy Changes', icon='policy')
            history_tab = ui.tab('history', label='Version History', icon='history')

        with ui.tab_panels(tabs, value=current_tab).classes('w-full'):
            # Current Version Panel
            with ui.tab_panel(current_tab):
                render_current_version_panel(current_user)

            # Upload & Analyze Panel (NEW - AI-powered)
            with ui.tab_panel(upload_tab):
                render_upload_analyze_panel(current_user)

            # Policy Changes Panel (NEW)
            with ui.tab_panel(policy_tab):
                render_policy_changes_panel(current_user)

            # Version History Panel (Enhanced)
            with ui.tab_panel(history_tab):
                render_version_history_panel(current_user)

        with ui.row().classes('w-full mt-6'):
            ui.button('Back', on_click=go_back, icon='arrow_back').props('outline')


def render_stats_bar():
    """Render summary statistics bar at top of page."""
    db = next(get_db())
    try:
        policy_service = PolicyChangeService(db)
        handbook_service = HandbookRevisionService(db)

        # Get counts
        active_changes = policy_service.get_active_changes()
        latest_handbook = handbook_service.get_active_revision()
        all_versions = policy_service.get_handbook_versions()

        with ui.card().classes('w-full mb-6 p-4').style(f'border-left: 4px solid {PTO_GOLD};'):
            with ui.row().classes('w-full justify-around items-center'):
                # Current Version
                with ui.column().classes('items-center'):
                    ui.icon('menu_book', size='2rem', color='primary')
                    ui.label(f'v{latest_handbook.version}' if latest_handbook else 'Default').classes('text-xl font-bold')
                    ui.label('Current Version').classes('text-xs opacity-60')

                ui.separator().props('vertical').classes('h-16')

                # Active Policy Changes
                with ui.column().classes('items-center'):
                    ui.icon('update', size='2rem', color='green')
                    ui.label(str(len(active_changes))).classes('text-xl font-bold text-green-500')
                    ui.label('Active Changes').classes('text-xs opacity-60')

                ui.separator().props('vertical').classes('h-16')

                # Total Versions
                with ui.column().classes('items-center'):
                    ui.icon('history', size='2rem', color='blue')
                    ui.label(str(len(all_versions))).classes('text-xl font-bold text-blue-500')
                    ui.label('Published Versions').classes('text-xs opacity-60')

                ui.separator().props('vertical').classes('h-16')

                # Pending Analysis
                pending = db.query(HandbookUpload).filter(
                    HandbookUpload.status == 'ready',
                    HandbookUpload.published_at.is_(None)
                ).count()

                with ui.column().classes('items-center'):
                    ui.icon('pending_actions', size='2rem', color='amber' if pending > 0 else 'gray')
                    ui.label(str(pending)).classes(f'text-xl font-bold {"text-amber-500" if pending > 0 else ""}')
                    ui.label('Pending Review').classes('text-xs opacity-60')

    finally:
        db.close()


def render_current_version_panel(current_user):
    """Render the current handbook version panel with section navigation."""
    db = next(get_db())
    try:
        service = HandbookRevisionService(db)
        active = service.get_active_revision()

        content_to_display = active.content if active else HANDBOOK_CONTENT
        version_label = f'Version {active.version}' if active else 'Default Version (May 1, 2024)'
        updated_label = f"Last updated: {active.created_at.strftime('%B %d, %Y at %I:%M %p')}" if active else 'Source: Haventech LLC Employee Handbook'

        # Parse sections from handbook content
        sections = parse_handbook_sections(content_to_display)

        # Section icons mapping
        section_icons = {
            'holidays': 'celebration',
            'vacation': 'beach_access',
            'personal': 'person',
            'sick': 'medical_services',
            'remote': 'home_work',
            'bereavement': 'sentiment_very_dissatisfied',
            'jury': 'gavel',
            'fmla': 'family_restroom',
            'overview': 'info',
            'general': 'description',
            'time off': 'schedule',
            'chicago': 'location_city',
            'state': 'map',
            'family': 'family_restroom',
            'other': 'more_horiz',
        }

        # Short display names for TOC (full titles shown in content area)
        short_names = {
            'Haventech LLC - Time Off Policies': 'Time Off Overview',
            'Chicago Paid Sick and Safe Leave (Any Reason)': 'Chicago Safe Leave',
            'State-Specific Sick Time Policies': 'State Sick Policies',
            'Family and Medical Leave (FMLA)': 'FMLA',
            'Paid Sick Time (Medical Use Only)': 'Medical Sick Time',
            'State Family Leave Laws': 'State Family Leave',
        }

        # State for selected section - default to first section
        first_section = sections[0] if sections else None
        selected_section = {'value': first_section['title'] if first_section else None}
        content_display = {'element': None}

        # Header card with version info
        with ui.card().classes('w-full p-4 mb-4'):
            with ui.row().classes('justify-between items-center'):
                with ui.column():
                    ui.label(version_label).classes('text-lg font-bold')
                    ui.label(updated_label).classes('text-sm opacity-70')
                    ui.label(f'{len(content_to_display):,} characters • {len(sections)} sections').classes('text-sm opacity-70')
                ui.badge('Active', color='green')

            if active and active.change_summary:
                with ui.card().classes('w-full mt-4 p-3 border-l-4 border-blue-500'):
                    ui.label('Change Summary').classes('font-semibold text-sm')
                    ui.label(active.change_summary).classes('text-sm')

        # Main content area with sidebar navigation - equal heights, no scrolling
        with ui.row().classes('w-full gap-4 items-start'):
            # Left sidebar - Table of Contents (NO scroll - all sections visible)
            with ui.card().classes('p-4').style('width: 260px; min-width: 260px;'):
                ui.label('Table of Contents').classes('text-lg font-bold mb-3')

                # Search input
                search_input = ui.input(
                    placeholder='Search sections...',
                    on_change=lambda e: filter_sections(e.value)
                ).classes('w-full mb-3').props('dense outlined')

                # Section list container - NO scroll, all visible
                section_list = ui.column().classes('w-full gap-2')

                def filter_sections(query):
                    """Filter sections based on search query."""
                    section_list.clear()
                    with section_list:
                        render_section_list(sections, query, selected_section, content_display, section_icons, short_names)

                def render_section_list(sections, query, selected_section, content_display, icons, names):
                    """Render the section list with optional filtering."""
                    query_lower = (query or '').lower()
                    for section in sections:
                        if query_lower and query_lower not in section['title'].lower():
                            continue

                        # Determine icon
                        icon_name = 'description'
                        title_lower = section['title'].lower()
                        for key, icon in icons.items():
                            if key in title_lower:
                                icon_name = icon
                                break

                        is_selected = selected_section['value'] == section['title']

                        # Get short display name or use original
                        display_name = names.get(section['title'], section['title'])

                        def create_click_handler(sec):
                            def handler():
                                selected_section['value'] = sec['title']
                                update_content_display(sec, content_display)
                                # Refresh the list to show selection
                                filter_sections(search_input.value)
                            return handler

                        # Tile-style card for each section - TJM Gold accent
                        tile_style = f'border: 2px solid {PTO_GOLD}; background: rgba(201,162,39,0.15);' if is_selected else 'border: 1px solid rgba(255,255,255,0.1);'
                        with ui.card().classes('w-full cursor-pointer p-2').style(tile_style).on('click', create_click_handler(section)):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon(icon_name, size='sm').style(f'color: {PTO_GOLD};' if is_selected else 'color: gray;')
                                ui.label(display_name).classes('text-sm').style(
                                    f'color: {PTO_GOLD}; font-weight: 600;' if is_selected else ''
                                )

                # Initial render
                with section_list:
                    render_section_list(sections, '', selected_section, content_display, section_icons, short_names)

            # Right content area - tall, matches TOC
            with ui.column().classes('flex-1'):
                # Content display card - NO internal scroll constraint
                content_display['element'] = ui.card().classes('w-full p-6')

                # Initial state - show first section by default
                if first_section:
                    update_content_display(first_section, content_display)

        # View full handbook button
        def show_full_handbook():
            with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl max-h-screen'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Employee Handbook').classes('text-xl font-bold')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                with ui.scroll_area().classes('w-full').style('height: 70vh'):
                    ui.markdown(content_to_display).classes('text-sm')
            dialog.open()

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('View Full Handbook', icon='menu_book', on_click=show_full_handbook).props('outline')

    finally:
        db.close()


def parse_handbook_sections(content: str) -> list:
    """Parse handbook content into sections based on markdown headers."""
    import re

    sections = []
    current_section = None
    current_content = []

    lines = content.split('\n')

    for line in lines:
        # Match markdown headers (# or ##)
        header_match = re.match(r'^(#{1,2})\s+(.+)$', line.strip())

        if header_match:
            # Save previous section
            if current_section:
                sections.append({
                    'title': current_section,
                    'content': '\n'.join(current_content).strip()
                })

            current_section = header_match.group(2).strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    # Don't forget the last section
    if current_section:
        sections.append({
            'title': current_section,
            'content': '\n'.join(current_content).strip()
        })

    # If no sections found, create one from the whole content
    if not sections:
        sections.append({
            'title': 'Handbook Content',
            'content': content
        })

    return sections


def update_content_display(section: dict, content_display: dict):
    """Update the content display area with selected section."""
    content_display['element'].clear()

    # Section icons mapping
    section_icons = {
        'holidays': 'celebration',
        'vacation': 'beach_access',
        'personal': 'person',
        'sick': 'medical_services',
        'remote': 'home_work',
        'bereavement': 'sentiment_very_dissatisfied',
        'jury': 'gavel',
        'fmla': 'family_restroom',
        'overview': 'info',
        'general': 'description',
    }

    # Determine icon
    icon_name = 'description'
    title_lower = section['title'].lower()
    for key, icon in section_icons.items():
        if key in title_lower:
            icon_name = icon
            break

    with content_display['element']:
        # Header with TJM Gold accent
        with ui.card().classes('w-full mb-4 p-4').style(f'border-left: 4px solid {PTO_GOLD}; background: rgba(201,162,39,0.1);'):
            with ui.row().classes('items-center gap-3'):
                ui.icon(icon_name, size='lg').style(f'color: {PTO_GOLD};')
                ui.label(section['title']).classes('text-xl font-bold').style(f'color: {PTO_GOLD};')

        # Content area - NO height constraint, shows full content
        with ui.card().classes('w-full p-4'):
            ui.markdown(section['content']).classes('text-sm handbook-content')

        # Footer with section info
        with ui.row().classes('w-full justify-between items-center mt-4 opacity-60'):
            ui.label(f'{len(section["content"]):,} characters').classes('text-xs')
            ui.label(f'{len(section["content"].split())} words').classes('text-xs')


def render_upload_analyze_panel(current_user):
    """Render the upload and AI analysis panel."""
    # State containers
    analysis_container = {'element': None}
    current_upload = {'data': None}

    with ui.card().classes('w-full mb-6').style(f'border-left: 4px solid {PTO_GOLD};'):
        with ui.card_section().classes('p-6'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('smart_toy', size='2rem', color='primary')
                ui.label('AI-Powered Handbook Analysis').classes('text-xl font-bold')

            ui.label(
                'Upload a new handbook document and let AI automatically detect policy changes. '
                'The system will extract policy values, compare to current settings, and generate '
                'friendly summaries for employees.'
            ).classes('opacity-70 mb-6')

            # File upload area
            async def handle_upload(e):
                if not e.content:
                    return

                # Save uploaded file
                filename = e.name
                file_path = os.path.join(UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")

                with open(file_path, 'wb') as f:
                    f.write(e.content.read())

                # Show analyzing state
                with analysis_container['element']:
                    analysis_container['element'].clear()
                    with ui.card().classes('w-full p-6').style('border-left: 4px solid #3b82f6;'):
                        with ui.row().classes('items-center gap-4'):
                            ui.spinner(size='xl', color='primary')
                            with ui.column():
                                ui.label('Analyzing with Claude AI...').classes('text-lg font-semibold')
                                ui.label('Extracting policy values and detecting changes').classes('opacity-70')

                # Perform analysis
                db = next(get_db())
                try:
                    service = HandbookAnalysisService(db)
                    upload, changes = await service.analyze_handbook(
                        file_path=file_path,
                        filename=filename,
                        uploaded_by=current_user['id']
                    )
                    current_upload['data'] = upload

                    # Render analysis results
                    render_analysis_results(analysis_container, upload, changes, current_user)

                except Exception as ex:
                    with analysis_container['element']:
                        analysis_container['element'].clear()
                        with ui.card().classes('w-full p-6').style('border-left: 4px solid #ef4444;'):
                            with ui.row().classes('items-center gap-3 mb-3'):
                                ui.icon('error', color='red', size='lg')
                                ui.label('Analysis Error').classes('text-lg font-bold text-red-400')
                            ui.label(str(ex)).classes('opacity-80')
                finally:
                    db.close()

            with ui.column().classes('w-full items-center gap-4'):
                with ui.card().classes('w-full p-8 border-2 border-dashed').style('border-color: rgba(201,162,39,0.5);'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('cloud_upload', size='3rem', color='primary')
                        ui.upload(
                            label='Drop handbook here or click to browse',
                            on_upload=handle_upload,
                            auto_upload=True
                        ).classes('w-full max-w-md').props('accept=".pdf,.docx,.doc,.txt"')
                        ui.label('Supported formats: PDF, DOCX, TXT').classes('text-xs opacity-60')

    # Analysis results container
    analysis_container['element'] = ui.column().classes('w-full')

    # Check for pending uploads
    db = next(get_db())
    try:
        pending = db.query(HandbookUpload).filter(
            HandbookUpload.status == 'ready',
            HandbookUpload.published_at.is_(None)
        ).order_by(HandbookUpload.uploaded_at.desc()).first()

        if pending:
            current_upload['data'] = pending
            changes = pending.extracted_policies.get('changes', []) if pending.extracted_policies else []
            render_analysis_results(analysis_container, pending, changes, current_user)
    finally:
        db.close()


def render_analysis_results(container, upload: HandbookUpload, changes: list, user: dict):
    """Render the AI analysis results with full UI."""
    with container['element']:
        container['element'].clear()

        # Revert detection alert
        if upload.detected_duplicate_of:
            with ui.card().classes('w-full mb-4 p-6').style('border-left: 4px solid #f59e0b; background: rgba(245,158,11,0.1);'):
                with ui.row().classes('items-center gap-3 mb-4'):
                    ui.icon('restore', color='amber', size='lg')
                    ui.label('Previous Version Detected!').classes('text-xl font-bold text-amber-400')

                ui.label(
                    f'This handbook matches a previously uploaded version ({upload.detected_duplicate_of}). '
                    f'If you proceed, this will revert all policy changes back to that version.'
                ).classes('mb-4')

                with ui.row().classes('gap-4'):
                    async def do_revert():
                        db = next(get_db())
                        try:
                            service = HandbookAnalysisService(db)
                            revert_upload, logs = service.revert_to_version(
                                target_version=upload.detected_duplicate_of,
                                admin_id=user['id']
                            )
                            show_success_dialog('Revert Complete', f'Reverted to {upload.detected_duplicate_of} successfully!', on_close=lambda: ui.navigate.to('/admin/handbook'))
                        except Exception as ex:
                            show_error_dialog('Revert Error', str(ex))
                        finally:
                            db.close()

                    ui.button('Confirm Revert', on_click=lambda: asyncio.create_task(do_revert()), color='amber').props('icon=restore')
                    ui.button('Cancel', on_click=lambda: ui.navigate.to('/admin/handbook')).props('flat')

        # Main analysis results
        with ui.card().classes('w-full p-6').style('border-left: 4px solid #22c55e;'):
            # Header
            with ui.row().classes('items-center justify-between mb-6'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('smart_toy', color='green', size='lg')
                    ui.label('AI Analysis Complete').classes('text-xl font-bold')
                with ui.row().classes('items-center gap-2'):
                    ui.badge(f'{upload.version}', color='green')
                    status_color = {'ready': 'blue', 'published': 'green', 'error': 'red'}.get(upload.status, 'gray')
                    ui.badge(upload.status.upper(), color=status_color)

            # AI Summary
            if upload.ai_summary:
                with ui.card().classes('w-full p-4 mb-6').style('background: rgba(34,197,94,0.1);'):
                    with ui.row().classes('items-start gap-3'):
                        ui.icon('lightbulb', color='green')
                        ui.label(upload.ai_summary).classes('italic')

            # Changes section
            if changes:
                ui.label(f'Detected {len(changes)} Policy Change(s)').classes('text-lg font-semibold mb-4')

                for i, change in enumerate(changes):
                    policy_name = POLICY_TYPES.get(
                        change['policy_type'], {}
                    ).get('name', change['policy_type'].replace('_', ' ').title())

                    is_new = change.get('is_new', False)

                    with ui.card().classes('w-full mb-3 p-4').style(
                        f'border-left: 4px solid {"#3b82f6" if is_new else "#22c55e"};'
                    ):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('gap-2 flex-1'):
                                # Policy name with badge
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(
                                        'add_circle' if is_new else 'change_circle',
                                        color='blue' if is_new else 'green'
                                    )
                                    ui.label(policy_name).classes('font-semibold text-lg')
                                    if is_new:
                                        ui.badge('NEW', color='blue')

                                # Location scope
                                location_parts = []
                                if change.get('location_city'):
                                    location_parts.append(change['location_city'])
                                if change.get('location_state'):
                                    location_parts.append(change['location_state'])

                                if location_parts:
                                    ui.label(f'Affects: {", ".join(location_parts)} employees').classes('text-sm opacity-60')
                                else:
                                    ui.label('Affects: All employees').classes('text-sm opacity-60')

                                # AI Summary for this change
                                if change.get('ai_summary'):
                                    with ui.card().classes('mt-2 p-3').style('background: rgba(34,197,94,0.1);'):
                                        ui.label(change['ai_summary']).classes('text-sm')

                            # Value change display
                            with ui.column().classes('items-end gap-1'):
                                if not is_new:
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(change['old_value_display']).classes('line-through opacity-50')
                                        ui.icon('arrow_forward', size='xs', color='gray')
                                        ui.label(change['new_value_display']).classes('font-bold text-lg text-green-400')
                                else:
                                    ui.label(change['new_value_display']).classes('font-bold text-lg text-blue-400')

            else:
                with ui.card().classes('w-full p-6 text-center'):
                    ui.icon('check_circle', size='3rem', color='green')
                    ui.label('No Policy Changes Detected').classes('text-lg font-semibold mt-2')
                    ui.label('The uploaded handbook has the same policy values as current settings.').classes('opacity-70')

            # Action buttons
            if changes and upload.status == 'ready':
                ui.separator().classes('my-6')

                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Ready to publish these changes to all employees?').classes('opacity-70')

                    with ui.row().classes('gap-4'):
                        async def publish_changes():
                            db = next(get_db())
                            try:
                                service = HandbookAnalysisService(db)
                                logs = service.publish_handbook(
                                    upload_id=upload.id,
                                    admin_id=user['id'],
                                    effective_date=date.today()
                                )
                                show_success_dialog('Changes Published', f'Published {len(logs)} policy changes successfully!', on_close=lambda: ui.navigate.to('/admin/handbook'))
                            except Exception as ex:
                                show_error_dialog('Publish Error', str(ex))
                            finally:
                                db.close()

                        def discard_upload():
                            db = next(get_db())
                            try:
                                record = db.query(HandbookUpload).filter_by(id=upload.id).first()
                                if record and record.status != 'published':
                                    db.delete(record)
                                    db.commit()
                                ui.navigate.to('/admin/handbook')
                            finally:
                                db.close()

                        ui.button('Discard', on_click=discard_upload).props('flat color=red icon=delete')
                        ui.button(
                            'Publish Changes',
                            on_click=lambda: asyncio.create_task(publish_changes()),
                            color='green'
                        ).props('icon=publish')

            elif upload.status == 'published':
                with ui.row().classes('items-center gap-2 mt-4'):
                    ui.icon('check_circle', color='green')
                    ui.label(f'Published on {upload.published_at.strftime("%B %d, %Y at %I:%M %p")}').classes('text-green-400')


def render_policy_changes_panel(current_user):
    """Render the active policy changes panel."""
    db = next(get_db())
    try:
        policy_service = PolicyChangeService(db)
        active_changes = policy_service.get_active_changes()

        with ui.card().classes('w-full p-6 mb-6').style(f'border-left: 4px solid {PTO_GOLD};'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('visibility', size='2rem', color='primary')
                ui.label('Active Policy Change Indicators').classes('text-xl font-bold')

            ui.label(
                'These policy changes are currently visible to employees. '
                'Change indicators (badges, tooltips) automatically expire after 30 days.'
            ).classes('opacity-70')

        if not active_changes:
            with ui.card().classes('w-full p-8 text-center'):
                ui.icon('check_circle_outline', size='4rem', color='gray')
                ui.label('No Active Changes').classes('text-xl font-semibold mt-4 opacity-70')
                ui.label('All policy indicators have expired or none have been published.').classes('text-sm opacity-50')
        else:
            # Group changes by handbook version
            by_version = {}
            for change in active_changes:
                ver = change.handbook_version
                if ver not in by_version:
                    by_version[ver] = []
                by_version[ver].append(change)

            for version, changes in by_version.items():
                with ui.card().classes('w-full mb-4').style('border-left: 4px solid #22c55e;'):
                    with ui.expansion(f'Version {version} - {len(changes)} change(s)').classes('w-full'):
                        for change in changes:
                            policy_name = policy_service.format_policy_type_name(change.policy_type)
                            days_left = (change.expires_at - datetime.utcnow()).days

                            with ui.card().classes('w-full mb-2 p-4'):
                                with ui.row().classes('w-full justify-between items-start'):
                                    with ui.column().classes('gap-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(policy_name).classes('font-semibold')
                                            if change.is_revert:
                                                ui.badge('REVERTED', color='orange')
                                            else:
                                                ui.badge('UPDATED', color='green')

                                        ui.label(f'Effective: {change.effective_date.strftime("%B %d, %Y")}').classes('text-sm opacity-60')

                                        if change.ai_summary:
                                            ui.label(change.ai_summary).classes('text-sm mt-2 italic')

                                    with ui.column().classes('items-end gap-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(change.old_value_display).classes('line-through opacity-50')
                                            ui.icon('arrow_forward', size='xs')
                                            ui.label(change.new_value_display).classes('font-bold text-green-400')

                                        # Days remaining indicator (days until change expires, not PTO days)
                                        if days_left <= 7:
                                            ui.label(f'{days_left}d left').classes('text-xs text-amber-400')
                                        else:
                                            ui.label(f'{days_left}d left').classes('text-xs opacity-50')

    finally:
        db.close()


def render_version_history_panel(current_user):
    """Render the version history panel with revert capability."""
    db = next(get_db())
    try:
        policy_service = PolicyChangeService(db)
        handbook_service = HandbookRevisionService(db)

        # Get handbook uploads (policy versions)
        policy_versions = policy_service.get_handbook_versions()

        # Get handbook revisions (content versions)
        content_revisions = handbook_service.get_all_revisions()

        with ui.card().classes('w-full p-6 mb-6').style(f'border-left: 4px solid {PTO_GOLD};'):
            with ui.row().classes('items-center gap-3 mb-4'):
                ui.icon('history', size='2rem', color='primary')
                ui.label('Version History').classes('text-xl font-bold')

            ui.label(
                'Complete history of handbook versions with ability to revert to previous policy values.'
            ).classes('opacity-70')

        # Policy Versions Section
        ui.label('Policy Versions').classes('text-lg font-semibold mb-3')

        if not policy_versions:
            with ui.card().classes('w-full p-6 text-center mb-6'):
                ui.icon('info', size='2rem', color='gray')
                ui.label('No policy versions published yet').classes('opacity-70 mt-2')
                ui.label('Upload and analyze a handbook to create the first version.').classes('text-sm opacity-50')
        else:
            for i, version in enumerate(policy_versions):
                is_current = i == 0

                with ui.card().classes('w-full mb-3 p-4').style(
                    f'border-left: 4px solid {"#22c55e" if is_current else "#6b7280"};'
                ):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.column().classes('gap-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(version.version).classes('font-bold text-lg')
                                if is_current:
                                    ui.badge('Current', color='green')
                                if version.is_revert_of:
                                    ui.badge('Revert', color='orange')

                            ui.label(
                                f'Published {version.published_at.strftime("%B %d, %Y at %I:%M %p")}'
                            ).classes('text-sm opacity-70')

                            if version.ai_summary:
                                ui.label(version.ai_summary[:100] + ('...' if len(version.ai_summary) > 100 else '')).classes('text-sm opacity-60 mt-1')

                            # Show change count
                            if version.extracted_policies:
                                change_count = version.extracted_policies.get('change_count', 0)
                                ui.label(f'{change_count} policy change(s)').classes('text-xs opacity-50')

                        # Revert button (not for current version)
                        if not is_current:
                            def create_revert_handler(v):
                                def handler():
                                    confirm_revert_dialog(v, current_user)
                                return handler

                            ui.button(
                                'Revert to this',
                                on_click=create_revert_handler(version)
                            ).props('flat color=amber size=sm icon=restore')

        # Content Revisions Section
        ui.separator().classes('my-6')
        ui.label('Content Revisions').classes('text-lg font-semibold mb-3')

        if not content_revisions:
            with ui.card().classes('w-full p-6 text-center'):
                ui.label('No content revisions yet').classes('opacity-70')
        else:
            for rev in content_revisions[:10]:  # Show last 10
                with ui.card().classes('w-full mb-2 p-3'):
                    with ui.row().classes('justify-between items-center'):
                        with ui.column().classes('gap-1'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label(f'Version {rev.version}').classes('font-medium')
                                if rev.is_active:
                                    ui.badge('Active', color='green')
                            ui.label(f"Created: {rev.created_at.strftime('%Y-%m-%d %H:%M')}").classes('text-xs opacity-70')
                        if rev.change_summary:
                            ui.label(rev.change_summary[:50] + '...').classes('text-sm opacity-60')

    finally:
        db.close()


def confirm_revert_dialog(version: HandbookUpload, user: dict):
    """Show confirmation dialog before reverting to a previous version."""
    with ui.dialog() as dialog, ui.card().classes('p-6').style('min-width: 450px;'):
        with ui.row().classes('items-center gap-3 mb-4'):
            ui.icon('restore', color='amber', size='lg')
            ui.label('Confirm Revert').classes('text-xl font-bold')

        ui.label(f'Are you sure you want to revert to version {version.version}?').classes('mb-2')

        with ui.card().classes('w-full p-4 mb-4').style('background: rgba(245,158,11,0.1);'):
            ui.label('This will:').classes('font-semibold mb-2')
            with ui.column().classes('gap-1'):
                ui.label('• Create new policy change entries marked as "reverted"').classes('text-sm')
                ui.label('• Show revert indicators to employees for 30 days').classes('text-sm')
                ui.label('• Restore policy values from the selected version').classes('text-sm')

        with ui.row().classes('w-full justify-end gap-4'):
            ui.button('Cancel', on_click=dialog.close).props('flat')

            async def do_revert():
                dialog.close()
                db = next(get_db())
                try:
                    service = HandbookAnalysisService(db)
                    revert_upload, logs = service.revert_to_version(
                        target_version=version.version,
                        admin_id=user['id']
                    )
                    show_success_dialog('Revert Complete', f'Reverted to {version.version} with {len(logs)} changes', on_close=lambda: ui.navigate.to('/admin/handbook'))
                except Exception as ex:
                    show_error_dialog('Revert Error', str(ex))
                finally:
                    db.close()

            ui.button(
                'Confirm Revert',
                on_click=lambda: asyncio.create_task(do_revert()),
                color='amber'
            ).props('icon=restore')

    dialog.open()
