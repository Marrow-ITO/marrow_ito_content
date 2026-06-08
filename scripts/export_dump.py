"""Export the local marrow_ito_search database to a single gzipped archive.

Runs on the LOCAL machine (where the data lives). Wraps `mongodump` to
produce one self-contained, gzip-compressed archive file that carries every
collection's documents AND indexes. Move that file to the remote machine
however you like (S3, scp, ...) and restore it with scripts/restore_dump.py.

This is the right shape for the "two machines, no shared network" case:
the local box can't reach Atlas and the remote box can't reach local Mongo,
so we ship a file in between.

Note: the FAISS vector indexes are NOT in Mongo — rebuild them on the remote
after restoring with the scripts/build_*_index.py scripts.

Requires the MongoDB Database Tools (`mongodump`) on PATH:
    brew install mongodb-database-tools

Usage:
    uv run python scripts/export_dump.py
    uv run python scripts/export_dump.py --out /tmp/marrow_ito_search.archive.gz
    uv run python scripts/export_dump.py --collections concepts videos
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Make the project root importable so we can reuse the app config.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402


def main() -> None:
    """Parses CLI arguments and runs mongodump into a gzip archive."""
    parser = argparse.ArgumentParser(description="Dump local Mongo DB -> gzip archive.")
    parser.add_argument("--source-uri", default=settings.mongo_uri, help="Source Mongo URI.")
    parser.add_argument("--db", default=settings.mongo_db, help="Database to dump.")
    parser.add_argument(
        "--out", default=None,
        help="Output archive path (default: ./dumps/<db>.archive.gz).",
    )
    parser.add_argument(
        "--collection", default=None,
        help="Dump a single collection (default: the whole database).",
    )
    args = parser.parse_args()

    if shutil.which("mongodump") is None:
        print("error: mongodump not found on PATH. Install MongoDB Database Tools:\n"
              "  brew install mongodb-database-tools", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out) if args.out else Path("dumps") / f"{args.db}.archive.gz"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "mongodump",
        f"--uri={args.source_uri}",
        f"--db={args.db}",
        "--gzip",
        f"--archive={out_path}",
    ]
    if args.collection:
        cmd.append(f"--collection={args.collection}")

    print(f"source : {args.source_uri} / {args.db}")
    print(f"archive: {out_path}")
    print(f"running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nexport FAILED — see mongodump output above.", file=sys.stderr)
        sys.exit(result.returncode)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\nDONE · wrote {out_path} ({size_mb:.1f} MB)")
    print("Next: move this file to the remote machine (S3/scp), then run:")
    print(f"  ATLAS_URI='...' uv run python scripts/restore_dump.py --archive {out_path.name}")


if __name__ == "__main__":
    main()
