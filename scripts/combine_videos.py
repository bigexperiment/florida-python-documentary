#!/usr/bin/env python3
"""Combine all MP4 files in a folder, excluding specified files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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


def sort_key(path: Path) -> tuple:
    name = path.name.lower()
    if name.startswith("into"):
        return (0, name)
    if "asymmetric_war" in name:
        return (1, name)
    return (2, name)


def build_concat_filter(inputs: list[Path]) -> str:
    parts = []
    for i in range(len(inputs)):
        parts.append(
            f"[{i}:v]fps=30,scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
            f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[a{i}]"
        )
    video_inputs = "".join(f"[v{i}]" for i in range(len(inputs)))
    audio_inputs = "".join(f"[a{i}]" for i in range(len(inputs)))
    parts.append(f"{video_inputs}concat=n={len(inputs)}:v=1:a=0[vout]")
    parts.append(f"{audio_inputs}concat=n={len(inputs)}:v=0:a=1[aout]")
    return ";".join(parts)


ROOT = Path(__file__).resolve().parent.parent
BROLL = ROOT / "assets" / "broll"
OUTPUT_DIR = ROOT / "output"


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine MP4 videos with ffmpeg")
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        default=BROLL,
        help="Directory containing videos (default: assets/broll)",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=["main video.mp4"],
        help="Filename(s) to exclude (default: main video.mp4)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: combined_output.mp4)",
    )
    args = parser.parse_args()

    directory = args.dir.resolve()
    exclude = {name.lower() for name in args.exclude}
    videos = sorted(
        [
            path
            for path in directory.glob("*.mp4")
            if path.name.lower() not in exclude
        ],
        key=sort_key,
    )

    if not videos:
        print("No videos found to combine.", file=sys.stderr)
        return 1

    output = (args.output or OUTPUT_DIR / "combined_output.mp4").resolve()

    print("Combining videos in this order:")
    total = 0.0
    for i, path in enumerate(videos, 1):
        duration = probe_duration(path)
        total += duration
        print(f"  {i:2}. {path.name} ({duration:.1f}s)")

    filter_complex = build_concat_filter(videos)
    cmd = ["ffmpeg", "-y"]
    for path in videos:
        cmd.extend(["-i", str(path)])
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
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )

    print(f"\nOutput: {output}")
    print(f"Estimated duration: {total:.1f}s ({total / 60:.1f} min)")
    print("\nRunning ffmpeg...")
    subprocess.run(cmd, check=True)
    print(f"\nDone: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
