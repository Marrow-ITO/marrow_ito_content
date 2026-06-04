from app.db import Collections
from app.models import Subject
from app.repositories.base import BaseRepo


class SubjectRepo(BaseRepo[Subject]):
    collection_name = Collections.subjects
    model = Subject
