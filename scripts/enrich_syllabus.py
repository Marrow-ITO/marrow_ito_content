"""Enrich subjects.json with topic and lesson hierarchy scraped from prepladder.

Reads the canonical NEET-PG subjects file (output of extract_subjects.py),
fetches the prepladder NEET-PG syllabus page, parses the single
"Subject-wise NEET PG Syllabus" table (3 columns: Subject, Topic, Sub-Topic),
maps the source subject names to the NEET-PG 2026 canonical taxonomy, and
populates each subject's `topics` array with topics and lessons.

Table cell structure expected on the source page:
    <td rowspan="N"><h4>NEET PG Exam Syllabus for <a>Anatomy</a></h4></td>
    <td>General Embryology</td>
    <td><ul><li>Developmental Timeline</li><li><a>Gametogenesis</a></li>...</ul></td>

The original file is preserved; output is written to a new file by default.

Usage:
    uv run python scripts/enrich_syllabus.py
    uv run python scripts/enrich_syllabus.py -i data/subjects.json \
        -o data/subjects_with_syllabus.json
    uv run python scripts/enrich_syllabus.py --save-html debug.html
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag


SYLLABUS_URL = (
    "https://www.prepladder.com/neet-pg-study-material/syllabus/"
    "neet-pg-syllabus-detailed-subject-wise-topics"
)

# Mapping: prepladder subject name -> NEET-PG 2026 canonical name.
# `None` means the prepladder subject is dropped (not part of NEET-PG 2026).
SUBJECT_MAP: dict[str, str | None] = {
    "Anatomy": "Anatomy",
    "Physiology": "Physiology",
    "Biochemistry": "Biochemistry",
    "Pathology": "Pathology",
    "Pharmacology": "Pharmacology",
    "Microbiology": "Microbiology",
    "PSM": "Community Medicine",
    "ENT": "ENT",
    "Ophthalmology": "Ophthalmology",
    "Gynaecology & Obstetrics": "Obstetrics & Gynecology",
    "Forensic Medicine": "Forensic Medicine",
    "Pediatrics": "Pediatrics",
    "Surgery": "Surgery",
    "Medicine": "Medicine",
    "Radiology": "Radiology",
    "Dermatology": "Dermatology",
    "Psychiatry": "Psychiatry",
    "Orthopedics": "Orthopedics",
    "Anesthesia": "Anesthesia",
    # Dropped (not in NEET-PG 2026 canonical list)
    "Emergency Medicine": None,
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_html(url: str) -> str:
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=30
    )
    response.raise_for_status()
    return response.text


def find_syllabus_table(soup: BeautifulSoup) -> Tag | None:
    """Locate the syllabus table by caption text, with a header-based fallback."""
    for table in soup.find_all("table"):
        caption = table.find("caption")
        if caption and "Subject-wise NEET PG Syllabus" in caption.get_text():
            return table
    for table in soup.find_all("table"):
        header_texts = [
            th.get_text(strip=True).lower() for th in table.find_all("th")
        ]
        if {"subject", "topic"} <= set(header_texts):
            return table
    return None


SUBJECT_PREFIX = "NEET PG Exam Syllabus for"


def _normalise(text: str) -> str:
    """Strip non-breaking spaces and surrounding whitespace."""
    return text.replace("\xa0", " ").strip()


def extract_subject_name(cell: Tag) -> str | None:
    """Pull the clean subject name out of the subject column cell.

    The cell looks like:
        <td rowspan="N"><h4>NEET PG Exam Syllabus for <a>Anatomy</a></h4></td>

    Prefer the anchor text; fall back to stripping the boilerplate prefix.
    """
    heading = cell.find("h4") or cell.find(["h3", "h2"])
    if heading is not None:
        anchor = heading.find("a")
        if anchor is not None:
            name = _normalise(anchor.get_text(separator=" ", strip=True))
            if name:
                return name
        text = _normalise(heading.get_text(separator=" ", strip=True))
        if text.startswith(SUBJECT_PREFIX):
            text = text[len(SUBJECT_PREFIX) :].strip()
        return text or None

    text = _normalise(cell.get_text(separator=" ", strip=True))
    return text or None


def extract_lessons(cell: Tag) -> list[str]:
    """Pull individual lesson names from a sub-topic cell.

    The cell is expected to contain `<ul><li>...</li></ul>`; each `<li>`
    becomes one lesson. If no `<li>` is present, the whole cell text is
    treated as a single lesson (fallback for malformed rows).
    """
    items = cell.find_all("li")
    if items:
        lessons = [
            _normalise(item.get_text(separator=" ", strip=True))
            for item in items
        ]
        return [lesson for lesson in lessons if lesson]

    text = _normalise(cell.get_text(separator=" ", strip=True))
    return [text] if text else []


def parse_table(table: Tag) -> list[tuple[str, str, list[str]]]:
    """Walk all rows, carrying forward subject/topic across rowspan cells.

    Each output row is (subject_name, topic_name, [lesson, ...]) where the
    lesson list has already been split from the `<li>` items.
    """
    rows: list[tuple[str, str, list[str]]] = []
    last_subject: str | None = None
    last_topic: str | None = None

    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        if all(cell.name == "th" for cell in cells):
            continue  # skip header row

        subject_cell: Tag | None = None
        topic_cell: Tag | None = None
        subtopic_cell: Tag | None = None

        if len(cells) >= 3:
            subject_cell, topic_cell, subtopic_cell = cells[0], cells[1], cells[2]
        elif len(cells) == 2:
            topic_cell, subtopic_cell = cells[0], cells[1]
        elif len(cells) == 1:
            subtopic_cell = cells[0]

        if subject_cell is not None:
            new_subject = extract_subject_name(subject_cell)
            if new_subject:
                last_subject = new_subject
        if topic_cell is not None:
            new_topic = _normalise(topic_cell.get_text(separator=" ", strip=True))
            if new_topic:
                last_topic = new_topic

        if subtopic_cell is not None and last_subject and last_topic:
            lessons = extract_lessons(subtopic_cell)
            if lessons:
                rows.append((last_subject, last_topic, lessons))

    return rows


def build_taxonomy(
    rows: list[tuple[str, str, list[str]]],
) -> tuple[dict[str, dict[str, list[str]]], set[str]]:
    """Group rows into {canonical_subject: {topic: [lesson, ...]}}.

    Returns the taxonomy and the set of source subject names that had no
    entry in SUBJECT_MAP (so the caller can warn).
    """
    taxonomy: dict[str, dict[str, list[str]]] = {}
    unmapped_subjects: set[str] = set()

    for raw_subject, topic, lessons_in_row in rows:
        raw_subject_normalised = raw_subject.strip()

        if raw_subject_normalised not in SUBJECT_MAP:
            unmapped_subjects.add(raw_subject_normalised)
            continue

        canonical = SUBJECT_MAP[raw_subject_normalised]
        if canonical is None:
            continue  # explicitly dropped

        topic_clean = topic.strip()
        if not topic_clean:
            continue

        subject_topics = taxonomy.setdefault(canonical, {})
        lessons = subject_topics.setdefault(topic_clean, [])
        seen = set(lessons)
        for lesson in lessons_in_row:
            if lesson and lesson not in seen:
                lessons.append(lesson)
                seen.add(lesson)

    return taxonomy, unmapped_subjects


def enrich_subjects(
    existing: dict, taxonomy: dict[str, dict[str, list[str]]]
) -> dict:
    """Populate `topics` on each subject from the taxonomy, preserving other fields."""
    for subject in existing.get("subjects", []):
        subject_topics = taxonomy.get(subject["name"], {})
        subject["topics"] = [
            {
                "name": topic_name,
                "lessons": [{"name": lesson} for lesson in lessons],
            }
            for topic_name, lessons in subject_topics.items()
        ]
    existing["syllabus_enriched_at"] = datetime.now(timezone.utc).isoformat()
    existing["syllabus_source"] = SYLLABUS_URL
    return existing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich subjects.json with topics/lessons from prepladder syllabus"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("data/subjects.json"),
        help="Existing subjects JSON (default: data/subjects.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/subjects_with_syllabus.json"),
        help="Output JSON (default: data/subjects_with_syllabus.json)",
    )
    parser.add_argument(
        "--syllabus-url",
        type=str,
        default=SYLLABUS_URL,
        help="Override the syllabus page URL",
    )
    parser.add_argument(
        "--save-html",
        type=Path,
        default=None,
        help="Save fetched HTML to this path for debugging",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    existing = json.loads(args.input.read_text(encoding="utf-8"))

    print(f"Fetching: {args.syllabus_url}")
    try:
        html = fetch_html(args.syllabus_url)
    except requests.RequestException as exc:
        print(f"error: failed to fetch syllabus page: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.save_html:
        args.save_html.parent.mkdir(parents=True, exist_ok=True)
        args.save_html.write_text(html, encoding="utf-8")
        print(f"Saved HTML: {args.save_html}")

    soup = BeautifulSoup(html, "html.parser")

    table = find_syllabus_table(soup)
    if table is None:
        print(
            "error: could not find the syllabus table on the page. "
            "Run with --save-html and inspect the markup.",
            file=sys.stderr,
        )
        sys.exit(3)

    rows = parse_table(table)
    if not rows:
        print(
            "error: syllabus table found but no usable rows parsed. "
            "Check the table structure with --save-html.",
            file=sys.stderr,
        )
        sys.exit(4)

    taxonomy, unmapped = build_taxonomy(rows)

    if unmapped:
        print(
            "WARN: unmapped prepladder subjects (no entry in SUBJECT_MAP): "
            f"{sorted(unmapped)}",
            file=sys.stderr,
        )

    enriched = enrich_subjects(existing, taxonomy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Parsed {len(rows)} rows from syllabus table.")
    print(f"Output: {args.output}")
    print("\nPer-subject topic / lesson counts:")
    for subject in enriched["subjects"]:
        topics = subject.get("topics", [])
        n_topics = len(topics)
        n_lessons = sum(len(topic["lessons"]) for topic in topics)
        marker = "" if n_topics else "   <- EMPTY (no rows matched)"
        print(
            f"  {subject['name']:<28} {n_topics:>3} topics, "
            f"{n_lessons:>4} lessons{marker}"
        )


if __name__ == "__main__":
    main()
