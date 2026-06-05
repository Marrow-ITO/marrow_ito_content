"""Concept-graph backed autosuggest for GET /api/suggest.

Replaces the old hand-curated ``_SUGGEST_TABLE`` (six fixed prefixes) with a
lookup against the ``concepts`` collection. Flow per keystroke (no LLM, no
embedding — pure Mongo):

  1. Prefix-match the typed text against every concept's search terms
     (synonyms + abbreviations + canonical names).
  2. Pick the single best concept to headline (exact alias beats prefix;
     popularity breaks ties).
  3. Read that concept's typed ``edges`` and render them as the "delight"
     rows ("a type of IBD", "frequently confused", ...).
  4. Backfill with the remaining prefix matches as plain concept rows, so the
     ~1.5k bulk taxonomy concepts still surface useful as-you-type results.

Output matches BACKEND_PRD.md: a list of
``{"text", "context", "type"}`` where type is one of
``concept | subtopic | intent | disambiguation``.
"""

from app.models import Concept
from app.repositories import ConceptRepo


DEFAULT_LIMIT = 8


def _headline_row(concept: Concept) -> dict:
    """Builds the first dropdown row for a concept.

    Args:
        concept: The resolved headline concept.

    Returns:
        A suggestion row dict.
    """
    if concept.abbr:
        # e.g. text "IBD", context "Inflammatory Bowel Disease".
        return {"text": concept.abbr, "context": concept.name, "type": "concept"}
    return {
        "text": concept.name,
        "context": concept.self_context or "common topic",
        "type": "concept",
    }


def _edge_rows(concept: Concept) -> list[dict]:
    """Renders a concept's typed edges into suggestion rows.

    Args:
        concept: The resolved headline concept.

    Returns:
        Ordered suggestion rows derived from the concept's edges.
    """
    label = concept.abbr or concept.name
    edges = concept.edges or {}
    rows: list[dict] = []

    for target in edges.get("child", []):
        rows.append(
            {"text": target, "context": f"a type of {label}", "type": "subtopic"}
        )
    for target in edges.get("confused_with", []):
        rows.append(
            {
                "text": f"{label} vs {target}",
                "context": "frequently confused",
                "type": "disambiguation",
            }
        )
    for target in edges.get("next_step", []):
        rows.append(
            {
                "text": f"{label} — {target}",
                "context": "common intent",
                "type": "intent",
            }
        )
    for target in edges.get("related", []):
        rows.append({"text": target, "context": "related concept", "type": "concept"})

    return rows


def _pick_best(matches: list[Concept], token: str) -> Concept:
    """Chooses the headline concept from the prefix matches.

    Prefers a concept whose search terms contain the typed text exactly (an
    exact abbreviation/alias hit such as "mi" -> Myocardial Infarction);
    otherwise falls back to the most popular match.

    Args:
        matches: Prefix-matched concepts, already popularity-sorted.
        token: The lower-cased typed text.

    Returns:
        The concept to headline.
    """
    exact = [c for c in matches if token in (c.search_terms or [])]
    if exact:
        return exact[0]
    return matches[0]


def suggest(prefix: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Returns as-you-type suggestion rows for a typed prefix.

    Args:
        prefix: The partial query typed by the user.
        limit: Maximum number of rows to return.

    Returns:
        A list of suggestion rows (possibly empty) in the PRD shape.
    """
    token = (prefix or "").strip().lower()
    if not token:
        return []

    matches = ConceptRepo().search_prefix(token, limit=12)
    if not matches:
        return []

    best = _pick_best(matches, token)

    # Dedupe by text, preserving order — a target can appear as both a child
    # and a related concept; keep the first (more specific) rendering.
    rows: list[dict] = []
    seen: set[str] = set()
    for row in [_headline_row(best)] + _edge_rows(best):
        key = row["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    for concept in matches:
        if len(rows) >= limit:
            break
        if concept.name_lower == best.name_lower:
            continue
        if concept.name.lower() in seen:
            continue
        rows.append(
            {
                "text": concept.name,
                "context": concept.self_context or "related topic",
                "type": "concept",
            }
        )
        seen.add(concept.name.lower())

    return rows[:limit]
