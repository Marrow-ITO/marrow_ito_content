"""JSON API endpoints consumed by the React frontend.

Contract spelled out in BACKEND_PRD.md. CORS is enabled at the app factory
for `/api/*` so the local React dev server can hit these directly.
"""

from flask import Blueprint, jsonify, request

from app.services.api_search import search as do_search
from app.services.concept_suggest import suggest as do_suggest
from app.services.recent_update_api import fetch_recent_update
from app.services.video_api import fetch_video


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/search", methods=["GET"])
def search_endpoint():
    q = request.args.get("q", "")
    if not q.strip():
        return jsonify({"error": "Missing required query parameter 'q'."}), 400
    return jsonify(do_search(q))


@api_bp.route("/suggest", methods=["GET"])
def suggest_endpoint():
    q = request.args.get("q", "")
    return jsonify({"query": q.strip(), "suggestions": do_suggest(q)})


@api_bp.route("/videos/<video_id>", methods=["GET"])
def video_detail_endpoint(video_id: str):
    start_time_raw = request.args.get("start_time")
    start_time: int | None = None
    if start_time_raw is not None and start_time_raw != "":
        try:
            start_time = int(start_time_raw)
        except ValueError:
            return jsonify({
                "error": "Invalid start_time, must be integer seconds."
            }), 400
        if start_time < 0:
            return jsonify({
                "error": "start_time must be non-negative."
            }), 400

    payload = fetch_video(video_id, start_time=start_time)
    if payload is None:
        return jsonify({"error": "Video not found."}), 404
    return jsonify(payload)


@api_bp.route("/recent_updates/<update_id>", methods=["GET"])
def recent_update_detail_endpoint(update_id: str):
    payload = fetch_recent_update(update_id)
    if payload is None:
        return jsonify({"error": "Recent update not found."}), 404
    return jsonify(payload)
