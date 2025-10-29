import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import argparse

import openmeteo_requests
from retry_requests import retry

# ---------------------- API DATA FETCHING ---------------------- #

def fetch_weather_data(df, dataset_folder="Dataset", total_cities=10):
    """Fetch weather data for a list of up to `total_cities` cities using the Open-Meteo API."""
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)

    openmeteo = openmeteo_requests.Client()
    combined_data = []

    total_cities = min(total_cities, len(df))
    print(f"\nFetching weather data for {total_cities} cities...\n")

    for i in range(total_cities):
        City = df.iloc[i]['City']
        Lat = df.iloc[i]['Lat']
        Lng = df.iloc[i]['Lng']

        print(f"Fetching data for {City} ({Lat}, {Lng})...")

        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": Lat,
            "longitude": Lng,
            "start_date": "2010-01-01",
            "end_date": "2024-02-20",
            "hourly": ["temperature_2m", "relative_humidity_2m", "pressure_msl"]
        }

        try:
            responses = openmeteo.weather_api(url, params=params)
            # the library returns a list-like response; adapt if your client differs
            response = responses[0]
            hourly = response.Hourly()

            # Build datetime index for hourly entries (these calls depend on the client API)
            start_ts = pd.to_datetime(hourly.Time(), unit="s", utc=True)
            end_ts = pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True)
            freq_seconds = int(hourly.Interval())

            date_range = pd.date_range(start=start_ts, end=end_ts, freq=pd.Timedelta(seconds=freq_seconds), inclusive="left")

            temperature = np.asarray(hourly.Variables(0).ValuesAsNumpy())
            humidity = np.asarray(hourly.Variables(1).ValuesAsNumpy())
            pressure = np.asarray(hourly.Variables(2).ValuesAsNumpy())

            # If lengths mismatch, attempt to align by trimming or padding with NaN
            min_len = min(len(date_range), len(temperature), len(humidity), len(pressure))
            date_range = date_range[:min_len]
            temperature = temperature[:min_len]
            humidity = humidity[:min_len]
            pressure = pressure[:min_len]

            hourly_data = {
                "City": [City] * min_len,
                "date": date_range,
                "temperature": temperature,
                "humidity": humidity,
                "pressure": pressure
            }

            df_city = pd.DataFrame(hourly_data)
            combined_data.append(df_city)

        except Exception as e:
            print(f"❌ Error fetching data for {City}: {e}")
            time.sleep(3)
            continue

    if combined_data:
        combined_df = pd.concat(combined_data, ignore_index=True)
        file_path = os.path.join(dataset_folder, "combined_weather.csv")
        combined_df.to_csv(file_path, index=False)
        print(f"\n✅ Combined dataset saved at: {file_path}")
        return file_path
    else:
        raise Exception("No data could be fetched.")


# ---------------------- DATA ANALYSIS & FORECAST ---------------------- #

def load_data(file_path):
    try:
        data = pd.read_csv(file_path, parse_dates=['date'])
        print(f"Loaded data from {file_path}")
        # normalize column names
        data.columns = data.columns.str.strip()
        # ensure numeric types
        for col in ['temperature', 'humidity', 'pressure']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        return data
    except Exception as e:
        raise Exception(f"Error loading data from {file_path}: {e}")


def analyze_patterns(data):
    print("\nWeather Data Analysis")
    print("=" * 50)
    if data.empty:
        print("No data available to analyze.")
        return

    print(f"Data period: {data['date'].min()} to {data['date'].max()}")
    print(f"Total records: {len(data)}")

    for city, df_city in data.groupby('City'):
        mean_temp = df_city['temperature'].mean()
        median_temp = df_city['temperature'].median()
        std_temp = df_city['temperature'].std()
        print(f"\n📍 City: {city}")
        print(f"Mean Temp: {mean_temp:.2f}°C (median {median_temp:.2f}, std {std_temp:.2f})")


def seasonal_insights(data):
    """Return seasonal (monthly) average temperature table per city and save as CSV."""
    if data.empty:
        print("No data for seasonal insights.")
        return pd.DataFrame()

    data = data.copy()
    data['month'] = data['date'].dt.month
    seasonal_stats = data.groupby(['City', 'month'])['temperature'].mean().unstack(fill_value=np.nan)
    seasonal_stats = seasonal_stats.round(2)
    seasonal_stats.to_csv("seasonal_temperature_averages.csv")
    print("\n📊 Seasonal temperature averages saved to seasonal_temperature_averages.csv")
    return seasonal_stats


def compute_correlation(data):
    """Print and save correlation matrices for temperature, humidity and pressure per city."""
    if data.empty:
        print("No data for correlation computation.")
        return {}

    corr_map = {}
    print("\n🔗 Correlation Analysis")
    for city, df_city in data.groupby("City"):
        df_subset = df_city[['temperature', 'humidity', 'pressure']].dropna()
        if df_subset.shape[0] < 2:
            print(f"City {city}: Not enough data to compute correlations.")
            corr_map[city] = None
            continue
        corr = df_subset.corr().round(2)
        corr_map[city] = corr
        print(f"\nCity: {city}\n{corr}")
        # save each matrix
        corr.to_csv(f"correlation_{city.replace(' ', '_')}.csv")
    return corr_map


def visualize_patterns(data, out_folder="plots"):
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    for city, df_city in data.groupby('City'):
        df_city = df_city.sort_values('date')
        plt.figure(figsize=(12, 6))
        # plot temperature
        plt.plot(df_city['date'], df_city['temperature'], label='Temperature (°C)')
        # plot humidity on same axes (will share y but that's okay for overview)
        plt.plot(df_city['date'], df_city['humidity'], label='Humidity (%)', alpha=0.6)
        plt.title(f"Weather Trends - {city}")
        plt.xlabel('Date')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        filename = os.path.join(out_folder, f"weather_patterns_{city.replace(' ', '_')}.png")
        plt.savefig(filename)
        plt.close()
        print(f"Saved plot: {filename}")


def heatmap_humidity_temp(data, out_folder="plots"):
    """Scatter plot (heatmap-style) of humidity vs temperature for each city."""
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    for city, df_city in data.groupby("City"):
        df_city = df_city.dropna(subset=['temperature', 'humidity'])
        if df_city.empty:
            print(f"No temp/humidity data for {city}, skipping heatmap.")
            continue
        plt.figure(figsize=(10, 6))
        plt.scatter(df_city["temperature"], df_city["humidity"], alpha=0.4, s=8)
        plt.xlabel("Temperature (°C)")
        plt.ylabel("Humidity (%)")
        plt.title(f"Humidity vs Temperature - {city}")
        plt.grid(True, alpha=0.2)
        filename = os.path.join(out_folder, f"humidity_vs_temp_{city.replace(' ', '_')}.png")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        print(f"Saved scatter heatmap: {filename}")


def daily_range_plot(data, out_folder="plots"):
    """Plot filled daily min-max temperature ranges for each city."""
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    data = data.copy()
    data['date_only'] = data['date'].dt.date
    daily_range = data.groupby(['City', 'date_only'])['temperature'].agg(['min', 'max']).reset_index()
    for city in daily_range['City'].unique():
        df_city = daily_range[daily_range['City'] == city].set_index('date_only').sort_index()
        if df_city.empty:
            print(f"No daily range data for {city}, skipping.")
            continue
        plt.figure(figsize=(12, 6))
        plt.fill_between(df_city.index, df_city['min'], df_city['max'], alpha=0.3)
        plt.title(f"Daily Temperature Range - {city}")
        plt.xlabel("Date")
        plt.ylabel("Temperature (°C)")
        plt.xticks(rotation=30)
        plt.tight_layout()
        filename = os.path.join(out_folder, f"temp_range_{city.replace(' ', '_')}.png")
        plt.savefig(filename)
        plt.close()
        print(f"Saved temperature range plot: {filename}")


def detect_anomalies(data, threshold=3):
    print("\nAnomaly Detection")
    anomalies_list = []

    for city, df_city in data.groupby('City'):
        dfc = df_city.copy()
        if dfc['temperature'].dropna().shape[0] < 2:
            continue
        mean = dfc['temperature'].mean()
        std = dfc['temperature'].std()
        if pd.isna(std) or std == 0:
            continue
        dfc['zscore'] = (dfc['temperature'] - mean) / std
        dfc['anomaly'] = np.abs(dfc['zscore']) > threshold
        anomalies_list.append(dfc[dfc['anomaly']])

    if anomalies_list:
        anomalies_df = pd.concat(anomalies_list, ignore_index=True)
        print(f"Detected {len(anomalies_df)} anomalies across all cities.")
        return anomalies_df
    else:
        print("No anomalies detected.")
        return pd.DataFrame()


def forecast(data, days_ahead=30):
    print("\nForecasting Future Temperatures...")
    forecasts = []
    for city, df_city in data.groupby('City'):
        dfc = df_city.copy().dropna(subset=['date', 'temperature'])
        if dfc.shape[0] < 2:
            print(f"Not enough data to forecast for {city}.")
            continue

        dfc['day_of_year'] = dfc['date'].dt.dayofyear
        X = dfc['day_of_year'].values
        y = dfc['temperature'].values

        varX = np.var(X)
        if varX == 0:
            slope = 0.0
        else:
            slope = np.cov(X, y)[0, 1] / varX
        intercept = np.mean(y) - slope * np.mean(X)

        last_date = dfc['date'].max()
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days_ahead)
        last_day = dfc['day_of_year'].max()
        future_days = np.arange(last_day + 1, last_day + days_ahead + 1)
        predictions = slope * future_days + intercept
        # If lengths mismatch, resize
        if len(predictions) != len(future_dates):
            predictions = np.resize(predictions, len(future_dates))

        forecast_df = pd.DataFrame({
            'City': city,
            'date': future_dates,
            'predicted_temperature': predictions
        })
        forecasts.append(forecast_df)

    if forecasts:
        forecast_all = pd.concat(forecasts, ignore_index=True)
        print(f"Forecast produced for {forecast_all['City'].nunique()} cities ({len(forecast_all)} rows).")
        return forecast_all
    else:
        print("No forecasts produced.")
        return pd.DataFrame()


def export_to_csv(data, filename):
    try:
        data.to_csv(filename, index=False)
        print(f"Exported: {filename}")
    except Exception as e:
        print(f"Failed to export {filename}: {e}")


# ---------------------- MAIN SCRIPT ---------------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather Data Analyzer")
    parser.add_argument("--city_file", type=str, default="weather.csv")
    parser.add_argument("--total_cities", type=int, default=10)
    parser.add_argument("--days_ahead", type=int, default=30)
    args = parser.parse_args()

    try:
        # Load and clean city file
        df_cities = pd.read_csv(args.city_file)
        df_cities.columns = df_cities.columns.str.strip()  # Remove unwanted spaces

        df_cities = df_cities.rename(columns={
            'latitude': 'Lat', 'Latitude': 'Lat', 'lat': 'Lat', 'LAT': 'Lat',
            'longitude': 'Lng', 'Longitude': 'Lng', 'long': 'Lng', 'lng': 'Lng', 'LNG': 'Lng',
            'city': 'City', 'CityName': 'City'
        })

        required_cols = {'City', 'Lat', 'Lng'}
        if not required_cols.issubset(df_cities.columns):
            raise Exception(f"CSV must contain columns: {required_cols}")

        # Step 1: Fetch data
        combined_file = fetch_weather_data(df_cities, total_cities=args.total_cities)

        # Step 2: Load combined data
        weather_data = load_data(combined_file)

        # Step 3: Perform analyses
        analyze_patterns(weather_data)

        # New enhanced analyses & visualizations
        seasonal_tbl = seasonal_insights(weather_data)                    # saves CSV
        corr_map = compute_correlation(weather_data)                      # saves per-city CSVs
        visualize_patterns(weather_data, out_folder="plots")              # line plots
        heatmap_humidity_temp(weather_data, out_folder="plots")          # scatter heatmaps
        daily_range_plot(weather_data, out_folder="plots")               # daily range plots

        anomalies = detect_anomalies(weather_data)
        forecasts = forecast(weather_data, days_ahead=args.days_ahead)

        # Step 4: Export final files
        export_to_csv(weather_data, "combined_weather_data.csv")
        if not anomalies.empty:
            export_to_csv(anomalies, "anomalies.csv")
        else:
            print("No anomalies file produced (empty).")
        if not forecasts.empty:
            export_to_csv(forecasts, "forecast.csv")
        else:
            print("No forecast file produced (empty).")

        print("\n🎉 All tasks completed successfully ✅")
    except Exception as main_e:
        print(f"\nFatal error: {main_e}")
        raise
