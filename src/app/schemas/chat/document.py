# app/schemas/chat/document.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class DocumentBase(BaseModel):
    filename: str
    file_type: str
    metadata: Dict[str, Any] = {}

class DocumentCreate(DocumentBase):
    collection_id: int
    storage_path: str

class DocumentUpdate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    error_message: Optional[str] = None

class DocumentRead(DocumentBase):
    id: int
    collection_id: int
    storage_path: str
    status: str
    job_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True