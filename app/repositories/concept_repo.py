import re

from app.db import Collections
from app.models import Concept
from app.repositories.base import BaseRepo


class ConceptRepo(BaseRepo[Concept]):
    """Repository for the medical concept graph.

    Adds concept-graph specific helpers on top of BaseRepo: index creation,
    upsert keyed on the canonical name, and the word-boundary prefix search
    that backs the as-you-type dropdown.
    """

    collection_name = Collections.concepts
    model = Concept

    def ensure_indexes(self) -> None:
        """Creates the indexes the suggest path relies on.

        Returns:
            None.
        """
        # Multikey index over the searchable terms; an anchored word-boundary
        # regex (\b<token>) can use this for the common case.
        self.collection.create_index("search_terms")
        self.collection.create_index("name_lower")
        self.collection.create_index([("popularity", -1)])

    def upsert_by_name(self, concept: Concept) -> None:
        """Inserts or fully replaces a concept's fields, keyed on name_lower.

        Args:
            concept: The concept to persist. ``name_lower`` must be set.

        Returns:
            None.
        """
        payload = concept.to_mongo()
        payload.pop("_id", None)
        self.collection.update_one(
            {"name_lower": payload["name_lower"]},
            {"$set": payload},
            upsert=True,
        )

    def insert_if_absent(self, concept: Concept) -> bool:
        """Inserts a concept only when no node with the same name_lower exists.

        Used by the taxonomy build so it never overwrites a richer curated
        node (curated wins on name collisions).

        Args:
            concept: The concept to insert.

        Returns:
            True if a new document was inserted, False if one already existed.
        """
        payload = concept.to_mongo()
        payload.pop("_id", None)
        result = self.collection.update_one(
            {"name_lower": payload["name_lower"]},
            {"$setOnInsert": payload},
            upsert=True,
        )
        return result.upserted_id is not None

    def search_prefix(self, prefix: str, limit: int = 12) -> list[Concept]:
        """Returns concepts whose any search term starts at a word boundary.

        Word-boundary (``\\b<token>``) rather than start-anchored, so typing
        "bowel" still finds "inflammatory bowel disease". Results are ordered
        by popularity (curated concepts first).

        Args:
            prefix: The raw typed text.
            limit: Maximum number of concepts to return.

        Returns:
            A list of matching Concept documents, possibly empty.
        """
        token = (prefix or "").strip().lower()
        if not token:
            return []
        pattern = r"\b" + re.escape(token)
        cursor = (
            self.collection.find({"search_terms": {"$regex": pattern}})
            .sort("popularity", -1)
            .limit(limit)
        )
        return [self.model.model_validate(d) for d in cursor]
