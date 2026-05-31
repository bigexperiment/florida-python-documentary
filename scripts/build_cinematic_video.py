#!/usr/bin/env python3
"""Build a cinematic B-roll video synced to narration and transcript."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BROLL = ROOT / "assets" / "broll"
AUDIO = ROOT / "assets" / "audio"
DOCS = ROOT / "docs"
OUTPUT_DIR = ROOT / "output"
NARRATION = AUDIO / (
    "ElevenLabs_2026-05-23T01_28_35_Daniel - Steady Broadcaster_pre_sp100_s50_sb75_se0_b_m2.mp3"
)
TRANSCRIPT = DOCS / "full-video-transcript.txt"
OUTPUT = OUTPUT_DIR / "final_documentary.mp4"

TRANSITION_SEC = 0.65
TRANSITIONS = [
    "fade",
    "dissolve",
    "smoothleft",
    "smoothright",
    "circleopen",
    "fadeblack",
    "wiperight",
    "slideleft",
]


@dataclass
class Segment:
    clip: Path
    duration: float


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
    matches = sorted(BROLL.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No clip matching {pattern}")
    return matches[0]


def load_paragraphs() -> list[str]:
    text = TRANSCRIPT.read_text(encoding="utf-8").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise ValueError("Transcript has no paragraphs")
    return paragraphs


def build_timeline(audio_duration: float, paragraphs: list[str]) -> list[float]:
    words = [len(p.split()) for p in paragraphs]
    total_words = sum(words)
    n = len(paragraphs)
    overlap = TRANSITION_SEC * (n - 1)
    scaled_total = audio_duration + overlap
    durations = [scaled_total * (w / total_words) for w in words]
    return durations


def segment_plan(durations: list[float]) -> list[Segment]:
    landscape = find_clip("Pythons_in_Everglades_landscape*.mp4")
    clips = [
        find_clip("into.mp4"),  # Everglades opener
        find_clip("Python_moving_in_swamp_water*.mp4"),  # pet trade / swamp
        find_clip("Hurricane_destroys_reptile_facility*.mp4"),  # Hurricane Andrew
        landscape,  # ecosystem collapse
        find_clip("Python_swallowing_alligator_dawn_202605222100.mp4"),  # alligator predation
        find_clip("Officers_capture_python_in_swamp*.mp4"),  # scout snake / swamp ops
        find_clip("Officers_capture_large_python*.mp4"),  # hand capture struggle
        find_clip("Python_Challenge_hunters_capture*.mp4"),  # Python Challenge
        find_clip("Python_hunting_with_thermal_cameras*.mp4"),  # infrared tech
        find_clip("Hybrid_python_spreads_across_Flo*.mp4"),  # hybrid expansion
        landscape,  # closing — same clip, second input
    ]
    if len(clips) != len(durations):
        raise ValueError(f"Clip count {len(clips)} != section count {len(durations)}")
    return [Segment(clip=clips[i], duration=durations[i]) for i in range(len(durations))]


def prepare_video_filter(input_idx: int, source_duration: float, target: float, label: str) -> str:
    base = (
        f"[{input_idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,"
    )
    if source_duration >= target:
        return (
            f"{base}trim=duration={target:.3f},setpts=PTS-STARTPTS,"
            f"format=yuv420p[{label}]"
        )
    speed = target / source_duration
    return (
        f"{base}setpts=PTS*{speed:.6f},trim=duration={target:.3f},setpts=PTS-STARTPTS,"
        f"format=yuv420p[{label}]"
    )


def build_filter_complex(segments: list[Segment], narration_idx: int) -> str:
    parts: list[str] = []
    labels: list[str] = []

    for i, seg in enumerate(segments):
        src = probe_duration(seg.clip)
        label = f"s{i}"
        parts.append(prepare_video_filter(i, src, seg.duration, label))
        labels.append(label)

    prev = labels[0]
    cumulative = segments[0].duration
    for i in range(1, len(segments)):
        transition = TRANSITIONS[i % len(TRANSITIONS)]
        offset = cumulative - TRANSITION_SEC
        out = "vout" if i == len(segments) - 1 else f"x{i}"
        parts.append(
            f"[{prev}][{labels[i]}]xfade=transition={transition}:"
            f"duration={TRANSITION_SEC}:offset={offset:.3f}[{out}]"
        )
        prev = out
        cumulative = offset + segments[i].duration

    parts.append(f"[{narration_idx}:a]aformat=sample_rates=48000:channel_layouts=stereo[aout]")
    return ";".join(parts)


def main() -> int:
    if not NARRATION.is_file():
        print(f"Missing narration: {NARRATION}", file=sys.stderr)
        return 1
    if not TRANSCRIPT.is_file():
        print(f"Missing transcript: {TRANSCRIPT}", file=sys.stderr)
        return 1

    paragraphs = load_paragraphs()
    audio_duration = probe_duration(NARRATION)
    durations = build_timeline(audio_duration, paragraphs)
    segments = segment_plan(durations)

    print(f"Narration: {audio_duration:.1f}s | Sections: {len(segments)}")
    for i, seg in enumerate(segments, 1):
        print(f"  {i:2}. {seg.duration:5.1f}s  {seg.clip.name}")

    cmd = ["ffmpeg", "-y"]
    for seg in segments:
        cmd.extend(["-i", str(seg.clip)])
    cmd.extend(["-i", str(NARRATION)])

    narration_idx = len(segments)
    filter_complex = build_filter_complex(segments, narration_idx)
    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
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

    print(f"\nRendering -> {OUTPUT}")
    subprocess.run(cmd, check=True)

    meta = {
        "output": str(OUTPUT),
        "audio_duration": audio_duration,
        "segments": [
            {"clip": seg.clip.name, "duration": round(seg.duration, 2)}
            for seg in segments
        ],
    }
    (DOCS / "cinematic_documentary_plan.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
