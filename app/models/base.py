from typing import Annotated, Any

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_object_id(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    raise ValueError(f"Invalid ObjectId: {value!r}")


PyObjectId = Annotated[ObjectId, BeforeValidator(_validate_object_id)]


class BaseDoc(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: PyObjectId | None = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data
