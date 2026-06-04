from bson import ObjectId

from app.db import Collections
from app.models import Lesson
from app.repositories.base import BaseRepo


class LessonRepo(BaseRepo[Lesson]):
    collection_name = Collections.lessons
    model = Lesson

    def list_by_topic(self, topic_id: str | ObjectId) -> list[Lesson]:
        return self.list_all({"topic_id": self._to_object_id(topic_id)})
