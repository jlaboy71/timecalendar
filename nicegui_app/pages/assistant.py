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

    # ================================================================
    # PREMIUM CSS - Futuristic Glassmorphism & Cyberpunk Effects
    # ================================================================
    ui.add_head_html(f"""
<style>
/* ===== ANIMATIONS ===== */
@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.7; transform: scale(1.1); }}
}}

@keyframes cyber-pulse {{
    0%, 100% {{ box-shadow: 0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor; }}
    50% {{ box-shadow: 0 0 20px currentColor, 0 0 40px currentColor, 0 0 60px currentColor; }}
}}

@keyframes data-flow {{
    0% {{ background-position: 0% 50%; }}
    100% {{ background-position: 200% 50%; }}
}}

@keyframes message-appear {{
    0% {{ opacity: 0; transform: translateY(20px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes glow-border {{
    0%, 100% {{ border-color: rgba(201, 162, 39, 0.3); }}
    50% {{ border-color: rgba(201, 162, 39, 0.6); }}
}}

@keyframes shimmer {{
    0% {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}

/* ===== GLASSMORPHISM BASE ===== */
.glass-panel {{
    background: rgba(30, 30, 40, 0.75) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 0.5px solid rgba(201, 162, 39, 0.25) !important;
    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}}

.glass-panel-glow {{
    background: rgba(30, 30, 40, 0.8) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 0.5px solid rgba(201, 162, 39, 0.35) !important;
    box-shadow:
        0 0 30px rgba(201, 162, 39, 0.1),
        0 8px 32px rgba(0, 0, 0, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    animation: glow-border 3s ease-in-out infinite;
}}

/* ===== CYBERPUNK PIPELINE ===== */
.pipeline-stage {{
    position: relative;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}}

.pipeline-stage-active {{
    filter: drop-shadow(0 0 12px currentColor);
}}

.pipeline-icon-bg {{
    position: relative;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}}

.pipeline-icon-bg::before {{
    content: '';
    position: absolute;
    inset: -4px;
    border-radius: 50%;
    background: transparent;
    transition: all 0.4s ease;
}}

.pipeline-icon-active::before {{
    background: radial-gradient(circle, currentColor 0%, transparent 70%);
    opacity: 0.3;
    animation: cyber-pulse 1.5s ease-in-out infinite;
}}

.data-fiber {{
    position: relative;
    height: 3px !important;
    border-radius: 2px;
    overflow: hidden;
    transition: all 0.4s ease;
}}

.data-fiber::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(201, 162, 39, 0.8) 25%,
        {PTO_GOLD} 50%,
        rgba(201, 162, 39, 0.8) 75%,
        transparent 100%
    );
    background-size: 200% 100%;
    opacity: 0;
    transition: opacity 0.3s ease;
}}

.data-fiber-active::before {{
    opacity: 1;
    animation: data-flow 1s linear infinite;
}}

.data-fiber-glow {{
    box-shadow: 0 0 8px {PTO_GOLD}, 0 0 16px rgba(201, 162, 39, 0.5);
}}

/* ===== PREMIUM CHAT BUBBLES ===== */
.chat-message-wrapper {{
    animation: message-appear 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}}

.chat-bubble-user {{
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%) !important;
    border: 1px solid rgba(201, 162, 39, 0.3) !important;
    border-radius: 16px 16px 4px 16px !important;
    box-shadow:
        0 4px 16px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}}

.chat-bubble-ai {{
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border: 1px solid rgba(139, 92, 246, 0.3) !important;
    border-radius: 16px 16px 16px 4px !important;
    box-shadow:
        0 4px 16px rgba(0, 0, 0, 0.4),
        0 0 20px rgba(139, 92, 246, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}}

.chat-bubble-ai::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.4), transparent);
}}

/* ===== PREMIUM BUTTONS ===== */
.btn-cyber {{
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}}

.btn-cyber::before {{
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.1),
        transparent
    );
    transition: left 0.5s ease;
}}

.btn-cyber:hover::before {{
    left: 100%;
}}

/* ===== SPEAKER BUTTON ANIMATION ===== */
.speaker-playing {{
    background-color: #ef4444 !important;
    animation: pulse 1s infinite !important;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.5) !important;
}}

/* ===== INPUT FIELD PREMIUM ===== */
.premium-input .q-field__control {{
    background: rgba(30, 30, 40, 0.6) !important;
    border: 1px solid rgba(201, 162, 39, 0.2) !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}}

.premium-input .q-field__control:hover {{
    border-color: rgba(201, 162, 39, 0.4) !important;
}}

.premium-input .q-field--focused .q-field__control {{
    border-color: {PTO_GOLD} !important;
    box-shadow: 0 0 16px rgba(201, 162, 39, 0.2) !important;
}}

/* ===== SYSTEM MANUAL DIALOG ===== */
.system-manual {{
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(201, 162, 39, 0.3) !important;
}}

.manual-section {{
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 12px;
    transition: all 0.3s ease;
}}

.manual-section:hover {{
    border-color: rgba(201, 162, 39, 0.3);
    box-shadow: 0 0 20px rgba(201, 162, 39, 0.1);
}}

.spec-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
}}

.spec-table th {{
    background: rgba(201, 162, 39, 0.1);
    border-bottom: 1px solid rgba(201, 162, 39, 0.3);
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    color: {PTO_GOLD};
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
}}

.spec-table td {{
    padding: 12px 16px;
    border-bottom: 1px solid rgba(71, 85, 105, 0.2);
}}

.spec-table tr:hover td {{
    background: rgba(201, 162, 39, 0.05);
}}

/* ===== SCROLL STYLING ===== */
.premium-scroll::-webkit-scrollbar {{
    width: 6px;
}}

.premium-scroll::-webkit-scrollbar-track {{
    background: rgba(30, 30, 40, 0.5);
    border-radius: 3px;
}}

.premium-scroll::-webkit-scrollbar-thumb {{
    background: rgba(201, 162, 39, 0.4);
    border-radius: 3px;
}}

.premium-scroll::-webkit-scrollbar-thumb:hover {{
    background: rgba(201, 162, 39, 0.6);
}}

/* ===== EXPANSION PANEL PREMIUM ===== */
.expansion-premium .q-expansion-item__container {{
    background: rgba(30, 30, 40, 0.6) !important;
    backdrop-filter: blur(8px) !important;
    border: 0.5px solid rgba(201, 162, 39, 0.2) !important;
}}

.expansion-premium .q-item {{
    transition: all 0.3s ease;
}}

.expansion-premium .q-item:hover {{
    background: rgba(201, 162, 39, 0.05) !important;
}}
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

        # Agent selector row with premium glassmorphism
        with ui.row().classes('w-full items-center gap-4 mb-4 p-4 rounded-xl glass-panel'):
            # Agent label with icon
            with ui.row().classes('items-center gap-2'):
                ui.icon('smart_toy', size='1.2rem').style(f'color: {PTO_GOLD}; opacity: 0.7;')
                ui.label('AGENT').classes('text-xs font-bold tracking-widest opacity-60')

            # Build options for dropdown
            agent_options = {
                k: f"{v['name']}"
                for k, v in available_agents.items()
            }

            agent_select = ui.select(
                options=agent_options,
                value='smart_scheduler',
                on_change=lambda e: switch_agent(e.value)
            ).classes('min-w-48 premium-input').props('dense outlined dark')

            # Agent icon and description (updates when agent changes)
            agent_info = AGENTS[agent_state['current_type']]
            with ui.row().classes('items-center gap-3 ml-auto'):
                # Glowing agent icon
                with ui.element('div').classes('rounded-full p-2').style(
                    f'background: radial-gradient(circle, {agent_info["color"]}20 0%, transparent 70%); '
                    f'box-shadow: 0 0 10px {agent_info["color"]}30;'
                ):
                    ui.icon(agent_info['icon'], size='1.2rem').style(f'color: {agent_info["color"]};')
                ui.label(agent_info['description']).classes('text-sm opacity-70')

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

        # Chat container (scrollable) with glassmorphism
        chat_container = ui.column().classes(
            'w-full overflow-y-auto p-5 rounded-xl glass-panel-glow premium-scroll'
        ).style('min-height: 320px; max-height: 55vh;')

        # Store reference to confirmation dialog
        confirmation_dialog_ref = {'dialog': None}

        def add_chat_message(role: str, content: str, avatar: str = None):
            """Add a message to the chat display."""
            chat_messages.append({'role': role, 'content': content})
            render_chat()

        def render_chat():
            """Render all chat messages with premium bubble styling."""
            chat_container.clear()
            current_agent = AGENTS[agent_state['current_type']]
            with chat_container:
                if not chat_messages:
                    # Welcome message - premium styling
                    with ui.column().classes('items-center justify-center py-8 chat-message-wrapper'):
                        # Glowing icon container
                        with ui.element('div').classes('rounded-full p-4 mb-4').style(
                            f'background: radial-gradient(circle, {current_agent["color"]}20 0%, transparent 70%); '
                            f'box-shadow: 0 0 30px {current_agent["color"]}30;'
                        ):
                            ui.icon(current_agent['icon'], size='3rem').style(
                                f'color: {current_agent["color"]};'
                            )
                        ui.label(f"Hi {user_name}!").classes('text-2xl font-light mb-1')
                        ui.label(f"I'm your {current_agent['name']}").classes('text-lg opacity-70 mb-4')
                        with ui.element('div').classes('max-w-lg text-center').style(
                            'background: rgba(30, 41, 59, 0.5); '
                            'border: 1px solid rgba(71, 85, 105, 0.3); '
                            'border-radius: 12px; padding: 16px;'
                        ):
                            ui.label(current_agent['welcome']).classes('opacity-80 text-sm leading-relaxed')
                else:
                    for msg in chat_messages:
                        is_user = msg['role'] == 'user'
                        # Custom premium chat bubble
                        with ui.element('div').classes(
                            f'chat-message-wrapper w-full flex {"justify-end" if is_user else "justify-start"} mb-3'
                        ):
                            with ui.element('div').classes(
                                f'max-w-[80%] {"chat-bubble-user" if is_user else "chat-bubble-ai"} p-4'
                            ).style('position: relative;'):
                                # Header with name
                                with ui.row().classes('items-center gap-2 mb-2'):
                                    if is_user:
                                        ui.icon('person', size='sm').style(f'color: {PTO_GOLD}; opacity: 0.7;')
                                        ui.label('You').classes('text-xs font-semibold opacity-70')
                                    else:
                                        ui.icon(current_agent['icon'], size='sm').style(
                                            f'color: {current_agent["color"]};'
                                        )
                                        ui.label(current_agent['name']).classes('text-xs font-semibold').style(
                                            f'color: {current_agent["color"]}; opacity: 0.8;'
                                        )
                                # Message content
                                ui.markdown(msg['content']).classes('text-sm leading-relaxed')

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
            """Update pipeline UI with cyberpunk effects based on current state.

            Visual states:
            - Ghost mode (idle): Low opacity, grayscale, subtle styling
            - Active stage: Full color, outer glow, pulsing animation
            - Data fibers: Animated gold flow when data is passing through
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

            # Determine base opacity based on voice mode
            voice_mode_on = pipeline_state.get('voice_mode', False)
            ghost_opacity = 'opacity-30' if voice_mode_on else 'opacity-20'

            # Update each stage's appearance with cyberpunk effects
            for stage_id, refs in pipeline_refs.items():
                is_active = (stage_id == active_stage)
                color = refs['color']

                if is_active:
                    # ACTIVE: Full cyberpunk glow effect
                    refs['container'].classes(add='pipeline-stage-active')
                    refs['emoji'].classes(remove='opacity-20 opacity-30')
                    refs['emoji'].classes(add='opacity-100 animate-pulse')
                    refs['emoji'].style('transform: scale(1.15); filter: none;')

                    # Cyberpunk outer glow on icon background
                    refs['icon_bg'].classes(add='pipeline-icon-active')
                    refs['icon_bg'].style(
                        f'background: radial-gradient(circle, {color}30 0%, {color}10 50%, transparent 70%); '
                        f'border: 1px solid {color}80; '
                        f'box-shadow: 0 0 20px {color}60, 0 0 40px {color}30, inset 0 0 15px {color}20; '
                        f'color: {color};'
                    )

                    refs['text'].classes(remove='opacity-20 opacity-30')
                    refs['text'].classes(add='opacity-100')
                    refs['text'].style(f'color: {color}; font-weight: 700; text-shadow: 0 0 10px {color}60;')
                else:
                    # GHOST MODE: Subtle, dimmed appearance
                    refs['container'].classes(remove='pipeline-stage-active')
                    refs['emoji'].classes(remove='opacity-100 opacity-20 opacity-30 animate-pulse')
                    refs['emoji'].classes(add=ghost_opacity)
                    refs['emoji'].style('transform: scale(1); filter: grayscale(50%);')

                    refs['icon_bg'].classes(remove='pipeline-icon-active')
                    refs['icon_bg'].style(
                        'background: linear-gradient(145deg, #2d3748 0%, #1a202c 100%); '
                        'border: 1px solid rgba(75, 85, 99, 0.3); '
                        'box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);'
                    )

                    refs['text'].classes(remove='opacity-100 opacity-20 opacity-30')
                    refs['text'].classes(add=ghost_opacity)
                    refs['text'].style('color: inherit; font-weight: 400; text-shadow: none;')

            # Update data fiber connectors with animated gold flow
            stage_order = [s['id'] for s in PIPELINE_STAGES]
            active_index = stage_order.index(active_stage) if active_stage in stage_order else -1

            for i, conn in enumerate(connector_refs):
                if active_index > i:
                    # Data has passed through - lit gold
                    conn['element'].classes(remove='opacity-20 opacity-30')
                    conn['element'].classes(add='opacity-100 data-fiber-glow')
                    conn['element'].classes(remove='data-fiber-active')
                    conn['element'].style(f'background-color: {PTO_GOLD}; height: 3px;')
                elif active_index == i:
                    # Data currently flowing - animated gold stream
                    conn['element'].classes(remove='opacity-20 opacity-30')
                    conn['element'].classes(add='opacity-100 data-fiber-active data-fiber-glow')
                    conn['element'].style(f'background-color: {PTO_GOLD}; height: 3px;')
                else:
                    # Waiting for data - ghost mode
                    conn['element'].classes(remove='opacity-100 data-fiber-active data-fiber-glow opacity-20 opacity-30')
                    conn['element'].classes(add=ghost_opacity)
                    conn['element'].style('background-color: #374151; height: 3px;')

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
        # INPUT AREA - Premium Glassmorphism Design
        # ================================================================

        # Container that we'll rebuild when voice toggles - premium styling
        input_container = ui.row().classes('w-full items-center gap-3 mt-4 p-3 rounded-xl glass-panel')

        # Track voice state (simpler dict)
        voice_enabled = {'value': False, 'recording': False}

        # Reference to input field for send_message
        input_ref = {'field': None}

        def show_voice_commands_help():
            """Show premium System Intelligence Manual dialog."""
            with ui.dialog().props('maximized') as help_dialog:
                with ui.card().classes('w-full h-full system-manual p-0 overflow-hidden'):
                    # ========================================
                    # HEADER - Executive Branding
                    # ========================================
                    with ui.element('div').classes('w-full py-6 px-8').style(
                        f'background: linear-gradient(135deg, rgba(201, 162, 39, 0.15) 0%, transparent 50%); '
                        f'border-bottom: 1px solid rgba(201, 162, 39, 0.3);'
                    ):
                        with ui.row().classes('items-center justify-between'):
                            with ui.row().classes('items-center gap-4'):
                                # Logo/Icon
                                with ui.element('div').classes('rounded-lg p-3').style(
                                    f'background: linear-gradient(135deg, {PTO_GOLD}30 0%, {PTO_GOLD}10 100%); '
                                    f'border: 1px solid {PTO_GOLD}50;'
                                ):
                                    ui.icon('smart_toy', size='2rem').style(f'color: {PTO_GOLD};')
                                with ui.column().classes('gap-0'):
                                    ui.label('SYSTEM INTELLIGENCE MANUAL').classes(
                                        'text-2xl font-bold tracking-wide'
                                    ).style(f'color: {PTO_GOLD};')
                                    ui.label('PTO Central Voice Assistant • Technical Specification').classes(
                                        'text-sm opacity-60 font-mono'
                                    )
                            # Close button
                            ui.button(icon='close', on_click=help_dialog.close).props(
                                'round flat'
                            ).style('color: white; opacity: 0.7;')

                    # ========================================
                    # CONTENT - Scrollable Manual
                    # ========================================
                    with ui.scroll_area().classes('w-full premium-scroll').style('height: calc(100vh - 120px);'):
                        with ui.column().classes('gap-8 p-8 max-w-5xl mx-auto'):

                            # --- SECTION 1: SYSTEM OVERVIEW ---
                            with ui.element('div').classes('manual-section p-6'):
                                with ui.row().classes('items-center gap-3 mb-4'):
                                    ui.icon('hub', size='1.5rem').style(f'color: {PTO_GOLD};')
                                    ui.label('SYSTEM OVERVIEW').classes(
                                        'text-lg font-bold tracking-wider'
                                    ).style(f'color: {PTO_GOLD};')
                                ui.label(
                                    'The PTO Central Voice Assistant is an AI-powered automation system that enables '
                                    'natural language interaction with your company\'s PTO management platform. '
                                    'Using advanced speech recognition and synthesis, employees can check balances, '
                                    'request time off, and receive intelligent scheduling recommendations—all hands-free.'
                                ).classes('opacity-80 leading-relaxed')

                                # Tech stack badges
                                with ui.row().classes('gap-3 mt-4 flex-wrap'):
                                    for tech, icon in [
                                        ('NiceGUI Framework', 'code'),
                                        ('OpenAI GPT-4o', 'psychology'),
                                        ('Web Speech API', 'mic'),
                                        ('OpenAI TTS', 'volume_up'),
                                    ]:
                                        with ui.element('div').classes('flex items-center gap-2 px-3 py-1 rounded-full').style(
                                            'background: rgba(201, 162, 39, 0.1); border: 1px solid rgba(201, 162, 39, 0.3);'
                                        ):
                                            ui.icon(icon, size='xs').style(f'color: {PTO_GOLD}; opacity: 0.8;')
                                            ui.label(tech).classes('text-xs font-mono')

                            # --- SECTION 2: DATA PIPELINE ---
                            with ui.element('div').classes('manual-section p-6'):
                                with ui.row().classes('items-center gap-3 mb-4'):
                                    ui.icon('timeline', size='1.5rem').style(f'color: {PTO_GOLD};')
                                    ui.label('DATA PROCESSING PIPELINE').classes(
                                        'text-lg font-bold tracking-wider'
                                    ).style(f'color: {PTO_GOLD};')

                                # Pipeline specification table
                                with ui.element('table').classes('spec-table'):
                                    with ui.element('thead'):
                                        with ui.element('tr'):
                                            for header in ['Stage', 'Component', 'Technology', 'Latency']:
                                                ui.element('th').props(f'innerHTML="{header}"')
                                    with ui.element('tbody'):
                                        pipeline_specs = [
                                            ('🎙️', 'TRANSCRIBE', 'Web Speech API', '< 100ms'),
                                            ('⚡', 'BRIDGE', 'WebSocket Sync', '< 50ms'),
                                            ('🧠', 'GENERATE', 'OpenAI GPT-4o', '1-3s'),
                                            ('🔊', 'SYNTHESIZE', 'OpenAI TTS Nova', '< 500ms'),
                                        ]
                                        for emoji, stage, tech, latency in pipeline_specs:
                                            with ui.element('tr'):
                                                ui.element('td').classes('font-mono').props(f'innerHTML="{emoji} {stage}"')
                                                ui.element('td').props(f'innerHTML="{stage}"')
                                                ui.element('td').classes('opacity-70').props(f'innerHTML="{tech}"')
                                                ui.element('td').classes('font-mono text-green-400').props(f'innerHTML="{latency}"')

                                with ui.row().classes('items-center gap-2 mt-4 p-3 rounded-lg').style(
                                    'background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3);'
                                ):
                                    ui.icon('speed', size='sm').classes('text-green-400')
                                    ui.label('Total round-trip latency: 2-4 seconds for complete voice interaction').classes(
                                        'text-sm text-green-400'
                                    )

                            # --- SECTION 3: VOICE COMMANDS ---
                            with ui.element('div').classes('manual-section p-6'):
                                with ui.row().classes('items-center gap-3 mb-4'):
                                    ui.icon('record_voice_over', size='1.5rem').style(f'color: {PTO_GOLD};')
                                    ui.label('VOICE COMMAND REFERENCE').classes(
                                        'text-lg font-bold tracking-wider'
                                    ).style(f'color: {PTO_GOLD};')

                                with ui.element('table').classes('spec-table'):
                                    with ui.element('thead'):
                                        with ui.element('tr'):
                                            for header in ['Command Phrase', 'Action', 'Category']:
                                                ui.element('th').props(f'innerHTML="{header}"')
                                    with ui.element('tbody'):
                                        commands_data = [
                                            ('"Clear chat" / "New chat"', 'Reset conversation', 'Navigation'),
                                            ('"Go back" / "Go home"', 'Return to dashboard', 'Navigation'),
                                            ('"Log out" / "Sign out"', 'End session', 'Auth'),
                                            ('"Dark mode"', 'Enable dark theme', 'Display'),
                                            ('"Light mode"', 'Enable light theme', 'Display'),
                                            ('"Stop" / "Be quiet"', 'Halt audio playback', 'Audio'),
                                            ('"Help"', 'Show this manual', 'System'),
                                        ]
                                        for cmd, action, category in commands_data:
                                            with ui.element('tr'):
                                                ui.element('td').classes('font-mono').style(f'color: {PTO_GOLD};').props(f'innerHTML="{cmd}"')
                                                ui.element('td').classes('opacity-80').props(f'innerHTML="{action}"')
                                                cat_color = {'Navigation': '#3b82f6', 'Auth': '#ef4444', 'Display': '#8b5cf6', 'Audio': '#22c55e', 'System': '#f59e0b'}
                                                ui.element('td').props(f'innerHTML="<span style=\\"color: {cat_color.get(category, PTO_GOLD)};\\">{category}</span>"')

                            # --- SECTION 4: AGENT CAPABILITIES ---
                            with ui.element('div').classes('manual-section p-6'):
                                with ui.row().classes('items-center gap-3 mb-4'):
                                    ui.icon('psychology', size='1.5rem').style(f'color: {PTO_GOLD};')
                                    ui.label('AI AGENT CAPABILITIES').classes(
                                        'text-lg font-bold tracking-wider'
                                    ).style(f'color: {PTO_GOLD};')

                                with ui.row().classes('gap-4 flex-wrap'):
                                    agents_info = [
                                        ('Smart Scheduler', 'event_available', '#4CAF50', 'Optimal vacation planning with holiday awareness'),
                                        ('Year-End Optimizer', 'calendar_month', '#FF9800', 'Prevent PTO loss before December 31st'),
                                        ('Approval Assistant', 'fact_check', '#2196F3', 'Streamline manager approval workflows'),
                                    ]
                                    for name, icon, color, desc in agents_info:
                                        with ui.element('div').classes('flex-1 min-w-[250px] p-4 rounded-lg').style(
                                            f'background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1); '
                                            f'border: 1px solid {color}40;'
                                        ):
                                            with ui.row().classes('items-center gap-2 mb-2'):
                                                ui.icon(icon, size='sm').style(f'color: {color};')
                                                ui.label(name).classes('font-semibold').style(f'color: {color};')
                                            ui.label(desc).classes('text-sm opacity-70')

                            # --- FOOTER ---
                            with ui.element('div').classes('text-center py-6 opacity-50'):
                                ui.label('PTO Central • Enterprise Automation Platform').classes('text-xs font-mono')
                                ui.label('© 2025 Haventech Solutions').classes('text-xs')

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
                msg_input = ui.input(placeholder='Ask about your PTO...').classes('flex-grow chat-input-field premium-input').props('outlined dense dark')
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
        # LIVE PIPELINE - Cyberpunk Visual Progress Indicator
        # Futuristic "data flow" visualization with glowing effects
        # ================================================================
        pipeline_container = ui.row().classes(
            'w-full items-center justify-center gap-6 py-3 px-6 rounded-xl mt-3 glass-panel'
        ).style('height: 70px;')
        pipeline_container_ref['container'] = pipeline_container

        def build_live_pipeline():
            """Build the cyberpunk pipeline UI with data fiber connectors."""
            pipeline_container.clear()
            pipeline_refs.clear()
            connector_refs.clear()

            with pipeline_container:
                for i, stage in enumerate(PIPELINE_STAGES):
                    # Create stage container with cyberpunk styling
                    with ui.column().classes('items-center gap-1 pipeline-stage') as stage_col:
                        # Outer glow container for cyberpunk effect
                        with ui.element('div').classes(
                            'rounded-full p-3 pipeline-icon-bg transition-all duration-300'
                        ).style(
                            f'background: linear-gradient(145deg, #2d3748 0%, #1a202c 100%); '
                            f'border: 1px solid rgba(75, 85, 99, 0.3); '
                            f'box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);'
                        ) as icon_bg:
                            # Emoji with ghost mode opacity
                            emoji_label = ui.label(stage['emoji']).classes(
                                'text-2xl transition-all duration-300 opacity-20'
                            ).style('filter: grayscale(50%);')

                        # Stage label with tech font styling
                        text_label = ui.label(stage['label'].upper()).classes(
                            'text-xs font-mono tracking-wider transition-all duration-300 opacity-20'
                        )

                        # Store references with color info
                        pipeline_refs[stage['id']] = {
                            'container': stage_col,
                            'icon_bg': icon_bg,
                            'emoji': emoji_label,
                            'text': text_label,
                            'color': stage['color'],
                            'state_key': stage.get('state_key')
                        }

                    # Add data fiber connector between stages
                    if i < len(PIPELINE_STAGES) - 1:
                        # Data fiber cable with animated flow when active
                        connector = ui.element('div').classes(
                            'data-fiber w-12 rounded-full transition-all duration-300 opacity-20'
                        ).style('background-color: #374151; height: 3px;')
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
        # UNDER THE HOOD - Premium Technical Architecture Panel
        # ================================================================
        with ui.expansion(
            'Technical Architecture',
            icon='architecture'
        ).classes('w-full mt-6 expansion-premium rounded-xl'):
            with ui.column().classes('gap-5 p-5'):
                # Header with gradient accent
                with ui.element('div').classes('w-full pb-4 mb-2').style(
                    f'border-bottom: 1px solid rgba(201, 162, 39, 0.2);'
                ):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('hub', size='1.5rem').style(f'color: {PTO_GOLD};')
                        ui.label('VOICE-ENABLED AI ASSISTANT').classes(
                            'text-lg font-bold tracking-wider'
                        ).style(f'color: {PTO_GOLD};')
                    ui.label('Real-time data flow architecture').classes('text-sm opacity-60 mt-1 font-mono')

                # Data flow diagram using premium cards
                flow_steps = [
                    {
                        'emoji': '🎙️',
                        'title': 'VOICE CAPTURE',
                        'tech': 'Web Speech API',
                        'desc': 'Real-time speech-to-text conversion using browser\'s native SpeechRecognition engine.',
                        'color': '#ef4444',
                        'latency': '< 100ms'
                    },
                    {
                        'emoji': '⚡',
                        'title': 'STATE BRIDGE',
                        'tech': 'WebSocket Sync',
                        'desc': 'Bidirectional JavaScript↔Python state synchronization via NiceGUI reactive bindings.',
                        'color': '#f59e0b',
                        'latency': '< 50ms'
                    },
                    {
                        'emoji': '🧠',
                        'title': 'AI PROCESSING',
                        'tech': 'OpenAI GPT-4o',
                        'desc': 'Intelligent agent with PTO tools: balance lookup, date optimization, request management.',
                        'color': '#8b5cf6',
                        'latency': '1-3s'
                    },
                    {
                        'emoji': '🔊',
                        'title': 'VOICE OUTPUT',
                        'tech': 'OpenAI TTS Nova',
                        'desc': 'Natural speech synthesis with the Nova voice model, streamed via HTML5 Audio.',
                        'color': '#22c55e',
                        'latency': '< 500ms'
                    }
                ]

                for step in flow_steps:
                    with ui.element('div').classes('w-full p-4 rounded-lg transition-all duration-300').style(
                        f'background: linear-gradient(135deg, {step["color"]}10 0%, transparent 50%); '
                        f'border: 1px solid {step["color"]}30; '
                        f'border-left: 3px solid {step["color"]};'
                    ):
                        with ui.row().classes('items-start gap-4'):
                            # Glowing emoji container
                            with ui.element('div').classes('rounded-full p-3 flex-shrink-0').style(
                                f'background: radial-gradient(circle, {step["color"]}20 0%, transparent 70%); '
                                f'box-shadow: 0 0 15px {step["color"]}30;'
                            ):
                                ui.label(step['emoji']).classes('text-2xl')
                            # Content
                            with ui.column().classes('gap-1 flex-grow'):
                                with ui.row().classes('items-center gap-3'):
                                    ui.label(step['title']).classes('font-bold tracking-wide').style(f'color: {step["color"]};')
                                    with ui.element('div').classes('px-2 py-0.5 rounded-full').style(
                                        f'background: {step["color"]}20; border: 1px solid {step["color"]}40;'
                                    ):
                                        ui.label(step['tech']).classes('text-xs font-mono').style(f'color: {step["color"]};')
                                ui.label(step['desc']).classes('text-sm opacity-70 leading-relaxed')
                            # Latency indicator
                            with ui.element('div').classes('flex-shrink-0 text-right'):
                                ui.label(step['latency']).classes('text-xs font-mono text-green-400')

                # Performance summary
                with ui.element('div').classes('w-full p-4 rounded-lg mt-2').style(
                    'background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3);'
                ):
                    with ui.row().classes('items-center justify-between'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('speed', size='sm').classes('text-green-400')
                            ui.label('Total Round-Trip Latency').classes('text-sm font-semibold text-green-400')
                        ui.label('2-4 seconds').classes('font-mono font-bold text-green-400')

                # Technology stack
                with ui.row().classes('w-full flex-wrap gap-3 mt-2 pt-4').style(
                    'border-top: 1px solid rgba(71, 85, 105, 0.3);'
                ):
                    tech_stack = [
                        ('NiceGUI', 'Framework'),
                        ('Quasar', 'Components'),
                        ('GPT-4o', 'Intelligence'),
                        ('TTS Nova', 'Voice'),
                    ]
                    for name, desc in tech_stack:
                        with ui.element('div').classes('flex items-center gap-2 px-3 py-2 rounded-lg').style(
                            'background: rgba(201, 162, 39, 0.1); border: 1px solid rgba(201, 162, 39, 0.2);'
                        ):
                            ui.label(name).classes('text-sm font-semibold').style(f'color: {PTO_GOLD};')
                            ui.label(f'• {desc}').classes('text-xs opacity-50')

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
