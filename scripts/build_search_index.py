"""Build the search infrastructure for the Flask app.

What this script does (idempotent — safe to re-run):

  1. Backfill `name_lower` (or `title_lower`) on subjects, topics, lessons,
     qbanks so prefix-regex autocomplete uses an index.
  2. Create B-tree indexes on those lower-cased fields.
  3. Drop and rebuild the `search_documents` collection — one doc per
     lesson, denormalised with subject/topic/lesson names ONLY. MCQ
     content is intentionally NOT included; the qbank-arm of search ranks
     on lesson taxonomy alone so that queries like "ulcerative colitis"
     surface the lesson rather than a random MCQ that happens to mention
     UC in passing.
  4. Create the `$text` index on `search_documents` with field weights
     (title=10, topic_name=4, subject_name=2).
  5. Embed every search document with the configured sentence-transformer
     model and persist a FAISS index + an id-mapping JSON to `data/`.

Run after seed_taxonomy.py. Re-run whenever the embedding model in
app/services/embedder.py changes — otherwise the FAISS vectors will be in
a different space from runtime query embeddings and MCQ hits will score
near zero.

Usage:
    uv run --group ingest python scripts/build_search_index.py
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

from app.db import Collections, get_collection, get_db  # noqa: E402


DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
# DEFAULT_MODEL = "intfloat/e5-base-v2"

SEARCH_DOCS = "search_documents"

TEXT_WEIGHTS = {
    "title": 10,
    "topic_name": 4,
    "subject_name": 2,
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAISS_PATH = DATA_DIR / "search_faiss.index"
ID_MAP_PATH = DATA_DIR / "search_faiss_ids.json"


# ---------- Step 1 + 2: backfill name_lower and create B-tree indexes ----------

def backfill_lowercase_fields() -> dict:
    db = get_db()
    stats = {}

    for coll_name, src, dst in [
        (Collections.subjects, "name", "name_lower"),
        (Collections.topics, "name", "name_lower"),
        (Collections.lessons, "name", "name_lower"),
        (Collections.qbanks, "title", "title_lower"),
    ]:
        coll = db[coll_name]
        updated = 0
        for doc in coll.find({dst: {"$exists": False}}, {src: 1}):
            value = doc.get(src) or ""
            coll.update_one(
                {"_id": doc["_id"]}, {"$set": {dst: value.lower()}}
            )
            updated += 1
        coll.create_index(dst)
        stats[coll_name] = updated

    return stats


# ---------- Step 3: build search_documents ----------

def build_search_documents() -> int:
    """One doc per lesson, denormalised with subject/topic/lesson names only.

    Intentionally no MCQ content — the qbank arm ranks on lesson taxonomy
    alone. If a lesson needs to be findable by a term that doesn't appear
    in its name, add the term to the synonym map or concept graph.
    """
    db = get_db()
    subjects = {s["_id"]: s for s in db[Collections.subjects].find()}
    topics = {t["_id"]: t for t in db[Collections.topics].find()}
    lessons = list(db[Collections.lessons].find())
    target = db[SEARCH_DOCS]

    target.drop()

    docs: list[dict] = []
    for lesson in lessons:
        topic = topics.get(lesson.get("topic_id"))
        subject = subjects.get(topic["subject_id"]) if topic else None
        if not topic or not subject:
            continue

        docs.append(
            {
                "_id": lesson["_id"],            # same id as the lesson
                "lesson_id": lesson["_id"],
                "topic_id": topic["_id"],
                "subject_id": subject["_id"],
                "title": lesson.get("name") or "",
                "topic_name": topic.get("name") or "",
                "subject_name": subject.get("name") or "",
            }
        )

    if docs:
        target.insert_many(docs)

    # Drop any pre-existing text index then recreate with our weights.
    for name in [
        idx["name"] for idx in target.list_indexes() if idx.get("textIndexVersion")
    ]:
        target.drop_index(name)

    target.create_index(
        [
            ("title", "text"),
            ("topic_name", "text"),
            ("subject_name", "text"),
        ],
        weights=TEXT_WEIGHTS,
        default_language="english",
        name="search_text_index",
    )

    # Filter indexes for facet queries.
    target.create_index("subject_id")
    target.create_index("topic_id")

    return len(docs)


# ---------- Step 5: embed and save FAISS ----------

def build_faiss_index(model_name: str) -> int:
    coll = get_collection(SEARCH_DOCS)
    docs = list(coll.find({}, {"title": 1, "topic_name": 1, "subject_name": 1}))
    if not docs:
        return 0

    texts: list[str] = []
    ids: list[str] = []
    for d in docs:
        # Title-led semantic input + hierarchical context. No MCQ content.
        text = (
            f"{d['title']}. "
            f"Topic: {d['topic_name']}. "
            f"Subject: {d['subject_name']}."
        ).strip()
        texts.append(text)
        ids.append(str(d["_id"]))

    print(f"  Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"  Embedding {len(texts)} search documents...")
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_PATH))
    ID_MAP_PATH.write_text(
        json.dumps({"ids": ids, "dim": int(embeddings.shape[1])}),
        encoding="utf-8",
    )

    return len(texts)


# ---------- Main ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build keyword + semantic search infra for the app"
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"sentence-transformers model id (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--skip-faiss", action="store_true",
        help="Skip the FAISS embedding step (keyword-only build)",
    )
    args = parser.parse_args()

    print("Step 1+2: backfilling name_lower + creating B-tree indexes")
    backfill = backfill_lowercase_fields()
    for coll, n in backfill.items():
        print(f"  {coll}: backfilled {n} docs, index created")

    print("\nStep 3+4: building search_documents + $text index")
    n = build_search_documents()
    print(f"  Wrote {n} search documents with field-weighted text index.")

    if args.skip_faiss:
        print("\nSkipping FAISS (--skip-faiss).")
        return

    print("\nStep 5: building FAISS index")
    n_embedded = build_faiss_index(args.model)
    print(f"  Embedded {n_embedded} docs.")
    print(f"  FAISS index:  {FAISS_PATH}")
    print(f"  ID mapping:   {ID_MAP_PATH}")


if __name__ == "__main__":
    main()
