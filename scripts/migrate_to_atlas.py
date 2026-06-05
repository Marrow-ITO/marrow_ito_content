"""Migrate every collection (data + indexes) from local Mongo to Atlas.

Copies all collections in the marrow_ito_search database from the local
source to an Atlas cluster, including indexes. By default each target
collection is dropped first so the result is an exact mirror; use --no-drop
to upsert instead (idempotent, keyed on _id).

The Atlas connection string is NEVER hard-coded — pass it via --target-uri
or the ATLAS_URI environment variable.

Atlas SRV URIs (mongodb+srv://...) need dnspython:
    uv add "pymongo[srv]"      # or: uv add dnspython

Usage:
    export ATLAS_URI='mongodb+srv://user:pass@cluster0.xid9pie.mongodb.net/?appName=Cluster0'
    uv run python scripts/migrate_to_atlas.py --dry-run      # preview
    uv run python scripts/migrate_to_atlas.py                # migrate (drop+copy)
    uv run python scripts/migrate_to_atlas.py --no-drop      # upsert instead
    uv run python scripts/migrate_to_atlas.py --collections concepts videos
"""

import argparse
import os
import sys
from pathlib import Path

# Make the project root importable so we can reuse the app config.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient, ReplaceOne  # noqa: E402
from pymongo.database import Database  # noqa: E402

from app.config import settings  # noqa: E402

BATCH_SIZE = 500
# Index option keys worth carrying over to the target.
_INDEX_OPTS = (
    "unique", "sparse", "expireAfterSeconds",
    "partialFilterExpression", "collation", "weights", "default_language",
)


def _copy_indexes(src_coll, dst_coll) -> int:
    """Recreates the source collection's indexes on the target.

    Args:
        src_coll: Source collection.
        dst_coll: Target collection.

    Returns:
        The number of indexes created (excluding the default _id index).
    """
    created = 0
    for name, spec in src_coll.index_information().items():
        if name == "_id_":
            continue
        keys = spec["key"]  # list of (field, direction) tuples
        opts = {k: spec[k] for k in _INDEX_OPTS if k in spec}
        try:
            dst_coll.create_index(keys, name=name, **opts)
            created += 1
        except Exception as exc:  # noqa: BLE001 — report and continue.
            print(f"      ! index {name!r} skipped: {type(exc).__name__}: {str(exc)[:80]}")
    return created


def _migrate_collection(
    src_db: Database, dst_db: Database, name: str, drop: bool, batch: int
) -> dict:
    """Copies one collection's documents and indexes to the target.

    Args:
        src_db: Source database.
        dst_db: Target database.
        name: Collection name.
        drop: When True, drop the target collection then bulk-insert; else upsert.
        batch: Write batch size.

    Returns:
        A stats dict: source/copied/target counts and index count.
    """
    src_coll = src_db[name]
    dst_coll = dst_db[name]
    source_count = src_coll.count_documents({})

    if drop:
        dst_coll.drop()

    copied = 0
    buffer: list = []

    def flush() -> None:
        nonlocal copied, buffer
        if not buffer:
            return
        if drop:
            dst_coll.insert_many(buffer, ordered=False)
        else:
            dst_coll.bulk_write(
                [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in buffer],
                ordered=False,
            )
        copied += len(buffer)
        buffer = []

    for doc in src_coll.find({}):
        buffer.append(doc)
        if len(buffer) >= batch:
            flush()
    flush()

    indexes = _copy_indexes(src_coll, dst_coll)
    return {
        "source": source_count,
        "copied": copied,
        "target": dst_coll.count_documents({}),
        "indexes": indexes,
    }


def main() -> None:
    """Parses CLI arguments and runs the migration.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Migrate local Mongo -> Atlas.")
    parser.add_argument(
        "--target-uri", default=os.getenv("ATLAS_URI"),
        help="Atlas connection string (or set ATLAS_URI env var).",
    )
    parser.add_argument("--source-uri", default=settings.mongo_uri)
    parser.add_argument("--db", default=settings.mongo_db, help="Source DB name.")
    parser.add_argument("--target-db", default=None, help="Target DB (default: same as --db).")
    parser.add_argument("--collections", nargs="*", help="Subset to migrate (default: all).")
    parser.add_argument("--no-drop", action="store_true", help="Upsert instead of drop+insert.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="List collections + counts, copy nothing.")
    args = parser.parse_args()

    if not args.target_uri and not args.dry_run:
        print("error: provide the Atlas URI via --target-uri or ATLAS_URI.", file=sys.stderr)
        sys.exit(1)

    target_db_name = args.target_db or args.db
    drop = not args.no_drop

    src_client = MongoClient(args.source_uri, serverSelectionTimeoutMS=5000)
    src_db = src_client[args.db]
    src_client.admin.command("ping")

    names = args.collections or sorted(
        c for c in src_db.list_collection_names() if not c.startswith("system.")
    )
    print(f"source: {args.source_uri} / {args.db}")
    print(f"collections ({len(names)}): {', '.join(names)}")

    if args.dry_run:
        print("\n--dry-run — counts only:")
        for name in names:
            print(f"  {name:<22} {src_db[name].count_documents({}):>8} docs")
        return

    dst_client = MongoClient(args.target_uri, serverSelectionTimeoutMS=15000)
    dst_db = dst_client[target_db_name]
    dst_client.admin.command("ping")
    print(f"target: {target_db_name} on Atlas  (mode: {'drop+insert' if drop else 'upsert'})\n")

    grand = {"source": 0, "copied": 0, "target": 0}
    for name in names:
        print(f"  → {name} ...", end=" ", flush=True)
        s = _migrate_collection(src_db, dst_db, name, drop=drop, batch=args.batch_size)
        for k in grand:
            grand[k] += s[k]
        ok = "OK" if s["target"] >= s["source"] else "MISMATCH!"
        print(f"{s['copied']} copied · target now {s['target']}/{s['source']} · "
              f"{s['indexes']} indexes  [{ok}]")

    print(f"\nDONE · {grand['copied']} docs copied across {len(names)} collections "
          f"(source {grand['source']} → target {grand['target']})")


if __name__ == "__main__":
    main()
