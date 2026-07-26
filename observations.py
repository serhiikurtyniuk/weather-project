import requests
import csv
from datetime import date, timedelta

url = "https://archive-api.open-meteo.com/v1/archive"

cities = [
    {"name": "Winnipeg", "province": "MB", "lat": 49.9, "lon": -97.14},
    {"name": "Regina", "province": "SK", "lat": 50.45, "lon": -104.6},
    {"name": "Toronto", "province": "ON", "lat": 43.65, "lon": -79.38}
]

yesterday = (date.today() - timedelta(days=1)).isoformat()

with open("observations.csv","a",newline="")as f:
    writer = csv.writer(f)

    for city in cities:
        params = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "start_date": yesterday,
            "end_date": yesterday,
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "auto"
        }

        response = requests.get(url, params=params)
        data = response.json()

        actual_high = data["daily"]["temperature_2m_max"][0]
        actual_precip = data["daily"]["precipitation_sum"][0]

        writer.writerow([
            yesterday,
            city["name"],
            city["province"],
            actual_high,
            actual_precip
        ])

print("done")