# ParcelPilot Product Note

## 1. Additional Client Problems Addressed

We addressed **both** optional client problems in this submission:

### Problem 1: Proactive Issue Detection
- **Solution**: Built an internal **Proactive Operations Dashboard** (`/dashboard`) that continuously scans structured ticket and order data to detect:
  1. **SLA Breaches & Warnings**: Identifies tickets approaching or exceeding priority SLAs (e.g. Critical >24h, High >48h) and highlights them before customers escalate.
  2. **Ticket Surges**: Aggregates ticket volume by category to catch systemic product bugs or carrier disruptions early (e.g., sudden spike in "Pickup Delays").
  3. **Multi-Ticket Account Churn Risk**: Flags accounts with multiple open tickets simultaneously so support managers can intervene proactively.
- **Workflow**: Clicking "Investigate Ticket" on any proactive alert immediately opens the agent chat with pre-loaded context to resolve the issue.

### Problem 2: Trust and Reliability
- **Solution**: Built a multi-layered trust model:
  1. **Explicit Source Reliability Hierarchy**: Ranked retrieval metadata prevents outdated policy (v2) or incorrect historical tickets from overriding authoritative contracts or v3 policies.
  2. **Conflict Warning Engine**: Automatically alerts the user when retrieved sources contain conflicting guidance (e.g., deprecated vs. current policy).
  3. **Two-Phase Action Gate**: All state modifications require explicit human confirmation with a clear visual preview before execution.

---

## 2. What Else We Would Build for ParcelPilot

If continuing to build ParcelPilot, the highest-priority roadmap items would be:

1. **Carrier API Integration & Real-Time Tracking Sync**:
   - Auto-query carrier APIs (FedEx, DHL, UPS) when a pickup delay is reported to verify carrier fault automatically without manual agent research.

2. **Automated Service Credit Processing & Ledger**:
   - Calculate exact credit eligibility based on contract SLAs and automatically post credit memos to the customer account upon approval.

3. **Autonomous Email & Webhook Escalation Triggers**:
   - Send automated Slack/Email alerts to Account Managers when an Enterprise Account's SLA is breached.

4. **RLHF & Feedback Loop on Agent Resolutions**:
   - Allow support managers to rate agent resolutions (👍/👎), automatically flagging low-scoring answers for human review and retraining vector embeddings.

---

## 3. What Was Intentionally Left Out of the Submission

- **Third-Party Carrier API Integrations**: Mocked operational carrier status within SQLite rather than connecting to live carrier endpoints.
- **Multi-Tenant SSO / OAuth Integration**: Implemented JWT authentication with pre-configured mock personas (`northstar`, `lumenworks`, `support`, `ops`) for instant evaluation.
- **Complex Background Queue (Celery/Redis)**: Computed proactive issue detection directly via indexed SQL queries to keep setup zero-dependency and fast.

---

## 4. One Metric to Judge Product Usefulness

> **Primary Metric: First-Contact Resolution Rate (FCR) with Zero SLA Breaches**
>
> *Definition*: The percentage of customer support inquiries resolved accurately on the first interaction without requiring manual tier-2 escalation or breaching contract SLA limits.
>
> *Why it matters*: High FCR directly reduces operational overhead for ParcelPilot's 20-person support team while ensuring enterprise customers (like Northstar & LumenWorks) receive trusted, contract-compliant resolutions.
