"""A fictional demo user, so the app can be explored without real data."""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import db


def _ym(years_ahead: float) -> str:
    today = date.today()
    months = today.year * 12 + today.month - 1 + round(years_ahead * 12)
    return f"{months // 12:04d}-{months % 12 + 1:02d}"


DEMO_PROFILE = {
    "name": "Demo Student",
    "base_currency": "USD",
    "income_usd": 5200,
    "income_inr": 0,
    "essentials_usd": 2300,
    "essentials_inr": 15000,
    "lifestyle_pct": 10,
    "emergency_balance_usd": 1500,
    "emergency_months": 4,
    "starter_emergency_months": 1,
    "fx_usd_inr": 88.0,
    "fx_drift_pct": 2.0,
    "remit_fee_pct": 1.0,
    "debt_strategy": "avalanche",
    "high_interest_apr": 12,
    "low_interest_apr": 6,
    "min_goal_share_pct": 20,
    "inflation_usd_pct": 3.0,
    "inflation_inr_pct": 5.5,
}


def demo_debts() -> pd.DataFrame:
    return pd.DataFrame([
        {"name": "US credit card", "country": "US", "currency": "USD", "kind": "short_term",
         "balance": 3200, "apr": 24.9, "min_payment": 100},
        {"name": "Personal loan (India)", "country": "India", "currency": "INR", "kind": "short_term",
         "balance": 250000, "apr": 14.0, "min_payment": 8000},
        {"name": "Education loan (India)", "country": "India", "currency": "INR", "kind": "education",
         "balance": 1800000, "apr": 9.5, "min_payment": 25000},
        {"name": "Loan from family", "country": "India", "currency": "INR", "kind": "informal",
         "balance": 100000, "apr": 0.0, "min_payment": 5000},
    ])


def demo_goals() -> pd.DataFrame:
    return pd.DataFrame([
        {"name": "Vacation", "country": "US", "currency": "USD", "target_amount": 2500,
         "target_date": _ym(1), "priority": 4, "current_value": 0},
        {"name": "Wedding", "country": "India", "currency": "INR", "target_amount": 1500000,
         "target_date": _ym(3), "priority": 2, "current_value": 0},
        {"name": "Land in India", "country": "India", "currency": "INR", "target_amount": 3000000,
         "target_date": _ym(5), "priority": 1, "current_value": 0},
        {"name": "Build rental house (India)", "country": "India", "currency": "INR", "target_amount": 4000000,
         "target_date": _ym(9), "priority": 3, "current_value": 0},
        {"name": "US house down payment", "country": "US", "currency": "USD", "target_amount": 60000,
         "target_date": _ym(8), "priority": 3, "current_value": 0},
    ])


def load_demo() -> None:
    db.reset_all()
    db.save_profile(DEMO_PROFILE)
    db.replace_table("debts", demo_debts())
    db.replace_table("goals", demo_goals())
