"""Build the medical concept graph that powers /api/suggest.

Two sources write into the same ``concepts`` collection:

  --source curated   Step 1. A small, hand-curated graph for the demo
                     concepts (IBD, MI, HF, Pantoprazole, ...). Pulls
                     canonical names + abbreviations from
                     app.services.abbreviations, "related" edges from
                     RELATED_CONCEPTS, the "delight" edges (child /
                     confused_with / next_step) from the curated maps below,
                     and aliases from data/medical_synonyms.txt.

  --source taxonomy  Step 2. Bulk breadth from the real NEET-PG syllabus
                     (data/subjects_with_syllabus.json): every subject, topic
                     and lesson becomes a searchable concept, with subject ->
                     topic -> lesson "a type of" child edges. ~1.5k nodes,
                     no external download, no license. Inserts only where a
                     name is not already present, so curated nodes win.

  --source all       curated (with drop) then taxonomy (append). Default.

Usage:
    uv run python scripts/build_concept_graph.py                 # all
    uv run python scripts/build_concept_graph.py --source curated
    uv run python scripts/build_concept_graph.py --source taxonomy --no-drop
"""

import argparse
import json
import sys
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Collections, get_db  # noqa: E402
from app.models import Concept  # noqa: E402
from app.repositories import ConceptRepo  # noqa: E402
from app.services.abbreviations import (  # noqa: E402
    ABBREVIATIONS,
    RELATED_CONCEPTS,
)


SYNONYMS_PATH = Path("data/medical_synonyms.txt")
SYLLABUS_PATH = Path("data/subjects_with_syllabus.json")

CURATED_POPULARITY = 0.90
TARGET_STUB_POPULARITY = 0.70
TAXONOMY_POPULARITY = {"subject": 0.60, "topic": 0.50, "lesson": 0.40}


# The "delight" edges that are NOT already in the existing dictionaries.
# Keyed by canonical (title-cased) name.
CURATED_CHILDREN: dict[str, list[str]] = {
    "Inflammatory Bowel Disease": ["Ulcerative Colitis", "Crohn's Disease"],
    "Myocardial Infarction": ["STEMI", "NSTEMI"],
    "Acute Coronary Syndrome": ["STEMI", "NSTEMI", "Unstable Angina"],
    "Heart Failure": ["HFrEF", "HFpEF"],
    "Diabetes Mellitus": ["Type 1 Diabetes Mellitus", "Type 2 Diabetes Mellitus"],
    "Cerebrovascular Accident": ["Ischemic Stroke", "Hemorrhagic Stroke"],
}

CURATED_CONFUSED: dict[str, list[str]] = {
    "Inflammatory Bowel Disease": ["Irritable Bowel Syndrome"],
    "Myocardial Infarction": ["Angina Pectoris"],
    "Ulcerative Colitis": ["Crohn's Disease"],
    "Acute Kidney Injury": ["Chronic Kidney Disease"],
}

# Rendered as "<concept> — <intent>" in the dropdown.
CURATED_NEXT_STEP: dict[str, list[str]] = {
    "Inflammatory Bowel Disease": ["management"],
    "Myocardial Infarction": ["diagnosis", "management"],
    "Heart Failure": ["management"],
    "Diabetes Mellitus": ["management"],
    "Tuberculosis": ["treatment"],
}


def _slug_lower(name: str) -> str:
    """Returns the lower-cased canonical form used as the upsert key.

    Args:
        name: A display name.

    Returns:
        The lower-cased, stripped name.
    """
    return name.strip().lower()


def _parse_synonym_classes(path: Path) -> list[list[str]]:
    """Parses the Solr-format synonyms file into equivalence classes.

    Args:
        path: Path to medical_synonyms.txt.

    Returns:
        A list of equivalence classes, each a list of lower-cased terms.
    """
    classes: list[list[str]] = []
    if not path.exists():
        return classes
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        terms = [t.strip().lower() for t in line.split(",") if t.strip()]
        if len(terms) >= 2:
            classes.append(terms)
    return classes


def _build_term_index(classes: list[list[str]]) -> dict[str, set[int]]:
    """Maps each synonym term to the indices of classes that contain it.

    Args:
        classes: Equivalence classes from _parse_synonym_classes.

    Returns:
        A dict of term -> set of class indices.
    """
    index: dict[str, set[int]] = {}
    for idx, terms in enumerate(classes):
        for term in terms:
            index.setdefault(term, set()).add(idx)
    return index


def _expand_aliases(
    seed_terms: set[str],
    classes: list[list[str]],
    term_index: dict[str, set[int]],
) -> list[str]:
    """Expands a concept's seed terms with one hop through synonym classes.

    Args:
        seed_terms: Lower-cased terms already known for the concept.
        classes: All equivalence classes.
        term_index: Output of _build_term_index.

    Returns:
        Sorted, de-duplicated list of alias terms (lower-cased).
    """
    aliases: set[str] = set(seed_terms)
    for term in list(seed_terms):
        for class_idx in term_index.get(term, ()):
            aliases.update(classes[class_idx])
    return sorted(aliases)


def build_curated(repo: ConceptRepo, drop: bool) -> int:
    """Builds the curated demo concept graph.

    Args:
        repo: The concept repository.
        drop: When True, drops the concepts collection before seeding.

    Returns:
        The number of concept nodes written.
    """
    if drop:
        get_db()[Collections.concepts].drop()

    classes = _parse_synonym_classes(SYNONYMS_PATH)
    term_index = _build_term_index(classes)

    # name_lower -> abbr (upper-cased), so target/stub nodes can recover an
    # abbreviation when one exists.
    name_to_abbr: dict[str, str] = {
        _slug_lower(name): abbr.upper() for abbr, name in ABBREVIATIONS.items()
    }

    # canonical name -> partial record we accumulate before persisting.
    records: dict[str, dict] = {}

    def ensure(name: str, abbr: str | None = None, popularity: float = TARGET_STUB_POPULARITY) -> dict:
        key = _slug_lower(name)
        rec = records.get(key)
        if rec is None:
            rec = {
                "name": name,
                "abbr": abbr or name_to_abbr.get(key),
                "popularity": popularity,
                "edges": {},
                "seed_terms": {key},
            }
            records[key] = rec
        if abbr and not rec["abbr"]:
            rec["abbr"] = abbr
        rec["popularity"] = max(rec["popularity"], popularity)
        return rec

    # 1. One concept per abbreviation entry (the headline demo concepts).
    for abbr, name in ABBREVIATIONS.items():
        rec = ensure(name, abbr=abbr.upper(), popularity=CURATED_POPULARITY)
        rec["seed_terms"].update({abbr.lower(), _slug_lower(name)})

    # 2. Attach edges, creating stub nodes for any referenced target.
    def attach(edge_map: dict[str, list[str]], edge_type: str, literal: bool) -> None:
        for canonical, targets in edge_map.items():
            rec = ensure(canonical, popularity=CURATED_POPULARITY)
            rec["edges"][edge_type] = list(targets)
            if not literal:
                for target in targets:
                    ensure(target)  # make the target resolvable on its own

    attach(RELATED_CONCEPTS, "related", literal=False)
    attach(CURATED_CHILDREN, "child", literal=False)
    attach(CURATED_CONFUSED, "confused_with", literal=False)
    attach(CURATED_NEXT_STEP, "next_step", literal=True)  # intents are not nodes

    # 3. Expand aliases via synonyms, compute search_terms, persist.
    for rec in records.values():
        if rec["abbr"]:
            rec["seed_terms"].add(rec["abbr"].lower())
        aliases = _expand_aliases(rec["seed_terms"], classes, term_index)
        name_lower = _slug_lower(rec["name"])
        search_terms = sorted(set(aliases) | {name_lower})
        repo.upsert_by_name(
            Concept(
                name=rec["name"],
                name_lower=name_lower,
                abbr=rec["abbr"],
                aliases=aliases,
                search_terms=search_terms,
                edges=rec["edges"],
                source="curated",
                popularity=rec["popularity"],
            )
        )

    return len(records)


def build_taxonomy(repo: ConceptRepo, path: Path) -> dict:
    """Builds bulk concept nodes from the NEET-PG syllabus taxonomy.

    Args:
        repo: The concept repository.
        path: Path to subjects_with_syllabus.json.

    Returns:
        Counts of inserted nodes per level.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    classes = _parse_synonym_classes(SYNONYMS_PATH)
    term_index = _build_term_index(classes)
    stats = {"subject": 0, "topic": 0, "lesson": 0}

    def make(name: str, level: str, context: str, children: list[str]) -> Concept:
        name_lower = _slug_lower(name)
        aliases = _expand_aliases({name_lower}, classes, term_index)
        edges = {"child": children} if children else {}
        return Concept(
            name=name,
            name_lower=name_lower,
            self_context=context,
            aliases=aliases,
            search_terms=sorted(set(aliases) | {name_lower}),
            edges=edges,
            source="taxonomy",
            popularity=TAXONOMY_POPULARITY[level],
        )

    for subject in data.get("subjects", []):
        s_name = subject.get("name")
        if not s_name:
            continue
        topics = subject.get("topics", [])
        if repo.insert_if_absent(
            make(s_name, "subject", "subject", [t["name"] for t in topics if t.get("name")])
        ):
            stats["subject"] += 1

        for topic in topics:
            t_name = topic.get("name")
            if not t_name:
                continue
            lessons = topic.get("lessons", [])
            if repo.insert_if_absent(
                make(
                    t_name,
                    "topic",
                    f"topic in {s_name}",
                    [le["name"] for le in lessons if le.get("name")],
                )
            ):
                stats["topic"] += 1

            for lesson in lessons:
                l_name = lesson.get("name")
                if not l_name:
                    continue
                if repo.insert_if_absent(make(l_name, "lesson", f"in {t_name}", [])):
                    stats["lesson"] += 1

    return stats


def main() -> None:
    """Parses CLI arguments and builds the requested concept-graph source(s).

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Build the medical concept graph.")
    parser.add_argument(
        "--source",
        choices=["curated", "taxonomy", "all"],
        default="all",
        help="Which source(s) to build (default: all).",
    )
    parser.add_argument(
        "--no-drop",
        action="store_true",
        help="Do not drop the concepts collection before the curated build.",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=SYLLABUS_PATH,
        help=f"Syllabus JSON for the taxonomy build (default: {SYLLABUS_PATH}).",
    )
    args = parser.parse_args()

    repo = ConceptRepo()

    if args.source in ("curated", "all"):
        count = build_curated(repo, drop=not args.no_drop)
        print(f"curated:  {count} concepts")

    if args.source in ("taxonomy", "all"):
        if not args.input.exists():
            print(f"error: syllabus not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        stats = build_taxonomy(repo, args.input)
        print(
            "taxonomy: "
            f"{stats['subject']} subjects, {stats['topic']} topics, "
            f"{stats['lesson']} lessons inserted"
        )

    repo.ensure_indexes()
    total = get_db()[Collections.concepts].estimated_document_count()
    print(f"indexes ensured · {total} total concepts in '{Collections.concepts}'")


if __name__ == "__main__":
    main()
