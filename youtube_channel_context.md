# YouTube Channel — Full Project Context
> **Purpose of this file:** Paste this into any new chat session. The AI will instantly know the full project, pipeline, files, and current progress without needing re-explanation.

---

## 1. What This Channel Is

An **automated documentary YouTube channel** in the style of **Curious Mind, Wendover Productions, and Vox Explainers**.

- **Format:** Narrated, cinematic, B-roll-heavy documentary. No talking head. No on-camera host.
- **Content type:** Explainer / informational documentary — "hidden truth" and "you didn't know this" angles
- **Length:** Long-form (8–12 minutes, YouTube main feed)
- **Thumbnail style:** Two-line clicky hooks. Line 1 = shocking claim. Line 2 = urgency or payoff.
  - Example: `"Every ChatGPT message costs a bottle of water / here's the math"`
- **Title style:** Curious Mind formula — lead with the mystery, payoff in subtitle
- **Competition niche:** curiosity / mystery / geopolitics / environment / tech explainers

---

## 2. The Production Pipeline (Technical)

| Step | Tool / Method |
|------|--------------|
| Narration audio | ElevenLabs (TTS voice) |
| Word-level timing | Whisper (used to lock cuts to narration) |
| B-roll + main footage | Semantic clip matching from per-second catalog (v6 pipeline) |
| Clip selection | `semantic_tags` in script JSON guide matching |
| Sync audit | Custom tools in `scripts/sync/` score each shot vs narration |
| Publishing | YouTube — thumbnail + title tested for CTR |

### Edit versions history (Project 1 test bed — archived)
- **v1** — Simple cinematic B-roll cut
- **v2** — Early narration sync attempt
- **v3–v4** — Whisper-locked timelines; v4 was the sync-fixed milestone
- **v5–v6** — Semantic clip matching from per-second catalog; **v6 is current best**
- **v6 features:** Hard cuts locked to narration, topic-aware clip selection, fewer repeated frames

Project 1 (Burmese Python / Everglades) validated the pipeline. **Project 2 is now active.**

---

## 3. Repo Layout

```
├── youtube_channel_context.md     ← this file
├── scripts/                       Shared v6 pipeline (build, catalog, sync)
├── prompts/
│   └── ai-water-supply/           Active narration + voice notes
├── projects/
│   └── ai-water-supply/           Active video (Project 2)
└── archive/
    └── project-1-burmese-python/  Completed test project (not deleted)
```

Default project: `ai-water-supply` (override with `DOCUMENTARY_PROJECT=...`)

---

## 4. Topic Research — 12 Ideas (All Trending as of May 2026)

### 🌍 Geopolitics
1. **China owns the minerals inside every device you own** — rare earth supply chain, China controls every step
2. **Iran is building a nuclear bomb — and nobody can stop it** — US bombing June 2025, New START expired Feb 2026
3. **Greenland is now the most strategically important island on Earth** — US/China/Denmark competition, Arctic route, rare earths

### 🌱 Environment
4. **The glacier that could drown Miami** — Thwaites Doomsday Glacier, ice shelf near collapse, Florida angle
5. **The hidden water war nobody is talking about** — water privatization, rivers running dry globally
6. **The coral reefs are dying in real time** — 1.5°C breach confirmed 2025, annual bleaching events

### 🔬 Science
7. **Microplastics are inside your brain right now** — found in hearts, lungs, brains 2024–26
8. **How a new space telescope will rewrite everything we know** — NASA Roman Space Telescope, launches autumn 2026

### 💻 Tech / AI
9. **AI is secretly draining your city's water supply** ← ✅ **CHOSEN — SCRIPT COMPLETE (Project 2)**
10. **The energy grid is not ready for AI** — 72% YoY demand growth, 1970s grids can't handle it

### 🏙️ Society
11. **America's pipes are rotting** — PFAS, aging infrastructure, FEMA cuts
12. **The US public health system is flying blind** — CDC layoffs, next pandemic blind spot

---

## 5. Active Video: "AI Is Secretly Draining Your City's Water Supply"

### Quick Brief
- **Project folder:** `projects/ai-water-supply/`
- **Thumbnail hook:** `"Every ChatGPT message costs a bottle of water / here's the math"`
- **Best title option:** *AI Is Quietly Draining America's Water Supply (And No One Is Talking About It)*
- **Runtime:** 10–11 minutes
- **Narration word count:** ~1,615 words at 145–155 wpm

### Script Structure (8 Acts)

| Act | Name | Timestamp | Theme | Key hook |
|-----|------|-----------|-------|----------|
| 0 | Cold Open | 00:00 | Hook | Water bottle in hand before reveal |
| 1 | The Invisible Transaction | 00:45 | Explainer — how cooling works | Sweat analogy for evaporative cooling |
| 2 | The Numbers | 02:30 | Scale — corporate stats | Google 8.1B gallons, GPT-4 training 13.4M/month |
| 3 | The Town That Fought Google | 04:15 | Narrative — The Dalles Oregon | City sued its own newspaper to protect Google's secret |
| 4 | The Desert Is Open For Business | 06:30 | Geography — drought zones | 200 data centers in Arizona, 23,000 residents' worth of water |
| 5 | The Hidden Third Layer — Chips | 07:50 | Escalation — semiconductor water | TSMC Phoenix fab: 5M gallons/day ultrapure water |
| 6 | Where This Is Going | 09:10 | Projections | Morgan Stanley: 11x growth to 1 trillion liters by 2028 |
| 7 | The Community That Won | 10:05 | Solution beat | Quincy WA + Microsoft: $35M recycling, 380M gallons/year saved |
| 8 | Outro | 11:05 | Moral close | "Your query, their water" — who gets to decide |

### Key Stories in This Video
- **The Dalles, Oregon** — Google built its first data center here in 2006 in secrecy. By 2021, when The Oregonian filed a public records request, the city sued their own newspaper (on Google's behalf, Google paid legal costs) to keep usage a "trade secret." After a 13-month legal fight, Google lost. Usage revealed: 274.5M gallons/year — a third of the city's water supply. Resident Dawn Rasmussen: *"I'm flabbergasted. And I'm scared for the future."*
- **Phoenix / Mesa / Buckeye, Arizona** — Nearly 200 data centers being built in a state with extreme drought. Google's Mesa permit: 1.45B gallons/year (same as 23,000 Arizonans). 2/3 of all new AI data centers are in high water stress zones.
- **TSMC Phoenix** — Chip manufacturing hidden second layer. A single fab uses up to 5M gallons/day of ultrapure water. TSMC is building in Phoenix. Same drought, same depleted Colorado River.
- **Quincy, Washington** — The win. Microsoft built a data center but community negotiated. Microsoft funded $35M water recycling facility. Saves 380M gallons/year. Proof the deal is negotiable.

### Key Stats (verified)

| Stat | Figure | Source |
|------|--------|--------|
| Single data center (100MW) daily water | 2M liters/day | IEA 2025 |
| Google global water use | 8.1B gallons | Google Sustainability 2024 |
| Google Council Bluffs Iowa | 1B gallons/year, peak 2.7M/day | Google 2024 |
| Microsoft West Des Moines (5 facilities) | 68.5M gallons/year | KCUR 2024 |
| GPT-4 training (1 month, Iowa) | 13.4M gallons | Futurism / UC Riverside 2022 |
| Amazon water disclosure | None (undisclosed) | Investigative reports |
| Google The Dalles Oregon | 274.5M gallons/year | Oregon public records 2022 |
| Google Mesa AZ permit | 1.45B gallons/year (23,000 residents) | Source Material 2025 |
| New data centers in drought zones | 66% (2 in 3) | World Resources Institute |
| Single chip fab ultrapure water | 5M gallons/day | Morgan Stanley / industry |
| Morgan Stanley AI water projection | 1,068B liters/year by 2028 (11x) | Morgan Stanley Sep 2025 |
| 190+ data center bills in US legislatures | 190 bills | AI Tool Discovery 2025 |
| Microsoft Quincy recycling facility | $35M cost, 380M gallons/year saved | Sustainability reports |
| Phoenix golf courses vs data centers | Golf: 29B gal vs data centers: 905M gal | Andy Masley / AZFamily 2026 |

---

## 6. Output Files

| File | Description |
|------|-------------|
| `youtube_channel_context.md` | **This file** — full project briefing, paste at start of new sessions |
| `projects/ai-water-supply/data/script_AI_water_supply.json` | Full script as structured JSON — each act with narration, b-roll, stats, metadata |
| `prompts/ai-water-supply/narration.txt` | Flat narration text for ElevenLabs (extracted from JSON) |
| `prompts/ai-water-supply/voice.txt` | Voice settings and render notes |

### JSON Schema (script_AI_water_supply.json)
The JSON is designed for AI pipeline queries. Top-level keys:
- **`video`** — metadata: id, topic, runtime, word count, wpm, status
- **`thumbnail_hooks[]`** — 4 options with strength tags
- **`title_options[]`** — 4 options with style notes
- **`acts[]`** — each act contains:
  - `narration` — clean text, paste directly into ElevenLabs
  - `broll[]` — each shot with `description`, `type`, `semantic_tags` for clip matching
  - `stats_cited[]` — IDs linking to stats array
  - `keywords[]`, `retention_device`, `timestamp_start/end`
- **`stats[]`** — 17 individual stats: `figure`, `unit`, `source`, `year`, `verified`, `acts_cited_in`, `tags`
- **`people[]`** — characters (Dawn Rasmussen) with quote and story context
- **`companies[]`** — Google, Microsoft, Amazon, Meta, TSMC with stance and linked stats
- **`locations[]`** — The Dalles, Phoenix, Quincy, Iowa with significance summaries
- **`broll_master_list[]`** — all 37 B-roll shots flat-listed with act + semantic tags

---

## 7. What To Work On Next

Likely next tasks (in order of priority):

1. **B-roll sourcing** — use `broll_master_list` from the JSON to start pulling footage. Primary needs: aerial Phoenix/desert data centers, Colorado River drought, cooling towers, The Dalles Oregon, Quincy WA, TSMC cleanroom, chip close-ups.
2. **Narration render** — feed `prompts/ai-water-supply/narration.txt` to ElevenLabs.
3. **Whisper pass** — generate `data/whisper/narration_whisper.json` from rendered audio.
4. **Sync pass** — run the v6 pipeline on narration audio + B-roll catalog. Use `semantic_tags` in the JSON to guide clip matching.
5. **Thumbnail design** — primary hook: `"Every ChatGPT message costs a bottle of water / here's the math"`. Background: cooling tower steam or desert data center aerial.
6. **Next script** — top candidates: rare earth minerals (China), microplastics in brain, or Doomsday Glacier.

---

## 8. Channel Voice & Style Rules

- **Never** use bullet points in narration — always full sentences, short and punchy
- **Always** have a physical or personal hook in the cold open (water bottle, not an abstract fact)
- **Escalate** — each act should raise the stakes or reveal a deeper layer
- **Include one "win" beat** before the outro — audiences disengage from pure doom
- **Counterpoint goes last** — present the other side in the final 90 seconds, not earlier
- **End with a moral question**, not a conclusion — "who gets to decide?" not "here's what should happen"
- Narration pace target: **145–155 wpm** for ElevenLabs render settings
- B-roll cuts should be **hard cuts on narration beats**, not dissolves (per v6 pipeline behavior)

---

## 9. Archived — Project 1 (Burmese Python)

Everglades invasive python documentary. Pipeline test bed. All files preserved at:

`archive/project-1-burmese-python/`

Best output: `archive/project-1-burmese-python/burmese-python/output/final_documentary_6.mp4`

Not active. Do not mix Project 1 assets into Project 2 workflows unless explicitly testing.
