"""Admin page for managing employee handbook revisions."""
from datetime import datetime
from pathlib import Path
from nicegui import ui, app
from src.database import get_db
from src.config import config
from src.logging_config import get_logger
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode, show_warning_dialog, show_error_dialog
from src.services.handbook_revision_service import HandbookRevisionService
from nicegui_app.static.handbook_content import HANDBOOK_CONTENT

logger = get_logger(__name__)


def admin_handbook_page():
    """Admin handbook management page content."""
    apply_dark_mode()

    user_role = app.storage.general.get('user', {}).get('role')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/')
        return

    current_user = app.storage.general.get('user')

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_header(title='HANDBOOK MANAGEMENT', show_back=False)

        # Tabs for different views
        with ui.tabs().classes('w-full') as tabs:
            current_tab = ui.tab('current', label='Current Version', icon='visibility')
            update_tab = ui.tab('update', label='Update Handbook', icon='edit')
            history_tab = ui.tab('history', label='Revision History', icon='history')

        with ui.tab_panels(tabs, value=current_tab).classes('w-full'):
            # Current Version Panel
            with ui.tab_panel(current_tab):
                db = next(get_db())
                try:
                    service = HandbookRevisionService(db)
                    active = service.get_active_revision()

                    content_to_display = active.content if active else HANDBOOK_CONTENT
                    version_label = f'Version {active.version}' if active else 'Default Version (May 1, 2024)'
                    updated_label = f"Last updated: {active.created_at.strftime('%B %d, %Y at %I:%M %p')}" if active else 'Source: Haventech LLC Employee Handbook'

                    with ui.card().classes('w-full p-4 mb-4'):
                        with ui.row().classes('justify-between items-center'):
                            with ui.column():
                                ui.label(version_label).classes('text-lg font-bold')
                                ui.label(updated_label).classes('text-sm opacity-70')
                                ui.label(f'{len(content_to_display):,} characters').classes('text-sm opacity-70')
                            ui.badge('Active', color='green')

                        if active and active.change_summary:
                            with ui.card().classes('w-full mt-4 p-3 border-l-4 border-blue-500'):
                                ui.label('Change Summary').classes('font-semibold text-sm')
                                ui.label(active.change_summary).classes('text-sm')

                    with ui.card().classes('w-full p-4'):
                        ui.label('Content Preview').classes('font-semibold mb-2')
                        preview_text = content_to_display[:1500] + '...' if len(content_to_display) > 1500 else content_to_display
                        ui.markdown(preview_text).classes('text-sm')

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

            # Update Handbook Panel
            with ui.tab_panel(update_tab):
                preview_state = {'report': None, 'new_content': None, 'backup_file': None}

                with ui.card().classes('w-full p-4 mb-4 border-2 border-dashed border-blue-400'):
                    ui.label('Upload New Handbook PDF').classes('text-lg font-bold mb-2')
                    ui.label('Upload a PDF file to extract and validate handbook content.').classes('text-sm opacity-70 mb-4')

                    validation_container = ui.column().classes('w-full')
                    validation_container.set_visibility(False)

                    REQUIRED_SECTIONS = [
                        ('holidays', ['holiday', 'holidays', 'market holiday']),
                        ('vacation', ['vacation', 'vacation policy', 'annual vacation']),
                        ('personal', ['personal day', 'personal days']),
                        ('sick', ['sick time', 'sick leave', 'paid sick']),
                    ]

                    OPTIONAL_SECTIONS = [
                        ('fmla', ['fmla', 'family and medical leave']),
                        ('bereavement', ['bereavement']),
                        ('jury duty', ['jury duty']),
                        ('remote work', ['remote work', 'work from home']),
                    ]

                    # Get handbook directory path
                    handbook_dir = Path(__file__).parent.parent.parent / 'handbook'

                    async def handle_pdf_upload(e):
                        if not e.content:
                            show_warning_dialog('No File', 'Please select a PDF file to upload.')
                            return

                        try:
                            import io
                            import hashlib
                            from pypdf import PdfReader

                            pdf_bytes = e.content.read()
                            file_hash = hashlib.md5(pdf_bytes).hexdigest()

                            handbook_dir.mkdir(exist_ok=True)

                            duplicate_found = None
                            for subfolder in handbook_dir.iterdir():
                                if subfolder.is_dir():
                                    for pdf_file in subfolder.glob('*.pdf'):
                                        existing_hash = hashlib.md5(pdf_file.read_bytes()).hexdigest()
                                        if existing_hash == file_hash:
                                            duplicate_found = (subfolder.name, pdf_file.name)
                                            break
                                if duplicate_found:
                                    break

                            if duplicate_found:
                                validation_container.clear()
                                validation_container.set_visibility(True)
                                with validation_container:
                                    with ui.card().classes('w-full p-4 border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20'):
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.icon('info', color='orange').classes('text-2xl')
                                            ui.label('This File Already Exists').classes('font-bold text-amber-700 dark:text-amber-400')
                                        ui.label(f'Location: handbook/{duplicate_found[0]}/{duplicate_found[1]}').classes('text-sm font-mono')
                                return

                            pdf_file_io = io.BytesIO(pdf_bytes)
                            reader = PdfReader(pdf_file_io)

                            extracted_text = []
                            for page_num, page in enumerate(reader.pages, 1):
                                text = page.extract_text()
                                if text:
                                    extracted_text.append(f"--- Page {page_num} ---\n{text}")

                            full_text = "\n\n".join(extracted_text)
                            text_lower = full_text.lower()

                            missing_required = []
                            found_required = []

                            for section_name, keywords in REQUIRED_SECTIONS:
                                found = any(kw in text_lower for kw in keywords)
                                if found:
                                    found_required.append(section_name)
                                else:
                                    missing_required.append(section_name)

                            found_optional = []
                            for section_name, keywords in OPTIONAL_SECTIONS:
                                if any(kw in text_lower for kw in keywords):
                                    found_optional.append(section_name)

                            validation_container.clear()
                            validation_container.set_visibility(True)

                            with validation_container:
                                with ui.row().classes('items-center gap-2 mb-3'):
                                    ui.icon('picture_as_pdf', color='red').classes('text-2xl')
                                    ui.label(f'{e.name}').classes('font-bold')
                                    ui.label(f'({len(reader.pages)} pages, {len(full_text):,} characters)').classes('text-sm opacity-70')

                                if missing_required:
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20'):
                                        ui.label('Missing Required Sections').classes('font-bold text-red-700 dark:text-red-400')
                                        for section in missing_required:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('cancel', color='red')
                                                ui.label(section.title()).classes('text-sm')
                                else:
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-green-500 bg-green-50 dark:bg-green-900/20'):
                                        ui.label('All Required Sections Found').classes('font-bold text-green-700 dark:text-green-400')
                                        for section in found_required:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('check_circle', color='green')
                                                ui.label(section.title()).classes('text-sm')

                                if found_optional:
                                    with ui.card().classes('w-full p-4 mb-3 border-l-4 border-blue-500'):
                                        ui.label('Additional Sections Detected').classes('font-bold')
                                        for section in found_optional:
                                            with ui.row().classes('items-center gap-2'):
                                                ui.icon('info', color='blue')
                                                ui.label(section.title()).classes('text-sm')

                                with ui.row().classes('gap-4 mt-4 items-center flex-wrap'):
                                    if not missing_required:
                                        upload_state = {'pdf_bytes': pdf_bytes, 'filename': e.name}

                                        def save_and_load():
                                            today = datetime.now().strftime('%m%d%y')
                                            save_dir = handbook_dir / today
                                            save_dir.mkdir(exist_ok=True)
                                            save_path = save_dir / upload_state['filename']
                                            save_path.write_bytes(upload_state['pdf_bytes'])
                                            content_input.value = full_text
                                            ui.notify(f'PDF saved to handbook/{today}/ and content loaded into editor.', type='positive')
                                            validation_container.set_visibility(False)

                                        ui.button('Save PDF & Load Content', icon='save', on_click=save_and_load).props('color=primary')
                                    else:
                                        upload_state = {'pdf_bytes': pdf_bytes, 'filename': e.name}

                                        def save_anyway():
                                            today = datetime.now().strftime('%m%d%y')
                                            save_dir = handbook_dir / today
                                            save_dir.mkdir(exist_ok=True)
                                            save_path = save_dir / upload_state['filename']
                                            save_path.write_bytes(upload_state['pdf_bytes'])
                                            content_input.value = full_text
                                            show_warning_dialog('Missing Sections', 'PDF saved, but missing sections may cause issues.')
                                            validation_container.set_visibility(False)

                                        ui.button('Save Anyway (Not Recommended)', icon='warning', on_click=save_anyway).props('color=warning outline')

                        except ImportError:
                            show_error_dialog('Library Missing', 'PDF parsing library not installed. Run: pip install pypdf')
                        except Exception as ex:
                            show_error_dialog('PDF Error', f'Error reading PDF: {str(ex)}')

                    with ui.row().classes('items-center gap-4'):
                        ui.upload(
                            label='Select PDF File',
                            on_upload=handle_pdf_upload,
                            auto_upload=True,
                            max_files=1
                        ).props('accept=".pdf" color=primary').classes('max-w-xs')
                        ui.label('or paste content manually below').classes('text-sm opacity-70')

                with ui.card().classes('w-full p-4'):
                    ui.label('Handbook Content Editor').classes('text-lg font-bold mb-2')
                    ui.label('Edit the handbook content below. Click "Preview Changes" to review before applying.').classes('text-sm opacity-70 mb-4')

                    db = next(get_db())
                    try:
                        service = HandbookRevisionService(db)
                        active = service.get_active_revision()
                        initial_content = active.content if active else HANDBOOK_CONTENT
                    finally:
                        db.close()

                    content_input = ui.textarea(
                        label='Handbook Content (Markdown)',
                        value=initial_content
                    ).classes('w-full').props('outlined rows=20')

                    preview_container = ui.column().classes('w-full mt-4')
                    preview_container.set_visibility(False)

                    confirm_container = ui.row().classes('w-full justify-end gap-4 mt-4')
                    confirm_container.set_visibility(False)

                    def preview_changes():
                        new_content = content_input.value.strip()
                        if not new_content:
                            show_error_dialog('Empty Content', 'Content cannot be empty. Please enter or paste content first.')
                            return

                        preview_db = next(get_db())
                        try:
                            preview_service = HandbookRevisionService(preview_db)
                            current = preview_service.get_active_revision()
                            old_content = current.content if current else ""

                            report = preview_service._analyze_changes(old_content, new_content)

                            if not report.get('has_changes'):
                                ui.notify('No changes detected in the content', type='info')
                                return

                            preview_state['report'] = report
                            preview_state['new_content'] = new_content

                            preview_container.clear()
                            preview_container.set_visibility(True)
                            confirm_container.set_visibility(True)

                            with preview_container:
                                ui.label('Change Preview').classes('text-lg font-bold mb-2')

                                stats = report.get('stats', {})
                                with ui.card().classes('w-full p-4 mb-4 border-l-4 border-amber-500'):
                                    with ui.row().classes('gap-8'):
                                        with ui.column():
                                            ui.label('Lines Added').classes('text-sm opacity-70')
                                            ui.label(f"+{stats.get('additions', 0)}").classes('text-2xl font-bold text-green-600')
                                        with ui.column():
                                            ui.label('Lines Removed').classes('text-sm opacity-70')
                                            ui.label(f"-{stats.get('deletions', 0)}").classes('text-2xl font-bold text-red-600')
                                        with ui.column():
                                            ui.label('Total Changes').classes('text-sm opacity-70')
                                            ui.label(f"{stats.get('total_lines_changed', 0)}").classes('text-2xl font-bold')

                                changes = report.get('changes', [])
                                if changes:
                                    ui.label('Changes by Section').classes('font-semibold mb-2')
                                    with ui.card().classes('w-full p-3'):
                                        for change in changes[:10]:
                                            with ui.row().classes('items-center gap-2 py-1 border-b last:border-0'):
                                                section = change.get('section', 'General')
                                                summary = change.get('summary', '')
                                                ui.label(section or 'General').classes('font-medium')
                                                ui.label(summary).classes('text-sm opacity-70')
                                        if len(changes) > 10:
                                            ui.label(f'...and {len(changes) - 10} more sections').classes('text-sm opacity-50 mt-2')

                                with ui.card().classes('w-full p-3 mt-4 border-l-4 border-blue-500'):
                                    ui.label('A backup will be automatically created before applying changes.').classes('text-sm')

                        except Exception as e:
                            show_error_dialog('Analysis Error', f'Error analyzing changes: {str(e)}')
                        finally:
                            preview_db.close()

                    def cancel_preview():
                        preview_container.set_visibility(False)
                        confirm_container.set_visibility(False)
                        preview_state['report'] = None
                        preview_state['new_content'] = None

                    def confirm_and_save():
                        if not preview_state['new_content'] or not preview_state['report']:
                            show_warning_dialog('Preview Required', 'Please preview changes before applying them.')
                            return

                        import shutil

                        try:
                            handbook_db_url = config.DATABASE_URL
                            if handbook_db_url.startswith('sqlite:///'):
                                handbook_db_filename = handbook_db_url.replace('sqlite:///', '')
                                db_path = Path(__file__).parent.parent.parent / handbook_db_filename
                            else:
                                db_path = Path(__file__).parent.parent.parent / 'tjm_calendar.db'
                            backup_dir = Path(__file__).parent.parent.parent / 'backups' / 'handbook_changes'
                            backup_dir.mkdir(parents=True, exist_ok=True)

                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            backup_file = backup_dir / f'pre_handbook_change_{timestamp}.db'
                            shutil.copy2(db_path, backup_file)
                            preview_state['backup_file'] = backup_file
                            logger.info(f"Created handbook change backup: {backup_file}")
                        except Exception as e:
                            show_error_dialog('Backup Failed', f'Backup failed: {str(e)}. Changes not applied.')
                            logger.error(f"Handbook backup failed: {str(e)}")
                            return

                        save_db = next(get_db())
                        try:
                            save_service = HandbookRevisionService(save_db)
                            revision, report = save_service.create_revision(
                                content=preview_state['new_content'],
                                created_by=current_user.get('id')
                            )

                            ui.notify(
                                f"Version {revision.version} saved! Backup: {backup_file.name}",
                                type='positive'
                            )
                            logger.info(f"Handbook updated to version {revision.version}")

                            cancel_preview()

                        except Exception as e:
                            show_error_dialog('Save Failed', f'Error saving: {str(e)}. Backup available at {backup_file.name}')
                            logger.error(f"Handbook save failed: {str(e)}")
                        finally:
                            save_db.close()

                    with ui.row().classes('w-full justify-end gap-4 mt-4'):
                        ui.button('Preview Changes', on_click=preview_changes, color='primary', icon='preview')

                    with confirm_container:
                        ui.button('Cancel', on_click=cancel_preview, icon='close').props('flat')
                        ui.button('Apply Changes', on_click=confirm_and_save, color='positive', icon='check').classes('text-white')

            # Revision History Panel
            with ui.tab_panel(history_tab):
                history_container = ui.column().classes('w-full')

                def load_history():
                    history_container.clear()
                    db = next(get_db())
                    try:
                        service = HandbookRevisionService(db)
                        revisions = service.get_all_revisions()

                        with history_container:
                            if not revisions:
                                ui.label('No revisions found').classes('opacity-70')
                                return

                            for rev in revisions:
                                with ui.card().classes('w-full mb-3 p-4'):
                                    with ui.row().classes('justify-between items-start'):
                                        with ui.column():
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(f'Version {rev.version}').classes('font-bold')
                                                if rev.is_active:
                                                    ui.badge('Active', color='green')
                                            ui.label(f"Created: {rev.created_at.strftime('%Y-%m-%d %H:%M')}").classes('text-sm opacity-70')
                                            if rev.change_summary:
                                                ui.label(rev.change_summary).classes('text-sm mt-2')
                    finally:
                        db.close()

                load_history()

        with ui.row().classes('w-full mt-6'):
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard'), icon='arrow_back').props('outline')
