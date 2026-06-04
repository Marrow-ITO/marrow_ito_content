from app.db import Collections
from app.models import Test
from app.repositories.base import BaseRepo


class TestRepo(BaseRepo[Test]):
    collection_name = Collections.tests
    model = Test
