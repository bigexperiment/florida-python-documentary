#!/usr/bin/env python3
"""Build final_documentary_6.mp4 — whisper-locked cuts + topic-aware global catalog search."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUTPUT_DIR = ROOT / "output"
NARRATION = ROOT / "assets" / "audio" / (
    "ElevenLabs_2026-05-23T01_28_35_Daniel - Steady Broadcaster_pre_sp100_s50_sb75_se0_b_m2.mp3"
)
TRANSCRIPT = DOCS / "full-video-transcript.txt"
WHISPER_JSON = DOCS / "narration_whisper.json"
CATALOG_JSON = DOCS / "main_video_catalog.json"
MAIN_VIDEO = ROOT / "assets" / "main" / "The_Asymmetric_War__Florida_vs.mp4"
OUTPUT = OUTPUT_DIR / "final_documentary_6.mp4"
PLAN_OUT = DOCS / "final_documentary_6_plan.json"

MIN_SHOT = 3.0
MAX_SHOT = 5.0
CHUNK_SIZE = 10
FPS = 30
MIN_MATCH_SCORE = 12.0

from build_documentary_v3 import (  # noqa: E402
    AVOID_BY_SECTION,
    SECTION_DEFS,
    Section,
    align_sections,
    find_clip,
    load_whisper_segments,
    normalize,
    probe_duration,
)
from build_documentary_v4 import (  # noqa: E402
    BrollTracker,
    TimelineSlot,
    build_timeline_slots,
    concat_videos,
    render_chunk,
)

SECTION_OVERRIDES: list[tuple[list[str], str]] = [
    (["established", "self reproducing", "scientists confirmed", "year 2000"], "Ecosystem collapse"),
    (["alligator", "food chain", "predator eating"], "Alligator predation"),
    (["scout snake", "radio transmitter", "breeding aggregation", "implant beneath"], "Scout snake program"),
    (["at night", "headlamp", "snake hook", "pitch black", "three grown men"], "Hand capture"),
    (["python challenge", "prize money", "10000", "civilian", "23000", "one percent"], "Python Challenge"),
    (["thermal", "infrared", "850", "environmental dna", "heat signature"], "Thermal / eDNA tech"),
    (["hybrid", "indian rock", "genetic vigor", "2025 range"], "Hybrid expansion"),
    (["eradication", "damage control", "irreversibly", "surrendered", "holding the line"], "Conclusion"),
]

HAND_CAPTURE_BROLL = "Officers_capture_large_python_202605222105.mp4"


PHRASE_BOOSTS = [
    ("scout snake", 15),
    ("hurricane andrew", 15),
    ("python challenge", 15),
    ("environmental dna", 12),
    ("heat signature", 12),
    ("pet trade", 10),
    ("food web", 10),
    ("burmese python", 10),
    ("outgrew their enclosures", 12),
    ("importing thousands", 12),
    ("breeding facility", 10),
    ("thermal imaging", 10),
    ("alligator", 8),
    ("everglades", 6),
    ("hybrid", 6),
    ("eradication", 6),
]


@dataclass
class Shot:
    path: Path
    src_start: float
    duration: float
    output_start: float
    output_end: float
    slot_text: str
    section_title: str
    catalog_second: int | None = None
    catalog_topic: str | None = None
    score: float = 0.0
    match_reason: str = ""


class TopicCatalogMatcher:
    """Match catalog by narration text + section topic, not main-video timeline position."""

    def __init__(self, catalog_path: Path) -> None:
        self.entries = json.loads(catalog_path.read_text(encoding="utf-8"))["segments"]
        self.used_ranges: list[tuple[float, float]] = []

    def _free(self, start: float, duration: float) -> bool:
        end = start + duration
        for u0, u1 in self.used_ranges:
            if not (end <= u0 + 0.05 or start >= u1 - 0.05):
                return False
        return True

    def _score(self, entry: dict, slot: TimelineSlot, section: Section) -> float:
        score = 0.0
        topic = entry.get("topic", "")
        if topic in section.topics:
            score += 25.0
        else:
            score -= 20.0

        blob = normalize(
            f"{entry.get('transcript', '')} {entry.get('visual_summary', '')} {topic}"
        )
        slot_norm = normalize(slot.text)

        slot_words = {w for w in slot_norm.split() if len(w) > 3}
        blob_words = set(blob.split())
        score += len(slot_words & blob_words) * 4.0

        for kw in section.keywords:
            if kw in blob:
                score += 5.0
            if kw in slot_norm:
                score += 3.0

        for phrase, boost in PHRASE_BOOSTS:
            if phrase in slot_norm and phrase in blob:
                score += boost

        for word in slot_norm.split():
            if len(word) > 4 and word in blob:
                score += 1.5

        return score

    def pick(
        self, slot: TimelineSlot, section: Section, duration: float, avoid: set[str]
    ) -> tuple[float, float, int, str, float]:
        candidates: list[tuple[float, dict, bool]] = []
        for entry in self.entries:
            if entry["topic"] in avoid:
                continue
            if entry["topic"] not in section.topics:
                continue
            start = float(entry["second"])
            free = self._free(start, duration)
            score = self._score(entry, slot, section) + (8.0 if free else -6.0)
            candidates.append((score, entry, free))

        if not candidates:
            raise ValueError(f"No catalog match for slot at {slot.start:.1f}s: {slot.text[:60]}")

        candidates.sort(key=lambda x: (-x[0], x[1]["second"]))
        best_score, best, _free = candidates[0]
        start = float(best["second"])
        self.used_ranges.append((start, start + duration))
        reason = (
            f"topic={best['topic']} score={best_score:.1f} "
            f"sec={best['second']} | {best['visual_summary'][:55]}"
        )
        return start, best["second"], best["topic"], reason, best_score


def resolve_section(slot: TimelineSlot, sections: list[Section]) -> Section:
    text = normalize(slot.text)
    for keywords, title in SECTION_OVERRIDES:
        if any(k in text for k in keywords):
            return next(s for s in sections if s.title == title)
    return slot.section


def hand_capture_broll(broll: BrollTracker) -> Path | None:
    path = find_clip(HAND_CAPTURE_BROLL)
    if path.name in broll.used:
        return None
    broll.used.add(path.name)
    return path


EXTRA_AVOID: dict[int, set[str]] = {
    6: {"everglades", "alligator", "python_challenge"},
    7: {"everglades", "hurricane", "hybrid", "technology"},
    8: {"alligator", "population", "everglades", "scout_snake"},
    9: {"alligator", "python_challenge", "scout_snake"},
    10: {"python_challenge", "scout_snake", "technology"},
    11: {"everglades", "pet_trade", "hurricane", "python_challenge"},
}


def build_shots(slots: list[TimelineSlot], sections: list[Section], matcher: TopicCatalogMatcher) -> list[Shot]:
    shots: list[Shot] = []
    broll = BrollTracker()
    section_slot_index: dict[int, int] = {}

    for slot in slots:
        section = resolve_section(slot, sections)
        idx = section_slot_index.get(section.index, 0)
        section_slot_index[section.index] = idx + 1
        avoid = AVOID_BY_SECTION.get(section.index, set()) | EXTRA_AVOID.get(section.index, set())
        duration = slot.duration
        slot_norm = normalize(slot.text)

        path = None
        if idx == 0:
            path = broll.take_for_section(section.index)
        elif any(k in slot_norm for k in ["headlamp", "snake hook", "at night", "pitch black"]):
            path = hand_capture_broll(broll)
        if path is not None:
            clip_len = probe_duration(path)
            use = min(duration, clip_len)
            shots.append(
                Shot(
                    path=path,
                    src_start=0.0,
                    duration=use,
                    output_start=slot.start,
                    output_end=slot.start + use,
                    slot_text=slot.text,
                    section_title=section.title,
                    score=999.0,
                    match_reason="section b-roll",
                )
            )
            if duration - use > 0.05:
                src, cat_sec, cat_topic, reason, score = matcher.pick(
                    slot, section, duration - use, avoid
                )
                shots.append(
                    Shot(
                        path=MAIN_VIDEO,
                        src_start=src,
                        duration=duration - use,
                        output_start=slot.start + use,
                        output_end=slot.end,
                        slot_text=slot.text,
                        section_title=section.title,
                        catalog_second=cat_sec,
                        catalog_topic=cat_topic,
                        score=score,
                        match_reason=reason,
                    )
                )
            continue

        src, cat_sec, cat_topic, reason, score = matcher.pick(slot, section, duration, avoid)
        shots.append(
            Shot(
                path=MAIN_VIDEO,
                src_start=src,
                duration=duration,
                output_start=slot.start,
                output_end=slot.end,
                slot_text=slot.text,
                section_title=section.title,
                catalog_second=cat_sec,
                catalog_topic=cat_topic,
                score=score,
                match_reason=reason,
            )
        )

    return shots


def pad_video_track(video: Path, target: float, out: Path) -> None:
    current = probe_duration(video)
    gap = target - current
    if gap <= 0.02:
        if video.resolve() != out.resolve():
            shutil.copy2(video, out)
        return
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"tpad=stop_mode=clone:stop_duration={gap:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            str(out),
        ],
        check=True,
        capture_output=True,
    )


def mux_audio(video: Path, audio: Path, out_path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v",
            "-map",
            "1:a",
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
            f"{duration:.3f}",
            str(out_path),
        ],
        check=True,
    )


def main() -> int:
    for path in (WHISPER_JSON, CATALOG_JSON, TRANSCRIPT, NARRATION, MAIN_VIDEO):
        if not path.is_file():
            print(f"Missing: {path}", file=sys.stderr)
            return 1

    paragraphs = [
        p.strip()
        for p in TRANSCRIPT.read_text(encoding="utf-8").strip().split("\n\n")
        if p.strip()
    ]
    segments = load_whisper_segments()
    sections = align_sections(paragraphs, segments)
    audio_duration = probe_duration(NARRATION)
    slots = build_timeline_slots(segments, sections)
    matcher = TopicCatalogMatcher(CATALOG_JSON)
    shots = build_shots(slots, sections, matcher)

    shot_total = sum(s.duration for s in shots)
    low = [s for s in shots if s.score < MIN_MATCH_SCORE and s.path == MAIN_VIDEO]
    print(
        f"Slots: {len(slots)} | Shots: {len(shots)} | "
        f"Planned track: {shot_total:.2f}s | Audio: {audio_duration:.2f}s"
    )
    print(f"Low-score main clips: {len(low)}")

    with tempfile.TemporaryDirectory(prefix="doc6_") as tmp:
        tmpdir = Path(tmp)
        chunk_paths: list[Path] = []
        for i in range(0, len(shots), CHUNK_SIZE):
            chunk = shots[i : i + CHUNK_SIZE]
            chunk_path = tmpdir / f"chunk_{i // CHUNK_SIZE:03d}.mp4"
            print(f"Rendering chunk {i // CHUNK_SIZE + 1} ({len(chunk)} shots)...")
            render_chunk(chunk, chunk_path)
            chunk_paths.append(chunk_path)

        raw_track = tmpdir / "raw_track.mp4"
        if len(chunk_paths) == 1:
            raw_track = chunk_paths[0]
        else:
            concat_videos(chunk_paths, raw_track)

        raw_dur = probe_duration(raw_track)
        print(f"Raw video track: {raw_dur:.2f}s (drift: {raw_dur - audio_duration:+.2f}s)")

        padded = tmpdir / "padded_track.mp4"
        pad_video_track(raw_track, audio_duration, padded)
        print(f"Padded video track: {probe_duration(padded):.2f}s")

        print("Muxing narration...")
        mux_audio(padded, NARRATION, OUTPUT, audio_duration)

    out_vid = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(OUTPUT),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(f"Final video stream: {float(out_vid.stdout.strip()):.2f}s")

    plan = {
        "output": str(OUTPUT),
        "audio_duration": audio_duration,
        "sync_method": "Whisper slots + topic-aware global catalog search (no timeline bias)",
        "min_match_score": MIN_MATCH_SCORE,
        "shots": [
            {
                "output_start": round(s.output_start, 2),
                "output_end": round(s.output_end, 2),
                "duration": round(s.duration, 2),
                "narration": s.slot_text,
                "section": s.section_title,
                "clip": s.path.name,
                "src_start": round(s.src_start, 2),
                "catalog_second": s.catalog_second,
                "catalog_topic": s.catalog_topic,
                "score": round(s.score, 1),
                "match_reason": s.match_reason,
            }
            for s in shots
        ],
    }
    PLAN_OUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Done: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
