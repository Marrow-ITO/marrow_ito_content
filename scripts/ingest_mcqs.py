"""Ingest MedMCQA MCQs into MongoDB, semantically matched to seeded lessons.

Pipeline:
  1. Load MedMCQA records (JSONL or JSON array).
  2. Filter: choice_type == "single", all 4 options present, valid `cop`,
     `subject_name` mappable to a canonical NEET-PG 2026 subject that has
     lessons seeded in the DB.
  3. Dedupe by `source_id` against MCQs already in the DB.
  4. Per-subject top-up sampling: for each subject, sample up to
     (--per-subject) records minus what's already in the DB.
  5. Build one FAISS index per subject over its lesson embeddings, where
     each lesson is embedded as "Subject > Topic > Lesson".
  6. Embed each MCQ as (stem + options + explanation), search the subject's
     FAISS index, and assign to the top-1 lesson IF cosine similarity meets
     the threshold. Below-threshold MCQs are skipped (not inserted).
  7. Insert each accepted MCQ with resolved (subject_id, topic_id,
     lesson_id, qbank_id) plus provenance (source_id, match_similarity).

Embedding model: pritamdeka/S-PubMedBert-MS-MARCO (medical-aware, local,
via sentence-transformers).

Dedupe: skips records whose MedMCQA `id` is already present in the mcqs
collection (set via `source_id` on prior runs).

Usage:
    uv sync --group ingest         # one-time, installs torch/faiss/etc.
    uv run python scripts/ingest_mcqs.py /path/to/medmcqa.jsonl
    uv run python scripts/ingest_mcqs.py /path/to/medmcqa.jsonl \\
        --per-subject 2000 --threshold 0.6 --seed 42
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import faiss  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.db import Collections, get_collection  # noqa: E402
from app.models import MCQ, MCQAnswer  # noqa: E402
from app.repositories import (  # noqa: E402
    LessonRepo,
    MCQRepo,
    QBankRepo,
    SubjectRepo,
    TopicRepo,
)


DEFAULT_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
DEFAULT_PER_SUBJECT = 2000
DEFAULT_THRESHOLD = 0.6


# MedMCQA subject_name -> canonical NEET-PG 2026 name. Mirror of the map in
# extract_subjects.py; duplicated here to keep this script self-contained.
SUBJECT_MAP: dict[str, str | None] = {
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
    "Social & Preventive Medicine": "Community Medicine",
    "Gynaecology & Obstetrics": "Obstetrics & Gynecology",
    "Skin": "Dermatology",
    "Anaesthesia": "Anesthesia",
    "Orthopaedics": "Orthopedics",
    "Dental": None,
    "Unknown": None,
}


COP_TO_ANSWER = {
    1: MCQAnswer.OPTION_1,
    2: MCQAnswer.OPTION_2,
    3: MCQAnswer.OPTION_3,
    4: MCQAnswer.OPTION_4,
}


# ---------- Loading and filtering ----------

def load_records(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    records: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def is_valid(record: dict) -> bool:
    if record.get("choice_type") != "single":
        return False
    if not record.get("question"):
        return False
    if not all(record.get(k) for k in ("opa", "opb", "opc", "opd")):
        return False
    if record.get("cop") not in (1, 2, 3, 4):
        return False
    subject_raw = (record.get("subject_name") or "").strip()
    if subject_raw not in SUBJECT_MAP or SUBJECT_MAP[subject_raw] is None:
        return False
    return True


def sample_top_up(
    records: list[dict],
    per_subject_target: int,
    existing_per_subject: dict[str, int],
    seed: int,
) -> tuple[list[dict], dict[str, dict[str, int]]]:
    """Sample records to top each subject up to `per_subject_target`.

    Returns (sample, quotas) where `quotas[subject_name]` is a dict with
    keys: existing, quota, available, sampled.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        canonical = SUBJECT_MAP[record["subject_name"].strip()]
        grouped[canonical].append(record)

    rng = random.Random(seed)
    sample: list[dict] = []
    quotas: dict[str, dict[str, int]] = {}

    for subject, recs in grouped.items():
        existing = existing_per_subject.get(subject, 0)
        quota = max(0, per_subject_target - existing)
        if quota <= 0:
            quotas[subject] = {
                "existing": existing,
                "quota": 0,
                "available": len(recs),
                "sampled": 0,
            }
            continue
        rng.shuffle(recs)
        picked = recs[:quota]
        sample.extend(picked)
        quotas[subject] = {
            "existing": existing,
            "quota": quota,
            "available": len(recs),
            "sampled": len(picked),
        }

    return sample, quotas


# ---------- Text builders for embedding ----------

def build_mcq_text(record: dict) -> str:
    parts = [
        record["question"].strip(),
        f"A) {record['opa']}",
        f"B) {record['opb']}",
        f"C) {record['opc']}",
        f"D) {record['opd']}",
    ]
    explanation = (record.get("exp") or "").strip()
    if explanation:
        parts.append(f"Explanation: {explanation}")
    return " | ".join(parts)


def build_lesson_text(subject: str, topic: str, lesson: str) -> str:
    return f"{subject} > {topic} > {lesson}"


# ---------- Per-subject FAISS index ----------

class SubjectIndex:
    def __init__(
        self,
        subject_id,
        subject_name: str,
        index: faiss.Index,
        entries: list[dict],
    ):
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.index = index
        self.entries = entries


def build_subject_indexes(
    model: SentenceTransformer,
) -> dict[str, SubjectIndex]:
    subject_repo = SubjectRepo()
    topic_repo = TopicRepo()
    lesson_repo = LessonRepo()
    qbank_repo = QBankRepo()

    indexes: dict[str, SubjectIndex] = {}

    for subject in subject_repo.list_all():
        topics = topic_repo.list_by_subject(subject.id)
        entries: list[dict] = []
        texts: list[str] = []

        for topic in topics:
            lessons = lesson_repo.list_by_topic(topic.id)
            for lesson in lessons:
                qbanks = qbank_repo.list_by_lesson(lesson.id)
                if not qbanks:
                    continue
                entries.append(
                    {
                        "lesson_id": lesson.id,
                        "lesson_name": lesson.name,
                        "topic_id": topic.id,
                        "topic_name": topic.name,
                        "qbank_id": qbanks[0].id,
                    }
                )
                texts.append(
                    build_lesson_text(subject.name, topic.name, lesson.name)
                )

        if not entries:
            continue

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        indexes[subject.name] = SubjectIndex(
            subject_id=subject.id,
            subject_name=subject.name,
            index=index,
            entries=entries,
        )

    return indexes


def existing_source_ids() -> set[str]:
    """Pull source_id values already present in the mcqs collection."""
    coll = get_collection(Collections.mcqs)
    return {
        doc["source_id"]
        for doc in coll.find(
            {"source_id": {"$exists": True, "$ne": None}},
            {"source_id": 1, "_id": 0},
        )
    }


def existing_counts_by_subject_name() -> dict[str, int]:
    """How many MCQs are already in the DB per canonical subject name."""
    subjects = {s.id: s.name for s in SubjectRepo().list_all()}
    counts_by_id = MCQRepo().counts_by_subject()
    return {
        subjects[subject_id]: count
        for subject_id, count in counts_by_id.items()
        if subject_id in subjects
    }


# ---------- Main ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest MedMCQA MCQs into MongoDB via semantic lesson matching"
    )
    parser.add_argument("input", type=Path, help="MedMCQA file (JSONL or JSON array)")
    parser.add_argument(
        "--per-subject", type=int, default=DEFAULT_PER_SUBJECT,
        help=(
            f"Target MCQ count per subject in the DB (top-up; default: "
            f"{DEFAULT_PER_SUBJECT}). Subjects already at or above this "
            "count are skipped."
        ),
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Min cosine similarity for assignment (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"sentence-transformers model id (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # 1. Load + filter
    print(f"Loading: {args.input}")
    records = load_records(args.input)
    print(f"  Raw records:    {len(records)}")

    valid = [r for r in records if is_valid(r)]
    print(f"  After filter:   {len(valid)} (single-type, valid, mapped subject)")

    # 2. Load embedding model + build per-subject indexes
    print(f"\nLoading embedding model: {args.model}")
    print("  (first run downloads ~500MB)")
    model = SentenceTransformer(args.model)

    print("Building per-subject lesson indexes...")
    indexes = build_subject_indexes(model)
    print(f"  Subjects with lessons: {len(indexes)}")
    for name, idx in indexes.items():
        print(f"    {name:<28} {len(idx.entries):>4} lessons")

    if not indexes:
        print("error: no lessons in DB. Run seed_taxonomy.py first.", file=sys.stderr)
        sys.exit(2)

    # 3. Filter records to subjects we have indexes for + dedupe by source_id
    eligible = [
        r for r in valid
        if SUBJECT_MAP[r["subject_name"].strip()] in indexes
    ]
    print(f"\n  Eligible (subject has lessons): {len(eligible)}")

    already_ingested = existing_source_ids()
    if already_ingested:
        before = len(eligible)
        eligible = [r for r in eligible if str(r.get("id")) not in already_ingested]
        print(
            f"  After dedupe by source_id: {len(eligible)} "
            f"(skipped {before - len(eligible)} already ingested)"
        )

    # 4. Per-subject top-up sample
    existing_counts = existing_counts_by_subject_name()
    sampled, quotas = sample_top_up(
        eligible, args.per_subject, existing_counts, args.seed
    )
    print(
        f"\n  Top-up plan (target {args.per_subject} per subject; "
        f"{len(sampled)} new records to process):"
    )
    print(
        f"    {'subject':<28} {'existing':>9} {'quota':>7} "
        f"{'avail':>7} {'sampled':>8}"
    )
    for subject in sorted(quotas):
        q = quotas[subject]
        short = " (LOW)" if q["sampled"] < q["quota"] else ""
        print(
            f"    {subject:<28} {q['existing']:>9} {q['quota']:>7} "
            f"{q['available']:>7} {q['sampled']:>8}{short}"
        )
    if not sampled:
        print("\nNothing to do: every subject already at or above target.")
        return

    # 5. Batch-embed all sampled MCQs
    print(f"\nEmbedding {len(sampled)} MCQs (batched)...")
    texts = [build_mcq_text(r) for r in sampled]
    mcq_embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # 6. Per-MCQ: search the subject's index + insert if above threshold
    mcq_repo = MCQRepo()
    matched_per_subject: dict[str, int] = defaultdict(int)
    skipped_per_subject: dict[str, int] = defaultdict(int)
    similarities: list[float] = []

    print(f"\nMatching and inserting (threshold = {args.threshold})...")
    for i, record in enumerate(sampled):
        canonical = SUBJECT_MAP[record["subject_name"].strip()]
        subject_index = indexes[canonical]

        query = mcq_embeddings[i : i + 1]
        scores, ids = subject_index.index.search(query, k=1)
        top_score = float(scores[0][0])
        top_entry = subject_index.entries[int(ids[0][0])]
        similarities.append(top_score)

        if top_score < args.threshold:
            skipped_per_subject[canonical] += 1
            continue

        mcq = MCQ(
            title=record["question"].strip(),
            option_1=record["opa"],
            option_2=record["opb"],
            option_3=record["opc"],
            option_4=record["opd"],
            answer=COP_TO_ANSWER[record["cop"]],
            answer_desc=(record.get("exp") or "").strip(),
            subject_id=subject_index.subject_id,
            topic_id=top_entry["topic_id"],
            lesson_id=top_entry["lesson_id"],
            qbank_id=top_entry["qbank_id"],
            source_id=str(record.get("id")) if record.get("id") else None,
            match_similarity=top_score,
        )
        mcq_repo.insert(mcq)
        matched_per_subject[canonical] += 1

    # 7. Report
    total_matched = sum(matched_per_subject.values())
    total_skipped = sum(skipped_per_subject.values())

    print("\nResults:")
    print(f"  Total processed: {len(sampled)}")
    print(f"  Matched (inserted): {total_matched}")
    print(f"  Skipped (below threshold {args.threshold}): {total_skipped}")
    if similarities:
        arr = np.array(similarities)
        print(
            f"  Similarity distribution: "
            f"min={arr.min():.3f}, "
            f"mean={arr.mean():.3f}, "
            f"median={np.median(arr):.3f}, "
            f"max={arr.max():.3f}"
        )

    print("\nPer-subject breakdown:")
    all_subjects = sorted(set(matched_per_subject) | set(skipped_per_subject))
    for subject in all_subjects:
        m = matched_per_subject.get(subject, 0)
        s = skipped_per_subject.get(subject, 0)
        total = m + s
        rate = (m / total * 100) if total else 0.0
        print(
            f"  {subject:<28} matched={m:>4}, skipped={s:>4} "
            f"({rate:>5.1f}% accepted)"
        )


if __name__ == "__main__":
    main()
