from app.models.base import BaseDoc, PyObjectId


class Topic(BaseDoc):
    name: str
    subject_id: PyObjectId
