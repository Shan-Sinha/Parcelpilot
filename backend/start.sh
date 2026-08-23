#!/bin/bash
# Render backend startup: runs data ingestion into /tmp/data then starts uvicorn
set -e

echo "=== Starting ParcelPilot Backend ==="

# Create data directories
mkdir -p "${DATA_DIR:-/tmp/data}/chroma"

# Set default DOCS_DIR if not set
export DOCS_DIR="${DOCS_DIR:-docs}"
export DATA_DIR="${DATA_DIR:-/tmp/data}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/tmp/data/chroma}"
export SQLITE_DB_PATH="${SQLITE_DB_PATH:-/tmp/data/parcelpilot.db}"

echo "=== Environment Setup ==="
echo "DOCS_DIR: $DOCS_DIR"
echo "DATA_DIR: $DATA_DIR"

# Check if DB already exists (skip re-ingest on restarts to save boot time)
if [ -f "$SQLITE_DB_PATH" ]; then
  ROW_COUNT=$(python -c "import sqlite3; c=sqlite3.connect('$SQLITE_DB_PATH'); print(c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0])" 2>/dev/null || echo "0")
  echo "=== DB already exists with $ROW_COUNT tickets — skipping ingest ==="
else
  echo "=== Running data ingestion ==="
  python -m scripts.ingest
fi

echo "=== Starting uvicorn on port ${PORT:-8000} ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
