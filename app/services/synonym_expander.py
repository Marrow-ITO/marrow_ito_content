"""Medical synonym expander.

Loads `data/medical_synonyms.txt` (Solr/OpenSearch synonyms.txt format) and
exposes `expand(query)`: returns a space-joined expanded query string that
is safe to send to MongoDB `$text` search.

Expansion rules:
  - Phrase pass first: any multi-word phrase in the synonyms file that
    appears in the raw query expands to the full equivalence class.
  - Stop-word strip the remaining tokens (Lucene/Snowball English list).
  - Token pass: each remaining token is looked up; if it's in a class, the
    full class is added.
  - The final expanded set always includes the original token-stream.
"""

import re
from pathlib import Path


# Lucene/Snowball English stop-word list (subset that matters in medical
# queries). Lower-case, single tokens.
STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the",
        "is", "am", "are", "was", "were", "be", "been", "being",
        "of", "in", "on", "at", "to", "for", "with", "by", "from",
        "and", "or", "but", "if", "then", "else", "as", "than",
        "this", "that", "these", "those",
        "it", "its", "they", "them", "their",
        "i", "you", "we", "he", "she",
        "do", "does", "did", "doing", "done",
        "have", "has", "had", "having",
        "not", "no",
        "into", "about", "over", "under", "up", "down",
        "what", "which", "who", "whom",
        "so", "such", "very", "much",
    }
)


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-/]*")


class SynonymExpander:
    def __init__(self, synonyms_path: Path | str) -> None:
        self._classes: list[list[str]] = []
        self._term_to_class_indices: dict[str, set[int]] = {}
        self._multi_word_terms: list[tuple[str, int]] = []  # (term, class_idx)
        self._load(Path(synonyms_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            terms = [t.strip().lower() for t in line.split(",")]
            terms = [t for t in terms if t]
            if len(terms) < 2:
                continue
            class_idx = len(self._classes)
            self._classes.append(terms)
            for term in terms:
                self._term_to_class_indices.setdefault(term, set()).add(class_idx)
                if " " in term:
                    self._multi_word_terms.append((term, class_idx))
        # Sort multi-word terms longest first so longer phrases match before
        # shorter sub-phrases ("acute coronary syndrome" before "acute").
        self._multi_word_terms.sort(key=lambda pair: -len(pair[0]))

    def expand(self, query: str) -> str:
        """Expand the query and return a space-joined string of terms.

        Always includes the (normalised, non-stop-word) original tokens, plus
        any synonyms triggered by phrase or token matches.
        """
        if not query:
            return ""

        query_lower = query.lower()
        matched_class_indices: set[int] = set()
        consumed_spans: list[tuple[int, int]] = []

        # Phrase pass on the raw (lower-cased) string.
        for phrase, class_idx in self._multi_word_terms:
            start = query_lower.find(phrase)
            if start == -1:
                continue
            # Require the phrase to be word-bounded.
            end = start + len(phrase)
            before = query_lower[start - 1] if start > 0 else " "
            after = query_lower[end] if end < len(query_lower) else " "
            if not before.isalnum() and not after.isalnum():
                matched_class_indices.add(class_idx)
                consumed_spans.append((start, end))

        # Mask consumed spans so token pass doesn't double-trigger on words
        # that are already part of a matched phrase.
        masked = list(query_lower)
        for start, end in consumed_spans:
            for i in range(start, end):
                masked[i] = " "
        masked_str = "".join(masked)

        # Token pass on the masked string.
        tokens = [m.group(0) for m in _TOKEN_RE.finditer(masked_str)]
        kept_tokens: list[str] = []
        for token in tokens:
            if token in STOP_WORDS:
                continue
            kept_tokens.append(token)
            for class_idx in self._term_to_class_indices.get(token, ()):
                matched_class_indices.add(class_idx)

        expanded: list[str] = list(kept_tokens)
        for class_idx in matched_class_indices:
            expanded.extend(self._classes[class_idx])

        # De-dupe while preserving order.
        seen: set[str] = set()
        deduped: list[str] = []
        for term in expanded:
            if term not in seen:
                seen.add(term)
                deduped.append(term)

        # For Mongo $text, multi-word phrases stay quoted so they're treated
        # as a phrase. Single tokens go in unquoted.
        out_parts: list[str] = []
        for term in deduped:
            if " " in term:
                out_parts.append(f'"{term}"')
            else:
                out_parts.append(term)

        return " ".join(out_parts)

    def prefix_candidates(self, typed: str) -> list[str]:
        """Return prefix strings to query Mongo with for autocomplete.

        Branching logic:
          - If the typed text is an EXACT synonym (e.g. "MI"), use only its
            equivalence class. Skip the multi-word phrase pass so unrelated
            phrases that just share starting letters ("mitral stenosis",
            "mini mental state examination") don't leak in.
          - Otherwise, treat the typed text as a partial type-ahead and
            bring in any equivalence class whose multi-word phrase starts
            with what was typed ("ulcer" -> the IBD-family class).
        Short abbreviations (<=4 chars) are then filtered out of the final
        candidate set because `^uc` / `^cd` style prefixes match noisy
        things on their own; we want the expanded forms doing the work.
        """
        typed_lower = (typed or "").strip().lower()
        if not typed_lower:
            return []

        candidates: set[str] = set()
        is_known_synonym = typed_lower in self._term_to_class_indices

        if is_known_synonym:
            for class_idx in self._term_to_class_indices[typed_lower]:
                candidates.update(self._classes[class_idx])
        else:
            for phrase, class_idx in self._multi_word_terms:
                if phrase.startswith(typed_lower):
                    candidates.update(self._classes[class_idx])

        # Drop short single-word abbreviations — keep multi-word phrases
        # and longer single words.
        candidates = {c for c in candidates if " " in c or len(c) > 4}

        if not is_known_synonym:
            candidates.add(typed_lower)

        return sorted(candidates, key=lambda s: (len(s), s))

    def stats(self) -> dict:
        return {
            "classes": len(self._classes),
            "unique_terms": len(self._term_to_class_indices),
            "multi_word_terms": len(self._multi_word_terms),
        }


_expander: SynonymExpander | None = None


def get_expander() -> SynonymExpander:
    """Lazy singleton — load synonyms once per process."""
    global _expander
    if _expander is None:
        from app.config import settings  # noqa: PLC0415
        path = (
            Path(__file__).resolve().parent.parent.parent
            / "data"
            / "medical_synonyms.txt"
        )
        # Use settings if you want to make this configurable later
        _ = settings  # silence unused-import linter
        _expander = SynonymExpander(path)
    return _expander
