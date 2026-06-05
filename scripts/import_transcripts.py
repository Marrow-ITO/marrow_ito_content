"""Backfill video_transcript_raw from a folder of .srt files.

For every .srt in the given folder:
  1. Parse the SRT into (start_time_seconds, text) cues.
  2. Convert to the `[mm:ss] text` per-line format used by Video.video_transcript_raw.
  3. Match to a video in DB by filename stem (case-insensitive, whitespace
     collapsed) — `Foo - Subject.srt` <-> `Foo - Subject.mp3`.
  4. Update video_transcript_raw on the matched video.

Reports unmatched SRTs and videos that already had a transcript (which
will be overwritten — pass --no-overwrite to skip those).

Usage:
    uv run python scripts/import_transcripts.py ~/Downloads/Transcripts
"""

import argparse
import re
import sys
from pathlib import Path

# Make the project root importable so we can use the app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Collections, get_db  # noqa: E402


SRT_CUE_RE = re.compile(
    r"(?P<index>\d+)\s*\n"
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n"
    r"(?P<text>(?:.+\n?)*?)"
    r"(?=\n\d+\s*\n|\Z)",
    re.MULTILINE,
)


def srt_timestamp_to_seconds(ts: str) -> int:
    """SRT '00:01:23,456' -> 83 (integer seconds, ms dropped)."""
    ts = ts.replace(",", ".")
    h, m, rest = ts.split(":", 2)
    s = float(rest)
    return int(int(h) * 3600 + int(m) * 60 + s)


def format_mm_ss(seconds: int) -> str:
    if seconds >= 3600:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def srt_to_inline_transcript(srt_text: str) -> str:
    """Convert SRT into `[mm:ss] text` lines, one per cue."""
    lines: list[str] = []
    for match in SRT_CUE_RE.finditer(srt_text):
        start = srt_timestamp_to_seconds(match.group("start"))
        # Flatten multi-line cue text to a single space-joined line.
        text = match.group("text").strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        lines.append(f"[{format_mm_ss(start)}] {text}")
    return "\n".join(lines)


def normalise_stem(stem: str) -> str:
    """Lowercase + collapse whitespace for tolerant filename matching."""
    return re.sub(r"\s+", " ", stem.strip().lower())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill Video.video_transcript_raw from .srt files"
    )
    parser.add_argument(
        "src_dir", type=Path, help="Folder containing .srt files (one per video)"
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip videos that already have a transcript",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse + match but don't write to DB",
    )
    args = parser.parse_args()

    if not args.src_dir.exists() or not args.src_dir.is_dir():
        print(f"error: not a directory: {args.src_dir}", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    videos_coll = db[Collections.videos]

    # Build a lookup: normalised filename stem -> video doc
    videos_by_stem: dict[str, dict] = {}
    for v in videos_coll.find(
        {"file_name": {"$exists": True, "$ne": None}},
        {"file_name": 1, "title": 1, "video_transcript_raw": 1},
    ):
        stem = Path(v["file_name"]).stem
        videos_by_stem[normalise_stem(stem)] = v

    matched = 0
    unmatched: list[str] = []
    skipped_existing: list[str] = []
    empty_srts: list[str] = []

    srt_files = sorted(args.src_dir.glob("*.srt"))
    if not srt_files:
        print(f"error: no .srt files in {args.src_dir}", file=sys.stderr)
        sys.exit(1)

    for srt_path in srt_files:
        key = normalise_stem(srt_path.stem)
        video = videos_by_stem.get(key)
        if not video:
            unmatched.append(srt_path.name)
            continue

        raw = srt_path.read_text(encoding="utf-8", errors="replace")
        inline = srt_to_inline_transcript(raw)
        if not inline:
            empty_srts.append(srt_path.name)
            continue

        if args.no_overwrite and video.get("video_transcript_raw"):
            skipped_existing.append(srt_path.name)
            continue

        if not args.dry_run:
            videos_coll.update_one(
                {"_id": video["_id"]},
                {"$set": {"video_transcript_raw": inline}},
            )
        matched += 1

    print(("DRY RUN — " if args.dry_run else "") + "Backfill summary:")
    print(f"  .srt files scanned:         {len(srt_files)}")
    print(f"  matched + written:          {matched}")
    print(f"  unmatched (no video):       {len(unmatched)}")
    print(f"  skipped (existing):         {len(skipped_existing)}")
    print(f"  skipped (empty after parse):{len(empty_srts)}")

    if unmatched:
        print("\nUnmatched .srt files:")
        for name in unmatched:
            print(f"  {name}")
    if skipped_existing:
        print("\nSkipped (transcript already present):")
        for name in skipped_existing:
            print(f"  {name}")
    if empty_srts:
        print("\nSkipped (empty transcript):")
        for name in empty_srts:
            print(f"  {name}")


if __name__ == "__main__":
    main()
