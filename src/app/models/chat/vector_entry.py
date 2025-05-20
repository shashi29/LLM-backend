# app/models/chat/vector_entry.py
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, Integer, ForeignKey, Text
from pydantic import ConfigDict

class VectorEntry(SQLModel, table=True):
    """
    Metadata for vector entries stored in Qdrant.
    This model tracks vector IDs and their sources.
    """
    __tablename__ = "VectorEntry"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(sa_column=Column(Integer, ForeignKey("Document.id", ondelete="CASCADE")))
    vector_id: str = Field(index=True)  # Qdrant vector ID
    page_number: Optional[int] = Field(default=None)
    chunk_index: Optional[int] = Field(default=None)
    text_content: str = Field(sa_column=Column(Text))
    metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_id": 3,
                    "vector_id": "vector-12345",
                    "page_number": 12,
                    "chunk_index": 2,
                    "text_content": "Q4 sales reached $2.3M (15% increase from Q3)",
                    "metadata": {
                        "source": "Annual Report 2024",
                        "section": "Financial Performance"
                    }
                }
            ]
        }
    )