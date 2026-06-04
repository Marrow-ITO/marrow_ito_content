from bson import ObjectId

from app.db import Collections
from app.models import Topic
from app.repositories.base import BaseRepo


class TopicRepo(BaseRepo[Topic]):
    collection_name = Collections.topics
    model = Topic

    def list_by_subject(self, subject_id: str | ObjectId) -> list[Topic]:
        return self.list_all({"subject_id": self._to_object_id(subject_id)})
