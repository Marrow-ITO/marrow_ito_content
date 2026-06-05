"""Seed Subject -> Topic -> Lesson -> QBank hierarchy into MongoDB from JSON.

Reads `data/subjects_with_syllabus.json` (output of enrich_syllabus.py) and
creates documents in the subjects, topics, lessons, and qbanks collections
with proper ObjectId references.

For each lesson, ONE QBank is auto-created (title = lesson name,
lesson_id links to the lesson). MCQs, Videos, and Tests collections are
NOT touched -- those are populated by separate scripts later.

For empty subjects (no topics in the input JSON), only the Subject document
is created. Topics and lessons for those subjects can be added later by
re-running this script after editing the JSON.

By default, the four owned collections (subjects, topics, lessons, qbanks)
are dropped before re-seeding so the DB reflects the input JSON exactly.
Use --no-drop to append instead.

Usage:
    uv run python scripts/seed_taxonomy.py
    uv run python scripts/seed_taxonomy.py -i path/to/input.json --no-drop
"""

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Collections, get_db  # noqa: E402
from app.models import Lesson, QBank, Subject, Topic  # noqa: E402
from app.repositories import (  # noqa: E402
    LessonRepo,
    QBankRepo,
    SubjectRepo,
    TopicRepo,
)


OWNED_COLLECTIONS = [
    Collections.subjects,
    Collections.topics,
    Collections.lessons,
    Collections.qbanks,
]


def drop_owned_collections() -> None:
    db = get_db()
    for name in OWNED_COLLECTIONS:
        db[name].drop()


def seed(data: dict) -> dict:
    """Insert hierarchy from the JSON payload. Returns counts per collection."""
    subject_repo = SubjectRepo()
    topic_repo = TopicRepo()
    lesson_repo = LessonRepo()
    qbank_repo = QBankRepo()

    stats = {
        "subjects": 0,
        "topics": 0,
        "lessons": 0,
        "qbanks": 0,
        "empty_subjects": 0,
    }

    for subject_data in data.get("subjects", []):
        subject_name = subject_data.get("name")
        if not subject_name:
            continue

        subject_id = subject_repo.insert(
            Subject(name=subject_name, name_lower=subject_name.lower())
        )
        stats["subjects"] += 1

        topics = subject_data.get("topics", [])
        if not topics:
            stats["empty_subjects"] += 1
            continue

        for topic_data in topics:
            topic_name = topic_data.get("name")
            if not topic_name:
                continue

            topic_id = topic_repo.insert(
                Topic(
                    name=topic_name,
                    name_lower=topic_name.lower(),
                    subject_id=subject_id,
                )
            )
            stats["topics"] += 1

            for lesson_data in topic_data.get("lessons", []):
                lesson_name = lesson_data.get("name")
                if not lesson_name:
                    continue

                lesson_id = lesson_repo.insert(
                    Lesson(
                        name=lesson_name,
                        name_lower=lesson_name.lower(),
                        topic_id=topic_id,
                    )
                )
                stats["lessons"] += 1

                qbank_repo.insert(
                    QBank(
                        title=lesson_name,
                        title_lower=lesson_name.lower(),
                        lesson_id=lesson_id,
                    )
                )
                stats["qbanks"] += 1

    return stats


def print_sample() -> None:
    """Quick read-back to confirm the hierarchy is queryable end-to-end."""
    subject_repo = SubjectRepo()
    topic_repo = TopicRepo()
    lesson_repo = LessonRepo()
    qbank_repo = QBankRepo()

    subjects = subject_repo.list_all()
    print(f"\nRead-back: {len(subjects)} subjects in DB.")
    if not subjects:
        return

    sample = subjects[0]
    topics = topic_repo.list_by_subject(sample.id)
    print(f"  Sample subject: {sample.name} -> {len(topics)} topics")
    if not topics:
        return
    sample_topic = topics[0]
    lessons = lesson_repo.list_by_topic(sample_topic.id)
    print(f"    Sample topic: {sample_topic.name} -> {len(lessons)} lessons")
    if not lessons:
        return
    sample_lesson = lessons[0]
    qbanks = qbank_repo.list_by_lesson(sample_lesson.id)
    print(
        f"      Sample lesson: {sample_lesson.name} -> {len(qbanks)} qbank(s)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed Subject/Topic/Lesson/QBank hierarchy into MongoDB"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("data/subjects_with_syllabus.json"),
        help="Input JSON (default: data/subjects_with_syllabus.json)",
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Append to existing collections instead of dropping first",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(args.input.read_text(encoding="utf-8"))

    if not args.no_drop:
        print(
            f"Dropping collections: {', '.join(OWNED_COLLECTIONS)}\n"
            "(MCQs, Videos, Tests collections are NOT touched.)"
        )
        drop_owned_collections()

    stats = seed(data)

    print("\nSeed complete:")
    for key, value in stats.items():
        print(f"  {key:<16} {value:>6}")

    print_sample()


if __name__ == "__main__":
    main()
