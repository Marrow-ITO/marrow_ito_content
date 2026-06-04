from app.models.base import BaseDoc, PyObjectId


class Test(BaseDoc):
    title: str
    mcq_ids: list[PyObjectId] = []
