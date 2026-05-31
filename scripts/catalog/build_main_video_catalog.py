#!/usr/bin/env python3
"""Build per-second catalog of main documentary video."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_paths import (  # noqa: E402
    CATALOG_DIR,
    CATALOG_JSON as CATALOG_OUT,
    FRAMES_DIR,
    MAIN_VIDEO,
    MAIN_VIDEO_WHISPER as WHISPER_JSON,
)

TOPIC_RANGES: list[tuple[int, int, str, str]] = [
    (0, 37, "everglades", "Everglades landscape and invasive predator introduction"),
    (37, 65, "pet_trade", "Miami exotic pet trade and illegal releases"),
    (65, 90, "hurricane", "Hurricane Andrew 1992 and breeding facility breach"),
    (90, 120, "population", "Established python population and management shift"),
    (120, 160, "python_biology", "Python camouflage, reproduction, and advantages"),
    (160, 180, "ecosystem_collapse", "Native mammal decline charts and local extinctions"),
    (180, 220, "alligator", "Alligator predation, lungworm parasite, food web collapse"),
    (220, 260, "python_challenge", "Florida Python Challenge and removal statistics"),
    (260, 280, "scout_snake", "Scout snake radio transmitter program"),
    (280, 320, "technology", "Thermal cameras, canine units, and eDNA testing"),
    (320, 350, "hybrid", "Hybrid genetics and northward range expansion"),
    (350, 366, "conclusion", "Eradication impossible; Everglades under siege"),
]


def seconds_to_timestamp(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


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


def transcript_at_second(segments: list[dict], second: int) -> str:
    t = float(second) + 0.5
    for seg in segments:
        if seg["start"] <= t < seg["end"]:
            return seg["text"]
    if segments and t >= segments[-1]["end"]:
        return segments[-1]["text"]
    return ""


def topic_for_second(second: int) -> tuple[str, str]:
    for start, end, topic, summary in TOPIC_RANGES:
        if start <= second <= end:
            return topic, summary
    return "general", "Documentary illustration or map graphic"


def visual_summary(second: int, transcript: str, topic: str, topic_summary: str) -> str:
    text = transcript.lower()
    if "everglades" in text or "sawgrass" in text:
        return "Wide Everglades marshland with sawgrass and sky"
    if "hurricane" in text or "andrew" in text or "1992" in text or "category 5" in text:
        return "August 1992 calendar beside hurricane map over Florida"
    if "pet trade" in text or "miami" in text or "exotic" in text:
        return "Vintage Miami port / exotic reptile trade illustration"
    if "graph" in text or "99%" in text or "raccoon" in text or "opossum" in text:
        return "Declining native mammal population chart or infographic"
    if "alligator" in text:
        return "Python vs alligator predation illustration"
    if "lungworm" in text or "parasite" in text:
        return "Parasite / pathology scientific illustration"
    if "python challenge" in text or "prize money" in text or "23,000" in text:
        return "Python Challenge hunters and removal statistics graphics"
    if "scout snake" in text or "radio transmitter" in text or "implant" in text:
        return "Surgical radio transmitter implant on captured python"
    if "thermal" in text or "infrared" in text or "850" in text:
        return "Thermal/infrared python detection on patrol vehicle"
    if "edna" in text or "environmental dna" in text or "water" in text and "testing" in text:
        return "Environmental DNA / water sampling laboratory graphic"
    if "hybrid" in text or "indian rock python" in text or "genetic" in text:
        return "DNA helix and hybrid python genetics visualization"
    if "eradication" in text or "damage control" in text or "endure" in text:
        return "Swamp ecosystem finale with python among native wildlife"
    if "camouflage" in text or "invisible" in text:
        return "Camouflaged Burmese python hidden in leaf litter"
    if "capture" in text or "hand" in text or "headlamp" in text:
        return "Nighttime hand capture of python with flashlight"
    if "egg" in text or "clutch" in text:
        return "Python reproduction / egg clutch illustration"
    return topic_summary


def main() -> int:
    if not WHISPER_JSON.is_file():
        raise SystemExit(f"Missing whisper output: {WHISPER_JSON}")

    segments = load_whisper_segments()
    duration = math.floor(366.294785)  # match ffprobe; seconds 0..365
    entries = []

    for second in range(duration):
        transcript = transcript_at_second(segments, second)
        topic, topic_summary = topic_for_second(second)
        frame_num = second + 1  # ffmpeg fps=1 starts at frame_0001
        frame_rel = f"intermediate/main_video_frames/frame_{frame_num:04d}.jpg"
        entries.append(
            {
                "second": second,
                "timestamp": seconds_to_timestamp(second),
                "transcript": transcript,
                "frame": frame_rel,
                "topic": topic,
                "visual_summary": visual_summary(second, transcript, topic, topic_summary),
            }
        )

    catalog = {
        "source": "The_Asymmetric_War__Florida_vs.mp4",
        "duration": 366.29,
        "frames_dir": "intermediate/main_video_frames/",
        "whisper_source": "data/whisper/main_video_whisper.json",
        "segments": entries,
    }
    CATALOG_OUT.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"Wrote {CATALOG_OUT} with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
