# app/models/rag_collection.py
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

class RAGCollection(BaseModel):
    id: Optional[int] = None
    board_id: int
    collection_name: str
    vector_size: int = 384
    distance: str = "COSINE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ChatMessage(BaseModel):
    id: Optional[int] = None
    collection_id: int
    session_id: str
    sender: str
    message: str
    timestamp: Optional[datetime] = None

class FileInfo(BaseModel):
    filename: str
    size: int
    storage_path: str
    metadata: Dict[str, str] = {}

class ChatHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]

class ChatSession(BaseModel):
    session_id: str
    last_message: datetime
    message_count: int

class ChatStats(BaseModel):
    total_messages: int
    unique_sessions: int
    avg_messages_per_session: float
    message_counts_by_sender: Dict[str, int]