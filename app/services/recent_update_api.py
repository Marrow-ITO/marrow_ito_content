"""Service behind GET /api/recent_updates/<id>.

Fetches a single recent update by its Mongo _id and returns a JSON-ready
dict, mirroring the shape produced by video_api.fetch_video.
"""

from bson import ObjectId

from app.repositories import RecentUpdateRepo


def fetch_recent_update(update_id: str) -> dict | None:
    """Return a JSON-ready recent-update dict, or None if it doesn't exist.

    Args:
        update_id: The recent update's Mongo _id (hex string).

    Returns:
        The update payload, or None for a missing / invalid id.
    """
    if not update_id or not ObjectId.is_valid(update_id):
        return None

    update = RecentUpdateRepo().get(update_id)
    if not update:
        return None

    return {
        "id": str(update.id),
        "source_id": update.source_id,
        "date_of_update": update.date_of_update,
        "subject": update.subject,
        "subject_id": str(update.subject_id) if update.subject_id else None,
        "subject_name": update.subject_name,
        "update_topic": update.update_topic,
        "content": update.content,
        "reference": update.reference,
    }
