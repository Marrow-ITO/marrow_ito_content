"""Search-related HTTP routes: /search, /search/transcripts, /api/autocomplete."""

from flask import Blueprint, jsonify, render_template, request

from app.repositories import SubjectRepo
from app.services.autocomplete import autocomplete as do_autocomplete
from app.services.search import search as do_search
from app.services.transcript_search import search as do_transcript_search


search_bp = Blueprint("search", __name__)


@search_bp.route("/api/autocomplete")
def autocomplete_api():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"q": q, "suggestions": []})
    suggestions = do_autocomplete(q, limit=10)
    return jsonify({"q": q, "suggestions": suggestions})


@search_bp.route("/search")
def search_page():
    q = request.args.get("q", "").strip()
    subject_id = request.args.get("subject_id") or None

    subjects = SubjectRepo().list_all()
    selected_subject_name = None
    if subject_id:
        match = next((s for s in subjects if str(s.id) == subject_id), None)
        if match:
            selected_subject_name = match.name
        else:
            subject_id = None  # invalid, ignore

    if not q:
        return render_template(
            "search.html",
            q="",
            results=[],
            subjects=subjects,
            selected_subject_id=subject_id,
            selected_subject_name=selected_subject_name,
            expanded="",
            keyword_count=0,
            semantic_count=0,
        )

    result = do_search(q, subject_id=subject_id, limit=20)

    return render_template(
        "search.html",
        q=result["query"],
        results=result["results"],
        subjects=subjects,
        selected_subject_id=subject_id,
        selected_subject_name=selected_subject_name,
        expanded=result["expanded"],
        keyword_count=result["keyword_count"],
        semantic_count=result["semantic_count"],
    )


@search_bp.route("/search/transcripts")
def transcript_search_page():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template(
            "search_transcripts.html",
            q="",
            results=[],
            ready=True,
            mode="raw",
            interpreted_as=None,
            matched_alias=None,
            suggestion=None,
            no_confident=False,
        )
    result = do_transcript_search(q, limit=20)
    return render_template(
        "search_transcripts.html",
        q=result["query"],
        results=result["results"],
        ready=result["ready"],
        mode=result["mode"],
        interpreted_as=result["interpreted_as"],
        matched_alias=result["matched_alias"],
        suggestion=result["suggestion"],
        no_confident=result["no_confident"],
    )
