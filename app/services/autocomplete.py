"""Synonym-aware word-boundary autocomplete over lesson/topic/qbank titles.

Matches `\\b<term>` (word starts with the typed text anywhere in the title)
rather than `^<term>` (title starts with the typed text). So typing "bowel"
finds "Inflammatory bowel disease", not only titles literally starting with
"bowel".

When the typed text matches a synonym (e.g. "IBD" -> "inflammatory bowel
disease"), we run the word-boundary match against every candidate in the
synonym equivalence class via a `$or` query.

Trade-off: word-boundary regex doesn't use the B-tree index on
`name_lower`. At ~1500 docs (subjects + topics + lessons + qbanks) this is
a few milliseconds collection scan — fine for autocomplete latency.
"""

import re

from app.db import Collections, get_db
from app.services.synonym_expander import get_expander


def _safe_word_boundary(term: str) -> str:
    """Build a regex that matches `term` at a word boundary anywhere."""
    return r"\b" + re.escape(term.strip().lower())


def _build_filter(candidates: list[str], field: str) -> dict:
    """Build a `$or` filter that word-boundary-matches `field` against any candidate."""
    if len(candidates) == 1:
        return {field: {"$regex": _safe_word_boundary(candidates[0])}}
    return {
        "$or": [
            {field: {"$regex": _safe_word_boundary(c)}}
            for c in candidates
        ]
    }


def autocomplete(prefix: str, limit: int = 10) -> list[dict]:
    """Return up to `limit` matching items across lessons + topics + subjects.

    Each result: {type, id, name, parent_id?}.
    Synonyms are expanded so abbreviations (UC, IBD, MI, ...) surface
    matches against the full form.
    """
    prefix = (prefix or "").strip()
    if not prefix:
        return []

    candidates = get_expander().prefix_candidates(prefix)
    if not candidates:
        candidates = [prefix.lower()]

    db = get_db()
    per_kind = max(3, limit // 3)
    results: list[dict] = []
    seen_ids: set[str] = set()

    # Lessons first — typical drill-down target.
    for doc in db[Collections.lessons].find(
        _build_filter(candidates, "name_lower"),
        {"name": 1, "topic_id": 1},
    ).limit(per_kind * 2):  # over-fetch for de-dupe headroom
        doc_id = str(doc["_id"])
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        results.append(
            {
                "type": "lesson",
                "id": doc_id,
                "name": doc.get("name", ""),
                "parent_id": str(doc["topic_id"]),
            }
        )
        if len(results) >= per_kind:
            break

    for doc in db[Collections.topics].find(
        _build_filter(candidates, "name_lower"),
        {"name": 1, "subject_id": 1},
    ).limit(per_kind):
        results.append(
            {
                "type": "topic",
                "id": str(doc["_id"]),
                "name": doc.get("name", ""),
                "parent_id": str(doc["subject_id"]),
            }
        )

    for doc in db[Collections.subjects].find(
        _build_filter(candidates, "name_lower"),
        {"name": 1},
    ).limit(per_kind):
        results.append(
            {
                "type": "subject",
                "id": str(doc["_id"]),
                "name": doc.get("name", ""),
            }
        )

    return results[:limit]
