from __future__ import annotations
import json
from io import BytesIO
from datetime import datetime
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sklearn.linear_model import LinearRegression
from database import get_active_rates


def calculate_bill(units: float, rates: list[dict] | None = None):
    rates = rates or get_active_rates()
    units = max(0.0, float(units))
    breakdown = []
    total = 0.0

    for slab in sorted(rates, key=lambda x: float(x["slab_start"])):
        start = float(slab["slab_start"])
        end = slab["slab_end"]
        rate = float(slab["rate_per_liter"])

        if units <= start:
            continue

        if end is None:
            slab_units = units - start
            slab_label = f"Above {int(start)}"
        else:
            end = float(end)
            slab_units = min(units, end) - start
            slab_label = f"{int(start)} - {int(end)}"

        slab_units = max(0.0, slab_units)

        if slab_units > 0:
            cost = slab_units * rate
            total += cost
            breakdown.append({
                "slab": slab_label,
                "units": round(slab_units, 2),
                "rate": rate,
                "cost": round(cost, 2),
            })

    return round(total, 2), breakdown


def daily_usage_dataframe(logs: list[dict]) -> pd.DataFrame:
    if not logs:
        return pd.DataFrame(columns=["date", "usage_liters"])
    df = pd.DataFrame(logs)
    df["logged_at"] = pd.to_datetime(df["logged_at"])
    daily = (
        df.groupby(df["logged_at"].dt.date)["usage_liters"]
        .sum()
        .reset_index()
        .rename(columns={"logged_at": "date"})
    )
    daily.columns = ["date", "usage_liters"]
    daily["date"] = pd.to_datetime(daily["date"])
    return daily.sort_values("date")


def monthly_usage_dataframe(logs: list[dict]) -> pd.DataFrame:
    if not logs:
        return pd.DataFrame(columns=["month", "usage_liters"])
    df = pd.DataFrame(logs)
    df["logged_at"] = pd.to_datetime(df["logged_at"])
    monthly = (
        df.groupby(df["logged_at"].dt.to_period("M").astype(str))["usage_liters"]
        .sum()
        .reset_index()
    )
    monthly.columns = ["month", "usage_liters"]
    return monthly.sort_values("month")


def detect_abnormal_usage(daily_df: pd.DataFrame):
    if daily_df.empty or len(daily_df) < 7:
        return {"is_abnormal": False, "message": "Need at least 7 daily records for leak detection."}

    rolling_mean = daily_df["usage_liters"].rolling(window=7).mean().iloc[-1]
    latest = daily_df["usage_liters"].iloc[-1]
    ratio = latest / rolling_mean if rolling_mean and rolling_mean > 0 else 1

    is_abnormal = ratio >= 1.8 or latest >= (rolling_mean + 150)
    message = (
        f"Possible abnormal usage detected. Latest day: {latest:.1f}L vs 7-day average: {rolling_mean:.1f}L."
        if is_abnormal else
        f"Usage pattern looks normal. Latest day: {latest:.1f}L, 7-day average: {rolling_mean:.1f}L."
    )
    return {"is_abnormal": is_abnormal, "message": message, "latest": latest, "avg_7d": rolling_mean}


def predict_next_7_days(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df.empty or len(daily_df) < 7:
        return pd.DataFrame(columns=["date", "predicted_usage_liters"])

    df = daily_df.copy().sort_values("date").reset_index(drop=True)
    df["day_index"] = np.arange(len(df))
    X = df[["day_index"]]
    y = df["usage_liters"]

    model = LinearRegression()
    model.fit(X, y)

    future_idx = np.arange(len(df), len(df) + 7)
    future_dates = pd.date_range(df["date"].max() + pd.Timedelta(days=1), periods=7)
    predictions = model.predict(future_idx.reshape(-1, 1))
    predictions = np.maximum(predictions, 0)

    return pd.DataFrame({
        "date": future_dates,
        "predicted_usage_liters": predictions.round(2)
    })


def generate_recommendations(current_month_usage: float, predicted_avg: float, threshold: float):
    recs = []

    if current_month_usage > threshold:
        recs.append("Your usage is above the defined threshold. Check for leaks, dripping taps, and unnecessary overflow.")
    if predicted_avg > 100:
        recs.append("Predicted daily consumption is high. Consider bucket bathing, timed motor usage, and low-flow fixtures.")
    if current_month_usage < threshold * 0.7:
        recs.append("Great job maintaining efficient water usage. Keep monitoring peak-time consumption to stay efficient.")
    if not recs:
        recs.append("Usage is stable. Continue periodic meter checks and fix minor leaks early.")
    recs.append("Reuse RO discharge water or greywater for cleaning and gardening where feasible.")
    return recs


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def create_bill_pdf(user: dict, period_month: str, total_liters: float, breakdown: list[dict], total_amount: float) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Smart Water Supply Bill")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Name: {user['name']}")
    y -= 18
    c.drawString(40, y, f"Household: {user['household']}")
    y -= 18
    c.drawString(40, y, f"Connection ID: {user['connection_id']}")
    y -= 18
    c.drawString(40, y, f"RFID ID: {user['rfid_id']}")
    y -= 18
    c.drawString(40, y, f"Billing Period: {period_month}")
    y -= 18
    c.drawString(40, y, f"Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Slab")
    c.drawString(210, y, "Units")
    c.drawString(310, y, "Rate")
    c.drawString(420, y, "Cost")
    y -= 16
    c.line(40, y, 520, y)
    y -= 16

    c.setFont("Helvetica", 11)
    for row in breakdown:
        c.drawString(40, y, str(row["slab"]))
        c.drawString(210, y, str(row["units"]))
        c.drawString(310, y, f"₹{row['rate']}/L")
        c.drawString(420, y, f"₹{row['cost']}")
        y -= 18
        if y < 80:
            c.showPage()
            y = height - 50

    y -= 10
    c.line(40, y, 520, y)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Total Water Used: {round(total_liters,2)} L")
    y -= 20
    c.drawString(40, y, f"Total Amount Payable: ₹{round(total_amount,2)}")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(40, y, "Future scope: IoT sensor integration, QR-based access, auto valve control, and smart city dashboards.")

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def serialize_breakdown(breakdown: list[dict]) -> str:
    return json.dumps(breakdown)


def deserialize_breakdown(breakdown_text: str) -> list[dict]:
    try:
        return json.loads(breakdown_text)
    except Exception:
        return []
