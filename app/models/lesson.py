from app.models.base import BaseDoc, PyObjectId


class Lesson(BaseDoc):
    name: str
    name_lower: str | None = None
    topic_id: PyObjectId
