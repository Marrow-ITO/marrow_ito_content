"""Jinja demo pages for the concept-aware suggest and search APIs.

Two independent pages, one per API:

  /ui/suggest  As-you-type dropdown demo. The page shell is server-rendered;
               the dropdown calls GET /api/suggest live as the user types.

  /ui/search   Results page. Server-side rendered: the route calls the same
               service behind GET /api/search and groups the results by
               content type for display, mirroring the product mock.
"""

from flask import Blueprint, render_template, request

from app.services.api_search import search as do_search


concept_ui_bp = Blueprint("concept_ui", __name__)

# Display order + labels for the result groups (screen-3 grouping).
TYPE_ORDER = [
    "video", "timestamp", "note", "qbank", "recent_update",
    "module", "pearl", "clinical_q",
]
TYPE_LABELS = {
    "video": "Videos",
    "timestamp": "Timestamps",
    "note": "Lecture notes",
    "qbank": "QBank",
    "recent_update": "Recent updates",
    "module": "Modules",
    "pearl": "Pearls",
    "clinical_q": "Clinical questions",
}


def _group_results(results: list[dict]) -> list[dict]:
    """Groups search results by content type in display order.

    Args:
        results: The flat result list from the search service.

    Returns:
        A list of {"type", "label", "items"} groups.
    """
    by_type: dict[str, list[dict]] = {}
    for result in results:
        by_type.setdefault(result.get("type", "other"), []).append(result)

    groups: list[dict] = []
    for type_key in TYPE_ORDER:
        if type_key in by_type:
            groups.append(
                {
                    "type": type_key,
                    "label": TYPE_LABELS.get(type_key, type_key.title()),
                    "rows": by_type.pop(type_key),
                }
            )
    # Any unexpected types fall through, preserving insertion order.
    for type_key, rows in by_type.items():
        groups.append({"type": type_key, "label": type_key.title(), "rows": rows})
    return groups


@concept_ui_bp.route("/ui/suggest")
def suggest_ui():
    """Renders the as-you-type suggest demo page.

    Returns:
        The rendered suggest demo template.
    """
    return render_template("ui_suggest.html")


@concept_ui_bp.route("/ui/search")
def search_ui():
    """Renders the search results demo page for a query.

    Returns:
        The rendered search demo template (empty state when no query).
    """
    query = request.args.get("q", "").strip()
    data = do_search(query) if query else None
    groups = _group_results(data["results"]) if data and data.get("results") else []
    return render_template("ui_search.html", q=query, data=data, groups=groups)
