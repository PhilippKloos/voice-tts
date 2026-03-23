import io
import wave
import urllib.request
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
_loaded: dict = {}

def ensure_model(voice_id: str) -> Path:
    """Download voice model files if not present, return .onnx path."""
    info  = VOICE_MAP[voice_id]
    onnx  = MODELS_DIR / f"{voice_id}.onnx"
    config = MODELS_DIR / f"{voice_id}.onnx.json"
    if not onnx.exists():
        print(f"[TTS] Downloading {voice_id} model (~50 MB) …")
        urllib.request.urlretrieve(f"{HF_BASE}/{info['path']}.onnx",        onnx)
        urllib.request.urlretrieve(f"{HF_BASE}/{info['path']}.onnx.json",   config)
        print(f"[TTS] {voice_id} ready.")
    return onnx

def get_voice(voice_id: str):
    if voice_id not in _loaded:
        from piper.voice import PiperVoice
        onnx = ensure_model(voice_id)
        _loaded[voice_id] = PiperVoice.load(str(onnx))
    return _loaded[voice_id]

# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="VoiceTTS", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
