# English Learning Material Management System

A web application for importing, transcribing, and reviewing English learning materials with Anki and Telegram integration.

## Features
- **4 import types**: local file upload, media URL (YouTube/Bilibili), article URL, plain text
- **Media pipeline**: yt-dlp → FFmpeg → STT (wangwangit/tts) → segmented audio clips
- **Text pipeline**: article scraping / plain text → sentence split → TTS audio generation
- **Anki integration**: push segments as cards with real audio
- **Telegram integration**: send audio clips to your bot
- **Zero-middleware**: SQLite handles both DB and task queue, no Redis/RabbitMQ needed

## Prerequisites

### Windows Development
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [FFmpeg](https://ffmpeg.org/download.html) — add to PATH
- [yt-dlp](https://github.com/yt-dlp/yt-dlp#installation) — `pip install yt-dlp`
- Node.js 18+

### Linux / Docker Production
FFmpeg and yt-dlp are installed automatically in the Docker image.

---

## Development Setup

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in:
#   SECRET_KEY=<random string>
#   TTS_WORKER_URL=https://your-worker.workers.dev
#   TELEGRAM_BOT_TOKEN=  (optional)
```

### 2. Install backend dependencies
```bash
uv sync
```

### 3. Start backend (API server)
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

### 4. Start background worker (separate terminal)
```bash
uv run python backend/worker.py
```

### 5. Install & start frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Production Deployment (Docker)

### 1. Build frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 2. Start services
```bash
cp .env.example .env
# Edit .env with production values
docker compose up -d
# App available at http://localhost:80
```

---

## Project Structure

```
├── backend/
│   ├── main.py          — FastAPI app
│   ├── worker.py        — Background job processor (APScheduler)
│   ├── config.py        — Environment settings
│   ├── database.py      — SQLite engine & session
│   ├── models/          — SQLModel table definitions
│   ├── schemas/         — Pydantic request/response models
│   ├── routers/         — API route handlers
│   └── services/        — Business logic (FFmpeg, STT, TTS, Anki, Telegram)
├── frontend/
│   └── src/
│       ├── views/       — Login, Materials, MaterialDetail, Settings
│       ├── stores/      — Pinia stores (auth, app)
│       ├── api/         — Axios API client
│       └── router/      — Vue Router
├── nginx/nginx.conf      — Production Nginx config
├── storage/              — Media files (git-ignored)
│   ├── originals/        — Original downloads (never deleted)
│   ├── audio/            — Cut MP3 segments
│   └── temp/             — Temporary processing files
└── data.db               — SQLite database (git-ignored)
```

---

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Material Processing Pipelines

### Media (upload / YouTube URL)
```
yt-dlp download (URL only)
  → FFmpeg: extract mono 16kHz WAV
  → POST /v1/audio/transcriptions (STT, auto-chunks >9MB)
  → FFmpeg: cut each sentence as 64kbps mp3
  → Write Segment rows (audio_source_type = "original")
```

### Text (article URL / plain text)
```
httpx + BeautifulSoup4: fetch article text (URL only)
  → Split into sentences by punctuation
  → POST /v1/audio/speech per sentence (TTS)
  → Save mp3 clips
  → Write Segment rows (audio_source_type = "tts")
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | JWT signing key |
| `DATABASE_URL` | `sqlite:///./data.db` | SQLite path |
| `STORAGE_BASE_PATH` | `./storage` | Media storage root |
| `TTS_WORKER_URL` | `https://tts.wangwangit.com` | wangwangit/tts worker URL |
| `TTS_TOKEN` | *(empty)* | SiliconFlow token for STT |
| `TELEGRAM_BOT_TOKEN` | *(empty)* | Telegram bot token |
| `ANKI_CONNECT_URL` | `http://localhost:8765` | AnkiConnect URL |
| `JOB_POLL_INTERVAL` | `5` | Worker poll interval (seconds) |
