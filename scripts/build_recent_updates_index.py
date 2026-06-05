"""Build the recent-updates search FAISS index.

Each update is embedded as a TOPIC-boosted vector: the update_topic and the
content are embedded separately and combined as a weighted sum
(TOPIC_WEIGHT on the topic), then re-normalized. This makes a query match
primarily on what the update is *about* (its headline) while still drawing
on the body. Writes:

    data/recent_updates_faiss.index
    data/recent_updates_meta.json

Each meta row carries the fields search needs with no DB lookup, including
recent_update_id (our Mongo _id, for the detail API) and source attribution.

Run AFTER import_recent_updates.py.

Usage:
    uv run python scripts/build_recent_updates_index.py
    uv run python scripts/build_recent_updates_index.py --topic-weight 0.6
"""

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import faiss  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.db import Collections, get_db  # noqa: E402

DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
DEFAULT_TOPIC_WEIGHT = 0.6

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAISS_PATH = DATA_DIR / "recent_updates_faiss.index"
META_PATH = DATA_DIR / "recent_updates_meta.json"


def collect_updates() -> list[dict]:
    """Collects recent updates from Mongo into meta rows.

    Returns:
        One row per update with the fields search + detail need.
    """
    db = get_db()
    rows: list[dict] = []
    for u in db[Collections.recent_updates].find().sort("source_id", 1):
        ref = u.get("reference") or {}
        rows.append({
            "recent_update_id": str(u["_id"]),
            "source_id": u.get("source_id"),
            "update_topic": u.get("update_topic", ""),
            "content": u.get("content", ""),
            "subject": u.get("subject"),
            "subject_name": u.get("subject_name"),
            "subject_id": str(u["subject_id"]) if u.get("subject_id") else None,
            "date_of_update": u.get("date_of_update"),
            "source_name": ref.get("source_name"),
            "reference_link": ref.get("reference_link"),
        })
    return rows


def build(model_name: str, topic_weight: float) -> int:
    """Embeds updates (topic-boosted) and writes the FAISS index + meta.

    Args:
        model_name: sentence-transformers model id.
        topic_weight: Weight on the topic vector (content gets 1 - this).

    Returns:
        The number of vectors written.
    """
    rows = collect_updates()
    if not rows:
        print(
            "error: no recent updates found. Run import_recent_updates.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"  {len(rows)} updates")

    print(f"\nLoading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    # Topic carries the subject as context so it sits near the right area.
    topic_texts = [
        f"{r['subject_name'] or r['subject'] or ''}: {r['update_topic']}".strip(": ")
        for r in rows
    ]
    content_texts = [r["content"] for r in rows]

    topic_emb = model.encode(
        topic_texts, normalize_embeddings=True, batch_size=32,
        show_progress_bar=True, convert_to_numpy=True,
    ).astype(np.float32)
    content_emb = model.encode(
        content_texts, normalize_embeddings=True, batch_size=32,
        show_progress_bar=True, convert_to_numpy=True,
    ).astype(np.float32)

    # Topic-boosted combination, then re-normalize so cosine stays comparable.
    combined = topic_weight * topic_emb + (1.0 - topic_weight) * content_emb
    norms = np.linalg.norm(combined, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    combined = (combined / norms).astype(np.float32)

    index = faiss.IndexFlatIP(combined.shape[1])
    index.add(combined)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_PATH))
    META_PATH.write_text(
        json.dumps({"dim": int(combined.shape[1]), "updates": rows}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nFAISS index: {FAISS_PATH}")
    print(f"Meta:        {META_PATH}")
    print(f"Vectors:     {index.ntotal} (dim {combined.shape[1]}, topic_weight={topic_weight})")
    return index.ntotal


def main() -> None:
    """Parses CLI arguments and builds the recent-updates index.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Build the recent-updates FAISS index.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--topic-weight", type=float, default=DEFAULT_TOPIC_WEIGHT)
    args = parser.parse_args()
    build(args.model, args.topic_weight)


if __name__ == "__main__":
    main()
