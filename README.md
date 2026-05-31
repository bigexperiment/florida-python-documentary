# Documentary workspace

Multi-project repo for AI-assisted documentary editing. Each project lives under `projects/` with its own assets, data, and outputs. Shared build tools live in `scripts/`.

## Layout

```
├── prompts/                    Narration and voice prompts per project
│   └── burmese-python/
├── projects/                   One folder per documentary
│   └── burmese-python/
│       ├── assets/             Source B-roll, main video, audio
│       ├── data/               Plans, whisper, subtitles, catalog
│       ├── output/             Rendered MP4s
│       ├── intermediate/       Extracted frames (local)
│       └── reports/            Sync audit JSON (+ local review frames)
└── scripts/                    Shared Python pipeline
```

## Projects

| Project | Folder | Description |
|---------|--------|-------------|
| Burmese Python | `projects/burmese-python/` | Florida Everglades invasive python documentary |

## Quick start (Burmese Python)

```bash
# Rebuild best edit (v6)
python3.12 scripts/build/build_documentary_v6.py

# Audit sync
python3.12 scripts/sync/audit_sync.py \
  --video projects/burmese-python/output/final_documentary_6.mp4 \
  --plan projects/burmese-python/data/plans/final_documentary_6_plan.json
```

Set `DOCUMENTARY_PROJECT=burmese-python` to target a different project folder (default).

## Requirements

- Python 3.12+
- ffmpeg / ffprobe
