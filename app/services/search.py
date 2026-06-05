"""Hybrid keyword + semantic search over the `search_documents` collection.

  - Keyword arm:   MongoDB `$text` with synonym-expanded query.
  - Semantic arm:  FAISS k-NN over PubMedBERT embeddings of search docs.
  - Fusion:        Reciprocal Rank Fusion (RRF) at the app layer.

Returns a list of hydrated result dicts ready for the template.
"""

from bson import ObjectId

from app.db import Collections, get_collection, get_db
from app.services.embedder import get_faiss_index, get_model
from app.services.synonym_expander import get_expander


SEARCH_DOCS = "search_documents"

RRF_K = 60
KEYWORD_TOP_K = 50
SEMANTIC_TOP_K = 50
FINAL_TOP_K = 20


def _keyword_search(
    expanded_query: str, subject_id: ObjectId | None
) -> list[tuple[str, float]]:
    """Return [(doc_id_str, mongo_text_score), ...] sorted by score desc."""
    if not expanded_query:
        return []
    coll = get_collection(SEARCH_DOCS)
    filter_: dict = {"$text": {"$search": expanded_query}}
    if subject_id is not None:
        filter_["subject_id"] = subject_id
    cursor = (
        coll.find(filter_, {"score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"})])
        .limit(KEYWORD_TOP_K)
    )
    return [(str(d["_id"]), float(d["score"])) for d in cursor]


def _semantic_search(
    query: str, subject_id: ObjectId | None
) -> list[tuple[str, float]]:
    """Return [(doc_id_str, cosine_similarity), ...] sorted desc."""
    index, ids = get_faiss_index()
    if index is None or not ids:
        return []

    model = get_model()
    query_emb = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype("float32")

    # Over-fetch when filtering by subject so we still have enough hits
    # after the filter is applied.
    k = SEMANTIC_TOP_K * 4 if subject_id is not None else SEMANTIC_TOP_K
    k = min(k, len(ids))
    scores, idx = index.search(query_emb, k)

    candidates = [
        (ids[int(i)], float(s))
        for s, i in zip(scores[0], idx[0])
        if int(i) != -1
    ]

    if subject_id is None:
        return candidates[:SEMANTIC_TOP_K]

    # Filter by subject_id via a single batch lookup on the search docs.
    candidate_ids = [ObjectId(c[0]) for c in candidates]
    allowed = {
        str(d["_id"])
        for d in get_collection(SEARCH_DOCS).find(
            {"_id": {"$in": candidate_ids}, "subject_id": subject_id},
            {"_id": 1},
        )
    }
    filtered = [(doc_id, s) for doc_id, s in candidates if doc_id in allowed]
    return filtered[:SEMANTIC_TOP_K]


def _rrf_fuse(
    keyword: list[tuple[str, float]],
    semantic: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. Returns [(doc_id, fused_score), ...] desc."""
    fused: dict[str, float] = {}
    for rank, (doc_id, _) in enumerate(keyword):
        fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, (doc_id, _) in enumerate(semantic):
        fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(fused.items(), key=lambda kv: -kv[1])


def _hydrate(doc_ids: list[str]) -> list[dict]:
    """Fetch the search_documents and add MCQ counts for display."""
    if not doc_ids:
        return []

    object_ids = [ObjectId(d) for d in doc_ids]
    docs = {
        str(d["_id"]): d
        for d in get_collection(SEARCH_DOCS).find({"_id": {"$in": object_ids}})
    }

    # MCQ counts grouped per lesson.
    mcq_counts: dict[ObjectId, int] = {}
    for entry in get_db()[Collections.mcqs].aggregate(
        [
            {"$match": {"lesson_id": {"$in": object_ids}}},
            {"$group": {"_id": "$lesson_id", "count": {"$sum": 1}}},
        ]
    ):
        mcq_counts[entry["_id"]] = entry["count"]

    out: list[dict] = []
    for doc_id in doc_ids:
        doc = docs.get(doc_id)
        if not doc:
            continue
        snippet = (doc.get("content") or "")[:240].strip()
        if len(doc.get("content") or "") > 240:
            snippet += "…"
        out.append(
            {
                "lesson_id": str(doc["_id"]),
                "topic_id": str(doc["topic_id"]),
                "subject_id": str(doc["subject_id"]),
                "title": doc.get("title", ""),
                "topic_name": doc.get("topic_name", ""),
                "subject_name": doc.get("subject_name", ""),
                "snippet": snippet,
                "mcq_count": mcq_counts.get(doc["_id"], 0),
            }
        )
    return out


def search(
    query: str,
    subject_id: str | None = None,
    limit: int = FINAL_TOP_K,
) -> dict:
    """Top-level entry point. Returns a dict for the template."""
    raw_query = (query or "").strip()
    if not raw_query:
        return {
            "query": "",
            "expanded": "",
            "results": [],
            "keyword_count": 0,
            "semantic_count": 0,
        }

    subject_oid = ObjectId(subject_id) if subject_id else None

    expanded = get_expander().expand(raw_query)

    keyword_hits = _keyword_search(expanded, subject_oid)
    semantic_hits = _semantic_search(raw_query, subject_oid)

    fused = _rrf_fuse(keyword_hits, semantic_hits)[:limit]
    hydrated = _hydrate([doc_id for doc_id, _ in fused])

    return {
        "query": raw_query,
        "expanded": expanded,
        "results": hydrated,
        "keyword_count": len(keyword_hits),
        "semantic_count": len(semantic_hits),
    }
