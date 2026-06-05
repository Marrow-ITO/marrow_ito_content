"""Service behind GET /api/videos/<id>.

Fetches a video and the hierarchical context the frontend needs to render
the player page (subject / topic / lesson breadcrumb), plus any URL we
have. Echoes the client's `start_time` back when supplied so the player
can seek to the right moment from a search result.

For YouTube-hosted videos we also extract the bare YouTube video ID from
`video.url` and surface it as `video_id` so the frontend can embed the
player without re-parsing the URL.
"""

from urllib.parse import parse_qs, urlparse

from bson import ObjectId

from app.repositories import (
    LessonRepo,
    SubjectRepo,
    TopicRepo,
    VideoRepo,
)


_YOUTUBE_HOSTS = {
    "youtube.com",
    "youtu.be",
    "m.youtube.com",
    "www.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def extract_youtube_video_id(url: str | None) -> str | None:
    """Pull the 11-ish-char YouTube video id out of any common URL form.

    Handles:
      youtube.com/watch?v=ID  ·  youtu.be/ID  ·  youtube.com/embed/ID
      youtube.com/shorts/ID   ·  youtube.com/v/ID

    Returns None if `url` is empty / not a YouTube URL / has no extractable id.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
    except (ValueError, AttributeError):
        return None

    host = (parsed.netloc or "").lower()
    if host not in _YOUTUBE_HOSTS:
        return None

    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/", 1)[0]
        return candidate or None

    path = parsed.path or ""
    if path in ("/watch", "/watch/"):
        candidate = parse_qs(parsed.query).get("v", [None])[0]
        return candidate or None

    for prefix in ("/embed/", "/shorts/", "/v/", "/live/"):
        if path.startswith(prefix):
            candidate = path[len(prefix):].strip("/").split("/", 1)[0]
            return candidate or None

    return None


def fetch_video(video_id: str, start_time: int | None = None) -> dict | None:
    """Return a JSON-ready dict, or None if the video doesn't exist."""
    if not video_id or not ObjectId.is_valid(video_id):
        return None

    video = VideoRepo().get(video_id)
    if not video:
        return None

    lesson = LessonRepo().get(video.lesson_id) if video.lesson_id else None
    topic = TopicRepo().get(lesson.topic_id) if lesson else None
    subject = SubjectRepo().get(topic.subject_id) if topic else None

    payload: dict = {
        "id": str(video.id),
        "title": video.title,
        "url": video.url,
        "video_id": extract_youtube_video_id(video.url),
        "file_name": video.file_name,
        "duration_seconds": video.duration_seconds,
        "description": video.description,
        "lesson_id": str(lesson.id) if lesson else None,
        "lesson_name": lesson.name if lesson else None,
        "topic_id": str(topic.id) if topic else None,
        "topic_name": topic.name if topic else None,
        "subject_id": str(subject.id) if subject else None,
        "subject_name": subject.name if subject else None,
    }

    if start_time is not None:
        payload["start_time"] = start_time

    return payload
