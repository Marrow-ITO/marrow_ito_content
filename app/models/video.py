from app.models.base import BaseDoc, PyObjectId


class Video(BaseDoc):
    title: str
    description: str | None = None
    url: str | None = None
    duration_seconds: int | None = None
    lesson_id: PyObjectId
