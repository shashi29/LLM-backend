# app/schemas/chat/collection.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    vector_size: int = 384
    distance_metric: str = "COSINE"

class CollectionCreate(CollectionBase):
    board_id: int

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CollectionRead(CollectionBase):
    id: int
    board_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CollectionStats(BaseModel):
    id: int
    name: str
    document_count: int
    session_count: int
    message_count: int
    last_activity: Optional[datetime] = None