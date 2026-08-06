import requests
import csv
import time

HOURLY_URL = "https://api.weather.gc.ca/collections/climate-hourly/items"

station_map = {
    "Winnipeg": "5023262", "Brandon": "5010490", "Thompson": "5062918",
    "Portage la Prairie": "5012324", "Steinbach": "5021500",
    "Regina": "4016699", "Saskatoon": "4057165",
    "Calgary": "3031094", "Edmonton": "3012209",
    "Vancouver": "1108824", "Victoria": "1018611", "Kelowna": "1123939",
    "Toronto": "6158359", "Ottawa": "6105978", "Hamilton": "6153301", "London": "6144473",
    "Montreal": "7024745", "Quebec City": "7010565", "Gatineau": "6105978",
    "Halifax": "8202255", "Fredericton": "8101605", "Moncton": "8103201",
    "Charlottetown": "8300301", "St. John's": "8403505",
    "Whitehorse": "2101310", "Yellowknife": "2204101", "Iqaluit": "2402592"
}


def fetch_wind_max(station_id, target_date):
    params = {
        "f": "json",
        "CLIMATE_IDENTIFIER": station_id,
        "datetime": f"{target_date}T00:00:00/{target_date}T23:00:00",
        "limit": 30
    }
    for attempt in range(3):
        try:
            r = requests.get(HOURLY_URL, params=params, timeout=30)
            r.raise_for_status()
            feats = r.json().get("features", [])
            speeds = [f["properties"].get("WIND_SPEED") for f in feats]
            speeds = [s for s in speeds if s is not None]
            return max(speeds) if speeds else None
        except requests.exceptions.RequestException as e:
            print(f"    error: {e}")
            time.sleep(2)
    return None


# --- read existing file, preserve original rows exactly ---
with open("ec_observations.csv", newline="") as f:
    reader = csv.DictReader(f)
    original_fieldnames = reader.fieldnames
    rows = list(reader)

# --- build the new header, adding wind_speed_actual only if missing ---
if "wind_speed_actual" in original_fieldnames:
    new_fieldnames = original_fieldnames
else:
    new_fieldnames = original_fieldnames + ["wind_speed_actual"]

filled = 0
for row in rows:
    if row.get("wind_speed_actual"):
        continue

    station_id = station_map.get(row["city"])
    if station_id is None:
        print(f"skip: no station for {row['city']}")
        row["wind_speed_actual"] = ""
        continue

    wind = fetch_wind_max(station_id, row["date"])
    row["wind_speed_actual"] = wind if wind is not None else ""
    print(f"{row['date']} {row['city']}: {wind}")
    filled += 1
    time.sleep(0.4)

# --- write to a NEW file first, never overwrite the original directly ---
with open("ec_observations_new.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=new_fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nFilled {filled} rows")
print("Wrote to ec_observations_new.csv — check it, then rename it over the original.")