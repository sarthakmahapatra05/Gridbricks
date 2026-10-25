from datetime import datetime, timezone
import math
import numpy as np
import pandas as pd
import pytest

from backend.analysis import (
    compare_day,
    compute_metrics,
    select_decision_forecast,
)


def test_forecast_after_cutoff_is_ignored():
    target_date = "2026-01-05"
    start_time = pd.Timestamp("2026-01-05 12:00:00+00:00")

    forecasts = pd.DataFrame(
        [
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 08:30:00+00:00"),
                "generation": 1200,
            },
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 09:00:01+00:00"),
                "generation": 9999,
            },
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 14:00:00+00:00"),
                "generation": 8888,
            },
        ]
    )

    result = select_decision_forecast(forecasts, target_date=target_date, cutoff_hour=9)

    assert len(result) == 1
    selected_row = result.iloc[0]
    assert selected_row["startTime"] == start_time
    assert selected_row["forecast"] == 1200
    assert selected_row["publishTime"] == pd.Timestamp("2026-01-04 08:30:00+00:00")


def test_latest_forecast_before_cutoff_is_picked_when_several_exist():
    target_date = "2026-01-05"
    start_time = pd.Timestamp("2026-01-05 15:00:00+00:00")

    forecasts = pd.DataFrame(
        [
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-03 12:00:00+00:00"),
                "generation": 1000,
            },
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 06:30:00+00:00"),
                "generation": 1500,
            },
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 08:59:00+00:00"),
                "generation": 1750,
            },
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 10:00:00+00:00"),
                "generation": 3000,
            },
        ]
    )

    result = select_decision_forecast(forecasts, target_date=target_date, cutoff_hour=9)

    assert len(result) == 1
    selected_row = result.iloc[0]
    assert selected_row["forecast"] == 1750
    assert selected_row["publishTime"] == pd.Timestamp("2026-01-04 08:59:00+00:00")


def test_no_forecast_before_cutoff_returns_empty():
    target_date = "2026-01-05"
    start_time = pd.Timestamp("2026-01-05 12:00:00+00:00")

    forecasts = pd.DataFrame(
        [
            {
                "startTime": start_time,
                "publishTime": pd.Timestamp("2026-01-04 10:00:00+00:00"),
                "generation": 5000,
            }
        ]
    )

    result = select_decision_forecast(forecasts, target_date=target_date, cutoff_hour=9)
    assert len(result) == 0
    assert list(result.columns) == ["startTime", "forecast", "publishTime"]


def test_metrics_on_tiny_handmade_example():
    df = pd.DataFrame(
        {
            "actual": [100.0, 200.0, 300.0],
            "forecast": [110.0, 190.0, 330.0],
        }
    )

    metrics = compute_metrics(df)

    assert metrics["n_points"] == 3
    assert metrics["mae"] == pytest.approx(16.67, abs=0.01)
    assert metrics["rmse"] == pytest.approx(19.15, abs=0.01)
    assert metrics["bias"] == pytest.approx(10.00, abs=0.01)
    assert metrics["mean_actual"] == pytest.approx(200.00, abs=0.01)
    assert metrics["mean_forecast"] == pytest.approx(210.00, abs=0.01)
    assert metrics["bias_percent"] == pytest.approx(5.00, abs=0.01)
    assert metrics["note"] == "Forecast is hourly; accuracy is measured on hourly points only."


def test_missing_values_skipped_in_metrics():
    df = pd.DataFrame(
        {
            "actual": [100.0, 200.0, np.nan, 400.0],
            "forecast": [110.0, 190.0, 300.0, np.nan],
        }
    )

    metrics = compute_metrics(df)

    assert metrics["n_points"] == 2
    assert metrics["mae"] == pytest.approx(10.0, abs=0.01)
    assert metrics["rmse"] == pytest.approx(10.0, abs=0.01)
    assert metrics["bias"] == pytest.approx(0.0, abs=0.01)


def test_compare_day_merges_properly():
    target_date = "2026-01-02"
    t1 = pd.Timestamp("2026-01-02 00:00:00+00:00")
    t2 = pd.Timestamp("2026-01-02 00:30:00+00:00")

    actuals = pd.DataFrame(
        [
            {"startTime": t1, "generation": 5000},
            {"startTime": t2, "generation": 5200},
        ]
    )

    forecasts = pd.DataFrame(
        [
            {
                "startTime": t1,
                "publishTime": pd.Timestamp("2026-01-01 08:30:00+00:00"),
                "generation": 5500,
            }
        ]
    )

    comp = compare_day(
        target_date=target_date,
        cutoff_hour=9,
        actuals=actuals,
        forecasts=forecasts,
        how="left",
    )

    assert list(comp.columns) == ["startTime", "actual", "forecast", "error", "publishTime"]
    assert len(comp) == 2

    r0 = comp.iloc[0]
    assert r0["actual"] == 5000
    assert r0["forecast"] == 5500
    assert r0["error"] == 500

    r1 = comp.iloc[1]
    assert r1["actual"] == 5200
    assert pd.isna(r1["forecast"])
    assert pd.isna(r1["error"])
