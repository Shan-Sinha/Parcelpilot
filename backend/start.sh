#!/bin/bash
# Render backend startup: copies PDFs, runs ingestion, then starts server
set -e

echo "=== Starting ParcelPilot Backend ==="

# Create data directories
mkdir -p "${DATA_DIR:-/data}/chroma"

# PDFs are committed in the repo root (one level up from backend/)
# Copy them to DOCS_DIR so ingest.py can find them
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_TARGET="${DOCS_DIR:-/docs}"
mkdir -p "$DOCS_TARGET"

echo "=== Copying PDFs from $REPO_ROOT → $DOCS_TARGET ==="
cp "$REPO_ROOT"/*.pdf "$DOCS_TARGET/" 2>/dev/null && echo "PDFs copied" || echo "No PDFs in repo root (may already be in DOCS_DIR)"
cp "$REPO_ROOT"/*.xlsx "$DOCS_TARGET/" 2>/dev/null && echo "Excel copied" || echo "No xlsx in repo root"

# Check if DB already exists (skip re-ingest on restarts to save boot time)
DB_PATH="${SQLITE_DB_PATH:-${DATA_DIR:-/data}/parcelpilot.db}"
if [ -f "$DB_PATH" ]; then
  ROW_COUNT=$(python -c "import sqlite3; c=sqlite3.connect('$DB_PATH'); print(c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])" 2>/dev/null || echo "0")
  echo "=== DB already exists with $ROW_COUNT tickets — skipping ingest ==="
else
  echo "=== Running data ingestion ==="
  python -m scripts.ingest
fi

echo "=== Starting uvicorn on port ${PORT:-8000} ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
