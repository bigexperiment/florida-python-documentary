#!/usr/bin/env python3
"""Build final_documentary_3.mp4 using main_video_catalog.json for semantic clip selection."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BROLL = ROOT / "assets" / "broll"
MAIN = ROOT / "assets" / "main"
AUDIO = ROOT / "assets" / "audio"
DOCS = ROOT / "docs"
OUTPUT_DIR = ROOT / "output"
NARRATION = AUDIO / (
    "ElevenLabs_2026-05-23T01_28_35_Daniel - Steady Broadcaster_pre_sp100_s50_sb75_se0_b_m2.mp3"
)
TRANSCRIPT = DOCS / "full-video-transcript.txt"
WHISPER_JSON = DOCS / "narration_whisper.json"
CATALOG_JSON = DOCS / "main_video_catalog.json"
MAIN_VIDEO = MAIN / "The_Asymmetric_War__Florida_vs.mp4"
OUTPUT = OUTPUT_DIR / "final_documentary_3.mp4"
PLAN_OUT = DOCS / "final_documentary_3_plan.json"

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
    catalog_second: int | None = None
    match_reason: str = ""


@dataclass
class Section:
    index: int
    start: float
    end: float
    title: str
    topics: list[str]
    keywords: list[str]
    second_range: tuple[int, int]
    broll: list[str] = field(default_factory=list)


SECTION_DEFS = [
    Section(
        1,
        0,
        0,
        "Everglades opener",
        ["everglades"],
        ["everglades", "sawgrass", "ecosystem", "predator", "surface", "specialized"],
        (0, 37),
        ["into.mp4"],
    ),
    Section(
        2,
        0,
        0,
        "Exotic pet trade",
        ["pet_trade"],
        ["miami", "exotic", "pet", "reptile", "import", "enclosure", "release", "1980"],
        (37, 65),
        ["Python_moving_in_swamp_water_202605222056.mp4"],
    ),
    Section(
        3,
        0,
        0,
        "Hurricane Andrew",
        ["hurricane"],
        ["hurricane", "andrew", "1992", "storm", "category", "breeding", "facility"],
        (65, 90),
        ["Hurricane_destroys_reptile_facility_202605222058.mp4"],
    ),
    Section(
        4,
        0,
        0,
        "Ecosystem collapse",
        ["ecosystem_collapse", "python_biology", "population"],
        [
            "mammal",
            "raccoon",
            "opossum",
            "extinct",
            "camouflage",
            "egg",
            "predator",
            "collapse",
            "food web",
        ],
        (90, 180),
        ["Pythons_in_Everglades_landscape_202605222112.mp4"],
    ),
    Section(
        5,
        0,
        0,
        "Alligator predation",
        ["alligator"],
        ["alligator", "apex", "food chain", "predator eating", "consuming"],
        (180, 220),
        [
            "Python_hunting_alligator_in_Ever*.mp4",
            "Python_swallowing_alligator_dawn_202605222100.mp4",
            "Python_swallowing_alligator_dawn_202605222103.mp4",
        ],
    ),
    Section(
        6,
        0,
        0,
        "Scout snake program",
        ["scout_snake"],
        ["scout", "transmitter", "implant", "radio", "breeding aggregation", "tracked"],
        (255, 285),
        ["Officers_capture_python_in_swamp_202605222033.mp4"],
    ),
    Section(
        7,
        0,
        0,
        "Hand capture",
        ["scout_snake", "python_challenge"],
        ["capture", "hand", "night", "headlamp", "hook", "officers", "swamp", "flashlight"],
        (195, 215),
        ["Officers_capture_large_python_202605222105.mp4"],
    ),
    Section(
        8,
        0,
        0,
        "Python Challenge",
        ["python_challenge"],
        ["python challenge", "hunters", "prize", "civilian", "removed", "23,000", "compete"],
        (220, 260),
        ["Python_Challenge_hunters_capture*.mp4"],
    ),
    Section(
        9,
        0,
        0,
        "Thermal / eDNA tech",
        ["technology"],
        ["thermal", "infrared", "edna", "dna", "camera", "technology", "nanometer", "water"],
        (280, 320),
        ["Python_hunting_with_thermal_cameras_202605222109.mp4"],
    ),
    Section(
        10,
        0,
        0,
        "Hybrid expansion",
        ["hybrid"],
        ["hybrid", "genetic", "indian rock", "range", "north", "counties", "climate", "adapt"],
        (320, 350),
        ["Hybrid_python_spreads_across_Flo*.mp4"],
    ),
    Section(
        11,
        0,
        0,
        "Conclusion",
        ["conclusion"],
        ["eradication", "damage control", "endure", "surrendered", "habitat", "irreversibly"],
        (350, 365),
        [],
    ),
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


class CatalogMatcher:
    def __init__(self, catalog_path: Path) -> None:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.entries = data["segments"]
        self.used_ranges: list[tuple[float, float]] = []

    def _free(self, start: float, duration: float) -> bool:
        end = start + duration
        for used_start, used_end in self.used_ranges:
            if not (end <= used_start + 0.05 or start >= used_end - 0.05):
                return False
        return True

    def _score(self, entry: dict, section: Section) -> float:
        score = 0.0
        lo, hi = section.second_range
        sec = entry["second"]
        if lo <= sec <= hi:
            score += 10.0
        elif sec < lo:
            score -= abs(lo - sec) * 0.05
        else:
            score -= abs(sec - hi) * 0.05

        if entry["topic"] in section.topics:
            score += 8.0

        blob = normalize(
            f"{entry.get('transcript', '')} {entry.get('visual_summary', '')} {entry.get('topic', '')}"
        )
        for kw in section.keywords:
            if kw in blob:
                score += 2.5

        return score

    def pick_start(
        self, section: Section, duration: float, avoid_topics: set[str] | None = None
    ) -> tuple[float, int, str]:
        avoid_topics = avoid_topics or set()
        candidates: list[tuple[float, dict]] = []
        for entry in self.entries:
            if entry["topic"] in avoid_topics:
                continue
            start = float(entry["second"])
            if not self._free(start, duration):
                continue
            candidates.append((self._score(entry, section), entry))

        if not candidates:
            raise ValueError(f"No catalog match for section {section.index}: {section.title}")

        candidates.sort(key=lambda x: (-x[0], x[1]["second"]))
        best_score, best = candidates[0]
        start = float(best["second"])
        end = start + duration
        self.used_ranges.append((start, end))
        reason = (
            f"topic={best['topic']} score={best_score:.1f} "
            f"visual={best['visual_summary'][:60]}"
        )
        return start, best["second"], reason


class UsageTracker:
    def __init__(self) -> None:
        self.broll_used: set[str] = set()

    def claim_broll(self, path: Path, src_start: float, duration: float) -> None:
        if path.name in self.broll_used:
            raise ValueError(f"B-roll reused: {path.name}")
        if src_start > 0.01:
            raise ValueError(f"B-roll partial reuse not allowed: {path.name}")
        clip_len = probe_duration(path)
        if duration > clip_len + 0.05:
            raise ValueError(f"B-roll overused: {path.name}")
        self.broll_used.add(path.name)


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


AVOID_BY_SECTION: dict[int, set[str]] = {
    3: {"python_challenge", "technology", "hybrid"},
    5: {"hurricane", "pet_trade", "python_challenge", "technology"},
    6: {"hurricane", "python_challenge", "hybrid", "alligator"},
    7: {"hurricane", "hybrid", "technology"},
    8: {"hurricane", "scout_snake", "hybrid", "technology"},
    9: {"hurricane", "pet_trade", "python_challenge", "hybrid"},
    10: {"hurricane", "python_challenge", "scout_snake"},
}


def build_section_shots(
    section: Section, tracker: UsageTracker, matcher: CatalogMatcher
) -> list[Shot]:
    duration = section.end - section.start
    durations = split_shot_durations(duration)
    shots: list[Shot] = []
    broll_queue = [find_clip(p) for p in section.broll]
    avoid = AVOID_BY_SECTION.get(section.index, set())

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
            src_start, cat_sec, reason = matcher.pick_start(section, remaining, avoid)
            shots.append(
                Shot(
                    path=MAIN_VIDEO,
                    src_start=src_start,
                    duration=remaining,
                    label=f"s{section.index}_m",
                    catalog_second=cat_sec,
                    match_reason=reason,
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


def render_final(section_videos: list[Path], audio_duration: float) -> None:
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
    for path in (WHISPER_JSON, CATALOG_JSON, TRANSCRIPT, NARRATION, MAIN_VIDEO):
        if not path.is_file():
            print(f"Missing required file: {path}", file=sys.stderr)
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
    audio_duration = probe_duration(NARRATION)
    matcher = CatalogMatcher(CATALOG_JSON)
    tracker = UsageTracker()

    all_shots: dict[int, list[Shot]] = {}
    for section in sections:
        all_shots[section.index] = build_section_shots(section, tracker, matcher)

    print(f"Building {OUTPUT.name} | audio {audio_duration:.1f}s | catalog-driven main clips")
    for section in sections:
        shots = all_shots[section.index]
        main_shots = [s for s in shots if s.path == MAIN_VIDEO]
        print(
            f"  Section {section.index:2d} {section.start:6.1f}-{section.end:6.1f}s "
            f"({section.end - section.start:5.1f}s) {len(shots)} shots | {section.title}"
        )
        for ms in main_shots:
            print(
                f"    main @{ms.src_start:.0f}s ({ms.duration:.1f}s) "
                f"catalog_sec={ms.catalog_second} | {ms.match_reason}"
            )

    with tempfile.TemporaryDirectory(prefix="doc3_") as tmp:
        tmpdir = Path(tmp)
        section_videos: list[Path] = []
        for section in sections:
            print(f"Rendering section {section.index}...")
            section_videos.append(render_section(section, all_shots[section.index], tmpdir))
        print("Assembling final video...")
        render_final(section_videos, audio_duration)

    plan = {
        "output": str(OUTPUT),
        "audio_duration": audio_duration,
        "catalog": str(CATALOG_JSON),
        "matching_strategy": "Per-section topic ranges + keyword scoring from main_video_catalog.json",
        "sections": [
            {
                "index": s.index,
                "title": s.title,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "topics": s.topics,
                "second_range": list(s.second_range),
                "shots": [
                    {
                        "clip": shot.path.name,
                        "src_start": round(shot.src_start, 2),
                        "duration": round(shot.duration, 2),
                        "catalog_second": shot.catalog_second,
                        "match_reason": shot.match_reason,
                    }
                    for shot in all_shots[s.index]
                ],
            }
            for s in sections
        ],
    }
    PLAN_OUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    out_dur = probe_duration(OUTPUT)
    print(f"Done: {OUTPUT} ({out_dur:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
