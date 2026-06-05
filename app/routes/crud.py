"""CRUD routes for Subject / Topic / Lesson / MCQ / Video / VideoNote.

Form-based (no JSON API) so the existing server-rendered UI just submits
plain POST forms. Each entity has:
  - GET  <new-form>        — render an empty form
  - POST <create>          — handle submission, redirect to detail
  - GET  <edit-form>       — render a pre-filled form
  - POST <edit-submit>     — handle submission, redirect to detail
  - POST <delete>          — cascade where appropriate, redirect to parent

Delete cascades for Subject/Topic/Lesson are handled in app.services.crud.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.repositories import (
    LessonRepo,
    MCQRepo,
    QBankRepo,
    RecentUpdateRepo,
    SubjectRepo,
    TopicRepo,
    VideoNoteRepo,
    VideoRepo,
)
from app.services import crud


crud_bp = Blueprint("crud", __name__)


# ============================================================
# Subject
# ============================================================

@crud_bp.route("/subjects/new", methods=["GET", "POST"])
def subject_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            new_id = crud.create_subject(name)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("form_subject.html", subject=None, name=name)
        return redirect(url_for("browse.subject_detail", subject_id=new_id))
    return render_template("form_subject.html", subject=None, name="")


@crud_bp.route("/subjects/<subject_id>/edit", methods=["GET", "POST"])
def subject_edit(subject_id: str):
    subject = SubjectRepo().get(subject_id)
    if not subject:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            crud.update_subject(subject_id, name)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("form_subject.html", subject=subject, name=name)
        return redirect(url_for("browse.subject_detail", subject_id=subject_id))
    return render_template("form_subject.html", subject=subject, name=subject.name)


@crud_bp.route("/subjects/<subject_id>/delete", methods=["POST"])
def subject_delete(subject_id: str):
    subject = SubjectRepo().get(subject_id)
    if not subject:
        abort(404)
    counts = crud.delete_subject_cascade(subject_id)
    flash(
        f"Deleted subject \"{subject.name}\" "
        f"({counts['topics']} topics, {counts['lessons']} lessons, "
        f"{counts['mcqs']} MCQs).",
        "success",
    )
    return redirect(url_for("browse.index"))


# ============================================================
# Topic
# ============================================================

@crud_bp.route("/subjects/<subject_id>/topics/new", methods=["GET", "POST"])
def topic_new(subject_id: str):
    subject = SubjectRepo().get(subject_id)
    if not subject:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            new_id = crud.create_topic(subject_id, name)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_topic.html", topic=None, subject=subject, name=name
            )
        return redirect(url_for("browse.topic_detail", topic_id=new_id))
    return render_template("form_topic.html", topic=None, subject=subject, name="")


@crud_bp.route("/topics/<topic_id>/edit", methods=["GET", "POST"])
def topic_edit(topic_id: str):
    topic = TopicRepo().get(topic_id)
    if not topic:
        abort(404)
    subject = SubjectRepo().get(topic.subject_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            crud.update_topic(topic_id, name)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_topic.html", topic=topic, subject=subject, name=name
            )
        return redirect(url_for("browse.topic_detail", topic_id=topic_id))
    return render_template(
        "form_topic.html", topic=topic, subject=subject, name=topic.name
    )


@crud_bp.route("/topics/<topic_id>/delete", methods=["POST"])
def topic_delete(topic_id: str):
    topic = TopicRepo().get(topic_id)
    if not topic:
        abort(404)
    parent_subject_id = str(topic.subject_id)
    counts = crud.delete_topic_cascade(topic_id)
    flash(
        f"Deleted topic \"{topic.name}\" "
        f"({counts['lessons']} lessons, {counts['mcqs']} MCQs).",
        "success",
    )
    return redirect(url_for("browse.subject_detail", subject_id=parent_subject_id))


# ============================================================
# Lesson
# ============================================================

@crud_bp.route("/topics/<topic_id>/lessons/new", methods=["GET", "POST"])
def lesson_new(topic_id: str):
    topic = TopicRepo().get(topic_id)
    if not topic:
        abort(404)
    subject = SubjectRepo().get(topic.subject_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            new_id = crud.create_lesson(topic_id, name)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_lesson.html",
                lesson=None, topic=topic, subject=subject, name=name,
            )
        return redirect(url_for("browse.lesson_detail", lesson_id=new_id))
    return render_template(
        "form_lesson.html",
        lesson=None, topic=topic, subject=subject, name="",
    )


@crud_bp.route("/lessons/<lesson_id>/edit", methods=["GET", "POST"])
def lesson_edit(lesson_id: str):
    lesson = LessonRepo().get(lesson_id)
    if not lesson:
        abort(404)
    topic = TopicRepo().get(lesson.topic_id)
    subject = SubjectRepo().get(topic.subject_id) if topic else None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            crud.update_lesson(
                lesson_id,
                name,
                thumbnail_file=request.files.get("thumbnail"),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_lesson.html",
                lesson=lesson, topic=topic, subject=subject, name=name,
            )
        return redirect(url_for("browse.lesson_detail", lesson_id=lesson_id))
    return render_template(
        "form_lesson.html",
        lesson=lesson, topic=topic, subject=subject, name=lesson.name,
    )


@crud_bp.route("/lessons/<lesson_id>/delete", methods=["POST"])
def lesson_delete(lesson_id: str):
    lesson = LessonRepo().get(lesson_id)
    if not lesson:
        abort(404)
    parent_topic_id = str(lesson.topic_id)
    counts = crud.delete_lesson_cascade(lesson_id)
    flash(
        f"Deleted lesson \"{lesson.name}\" ({counts['mcqs']} MCQs).",
        "success",
    )
    return redirect(url_for("browse.topic_detail", topic_id=parent_topic_id))


# ============================================================
# MCQ
# ============================================================

@crud_bp.route("/qbanks/<qbank_id>/mcqs/new", methods=["GET", "POST"])
def mcq_new(qbank_id: str):
    qbank = QBankRepo().get(qbank_id)
    if not qbank:
        abort(404)
    if request.method == "POST":
        try:
            new_id = crud.create_mcq_in_qbank(qbank_id, request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_mcq.html", mcq=None, qbank=qbank, form=request.form
            )
        return redirect(url_for("browse.mcq_detail", mcq_id=new_id))
    return render_template("form_mcq.html", mcq=None, qbank=qbank, form={})


@crud_bp.route("/mcqs/<mcq_id>/edit", methods=["GET", "POST"])
def mcq_edit(mcq_id: str):
    mcq = MCQRepo().get(mcq_id)
    if not mcq:
        abort(404)
    qbank = QBankRepo().get(mcq.qbank_id)
    if request.method == "POST":
        try:
            crud.update_mcq(mcq_id, request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_mcq.html", mcq=mcq, qbank=qbank, form=request.form
            )
        return redirect(url_for("browse.mcq_detail", mcq_id=mcq_id))
    return render_template("form_mcq.html", mcq=mcq, qbank=qbank, form={})


@crud_bp.route("/mcqs/<mcq_id>/delete", methods=["POST"])
def mcq_delete(mcq_id: str):
    mcq = MCQRepo().get(mcq_id)
    if not mcq:
        abort(404)
    parent_qbank_id = str(mcq.qbank_id)
    crud.delete_mcq(mcq_id)
    flash("MCQ deleted.", "success")
    return redirect(url_for("browse.qbank_detail", qbank_id=parent_qbank_id))


# ============================================================
# Video
# ============================================================

@crud_bp.route("/lessons/<lesson_id>/videos/new", methods=["GET", "POST"])
def video_new(lesson_id: str):
    lesson = LessonRepo().get(lesson_id)
    if not lesson:
        abort(404)
    if request.method == "POST":
        try:
            new_id = crud.create_video(lesson_id, request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_video.html", video=None, lesson=lesson, form=request.form
            )
        return redirect(url_for("browse.video_detail", video_id=new_id))
    return render_template("form_video.html", video=None, lesson=lesson, form={})


@crud_bp.route("/videos/<video_id>/edit", methods=["GET", "POST"])
def video_edit(video_id: str):
    video = VideoRepo().get(video_id)
    if not video:
        abort(404)
    lesson = LessonRepo().get(video.lesson_id)
    if request.method == "POST":
        try:
            crud.update_video(
                video_id,
                request.form,
                thumbnail_file=request.files.get("thumbnail"),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "form_video.html", video=video, lesson=lesson, form=request.form
            )
        return redirect(url_for("browse.video_detail", video_id=video_id))
    return render_template("form_video.html", video=video, lesson=lesson, form={})


@crud_bp.route("/videos/<video_id>/delete", methods=["POST"])
def video_delete(video_id: str):
    video = VideoRepo().get(video_id)
    if not video:
        abort(404)
    parent_lesson_id = str(video.lesson_id)
    counts = crud.delete_video_cascade(video_id)
    flash(
        f"Deleted video \"{video.title}\" ({counts['notes']} notes).",
        "success",
    )
    return redirect(url_for("browse.lesson_detail", lesson_id=parent_lesson_id))


# ============================================================
# Video notes
# ============================================================

@crud_bp.route("/videos/<video_id>/notes/new", methods=["POST"])
def video_note_add(video_id: str):
    video = VideoRepo().get(video_id)
    if not video:
        abort(404)

    files = request.files.getlist("images")
    # Filter out empty file slots (browser sends one even when nothing picked).
    files = [f for f in files if f and f.filename]
    if not files:
        flash("Please choose at least one image file.", "error")
        return redirect(url_for("browse.video_detail", video_id=video_id))

    # Order: append after existing notes, preserving the submission order of
    # the selected files.
    starting_order = VideoNoteRepo().next_order_for_video(video_id)

    added = 0
    skipped_kind: list[str] = []
    skipped_other: list[str] = []

    for offset, f in enumerate(files):
        mime_type = (f.mimetype or "image/png").lower()
        if not mime_type.startswith("image/"):
            skipped_kind.append(f.filename)
            continue
        try:
            crud.add_video_note(
                video_id=video_id,
                image_bytes=f.read(),
                mime_type=mime_type,
                order=starting_order + added,
            )
            added += 1
        except ValueError as exc:
            skipped_other.append(f"{f.filename}: {exc}")

    if added:
        flash(
            f"Added {added} note{'' if added == 1 else 's'}.",
            "success",
        )
    if skipped_kind:
        flash(
            "Skipped (unsupported file type): " + ", ".join(skipped_kind),
            "error",
        )
    for msg in skipped_other:
        flash(f"Skipped: {msg}", "error")

    return redirect(url_for("browse.video_detail", video_id=video_id))


@crud_bp.route("/video-notes/<note_id>/delete", methods=["POST"])
def video_note_delete(note_id: str):
    note = VideoNoteRepo().get(note_id)
    if not note:
        abort(404)
    parent_video_id = str(note.video_id)
    crud.delete_video_note(note_id)
    flash("Note deleted.", "success")
    return redirect(url_for("browse.video_detail", video_id=parent_video_id))


# ============================================================
# Recent updates
# ============================================================

@crud_bp.route("/recent-updates", methods=["GET"])
def recent_update_list():
    repo = RecentUpdateRepo()
    updates = list(
        repo.collection.find(
            {},
            {"update_topic": 1, "subject_name": 1, "date_of_update": 1, "thumbnail": 1},
        ).sort([("date_of_update", -1)])
    )
    return render_template("recent_updates_list.html", updates=updates)


@crud_bp.route("/recent-updates/<update_id>/edit", methods=["GET", "POST"])
def recent_update_edit(update_id: str):
    update = RecentUpdateRepo().get(update_id)
    if not update:
        abort(404)
    if request.method == "POST":
        try:
            ok = crud.update_recent_update_thumbnail(
                update_id, thumbnail_file=request.files.get("thumbnail")
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("form_recent_update.html", update=update)
        if ok:
            flash("Thumbnail updated.", "success")
        else:
            flash("Please choose an image file.", "error")
        return redirect(
            url_for("crud.recent_update_edit", update_id=update_id)
        )
    return render_template("form_recent_update.html", update=update)
