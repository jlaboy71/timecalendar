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

    # Inject CSS for speaker button animation
    ui.add_head_html("""
<style>
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(1.1); }
}
.speaker-playing {
    background-color: #ef4444 !important;
    animation: pulse 1s infinite !important;
}
</style>
""")

    # Inject Web Speech API for voice input (enhanced with auto-send and audio control)
    ui.add_body_html("""
<script>
window.ptoVoice = {
    recognition: null,
    isRecording: false,
    lastTranscript: '',
    autoSendTimer: null,
    autoSendEnabled: true,
    // Audio playback control
    currentAudio: null,
    isPlaying: false,

    init: function() {
        console.log('[PTO Voice] Initializing Speech Recognition...');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('[PTO Voice] Speech recognition not supported in this browser');
            return false;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let transcript = '';
            let isFinal = false;

            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    isFinal = true;
                }
            }

            console.log('[PTO Voice] Transcript:', transcript, '| Final:', isFinal);
            this.lastTranscript = transcript;

            // CHECK FOR VOICE COMMANDS (only on final results)
            if (isFinal && transcript.trim()) {
                const command = this.checkVoiceCommand(transcript.trim().toLowerCase());
                if (command) {
                    console.log('[PTO Voice] Command recognized:', command);
                    // Clear any pending auto-send timer
                    if (this.autoSendTimer) {
                        clearTimeout(this.autoSendTimer);
                        this.autoSendTimer = null;
                    }
                    // Clear the transcript so it doesn't get sent
                    this.lastTranscript = '';
                    // Execute the command via Python callback
                    this.executeCommand(command);
                    return;  // Don't proceed with normal input handling
                }
            }

            // Target the input by class (more reliable in NiceGUI)
            const wrapper = document.querySelector('.chat-input-field');
            if (wrapper) {
                // Find the inner input element (NiceGUI wraps inputs in Quasar components)
                const innerInput = wrapper.querySelector('input') || wrapper;
                console.log('[PTO Voice] Found input element:', innerInput);

                // Set value using native setter to bypass Vue/Quasar reactivity issues
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(innerInput, transcript);

                // Dispatch input event to trigger NiceGUI/Vue reactivity
                innerInput.dispatchEvent(new Event('input', { bubbles: true }));

                // Also dispatch a change event for good measure
                innerInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Focus the input so user can see their text
                innerInput.focus();

                console.log('[PTO Voice] Input value set to:', innerInput.value);

                // AUTO-SEND: If result is final, trigger send after delay
                if (isFinal && this.autoSendEnabled && transcript.trim()) {
                    console.log('[PTO Voice] Final result detected - auto-sending in 800ms...');

                    // Clear any existing timer
                    if (this.autoSendTimer) {
                        clearTimeout(this.autoSendTimer);
                    }

                    this.autoSendTimer = setTimeout(() => {
                        // Double-check transcript isn't empty (prevents noise-triggered sends)
                        const currentTranscript = this.lastTranscript.trim();
                        if (!currentTranscript) {
                            console.log('[PTO Voice] Auto-send cancelled - transcript is empty');
                            return;
                        }

                        console.log('[PTO Voice] Auto-send triggered!');
                        // Find and click the send button
                        const sendBtn = document.querySelector('.voice-send-btn');
                        if (sendBtn) {
                            sendBtn.click();
                            console.log('[PTO Voice] Send button clicked');
                        } else {
                            // Fallback: find by icon
                            const sendBtnFallback = document.querySelector('button[title="Send"]') ||
                                                    document.querySelector('button .q-icon:contains("send")')?.closest('button');
                            if (sendBtnFallback) {
                                sendBtnFallback.click();
                                console.log('[PTO Voice] Send button (fallback) clicked');
                            } else {
                                console.error('[PTO Voice] Could not find send button');
                            }
                        }
                    }, 800);  // 800ms delay for more breathing room
                }
            } else {
                console.error('[PTO Voice] Could not find .chat-input-field element');
                // Fallback: try finding by placeholder
                const fallbackInput = document.querySelector('input[placeholder*="Ask about"]');
                if (fallbackInput) {
                    console.log('[PTO Voice] Using fallback selector');
                    fallbackInput.value = transcript;
                    fallbackInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        };

        this.recognition.onend = () => {
            console.log('[PTO Voice] Recognition ended');
            this.isRecording = false;
        };

        this.recognition.onerror = (event) => {
            console.error('[PTO Voice] Speech error:', event.error);
            this.isRecording = false;
        };

        console.log('[PTO Voice] Initialization complete');
        return true;
    },

    start: function() {
        console.log('[PTO Voice] Mic started - attempting to begin recognition');
        // STOP any playing audio first (so AI doesn't talk over user)
        this.stopAudio();

        if (!this.recognition && !this.init()) {
            alert('Speech recognition not supported in this browser. Try Chrome or Edge.');
            return false;
        }
        try {
            this.recognition.start();
            this.isRecording = true;
            console.log('[PTO Voice] Recognition started successfully');
            return true;
        } catch (e) {
            console.error('[PTO Voice] Failed to start:', e);
            return false;
        }
    },

    stop: function() {
        if (this.recognition && this.isRecording) {
            console.log('[PTO Voice] Stopping recognition');
            this.recognition.stop();
            this.isRecording = false;
        }
        // Clear auto-send timer if stopping manually
        if (this.autoSendTimer) {
            clearTimeout(this.autoSendTimer);
            this.autoSendTimer = null;
        }
    },

    // Helper to update speaker button visual
    updateSpeakerButton: function(playing) {
        const btn = document.querySelector('.voice-speaker-btn');
        if (btn) {
            if (playing) {
                btn.classList.add('speaker-playing');
            } else {
                btn.classList.remove('speaker-playing');
                btn.style.backgroundColor = '';
                btn.style.animation = '';
            }
        }
    },

    // Play audio and track it for stop/interrupt capability
    playAudio: function(url) {
        // Stop any currently playing audio first
        this.stopAudio();

        console.log('[PTO Voice] Playing audio:', url);
        this.currentAudio = new Audio(url);
        this.isPlaying = true;
        this.updateSpeakerButton(true);

        this.currentAudio.onended = () => {
            console.log('[PTO Voice] Audio playback ended');
            this.isPlaying = false;
            this.currentAudio = null;
            this.updateSpeakerButton(false);
        };

        this.currentAudio.onerror = (e) => {
            console.error('[PTO Voice] Audio error:', e);
            this.isPlaying = false;
            this.currentAudio = null;
            this.updateSpeakerButton(false);
        };

        this.currentAudio.play().catch(e => {
            console.error('[PTO Voice] Audio play error:', e);
            this.isPlaying = false;
            this.currentAudio = null;
            this.updateSpeakerButton(false);
        });

        return true;
    },

    // Stop/interrupt any playing audio
    stopAudio: function() {
        // Stop HTML5 audio
        if (this.currentAudio) {
            console.log('[PTO Voice] Stopping audio playback');
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.isPlaying = false;

        // Also stop browser TTS (SpeechSynthesis)
        if (window.speechSynthesis && window.speechSynthesis.speaking) {
            console.log('[PTO Voice] Stopping browser TTS');
            window.speechSynthesis.cancel();
        }

        // Reset speaker button visual
        this.updateSpeakerButton(false);

        return true;
    },

    // Check if audio is currently playing
    getIsPlaying: function() {
        return this.isPlaying || (window.speechSynthesis && window.speechSynthesis.speaking);
    },

    getLastTranscript: function() {
        return this.lastTranscript;
    },

    clearTranscript: function() {
        this.lastTranscript = '';
    },

    // Voice command patterns - returns command name if matched, null otherwise
    checkVoiceCommand: function(text) {
        // Normalize text for matching
        const normalized = text.toLowerCase().trim();

        // Command patterns (order matters - more specific first)
        const commands = [
            // Clear chat
            { patterns: ['clear chat', 'clear history', 'clear the chat', 'clear conversation', 'new chat', 'start over'], command: 'clear_chat' },
            // Navigation
            { patterns: ['go back', 'go home', 'return', 'back to dashboard', 'go to dashboard'], command: 'go_back' },
            // Logout
            { patterns: ['log out', 'logout', 'sign out', 'sign off'], command: 'logout' },
            // Theme toggle
            { patterns: ['dark mode', 'enable dark mode', 'turn on dark mode', 'switch to dark'], command: 'dark_mode' },
            { patterns: ['light mode', 'enable light mode', 'turn on light mode', 'switch to light'], command: 'light_mode' },
            // Audio control
            { patterns: ['stop', 'stop talking', 'be quiet', 'silence', 'shut up', 'stop audio', 'mute'], command: 'stop_audio' },
            // Help
            { patterns: ['help', 'what can you do', 'voice commands', 'list commands'], command: 'help' },
        ];

        for (const cmd of commands) {
            for (const pattern of cmd.patterns) {
                // Check for exact match or if text starts with pattern
                if (normalized === pattern || normalized.startsWith(pattern + ' ')) {
                    return cmd.command;
                }
            }
        }

        return null;  // No command matched
    },

    // Execute a voice command by calling Python handler
    executeCommand: function(command) {
        console.log('[PTO Voice] Executing command:', command);

        // Clear the input field
        const wrapper = document.querySelector('.chat-input-field');
        if (wrapper) {
            const innerInput = wrapper.querySelector('input') || wrapper;
            innerInput.value = '';
            innerInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        // Trigger Python callback via custom event
        // NiceGUI listens for this event on elements with the voice-command-handler class
        const event = new CustomEvent('voiceCommand', {
            detail: { command: command },
            bubbles: true
        });
        document.dispatchEvent(event);

        // Also try direct element dispatch for NiceGUI
        const handler = document.querySelector('.voice-command-handler');
        if (handler) {
            handler.dispatchEvent(event);
        }
    }
};
// Initialize on page load
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

        # Thinking indicator container (near input area, shown during processing)
        thinking_indicator = ui.row().classes('w-full items-center gap-2 mt-2 hidden')

        def show_thinking(show: bool):
            """Show or hide the thinking indicator near input."""
            thinking_indicator.clear()
            if show:
                with thinking_indicator:
                    ui.spinner('dots', size='sm').style(f'color: {PTO_GOLD};')
                    ui.label('AI is thinking...').classes('text-amber-400 text-sm animate-pulse')
                thinking_indicator.classes(remove='hidden')
            else:
                thinking_indicator.classes(add='hidden')

        # ================================================================
        # LIVE PIPELINE - Visual progress indicator with connecting lines
        # ================================================================
        # Pipeline state tracking (separate from voice_enabled for clarity)
        pipeline_state = {
            'recording': False,
            'thinking': False,
            'playing': False,
            'current_stage': None,  # 'transcribing', 'processing', 'generating', 'speaking', or None
            'voice_mode': False  # Track if voice mode is enabled for opacity levels
        }

        # Pipeline stage configuration
        PIPELINE_STAGES = [
            {'id': 'transcribing', 'emoji': '🎙️', 'label': 'Mic', 'color': '#ef4444', 'state_key': 'recording'},
            {'id': 'processing', 'emoji': '⚡', 'label': 'Bridge', 'color': '#f59e0b', 'state_key': None},
            {'id': 'generating', 'emoji': '🧠', 'label': 'AI', 'color': '#8b5cf6', 'state_key': 'thinking'},
            {'id': 'speaking', 'emoji': '🔊', 'label': 'Speaker', 'color': '#22c55e', 'state_key': 'playing'},
        ]

        # Store references to pipeline stage elements for reactive updates
        # (container will be created later, after input_container)
        pipeline_refs = {}
        connector_refs = []
        pipeline_container_ref = {'container': None}

        def update_pipeline_ui():
            """Update pipeline UI based on current state (recording, thinking, playing).

            This function checks the pipeline_state dict and updates the visual appearance
            of each stage to reflect the current activity.
            - Ghost mode (idle): opacity-15 for all elements
            - Active stage: opacity-100 with animate-pulse
            - Connectors: dull gray when idle, bright gold when data flows through
            """
            if not pipeline_refs:
                return  # Pipeline not built yet

            # Determine active stage from state
            active_stage = pipeline_state.get('current_stage')

            # If no explicit stage but we have state flags, infer the stage
            if active_stage is None:
                if pipeline_state.get('playing'):
                    active_stage = 'speaking'
                elif pipeline_state.get('thinking'):
                    active_stage = 'generating'
                elif pipeline_state.get('recording'):
                    active_stage = 'transcribing'

            # Determine base opacity class based on voice mode
            voice_mode_on = pipeline_state.get('voice_mode', False)
            ghost_opacity_class = 'opacity-40' if voice_mode_on else 'opacity-15'

            # Update each stage's appearance
            for stage_id, refs in pipeline_refs.items():
                is_active = (stage_id == active_stage)

                if is_active:
                    # Active stage - full opacity, scaled up, pulsing with glow
                    refs['emoji'].classes(remove='opacity-15 opacity-40')
                    refs['emoji'].classes(add='opacity-100 animate-pulse')
                    refs['emoji'].style('transform: scale(1.2);')
                    refs['icon_bg'].style(f'background-color: {refs["color"]}20; box-shadow: 0 0 20px {refs["color"]}60;')
                    refs['text'].classes(remove='opacity-15 opacity-40')
                    refs['text'].classes(add='opacity-100')
                    refs['text'].style(f'color: {refs["color"]}; font-weight: 600;')
                else:
                    # Inactive stage - ghost mode opacity
                    refs['emoji'].classes(remove='opacity-100 opacity-15 opacity-40 animate-pulse')
                    refs['emoji'].classes(add=ghost_opacity_class)
                    refs['emoji'].style('transform: scale(1);')
                    refs['icon_bg'].style('background-color: #374151; box-shadow: none;')
                    refs['text'].classes(remove='opacity-100 opacity-15 opacity-40')
                    refs['text'].classes(add=ghost_opacity_class)
                    refs['text'].style('color: inherit; font-weight: 400;')

            # Update connectors - light up with GOLD when data flows through
            stage_order = [s['id'] for s in PIPELINE_STAGES]
            active_index = stage_order.index(active_stage) if active_stage in stage_order else -1

            for i, conn in enumerate(connector_refs):
                if active_index > i:
                    # Connector is before active stage - lit up gold (data has passed)
                    conn['element'].classes(remove='opacity-15 opacity-40')
                    conn['element'].classes(add='opacity-80')
                    conn['element'].style(f'background-color: {PTO_GOLD};')
                elif active_index == i:
                    # Connector leads to active stage - bright gold, pulsing
                    conn['element'].classes(remove='opacity-15 opacity-40')
                    conn['element'].classes(add='opacity-100 animate-pulse')
                    conn['element'].style(f'background-color: {PTO_GOLD};')
                else:
                    # Connector is after active stage - ghost mode
                    conn['element'].classes(remove='opacity-100 opacity-80 opacity-15 opacity-40 animate-pulse')
                    conn['element'].classes(add=ghost_opacity_class)
                    conn['element'].style('background-color: #4b5563;')

        def update_pipeline(active_stage: str = None):
            """Update the pipeline to highlight the active stage.

            Args:
                active_stage: One of 'transcribing', 'processing', 'generating', 'speaking', or None for idle
            """
            pipeline_state['current_stage'] = active_stage

            if active_stage is None:
                # Reset to idle state (but keep visible)
                pipeline_state['recording'] = False
                pipeline_state['thinking'] = False
                pipeline_state['playing'] = False
            else:
                # Update state flags based on stage
                pipeline_state['recording'] = (active_stage == 'transcribing')
                pipeline_state['thinking'] = (active_stage in ['processing', 'generating'])
                pipeline_state['playing'] = (active_stage == 'speaking')

            # Update the UI
            update_pipeline_ui()

        def set_pipeline_voice_mode(enabled: bool):
            """Set voice mode state and update pipeline opacity accordingly."""
            pipeline_state['voice_mode'] = enabled
            update_pipeline_ui()

        async def play_tts_response(text: str, max_chars: int = 300, full_text: bool = False):
            """Play TTS for the given text (auto-play when voice mode is on).

            Args:
                text: Text to convert to speech
                max_chars: Max characters to send to TTS (reduces latency for long responses)
                full_text: If True, play the entire response (used for manual speaker clicks)
            """
            # Show 'speaking' stage in pipeline
            update_pipeline('speaking')

            # Clean text for TTS
            clean_text = text.replace('**', '').replace('*', '').replace('#', '').replace('\n', ' ').strip()

            # Truncate to max_chars for performance UNLESS full_text is requested
            if not full_text and len(clean_text) > max_chars:
                # Try to break at a sentence boundary
                truncated = clean_text[:max_chars]
                last_period = truncated.rfind('.')
                last_question = truncated.rfind('?')
                last_exclaim = truncated.rfind('!')
                best_break = max(last_period, last_question, last_exclaim)
                if best_break > max_chars // 2:
                    clean_text = truncated[:best_break + 1]
                else:
                    clean_text = truncated + '...'
                logger.info(f"TTS truncated from {len(text)} to {len(clean_text)} chars for performance")
            elif full_text:
                logger.info(f"TTS playing full response ({len(clean_text)} chars)")

            # Try OpenAI TTS with 'nova' voice (more natural than 'onyx')
            try:
                from src.services.voice.voice_interface import get_voice_interface
                import asyncio

                # Use 'nova' for a more natural, friendly tone
                voice_interface = get_voice_interface('nova')

                # Set a timeout to prevent hanging on slow API responses
                try:
                    audio_path = await asyncio.wait_for(
                        voice_interface.text_to_speech(clean_text),
                        timeout=10.0  # 10 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("OpenAI TTS timed out after 10s, falling back to browser")
                    raise Exception("TTS timeout")

                if audio_path:
                    audio_url = voice_interface.get_audio_url(audio_path.name)
                    # Use the new playAudio function for stop/interrupt support
                    await ui.run_javascript(f'window.ptoVoice.playAudio("{audio_url}")')
                    # Hide pipeline after a short delay (audio plays async)
                    await asyncio.sleep(0.5)
                    update_pipeline(None)
                    return True

            except Exception as e:
                logger.warning(f"OpenAI TTS failed, falling back to browser: {e}")

            # Fallback to browser TTS (SpeechSynthesis API) - always works, no API needed
            await ui.run_javascript(f'''
                console.log('[PTO Voice] Using browser TTS fallback');
                window.ptoVoice.stopAudio();  // Stop any existing audio first
                const utterance = new SpeechSynthesisUtterance({repr(clean_text)});
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                window.speechSynthesis.speak(utterance);
            ''')
            # Hide pipeline after a short delay
            await asyncio.sleep(0.5)
            update_pipeline(None)
            return True

        def process_message(message: str):
            """Process user message through the agent."""
            if agent_state['loading']:
                return

            agent_state['loading'] = True
            show_thinking(True)

            # Show 'processing' stage in pipeline
            update_pipeline('processing')

            # Show loading indicator in chat
            with chat_container:
                loading_row = ui.row().classes('items-center gap-2')
                with loading_row:
                    ui.spinner(size='sm').style(f'color: {PTO_GOLD};')
                    ui.label('Thinking...').classes('opacity-60')

            async def do_process():
                """Async processing of message."""
                try:
                    # Show 'generating' stage when agent starts processing
                    update_pipeline('generating')

                    agent = get_agent()
                    if agent is None:
                        show_error(f"Could not initialize AI assistant: {agent_state['error']}")
                        update_pipeline(None)  # Hide pipeline on error
                        return

                    # Process through agent in a thread to avoid blocking websocket
                    result = await asyncio.to_thread(agent.process_message, message)

                    # Remove loading indicator
                    loading_row.delete()
                    show_thinking(False)

                    # Add assistant response
                    response_text = result.get('response', 'No response')
                    add_chat_message('assistant', response_text)

                    # AUTO-TTS: If voice mode is enabled, automatically play the response
                    # (play_tts_response will update pipeline to 'speaking' then hide it)
                    if voice_enabled.get('value', False):
                        logger.info("Voice mode active - auto-playing TTS response")
                        await play_tts_response(response_text)
                    else:
                        # No TTS - hide pipeline now
                        update_pipeline(None)

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
                    show_thinking(False)
                    update_pipeline(None)  # Hide pipeline on error
                    logger.error(f"Agent error: {e}")
                    add_chat_message('assistant', f"I encountered an error: {str(e)}")
                finally:
                    agent_state['loading'] = False

            ui.timer(0.1, do_process, once=True)

        def send_message():
            """Handle send button click."""
            if not input_ref['field']:
                return
            message = input_ref['field'].value.strip()
            if not message:
                return

            # Clear input
            input_ref['field'].value = ''

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

        # ================================================================
        # INPUT AREA - NUCLEAR REBUILD APPROACH
        # ================================================================

        # Container that we'll rebuild when voice toggles
        input_container = ui.row().classes('w-full items-center gap-3 mt-4')

        # Track voice state (simpler dict)
        voice_enabled = {'value': False, 'recording': False}

        # Reference to input field for send_message
        input_ref = {'field': None}

        def show_voice_commands_help():
            """Show help dialog with available voice commands and pipeline explanation."""
            with ui.dialog() as help_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 550px; max-width: 650px;'):
                ui.label('🎤 Voice Assistant Guide').classes('text-xl font-bold mb-4')

                # ========================================
                # UNDERSTANDING THE PIPELINE SECTION
                # ========================================
                with ui.expansion('Understanding the Pipeline', icon='timeline').classes('w-full mb-4').style(
                    f'background-color: #374151; border-left: 3px solid {PTO_GOLD};'
                ):
                    with ui.column().classes('gap-3 p-3'):
                        ui.label('The pipeline shows real-time processing status:').classes('opacity-80 text-sm mb-2')

                        # Pipeline stages explanation
                        pipeline_info = [
                            ('🎙️', 'Mic (Transcribing)', '#ef4444', 'Your voice is being captured and converted to text'),
                            ('⚡', 'Bridge (Processing)', '#f59e0b', 'Text is being sent from browser to AI backend'),
                            ('🧠', 'AI (Generating)', '#8b5cf6', 'AI agent is thinking and formulating a response'),
                            ('🔊', 'Speaker (Speaking)', '#22c55e', 'Response is being converted to speech and played'),
                        ]

                        for emoji, label, color, desc in pipeline_info:
                            with ui.row().classes('items-center gap-3'):
                                with ui.element('div').classes('rounded-full p-2').style(f'background-color: {color}20;'):
                                    ui.label(emoji).classes('text-lg')
                                with ui.column().classes('gap-0'):
                                    ui.label(label).classes('font-semibold text-sm').style(f'color: {color};')
                                    ui.label(desc).classes('text-xs opacity-70')

                        ui.separator().classes('my-2')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('info', size='sm').style(f'color: {PTO_GOLD};')
                            ui.label('Connecting lines light up gold as data flows through each stage.').classes('text-xs opacity-60 italic')

                # ========================================
                # VOICE COMMANDS SECTION
                # ========================================
                ui.label('Voice Commands').classes('font-semibold mt-2 mb-2')
                ui.label('Say any of these commands while voice mode is active:').classes('opacity-70 mb-3 text-sm')

                # Commands table
                with ui.element('table').classes('w-full').style('border-collapse: collapse;'):
                    # Header row
                    with ui.element('thead'):
                        with ui.element('tr').style('border-bottom: 1px solid #4b5563;'):
                            ui.element('th').classes('text-left p-2 text-amber-400').style('width: 40%;').props('innerHTML="Command"')
                            ui.element('th').classes('text-left p-2 text-amber-400').props('innerHTML="Action"')

                    # Body rows
                    with ui.element('tbody'):
                        commands_data = [
                            ('"Clear chat" / "New chat"', 'Start a fresh conversation'),
                            ('"Go back" / "Go home"', 'Return to dashboard'),
                            ('"Log out" / "Sign out"', 'Sign out of the app'),
                            ('"Dark mode"', 'Switch to dark theme'),
                            ('"Light mode"', 'Switch to light theme'),
                            ('"Stop" / "Be quiet"', 'Stop audio playback'),
                            ('"Help" / "Voice commands"', 'Show this reference'),
                        ]
                        for cmd, action in commands_data:
                            with ui.element('tr').style('border-bottom: 1px solid #374151;'):
                                ui.element('td').classes('p-2 font-mono text-sm').style('color: #fbbf24;').props(f'innerHTML="{cmd}"')
                                ui.element('td').classes('p-2 opacity-80 text-sm').props(f'innerHTML="{action}"')

                ui.button('Close', on_click=help_dialog.close).classes('mt-4').style(
                    f'background-color: {PTO_GOLD} !important; color: white !important;'
                )
            help_dialog.open()

        def build_input_area(with_voice: bool):
            """Build the input area with or without voice controls."""
            input_container.clear()

            # Update pipeline voice mode (affects base opacity)
            set_pipeline_voice_mode(with_voice)

            # Reset pipeline to idle state
            pipeline_state['current_stage'] = None
            pipeline_state['recording'] = False
            pipeline_state['thinking'] = False
            pipeline_state['playing'] = False
            update_pipeline_ui()

            with input_container:
                # Voice toggle (always present) with descriptive tooltip
                def on_toggle(e):
                    voice_enabled['value'] = e.value
                    voice_enabled['recording'] = False
                    build_input_area(e.value)  # REBUILD!
                    if e.value:
                        ui.notify('🎤 Voice ON - click mic to speak', type='info')

                ui.switch('', value=with_voice, on_change=on_toggle).tooltip(
                    'Enable voice mode for hands-free interaction. Speak to input text and hear responses.'
                )

                # Info button (?) - shows voice commands help
                ui.button(icon='help_outline', on_click=show_voice_commands_help).props(
                    'round fab-mini flat'
                ).style(f'color: {PTO_GOLD} !important;').tooltip(
                    'View available voice commands and how voice mode works'
                )

                if with_voice:
                    # === MIC BUTTON (only when voice enabled) ===
                    async def on_mic():
                        if voice_enabled['recording']:
                            # Stop recording
                            voice_enabled['recording'] = False
                            build_input_area(True)  # Rebuild to show amber mic
                            await ui.run_javascript('window.ptoVoice && window.ptoVoice.stop()')
                        else:
                            # Start recording - STOP any playing audio first (so AI doesn't talk over user)
                            await ui.run_javascript('window.ptoVoice && window.ptoVoice.stopAudio()')
                            voice_enabled['recording'] = True
                            # Show 'transcribing' stage in pipeline
                            update_pipeline('transcribing')
                            build_input_area(True)  # Rebuild to show red mic
                            await ui.run_javascript('window.ptoVoice && window.ptoVoice.start()')
                            ui.notify('🎤 Listening...', type='info')

                    mic_color = 'red' if voice_enabled['recording'] else 'amber'
                    ui.button(icon='mic', on_click=on_mic).props(f'round fab-mini color={mic_color}').tooltip('Speak')

                    # Recording indicator (only when recording)
                    if voice_enabled['recording']:
                        with ui.row().classes('items-center gap-1'):
                            ui.spinner('audio', size='sm', color='red')
                            ui.label('Listening...').classes('text-red-400 text-xs')

                # === TEXT INPUT (always present) - with stable ID for voice targeting ===
                msg_input = ui.input(placeholder='Ask about your PTO...').classes('flex-grow chat-input-field').props('outlined dense')
                input_ref['field'] = msg_input

                # === SEND BUTTON (always present) ===
                async def on_send():
                    # Show 'transcribing' stage if voice mode is active
                    if voice_enabled.get('value', False):
                        update_pipeline('transcribing')

                    # Small delay to ensure browser-to-Python value sync
                    await asyncio.sleep(0.1)

                    # Try to get text from Python binding first
                    text = msg_input.value if msg_input.value else ''

                    # If empty, try to fetch from JavaScript (voice input may not have synced)
                    if not text.strip():
                        js_text = await ui.run_javascript('window.ptoVoice.getLastTranscript()')
                        if js_text and js_text.strip():
                            text = js_text
                            logger.info(f"Using JS transcript: {text}")
                            # Clear the JS transcript
                            await ui.run_javascript('window.ptoVoice.clearTranscript()')

                    if text and text.strip():
                        msg_input.value = ''
                        # Clear recording state if user was speaking
                        if voice_enabled['recording']:
                            voice_enabled['recording'] = False
                            await ui.run_javascript('window.ptoVoice && window.ptoVoice.stop()')
                            build_input_area(voice_enabled['value'])  # Rebuild to reset mic state
                        # Add user message and process
                        add_chat_message('user', text.strip())
                        process_message(text.strip())
                    else:
                        # No text to send - hide pipeline if it was shown
                        update_pipeline(None)

                # Send button with class for JS targeting
                ui.button(icon='send', on_click=on_send).props('round fab-mini color=amber').classes('voice-send-btn').tooltip('Send')
                msg_input.on('keydown.enter', on_send)

                if with_voice:
                    # === SPEAKER BUTTON (only when voice enabled) - toggles play/stop ===
                    async def on_speaker():
                        # Check if audio is currently playing
                        is_playing = await ui.run_javascript('window.ptoVoice.getIsPlaying()')

                        if is_playing:
                            # STOP the audio (JS handles visual reset automatically)
                            await ui.run_javascript('window.ptoVoice.stopAudio()')
                            ui.notify('⏹️ Audio stopped', type='info')
                            return

                        # Not playing - find last assistant message and play it
                        last_msg = None
                        for m in reversed(chat_messages):
                            if isinstance(m, dict) and m.get('role') == 'assistant':
                                last_msg = m.get('content', '')
                                break

                        if not last_msg:
                            ui.notify('No response to play', type='warning')
                            return

                        ui.notify('🔊 Generating audio...', type='info')

                        # Use full_text=True for manual speaker clicks (play entire response)
                        # JS playAudio() automatically handles visual feedback
                        await play_tts_response(last_msg, full_text=True)
                        ui.notify('🔊 Playing full response...', type='positive')

                    ui.button(icon='volume_up', on_click=on_speaker).props('round fab-mini color=amber').classes('voice-speaker-btn').tooltip('Play/Stop')

                # === CLEAR BUTTON (always present) ===
                ui.button('Clear', icon='delete', on_click=clear_history).props('flat').style(f'color: {PTO_GOLD} !important;')

        # Initial build (no voice)
        build_input_area(False)

        # ================================================================
        # LIVE PIPELINE - Visual progress indicator
        # Positioned directly below input area for immediate visibility
        # Always visible in "ghost mode" (opacity-15 idle, opacity-100 when active)
        # ================================================================
        pipeline_container = ui.row().classes(
            'w-full items-center justify-center gap-4 py-2 px-4 rounded-lg mt-2'
        ).style('background-color: #1f2937; height: 60px;')
        pipeline_container_ref['container'] = pipeline_container

        def build_live_pipeline():
            """Build the live pipeline UI with connecting lines."""
            pipeline_container.clear()
            pipeline_refs.clear()
            connector_refs.clear()

            with pipeline_container:
                for i, stage in enumerate(PIPELINE_STAGES):
                    # Create stage container with icon and label
                    with ui.column().classes('items-center gap-0') as stage_col:
                        # Icon container with background circle
                        with ui.element('div').classes(
                            'rounded-full p-2 transition-all duration-300'
                        ).style('background-color: #374151;') as icon_bg:
                            # Ghost mode: opacity-15 by default
                            emoji_label = ui.label(stage['emoji']).classes(
                                'text-xl transition-all duration-300 opacity-15'
                            )

                        # Stage label - ghost mode opacity
                        text_label = ui.label(stage['label']).classes(
                            'text-xs transition-all duration-300 opacity-15'
                        )

                        # Store references
                        pipeline_refs[stage['id']] = {
                            'container': stage_col,
                            'icon_bg': icon_bg,
                            'emoji': emoji_label,
                            'text': text_label,
                            'color': stage['color'],
                            'state_key': stage.get('state_key')
                        }

                    # Add connecting line between stages (except after last)
                    if i < len(PIPELINE_STAGES) - 1:
                        # Ghost mode: dull gray connector at low opacity
                        connector = ui.element('div').classes(
                            'h-0.5 w-8 rounded transition-all duration-300 opacity-15'
                        ).style('background-color: #4b5563;')
                        connector_refs.append({
                            'element': connector,
                            'from_stage': stage['id'],
                            'to_stage': PIPELINE_STAGES[i + 1]['id']
                        })

        # Build the pipeline UI
        build_live_pipeline()

        # ================================================================
        # VOICE COMMAND HANDLER
        # ================================================================

        # Store for pending voice command (set by JS, consumed by Python timer)
        voice_command_state = {'pending': None}

        async def handle_voice_command(command: str):
            """Handle a voice command from JavaScript."""
            logger.info(f"Voice command received: {command}")

            # Command handlers with visual feedback
            command_labels = {
                'clear_chat': '🗑️ Clear Chat',
                'go_back': '🏠 Go Back',
                'logout': '🚪 Logout',
                'dark_mode': '🌙 Dark Mode',
                'light_mode': '☀️ Light Mode',
                'stop_audio': '🔇 Stop Audio',
                'help': '❓ Help',
            }

            label = command_labels.get(command, command)
            ui.notify(f'✨ Command: {label}', type='positive', timeout=2000)

            # Execute the command
            if command == 'clear_chat':
                clear_history()

            elif command == 'go_back':
                ui.navigate.to('/dashboard')

            elif command == 'logout':
                # Clear session and redirect to login
                app.storage.user.clear()
                ui.navigate.to('/')

            elif command == 'dark_mode':
                app.storage.general['dark_mode'] = True
                apply_dark_mode()
                ui.notify('🌙 Dark mode enabled', type='info')

            elif command == 'light_mode':
                app.storage.general['dark_mode'] = False
                # Refresh to apply light mode
                ui.navigate.to('/assistant')

            elif command == 'stop_audio':
                await ui.run_javascript('window.ptoVoice.stopAudio()')
                ui.notify('🔇 Audio stopped', type='info')

            elif command == 'help':
                # Show help dialog with available commands
                with ui.dialog() as help_dialog, ui.card().classes('p-6').style('background-color: #1f2937; min-width: 400px;'):
                    ui.label('🎤 Voice Commands').classes('text-xl font-bold mb-4')
                    with ui.column().classes('gap-2'):
                        commands_list = [
                            ('"Clear chat"', 'Start a new conversation'),
                            ('"Go back"', 'Return to dashboard'),
                            ('"Log out"', 'Sign out of the app'),
                            ('"Dark mode"', 'Switch to dark theme'),
                            ('"Light mode"', 'Switch to light theme'),
                            ('"Stop"', 'Stop audio playback'),
                            ('"Help"', 'Show this help'),
                        ]
                        for cmd, desc in commands_list:
                            with ui.row().classes('items-center gap-2'):
                                ui.label(cmd).classes('font-mono text-amber-400')
                                ui.label(f'- {desc}').classes('opacity-70')
                    ui.button('Close', on_click=help_dialog.close).classes('mt-4').style(
                        f'background-color: {PTO_GOLD} !important; color: white !important;'
                    )
                help_dialog.open()

        # Poll for voice commands from JavaScript (runs every 200ms when voice is enabled)
        async def check_voice_commands():
            """Check for pending voice commands from JavaScript."""
            if not voice_enabled.get('value', False):
                return  # Only check when voice mode is on

            try:
                # Check if there's a pending command in JavaScript
                command = await ui.run_javascript('''
                    const cmd = window.ptoVoice._pendingCommand;
                    window.ptoVoice._pendingCommand = null;
                    return cmd;
                ''')
                if command:
                    await handle_voice_command(command)
            except Exception as e:
                logger.debug(f"Voice command check error: {e}")

        # Timer to poll for voice commands
        ui.timer(0.2, check_voice_commands)

        # Update the JavaScript executeCommand to store the command for Python to pick up
        ui.run_javascript('''
            // Override executeCommand to store pending command for Python polling
            window.ptoVoice.executeCommand = function(command) {
                console.log('[PTO Voice] Storing command for Python:', command);
                this._pendingCommand = command;

                // Clear the input field
                const wrapper = document.querySelector('.chat-input-field');
                if (wrapper) {
                    const innerInput = wrapper.querySelector('input') || wrapper;
                    innerInput.value = '';
                    innerInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            };
        ''')

        # Quick action suggestions (agent-specific)
        suggestions_container = ui.row().classes('w-full gap-2 mt-2 flex-wrap')

        def quick_ask(question: str):
            if input_ref['field']:
                input_ref['field'].value = question
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

        # ================================================================
        # UNDER THE HOOD - Technical Architecture Expansion
        # ================================================================
        with ui.expansion(
            'How this works (Technical Architecture)',
            icon='architecture'
        ).classes('w-full mt-6').style('background-color: #374151; border-radius: 8px;'):
            with ui.column().classes('gap-4 p-4'):
                ui.label('Voice-Enabled AI Assistant Data Flow').classes('text-lg font-semibold mb-2')

                # Data flow diagram using cards
                flow_steps = [
                    {
                        'icon': 'mic',
                        'emoji': '🎤',
                        'title': 'Input: Voice Recognition',
                        'tech': 'Web Speech API (Browser)',
                        'desc': 'Browser captures your voice and converts speech to text in real-time using the SpeechRecognition API.',
                        'color': '#ef4444'
                    },
                    {
                        'icon': 'bolt',
                        'emoji': '⚡',
                        'title': 'Processing: Command Parser',
                        'tech': 'JavaScript → Python State Sync',
                        'desc': 'JavaScript parses voice commands (e.g., "clear chat") and syncs text to Python via NiceGUI\'s reactive binding.',
                        'color': '#f59e0b'
                    },
                    {
                        'icon': 'psychology',
                        'emoji': '🧠',
                        'title': 'Intelligence: AI Agent',
                        'tech': 'OpenAI GPT-4o / Claude Sonnet',
                        'desc': 'Your message is processed by an AI agent with access to PTO tools: balance lookups, date optimization, and request creation.',
                        'color': '#8b5cf6'
                    },
                    {
                        'icon': 'volume_up',
                        'emoji': '🔊',
                        'title': 'Output: Text-to-Speech',
                        'tech': 'OpenAI TTS (Nova) → HTML5 Audio',
                        'desc': 'AI responses are converted to natural speech using OpenAI\'s TTS API with the "Nova" voice, played via HTML5 Audio.',
                        'color': '#22c55e'
                    }
                ]

                for step in flow_steps:
                    with ui.card().classes('w-full p-3').style(f'background-color: #1f2937; border-left: 4px solid {step["color"]};'):
                        with ui.row().classes('items-center gap-3'):
                            ui.label(step['emoji']).classes('text-2xl')
                            with ui.column().classes('gap-1 flex-grow'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(step['title']).classes('font-semibold')
                                    ui.badge(step['tech']).props('outline').style(f'color: {step["color"]}; border-color: {step["color"]};')
                                ui.label(step['desc']).classes('text-sm opacity-70')

                # Arrow indicators between steps (visual connector)
                ui.separator().classes('my-2')

                # Technology stack summary
                with ui.row().classes('w-full flex-wrap gap-4 mt-2'):
                    tech_badges = [
                        ('NiceGUI', 'Python web framework'),
                        ('Quasar', 'Vue.js UI components'),
                        ('OpenAI API', 'GPT-4o & TTS'),
                        ('Web Speech API', 'Browser voice I/O'),
                    ]
                    for name, desc in tech_badges:
                        with ui.column().classes('items-center'):
                            ui.badge(name).style(f'background-color: {PTO_GOLD} !important;')
                            ui.label(desc).classes('text-xs opacity-60')

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
