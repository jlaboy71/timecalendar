"""
Employee Handbook page with AI chat for managers and styled viewer for employees.
"""
from nicegui import ui, app
from nicegui_app.static.handbook_content import HANDBOOK_SECTIONS
from nicegui_app.logo import LOGO_DATA_URL


def handbook_page():
    """Employee handbook page - AI chat for managers/admins, styled viewer for employees."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    # Check if user is logged in
    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return

    user_data = app.storage.general.get('user')
    user_role = user_data.get('role', 'employee')
    is_manager_or_admin = user_role in ['manager', 'admin', 'superadmin']

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        # Header with logo above title (matching dashboard style)
        with ui.row().classes('w-full justify-between items-start mb-6'):
            with ui.column().classes('gap-2'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 50px; width: auto;')
                with ui.row().classes('items-center gap-2'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat round')
                    if is_manager_or_admin:
                        ui.label('HANDBOOK AI ASSISTANT').classes('text-xl font-bold uppercase').style('color: #5a6a72;')
                    else:
                        ui.label('EMPLOYEE HANDBOOK').classes('text-xl font-bold uppercase').style('color: #5a6a72;')

            # Right side - AI badge for managers and dark mode toggle
            with ui.row().classes('items-center gap-2'):
                if is_manager_or_admin:
                    ui.badge('AI Enabled', color='green').props('outline')

                # Dark mode toggle
                def toggle_dark_mode():
                    current = app.storage.general.get('dark_mode', False)
                    new_state = not current
                    app.storage.general['dark_mode'] = new_state
                    if new_state:
                        dark_mode.enable()
                    else:
                        dark_mode.disable()
                    dark_toggle.props(f'icon={"light_mode" if new_state else "dark_mode"}')

                dark_toggle = ui.button(
                    icon='light_mode' if is_dark else 'dark_mode',
                    on_click=toggle_dark_mode
                ).props('flat round')

        # Show AI Chat for managers/admins
        if is_manager_or_admin:
            render_ai_chat()
            ui.separator().classes('my-6')
            with ui.expansion('View Full Handbook', icon='menu_book').classes('w-full'):
                render_styled_handbook()
        else:
            # Employees see the styled handbook directly
            render_styled_handbook()


def render_ai_chat():
    """Render the AI chat interface for handbook Q&A."""
    from src.services.handbook_service import HandbookService

    handbook_service = HandbookService()
    conversation_history = []

    with ui.card().classes('w-full'):
        with ui.row().classes('w-full items-center gap-2 mb-4'):
            ui.icon('smart_toy', color='primary').classes('text-2xl')
            ui.label('Handbook AI Assistant').classes('text-lg font-semibold').style('color: #5a6a72;')
            if not handbook_service.is_available():
                ui.badge('API Key Required', color='red').props('outline')

        if not handbook_service.is_available():
            with ui.card().classes('w-full p-4 border-l-4 border-amber-500'):
                ui.label('AI Assistant Not Configured').classes('font-semibold text-amber-600')
                ui.label('To enable AI chat, add ANTHROPIC_API_KEY to your .env file.').classes('text-sm opacity-70')
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

                # Get response
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
                ('What benefits are offered?', 'health_and_safety'),
            ]
            for q, icon in quick_questions:
                def make_handler(question):
                    async def handler():
                        question_input.value = question
                        await send_question()
                    return handler
                ui.button(q, icon=icon, on_click=make_handler(q)).props('flat dense size=sm outline')


def render_styled_handbook():
    """Render the styled handbook viewer."""

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
            ui.label('Last Updated: January 2024 | For questions, contact HR at hr@haventech.com').classes('text-xs opacity-60')
