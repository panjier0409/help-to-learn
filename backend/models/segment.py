from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class AudioSourceType(str, Enum):
    original = "original"  # FFmpeg cut from original video/audio (real human voice)
    tts = "tts"            # wangwangit TTS generated (for article/text materials)


class Segment(SQLModel, table=True):
    __tablename__ = "segments"

    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="materials.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    index: int = Field(description="Sequence number within the material")

    # Time info — None for text/article materials
    start_time: Optional[float] = Field(default=None)
    end_time: Optional[float] = Field(default=None)
    duration: Optional[float] = Field(default=None)

    text: str = Field(description="Transcribed or source text")
    translation: Optional[str] = Field(default=None, description="Optional Chinese translation")

    audio_source_type: AudioSourceType
    audio_file_path: str = Field(max_length=1024, description="Path to mp3 file")

    created_at: datetime = Field(default_factory=datetime.utcnow)
