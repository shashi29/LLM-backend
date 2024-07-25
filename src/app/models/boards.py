# app/models/boards.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Boards(BaseModel):
    id: Optional[int] = None
    main_board_id: int
    name: str
    is_active : Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "main_board_id": 1,
                    "name": "Sale Analysis",
                }
            ]
        }