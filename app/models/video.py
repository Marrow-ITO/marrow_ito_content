from app.models.base import BaseDoc, PyObjectId


class Video(BaseDoc):
    title: str
    file_name: str | None = None
    description: str | None = None
    url: str | None = None
    duration_seconds: int | None = None
    lesson_id: PyObjectId
    # Inline `[mm:ss] text` lines. Source-of-truth for transcript search.
    video_transcript_raw: str | None = None


class VideoNote(BaseDoc):
    """A single page-image attached to a video.

    `image_data` is a base64-encoded string (data-URI body without the
    `data:image/...;base64,` prefix); the mime type is in `mime_type`.
    Stored in a separate collection so 16MB Mongo doc limit doesn't bite
    when a video has many large pages.
    """
    video_id: PyObjectId
    image_data: str
    mime_type: str = "image/png"
    order: int = 1
