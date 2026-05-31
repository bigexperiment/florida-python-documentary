#!/usr/bin/env python3
"""Build final_documentary_2.mp4: fast cuts, whisper-synced, no repeated frames."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_paths import (  # noqa: E402
    BROLL,
    MAIN,
    MAIN_VIDEO,
    NARRATION_MP3 as NARRATION,
    OUTPUT_DIR,
    PLANS,
    TRANSCRIPT,
    NARRATION_WHISPER as WHISPER_JSON,
)

OUTPUT = OUTPUT_DIR / "final_documentary_2.mp4"
PLAN_OUT = PLANS / "final_documentary_2_plan.json"

MIN_SHOT = 3.0
MAX_SHOT = 5.0
SECTION_XFADE = 0.45
TRANSITIONS = ["fade", "dissolve", "smoothleft", "smoothright", "fadeblack"]


@dataclass
class Shot:
    path: Path
    src_start: float
    duration: float
    label: str


@dataclass
class Section:
    index: int
    start: float
    end: float
    title: str
    broll: list[str] = field(default_factory=list)
    main_hints: list[float] = field(default_factory=list)


SECTION_DEFS = [
    Section(1, 0, 0, "Everglades opener", ["into.mp4"], [5, 18, 32]),
    Section(
        2,
        0,
        0,
        "Exotic pet trade",
        ["Python_moving_in_swamp_water_202605222056.mp4"],
        [42, 55, 68, 82],
    ),
    Section(
        3,
        0,
        0,
        "Hurricane Andrew",
        ["Hurricane_destroys_reptile_facility_202605222058.mp4"],
        [64, 78, 92, 108],
    ),
    Section(
        4,
        0,
        0,
        "Ecosystem collapse",
        ["Pythons_in_Everglades_landscape_202605222112.mp4"],
        [118, 132, 145, 158, 172],
    ),
    Section(
        5,
        0,
        0,
        "Alligator predation",
        [
            "Python_hunting_alligator_in_Ever*.mp4",
            "Python_swallowing_alligator_dawn_202605222100.mp4",
            "Python_swallowing_alligator_dawn_202605222103.mp4",
        ],
        [185, 198],
    ),
    Section(
        6,
        0,
        0,
        "Scout snake program",
        ["Officers_capture_python_in_swamp_202605222033.mp4"],
        [228, 242, 255],
    ),
    Section(
        7,
        0,
        0,
        "Hand capture",
        ["Officers_capture_large_python_202605222105.mp4"],
        [198, 212, 268, 282],
    ),
    Section(
        8,
        0,
        0,
        "Python Challenge",
        ["Python_Challenge_hunters_capture*.mp4"],
        [180, 205, 220, 295],
    ),
    Section(
        9,
        0,
        0,
        "Thermal / eDNA tech",
        ["Python_hunting_with_thermal_cameras_202605222109.mp4"],
        [248, 262, 276, 290, 305],
    ),
    Section(
        10,
        0,
        0,
        "Hybrid expansion",
        ["Hybrid_python_spreads_across_Flo*.mp4"],
        [310, 325, 338, 352],
    ),
    Section(
        11,
        0,
        0,
        "Conclusion",
        [],
        [330, 345, 358, 365],
    ),
]

ANCHORS = [
    "The Florida Everglades",
    "In the 1980s",
    "Then in August of 1992",
    "These snakes have no natural predators",
    "But the pythons didn't stop",
    "In response, scientists launched",
    "At night, wildlife officers",
    "Florida has also mobilized",
    "The state has pivoted to technology",
    "But now, genetic testing",
    "Total eradication is no longer",
]


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


def find_clip(pattern: str) -> Path:
    folder = BROLL if not pattern.startswith("main:") else MAIN
    name = pattern.replace("main:", "")
    if "*" not in name:
        path = folder / name
        if path.is_file():
            return path
    matches = sorted(folder.glob(name))
    if not matches:
        raise FileNotFoundError(f"No clip matching {pattern}")
    return matches[0]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_whisper_segments() -> list[dict]:
    data = json.loads(WHISPER_JSON.read_text(encoding="utf-8"))
    segments = []
    for item in data["transcription"]:
        segments.append(
            {
                "start": item["offsets"]["from"] / 1000.0,
                "end": item["offsets"]["to"] / 1000.0,
                "text": item["text"].strip(),
            }
        )
    return segments


def whisper_full_text(segments: list[dict]) -> str:
    return normalize(" ".join(s["text"] for s in segments))


def char_time_map(segments: list[dict]) -> tuple[str, list[tuple[int, float]]]:
    chars: list[str] = []
    index: list[tuple[int, float]] = []
    pos = 0
    for seg in segments:
        chunk = normalize(seg["text"])
        if not chunk:
            continue
        if chars:
            chars.append(" ")
            pos += 1
        for ch in chunk:
            chars.append(ch)
            index.append((pos, seg["start"]))
            pos += 1
    return "".join(chars), index


def time_at_char(index: list[tuple[int, float]], char_pos: int, segments: list[dict], end: bool) -> float:
    if not index:
        return 0.0
    for i, (pos, start) in enumerate(index):
        if pos >= char_pos:
            return segments[min(i, len(segments) - 1)]["end" if end else "start"]
    return segments[-1]["end" if end else "start"]


def align_sections(paragraphs: list[str], segments: list[dict]) -> list[Section]:
    para_words = [max(len(normalize(p).split()), 1) for p in paragraphs]
    assignments: list[int] = []
    para_idx = 0
    words_seen = 0
    target = para_words[0]

    for seg in segments:
        w = max(len(normalize(seg["text"]).split()), 1)
        assignments.append(para_idx)
        words_seen += w
        if para_idx < len(paragraphs) - 1 and words_seen >= target:
            para_idx += 1
            target += para_words[para_idx]

    aligned: list[Section] = []
    for i in range(len(paragraphs)):
        seg_group = [segments[j] for j, a in enumerate(assignments) if a == i]
        if not seg_group:
            raise ValueError(f"No whisper segments mapped to section {i + 1}")
        section = SECTION_DEFS[i]
        section.start = seg_group[0]["start"]
        section.end = seg_group[-1]["end"]
        aligned.append(section)

    aligned[-1].end = segments[-1]["end"]
    return aligned


class UsageTracker:
    def __init__(self) -> None:
        self.broll_used: set[str] = set()
        self.main_used: list[tuple[float, float]] = []
        self.main_cursor = 0.0

    def claim_broll(self, path: Path, src_start: float, duration: float) -> None:
        if path.name in self.broll_used:
            raise ValueError(f"B-roll reused: {path.name}")
        if src_start > 0.01:
            raise ValueError(f"B-roll partial reuse not allowed: {path.name}")
        clip_len = probe_duration(path)
        if duration > clip_len + 0.05:
            raise ValueError(f"B-roll overused: {path.name}")
        self.broll_used.add(path.name)

    def _main_free(self, start: float, duration: float) -> bool:
        end = start + duration
        for used_start, used_end in self.main_used:
            if not (end <= used_start + 0.05 or start >= used_end - 0.05):
                return False
        return True

    def claim_main(self, preferred: float | None, duration: float, main_duration: float) -> float:
        candidates: list[float] = []
        if preferred is not None:
            candidates.append(preferred)
        candidates.append(self.main_cursor)

        t = 0.0
        while t <= max(0.0, main_duration - duration):
            candidates.append(t)
            t += 0.35

        seen: set[float] = set()
        for raw in candidates:
            start = round(max(0.0, min(raw, main_duration - duration)), 2)
            if start in seen:
                continue
            seen.add(start)
            if self._main_free(start, duration):
                end = start + duration
                self.main_used.append((start, end))
                self.main_cursor = min(main_duration, end + 0.15)
                return start
        raise ValueError("Ran out of unique main-video frames")


def split_shot_durations(total: float) -> list[float]:
    parts: list[float] = []
    remaining = total
    while remaining > 0.08:
        if remaining <= MAX_SHOT:
            parts.append(remaining)
            break
        parts.append(min(MAX_SHOT, max(MIN_SHOT, remaining / 2)))
        remaining -= parts[-1]
    if parts:
        drift = total - sum(parts)
        parts[-1] += drift
    return parts


def build_section_shots(section: Section, tracker: UsageTracker, main_duration: float) -> list[Shot]:
    duration = section.end - section.start
    durations = split_shot_durations(duration)
    shots: list[Shot] = []
    broll_queue = [find_clip(p) for p in section.broll]
    hints = list(section.main_hints)
    hint_idx = 0

    for target in durations:
        remaining = target
        if broll_queue:
            path = broll_queue.pop(0)
            clip_len = probe_duration(path)
            use = min(remaining, clip_len)
            tracker.claim_broll(path, 0.0, use)
            shots.append(
                Shot(
                    path=path,
                    src_start=0.0,
                    duration=use,
                    label=f"s{section.index}_b",
                )
            )
            remaining -= use

        if remaining > 0.05:
            hint = hints[hint_idx] if hint_idx < len(hints) else None
            hint_idx += 1
            src_start = tracker.claim_main(hint or 0.0, remaining, main_duration)
            shots.append(
                Shot(
                    path=MAIN_VIDEO,
                    src_start=src_start,
                    duration=remaining,
                    label=f"s{section.index}_m",
                )
            )

    return shots


def shot_filter(input_idx: int, shot: Shot, label: str) -> str:
    return (
        f"[{input_idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,"
        f"trim=start={shot.src_start:.3f}:duration={shot.duration:.3f},"
        f"setpts=PTS-STARTPTS,format=yuv420p[{label}]"
    )


def render_section(section: Section, shots: list[Shot], tmpdir: Path) -> Path:
    unique_inputs: list[Path] = []
    input_map: dict[Path, int] = {}
    for shot in shots:
        if shot.path not in input_map:
            input_map[shot.path] = len(unique_inputs)
            unique_inputs.append(shot.path)

    parts: list[str] = []
    labels: list[str] = []
    for i, shot in enumerate(shots):
        idx = input_map[shot.path]
        label = f"v{i}"
        parts.append(shot_filter(idx, shot, label))
        labels.append(label)

    if len(labels) == 1:
        parts.append(f"[{labels[0]}]copy[vout]")
    else:
        prev = labels[0]
        cumulative = shots[0].duration
        for i in range(1, len(labels)):
            transition = TRANSITIONS[i % len(TRANSITIONS)]
            offset = max(0.0, cumulative - SECTION_XFADE)
            out = "vout" if i == len(labels) - 1 else f"x{i}"
            parts.append(
                f"[{prev}][{labels[i]}]xfade=transition={transition}:"
                f"duration={SECTION_XFADE}:offset={offset:.3f}[{out}]"
            )
            prev = out
            cumulative = offset + shots[i].duration

    out_path = tmpdir / f"section_{section.index:02d}.mp4"
    cmd = ["ffmpeg", "-y"]
    for path in unique_inputs:
        cmd.extend(["-i", str(path)])
    cmd.extend(
        [
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            str(out_path),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def render_final(section_videos: list[Path], sections: list[Section], audio_duration: float) -> None:
    parts: list[str] = []
    labels = [f"sec{i}" for i in range(len(section_videos))]

    for i, path in enumerate(section_videos):
        dur = probe_duration(path)
        parts.append(
            f"[{i}:v]scale=1280:720,fps=30,trim=duration={dur:.3f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[{labels[i]}]"
        )

    prev = labels[0]
    cumulative = probe_duration(section_videos[0])
    for i in range(1, len(labels)):
        transition = TRANSITIONS[i % len(TRANSITIONS)]
        offset = max(0.0, cumulative - SECTION_XFADE)
        out = "vout" if i == len(labels) - 1 else f"y{i}"
        parts.append(
            f"[{prev}][{labels[i]}]xfade=transition={transition}:"
            f"duration={SECTION_XFADE}:offset={offset:.3f}[{out}]"
        )
        prev = out
        cumulative = offset + probe_duration(section_videos[i])

    narration_idx = len(section_videos)
    parts.append(
        f"[{narration_idx}:a]aformat=sample_rates=48000:channel_layouts=stereo[aout]"
    )

    cmd = ["ffmpeg", "-y"]
    for path in section_videos:
        cmd.extend(["-i", str(path)])
    cmd.extend(["-i", str(NARRATION)])
    cmd.extend(
        [
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-t",
            f"{audio_duration:.3f}",
            str(OUTPUT),
        ]
    )
    subprocess.run(cmd, check=True)


def main() -> int:
    if not WHISPER_JSON.is_file():
        print(f"Missing whisper timing file: {WHISPER_JSON}", file=sys.stderr)
        return 1

    paragraphs = [
        p.strip()
        for p in TRANSCRIPT.read_text(encoding="utf-8").strip().split("\n\n")
        if p.strip()
    ]
    if len(paragraphs) != len(SECTION_DEFS):
        print("Paragraph/section count mismatch", file=sys.stderr)
        return 1

    segments = load_whisper_segments()
    sections = align_sections(paragraphs, segments)
    main_duration = probe_duration(MAIN_VIDEO)
    audio_duration = probe_duration(NARRATION)
    tracker = UsageTracker()

    all_shots: dict[int, list[Shot]] = {}
    for section in sections:
        all_shots[section.index] = build_section_shots(section, tracker, main_duration)

    print(f"Building {OUTPUT.name} | audio {audio_duration:.1f}s")
    for section in sections:
        shots = all_shots[section.index]
        print(
            f"  Section {section.index:2d} {section.start:6.1f}-{section.end:6.1f}s "
            f"({section.end - section.start:5.1f}s) {len(shots)} shots | {section.title}"
        )

    with tempfile.TemporaryDirectory(prefix="doc2_") as tmp:
        tmpdir = Path(tmp)
        section_videos: list[Path] = []
        for section in sections:
            print(f"Rendering section {section.index}...")
            section_videos.append(render_section(section, all_shots[section.index], tmpdir))
        print("Assembling final video...")
        render_final(section_videos, sections, audio_duration)

    plan = {
        "output": str(OUTPUT),
        "audio_duration": audio_duration,
        "sections": [
            {
                "index": s.index,
                "title": s.title,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "shots": [
                    {
                        "clip": shot.path.name,
                        "src_start": round(shot.src_start, 2),
                        "duration": round(shot.duration, 2),
                    }
                    for shot in all_shots[s.index]
                ],
            }
            for s in sections
        ],
    }
    PLAN_OUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Done: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
