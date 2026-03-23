# VoiceTTS — Developer & Maintenance Handbook

This document covers how the project is structured, how to develop and debug it, how to add voices, and how to maintain it over time.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Local Development](#local-development)
4. [Backend Reference](#backend-reference)
5. [Frontend Reference](#frontend-reference)
6. [Adding Voices](#adding-voices)
7. [API Reference](#api-reference)
8. [Common Errors & Fixes](#common-errors--fixes)
9. [Maintenance Tasks](#maintenance-tasks)
10. [Deployment](#deployment)

---

## Architecture Overview

```
Browser / API client
       │
       ▼
FastAPI (port 8080)
  ├── GET/POST /api/tts   → Piper TTS engine → WAV bytes → response
  ├── GET /api/voices     → static list of voices
  ├── GET /api/health     → health check
  └── GET /*              → serves built React SPA (backend/static/)

Piper TTS
  ├── .onnx model files   → backend/data/models/   (downloaded on first use)
  └── piper-phonemize     → bundled espeak-ng (no system install needed)
```

**Key design decisions:**
- Everything runs on a single port (8080). FastAPI serves both the API and the React SPA.
- No database. Voices are a hardcoded list in `main.py`. Voice model files are stored on disk.
- No GPU required. Piper uses ONNX Runtime (CPU inference), generating speech in ~0.5–2 s.
- Model files are gitignored. They download automatically on first use from HuggingFace.

---

## Tech Stack

| Layer     | Technology          | Version  | Notes                                    |
|-----------|---------------------|----------|------------------------------------------|
| Backend   | Python              | 3.10–3.12| venv at `backend/.venv`                  |
| Backend   | FastAPI             | ≥0.111   | ASGI, async routes                       |
| Backend   | Uvicorn             | ≥0.29    | ASGI server, `--reload` in dev           |
| TTS       | piper-tts           | latest   | Wraps ONNX Runtime + piper-phonemize     |
| Frontend  | React + TypeScript  | 18 / 5   | Vite build tool                          |
| Frontend  | Tailwind CSS        | 3        | Utility-first styling                    |
| Frontend  | lucide-react        | latest   | Icons                                    |

---

## Local Development

### First run

```bash
./start.sh
```

This will:
1. Build the React frontend into `backend/static/`
2. Create a Python venv at `backend/.venv`
3. Install all Python deps
4. Start uvicorn with `--reload`

### Iterating on the backend

Uvicorn runs with `--reload` so any change to `backend/main.py` restarts the server automatically. No rebuild needed.

```bash
# Manually start backend only (after venv exists)
cd backend
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Iterating on the frontend

Run the Vite dev server separately — it proxies `/api` to the backend:

```bash
# Terminal 1 — backend
cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 — frontend dev server
cd frontend && npm run dev
# Open http://localhost:5173
```

The proxy is configured in `frontend/vite.config.ts`:
```typescript
proxy: {
  "/api": { target: "http://localhost:8080", changeOrigin: true }
}
```

### Rebuilding the frontend

```bash
./start.sh --rebuild
```

Or manually:
```bash
cd frontend && npm run build
# Output goes to backend/static/
```

---

## Backend Reference

### `backend/main.py`

All logic lives in this single file.

**Key sections:**

| Section | Lines | Purpose |
|---|---|---|
| `VOICES` list | ~21–34 | Declare available voices and their HuggingFace paths |
| `ensure_model()` | ~41–51 | Download `.onnx` + `.onnx.json` if not cached |
| `get_voice()` | ~53–58 | Lazy-load PiperVoice into memory, cache in `_loaded` dict |
| `_synthesize()` | ~85–112 | Core synthesis — validates input, runs Piper, returns WAV bytes |
| `_wav_response()` | ~114–122 | Wraps bytes in a FastAPI `Response` with correct headers |
| Routes | ~124–145 | Three TTS endpoints + voices + health |

**`_synthesize()` flow:**
```
text + voice_id + speed
    → validate inputs
    → get_voice(voice_id)          # loads model if not cached
        → ensure_model(voice_id)   # downloads .onnx if missing
    → PiperVoice.synthesize_wav()  # ONNX inference → PCM audio
    → write to io.BytesIO as WAV
    → return bytes
```

**Speed control:**
Piper uses `length_scale` (inverse of speed). `speed=2.0` → `length_scale=0.5` (shorter, faster).
```python
SynthesisConfig(length_scale=1.0 / speed)
```

**Voice model files:**
Each voice needs two files in `backend/data/models/`:
- `{voice_id}.onnx` — the neural network weights
- `{voice_id}.onnx.json` — phoneme config (sample rate, phoneme map, etc.)

### `backend/requirements.txt`

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9    # required for Form() parameters
piper-tts                   # pulls in onnxruntime + piper-phonemize
aiofiles>=23.2.1
```

To upgrade all deps:
```bash
cd backend
.venv/bin/pip install --upgrade -r requirements.txt
```

---

## Frontend Reference

### File map

```
frontend/src/
├── main.tsx          Entry point — mounts <App />
├── index.css         Tailwind directives + custom component classes (.btn, .card, .input)
├── types.ts          TypeScript interfaces: Voice
├── api.ts            All fetch() calls to /api — fetchVoices(), generateSpeech()
├── App.tsx           Root component — fetches voices, renders Header + StudioPanel
└── components/
    ├── Header.tsx    Top bar with logo
    └── StudioPanel.tsx  Voice picker grid + speed slider + text area + audio player
```

### `api.ts` — backend interface

```typescript
fetchVoices()                              // GET /api/voices
generateSpeech(text, voiceId, speed)       // POST /api/tts (form)
```

To call a different endpoint (e.g. switch to JSON POST), edit `generateSpeech()` in `api.ts`.

### Adding a new UI control

1. Add state in `StudioPanel.tsx`
2. Pass the value to `generateSpeech()` in `api.ts`
3. Add the form field in the `tts_form` route in `main.py`

### Tailwind custom classes

Defined in `frontend/src/index.css`:

| Class | What it is |
|---|---|
| `.btn-primary` | Purple filled button |
| `.btn-ghost` | Transparent bordered button |
| `.btn-danger` | Red tinted button |
| `.card` | Dark rounded panel |
| `.input` | Dark text input / textarea |
| `.label` | Small uppercase field label |
| `.badge` | Small pill tag |

---

## Adding Voices

Piper voices are published at:
`https://huggingface.co/rhasspy/piper-voices`

To add a new voice:

1. Find the voice on HuggingFace. The path format is:
   `{lang}/{lang_region}/{name}/{quality}/{lang_region}-{name}-{quality}`
   e.g. `en/en_US/ljspeech/high/en_US-ljspeech-high`

2. Add an entry to `VOICES` in `backend/main.py`:
   ```python
   {"id": "en_US-ljspeech-high", "name": "LJSpeech", "gender": "F", "accent": "American",
    "path": "en/en_US/ljspeech/high/en_US-ljspeech-high"},
   ```

3. The model downloads automatically on first use. No restart needed.

**Quality tiers** (affects model size and speed):
| Quality | Size  | Speed on CPU |
|---------|-------|--------------|
| `low`   | ~15 MB | Very fast   |
| `medium`| ~50 MB | Fast        |
| `high`  | ~100 MB| Moderate   |

**Other languages:** Piper supports 30+ languages. Browse voices at:
`https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0`

---

## API Reference

### `GET /api/health`
Returns `{"status": "ok"}`. Use for uptime monitoring.

### `GET /api/voices`
Returns the full voice list.
```json
{
  "voices": [
    {"id": "en_US-lessac-medium", "name": "Lessac", "gender": "F", "accent": "American"}
  ]
}
```

### `GET /api/tts`
| Param | Type | Default | Notes |
|---|---|---|---|
| `text` | string | required | Max 3000 chars |
| `voice_id` | string | `en_US-lessac-medium` | Must be in VOICES list |
| `speed` | float | `1.0` | Range: 0.5–2.0 |

Returns: `audio/wav`

### `POST /api/tts/json`
Body (JSON):
```json
{"text": "...", "voice_id": "...", "speed": 1.0}
```
Returns: `audio/wav`

### `POST /api/tts`
Body (multipart/form-data): `text`, `voice_id`, `speed`
Returns: `audio/wav`

---

## Common Errors & Fixes

### `TTS synthesis failed: 'PiperVoice' object has no attribute 'X'`
The installed piper-tts version has a different API. Check available methods:
```bash
backend/.venv/bin/python -c "from piper.voice import PiperVoice; print(dir(PiperVoice))"
```
Then update the call in `_synthesize()` in `main.py` accordingly.

### `TTS synthesis failed: # channels not specified`
The `wave.Wave_write` object needs its format set before writing. Make sure `set_wav_format=True` is passed to `synthesize_wav()`.

### Model download fails / hangs
HuggingFace may be temporarily slow. The model files can also be downloaded manually:
```bash
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
VOICE="en_US-lessac-medium"
curl -L "$BASE/en/en_US/lessac/medium/$VOICE.onnx" -o "backend/data/models/$VOICE.onnx"
curl -L "$BASE/en/en_US/lessac/medium/$VOICE.onnx.json" -o "backend/data/models/$VOICE.onnx.json"
```

### Frontend build fails with TypeScript errors
```bash
cd frontend && npx tsc --noEmit
```
Check `src/types.ts` is in sync with what the backend actually returns from `/api/voices`.

### Port 8080 already in use
```bash
lsof -i :8080          # find the process
kill <PID>
```
Or change the port in `start.sh`.

### `npm: command not found` in start.sh
nvm is not sourced in non-interactive shells. The script handles this automatically via:
```bash
source "$HOME/.nvm/nvm.sh"
```
If it still fails, run `nvm use --lts` manually first.

### Disk space during install
`piper-tts` pulls in PyTorch as a transitive dependency (~2 GB). If you're low on space, clear caches first:
```bash
pip cache purge
rm -rf ~/.cache/huggingface
```

---

## Maintenance Tasks

### Updating Python dependencies

```bash
cd backend
.venv/bin/pip install --upgrade -r requirements.txt
```

To pin current versions (for reproducibility):
```bash
.venv/bin/pip freeze > requirements.lock
```

### Updating frontend dependencies

```bash
cd frontend
npm update
npm audit fix
```

### Clearing downloaded voice models

```bash
rm -rf backend/data/models/
```
Models re-download on next use.

### Checking what's using disk

```bash
du -sh backend/data/models/*    # voice models
du -sh backend/.venv            # Python venv (~300 MB)
du -sh frontend/node_modules    # npm packages (~150 MB)
```

### Viewing logs

If running via `start.sh`, logs print directly to the terminal. To run in background with logs:
```bash
nohup ./start.sh > /tmp/voicetts.log 2>&1 &
tail -f /tmp/voicetts.log
```

---

## Deployment

### Local network (current setup)
```bash
./start.sh
# Accessible at http://<machine-ip>:8080 from any device on the same network
```

### systemd service (run on boot)

Create `/etc/systemd/system/voicetts.service`:
```ini
[Unit]
Description=VoiceTTS
After=network.target

[Service]
User=philipp
WorkingDirectory=/home/philipp/Programming/projects in the working /voice-tts/backend
ExecStart=/home/philipp/Programming/projects in the working /voice-tts/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable voicetts
sudo systemctl start voicetts
sudo journalctl -u voicetts -f   # view logs
```

### Behind nginx (domain deployment)

See `nginx.conf` in the project root. Key settings:
- `proxy_read_timeout 30s` — TTS can take a few seconds for long text
- `client_max_body_size 1M` — text-only, so 1 MB is plenty

```bash
sudo cp nginx.conf /etc/nginx/sites-available/voice-tts
# Edit: replace yourdomain.com
sudo ln -s /etc/nginx/sites-available/voice-tts /etc/nginx/sites-enabled/
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

### Docker

```bash
# Build frontend first
cd frontend && npm run build && cd ..

# Build and run
docker compose up -d
```

The `docker-compose.yml` mounts `backend/static` (built frontend) and a named volume for voice model persistence.
