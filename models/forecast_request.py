from pydantic import BaseModel
from typing import Optional

class ForecastRequest(BaseModel):
    date_column: str
    dependent_variable: str
    forecast_days: int = 30
    aggregation_period: str = 'D'  # Daily ('D'), Weekly ('W'), Monthly ('M')
    filters: Optional[dict] = None
