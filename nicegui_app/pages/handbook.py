"""
Employee Handbook page with AI chat for managers and styled viewer for employees.
Uses database content (if available) for both display and AI search.
"""
from nicegui import ui, app
from nicegui_app.static.handbook_content import HANDBOOK_SECTIONS
from nicegui_app.components.header import page_header
from nicegui_app.components.theme import apply_dark_mode
from src.database import get_db


def get_active_handbook_content():
    """
    Get the active handbook content from database or fall back to static.

    Returns:
        Tuple of (content, version) where content is the markdown text
        and version is the version string or 'static' for fallback.
    """
    db = next(get_db())
    try:
        from src.models.handbook_revision import HandbookRevision
        active = db.query(HandbookRevision).filter(HandbookRevision.is_active == True).first()
        if active:
            return active.content, active.version
    except Exception:
        pass
    finally:
        db.close()

    # Fall back to static content
    from nicegui_app.static.handbook_content import HANDBOOK_CONTENT
    return HANDBOOK_CONTENT, 'static'


def handbook_page():
    """Employee handbook page - AI chat for managers/admins, styled viewer for employees."""

    apply_dark_mode()

    # Check if user is logged in
    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return

    user_data = app.storage.general.get('user')
    user_role = user_data.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    # Get current handbook content and version
    handbook_content, handbook_version = get_active_handbook_content()

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header with greeting
        title = 'HANDBOOK AI ASSISTANT' if is_manager_or_admin else 'EMPLOYEE HANDBOOK'
        page_header(title=title, show_back=False)

        # Version and AI badge
        with ui.row().classes('mb-4 gap-2'):
            if handbook_version != 'static':
                ui.badge(f'Version {handbook_version}', color='blue').props('outline')
            if is_manager_or_admin:
                ui.badge('AI Enabled', color='green').props('outline')

        # Show AI Chat for managers/admins
        if is_manager_or_admin:
            render_ai_chat()
            ui.separator().classes('my-6')
            with ui.expansion('View Full Handbook', icon='menu_book').classes('w-full'):
                render_handbook_content(handbook_content)
        else:
            # Employees see the handbook content directly
            render_handbook_content(handbook_content)

        # Back to Dashboard button
        ui.button('Back to Dashboard', icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('outline').classes('mt-6')


def render_ai_chat():
    """Render the AI chat interface for handbook Q&A - uses database content."""
    from src.services.handbook_service import HandbookService

    # Create handbook service with database session for live content
    db = next(get_db())
    handbook_service = HandbookService(db_session=db)
    conversation_history = []

    # Get version info
    version = handbook_service.get_handbook_version()

    with ui.card().classes('w-full'):
        with ui.row().classes('w-full items-center gap-2 mb-4'):
            ui.icon('smart_toy', color='primary').classes('text-2xl')
            ui.label('Handbook AI Assistant').classes('text-lg font-semibold').style('color: #5a6a72;')
            if version:
                ui.badge(f'v{version}', color='blue').props('outline dense')
            if not handbook_service.is_available():
                ui.badge('API Key Required', color='red').props('outline')

        if not handbook_service.is_available():
            with ui.card().classes('w-full p-4 border-l-4 border-amber-500'):
                ui.label('AI Assistant Not Configured').classes('font-semibold text-amber-600')
                ui.label('To enable AI chat, add ANTHROPIC_API_KEY to your .env file.').classes('text-sm opacity-70')
            db.close()
            return

        ui.label('Ask questions about company policies, PTO, benefits, and more.').classes('text-sm opacity-70 mb-4')

        # Chat container with dark mode support
        chat_container = ui.column().classes('w-full max-h-96 overflow-y-auto p-3 rounded-lg mb-4').style(
            'background-color: var(--q-dark-page, #f5f5f5);'
        )

        # Welcome message
        with chat_container:
            with ui.row().classes('w-full justify-start mb-3'):
                with ui.card().classes('max-w-md p-3 border-l-4 border-blue-500'):
                    with ui.row().classes('items-center gap-2 mb-1'):
                        ui.icon('smart_toy', size='sm').classes('text-blue-500')
                        ui.label('Assistant').classes('text-xs font-semibold text-blue-500')
                    ui.label("Hello! I'm your handbook assistant. Ask me anything about company policies, PTO, benefits, or workplace guidelines.").classes('text-sm')

        # Input area
        with ui.row().classes('w-full gap-2 items-end'):
            question_input = ui.input(
                placeholder='Ask about vacation policy, sick time, benefits...'
            ).classes('flex-grow').props('outlined dense')

            async def send_question():
                question = question_input.value.strip()
                if not question:
                    return

                # Clear input
                question_input.value = ''

                # Add user message to chat
                with chat_container:
                    with ui.row().classes('w-full justify-end mb-3'):
                        with ui.card().classes('max-w-md p-3 border-l-4 border-green-500'):
                            with ui.row().classes('items-center gap-2 mb-1'):
                                ui.icon('person', size='sm').classes('text-green-500')
                                ui.label('You').classes('text-xs font-semibold text-green-500')
                            ui.label(question).classes('text-sm')

                # Show loading
                with chat_container:
                    loading_row = ui.row().classes('w-full justify-start mb-3')
                    with loading_row:
                        with ui.card().classes('p-3'):
                            with ui.row().classes('items-center gap-2'):
                                ui.spinner('dots', size='sm')
                                ui.label('Thinking...').classes('text-sm opacity-60')

                # Get response (uses database content via handbook_service)
                response = handbook_service.ask_question_sync(question, conversation_history)

                # Remove loading
                loading_row.delete()

                # Add to conversation history
                conversation_history.append({"role": "user", "content": question})
                conversation_history.append({"role": "assistant", "content": response})

                # Add response to chat
                with chat_container:
                    with ui.row().classes('w-full justify-start mb-3'):
                        with ui.card().classes('max-w-md p-3 border-l-4 border-blue-500'):
                            with ui.row().classes('items-center gap-2 mb-1'):
                                ui.icon('smart_toy', size='sm').classes('text-blue-500')
                                ui.label('Assistant').classes('text-xs font-semibold text-blue-500')
                            ui.markdown(response).classes('text-sm')

                # Scroll to bottom
                await ui.run_javascript('document.querySelector(".max-h-96").scrollTop = document.querySelector(".max-h-96").scrollHeight')

            ui.button(icon='send', on_click=send_question).props('color=primary round')
            question_input.on('keydown.enter', send_question)

        # Quick question buttons
        ui.label('Quick Questions:').classes('text-xs opacity-60 mt-4 mb-2')
        with ui.row().classes('w-full gap-2 flex-wrap'):
            quick_questions = [
                ('How much vacation do I get?', 'beach_access'),
                ('What are the holidays?', 'celebration'),
                ('How does sick time work?', 'medical_services'),
            ]
            for q, icon in quick_questions:
                def make_handler(question):
                    async def handler():
                        question_input.value = question
                        await send_question()
                    return handler
                ui.button(q, icon=icon, on_click=make_handler(q)).props('flat dense size=sm outline')


def render_handbook_content(content: str):
    """
    Render handbook content - either from database or static sections.

    Args:
        content: The handbook content as markdown text
    """
    # Check if we have structured sections (static) or raw markdown (database)
    if HANDBOOK_SECTIONS and not content.startswith('#'):
        # Use structured sections (static file format)
        render_styled_handbook()
    else:
        # Render raw markdown content (from database)
        render_markdown_handbook(content)


def render_markdown_handbook(content: str):
    """Render handbook as markdown content with scrollable sections."""

    with ui.card().classes('w-full p-6'):
        ui.label('Employee Handbook').classes('text-lg font-semibold mb-4').style('color: #5a6a72;')
        ui.markdown(content).classes('prose max-w-none')

    # Footer
    with ui.card().classes('w-full p-4 text-center mt-4'):
        with ui.row().classes('w-full justify-center items-center gap-2'):
            ui.icon('info', size='sm').classes('opacity-60')
            ui.label('For questions, contact HR').classes('text-xs opacity-60')


def render_styled_handbook():
    """Render the styled handbook viewer using static sections."""

    # Section navigation card
    with ui.card().classes('w-full mb-4 p-3'):
        ui.label('Quick Navigation').classes('text-sm font-semibold mb-2').style('color: #5a6a72;')
        with ui.row().classes('w-full gap-2 flex-wrap'):
            for section in HANDBOOK_SECTIONS:
                ui.button(
                    section['title'],
                    icon=section['icon'],
                    on_click=lambda s=section['id']: ui.run_javascript(f'document.getElementById("{s}").scrollIntoView({{behavior: "smooth"}})')
                ).props('flat dense size=sm')

    # Render each section with consistent styling
    for section in HANDBOOK_SECTIONS:
        # Determine border color based on section
        border_colors = {
            'welcome': 'border-blue-500',
            'company': 'border-indigo-500',
            'holidays': 'border-amber-500',
            'vacation': 'border-blue-500',
            'personal': 'border-purple-500',
            'sick': 'border-green-500',
            'bereavement': 'border-pink-500',
            'benefits': 'border-teal-500',
            'conduct': 'border-orange-500',
            'safety': 'border-red-500',
            'contact': 'border-gray-500',
        }
        border_class = border_colors.get(section['id'], 'border-blue-500')

        with ui.card().classes(f'w-full mb-4 border-l-4 {border_class}').props(f'id="{section["id"]}"'):
            with ui.row().classes('items-center gap-2 mb-3'):
                ui.icon(section['icon'], color='primary').classes('text-xl')
                ui.label(section['title']).classes('text-lg font-semibold').style('color: #5a6a72;')

            ui.markdown(section['content']).classes('text-sm handbook-content')

    # Footer
    with ui.card().classes('w-full p-4 text-center'):
        with ui.row().classes('w-full justify-center items-center gap-2'):
            ui.icon('info', size='sm').classes('opacity-60')
            ui.label('For questions, contact HR').classes('text-xs opacity-60')
