from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from backend.config import settings
from backend.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create storage directories
    for sub in ("originals", "audio", "temp"):
        os.makedirs(os.path.join(settings.STORAGE_BASE_PATH, sub), exist_ok=True)
    # Create DB tables
    create_db_and_tables()
    yield


app = FastAPI(
    title="English Learning Material Management",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production via env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from backend.routers import auth, users, materials, segments, push, jobs  # noqa: E402
from fastapi.responses import FileResponse
from backend.database import get_session as _gs
from sqlmodel import Session as _Session

app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(users.router,     prefix="/api/users",     tags=["Users"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])
app.include_router(segments.router,  prefix="/api/segments",  tags=["Segments"])
app.include_router(push.router,      prefix="/api",           tags=["Push"])
app.include_router(jobs.router,      prefix="/api/jobs",      tags=["Jobs"])


@app.get("/api/audio/{segment_id}", tags=["Audio"])
def serve_audio(segment_id: int, session: _Session = Depends(_gs)):
    """Serve a segment's mp3 audio file."""
    from fastapi import HTTPException
    from backend.models.segment import Segment
    segment = session.get(Segment, segment_id)
    if not segment or not segment.audio_file_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    import os
    if not os.path.exists(segment.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")
    return FileResponse(segment.audio_file_path, media_type="audio/mpeg")


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}
