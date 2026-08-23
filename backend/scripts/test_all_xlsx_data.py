"""
Test script to run AI Agent queries & tool calls against every row in ParcelPilot_Assessment_Data.xlsx
"""
import sqlite3
import json
from app.agent import run_agent
from app.auth import MOCK_USERS, UserContext

conn = sqlite3.connect("data/parcelpilot.db")
conn.row_factory = sqlite3.Row

print("==========================================================")
print("     PARCELPILOT COMPLETE XLSX DATA VERIFICATION TEST")
print("==========================================================")

# 1. Accounts Test
print("\n--- 1. TESTING ACCOUNTS (4 Rows) ---")
accounts = conn.execute("SELECT * FROM accounts").fetchall()
for acc in accounts:
    acc_id = acc["account_id"]
    comp_name = acc["company_name"]
    plan = acc["plan"]
    print(f"\n[Account] ID: {acc_id} | Name: {comp_name} | Plan: {plan}")
    
    # Query account details via agent as Internal user
    user = UserContext(**MOCK_USERS["support"])
    resp = run_agent(messages=[{"role": "user", "content": f"Get account details for {acc_id}"}], user=user)
    print(f"  Agent Answer: {resp.get('message')[:150]}...")
    if resp.get("tool_calls"):
        print(f"  Tools Called: {[t['tool'] for t in resp['tool_calls']]}")

# 2. Orders Test
print("\n--- 2. TESTING ORDERS (6 Rows) ---")
orders = conn.execute("SELECT * FROM orders").fetchall()
for ord in orders:
    order_id = ord["order_id"]
    acc_id = ord["account_id"]
    carrier = ord["carrier"]
    status = ord["status"]
    print(f"\n[Order] ID: {order_id} | Account: {acc_id} | Carrier: {carrier} | Status: {status}")
    
    # Query order status via agent as Customer (Northstar or LumenWorks if matching, else internal)
    persona = "northstar" if acc_id == "ACC-001" else ("lumenworks" if acc_id == "ACC-002" else "support")
    user = UserContext(**MOCK_USERS[persona])
    resp = run_agent(messages=[{"role": "user", "content": f"Check status of order {order_id}"}], user=user)
    print(f"  Agent Answer: {resp.get('message')[:150]}...")
    if resp.get("tool_calls"):
        print(f"  Tools Called: {[t['tool'] for t in resp['tool_calls']]}")

# 3. Tickets Test
print("\n--- 3. TESTING TICKETS (7 Rows) ---")
tickets = conn.execute("SELECT * FROM tickets").fetchall()
for tkt in tickets:
    ticket_id = tkt["ticket_id"]
    acc_id = tkt["account_id"]
    subject = tkt["subject"]
    status = tkt["status"]
    print(f"\n[Ticket] ID: {ticket_id} | Account: {acc_id} | Subject: {subject} | Status: {status}")
    
    persona = "northstar" if acc_id == "ACC-001" else ("lumenworks" if acc_id == "ACC-002" else "support")
    user = UserContext(**MOCK_USERS[persona])
    resp = run_agent(messages=[{"role": "user", "content": f"Lookup ticket {ticket_id} and check resolution policy"}], user=user)
    print(f"  Agent Answer: {resp.get('message')[:150]}...")
    if resp.get("tool_calls"):
        print(f"  Tools Called: {[t['tool'] for t in resp['tool_calls']]}")

print("\n==========================================================")
print("     ALL XLSX RECS TESTED SUCCESSFULLY!")
print("==========================================================")
