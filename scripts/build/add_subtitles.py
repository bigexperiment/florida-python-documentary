#!/usr/bin/env python3
"""Burn styled subtitles synced to whisper timings + canonical transcript text."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_paths import (  # noqa: E402
    NARRATION_MP3 as DEFAULT_NARRATION,
    NARRATION_WHISPER as WHISPER_JSON,
    OUTPUT_DIR,
    SUBTITLES,
    TRANSCRIPT as DEFAULT_TRANSCRIPT,
    TRANSCRIPTS,
)

DEFAULT_VIDEO = OUTPUT_DIR / "final_documentary.mp4"
MAX_LINE = 44


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def normalize(text: str) -> str:
    text = text.lower().replace("—", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t]


def format_ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_ts_bracket(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def load_whisper_segments() -> list[dict]:
    data = json.loads(WHISPER_JSON.read_text(encoding="utf-8"))
    return [
        {
            "start": item["offsets"]["from"] / 1000.0,
            "end": item["offsets"]["to"] / 1000.0,
            "text": item["text"].strip(),
            "words": tokenize(item["text"]),
        }
        for item in data["transcription"]
    ]


def load_transcript_words(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8").strip()
    return [w for w, _, _ in build_word_spans(raw)]


def build_word_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[A-Za-z0-9']+", text):
        norm = normalize(match.group(0))
        if norm:
            spans.append((norm, match.start(), match.end()))
    return spans


def extract_transcript_text(spans: list[tuple[str, int, int]], raw: str, indices: list[int]) -> str:
    if not indices:
        return ""
    ordered = sorted(set(indices))
    parts: list[str] = []
    cursor = -1
    for idx in ordered:
        if idx >= len(spans):
            continue
        _, start, end = spans[idx]
        if cursor != -1 and start > cursor:
            gap = raw[cursor:start].strip()
            if gap:
                parts.append(gap)
        parts.append(raw[start:end])
        cursor = end
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def clean_subtitle_text(text: str) -> str:
    text = re.sub(r"\s+-\s+", "-", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\s+\.", ".", text)
    text = re.sub(r"\s+—\s+", " — ", text)
    text = re.sub(r"\s+'", "'", text)
    return re.sub(r"\s+", " ", text).strip()


def align_transcript_to_whisper(
    transcript_words: list[str],
    whisper_segments: list[dict],
    transcript_raw: str,
    word_spans: list[tuple[str, int, int]],
) -> list[tuple[float, float, str]]:
    whisper_words: list[str] = []
    seg_ranges: list[tuple[int, int]] = []
    cursor = 0
    for seg in whisper_segments:
        count = len(seg["words"])
        seg_ranges.append((cursor, cursor + count))
        whisper_words.extend(seg["words"])
        cursor += count

    matcher = difflib.SequenceMatcher(None, whisper_words, transcript_words, autojunk=False)
    whisper_to_transcript: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                whisper_to_transcript[i1 + offset] = j1 + offset
        elif tag == "replace":
            span = min(i2 - i1, j2 - j1)
            for offset in range(span):
                whisper_to_transcript[i1 + offset] = j1 + offset

    cues: list[tuple[float, float, str]] = []
    t_cursor = 0
    for seg, (w0, w1) in zip(whisper_segments, seg_ranges):
        mapped: list[int] = []
        for wi in range(w0, w1):
            if wi in whisper_to_transcript:
                mapped.append(whisper_to_transcript[wi])
                t_cursor = whisper_to_transcript[wi] + 1
            elif t_cursor < len(transcript_words):
                mapped.append(t_cursor)
                t_cursor += 1
        if mapped and mapped[-1] + 1 < len(transcript_words):
            if transcript_words[mapped[-1] + 1] == "percent" and transcript_words[mapped[-1]].isdigit():
                mapped.append(mapped[-1] + 1)
                t_cursor = mapped[-1] + 1
        if mapped:
            text = extract_transcript_text(word_spans, transcript_raw, mapped)
        else:
            text = seg["text"]
        cues.append((seg["start"], seg["end"], wrap_subtitle(clean_subtitle_text(text))))

    return cues


def wrap_subtitle(text: str) -> str:
    words = text.split()
    if not words:
        return ""
    line1: list[str] = []
    idx = 0
    while idx < len(words):
        candidate = " ".join(line1 + [words[idx]])
        if len(candidate) <= MAX_LINE or not line1:
            line1.append(words[idx])
            idx += 1
        else:
            break
    if idx >= len(words):
        return " ".join(line1)
    line2 = " ".join(words[idx:])
    return f"{' '.join(line1)}\n{line2}"


def write_srt(cues: list[tuple[float, float, str]], path: Path) -> None:
    lines: list[str] = []
    for i, (start, end, text) in enumerate(cues, 1):
        lines.extend([str(i), f"{format_ts(start)} --> {format_ts(end)}", text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_timestamped_transcript(
    cues: list[tuple[float, float, str]], path: Path
) -> None:
    lines = [
        f"[{format_ts_bracket(start)} --> {format_ts_bracket(end)}] {text.replace(chr(10), ' ')}"
        for start, end, text in cues
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_cues(
    cues: list[tuple[float, float, str]],
    transcript_words: list[str],
    audio_duration: float,
) -> None:
    cue_words = tokenize(" ".join(t.replace("\n", " ") for _, _, t in cues))
    ratio = difflib.SequenceMatcher(None, cue_words, transcript_words, autojunk=False).ratio()
    gaps = []
    overlaps = []
    for i in range(len(cues) - 1):
        if cues[i][1] > cues[i + 1][0] + 0.001:
            overlaps.append(i + 1)
        if cues[i + 1][0] - cues[i][1] > 0.05:
            gaps.append(i + 1)

    print(f"Transcript coverage ratio: {ratio:.4f}")
    print(f"Cues: {len(cues)} | First: {cues[0][0]:.3f}s | Last end: {cues[-1][1]:.3f}s | Audio: {audio_duration:.3f}s")
    if overlaps:
        print(f"WARNING: {len(overlaps)} overlapping cue boundaries")
    if gaps:
        print(f"Note: {len(gaps)} small gaps between cues")
    if ratio < 0.98:
        raise SystemExit(f"Transcript alignment too low ({ratio:.4f}); aborting burn-in.")
    if abs(cues[-1][1] - audio_duration) > 0.15:
        print(f"WARNING: last cue ends {cues[-1][1] - audio_duration:+.3f}s from audio end")


def find_ffmpeg() -> str:
    for candidate in (
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "ffmpeg",
    ):
        try:
            subprocess.run([candidate, "-version"], capture_output=True, check=True)
            return candidate
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("ffmpeg not found")


def burn_subtitles(video: Path, srt: Path, output: Path) -> None:
    ffmpeg = find_ffmpeg()
    style = (
        "FontName=Helvetica Neue,FontSize=26,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&HC0000000,Bold=1,"
        "BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV=48"
    )
    vf = f"subtitles={srt.resolve()}:force_style='{style}'"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Add whisper-synced styled subtitles")
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--narration", type=Path, default=DEFAULT_NARRATION)
    parser.add_argument("--transcript", type=Path, default=DEFAULT_TRANSCRIPT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "final_documentary_subtitled.mp4")
    parser.add_argument("--srt", type=Path, default=SUBTITLES / "final_documentary.srt")
    parser.add_argument(
        "--timestamped",
        type=Path,
        default=TRANSCRIPTS / "final_documentary_timestamped_transcript.txt",
    )
    args = parser.parse_args()

    for path in (args.video, args.narration, args.transcript, WHISPER_JSON):
        if not path.is_file():
            print(f"Missing file: {path}", file=sys.stderr)
            return 1

    transcript_raw = args.transcript.read_text(encoding="utf-8").strip()
    word_spans = build_word_spans(transcript_raw)
    transcript_words = [w for w, _, _ in word_spans]
    whisper_segments = load_whisper_segments()
    audio_duration = probe_duration(args.narration)

    cues = align_transcript_to_whisper(
        transcript_words, whisper_segments, transcript_raw, word_spans
    )
    verify_cues(cues, transcript_words, audio_duration)

    write_srt(cues, args.srt)
    write_timestamped_transcript(cues, args.timestamped)
    print(f"Wrote {len(cues)} cues -> {args.srt}")
    print(f"Timestamped transcript -> {args.timestamped}")

    print(f"Burning subtitles into {args.output} ...")
    burn_subtitles(args.video, args.srt, args.output)
    print(f"Done: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
