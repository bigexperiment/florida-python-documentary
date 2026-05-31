#!/usr/bin/env python3
"""Build final_documentary_4.mp4 — whisper-locked timeline, hard cuts, semantic catalog matching."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import (  # noqa: E402
    BROLL,
    CATALOG_JSON,
    MAIN,
    MAIN_VIDEO,
    NARRATION_MP3 as NARRATION,
    OUTPUT_DIR,
    PLANS,
    TRANSCRIPT,
    NARRATION_WHISPER as WHISPER_JSON,
)

OUTPUT = OUTPUT_DIR / "final_documentary_4.mp4"
PLAN_OUT = PLANS / "final_documentary_4_plan.json"

MIN_SHOT = 3.0
MAX_SHOT = 5.0
CHUNK_SIZE = 10

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


@dataclass
class TimelineSlot:
    start: float
    end: float
    text: str
    section: Section

    @property
    def duration(self) -> float:
        return self.end - self.start


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
    match_reason: str = ""


class CatalogMatcher:
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
        lo, hi = section.second_range
        sec = entry["second"]
        if lo <= sec <= hi:
            score += 12.0
        else:
            score -= min(abs(sec - lo), abs(sec - hi)) * 0.08

        if entry["topic"] in section.topics:
            score += 10.0

        blob = normalize(
            f"{entry.get('transcript', '')} {entry.get('visual_summary', '')} {entry.get('topic', '')}"
        )
        slot_words = set(normalize(slot.text).split())
        for word in slot_words:
            if len(word) > 3 and word in blob:
                score += 1.5
        for kw in section.keywords:
            if kw in blob or kw in normalize(slot.text):
                score += 2.0
        return score

    def pick(
        self, slot: TimelineSlot, section: Section, duration: float, avoid: set[str]
    ) -> tuple[float, int, str]:
        candidates: list[tuple[float, dict]] = []
        for entry in self.entries:
            if entry["topic"] in avoid:
                continue
            start = float(entry["second"])
            if not self._free(start, duration):
                continue
            candidates.append((self._score(entry, slot, section), entry))

        if not candidates:
            raise ValueError(f"No catalog match for slot at {slot.start:.1f}s: {slot.text[:50]}")

        candidates.sort(key=lambda x: (-x[0], x[1]["second"]))
        best_score, best = candidates[0]
        start = float(best["second"])
        self.used_ranges.append((start, start + duration))
        reason = (
            f"topic={best['topic']} score={best_score:.1f} "
            f"visual={best['visual_summary'][:55]}"
        )
        return start, best["second"], reason


class BrollTracker:
    def __init__(self) -> None:
        self.used: set[str] = set()
        self.section_broll: dict[int, list[Path]] = {}
        for i, sec in enumerate(SECTION_DEFS, start=1):
            self.section_broll[i] = [find_clip(p) for p in sec.broll]

    def take_for_section(self, section_index: int) -> Path | None:
        queue = self.section_broll.get(section_index, [])
        while queue:
            path = queue.pop(0)
            if path.name not in self.used:
                self.used.add(path.name)
                return path
        return None


def build_timeline_slots(segments: list[dict], sections: list[Section]) -> list[TimelineSlot]:
    slots: list[TimelineSlot] = []
    i = 0
    while i < len(segments):
        start = segments[i]["start"]
        end = segments[i]["end"]
        texts = [segments[i]["text"]]
        i += 1
        while i < len(segments):
            dur = end - start
            next_dur = segments[i]["end"] - segments[i]["start"]
            if dur >= MAX_SHOT:
                break
            if dur + next_dur > MAX_SHOT and dur >= MIN_SHOT:
                break
            texts.append(segments[i]["text"])
            end = segments[i]["end"]
            i += 1
            if end - start >= MAX_SHOT:
                break

        section = next(s for s in sections if s.start <= start < s.end)
        slots.append(TimelineSlot(start=start, end=end, text=" ".join(texts), section=section))

    slots[-1].end = segments[-1]["end"]
    total = sum(s.duration for s in slots)
    target = segments[-1]["end"]
    if abs(total - target) > 0.01:
        slots[-1].end += target - total
    return slots


def build_shots(slots: list[TimelineSlot], matcher: CatalogMatcher) -> list[Shot]:
    shots: list[Shot] = []
    broll = BrollTracker()
    section_slot_index: dict[int, int] = {}

    for slot in slots:
        section = slot.section
        idx = section_slot_index.get(section.index, 0)
        section_slot_index[section.index] = idx + 1
        avoid = AVOID_BY_SECTION.get(section.index, set())
        duration = slot.duration

        path = broll.take_for_section(section.index) if idx == 0 else None
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
                    match_reason="section b-roll",
                )
            )
            if duration - use > 0.05:
                src, cat_sec, reason = matcher.pick(slot, section, duration - use, avoid)
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
                        match_reason=reason,
                    )
                )
            continue

        src, cat_sec, reason = matcher.pick(slot, section, duration, avoid)
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


def render_chunk(shots: list[Shot], out_path: Path) -> None:
    unique_inputs: list[Path] = []
    input_map: dict[Path, int] = {}
    for shot in shots:
        if shot.path not in input_map:
            input_map[shot.path] = len(unique_inputs)
            unique_inputs.append(shot.path)

    parts: list[str] = []
    labels: list[str] = []
    for i, shot in enumerate(shots):
        parts.append(shot_filter(input_map[shot.path], shot, f"s{i}"))
        labels.append(f"s{i}")

    parts.append("".join(f"[{l}]" for l in labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")

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


def concat_videos(paths: list[Path], out_path: Path) -> None:
    list_file = out_path.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in paths),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_path),
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
    matcher = CatalogMatcher(CATALOG_JSON)
    shots = build_shots(slots, matcher)

    shot_total = sum(s.duration for s in shots)
    print(f"Slots: {len(slots)} | Shots: {len(shots)} | Video track: {shot_total:.2f}s | Audio: {audio_duration:.2f}s")

    with tempfile.TemporaryDirectory(prefix="doc4_") as tmp:
        tmpdir = Path(tmp)
        chunk_paths: list[Path] = []
        for i in range(0, len(shots), CHUNK_SIZE):
            chunk = shots[i : i + CHUNK_SIZE]
            chunk_path = tmpdir / f"chunk_{i // CHUNK_SIZE:03d}.mp4"
            print(f"Rendering chunk {i // CHUNK_SIZE + 1} ({len(chunk)} shots)...")
            render_chunk(chunk, chunk_path)
            chunk_paths.append(chunk_path)

        video_path = tmpdir / "video_track.mp4"
        if len(chunk_paths) == 1:
            video_path = chunk_paths[0]
        else:
            concat_videos(chunk_paths, video_path)

        vid_dur = probe_duration(video_path)
        print(f"Video track duration: {vid_dur:.2f}s (drift vs audio: {vid_dur - audio_duration:+.2f}s)")
        print("Muxing narration...")
        mux_audio(video_path, NARRATION, OUTPUT, audio_duration)

    plan = {
        "output": str(OUTPUT),
        "audio_duration": audio_duration,
        "sync_method": "Whisper slot boundaries + hard concat (no xfade drift)",
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
                "match_reason": s.match_reason,
            }
            for s in shots
        ],
    }
    PLAN_OUT.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Done: {OUTPUT} ({probe_duration(OUTPUT):.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
