"""
Tool 3: State-changing actions.

IMPORTANT: This tool returns a confirmation_required payload.
The action is NOT executed until the frontend sends a separate /confirm request.
"""
from typing import Optional
from ..auth import UserContext

# Allowed action types
ACTION_TYPES = {
    "create_escalation",
    "update_ticket_status",
    "add_ticket_note",
    "create_followup_task",
}


def prepare(
    action_type: str,
    details: dict,
    reason: str = "",
    user: UserContext = None,
) -> dict:
    """
    Validate the action and return a confirmation payload.
    Does NOT write to the database.
    """
    if action_type not in ACTION_TYPES:
        return {
            "confirmation_required": False,
            "error": f"Unknown action type: {action_type}. Valid types: {', '.join(ACTION_TYPES)}",
        }

    summary = _build_summary(action_type, details, reason)

    return {
        "confirmation_required": True,
        "action_type": action_type,
        "details": details,
        "reason": reason,
        "summary": summary,
        "requested_by": user.username if user else "unknown",
    }


def execute(
    action_type: str,
    details: dict,
    reason: str = "",
    user: UserContext = None,
) -> dict:
    """Execute the confirmed action against the database."""
    from .. import database as db

    username = user.username if user else "system"

    try:
        if action_type == "create_escalation":
            ticket_id = details.get("ticket_id", "")
            account_id = details.get("account_id", "")
            priority = details.get("priority", "high")

            # Access control: customers can only escalate their own tickets
            if user and user.is_customer:
                ticket = db.get_ticket(ticket_id, requesting_account_id=user.account_id)
                if not ticket:
                    return {"success": False, "error": "Ticket not found or access denied."}
                account_id = user.account_id

            result = db.create_escalation(
                ticket_id=ticket_id,
                account_id=account_id,
                reason=reason or details.get("reason", ""),
                priority=priority,
                created_by=username,
            )
            return {"success": True, "action": "create_escalation", "result": result}

        elif action_type == "update_ticket_status":
            ticket_id = details.get("ticket_id", "")
            new_status = details.get("new_status", "")
            note = details.get("note", reason)

            if user and user.is_customer:
                ticket = db.get_ticket(ticket_id, requesting_account_id=user.account_id)
                if not ticket:
                    return {"success": False, "error": "Ticket not found or access denied."}

            result = db.update_ticket_status(ticket_id, new_status, note, username)
            return {"success": True, "action": "update_ticket_status", "result": result}

        elif action_type == "add_ticket_note":
            ticket_id = details.get("ticket_id", "")
            note = details.get("note", reason)

            if user and user.is_customer:
                ticket = db.get_ticket(ticket_id, requesting_account_id=user.account_id)
                if not ticket:
                    return {"success": False, "error": "Ticket not found or access denied."}

            result = db.add_ticket_note(ticket_id, note, username)
            return {"success": True, "action": "add_ticket_note", "result": result}

        elif action_type == "create_followup_task":
            result = db.create_followup_task(
                ticket_id=details.get("ticket_id", ""),
                description=details.get("description", ""),
                assigned_to=details.get("assigned_to", "support"),
                due_date=details.get("due_date", ""),
                created_by=username,
            )
            return {"success": True, "action": "create_followup_task", "result": result}

        else:
            return {"success": False, "error": f"Unknown action: {action_type}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_summary(action_type: str, details: dict, reason: str) -> str:
    if action_type == "create_escalation":
        return (
            f"Create escalation for ticket **{details.get('ticket_id', '?')}** "
            f"with priority **{details.get('priority', 'high')}**. "
            f"Reason: {reason or details.get('reason', 'not specified')}"
        )
    elif action_type == "update_ticket_status":
        return (
            f"Update ticket **{details.get('ticket_id', '?')}** "
            f"status to **{details.get('new_status', '?')}**."
        )
    elif action_type == "add_ticket_note":
        return (
            f"Add note to ticket **{details.get('ticket_id', '?')}**: "
            f"'{details.get('note', reason)}'"
        )
    elif action_type == "create_followup_task":
        return (
            f"Create follow-up task for ticket **{details.get('ticket_id', '?')}**: "
            f"{details.get('description', '')} (assigned to {details.get('assigned_to', 'support')}, "
            f"due {details.get('due_date', 'TBD')})"
        )
    return f"Perform {action_type} with details: {details}"
