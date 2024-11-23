import pandas as pd
from autots import AutoTS
import logging
from typing import Optional
from app.models.forecast_response import ForecastResponseModel

class ForecastRepository:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.logger = logging.getLogger("ForecastRepository")
    
    def load_data(self) -> pd.DataFrame:
        self.logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)
        self.logger.info("Data loaded successfully")
        return df
    
    def preprocess_data(self, df: pd.DataFrame, fiscal_year_start: str, fiscal_year_end: str) -> pd.DataFrame:
        self.logger.info("Preprocessing data")
        df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['Order Date'])
        return df
    
    def filter_data(self, df: pd.DataFrame, product_category: Optional[str], product_sub_category: Optional[str],
                   fiscal_year_start: str, fiscal_year_end: str) -> pd.DataFrame:
        self.logger.info("Filtering data")
        fiscal_year_start = pd.to_datetime(fiscal_year_start)
        fiscal_year_end = pd.to_datetime(fiscal_year_end)
        
        filtered_df = df[
            (df['Order Date'] >= fiscal_year_start) &
            (df['Order Date'] <= fiscal_year_end)
        ]
        
        if product_category:
            filtered_df = filtered_df[filtered_df['Product Category'] == product_category]
        if product_sub_category:
            filtered_df = filtered_df[filtered_df['Product Sub-Category'] == product_sub_category]
        
        self.logger.info(f"Data filtered: {filtered_df.shape[0]} records")
        return filtered_df
    
    def aggregate_data(self, filtered_df: pd.DataFrame, dependent_variable: str,
                      aggregation_period: str) -> pd.DataFrame:
        self.logger.info("Aggregating data")
        grouped_df = filtered_df.groupby('Order Date').agg({
            dependent_variable: 'sum'
        }).reset_index()
        
        grouped_df['Order Date'] = pd.to_datetime(grouped_df['Order Date'])
        grouped_df.set_index('Order Date', inplace=True)
        
        if aggregation_period in ['W', 'M']:
            grouped_df = grouped_df.resample(aggregation_period).sum()
        
        if grouped_df.shape[0] < 3:
            raise ValueError(f"Not enough data points after resampling for '{aggregation_period}' period.")
        
        self.logger.info(f"Data aggregated: {grouped_df.shape[0]} records")
        return grouped_df
    
    def train_forecast_model(self, grouped_df: pd.DataFrame, forecast_days: int, aggregation_period: str) -> pd.DataFrame:
        self.logger.info("Training forecast model")
        model = AutoTS(
            forecast_length=forecast_days,
            frequency=aggregation_period,
            ensemble='simple',
            max_generations=5,
            min_allowed_train_percent=0.1,
            n_jobs=-1
        )
        model = model.fit(grouped_df)
        forecast = model.predict()
        forecast_df = forecast.forecast
        self.logger.info("Forecasting completed")
        return forecast_df
    
    def format_forecast(self, forecast_df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Formatting forecast data")
        formatted_forecast_df = forecast_df.applymap(lambda x: '${:,.2f}'.format(x))
        return formatted_forecast_df
