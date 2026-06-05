from pydantic import Field

from app.models.base import BaseDoc, PyObjectId


class RecentUpdate(BaseDoc):
    """A recent clinical/guideline update, ingested from recent_update_ito.json.

    Mirrors the source JSON, with the source subject string mapped onto our
    own subjects taxonomy (subject_id / subject_name) for grouping and search
    context.

    Attributes:
        source_id: The `id` from the source JSON (stable external key).
        date_of_update: ISO date string of the update, e.g. "2024-11-19".
        subject: The original subject string from the source JSON.
        subject_id: Mapped subject _id in our taxonomy, or None if unmapped.
        subject_name: Our canonical subject name, or None if unmapped.
        update_topic: The headline of the update (boosted in search).
        content: The full update body.
        reference: Source attribution, e.g.
            {"source_name": ..., "reference_link": ...}.
    """

    source_id: int
    date_of_update: str | None = None
    subject: str | None = None
    subject_id: PyObjectId | None = None
    subject_name: str | None = None
    update_topic: str
    content: str
    reference: dict = Field(default_factory=dict)
