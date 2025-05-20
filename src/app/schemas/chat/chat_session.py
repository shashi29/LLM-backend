# app/schemas/chat/chat_session.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class ChatSessionBase(BaseModel):
    title: Optional[str] = "New Chat"

class ChatSessionCreate(ChatSessionBase):
    collection_id: int
    client_user_id: int
    session_uuid: Optional[str] = None  # Generated server-side if not provided

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None

class ChatSessionRead(ChatSessionBase):
    id: int
    session_uuid: str
    collection_id: int
    client_user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatSessionSummary(BaseModel):
    id: int
    session_uuid: str
    title: str
    last_message_at: datetime
    message_count: int