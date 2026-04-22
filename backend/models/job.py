from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class JobType(str, Enum):
    process_material = "process_material"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: JobType
    payload: str = Field(description="JSON-encoded job parameters")

    status: JobStatus = Field(default=JobStatus.pending)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    error_msg: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    run_at: datetime = Field(default_factory=datetime.utcnow, description="Execute at or after this time")
