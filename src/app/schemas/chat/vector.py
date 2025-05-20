# app/schemas/chat/vector.py
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class VectorEntryBase(BaseModel):
    document_id: int
    vector_id: str
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    text_content: str
    metadata: Dict[str, Any] = {}

class VectorEntryCreate(VectorEntryBase):
    pass

class VectorEntryRead(VectorEntryBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True