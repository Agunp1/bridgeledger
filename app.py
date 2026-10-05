"""BridgeLedger - personal finance discipline for money that lives in two countries.

Run with:  streamlit run app.py
"""
import altair as alt
import pandas as pd
import streamlit as st

from core import db, planner, sample, ui

ui.page_setup("Dashboard")
st.title("🌉 BridgeLedger")
st.caption("One plan for your US and India money: clear debt, stay disciplined, invest toward every goal.")

profile = db.get_profile()

if not profile:
    st.subheader("Welcome! Let's set you up.")
    st.markdown(
        "1. **Setup**: your income, essential costs and settings  \n"
        "2. **Debts**: everything you owe, in the US and India  \n"
        "3. **Goals**: house, land, wedding, travel, with target dates  \n"
        "4. **Plan**: your monthly waterfall, debt-free date and goal timelines  \n"
        "5. **Check-in**: once a month, record what you actually did"
    )
    c1, c2 = st.columns(2)
    c1.page_link("pages/1_Setup.py", label="Start as a new user", icon="👤")
    if c2.button("Explore with demo data"):
        sample.load_demo()
        st.rerun()
    st.stop()

debts = db.load_table("debts")
goals = db.load_table("goals")
plan = ui.current_plan()
nw = planner.net_worth_usd(profile, debts, goals)

st.subheader(f"Hi {profile['name'].split()[0]} 👋")
for w in plan.warnings:
    st.warning(w)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Net worth (USD)", ui.money(nw["net_worth"]))
c2.metric("Total debt (USD)", ui.money(nw["liabilities"]))
c3.metric("Debt-free", plan.debt_free_month or "beyond horizon")
c4.metric("Emergency fund full", plan.emergency_full_month or "beyond horizon")

# ---- this month's plan
st.markdown("### This month's plan")
if plan.this_month:
    tm = pd.DataFrame(plan.this_month)
    tm = tm[tm["amount"] > 0.5].copy()
    tm["Amount"] = [ui.money(a, c) for a, c in zip(tm["amount"], tm["currency"])]
    st.dataframe(tm[["bucket", "item", "Amount", "note"]].rename(
        columns={"bucket": "Bucket", "item": "Item", "note": "How"}),
        hide_index=True, width="stretch")
    first = plan.ledger.iloc[0]
    split = pd.DataFrame({
        "Bucket": ["Essentials", "Lifestyle", "Debt (min)", "Debt (extra)", "Emergency", "Goals", "Unallocated"],
        "USD": [first.essentials, first.lifestyle, first.debt_minimums, first.debt_extra,
                first.emergency, first.goals, first.unallocated],
    })
    split = split[split.USD > 0.5]
    st.altair_chart(
        alt.Chart(split).mark_bar().encode(
            x=alt.X("USD:Q", title="USD this month"), y=alt.Y("Bucket:N", sort=None, title=None),
            tooltip=["Bucket", alt.Tooltip("USD:Q", format=",.0f")]),
        width="stretch")

# ---- goals
st.markdown("### Goals")
if len(plan.goal_summary):
    cols = st.columns(min(3, len(plan.goal_summary)))
    for i, g in plan.goal_summary.iterrows():
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{g['Goal']}**  ·  P{g['Priority']}")
                saved = float(g["Saved now"])
                target = float(g["Target at date (with inflation)"]) or 1
                st.progress(min(saved / target, 1.0))
                st.caption(f"{ui.money(saved, g['Currency'])} of {ui.money(target, g['Currency'])} by {g['Target date']}")
                st.write(f"{'✅' if g['Status'] in ('On track', 'Reached') else '⚠️'} {g['Status']}  ·  {g['Mix now']}")
else:
    st.info("No goals yet. Add them on the Goals page.")

# ---- discipline streak
checkins = db.load_checkins()
st.markdown("### Discipline")
if len(checkins):
    last = checkins.sort_values("month").iloc[-1]
    streak = 0
    for s in checkins.sort_values("month", ascending=False)["score"]:
        if s >= 70:
            streak += 1
        else:
            break
    d1, d2, d3 = st.columns(3)
    d1.metric("Last check-in", last["month"])
    d2.metric("Last score", f"{int(last['score'])}/100")
    d3.metric("Streak (score ≥ 70)", f"{streak} month{'s' if streak != 1 else ''}")
else:
    st.info("No check-ins yet. At the end of each month, record what you actually did on the Check-in page.")

with st.sidebar:
    st.caption("Data is stored locally in `data/bridgeledger.db` and never leaves your computer.")
    if st.button("Load demo data (replaces everything)"):
        sample.load_demo()
        st.cache_data.clear()
        st.rerun()
