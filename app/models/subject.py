from app.models.base import BaseDoc


class Subject(BaseDoc):
    name: str
    name_lower: str | None = None
