from datetime import datetime
from typing import Optional, Any, Text
from pydantic import BaseModel

class QuadrantCollectionTable(BaseModel):
    id: Optional[Any] = None
    board_id: Optional[Any]
    collection_name: str
    collection_description: Optional[Text] = None
    collection_configuration: Optional[Text] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "board_id": 1,
                    "collection_name": "Collection Name",
                    "collection_description": "Description of the collection",
                    "collection_configuration": '{"key": "value"}'
                }
            ]
        }
