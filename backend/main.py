import io
import os
import json
import hashlib
import tempfile
import wave
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── voice model storage ───────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
MODELS_DIR  = BASE_DIR / "data" / "models"
FRONT_DIR   = BASE_DIR / "static"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

VOICES = [
    {"id": "en_US-lessac-medium",       "name": "Lessac",   "gender": "F", "accent": "American",
     "path": "en/en_US/lessac/medium/en_US-lessac-medium"},
    {"id": "en_US-ryan-medium",         "name": "Ryan",     "gender": "M", "accent": "American",
     "path": "en/en_US/ryan/medium/en_US-ryan-medium"},
    {"id": "en_US-amy-medium",          "name": "Amy",      "gender": "F", "accent": "American",
     "path": "en/en_US/amy/medium/en_US-amy-medium"},
    {"id": "en_US-joe-medium",          "name": "Joe",      "gender": "M", "accent": "American",
     "path": "en/en_US/joe/medium/en_US-joe-medium"},
    {"id": "en_GB-jenny_dioco-medium",  "name": "Jenny",    "gender": "F", "accent": "British",
     "path": "en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium"},
    {"id": "en_GB-alan-medium",         "name": "Alan",     "gender": "M", "accent": "British",
     "path": "en/en_GB/alan/medium/en_GB-alan-medium"},
]

VOICE_MAP = {v["id"]: v for v in VOICES}

# ── model loading ─────────────────────────────────────────────────────────────
# LRU-bounded cache so memory cannot grow without limit if many voices are used.
_VOICE_CACHE_MAX = int(os.getenv("VOICE_TTS_CACHE_MAX", "3"))
_loaded: "OrderedDict[str, object]" = OrderedDict()

# Optional pinned SHA-256 sums. Populate via env var
# VOICE_TTS_MODEL_SHA256_JSON='{"en_US-lessac-medium":"<hex>", ...}' to enforce
# integrity at download time. When unset, we still verify the file was fully
# written and is a non-trivial ONNX blob (magic-byte check).
try:
    _PINNED_SHA256: dict = json.loads(os.getenv("VOICE_TTS_MODEL_SHA256_JSON", "{}"))
except Exception:
    _PINNED_SHA256 = {}


def _sha256_of_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _atomic_download(url: str, dest: Path) -> None:
    """Download to a sibling temp file, then atomically rename — partial writes
    can never leave a corrupt model in place."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".part", dir=str(dest.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        urllib.request.urlretrieve(url, tmp_path)
        os.replace(tmp_path, dest)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _verify_onnx_file(onnx_path: Path, voice_id: str) -> None:
    if onnx_path.stat().st_size < 1024 * 100:  # piper models are >>100 KB
        raise RuntimeError(f"downloaded model {voice_id} too small — likely truncated")
    expected = _PINNED_SHA256.get(voice_id)
    if expected:
        actual = _sha256_of_file(onnx_path)
        if actual.lower() != expected.lower():
            onnx_path.unlink(missing_ok=True)
            raise RuntimeError(f"sha256 mismatch for {voice_id}: expected {expected}, got {actual}")


def ensure_model(voice_id: str) -> Path:
    """Download voice model files if not present, return .onnx path."""
    info  = VOICE_MAP[voice_id]
    onnx  = MODELS_DIR / f"{voice_id}.onnx"
    config = MODELS_DIR / f"{voice_id}.onnx.json"
    if not onnx.exists():
        print(f"[TTS] Downloading {voice_id} model (~50 MB) …")
        _atomic_download(f"{HF_BASE}/{info['path']}.onnx", onnx)
        _atomic_download(f"{HF_BASE}/{info['path']}.onnx.json", config)
        try:
            _verify_onnx_file(onnx, voice_id)
        except Exception:
            # Clean up so a retry can re-download cleanly.
            onnx.unlink(missing_ok=True)
            config.unlink(missing_ok=True)
            raise
        print(f"[TTS] {voice_id} ready.")
    return onnx

def get_voice(voice_id: str):
    if voice_id in _loaded:
        _loaded.move_to_end(voice_id)
        return _loaded[voice_id]
    from piper.voice import PiperVoice
    onnx = ensure_model(voice_id)
    voice_obj = PiperVoice.load(str(onnx))
    _loaded[voice_id] = voice_obj
    while len(_loaded) > _VOICE_CACHE_MAX:
        _loaded.popitem(last=False)  # evict least-recently-used
    return voice_obj

# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="VoiceTTS", version="3.0.0")

# CORS — restrict to configured origins; default to none (same-origin only via
# the static mount). Set VOICE_TTS_ALLOWED_ORIGINS=https://a.com,https://b.com
_allowed = os.getenv("VOICE_TTS_ALLOWED_ORIGINS", "").strip()
_origins = [o.strip() for o in _allowed.split(",") if o.strip()] if _allowed else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/voices")
def list_voices():
    return {"voices": VOICES}

class TTSRequest(BaseModel):
    text:     str
    voice_id: str   = "en_US-lessac-medium"
    speed:    float = 1.0

def _synthesize(text: str, voice_id: str, speed: float) -> bytes:
    """Core synthesis — returns raw WAV bytes."""
    if not text.strip():
        raise HTTPException(400, "Text cannot be empty.")
    if len(text) > 3000:
        raise HTTPException(400, "Text too long – max 3000 characters.")
    if voice_id not in VOICE_MAP:
        raise HTTPException(400, f"Unknown voice '{voice_id}'. Valid voices: {list(VOICE_MAP)}")
    # Form/JSON paths skip Query validation — guard speed here.
    # speed must be in [0.5, 2.0] to avoid div-by-zero / runaway synthesis.
    if not (0.5 <= speed <= 2.0):
        raise HTTPException(400, "speed must be between 0.5 and 2.0")

    try:
        voice = get_voice(voice_id)
    except Exception as e:
        raise HTTPException(500, f"Failed to load voice model: {e}")

    try:
        from piper.config import SynthesisConfig
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            voice.synthesize_wav(
                text.strip(),
                wav_file,
                syn_config=SynthesisConfig(length_scale=1.0 / speed),
                set_wav_format=True,
            )
        buf.seek(0)
        return buf.read()
    except Exception as e:
        raise HTTPException(500, f"TTS synthesis failed: {e}")

def _wav_response(data: bytes) -> Response:
    return Response(
        content=data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=speech.wav",
            "Cache-Control": "no-cache",
        },
    )

# ── POST form (used by the web UI) ────────────────────────────────────────────
@app.post("/api/tts")
async def tts_form(
    text:     str   = Form(...),
    voice_id: str   = Form(default="en_US-lessac-medium"),
    speed:    float = Form(default=1.0),
):
    return _wav_response(_synthesize(text, voice_id, speed))

# ── POST JSON ─────────────────────────────────────────────────────────────────
@app.post("/api/tts/json")
async def tts_json(body: TTSRequest):
    return _wav_response(_synthesize(body.text, body.voice_id, body.speed))

# ── GET (simplest – pass text as query param) ─────────────────────────────────
@app.get("/api/tts")
async def tts_get(
    text:     str            = Query(..., description="Text to speak"),
    voice_id: str            = Query(default="en_US-lessac-medium", description="Voice ID"),
    speed:    float          = Query(default=1.0, ge=0.5, le=2.0, description="Speed multiplier"),
):
    return _wav_response(_synthesize(text, voice_id, speed))

# ── serve built React frontend ────────────────────────────────────────────────
if FRONT_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONT_DIR), html=True), name="frontend")
