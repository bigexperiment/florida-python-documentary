# Documentary Channel — Automated Pipeline

Multi-project repo for AI-assisted YouTube documentaries (Curious Mind / Wendover style).

**Active project:** Project 2 — *AI Is Secretly Draining Your City's Water Supply*

**Full briefing:** [`youtube_channel_context.md`](youtube_channel_context.md) — paste into new chat sessions.

## Layout

```
├── youtube_channel_context.md   Full project context
├── prompts/ai-water-supply/     Narration + voice notes
├── projects/ai-water-supply/    Active video (script, assets, output)
├── scripts/                     Shared v6 build pipeline
└── archive/project-1-burmese-python/   Archived Everglades test project
```

## Project 2 — next steps

1. Render narration → `prompts/ai-water-supply/narration.txt` → ElevenLabs
2. Source B-roll from `projects/ai-water-supply/data/script_AI_water_supply.json` → `broll_master_list`
3. Run Whisper + v6 pipeline

```bash
# Default project is ai-water-supply
python3.12 scripts/build/build_documentary_v6.py
```

## Requirements

- Python 3.12+
- ffmpeg / ffprobe
- ElevenLabs API (narration)
