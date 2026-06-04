from app.models.base import BaseDoc, PyObjectId


class QBank(BaseDoc):
    title: str
    lesson_id: PyObjectId
