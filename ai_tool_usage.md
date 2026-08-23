# AI Tool Usage Statement

## Tools Used
- **Google Antigravity**: Autonomous AI coding assistant powered by Gemini 3.6 Flash & Claude 3.5/Sonnet models.

## Usage Summary
1. **Architecture & Schema Design**: Used AI to design the multi-step agent loop, ChromaDB vector metadata schema, SQLite relational structure, and two-phase action confirmation workflow.
2. **Data Ingestion Scripting**: Generated Python scripts (`scripts/ingest.py`) to chunk and embed all 6 PDF documents into ChromaDB with source reliability metadata and convert `ParcelPilot_Assessment_Data.xlsx` sheets into SQLite tables.
3. **Full-Stack Implementation**: Built the complete FastAPI backend (auth, agent loop, tools, routers) and Next.js 14 glassmorphism frontend (Login, ChatInterface with Tool Visualizer, Confirmation Modal, Proactive Dashboard).
4. **Documentation & Synthesis**: Generated comprehensive architecture and product notes detailing trade-offs, access control enforcement, and source reliability algorithms.
