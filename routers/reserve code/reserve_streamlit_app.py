import asyncio
import aiohttp
import pandas as pd
import streamlit as st
import io
import base64

FASTAPI_URL = "http://127.0.0.1:8000"

async def analyze_dataset(file_content):
    async with aiohttp.ClientSession() as session:
        files = {'file': file_content}
        async with session.post(f"{FASTAPI_URL}/upload_and_analyze", data=files) as response:
            try:
                response_data = await response.json()
                if response.status != 200:
                    st.error(f"Error {response.status}: {response_data.get('detail', 'Unknown error')}")
                return response_data
            except Exception as e:
                st.error(f"Error parsing analysis result: {e}")
                response_text = await response.text()
                st.error(f"Response text: {response_text}")
                return None


async def perform_forecasting(file_content, date_column, target_column, feature_column, forecast_type, forecast_length):
    async with aiohttp.ClientSession() as session:
        data = {
            "date_column": date_column,
            "target_column": target_column,
            "forecast_type": forecast_type,
            "forecast_length": str(forecast_length)  # Ensure this is an integer
        }
        
        # Only add `feature_column` to the request if it's provided
        if feature_column:
            data["feature_column"] = feature_column

        files = {'file': file_content}
        async with session.post(f"{FASTAPI_URL}/forecast", data={**data, **files}) as response:
            try:
                forecast_result = await response.json()
                return forecast_result
            except Exception as e:
                print(f"Error parsing forecast result: {e}")
                response_text = await response.text()
                print(f"Response text: {response_text}")
                return None

st.title("Forecasting Application")
st.subheader("Step 1: Upload your dataset")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    try:
        file_content = uploaded_file.read()
        df = pd.read_csv(io.StringIO(file_content.decode("utf-8")))

        if df.empty:
            st.error("The dataset is empty or could not be read properly.")
        else:
            st.write("Dataset Preview:")
            st.write(df.head())

            st.write("Analyzing dataset columns...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(analyze_dataset(file_content))

            if "column_info" in response:
                column_info = response["column_info"]
                st.write("Column Information:")
                st.write(column_info)

                date_column = st.selectbox("Select the Timeline Dimensions", column_info['Timeline_dimensions'])
                target_column = st.selectbox("Select the Key Figure (target column)", column_info['Key_figures'])
                feature_column = st.selectbox("Select an additional Feature Column (optional)", ["None"] + column_info['Key_figures'])
                forecast_type = st.selectbox("Select Forecast Type", ["daily", "weekly", "monthly"])
                forecast_length = st.number_input("Select Forecast Length (e.g., number of periods)", min_value=1)

                if st.button("Perform Forecasting"):
                    # Pass 'None' if no additional feature is selected
                    selected_feature_column = None if feature_column == "None" else feature_column

                    forecast_result = loop.run_until_complete(
                        perform_forecasting(file_content, date_column, target_column, selected_feature_column, forecast_type, forecast_length)
                    )

                    if "forecast" in forecast_result:
                        # Convert forecast data to DataFrame for line chart
                        forecast_df = pd.DataFrame(forecast_result["forecast"])
                        forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])  # Ensure date parsing
                        
                        # Plot forecasted values with confidence intervals using st.line_chart
                        st.write("Forecast Results:")
                        st.line_chart(
                            data=forecast_df.set_index("ds")[["yhat", "yhat_lower", "yhat_upper"]],
                            x_label="Date",
                            y_label="Forecasted Value",
                            use_container_width=True
                        )

                        # Optionally show the plot image as a secondary visualization
                        if "forecast_plot" in forecast_result:
                            plot_base64 = forecast_result["forecast_plot"]
                            plot_bytes = base64.b64decode(plot_base64)
                            st.write("Forecast Plot:")
                            st.image(plot_bytes, use_column_width=True)
                    else:
                        st.error(f"Error during forecasting: {forecast_result.get('detail', 'Unknown error occurred.')}")
            else:
                st.error("Unable to analyze the dataset.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
