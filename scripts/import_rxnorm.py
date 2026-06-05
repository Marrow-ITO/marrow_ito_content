"""Import clean drug concepts from RxNorm into the concept graph.

Uses the open RxNav REST API (no key, no license, no file download):
``/REST/allconcepts.json?tty=IN`` for generic ingredients and ``tty=BN`` for
brand names. RxNorm's raw lists are noisy (IUPAC chemical strings, consumer
products), so names are filtered to clean, drug-like tokens before insert.

Drug nodes are inserted with ``insert_if_absent`` so curated concepts
(Pantoprazole, Aspirin, ...) keep their richer edges on a name collision.

Usage:
    uv run python scripts/import_rxnorm.py
    uv run python scripts/import_rxnorm.py --no-brands
"""

import argparse
import re
import sys
from pathlib import Path

import requests

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Concept  # noqa: E402
from app.repositories import ConceptRepo  # noqa: E402


RXNAV_ALLCONCEPTS = "https://rxnav.nlm.nih.gov/REST/allconcepts.json"
HTTP_TIMEOUT = 60

INGREDIENT_POPULARITY = 0.55
BRAND_POPULARITY = 0.50

# Keep clean drug-like names: letters/space/hyphen/apostrophe/period only,
# 3..32 chars, at most 3 words. Drops IUPAC chemicals and combo/consumer junk.
_CLEAN_NAME = re.compile(r"^[A-Za-z][A-Za-z .'\-]{2,31}$")


def _is_clean(name: str) -> bool:
    """Returns whether a drug name is clean enough to surface in type-ahead.

    Args:
        name: A raw RxNorm concept name.

    Returns:
        True if the name looks like a real, displayable drug name.
    """
    stripped = name.strip()
    return bool(_CLEAN_NAME.match(stripped)) and len(stripped.split()) <= 3


def _fetch_names(tty: str) -> list[str]:
    """Fetches all RxNorm concept names of a given term type.

    Args:
        tty: RxNorm term type, e.g. "IN" (ingredient) or "BN" (brand name).

    Returns:
        The list of concept names returned by RxNav.
    """
    resp = requests.get(RXNAV_ALLCONCEPTS, params={"tty": tty}, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    group = resp.json().get("minConceptGroup", {})
    return [c["name"] for c in group.get("minConcept", [])]


def _import_tty(
    repo: ConceptRepo, tty: str, context: str, popularity: float
) -> dict:
    """Imports one RxNorm term type into the concept graph.

    Args:
        repo: The concept repository.
        tty: RxNorm term type to import.
        context: Headline-row context label for these nodes.
        popularity: Ranking weight for these nodes.

    Returns:
        Counts for fetched / kept / inserted.
    """
    names = _fetch_names(tty)
    kept = sorted({n.strip() for n in names if _is_clean(n)})
    inserted = 0
    for name in kept:
        name_lower = name.lower()
        was_new = repo.insert_if_absent(
            Concept(
                name=name,
                name_lower=name_lower,
                self_context=context,
                aliases=[name_lower],
                search_terms=[name_lower],
                edges={},
                source="rxnorm",
                popularity=popularity,
            )
        )
        if was_new:
            inserted += 1
    return {"fetched": len(names), "kept": len(kept), "inserted": inserted}


def main() -> None:
    """Parses CLI arguments and imports the requested RxNorm term types.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Import RxNorm drugs.")
    parser.add_argument(
        "--no-ingredients", action="store_true", help="Skip generic ingredients."
    )
    parser.add_argument(
        "--no-brands", action="store_true", help="Skip brand names."
    )
    args = parser.parse_args()

    repo = ConceptRepo()

    if not args.no_ingredients:
        stats = _import_tty(repo, "IN", "generic drug", INGREDIENT_POPULARITY)
        print(
            "ingredients: "
            f"fetched={stats['fetched']} kept={stats['kept']} "
            f"inserted={stats['inserted']} "
            f"(dropped {stats['fetched'] - stats['kept']} noisy names)"
        )

    if not args.no_brands:
        stats = _import_tty(repo, "BN", "brand drug", BRAND_POPULARITY)
        print(
            "brands:      "
            f"fetched={stats['fetched']} kept={stats['kept']} "
            f"inserted={stats['inserted']} "
            f"(dropped {stats['fetched'] - stats['kept']} noisy names)"
        )

    repo.ensure_indexes()
    print("indexes ensured.")


if __name__ == "__main__":
    main()
