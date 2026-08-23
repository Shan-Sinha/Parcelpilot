from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI, AzureOpenAI
from .config import settings, SOURCE_RELIABILITY

_client: Optional[chromadb.PersistentClient] = None
_collection = None
_openai_client = None


def _get_chroma():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=settings.resolved_chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="parcelpilot_docs",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_openai():
    global _openai_client
    if _openai_client is None:
        if settings.azure_openai_api_key and settings.azure_openai_endpoint:
            _openai_client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        else:
            _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def embed(texts: list[str]) -> list[list[float]]:
    try:
        model_name = settings.azure_openai_embedding_deployment if (settings.azure_openai_api_key and settings.azure_openai_endpoint) else settings.embedding_model
        response = _get_openai().embeddings.create(
            model=model_name,
            input=texts,
        )
        return [d.embedding for d in response.data]
    except Exception as e:
        print(f"Warning: OpenAI embedding call failed ({e}), using fallback vector representation.")
        # Lightweight determinisitc fallback vector (1536 dim) if embedding model is not deployed on Azure endpoint
        import hashlib
        vectors = []
        for text in texts:
            seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
            import random
            rng = random.Random(seed)
            vec = [rng.uniform(-1.0, 1.0) for _ in range(1536)]
            norm = sum(x*x for x in vec) ** 0.5
            vectors.append([x/norm for x in vec])
        return vectors


def search_documents(
    query: str,
    n_results: int = 6,
    doc_filter: Optional[str] = None,
    customer_scope: Optional[str] = None,
) -> list[dict]:
    """
    Search documents and return chunks with full source metadata.

    Args:
        query: Natural language query
        n_results: Max number of chunks to return
        doc_filter: One of "all", "policies", "agreements", "sops", "product_guide"
        customer_scope: If set (e.g. "northstar"), also include that customer's agreement
    """
    collection = _get_chroma()
    query_embedding = embed([query])[0]

    # Build ChromaDB where filter
    where = None
    if doc_filter and doc_filter != "all":
        badge_map = {
            "policies": ["policy", "deprecated"],
            "agreements": ["contract"],
            "sops": ["sop"],
            "product_guide": ["guide"],
        }
        badges = badge_map.get(doc_filter, [])
        if badges:
            where = {"badge": {"$in": badges}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count() or 1),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if not results["ids"] or not results["ids"][0]:
        return chunks

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        reliability = SOURCE_RELIABILITY.get(meta.get("source_file", ""), {})
        chunk_scope = reliability.get("customer_scope")

        # Exclude contract chunks belonging to other customers for strict isolation
        if customer_scope and chunk_scope and chunk_scope != customer_scope:
            continue

        chunks.append({
            "text": doc,
            "source_file": meta.get("source_file", "unknown"),
            "source_label": reliability.get("label", meta.get("source_file", "")),
            "badge": reliability.get("badge", "unknown"),
            "priority": reliability.get("priority", 99),
            "trust": reliability.get("trust", "unknown"),
            "is_deprecated": reliability.get("is_deprecated", False),
            "customer_scope": chunk_scope,
            "page": meta.get("page", "?"),
            "relevance_score": round(1 - dist, 3),
        })

    # Sort by priority (lower = higher authority), then by relevance
    chunks.sort(key=lambda c: (c["priority"], -c["relevance_score"]))
    return chunks
