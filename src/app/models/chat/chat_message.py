# app/models/chat/chat_message.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, Integer, ForeignKey, Text
from pydantic import ConfigDict
from sqlmodel import SQLModel, Field, Relationship

class ChatMessage(SQLModel, table=True):
    """
    Represents an individual message within a chat session.
    """
    __tablename__ = "ChatMessage"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(sa_column=Column(Integer, ForeignKey("ChatSession.id", ondelete="CASCADE")))
    sender: str = Field()  # "user" or "assistant"
    message: str = Field(sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional fields for assistant messages
    sources: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))  # References to source documents
    metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # Additional metadata
    
    # Relationships
    session: "ChatSession" = Relationship(back_populates="messages")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": 1,
                    "sender": "user",
                    "message": "What were our Q4 sales figures?",
                    "sources": [],
                    "metadata": {}
                },
                {
                    "session_id": 1,
                    "sender": "assistant",
                    "message": "The Q4 sales figures were $2.3 million, which is 15% higher than Q3.",
                    "sources": [
                        {
                            "document_id": 3,
                            "page": 12,
                            "text": "Q4 sales reached $2.3M (15% increase from Q3)",
                            "relevance_score": 0.92
                        }
                    ],
                    "metadata": {
                        "processing_time": 1.45,
                        "tokens_used": 357
                    }
                }
            ]
        }
    )