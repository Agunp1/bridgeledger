"""The planning engine.

Simulates your finances month by month. Each month the money flows through a
fixed waterfall (the "rulebook"):

    1. Essentials (US + India)
    2. Lifestyle allowance (guilt-free spending)
    3. Minimum payments on every debt
    4. Starter emergency fund
    5. Extra payments on high-interest debt (goals still keep a minimum share)
       ...or, once high-interest debt is gone, the full emergency fund
    6. Goal SIPs, by priority, sized from each goal's glide path
    7. Leftover -> moderate-interest debt, then accelerate the top goal

When a debt is cleared, its payment is automatically freed up for the next
debt and then for your goals ("rollover"). All money is pooled in USD; INR
income pays INR obligations first, and anything beyond that is converted with
the remittance fee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import assumptions as A

MAX_MONTHS = 480  # 40 years


# ---------------------------------------------------------------- helpers

def month_label(start: date, offset: int) -> str:
    y = start.year + (start.month - 1 + offset) // 12
    m = (start.month - 1 + offset) % 12 + 1
    return f"{y:04d}-{m:02d}"


def months_between(start: date, ym: str) -> int:
    """Months from the start month to a 'YYYY-MM' target."""
    y, m = (int(x) for x in str(ym)[:7].split("-"))
    return (y - start.year) * 12 + (m - start.month)


def nominal_target(amount_today: float, months: int, inflation_pct: float) -> float:
    return amount_today * (1 + inflation_pct / 100) ** (max(months, 0) / 12)


def required_monthly(value: float, target: float, months_left: int, currency: str) -> float:
    """Monthly contribution (goal currency) that reaches `target` by the deadline,
    following the glide path. The future value is linear in the payment, so we
    simulate twice and solve exactly."""
    if value >= target:
        return 0.0
    if months_left <= 0:
        return target - value

    def fv(payment: float) -> float:
        v = value
        for k in range(months_left):
            v = v * (1 + A.monthly_return(currency, months_left - k)) + payment
        return v

    base = fv(0.0)
    slope = fv(1.0) - base
    return max(0.0, (target - base) / slope)


class Wallet:
    """This month's money. USD income plus INR income held in India."""

    def __init__(self, usd: float, inr: float, fx: float, fee_pct: float):
        self.usd, self.inr, self.fx, self.fee = usd, inr, fx, fee_pct / 100

    def total_usd(self) -> float:
        return self.usd + self.inr / self.fx

    def usd_cost(self, amount: float, currency: str) -> float:
        """USD cost of paying `amount` in `currency` right now."""
        if currency == "INR":
            from_pool = min(amount, self.inr)
            rest = amount - from_pool
            return from_pool / self.fx + rest / self.fx * (1 + self.fee)
        from_usd = min(amount, self.usd)
        return from_usd + (amount - from_usd)

    def max_payable(self, usd_budget: float, currency: str) -> float:
        """How much of `currency` a USD budget can pay for."""
        usd_budget = min(usd_budget, self.total_usd())
        if usd_budget <= 0:
            return 0.0
        if currency == "INR":
            from_pool = min(self.inr, usd_budget * self.fx)
            left = usd_budget - from_pool / self.fx
            return from_pool + max(left, 0) * self.fx / (1 + self.fee)
        return usd_budget

    def pay(self, amount: float, currency: str) -> float:
        """Pay as much of `amount` as possible. Returns USD spent."""
        if amount <= 0:
            return 0.0
        amount = min(amount, self.max_payable(self.total_usd(), currency))
        if currency == "INR":
            from_pool = min(amount, self.inr)
            self.inr -= from_pool
            usd_needed = (amount - from_pool) / self.fx * (1 + self.fee)
            self.usd -= usd_needed
            spent = from_pool / self.fx + usd_needed
        else:
            from_usd = min(amount, self.usd)
            self.usd -= from_usd
            self.inr -= (amount - from_usd) * self.fx  # USD bill covered by INR money
            spent = amount
        self.usd = max(self.usd, 0.0) if self.usd > -1e-6 else self.usd
        self.inr = max(self.inr, 0.0) if self.inr > -1e-4 else self.inr
        return spent


# ---------------------------------------------------------------- results

@dataclass
class PlanResult:
    ledger: pd.DataFrame                       # one row per month, USD amounts per bucket
    debt_balances: pd.DataFrame                # month x debt (USD equivalent)
    goal_values: pd.DataFrame                  # month x goal (goal currency)
    debt_summary: pd.DataFrame
    goal_summary: pd.DataFrame
    this_month: list[dict] = field(default_factory=list)  # actionable lines for month 0
    warnings: list[str] = field(default_factory=list)
    debt_free_month: str | None = None
    emergency_full_month: str | None = None


# ---------------------------------------------------------------- engine

def run_plan(profile: dict, debts: pd.DataFrame, goals: pd.DataFrame,
             start: date | None = None, extra_income_usd: float = 0.0) -> PlanResult:
    start = (start or date.today()).replace(day=1)
    p = profile
    fx0 = float(p["fx_usd_inr"])
    drift = float(p["fx_drift_pct"]) / 100
    strategy = p.get("debt_strategy", "avalanche")
    high_apr, low_apr = float(p["high_interest_apr"]), float(p["low_interest_apr"])
    goal_share = float(p["min_goal_share_pct"]) / 100
    warnings: list[str] = []

    # --- state
    D = [dict(r) for _, r in debts.iterrows()] if len(debts) else []
    for d in D:
        d["bal"] = float(d["balance"] or 0)
        d["interest_paid"] = 0.0
        d["paid_off"] = None if d["bal"] > 0.005 else "already clear"

    G = [dict(r) for _, r in goals.iterrows()] if len(goals) else []
    for g in G:
        infl = p["inflation_inr_pct"] if g["currency"] == "INR" else p["inflation_usd_pct"]
        g["deadline"] = months_between(start, g["target_date"])
        g["target_nominal"] = nominal_target(float(g["target_amount"]), g["deadline"], float(infl))
        g["value"] = float(g["current_value"] or 0)
        g["done"] = None if g["value"] < g["target_nominal"] else month_label(start, 0)
        g["required_now"] = required_monthly(g["value"], g["target_nominal"], g["deadline"], g["currency"])
        if g["deadline"] < 0:
            warnings.append(f"Goal '{g['name']}' has a target date in the past. Update it on the Goals page.")
    G.sort(key=lambda g: (int(g["priority"]), g["deadline"]))

    ef = float(p["emergency_balance_usd"])
    ef_rate = (1 + A.EXPECTED_RETURNS["USD"]["safe"] / 100) ** (1 / 12) - 1

    last_goal = max([g["deadline"] for g in G], default=0)
    horizon = min(MAX_MONTHS, max(last_goal + 120, 60))

    ledger_rows, debt_rows, goal_rows, this_month = [], [], [], []
    debt_free_month = None if any(d["bal"] > 0.005 for d in D) else month_label(start, 0)
    ef_full_month = None

    def debt_order(ds, fx):
        if strategy == "snowball":
            return sorted(ds, key=lambda d: d["bal"] / (fx if d["currency"] == "INR" else 1))
        return sorted(ds, key=lambda d: -float(d["apr"]))

    for t in range(horizon):
        label = month_label(start, t)
        fx = fx0 * (1 + drift) ** (t / 12)
        income_usd = float(p["income_usd"]) + extra_income_usd
        w = Wallet(income_usd, float(p["income_inr"]), fx, float(p["remit_fee_pct"]))
        row = {"month": label, "essentials": 0.0, "lifestyle": 0.0, "debt_minimums": 0.0,
               "debt_extra": 0.0, "emergency": 0.0, "goals": 0.0, "unallocated": 0.0}
        lines = []  # detailed lines, kept only for month 0

        # growth and interest accrue first
        for d in D:
            if d["bal"] > 0.005:
                interest = d["bal"] * float(d["apr"]) / 1200
                d["bal"] += interest
                d["interest_paid"] += interest
        for g in G:
            if not g["done"]:
                g["value"] *= 1 + A.monthly_return(g["currency"], g["deadline"] - t)
        ef *= 1 + ef_rate

        # 1. essentials
        ess_usd_equiv = float(p["essentials_usd"]) + float(p["essentials_inr"]) / fx
        row["essentials"] += w.pay(float(p["essentials_usd"]), "USD")
        row["essentials"] += w.pay(float(p["essentials_inr"]), "INR")

        # 2. lifestyle allowance
        lifestyle = float(p["lifestyle_pct"]) / 100 * (income_usd + float(p["income_inr"]) / fx)
        lifestyle = min(lifestyle, w.total_usd())
        row["lifestyle"] = w.pay(lifestyle, "USD")
        if t == 0:
            lines.append({"bucket": "Lifestyle", "item": "Guilt-free spending", "amount": lifestyle,
                          "currency": "USD", "note": "Spend it without guilt; it's planned."})

        # 3. minimums
        active = [d for d in D if d["bal"] > 0.005]
        for d in active:
            pay_amt = min(float(d["min_payment"] or 0), d["bal"])
            cost = w.usd_cost(pay_amt, d["currency"])
            if cost > w.total_usd() + 1e-9:
                pay_amt = w.max_payable(w.total_usd(), d["currency"])
                if t == 0:
                    warnings.append(f"Not enough money for the minimum payment on '{d['name']}'.")
            row["debt_minimums"] += w.pay(pay_amt, d["currency"])
            d["bal"] -= pay_amt
            if t == 0:
                lines.append({"bucket": "Debt minimum", "item": d["name"], "amount": pay_amt,
                              "currency": d["currency"], "note": f"{float(d['apr']):.1f}% APR"})

        def pay_debts_extra(candidates, budget):
            spent = 0.0
            for d in debt_order([d for d in candidates if d["bal"] > 0.005], fx):
                if budget - spent <= 0.005:
                    break
                amt = min(d["bal"], w.max_payable(budget - spent, d["currency"]))
                cost = w.pay(amt, d["currency"])
                d["bal"] -= amt
                spent += cost
                if t == 0 and amt > 0.005:
                    lines.append({"bucket": "Debt extra", "item": d["name"], "amount": amt,
                                  "currency": d["currency"], "note": f"Extra payment ({strategy})"})
            return spent

        def fund_ef(budget):
            nonlocal ef
            amt = max(0.0, min(budget, w.total_usd()))
            spent = w.pay(amt, "USD")
            ef += spent
            if t == 0 and spent > 0.005:
                lines.append({"bucket": "Emergency fund", "item": "Emergency fund top-up", "amount": spent,
                              "currency": "USD", "note": "Keep in high-yield savings"})
            return spent

        # 4. starter emergency fund
        R = w.total_usd()
        starter_gap = float(p["starter_emergency_months"]) * ess_usd_equiv - ef
        if starter_gap > 0 and R > 0:
            row["emergency"] += fund_ef(min(starter_gap, A.STARTER_EMERGENCY_CAP * R))

        # 5. high-interest debt attack, or full emergency fund
        R = w.total_usd()
        high = [d for d in D if d["bal"] > 0.005 and float(d["apr"]) >= high_apr]
        if high and R > 0:
            row["debt_extra"] += pay_debts_extra(high, R * (1 - goal_share))
        else:
            full_gap = float(p["emergency_months"]) * ess_usd_equiv - ef
            if full_gap > 0 and R > 0:
                row["emergency"] += fund_ef(min(full_gap, A.FULL_EMERGENCY_CAP * R))

        # 6. goal SIPs in priority order
        for g in G:
            if g["done"]:
                continue
            months_left = g["deadline"] - t
            req = required_monthly(g["value"], g["target_nominal"], months_left, g["currency"])
            if t == 0:
                g["planned_now"] = 0.0
            if req <= 0:
                continue
            amt = min(req, w.max_payable(w.total_usd(), g["currency"]))
            row["goals"] += w.pay(amt, g["currency"])
            g["value"] += amt
            if t == 0:
                g["planned_now"] = amt
                eq = A.equity_share(months_left)
                v = A.SUGGESTED_VEHICLES.get(g["currency"], A.SUGGESTED_VEHICLES["USD"])
                lines.append({"bucket": "Goal SIP", "item": g["name"], "amount": amt, "currency": g["currency"],
                              "note": f"{eq:.0%} {v['equity']} / {1 - eq:.0%} {v['safe']}"
                                      + ("" if amt >= req - 0.5 else f" (short of {req:,.0f} needed)")})

        # 7. leftover: moderate debt, then accelerate top unfinished goal
        R = w.total_usd()
        moderate = [d for d in D if d["bal"] > 0.005 and float(d["apr"]) >= low_apr]
        if moderate and R > 0.005:
            row["debt_extra"] += pay_debts_extra(moderate, R)
        R = w.total_usd()
        open_goals = [g for g in G if not g["done"]]
        if open_goals and R > 0.005:
            g = open_goals[0]
            gap = max(0.0, g["target_nominal"] - g["value"])
            amt = min(gap, w.max_payable(R, g["currency"]))
            row["goals"] += w.pay(amt, g["currency"])
            g["value"] += amt
            if t == 0 and amt > 0.005:
                g["planned_now"] = g.get("planned_now", 0.0) + amt
                lines.append({"bucket": "Goal boost", "item": g["name"], "amount": amt,
                              "currency": g["currency"], "note": "Surplus sent to your top goal"})
        row["unallocated"] = max(0.0, w.total_usd())
        if t == 0 and row["unallocated"] > 0.5:
            lines.append({"bucket": "Unallocated", "item": "Surplus", "amount": row["unallocated"],
                          "currency": "USD", "note": "Add a goal or raise a target to use this"})

        # bookkeeping
        for d in D:
            if d["bal"] <= 0.005 and d["paid_off"] is None:
                d["bal"] = 0.0
                d["paid_off"] = label
        for g in G:
            if not g["done"] and g["value"] >= g["target_nominal"] - 0.5:
                g["done"] = label
        if debt_free_month is None and all(d["bal"] <= 0.005 for d in D):
            debt_free_month = label
        if ef_full_month is None and ef >= float(p["emergency_months"]) * ess_usd_equiv - 0.5:
            ef_full_month = label

        row["emergency_balance"] = ef
        row["total_debt_usd"] = sum(d["bal"] / (fx if d["currency"] == "INR" else 1) for d in D)
        ledger_rows.append(row)
        debt_rows.append({"month": label, **{d["name"]: d["bal"] / (fx if d["currency"] == "INR" else 1) for d in D}})
        goal_rows.append({"month": label, **{g["name"]: g["value"] for g in G}})
        if t == 0:
            this_month = lines

        if (debt_free_month and all(g["done"] for g in G) and ef_full_month and t >= last_goal):
            break

    # --- summaries
    debt_summary = pd.DataFrame([{
        "Debt": d["name"], "Country": d["country"], "Currency": d["currency"],
        "Balance now": float(d["balance"] or 0), "APR %": float(d["apr"]),
        "Paid off": d["paid_off"] or "beyond horizon",
        "Months": (months_between(start, d["paid_off"]) + 1) if d["paid_off"] and d["paid_off"] != "already clear" else None,
        "Interest paid": round(d["interest_paid"], 2),
    } for d in D])

    goal_rows_summary = []
    for g in G:
        status = "Reached" if g["value"] >= g["target_nominal"] - 0.5 and g["done"] == month_label(start, 0) else None
        if g["done"]:
            late = months_between(start, g["done"]) - g["deadline"]
            status = status or ("On track" if late <= 0 else f"Late by {late} mo")
        else:
            status = "Not reached in horizon"
        goal_rows_summary.append({
            "Goal": g["name"], "Priority": int(g["priority"]), "Currency": g["currency"],
            "Target date": str(g["target_date"])[:7], "Target (today's money)": float(g["target_amount"]),
            "Target at date (with inflation)": round(g["target_nominal"], 0),
            "Saved now": float(g["current_value"] or 0),
            "Needed monthly": round(g["required_now"], 0),
            "Planned this month": round(g.get("planned_now", 0.0), 0),
            "Mix now": f"{A.equity_share(g['deadline']):.0%} equity",
            "Horizon": A.risk_bucket(g["deadline"]),
            "Projected finish": g["done"] or "-", "Status": status,
        })
    goal_summary = pd.DataFrame(goal_rows_summary)

    if ledger_rows and ledger_rows[0]["essentials"] + 0.5 < float(p["essentials_usd"]) + float(p["essentials_inr"]) / fx0:
        warnings.insert(0, "Income does not cover essentials. Reduce fixed costs before anything else.")

    return PlanResult(
        ledger=pd.DataFrame(ledger_rows),
        debt_balances=pd.DataFrame(debt_rows),
        goal_values=pd.DataFrame(goal_rows),
        debt_summary=debt_summary,
        goal_summary=goal_summary,
        this_month=this_month,
        warnings=warnings,
        debt_free_month=debt_free_month,
        emergency_full_month=ef_full_month,
    )


# ---------------------------------------------------------------- discipline

def discipline_score(planned: dict, actual: dict) -> int:
    """0-100. Rewards hitting debt and investing targets, penalises lifestyle overspend."""
    def ratio(a, b):
        return 1.0 if b <= 0 else max(0.0, min(a / b, 1.0))

    debt = ratio(actual["debt"], planned["debt"])
    invest = ratio(actual["invest"], planned["invest"])
    over = max(0.0, actual["lifestyle"] - planned["lifestyle"])
    lifestyle = 1.0 if planned["lifestyle"] <= 0 else max(0.0, 1 - over / planned["lifestyle"])
    return round(100 * (0.4 * debt + 0.4 * invest + 0.2 * lifestyle))


def net_worth_usd(profile: dict, debts: pd.DataFrame, goals: pd.DataFrame) -> dict:
    fx = float(profile["fx_usd_inr"])
    conv = lambda amt, ccy: float(amt or 0) / (fx if ccy == "INR" else 1)
    assets = float(profile["emergency_balance_usd"]) + sum(
        conv(r.current_value, r.currency) for r in goals.itertuples())
    liabilities = sum(conv(r.balance, r.currency) for r in debts.itertuples())
    return {"assets": assets, "liabilities": liabilities, "net_worth": assets - liabilities}
