from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import timedelta
import pandas as pd
import plotly.graph_objs as go
from statsmodels.tsa.arima.model import ARIMA
from loguru import logger
import io

# Create APIRouter instance
router = APIRouter()

# Logger configuration
logger.add("forecasting.log", rotation="1 MB", retention="10 days", level="DEBUG")

# Constants
CATEGORY_OPTIONS = ['actual', 'forecast', 'rolling forecast']
FREQUENCY_OPTIONS = {'daily': 'D', 'weekly': 'W', 'monthly': 'M'}
TEMP_FILE_PATH = "temp_upload.csv"  # Path to temporarily save uploaded file

# Step 1: Upload and Analyze File
@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save file temporarily
        with open(TEMP_FILE_PATH, "wb") as buffer:
            buffer.write(file.file.read())
        logger.info("File uploaded and saved successfully.")
        
        # Load dataset
        df = pd.read_csv(TEMP_FILE_PATH)
        
        # Analyze columns
        column_info = analyze_dataset(df)
        return JSONResponse(content=column_info)
    except Exception as e:
        logger.error(f"Error uploading or analyzing file: {str(e)}")
        raise HTTPException(status_code=400, detail="Error processing uploaded file")

# Utility function to analyze dataset columns
def analyze_dataset(df: pd.DataFrame):
    timeline_keywords = ['date', 'year', 'month', 'day', 'time']
    exclusion_keywords = ['code', 'id', 'number', 'num', 'sr.no', 'no', 'patient', 'record', 'reference', 'sequence', 'entry', 'count', 'status', 'flag', 'name', 'label', 'type', 'category', 'index']
    
    time_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in timeline_keywords)]
    numerical_columns = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    continuous_columns = [col for col in numerical_columns if (not any(exclude in col.lower() for exclude in exclusion_keywords)) and df[col].nunique() > 1]

    all_columns = set(df.columns)
    time_set = set(time_columns)
    continuous_set = set(continuous_columns)
    categorical_columns = list(all_columns - time_set - continuous_set)

    column_info = {
        'Timeline_dimensions': time_columns,
        'Key_figures': continuous_columns,
        'Categorical_columns': categorical_columns
    }
    return column_info

# BaseModel for forecast request validation
class ForecastRequest(BaseModel):
    date_column: str
    target_column: str
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    frequency: Literal['daily', 'weekly', 'monthly']
    category: Literal['actual', 'forecast', 'rolling forecast']
    forecast_length: Optional[int] = 30  # Default forecast length if not provided
    user_role: Literal['public', 'private']

# Utility Functions for Forecasting and Rolling Forecast
def preprocess_and_filter(df, date_column, target_column, frequency, filter_column=None, filter_value=None):
    if filter_column and filter_value:
        df = df[df[filter_column] == filter_value]

    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.dropna(subset=[date_column, target_column])

    if df[date_column].duplicated().any():
        df = df.groupby(date_column)[target_column].mean().reset_index()

    df = df.set_index(date_column)
    df = df.asfreq(FREQUENCY_OPTIONS[frequency])

    return df

def perform_forecasting_arima(train_df, target_column, forecast_length, frequency='D'):
    model = ARIMA(train_df[target_column], order=(5, 1, 0))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=forecast_length)
    last_date = train_df.index[-1]
    forecast_index = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_length, freq=FREQUENCY_OPTIONS[frequency])
    forecast_df = pd.DataFrame({target_column: forecast}, index=forecast_index)
    return forecast_df

# Plot functions for each category
def plot_actual(train_df, target_column):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=train_df.index, y=train_df[target_column], mode='lines', name='Actual Data', line=dict(color='blue')))
    fig.update_layout(title="Historical Data (Actual)", xaxis_title="Date", yaxis_title=target_column, template="plotly_dark", hovermode="x")
    return fig

def plot_forecast(train_df, forecast_df, target_column):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=train_df.index, y=train_df[target_column], mode='lines', name='Actual Data', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=forecast_df.index, y=forecast_df[target_column], mode='lines', name='Forecast', line=dict(color='orange')))
    fig.update_layout(title="Forecast with Historical Data", xaxis_title="Date", yaxis_title=target_column, template="plotly_dark", hovermode="x")
    return fig

def plot_rolling_forecast(df, date_column, target_column, window_size, forecast_length, frequency):
    rolling_forecast_df = df.copy()
    for _ in range(forecast_length):
        rolling_forecast = perform_forecasting_arima(rolling_forecast_df[-window_size:], target_column, forecast_length=1, frequency=frequency)
        rolling_forecast_df = pd.concat([rolling_forecast_df, rolling_forecast])
        rolling_forecast_df = rolling_forecast_df.shift(-1)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[target_column], mode='lines', name='Actual Data', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=rolling_forecast_df.index[-forecast_length:], y=rolling_forecast_df[target_column][-forecast_length:], mode='lines', name='Rolling Forecast', line=dict(color='orange')))
    fig.update_layout(title="Rolling Forecast with Drop/Add Approach", xaxis_title="Date", yaxis_title=target_column, template="plotly_dark", hovermode="x")
    return fig

# Access Control for Forecasting
def check_access(user_role, category):
    if user_role == 'private':
        logger.info(f"Private access for {category}. Only the creator can modify and view.")
        return True
    elif user_role == 'public':
        logger.info(f"Public access for {category}. Data can be shared with others.")
        return True
    else:
        logger.error("Invalid user role.")
        return False

# Step 2: Forecasting with User-Selected Columns
@router.post("/forecast")
async def forecast(request: ForecastRequest):
    # Load dataset from saved file
    try:
        df = pd.read_csv(TEMP_FILE_PATH)
        logger.info("Loaded temporary file for forecasting.")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Temporary file not found. Please upload the file again.")
    
    # Preprocess data
    df = preprocess_and_filter(df, request.date_column, request.target_column, request.frequency, request.filter_column, request.filter_value)

    # Split data into train and test sets
    split_point = int(len(df) * 0.8)
    train_df = df.iloc[:split_point]
    test_df = df.iloc[split_point:]

    # Access control check
    if not check_access(request.user_role, request.category):
        raise HTTPException(status_code=403, detail="Access denied due to insufficient permissions")

    # Generate plot based on selected category
    if request.category == 'actual':
        fig = plot_actual(train_df, request.target_column)
    elif request.category == 'forecast':
        forecast_df = perform_forecasting_arima(train_df, request.target_column, forecast_length=request.forecast_length, frequency=request.frequency)
        fig = plot_forecast(train_df, forecast_df, request.target_column)
    elif request.category == 'rolling forecast':
        fig = plot_rolling_forecast(df, request.date_column, request.target_column, window_size=split_point, forecast_length=request.forecast_length, frequency=request.frequency)
    else:
        raise HTTPException(status_code=400, detail="Invalid category selected")

    # Save plot to a buffer and return
    img_bytes = io.BytesIO()
    fig.write_image(img_bytes, format='png')
    img_bytes.seek(0)
    return StreamingResponse(img_bytes, media_type="image/png")
