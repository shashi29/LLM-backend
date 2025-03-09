from pydantic import BaseModel
from typing import Any, Dict, Optional

class ForecastResponseModel(BaseModel):
    status_code: int
    detail: str
    start_time: str
    end_time: str
    duration_seconds: float
    message: Optional[str]
    table: Optional[Dict[str, Any]]
    graph: Optional[str]
