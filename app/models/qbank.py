from app.models.base import BaseDoc, PyObjectId


class QBank(BaseDoc):
    title: str
    title_lower: str | None = None
    lesson_id: PyObjectId
