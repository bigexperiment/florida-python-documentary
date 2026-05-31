#!/usr/bin/env python3
"""Build final_documentary_5.mp4 — one clip per whisper segment, semantic catalog search."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from project_paths import (  # noqa: E402
    BROLL,
    CATALOG_JSON,
    MAIN,
    MAIN_VIDEO,
    NARRATION_MP3 as NARRATION,
    OUTPUT_DIR,
    PLANS,
    NARRATION_WHISPER as WHISPER_JSON,
)

OUTPUT = OUTPUT_DIR / "final_documentary_5.mp4"
PLAN_OUT = PLANS / "final_documentary_5_plan.json"
CHUNK_SIZE = 8
MIN_SCORE = 8

BROLL_RULES: list[tuple[str, list[str]]] = [
    ("into.mp4", ["everglades", "sawgrass", "ecosystem", "predator", "surface"]),
    (
        "Python_moving_in_swamp_water_202605222056.mp4",
        ["import", "reptile", "port", "miami", "enclosure", "swamp", "dump", "wild"],
    ),
    (
        "Hurricane_destroys_reptile_facility_202605222058.mp4",
        ["hurricane", "andrew", "1992", "storm", "facility", "breeding", "catastrophic"],
    ),
    (
        "Pythons_in_Everglades_landscape_202605222112.mp4",
        ["predators", "mammal", "extinction", "food web", "collapse", "invisible", "camouflage"],
    ),
    (
        "Python_hunting_alligator_in_Ever*.mp4",
        ["food chain", "apex", "hunting", "alligator", "consuming"],
    ),
    (
        "Python_swallowing_alligator_dawn_202605222100.mp4",
        ["alligator", "predator-eating", "predator eating"],
    ),
    (
        "Python_swallowing_alligator_dawn_202605222103.mp4",
        ["alligator", "apex predator"],
    ),
    (
        "Officers_capture_python_in_swamp_202605222033.mp4",
        ["scout", "transmitter", "implant", "tracked", "breeding aggregation", "biologists"],
    ),
    (
        "Officers_capture_large_python_202605222105.mp4",
        ["night", "headlamp", "hook", "capture", "hand", "struggle", "constrict", "officers"],
    ),
    (
        "Python_Challenge_hunters_capture*.mp4",
        ["challenge", "hunters", "prize", "23000", "23,000", "civilian", "contractors"],
    ),
    (
        "Python_hunting_with_thermal_cameras_202605222109.mp4",
        ["thermal", "infrared", "850", "heat signature", "invisible", "technology", "edna", "water"],
    ),
    (
        "Hybrid_python_spreads_across_Flo*.mp4",
        ["hybrid", "indian rock", "genetic", "expansion", "climate", "counties"],
    ),
]

PHRASE_BOOSTS = [
    ("scout snake", 12),
    ("hurricane andrew", 12),
    ("python challenge", 12),
    ("environmental dna", 10),
    ("heat signature", 10),
    ("pet trade", 8),
    ("food web", 8),
    ("alligator", 6),
    ("everglades", 6),
    ("hybrid", 6),
    ("eradication", 6),
    ("thermal", 5),
    ("infrared", 5),
]


@dataclass
class Shot:
    path: Path
    src_start: float
    duration: float
    output_start: float
    output_end: float
    narration: str
    score: float
    catalog_second: int | None = None
    match_reason: str = ""


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    if "*" not in pattern:
        path = BROLL / pattern
        if path.is_file():
            return path
    matches = sorted(BROLL.glob(pattern))
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def load_narration_segments() -> list[dict]:
    data = json.loads(WHISPER_JSON.read_text(encoding="utf-8"))
    return [
        {
            "start": item["offsets"]["from"] / 1000.0,
            "end": item["offsets"]["to"] / 1000.0,
            "text": item["text"].strip(),
        }
        for item in data["transcription"]
    ]


def score_text(slot_text: str, blob: str) -> float:
    slot = normalize(slot_text)
    target = normalize(blob)
    score = 0.0
    slot_words = {w for w in slot.split() if len(w) > 3}
    target_words = set(target.split())
    score += len(slot_words & target_words) * 2.0
    for phrase, boost in PHRASE_BOOSTS:
        if phrase in slot and phrase in target:
            score += boost
    for word in slot.split():
        if len(word) > 4 and word in target:
            score += 1.0
    return score


class Matcher:
    def __init__(self) -> None:
        self.catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))["segments"]
        self.broll_rules = [(find_clip(p), kws) for p, kws in BROLL_RULES]
        self.broll_used: set[str] = set()
        self.main_used: list[tuple[float, float]] = []

    def _main_free(self, start: float, duration: float) -> bool:
        end = start + duration
        for u0, u1 in self.main_used:
            if not (end <= u0 + 0.05 or start >= u1 - 0.05):
                return False
        return True

    def pick(self, seg: dict) -> Shot:
        text = seg["text"]
        duration = seg["end"] - seg["start"]
        best_broll: tuple[float, Path, str] | None = None

        for path, keywords in self.broll_rules:
            if path.name in self.broll_used:
                continue
            blob = " ".join(keywords)
            s = score_text(text, blob)
            if s >= MIN_SCORE and (best_broll is None or s > best_broll[0]):
                best_broll = (s, path, f"b-roll keyword score={s:.1f}")

        if best_broll and best_broll[0] >= MIN_SCORE + 2:
            path = best_broll[1]
            clip_len = probe_duration(path)
            if clip_len + 0.05 >= duration:
                self.broll_used.add(path.name)
                return Shot(
                    path=path,
                    src_start=0.0,
                    duration=duration,
                    output_start=seg["start"],
                    output_end=seg["end"],
                    narration=text,
                    score=best_broll[0],
                    match_reason=best_broll[2],
                )

        candidates: list[tuple[float, dict]] = []
        for entry in self.catalog:
            start = float(entry["second"])
            if not self._main_free(start, duration):
                continue
            blob = f"{entry.get('transcript', '')} {entry.get('visual_summary', '')} {entry.get('topic', '')}"
            s = score_text(text, blob)
            if s >= MIN_SCORE:
                candidates.append((s, entry))

        if not candidates:
            for entry in self.catalog:
                start = float(entry["second"])
                if not self._main_free(start, duration):
                    continue
                blob = f"{entry.get('transcript', '')} {entry.get('visual_summary', '')}"
                s = score_text(text, blob)
                candidates.append((s, entry))

        candidates.sort(key=lambda x: (-x[0], x[1]["second"]))
        best_score, best = candidates[0]
        start = float(best["second"])
        self.main_used.append((start, start + duration))
        reason = (
            f"catalog sec={best['second']} topic={best['topic']} "
            f"score={best_score:.1f} | {best['visual_summary'][:50]}"
        )
        return Shot(
            path=MAIN_VIDEO,
            src_start=start,
            duration=duration,
            output_start=seg["start"],
            output_end=seg["end"],
            narration=text,
            score=best_score,
            catalog_second=best["second"],
            match_reason=reason,
        )


def shot_filter(input_idx: int, shot: Shot, label: str) -> str:
    return (
        f"[{input_idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,"
        f"trim=start={shot.src_start:.3f}:duration={shot.duration:.3f},"
        f"setpts=PTS-STARTPTS,format=yuv420p[{label}]"
    )


def render_chunk(shots: list[Shot], out_path: Path) -> None:
    unique: list[Path] = []
    idx_map: dict[Path, int] = {}
    for s in shots:
        if s.path not in idx_map:
            idx_map[s.path] = len(unique)
            unique.append(s.path)
    parts = []
    labels = []
    for i, shot in enumerate(shots):
        parts.append(shot_filter(idx_map[shot.path], shot, f"s{i}"))
        labels.append(f"s{i}")
    parts.append("".join(f"[{l}]" for l in labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")
    cmd = ["ffmpeg", "-y"]
    for p in unique:
        cmd.extend(["-i", str(p)])
    cmd.extend(["-filter_complex", ";".join(parts), "-map", "[vout]", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", str(out_path)])
    subprocess.run(cmd, check=True, capture_output=True)


def concat_videos(paths: list[Path], out_path: Path) -> None:
    lst = out_path.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{p.resolve()}'" for p in paths), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out_path)],
        check=True,
        capture_output=True,
    )


def mux(video: Path, out: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(NARRATION),
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{duration:.3f}", str(out),
        ],
        check=True,
    )


def main() -> int:
    segments = load_narration_segments()
    matcher = Matcher()
    shots: list[Shot] = []

    for seg in segments:
        shot = matcher.pick(seg)
        shot.duration = seg["end"] - seg["start"]
        shot.output_start = seg["start"]
        shot.output_end = seg["end"]
        shots.append(shot)

    total = sum(s.duration for s in shots)
    audio_dur = probe_duration(NARRATION)
    print(f"Segments: {len(segments)} | Shots: {len(shots)} | track={total:.2f}s audio={audio_dur:.2f}s")

    low = [s for s in shots if s.score < MIN_SCORE]
    print(f"Low-score shots: {len(low)}")

    with tempfile.TemporaryDirectory(prefix="doc5_") as tmp:
        tmpdir = Path(tmp)
        chunks: list[Path] = []
        for i in range(0, len(shots), CHUNK_SIZE):
            chunk = shots[i : i + CHUNK_SIZE]
            p = tmpdir / f"c{i // CHUNK_SIZE:03d}.mp4"
            print(f"Chunk {i // CHUNK_SIZE + 1}: {len(chunk)} shots")
            render_chunk(chunk, p)
            chunks.append(p)
        vtrack = chunks[0] if len(chunks) == 1 else tmpdir / "vtrack.mp4"
        if len(chunks) > 1:
            concat_videos(chunks, vtrack)
        print(f"Video track: {probe_duration(vtrack):.2f}s")
        mux(vtrack, OUTPUT, audio_dur)

    plan = {
        "output": str(OUTPUT),
        "audio_duration": audio_dur,
        "sync_method": "1 whisper segment = 1 clip; global catalog keyword search",
        "min_score": MIN_SCORE,
        "shots": [
            {
                "output_start": round(s.output_start, 2),
                "output_end": round(s.output_end, 2),
                "duration": round(s.duration, 2),
                "narration": s.narration,
                "clip": s.path.name,
                "src_start": round(s.src_start, 2),
                "catalog_second": s.catalog_second,
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
