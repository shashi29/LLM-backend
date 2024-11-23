from pydantic import BaseModel
from typing import Optional, Dict

class ForecastRequest(BaseModel):
    dataset_path: str
    filters: Optional[Dict[str, str]] = None
    fiscal_year_start: Optional[str] = None
    fiscal_year_end: Optional[str] = None
