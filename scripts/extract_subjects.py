"""Extract canonical NEET-PG 2026 subjects from a MedMCQA dump.

Reads a MedMCQA file (JSONL or JSON array), maps each record's `subject_name`
to the canonical NEET-PG 2026 subject taxonomy (19 subjects across 3
categories), aggregates MCQ counts per canonical subject, and writes a
structured JSON file ready for manual topic/lesson population.

Subjects not in the NEET-PG syllabus (e.g. Dental) and unclassified records
(Unknown) are dropped and reported under a "skipped" section.

Usage:
    uv run python scripts/extract_subjects.py <input_path> [-o <output_path>]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# Mapping: MedMCQA subject_name -> NEET-PG 2026 canonical name.
# `None` means the source subject is dropped (not part of NEET-PG syllabus).
SUBJECT_MAP: dict[str, str | None] = {
    # Direct (already canonical)
    "Anatomy": "Anatomy",
    "Physiology": "Physiology",
    "Biochemistry": "Biochemistry",
    "Pathology": "Pathology",
    "Pharmacology": "Pharmacology",
    "Microbiology": "Microbiology",
    "Forensic Medicine": "Forensic Medicine",
    "Medicine": "Medicine",
    "Surgery": "Surgery",
    "Pediatrics": "Pediatrics",
    "ENT": "ENT",
    "Ophthalmology": "Ophthalmology",
    "Psychiatry": "Psychiatry",
    "Radiology": "Radiology",
    # Renamed / re-ordered
    "Social & Preventive Medicine": "Community Medicine",
    "Gynaecology & Obstetrics": "Obstetrics & Gynecology",
    "Skin": "Dermatology",
    # Spelling: UK -> US (per NEET-PG 2026 canonical list)
    "Anaesthesia": "Anesthesia",
    "Orthopaedics": "Orthopedics",
    # Dropped
    "Dental": None,    # not part of NEET-PG syllabus
    "Unknown": None,   # unclassified records
}


# NEET-PG 2026 canonical taxonomy by category.
CATEGORY_SUBJECTS: dict[str, list[str]] = {
    "Pre-Clinical": ["Anatomy", "Physiology", "Biochemistry"],
    "Para-Clinical": [
        "Pathology",
        "Pharmacology",
        "Microbiology",
        "Forensic Medicine",
        "Community Medicine",
    ],
    "Clinical": [
        "Medicine",
        "Surgery",
        "Obstetrics & Gynecology",
        "Pediatrics",
        "Orthopedics",
        "ENT",
        "Ophthalmology",
        "Dermatology",
        "Psychiatry",
        "Radiology",
        "Anesthesia",
    ],
}

CATEGORY_ORDER = ["Pre-Clinical", "Para-Clinical", "Clinical"]

# Reverse lookup: canonical subject -> category.
SUBJECT_CATEGORY: dict[str, str] = {
    subject: category
    for category, subjects in CATEGORY_SUBJECTS.items()
    for subject in subjects
}


def load_records(path: Path) -> list[dict]:
    """Load MedMCQA records, auto-detecting JSONL vs JSON array format."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        return json.loads(text)

    records: list[dict] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(
                f"warn: skipping malformed line {line_no}: {exc}",
                file=sys.stderr,
            )
    return records


def aggregate(records: list[dict]) -> tuple[
    dict[str, int],
    dict[str, set[str]],
    Counter,
    Counter,
]:
    """Aggregate MCQ counts under canonical NEET-PG subjects.

    Returns:
        canonical_counts: canonical_name -> mcq_count
        source_subjects:  canonical_name -> set of MedMCQA source names that
                          contributed to it
        skipped_counts:   MedMCQA source name -> mcq_count (mapped to None)
        unmapped_counts:  MedMCQA source name -> mcq_count (not in SUBJECT_MAP)
    """
    canonical_counts: dict[str, int] = defaultdict(int)
    source_subjects: dict[str, set[str]] = defaultdict(set)
    skipped_counts: Counter = Counter()
    unmapped_counts: Counter = Counter()

    for record in records:
        raw = record.get("subject_name")
        if not raw:
            unmapped_counts["<missing>"] += 1
            continue
        name = raw.strip()
        if not name:
            unmapped_counts["<missing>"] += 1
            continue

        if name not in SUBJECT_MAP:
            unmapped_counts[name] += 1
            continue

        canonical = SUBJECT_MAP[name]
        if canonical is None:
            skipped_counts[name] += 1
            continue

        canonical_counts[canonical] += 1
        source_subjects[canonical].add(name)

    return canonical_counts, source_subjects, skipped_counts, unmapped_counts


def build_output(
    canonical_counts: dict[str, int],
    source_subjects: dict[str, set[str]],
    skipped_counts: Counter,
    unmapped_counts: Counter,
) -> dict:
    subjects = []
    for category in CATEGORY_ORDER:
        in_category = [
            (name, canonical_counts.get(name, 0))
            for name in CATEGORY_SUBJECTS[category]
        ]
        in_category.sort(key=lambda item: item[1], reverse=True)
        for name, count in in_category:
            subjects.append(
                {
                    "name": name,
                    "category": category,
                    "mcq_count": count,
                    "source_subjects": sorted(source_subjects.get(name, set())),
                    "topics": [],
                }
            )

    return {
        "source": "medmcqa",
        "taxonomy": "NEET-PG 2026",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total_subjects": len(subjects),
        "total_mcqs": sum(canonical_counts.values()),
        "skipped": {
            "reason": "not part of NEET-PG syllabus or unclassified",
            "by_source": [
                {"name": name, "mcq_count": count}
                for name, count in skipped_counts.most_common()
            ],
            "total_mcqs": sum(skipped_counts.values()),
        },
        "unmapped": {
            "reason": "source subject_name not present in SUBJECT_MAP",
            "by_source": [
                {"name": name, "mcq_count": count}
                for name, count in unmapped_counts.most_common()
            ],
            "total_mcqs": sum(unmapped_counts.values()),
        },
        "subjects": subjects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract canonical NEET-PG 2026 subjects from a MedMCQA dump"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to MedMCQA file (JSONL or JSON array)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/subjects.json"),
        help="Output JSON path (default: data/subjects.json)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    records = load_records(args.input)
    if not records:
        print("error: no records loaded from input", file=sys.stderr)
        sys.exit(1)

    canonical_counts, source_subjects, skipped_counts, unmapped_counts = aggregate(
        records
    )

    output = build_output(
        canonical_counts, source_subjects, skipped_counts, unmapped_counts
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        f"Mapped to {output['total_subjects']} NEET-PG 2026 subjects "
        f"from {output['total_mcqs']} MCQs."
    )
    print(f"Skipped: {output['skipped']['total_mcqs']} MCQs "
          f"({', '.join(s['name'] for s in output['skipped']['by_source']) or 'none'})")
    if output["unmapped"]["total_mcqs"]:
        print(
            f"WARN: {output['unmapped']['total_mcqs']} MCQs had subject_name "
            f"not in SUBJECT_MAP — add entries for: "
            f"{', '.join(s['name'] for s in output['unmapped']['by_source'])}"
        )
    print(f"Output: {args.output}")
    print("\nBy category:")
    for category in CATEGORY_ORDER:
        print(f"  {category}")
        for subject in output["subjects"]:
            if subject["category"] == category:
                print(
                    f"    {subject['mcq_count']:>6}  {subject['name']}"
                    + (
                        f"   (from: {', '.join(subject['source_subjects'])})"
                        if subject["source_subjects"]
                        and subject["source_subjects"] != [subject["name"]]
                        else ""
                    )
                )


if __name__ == "__main__":
    main()
