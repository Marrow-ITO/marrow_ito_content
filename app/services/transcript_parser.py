"""Parse the `[mm:ss] text` transcript format and chunk for embedding.

Two functions:
  - parse_segments(raw)  -> list[{start_time, text}]
  - chunk_segments(segs) -> list[{start_time, end_time, text}]

Chunking targets ~CHUNK_SECONDS of speech OR ~CHUNK_WORDS words, whichever
limit hits first. This gives a granularity students can actually use
("jump to this point") without flooding the index with single-sentence
chunks.
"""

import re


# `[mm:ss]` or `[h:mm:ss]` or `[hh:mm:ss]` — leading bracket, optional hours.
_TIMESTAMP_RE = re.compile(
    r"\[\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*\]\s*(.*)"
)

CHUNK_SECONDS = 30
CHUNK_WORDS = 120


def parse_segments(raw: str) -> list[dict]:
    """Parse `[mm:ss] text` lines. Returns [{start_time: int, text: str}].

    Lines that don't match the timestamp pattern are appended to the
    previous segment's text (forgiving of multi-line cues).
    """
    if not raw:
        return []

    segments: list[dict] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _TIMESTAMP_RE.match(line)
        if m:
            h = int(m.group(1)) if m.group(1) else 0
            mm = int(m.group(2))
            ss = int(m.group(3))
            start = h * 3600 + mm * 60 + ss
            text = m.group(4).strip()
            segments.append({"start_time": start, "text": text})
        else:
            if segments:
                segments[-1]["text"] = (
                    segments[-1]["text"] + " " + line
                ).strip()
    return segments


def chunk_segments(segments: list[dict]) -> list[dict]:
    """Group adjacent segments into chunks. Returns
    [{start_time, end_time, text}].

    A chunk ends when accumulated duration >= CHUNK_SECONDS OR word count
    >= CHUNK_WORDS. The final chunk is always emitted even if smaller.

    end_time is the start_time of the next segment after the chunk
    (or chunk start + CHUNK_SECONDS for the last chunk in the transcript).
    """
    if not segments:
        return []

    chunks: list[dict] = []
    current: list[dict] = []
    current_start: int = segments[0]["start_time"]
    current_words: int = 0

    for i, seg in enumerate(segments):
        if not current:
            current_start = seg["start_time"]
            current_words = 0

        current.append(seg)
        current_words += len(seg["text"].split())

        next_start = (
            segments[i + 1]["start_time"]
            if i + 1 < len(segments)
            else seg["start_time"] + CHUNK_SECONDS
        )
        duration_so_far = next_start - current_start

        should_close = (
            duration_so_far >= CHUNK_SECONDS
            or current_words >= CHUNK_WORDS
            or i == len(segments) - 1
        )

        if should_close:
            kept = [s for s in current if s["text"]]
            chunk_text = " ".join(s["text"] for s in kept).strip()
            if chunk_text:
                chunks.append(
                    {
                        "start_time": current_start,
                        "end_time": next_start,
                        "text": chunk_text,
                        # Keep per-segment data so search can pinpoint the
                        # exact timestamp where matched content begins.
                        "segments": [
                            {"start_time": s["start_time"], "text": s["text"]}
                            for s in kept
                        ],
                    }
                )
            current = []

    return chunks


def format_mm_ss(seconds: int) -> str:
    if seconds >= 3600:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"
