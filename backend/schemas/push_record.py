from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.models.push_record import Platform, PushStatus


class PushRequest(BaseModel):
    platform: Platform
    anki_note_id: Optional[int] = None


class PushRecordRead(BaseModel):
    id: int
    segment_id: int
    platform: Platform
    status: PushStatus
    anki_card_id: Optional[int]
    error_msg: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]

    model_config = {"from_attributes": True}
