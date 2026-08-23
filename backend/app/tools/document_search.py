"""Tool 1: Document search with source reliability context."""
from typing import Optional
from ..vector_store import search_documents as _search
from ..auth import UserContext


def run(
    query: str,
    doc_filter: str = "all",
    user: UserContext = None,
) -> dict:
    """
    Search policy docs, agreements, SOPs, and product guides.
    Returns ranked chunks with reliability metadata.
    """
    customer_scope = user.customer_scope if user else None
    chunks = _search(query=query, n_results=8, doc_filter=doc_filter, customer_scope=customer_scope)

    if not chunks:
        return {"found": False, "message": "No relevant documents found.", "sources": []}

    # Build a structured result the LLM can reason over
    result_text = ""
    sources = []
    for i, c in enumerate(chunks[:5]):  # top 5
        deprecated_note = " ⚠️ DEPRECATED — use with caution" if c["is_deprecated"] else ""
        scope_note = f" [applies to: {c['customer_scope']}]" if c["customer_scope"] else ""
        result_text += (
            f"\n[Source {i+1}: {c['source_label']}{deprecated_note}{scope_note} | "
            f"Trust: {c['trust']} | Page: {c['page']}]\n"
            f"{c['text']}\n"
        )
        sources.append({
            "source_file": c["source_file"],
            "source_label": c["source_label"],
            "badge": c["badge"],
            "trust": c["trust"],
            "is_deprecated": c["is_deprecated"],
            "customer_scope": c["customer_scope"],
            "page": c["page"],
            "relevance_score": c["relevance_score"],
        })

    return {
        "found": True,
        "result_text": result_text,
        "sources": sources,
        "conflict_warning": _detect_conflicts(chunks),
    }


def _detect_conflicts(chunks: list[dict]) -> Optional[str]:
    """Check if a deprecated source was surfaced alongside a current one."""
    has_deprecated = any(c["is_deprecated"] for c in chunks)
    has_current = any(not c["is_deprecated"] for c in chunks)
    if has_deprecated and has_current:
        return (
            "Note: Both current and deprecated sources were found. "
            "Prefer the current policy (v3) over deprecated (v2). "
            "Customer-specific agreements override general policies."
        )
    return None
