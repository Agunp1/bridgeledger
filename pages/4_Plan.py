import altair as alt
import pandas as pd
import streamlit as st

from core import assumptions as A
from core import ui

ui.page_setup("Plan", "📈")
st.title("📈 Your plan")
profile = ui.require_profile()

extra = st.slider("What if I earned more each month? (extra USD)", 0, 3000, 0, step=100,
                  help="See how a raise, side income or a cut in spending changes every date below.")
plan = ui.current_plan(float(extra))
base = ui.current_plan(0.0) if extra else plan

for w in plan.warnings:
    st.warning(w)

c1, c2, c3 = st.columns(3)
c1.metric("Debt-free", plan.debt_free_month or "beyond horizon",
          delta=None if not extra or plan.debt_free_month == base.debt_free_month else f"was {base.debt_free_month}",
          delta_color="off")
c2.metric("Emergency fund full", plan.emergency_full_month or "beyond horizon")
on_track = (plan.goal_summary["Status"].isin(["On track", "Reached"]).sum() if len(plan.goal_summary) else 0)
c3.metric("Goals on track", f"{on_track} / {len(plan.goal_summary)}")

tab_goals, tab_debts, tab_flow, tab_rules = st.tabs(["Goals", "Debts", "Monthly flow", "How the plan works"])

with tab_goals:
    if len(plan.goal_summary):
        st.dataframe(plan.goal_summary, hide_index=True, width="stretch")
        st.caption("'Needed monthly' is what the goal needs on its own. 'Planned this month' is what it gets "
                   "after debt and higher-priority goals. As debts clear, freed money flows to goals.")
        gv = plan.goal_values.melt("month", var_name="Goal", value_name="Value")
        cur = {r.Goal: r.Currency for r in plan.goal_summary.itertuples()}
        ccy = st.radio("Show goals in", ["INR", "USD"], horizontal=True)
        gv = gv[gv.Goal.map(cur) == ccy]
        if len(gv):
            st.altair_chart(alt.Chart(gv).mark_line().encode(
                x=alt.X("month:N", title=None, axis=alt.Axis(labelOverlap=True)),
                y=alt.Y("Value:Q", title=f"Value ({ccy})"), color="Goal:N",
                tooltip=["month", "Goal", alt.Tooltip("Value:Q", format=",.0f")]), width="stretch")
        st.markdown("**Glide path** (equity share by years left)")
        st.dataframe(pd.DataFrame([{"Years left": f"{y}+", "Equity": f"{s:.0%}", "Safer assets": f"{1 - s:.0%}"}
                                   for y, s in A.GLIDE_PATH]), hide_index=True)
    else:
        st.info("Add goals to see their timelines.")

with tab_debts:
    if len(plan.debt_summary):
        st.dataframe(plan.debt_summary, hide_index=True, width="stretch")
        db_long = plan.debt_balances.melt("month", var_name="Debt", value_name="USD")
        st.altair_chart(alt.Chart(db_long).mark_area().encode(
            x=alt.X("month:N", title=None, axis=alt.Axis(labelOverlap=True)),
            y=alt.Y("USD:Q", stack=True, title="Remaining (USD equivalent)"), color="Debt:N",
            tooltip=["month", "Debt", alt.Tooltip("USD:Q", format=",.0f")]), width="stretch")
        st.caption(f"Strategy: **{profile['debt_strategy']}**. When a debt is paid off, its payment rolls to the next one.")
    else:
        st.success("No debts. Everything goes to goals.")

with tab_flow:
    flow = plan.ledger[["month", "lifestyle", "debt_minimums", "debt_extra", "emergency", "goals", "unallocated"]]
    flow = flow.rename(columns={"lifestyle": "Lifestyle", "debt_minimums": "Debt (min)", "debt_extra": "Debt (extra)",
                                "emergency": "Emergency", "goals": "Goals", "unallocated": "Unallocated"})
    long = flow.melt("month", var_name="Bucket", value_name="USD")
    st.altair_chart(alt.Chart(long).mark_bar().encode(
        x=alt.X("month:N", title=None, axis=alt.Axis(labelOverlap=True)),
        y=alt.Y("USD:Q", stack=True, title="USD per month (after essentials)"), color="Bucket:N",
        tooltip=["month", "Bucket", alt.Tooltip("USD:Q", format=",.0f")]), width="stretch")
    st.caption("Watch the debt bars shrink and the goal bars grow: that's the rollover effect.")
    st.download_button("Download month-by-month plan (CSV)", plan.ledger.to_csv(index=False), "bridgeledger_plan.csv")

with tab_rules:
    st.markdown(f"""
Every month your money flows through this order:

1. **Essentials** (US + India)
2. **Lifestyle**: {profile['lifestyle_pct']:.0f}% of income, guilt-free
3. **Minimum payments** on every debt
4. **Starter emergency fund**: {profile['starter_emergency_months']:g} month(s) of essentials
5. **High-interest debt** (≥ {profile['high_interest_apr']:g}% APR) gets the rest, except
   {profile['min_goal_share_pct']:.0f}% that keeps your goals alive. Once it's gone → **full emergency fund**
   ({profile['emergency_months']:g} months)
6. **Goal SIPs** in priority order, each sized to hit its target on time
7. **Leftover** → moderate debt (≥ {profile['low_interest_apr']:g}% APR), then your top goal

Debts below {profile['low_interest_apr']:g}% only get minimums, because investing is expected to earn more.

**Currency:** INR income pays INR costs first. Anything sent from the US costs {profile['remit_fee_pct']:g}%
in fees, and the rupee is assumed to weaken {profile['fx_drift_pct']:g}% a year.

*Expected returns and the glide path are planning assumptions, not predictions or investment advice.*
""")
