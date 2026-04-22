"""
test_subtitle_parser.py
Run directly -- no pytest needed:

  uv run python tests/test_subtitle_parser.py

Each test prints the raw subtitle sample, parsed results, and merge results
so you can inspect the output format visually.

To test a real downloaded .vtt / .srt file, pass its path as an argument:
  uv run python tests/test_subtitle_parser.py path/to/file.en.vtt
"""
import json
import sys
import os

# Force UTF-8 stdout so Chinese characters display correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.subtitle_parser import (
    parse_vtt,
    parse_srt,
    parse_sub_file,
    merge_nearby_segments,
    ts_to_seconds,
)


# ------------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------------

def _dump(segs: list[dict], label: str = "") -> None:
    if label:
        print(f"\n  [{label}]  ({len(segs)} segments)")
    for s in segs:
        print(f"    {s['start']:8.3f}s -> {s['end']:8.3f}s  |  {s['text']!r}")


def _section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")


def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL]  {msg}")
    sys.exit(1)


# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

# 1. Standard VTT (YouTube manual captions style)
SAMPLE_VTT_STANDARD = """\
WEBVTT
Kind: captions
Language: en

00:00:01.234 --> 00:00:04.567
Hello, welcome to this lesson.

00:00:05.000 --> 00:00:08.200
Today we will learn about Python.

00:00:09.100 --> 00:00:12.000
Let's get started!
"""

# 2. YouTube auto-generated VTT (has inline timing tags per word)
SAMPLE_VTT_AUTO = """\
WEBVTT
Kind: captions
Language: en

00:00:00.080 --> 00:00:01.760 align:start position:0%
<00:00:00.080><c>hello</c>

00:00:01.760 --> 00:00:03.200 align:start position:0%
<00:00:01.760><c>welcome</c><00:00:02.080><c> to</c><00:00:02.320><c> the</c>

00:00:03.200 --> 00:00:05.440 align:start position:0%
<00:00:03.200><c>channel</c>

00:00:05.440 --> 00:00:07.200 align:start position:0%
<00:00:05.440><c>today</c><00:00:05.760><c> we</c><00:00:06.000><c> talk</c>

00:00:07.200 --> 00:00:09.600 align:start position:0%
<00:00:07.200><c>about</c><00:00:07.600><c> Python</c>
"""

# 3. Standard SRT
SAMPLE_SRT_STANDARD = """\
1
00:00:01,500 --> 00:00:04,000
This is the first subtitle.

2
00:00:05,000 --> 00:00:07,500
This is the second subtitle.

3
00:00:08,000 --> 00:00:10,200
And the third one.
"""

# 4. SRT with HTML tags (Netflix / some platforms)
SAMPLE_SRT_HTML = """\
1
00:00:01,000 --> 00:00:03,000
<i>This is italic text.</i>

2
00:00:03,500 --> 00:00:06,000
<b>Bold subtitle</b> with <font color="#00ff00">color</font>.

3
00:00:06,500 --> 00:00:09,000
Plain text here.
"""

# 5. Fragmented VTT (one word per cue) for merge testing
SAMPLE_VTT_FRAGMENTED = """\
WEBVTT

00:00:01.000 --> 00:00:02.000
The

00:00:02.100 --> 00:00:03.000
quick

00:00:03.100 --> 00:00:04.000
brown

00:00:05.000 --> 00:00:06.000
fox
"""

# 6. YouTube auto-generated VTT with overlapping/sliding-window cues
#    The SAME text appears in multiple consecutive cues with overlapping windows.
SAMPLE_VTT_OVERLAP = """\
WEBVTT

00:00:01.000 --> 00:00:04.000 align:start position:0%
Hello and welcome

00:00:02.500 --> 00:00:05.500 align:start position:0%
Hello and welcome to the show

00:00:04.500 --> 00:00:07.000 align:start position:0%
welcome to the show today

00:00:06.500 --> 00:00:09.000 align:start position:0%
today we will learn
"""

# 6. ts_to_seconds edge cases
TS_CASES = [
    ("00:00:01.234",  1.234),
    ("00:01:00.000",  60.0),
    ("01:00:00.000",  3600.0),
    ("01:30:45.500",  5445.5),
    ("00:00:01,234",  1.234),   # SRT comma separator
    ("01:30.500",     90.5),    # short MM:SS.mmm form
]


# ------------------------------------------------------------------
# Test functions
# ------------------------------------------------------------------

def test_ts_to_seconds():
    _section("ts_to_seconds -- timestamp conversion")
    all_ok = True
    for ts, expected in TS_CASES:
        got = ts_to_seconds(ts)
        ok = abs(got - expected) < 0.001
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {ts!r:28s}  ->  {got:.3f}s  (expected {expected:.3f}s)  {status}")
        if not ok:
            all_ok = False
    if not all_ok:
        _fail("ts_to_seconds mismatch")
    _ok("all timestamps correct")


def test_parse_vtt_standard():
    _section("parse_vtt -- standard VTT")
    print(f"\n  Input:\n{SAMPLE_VTT_STANDARD}")
    segs = parse_vtt(SAMPLE_VTT_STANDARD)
    _dump(segs, "Parsed")
    if len(segs) != 3:
        _fail(f"expected 3 segments, got {len(segs)}")
    if segs[0]["text"] != "Hello, welcome to this lesson.":
        _fail(f"text mismatch: {segs[0]['text']!r}")
    if abs(segs[0]["start"] - 1.234) > 0.001:
        _fail(f"start time mismatch: {segs[0]['start']}")
    _ok("count / timestamps / text all correct")


def test_parse_vtt_auto_generated():
    _section("parse_vtt -- YouTube auto-generated (inline timing tags)")
    print(f"\n  Input:\n{SAMPLE_VTT_AUTO}")
    segs = parse_vtt(SAMPLE_VTT_AUTO)
    _dump(segs, "Parsed (tags stripped)")

    for s in segs:
        if "<" in s["text"] or ">" in s["text"]:
            _fail(f"inline tag not cleaned: {s['text']!r}")
    _ok("inline tags stripped")

    merged = merge_nearby_segments(segs, gap_threshold=0.5)
    _dump(merged, f"Merged gap<0.5s ({len(segs)} -> {len(merged)})")
    _ok("merge done")


def test_parse_srt_standard():
    _section("parse_srt -- standard SRT")
    print(f"\n  Input:\n{SAMPLE_SRT_STANDARD}")
    segs = parse_srt(SAMPLE_SRT_STANDARD)
    _dump(segs, "Parsed")
    if len(segs) != 3:
        _fail(f"expected 3 segments, got {len(segs)}")
    if abs(segs[0]["start"] - 1.5) > 0.001:
        _fail(f"start time mismatch: {segs[0]['start']}")
    _ok("count / timestamps / text all correct")


def test_parse_srt_with_html():
    _section("parse_srt -- SRT with HTML tags")
    print(f"\n  Input:\n{SAMPLE_SRT_HTML}")
    segs = parse_srt(SAMPLE_SRT_HTML)
    _dump(segs, "Parsed (HTML stripped)")
    for s in segs:
        if "<" in s["text"]:
            _fail(f"HTML tag not cleaned: {s['text']!r}")
    if segs[0]["text"] != "This is italic text.":
        _fail(f"text[0] mismatch: {segs[0]['text']!r}")
    if segs[1]["text"] != "Bold subtitle with color.":
        _fail(f"text[1] mismatch: {segs[1]['text']!r}")
    _ok("HTML tags stripped, text correct")


def test_merge_nearby_segments():
    _section("merge_nearby_segments -- short-gap merging")
    print(f"\n  Input:\n{SAMPLE_VTT_FRAGMENTED}")
    segs = parse_vtt(SAMPLE_VTT_FRAGMENTED)
    _dump(segs, f"Original ({len(segs)} segments)")

    # The / quick / brown are <0.5s apart -> merged; fox is 1s later -> separate
    merged_05 = merge_nearby_segments(segs, gap_threshold=0.5)
    _dump(merged_05, f"Merged gap<0.5s ({len(merged_05)} segments)")
    if len(merged_05) != 2:
        _fail(f"expected 2 segments after merge, got {len(merged_05)}")
    if not ("The" in merged_05[0]["text"] and "quick" in merged_05[0]["text"] and "brown" in merged_05[0]["text"]):
        _fail(f"first merged segment wrong: {merged_05[0]['text']!r}")
    _ok("The/quick/brown merged; fox separate")

    # gap<2.0s -> everything merges into 1
    merged_20 = merge_nearby_segments(segs, gap_threshold=2.0)
    _dump(merged_20, f"Merged gap<2.0s ({len(merged_20)} segments)")
    if len(merged_20) != 1:
        _fail(f"expected 1 segment, got {len(merged_20)}")
    _ok("all merged into 1")

    # Test max_duration constraint
    # Everything has 0.1s gap. Total duration is 5s.
    # If max_duration=2.5s, it should split into 3 segments.
    merged_max = merge_nearby_segments(segs, gap_threshold=1.0, max_duration=2.5)
    _dump(merged_max, f"Merged gap<1.0s, max_dur=2.5s ({len(merged_max)} segments)")
    if len(merged_max) != 3:
         _fail(f"expected 3 segments with max_duration=2.5s, got {len(merged_max)}")
    for s in merged_max:
        dur = s["end"] - s["start"]
        if dur > 2.5:
            _fail(f"segment duration {dur} exceeds max_duration 2.5")
    _ok("max_duration limit respected")



def test_empty_inputs():
    _section("edge cases -- empty / minimal inputs")
    if parse_vtt("") != []:
        _fail("parse_vtt('') should return []")
    if parse_srt("") != []:
        _fail("parse_srt('') should return []")
    if merge_nearby_segments([]) != []:
        _fail("merge_nearby_segments([]) should return []")
    if parse_vtt("WEBVTT\n\n") != []:
        _fail("parse_vtt with no cues should return []")
    _ok("all empty inputs return []")


def test_real_file(path: str) -> None:
    """Parse a real downloaded subtitle file and show output."""
    _section(f"Real file: {path}")
    segs = parse_sub_file(path)
    _dump(segs, f"Raw ({len(segs)} segments)")

    merged = merge_nearby_segments(segs, gap_threshold=0.5)
    _dump(merged, f"Merged gap<0.5s ({len(merged)} segments)")

    print("\n  JSON preview (first 5 merged segments):")
    print(json.dumps(merged[:5], ensure_ascii=False, indent=4))


def test_vtt_deduplication():
    _section("parse_vtt -- YouTube overlapping/duplicate cue deduplication")
    print(f"\n  Input:\n{SAMPLE_VTT_OVERLAP}")
    segs = parse_vtt(SAMPLE_VTT_OVERLAP)
    _dump(segs, f"After dedup ({len(segs)} segments)")

    # The 4 overlapping cues should be collapsed to non-overlapping unique segments
    # No two consecutive segments should share a text substring
    for i in range(len(segs) - 1):
        a, b = segs[i]["text"], segs[i + 1]["text"]
        if a in b or b in a:
            _fail(f"Consecutive segments still overlap: {a!r} / {b!r}")
        if segs[i]["end"] > segs[i + 1]["start"]:
            _fail(f"Segments still overlap in time: {segs[i]} / {segs[i+1]}")

    print(f"\n  Result timestamps (no overlaps):")
    for s in segs:
        print(f"    {s['start']:.3f}s -> {s['end']:.3f}s  {s['text']!r}")
    _ok("overlapping cues deduplicated, timestamps non-overlapping")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    test_ts_to_seconds()
    test_parse_vtt_standard()
    test_parse_vtt_auto_generated()
    test_vtt_deduplication()
    test_parse_srt_standard()
    test_parse_srt_with_html()
    test_merge_nearby_segments()
    test_empty_inputs()

    # Optional: pass a real subtitle file path on the command line
    if len(sys.argv) > 1:
        test_real_file(sys.argv[1])

    print(f"\n{'=' * 62}")
    print("  All tests passed.")
    print(f"{'=' * 62}\n")
