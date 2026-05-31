#!/usr/bin/env python3
"""Extract review frames from a documentary and compare to narration at each cut."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WHISPER_JSON = DOCS / "narration_whisper.json"


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


def load_whisper_fixed() -> list[dict]:
    data = json.loads(WHISPER_JSON.read_text(encoding="utf-8"))
    return [
        {
            "start": item["offsets"]["from"] / 1000.0,
            "end": item["offsets"]["to"] / 1000.0,
            "text": item["text"].strip(),
        }
        for item in data["transcription"]
    ]


def narration_at(segments: list[dict], t: float) -> str:
    parts = [s["text"] for s in segments if s["start"] <= t < s["end"]]
    if not parts:
        nearest = min(segments, key=lambda s: min(abs(s["start"] - t), abs(s["end"] - t)))
        return nearest["text"]
    return " ".join(parts)


def extract_frame(video: Path, t: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ],
        check=True,
        capture_output=True,
    )


def build_timeline_from_plan(plan: dict) -> list[dict]:
    if "sections" in plan:
        entries: list[dict] = []
        t = 0.0
        for section in plan["sections"]:
            sec_start = section["start"]
            if abs(sec_start - t) > 0.5:
                t = sec_start
            for shot in section["shots"]:
                entries.append(
                    {
                        "output_start": t,
                        "output_end": t + shot["duration"],
                        "duration": shot["duration"],
                        "clip": shot["clip"],
                        "src_start": shot.get("src_start"),
                        "catalog_second": shot.get("catalog_second"),
                        "match_reason": shot.get("match_reason", ""),
                        "section": section["title"],
                        "section_start": section["start"],
                        "section_end": section["end"],
                        "narration_hint": shot.get("narration", ""),
                    }
                )
                t += shot["duration"]
        return entries

    return [
        {
            "output_start": shot["output_start"],
            "output_end": shot["output_end"],
            "duration": shot["duration"],
            "clip": shot["clip"],
            "src_start": shot.get("src_start"),
            "catalog_second": shot.get("catalog_second"),
            "match_reason": shot.get("match_reason", ""),
            "section": shot.get("section", ""),
            "section_start": shot["output_start"],
            "section_end": shot["output_end"],
            "narration_hint": shot.get("narration", ""),
        }
        for shot in plan["shots"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Review A/V sync of a documentary")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DOCS / "sync_review",
    )
    args = parser.parse_args()

    if not args.video.is_file():
        print(f"Missing video: {args.video}", file=sys.stderr)
        return 1
    if not args.plan.is_file():
        print(f"Missing plan: {args.plan}", file=sys.stderr)
        return 1

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    segments = load_whisper_fixed()
    timeline = build_timeline_from_plan(plan)
    video_dur = probe_duration(args.video)
    audio_dur = plan.get("audio_duration", video_dur)

    out_dir = args.out_dir / args.video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    review: list[dict] = []
    for i, entry in enumerate(timeline):
        mid = entry["output_start"] + entry["duration"] / 2
        frame_path = out_dir / f"shot_{i+1:03d}_t{mid:06.2f}.jpg"
        extract_frame(args.video, mid, frame_path)
        expected_narration = entry.get("narration_hint") or narration_at(segments, mid)
        review.append(
            {
                "shot": i + 1,
                "output_time": round(mid, 2),
                "planned_shot_start": round(entry["output_start"], 2),
                "section": entry["section"],
                "section_narration_window": f"{entry['section_start']:.1f}-{entry['section_end']:.1f}s",
                "clip": entry["clip"],
                "src_start": entry["src_start"],
                "catalog_second": entry["catalog_second"],
                "match_reason": entry["match_reason"],
                "narration_at_output_time": expected_narration,
                "frame": str(frame_path.relative_to(ROOT)),
            }
        )

    report = {
        "video": str(args.video),
        "video_duration": video_dur,
        "audio_duration": audio_dur,
        "duration_drift": round(video_dur - audio_dur, 3),
        "shots": review,
    }
    report_path = out_dir / "sync_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Video duration: {video_dur:.2f}s | Audio: {audio_dur:.2f}s | Drift: {video_dur - audio_dur:+.2f}s")
    print(f"Extracted {len(review)} review frames -> {out_dir}")
    print(f"Report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
