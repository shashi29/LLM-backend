# app/models/chat/job.py
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, Integer, ForeignKey
from pydantic import ConfigDict

class ProcessingJob(SQLModel, table=True):
    """
    Represents a background processing job for document indexing.
    """
    __tablename__ = "ProcessingJob"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_uuid: str = Field(index=True)
    document_id: int = Field(sa_column=Column(Integer, ForeignKey("Document.id", ondelete="CASCADE")))
    status: str = Field(default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED
    progress: Optional[float] = Field(default=0.0)  # Progress percentage (0-100)
    error_message: Optional[str] = Field(default=None)
    result: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_uuid": "e47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "document_id": 3,
                    "status": "COMPLETED",
                    "progress": 100.0,
                    "result": {
                        "chunks_processed": 45,
                        "vectors_created": 87,
                        "processing_time": 12.3
                    }
                }
            ]
        }
    )