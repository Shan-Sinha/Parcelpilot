# ParcelPilot Architecture Note

## 1. Agent Design

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

### Multi-Step Reasoning Flow
For complex queries (e.g., *"Can Northstar cancel ORD-1001 without a fee?"*), the agent executes sequential tool steps:
1. `lookup_data(entity="order", filters={"order_id": "ORD-1001"})` → Retrieves account ID (`ACC-001`), carrier, status, pickup date.
2. `lookup_data(entity="account", filters={"account_id": "ACC-001"})` → Confirms company name (`Northstar Logistics`) and tier.
3. `search_documents(query="Northstar cancellation fee")` → Retrieves `05_Northstar_Logistics_Enterprise_Agreement.pdf` (Priority 1) and `03_Cancellation_and_Service_Credit_SOP_v4.pdf` (Priority 3).
4. **Reasoning Step** → Cross-references customer enterprise agreement terms against general SOP rules. Identifies that the Enterprise Agreement overrides general policy.
5. **Synthesis & Citation** → Synthesizes the response with clear citations, source hierarchy explanation, and calculated dates/fees.

---

## 2. Tool Design & Data Scoping

The system exposes 3 distinct tools to the agent:

| Tool | Capability | Access Control Enforcement |
|------|------------|----------------------------|
| `search_documents` | Vector similarity search over policy PDFs, agreements, and guides via ChromaDB | Agreement chunks tagged with `customer_scope`. Customer users only receive chunks matching their scope or general public policies. |
| `lookup_data` | Structured SQL query over `accounts`, `orders`, `tickets` | **Enforced in Python/SQL data layer**: If `user.is_customer`, all queries auto-append `WHERE account_id = user.account_id`. Models cannot bypass this. |
| `create_action` | Prepares state-changing actions (`create_escalation`, `update_ticket_status`, `add_ticket_note`, `create_followup_task`) | **Two-phase Action Gate**: Returns `confirmation_required: true` with action preview. Execution requires explicit user confirmation via `/api/chat/confirm`. |

---

## 3. Document and Structured Data Handling

### Document Ingestion (PDFs → ChromaDB)
- **Ingestion Pipeline**: All 6 PDF documents are parsed using `pypdf`, chunked into 800-character segments with 150-character overlap, and embedded using `text-embedding-3-small`.
- **Metadata Tagging**: Every vector chunk is indexed with key metadata:
  - `source_file`: Original PDF filename
  - `priority`: Hierarchy score (1 to 5)
  - `badge`: Categorization (`contract`, `policy`, `sop`, `guide`, `deprecated`)
  - `trust`: Reliability rating (`high`, `medium`, `low`)
  - `is_deprecated`: Boolean flag (`True` for Policy v2)
  - `customer_scope`: Account restriction (`northstar`, `lumenworks`, or empty for general)

### Structured Data (Excel → SQLite)
- The assessment Excel workbook (`ParcelPilot_Assessment_Data.xlsx`) is ingested into SQLite tables: `accounts`, `orders`, `tickets`.
- Additional operational tables are created: `escalations`, `ticket_notes`, `followup_tasks`.

---

## 4. Source Reliability & Conflict Resolution

ParcelPilot's source base contains intentional conflicts and outdated information. The system handles this through a strict **Source Reliability Hierarchy**:

```
Priority 1: Customer Enterprise Agreements (05_Northstar, 06_LumenWorks)  [HIGHEST AUTHORITY - Overrides general policy]
Priority 2: Support Policy v3 CURRENT (01_Support_Policy_v3_CURRENT)        [Authoritative General Policy]
Priority 3: Cancellation & Service Credit SOP v4 (03_SOP_v4)               [Authoritative Operations Procedure]
Priority 4: Product Operations Guide & Known Issues (04_Ops_Guide)         [Informational Product Context]
Priority 5: Support Policy v2 DEPRECATED (02_Support_Policy_v2_DEPRECATED)   [LOW TRUST - Flagged as Deprecated]
Priority 6: Historical Ticket Resolutions                                  [CONTEXT ONLY - May contain incorrect guidance]
```

### Conflict Resolution Strategy
- **Agreement vs. Policy**: When a customer contract specifies terms differing from general policy, the agent explicitly states: *"Under Northstar's Enterprise Agreement (Section X), cancellation terms override standard Policy v3."*
- **Current vs. Deprecated**: Deprecated Policy v2 is tagged with low trust. If surfaced, the system prompt instructs the agent to favor v3 and explicitly warn the user if v2 was referenced.
- **Ticket History**: Historical tickets are treated purely as historical logs, never as policy ground truth.

---

## 5. Major Technical Trade-offs

1. **SQLite + ChromaDB vs. PostgreSQL/pgvector**:
   - *Choice*: SQLite + local ChromaDB persistent store.
   - *Rationale*: Zero external database dependency, instant local boot, lightweight deployment, perfect for assessment evaluation.

2. **Server-Side Access Control in Data Layer vs. Prompt Instructions**:
   - *Choice*: Enforced in the Python/SQL tool function layer rather than relying on LLM system prompt compliance.
   - *Rationale*: Prompt instructions can be bypassed via prompt injection. Scoping `WHERE account_id = user.account_id` in Python guarantees zero cross-account data leaks.

3. **Two-Phase Action Gate vs. Direct Tool Execution**:
   - *Choice*: `create_action` returns a preview payload requiring user confirmation via a separate endpoint call.
   - *Rationale*: Prevents accidental modifications, hallucinatory side effects, and meets Requirement #4.
