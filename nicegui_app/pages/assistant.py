"""
PTO Assistant - AI-Powered PTO Planning Interface

This page provides a chat interface to PTO Central AI agents, enabling:
1. Natural language PTO planning conversations
2. AI-powered balance checking and date suggestions
3. Human-in-the-loop confirmation for write operations
4. Multiple agent types for different use cases

Agents:
- Smart Scheduler: Find optimal vacation dates, check balances
- Year-End Optimizer: Use expiring PTO before year-end
- Approval Assistant: Help managers review and approve requests (manager+ only)
"""
from datetime import datetime
import asyncio
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from nicegui_app.components.theme import apply_dark_mode, PTO_GOLD, PTO_GRAY
from src.logging_config import get_logger

logger = get_logger(__name__)

# Agent configuration with display metadata
AGENTS = {
    "smart_scheduler": {
        "name": "Smart Scheduler",
        "icon": "event_available",
        "description": "Find optimal vacation dates and check balances",
        "color": "#4CAF50",
        "manager_only": False,
        "welcome": (
            "I can help you find the best dates for your vacation - including ways to "
            "maximize your time off using market holidays and long weekends. "
            "What are you planning?"
        ),
        "suggestions": [
            "What's my vacation balance?",
            "Can I take off next Friday?",
            "Help me plan a week vacation",
            "When are the market holidays?",
        ],
    },
    "year_end_optimizer": {
        "name": "Year-End Optimizer",
        "icon": "calendar_month",
        "description": "Use expiring PTO before December 31st",
        "color": "#FF9800",
        "manager_only": False,
        "welcome": (
            "I'm here to help you use your remaining PTO before it expires on December 31st. "
            "Want me to check your balance and find some good dates in December?"
        ),
        "suggestions": [
            "What PTO will I lose at year end?",
            "Find December dates for me",
            "What's my personal day balance?",
            "Show me open slots in December",
        ],
    },
    "approval_assistant": {
        "name": "Approval Assistant",
        "icon": "fact_check",
        "description": "Review and approve team PTO requests",
        "color": "#2196F3",
        "manager_only": True,
        "welcome": (
            "I can help you review and approve PTO requests from your team. "
            "Would you like to see pending requests, or get recommendations on which ones to approve?"
        ),
        "suggestions": [
            "Show pending requests",
            "Who's out this week?",
            "Check team coverage for next month",
            "Any coverage conflicts?",
        ],
    },
}


def assistant_page():
    """PTO Assistant page with multi-agent chat interface."""
    apply_dark_mode()

    # Get current user
    current_user = app.storage.user.get('user', {})
    user_id = current_user.get('id')
    user_name = current_user.get('first_name', 'there')
    user_role = current_user.get('role', 'employee')

    if not user_id:
        ui.label('Session expired. Please log in again.').classes('text-amber-500 p-4')
        ui.timer(2.0, lambda: ui.navigate.to('/'), once=True)
        return

    # Filter available agents based on role
    is_manager_or_above = user_role in ['manager', 'admin', 'superadmin']
    available_agents = {
        k: v for k, v in AGENTS.items()
        if not v.get('manager_only') or is_manager_or_above
    }

    # State: current agent type and instance
    agent_state = {
        'current_type': 'smart_scheduler',
        'agent': None,
        'loading': False,
        'error': None
    }

    # Voice state
    voice_state = {
        'enabled': False,
        'recording': False,
        'mic_button': None,
        'recording_indicator': None,
        'speaker_button': None
    }

    def get_agent():
        """Get or create the current agent."""
        agent_type = agent_state['current_type']
        if agent_state['agent'] is None:
            try:
                from src.services.agent_service import create_agent
                agent_state['agent'] = create_agent(agent_type, user_id=user_id)
                logger.info(f"{agent_type} agent created for user {user_id}")
            except Exception as e:
                agent_state['error'] = str(e)
                logger.error(f"Failed to create agent: {e}")
        return agent_state['agent']

    def switch_agent(new_type: str):
        """Switch to a different agent type."""
        if new_type == agent_state['current_type']:
            return
        agent_state['current_type'] = new_type
        agent_state['agent'] = None
        agent_state['error'] = None
        # Clear chat and show new welcome
        nonlocal chat_messages
        chat_messages = []
        render_chat()
        update_suggestions()
        ui.notify(f'Switched to {AGENTS[new_type]["name"]}', type='info')

    # Chat history for display (separate from agent's internal history)
    chat_messages = []

    # Inject Web Speech API for voice input
    ui.add_body_html("""
<script>
window.ptoVoice = {
    recognition: null,
    isRecording: false,

    init: function() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Speech recognition not supported');
            return false;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            const input = document.querySelector('input[placeholder*="Ask about"]');
            if (input) {
                input.value = transcript;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };

        this.recognition.onend = () => {
            this.isRecording = false;
        };

        this.recognition.onerror = (event) => {
            console.error('Speech error:', event.error);
            this.isRecording = false;
        };

        return true;
    },

    start: function() {
        if (!this.recognition && !this.init()) {
            alert('Speech recognition not supported in this browser. Try Chrome or Edge.');
            return false;
        }
        try {
            this.recognition.start();
            this.isRecording = true;
            return true;
        } catch (e) {
            console.error('Failed to start:', e);
            return false;
        }
    },

    stop: function() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
        }
    }
};
window.ptoVoice.init();
</script>
""")

    with ui.column().classes('w-full max-w-4xl mx-auto p-4 min-h-screen'):
        # Header (no back button)
        page_header(title='PTO ASSISTANT', show_back=False)

        # Current date/time display
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        with ui.row().classes('items-center gap-2 mb-2'):
            ui.icon('schedule', size='1.2rem').classes('opacity-60')
            ui.label(f"{date_str} at {time_str}").classes('text-sm opacity-60')

        # Agent selector row
        with ui.row().classes('w-full items-center gap-4 mb-4 p-3 rounded-lg').style('background-color: #374151;'):
            ui.label('Agent:').classes('text-sm opacity-70')

            # Build options for dropdown
            agent_options = {
                k: f"{v['name']}"
                for k, v in available_agents.items()
            }

            agent_select = ui.select(
                options=agent_options,
                value='smart_scheduler',
                on_change=lambda e: switch_agent(e.value)
            ).classes('min-w-48').props('dense outlined dark')

            # Agent icon and description (updates when agent changes)
            agent_info = AGENTS[agent_state['current_type']]
            with ui.row().classes('items-center gap-2 ml-auto'):
                agent_icon_label = ui.icon(
                    agent_info['icon'],
                    size='1.2rem'
                ).style(f'color: {agent_info["color"]};')
                agent_desc_label = ui.label(
                    agent_info['description']
                ).classes('text-sm opacity-70')

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
            'w-full overflow-y-auto p-4 rounded-lg'
        ).style('background-color: #1f2937; min-height: 300px; max-height: 50vh;')

        # Store reference to confirmation dialog
        confirmation_dialog_ref = {'dialog': None}

        def add_chat_message(role: str, content: str, avatar: str = None):
            """Add a message to the chat display."""
            chat_messages.append({'role': role, 'content': content})
            render_chat()

        def render_chat():
            """Render all chat messages."""
            chat_container.clear()
            current_agent = AGENTS[agent_state['current_type']]
            with chat_container:
                if not chat_messages:
                    # Welcome message - agent-specific
                    with ui.column().classes('items-start pt-4 opacity-70'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon(current_agent['icon'], size='2.5rem').style(
                                f'color: {current_agent["color"]};'
                            )
                            ui.label(f"Hi {user_name}! I'm your {current_agent['name']}.").classes('text-xl')
                        ui.label(current_agent['welcome']).classes('ml-1 mt-2 max-w-xl')
                else:
                    for msg in chat_messages:
                        is_user = msg['role'] == 'user'
                        with ui.chat_message(
                            name='You' if is_user else current_agent['name'],
                            sent=is_user,
                            avatar='person' if is_user else current_agent['icon']
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
                import asyncio
                try:
                    agent = get_agent()
                    if agent is None:
                        show_error(f"Could not initialize AI assistant: {agent_state['error']}")
                        return

                    # Process through agent in a thread to avoid blocking websocket
                    result = await asyncio.to_thread(agent.process_message, message)

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
            update_suggestions()
            ui.notify('Chat history cleared', type='info')

        # Initial render
        render_chat()

        # Voice handler functions
        def toggle_voice_mode(enabled: bool):
            """Toggle voice input mode."""
            voice_state['enabled'] = enabled
            if enabled:
                voice_state['mic_button'].classes(remove='hidden')
                ui.notify('Voice mode enabled. Click the mic to speak.', type='info')
            else:
                voice_state['mic_button'].classes(add='hidden')
                voice_state['recording_indicator'].classes(add='hidden')
                if voice_state['recording']:
                    ui.run_javascript('window.ptoVoice.stop()')
                    voice_state['recording'] = False
                    voice_state['mic_button'].props(remove='color=red')

        async def toggle_recording():
            """Toggle voice recording on/off."""
            if voice_state['recording']:
                # Stop recording
                voice_state['recording'] = False
                voice_state['mic_button'].props(remove='color=red')
                voice_state['recording_indicator'].classes(add='hidden')
                await ui.run_javascript('window.ptoVoice.stop()')
            else:
                # Start recording
                voice_state['recording'] = True
                voice_state['mic_button'].props('color=red')
                voice_state['recording_indicator'].classes(remove='hidden')
                await ui.run_javascript('window.ptoVoice.start()')

        async def replay_last_response():
            """Replay the last agent response using browser TTS."""
            if not chat_messages:
                ui.notify('No response to replay', type='warning')
                return

            last_assistant_msg = None
            for msg in reversed(chat_messages):
                if msg.get('role') == 'assistant':
                    last_assistant_msg = msg.get('content', '')
                    break

            if not last_assistant_msg:
                ui.notify('No response to replay', type='warning')
                return

            # Use browser's built-in TTS
            # Strip markdown formatting for cleaner speech
            clean_text = last_assistant_msg.replace('**', '').replace('*', '').replace('#', '')
            clean_text = clean_text[:500]  # Limit length
            await ui.run_javascript(f'''
                const utterance = new SpeechSynthesisUtterance({repr(clean_text)});
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                window.speechSynthesis.speak(utterance);
            ''')
            ui.notify('Playing response...', type='info')

        # Input row at bottom
        with ui.row().classes('w-full items-center gap-2 mt-4'):
            # Voice toggle switch
            voice_toggle = ui.switch('', value=False).tooltip('Enable voice input')
            voice_toggle.on('change', lambda e: toggle_voice_mode(e.value))

            # Microphone button (hidden until voice enabled)
            voice_state['mic_button'] = ui.button(
                icon='mic',
                on_click=toggle_recording
            ).props('round fab-mini').classes('hidden').tooltip('Click to speak')

            # Recording indicator (hidden)
            voice_state['recording_indicator'] = ui.row().classes('items-center gap-1 hidden')
            with voice_state['recording_indicator']:
                ui.spinner('audio', size='sm', color='red')
                ui.label('Listening...').classes('text-red-500 text-sm animate-pulse')

            # Text input
            input_field = ui.input(placeholder='Ask about your PTO...').classes(
                'flex-grow'
            ).props('outlined dense').on('keydown.enter', send_message)

            # Send button
            send_button = ui.button(icon='send', on_click=send_message).style(
                f'background-color: {PTO_GOLD} !important; color: white !important;'
            )

            # Speaker button (replay last response)
            voice_state['speaker_button'] = ui.button(
                icon='volume_up',
                on_click=replay_last_response
            ).props('round fab-mini').tooltip('Replay last response').style(
                f'color: {PTO_GOLD} !important;'
            )

            # Clear button
            ui.button('Clear', icon='delete', on_click=clear_history).props('flat').style(
                f'color: {PTO_GOLD} !important;'
            )

        # Quick action suggestions (agent-specific)
        suggestions_container = ui.row().classes('w-full gap-2 mt-2 flex-wrap')

        def quick_ask(question: str):
            input_field.value = question
            send_message()

        def update_suggestions():
            """Update quick action buttons based on current agent."""
            suggestions_container.clear()
            current_agent = AGENTS[agent_state['current_type']]
            with suggestions_container:
                for suggestion in current_agent['suggestions']:
                    ui.button(
                        suggestion,
                        on_click=lambda e, s=suggestion: quick_ask(s)
                    ).props('flat dense').classes('text-xs').style(
                        f'color: {PTO_GOLD} !important;'
                    )

        # Initial render of suggestions
        update_suggestions()

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
