from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.analysis import (
    compare_day,
    compute_metrics,
    compute_metrics_range,
    load_data,
    parse_target_date,
)

app = FastAPI(
    title="UK Wind Generation Day-Ahead Forecasting API",
    description="Decision-support analytics for UK wholesale day-ahead power purchasing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    load_data()
except Exception as e:
    print(f"Warning: Initial data load failed: {e}")


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class DatesResponse(BaseModel):
    min_date: str
    max_date: str
    available_dates: List[str]
    default_cutoff_hour: int
    note: str


class MetricsResponse(BaseModel):
    mae: Optional[float]
    rmse: Optional[float]
    bias: Optional[float]
    mean_actual: Optional[float]
    mean_forecast: Optional[float]
    bias_percent: Optional[float]
    n_points: int
    note: str


class AccuracyResponse(MetricsResponse):
    start_date: str
    end_date: str
    cutoff_hour: int
    daily_breakdown: Optional[List[dict]] = None


class DaySlotItem(BaseModel):
    startTime: str
    actual: Optional[float]
    forecast: Optional[float]
    error: Optional[float]
    publishTime: Optional[str]


class DayComparisonResponse(BaseModel):
    target_date: str
    decision_date: str
    cutoff_hour: int
    cutoff_time_utc: str
    metrics: MetricsResponse
    slots: List[DaySlotItem]


@app.get("/", tags=["General"])
def root():
    return {
        "service": "UK Wind Generation Day-Ahead Forecasting API",
        "status": "healthy",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": ["/api/dates", "/api/day", "/api/accuracy"]
    }


@app.get("/api/health", response_model=HealthResponse, tags=["General"])
def get_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@app.get("/api/dates", response_model=DatesResponse, tags=["Metadata"])
def get_available_dates():
    jan_dates = [f"2026-01-{d:02d}" for d in range(1, 32)]
    return {
        "min_date": "2026-01-01",
        "max_date": "2026-01-31",
        "available_dates": jan_dates,
        "default_cutoff_hour": 9,
        "note": "Decision for target date D is made on day D-1 at cutoff_hour UK time.",
    }


@app.get("/api/accuracy", response_model=AccuracyResponse, tags=["Evaluation"])
def get_accuracy(
    start_date: str = Query("2026-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2026-01-31", description="End date (YYYY-MM-DD)"),
    cutoff_hour: int = Query(9, ge=0, le=23, description="Decision cutoff hour on day D-1 (UK time)"),
    include_daily: bool = Query(True, description="Whether to include daily breakdown"),
):
    try:
        s_date = parse_target_date(start_date)
        e_date = parse_target_date(end_date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    if s_date > e_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    actuals, forecasts = load_data()

    daily_records = []
    daily_breakdown = []
    curr = s_date

    while curr <= e_date:
        day_str = curr.strftime("%Y-%m-%d")
        comp = compare_day(curr, cutoff_hour=cutoff_hour, actuals=actuals, forecasts=forecasts)
        daily_records.append(comp)

        if include_daily:
            d_metrics = compute_metrics(comp)
            daily_breakdown.append({
                "date": day_str,
                "mae": d_metrics["mae"],
                "rmse": d_metrics["rmse"],
                "bias": d_metrics["bias"],
                "mean_actual": d_metrics["mean_actual"],
                "mean_forecast": d_metrics["mean_forecast"],
                "bias_percent": d_metrics["bias_percent"],
                "n_points": d_metrics["n_points"],
            })

        curr += timedelta(days=1)

    import pandas as pd
    combined_df = pd.concat(daily_records, ignore_index=True)
    overall_metrics = compute_metrics(combined_df)

    return {
        **overall_metrics,
        "start_date": s_date.strftime("%Y-%m-%d"),
        "end_date": e_date.strftime("%Y-%m-%d"),
        "cutoff_hour": cutoff_hour,
        "daily_breakdown": daily_breakdown if include_daily else None,
    }


@app.get("/api/day", response_model=DayComparisonResponse, tags=["Forecasts & Actuals"])
def get_day_comparison(
    date: str = Query("2026-01-15", description="Target delivery date (YYYY-MM-DD)"),
    cutoff_hour: int = Query(9, ge=0, le=23, description="Decision cutoff hour on day D-1 (UK time)"),
):
    try:
        t_date = parse_target_date(date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date parameter: {e}")

    actuals, forecasts = load_data()
    comp = compare_day(t_date, cutoff_hour=cutoff_hour, actuals=actuals, forecasts=forecasts)

    if comp.empty:
        raise HTTPException(status_code=404, detail=f"No data available for date {date}")

    day_metrics = compute_metrics(comp)
    decision_date = t_date - timedelta(days=1)

    slots = []
    for _, row in comp.iterrows():
        slots.append({
            "startTime": row["startTime"].isoformat() if hasattr(row["startTime"], "isoformat") else str(row["startTime"]),
            "actual": None if row["actual"] is None or str(row["actual"]) == "nan" else float(row["actual"]),
            "forecast": None if row["forecast"] is None or str(row["forecast"]) == "nan" else float(row["forecast"]),
            "error": None if row["error"] is None or str(row["error"]) == "nan" else float(row["error"]),
            "publishTime": None if row["publishTime"] is None or str(row["publishTime"]) in ["NaT", "nan"] else row["publishTime"].isoformat() if hasattr(row["publishTime"], "isoformat") else str(row["publishTime"]),
        })

    return {
        "target_date": t_date.strftime("%Y-%m-%d"),
        "decision_date": decision_date.strftime("%Y-%m-%d"),
        "cutoff_hour": cutoff_hour,
        "cutoff_time_utc": f"{decision_date.strftime('%Y-%m-%d')} {cutoff_hour:02d}:00:00 UTC",
        "metrics": day_metrics,
        "slots": slots,
    }


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
