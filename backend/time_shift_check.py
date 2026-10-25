from datetime import timedelta
import pandas as pd
import numpy as np
from backend.analysis import load_data, select_decision_forecast

def run_time_shift_analysis():
    actuals, forecasts = load_data()

    jan_days = [f"2026-01-{d:02d}" for d in range(1, 32)]
    decision_fc_list = []
    for day_str in jan_days:
        df_day = select_decision_forecast(forecasts, day_str, cutoff_hour=9)
        decision_fc_list.append(df_day)
    all_fc = pd.concat(decision_fc_list, ignore_index=True)
    all_fc = all_fc.rename(columns={"generation": "forecast"})

    act = actuals.rename(columns={"generation": "actual"})

    print("=" * 65)
    print("TIMESTAMP SHIFT CORRELATION CHECK (-2h to +2h)")
    print("Evaluating Actual(t) vs Forecast(t + shift)")
    print("=" * 65)
    print(f"{'Shift (hours)':<15} | {'Shift (slots)':<15} | {'N Points':<10} | {'Correlation (r)':<16} | {'MAE (MW)':<10}")
    print("-" * 65)

    shifts_in_half_hours = [-4, -3, -2, -1, 0, 1, 2, 3, 4]

    results = []
    for shift_slots in shifts_in_half_hours:
        shift_delta = timedelta(minutes=30 * shift_slots)
        shift_hours = shift_slots * 0.5

        fc_shifted = all_fc.copy()
        fc_shifted["matched_actual_time"] = fc_shifted["startTime"] - shift_delta

        merged = pd.merge(
            act[["startTime", "actual"]],
            fc_shifted[["matched_actual_time", "forecast"]],
            left_on="startTime",
            right_on="matched_actual_time",
            how="inner"
        ).dropna(subset=["actual", "forecast"])

        n = len(merged)
        if n > 2:
            r = merged["actual"].corr(merged["forecast"])
            mae = (merged["forecast"] - merged["actual"]).abs().mean()
            bias = (merged["forecast"] - merged["actual"]).mean()
            results.append({
                "shift_hours": shift_hours,
                "shift_slots": shift_slots,
                "n": n,
                "correlation": r,
                "mae": mae,
                "bias": bias
            })
            sign = "+" if shift_hours > 0 else ""
            print(f"{sign}{shift_hours:<14.1f} | {sign}{shift_slots:<14d} | {n:<10d} | {r:<16.4f} | {mae:<10.1f}")
        else:
            print(f"{shift_hours:<15.1f} | Insufficient data")

    print("=" * 65)

    best = max(results, key=lambda x: x["correlation"])
    print(f"Peak Correlation at Shift: {best['shift_hours']:+.1f}h (r = {best['correlation']:.4f}, MAE = {best['mae']:.1f} MW)")
    zero = next(r for r in results if r["shift_slots"] == 0)
    print(f"Zero Shift (Aligned):      {zero['shift_hours']:+.1f}h (r = {zero['correlation']:.4f}, MAE = {zero['mae']:.1f} MW)")
    print("=" * 65)

if __name__ == "__main__":
    run_time_shift_analysis()
