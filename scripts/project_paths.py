"""Shared project paths — all scripts resolve files relative to the repo root."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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

INTERMEDIATE = ROOT / "intermediate"
FRAMES_DIR = INTERMEDIATE / "main_video_frames"
MAIN_VIDEO_AUDIO = INTERMEDIATE / "main_video_audio.wav"

REPORTS = ROOT / "reports"
SYNC_AUDIT = REPORTS / "sync_audit"
SYNC_REVIEW = REPORTS / "sync_review"

MAIN_VIDEO = MAIN / "The_Asymmetric_War__Florida_vs.mp4"
NARRATION_MP3 = AUDIO / (
    "ElevenLabs_2026-05-23T01_28_35_Daniel - Steady Broadcaster_pre_sp100_s50_sb75_se0_b_m2.mp3"
)
TRANSCRIPT = TRANSCRIPTS / "full-video-transcript.txt"
NARRATION_WHISPER = WHISPER / "narration_whisper.json"
MAIN_VIDEO_WHISPER = WHISPER / "main_video_whisper.json"
CATALOG_JSON = CATALOG_DIR / "main_video_catalog.json"
