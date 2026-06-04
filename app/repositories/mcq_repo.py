from bson import ObjectId

from app.db import Collections
from app.models import MCQ
from app.repositories.base import BaseRepo


class MCQRepo(BaseRepo[MCQ]):
    collection_name = Collections.mcqs
    model = MCQ

    def list_by_qbank(self, qbank_id: str | ObjectId) -> list[MCQ]:
        return self.list_all({"qbank_id": self._to_object_id(qbank_id)})

    def list_by_ids(self, mcq_ids: list[ObjectId]) -> list[MCQ]:
        if not mcq_ids:
            return []
        cursor = self.collection.find({"_id": {"$in": mcq_ids}})
        return [self.model.model_validate(d) for d in cursor]
