# app/schemas/chat/job.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class JobBase(BaseModel):
    document_id: int
    status: str = "QUEUED"

class JobCreate(JobBase):
    job_uuid: str

class JobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class JobRead(JobBase):
    id: int
    job_uuid: str
    progress: float
    error_message: Optional[str] = None
    result: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True