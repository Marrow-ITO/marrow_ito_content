from app.models.base import BaseDoc, PyObjectId


class Lesson(BaseDoc):
    name: str
    name_lower: str | None = None
    topic_id: PyObjectId
    # Base64-encoded thumbnail uploaded via the edit form; surfaced as a
    # data-URI `thumbnail_url` in /api/search results.
    thumbnail: str | None = None
    thumbnail_mime_type: str | None = None
