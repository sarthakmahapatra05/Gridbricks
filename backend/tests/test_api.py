import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_api_dates():
    response = client.get("/api/dates")
    assert response.status_code == 200
    data = response.json()
    assert data["min_date"] == "2026-01-01"
    assert data["max_date"] == "2026-01-31"
    assert len(data["available_dates"]) == 31
    assert data["default_cutoff_hour"] == 9


def test_api_accuracy_fields():
    response = client.get("/api/accuracy?start_date=2026-01-01&end_date=2026-01-31&cutoff_hour=9")
    assert response.status_code == 200
    data = response.json()

    assert "mae" in data
    assert "rmse" in data
    assert "bias" in data
    assert "mean_actual" in data
    assert "mean_forecast" in data
    assert "bias_percent" in data
    assert "n_points" in data
    assert "note" in data

    assert data["n_points"] == 744
    assert data["mae"] > 0
    assert data["rmse"] > 0
    assert data["bias"] > 0
    assert data["mean_actual"] > 0
    assert data["mean_forecast"] > 0
    assert data["bias_percent"] > 0
    assert data["note"] == "Forecast is hourly; accuracy is measured on hourly points only."

    assert "daily_breakdown" in data
    assert len(data["daily_breakdown"]) == 31
    day_0 = data["daily_breakdown"][0]
    assert "mean_actual" in day_0
    assert "mean_forecast" in day_0
    assert "bias_percent" in day_0


def test_api_day_comparison():
    target_date = "2026-01-15"
    response = client.get(f"/api/day?date={target_date}&cutoff_hour=9")
    assert response.status_code == 200
    data = response.json()

    assert data["target_date"] == target_date
    assert data["decision_date"] == "2026-01-14"
    assert data["cutoff_hour"] == 9
    assert len(data["slots"]) == 48

    slot_0 = data["slots"][0]
    assert slot_0["actual"] is not None
    assert slot_0["forecast"] is not None
    assert slot_0["error"] is not None
    assert slot_0["publishTime"] is not None

    slot_1 = data["slots"][1]
    assert slot_1["actual"] is not None
    assert slot_1["forecast"] is None
    assert slot_1["error"] is None
