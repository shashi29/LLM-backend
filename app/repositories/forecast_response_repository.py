import logging
from app.models.forecast_response import ForecastResponseModel

class ForecastResponseRepository:
    def __init__(self):
        self.logger = logging.getLogger("ForecastResponseRepository")

    def create_forecast_response(self, response: ForecastResponseModel):
        # Here you can implement logic to save the response, e.g., to a database
        # For demonstration purposes, let's just log the response
        self.logger.info(f"Saving forecast response: {response.dict()}")
        # This is where you could implement your database save logic
