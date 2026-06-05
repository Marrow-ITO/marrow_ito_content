from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.config import settings


_client: MongoClient | None = None
_database: Database | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri)
    return _client


def get_db() -> Database:
    global _database
    if _database is None:
        _database = get_client()[settings.mongo_db]
    return _database


def get_collection(name: str) -> Collection:
    return get_db()[name]


class Collections:
    subjects = "subjects"
    topics = "topics"
    lessons = "lessons"
    qbanks = "qbanks"
    videos = "videos"
    video_notes = "video_notes"
    mcqs = "mcqs"
    tests = "tests"
    concepts = "concepts"
    recent_updates = "recent_updates"
