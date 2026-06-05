from typing import Generic, TypeVar

from bson import ObjectId
from pymongo.collection import Collection

from app.db import get_collection
from app.models.base import BaseDoc


T = TypeVar("T", bound=BaseDoc)


class BaseRepo(Generic[T]):
    collection_name: str
    model: type[T]

    @property
    def collection(self) -> Collection:
        return get_collection(self.collection_name)

    def _to_object_id(self, value: str | ObjectId) -> ObjectId:
        return value if isinstance(value, ObjectId) else ObjectId(value)

    def get(self, doc_id: str | ObjectId) -> T | None:
        doc = self.collection.find_one({"_id": self._to_object_id(doc_id)})
        return self.model.model_validate(doc) if doc else None

    def list_all(self, filter_: dict | None = None) -> list[T]:
        cursor = self.collection.find(filter_ or {})
        return [self.model.model_validate(d) for d in cursor]

    def insert(self, doc: T) -> ObjectId:
        payload = doc.to_mongo()
        payload.pop("_id", None)
        result = self.collection.insert_one(payload)
        return result.inserted_id

    def update_fields(
        self, doc_id: str | ObjectId, fields: dict
    ) -> bool:
        """Update specific fields on a document. Returns True if matched."""
        if not fields:
            return False
        result = self.collection.update_one(
            {"_id": self._to_object_id(doc_id)},
            {"$set": fields},
        )
        return result.matched_count > 0

    def delete(self, doc_id: str | ObjectId) -> bool:
        result = self.collection.delete_one(
            {"_id": self._to_object_id(doc_id)}
        )
        return result.deleted_count > 0
