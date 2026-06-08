"""Restore a gzipped archive (from export_dump.py) into an Atlas cluster.

Runs on the REMOTE machine (the only box that can reach Atlas). Wraps
`mongorestore` to load the archive produced by scripts/export_dump.py
DIRECTLY into Atlas — no intermediate local Mongo is needed. Documents and
indexes both come back.

The Atlas connection string is NEVER hard-coded — pass it via --target-uri
or the ATLAS_URI environment variable. Atlas SRV URIs (mongodb+srv://...)
work as-is with mongorestore.

By default each collection in the archive is dropped on the target before
restore, so the result is an exact mirror; use --no-drop to merge instead.

Reminder: the FAISS vector indexes are not in this archive. After a clean
restore, rebuild them on the remote with scripts/build_*_index.py.

Requires the MongoDB Database Tools (`mongorestore`) on PATH:
    # Debian/Ubuntu: install the mongodb-database-tools package
    # macOS:         brew install mongodb-database-tools

Usage:
    export ATLAS_URI='mongodb+srv://user:pass@cluster0.xxxx.mongodb.net/?appName=Cluster0'
    uv run python scripts/restore_dump.py --archive dumps/marrow_ito_search.archive.gz
    uv run python scripts/restore_dump.py --archive <file> --no-drop      # merge
    uv run python scripts/restore_dump.py --archive <file> --target-db staging_search
    uv run python scripts/restore_dump.py --archive <file> --dry-run      # preview
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Make the project root importable so we can reuse the app config.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402


def main() -> None:
    """Parses CLI arguments and runs mongorestore from a gzip archive into Atlas."""
    parser = argparse.ArgumentParser(description="Restore gzip archive -> Atlas.")
    parser.add_argument(
        "--target-uri", default=os.getenv("ATLAS_URI"),
        help="Atlas connection string (or set ATLAS_URI env var).",
    )
    parser.add_argument("--archive", required=True, help="Path to the .archive.gz file.")
    parser.add_argument(
        "--source-db", default=settings.mongo_db,
        help="DB name baked into the archive (default: %(default)s).",
    )
    parser.add_argument(
        "--target-db", default=None,
        help="DB name to restore INTO on Atlas (default: same as --source-db).",
    )
    parser.add_argument(
        "--no-drop", action="store_true",
        help="Merge into existing data instead of dropping each collection first.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Let mongorestore scan the archive and report, writing nothing.",
    )
    args = parser.parse_args()

    if shutil.which("mongorestore") is None:
        print("error: mongorestore not found on PATH. Install MongoDB Database Tools.",
              file=sys.stderr)
        sys.exit(1)

    if not args.target_uri:
        print("error: provide the Atlas URI via --target-uri or ATLAS_URI.", file=sys.stderr)
        sys.exit(1)

    archive = Path(args.archive)
    if not archive.is_file():
        print(f"error: archive not found: {archive}", file=sys.stderr)
        sys.exit(1)

    target_db = args.target_db or args.source_db

    cmd = [
        "mongorestore",
        f"--uri={args.target_uri}",
        "--gzip",
        f"--archive={archive}",
        # Only touch the namespace we shipped, even if the archive holds more.
        f"--nsInclude={args.source_db}.*",
    ]
    if target_db != args.source_db:
        # Remap the namespace so a DB renamed on Atlas still lands correctly.
        cmd.append(f"--nsFrom={args.source_db}.*")
        cmd.append(f"--nsTo={target_db}.*")
    if not args.no_drop:
        cmd.append("--drop")
    if args.dry_run:
        cmd.append("--dryRun")

    size_mb = archive.stat().st_size / (1024 * 1024)
    mode = "merge (--no-drop)" if args.no_drop else "drop + restore"
    print(f"archive: {archive} ({size_mb:.1f} MB)")
    print(f"target : {target_db} on Atlas  (mode: {mode}{', DRY RUN' if args.dry_run else ''})")
    # Avoid printing the URI — it contains credentials.
    print(f"running: mongorestore --gzip --archive={archive} --nsInclude={args.source_db}.* "
          f"{'--drop ' if not args.no_drop else ''}{'--dryRun ' if args.dry_run else ''}[uri hidden]\n")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\nrestore FAILED — see mongorestore output above.", file=sys.stderr)
        sys.exit(result.returncode)

    print(f"\nDONE · restored into {target_db} on Atlas.")
    if not args.dry_run:
        print("Next: rebuild the FAISS indexes on this machine:")
        print("  uv run python scripts/build_search_index.py")
        print("  uv run python scripts/build_transcript_index.py")
        print("  uv run python scripts/build_notes_index.py")
        print("  uv run python scripts/build_recent_updates_index.py")


if __name__ == "__main__":
    main()
