from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Dict, Optional
from app.models.forecast_request import ForecastRequest
from app.models.forecast_response import ForecastResponseModel
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.forecast_response_repository import ForecastResponseRepository  # Assuming this exists
import logging
from datetime import datetime
import pandas as pd
import shutil
import os

router = APIRouter(prefix="/forecast", tags=["Forecast"])

# Initialize repository instances (adjust the path as needed)
forecast_repo = ForecastRepository(data_path='C:/Users/hp/Desktop/ONEVEGA/datasets for GbussinessAI/P6-SuperStoreUS-2015 sheets/Orders.csv')
forecast_response_repo = ForecastResponseRepository()

@router.post("/upload", response_model=ForecastResponseModel)
async def upload_file(file: UploadFile = File(...), 
                       fiscal_year_start: str = "2015-01-01", 
                       fiscal_year_end: str = "2015-06-30", 
                       forecast_days: int = 30,
                       aggregation_period: str = 'D', 
                       dependent_variable: str = 'Sales', 
                       product_category: Optional[str] = None, 
                       product_sub_category: Optional[str] = None):
    start_time = datetime.now()
    logger = logging.getLogger("ForecastAPI")

    try:
        # Save the uploaded file
        file_location = f"uploaded_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load and preprocess data
        df = pd.read_csv(file_location)
        df = forecast_repo.preprocess_data(df, fiscal_year_start, fiscal_year_end)

        # Filter data
        filtered_df = forecast_repo.filter_data(
            df,
            product_category=product_category,
            product_sub_category=product_sub_category,
            fiscal_year_start=fiscal_year_start,
            fiscal_year_end=fiscal_year_end
        )

        # Aggregate data
        grouped_df = forecast_repo.aggregate_data(
            filtered_df,
            dependent_variable=dependent_variable,
            aggregation_period=aggregation_period
        )

        # Train model and predict
        forecast_df = forecast_repo.train_forecast_model(
            grouped_df,
            forecast_days=forecast_days,
            aggregation_period=aggregation_period
        )

        # Format forecast
        formatted_forecast_df = forecast_repo.format_forecast(forecast_df)

        # Convert forecast to JSON-friendly format
        forecast_json = formatted_forecast_df.reset_index().to_dict(orient='records')

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Prepare the response model
        result = ForecastResponseModel(
            status_code=200,
            detail="Forecast Run Successfully",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            board_id=1,  # Set this according to your logic
            prompt_text="Run Forecast",
            message=[f"Forecasted {dependent_variable} for the next {forecast_days} days."],
            table={
                "columns": formatted_forecast_df.reset_index().columns.tolist(),
                "data": formatted_forecast_df.reset_index().values.tolist(),
                "title": "Forecasted Data"
            },
            graph={}  # Placeholder for graph data if needed
        )

        # Save the forecast response to the database
        forecast_response_repo.create_forecast_response(result)

        # Log the successful forecast
        logger.info(f"Forecast completed in {duration} seconds with uploaded file {file_location}")

        # Optionally remove the uploaded file after processing
        os.remove(file_location)

        return result

    except ValueError as ve:
        logger.error(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
