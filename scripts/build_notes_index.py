"""Build the video-notes search FAISS index from the page images.

video_notes stores one base64 PNG per page (`image_data`, `order`). This
script:

  1. EXTRACT: OCR each page image with Tesseract and cache the text back onto
     the note document (`extracted_text`), so re-runs are free / resumable.
  2. BUILD:   embed each page's text (with subject>topic>lesson context) using
     the same sentence-transformer as the other indexes and write:
         data/notes_faiss.index
         data/notes_meta.json

Each meta row carries everything search needs with no further DB lookup,
including the two fields the feature requires:
    video_content_id (= the note's video_id) and page_no (= the note's order).

This is a SEPARATE index from transcripts / MCQ — surfaced as its own
"Notes" group in /api/search.

Requires the Tesseract binary (`brew install tesseract`).

Usage:
    uv run python scripts/build_notes_index.py
    uv run python scripts/build_notes_index.py --force        # re-OCR all pages
    uv run python scripts/build_notes_index.py --skip-extract # embed cached text
"""

import argparse
import base64
import io
import sys
import tempfile
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# macOS restricts the Homebrew tesseract binary's access to /tmp and
# /var/folders, so pytesseract's default temp files are unreadable by the
# child process. Point temp files at a project-local dir tesseract can read.
_OCR_TMP = Path(__file__).resolve().parent.parent / ".ocr_tmp"
_OCR_TMP.mkdir(exist_ok=True)
tempfile.tempdir = str(_OCR_TMP)

import numpy as np  # noqa: E402
import faiss  # noqa: E402
import pytesseract  # noqa: E402
from PIL import Image  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.db import Collections, get_db  # noqa: E402

DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAISS_PATH = DATA_DIR / "notes_faiss.index"
META_PATH = DATA_DIR / "notes_meta.json"

# Pages whose OCR yields fewer than this many characters are treated as empty
# (blank/diagram-only slides) and excluded from the index.
MIN_TEXT_CHARS = 15


def _ocr_image(image_data: str) -> str:
    """Runs Tesseract OCR on a base64-encoded image.

    Args:
        image_data: Base64 body of the image (no data-URI prefix).

    Returns:
        The extracted text, whitespace-collapsed.
    """
    raw = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(raw))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return " ".join(text.split())


def extract(force: bool) -> dict:
    """OCRs note pages and caches the text on each note document.

    Args:
        force: When True, re-OCR pages that already have extracted_text.

    Returns:
        Counts of pages processed / skipped / failed.
    """
    db = get_db()
    query = {} if force else {"extracted_text": {"$exists": False}}
    notes = list(db[Collections.video_notes].find(query, {"image_data": 1}))
    stats = {"ocr": 0, "failed": 0, "total": db[Collections.video_notes].estimated_document_count()}
    for note in notes:
        try:
            text = _ocr_image(note["image_data"])
        except Exception as exc:  # noqa: BLE001 — keep going on a bad page.
            print(f"  OCR failed for {note['_id']}: {type(exc).__name__}: {str(exc)[:80]}")
            stats["failed"] += 1
            continue
        db[Collections.video_notes].update_one(
            {"_id": note["_id"]}, {"$set": {"extracted_text": text}}
        )
        stats["ocr"] += 1
    return stats


def collect_pages() -> list[dict]:
    """Collects OCR'd note pages joined with their hierarchy context.

    Returns:
        One row per page with denormalized subject/topic/lesson context.
    """
    db = get_db()
    subjects = {s["_id"]: s for s in db[Collections.subjects].find()}
    topics = {t["_id"]: t for t in db[Collections.topics].find()}
    lessons = {le["_id"]: le for le in db[Collections.lessons].find()}
    videos = {v["_id"]: v for v in db[Collections.videos].find()}

    rows: list[dict] = []
    cursor = db[Collections.video_notes].find(
        {"extracted_text": {"$exists": True}}
    ).sort([("video_id", 1), ("order", 1)])
    for note in cursor:
        text = (note.get("extracted_text") or "").strip()
        if len(text) < MIN_TEXT_CHARS:
            continue
        video = videos.get(note.get("video_id"))
        lesson = lessons.get(video.get("lesson_id")) if video else None
        topic = topics.get(lesson.get("topic_id")) if lesson else None
        subject = subjects.get(topic["subject_id"]) if topic else None
        rows.append({
            "video_content_id": str(note["video_id"]),
            "page_no": int(note.get("order", 1)),
            "video_title": video.get("title", "") if video else "",
            "lesson_id": str(lesson["_id"]) if lesson else None,
            "lesson_name": lesson.get("name", "") if lesson else "",
            "topic_name": topic.get("name", "") if topic else "",
            "subject_name": subject.get("name", "") if subject else "",
            "text": text,
        })
    return rows


def build(model_name: str) -> int:
    """Embeds OCR'd pages and writes the notes FAISS index + meta.

    Args:
        model_name: sentence-transformers model id.

    Returns:
        The number of vectors written.
    """
    rows = collect_pages()
    if not rows:
        print("error: no OCR'd note pages found. Run extraction first.", file=sys.stderr)
        sys.exit(1)

    n_videos = len(set(r["video_content_id"] for r in rows))
    print(f"  {len(rows)} pages from {n_videos} videos")

    print(f"\nLoading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    # Embed with hierarchy context so a page lands under its lesson even when
    # the page text doesn't name the concept explicitly.
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
        __import__("json").dumps(
            {"dim": int(embeddings.shape[1]), "pages": rows}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(f"\nFAISS index: {FAISS_PATH}")
    print(f"Meta:        {META_PATH}")
    print(f"Vectors:     {index.ntotal} (dim {embeddings.shape[1]})")
    return index.ntotal


def main() -> None:
    """Parses CLI arguments and runs the extract + build phases.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Build the video-notes FAISS index.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--force", action="store_true", help="Re-OCR all pages.")
    parser.add_argument("--skip-extract", action="store_true", help="Embed cached text only.")
    args = parser.parse_args()

    if not args.skip_extract:
        print("OCR extraction...")
        stats = extract(force=args.force)
        print(
            f"  OCR'd {stats['ocr']} pages "
            f"({stats['failed']} failed, {stats['total']} total notes)"
        )

    print("\nBuilding index...")
    build(args.model)


if __name__ == "__main__":
    main()
