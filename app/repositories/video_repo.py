from bson import ObjectId

from app.db import Collections
from app.models import Video
from app.repositories.base import BaseRepo


class VideoRepo(BaseRepo[Video]):
    collection_name = Collections.videos
    model = Video

    def list_by_lesson(self, lesson_id: str | ObjectId) -> list[Video]:
        return self.list_all({"lesson_id": self._to_object_id(lesson_id)})
