"""Lazy singletons for the embedding model + FAISS index.

Loaded on first use so app boot stays fast. Subsequent calls reuse the same
in-memory instances.
"""

import json
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
# DEFAULT_MODEL = "intfloat/e5-large-v2"

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_FAISS_PATH = _DATA_DIR / "search_faiss.index"
_ID_MAP_PATH = _DATA_DIR / "search_faiss_ids.json"
_TRANSCRIPT_FAISS_PATH = _DATA_DIR / "transcript_faiss.index"
_TRANSCRIPT_META_PATH = _DATA_DIR / "transcript_meta.json"
_NOTES_FAISS_PATH = _DATA_DIR / "notes_faiss.index"
_NOTES_META_PATH = _DATA_DIR / "notes_meta.json"
_UPDATES_FAISS_PATH = _DATA_DIR / "recent_updates_faiss.index"
_UPDATES_META_PATH = _DATA_DIR / "recent_updates_meta.json"


_model: Any = None
_index: Any = None
_ids: list[str] | None = None
_transcript_index: Any = None
_transcript_meta: list[dict] | None = None
_notes_index: Any = None
_notes_meta: list[dict] | None = None
_updates_index: Any = None
_updates_meta: list[dict] | None = None


def get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        _model = SentenceTransformer(DEFAULT_MODEL)
    return _model


def get_faiss_index() -> tuple[Any, list[str]]:
    """Return (faiss_index, ids_in_position_order). Empty list if not built."""
    global _index, _ids
    if _index is None or _ids is None:
        if not _FAISS_PATH.exists() or not _ID_MAP_PATH.exists():
            return None, []
        import faiss  # noqa: PLC0415
        _index = faiss.read_index(str(_FAISS_PATH))
        _ids = json.loads(_ID_MAP_PATH.read_text(encoding="utf-8"))["ids"]
    return _index, _ids


def get_transcript_index() -> tuple[Any, list[dict]]:
    """Return (faiss_index, chunks_meta_in_position_order). Empty if not built."""
    global _transcript_index, _transcript_meta
    if _transcript_index is None or _transcript_meta is None:
        if not _TRANSCRIPT_FAISS_PATH.exists() or not _TRANSCRIPT_META_PATH.exists():
            return None, []
        import faiss  # noqa: PLC0415
        _transcript_index = faiss.read_index(str(_TRANSCRIPT_FAISS_PATH))
        _transcript_meta = json.loads(
            _TRANSCRIPT_META_PATH.read_text(encoding="utf-8")
        )["chunks"]
    return _transcript_index, _transcript_meta


def get_notes_index() -> tuple[Any, list[dict]]:
    """Return (faiss_index, pages_meta_in_position_order). Empty if not built."""
    global _notes_index, _notes_meta
    if _notes_index is None or _notes_meta is None:
        if not _NOTES_FAISS_PATH.exists() or not _NOTES_META_PATH.exists():
            return None, []
        import faiss  # noqa: PLC0415
        _notes_index = faiss.read_index(str(_NOTES_FAISS_PATH))
        _notes_meta = json.loads(
            _NOTES_META_PATH.read_text(encoding="utf-8")
        )["pages"]
    return _notes_index, _notes_meta


def get_recent_updates_index() -> tuple[Any, list[dict]]:
    """Return (faiss_index, updates_meta_in_position_order). Empty if not built."""
    global _updates_index, _updates_meta
    if _updates_index is None or _updates_meta is None:
        if not _UPDATES_FAISS_PATH.exists() or not _UPDATES_META_PATH.exists():
            return None, []
        import faiss  # noqa: PLC0415
        _updates_index = faiss.read_index(str(_UPDATES_FAISS_PATH))
        _updates_meta = json.loads(
            _UPDATES_META_PATH.read_text(encoding="utf-8")
        )["updates"]
    return _updates_index, _updates_meta


def is_ready() -> bool:
    return _FAISS_PATH.exists() and _ID_MAP_PATH.exists()


def is_transcript_ready() -> bool:
    return _TRANSCRIPT_FAISS_PATH.exists() and _TRANSCRIPT_META_PATH.exists()


def is_notes_ready() -> bool:
    return _NOTES_FAISS_PATH.exists() and _NOTES_META_PATH.exists()


# Raw cosine from this bi-encoder lives in a narrow cone: even gibberish
# scores ~0.80 and unrelated medical text ~0.85, while a strong match is
# ~0.95+. We linearly rescale the meaningful band [FLOOR, CEIL] -> [0, 1] for
# display and confidence gating. These are model-level properties — re-tune if
# DEFAULT_MODEL changes.
SIM_FLOOR = 0.84
SIM_CEIL = 0.96


def calibrate_relevance(score: float) -> float:
    """Rescales a raw cosine score to a 0..1 relevance.

    Args:
        score: Raw cosine similarity (inner product of unit vectors).

    Returns:
        Clamped relevance in [0, 1]: FLOOR maps to 0, CEIL maps to 1.
    """
    relevance = (score - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)
    return max(0.0, min(1.0, relevance))
