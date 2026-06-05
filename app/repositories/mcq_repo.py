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

    def _counts_grouped_by(
        self, group_field: str, match: dict | None = None
    ) -> dict[ObjectId, int]:
        pipeline: list[dict] = []
        if match:
            pipeline.append({"$match": match})
        pipeline.append(
            {"$group": {"_id": f"${group_field}", "count": {"$sum": 1}}}
        )
        return {
            doc["_id"]: doc["count"]
            for doc in self.collection.aggregate(pipeline)
            if doc["_id"] is not None
        }

    def counts_by_subject(self) -> dict[ObjectId, int]:
        return self._counts_grouped_by("subject_id")

    def counts_by_topic(self, subject_id: str | ObjectId) -> dict[ObjectId, int]:
        return self._counts_grouped_by(
            "topic_id", {"subject_id": self._to_object_id(subject_id)}
        )

    def counts_by_lesson(self, topic_id: str | ObjectId) -> dict[ObjectId, int]:
        return self._counts_grouped_by(
            "lesson_id", {"topic_id": self._to_object_id(topic_id)}
        )

    def counts_by_qbank(self, lesson_id: str | ObjectId) -> dict[ObjectId, int]:
        return self._counts_grouped_by(
            "qbank_id", {"lesson_id": self._to_object_id(lesson_id)}
        )

    def count_by_qbank(self, qbank_id: str | ObjectId) -> int:
        return self.collection.count_documents(
            {"qbank_id": self._to_object_id(qbank_id)}
        )
