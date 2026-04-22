from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class Platform(str, Enum):
    anki = "anki"
    telegram = "telegram"


class PushStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class PushRecord(SQLModel, table=True):
    __tablename__ = "push_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    segment_id: int = Field(foreign_key="segments.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    platform: Platform
    status: PushStatus = Field(default=PushStatus.pending)
    anki_card_id: Optional[int] = Field(default=None, description="Anki note ID after successful push")
    error_msg: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = Field(default=None)
