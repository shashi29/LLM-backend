# app/models/boards.py
from pydantic import BaseModel

class Boards(BaseModel):
    id: int
    name: str
    main_board_id: int

    class Config:
        orm_mode = True
