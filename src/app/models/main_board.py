# app/models/main_board.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MainBoard(BaseModel):
    id: Optional[int] = None
    client_user_id: Optional[int] = None
    name: str #ANALYSIS  FORECASTING KPI_DEFINITION WHAT_IF_FRAMEWORK PROFITABILITY_ANALYSIS
    main_board_type: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "client_user_id": 1,
                    "name": "Analysis",
                    "main_board_type": "ANALYSIS"
                }
            ]
        }