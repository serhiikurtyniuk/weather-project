import requests
import csv
import os
import time
import sys
from datetime import date, timedelta
from calendar import monthrange

PREV_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

LEAD_TIMES = [1, 3, 7]
START_DATE = date(2024, 1, 1)
END_DATE = date.today() - timedelta(days=7)

MIN_HOURS_PER_DAY = 20

PROGRESS_FILE = "backfill_progress.txt"

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


def load_progress():
    if not os.path.isfile(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE) as f:
        return set(line.strip() for line in f if line.strip())


def mark_done(key):
    with open(PROGRESS_FILE, "a") as f:
        f.write(key + "\n")


def month_chunks(start, end):
    cur = date(start.year, start.month, 1)
    while cur <= end:
        last_day = date(cur.year, cur.month, monthrange(cur.year, cur.month)[1])
        yield (max(cur, start), min(last_day, end))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def fetch_json(url, params, attempts=10):
    for i in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"    attempt {i + 1} failed: {e}")
            time.sleep(3)
    return None


def bucket_by_day(times, values):
    buckets = {}
    for t, v in zip(times, values):
        if v is None:
            continue
        day = t[:10]
        buckets.setdefault(day, []).append(v)
    return {d: vs for d, vs in buckets.items() if len(vs) >= MIN_HOURS_PER_DAY}


def backfill_forecasts():
    file_exists = os.path.isfile("backfill_forecasts.csv")
    progress = load_progress()

    with open("backfill_forecasts.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["target_date", "city", "province", "horizon",
                             "temp_max", "temp_min", "wind_speed_max"])

        hourly_vars = []
        for lead in LEAD_TIMES:
            hourly_vars.append(f"temperature_2m_previous_day{lead}")
            hourly_vars.append(f"wind_speed_10m_previous_day{lead}")
        hourly_param = ",".join(hourly_vars)

        for city in cities:
            for chunk_start, chunk_end in month_chunks(START_DATE, END_DATE):
                key = f"fc|{city['name']}|{chunk_start.strftime('%Y-%m')}"
                if key in progress:
                    continue

                params = {
                    "latitude": city["lat"],
                    "longitude": city["lon"],
                    "hourly": hourly_param,
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "timezone": "auto"
                }

                data = fetch_json(PREV_RUNS_URL, params)
                if data is None or "hourly" not in data:
                    print(f"  SKIPPED {key}")
                    continue

                times = data["hourly"]["time"]
                rows_written = 0

                for lead in LEAD_TIMES:
                    temps = data["hourly"].get(f"temperature_2m_previous_day{lead}")
                    winds = data["hourly"].get(f"wind_speed_10m_previous_day{lead}")
                    if temps is None:
                        continue

                    temp_days = bucket_by_day(times, temps)
                    wind_days = bucket_by_day(times, winds) if winds else {}

                    for day in sorted(temp_days):
                        tvals = temp_days[day]
                        wvals = wind_days.get(day)
                        writer.writerow([
                            day,
                            city["name"],
                            city["province"],
                            lead,
                            round(max(tvals), 1),
                            round(min(tvals), 1),
                            round(max(wvals), 1) if wvals else ""
                        ])
                        rows_written += 1

                mark_done(key)
                print(f"  {key}: {rows_written} rows")
                time.sleep(0.4)


def backfill_observations():
    file_exists = os.path.isfile("backfill_observations.csv")
    progress = load_progress()

    with open("backfill_observations.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "city", "province",
                             "temp_max_actual", "temp_min_actual", "wind_speed_actual"])

        for city in cities:
            for chunk_start, chunk_end in month_chunks(START_DATE, END_DATE):
                key = f"obs|{city['name']}|{chunk_start.strftime('%Y-%m')}"
                if key in progress:
                    continue

                params = {
                    "latitude": city["lat"],
                    "longitude": city["lon"],
                    "hourly": "temperature_2m,wind_speed_10m",
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "timezone": "auto"
                }

                data = fetch_json(ARCHIVE_URL, params)
                if data is None or "hourly" not in data:
                    print(f"  SKIPPED {key}")
                    continue

                times = data["hourly"]["time"]
                temp_days = bucket_by_day(times, data["hourly"]["temperature_2m"])
                wind_days = bucket_by_day(times, data["hourly"]["wind_speed_10m"])

                rows_written = 0
                for day in sorted(temp_days):
                    tvals = temp_days[day]
                    wvals = wind_days.get(day)
                    writer.writerow([
                        day,
                        city["name"],
                        city["province"],
                        round(max(tvals), 1),
                        round(min(tvals), 1),
                        round(max(wvals), 1) if wvals else ""
                    ])
                    rows_written += 1

                mark_done(key)
                print(f"  {key}: {rows_written} rows")
                time.sleep(0.4)


print(f"Backfilling {START_DATE} to {END_DATE}, lead times {LEAD_TIMES}")
print("\n=== Forecasts ===")
backfill_forecasts()
print("\n=== Observations ===")
backfill_observations()
print("\ndone")