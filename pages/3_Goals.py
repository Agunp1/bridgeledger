import re

import pandas as pd
import streamlit as st

from core import db, ui

ui.page_setup("Goals", "🎯")
st.title("🎯 Goals")
ui.require_profile()
st.caption("What you're investing toward. Enter the cost **in today's money**; inflation is added automatically. "
           "Target date as YYYY-MM. Priority 1 = most important.")

df = db.load_table("goals").drop(columns=["id"], errors="ignore")
if df.empty:
    df = pd.DataFrame(columns=db.TABLE_COLUMNS["goals"])
df["target_date"] = df["target_date"].astype(str)

edited = st.data_editor(
    df, num_rows="dynamic", width="stretch", hide_index=True,
    column_config={
        "name": st.column_config.TextColumn("Goal", required=True),
        "country": st.column_config.SelectboxColumn("Country", options=["US", "India"], default="US", required=True),
        "currency": st.column_config.SelectboxColumn("Currency", options=["USD", "INR"], default="USD", required=True),
        "target_amount": st.column_config.NumberColumn("Cost (today's money)", min_value=0, format="%.0f", required=True),
        "target_date": st.column_config.TextColumn("Target date (YYYY-MM)", required=True, validate=r"^\d{4}-\d{2}$"),
        "priority": st.column_config.NumberColumn("Priority", min_value=1, max_value=5, step=1, default=3),
        "current_value": st.column_config.NumberColumn("Already saved", min_value=0, format="%.0f", default=0.0),
    },
)

if st.button("Save goals", type="primary"):
    rows = edited.dropna(subset=["name"])
    bad = [n for n, d in zip(rows.name, rows.target_date) if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(d))]
    if bad:
        st.error("Fix the target date (YYYY-MM) for: " + ", ".join(bad))
    else:
        db.replace_table("goals", edited.fillna({"priority": 3, "current_value": 0}))
        st.cache_data.clear()
        st.success("Goals saved.")

with st.expander("Ideas for goals"):
    st.markdown(
        "- **Short term (< 2 yrs):** vacation, laptop, visa/travel costs → kept mostly in cash-like assets\n"
        "- **Medium term (2–5 yrs):** wedding, land in India, car → balanced mix\n"
        "- **Long term (5+ yrs):** US house down payment, building a rental house → mostly equity, "
        "shifting safer as the date gets closer (glide path)"
    )

ui.link("pages/4_Plan.py", "Next: See your plan →", "📈")
