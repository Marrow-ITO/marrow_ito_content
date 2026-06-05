"""Ingest recent_update_ito.json into the recent_updates collection.

Each source record { id, date_of_update, subject, update_topic, content,
reference } becomes a RecentUpdate document. The source `subject` string is
mapped onto our own subjects taxonomy (subject_id / subject_name) by name,
with a small alias map for naming differences.

Idempotent: upserts by source_id, so re-running refreshes in place.

Usage:
    uv run python scripts/import_recent_updates.py
    uv run python scripts/import_recent_updates.py -i /path/to/recent_update_ito.json
"""

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import RecentUpdate  # noqa: E402
from app.repositories import RecentUpdateRepo, SubjectRepo  # noqa: E402

# recent_update_ito.json lives one level up, in the rounds_api parent dir.
DEFAULT_INPUT = Path(__file__).resolve().parent.parent.parent / "recent_update_ito.json"

# Source-subject names that don't match our taxonomy verbatim.
SUBJECT_ALIASES = {
    "general medicine": "Medicine",
    "obstetrics and gynecology": "Obstetrics & Gynecology",
    "obstetrics and gynaecology": "Obstetrics & Gynecology",
}


def _build_subject_map() -> dict:
    """Builds a lower-cased subject-name -> (id, canonical name) lookup.

    Returns:
        A dict keyed by lower-cased subject name.
    """
    return {
        s.name.lower(): (s.id, s.name) for s in SubjectRepo().list_all()
    }


def _map_subject(source_subject: str | None, subject_map: dict) -> tuple:
    """Maps a source subject string onto our taxonomy.

    Args:
        source_subject: The subject string from the source JSON.
        subject_map: Output of _build_subject_map().

    Returns:
        A (subject_id, subject_name) tuple; (None, None) if unmapped.
    """
    if not source_subject:
        return None, None
    key = source_subject.strip().lower()
    key = SUBJECT_ALIASES.get(key, source_subject.strip()).lower()
    match = subject_map.get(key)
    if match:
        return match[0], match[1]
    return None, None


def main() -> None:
    """Parses CLI arguments and ingests the recent updates.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Ingest recent updates.")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    records = json.loads(args.input.read_text(encoding="utf-8"))
    subject_map = _build_subject_map()
    repo = RecentUpdateRepo()

    mapped = unmapped = 0
    unmapped_subjects: set[str] = set()
    for rec in records:
        subject_id, subject_name = _map_subject(rec.get("subject"), subject_map)
        if subject_name:
            mapped += 1
        else:
            unmapped += 1
            if rec.get("subject"):
                unmapped_subjects.add(rec["subject"])

        repo.upsert_by_source_id(
            RecentUpdate(
                source_id=int(rec["id"]),
                date_of_update=rec.get("date_of_update"),
                subject=rec.get("subject"),
                subject_id=subject_id,
                subject_name=subject_name,
                update_topic=rec.get("update_topic", ""),
                content=rec.get("content", ""),
                reference=rec.get("reference") or {},
            )
        )

    print(f"ingested {len(records)} updates · subject mapped {mapped}, unmapped {unmapped}")
    if unmapped_subjects:
        print(f"  unmapped subjects: {sorted(unmapped_subjects)}")


if __name__ == "__main__":
    main()
