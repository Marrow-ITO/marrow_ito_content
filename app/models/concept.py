from pydantic import Field

from app.models.base import BaseDoc


class Concept(BaseDoc):
    """A single node in the medical concept graph.

    A concept is one medical term (a disease, drug, procedure or syllabus
    topic). It carries every string a user might type for it (``aliases`` /
    ``search_terms``) so the same node powers abbreviation expansion and the
    as-you-type dropdown, plus typed ``edges`` to neighbouring concepts that
    become the "delight" rows in the suggest response.

    Attributes:
        name: Canonical display name, e.g. "Inflammatory Bowel Disease".
        name_lower: Lower-cased canonical name, used as the upsert key.
        abbr: Short form shown as the headline row text, e.g. "IBD". None for
            concepts that have no abbreviation (most syllabus topics).
        self_context: The context label for the headline row. For abbreviated
            concepts this is left None (the canonical name is used); for
            taxonomy nodes it is the parent's name, e.g. "a topic in Anatomy".
        aliases: Lower-cased synonyms / abbreviations / spelling variants.
        search_terms: Lower-cased, de-duplicated union of the canonical name
            and every alias. This is the prefix-searchable field.
        edges: Typed relationships -> lists of neighbouring concept display
            names. Recognised keys: "child", "related", "confused_with",
            "next_step".
        source: Where the node came from, e.g. "curated" or "taxonomy".
        popularity: Ranking tie-breaker (0..1); curated demo concepts rank
            above bulk taxonomy nodes.
    """

    name: str
    name_lower: str | None = None
    abbr: str | None = None
    self_context: str | None = None
    aliases: list[str] = Field(default_factory=list)
    search_terms: list[str] = Field(default_factory=list)
    edges: dict[str, list[str]] = Field(default_factory=dict)
    source: str = "curated"
    popularity: float = 0.0
