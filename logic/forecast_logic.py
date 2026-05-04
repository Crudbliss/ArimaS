"""
forecast_logic.py
-----------------
Demand forecasting using ARIMA and Random Forest.
Produces per-product 14-day demand predictions and reorder recommendations.
"""

import warnings
import math
import sys
import os

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")   # suppress statsmodels verbosity

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


# ── Data helpers ──────────────────────────────────────────────────────

def get_daily_sales(product_id: int) -> pd.DataFrame:
    """
    Return a DataFrame with columns [date, qty_sold] for one product.
    Dates are filled in (zeros for days with no sales) so the series is continuous.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT date(sold_at) AS day, SUM(qty_sold) AS qty
        FROM sales
        WHERE product_id = ?
        GROUP BY day
        ORDER BY day
    """, (product_id,)).fetchall()
    conn.close()

    if not rows:
        return pd.DataFrame(columns=["date", "qty"])

    df = pd.DataFrame(rows, columns=["date", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Fill missing days with 0
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_idx, fill_value=0)
    df.index.name = "date"
    df = df.reset_index()
    return df


def get_all_products_basic() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, stock_pieces, reorder_level, pieces_per_sack, bundle_qty "
        "FROM products ORDER BY name"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "stock": r[2],
         "reorder": r[3], "pps": r[4], "bundle": r[5]}
        for r in rows
    ]


# ── ARIMA Forecast ────────────────────────────────────────────────────

def arima_forecast(product_id: int, horizon: int = 14) -> dict:
    """
    Fit an ARIMA(1,1,1) on daily sales and forecast `horizon` days ahead.

    Returns:
        {
          "history_dates":  list of str,
          "history_values": list of float,
          "forecast_dates": list of str,
          "forecast_values": list of float,
          "total_predicted": float,
          "error": str | None
        }
    """
    from statsmodels.tsa.arima.model import ARIMA

    df = get_daily_sales(product_id)
    result = {
        "history_dates":   [],
        "history_values":  [],
        "forecast_dates":  [],
        "forecast_values": [],
        "total_predicted": 0.0,
        "error":           None,
    }

    if df.empty or len(df) < 7:
        result["error"] = "Not enough sales history (need at least 7 days)."
        return result

    series = df["qty"].astype(float).values
    result["history_dates"]  = [str(d.date()) for d in df["date"]]
    result["history_values"] = series.tolist()

    try:
        model  = ARIMA(series, order=(1, 1, 1))
        fitted = model.fit()
        fc     = fitted.forecast(steps=horizon)
        fc     = np.maximum(fc, 0)   # no negative demand

        last_date = df["date"].iloc[-1]
        fc_dates  = [
            str((last_date + pd.Timedelta(days=i + 1)).date())
            for i in range(horizon)
        ]

        result["forecast_dates"]  = fc_dates
        result["forecast_values"] = [round(float(v), 2) for v in fc]
        result["total_predicted"] = round(float(fc.sum()), 2)
    except Exception as e:
        result["error"] = f"ARIMA error: {e}"

    return result


# ── Random Forest Forecast ────────────────────────────────────────────

def rf_forecast(product_id: int, horizon: int = 14) -> dict:
    """
    Train a Random Forest Regressor on lag features and forecast `horizon` days.

    Features per day: day_of_week, month, lag_1..lag_7, rolling_7, rolling_14
    """
    from sklearn.ensemble import RandomForestRegressor

    df = get_daily_sales(product_id)
    result = {
        "history_dates":   [],
        "history_values":  [],
        "forecast_dates":  [],
        "forecast_values": [],
        "total_predicted": 0.0,
        "error":           None,
    }

    if df.empty or len(df) < 21:
        result["error"] = "Not enough sales history (need at least 21 days for RF)."
        return result

    result["history_dates"]  = [str(d.date()) for d in df["date"]]
    result["history_values"] = df["qty"].tolist()

    df = df.copy()
    df["dow"]       = df["date"].dt.dayofweek
    df["month"]     = df["date"].dt.month
    df["roll7"]     = df["qty"].rolling(7,  min_periods=1).mean().shift(1)
    df["roll14"]    = df["qty"].rolling(14, min_periods=1).mean().shift(1)
    for lag in range(1, 8):
        df[f"lag_{lag}"] = df["qty"].shift(lag)

    df = df.dropna()
    if len(df) < 14:
        result["error"] = "Still insufficient data after feature engineering."
        return result

    feature_cols = ["dow", "month", "roll7", "roll14"] + [f"lag_{i}" for i in range(1, 8)]
    X = df[feature_cols].values
    y = df["qty"].values

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Walk-forward forecast
    last_row = df.iloc[-1]
    history  = list(df["qty"].values)
    last_date = df["date"].iloc[-1]

    fc_dates  = []
    fc_values = []

    for i in range(horizon):
        next_date = last_date + pd.Timedelta(days=i + 1)
        lags      = list(reversed(history[-(7):]))
        roll7     = np.mean(history[-7:])
        roll14    = np.mean(history[-14:]) if len(history) >= 14 else roll7
        features  = np.array([[
            next_date.dayofweek, next_date.month,
            roll7, roll14, *lags
        ]])
        pred = max(0.0, float(model.predict(features)[0]))
        fc_values.append(round(pred, 2))
        fc_dates.append(str(next_date.date()))
        history.append(pred)

    result["forecast_dates"]  = fc_dates
    result["forecast_values"] = fc_values
    result["total_predicted"] = round(sum(fc_values), 2)
    return result


# ── Reorder Recommendations ───────────────────────────────────────────

def generate_recommendations() -> list[dict]:
    """
    For every product, run both models, average their 14-day predictions,
    and recommend sacks to order if stock won't cover demand.
    """
    products = get_all_products_basic()
    recs = []

    for p in products:
        a = arima_forecast(p["id"], horizon=14)
        r = rf_forecast(p["id"],    horizon=14)

        arima_total = a["total_predicted"] if not a["error"] else None
        rf_total    = r["total_predicted"] if not r["error"] else None

        # Average whichever models succeeded
        valids = [v for v in [arima_total, rf_total] if v is not None]
        if not valids:
            avg_demand = 0.0
            note = "Insufficient data"
        else:
            avg_demand = sum(valids) / len(valids)
            note = "ARIMA+RF avg" if len(valids) == 2 else ("ARIMA only" if arima_total else "RF only")

        # Pieces needed = demand × bundle_qty
        pieces_needed = avg_demand * p["bundle"]
        shortfall     = pieces_needed - p["stock"]
        sacks_needed  = math.ceil(shortfall / p["pps"]) if shortfall > 0 and p["pps"] > 0 else 0

        recs.append({
            "product_id":     p["id"],
            "name":           p["name"],
            "current_stock":  p["stock"],
            "predicted_14d":  round(avg_demand, 1),
            "pieces_needed":  round(pieces_needed, 1),
            "shortfall":      round(max(0.0, shortfall), 1),
            "sacks_to_order": sacks_needed,
            "status":         "⚠ Reorder" if sacks_needed > 0 else "OK",
            "note":           note,
        })

    recs.sort(key=lambda x: x["sacks_to_order"], reverse=True)
    return recs
