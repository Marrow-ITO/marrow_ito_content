"""Typo / abbreviation aware query resolver, backed by the concept graph.

The embedding model resolves bare phrases (uc <-> ulcerative colitis) but
fails to *retrieve* from short abbreviations or typos: the signal is too
diffuse to separate the right chunk from the cone of noise, and an OOV typo
("ubd") collapses to subword junk. So we resolve the query deterministically
against the concept graph BEFORE embedding, into one of three modes:

  - "expanded":     the query is a known alias/abbreviation ("uc", "ibd").
                    We return the canonical name to embed instead — proven to
                    rank far better than the abbreviation.
  - "did_you_mean": not a known alias, but edit-distance 1 from one ("ubd" ->
                    "ibd"). We surface a suggestion; the caller returns NO
                    results (we never silently rewrite the query).
  - "raw":          no concept match; embed the query unchanged.
"""

from dataclasses import dataclass

from app.repositories import ConceptRepo


@dataclass(frozen=True)
class Resolution:
    """Outcome of resolving a raw query against the concept graph.

    Attributes:
        mode: One of "expanded", "did_you_mean", "raw".
        embed_query: The text the caller should embed.
        interpreted_as: Canonical concept name when expanded, else None.
        matched_alias: The alias the query matched (when expanded), else None.
        suggestion: The suggested canonical name (did_you_mean), else None.
    """

    mode: str
    embed_query: str
    interpreted_as: str | None = None
    matched_alias: str | None = None
    suggestion: str | None = None


def _edit_distance_le1(a: str, b: str) -> bool:
    """Returns whether two strings are within Levenshtein distance 1.

    Args:
        a: First string.
        b: Second string.

    Returns:
        True if at most one substitution, insertion or deletion separates them.
    """
    len_a, len_b = len(a), len(b)
    if abs(len_a - len_b) > 1:
        return False
    if len_a == len_b:
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    # Lengths differ by exactly 1: check for a single insertion/deletion.
    if len_a > len_b:
        a, b = b, a
        len_a, len_b = len_b, len_a
    i = j = 0
    skipped = False
    while i < len_a and j < len_b:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif skipped:
            return False
        else:
            skipped = True
            j += 1
    return True


class ConceptResolver:
    """In-memory alias index over the concept graph for query resolution."""

    def __init__(self) -> None:
        """Initializes empty indexes; data loads lazily on first resolve."""
        # Priority tiers for exact resolution: a concept's own abbreviation
        # and canonical name beat a loosely-expanded synonym alias. This keeps
        # "uc" -> Ulcerative Colitis (its own abbr) rather than IBD (which only
        # carries "uc" as a synonym-expanded alias).
        self._abbr_to_name: dict[str, str] = {}
        self._name_to_name: dict[str, str] = {}  # name_lower -> canonical name
        self._alias_to_name: dict[str, str] = {}
        self._popularity: dict[str, float] = {}
        self._abbr: dict[str, str | None] = {}
        self._by_len: dict[int, list[str]] = {}
        self._loaded = False

    def _load(self) -> None:
        """Loads aliases + metadata from the concepts collection once."""
        cursor = ConceptRepo().collection.find(
            {}, {"name": 1, "abbr": 1, "popularity": 1, "search_terms": 1}
        )
        for doc in cursor:
            name = doc.get("name")
            if not name:
                continue
            pop = float(doc.get("popularity", 0.0))
            self._popularity[name] = pop
            abbr = doc.get("abbr")
            self._abbr[name] = abbr
            self._name_to_name[name.lower()] = name
            if abbr:
                key = abbr.lower()
                if key not in self._abbr_to_name or pop > self._popularity.get(
                    self._abbr_to_name[key], 0.0
                ):
                    self._abbr_to_name[key] = name
            for alias in doc.get("search_terms", []):
                current = self._alias_to_name.get(alias)
                # Highest-popularity concept wins an alias collision.
                if current is None or pop > self._popularity.get(current, 0.0):
                    if current is None:
                        self._by_len.setdefault(len(alias), []).append(alias)
                    self._alias_to_name[alias] = name
        self._loaded = True

    def _resolve_exact(self, token: str) -> str | None:
        """Resolves a token to a canonical name by priority tier.

        Args:
            token: The lower-cased query token.

        Returns:
            The canonical concept name, or None if no exact match.
        """
        if token in self._abbr_to_name:
            return self._abbr_to_name[token]
        if token in self._name_to_name:
            return self._name_to_name[token]
        return self._alias_to_name.get(token)

    def _closest_within_edit1(self, token: str) -> str | None:
        """Finds the most popular alias within edit distance 1 of a token.

        Args:
            token: The lower-cased single-word query.

        Returns:
            The matching alias string, or None.
        """
        best_alias: str | None = None
        best_pop = -1.0
        for length in (len(token) - 1, len(token), len(token) + 1):
            for alias in self._by_len.get(length, ()):
                if alias == token or not _edit_distance_le1(token, alias):
                    continue
                pop = self._popularity.get(self._alias_to_name[alias], 0.0)
                if pop > best_pop:
                    best_pop = pop
                    best_alias = alias
        return best_alias

    def resolve(self, raw_query: str) -> Resolution:
        """Resolves a raw query into an expand / did-you-mean / raw outcome.

        Args:
            raw_query: The user's typed query.

        Returns:
            A Resolution describing how the caller should proceed.
        """
        if not self._loaded:
            self._load()
        token = (raw_query or "").strip().lower()
        if not token:
            return Resolution("raw", raw_query)

        # 1. Exact alias / abbreviation -> embed the canonical expansion.
        name = self._resolve_exact(token)
        if name:
            abbr = self._abbr.get(name)
            matched = token if abbr and token == abbr.lower() else None
            return Resolution(
                "expanded",
                embed_query=name,
                interpreted_as=name,
                matched_alias=matched,
            )

        # 2. Near-miss of a known alias (single word) -> did-you-mean.
        if " " not in token and len(token) >= 3:
            candidate = self._closest_within_edit1(token)
            if candidate is not None:
                return Resolution(
                    "did_you_mean",
                    embed_query=raw_query,
                    suggestion=self._resolve_exact(candidate) or self._alias_to_name[candidate],
                )

        # 3. Nothing matched -> embed as typed.
        return Resolution("raw", raw_query)


_resolver: ConceptResolver | None = None


def get_resolver() -> ConceptResolver:
    """Returns the process-wide ConceptResolver singleton.

    Returns:
        The lazily-initialized resolver.
    """
    global _resolver
    if _resolver is None:
        _resolver = ConceptResolver()
    return _resolver
