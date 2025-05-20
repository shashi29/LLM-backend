# app/models/chat/collection.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, ForeignKey
from pydantic import ConfigDict

class ChatCollection(SQLModel, table=True):
    """
    Represents a collection of documents for chat-based knowledge retrieval.
    Each collection is linked to a board and contains documents that can be queried.
    """
    __tablename__ = "ChatCollection"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    board_id: int = Field(sa_column=Column(Integer, ForeignKey("Boards.id", ondelete="CASCADE")))
    vector_size: int = Field(default=384)  # Default for all-MiniLM-L6-v2
    distance_metric: str = Field(default="COSINE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    board: "Boards" = Relationship(back_populates="chat_collections")
    chat_sessions: List["ChatSession"] = Relationship(
        back_populates="collection",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    documents: List["Document"] = Relationship(
        back_populates="collection",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Sales Knowledge Base",
                    "description": "Collection of sales documents and reports",
                    "board_id": 1,
                    "vector_size": 384,
                    "distance_metric": "COSINE"
                }
            ]
        }
    )