import requests
import os
import csv
import time
import sys
from datetime import date, timedelta

url = "https://api.weather.gc.ca/collections/climate-daily/items"

ec_obs_cities = [
    {"name": "Winnipeg", "province": "MB", "station_id": "5023262"},
    {"name": "Brandon", "province": "MB", "station_id": "5010490"},
    {"name": "Thompson", "province": "MB", "station_id": "5062918"},
    {"name": "Portage la Prairie", "province": "MB", "station_id": "5012324"},
    {"name": "Steinbach", "province": "MB", "station_id": "5021500"},
    {"name": "Regina", "province": "SK", "station_id": "4016699"},
    {"name": "Saskatoon", "province": "SK", "station_id": "4057165"},
    {"name": "Calgary", "province": "AB", "station_id": "3031094"},
    {"name": "Edmonton", "province": "AB", "station_id": "3012209"},
    {"name": "Vancouver", "province": "BC", "station_id": "1108446"},
    {"name": "Victoria", "province": "BC", "station_id": "1018611"},
    {"name": "Kelowna", "province": "BC", "station_id": "1123996"},
    {"name": "Toronto", "province": "ON", "station_id": "6158355"},
    {"name": "Ottawa", "province": "ON", "station_id": "6105978"},
    {"name": "Hamilton", "province": "ON", "station_id": "6153301"},
    {"name": "London", "province": "ON", "station_id": "6144478"},
    {"name": "Montreal", "province": "QC", "station_id": "7024745"},
    {"name": "Quebec City", "province": "QC", "station_id": "7010565"},
    {"name": "Gatineau", "province": "QC", "station_id": "6105978"},
    {"name": "Halifax", "province": "NS", "station_id": "8202255"},
    {"name": "Fredericton", "province": "NB", "station_id": "8101605"},
    {"name": "Moncton", "province": "NB", "station_id": "8103201"},
    {"name": "Charlottetown", "province": "PE", "station_id": "8300301"},
    {"name": "St. John's", "province": "NL", "station_id": "8403505"},
    {"name": "Whitehorse", "province": "YT", "station_id": "2101310"},
    {"name": "Yellowknife", "province": "NT", "station_id": "2204101"},
    {"name": "Iqaluit", "province": "NU", "station_id": "2402592"}
]


def fetch_with_fallback(station_id, max_days_back=6):
    for days_back in range(2, 2 + max_days_back):
        check_date = (date.today() - timedelta(days=days_back)).isoformat()

        params = {
            "f": "json",
            "CLIMATE_IDENTIFIER": station_id,
            "datetime": f"{check_date}/{check_date}",
            "limit": 5
        }

        props = None
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                features = data.get("features", [])
                if features:
                    props = features[0]["properties"]
                break
            except requests.exceptions.RequestException as e:
                print(f"    network error on {check_date}: {e}")
                time.sleep(2)

        if props is not None and props.get("MAX_TEMPERATURE") is not None:
            return check_date, props

    return None, None


file_exists = os.path.isfile("ec_observations.csv")

failed_cities = []

with open("ec_observations.csv", "a", newline="") as f:
    writer = csv.writer(f)

    if not file_exists:
        writer.writerow(["date", "city", "province", "temp_max_actual", "temp_min_actual", "precip_actual"])

    for city in ec_obs_cities:
        found_date, props = fetch_with_fallback(city["station_id"])

        if props is None:
            print(f"FAILED: {city['name']} (no valid data within lookback window)")
            failed_cities.append(city["name"])
            continue

        actual_high = props.get("MAX_TEMPERATURE")
        actual_low = props.get("MIN_TEMPERATURE")
        actual_precip = props.get("TOTAL_PRECIPITATION")

        writer.writerow([found_date, city["name"], city["province"], actual_high, actual_low, actual_precip])
        print(f"{city['name']}: {found_date}")

        time.sleep(0.5)

print("done")

if failed_cities:
    print(f"WARNING: {len(failed_cities)} cities failed permanently: {', '.join(failed_cities)}")
    sys.exit(1)