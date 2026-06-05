from bson import ObjectId

from app.db import Collections
from app.models import VideoNote
from app.repositories.base import BaseRepo


class VideoNoteRepo(BaseRepo[VideoNote]):
    collection_name = Collections.video_notes
    model = VideoNote

    def list_by_video(self, video_id: str | ObjectId) -> list[VideoNote]:
        cursor = self.collection.find(
            {"video_id": self._to_object_id(video_id)}
        ).sort("order", 1)
        return [self.model.model_validate(d) for d in cursor]

    def delete_by_video(self, video_id: str | ObjectId) -> int:
        return self.collection.delete_many(
            {"video_id": self._to_object_id(video_id)}
        ).deleted_count

    def next_order_for_video(self, video_id: str | ObjectId) -> int:
        last = list(
            self.collection.find(
                {"video_id": self._to_object_id(video_id)}, {"order": 1}
            )
            .sort("order", -1)
            .limit(1)
        )
        return (last[0]["order"] + 1) if last else 1
