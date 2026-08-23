# ParcelPilot AI — Support & Operations Engine

ParcelPilot AI is an intelligent, context-aware Support & Operations Engine designed for enterprise logistics platforms. It combines **Agentic Retrieval-Augmented Generation (RAG)** over enterprise contracts and SOPs, **parameterized SQL querying** over operational data, **Human-in-the-Loop action governance**, and **proactive operational issue detection**.

---

## 🌐 Live Deployed Application

- **Frontend App**: [https://parcelpilot-frontend-tdu5.onrender.com](https://parcelpilot-frontend-tdu5.onrender.com)
- **Backend API**: [https://parcelpilot-backend-p40g.onrender.com](https://parcelpilot-backend-p40g.onrender.com)
- **GitHub Repository**: [https://github.com/Shan-Sinha/Parcelpilot.git](https://github.com/Shan-Sinha/Parcelpilot.git)

---

## ⚡ Quick Start: Clone & Run Locally

### 1. Prerequisites
- **Python**: 3.10 or 3.11+
- **Node.js**: v18+ and `npm`
- **Azure OpenAI Service**: Endpoint & API Key (or OpenAI API Key)

---

### 2. Clone the Repository

```bash
git clone https://github.com/Shan-Sinha/Parcelpilot.git
cd Parcelpilot
```

---

### 3. Backend Setup (FastAPI + ChromaDB + SQLite)

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file inside the `backend/` directory:
   ```env
   AZURE_OPENAI_ENDPOINT="https://<your-azure-openai-resource>.openai.azure.com/"
   AZURE_OPENAI_API_KEY="<your-azure-openai-api-key>"
   AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"
   AZURE_OPENAI_API_VERSION="2024-02-15-preview"
   SECRET_KEY="parcelpilot-jwt-secret-change-in-production"
   DOCS_DIR="docs"
   DATA_DIR="/tmp/data"
   CHROMA_PERSIST_DIR="/tmp/data/chroma"
   SQLITE_DB_PATH="/tmp/data/parcelpilot.db"
   ```

5. Run data ingestion (Parses PDFs and Excel into ChromaDB & SQLite):
   ```bash
   python -m scripts.ingest
   ```

6. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The backend API will be live at `http://localhost:8000`.

---

### 4. Frontend Setup (Next.js 14 + Vanilla CSS)

1. Open a new terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file (optional for local dev):
   ```env
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

### 5. Pre-Configured Test Personas (One-Click Login)

The application provides four pre-configured persona buttons on the login screen:

| Persona | Role | Account / Scope | Access Level |
|---|---|---|---|
| **Northstar Logistics** | Enterprise Customer | `ACCT-001` | Scoped to ACCT-001 data & Northstar Enterprise Contract |
| **LumenWorks** | Service Customer | `ACCT-002` | Scoped to ACCT-002 data & LumenWorks Contract |
| **Sam Rivera** | Internal Support Agent | Internal | Full operational query access + Ticket action permissions |
| **Morgan Lee** | Internal Ops Manager | Internal | Full access + Proactive SLA & Issue Detection Dashboard |

---

## 🏗️ Architecture Note

### 1. Agent Design

The ParcelPilot AI Agent uses an autonomous tool-calling loop built on OpenAI GPT-4o. Rather than a static RAG chain, the agent dynamically decides which tools to invoke based on the user's intent, query parameters, and context.

```
                  ┌───────────────────────────────┐
                  │    User Prompt & Context      │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │   System Prompt Injector      │
                  │   - Role & Account Scope      │
                  │   - Source Hierarchy Rules    │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │      GPT-4o Agent Loop        │◄────┐
                  └──────────────┬────────────────┘     │
                                 │                      │
           ┌─────────────────────┼──────────────────┐   │
           ▼                     ▼                  ▼   │
  ┌──────────────────┐  ┌──────────────────┐  ┌─────────┴────────┐
  │ search_documents │  │   lookup_data    │  │  create_action   │
  │ (ChromaDB Vector)│  │ (SQLite DB)      │  │ (Action Gate)    │
  └────────┬─────────┘  └────────┬─────────┘  └─────────┬────────┘
           │                     │                      │
           └─────────────────────┴──────────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ Final Answer or Action Gate   │
                  └──────────────┬────────────────┘
```

#### Multi-Step Reasoning Flow
For complex queries (e.g., *"Can Northstar cancel ORD-1001 without a fee?"*), the agent executes sequential tool steps:
1. `lookup_data(entity="order", filters={"order_id": "ORD-1001"})` → Retrieves account ID (`ACCT-001`), carrier, status, pickup date.
2. `lookup_data(entity="account", filters={"account_id": "ACCT-001"})` → Confirms company name (`Northstar Logistics`) and tier.
3. `search_documents(query="Northstar cancellation fee")` → Retrieves `05_Northstar_Logistics_Enterprise_Agreement.pdf` (Priority 1) and `03_Cancellation_and_Service_Credit_SOP_v4.pdf` (Priority 3).
4. **Reasoning Step** → Cross-references customer enterprise agreement terms against general SOP rules. Identifies that the Enterprise Agreement overrides general policy.
5. **Synthesis & Citation** → Synthesizes the response with clear citations, source hierarchy explanation, and calculated dates/fees.

---

### 2. Tool Design & Data Scoping

The system exposes 3 distinct tools to the agent:

| Tool | Capability | Access Control Enforcement |
|------|------------|----------------------------|
| `search_documents` | Vector similarity search over policy PDFs, agreements, and guides via ChromaDB | Agreement chunks tagged with `customer_scope`. Customer users only receive chunks matching their scope or general public policies. |
| `lookup_data` | Structured SQL query over `accounts`, `orders`, `tickets` | **Enforced in Python/SQL data layer**: If `user.is_customer`, all queries auto-append `WHERE account_id = user.account_id`. Models cannot bypass this. |
| `create_action` | Prepares state-changing actions (`create_escalation`, `update_ticket_status`, `add_ticket_note`, `create_followup_task`) | **Two-phase Action Gate**: Returns `confirmation_required: true` with action preview. Execution requires explicit user confirmation via `/api/chat/confirm`. |

---

### 3. Document and Structured Data Handling

#### Document Ingestion (PDFs → ChromaDB)
- **Ingestion Pipeline**: All 6 PDF documents are parsed using `pypdf`, chunked into 800-character segments with 150-character overlap, and embedded using `text-embedding-3-small`.
- **Metadata Tagging**: Every vector chunk is indexed with key metadata:
  - `source_file`: Original PDF filename
  - `priority`: Hierarchy score (1 to 5)
  - `badge`: Categorization (`contract`, `policy`, `sop`, `guide`, `deprecated`)
  - `trust`: Reliability rating (`high`, `medium`, `low`)
  - `is_deprecated`: Boolean flag (`True` for Policy v2)
  - `customer_scope`: Account restriction (`northstar`, `lumenworks`, or empty for general)

#### Structured Data (Excel → SQLite)
- The assessment Excel workbook (`ParcelPilot_Assessment_Data.xlsx`) is ingested into SQLite tables: `accounts`, `orders`, `tickets`.
- Additional operational tables are created: `escalations`, `ticket_notes`, `followup_tasks`.

---

### 4. Source Reliability & Conflict Resolution

ParcelPilot's source base contains intentional conflicts and outdated information. The system handles this through a strict **Source Reliability Hierarchy**:

```
Priority 1: Customer Enterprise Agreements (05_Northstar, 06_LumenWorks)  [HIGHEST AUTHORITY - Overrides general policy]
Priority 2: Support Policy v3 CURRENT (01_Support_Policy_v3_CURRENT)        [Authoritative General Policy]
Priority 3: Cancellation & Service Credit SOP v4 (03_SOP_v4)               [Authoritative Operations Procedure]
Priority 4: Product Operations Guide & Known Issues (04_Ops_Guide)         [Informational Product Context]
Priority 5: Support Policy v2 DEPRECATED (02_Support_Policy_v2_DEPRECATED)   [LOW TRUST - Flagged as Deprecated]
Priority 6: Historical Ticket Resolutions                                  [CONTEXT ONLY - May contain incorrect guidance]
```

#### Conflict Resolution Strategy
- **Agreement vs. Policy**: When a customer contract specifies terms differing from general policy, the agent explicitly states: *"Under Northstar's Enterprise Agreement (Section X), cancellation terms override standard Policy v3."*
- **Current vs. Deprecated**: Deprecated Policy v2 is tagged with low trust. If surfaced, the system prompt instructs the agent to favor v3 and explicitly warn the user if v2 was referenced.
- **Ticket History**: Historical tickets are treated purely as historical logs, never as policy ground truth.

---

### 5. Major Technical Trade-offs

1. **SQLite + ChromaDB vs. PostgreSQL/pgvector**:
   - *Choice*: SQLite + local ChromaDB persistent store.
   - *Rationale*: Zero external database dependency, instant local boot, lightweight deployment, perfect for evaluation and cloud hosting.

2. **Server-Side Access Control in Data Layer vs. Prompt Instructions**:
   - *Choice*: Enforced in the Python/SQL tool function layer rather than relying on LLM system prompt compliance.
   - *Rationale*: Prompt instructions can be bypassed via prompt injection. Scoping `WHERE account_id = user.account_id` in Python guarantees zero cross-account data leaks.

3. **Two-Phase Action Gate vs. Direct Tool Execution**:
   - *Choice*: `create_action` returns a preview payload requiring user confirmation via a separate endpoint call.
   - *Rationale*: Prevents accidental modifications, hallucinatory side effects, and ensures strict human oversight.

---

## 📦 Product Note

### 1. Additional Client Problems Addressed

We addressed **both** optional client problems in this submission:

#### Problem 1: Proactive Issue Detection
- **Solution**: Built an internal **Proactive Operations Dashboard** (`/dashboard`) that continuously scans structured ticket and order data to detect:
  1. **SLA Breaches & Warnings**: Identifies tickets approaching or exceeding priority SLAs (e.g. Critical >24h, High >48h) and highlights them before customers escalate.
  2. **Ticket Surges**: Aggregates ticket volume by category to catch systemic product bugs or carrier disruptions early (e.g., sudden spike in "Pickup Delays").
  3. **Multi-Ticket Account Churn Risk**: Flags accounts with multiple open tickets simultaneously so support managers can intervene proactively.
- **Workflow**: Clicking "Investigate Ticket" on any proactive alert immediately opens the agent chat with pre-loaded context to resolve the issue.

#### Problem 2: Trust and Reliability
- **Solution**: Built a multi-layered trust model:
  1. **Explicit Source Reliability Hierarchy**: Ranked retrieval metadata prevents outdated policy (v2) or incorrect historical tickets from overriding authoritative contracts or v3 policies.
  2. **Conflict Warning Engine**: Automatically alerts the user when retrieved sources contain conflicting guidance (e.g., deprecated vs. current policy).
  3. **Two-Phase Action Gate**: All state modifications require explicit human confirmation with a clear visual preview before execution.

---

### 2. Product Roadmap & Future Enhancements

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

### 3. What Was Intentionally Left Out of the Submission

- **Third-Party Carrier API Integrations**: Mocked operational carrier status within SQLite rather than connecting to live carrier endpoints.
- **Multi-Tenant SSO / OAuth Integration**: Implemented JWT authentication with pre-configured mock personas (`northstar`, `lumenworks`, `support`, `ops`) for instant evaluation.
- **Complex Background Queue (Celery/Redis)**: Computed proactive issue detection directly via indexed SQL queries to keep setup zero-dependency and fast.

---

### 4. Key Metric to Judge Product Usefulness

> **Primary Metric: First-Contact Resolution Rate (FCR) with Zero SLA Breaches**
>
> *Definition*: The percentage of customer support inquiries resolved accurately on the first interaction without requiring manual tier-2 escalation or breaching contract SLA limits.
>
> *Why it matters*: High FCR directly reduces operational overhead for ParcelPilot's support team while ensuring enterprise customers (like Northstar & LumenWorks) receive trusted, contract-compliant resolutions.

---

## 🤖 AI Tool Usage Statement

### Tools Used
- **Google Antigravity**: Autonomous AI coding assistant powered by Gemini 3.6 Flash & Claude 3.5/Sonnet models.

### Usage Summary
1. **Architecture & Schema Design**: Used AI to design the multi-step agent loop, ChromaDB vector metadata schema, SQLite relational structure, and two-phase action confirmation workflow.
2. **Data Ingestion Scripting**: Generated Python scripts (`scripts/ingest.py`) to chunk and embed all 6 PDF documents into ChromaDB with source reliability metadata and convert `ParcelPilot_Assessment_Data.xlsx` sheets into SQLite tables.
3. **Full-Stack Implementation**: Built the complete FastAPI backend (auth, agent loop, tools, routers) and Next.js 14 glassmorphism frontend (Login, ChatInterface with Tool Visualizer, Confirmation Modal, Proactive Dashboard).
4. **Documentation & Synthesis**: Synthesized architecture and product notes detailing trade-offs, access control enforcement, and source reliability algorithms.
