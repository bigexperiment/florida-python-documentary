# Archived — Project 1: Burmese Python (Florida Everglades)

This was the **pipeline test bed** for the documentary automation stack (Whisper sync, semantic B-roll matching, v6 edit).

## What was built
- Edit versions v1–v6; **v6** (`output/final_documentary_6.mp4`) was the best cut
- Full assets, plans, whisper JSON, sync audit reports

## Key paths (all under this archive folder)
| Path | Contents |
|------|----------|
| `burmese-python/` | assets, data, output, intermediate, reports, models |
| `prompts/` | narration.txt, voice.txt |
| `what-we-are-doing.md` | Old channel research notes (superseded by `youtube_channel_context.md`) |

## Pipeline scripts
Shared scripts live at repo root `scripts/` — they now default to **project 2** (`ai-water-supply`).

To rebuild project 1 locally:
```bash
DOCUMENTARY_PROJECT=burmese-python python3.12 scripts/build/build_documentary_v6.py
```
*(Requires moving `burmese-python/` back to `projects/burmese-python/` or symlinking.)*
