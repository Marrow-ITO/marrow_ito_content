from bson import ObjectId

from app.db import Collections
from app.models import Video
from app.repositories.base import BaseRepo


class VideoRepo(BaseRepo[Video]):
    collection_name = Collections.videos
    model = Video

    def list_by_lesson(self, lesson_id: str | ObjectId) -> list[Video]:
        return self.list_all({"lesson_id": self._to_object_id(lesson_id)})

    def counts_by_subject(self) -> dict[ObjectId, int]:
        """Count videos grouped by their lesson's topic's subject_id."""
        pipeline = [
            {"$lookup": {
                "from": Collections.lessons,
                "localField": "lesson_id",
                "foreignField": "_id",
                "as": "lesson",
            }},
            {"$unwind": "$lesson"},
            {"$lookup": {
                "from": Collections.topics,
                "localField": "lesson.topic_id",
                "foreignField": "_id",
                "as": "topic",
            }},
            {"$unwind": "$topic"},
            {"$group": {"_id": "$topic.subject_id", "count": {"$sum": 1}}},
        ]
        return {
            doc["_id"]: doc["count"]
            for doc in self.collection.aggregate(pipeline)
            if doc["_id"] is not None
        }

    def counts_by_topic(
        self, subject_id: str | ObjectId
    ) -> dict[ObjectId, int]:
        """Count videos grouped by topic_id, scoped to one subject."""
        subject_oid = self._to_object_id(subject_id)
        pipeline = [
            {"$lookup": {
                "from": Collections.lessons,
                "localField": "lesson_id",
                "foreignField": "_id",
                "as": "lesson",
            }},
            {"$unwind": "$lesson"},
            {"$lookup": {
                "from": Collections.topics,
                "localField": "lesson.topic_id",
                "foreignField": "_id",
                "as": "topic",
            }},
            {"$unwind": "$topic"},
            {"$match": {"topic.subject_id": subject_oid}},
            {"$group": {"_id": "$topic._id", "count": {"$sum": 1}}},
        ]
        return {
            doc["_id"]: doc["count"]
            for doc in self.collection.aggregate(pipeline)
            if doc["_id"] is not None
        }

    def counts_by_lesson(
        self, topic_id: str | ObjectId
    ) -> dict[ObjectId, int]:
        """Count videos grouped by lesson_id, scoped to one topic."""
        topic_oid = self._to_object_id(topic_id)
        pipeline = [
            {"$lookup": {
                "from": Collections.lessons,
                "localField": "lesson_id",
                "foreignField": "_id",
                "as": "lesson",
            }},
            {"$unwind": "$lesson"},
            {"$match": {"lesson.topic_id": topic_oid}},
            {"$group": {"_id": "$lesson_id", "count": {"$sum": 1}}},
        ]
        return {
            doc["_id"]: doc["count"]
            for doc in self.collection.aggregate(pipeline)
            if doc["_id"] is not None
        }
