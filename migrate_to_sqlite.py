import sqlite3
import csv

conn = sqlite3.connect("weather.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        issued_at TEXT,
        city TEXT,
        province TEXT,
        target_date TEXT,
        horizon INTEGER,
        temp_max REAL,
        temp_min REAL,
        precip_prob REAL
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        date TEXT,
        city TEXT,
        province TEXT,
        temp_max_actual REAL,
        precip_actual REAL
    )
""")

conn.commit()
print("Tables created.")

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
                float(row["precip_prob"]) if row["precip_prob"] else None
            ))

    cursor.executemany("""
        INSERT INTO forecasts (source, issued_at, city, province, target_date, horizon, temp_max, temp_min, precip_prob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                float(row["precip_actual"]) if row["precip_actual"] else None
            ))

    cursor.executemany("""
        INSERT INTO observations (source, date, city, province, temp_max_actual, precip_actual)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    print(f"Loaded {len(rows)} rows from {filepath} as source '{source_name}'")


cursor.execute("DELETE FROM forecasts")
cursor.execute("DELETE FROM observations")
conn.commit()
print("Cleared existing data.")

load_forecasts_csv("forecasts.csv", "open-meteo")
load_forecasts_csv("ec_forecasts.csv", "ec")
load_observations_csv("observations.csv", "open-meteo")


cursor.execute("""
    SELECT source, COUNT(*) as row_count
    FROM forecasts
    GROUP BY source
""")

for row in cursor.fetchall():
    print(row)

conn.close()