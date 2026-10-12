"""Download hourly PM2.5 and PM10 for the study cities from Open-Meteo.

The numbers come from the CAMS global atmospheric model (about 40 km grid),
not from ground monitors. See the README for what that does and does not allow.

Run with:  uv run python -m hawa.fetch
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
START, END = "2023-01-01", "2025-12-31"
RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "pm_hourly.csv.gz"

# name: (latitude, longitude)
CITIES: dict[str, tuple[float, float]] = {
    "Delhi": (28.61, 77.21),
    "Lucknow": (26.85, 80.95),
    "Patna": (25.59, 85.14),
    "Kolkata": (22.57, 88.36),
    "Ahmedabad": (23.02, 72.57),
    "Bhilai": (21.21, 81.38),
    "Mumbai": (19.08, 72.88),
    "Hyderabad": (17.39, 78.49),
    "Bengaluru": (12.97, 77.59),
    "Chennai": (13.08, 80.27),
}


def fetch() -> pd.DataFrame:
    """One request for all cities; returns long-format rows (city, time, pm2_5, pm10)."""
    query = urllib.parse.urlencode(
        {
            "latitude": ",".join(str(lat) for lat, _ in CITIES.values()),
            "longitude": ",".join(str(lon) for _, lon in CITIES.values()),
            "hourly": "pm2_5,pm10",
            "start_date": START,
            "end_date": END,
            "timezone": "Asia/Kolkata",
        }
    )
    with urllib.request.urlopen(f"{API}?{query}", timeout=120) as response:
        payload = json.load(response)

    # The API answers in the order the coordinates were sent.
    frames = [
        pd.DataFrame(location["hourly"]).assign(city=city)
        for city, location in zip(CITIES, payload, strict=True)
    ]
    data = pd.concat(frames, ignore_index=True)
    data["time"] = pd.to_datetime(data["time"])
    return data[["city", "time", "pm2_5", "pm10"]]


if __name__ == "__main__":
    RAW_PATH.parent.mkdir(exist_ok=True)
    frame = fetch()
    frame.to_csv(RAW_PATH, index=False)
    print(f"Saved {len(frame):,} rows for {frame['city'].nunique()} cities to {RAW_PATH}")
