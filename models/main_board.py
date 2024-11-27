# app/models/main_board.py
from pydantic import BaseModel

class MainBoard(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
