# app/models/chat/document.py
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Table, Column, Integer, String, Text, JSON, ForeignKey, DateTime, MetaData
from sqlalchemy import create_engine

# Define the table explicitly
document_table = Table(
    "Document",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("collection_id", Integer, ForeignKey("ChatCollection.id", ondelete="CASCADE")),
    Column("filename", String(255), nullable=False),
    Column("storage_path", Text, nullable=False),
    Column("file_type", String(50), nullable=False),
    Column("status", String(50), nullable=False, default="PENDING"),
    Column("metadata", JSON, default={}),
    Column("job_id", String(255)),
    Column("error_message", Text),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow)
)

# Then define your SQLModel class that references the table
class Document(SQLModel, table=True):
    """
    Represents a document stored in a chat collection.
    """
    __table__ = document_table
    
    id: Optional[int] = None
    collection_id: int
    filename: str
    storage_path: str
    file_type: str
    status: str = "PENDING"
    metadata: Dict[str, Any] = {}
    job_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)