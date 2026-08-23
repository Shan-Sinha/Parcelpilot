"""Tool 2: Structured data lookup from SQLite (ingested from Excel)."""
import json
from typing import Optional
from .. import database as db
from ..auth import UserContext


def run(
    entity: str,
    filters: Optional[dict] = None,
    calculation: Optional[str] = None,
    user: UserContext = None,
) -> dict:
    """
    Query operational data: accounts, orders, tickets.

    Access control:
    - Customer users: automatically scoped to their account_id
    - Internal users: unrestricted
    """
    filters = filters or {}
    req_account = user.account_id if (user and user.is_customer) else None

    try:
        if entity == "account":
            account_id = filters.get("account_id") or req_account
            account_name = filters.get("company_name") or filters.get("account_name")

            if account_id:
                result = db.get_account(account_id, requesting_account_id=req_account)
            elif account_name:
                result = db.get_account_by_name(account_name, requesting_account_id=req_account)
            else:
                result = db.list_accounts(requesting_account_id=req_account)

            if not result:
                return {"found": False, "message": "Account not found or access denied."}
            return {"found": True, "entity": "account", "data": result}

        elif entity == "order":
            order_id = filters.get("order_id")
            if order_id:
                result = db.get_order(order_id, requesting_account_id=req_account)
                if not result:
                    return {"found": False, "message": f"Order {order_id} not found or access denied."}
                return {"found": True, "entity": "order", "data": result}
            else:
                results = db.list_orders(
                    account_id=filters.get("account_id"),
                    status=filters.get("status"),
                    requesting_account_id=req_account,
                )
                return {"found": True, "entity": "orders", "count": len(results), "data": results[:20]}

        elif entity == "ticket":
            ticket_id = filters.get("ticket_id")
            if ticket_id:
                result = db.get_ticket(ticket_id, requesting_account_id=req_account)
                if not result:
                    return {"found": False, "message": f"Ticket {ticket_id} not found or access denied."}
                return {"found": True, "entity": "ticket", "data": result}
            else:
                results = db.list_tickets(
                    account_id=filters.get("account_id"),
                    status=filters.get("status"),
                    priority=filters.get("priority"),
                    requesting_account_id=req_account,
                )
                return {"found": True, "entity": "tickets", "count": len(results), "data": results[:20]}

        elif entity == "tickets_summary":
            summary = db.get_tickets_summary(requesting_account_id=req_account)
            return {"found": True, "entity": "tickets_summary", "data": summary}

        elif entity == "orders_summary":
            orders = db.list_orders(requesting_account_id=req_account)
            by_status: dict = {}
            for o in orders:
                s = o.get("status", "unknown")
                by_status[s] = by_status.get(s, 0) + 1
            return {
                "found": True,
                "entity": "orders_summary",
                "data": {"total": len(orders), "by_status": by_status},
            }

        else:
            return {"found": False, "message": f"Unknown entity type: {entity}"}

    except Exception as e:
        return {"found": False, "message": f"Database error: {str(e)}"}
