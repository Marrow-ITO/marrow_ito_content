"""Service behind GET /api/qbank/<id>.

Returns the qbank, its parent taxonomy (lesson / topic / subject), the
lesson's thumbnail if any, and the full MCQ list under the qbank.

The route accepts either a qbank ObjectId or the lesson ObjectId. Search
results return `content_id = lesson_id` for qbank hits (because
search_documents are 1:1 with lessons), so accepting either keeps the
frontend from having to do an intermediate lookup.
"""

from bson import ObjectId

from app.repositories import (
    LessonRepo,
    MCQRepo,
    QBankRepo,
    SubjectRepo,
    TopicRepo,
)


_OPTION_KEYS = ("option_1", "option_2", "option_3", "option_4")


def _mcq_payload(mcq) -> dict:
    """Flatten an MCQ document for the API response."""
    answer_str = mcq.answer.value if hasattr(mcq.answer, "value") else mcq.answer
    try:
        answer_index = _OPTION_KEYS.index(answer_str)
    except ValueError:
        answer_index = 0
    return {
        "id": str(mcq.id),
        "title": mcq.title,
        "options": [
            mcq.option_1,
            mcq.option_2,
            mcq.option_3,
            mcq.option_4,
        ],
        "answer": answer_str,
        "answer_index": answer_index,
        "answer_desc": mcq.answer_desc,
    }


def _resolve_qbank(id_str: str):
    """Try `id_str` as a qbank id first, then as a lesson id. Returns the
    QBank model or None.
    """
    oid = ObjectId(id_str)

    qbank = QBankRepo().get(oid)
    if qbank is not None:
        return qbank

    # Fall back: maybe the caller passed the lesson id (search returns that
    # as `content_id` for qbank hits).
    qbanks = QBankRepo().list_by_lesson(oid)
    return qbanks[0] if qbanks else None


def fetch_qbank(id_str: str) -> dict | None:
    """JSON-ready qbank detail payload, or None if not found."""
    if not id_str or not ObjectId.is_valid(id_str):
        return None

    qbank = _resolve_qbank(id_str)
    if qbank is None:
        return None

    lesson = LessonRepo().get(qbank.lesson_id)
    topic = TopicRepo().get(lesson.topic_id) if lesson else None
    subject = SubjectRepo().get(topic.subject_id) if topic else None

    mcqs = MCQRepo().list_by_qbank(qbank.id)

    thumbnail_url: str | None = None
    if lesson and lesson.thumbnail:
        mime = lesson.thumbnail_mime_type or "image/png"
        thumbnail_url = f"data:{mime};base64,{lesson.thumbnail}"

    return {
        "id": str(qbank.id),
        "title": qbank.title,
        "thumbnail_url": thumbnail_url,
        "lesson_id": str(lesson.id) if lesson else None,
        "lesson_name": lesson.name if lesson else None,
        "topic_id": str(topic.id) if topic else None,
        "topic_name": topic.name if topic else None,
        "subject_id": str(subject.id) if subject else None,
        "subject_name": subject.name if subject else None,
        "mcq_count": len(mcqs),
        "mcqs": [_mcq_payload(m) for m in mcqs],
    }
