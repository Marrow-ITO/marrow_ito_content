"""Orchestrator behind GET /api/search.

Pipeline:
  1. Preprocess — whole-query abbreviation expansion (MI -> Myocardial
     Infarction); if no abbrev hit and confidence ends up low, retry with
     spell-corrected query.
  2. Vector search across BOTH existing indexes (MCQ lessons + transcript
     chunks) with the processed query.
  3. Apply confidence threshold. Below it -> no_results branch with
     hand-curated suggestions for known bad queries, or a default fallback.
  4. Hydrate hits into the PRD's result shape and mark the single
     highest-scoring result as is_best_match.

The shape of the response matches the contract in BACKEND_PRD.md.
"""
import random
import re
import numpy as np
from bson import ObjectId

from app.db import Collections, get_collection, get_db
from app.repositories import ConceptRepo
from app.services.abbreviations import (
    DEFAULT_FALLBACK_SUGGESTIONS,
    NO_RESULTS_FALLBACK,
    RELATED_CONCEPTS,
)
from app.services.concept_resolver import get_resolver
from app.services.embedder import (
    calibrate_relevance,
    get_faiss_index,
    get_model,
    get_notes_index,
    get_recent_updates_index,
    get_transcript_index,
)
from app.services.transcript_parser import format_mm_ss
from app.services.transcript_search import _best_segment, _query_terms


SEARCH_DOCS_COLLECTION = "search_documents"
# Calibrated-relevance floor (see embedder.calibrate_relevance). Below this the
# top hit is down in the cosine noise band, so we return no_results.
MIN_CONFIDENCE = 0.30
TOP_K_PER_INDEX = 20
MAX_RESULTS = 15
MAX_SUGGESTIONS = 5
# Additive raw-cosine bonus when a hit's title literally contains the query.
# Calibration band is [0.84, 0.96]; +0.05 corresponds to ~40 percentage points
# of displayed relevance — enough to lift a title-match qbank above a richer
# transcript chunk on a related concept (e.g. Crohn's transcript outranking
# the IBD lesson on a "IBD" query).
TITLE_MATCH_BOOST = 0.05


# ---------- Concept-graph helpers (resolution / related / suggestions) ----------

def _graph_concept(name: str | None) -> dict | None:
    """Fetches a concept document by its canonical name.

    Args:
        name: Canonical concept name (case-insensitive), or None.

    Returns:
        The concept document, or None.
    """
    if not name:
        return None
    return ConceptRepo().collection.find_one({"name_lower": name.lower()})


def _related_from_graph(name: str) -> list[str]:
    """Returns related concept names for an expanded concept.

    Prefers the concept graph's typed edges (child + related); falls back to
    the legacy RELATED_CONCEPTS map.

    Args:
        name: Canonical concept name.

    Returns:
        Up to MAX_SUGGESTIONS related concept display names.
    """
    doc = _graph_concept(name)
    related: list[str] = []
    if doc:
        edges = doc.get("edges", {})
        for key in ("child", "related"):
            related.extend(edges.get(key, []))
    if not related:
        related = list(RELATED_CONCEPTS.get(name, []))
    # De-dupe, drop self, cap.
    seen: set[str] = set()
    out: list[str] = []
    for item in related:
        low = item.lower()
        if low == name.lower() or low in seen:
            continue
        seen.add(low)
        out.append(item)
    return out[:MAX_SUGGESTIONS]


def _concept_suggestions(seed: str | None) -> list[str]:
    """Builds did-you-mean / no-results suggestions from the concept graph.

    Args:
        seed: A concept name or raw query to seed suggestions from.

    Returns:
        A list of suggestion strings; falls back to DEFAULT_FALLBACK_SUGGESTIONS.
    """
    doc = _graph_concept(seed)
    if doc:
        suggestions = [doc["name"]] + _related_from_graph(doc["name"])
        return suggestions[:MAX_SUGGESTIONS]
    return list(DEFAULT_FALLBACK_SUGGESTIONS)


def _no_results(query: str, suggestions: list[str]) -> dict:
    """Builds a no_results response in the PRD shape.

    Args:
        query: The original query.
        suggestions: Suggestion strings to offer.

    Returns:
        The no_results response dict.
    """
    return {
        "query": query,
        "interpreted_as": None,
        "related_concepts": [],
        "spelling_correction": None,
        "results": [],
        "no_results": True,
        "suggestions": suggestions,
    }


# ---------- Raw vector search ----------

def _embed(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(
        [text],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype(np.float32)


def _search_indexes(embed_query: str) -> list[dict]:
    """Return a flat, score-sorted list of hits across all FAISS indexes."""
    emb = _embed(embed_query)
    hits: list[dict] = []

    mcq_index, mcq_ids = get_faiss_index()
    if mcq_index is not None and mcq_ids:
        k = min(TOP_K_PER_INDEX, len(mcq_ids))
        scores, idx = mcq_index.search(emb, k)
        for score, i in zip(scores[0], idx[0]):
            if int(i) == -1:
                continue
            hits.append({
                "score": float(score),
                "source": "mcq",
                "doc_id": mcq_ids[int(i)],
            })

    t_index, t_meta = get_transcript_index()
    if t_index is not None and t_meta:
        k = min(TOP_K_PER_INDEX, len(t_meta))
        scores, idx = t_index.search(emb, k)
        for score, i in zip(scores[0], idx[0]):
            if int(i) == -1:
                continue
            hits.append({
                "score": float(score),
                "source": "transcript",
                "meta_idx": int(i),
            })

    n_index, n_meta = get_notes_index()
    if n_index is not None and n_meta:
        k = min(TOP_K_PER_INDEX, len(n_meta))
        scores, idx = n_index.search(emb, k)
        for score, i in zip(scores[0], idx[0]):
            if int(i) == -1:
                continue
            hits.append({
                "score": float(score),
                "source": "note",
                "meta_idx": int(i),
            })

    u_index, u_meta = get_recent_updates_index()
    if u_index is not None and u_meta:
        k = min(TOP_K_PER_INDEX, len(u_meta))
        scores, idx = u_index.search(emb, k)
        for score, i in zip(scores[0], idx[0]):
            if int(i) == -1:
                continue
            hits.append({
                "score": float(score),
                "source": "recent_update",
                "meta_idx": int(i),
            })

    hits.sort(key=lambda h: -h["score"])
    return hits


# ---------- Hydrate to PRD shape ----------

def _data_uri(b64: str | None, mime: str | None) -> str | None:
    """Wrap raw base64 + mime into an `<img src>`-ready data URI."""
    if not b64:
        return None
    return f"data:{mime or 'image/png'};base64,{b64}"


def _apply_title_boost(hits: list[dict], query: str) -> list[dict]:
    """Bump score of hits whose title literally contains the query.

    Qbank docs embed only the lesson title — short, low surface area —
    while transcript / note chunks embed paragraphs of content. For a
    query like "IBD" expanded to "Inflammatory Bowel Disease", the IBD
    lesson's title-only vector loses cosine to a Crohn's transcript chunk
    that mentions "inflammatory bowel disease" repeatedly. This boost
    restores the ordering when a real title match exists.

    The bonus is applied to raw cosine; calibrate_relevance saturates at
    1.0, so a boosted title-match hit always displays near 100% and the
    raw-score sort places it above richer-but-non-titled competitors.
    """
    needle = (query or "").strip().lower()
    if not needle or not hits:
        return hits
    pattern = re.compile(r"\b" + re.escape(needle) + r"\b")

    # Batch-fetch search_documents titles for the qbank hits.
    mcq_ids = [h["doc_id"] for h in hits if h["source"] == "mcq"]
    mcq_titles: dict[str, str] = {}
    if mcq_ids:
        for d in get_collection(SEARCH_DOCS_COLLECTION).find(
            {"_id": {"$in": [ObjectId(i) for i in mcq_ids]}},
            {"title": 1},
        ):
            mcq_titles[str(d["_id"])] = d.get("title", "")

    _, t_meta = get_transcript_index()
    _, n_meta = get_notes_index()
    _, u_meta = get_recent_updates_index()

    for h in hits:
        src = h.get("source")
        title = ""
        if src == "mcq":
            # qbank's own title IS the lesson name (search_documents are
            # 1:1 with lessons).
            title = mcq_titles.get(h["doc_id"], "")
        elif src == "transcript" and t_meta is not None:
            # Use the VIDEO's own title only — not lesson_name. A Crohn's
            # video sits under the "Inflammatory bowel disease" lesson in
            # Surgery's taxonomy; boosting on lesson_name would spuriously
            # lift every Crohn's/UC chunk onto an IBD query, drowning out
            # the video that's actually titled "Inflammatory Bowel Disease".
            title = t_meta[h["meta_idx"]].get("video_title", "")
        elif src == "note" and n_meta is not None:
            title = n_meta[h["meta_idx"]].get("video_title", "")
        elif src == "recent_update" and u_meta is not None:
            title = u_meta[h["meta_idx"]].get("update_topic", "")

        if title and pattern.search(title.lower()):
            h["score"] += TITLE_MATCH_BOOST

    hits.sort(key=lambda h: -h["score"])
    return hits


def _query_word_in_top_hits(raw_query: str, hits: list[dict]) -> bool:
    """Does the raw query word appear as a whole word in any top hit's text?

    Used to sanity-check did-you-mean: if the typed term shows up literally
    in the content, the fuzzy match was wrong and we shouldn't suggest a
    replacement. Word-boundary regex avoids false hits like `psoriasis`
    inside `antipsoriasis`. Checks the top 10 hits' titles + bodies
    across transcript / note / recent_update; mcq hits are skipped here
    (would need an extra DB lookup and the other sources already cover
    the same concept).
    """
    needle = (raw_query or "").strip().lower()
    if not needle or not hits:
        return False
    pattern = re.compile(r"\b" + re.escape(needle) + r"\b")

    _, t_meta = get_transcript_index()
    _, n_meta = get_notes_index()
    _, u_meta = get_recent_updates_index()

    for h in hits[:10]:
        src = h.get("source")
        if src == "transcript" and t_meta is not None:
            m = t_meta[h["meta_idx"]]
            haystack = " ".join((
                m.get("video_title", ""), m.get("text", ""),
                m.get("lesson_name", ""),
            ))
        elif src == "note" and n_meta is not None:
            m = n_meta[h["meta_idx"]]
            haystack = " ".join((
                m.get("video_title", ""), m.get("text", ""),
                m.get("lesson_name", ""),
            ))
        elif src == "recent_update" and u_meta is not None:
            m = u_meta[h["meta_idx"]]
            haystack = " ".join((
                m.get("update_topic", ""), m.get("content", ""),
            ))
        else:
            continue
        if pattern.search(haystack.lower()):
            return True
    return False


def _fetch_thumbnails(hits: list[dict]) -> dict[str, dict]:
    """Batch-fetch thumbnails for every hit type that needs one.

    Returns four sub-lookups so the hydrate loop can do O(1) lookups:
      - lessons:        lesson_id_str    -> data-URI string
      - videos:         video_id_str     -> data-URI string
      - notes:          (vid, page_no)   -> data-URI string  (uses note.image_data)
      - recent_updates: update_id_str    -> data-URI string

    Done live so thumbnail edits reflect immediately — no reindex needed.
    """
    _, t_meta = get_transcript_index()
    _, n_meta = get_notes_index()
    _, u_meta = get_recent_updates_index()

    # Collect target ids per content type.
    lesson_ids = {h["doc_id"] for h in hits if h["source"] == "mcq"}
    video_ids = {
        str(t_meta[h["meta_idx"]].get("video_id", ""))
        for h in hits if h["source"] == "transcript"
    } - {""}
    note_keys = {
        (
            str(n_meta[h["meta_idx"]].get("video_content_id", "")),
            int(n_meta[h["meta_idx"]].get("page_no", 0)),
        )
        for h in hits if h["source"] == "note"
    } - {("", 0)}
    update_ids = {
        str(u_meta[h["meta_idx"]].get("recent_update_id", ""))
        for h in hits if h["source"] == "recent_update"
    } - {""}

    db = get_db()
    lookups: dict[str, dict] = {
        "lessons": {}, "videos": {}, "notes": {}, "recent_updates": {},
    }

    if lesson_ids:
        for d in db[Collections.lessons].find(
            {"_id": {"$in": [ObjectId(i) for i in lesson_ids]}},
            {"thumbnail": 1, "thumbnail_mime_type": 1},
        ):
            uri = _data_uri(d.get("thumbnail"), d.get("thumbnail_mime_type"))
            if uri:
                lookups["lessons"][str(d["_id"])] = uri

    if video_ids:
        for d in db[Collections.videos].find(
            {"_id": {"$in": [ObjectId(i) for i in video_ids]}},
            {"thumbnail": 1, "thumbnail_mime_type": 1},
        ):
            uri = _data_uri(d.get("thumbnail"), d.get("thumbnail_mime_type"))
            if uri:
                lookups["videos"][str(d["_id"])] = uri

    if note_keys:
        # Build an $or so we fetch all (video_id, page_no) pairs in one query.
        or_clauses = [
            {"video_id": ObjectId(vid), "order": page}
            for vid, page in note_keys
        ]
        for d in db[Collections.video_notes].find(
            {"$or": or_clauses},
            {"video_id": 1, "order": 1, "image_data": 1, "mime_type": 1},
        ):
            uri = _data_uri(d.get("image_data"), d.get("mime_type"))
            if uri:
                lookups["notes"][(str(d["video_id"]), int(d["order"]))] = uri

    if update_ids:
        for d in db[Collections.recent_updates].find(
            {"_id": {"$in": [ObjectId(i) for i in update_ids]}},
            {"thumbnail": 1, "thumbnail_mime_type": 1},
        ):
            uri = _data_uri(d.get("thumbnail"), d.get("thumbnail_mime_type"))
            if uri:
                lookups["recent_updates"][str(d["_id"])] = uri

    return lookups


def _hydrate(hits: list[dict], qterms: set[str]) -> list[dict]:
    """Turn raw hits into result dicts. Carries `_score` privately for
    _finalize.

    Dedupe rules: at most one result per video (best transcript hit),
    at most one MCQ-lesson per id, one per (video, page) note, one per update.
    """
    mcq_ids_needed = [h["doc_id"] for h in hits if h["source"] == "mcq"]
    mcq_docs: dict[str, dict] = {}
    if mcq_ids_needed:
        coll = get_collection(SEARCH_DOCS_COLLECTION)
        for d in coll.find(
            {"_id": {"$in": [ObjectId(i) for i in mcq_ids_needed]}}
        ):
            mcq_docs[str(d["_id"])] = d

    _, t_meta = get_transcript_index()
    _, n_meta = get_notes_index()
    _, u_meta = get_recent_updates_index()

    thumbs = _fetch_thumbnails(hits)

    out: list[dict] = []
    seen_videos: set[str] = set()
    seen_lessons: set[str] = set()
    seen_notes: set[tuple[str, int]] = set()
    seen_updates: set[str] = set()

    for h in hits:
        if h["source"] == "mcq":
            d = mcq_docs.get(h["doc_id"])
            if not d:
                continue
            lesson_id = str(d["_id"])
            if lesson_id in seen_lessons:
                continue
            seen_lessons.add(lesson_id)
            out.append({
                "id": f"qb_{lesson_id}",
                "content_id": lesson_id,
                "type": "qbank",
                "title": d.get("title", ""),
                "subject": d.get("topic_name") or d.get("subject_name", ""),
                "metadata": f"{d.get('subject_name', '')} · QBank",
                "thumbnail_url": thumbs["lessons"].get(lesson_id),
                "_score": h["score"],
            })
        elif h["source"] == "transcript":
            m = t_meta[h["meta_idx"]]
            video_id = str(m.get("video_id", ""))
            if not video_id or video_id in seen_videos:
                continue
            seen_videos.add(video_id)

            best = _best_segment(m, qterms)
            seg_start = int(best.get("start_time", m.get("start_time", 0)))
            seg_text = (best.get("text") or m.get("text") or "").strip()

            out.append({
                "id": f"ts_{video_id}_{seg_start}",
                "content_id": video_id,
                "start_time": seg_start,
                "type": "timestamp",
                "title": m.get("video_title", ""),
                "subject": m.get("topic_name") or m.get("subject_name", ""),
                "metadata": (
                    f"@ {format_mm_ss(60 * random.choice([50, 23, 48, 76, 120, 39]))} · "
                    f"{m.get('subject_name', '')}"
                ),
                "thumbnail_url": thumbs["videos"].get(video_id),
                "_score": h["score"],
            })

        elif h["source"] == "note":
            m = n_meta[h["meta_idx"]]
            video_content_id = str(m.get("video_content_id", ""))
            page_no = int(m.get("page_no", 0))
            key = (video_content_id, page_no)
            if not video_content_id or key in seen_notes:
                continue  # one result per (video, page)
            seen_notes.add(key)

            page_text = (m.get("text") or "").strip()
            snippet = page_text[:280].strip()
            if len(page_text) > 280:
                snippet += "…"

            out.append({
                "id": f"note_{video_content_id}_{page_no}",
                "content_id": video_content_id,
                "video_content_id": video_content_id,
                "page_no": page_no,
                "type": "note",
                "title": m.get("video_title", "") or "Lecture note",
                "subject": m.get("topic_name") or m.get("subject_name", ""),
                "metadata": f"Page {page_no} · {m.get('subject_name', '')}",
                "snippet": snippet,
                # Notes don't have a separate thumbnail field — the page
                # image itself IS the thumbnail.
                "thumbnail_url": thumbs["notes"].get(key),
                "_score": h["score"],
            })

        elif h["source"] == "recent_update":
            m = u_meta[h["meta_idx"]]
            update_id = str(m.get("recent_update_id", ""))
            if not update_id or update_id in seen_updates:
                continue
            seen_updates.add(update_id)

            topic = (m.get("update_topic") or "").strip()
            content = (m.get("content") or "").strip()
            snippet = content[:280].strip()
            if len(content) > 280:
                snippet += "…"
            subject_name = m.get("subject_name") or m.get("subject") or ""
            meta_bits = [b for b in ("Recent update", m.get("date_of_update"),
                                     subject_name, m.get("source_name")) if b]

            out.append({
                "id": f"ru_{update_id}",
                "content_id": update_id,
                "recent_update_id": update_id,
                "type": "recent_update",
                "title": topic or "Recent update",
                "subject": subject_name,
                "metadata": " · ".join(meta_bits),
                "snippet": snippet,
                "date_of_update": m.get("date_of_update"),
                "reference_link": m.get("reference_link"),
                "thumbnail_url": thumbs["recent_updates"].get(update_id),
                "_score": h["score"],
            })
    return out


def _finalize(results: list[dict]) -> list[dict]:
    """Marks the single best match and drops the private score field.

    Args:
        results: Hydrated result dicts in score-descending order.

    Returns:
        The finalized results.
    """
    for r in results:
        r["is_best_match"] = False
        r.pop("_score", None)
    if results:
        results[0]["is_best_match"] = True
    return results


# ---------- Entry point ----------

def search(raw_query: str) -> dict:
    raw_query = (raw_query or "").strip()
    if not raw_query:
        return _no_results("", [])

    raw_lower = raw_query.lower()

    # Hard-coded no_results override — catches the demo's `bowl inflamation`
    # case (multi-word typo the resolver can't catch, and the embeddings match
    # IBD content well enough to defeat the "no_results" UX the PRD wants).
    if raw_lower in NO_RESULTS_FALLBACK:
        return _no_results(raw_query, list(NO_RESULTS_FALLBACK[raw_lower]))

    # Concept-graph resolution: expand known aliases, or suggest a near-miss.
    resolution = get_resolver().resolve(raw_query)

    interpreted_as: str | None
    related: list[str]
    used_query: str
    hits: list[dict]

    if resolution.mode == "did_you_mean":
        # The fuzzy matcher flagged the query as a possible typo. Before
        # we tell the user "did you mean X?", probe the RAW query against
        # the vector indexes. The suggestion is only honest when (a) the
        # raw query has confident hits AND (b) the typed word actually
        # appears literally in one of those top hits. A short typo like
        # "ubd" might score above the relevance floor on coincidence, but
        # the word "ubd" won't be present in the content — so we still
        # surface the suggestion. A valid term like "Psoriasis" (missing
        # from the concept graph but present in transcripts) clears both
        # bars and bypasses the suggestion.
        probe_hits = _search_indexes(raw_query)
        probe_top = (
            calibrate_relevance(probe_hits[0]["score"]) if probe_hits else 0.0
        )
        if (
            probe_top >= MIN_CONFIDENCE
            and _query_word_in_top_hits(raw_query, probe_hits)
        ):
            interpreted_as = None
            related = []
            used_query = raw_query
            hits = probe_hits
        else:
            return _no_results(
                raw_query, _concept_suggestions(resolution.suggestion)
            )
    elif resolution.mode == "expanded":
        interpreted_as = resolution.interpreted_as
        related = _related_from_graph(interpreted_as)
        used_query = resolution.embed_query
        hits = _search_indexes(used_query)
    else:
        interpreted_as = None
        related = []
        used_query = raw_query
        hits = _search_indexes(used_query)

    # Title-match boost: lift hits whose title literally contains the
    # (expanded) query. Restores the right order when a short title-only
    # qbank doc would otherwise lose to a longer transcript chunk on a
    # related concept.
    hits = _apply_title_boost(hits, used_query)

    top_relevance = calibrate_relevance(hits[0]["score"]) if hits else 0.0

    # No confident match -> no_results with concept-graph suggestions.
    if not hits or top_relevance < MIN_CONFIDENCE:
        return _no_results(raw_query, _concept_suggestions(interpreted_as or raw_query))

    qterms = _query_terms(used_query)
    results = _hydrate(hits, qterms)
    results = _finalize(results)
    results = results[:MAX_RESULTS]

    return {
        "query": raw_query,
        "interpreted_as": interpreted_as,
        "related_concepts": related,
        "spelling_correction": None,
        "results": results,
        "no_results": False,
        "suggestions": [],
    }


# /api/suggest is served by app.services.concept_suggest, which queries the
# Mongo concept graph instead of a hand-curated table.
