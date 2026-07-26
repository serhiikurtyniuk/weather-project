import requests
import csv
from datetime import date

url = "https://api.open-meteo.com/v1/forecast"

cities = [
    {"name": "Winnipeg", "province": "MB", "lat": 49.9, "lon": -97.14},
    {"name": "Regina", "province": "SK", "lat": 50.45, "lon": -104.6},
    {"name": "Toronto", "province": "ON", "lat": 43.65, "lon": -79.38}
]

today = date.today().isoformat()

with open("forecasts.csv", "a", newline="") as f:
    writer = csv.writer(f)

    for city in cities:
        params = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "daily": "temperature_2m_max,precipitation_probability_max",
            "timezone": "auto"
        }

        response = requests.get(url, params=params)
        data = response.json()

        dates = data["daily"]["time"]
        highs = data["daily"]["temperature_2m_max"]
        rain_chance = data["daily"]["precipitation_probability_max"]

        for i in range(len(dates)):
            writer.writerow([
                today,
                city["name"],
                city["province"],
                dates[i],
                i,
                highs[i],
                rain_chance[i]
            ])

print("done")