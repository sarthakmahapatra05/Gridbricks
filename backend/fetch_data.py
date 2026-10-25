import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BMRS_API_BASE = "https://data.elexon.co.uk/bmrs/api/v1"

DATA_DIR = Path(__file__).resolve().parent / "data"


def fetch_json(url: str, params: dict) -> list:
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    print(f"Fetching: {full_url}")

    req = urllib.request.Request(
        full_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Gridbricks-DataFetcher/1.0",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        if response.status != 200:
            raise RuntimeError(f"API request failed with HTTP {response.status}")
        raw_data = response.read().decode("utf-8")
        records = json.loads(raw_data)
        return records


def fetch_fuelhh_actuals(date_from: str = "2025-12-31", date_to: str = "2026-01-31") -> list:
    print("\n--- Fetching FUELHH Actual Wind Generation ---")
    url = f"{BMRS_API_BASE}/datasets/FUELHH/stream"
    params = {
        "settlementDateFrom": date_from,
        "settlementDateTo": date_to,
        "fuelType": "WIND",
    }

    records = fetch_json(url, params)

    wind_records = [r for r in records if r.get("fuelType") == "WIND"]
    print(f"Retrieved {len(wind_records)} FUELHH wind generation records.")
    return wind_records


def fetch_windfor_forecasts(
    datetime_from: str = "2025-12-31T00:00:00Z",
    datetime_to: str = "2026-01-31T23:59:59Z",
) -> list:
    print("\n--- Fetching WINDFOR Wind Generation Forecasts ---")
    url = f"{BMRS_API_BASE}/datasets/WINDFOR/stream"
    params = {
        "publishDateTimeFrom": datetime_from,
        "publishDateTimeTo": datetime_to,
    }

    records = fetch_json(url, params)
    print(f"Retrieved {len(records)} WINDFOR forecast records.")
    return records


def save_to_csv(records: list, file_path: Path, fieldnames: list):
    if not records:
        print(f"Warning: No records to save for {file_path.name}")
        return

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    file_size_kb = file_path.stat().st_size / 1024
    print(f"Saved {len(records)} rows to {file_path} ({file_size_kb:.1f} KB)")


def main():
    print("=" * 60)
    print("Elexon BMRS Wind Data Fetcher")
    print("Date window: Dec 31, 2025 -> Jan 31, 2026")
    print(f"Output directory: {DATA_DIR}")
    print("=" * 60)

    actuals = fetch_fuelhh_actuals(date_from="2025-12-31", date_to="2026-01-31")
    actuals_fields = [
        "startTime",
        "generation",
        "settlementDate",
        "settlementPeriod",
        "publishTime",
        "fuelType",
        "dataset",
    ]
    save_to_csv(actuals, DATA_DIR / "actual_wind.csv", actuals_fields)

    forecasts = fetch_windfor_forecasts(
        datetime_from="2025-12-31T00:00:00Z",
        datetime_to="2026-01-31T23:59:59Z",
    )
    forecasts_fields = [
        "startTime",
        "publishTime",
        "generation",
        "dataset",
    ]
    save_to_csv(forecasts, DATA_DIR / "forecast_wind.csv", forecasts_fields)

    print("\nData collection complete. Files ready in backend/data/:")
    print(f"  - {DATA_DIR / 'actual_wind.csv'}")
    print(f"  - {DATA_DIR / 'forecast_wind.csv'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error during data fetch: {e}", file=sys.stderr)
        sys.exit(1)
