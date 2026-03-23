# VoiceTTS

A locally-hosted text-to-speech web app and API. No cloud, no API keys, no GPU required.
Built with [Piper TTS](https://github.com/rhasspy/piper), FastAPI, and React.

---

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

Open **http://localhost:8080** in your browser, or `http://<your-ip>:8080` from any device on the same network.

> First time using a voice: the model (~50 MB) downloads automatically. All subsequent runs are fully offline.

### Requirements

- Python 3.10–3.12
- Node.js 18+ (for the first frontend build only)
- ~500 MB free disk space

---

## API

The backend exposes three ways to generate speech — all return an `audio/wav` file.

### GET (simplest)

```
GET /api/tts?text=Hello+world
```

| Parameter  | Default                  | Description                    |
|------------|--------------------------|--------------------------------|
| `text`     | required                 | Text to speak (max 3000 chars) |
| `voice_id` | `en_US-lessac-medium`    | Voice to use                   |
| `speed`    | `1.0`                    | Speed multiplier (0.5–2.0)     |

**curl:**
```bash
curl "http://localhost:8080/api/tts?text=Hello+world" --output speech.wav
curl "http://localhost:8080/api/tts?text=Hello&voice_id=en_GB-alan-medium&speed=0.9" --output speech.wav
```

**JavaScript fetch:**
```javascript
const res = await fetch(`http://localhost:8080/api/tts?text=${encodeURIComponent("Hello world")}`);
const blob = await res.blob();
const url = URL.createObjectURL(blob);
```

### POST JSON

```
POST /api/tts/json
Content-Type: application/json
```

```json
{
  "text": "Hello world",
  "voice_id": "en_US-ryan-medium",
  "speed": 1.0
}
```

```bash
curl -X POST http://localhost:8080/api/tts/json \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice_id": "en_US-ryan-medium"}' \
  --output speech.wav
```

### POST Form (used by the web UI)

```
POST /api/tts
Content-Type: multipart/form-data
Fields: text, voice_id, speed
```

### Other endpoints

| Endpoint      | Method | Description                      |
|---------------|--------|----------------------------------|
| `/api/voices` | GET    | List all available voices        |
| `/api/health` | GET    | Health check → `{"status":"ok"}` |

---

## Available Voices

| ID                         | Name   | Gender | Accent   |
|----------------------------|--------|--------|----------|
| `en_US-lessac-medium`      | Lessac | F      | American |
| `en_US-ryan-medium`        | Ryan   | M      | American |
| `en_US-amy-medium`         | Amy    | F      | American |
| `en_US-joe-medium`         | Joe    | M      | American |
| `en_GB-jenny_dioco-medium` | Jenny  | F      | British  |
| `en_GB-alan-medium`        | Alan   | M      | British  |

---

## Deploy Under a Domain

1. Run `./start.sh` to build the frontend and start the server.
2. Copy `nginx.conf` to `/etc/nginx/sites-available/voice-tts`.
3. Replace `yourdomain.com` in the config, then enable:
   ```bash
   sudo ln -s /etc/nginx/sites-available/voice-tts /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Add HTTPS: `sudo certbot --nginx -d yourdomain.com`

---

## Project Structure

```
voice-tts/
├── backend/
│   ├── main.py              # FastAPI app — all API routes
│   ├── requirements.txt     # Python dependencies
│   ├── data/models/         # Downloaded .onnx voice models (gitignored)
│   └── static/              # Built React frontend (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts           # All fetch calls to the backend
│   │   ├── types.ts
│   │   └── components/
│   │       ├── Header.tsx
│   │       └── StudioPanel.tsx
│   ├── package.json
│   └── vite.config.ts       # Proxies /api → :8080 in dev mode
├── nginx.conf               # Production reverse proxy config
├── start.sh                 # One-command local launcher
└── docker-compose.yml       # Optional Docker deployment
```
