from app.models.base import BaseDoc, PyObjectId


class Topic(BaseDoc):
    name: str
    name_lower: str | None = None
    subject_id: PyObjectId
