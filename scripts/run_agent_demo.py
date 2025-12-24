"""
Interactive Agent Demo Script
=============================
Run this to manually test agent conversations in the terminal.

Usage: python scripts/run_agent_demo.py
"""

import sys
from typing import Optional


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*60)
    print("  PTO CENTRAL - AI AGENT DEMO")
    print("="*60)
    print("""
Available agents:
  1. Smart Scheduler    - Find optimal vacation dates
  2. Year-End Optimizer - Use expiring PTO
  3. Approval Assistant - Help with approvals (manager)

Commands:
  /switch <1|2|3>  - Switch agent
  /reset           - Clear conversation
  /quit            - Exit demo
""")


def run_demo():
    """Run the interactive demo."""
    from src.services.agent_service import create_agent

    print_banner()

    # Configuration
    user_id = 1
    agent_types = {
        "1": "smart_scheduler",
        "2": "year_end_optimizer",
        "3": "approval_assistant",
    }
    current_agent_type = "smart_scheduler"

    # Create initial agent
    agent = create_agent(current_agent_type, user_id=user_id)
    print(f"\n[OK] Connected to: {current_agent_type}")
    print(f"  User ID: {user_id}")
    print("\nType your message and press Enter.\n")

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if user_input == "/quit":
                    print("\nGoodbye!")
                    break
                elif user_input == "/reset":
                    agent.reset_conversation()
                    print("\n[OK] Conversation reset\n")
                    continue
                elif user_input.startswith("/switch"):
                    parts = user_input.split()
                    if len(parts) == 2 and parts[1] in agent_types:
                        current_agent_type = agent_types[parts[1]]
                        agent = create_agent(current_agent_type, user_id=user_id)
                        print(f"\n[OK] Switched to: {current_agent_type}\n")
                    else:
                        print("\nUsage: /switch <1|2|3>\n")
                    continue
                else:
                    print("\nUnknown command. Try /quit, /reset, or /switch <1|2|3>\n")
                    continue

            # Send to agent
            print("\nAgent is thinking...")
            result = agent.process_message(user_input)

            # Display response
            print(f"\n[{current_agent_type}]:")
            print("-" * 40)
            print(result['response'])
            print("-" * 40)

            # Show metadata
            if result.get('actions_taken'):
                tools_used = [a['tool'] for a in result['actions_taken']]
                print(f"[Tools used: {', '.join(tools_used)}]")

            if result.get('pending_confirmation'):
                print("\n[!] CONFIRMATION REQUIRED")
                print(f"   Action: {result['pending_confirmation'].get('action_type')}")
                print(f"   Summary: {result['pending_confirmation'].get('summary')}")
                print("   Reply 'yes' to confirm or 'no' to cancel")

            print()

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}\n")


def main():
    """Entry point."""
    try:
        run_demo()
    except Exception as e:
        print(f"Failed to start demo: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
