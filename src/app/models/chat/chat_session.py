# app/models/chat/chat_session.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, ForeignKey
from pydantic import ConfigDict

class ChatSession(SQLModel, table=True):
    """
    Represents a chat session within a collection.
    A session groups related messages together.
    """
    __tablename__ = "ChatSession"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_uuid: str = Field(index=True)  # UUID for external reference
    collection_id: int = Field(sa_column=Column(Integer, ForeignKey("ChatCollection.id", ondelete="CASCADE")))
    client_user_id: int = Field(foreign_key="ClientUsers.id")
    title: Optional[str] = Field(default="New Chat")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    collection: "ChatCollection" = Relationship(back_populates="chat_sessions")
    messages: List["ChatMessage"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    "collection_id": 1,
                    "client_user_id": 5,
                    "title": "Q4 Sales Analysis"
                }
            ]
        }
    )