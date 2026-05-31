# Florida Python Documentary Project

## Folder structure

```
abc/
├── output/              Final rendered videos
├── assets/
│   ├── broll/           B-roll clips and intro
│   ├── main/            Original main documentary
│   └── audio/           Narration and audio files
├── docs/                Transcript, subtitles, edit plans
└── scripts/             Python build tools
```

## Key files

| File | Description |
|------|-------------|
| `output/final_documentary.mp4` | Final edit v1 (B-roll + ElevenLabs narration) |
| `output/final_documentary_6.mp4` | Best edit — sync-locked + topic-aware clip matching — **use this** |
| `output/final_documentary_4.mp4` | Sync-fixed edit (whisper-locked, hard cuts) |
| `assets/main/The_Asymmetric_War__Florida_vs.mp4` | Original main video |
| `docs/full-video-transcript.txt` | Narration script |
| `assets/audio/ElevenLabs_*.mp3` | Voiceover audio |

## Scripts

```bash
python3.12 scripts/build_cinematic_video.py   # Rebuild final documentary v1
python3.12 scripts/build_documentary_v6.py    # Rebuild best edit v6 (recommended)
python3.12 scripts/build_documentary_v4.py    # Rebuild sync-fixed v4
python3.12 scripts/audit_sync.py --video output/final_documentary_6.mp4 --plan docs/final_documentary_6_plan.json
python3.12 scripts/review_sync.py --video output/final_documentary_6.mp4 --plan docs/final_documentary_6_plan.json
python3.12 scripts/add_subtitles.py           # Add burned-in subtitles
python3.12 scripts/combine_videos.py          # Combine B-roll clips only
```
