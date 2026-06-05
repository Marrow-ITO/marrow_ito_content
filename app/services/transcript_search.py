"""Semantic search over video transcript chunks.

Reads the transcript FAISS + meta produced by
`scripts/build_transcript_index.py`. Query is embedded with the same
sentence-transformer model used at build time; we return the top-K
chunks by cosine similarity.

For each retrieved chunk we then PIN-POINT the timestamp where the
matched content begins: the chunk carries its per-segment data
(`segments: [{start_time, text}]`), and we score each segment by how
many query terms (synonym-expanded) appear in it. The winning
segment's start_time is what we display — so a search for "UC" lands
on the segment that actually starts with "Ulcerative colitis", not on
the chunk boundary three intro sentences earlier.
"""

import re

import numpy as np

from app.services.concept_resolver import get_resolver
from app.services.embedder import calibrate_relevance, get_model, get_transcript_index
from app.services.synonym_expander import STOP_WORDS, get_expander
from app.services.transcript_parser import format_mm_ss


SEMANTIC_TOP_K = 20

# Raw cosine from this bi-encoder (S-PubMedBert) lives in a narrow cone: even
# gibberish scores ~0.80 and unrelated medical text ~0.85, while a strong
# match is ~0.95+. Showing the raw cosine as a "% match" makes noise look
# confident. We linearly rescale the meaningful band [FLOOR, CEIL] -> [0, 1]
# for display only; the raw cosine is still returned as `score`. These two
# constants are model-level properties (re-tune if the embedding model
# changes), not query-specific.
# Minimum calibrated relevance (0..1) for the top hit; below this the whole
# result set is noise (the query resolved to nothing and matched nothing
# meaningfully), so we return no-confident-match instead of junk.
_MIN_CONFIDENCE = 0.30

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-/]*")


def _query_terms(raw_query: str) -> set[str]:
    """Tokens to look for in segments. Synonym-expanded, stop-word-stripped.

    Example: "UC" -> {"uc", "ulcerative", "colitis", "ibd",
                      "inflammatory", "bowel", "disease",
                      "cd", "crohn", "crohns"}
    """
    expanded = get_expander().expand(raw_query).lower()
    tokens = {
        t for t in _TOKEN_RE.findall(expanded)
        if t and t not in STOP_WORDS and len(t) > 1
    }
    # Always include the verbatim query tokens too.
    for t in _TOKEN_RE.findall(raw_query.lower()):
        if t and t not in STOP_WORDS and len(t) > 1:
            tokens.add(t)
    return tokens


def _best_segment(chunk: dict, query_tokens: set[str]) -> dict:
    """Pick the in-chunk segment with the most query-term hits.

    Tie-breaker: earliest segment wins. Falls back to the chunk-level
    start_time + text if a chunk has no `segments` field (older index).
    """
    segments = chunk.get("segments") or []
    if not segments:
        return {
            "start_time": int(chunk.get("start_time", 0)),
            "text": chunk.get("text", ""),
        }

    if not query_tokens:
        return segments[0]

    best = None
    best_score = -1  # so a 0-hit segment still beats no choice
    for seg in segments:
        seg_text = (seg.get("text") or "").lower()
        if not seg_text:
            continue
        score = sum(1 for t in query_tokens if t in seg_text)
        if score > best_score:
            best_score = score
            best = seg
    return best or segments[0]


def search(query: str, limit: int = SEMANTIC_TOP_K) -> dict:
    raw_query = (query or "").strip()
    base = {
        "query": raw_query,
        "results": [],
        "ready": True,
        "mode": "raw",
        "interpreted_as": None,
        "matched_alias": None,
        "suggestion": None,
        "no_confident": False,
    }
    if not raw_query:
        return base

    index, meta = get_transcript_index()
    if index is None or not meta:
        base["ready"] = False
        return base

    # Resolve typos / abbreviations against the concept graph first.
    resolution = get_resolver().resolve(raw_query)
    base["mode"] = resolution.mode

    if resolution.mode == "did_you_mean":
        # Never silently rewrite — suggest and return no results.
        base["suggestion"] = resolution.suggestion
        return base

    if resolution.mode == "expanded":
        base["interpreted_as"] = resolution.interpreted_as
        base["matched_alias"] = resolution.matched_alias

    embed_query = resolution.embed_query

    model = get_model()
    query_emb = model.encode(
        [embed_query],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    ).astype(np.float32)

    # Over-fetch so that video-level dedup still yields `limit` results.
    # FAISS hits are returned in score-descending order, so the first hit
    # we see for each video is also the best one for that video.
    k = min(max(limit * 5, 100), len(meta))
    scores, idx = index.search(query_emb, k)

    qterms = _query_terms(embed_query)

    results: list[dict] = []
    seen_videos: set[str] = set()
    for score, i in zip(scores[0], idx[0]):
        if int(i) == -1:
            continue
        m = meta[int(i)]
        video_id = m.get("video_id") or ""
        if video_id in seen_videos:
            continue  # one result per video — keep the best-scoring chunk
        seen_videos.add(video_id)

        best = _best_segment(m, qterms)
        seg_start = int(best.get("start_time", m.get("start_time", 0)))
        seg_text = (best.get("text") or m.get("text") or "").strip()
        snippet = seg_text[:280].strip()
        if len(seg_text) > 280:
            snippet += "…"

        results.append({
            "video_id": video_id,
            "video_title": m.get("video_title", ""),
            "lesson_id": m.get("lesson_id"),
            "lesson_name": m.get("lesson_name", ""),
            "topic_name": m.get("topic_name", ""),
            "subject_name": m.get("subject_name", ""),
            "start_time": seg_start,
            "start_time_label": format_mm_ss(seg_start),
            "chunk_start_time": int(m.get("start_time", 0)),
            "end_time": int(m.get("end_time", 0)),
            "snippet": snippet,
            "score": float(score),
            "relevance": calibrate_relevance(float(score)),
        })

        if len(results) >= limit:
            break

    # Confidence gate: if even the best hit is down in the noise band, the
    # query matched nothing meaningfully — return no-confident-match.
    if not results or results[0]["relevance"] < _MIN_CONFIDENCE:
        base["no_confident"] = True
        return base

    base["results"] = results
    return base
