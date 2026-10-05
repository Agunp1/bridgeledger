from datetime import date

import altair as alt
import streamlit as st

from core import db, planner, ui

ui.page_setup("Check-in", "✅")
st.title("✅ Monthly check-in")
ui.require_profile()
st.caption("Five minutes at the end of each month. Compare what you planned with what you did. "
           "This is where the discipline comes from.")

plan = ui.current_plan()
first = plan.ledger.iloc[0] if len(plan.ledger) else None
planned = {
    "lifestyle": float(first.lifestyle) if first is not None else 0.0,
    "debt": float(first.debt_minimums + first.debt_extra) if first is not None else 0.0,
    "invest": float(first.goals + first.emergency) if first is not None else 0.0,
}

c1, c2, c3 = st.columns(3)
c1.metric("Planned lifestyle", ui.money(planned["lifestyle"]))
c2.metric("Planned debt payments", ui.money(planned["debt"]))
c3.metric("Planned investing + emergency", ui.money(planned["invest"]))

with st.form("checkin"):
    month = st.text_input("Month (YYYY-MM)", date.today().strftime("%Y-%m"))
    c1, c2 = st.columns(2)
    income = c1.number_input("Income received (USD equivalent)", 0.0, step=100.0)
    lifestyle = c2.number_input("Lifestyle spending (USD)", 0.0, step=50.0)
    c1, c2 = st.columns(2)
    debt_paid = c1.number_input("Total debt payments (USD equivalent)", 0.0, step=50.0)
    invested = c2.number_input("Invested + emergency fund (USD equivalent)", 0.0, step=50.0)
    notes = st.text_area("What went well / what to fix next month?")
    if st.form_submit_button("Save check-in", type="primary"):
        score = planner.discipline_score(planned, {"lifestyle": lifestyle, "debt": debt_paid, "invest": invested})
        db.save_checkin({
            "month": month, "income_usd": income, "lifestyle_usd": lifestyle,
            "debt_paid_usd": debt_paid, "invested_usd": invested,
            "planned_lifestyle_usd": planned["lifestyle"], "planned_debt_usd": planned["debt"],
            "planned_invest_usd": planned["invest"], "score": score, "notes": notes,
        })
        st.success(f"Saved. Discipline score: **{score}/100**")
        if score >= 85:
            st.balloons()
        st.info("Now update your balances so next month's plan starts from reality: "
                "debt balances on **Debts**, saved amounts on **Goals**, emergency fund on **Setup**.")

history = db.load_checkins()
if len(history):
    st.subheader("History")
    st.altair_chart(alt.Chart(history).mark_bar().encode(
        x=alt.X("month:N", title=None), y=alt.Y("score:Q", title="Discipline score", scale=alt.Scale(domain=[0, 100])),
        color=alt.condition(alt.datum.score >= 70, alt.value("#2e7d32"), alt.value("#c62828")),
        tooltip=["month", "score", "notes"]), width="stretch")
    st.dataframe(history.drop(columns=["id"]).sort_values("month", ascending=False),
                 hide_index=True, width="stretch")
