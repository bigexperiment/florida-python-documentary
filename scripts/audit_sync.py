#!/usr/bin/env python3
"""Thorough sync audit: extract frame at each shot + score contextual match."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def extract_frame(video: Path, t: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)],
        check=True, capture_output=True,
    )


def load_timeline(plan: dict) -> list[dict]:
    if "shots" in plan and "sections" not in plan:
        return plan["shots"]
    entries = []
    t = 0.0
    for sec in plan.get("sections", []):
        if abs(sec["start"] - t) > 0.5:
            t = sec["start"]
        for shot in sec["shots"]:
            entries.append({**shot, "output_start": t, "output_end": t + shot["duration"]})
            t += shot["duration"]
    return entries


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=DOCS / "sync_audit")
    args = p.parse_args()

    plan = json.loads(args.plan.read_text())
    shots = load_timeline(plan)
    out_dir = args.out_dir / args.video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    vid_streams = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(args.video),
        ],
        capture_output=True, text=True, check=True,
    )
    aud_streams = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(args.video),
        ],
        capture_output=True, text=True, check=True,
    )
    video_stream_dur = float(vid_streams.stdout.strip())
    audio_stream_dur = float(aud_streams.stdout.strip())

    issues = []
    topic_issues = []
    audit = []
    for i, shot in enumerate(shots):
        t = shot["output_start"] + 0.3
        frame = out_dir / f"{i+1:03d}_t{shot['output_start']:06.2f}.jpg"
        extract_frame(args.video, t, frame)
        score = shot.get("score", 999)
        section = shot.get("section", "")
        cat_topic = shot.get("catalog_topic")
        entry = {
            "shot": i + 1,
            "time": round(shot["output_start"], 2),
            "end": round(shot.get("output_end", shot["output_start"] + shot["duration"]), 2),
            "section": section,
            "narration": shot.get("narration", "")[:120],
            "clip": shot["clip"],
            "catalog_second": shot.get("catalog_second"),
            "catalog_topic": cat_topic,
            "score": score,
            "match_reason": shot.get("match_reason", ""),
            "frame": str(frame.relative_to(ROOT)),
        }
        if shot["clip"].endswith("The_Asymmetric_War__Florida_vs.mp4") or "main" in shot["clip"].lower():
            if score < 12:
                issues.append(entry)
            if cat_topic and section:
                section_topics = {
                    "Everglades opener": {"everglades"},
                    "Exotic pet trade": {"pet_trade"},
                    "Hurricane Andrew": {"hurricane"},
                    "Ecosystem collapse": {"ecosystem_collapse", "python_biology", "population"},
                    "Alligator predation": {"alligator"},
                    "Scout snake program": {"scout_snake"},
                    "Hand capture": {"scout_snake", "python_challenge"},
                    "Python Challenge": {"python_challenge"},
                    "Thermal / eDNA tech": {"technology"},
                    "Hybrid expansion": {"hybrid"},
                    "Conclusion": {"conclusion"},
                }.get(section, set())
                if section_topics and cat_topic not in section_topics:
                    topic_issues.append(entry)
        audit.append(entry)

    report = {
        "video": str(args.video),
        "format_duration": probe_duration(args.video),
        "video_stream_duration": video_stream_dur,
        "audio_stream_duration": audio_stream_dur,
        "stream_drift": round(video_stream_dur - audio_stream_dur, 3),
        "audio_duration": plan.get("audio_duration"),
        "shots": len(shots),
        "low_score_count": len(issues),
        "topic_mismatch_count": len(topic_issues),
        "issues": issues,
        "topic_mismatches": topic_issues,
        "all_shots": audit,
    }
    report_path = out_dir / "audit_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Audited {len(shots)} shots -> {out_dir}")
    print(f"Format duration: {report['format_duration']:.2f}s")
    print(f"Video stream: {video_stream_dur:.2f}s | Audio stream: {audio_stream_dur:.2f}s | Drift: {report['stream_drift']:+.3f}s")
    print(f"Low-score main clips: {len(issues)} | Topic mismatches: {len(topic_issues)}")
    for iss in issues[:8]:
        print(f"  t={iss['time']}s score={iss['score']} | {iss['narration'][:50]}")
    for iss in topic_issues[:5]:
        print(f"  TOPIC t={iss['time']}s {iss['section']} got {iss['catalog_topic']}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
