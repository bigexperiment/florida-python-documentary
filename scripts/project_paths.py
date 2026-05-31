"""Shared project paths — scripts resolve files relative to a project folder."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT_NAME = os.environ.get("DOCUMENTARY_PROJECT", "ai-water-supply")

ROOT = REPO_ROOT / "projects" / PROJECT_NAME
PROMPTS = REPO_ROOT / "prompts" / PROJECT_NAME
ARCHIVE = REPO_ROOT / "archive"

ASSETS = ROOT / "assets"
BROLL = ASSETS / "broll"
MAIN = ASSETS / "main"
AUDIO = ASSETS / "audio"
OUTPUT_DIR = ROOT / "output"
MODELS = ROOT / "models"

DATA = ROOT / "data"
PLANS = DATA / "plans"
TRANSCRIPTS = DATA / "transcripts"
SUBTITLES = DATA / "subtitles"
WHISPER = DATA / "whisper"
CATALOG_DIR = DATA / "catalog"
SCRIPT_JSON = DATA / "script_AI_water_supply.json"

INTERMEDIATE = ROOT / "intermediate"
FRAMES_DIR = INTERMEDIATE / "main_video_frames"
MAIN_VIDEO_AUDIO = INTERMEDIATE / "main_video_audio.wav"

REPORTS = ROOT / "reports"
SYNC_AUDIT = REPORTS / "sync_audit"
SYNC_REVIEW = REPORTS / "sync_review"

NARRATION_PROMPT = PROMPTS / "narration.txt"
VOICE_PROMPT = PROMPTS / "voice.txt"
TRANSCRIPT = NARRATION_PROMPT

NARRATION_MP3 = AUDIO / "narration.mp3"
NARRATION_WHISPER = WHISPER / "narration_whisper.json"
MAIN_VIDEO_WHISPER = WHISPER / "main_video_whisper.json"
CATALOG_JSON = CATALOG_DIR / "main_video_catalog.json"

# Legacy burmese-python paths (project 1 — archived)
BURMESE_ARCHIVE = ARCHIVE / "project-1-burmese-python"
