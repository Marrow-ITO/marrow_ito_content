from bson import ObjectId

from app.db import Collections
from app.models import QBank
from app.repositories.base import BaseRepo


class QBankRepo(BaseRepo[QBank]):
    collection_name = Collections.qbanks
    model = QBank

    def list_by_lesson(self, lesson_id: str | ObjectId) -> list[QBank]:
        return self.list_all({"lesson_id": self._to_object_id(lesson_id)})
