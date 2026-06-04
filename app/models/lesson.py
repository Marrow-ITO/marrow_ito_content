from app.models.base import BaseDoc, PyObjectId


class Lesson(BaseDoc):
    name: str
    topic_id: PyObjectId
