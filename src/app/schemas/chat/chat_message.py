# app/schemas/chat/chat_message.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ChatMessageBase(BaseModel):
    message: str
    sender: str  # "user" or "assistant"

class ChatMessageCreate(ChatMessageBase):
    session_id: int
    sources: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class ChatMessageRead(ChatMessageBase):
    id: int
    session_id: int
    sources: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    session_uuid: Optional[str] = None
    collection_id: int

class ChatResponse(BaseModel):
    message: str
    session_id: int
    session_uuid: str
    sources: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}