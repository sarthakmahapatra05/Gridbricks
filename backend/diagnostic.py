import pandas as pd
import numpy as np
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo

df_act = pd.read_csv('backend/data/actual_wind.csv')
df_fc = pd.read_csv('backend/data/forecast_wind.csv')
df_act['startTime'] = pd.to_datetime(df_act['startTime'], utc=True)
df_fc['startTime'] = pd.to_datetime(df_fc['startTime'], utc=True)
df_fc['publishTime'] = pd.to_datetime(df_fc['publishTime'], utc=True)

daily_stats = []
all_rows_cutoff = []

for day in range(1, 32):
    t_date = date(2026, 1, day)
    dec_date = t_date - timedelta(days=1)
    cutoff = datetime.combine(dec_date, time(9, 0), tzinfo=ZoneInfo('Europe/London')).astimezone(timezone.utc)

    day_start = datetime.combine(t_date, time(0, 0), tzinfo=timezone.utc)
    day_end = datetime.combine(t_date, time(23, 30), tzinfo=timezone.utc)

    act_day = df_act[(df_act['startTime'] >= day_start) & (df_act['startTime'] <= day_end)].copy()
    act_day = act_day.rename(columns={'generation': 'actual'})[['startTime', 'actual']]

    fc_cand = df_fc[(df_fc['startTime'] >= day_start) & (df_fc['startTime'] <= day_end) & (df_fc['publishTime'] <= cutoff)].copy()
    if not fc_cand.empty:
        fc_sel = fc_cand.sort_values('publishTime').groupby('startTime').last().reset_index()
        fc_sel = fc_sel.rename(columns={'generation': 'forecast'})[['startTime', 'forecast', 'publishTime']]
    else:
        fc_sel = pd.DataFrame(columns=['startTime', 'forecast', 'publishTime'])

    merged = pd.merge(act_day, fc_sel, on='startTime', how='inner')
    merged['error'] = merged['forecast'] - merged['actual']

    d_mae = merged['error'].abs().mean()
    d_bias = merged['error'].mean()
    d_act_mean = merged['actual'].mean()
    d_fc_mean = merged['forecast'].mean()
    daily_stats.append({
        'day': t_date.strftime('%Y-%m-%d'),
        'mae': d_mae,
        'bias': d_bias,
        'actual_mean': d_act_mean,
        'forecast_mean': d_fc_mean,
        'n': len(merged)
    })
    all_rows_cutoff.append(merged)

df_daily = pd.DataFrame(daily_stats)
df_cutoff = pd.concat(all_rows_cutoff, ignore_index=True)

all_rows_latest = []
for day in range(1, 32):
    t_date = date(2026, 1, day)
    day_start = datetime.combine(t_date, time(0, 0), tzinfo=timezone.utc)
    day_end = datetime.combine(t_date, time(23, 30), tzinfo=timezone.utc)

    act_day = df_act[(df_act['startTime'] >= day_start) & (df_act['startTime'] <= day_end)].copy()
    act_day = act_day.rename(columns={'generation': 'actual'})[['startTime', 'actual']]

    fc_cand = df_fc[(df_fc['startTime'] >= day_start) & (df_fc['startTime'] <= day_end) & (df_fc['publishTime'] <= df_fc['startTime'])].copy()
    if not fc_cand.empty:
        fc_sel = fc_cand.sort_values('publishTime').groupby('startTime').last().reset_index()
        fc_sel = fc_sel.rename(columns={'generation': 'forecast', 'publishTime': 'latest_publishTime'})[['startTime', 'forecast', 'latest_publishTime']]
    else:
        fc_sel = pd.DataFrame(columns=['startTime', 'forecast', 'latest_publishTime'])

    merged = pd.merge(act_day, fc_sel, on='startTime', how='inner')
    merged['error'] = merged['forecast'] - merged['actual']
    all_rows_latest.append(merged)

df_latest = pd.concat(all_rows_latest, ignore_index=True)

print("=== 1. DAILY MAE AND BIAS (Day-Ahead Cutoff 09:00 D-1) ===")
print(f"{'Date':<12} | {'MAE (MW)':>10} | {'Bias (MW)':>10} | {'Act Mean':>10} | {'Fc Mean':>10} | {'Pattern'}")
print("-" * 75)
for idx, row in df_daily.iterrows():
    pattern = "Positive Bias" if row['bias'] > 0 else "Negative Bias"
    print(f"{row['day']:<12} | {row['mae']:>10.1f} | {row['bias']:>+10.1f} | {row['actual_mean']:>10.1f} | {row['forecast_mean']:>10.1f} | {pattern}")

pos_bias_days = (df_daily['bias'] > 0).sum()
neg_bias_days = (df_daily['bias'] < 0).sum()
print("-" * 75)
print(f"Days with positive bias: {pos_bias_days} / 31")
print(f"Days with negative bias: {neg_bias_days} / 31")

print("\n=== 2. MEAN FORECAST VS ACTUAL & RATIO ===")
mean_fc = df_cutoff['forecast'].mean()
mean_act = df_cutoff['actual'].mean()
ratio = mean_fc / mean_act
print(f"Mean Forecast : {mean_fc:10.2f} MW")
print(f"Mean Actual   : {mean_act:10.2f} MW")
print(f"Ratio (Fc/Act): {ratio:10.4f} (Forecast is {ratio*100:.1f}% of Actual)")

print("\n=== 3. CORRELATION & OVERALL METRICS (Day-Ahead Cutoff) ===")
corr = df_cutoff['forecast'].corr(df_cutoff['actual'])
mae = df_cutoff['error'].abs().mean()
rmse = np.sqrt((df_cutoff['error']**2).mean())
bias = df_cutoff['error'].mean()
print(f"Correlation (r) : {corr:10.4f} (R^2 = {corr**2:.4f})")
print(f"Overall MAE     : {mae:10.2f} MW")
print(f"Overall RMSE    : {rmse:10.2f} MW")
print(f"Overall Bias    : {bias:+10.2f} MW")

print("\n=== 4. LATEST FORECAST AVAILABLE BEFORE EACH STARTTIME (NO CUTOFF) ===")
mean_fc_lat = df_latest['forecast'].mean()
mean_act_lat = df_latest['actual'].mean()
ratio_lat = mean_fc_lat / mean_act_lat
corr_lat = df_latest['forecast'].corr(df_latest['actual'])
mae_lat = df_latest['error'].abs().mean()
rmse_lat = np.sqrt((df_latest['error']**2).mean())
bias_lat = df_latest['error'].mean()
print(f"Points Evaluated: {len(df_latest)}")
print(f"Mean Forecast   : {mean_fc_lat:10.2f} MW")
print(f"Mean Actual     : {mean_act_lat:10.2f} MW")
print(f"Ratio (Fc/Act)  : {ratio_lat:10.4f} (Forecast is {ratio_lat*100:.1f}% of Actual)")
print(f"Correlation (r) : {corr_lat:10.4f} (R^2 = {corr_lat**2:.4f})")
print(f"Overall MAE     : {mae_lat:10.2f} MW")
print(f"Overall RMSE    : {rmse_lat:10.2f} MW")
print(f"Overall Bias    : {bias_lat:+10.2f} MW")
