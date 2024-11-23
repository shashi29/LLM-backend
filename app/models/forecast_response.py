from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ForecastResponseModel(BaseModel):
    status_code: int
    detail: str
    start_time: str
    end_time: str
    duration_seconds: float
    board_id: int
    prompt_text: str
    message: List[str]
    table: Dict[str, Any]
    graph: Optional[Dict[str, Any]]  # Can hold additional graph data if needed

    class Config:
        orm_mode = True
