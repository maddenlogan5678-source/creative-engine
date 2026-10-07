# PROJECT FILE MAP — Creative Engine v7 (FINAL)

Project root: `/mnt/agents/output/app/`

## The files

| File | Role | Edit this when... |
|---|---|---|
| `engine.py` | ALL creative logic — dials, personas, prompts | Changing behavior, voice, dials |
| **`restrictions.py`** | **EVERY restriction in one file** — hard word list, refusal text, soft prompt caps | Reading/editing the restriction layer |
| `server.py` | Web layer (FastAPI routes) — talks to engine.py + agent-gw | Fixing loops, HTTP errors, gateway calls |
| `static/index.html` | The entire UI (single file) | Buttons, layout, chat, gallery |
| `index.html` | **Mirror copy of `static/index.html`** for the version manager | Refresh after UI edits: `cat static/index.html > index.html` |
| `Dockerfile` | Container build | Deploy issues |
| `requirements.txt` | Python deps | Import errors |
| `FILE_MAP.md` | This file | — |
| `generated/` | Generated images (gallery reads this) | Cleanup |
| `uploads/refs/` | YOUR reference uploads (scene/character/pose) — override defaults | Managing references outside UI |
| `uploads/defaults/` | Default references (fallbacks) | Setting new defaults |
| `data/characters.json` | Character cards (auto-created) | Editing/removing characters by hand |
| `data/chats.json` | RP chat history (auto-created) | Wiping conversations |

## WHERE THE RESTRICTIONS ARE (exact locations)

**All restrictions live in ONE file: `restrictions.py`**, marked in two layers:

- **[YOUR LAYER]** — editable, free, local:
  1. `HARD_BOUNDARY_TERMS` — blocked word list (substring match, zero tokens)
  2. `SAFETY_REFUSAL` — refusal message text
  3. Soft caps: `STORY_EXPLICIT_CAP`, `IMAGE_NONSEXUAL_TAG` + pointers to
     persona cards and RP_RULES in engine.py
- **[GATEWAY LAYER]** — the models' own moderation at agent-gw, not in any
  file you own, not reachable by code here.

Enforcement points in `server.py`: `verify_safety()` runs at the top of
`story()`, `image()`, and `rp_send()` — a hit returns HTTP 422.
The engine imports the list from `restrictions.py` (see engine.py [SAFETY]).

## engine.py section banners (Ctrl+F these)

- `[ENUMS]` — POWER_LEVEL, EXPLICIT_LEVEL, HARSHNESS_LEVEL, GRUESOME_LEVEL, CONTENT_TYPE
- `[TAXONOMIES]` — DARK_FICTION_GENRES, DARK_HUMOR_STYLES, DARK_ART_STYLES, REALISM_STYLES, DARK_VISUAL_ELEMENTS, MATURE_THEMES
- `[MODIFIERS]` — INTENSITY_MODIFIERS, HARSHNESS_MODIFIERS, GRUESOME_STORY, GRUESOME_IMAGE
- `[SAFETY]` — HARD_BOUNDARY_TERMS, verify_safety(), SAFETY_REFUSAL
- `[CLASSIFY]` — classify_content()
- `[PERSONAS]` — PERSONAS (Mei/Georgia/Zoey/Scarlet)
- `[ROLEPLAY]` — RP_RULES, rp_reply_local(), dialogue line pools
- `[PROMPT BUILDERS]` — build_story_prompt(), build_image_prompt()
- `[LOCAL COMPOSER]` — compose_story_local() (zero-token story path)

## server.py routes (Ctrl+F the path)

- `GET /` — UI
- `GET /api/options` — dropdown data
- `POST /api/story` — story generation (local composer default; `MEI_CHAT=1` env enables paid chat model)
- `POST /api/image` — image generation (agent-gw `generate_image` v2 + reference URLs)
- `POST /api/ref/{slot}` — upload reference (scene/character/pose)
- `DELETE /api/ref/{slot}` — clear reference
- `GET /ref/{slot}.png` — view reference
- `GET /api/gallery` — gallery JSON
- `GET /img/{name}` — serve image
- `GET/POST/DELETE /api/characters` — character CRUD
- `POST /api/rp/send` — roleplay message
- `GET/DELETE /api/rp/{cid}/history` — chat history

## Common fixes

- **Story loop / repeated beats** → `compose_story_local()` — beats count:
  `max(2, min(8, round(words / 120)))`; seed line controls reproducibility.
- **Image errors** → `image()` in server.py — envelope parser handles both
  `{"media": ...}` and `{"is_success": ...}` gateway shapes.
- **Upload errors** → `_to_public_url()` — reads `signed_url`, falls back to envelope.
- **Characters broken** → delete `data/characters.json`; it regenerates defaults.
- **Paid stories on** → `MEI_CHAT=1 uvicorn server:app --port 8000`

## Run

```bash
cd app
pip install -r requirements.txt
uvicorn server:app --port 8000
# open http://localhost:8000
```

Gateway: agent-gw (Moonshot). API key via `KIMI_API_KEY` env or `~/.kimi/agent-gw.json`.
