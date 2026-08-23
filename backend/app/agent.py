"""
Core agent — OpenAI tool-calling loop with multi-step reasoning.

Supports:
- Multi-step queries (order → account → agreement → policy → calculation)
- Source conflict detection and reliability ranking
- Confirmation gate for state-changing actions
- Full tool call transparency for the UI
"""
import json
from typing import Optional
from openai import OpenAI, AzureOpenAI
from .config import settings
from .auth import UserContext
from .tools import document_search, data_lookup, actions

_client = None


def _get_client():
    global _client
    if _client is None:
        if settings.azure_openai_api_key and settings.azure_openai_endpoint:
            _client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        else:
            _client = OpenAI(api_key=settings.openai_api_key)
    return _client


# ---------------------------------------------------------------------------
# Tool definitions for OpenAI
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search ParcelPilot's documents: policies, SOPs, customer agreements, product guides.\n"
                "Use when you need policy rules, SLA terms, cancellation procedures, service credits, "
                "or customer-specific contract terms.\n"
                "Sources have different authority levels:\n"
                "- Customer enterprise agreements (HIGHEST) override general policies for that customer\n"
                "- Current Support Policy v3 and SOP v4 are authoritative\n"
                "- Deprecated v2 policy has low trust — always prefer the current version\n"
                "- Historical ticket resolutions are context only and MAY be incorrect"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "doc_filter": {
                        "type": "string",
                        "enum": ["all", "policies", "agreements", "sops", "product_guide"],
                        "description": "Optional: filter by document type",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_data",
            "description": (
                "Query ParcelPilot's operational data: accounts, orders, tickets.\n"
                "Use to look up specific orders or tickets by ID, check order status, "
                "retrieve account entitlements, or summarise support activity.\n"
                "IMPORTANT: Customer users are automatically scoped to their own account — "
                "you cannot access other accounts' data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "enum": ["account", "order", "ticket", "orders_summary", "tickets_summary"],
                        "description": "Type of data to look up",
                    },
                    "filters": {
                        "type": "object",
                        "description": (
                            "Filters to apply. Examples:\n"
                            '  {"order_id": "ORD-1001"}\n'
                            '  {"account_id": "ACC-001"}\n'
                            '  {"ticket_id": "TKT-005"}\n'
                            '  {"status": "open"}\n'
                            '  {"company_name": "Northstar"}'
                        ),
                    },
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_action",
            "description": (
                "Create a state-changing action: escalation, ticket update, note, or follow-up task.\n"
                "IMPORTANT: This does NOT execute immediately. It returns a confirmation request "
                "that the user must approve before the action is taken.\n"
                "Always inform the user what you are about to do before calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "create_escalation",
                            "update_ticket_status",
                            "add_ticket_note",
                            "create_followup_task",
                        ],
                        "description": "Type of action",
                    },
                    "details": {
                        "type": "object",
                        "description": (
                            "Action details. Examples:\n"
                            '  create_escalation: {"ticket_id": "TKT-001", "account_id": "ACCT-001", "priority": "high"}\n'
                            '  update_ticket_status: {"ticket_id": "TKT-001", "new_status": "resolved", "note": "..."}\n'
                            '  add_ticket_note: {"ticket_id": "TKT-001", "note": "..."}\n'
                            '  create_followup_task: {"ticket_id": "TKT-001", "description": "...", "assigned_to": "support", "due_date": "2024-12-01"}'
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the action",
                    },
                },
                "required": ["action_type", "details"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(user: UserContext) -> str:
    if user.is_customer:
        context = (
            f"You are ParcelPilot's customer support AI assistant.\n"
            f"You are talking to {user.full_name} from {user.account_name} (Account ID: {user.account_id}).\n"
            f"You can ONLY access data belonging to {user.account_name}. "
            f"Never expose data from other accounts.\n"
            f"Customer-specific agreements for {user.account_name} override general ParcelPilot policies.\n"
        )
    else:
        context = (
            f"You are ParcelPilot's internal AI support assistant.\n"
            f"You are talking to {user.full_name} (Role: {user.role}).\n"
            f"You have full access to all account data. "
            f"When querying on behalf of a specific customer, specify their account_id in filters.\n"
        )

    return f"""{context}

## Source Reliability (follow this order when sources conflict)
1. Customer enterprise agreements — HIGHEST authority for that customer. They override general policies.
2. Support Policy v3 (CURRENT) — authoritative general policy
3. Cancellation & Service Credit SOP v4 — authoritative procedure
4. Product Operations Guide — informational, current
5. Support Policy v2 (DEPRECATED) — LOW trust. Only use if no current source covers the question. Always flag it as deprecated.
6. Historical ticket resolutions — CONTEXT ONLY. May contain incorrect information. Never rely on them for policy answers.

## Behaviour Rules
- When you cite a policy, state which document it comes from and whether it's current or deprecated.
- When a customer agreement overrides general policy, explicitly say so.
- When sources conflict, acknowledge the conflict and explain which source you're following and why.
- If you are not confident enough to answer reliably, say so and offer to escalate.
- For state-changing actions (escalations, ticket updates): always explain what you're about to do, then call create_action. The action requires user confirmation before it executes.
- Never guess account IDs, order IDs, or ticket IDs. Look them up using tools.
- Queries outside your capabilities should be escalated to the support team.

## Current Date Reference
Use the dataset snapshot time from the Excel README sheet as the reference time for age calculations.
"""


# ---------------------------------------------------------------------------
# Main agent function
# ---------------------------------------------------------------------------

def run_agent(
    messages: list[dict],
    user: UserContext,
) -> dict:
    """
    Run the multi-step agent loop.

    Returns:
        {
            "message": str,            # Final response text
            "tool_calls": list[dict],  # All tool calls made with inputs/outputs
            "requires_confirmation": dict | None,  # Set if action is pending
            "sources": list[dict],     # Deduplicated sources from document search
        }
    """
    client = _get_client()
    system_prompt = _build_system_prompt(user)
    model_name = settings.azure_openai_deployment_name if (settings.azure_openai_api_key and settings.azure_openai_endpoint) else settings.model

    # Filter out initial UI greeting messages so they don't pollute prompt history
    filtered_messages = []
    for m in messages:
        if m.get("role") == "assistant" and not filtered_messages and "Support Assistant" in m.get("content", ""):
            continue
        filtered_messages.append(m)

    # Build message list with system prompt
    full_messages = [{"role": "system", "content": system_prompt}] + filtered_messages

    tool_calls_log = []
    all_sources = []
    pending_confirmation = None

    MAX_ITERATIONS = 8

    for iteration in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model_name,
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
        )

        choice = response.choices[0]
        msg = choice.message

        # Add assistant message to history
        full_messages.append(msg.model_dump(exclude_none=True))

        # If no tool calls, we're done
        if not msg.tool_calls:
            return {
                "message": msg.content or "",
                "tool_calls": tool_calls_log,
                "requires_confirmation": pending_confirmation,
                "sources": _deduplicate_sources(all_sources),
            }

        # Process each tool call
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            tool_result = _execute_tool(fn_name, fn_args, user)

            # If action requires confirmation, store it and stop the loop
            if isinstance(tool_result, dict) and tool_result.get("confirmation_required"):
                pending_confirmation = tool_result
                # Give the LLM a message about what happened
                tool_output_str = json.dumps({
                    "status": "confirmation_required",
                    "summary": tool_result.get("summary"),
                    "message": "Action prepared. Awaiting user confirmation before execution.",
                })
            else:
                tool_output_str = json.dumps(tool_result)

            # Log tool call for UI
            log_entry = {
                "tool": fn_name,
                "input": fn_args,
                "output": tool_result,
            }
            tool_calls_log.append(log_entry)

            # Collect document sources
            if fn_name == "search_documents" and isinstance(tool_result, dict):
                all_sources.extend(tool_result.get("sources", []))

            # Add tool result to conversation
            full_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_output_str,
            })

        # If confirmation pending, do one more LLM call to get final message
        if pending_confirmation:
            response2 = client.chat.completions.create(
                model=model_name,
                messages=full_messages,
                temperature=0.1,
            )
            final_msg = response2.choices[0].message.content or ""
            return {
                "message": final_msg,
                "tool_calls": tool_calls_log,
                "requires_confirmation": pending_confirmation,
                "sources": _deduplicate_sources(all_sources),
            }

    # Max iterations reached
    last_content = ""
    for m in reversed(full_messages):
        if m.get("role") == "assistant" and m.get("content"):
            last_content = m["content"]
            break

    return {
        "message": last_content or "I reached my reasoning limit. Please try a more specific question.",
        "tool_calls": tool_calls_log,
        "requires_confirmation": pending_confirmation,
        "sources": _deduplicate_sources(all_sources),
    }


def _execute_tool(fn_name: str, fn_args: dict, user: UserContext) -> dict:
    """Dispatch tool call to the correct tool module."""
    if fn_name == "search_documents":
        return document_search.run(
            query=fn_args.get("query", ""),
            doc_filter=fn_args.get("doc_filter", "all"),
            user=user,
        )
    elif fn_name == "lookup_data":
        return data_lookup.run(
            entity=fn_args.get("entity", ""),
            filters=fn_args.get("filters"),
            calculation=fn_args.get("calculation"),
            user=user,
        )
    elif fn_name == "create_action":
        return actions.prepare(
            action_type=fn_args.get("action_type", ""),
            details=fn_args.get("details", {}),
            reason=fn_args.get("reason", ""),
            user=user,
        )
    else:
        return {"error": f"Unknown tool: {fn_name}"}


def _deduplicate_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for s in sources:
        key = (s.get("source_file"), s.get("page"))
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result
