# Burmese Python (Florida Everglades)

Documentary about invasive Burmese pythons in the Florida Everglades — B-roll + main footage synced to ElevenLabs narration.

## Prompts

| File | Purpose |
|------|---------|
| `prompts/burmese-python/narration.txt` | Full narration script (ElevenLabs source) |
| `prompts/burmese-python/voice.txt` | Voice ID and ElevenLabs settings |

## Key outputs

| File | Notes |
|------|-------|
| `output/final_documentary_6.mp4` | Best edit — use this |
| `output/final_documentary_4.mp4` | Sync-fixed v4 |
| `data/plans/final_documentary_6_plan.json` | Shot list for v6 |

## Rebuild

```bash
python3.12 scripts/build/build_documentary_v6.py
python3.12 scripts/build/add_subtitles.py \
  --video output/final_documentary_6.mp4
```

Paths above are relative to this project folder when run from repo root; scripts resolve them automatically.
