import sqlite3
import csv

conn = sqlite3.connect("weather.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS forecasts")
cursor.execute("""
    CREATE TABLE forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        issued_at TEXT,
        city TEXT,
        province TEXT,
        target_date TEXT,
        horizon INTEGER,
        temp_max REAL,
        temp_min REAL,
        precip_prob REAL,
        wind_speed_max REAL
    )
""")

cursor.execute("DROP TABLE IF EXISTS observations")
cursor.execute("""
    CREATE TABLE observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        date TEXT,
        city TEXT,
        province TEXT,
        temp_max_actual REAL,
        temp_min_actual REAL,
        precip_actual REAL,
        wind_speed_actual REAL
    )
""")

conn.commit()
print("Tables created.")


def dedupe(rows, key_indices):
    seen = set()
    result = []
    dropped = 0
    for r in rows:
        key = tuple(r[i] for i in key_indices)
        if key not in seen:
            seen.add(key)
            result.append(r)
        else:
            dropped += 1
    return result, dropped


def load_forecasts_csv(filepath, source_name):
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                source_name,
                row["issued_at"],
                row["city"],
                row["province"],
                row["target_date"],
                int(row["horizon"]),
                float(row["temp_max"]) if row["temp_max"] else None,
                float(row.get("temp_min")) if row.get("temp_min") else None,
                float(row["precip_prob"]) if row["precip_prob"] else None,
                float(row["wind_speed_max"]) if row.get("wind_speed_max") else None
            ))

    # dedupe on (source, issued_at, city, province, target_date, horizon)
    rows, dropped = dedupe(rows, key_indices=[0, 1, 2, 3, 4, 5])
    if dropped:
        print(f"  Dropped {dropped} duplicate row(s) from {filepath}")

    cursor.executemany("""
        INSERT INTO forecasts (source, issued_at, city, province, target_date, horizon, temp_max, temp_min, precip_prob, wind_speed_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    print(f"Loaded {len(rows)} rows from {filepath} as source '{source_name}'")


def load_observations_csv(filepath, source_name):
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                source_name,
                row["date"],
                row["city"],
                row["province"],
                float(row["temp_max_actual"]) if row["temp_max_actual"] else None,
                float(row["temp_min_actual"]) if row.get("temp_min_actual") else None,
                float(row["precip_actual"]) if row["precip_actual"] else None,
                float(row["wind_speed_actual"]) if row.get("wind_speed_actual") else None
            ))

    # dedupe on (source, date, city, province)
    rows, dropped = dedupe(rows, key_indices=[0, 1, 2, 3])
    if dropped:
        print(f"  Dropped {dropped} duplicate row(s) from {filepath}")

    cursor.executemany("""
        INSERT INTO observations (source, date, city, province, temp_max_actual, temp_min_actual, precip_actual, wind_speed_actual)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    print(f"Loaded {len(rows)} rows from {filepath} as source '{source_name}'")


load_forecasts_csv("forecasts.csv", "open-meteo")
load_forecasts_csv("ec_forecasts.csv", "ec")
load_observations_csv("observations.csv", "open-meteo")
load_observations_csv("ec_observations.csv", "ec")


cursor.execute("""
    SELECT source, COUNT(*) as row_count
    FROM forecasts
    GROUP BY source
""")
print("\nForecasts:")
for row in cursor.fetchall():
    print(row)

cursor.execute("""
    SELECT source, COUNT(*) as row_count
    FROM observations
    GROUP BY source
""")
print("\nObservations:")
for row in cursor.fetchall():
    print(row)

conn.close()