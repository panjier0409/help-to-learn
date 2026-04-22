from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.models.segment import AudioSourceType


class SegmentRead(BaseModel):
    id: int
    material_id: int
    user_id: int
    index: int
    start_time: Optional[float]
    end_time: Optional[float]
    duration: Optional[float]
    text: str
    translation: Optional[str]
    audio_source_type: AudioSourceType
    audio_file_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SegmentUpdate(BaseModel):
    text: Optional[str] = None
    translation: Optional[str] = None
