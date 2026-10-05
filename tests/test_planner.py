from datetime import date

import pandas as pd
import pytest

from core import planner, sample
from core.planner import Wallet, required_monthly, run_plan

START = date(2026, 10, 1)


def base_profile(**over):
    p = dict(sample.DEMO_PROFILE)
    p.update(over)
    return p


def test_required_monthly_reaches_target():
    pmt = required_monthly(0, 10_000, 24, "USD")
    v = 0.0
    from core import assumptions as A
    for k in range(24):
        v = v * (1 + A.monthly_return("USD", 24 - k)) + pmt
    assert v == pytest.approx(10_000, rel=1e-6)


def test_required_monthly_zero_when_reached():
    assert required_monthly(12_000, 10_000, 24, "USD") == 0


def test_wallet_inr_uses_local_income_before_remitting():
    w = Wallet(usd=1000, inr=10_000, fx=100, fee_pct=1)
    spent = w.pay(10_000, "INR")  # fully covered by INR income: no fee
    assert spent == pytest.approx(100)
    assert w.usd == pytest.approx(1000)
    spent = w.pay(10_000, "INR")  # now remitted from USD with 1% fee
    assert spent == pytest.approx(101)


def test_avalanche_pays_highest_rate_first():
    debts = pd.DataFrame([
        {"name": "card", "country": "US", "currency": "USD", "kind": "short_term", "balance": 2000, "apr": 25, "min_payment": 50},
        {"name": "loan", "country": "US", "currency": "USD", "kind": "short_term", "balance": 1000, "apr": 15, "min_payment": 50},
    ])
    r = run_plan(base_profile(essentials_inr=0, debt_strategy="avalanche"), debts, pd.DataFrame(), start=START)
    paid = dict(zip(r.debt_summary.Debt, r.debt_summary["Paid off"]))
    assert paid["card"] <= paid["loan"]


def test_snowball_pays_smallest_first():
    debts = pd.DataFrame([
        {"name": "card", "country": "US", "currency": "USD", "kind": "short_term", "balance": 5000, "apr": 25, "min_payment": 50},
        {"name": "small", "country": "US", "currency": "USD", "kind": "short_term", "balance": 500, "apr": 13, "min_payment": 20},
    ])
    r = run_plan(base_profile(essentials_inr=0, debt_strategy="snowball"), debts, pd.DataFrame(), start=START)
    first_extra = [l for l in r.this_month if l["bucket"] == "Debt extra"][0]
    assert first_extra["item"] == "small"


def test_low_interest_debt_gets_only_minimums_first_month():
    debts = pd.DataFrame([{"name": "edu", "country": "India", "currency": "INR", "kind": "education",
                           "balance": 1_000_000, "apr": 4, "min_payment": 10_000}])
    goals = pd.DataFrame([{"name": "house", "country": "US", "currency": "USD", "target_amount": 50_000,
                           "target_date": "2034-10", "priority": 1, "current_value": 0}])
    r = run_plan(base_profile(emergency_balance_usd=50_000), debts, goals, start=START)
    assert not [l for l in r.this_month if l["bucket"] == "Debt extra"]
    assert r.ledger.iloc[0]["goals"] > 0


def test_freed_debt_money_rolls_into_goals():
    debts = pd.DataFrame([{"name": "card", "country": "US", "currency": "USD", "kind": "short_term",
                           "balance": 3000, "apr": 24, "min_payment": 100}])
    goals = pd.DataFrame([{"name": "house", "country": "US", "currency": "USD", "target_amount": 200_000,
                           "target_date": "2036-10", "priority": 1, "current_value": 0}])
    r = run_plan(base_profile(essentials_inr=0, emergency_balance_usd=20_000), debts, goals, start=START)
    payoff = r.debt_free_month
    before = r.ledger[r.ledger.month < payoff].goals.mean()
    after = r.ledger[r.ledger.month > payoff].head(6).goals.mean()
    assert after > before


def test_essentials_shortfall_warns():
    r = run_plan(base_profile(income_usd=1000), sample.demo_debts(), sample.demo_goals(), start=START)
    assert any("essentials" in w for w in r.warnings)


def test_demo_plan_runs_and_clears_debt():
    r = run_plan(base_profile(), sample.demo_debts(), sample.demo_goals(), start=START)
    assert r.debt_free_month is not None
    assert len(r.goal_summary) == 5


def test_discipline_score():
    planned = {"lifestyle": 500, "debt": 1000, "invest": 1000}
    assert planner.discipline_score(planned, {"lifestyle": 500, "debt": 1000, "invest": 1000}) == 100
    assert planner.discipline_score(planned, {"lifestyle": 1000, "debt": 0, "invest": 0}) == 0
