import requests
import os
import csv
import time
import sys
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo

url_base = "https://api.weather.gc.ca/collections/citypageweather-realtime/items"

ec_cities = [
    {"name": "Winnipeg", "province": "MB", "ec_id": "mb-38", "tz": "America/Winnipeg"},
    {"name": "Brandon", "province": "MB", "ec_id": "mb-52", "tz": "America/Winnipeg"},
    {"name": "Thompson", "province": "MB", "ec_id": "mb-34", "tz": "America/Winnipeg"},
    {"name": "Portage la Prairie", "province": "MB", "ec_id": "mb-29", "tz": "America/Winnipeg"},
    {"name": "Steinbach", "province": "MB", "ec_id": "mb-13", "tz": "America/Winnipeg"},
    {"name": "Regina", "province": "SK", "ec_id": "sk-32", "tz": "America/Regina"},
    {"name": "Saskatoon", "province": "SK", "ec_id": "sk-40", "tz": "America/Regina"},
    {"name": "Calgary", "province": "AB", "ec_id": "ab-52", "tz": "America/Edmonton"},
    {"name": "Edmonton", "province": "AB", "ec_id": "ab-50", "tz": "America/Edmonton"},
    {"name": "Vancouver", "province": "BC", "ec_id": "bc-74", "tz": "America/Vancouver"},
    {"name": "Victoria", "province": "BC", "ec_id": "bc-85", "tz": "America/Vancouver"},
    {"name": "Kelowna", "province": "BC", "ec_id": "bc-48", "tz": "America/Vancouver"},
    {"name": "Toronto", "province": "ON", "ec_id": "on-143", "tz": "America/Toronto"},
    {"name": "Ottawa", "province": "ON", "ec_id": "on-118", "tz": "America/Toronto"},
    {"name": "Hamilton", "province": "ON", "ec_id": "on-77", "tz": "America/Toronto"},
    {"name": "London", "province": "ON", "ec_id": "on-137", "tz": "America/Toronto"},
    {"name": "Montreal", "province": "QC", "ec_id": "qc-147", "tz": "America/Toronto"},
    {"name": "Quebec City", "province": "QC", "ec_id": "qc-133", "tz": "America/Toronto"},
    {"name": "Gatineau", "province": "QC", "ec_id": "qc-126", "tz": "America/Toronto"},
    {"name": "Halifax", "province": "NS", "ec_id": "ns-19", "tz": "America/Halifax"},
    {"name": "Fredericton", "province": "NB", "ec_id": "nb-29", "tz": "America/Moncton"},
    {"name": "Moncton", "province": "NB", "ec_id": "nb-36", "tz": "America/Moncton"},
    {"name": "Charlottetown", "province": "PE", "ec_id": "pe-5", "tz": "America/Halifax"},
    {"name": "St. John's", "province": "NL", "ec_id": "nl-24", "tz": "America/St_Johns"},
    {"name": "Whitehorse", "province": "YT", "ec_id": "yt-16", "tz": "America/Whitehorse"},
    {"name": "Yellowknife", "province": "NT", "ec_id": "nt-24", "tz": "America/Yellowknife"},
    {"name": "Iqaluit", "province": "NU", "ec_id": "nu-21", "tz": "America/Iqaluit"}
]


def resolve_dates(forecasts, local_today):
    results = []
    current_date = None
    last_weekday = None

    for period in forecasts:
        value_text = period["period"]["value"]["en"]
        weekday_name = value_text.replace(" night", "").strip()

        if current_date is None:
            for offset in range(-2, 3):
                candidate = local_today + timedelta(days=offset)
                if candidate.strftime("%A") == weekday_name:
                    current_date = candidate
                    break
            if current_date is None:
                current_date = local_today
            last_weekday = weekday_name
        elif weekday_name != last_weekday:
            current_date = current_date + timedelta(days=1)
            last_weekday = weekday_name

        results.append((current_date, period))

    return results


def daily_max_precip(hourly_forecasts, tz):
    daily_max = {}

    for hour in hourly_forecasts:
        utc_time = datetime.fromisoformat(hour["timestamp"].replace("Z", "+00:00"))
        local_date = utc_time.astimezone(tz).date()

        lop_value = hour.get("lop", {}).get("value", {}).get("en")
        if lop_value is None:
            continue

        if local_date not in daily_max or lop_value > daily_max[local_date]:
            daily_max[local_date] = lop_value

    return daily_max


issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

file_exists = os.path.isfile("ec_forecasts.csv")

failed_cities = []

with open("ec_forecasts.csv", "a", newline="") as f:
    writer = csv.writer(f)

    if not file_exists:
        writer.writerow(["issued_at", "city", "province", "target_date", "horizon",
                         "temp_max", "temp_min", "precip_prob"])

    for city in ec_cities:
        url = f"{url_base}/{city['ec_id']}"
        params = {"f": "json"}

        data = None
        for attempt in range(20):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                if "properties" not in data or "forecastGroup" not in data["properties"]:
                    raise ValueError("missing forecastGroup in response")
                break
            except (requests.exceptions.RequestException, ValueError) as e:
                print(f"{city['name']} attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        if data is None:
            print(f"FAILED after 20 attempts: {city['name']}")
            failed_cities.append(city["name"])
            continue

        tz = ZoneInfo(city["tz"])
        local_today = datetime.now(tz).date()

        props = data["properties"]
        forecasts = props["forecastGroup"]["forecasts"]
        hourly = props.get("hourlyForecastGroup", {}).get("hourlyForecasts", [])

        dated_periods = resolve_dates(forecasts, local_today)
        precip_by_date = daily_max_precip(hourly, tz)

        # Collapse day/night periods into one row per date
        by_date = {}
        for target_date, period in dated_periods:
            temps = period.get("temperatures", {}).get("temperature", [])
            if not temps:
                continue

            temp_class = temps[0]["class"]["en"]
            temp_value = temps[0]["value"]["en"]

            if target_date not in by_date:
                by_date[target_date] = {"high": "", "low": ""}

            by_date[target_date][temp_class] = temp_value

        for target_date in sorted(by_date):
            horizon = (target_date - local_today).days
            precip = precip_by_date.get(target_date, "")

            writer.writerow([
                issued_at,
                city["name"],
                city["province"],
                target_date.isoformat(),
                horizon,
                by_date[target_date]["high"],
                by_date[target_date]["low"],
                precip
            ])

        time.sleep(1)

print("done")

if failed_cities:
    print(f"WARNING: {len(failed_cities)} cities failed permanently: {', '.join(failed_cities)}")
    sys.exit(1)