# Florida Python Documentary Project

Automated edit pipeline: sync B-roll and main-documentary clips to ElevenLabs narration using Whisper timings and a per-second video catalog.

**Repo:** https://github.com/bigexperiment/florida-python-documentary

## Folder structure

```
├── assets/                 Source media (local only — not in git)
│   ├── broll/              B-roll clips and intro
│   ├── main/               Original main documentary
│   └── audio/              Narration and audio files
├── data/                   Transcripts, plans, whisper output, catalog
│   ├── plans/              Edit plans (JSON)
│   ├── transcripts/        Narration scripts
│   ├── subtitles/          SRT files
│   ├── whisper/            Whisper transcription JSON
│   └── catalog/            Main-video per-second catalog
├── intermediate/           Extracted frames/audio (local only)
├── models/                 Whisper model weights (local only)
├── output/                 Final rendered videos (local only)
├── reports/                Sync audit/review outputs (local only)
└── scripts/
    ├── project_paths.py    Shared path constants
    ├── build/              Documentary build scripts
    ├── catalog/            Catalog generation
    └── sync/               Sync audit and review tools
```

## Key outputs

| File | Description |
|------|-------------|
| `output/final_documentary_6.mp4` | Best edit — sync-locked + topic-aware clip matching |
| `output/final_documentary_4.mp4` | Sync-fixed edit (whisper-locked, hard cuts) |
| `output/final_documentary.mp4` | v1 cinematic B-roll + narration |
| `data/plans/final_documentary_6_plan.json` | Shot list and match metadata for v6 |

## Setup

Place source media locally (not tracked in git):

- `assets/main/The_Asymmetric_War__Florida_vs.mp4`
- `assets/broll/*.mp4`
- `assets/audio/ElevenLabs_*.mp3`
- `models/ggml-base.en.bin` (Whisper)

## Scripts

```bash
# Recommended: rebuild best edit
python3.12 scripts/build/build_documentary_v6.py

# Other builds
python3.12 scripts/build/build_cinematic_video.py    # v1
python3.12 scripts/build/build_documentary_v4.py     # v4 sync-fixed
python3.12 scripts/build/add_subtitles.py            # burn-in subtitles
python3.12 scripts/build/combine_videos.py           # combine B-roll only

# Catalog (requires main video + whisper + extracted frames)
python3.12 scripts/catalog/build_main_video_catalog.py

# QA
python3.12 scripts/sync/audit_sync.py \
  --video output/final_documentary_6.mp4 \
  --plan data/plans/final_documentary_6_plan.json
python3.12 scripts/sync/review_sync.py \
  --video output/final_documentary_6.mp4 \
  --plan data/plans/final_documentary_6_plan.json
```

## Requirements

- Python 3.12+
- ffmpeg / ffprobe (Homebrew `ffmpeg-full` recommended for subtitle burn-in)
