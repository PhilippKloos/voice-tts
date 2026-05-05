# voice-tts

A self-hosted text-to-speech web app and HTTP API, built on [Piper](https://github.com/rhasspy/piper).
Runs entirely on CPU. Voice models download on first use and cache locally; no further network access is required.

## Stack

- Backend: Python 3.10+, FastAPI, Piper TTS
- Frontend: React + Vite (TypeScript)
- Reverse proxy: nginx (optional, for production)

## Install and run

```bash
git clone https://github.com/PhilippKloos/voice-tts
cd voice-tts
chmod +x start.sh
./start.sh
```

`start.sh` builds the frontend, installs Python dependencies into a venv, and starts the FastAPI server on port 8080.

Open `http://localhost:8080`.

The first request for a voice downloads its `.onnx` model (~50 MB). All subsequent requests are offline.

### Requirements

- Python 3.10–3.12
- Node.js 18+ (frontend build only)
- ~500 MB disk for models and node_modules

## API

All endpoints return `audio/wav`.

```
GET  /api/tts?text=Hello&voice_id=en_US-ryan-medium&speed=1.0
POST /api/tts/json    { "text": "...", "voice_id": "...", "speed": 1.0 }
POST /api/tts         (multipart form, used by the UI)
GET  /api/voices      list available voices
GET  /api/health
```

`text` is capped at 3000 characters. `speed` accepts 0.5–2.0.

```bash
curl "http://localhost:8080/api/tts?text=Hello+world" -o speech.wav
```

## Voices

| ID | Accent | Gender |
| --- | --- | --- |
| `en_US-lessac-medium` | American | F |
| `en_US-ryan-medium` | American | M |
| `en_US-amy-medium` | American | F |
| `en_US-joe-medium` | American | M |
| `en_GB-jenny_dioco-medium` | British | F |
| `en_GB-alan-medium` | British | M |

## Production deployment

`nginx.conf` is a sample reverse-proxy config. Replace `yourdomain.com`, symlink into `sites-enabled`, then provision TLS with certbot.

```bash
sudo ln -s /etc/nginx/sites-available/voice-tts /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

A `docker-compose.yml` is included for containerised deployment.

## Layout

```
backend/
  main.py          FastAPI app
  requirements.txt
  data/models/     downloaded voices (gitignored)
  static/          built frontend (gitignored)
frontend/
  src/             React + Vite source
  vite.config.ts   dev server proxies /api → :8080
nginx.conf
start.sh
docker-compose.yml
```

## License

MIT
