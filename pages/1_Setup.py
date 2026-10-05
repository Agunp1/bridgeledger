import streamlit as st

from core import db, fx, ui

ui.page_setup("Setup", "👤")
st.title("👤 Setup")
st.caption("Your income, fixed costs and the rules your plan follows. All amounts are monthly.")

existing = db.get_profile() or {}
d = lambda k, default: existing.get(k, default)

if "fx_live" not in st.session_state:
    st.session_state.fx_live = None

if st.button("Fetch today's USD → INR rate"):
    rate = fx.fetch_usd_inr()
    if rate:
        st.session_state.fx_live = rate
        st.success(f"1 USD = ₹{rate:,.2f}")
    else:
        st.error("Couldn't reach the exchange-rate service. Enter the rate manually.")

with st.form("profile"):
    st.subheader("About you")
    name = st.text_input("Your name", d("name", ""))

    st.subheader("Income (monthly, after tax)")
    c1, c2 = st.columns(2)
    income_usd = c1.number_input("Income in the US (USD)", 0.0, step=100.0, value=float(d("income_usd", 0)))
    income_inr = c2.number_input("Income in India (INR), e.g. rent", 0.0, step=1000.0, value=float(d("income_inr", 0)))

    st.subheader("Essentials (monthly)")
    c1, c2 = st.columns(2)
    essentials_usd = c1.number_input("US essentials (USD): rent, food, transport, insurance",
                                     0.0, step=50.0, value=float(d("essentials_usd", 0)))
    essentials_inr = c2.number_input("India essentials (INR): family support, bills",
                                     0.0, step=1000.0, value=float(d("essentials_inr", 0)))

    st.subheader("Lifestyle & safety net")
    c1, c2, c3 = st.columns(3)
    lifestyle_pct = c1.slider("Guilt-free spending (% of income)", 0, 40, int(d("lifestyle_pct", 10)))
    emergency_balance = c2.number_input("Emergency fund saved today (USD)", 0.0, step=100.0,
                                        value=float(d("emergency_balance_usd", 0)))
    emergency_months = c3.number_input("Emergency fund target (months of essentials)", 1.0, 12.0,
                                       value=float(d("emergency_months", 4)), step=0.5)

    st.subheader("Currency")
    c1, c2, c3 = st.columns(3)
    fx_default = st.session_state.fx_live or float(d("fx_usd_inr", 88.0))
    fx_rate = c1.number_input("USD → INR rate", 1.0, 500.0, value=float(fx_default), step=0.25)
    fx_drift = c2.number_input("Assumed yearly INR depreciation %", -5.0, 10.0, value=float(d("fx_drift_pct", 2.0)), step=0.5)
    remit_fee = c3.number_input("Remittance cost % (fees + FX markup)", 0.0, 5.0, value=float(d("remit_fee_pct", 1.0)), step=0.1)

    with st.expander("Plan rules (advanced)"):
        c1, c2 = st.columns(2)
        strategy = c1.radio("Debt strategy", ["avalanche", "snowball"],
                            index=0 if d("debt_strategy", "avalanche") == "avalanche" else 1,
                            help="Avalanche: highest interest first (cheapest). Snowball: smallest balance first (motivating).")
        min_goal_share = c2.slider("Share kept for goals while paying high-interest debt (%)", 0, 60,
                                   int(d("min_goal_share_pct", 20)))
        c1, c2, c3 = st.columns(3)
        high_apr = c1.number_input("High-interest threshold (APR %)", 0.0, 50.0, float(d("high_interest_apr", 12)))
        low_apr = c2.number_input("Low-interest threshold (APR %)", 0.0, 50.0, float(d("low_interest_apr", 6)),
                                  help="Debts below this only get minimum payments; investing wins.")
        starter = c3.number_input("Starter emergency fund (months)", 0.0, 6.0, float(d("starter_emergency_months", 1)), step=0.5)
        c1, c2 = st.columns(2)
        infl_usd = c1.number_input("US inflation %", 0.0, 15.0, float(d("inflation_usd_pct", 3.0)), step=0.5)
        infl_inr = c2.number_input("India inflation %", 0.0, 15.0, float(d("inflation_inr_pct", 5.5)), step=0.5)

    if st.form_submit_button("Save", type="primary"):
        if not name.strip():
            st.error("Please enter your name.")
        else:
            db.save_profile({
                "name": name.strip(), "base_currency": "USD",
                "income_usd": income_usd, "income_inr": income_inr,
                "essentials_usd": essentials_usd, "essentials_inr": essentials_inr,
                "lifestyle_pct": lifestyle_pct, "emergency_balance_usd": emergency_balance,
                "emergency_months": emergency_months, "starter_emergency_months": starter,
                "fx_usd_inr": fx_rate, "fx_drift_pct": fx_drift, "remit_fee_pct": remit_fee,
                "debt_strategy": strategy, "high_interest_apr": high_apr, "low_interest_apr": low_apr,
                "min_goal_share_pct": min_goal_share,
                "inflation_usd_pct": infl_usd, "inflation_inr_pct": infl_inr,
            })
            st.cache_data.clear()
            st.success("Saved. Next: add your debts.")

if db.get_profile():
    ui.link("pages/2_Debts.py", "Next: Debts →", "💳")

st.divider()
with st.expander("Danger zone"):
    st.write("Delete everything and start over as a new user.")
    if st.checkbox("I understand this deletes all my data"):
        if st.button("Reset everything", type="secondary"):
            db.reset_all()
            st.cache_data.clear()
            st.success("All data deleted.")
            st.rerun()
