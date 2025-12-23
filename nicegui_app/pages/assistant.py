"""
Smart Scheduler Assistant - AI-Powered PTO Planning Interface

This page provides a chat interface to the SmartSchedulerAgent, enabling:
1. Natural language PTO planning conversations
2. AI-powered balance checking and date suggestions
3. Human-in-the-loop confirmation for write operations
"""
from datetime import datetime
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, PTO_GOLD, PTO_GRAY
from src.logging_config import get_logger

logger = get_logger(__name__)


def assistant_page():
    """Smart Scheduler Assistant page with chat interface."""
    apply_dark_mode()

    # Get current user
    current_user = app.storage.user.get('user', {})
    user_id = current_user.get('id')
    user_name = current_user.get('first_name', 'there')

    if not user_id:
        ui.label('Session expired. Please log in again.').classes('text-amber-500 p-4')
        ui.timer(2.0, lambda: ui.navigate.to('/'), once=True)
        return

    # Initialize agent (lazy load to avoid import issues if ANTHROPIC_API_KEY not set)
    agent_state = {'agent': None, 'loading': False, 'error': None}

    def get_agent():
        """Get or create the SmartSchedulerAgent."""
        if agent_state['agent'] is None:
            try:
                from src.services.agent_service import SmartSchedulerAgent
                agent_state['agent'] = SmartSchedulerAgent(user_id=user_id)
                logger.info(f"SmartSchedulerAgent created for user {user_id}")
            except Exception as e:
                agent_state['error'] = str(e)
                logger.error(f"Failed to create agent: {e}")
        return agent_state['agent']

    # Chat history for display (separate from agent's internal history)
    chat_messages = []

    with ui.column().classes('w-full max-w-4xl mx-auto p-4 h-screen flex flex-col'):
        # Header
        page_header(title='SMART SCHEDULER', show_back=True)

        # Subtitle with AI indicator
        with ui.row().classes('items-center gap-2 mb-2'):
            ui.icon('smart_toy', size='1.5rem').style(f'color: {PTO_GOLD};')
            ui.label('AI-Powered PTO Planning Assistant').classes('text-lg opacity-80')

        # Current date/time display
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.icon('schedule', size='1.2rem').classes('opacity-60')
            ui.label(f"{date_str} at {time_str}").classes('text-sm opacity-60')

        # Error banner (hidden by default)
        error_banner = ui.column().classes('w-full hidden')

        def show_error(message: str):
            """Display an error banner."""
            error_banner.clear()
            with error_banner:
                with ui.card().classes('w-full p-4 border-l-4 border-red-500'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('error', size='1.5rem').classes('text-red-500')
                        ui.label(message).classes('text-red-400')
            error_banner.classes(remove='hidden')

        # Chat container (scrollable)
        chat_container = ui.column().classes(
            'w-full flex-grow overflow-y-auto p-4 rounded-lg'
        ).style('background-color: #1f2937; min-height: 400px; max-height: calc(100vh - 400px);')

        # Store reference to confirmation dialog
        confirmation_dialog_ref = {'dialog': None}

        def add_chat_message(role: str, content: str, avatar: str = None):
            """Add a message to the chat display."""
            chat_messages.append({'role': role, 'content': content})
            render_chat()

        def render_chat():
            """Render all chat messages."""
            chat_container.clear()
            with chat_container:
                if not chat_messages:
                    # Welcome message - positioned at top
                    with ui.column().classes('items-start pt-4 opacity-70'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('chat', size='2.5rem').style(f'color: {PTO_GOLD};')
                            ui.label(f"Hi {user_name}! I'm your Smart Scheduler.").classes('text-xl')
                        ui.label("Ask me about your PTO balance, planning vacation, or submitting requests.").classes('ml-1 mt-2')
                else:
                    for msg in chat_messages:
                        is_user = msg['role'] == 'user'
                        with ui.chat_message(
                            name='You' if is_user else 'Assistant',
                            sent=is_user,
                            avatar='person' if is_user else 'smart_toy'
                        ).classes('mb-2'):
                            ui.markdown(msg['content'])

        def process_message(message: str):
            """Process user message through the agent."""
            if agent_state['loading']:
                return

            agent_state['loading'] = True
            input_field.disable()
            send_button.disable()

            # Show loading indicator
            with chat_container:
                loading_row = ui.row().classes('items-center gap-2')
                with loading_row:
                    ui.spinner(size='sm').style(f'color: {PTO_GOLD};')
                    ui.label('Thinking...').classes('opacity-60')

            async def do_process():
                """Async processing of message."""
                try:
                    agent = get_agent()
                    if agent is None:
                        show_error(f"Could not initialize AI assistant: {agent_state['error']}")
                        return

                    # Process through agent (this makes API call)
                    result = agent.process_message(message)

                    # Remove loading indicator
                    loading_row.delete()

                    # Add assistant response
                    add_chat_message('assistant', result.get('response', 'No response'))

                    # Check for pending confirmation
                    pending = result.get('pending_confirmation')
                    if pending:
                        show_confirmation(pending)

                    # Log actions taken
                    actions = result.get('actions_taken', [])
                    if actions:
                        logger.info(f"Agent used {len(actions)} tools: {[a['tool'] for a in actions]}")

                except Exception as e:
                    loading_row.delete()
                    logger.error(f"Agent error: {e}")
                    add_chat_message('assistant', f"I encountered an error: {str(e)}")
                finally:
                    agent_state['loading'] = False
                    input_field.enable()
                    send_button.enable()

            ui.timer(0.1, do_process, once=True)

        def send_message():
            """Handle send button click."""
            message = input_field.value.strip()
            if not message:
                return

            # Clear input
            input_field.value = ''

            # Add user message to chat
            add_chat_message('user', message)

            # Process through agent
            process_message(message)

        def clear_history():
            """Clear chat history and reset agent."""
            nonlocal chat_messages
            chat_messages = []
            agent_state['agent'] = None
            agent_state['error'] = None
            if confirmation_dialog_ref['dialog'] is not None:
                confirmation_dialog_ref['dialog'].close()
            error_banner.classes(add='hidden')
            render_chat()
            ui.notify('Chat history cleared', type='info')

        # Initial render
        render_chat()

        # Input row at bottom
        with ui.row().classes('w-full items-center gap-2 mt-4'):
            input_field = ui.input(placeholder='Ask about your PTO...').classes(
                'flex-grow'
            ).props('outlined dense').on('keydown.enter', send_message)

            send_button = ui.button(icon='send', on_click=send_message).style(
                f'background-color: {PTO_GOLD} !important; color: white !important;'
            )

            ui.button('Clear', icon='delete', on_click=clear_history).props('flat').style(
                f'color: {PTO_GOLD} !important;'
            )

        # Quick action suggestions
        with ui.row().classes('w-full gap-2 mt-2 flex-wrap'):
            def quick_ask(question: str):
                input_field.value = question
                send_message()

            suggestions = [
                "What's my vacation balance?",
                "Can I take off next Friday?",
                "Help me plan a week vacation"
            ]
            for suggestion in suggestions:
                ui.button(
                    suggestion,
                    on_click=lambda s=suggestion: quick_ask(s)
                ).props('flat dense').classes('text-xs').style(
                    f'color: {PTO_GOLD} !important;'
                )

        def show_confirmation(pending_action: dict):
            """Display confirmation dialog for pending write action."""
            with ui.dialog().props('position="bottom"') as dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
                confirmation_dialog_ref['dialog'] = dialog

                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('warning', size='1.5rem').style(f'color: {PTO_GOLD};')
                    ui.label('Confirmation Required').classes('text-xl font-bold')

                ui.label(pending_action.get('action_summary', 'Action pending')).classes('mb-6 text-base')

                with ui.row().classes('w-full justify-end gap-3'):
                    def cancel_action():
                        """Handle user cancellation."""
                        dialog.close()
                        add_chat_message('user', 'CANCEL')
                        process_message('CANCEL')

                    def confirm_action():
                        """Handle user confirmation."""
                        dialog.close()
                        add_chat_message('user', 'CONFIRM')
                        process_message('CONFIRM')

                    ui.button('CANCEL', icon='close', on_click=cancel_action).props('outline').style(
                        f'border-color: {PTO_GOLD} !important; color: {PTO_GOLD} !important;'
                    )
                    ui.button('CONFIRM', icon='check', on_click=confirm_action).style(
                        f'background-color: {PTO_GOLD} !important; color: white !important;'
                    )

            dialog.open()

        # Back button
        ui.button('Back', icon='arrow_back', on_click=go_back).props('outline').classes('mt-4').style(
            f'border-color: {PTO_GOLD} !important; color: {PTO_GOLD} !important;'
        )
