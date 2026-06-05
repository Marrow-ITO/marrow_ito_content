"""Build the transcript search FAISS index from videos' video_transcript_raw.

Reads all videos that have `video_transcript_raw`, parses each into
segments, chunks adjacent segments into ~30s / ~120-word groups, embeds
each chunk with the configured sentence-transformer, and writes:

  data/transcript_faiss.index
  data/transcript_meta.json

This is a SEPARATE index from the MCQ search FAISS — different content
type, different result shape.

Each row in the meta JSON corresponds to one row in the FAISS index and
contains everything the search service needs at query time so it can
hydrate results with NO further DB lookups:

  { video_id, video_title, lesson_id, lesson_name, topic_name,
    subject_name, start_time, end_time, text }

Usage:
    uv run --group ingest python scripts/build_transcript_index.py
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
from app.services.transcript_parser import chunk_segments, parse_segments  # noqa: E402

DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
# DEFAULT_MODEL = "intfloat/e5-base-v2"


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAISS_PATH = DATA_DIR / "transcript_faiss.index"
META_PATH = DATA_DIR / "transcript_meta.json"


def collect_chunks() -> list[dict]:
    """Walk videos w/ transcripts, return [{...chunk + denorm context...}]."""
    db = get_db()
    subjects = {s["_id"]: s for s in db[Collections.subjects].find()}
    topics = {t["_id"]: t for t in db[Collections.topics].find()}
    lessons = {l["_id"]: l for l in db[Collections.lessons].find()}

    rows: list[dict] = []
    for v in db[Collections.videos].find(
        {"video_transcript_raw": {"$exists": True, "$ne": None}},
        {
            "title": 1,
            "lesson_id": 1,
            "file_name": 1,
            "video_transcript_raw": 1,
        },
    ):
        lesson = lessons.get(v.get("lesson_id"))
        if not lesson:
            continue
        topic = topics.get(lesson.get("topic_id"))
        subject = subjects.get(topic["subject_id"]) if topic else None

        segments = parse_segments(v.get("video_transcript_raw") or "")
        chunks = chunk_segments(segments)
        for c in chunks:
            rows.append({
                "video_id": str(v["_id"]),
                "video_title": v.get("title", ""),
                "lesson_id": str(lesson["_id"]),
                "lesson_name": lesson.get("name", ""),
                "topic_name": topic.get("name", "") if topic else "",
                "subject_name": subject.get("name", "") if subject else "",
                "start_time": c["start_time"],
                "end_time": c["end_time"],
                "text": c["text"],
                # Per-segment data lets the search service pinpoint the
                # exact in-chunk timestamp where a query term first appears.
                "segments": c.get("segments", []),
            })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the transcript FAISS index"
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"sentence-transformers model id (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    print("Collecting transcript chunks from DB...")
    rows = collect_chunks()
    if not rows:
        print(
            "error: no transcript chunks found. "
            "Ingest transcripts first (scripts/import_transcripts.py).",
            file=sys.stderr,
        )
        sys.exit(1)

    n_videos = len(set(r["video_id"] for r in rows))
    print(f"  {len(rows)} chunks from {n_videos} videos")

    print(f"\nLoading embedding model: {args.model}")
    model = SentenceTransformer(args.model)

    # Embed the chunk text together with hierarchical context so a query
    # like "ulcerative colitis management" lands on a transcript chunk
    # that may not name UC explicitly but lives under the UC lesson.
    print(f"Embedding {len(rows)} chunks...")
    texts = [
        f"{r['subject_name']} > {r['topic_name']} > {r['lesson_name']}: {r['text']}"
        for r in rows
    ]
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
    META_PATH.write_text(
        json.dumps({"dim": int(embeddings.shape[1]), "chunks": rows}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nFAISS index: {FAISS_PATH}")
    print(f"Meta:        {META_PATH}")
    print(f"Vectors:     {index.ntotal} (dim {embeddings.shape[1]})")


if __name__ == "__main__":
    main()
