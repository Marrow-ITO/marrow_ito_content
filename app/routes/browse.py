from flask import Blueprint, abort, render_template

from app.repositories import (
    LessonRepo,
    MCQRepo,
    QBankRepo,
    SubjectRepo,
    TestRepo,
    TopicRepo,
    VideoNoteRepo,
    VideoRepo,
)


browse_bp = Blueprint("browse", __name__)


@browse_bp.route("/")
def index():
    subjects = SubjectRepo().list_all()
    mcq_counts = MCQRepo().counts_by_subject()
    video_counts = VideoRepo().counts_by_subject()
    return render_template(
        "index.html",
        subjects=subjects,
        mcq_counts=mcq_counts,
        video_counts=video_counts,
    )


@browse_bp.route("/subjects/<subject_id>")
def subject_detail(subject_id: str):
    subject = SubjectRepo().get(subject_id)
    if not subject:
        abort(404)
    topics = TopicRepo().list_by_subject(subject_id)
    mcq_counts = MCQRepo().counts_by_topic(subject_id)
    video_counts = VideoRepo().counts_by_topic(subject_id)
    return render_template(
        "subject.html",
        subject=subject,
        topics=topics,
        mcq_counts=mcq_counts,
        video_counts=video_counts,
    )


@browse_bp.route("/topics/<topic_id>")
def topic_detail(topic_id: str):
    topic = TopicRepo().get(topic_id)
    if not topic:
        abort(404)
    subject = SubjectRepo().get(topic.subject_id)
    lessons = LessonRepo().list_by_topic(topic_id)
    mcq_counts = MCQRepo().counts_by_lesson(topic_id)
    video_counts = VideoRepo().counts_by_lesson(topic_id)
    return render_template(
        "topic.html",
        topic=topic,
        subject=subject,
        lessons=lessons,
        mcq_counts=mcq_counts,
        video_counts=video_counts,
    )


@browse_bp.route("/lessons/<lesson_id>")
def lesson_detail(lesson_id: str):
    lesson = LessonRepo().get(lesson_id)
    if not lesson:
        abort(404)
    topic = TopicRepo().get(lesson.topic_id)
    subject = SubjectRepo().get(topic.subject_id) if topic else None
    qbanks = QBankRepo().list_by_lesson(lesson_id)
    videos = VideoRepo().list_by_lesson(lesson_id)
    mcq_counts = MCQRepo().counts_by_qbank(lesson_id)
    return render_template(
        "lesson.html",
        lesson=lesson,
        topic=topic,
        subject=subject,
        qbanks=qbanks,
        videos=videos,
        mcq_counts=mcq_counts,
    )


@browse_bp.route("/qbanks/<qbank_id>")
def qbank_detail(qbank_id: str):
    qbank = QBankRepo().get(qbank_id)
    if not qbank:
        abort(404)
    lesson = LessonRepo().get(qbank.lesson_id)
    topic = TopicRepo().get(lesson.topic_id) if lesson else None
    subject = SubjectRepo().get(topic.subject_id) if topic else None
    mcqs = MCQRepo().list_by_qbank(qbank_id)
    return render_template(
        "qbank.html",
        qbank=qbank,
        lesson=lesson,
        topic=topic,
        subject=subject,
        mcqs=mcqs,
    )


@browse_bp.route("/mcqs/<mcq_id>")
def mcq_detail(mcq_id: str):
    mcq = MCQRepo().get(mcq_id)
    if not mcq:
        abort(404)
    qbank = QBankRepo().get(mcq.qbank_id)
    lesson = LessonRepo().get(mcq.lesson_id)
    topic = TopicRepo().get(mcq.topic_id)
    subject = SubjectRepo().get(mcq.subject_id)
    return render_template(
        "mcq.html",
        mcq=mcq,
        qbank=qbank,
        lesson=lesson,
        topic=topic,
        subject=subject,
    )


@browse_bp.route("/videos/<video_id>")
def video_detail(video_id: str):
    video = VideoRepo().get(video_id)
    if not video:
        abort(404)
    lesson = LessonRepo().get(video.lesson_id)
    topic = TopicRepo().get(lesson.topic_id) if lesson else None
    subject = SubjectRepo().get(topic.subject_id) if topic else None
    notes = VideoNoteRepo().list_by_video(video_id)
    return render_template(
        "video.html",
        video=video,
        lesson=lesson,
        topic=topic,
        subject=subject,
        notes=notes,
    )


@browse_bp.route("/tests")
def tests_list():
    tests = TestRepo().list_all()
    return render_template("tests.html", tests=tests)


@browse_bp.route("/tests/<test_id>")
def test_detail(test_id: str):
    test = TestRepo().get(test_id)
    if not test:
        abort(404)
    mcqs = MCQRepo().list_by_ids(test.mcq_ids)
    return render_template("test_detail.html", test=test, mcqs=mcqs)
