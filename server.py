#!/usr/bin/env python3
# ============================================================================
# FILE: server.py  —  PROJECT ROOT: /mnt/agents/output/app/
# ROLE: Web layer only. All creative logic lives in engine.py.
#   ROUTE MAP:
#     GET  /                  UI
#     GET  /api/options       dropdown data (personas, genres, refs state)
#     POST /api/story         story generation   <- token-saving switch: MEI_CHAT env
#     POST /api/image         image generation (agent-gw, v2, + references)
#     POST /api/ref/{slot}    upload scene/character/pose reference (overrides)
#     DELETE /api/ref/{slot}  clear a reference
#     GET  /ref/{slot}.png    view a reference
#     GET  /api/gallery       preview gallery JSON
#     GET  /img/{name}        serve generated image
#   FIX POINTS:
#     - story fallback/loops  -> story() below (chat try/except)
#     - image failures        -> image() below (gateway envelope parsing)
#     - upload failures       -> _to_public_url() (signed_url extraction)
# ============================================================================
"""Personal Story & Image Generator — FastAPI backend.

Gateway: agent-gw (Moonshot agent gateway SDK).
  - Images: client.tools.generate_image(description, size, reference_image_urls)
  - Uploads: client.upload_storage(...) -> public signed_url (required,
    because the gateway only accepts PUBLIC reference URLs).
  - Stories: client.chat_completion(model='kimi-for-coding') with local
    composer fallback when the credential can't reach chat.
Reference precedence: user-uploaded files override everything. If a slot
has no upload, any saved defaults are used; otherwise the slot is empty.
"""
import os, re, uuid, json, hashlib, traceback, logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("creative-engine")
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine import (CONTENT_TYPE, DARK_FICTION_GENRES, DARK_HUMOR_STYLES,
                    DARK_ART_STYLES, REALISM_STYLES, GOTHIC_ROMANCE_STYLES,
                    MATURE_THEMES, PERSONAS,
                    verify_safety, build_story_prompt, build_image_prompt,
                    compose_story_local, SAFETY_REFUSAL, RP_RULES,
                    rp_reply_local)

# Token-saving: stories use the free local composer by default.
# Set MEI_CHAT=1 in the environment to re-enable the paid chat model.
USE_CHAT = os.environ.get("MEI_CHAT", "") == "1"

app = FastAPI(title="Personal Creative Engine v7")
BASE = os.path.dirname(__file__)
IMG_DIR = os.path.join(BASE, "generated")
UP_DIR = os.path.join(BASE, "uploads")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(UP_DIR, exist_ok=True)

# Reference slots: scene / character / pose-creativity.
# User uploads (refs/<slot>.png) ALWAYS override defaults (defaults/<slot>.png).
REF_SLOTS = ["scene", "character", "pose"]
DEFAULTS_DIR = os.path.join(UP_DIR, "defaults")
REFS_DIR = os.path.join(UP_DIR, "refs")
os.makedirs(DEFAULTS_DIR, exist_ok=True)
os.makedirs(REFS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Character cards + RP chat history — JSON persistence (Supabase-ready schema)
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CHARS_FILE = os.path.join(DATA_DIR, "characters.json")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
TRAINERS_FILE = os.path.join(DATA_DIR, "trainers.json")

# Named character/scene trainer images: many per kind, each with a
# description + active flag. Active ones are injected into every image
# generation ("match this character exactly") and uploaded as references.
TRAINER_KINDS = ["character", "scene", "pose"]
TRAINER_DIR = os.path.join(UP_DIR, "trainers")
for k in TRAINER_KINDS:
    os.makedirs(os.path.join(TRAINER_DIR, k), exist_ok=True)


def _load_json(path, default):
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


DEFAULT_CHARACTERS = [
    {"id": "mei", "name": "Mei", "speech_style": "precise, ironic, dry",
     "catchphrase": "Ask me something real.",
     "default_line": "Say what you came to say.",
     "soft_line": "don't make this harder.",
     "pronouns": "she",
     "card": "Razor-sharp, all-genre writer's mind. Doesn't flatter, doesn't fill silence."},
    {"id": "georgia", "name": "Georgia", "speech_style": "slow, honey-and-ash",
     "catchphrase": "Sugar, everybody in this town lies. I'm just honest about it.",
     "default_line": "Sit down. Sweet tea's already poured.",
     "soft_line": "you stay right where I can see you.",
     "pronouns": "she",
     "card": "Southern gothic matriarch. Warm until she isn't. Knows everyone's sins."},
    {"id": "zoey", "name": "Zoey", "speech_style": "fast, chaotic, bitingly funny",
     "catchphrase": "Okay so that's either the best or worst idea I've heard today and it's 50/50.",
     "default_line": "Please tell me there's a plan and you just haven't told me the plan.",
     "soft_line": "...don't go, okay?",
     "pronouns": "she",
     "card": "Chaotic absurdist with a good heart and catastrophic impulse control."},
    {"id": "scarlet", "name": "Scarlet", "speech_style": "low, velvet, unhurried",
     "catchphrase": "Darling, I never lie. I just let men arrange the truth.",
     "default_line": "You've been watching me for ten minutes. Say something worth the stare.",
     "soft_line": "you're the one thing I didn't plan for.",
     "pronouns": "she",
     "card": "Flame-haired femme fatale. Smiles like a knife. Never the one who burns."},
]


class GenRequest(BaseModel):
    topic: str
    power: int = 7
    harshness: int = 7
    content: str = "UNLEASHED"
    genre: str = "NOIR"
    humor: str = "DARK_SATIRE"
    themes: list = []
    art_style: str = "DARK_SATIRE"
    gruesome: int = 1
    persona: str = "Mei"
    words: int = 500
    size: str = "1024x1024"
    use_references: bool = True
    # per-slot overrides: "upload" (default), "default", "none"
    ref_mode: dict = {}
    # named trainer ids to activate for this generation (empty = all active)
    trainer_ids: list = []


def _clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def _pick(d, key, default):
    return key if key in d else default


def _ref_files(req: GenRequest):
    """Files win over defaults. Mode: 'upload'|'default'|'none'."""
    files = []
    for slot in REF_SLOTS:
        mode = (req.ref_mode or {}).get(slot, "upload")
        if mode == "none":
            continue
        upload = os.path.join(REFS_DIR, f"{slot}.png")
        default = os.path.join(DEFAULTS_DIR, f"{slot}.png")
        if mode == "default":
            if os.path.isfile(default):
                files.append((slot, default))
        else:
            if os.path.isfile(upload):
                files.append((slot, upload))          # user file overrides
            elif os.path.isfile(default):
                files.append((slot, default))         # fallback to default
    return files


def _client():
    from agent_gw import AgentGwClient
    return AgentGwClient(timeout=450.0)


def _unwrap(resp):
    """Normalise every agent-gw response shape to a plain dict.
    Handles: raw dicts, ToolResponse wrappers, and the
    {"result": {"user": [{"text": "<json>"}]}} envelope."""
    raw = resp.raw if hasattr(resp, "raw") else resp
    if not isinstance(raw, dict):
        raise RuntimeError(f"unexpected gateway response type: {type(raw)}")
    if "result" in raw and isinstance(raw["result"], dict):
        user = raw["result"].get("user")
        if user and isinstance(user[0].get("text"), str):
            return json.loads(user[0]["text"])
    return raw


# Cache reference uploads: same file bytes -> reuse the public URL.
# Without this, every image generation re-uploads every reference.
_ref_url_cache = {}

def _to_public_url(client, path):
    """Upload a local reference via gateway storage -> public URL (cached)."""
    with open(path, "rb") as f:
        data = f.read()
    key = hashlib.sha256(data).hexdigest()
    if key in _ref_url_cache:
        return _ref_url_cache[key]
    resp = client.upload_storage(data, filename=os.path.basename(path),
                                 content_type="image/png")
    raw = _unwrap(resp)
    url = raw.get("signed_url") or raw.get("url")
    if not url:
        raise RuntimeError(f"upload returned no URL: {raw}")
    _ref_url_cache[key] = url
    return url


def _validate_size(size: str) -> str:
    """Gateway v2 size contract: multiples of 16, <=3840, ratio <= 3:1."""
    try:
        w, h = (int(x) for x in size.split("x"))
    except ValueError:
        raise ValueError(f"invalid size '{size}'; expected WIDTHxHEIGHT")
    if w <= 0 or h <= 0 or w % 16 or h % 16:
        raise ValueError(f"dimensions must be positive multiples of 16, got {w}x{h}")
    if w > 3840 or h > 3840:
        raise ValueError(f"dimensions cannot exceed 3840, got {w}x{h}")
    if max(w, h) / min(w, h) > 3:
        raise ValueError(f"aspect ratio cannot exceed 3:1, got {w}x{h}")
    if not (655360 <= w * h <= 8294400):
        raise ValueError(f"total pixels must be 655360..8294400, got {w * h}")
    return size


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "index.html"))


@app.get("/api/options")
def options():
    return {
        "personas": list(PERSONAS),
        "content_types": [c.name for c in CONTENT_TYPE],
        "genres": list(DARK_FICTION_GENRES),
        "humor_styles": list(DARK_HUMOR_STYLES),
        "art_styles": list(DARK_ART_STYLES),
        "realism_styles": list(REALISM_STYLES),
        "gothic_romance_styles": list(GOTHIC_ROMANCE_STYLES),
        "themes": list(MATURE_THEMES),
        "ref_slots": REF_SLOTS,
        "refs": {
            slot: {
                "upload": os.path.isfile(os.path.join(REFS_DIR, f"{slot}.png")),
                "default": os.path.isfile(os.path.join(DEFAULTS_DIR, f"{slot}.png")),
            } for slot in REF_SLOTS
        },
    }


# ---------------------------------------------------------------------------
# Reference upload / management — user files override defaults
# ---------------------------------------------------------------------------

@app.post("/api/ref/{slot}")
async def upload_ref(slot: str, file: UploadFile = File(...)):
    if slot not in REF_SLOTS:
        return JSONResponse({"error": f"unknown slot {slot}"}, status_code=404)
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)
    out = os.path.join(REFS_DIR, f"{slot}.png")
    with open(out, "wb") as f:
        f.write(data)
    return {"ok": True, "slot": slot, "bytes": len(data),
            "note": "upload overrides default for this slot"}


@app.delete("/api/ref/{slot}")
def delete_ref(slot: str, which: str = "upload"):
    target = REFS_DIR if which == "upload" else DEFAULTS_DIR
    p = os.path.join(target, f"{slot}.png")
    if os.path.isfile(p):
        os.remove(p)
    return {"ok": True}


@app.get("/ref/{slot}.png")
def get_ref(slot: str, which: str = "upload"):
    target = REFS_DIR if which == "upload" else DEFAULTS_DIR
    p = os.path.join(target, f"{slot}.png")
    if os.path.isfile(p):
        return FileResponse(p)
    return JSONResponse({"error": "not set"}, status_code=404)


# ---------------------------------------------------------------------------
# Preview gallery
# ---------------------------------------------------------------------------

@app.get("/api/gallery")
def gallery():
    items = []
    for name in sorted(os.listdir(IMG_DIR), reverse=True):
        if name.endswith((".png", ".jpg")):
            items.append({"name": name, "url": f"/img/{name}",
                          "time": os.path.getmtime(os.path.join(IMG_DIR, name))})
    return {"images": items}


# ---------------------------------------------------------------------------
# Story
# ---------------------------------------------------------------------------

@app.post("/api/story")
def story(req: GenRequest):
    ok, violation = verify_safety(req.topic)
    if not ok:
        return JSONResponse({"error": SAFETY_REFUSAL, "violation": violation},
                            status_code=422)
    power = _clamp(req.power, 1, 10)
    harsh = _clamp(req.harshness, 1, 10)
    genre = _pick(DARK_FICTION_GENRES, req.genre, "NOIR")
    humor = _pick(DARK_HUMOR_STYLES, req.humor, "DARK_SATIRE")
    themes = [t for t in req.themes if t in MATURE_THEMES][:5] or \
             ["MORAL_AMBIGUITY", "DARK_PSYCHOLOGY", "BETRAYAL"]
    words = _clamp(req.words, 100, 2000)
    gruesome = _clamp(req.gruesome, 1, 10)
    persona = req.persona if req.persona in PERSONAS else "Mei"
    prompt = build_story_prompt(req.topic, genre, humor, themes, power, harsh,
                                words, gruesome, persona_name=persona)
    # TOKEN-SAVING: local composer is the default story path (free).
    # Set env MEI_CHAT=1 to attempt the paid chat model first.
    if USE_CHAT:
        try:
            client = _client()
            resp = client.chat_completion(
                model="kimi-for-coding",
                messages=[{"role": "user", "content": prompt}],
                timeout=120.0,
            )
            text = resp["choices"][0]["message"]["content"]
            return {"story": text, "engine_prompt": prompt, "source": "chat-model"}
        except Exception as e:
            log.warning("chat model failed, falling back to composer: %s", e)
    text = compose_story_local(req.topic, genre, humor, themes, power, harsh,
                               words, persona)
    return {"story": text, "engine_prompt": prompt, "source": "local-composer"}


# ---------------------------------------------------------------------------
# Image (with reference slots)
# ---------------------------------------------------------------------------

@app.post("/api/image")
def image(req: GenRequest):
    ok, violation = verify_safety(req.topic)
    if not ok:
        return JSONResponse({"error": SAFETY_REFUSAL, "violation": violation},
                            status_code=422)
    power = _clamp(req.power, 1, 10)
    harsh = _clamp(req.harshness, 1, 10)
    art_style = _pick({**DARK_ART_STYLES, **REALISM_STYLES,
                       **GOTHIC_ROMANCE_STYLES}, req.art_style, "DARK_SATIRE")
    gruesome = _clamp(req.gruesome, 1, 10)
    try:
        size = _validate_size(req.size)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    trainers = _active_trainers(req)
    desc = build_image_prompt(req.topic, art_style, power, harsh, gruesome,
                              trainer_notes=[t.get("description", "")
                                             for t in trainers])
    out = os.path.join(IMG_DIR, f"{uuid.uuid4().hex}.png")
    try:
        import requests
        client = _client()
        ref_urls = []
        if req.use_references:
            for slot, path in _ref_files(req):
                ref_urls.append(_to_public_url(client, path))
            for t in trainers:
                ref_urls.append(_to_public_url(client, t["path"]))
        kwargs = dict(description=desc, size=size, version="v2", timeout=450.0)
        if ref_urls:
            kwargs["reference_image_urls"] = ref_urls
        resp = client.tools.generate_image(**kwargs)
        raw = _unwrap(resp)
        if raw.get("is_success") is False:
            raise RuntimeError(f"gateway error: {raw.get('error')}")
        url = raw.get("media", {}).get("url")
        if not url:
            raise RuntimeError(f"no media URL in gateway response: {str(raw)[:200]}")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(out, "wb") as f:
            f.write(r.content)
        log.info("image saved %s refs=%s", os.path.basename(out),
                 [s for s, _ in _ref_files(req)])
        return {"path": f"/img/{os.path.basename(out)}", "prompt": desc,
                "references_used": [s for s, _ in _ref_files(req)]}
    except Exception as e:
        log.error("image generation failed: %s\n%s", e, traceback.format_exc())
        return JSONResponse({"error": f"Image generation failed: {e}"}, status_code=500)


# ---------------------------------------------------------------------------
# Trainer roster — named character/scene/pose references with descriptions
# ---------------------------------------------------------------------------

def _trainers():
    return _load_json(TRAINERS_FILE, [])


@app.get("/api/trainers")
def list_trainers():
    return {"trainers": _trainers()}


class TrainerIn(BaseModel):
    name: str
    kind: str = "character"        # character | scene | pose
    description: str = ""          # "must match: pale, scar over left eye, ..."
    active: bool = True


@app.post("/api/trainers")
async def create_trainer(name: str = Form(...), kind: str = Form("character"),
                         description: str = Form(""), file: UploadFile = File(...)):
    if kind not in TRAINER_KINDS:
        return JSONResponse({"error": f"kind must be one of {TRAINER_KINDS}"}, status_code=400)
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)
    tid = uuid.uuid4().hex[:8]
    path = os.path.join(TRAINER_DIR, kind, f"{tid}.png")
    with open(path, "wb") as f:
        f.write(data)
    trainers = _trainers()
    entry = {"id": tid, "name": name, "kind": kind, "description": description,
             "active": True, "path": path}
    trainers.append(entry)
    _save_json(TRAINERS_FILE, trainers)
    log.info("trainer created: %s (%s)", name, kind)
    return entry


@app.delete("/api/trainers/{tid}")
def delete_trainer(tid: str):
    trainers = _trainers()
    for t in trainers:
        if t["id"] == tid and os.path.isfile(t["path"]):
            os.remove(t["path"])
    trainers = [t for t in trainers if t["id"] != tid]
    _save_json(TRAINERS_FILE, trainers)
    return {"ok": True}


@app.post("/api/trainers/{tid}/toggle")
def toggle_trainer(tid: str):
    trainers = _trainers()
    for t in trainers:
        if t["id"] == tid:
            t["active"] = not t.get("active", True)
    _save_json(TRAINERS_FILE, trainers)
    return {"ok": True}


@app.get("/trainer-img/{tid}.png")
def trainer_img(tid: str):
    safe = re.sub(r"[^a-f0-9]", "", tid)
    for k in TRAINER_KINDS:
        p = os.path.join(TRAINER_DIR, k, f"{safe}.png")
        if os.path.isfile(p):
            return FileResponse(p)
    return JSONResponse({"error": "not found"}, status_code=404)


def _active_trainers(req: GenRequest):
    """Selected trainers for this run: req.trainer_ids if given, else all active."""
    ts = _trainers()
    if req.trainer_ids:
        ts = [t for t in ts if t["id"] in req.trainer_ids]
    else:
        ts = [t for t in ts if t.get("active")]
    return [t for t in ts if os.path.isfile(t["path"])]


# ---------------------------------------------------------------------------
# Character cards + roleplay chat
# ---------------------------------------------------------------------------

class CharIn(BaseModel):
    name: str
    speech_style: str = ""
    catchphrase: str = ""
    default_line: str = ""
    soft_line: str = ""
    pronouns: str = "she"
    card: str = ""


class RpMsg(BaseModel):
    character_id: str
    message: str
    tone: int = 5          # 1=soft .. 10=hostile
    persona: str = ""      # unused by local composer; reserved


@app.get("/api/characters")
def list_chars():
    chars = _load_json(CHARS_FILE, None)
    if chars is None:
        chars = DEFAULT_CHARACTERS
        _save_json(CHARS_FILE, chars)
    return {"characters": chars}


@app.post("/api/characters")
def create_char(c: CharIn):
    chars = _load_json(CHARS_FILE, list(DEFAULT_CHARACTERS))
    entry = {"id": uuid.uuid4().hex[:8],
             **(c.model_dump() if hasattr(c, "model_dump") else c.dict())}
    chars.append(entry)
    _save_json(CHARS_FILE, chars)
    return entry


@app.delete("/api/characters/{cid}")
def delete_char(cid: str):
    chars = _load_json(CHARS_FILE, [])
    chars = [c for c in chars if c.get("id") != cid]
    _save_json(CHARS_FILE, chars)
    # also drop its chat history
    chats = _load_json(CHATS_FILE, {})
    chats.pop(cid, None)
    _save_json(CHATS_FILE, chats)
    return {"ok": True}


@app.get("/api/rp/{cid}/history")
def rp_history(cid: str):
    chats = _load_json(CHATS_FILE, {})
    return {"messages": chats.get(cid, [])[-100:]}


@app.post("/api/rp/send")
def rp_send(msg: RpMsg):
    ok, violation = verify_safety(msg.message)
    if not ok:
        return JSONResponse({"error": SAFETY_REFUSAL, "violation": violation},
                            status_code=422)
    chars = _load_json(CHARS_FILE, list(DEFAULT_CHARACTERS))
    char = next((c for c in chars if c.get("id") == msg.character_id), None)
    if not char:
        return JSONResponse({"error": "character not found"}, status_code=404)
    chats = _load_json(CHATS_FILE, {})
    hist = chats.setdefault(msg.character_id, [])
    hist.append({"role": "user", "text": msg.message})
    reply = rp_reply_local(char, msg.message, hist, tone=_clamp(msg.tone, 1, 10))
    hist.append({"role": "char", "text": reply, "name": char.get("name")})
    hist[:] = hist[-100:]          # cap history per character
    _save_json(CHATS_FILE, chats)
    return {"reply": reply, "history": hist}


@app.delete("/api/rp/{cid}/history")
def rp_reset(cid: str):
    chats = _load_json(CHATS_FILE, {})
    chats.pop(cid, None)
    _save_json(CHATS_FILE, chats)
    return {"ok": True}


@app.get("/img/{name}")
def get_img(name: str):
    safe = re.sub(r"[^a-f0-9.]", "", name)
    p = os.path.join(IMG_DIR, safe)
    if os.path.isfile(p):
        return FileResponse(p)
    return JSONResponse({"error": "not found"}, status_code=404)


app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
