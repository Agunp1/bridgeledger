import pandas as pd
import streamlit as st

from core import db, ui

LOAN_TYPES = ["Credit card", "Personal loan", "Education loan", "Home loan", "Car loan", "Two-wheeler loan",
              "Gold loan", "Loan against property", "Business loan", "Buy now, pay later", "Medical loan",
              "Loan from family/friends", "Other"]
OLD_KINDS = {"short_term": "Personal loan", "education": "Education loan", "informal": "Loan from family/friends", "other": "Other"}

ui.page_setup("Debts", "💳")
st.title("💳 Debts")
profile = ui.require_profile()
st.caption("Everything you owe in the US and in India. Edit the table, add rows at the bottom, then save. "
           "Amounts are in each debt's own currency.")

df = db.load_table("debts").drop(columns=["id"], errors="ignore")
if df.empty:
    df = pd.DataFrame(columns=db.TABLE_COLUMNS["debts"])
else:
    df["kind"] = df["kind"].map(lambda k: OLD_KINDS.get(k, k if k in LOAN_TYPES else "Other"))

edited = st.data_editor(
    df, num_rows="dynamic", width="stretch", hide_index=True,
    column_config={
        "name": st.column_config.TextColumn("Debt", required=True),
        "country": st.column_config.SelectboxColumn("Country", options=["US", "India"], default="US", required=True),
        "currency": st.column_config.SelectboxColumn("Currency", options=["USD", "INR"], default="USD", required=True),
        "kind": st.column_config.SelectboxColumn(
            "Loan type", options=LOAN_TYPES, default="Credit card"),
        "balance": st.column_config.NumberColumn("Balance", min_value=0, format="%.0f", required=True),
        "apr": st.column_config.NumberColumn("Interest % / yr", min_value=0, max_value=100, format="%.1f", default=0.0),
        "min_payment": st.column_config.NumberColumn("Min payment / month", min_value=0, format="%.0f", default=0.0),
    },
)

if st.button("Save debts", type="primary"):
    problems = []
    for _, r in edited.dropna(subset=["name"]).iterrows():
        if r["country"] == "India" and r["currency"] == "USD" or r["country"] == "US" and r["currency"] == "INR":
            problems.append(f"'{r['name']}': country and currency don't match. Fine if intended, just checking.")
        if (r["balance"] or 0) > 0 and (r["min_payment"] or 0) <= 0:
            problems.append(f"'{r['name']}' has no minimum payment, so it will only shrink from extra payments.")
    db.replace_table("debts", edited.fillna({"apr": 0, "min_payment": 0, "kind": "Other"}))
    st.cache_data.clear()
    st.success("Debts saved.")
    for p in problems:
        st.info(p)

fx = float(profile["fx_usd_inr"])
saved = db.load_table("debts")
if len(saved):
    total = sum(b / (fx if c == "INR" else 1) for b, c in zip(saved.balance, saved.currency))
    hi = saved[saved.apr >= profile["high_interest_apr"]]
    st.metric("Total debt in USD", ui.money(total))
    if len(hi):
        st.warning("High-interest debt (gets attacked first): " + ", ".join(hi.name))

ui.link("pages/3_Goals.py", "Next: Goals →", "🎯")
