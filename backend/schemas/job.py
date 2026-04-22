from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.models.job import JobType, JobStatus


class JobRead(BaseModel):
    id: int
    job_type: JobType
    status: JobStatus
    retry_count: int
    max_retries: int
    error_msg: Optional[str]
    created_at: datetime
    updated_at: datetime
    run_at: datetime

    model_config = {"from_attributes": True}


class MaterialJobCreated(BaseModel):
    material_id: int
    job_id: int
