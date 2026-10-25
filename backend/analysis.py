from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"

_CACHED_ACTUALS: Optional[pd.DataFrame] = None
_CACHED_FORECASTS: Optional[pd.DataFrame] = None


def parse_target_date(d: Union[str, date, datetime]) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def load_data(
    data_dir: Optional[Union[Path, str]] = None,
    force_reload: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    global _CACHED_ACTUALS, _CACHED_FORECASTS

    if not force_reload and _CACHED_ACTUALS is not None and _CACHED_FORECASTS is not None:
        return _CACHED_ACTUALS, _CACHED_FORECASTS

    base_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    actuals_path = base_dir / "actual_wind.csv"
    forecasts_path = base_dir / "forecast_wind.csv"

    if not actuals_path.exists() or not forecasts_path.exists():
        raise FileNotFoundError(
            f"Data files not found in {base_dir}. Please run fetch_data.py first."
        )

    df_actuals = pd.read_csv(actuals_path)
    df_forecasts = pd.read_csv(forecasts_path)

    df_actuals["startTime"] = pd.to_datetime(df_actuals["startTime"], utc=True)
    if "publishTime" in df_actuals.columns:
        df_actuals["publishTime"] = pd.to_datetime(df_actuals["publishTime"], utc=True)

    df_forecasts["startTime"] = pd.to_datetime(df_forecasts["startTime"], utc=True)
    df_forecasts["publishTime"] = pd.to_datetime(df_forecasts["publishTime"], utc=True)

    _CACHED_ACTUALS = df_actuals
    _CACHED_FORECASTS = df_forecasts

    return df_actuals, df_forecasts


def select_decision_forecast(
    forecasts: pd.DataFrame,
    target_date: Union[str, date, datetime],
    cutoff_hour: int = 9,
    tz_name: str = "Europe/London",
) -> pd.DataFrame:
    t_date = parse_target_date(target_date)
    decision_date = t_date - timedelta(days=1)

    local_tz = ZoneInfo(tz_name)
    cutoff_local = datetime.combine(decision_date, time(cutoff_hour, 0), tzinfo=local_tz)
    cutoff_utc = cutoff_local.astimezone(timezone.utc)

    target_start_utc = datetime.combine(t_date, time(0, 0), tzinfo=timezone.utc)
    target_end_utc = datetime.combine(t_date, time(23, 59, 59), tzinfo=timezone.utc)

    mask = (
        (forecasts["startTime"] >= target_start_utc)
        & (forecasts["startTime"] <= target_end_utc)
        & (forecasts["publishTime"] <= cutoff_utc)
    )
    candidates = forecasts.loc[mask].copy()

    if candidates.empty:
        return pd.DataFrame(columns=["startTime", "forecast", "publishTime"])

    selected = (
        candidates.sort_values("publishTime")
        .groupby("startTime", as_index=False)
        .last()
    )

    selected = selected.rename(columns={"generation": "forecast"})
    return selected[["startTime", "forecast", "publishTime"]]


def compare_day(
    target_date: Union[str, date, datetime],
    cutoff_hour: int = 9,
    actuals: Optional[pd.DataFrame] = None,
    forecasts: Optional[pd.DataFrame] = None,
    how: str = "left",
) -> pd.DataFrame:
    if actuals is None or forecasts is None:
        loaded_act, loaded_fc = load_data()
        actuals = actuals if actuals is not None else loaded_act
        forecasts = forecasts if forecasts is not None else loaded_fc

    t_date = parse_target_date(target_date)

    target_start_utc = datetime.combine(t_date, time(0, 0), tzinfo=timezone.utc)
    target_end_utc = datetime.combine(t_date, time(23, 59, 59), tzinfo=timezone.utc)

    act_mask = (actuals["startTime"] >= target_start_utc) & (
        actuals["startTime"] <= target_end_utc
    )
    day_actuals = actuals.loc[act_mask].copy()
    day_actuals = day_actuals.rename(columns={"generation": "actual"})

    day_forecast = select_decision_forecast(
        forecasts, target_date=t_date, cutoff_hour=cutoff_hour
    )

    merged = pd.merge(
        day_actuals[["startTime", "actual"]],
        day_forecast[["startTime", "forecast", "publishTime"]],
        on="startTime",
        how=how,
    )

    merged = merged.sort_values("startTime").reset_index(drop=True)

    merged["error"] = merged["forecast"] - merged["actual"]

    return merged[["startTime", "actual", "forecast", "error", "publishTime"]]


def compute_metrics(df: pd.DataFrame) -> Dict[str, Optional[Union[float, int, str]]]:
    default_note = "Forecast is hourly; accuracy is measured on hourly points only."

    if df.empty:
        return {
            "mae": None,
            "rmse": None,
            "bias": None,
            "mean_actual": None,
            "mean_forecast": None,
            "bias_percent": None,
            "n_points": 0,
            "note": default_note,
        }

    valid = df.dropna(subset=["actual", "forecast"]).copy()
    n_points = len(valid)

    if n_points == 0:
        return {
            "mae": None,
            "rmse": None,
            "bias": None,
            "mean_actual": None,
            "mean_forecast": None,
            "bias_percent": None,
            "n_points": 0,
            "note": default_note,
        }

    errors = valid["forecast"] - valid["actual"]

    mae = float(errors.abs().mean())
    rmse = float(np.sqrt((errors**2).mean()))
    bias = float(errors.mean())
    mean_actual = float(valid["actual"].mean())
    mean_forecast = float(valid["forecast"].mean())
    bias_percent = float((bias / mean_actual * 100)) if mean_actual != 0 else 0.0

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "mean_actual": round(mean_actual, 2),
        "mean_forecast": round(mean_forecast, 2),
        "bias_percent": round(bias_percent, 2),
        "n_points": n_points,
        "note": default_note,
    }


def compute_metrics_range(
    start_date: Union[str, date, datetime] = "2026-01-01",
    end_date: Union[str, date, datetime] = "2026-01-31",
    cutoff_hour: int = 9,
    actuals: Optional[pd.DataFrame] = None,
    forecasts: Optional[pd.DataFrame] = None,
) -> Dict[str, Optional[float]]:
    if actuals is None or forecasts is None:
        loaded_act, loaded_fc = load_data()
        actuals = actuals if actuals is not None else loaded_act
        forecasts = forecasts if forecasts is not None else loaded_fc

    s_date = parse_target_date(start_date)
    e_date = parse_target_date(end_date)

    daily_dfs = []
    curr = s_date
    while curr <= e_date:
        day_comp = compare_day(
            curr,
            cutoff_hour=cutoff_hour,
            actuals=actuals,
            forecasts=forecasts,
            how="left",
        )
        daily_dfs.append(day_comp)
        curr += timedelta(days=1)

    combined_df = pd.concat(daily_dfs, ignore_index=True)
    return compute_metrics(combined_df)


def run_sanity_check():
    print("=" * 70)
    print("RUNNING SANITY CHECK FOR JANUARY 2026 PURCHASE DECISIONS")
    print("Business Rule: Cutoff at 09:00 UK Time on Day D-1")
    print("=" * 70)

    actuals, forecasts = load_data()

    print("\n[Check 1] Half-hour Decision Forecast Availability per Target Day:")
    print("-" * 70)
    print(f"{'Target Day':<14} | {'Decision Cutoff (D-1)':<24} | {'Available Slots':<15} | {'Status'}")
    print("-" * 70)

    total_slots_expected = 48
    jan_start = date(2026, 1, 1)
    jan_end = date(2026, 1, 31)

    curr = jan_start
    all_comparisons = []

    while curr <= jan_end:
        dec_date = curr - timedelta(days=1)
        comp = compare_day(curr, cutoff_hour=9, actuals=actuals, forecasts=forecasts)
        all_comparisons.append(comp)

        forecast_slots_count = comp["forecast"].notna().sum()
        status = (
            "Complete (48/48)"
            if forecast_slots_count == total_slots_expected
            else f"Missing {total_slots_expected - forecast_slots_count} slots (:30 unforecasted in WINDFOR stream)"
        )

        cutoff_str = f"{dec_date.strftime('%Y-%m-%d')} 09:00 UK"
        print(
            f"{curr.strftime('%Y-%m-%d'):<14} | {cutoff_str:<24} | {forecast_slots_count:>2}/{total_slots_expected} slots    | {status}"
        )
        curr += timedelta(days=1)

    print("-" * 70)

    combined = pd.concat(all_comparisons, ignore_index=True)
    metrics = compute_metrics(combined)

    print("\n[Check 2] Overall January 2026 Evaluation Metrics:")
    print("-" * 70)
    print(f"  • Mean Absolute Error (MAE) : {metrics['mae']:.2f} MW")
    print(f"  • Root Mean Sq Error (RMSE) : {metrics['rmse']:.2f} MW")
    print(f"  • Forecast Bias (Mean Error): {metrics['bias']:.2f} MW")
    print(f"  • Total Evaluated Points    : {metrics['n_points']} points (24 hourly slots/day x 31 days)")
    print("-" * 70)

    sample_day = "2026-01-15"
    sample_comp = compare_day(sample_day, cutoff_hour=9, actuals=actuals, forecasts=forecasts)

    print(f"\n[Check 3] Sample Day First 5 Rows ({sample_day}):")
    print("-" * 70)
    print(sample_comp.head(5).to_string(index=False))
    print("=" * 70)


if __name__ == "__main__":
    run_sanity_check()
