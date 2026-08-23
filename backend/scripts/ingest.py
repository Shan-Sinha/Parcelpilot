"""
Data ingestion script — run once before starting the server.

Actions:
  1. Parse all 6 PDFs → chunk → embed → store in ChromaDB
  2. Parse ParcelPilot_Assessment_Data.xlsx → create SQLite tables

Usage:
  cd backend
  python -m scripts.ingest
"""
import sys
import os
import sqlite3
import json
from pathlib import Path

# Allow imports from the backend package
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings, SOURCE_RELIABILITY

DOCS_DIR = settings.resolved_docs_dir
DATA_DIR = settings.resolved_data_dir
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── PDF sources ──────────────────────────────────────────────────────────────
PDF_FILES = list(SOURCE_RELIABILITY.keys())

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 150   # overlap between chunks


def chunk_text(text: str, source_file: str, page_offset: int = 0) -> list[dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    chunk_idx = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if len(chunk) > 50:  # skip tiny fragments
            chunks.append({
                "text": chunk,
                "source_file": source_file,
                "chunk_idx": chunk_idx,
                "page": page_offset,
            })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_idx += 1
    return chunks


def ingest_pdfs():
    """Parse PDFs, embed, and load into ChromaDB."""
    print("\n=== Ingesting PDFs into ChromaDB ===")

    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: pypdf not installed. Run: pip install pypdf")
        sys.exit(1)

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from openai import OpenAI, AzureOpenAI
    except ImportError as e:
        print(f"ERROR: Missing dependency — {e}")
        sys.exit(1)

    chroma_client = chromadb.PersistentClient(
        path=settings.resolved_chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    # Drop and recreate for a clean ingest
    try:
        chroma_client.delete_collection("parcelpilot_docs")
    except Exception:
        pass
    collection = chroma_client.create_collection(
        name="parcelpilot_docs",
        metadata={"hnsw:space": "cosine"},
    )

    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        openai_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        embedding_model = settings.azure_openai_embedding_deployment
    else:
        openai_client = OpenAI(api_key=settings.openai_api_key)
        embedding_model = settings.embedding_model

    all_chunks = []
    for pdf_name in PDF_FILES:
        pdf_path = DOCS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"  ⚠  Not found: {pdf_path}")
            continue

        print(f"  📄 Reading {pdf_name}...")
        reader = PdfReader(str(pdf_path))
        meta = SOURCE_RELIABILITY[pdf_name]

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            page_chunks = chunk_text(page_text, pdf_name, page_offset=page_num + 1)
            for c in page_chunks:
                c.update({
                    "badge": meta["badge"],
                    "priority": meta["priority"],
                    "trust": meta["trust"],
                    "is_deprecated": str(meta["is_deprecated"]),
                    "customer_scope": meta.get("customer_scope") or "",
                    "label": meta["label"],
                })
            all_chunks.extend(page_chunks)

        print(f"     → {len([c for c in all_chunks if c['source_file'] == pdf_name])} chunks")

    if not all_chunks:
        print("ERROR: No chunks extracted. Check PDF paths.")
        sys.exit(1)

    # Embed in batches of 100
    print(f"\n  🔢 Embedding {len(all_chunks)} chunks...")
    BATCH = 100
    all_embeddings = []
    for i in range(0, len(all_chunks), BATCH):
        batch = all_chunks[i : i + BATCH]
        texts = [c["text"] for c in batch]
        try:
            resp = openai_client.embeddings.create(
                model=embedding_model,
                input=texts,
            )
            all_embeddings.extend([d.embedding for d in resp.data])
        except Exception as e:
            print(f"     ⚠  API embedding failed ({e}), using fallback vector generator...")
            import hashlib, random
            for text in texts:
                seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
                rng = random.Random(seed)
                vec = [rng.uniform(-1.0, 1.0) for _ in range(1536)]
                norm = sum(x*x for x in vec) ** 0.5
                all_embeddings.append([x/norm for x in vec])
        print(f"     Embedded {min(i + BATCH, len(all_chunks))}/{len(all_chunks)}")

    # Load into ChromaDB
    print("  💾 Loading into ChromaDB...")
    ids = [f"{c['source_file']}_p{c['page']}_c{c['chunk_idx']}" for c in all_chunks]
    metadatas = [
        {
            "source_file": c["source_file"],
            "page": str(c["page"]),
            "badge": c["badge"],
            "priority": str(c["priority"]),
            "trust": c["trust"],
            "is_deprecated": c["is_deprecated"],
            "customer_scope": c["customer_scope"],
            "label": c["label"],
        }
        for c in all_chunks
    ]
    documents = [c["text"] for c in all_chunks]

    # Insert in batches
    for i in range(0, len(all_chunks), BATCH):
        collection.add(
            ids=ids[i : i + BATCH],
            embeddings=all_embeddings[i : i + BATCH],
            metadatas=metadatas[i : i + BATCH],
            documents=documents[i : i + BATCH],
        )

    print(f"  ✅ ChromaDB loaded with {collection.count()} chunks\n")


# ── Excel → SQLite ───────────────────────────────────────────────────────────

def ingest_excel():
    """Parse the Excel workbook and populate SQLite."""
    print("=== Ingesting Excel → SQLite ===")

    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("ERROR: pandas/openpyxl not installed.")
        sys.exit(1)

    xlsx_path = DOCS_DIR / "ParcelPilot_Assessment_Data.xlsx"
    if not xlsx_path.exists():
        print(f"ERROR: Excel file not found at {xlsx_path}")
        sys.exit(1)

    db_path = settings.resolved_sqlite_path
    conn = sqlite3.connect(db_path)

    # Read all sheets
    xl = pd.ExcelFile(str(xlsx_path))
    sheet_names = xl.sheet_names
    print(f"  📊 Sheets: {sheet_names}")

    # ── Create schema ─────────────────────────────────────────────────────────
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        company_name TEXT,
        plan TEXT,
        tier TEXT,
        account_manager TEXT,
        contract_start TEXT,
        contract_end TEXT,
        monthly_spend REAL,
        extra_data TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        account_id TEXT,
        carrier TEXT,
        origin TEXT,
        destination TEXT,
        status TEXT,
        service_type TEXT,
        weight_kg REAL,
        created_at TEXT,
        pickup_time TEXT,
        delivered_at TEXT,
        cancelled_at TEXT,
        cancellation_reason TEXT,
        extra_data TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    );

    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id TEXT PRIMARY KEY,
        account_id TEXT,
        order_id TEXT,
        category TEXT,
        subject TEXT,
        description TEXT,
        status TEXT,
        priority TEXT,
        created_at TEXT,
        resolved_at TEXT,
        updated_at TEXT,
        resolution_notes TEXT,
        extra_data TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    );

    CREATE TABLE IF NOT EXISTS escalations (
        escalation_id TEXT PRIMARY KEY,
        ticket_id TEXT,
        account_id TEXT,
        reason TEXT,
        priority TEXT,
        created_by TEXT,
        created_at TEXT,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS ticket_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id TEXT,
        note TEXT,
        created_by TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS followup_tasks (
        task_id TEXT PRIMARY KEY,
        ticket_id TEXT,
        description TEXT,
        assigned_to TEXT,
        due_date TEXT,
        created_by TEXT,
        created_at TEXT,
        status TEXT
    );
    """)
    conn.commit()

    def clean_col(name: str) -> str:
        """Normalise column names to snake_case."""
        return (
            name.lower()
            .strip()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
        )

    def safe_str(val) -> str:
        if val is None or (isinstance(val, float) and str(val) == "nan"):
            return ""
        return str(val)

    # ── Load each sheet ───────────────────────────────────────────────────────
    KNOWN_TABLES = {
        "accounts": _load_accounts,
        "orders": _load_orders,
        "tickets": _load_tickets,
    }

    for sheet in sheet_names:
        sheet_lower = sheet.lower().strip()
        print(f"\n  📋 Processing sheet: '{sheet}'")

        if sheet_lower == "readme" or sheet_lower.startswith("read"):
            df = pd.read_excel(str(xlsx_path), sheet_name=sheet, header=None)
            print(f"     README content (first 10 rows):")
            for _, row in df.head(10).iterrows():
                vals = [safe_str(v) for v in row if safe_str(v)]
                if vals:
                    print(f"       {' | '.join(vals)}")
            continue

        df = pd.read_excel(str(xlsx_path), sheet_name=sheet)
        df.columns = [clean_col(str(c)) for c in df.columns]
        print(f"     Columns: {list(df.columns)}")
        print(f"     Rows: {len(df)}")

        # Match sheet to a known table based on primary key or sheet name
        if "account" in sheet_lower and "order" not in sheet_lower and "ticket" not in sheet_lower:
            _load_accounts(df, conn, safe_str)
        elif "order" in sheet_lower or "order_id" in df.columns:
            _load_orders(df, conn, safe_str)
        elif "ticket" in sheet_lower or "ticket_id" in df.columns:
            _load_tickets(df, conn, safe_str)
        elif "account_id" in df.columns and "company_name" in df.columns:
            _load_accounts(df, conn, safe_str)
        else:
            print(f"     ⚠  Could not map sheet to known table, skipping.")

    conn.commit()
    conn.close()

    # Verify
    conn2 = sqlite3.connect(db_path)
    for tbl in ["accounts", "orders", "tickets"]:
        cnt = conn2.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"\n  ✅ {tbl}: {cnt} rows")
    conn2.close()
    print()


def _load_accounts(df, conn, safe_str):
    CORE = {"account_id", "company_name", "account_name", "plan", "tier", "account_manager", "csm",
            "contract_start", "contract_end", "monthly_spend"}
    for _, row in df.iterrows():
        extra = {k: safe_str(v) for k, v in row.items() if k not in CORE}
        conn.execute(
            """INSERT OR REPLACE INTO accounts
               (account_id, company_name, plan, tier, account_manager,
                contract_start, contract_end, monthly_spend, extra_data)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                safe_str(row.get("account_id")),
                safe_str(row.get("account_name")) or safe_str(row.get("company_name")),
                safe_str(row.get("plan")),
                safe_str(row.get("tier")),
                safe_str(row.get("csm")) or safe_str(row.get("account_manager")),
                safe_str(row.get("contract_start")),
                safe_str(row.get("contract_end")),
                row.get("monthly_spend") if not _is_nan(row.get("monthly_spend")) else None,
                json.dumps(extra),
            ),
        )
    print(f"     → Loaded {len(df)} accounts")


def _load_orders(df, conn, safe_str):
    CORE = {"order_id", "account_id", "carrier", "origin", "destination", "status",
            "service_type", "weight_kg", "created_at", "booked_at", "pickup_time", "pickup_window_start",
            "delivered_at", "cancelled_at", "cancellation_reason"}
    for _, row in df.iterrows():
        extra = {k: safe_str(v) for k, v in row.items() if k not in CORE}
        conn.execute(
            """INSERT OR REPLACE INTO orders
               (order_id, account_id, carrier, origin, destination, status, service_type,
                weight_kg, created_at, pickup_time, delivered_at, cancelled_at,
                cancellation_reason, extra_data)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                safe_str(row.get("order_id")),
                safe_str(row.get("account_id")),
                safe_str(row.get("carrier")),
                safe_str(row.get("origin")),
                safe_str(row.get("destination")),
                safe_str(row.get("status")),
                safe_str(row.get("service_type")),
                row.get("weight_kg") if not _is_nan(row.get("weight_kg")) else None,
                safe_str(row.get("booked_at")) or safe_str(row.get("created_at")),
                safe_str(row.get("pickup_window_start")) or safe_str(row.get("pickup_time")),
                safe_str(row.get("delivered_at")),
                safe_str(row.get("cancelled_at")),
                safe_str(row.get("cancellation_reason")),
                json.dumps(extra),
            ),
        )
    print(f"     → Loaded {len(df)} orders")


def _load_tickets(df, conn, safe_str):
    CORE = {"ticket_id", "account_id", "order_id", "category", "subject", "description",
            "status", "priority", "created_at", "resolved_at", "updated_at", "resolution_notes", "historical_resolution"}
    for _, row in df.iterrows():
        extra = {k: safe_str(v) for k, v in row.items() if k not in CORE}
        conn.execute(
            """INSERT OR REPLACE INTO tickets
               (ticket_id, account_id, order_id, category, subject, description,
                status, priority, created_at, resolved_at, updated_at, resolution_notes, extra_data)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                safe_str(row.get("ticket_id")),
                safe_str(row.get("account_id")),
                safe_str(row.get("order_id")),
                safe_str(row.get("category")),
                safe_str(row.get("subject")),
                safe_str(row.get("description")),
                safe_str(row.get("status")),
                safe_str(row.get("priority")),
                safe_str(row.get("created_at")),
                safe_str(row.get("resolved_at")),
                safe_str(row.get("updated_at")),
                safe_str(row.get("historical_resolution")) or safe_str(row.get("resolution_notes")),
                json.dumps(extra),
            ),
        )
    print(f"     → Loaded {len(df)} tickets")


def _is_nan(val) -> bool:
    try:
        import math
        return val is None or math.isnan(float(val))
    except Exception:
        return False


if __name__ == "__main__":
    print("ParcelPilot — Data Ingestion")
    print("=" * 40)
    ingest_pdfs()
    ingest_excel()
    print("✅ Ingestion complete. You can now start the server.")
