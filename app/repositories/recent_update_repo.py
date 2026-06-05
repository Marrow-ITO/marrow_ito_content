from app.db import Collections
from app.models import RecentUpdate
from app.repositories.base import BaseRepo


class RecentUpdateRepo(BaseRepo[RecentUpdate]):
    collection_name = Collections.recent_updates
    model = RecentUpdate

    def upsert_by_source_id(self, update: RecentUpdate) -> None:
        """Inserts or replaces a recent update, keyed on its source_id.

        Args:
            update: The recent update to persist.

        Returns:
            None.
        """
        payload = update.to_mongo()
        payload.pop("_id", None)
        self.collection.update_one(
            {"source_id": payload["source_id"]},
            {"$set": payload},
            upsert=True,
        )
