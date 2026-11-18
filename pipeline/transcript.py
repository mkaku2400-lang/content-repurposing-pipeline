"""Load transcripts from uploaded .txt and .srt files."""

from __future__ import annotations

import re
from pathlib import Path

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "podcast_transcript.txt"

# An SRT timing line: 00:01:15,000 --> 00:01:18,500
_SRT_TIMING = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.]\d{1,3}\s*-->")
_SRT_TAG = re.compile(r"</?[a-zA-Z][^>]*>|\{\\[^}]*\}")
# Subtitles arrive a few words at a time; one timestamped paragraph per this many seconds reads better.
_PARAGRAPH_SECONDS = 30


class TranscriptError(Exception):
    """A problem with an uploaded file, with a message safe to show the user."""


def load_sample() -> str:
    return SAMPLE_PATH.read_text(encoding="utf-8")


def _stamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"[{hours}:{minutes:02d}:{secs:02d}]" if hours else f"[{minutes:02d}:{secs:02d}]"


def srt_to_transcript(srt_text: str) -> str:
    """Convert subtitles to readable paragraphs that keep a timestamp roughly every 30 seconds."""
    paragraphs: list[str] = []
    current: list[str] = []
    paragraph_start = None

    for block in re.split(r"\n\s*\n", srt_text.replace("\r", "").strip()):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if _SRT_TIMING.search(line)), None)
        if timing_index is None:
            continue
        hours, minutes, seconds = map(int, _SRT_TIMING.search(lines[timing_index]).groups())
        start = hours * 3600 + minutes * 60 + seconds
        text = _SRT_TAG.sub("", " ".join(lines[timing_index + 1 :])).strip()
        if not text:
            continue
        if paragraph_start is None:
            paragraph_start = start
        elif start - paragraph_start >= _PARAGRAPH_SECONDS:
            paragraphs.append(f"{_stamp(paragraph_start)} {' '.join(current)}")
            current, paragraph_start = [], start
        current.append(text)

    if current:
        paragraphs.append(f"{_stamp(paragraph_start)} {' '.join(current)}")
    return "\n\n".join(paragraphs)


def read_upload(filename: str, data: bytes) -> str:
    """Return the transcript text of an uploaded .txt or .srt file."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")

    if filename.lower().endswith(".srt"):
        text = srt_to_transcript(text)
        if not text:
            raise TranscriptError("No subtitles were found in this .srt file.")
    if not text.strip():
        raise TranscriptError("This file is empty.")
    return text.strip()
