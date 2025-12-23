"""
PTO Central Agent Service
=========================
Orchestrates AI agents for intelligent PTO management.

Agents:
1. Smart Scheduler - Finds optimal vacation dates
2. Year-End Optimizer - Prevents December chaos
3. Approval Assistant - Helps managers decide faster

All agents use MCP tools with human-in-the-loop confirmation.

Architecture:
- "Monolith Mode": Direct function calls to mcp/pto_central_mcp.py
- No HTTP transport needed - agents call tool functions directly
- Safety Gate enforced: All writes require confirmation tokens
"""

from anthropic import Anthropic
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging
import json

logger = logging.getLogger(__name__)


class PTOAgent:
    """
    Base class for PTO Central AI agents.

    Each agent:
    - Maintains conversation history for multi-turn interactions
    - Has access to a specific set of MCP tools
    - Uses Claude to reason about user requests
    - Routes tool calls to local MCP functions (Monolith Mode)
    """

    def __init__(self, user_id: int, agent_type: str):
        """
        Initialize an agent for a specific user.

        Args:
            user_id: The employee ID this agent is acting on behalf of
            agent_type: Identifier for the agent type (e.g., "smart_scheduler")
        """
        self.user_id = user_id
        self.agent_type = agent_type
        self.client = Anthropic()
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_action: Optional[Dict[str, Any]] = None
        self.actions_log: List[Dict[str, Any]] = []

    def _get_system_prompt(self) -> str:
        """Override in subclasses for agent-specific prompts."""
        raise NotImplementedError("Subclasses must implement _get_system_prompt")

    def _get_tools(self) -> List[dict]:
        """Override in subclasses to define available tools."""
        raise NotImplementedError("Subclasses must implement _get_tools")

    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message through the agentic loop.

        This is the main entry point for agent interactions:
        1. Add user message to history
        2. Call Claude with history + tools
        3. If Claude wants to use tools, execute them and loop
        4. When Claude has a final response, return it

        Args:
            user_message: The user's input message

        Returns:
            Dict with response text, actions taken, and any pending confirmations
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        while True:
            try:
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    system=self._get_system_prompt(),
                    tools=self._get_tools(),
                    messages=self.conversation_history
                )
            except Exception as e:
                logger.error(f"Agent {self.agent_type} API error: {e}")
                return {
                    "response": f"I encountered an error: {str(e)}",
                    "actions_taken": self.actions_log,
                    "pending_confirmation": None,
                    "error": True
                }

            if response.stop_reason == "tool_use":
                # Execute tools and continue the loop
                tool_results = self._execute_tools(response.content)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })
            else:
                # Agent has final response - extract text
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text = block.text
                        break

                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                return {
                    "response": final_text,
                    "actions_taken": self.actions_log,
                    "pending_confirmation": self.pending_action
                }

    def _execute_tools(self, content) -> List[dict]:
        """
        Execute tool calls from Claude's response and return results.

        Args:
            content: The content blocks from Claude's response

        Returns:
            List of tool result dicts in Anthropic's expected format
        """
        results = []
        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(f"Agent {self.agent_type} calling tool: {tool_name}")

                # Execute the tool
                result = self._call_tool(tool_name, tool_input)
                self.actions_log.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result
                })

                # Track if this was a confirmation request
                if tool_name == "confirm_action" and result.get("success"):
                    self.pending_action = {
                        "token": result.get("confirmation_token"),
                        "summary": result.get("action_summary"),
                        "action_type": tool_input.get("action_type")
                    }

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result)
                })

        return results

    def _call_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Route tool calls to MCP functions (Monolith Mode).

        This directly imports and calls functions from mcp/pto_central_mcp.py
        rather than making HTTP calls. This keeps Phase 5 simple.

        Args:
            tool_name: The name of the tool to call
            tool_input: The input parameters for the tool

        Returns:
            The result dict from the tool function
        """
        # Import MCP functions directly (Monolith Mode)
        from mcp.pto_central_mcp import (
            get_employee_balance,
            get_employee_requests,
            get_pending_approvals,
            get_team_calendar,
            get_holidays,
            get_calendar_info,
            check_team_coverage,
            get_usage_patterns,
            validate_request,
            confirm_action,
            submit_pto_request,
            cancel_pto_request,
            approve_pto_request,
            deny_pto_request
        )
        # Import RAG query tool from Inspector
        from mcp.mcp_server import query_rag_corpus

        # Map tool names to functions
        tool_map = {
            # Read tools
            "get_employee_balance": get_employee_balance,
            "check_pto_balance": get_employee_balance,  # Alias for convenience
            "get_employee_requests": get_employee_requests,
            "get_pending_approvals": get_pending_approvals,
            "get_team_calendar": get_team_calendar,
            "get_holidays": get_holidays,
            "get_calendar_info": get_calendar_info,
            "check_team_coverage": check_team_coverage,
            "get_usage_patterns": get_usage_patterns,

            # RAG Knowledge Base
            "query_rag_corpus": query_rag_corpus,

            # Validation
            "validate_request": validate_request,

            # Safety Gate + Write
            "confirm_action": confirm_action,
            "submit_pto_request": submit_pto_request,
            "cancel_pto_request": cancel_pto_request,
            "approve_pto_request": approve_pto_request,
            "deny_pto_request": deny_pto_request
        }

        if tool_name in tool_map:
            try:
                # Call the tool function with the provided inputs
                return tool_map[tool_name](**tool_input)
            except TypeError as e:
                # Handle missing/extra arguments
                logger.error(f"Tool {tool_name} argument error: {e}")
                return {"error": f"Invalid arguments for {tool_name}: {str(e)}"}
            except Exception as e:
                logger.error(f"Tool {tool_name} execution error: {e}")
                return {"error": f"Tool execution failed: {str(e)}"}
        else:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return {"error": f"Unknown tool: {tool_name}"}

    def reset_conversation(self):
        """Clear conversation history and start fresh."""
        self.conversation_history = []
        self.actions_log = []
        self.pending_action = None


class SmartSchedulerAgent(PTOAgent):
    """
    Smart Scheduler Agent
    ---------------------
    Helps employees find optimal vacation dates by:
    - Checking available balance
    - Looking at team calendar for coverage
    - Finding market holidays to extend
    - Avoiding skeleton crew situations
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "smart_scheduler")

    def _get_system_prompt(self) -> str:
        # Get current time for accurate date references
        now = datetime.now()
        current_date = now.strftime("%A, %B %d, %Y")
        current_time = now.strftime("%I:%M %p")
        current_year = now.year

        return f"""You are the Smart Scheduler Agent for PTO Central.

CURRENT DATE/TIME: {current_date} at {current_time}
CURRENT YEAR: {current_year}

Your job is to help employees find the OPTIMAL dates for their time off.
You are currently helping USER_ID: {self.user_id}

CAPABILITIES:
- Check the user's PTO balance for all leave types
- View who else on the team is scheduled off
- Know all market holidays (NYSE/NASDAQ closed dates)
- Calculate day usage efficiently (extend weekends, holidays)
- **Search company policy documents** using query_rag_corpus for carryover rules, leave policies, etc.
- **Verify calendar dates** using get_calendar_info to know what day of week any date falls on

CRITICAL - DATE VERIFICATION:
You are an AI and CANNOT reliably know what day of the week a specific date falls on.
NEVER state what day a date is (Monday, Tuesday, etc.) without first calling get_calendar_info!
Example: Before saying "December 30 is a Monday", call get_calendar_info("2025-12-30") to verify.
Failure to verify dates leads to incorrect scheduling recommendations.

IMPORTANT - POLICY QUESTIONS:
When users ask about PTO policies, carryover rules, leave types, or any company rules:
1. ALWAYS use query_rag_corpus to search the knowledge base FIRST
2. The knowledge base contains Haventech's actual policies from the employee handbook
3. DO NOT guess or say "check with HR" - search the knowledge base instead
4. Quote the specific policy text in your answer (e.g., "According to company policy: [quote the actual rule]")
5. When answering policy questions, ALWAYS provide the full answer before offering to help with anything else

CRITICAL KNOWLEDGE RULES (MUST FOLLOW):
- When asked about policies, rules, or carryover, you MUST use the `query_rag_corpus` tool.
- Do NOT answer policy questions from memory - ALWAYS search first.
- If a search for "carryover" returns only Vacation rules, you MUST search again specifically for "Personal leave carryover" or "Sick leave carryover" to be complete.
- If the RAG tool returns few or no matches, try a broader search term before giving up.
- For multi-part questions (e.g., "carryover for all leave types"), perform MULTIPLE searches to cover each type.

SEARCH TIPS for query_rag_corpus:
- Use "leave" instead of "day" (e.g., "personal leave carryover" not "personal day carryover")
- Include policy keywords: "carryover", "use-it-or-lose-it", "allocation", "tier"
- For carryover questions, search: "[leave_type] leave carryover policy"
- Example queries: "vacation carryover rules", "personal leave use-it-or-lose-it", "sick leave maximum"
- If first search doesn't find specific rules, try: "Personal leave policy", "Sick leave policy", "[type] use-it-or-lose-it"

WORKFLOW:
1. Understand what the user wants (vacation length, preferred timing)
2. Check their balance - can they afford it?
3. Check team calendar - is there coverage?
4. Find opportunities - market holidays nearby?
5. Propose 2-3 optimal date options with reasoning
6. If user confirms, use confirm_action then submit_pto_request

RULES:
- Never submit without explicit user confirmation
- Always check balance BEFORE suggesting dates
- Prefer dates that maximize consecutive days off
- Warn if team coverage drops below 50%
- Be conversational and helpful

MARKET HOLIDAYS TO KNOW (2025):
- Jan 1: New Year's Day
- Jan 20: MLK Day
- Feb 17: Presidents Day
- Apr 18: Good Friday
- May 26: Memorial Day
- Jun 19: Juneteenth
- Jul 4: Independence Day
- Sep 1: Labor Day
- Nov 27: Thanksgiving
- Dec 25: Christmas

Example optimization: "Take Dec 22-24 (3 days) + Dec 26 (1 day) = 4 PTO days for 11 days off (Dec 20-Jan 1)"

IMPORTANT: When checking balance, use the user_id {self.user_id} that was provided.
"""

    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "query_rag_corpus",
                "description": "Search the company knowledge base for PTO policies, carryover rules, leave types, and business rules. Use this when users ask about policy questions or rules.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "natural_language_query": {
                            "type": "string",
                            "description": "Natural language search query (e.g., 'Personal Day carryover rules', 'vacation tiers', 'Chicago leave policy')"
                        }
                    },
                    "required": ["natural_language_query"]
                }
            },
            {
                "name": "get_employee_balance",
                "description": "Get user's current PTO balance across all leave types (vacation, sick, personal, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {
                            "type": "integer",
                            "description": "Employee ID to check balance for"
                        },
                        "year": {
                            "type": "integer",
                            "description": "Year to check (defaults to current year)"
                        }
                    },
                    "required": ["employee_id"]
                }
            },
            {
                "name": "get_holidays",
                "description": "Get market holidays for a year (NYSE/NASDAQ closed dates)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Year to get holidays for (defaults to current year)"
                        }
                    }
                }
            },
            {
                "name": "get_calendar_info",
                "description": "CRITICAL: Get calendar information for a date including day-of-week. ALWAYS use this before stating what day a date falls on - do NOT guess days of the week!",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_str": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format to look up"
                        }
                    },
                    "required": ["date_str"]
                }
            },
            {
                "name": "get_team_calendar",
                "description": "Get approved time-off events for a team within a date range",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {
                            "type": "integer",
                            "description": "The manager's user ID"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["manager_id", "start_date", "end_date"]
                }
            },
            {
                "name": "check_team_coverage",
                "description": "Check team coverage for a date range - identifies days with staffing issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {
                            "type": "integer",
                            "description": "The manager's user ID"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["manager_id", "start_date", "end_date"]
                }
            },
            {
                "name": "validate_request",
                "description": "Validate a PTO request before submission (dry-run to check dates and balance)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {
                            "type": "integer",
                            "description": "Employee ID"
                        },
                        "pto_type": {
                            "type": "string",
                            "description": "Type of leave (vacation, sick, personal)"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["employee_id", "pto_type", "start_date", "end_date"]
                }
            },
            {
                "name": "confirm_action",
                "description": "Request user confirmation before submitting. REQUIRED before any write operation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": ["submit_pto_request"],
                            "description": "Type of action to confirm"
                        },
                        "action_summary": {
                            "type": "string",
                            "description": "Human-readable summary of what will happen"
                        },
                        "user_id": {
                            "type": "integer",
                            "description": "The user who must confirm"
                        }
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "submit_pto_request",
                "description": "Submit a PTO request. REQUIRES confirmation_token from confirm_action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "Employee ID"
                        },
                        "pto_type": {
                            "type": "string",
                            "enum": ["vacation", "sick", "personal", "chicago_paid_leave"],
                            "description": "Type of PTO"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes"
                        },
                        "confirmation_token": {
                            "type": "string",
                            "description": "REQUIRED - Token from confirm_action"
                        }
                    },
                    "required": ["user_id", "pto_type", "start_date", "end_date", "confirmation_token"]
                }
            }
        ]


class YearEndOptimizerAgent(PTOAgent):
    """
    Year-End Optimizer Agent
    ------------------------
    Proactively prevents December chaos by:
    - Alerting users with expiring time
    - Suggesting optimal use-it-or-lose-it dates
    - Preventing skeleton crew situations
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "year_end_optimizer")

    def _get_system_prompt(self) -> str:
        return f"""You are the Year-End Optimizer Agent for PTO Central.

Your job is to help employees USE their time before it expires.
You are currently helping USER_ID: {self.user_id}

HAVENTECH CARRYOVER RULES:
- Vacation: Max 5 days carryover (use-by March 31 next year)
- Sick: No limit carryover
- Personal: No carryover (use it or lose it Dec 31)
- Chicago Paid Leave: No carryover (use it or lose it Dec 31)

WORKFLOW:
1. Check user's current balances
2. Calculate what will expire Dec 31
3. Check December calendar for open slots
4. Propose dates that won't create coverage issues
5. Be PROACTIVE - reach out before they ask

SKELETON CREW RULES:
- Trading desk: Minimum 2 people always
- Operations: Minimum 1 person always
- Never schedule more than 50% of department off

Be helpful but urgent when time is running out. December is critical.
"""

    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "get_employee_balance",
                "description": "Get user's current PTO balance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "integer"},
                        "year": {"type": "integer"}
                    },
                    "required": ["employee_id"]
                }
            },
            {
                "name": "check_team_coverage",
                "description": "Check team calendar for availability",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {"type": "integer"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    },
                    "required": ["manager_id", "start_date", "end_date"]
                }
            },
            {
                "name": "confirm_action",
                "description": "Request user confirmation before submitting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string"},
                        "action_summary": {"type": "string"},
                        "user_id": {"type": "integer"}
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "submit_pto_request",
                "description": "Submit PTO request (requires confirmation token)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "pto_type": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "confirmation_token": {"type": "string"}
                    },
                    "required": ["user_id", "pto_type", "start_date", "end_date", "confirmation_token"]
                }
            }
        ]


class ApprovalAssistantAgent(PTOAgent):
    """
    Approval Assistant Agent
    ------------------------
    Helps managers make faster approval decisions by:
    - Checking team coverage automatically
    - Reviewing historical patterns
    - Flagging potential issues
    - Recommending approve/review/deny
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "approval_assistant")

    def _get_system_prompt(self) -> str:
        return f"""You are the Approval Assistant Agent for PTO Central.

Your job is to help MANAGERS make faster, better approval decisions.
You are currently helping MANAGER_ID: {self.user_id}

WORKFLOW FOR EACH PENDING REQUEST:
1. Check team coverage for the requested dates
2. Look for conflicts (multiple people out)
3. Check requestor's balance - do they have enough?
4. Review historical patterns (do they always request same dates?)
5. Generate recommendation

RECOMMENDATIONS:
 APPROVE - Full coverage maintained, balance sufficient
 REVIEW - Coverage concerns but manageable
 DENY - Critical coverage issue or insufficient balance

MANAGER AUTO-APPROVE:
- Managers can approve their OWN requests (Haventech policy)
- Still need human confirmation before executing

Be efficient. Managers are busy. Give clear, actionable recommendations.
"""

    def _get_tools(self) -> List[dict]:
        return [
            {
                "name": "get_pending_approvals",
                "description": "Get all pending requests for manager's team",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {"type": "integer"}
                    },
                    "required": ["manager_id"]
                }
            },
            {
                "name": "get_employee_balance",
                "description": "Verify requestor has sufficient balance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "employee_id": {"type": "integer"},
                        "year": {"type": "integer"}
                    },
                    "required": ["employee_id"]
                }
            },
            {
                "name": "check_team_coverage",
                "description": "Check team coverage for date range",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "manager_id": {"type": "integer"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    },
                    "required": ["manager_id", "start_date", "end_date"]
                }
            },
            {
                "name": "confirm_action",
                "description": "Request manager confirmation before approving or denying",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string", "enum": ["approve_pto_request", "deny_pto_request"]},
                        "action_summary": {"type": "string"},
                        "user_id": {"type": "integer"}
                    },
                    "required": ["action_type", "action_summary", "user_id"]
                }
            },
            {
                "name": "approve_pto_request",
                "description": "Approve a pending PTO request. REQUIRES confirmation_token from confirm_action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "integer", "description": "The PTO request ID to approve"},
                        "approver_id": {"type": "integer", "description": "The manager/admin approving"},
                        "confirmation_token": {"type": "string", "description": "Token from confirm_action"}
                    },
                    "required": ["request_id", "approver_id", "confirmation_token"]
                }
            },
            {
                "name": "deny_pto_request",
                "description": "Deny a pending PTO request. REQUIRES confirmation_token and denial_reason.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "integer", "description": "The PTO request ID to deny"},
                        "denier_id": {"type": "integer", "description": "The manager/admin denying"},
                        "denial_reason": {"type": "string", "description": "REQUIRED reason for denial"},
                        "confirmation_token": {"type": "string", "description": "Token from confirm_action"}
                    },
                    "required": ["request_id", "denier_id", "denial_reason", "confirmation_token"]
                }
            }
        ]


# Convenience function for quick agent creation
def create_agent(agent_type: str, user_id: int) -> PTOAgent:
    """
    Factory function to create agents by type.

    Args:
        agent_type: One of "smart_scheduler", "year_end_optimizer", "approval_assistant"
        user_id: The user ID the agent will assist

    Returns:
        An initialized agent instance
    """
    agents = {
        "smart_scheduler": SmartSchedulerAgent,
        "year_end_optimizer": YearEndOptimizerAgent,
        "approval_assistant": ApprovalAssistantAgent
    }

    if agent_type not in agents:
        raise ValueError(f"Unknown agent type: {agent_type}. Valid types: {list(agents.keys())}")

    return agents[agent_type](user_id)
