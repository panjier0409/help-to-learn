"""
subtitle_parser.py
――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
Standalone subtitle parsing utilities.

Supports:
  - WebVTT (.vtt)  — including YouTube auto-generated VTT with inline timing tags
  - SubRip  (.srt) — including HTML-tagged variants

YouTube auto-generated VTT quirks handled:
  1. Inline timing tags (<c>, <00:00:00.000>) are stripped.
  2. Overlapping/duplicate cues are deduplicated:
     YouTube repeats the same line in consecutive cues (sliding-window
     style). We keep only the LAST cue for any given piece of text,
     which gives the most accurate start/end timestamps.

Public API
――――――――――――
  parse_vtt(text)                       -> list[Segment]
  parse_srt(text)                       -> list[Segment]
  parse_sub_file(path)                  -> list[Segment]
  merge_nearby_segments(segs, gap=0.5)  -> list[Segment]
  ts_to_seconds(ts)                     -> float

Segment = {"start": float, "end": float, "text": str}
"""
import re
import os
from typing import Optional


# ──────────────────────────────────────────────────────────────────
# Type alias
# ──────────────────────────────────────────────────────────────────

Segment = dict  # {"start": float, "end": float, "text": str}


# ──────────────────────────────────────────────────────────────────
# Timestamp conversion
# ──────────────────────────────────────────────────────────────────

def ts_to_seconds(ts: str) -> float:
    """
    Convert a subtitle timestamp to seconds (float).

    Accepted formats:
      HH:MM:SS.mmm   (VTT)
      HH:MM:SS,mmm   (SRT)
      MM:SS.mmm      (short VTT)
    """
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


# ──────────────────────────────────────────────────────────────────
# VTT parser
# ──────────────────────────────────────────────────────────────────

# Matches:  00:00:01.234 --> 00:00:04.567 align:start position:0%
_VTT_CUE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})"   # start ts
    r"\s-->\s"
    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})"   # end ts
    r"[^\n]*\n"                                                  # optional settings line
    r"([\s\S]*?)(?=\n\n|\Z)",                                    # cue text
    re.MULTILINE,
)

# Inline VTT tags: <c>, <i>, <b>, <00:00:00.000>, <c.colorname>, etc.
_VTT_TAG = re.compile(r"<[^>]+>")


def _clean_vtt_text(raw: str) -> str:
    """Strip inline tags, collapse whitespace."""
    text = _VTT_TAG.sub("", raw).strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _deduplicate_vtt(segments: list[Segment]) -> list[Segment]:
    """
    Remove YouTube-style duplicate/overlapping VTT cues.

    YouTube auto-generated VTT uses a sliding window: the same text appears
    in 2–3 consecutive cues with slightly different timestamps. Example:

        00:00:01.000 --> 00:00:03.000   "Hello and welcome"
        00:00:02.000 --> 00:00:04.000   "Hello and welcome to the show"
        00:00:03.500 --> 00:00:05.000   "welcome to the show"

    Strategy:
      - Group cues whose time windows overlap.
      - Within each overlapping group, keep only the LAST cue — it always
        has the complete text for that speech burst and the best end-timestamp.
      - After deduplication, if consecutive kept segments have identical or
        substring text, discard the shorter one.
    """
    if not segments:
        return []

    # Step 1: collapse overlapping cues (keep last in each group)
    result: list[Segment] = []
    i = 0
    while i < len(segments):
        j = i
        # Extend group while next cue starts before current group ends
        while j + 1 < len(segments) and segments[j + 1]["start"] < segments[j]["end"]:
            j += 1
        # Keep the last cue in the overlapping group
        result.append(dict(segments[j]))
        i = j + 1

    # Step 2: remove exact or substring duplicates between consecutive segments
    cleaned: list[Segment] = [result[0]]
    for seg in result[1:]:
        prev = cleaned[-1]
        t_prev = prev["text"].strip()
        t_cur  = seg["text"].strip()
        if t_cur == t_prev:
            # Exact duplicate — extend end time, skip
            prev["end"] = max(prev["end"], seg["end"])
        elif t_cur in t_prev:
            # Current is a suffix of previous — skip (previous is more complete)
            pass
        elif t_prev in t_cur:
            # Previous is a prefix of current — replace previous with current
            cleaned[-1] = dict(seg)
        else:
            cleaned.append(dict(seg))

    return cleaned


def parse_vtt(text: str) -> list[Segment]:
    """
    Parse WebVTT subtitle text.

    Handles:
      - Standard VTT cues
      - YouTube auto-generated VTT (inline timing tags + overlapping cues)
      - Cue identifiers (numeric or named lines before the timestamp)

    Returns a deduplicated, sorted list of Segment dicts.
    """
    segments: list[Segment] = []
    for m in _VTT_CUE.finditer(text):
        start = ts_to_seconds(m.group(1))
        end   = ts_to_seconds(m.group(2))
        clean = _clean_vtt_text(m.group(3))
        if clean and end > start:
            segments.append({"start": start, "end": end, "text": clean})

    # Sort ascending
    segments.sort(key=lambda s: s["start"])

    # Deduplicate YouTube-style overlapping cues
    segments = _deduplicate_vtt(segments)

    return segments


# ──────────────────────────────────────────────────────────────────
# SRT parser
# ──────────────────────────────────────────────────────────────────

_SRT_BLOCK = re.compile(
    r"\d+\r?\n"                                               # sequence number
    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"  # timestamps
    r"[^\n]*\r?\n"                                            # optional line settings
    r"([\s\S]*?)(?=\r?\n\r?\n|\Z)",                           # subtitle text
    re.MULTILINE,
)

_HTML_TAG = re.compile(r"<[^>]+>")


def parse_srt(text: str) -> list[Segment]:
    """
    Parse SubRip (.srt) subtitle text.

    Handles:
      - Standard SRT blocks
      - SRT with HTML tags (<i>, <b>, <font color=...>)
      - Windows-style CRLF line endings

    Returns list of Segment dicts sorted by start time.
    """
    text = text.replace("\r\n", "\n")

    segments: list[Segment] = []
    for m in _SRT_BLOCK.finditer(text):
        start = ts_to_seconds(m.group(1))
        end   = ts_to_seconds(m.group(2))
        raw   = m.group(3).strip()
        clean = _HTML_TAG.sub("", raw)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean and end > start:
            segments.append({"start": start, "end": end, "text": clean})

    segments.sort(key=lambda s: s["start"])
    return segments


# ──────────────────────────────────────────────────────────────────
# File dispatcher
# ──────────────────────────────────────────────────────────────────

def parse_sub_file(path: str) -> list[Segment]:
    """
    Read a .vtt or .srt file from disk and parse it.
    Encoding: UTF-8 with replacement for any invalid bytes.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    ext = os.path.splitext(path)[1].lower()
    if ext == ".vtt":
        return parse_vtt(text)
    if ext == ".srt":
        return parse_srt(text)
    raise ValueError(f"Unsupported subtitle extension: {ext}")


# ──────────────────────────────────────────────────────────────────
# Segment merging
# ──────────────────────────────────────────────────────────────────

def merge_nearby_segments(
    segments: list[Segment],
    gap_threshold: float = 0.5,
    max_duration: float = 15.0,
) -> list[Segment]:
    """
    Merge adjacent segments whose gap is smaller than *gap_threshold* seconds,
    up to a maximum total duration of *max_duration* seconds.

    Collapses caption-style subtitles (one word/phrase per cue) into more
    natural sentence-length chunks, producing fewer but longer audio clips.

    Args:
        segments      : Sorted list of Segment dicts.
        gap_threshold : Max gap (seconds) to still merge. Default 0.5 s.
        max_duration  : Max duration (seconds) of a single merged segment.
                        Prevents creating excessively long clips if there are
                        few gaps in the recording. Default 30.0 s.

    Returns a new list; original is not modified.
    """
    if not segments:
        return []

    merged = [dict(segments[0])]
    for seg in segments[1:]:
        prev = merged[-1]
        gap = seg["start"] - prev["end"]
        
        # Check if we should merge:
        # 1. Gap is small enough
        # 2. Resulting duration doesn't exceed limit
        if gap < gap_threshold and (seg["end"] - prev["start"]) <= max_duration:
            prev["end"] = seg["end"]
            prev["text"] = prev["text"].rstrip() + " " + seg["text"].lstrip()
        else:
            merged.append(dict(seg))

    return merged
