"""Small shared helpers for the Streamlit pages."""
from __future__ import annotations

import streamlit as st

from . import db, planner

SYMBOL = {"USD": "$", "INR": "₹"}


def money(amount: float, currency: str = "USD") -> str:
    if amount is None:
        return "-"
    sym = SYMBOL.get(currency, "")
    if currency == "INR" and abs(amount) >= 100000:
        return f"{sym}{amount / 100000:,.2f} L"
    return f"{sym}{amount:,.0f}"


def page_setup(title: str, icon: str = "🌉") -> None:
    st.set_page_config(page_title=f"{title} · BridgeLedger", page_icon=icon, layout="wide")


def link(page: str, label: str, icon: str | None = None) -> None:
    """Page link that degrades to plain text if the page can't be resolved."""
    try:
        st.page_link(page, label=label, icon=icon)
    except Exception:
        st.markdown(f"{icon or ''} {label} (see the sidebar)")


def require_profile() -> dict:
    profile = db.get_profile()
    if not profile:
        st.info("No profile yet. Start on the **Setup** page, or load the demo from the Dashboard.")
        link("pages/1_Setup.py", "Go to Setup", "👤")
        st.stop()
    return profile


@st.cache_data(show_spinner=False)
def _cached_plan(profile_items: tuple, debts_json: str, goals_json: str, extra: float):
    import io
    import pandas as pd
    debts = pd.read_json(io.StringIO(debts_json), orient="records") if debts_json != "[]" else pd.DataFrame()
    goals = pd.read_json(io.StringIO(goals_json), orient="records", dtype={"target_date": str}) \
        if goals_json != "[]" else pd.DataFrame()
    return planner.run_plan(dict(profile_items), debts, goals, extra_income_usd=extra)


def current_plan(extra_income_usd: float = 0.0):
    profile = db.get_profile()
    debts = db.load_table("debts")
    goals = db.load_table("goals")
    return _cached_plan(tuple(sorted(profile.items())), debts.to_json(orient="records"),
                        goals.to_json(orient="records"), extra_income_usd)
