"""Mutation service for taxonomy and content.

Encapsulates the cascading delete logic and the cross-collection sync
(e.g. lesson rename also updates the auto-created QBank's title). Keeps
routes thin.

Note on search-index consistency:
  - DELETE flows clean up `search_documents` so deleted content does not
    surface in keyword search results.
  - EDIT and ADD flows do NOT update `search_documents` or the FAISS
    index. After meaningful content edits, run
    `scripts/build_search_index.py` to re-sync. Stale entries in FAISS
    are silently filtered by the hydrate step in search.py.
"""

import base64

from bson import ObjectId

from app.db import Collections, get_db
from app.models import MCQ, Lesson, Subject, Topic, Video, VideoNote
from app.repositories import (
    LessonRepo,
    MCQRepo,
    QBankRepo,
    SubjectRepo,
    TopicRepo,
    VideoNoteRepo,
    VideoRepo,
)


SEARCH_DOCS = "search_documents"


def _read_thumbnail(thumbnail_file) -> tuple[str, str] | None:
    """Read an uploaded thumbnail and return (base64_str, mime_type).

    Returns None when the file slot is empty (browser sends an empty
    FileStorage when nothing is picked). Raises ValueError if the
    uploaded file isn't an image.
    """
    if not thumbnail_file or not getattr(thumbnail_file, "filename", ""):
        return None
    mime_type = (getattr(thumbnail_file, "mimetype", "") or "").lower()
    if not mime_type.startswith("image/"):
        raise ValueError(f"Thumbnail must be an image (got {mime_type!r}).")
    data = thumbnail_file.read()
    if not data:
        return None
    return base64.b64encode(data).decode("ascii"), mime_type


# ---------- Subject ----------

def create_subject(name: str) -> ObjectId:
    name = name.strip()
    if not name:
        raise ValueError("Subject name is required.")
    return SubjectRepo().insert(Subject(name=name, name_lower=name.lower()))


def update_subject(subject_id: str | ObjectId, name: str) -> bool:
    name = name.strip()
    if not name:
        raise ValueError("Subject name is required.")
    return SubjectRepo().update_fields(
        subject_id, {"name": name, "name_lower": name.lower()}
    )


def delete_subject_cascade(subject_id: str | ObjectId) -> dict:
    """Delete a subject and everything under it. Returns counts."""
    oid = subject_id if isinstance(subject_id, ObjectId) else ObjectId(subject_id)
    db = get_db()

    topic_ids = [t["_id"] for t in db[Collections.topics].find({"subject_id": oid}, {"_id": 1})]
    lesson_ids = (
        [l["_id"] for l in db[Collections.lessons].find({"topic_id": {"$in": topic_ids}}, {"_id": 1})]
        if topic_ids else []
    )
    qbank_ids = (
        [q["_id"] for q in db[Collections.qbanks].find({"lesson_id": {"$in": lesson_ids}}, {"_id": 1})]
        if lesson_ids else []
    )

    mcqs_deleted = db[Collections.mcqs].delete_many({"subject_id": oid}).deleted_count
    qbanks_deleted = (
        db[Collections.qbanks].delete_many({"_id": {"$in": qbank_ids}}).deleted_count
        if qbank_ids else 0
    )
    lessons_deleted = (
        db[Collections.lessons].delete_many({"_id": {"$in": lesson_ids}}).deleted_count
        if lesson_ids else 0
    )
    topics_deleted = (
        db[Collections.topics].delete_many({"_id": {"$in": topic_ids}}).deleted_count
        if topic_ids else 0
    )
    subjects_deleted = db[Collections.subjects].delete_one({"_id": oid}).deleted_count

    search_deleted = db[SEARCH_DOCS].delete_many({"subject_id": oid}).deleted_count

    return {
        "subjects": subjects_deleted,
        "topics": topics_deleted,
        "lessons": lessons_deleted,
        "qbanks": qbanks_deleted,
        "mcqs": mcqs_deleted,
        "search_docs": search_deleted,
    }


# ---------- Topic ----------

def create_topic(subject_id: str | ObjectId, name: str) -> ObjectId:
    name = name.strip()
    if not name:
        raise ValueError("Topic name is required.")
    oid = subject_id if isinstance(subject_id, ObjectId) else ObjectId(subject_id)
    return TopicRepo().insert(
        Topic(name=name, name_lower=name.lower(), subject_id=oid)
    )


def update_topic(topic_id: str | ObjectId, name: str) -> bool:
    name = name.strip()
    if not name:
        raise ValueError("Topic name is required.")
    return TopicRepo().update_fields(
        topic_id, {"name": name, "name_lower": name.lower()}
    )


def delete_topic_cascade(topic_id: str | ObjectId) -> dict:
    oid = topic_id if isinstance(topic_id, ObjectId) else ObjectId(topic_id)
    db = get_db()

    lesson_ids = [l["_id"] for l in db[Collections.lessons].find({"topic_id": oid}, {"_id": 1})]
    qbank_ids = (
        [q["_id"] for q in db[Collections.qbanks].find({"lesson_id": {"$in": lesson_ids}}, {"_id": 1})]
        if lesson_ids else []
    )

    mcqs_deleted = db[Collections.mcqs].delete_many({"topic_id": oid}).deleted_count
    qbanks_deleted = (
        db[Collections.qbanks].delete_many({"_id": {"$in": qbank_ids}}).deleted_count
        if qbank_ids else 0
    )
    lessons_deleted = (
        db[Collections.lessons].delete_many({"_id": {"$in": lesson_ids}}).deleted_count
        if lesson_ids else 0
    )
    topics_deleted = db[Collections.topics].delete_one({"_id": oid}).deleted_count

    search_deleted = db[SEARCH_DOCS].delete_many({"topic_id": oid}).deleted_count

    return {
        "topics": topics_deleted,
        "lessons": lessons_deleted,
        "qbanks": qbanks_deleted,
        "mcqs": mcqs_deleted,
        "search_docs": search_deleted,
    }


# ---------- Lesson ----------

def create_lesson(topic_id: str | ObjectId, name: str) -> ObjectId:
    """Insert a lesson + auto-create its single qbank."""
    name = name.strip()
    if not name:
        raise ValueError("Lesson name is required.")
    topic_oid = topic_id if isinstance(topic_id, ObjectId) else ObjectId(topic_id)
    lesson_id = LessonRepo().insert(
        Lesson(name=name, name_lower=name.lower(), topic_id=topic_oid)
    )
    # Mirror the seed behaviour: one qbank per lesson, sharing the name.
    from app.models import QBank  # local to avoid circular import
    QBankRepo().insert(
        QBank(title=name, title_lower=name.lower(), lesson_id=lesson_id)
    )
    return lesson_id


def update_lesson(
    lesson_id: str | ObjectId,
    name: str,
    thumbnail_file=None,
) -> bool:
    """Update a lesson name AND keep the linked qbank's title in sync.

    `thumbnail_file` is an optional uploaded image (Werkzeug FileStorage).
    When provided, it replaces any existing thumbnail. Leaving it empty
    keeps whatever's already stored.
    """
    name = name.strip()
    if not name:
        raise ValueError("Lesson name is required.")
    lesson_oid = lesson_id if isinstance(lesson_id, ObjectId) else ObjectId(lesson_id)

    updates: dict = {"name": name, "name_lower": name.lower()}
    thumb = _read_thumbnail(thumbnail_file)
    if thumb is not None:
        updates["thumbnail"], updates["thumbnail_mime_type"] = thumb

    matched = LessonRepo().update_fields(lesson_oid, updates)
    if matched:
        get_db()[Collections.qbanks].update_many(
            {"lesson_id": lesson_oid},
            {"$set": {"title": name, "title_lower": name.lower()}},
        )
    return matched


def delete_lesson_cascade(lesson_id: str | ObjectId) -> dict:
    oid = lesson_id if isinstance(lesson_id, ObjectId) else ObjectId(lesson_id)
    db = get_db()

    mcqs_deleted = db[Collections.mcqs].delete_many({"lesson_id": oid}).deleted_count
    qbanks_deleted = db[Collections.qbanks].delete_many({"lesson_id": oid}).deleted_count
    lessons_deleted = db[Collections.lessons].delete_one({"_id": oid}).deleted_count
    search_deleted = db[SEARCH_DOCS].delete_many({"lesson_id": oid}).deleted_count

    return {
        "lessons": lessons_deleted,
        "qbanks": qbanks_deleted,
        "mcqs": mcqs_deleted,
        "search_docs": search_deleted,
    }


# ---------- MCQ ----------

def create_mcq_in_qbank(qbank_id: str | ObjectId, form: dict) -> ObjectId:
    """Insert a new MCQ under a qbank. Parent refs are derived from the qbank."""
    qbank = QBankRepo().get(qbank_id)
    if qbank is None:
        raise ValueError("QBank not found.")
    lesson = LessonRepo().get(qbank.lesson_id)
    if lesson is None:
        raise ValueError("Linked lesson not found.")
    topic = TopicRepo().get(lesson.topic_id)
    if topic is None:
        raise ValueError("Linked topic not found.")

    mcq = MCQ(
        title=(form.get("title") or "").strip(),
        option_1=(form.get("option_1") or "").strip(),
        option_2=(form.get("option_2") or "").strip(),
        option_3=(form.get("option_3") or "").strip(),
        option_4=(form.get("option_4") or "").strip(),
        answer=form.get("answer", "option_1"),
        answer_desc=(form.get("answer_desc") or "").strip(),
        subject_id=topic.subject_id,
        topic_id=topic.id,
        lesson_id=lesson.id,
        qbank_id=qbank.id,
    )
    if not mcq.title or not (mcq.option_1 and mcq.option_2 and mcq.option_3 and mcq.option_4):
        raise ValueError("Stem and all four options are required.")
    return MCQRepo().insert(mcq)


def update_mcq(mcq_id: str | ObjectId, form: dict) -> bool:
    """Update an MCQ's content fields. Parent references are immutable here."""
    updates = {
        "title": (form.get("title") or "").strip(),
        "option_1": (form.get("option_1") or "").strip(),
        "option_2": (form.get("option_2") or "").strip(),
        "option_3": (form.get("option_3") or "").strip(),
        "option_4": (form.get("option_4") or "").strip(),
        "answer": form.get("answer", "option_1"),
        "answer_desc": (form.get("answer_desc") or "").strip(),
    }
    if not updates["title"] or not all(
        updates[f"option_{i}"] for i in range(1, 5)
    ):
        raise ValueError("Stem and all four options are required.")
    return MCQRepo().update_fields(mcq_id, updates)


def delete_mcq(mcq_id: str | ObjectId) -> bool:
    return MCQRepo().delete(mcq_id)


# ---------- Video ----------

def create_video(lesson_id: str | ObjectId, form: dict) -> ObjectId:
    lesson_oid = lesson_id if isinstance(lesson_id, ObjectId) else ObjectId(lesson_id)
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Video title is required.")

    duration_raw = (form.get("duration_seconds") or "").strip()
    duration = int(duration_raw) if duration_raw.isdigit() else None

    video = Video(
        title=title,
        file_name=(form.get("file_name") or "").strip() or None,
        description=(form.get("description") or "").strip() or None,
        url=(form.get("url") or "").strip() or None,
        duration_seconds=duration,
        lesson_id=lesson_oid,
        video_transcript_raw=(form.get("video_transcript_raw") or "").strip() or None,
    )
    return VideoRepo().insert(video)


def update_video(
    video_id: str | ObjectId,
    form: dict,
    thumbnail_file=None,
) -> bool:
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Video title is required.")
    duration_raw = (form.get("duration_seconds") or "").strip()
    updates = {
        "title": title,
        "file_name": (form.get("file_name") or "").strip() or None,
        "description": (form.get("description") or "").strip() or None,
        "url": (form.get("url") or "").strip() or None,
        "duration_seconds": int(duration_raw) if duration_raw.isdigit() else None,
        "video_transcript_raw": (form.get("video_transcript_raw") or "").strip() or None,
    }
    thumb = _read_thumbnail(thumbnail_file)
    if thumb is not None:
        updates["thumbnail"], updates["thumbnail_mime_type"] = thumb
    return VideoRepo().update_fields(video_id, updates)


def delete_video_cascade(video_id: str | ObjectId) -> dict:
    """Delete a video and all of its notes."""
    oid = video_id if isinstance(video_id, ObjectId) else ObjectId(video_id)
    notes_deleted = VideoNoteRepo().delete_by_video(oid)
    video_deleted = VideoRepo().delete(oid)
    return {"video": int(video_deleted), "notes": notes_deleted}


# ---------- Video notes ----------

def add_video_note(
    video_id: str | ObjectId,
    image_bytes: bytes,
    mime_type: str,
    order: int | None = None,
) -> ObjectId:
    """Insert a single page-image as a note under a video.

    `image_bytes` is the raw file contents; this function base64-encodes
    it before storing. `order` defaults to the next sequential page
    number for that video.
    """
    if not image_bytes:
        raise ValueError("Image data is required.")
    if not mime_type.startswith("image/"):
        raise ValueError(f"Unsupported mime type: {mime_type}")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    repo = VideoNoteRepo()
    if order is None or order <= 0:
        order = repo.next_order_for_video(video_id)

    note = VideoNote(
        video_id=video_id if isinstance(video_id, ObjectId) else ObjectId(video_id),
        image_data=encoded,
        mime_type=mime_type,
        order=order,
    )
    return repo.insert(note)


def delete_video_note(note_id: str | ObjectId) -> bool:
    return VideoNoteRepo().delete(note_id)


# ---------- Recent updates ----------

def update_recent_update_thumbnail(
    update_id: str | ObjectId,
    thumbnail_file,
) -> bool:
    """Update only the thumbnail on a recent_update doc.

    Recent updates are ingested from JSON; the edit UI only exposes the
    thumbnail upload to keep the surface small.
    """
    thumb = _read_thumbnail(thumbnail_file)
    if thumb is None:
        # Treat "no file" as a no-op rather than an error.
        return False
    from app.repositories import RecentUpdateRepo  # local to avoid cycles
    return RecentUpdateRepo().update_fields(
        update_id,
        {"thumbnail": thumb[0], "thumbnail_mime_type": thumb[1]},
    )
