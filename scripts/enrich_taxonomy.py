"""Enrich NEET-PG syllabus topics into curated-quality concepts via an LLM.

The raw syllabus topics (e.g. "Vitamins and Minerals", "Urinary tract") are
clean names but carry no relationships. This script sends each topic to
Claude (Haiku by default) and asks for a canonical concept with an
abbreviation, aliases, and the "delight" edges (child / confused_with /
next_step). The results are written into the same ``concepts`` collection
with ``source = "enriched"`` and inserted only where the name is not already
present, so hand-curated concepts keep their authoritative edges.

Auth: reads ANTHROPIC_API_KEY (and optional ANTHROPIC_BASE_URL) from the
environment / project .env. Set a real key in marrow_ito_search/.env first.

Usage:
    uv run python scripts/enrich_taxonomy.py
    uv run python scripts/enrich_taxonomy.py --model claude-haiku-4-5 --limit 24
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Concept  # noqa: E402
from app.repositories import ConceptRepo  # noqa: E402


SYLLABUS_PATH = Path("data/subjects_with_syllabus.json")
ENRICHED_POPULARITY = 0.70  # above rxnorm (0.55) / below curated (0.90)
DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_BATCH = 12

_SYSTEM_PROMPT = (
    "You are a medical knowledge expert building a concept graph for an "
    "Indian medical-entrance (NEET-PG) study app. For each syllabus topic "
    "you return one clean, canonical medical concept with high-yield, "
    "exam-relevant relationships. Be conservative: omit a relationship rather "
    "than guess. Respond with JSON only."
)

_USER_TEMPLATE = """For each numbered topic below, return a JSON array. Each element:
{{
  "i": <the topic number>,
  "name": "<clean Title-Case canonical concept name>",
  "abbr": "<common abbreviation or null>",
  "aliases": ["<synonyms / lay terms a student might type>"],
  "children": ["<key sub-types or sub-concepts — 'a type of'>"],
  "confused_with": ["<concepts students commonly confuse this with>"],
  "next_step": ["<common study intents, e.g. 'management', 'diagnosis'>"]
}}
Rules: max 5 items per list; use [] when nothing high-confidence applies;
abbr is null unless a real abbreviation exists. JSON array only, no prose.

Topics:
{topics}"""


def _load_topics(path: Path) -> list[dict]:
    """Loads (topic, subject) pairs from the syllabus JSON.

    Args:
        path: Path to subjects_with_syllabus.json.

    Returns:
        A list of {"name", "subject"} dicts for every topic.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    topics: list[dict] = []
    for subject in data.get("subjects", []):
        s_name = subject.get("name", "")
        for topic in subject.get("topics", []):
            t_name = topic.get("name")
            if t_name:
                topics.append({"name": t_name, "subject": s_name})
    return topics


def _already_enriched(repo: ConceptRepo) -> set[str]:
    """Returns the set of lower-cased topic names already enriched.

    Enables resumable runs: a topic is skipped when a prior enriched concept
    already lists it among its search terms.

    Args:
        repo: The concept repository.

    Returns:
        A set of lower-cased terms covered by existing enriched concepts.
    """
    covered: set[str] = set()
    for doc in repo.collection.find({"source": "enriched"}, {"search_terms": 1}):
        covered.update(doc.get("search_terms", []))
    return covered


def _extract_json_array(text: str) -> list:
    """Extracts the first JSON array from a model response.

    Args:
        text: Raw model text, possibly wrapped in code fences.

    Returns:
        The parsed list, or an empty list on failure.
    """
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return []


def _to_concept(item: dict, topic: dict) -> Concept | None:
    """Converts one LLM result item into a Concept document.

    Args:
        item: A single object from the model's JSON array.
        topic: The originating {"name", "subject"} topic.

    Returns:
        A Concept, or None if the item lacks a usable name.
    """
    name = (item.get("name") or topic["name"]).strip()
    if not name:
        return None
    abbr = item.get("abbr")
    abbr = abbr.upper().strip() if isinstance(abbr, str) and abbr.strip() else None

    aliases = {a.strip().lower() for a in item.get("aliases", []) if a.strip()}
    aliases.add(name.lower())
    aliases.add(topic["name"].lower())  # keep the original topic searchable
    if abbr:
        aliases.add(abbr.lower())

    edges: dict[str, list[str]] = {}
    for key, field in (("child", "children"), ("confused_with", "confused_with"),
                       ("next_step", "next_step")):
        values = [v.strip() for v in item.get(field, []) if isinstance(v, str) and v.strip()]
        if values:
            edges[key] = values[:5]

    return Concept(
        name=name,
        name_lower=name.lower(),
        abbr=abbr,
        self_context=None if abbr else f"topic in {topic['subject']}",
        aliases=sorted(aliases),
        search_terms=sorted(aliases | {name.lower()}),
        edges=edges,
        source="enriched",
        popularity=ENRICHED_POPULARITY,
    )


def _enrich_batch(client, model: str, batch: list[dict]) -> tuple[list, dict]:
    """Sends one batch of topics to the LLM and parses the response.

    Args:
        client: An anthropic.Anthropic client.
        model: The model id to call.
        batch: The topics in this batch.

    Returns:
        A tuple of (parsed items, token-usage dict).
    """
    listing = "\n".join(
        f"{i}. {t['name']} (subject: {t['subject']})" for i, t in enumerate(batch)
    )
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _USER_TEMPLATE.format(topics=listing)}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
    return _extract_json_array(text), usage


def main() -> None:
    """Parses CLI arguments and runs the enrichment pass.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="LLM-enrich syllabus topics.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--limit", type=int, default=None, help="Cap topics (testing).")
    parser.add_argument("-i", "--input", type=Path, default=SYLLABUS_PATH)
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "error: ANTHROPIC_API_KEY is not set. Add it to marrow_ito_search/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    import anthropic  # noqa: PLC0415 — local so the import error is actionable.

    client = anthropic.Anthropic()
    repo = ConceptRepo()

    topics = _load_topics(args.input)
    covered = _already_enriched(repo)
    pending = [t for t in topics if t["name"].lower() not in covered]
    if args.limit is not None:
        pending = pending[: args.limit]

    print(
        f"topics: {len(topics)} total · {len(topics) - len(pending)} already done · "
        f"{len(pending)} to enrich (model={args.model})"
    )

    written = 0
    tok_in = tok_out = 0
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        try:
            items, usage = _enrich_batch(client, args.model, batch)
        except Exception as exc:  # noqa: BLE001 — keep going on a bad batch.
            print(f"  batch @{start}: ERROR {type(exc).__name__}: {str(exc)[:120]}")
            continue
        tok_in += usage["in"]
        tok_out += usage["out"]

        by_index = {it["i"]: it for it in items if isinstance(it, dict) and "i" in it}
        for idx, topic in enumerate(batch):
            concept = _to_concept(by_index.get(idx, {}), topic)
            if concept and repo.insert_if_absent(concept):
                written += 1
        print(f"  batch @{start}: +{len(batch)} topics · {written} written so far")

    repo.ensure_indexes()
    print(
        f"done · {written} enriched concepts written · "
        f"tokens in={tok_in} out={tok_out}"
    )


if __name__ == "__main__":
    main()
