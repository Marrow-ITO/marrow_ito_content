"""Import videos from a TSV file into the seeded taxonomy.

TSV columns (no quoting, tab-separated):
    file_name<TAB>Subject<TAB>Topic<TAB>Lesson

Behaviour (per user direction):
  - Rows where Topic or Lesson is "-" are SKIPPED and reported.
  - Subject names go through a small spelling map (Anaesthesia ->
    Anesthesia, Orthopaedics -> Orthopedics, Paediatrics -> Pediatrics,
    Skin -> Dermatology, Social & Preventive Medicine ->
    Community Medicine, Gynaecology & Obstetrics ->
    Obstetrics & Gynecology).
  - Topic and Lesson are matched EXACTLY (case-insensitive) against
    seeded docs under the resolved subject / topic. Mismatches are
    SKIPPED and reported so you can fix the TSV and re-run.
  - For successful matches, a Video is inserted with:
        title = file_name without extension
        file_name = raw filename from TSV
        lesson_id = matched lesson

Usage:
    uv run python scripts/import_videos.py /path/to/video_table.tsv
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Collections, get_db  # noqa: E402
from app.models import Video  # noqa: E402
from app.repositories import (  # noqa: E402
    LessonRepo,
    SubjectRepo,
    TopicRepo,
    VideoRepo,
)


SUBJECT_MAP: dict[str, str] = {
    "Anaesthesia": "Anesthesia",
    "Orthopaedics": "Orthopedics",
    "Paediatrics": "Pediatrics",
    "Skin": "Dermatology",
    "Social & Preventive Medicine": "Community Medicine",
    "Gynaecology & Obstetrics": "Obstetrics & Gynecology",
}


def canonicalize_subject(raw: str) -> str:
    raw = raw.strip()
    return SUBJECT_MAP.get(raw, raw)


def title_from_filename(filename: str) -> str:
    """'Foo - Subject.mp3' -> 'Foo - Subject'."""
    stem = Path(filename).stem
    return stem.strip()


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for line_no, raw_row in enumerate(reader, start=1):
            # Skip header (first row has empty file_name).
            if line_no == 1 and (not raw_row or not raw_row[0].strip()):
                continue
            # Pad to 4 columns
            row = (raw_row + [""] * 4)[:4]
            rows.append(
                {
                    "line_no": line_no,
                    "file_name": row[0].strip(),
                    "subject": row[1].strip(),
                    "topic": row[2].strip(),
                    "lesson": row[3].strip(),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import videos from a tab-separated taxonomy file"
    )
    parser.add_argument("tsv_path", type=Path, help="Path to video_table.tsv")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse + match but don't insert. Useful for previewing mismatches.",
    )
    args = parser.parse_args()

    if not args.tsv_path.exists():
        print(f"error: file not found: {args.tsv_path}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(args.tsv_path)
    if not rows:
        print("error: no data rows in TSV", file=sys.stderr)
        sys.exit(1)

    # Build name -> object lookups for fast case-insensitive matching.
    subjects = {s.name.lower(): s for s in SubjectRepo().list_all()}
    topics_by_subject: dict[str, dict[str, object]] = defaultdict(dict)
    for topic in get_db()[Collections.topics].find({}, {"name": 1, "subject_id": 1}):
        topics_by_subject[str(topic["subject_id"])][topic["name"].strip().lower()] = topic
    lessons_by_topic: dict[str, dict[str, object]] = defaultdict(dict)
    for lesson in get_db()[Collections.lessons].find({}, {"name": 1, "topic_id": 1}):
        lessons_by_topic[str(lesson["topic_id"])][lesson["name"].strip().lower()] = lesson

    video_repo = VideoRepo()

    stats = {
        "total": len(rows),
        "imported": 0,
        "skipped_no_taxonomy": 0,
        "skipped_subject": 0,
        "skipped_topic": 0,
        "skipped_lesson": 0,
    }
    skips: list[tuple[str, str]] = []  # (reason, line description)

    for row in rows:
        line = (
            f"L{row['line_no']:>2}: "
            f"{row['file_name']!r} -> "
            f"{row['subject']} / {row['topic']} / {row['lesson']}"
        )

        if row["topic"] == "-" or row["lesson"] == "-":
            stats["skipped_no_taxonomy"] += 1
            skips.append(("no taxonomy", line))
            continue

        canonical_subject = canonicalize_subject(row["subject"])
        subject = subjects.get(canonical_subject.lower())
        if subject is None:
            stats["skipped_subject"] += 1
            skips.append((f"subject not found ({canonical_subject!r})", line))
            continue

        topic = topics_by_subject.get(str(subject.id), {}).get(
            row["topic"].lower()
        )
        if topic is None:
            stats["skipped_topic"] += 1
            skips.append((f"topic {row['topic']!r} not under {canonical_subject!r}", line))
            continue

        lesson = lessons_by_topic.get(str(topic["_id"]), {}).get(
            row["lesson"].lower()
        )
        if lesson is None:
            stats["skipped_lesson"] += 1
            skips.append((
                f"lesson {row['lesson']!r} not under topic {row['topic']!r}",
                line,
            ))
            continue

        if not args.dry_run:
            video_repo.insert(
                Video(
                    title=title_from_filename(row["file_name"]),
                    file_name=row["file_name"],
                    lesson_id=lesson["_id"],
                )
            )
        stats["imported"] += 1

    print(("DRY RUN — " if args.dry_run else "") + "Import summary:")
    for key, value in stats.items():
        print(f"  {key:<24} {value:>4}")

    if skips:
        print("\nSkipped rows:")
        for reason, line in skips:
            print(f"  [{reason}] {line}")


if __name__ == "__main__":
    main()
