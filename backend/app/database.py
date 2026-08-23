"""
SQLite database layer — ingested from ParcelPilot_Assessment_Data.xlsx.

All public query methods accept an optional `account_id` filter.
When provided (customer context), queries are restricted to that account.
Internal users pass account_id=None to get unrestricted access.
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from .config import settings


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.resolved_sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _norm_acc(acc_id: Optional[str]) -> Optional[str]:
    if not acc_id:
        return None
    acc_str = str(acc_id).strip()
    if acc_str.startswith("ACC-") and not acc_str.startswith("ACCT-"):
        return acc_str.replace("ACC-", "ACCT-")
    return acc_str


# ---------------------------------------------------------------------------
# Account queries
# ---------------------------------------------------------------------------

def get_account(account_id: str, requesting_account_id: Optional[str] = None) -> Optional[dict]:
    """Fetch an account. Customer users can only fetch their own account."""
    acc_norm = _norm_acc(account_id)
    req_norm = _norm_acc(requesting_account_id)
    if req_norm and req_norm != acc_norm:
        return None  # Access denied — return nothing silently
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE account_id = ? OR account_id = ?",
            (acc_norm, acc_norm.replace("ACCT-", "ACC-") if acc_norm else acc_norm),
        ).fetchone()
    return dict(row) if row else None


def get_account_by_name(name: str, requesting_account_id: Optional[str] = None) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE LOWER(company_name) LIKE LOWER(?)",
            (f"%{name}%",),
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    req_norm = _norm_acc(requesting_account_id)
    rec_acc = _norm_acc(result.get("account_id"))
    if req_norm and rec_acc != req_norm:
        return None
    return result


def list_accounts(requesting_account_id: Optional[str] = None) -> list[dict]:
    req_norm = _norm_acc(requesting_account_id)
    with _get_conn() as conn:
        if req_norm:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE account_id = ? OR account_id = ?",
                (req_norm, req_norm.replace("ACCT-", "ACC-")),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM accounts").fetchall()
    return _rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Order queries
# ---------------------------------------------------------------------------

def get_order(order_id: str, requesting_account_id: Optional[str] = None) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    req_norm = _norm_acc(requesting_account_id)
    rec_acc = _norm_acc(result.get("account_id"))
    if req_norm and rec_acc != req_norm:
        return None  # Silently deny cross-account access
    return result


def list_orders(
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    requesting_account_id: Optional[str] = None,
) -> list[dict]:
    # Enforce account isolation for customers
    effective_account = _norm_acc(requesting_account_id if requesting_account_id else account_id)
    with _get_conn() as conn:
        query = "SELECT * FROM orders WHERE 1=1"
        params: list = []
        if effective_account:
            query += " AND (account_id = ? OR account_id = ?)"
            params.extend([effective_account, effective_account.replace("ACCT-", "ACC-")])
        if status:
            query += " AND LOWER(status) = LOWER(?)"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT 50"
        rows = conn.execute(query, params).fetchall()
    return _rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Ticket queries
# ---------------------------------------------------------------------------

def get_ticket(ticket_id: str, requesting_account_id: Optional[str] = None) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    req_norm = _norm_acc(requesting_account_id)
    rec_acc = _norm_acc(result.get("account_id"))
    if req_norm and rec_acc != req_norm:
        return None
    return result


def list_tickets(
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    requesting_account_id: Optional[str] = None,
) -> list[dict]:
    effective_account = _norm_acc(requesting_account_id if requesting_account_id else account_id)
    with _get_conn() as conn:
        query = "SELECT * FROM tickets WHERE 1=1"
        params: list = []
        if effective_account:
            query += " AND (account_id = ? OR account_id = ?)"
            params.extend([effective_account, effective_account.replace("ACCT-", "ACC-")])
        if status:
            query += " AND LOWER(status) = LOWER(?)"
            params.append(status)
        if priority:
            query += " AND LOWER(priority) = LOWER(?)"
            params.append(priority)
        query += " ORDER BY created_at DESC LIMIT 50"
        rows = conn.execute(query, params).fetchall()
    return _rows_to_dicts(rows)


def get_tickets_summary(requesting_account_id: Optional[str] = None) -> dict:
    with _get_conn() as conn:
        base = "FROM tickets"
        where = " WHERE account_id = ?" if requesting_account_id else ""
        params = [requesting_account_id] if requesting_account_id else []

        total = conn.execute(f"SELECT COUNT(*) {base}{where}", params).fetchone()[0]
        open_count = conn.execute(
            f"SELECT COUNT(*) {base}{where}{'AND' if where else ' WHERE'} LOWER(status) IN ('open','in_progress')",
            params,
        ).fetchone()[0] if not where else conn.execute(
            f"SELECT COUNT(*) {base}{where} AND LOWER(status) IN ('open','in_progress')",
            params,
        ).fetchone()[0]

        by_priority = _rows_to_dicts(
            conn.execute(
                f"SELECT priority, COUNT(*) as count {base}{where} GROUP BY priority",
                params,
            ).fetchall()
        )
        by_category = _rows_to_dicts(
            conn.execute(
                f"SELECT category, COUNT(*) as count {base}{where} GROUP BY category ORDER BY count DESC LIMIT 10",
                params,
            ).fetchall()
        )
    return {
        "total": total,
        "open": open_count,
        "by_priority": by_priority,
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# Escalation / Action store
# ---------------------------------------------------------------------------

def create_escalation(
    ticket_id: str,
    account_id: str,
    reason: str,
    priority: str,
    created_by: str,
) -> dict:
    import uuid
    from datetime import datetime, timezone
    esc_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO escalations (escalation_id, ticket_id, account_id, reason, priority, created_by, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'open')""",
            (esc_id, ticket_id, account_id, reason, priority, created_by, now),
        )
    return {
        "escalation_id": esc_id,
        "ticket_id": ticket_id,
        "account_id": account_id,
        "reason": reason,
        "priority": priority,
        "created_by": created_by,
        "created_at": now,
        "status": "open",
    }


def update_ticket_status(ticket_id: str, new_status: str, note: str, updated_by: str) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
            (new_status, now, ticket_id),
        )
        conn.execute(
            """INSERT INTO ticket_notes (ticket_id, note, created_by, created_at)
               VALUES (?, ?, ?, ?)""",
            (ticket_id, note, updated_by, now),
        )
    return {"ticket_id": ticket_id, "new_status": new_status, "updated_at": now}


def add_ticket_note(ticket_id: str, note: str, created_by: str) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO ticket_notes (ticket_id, note, created_by, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, note, created_by, now),
        )
    return {"ticket_id": ticket_id, "note": note, "created_at": now}


def create_followup_task(ticket_id: str, description: str, assigned_to: str, due_date: str, created_by: str) -> dict:
    import uuid
    from datetime import datetime, timezone
    task_id = f"TASK-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO followup_tasks (task_id, ticket_id, description, assigned_to, due_date, created_by, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (task_id, ticket_id, description, assigned_to, due_date, created_by, now),
        )
    return {
        "task_id": task_id,
        "ticket_id": ticket_id,
        "description": description,
        "assigned_to": assigned_to,
        "due_date": due_date,
        "status": "pending",
    }


# ---------------------------------------------------------------------------
# Proactive issue detection queries
# ---------------------------------------------------------------------------

def get_proactive_issues() -> list[dict]:
    """Analyse the data and return a list of issues that need attention."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    issues = []

    with _get_conn() as conn:
        # 1. Open tickets approaching/breaching SLA
        open_tickets = _rows_to_dicts(
            conn.execute(
                "SELECT t.*, a.company_name FROM tickets t LEFT JOIN accounts a ON t.account_id = a.account_id "
                "WHERE LOWER(t.status) IN ('open', 'in_progress')"
            ).fetchall()
        )
        for t in open_tickets:
            try:
                created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                age_hours = (now - created).total_seconds() / 3600
                sla_limit = 24 if t.get("priority", "").lower() == "critical" else (
                    48 if t.get("priority", "").lower() == "high" else 72
                )
                if age_hours > sla_limit:
                    issues.append({
                        "type": "sla_breach",
                        "severity": "critical",
                        "title": f"SLA Breach: {t['ticket_id']}",
                        "description": f"Ticket {t['ticket_id']} ({t.get('company_name','')}) "
                                       f"is {age_hours:.0f}h old — exceeds {sla_limit}h SLA for {t.get('priority','normal')} priority.",
                        "ticket_id": t["ticket_id"],
                        "account_id": t.get("account_id"),
                        "age_hours": round(age_hours, 1),
                    })
                elif age_hours > sla_limit * 0.8:
                    issues.append({
                        "type": "sla_warning",
                        "severity": "high",
                        "title": f"SLA Warning: {t['ticket_id']}",
                        "description": f"Ticket {t['ticket_id']} ({t.get('company_name','')}) "
                                       f"at {age_hours:.0f}h — approaching {sla_limit}h SLA.",
                        "ticket_id": t["ticket_id"],
                        "account_id": t.get("account_id"),
                        "age_hours": round(age_hours, 1),
                    })
            except Exception:
                pass

        # 2. Surge detection — category with many recent tickets
        surge = _rows_to_dicts(
            conn.execute(
                "SELECT category, COUNT(*) as cnt FROM tickets GROUP BY category ORDER BY cnt DESC LIMIT 5"
            ).fetchall()
        )
        for s in surge:
            if s["cnt"] and s["cnt"] >= 3:
                issues.append({
                    "type": "ticket_surge",
                    "severity": "medium",
                    "title": f"Ticket Surge: {s['category']}",
                    "description": f"{s['cnt']} tickets in category '{s['category']}'. Possible systemic issue.",
                    "category": s["category"],
                    "count": s["cnt"],
                })

        # 3. Multiple tickets from same account (possible churn risk)
        acct_tickets = _rows_to_dicts(
            conn.execute(
                "SELECT t.account_id, a.company_name, COUNT(*) as cnt FROM tickets t "
                "LEFT JOIN accounts a ON t.account_id = a.account_id "
                "WHERE LOWER(t.status) IN ('open','in_progress') "
                "GROUP BY t.account_id HAVING cnt >= 2"
            ).fetchall()
        )
        for a in acct_tickets:
            issues.append({
                "type": "account_multi_ticket",
                "severity": "high",
                "title": f"Multiple Open Tickets: {a.get('company_name', a['account_id'])}",
                "description": f"{a.get('company_name', a['account_id'])} has {a['cnt']} open tickets simultaneously — possible escalation risk.",
                "account_id": a["account_id"],
                "count": a["cnt"],
            })

    # Sort by severity
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda x: order.get(x.get("severity", "low"), 3))
    return issues
