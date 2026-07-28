import requests
import os
import csv
import time
import sys
from datetime import datetime, timezone


url = "https://api.open-meteo.com/v1/forecast"

cities = [
    {"name": "Winnipeg", "province": "MB", "lat": 49.90, "lon": -97.14},
    {"name": "Brandon", "province": "MB", "lat": 49.85, "lon": -99.95},
    {"name": "Thompson", "province": "MB", "lat": 55.74, "lon": -97.86},
    {"name": "Portage la Prairie", "province": "MB", "lat": 49.97, "lon": -98.29},
    {"name": "Steinbach", "province": "MB", "lat": 49.53, "lon": -96.68},
    {"name": "Regina", "province": "SK", "lat": 50.45, "lon": -104.60},
    {"name": "Saskatoon", "province": "SK", "lat": 52.13, "lon": -106.67},
    {"name": "Calgary", "province": "AB", "lat": 51.05, "lon": -114.07},
    {"name": "Edmonton", "province": "AB", "lat": 53.55, "lon": -113.49},
    {"name": "Vancouver", "province": "BC", "lat": 49.28, "lon": -123.12},
    {"name": "Victoria", "province": "BC", "lat": 48.43, "lon": -123.37},
    {"name": "Kelowna", "province": "BC", "lat": 49.89, "lon": -119.50},
    {"name": "Toronto", "province": "ON", "lat": 43.65, "lon": -79.38},
    {"name": "Ottawa", "province": "ON", "lat": 45.42, "lon": -75.70},
    {"name": "Hamilton", "province": "ON", "lat": 43.26, "lon": -79.87},
    {"name": "London", "province": "ON", "lat": 42.98, "lon": -81.25},
    {"name": "Montreal", "province": "QC", "lat": 45.50, "lon": -73.57},
    {"name": "Quebec City", "province": "QC", "lat": 46.81, "lon": -71.21},
    {"name": "Gatineau", "province": "QC", "lat": 45.48, "lon": -75.65},
    {"name": "Halifax", "province": "NS", "lat": 44.65, "lon": -63.57},
    {"name": "Fredericton", "province": "NB", "lat": 45.96, "lon": -66.64},
    {"name": "Moncton", "province": "NB", "lat": 46.09, "lon": -64.79},
    {"name": "Charlottetown", "province": "PE", "lat": 46.24, "lon": -63.13},
    {"name": "St. John's", "province": "NL", "lat": 47.56, "lon": -52.71},
    {"name": "Whitehorse", "province": "YT", "lat": 60.72, "lon": -135.05},
    {"name": "Yellowknife", "province": "NT", "lat": 62.45, "lon": -114.37},
    {"name": "Iqaluit", "province": "NU", "lat": 63.75, "lon": -68.51}
]

issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

file_exists = os.path.isfile("forecasts.csv")

failed_cities = []

with open("forecasts.csv", "a", newline="") as f:
    writer = csv.writer(f)

    if not file_exists:
        writer.writerow(["issued_at", "city", "province", "target_date", "horizon", "temp_max", "temp_min", "precip_prob", "wind_speed_max"])

    for city in cities:
        params = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 14
        }

        data = None
        for attempt in range(20):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.RequestException as e:
                print(f"{city['name']} attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        if data is None:
            print(f"FAILED after 20 attempts: {city['name']}")
            failed_cities.append(city["name"])
            continue

        dates = data["daily"]["time"]
        highs = data["daily"]["temperature_2m_max"]
        lows = data["daily"]["temperature_2m_min"]
        rain_chance = data["daily"]["precipitation_probability_max"]
        wind_speed = data["daily"]["wind_speed_10m_max"]

        for i in range(len(dates)):
            writer.writerow([issued_at, city["name"], city["province"], dates[i], i, highs[i], lows[i], rain_chance[i], wind_speed[i]])

print("done")

if failed_cities:
    print(f"WARNING: {len(failed_cities)} cities failed permanently: {', '.join(failed_cities)}")
    sys.exit(1)