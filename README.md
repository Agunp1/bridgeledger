# 🌉 BridgeLedger

**Personal finance discipline for people whose money lives in two countries.**

Most budgeting apps assume one country and one currency. International students and immigrants often have
debts in India *and* the US, earn in dollars, support family in rupees, and have goals on both sides:
land in India, a house in the US, a wedding, travel.

BridgeLedger turns all of that into **one monthly plan**: what to pay, what to invest, where, and what you can
spend guilt-free. A monthly check-in then tracks whether you actually followed it.

## What it does

| | |
|---|---|
| **Two currencies, one picture** | Every debt and goal keeps its own currency (USD/INR). The plan pools money in USD, uses INR income for INR costs first, and charges remittance fees only on money actually sent home. |
| **Debt payoff with rollover** | Avalanche or snowball. When a debt is cleared, its payment rolls to the next debt and then into your goals. |
| **Goal-based investing** | Each goal (house, land, wedding, vacation) gets its own monthly SIP, inflation-adjusted target and **glide path**: more equity when the goal is far away, safer assets as it gets close. |
| **A rulebook, not just a tracker** | A fixed monthly waterfall decides where every dollar goes (see below). |
| **What-if** | Slide in extra income and see every date move. |
| **Monthly check-in** | Planned vs actual → a 0–100 discipline score and a streak. |

## The monthly waterfall

1. Essentials (US + India)
2. Lifestyle allowance (% of income, guilt-free)
3. Minimum payments on every debt
4. Starter emergency fund (default 1 month)
5. High-interest debt (≥ 12% APR) gets the rest, except a share (default 20%) that keeps goals alive.
   Once it's gone → full emergency fund (default 4 months)
6. Goal SIPs in priority order, each sized to hit its target on time
7. Leftover → moderate-interest debt (≥ 6%), then accelerate the top goal

Debts below the low-interest threshold only get minimums, since investing is expected to earn more.
Every threshold is editable on the Setup page.

## Glide path

| Years to goal | Equity | Safer assets |
|---|---|---|
| 7+ | 80% | 20% |
| 5–7 | 70% | 30% |
| 3–5 | 50% | 50% |
| 2–3 | 30% | 70% |
| 1–2 | 15% | 85% |
| < 1 | 0% | 100% |

Expected returns (`core/assumptions.py`) are per currency: USD equity 8% / safe 4%, INR equity 11% / safe 6.5%.
They are planning assumptions, not predictions.

## Quick start

```bash
git clone https://github.com/Agunp1/bridgeledger.git
cd bridgeledger
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then either **Start as a new user** (Setup → Debts → Goals → Plan) or click **Explore with demo data**.

## Privacy

Your data is stored in a local SQLite file, `data/bridgeledger.db`, which is git-ignored.
Nothing is sent anywhere except an optional call to the free [Frankfurter](https://www.frankfurter.app/)
API for today's USD→INR rate.

## Project structure

```
app.py                 Dashboard: this month's plan, goals, discipline streak
pages/
  1_Setup.py           Income, essentials, currency, plan rules
  2_Debts.py           Editable debt table (US + India)
  3_Goals.py           Editable goal table
  4_Plan.py            Projections, debt payoff, goal timelines, what-if
  5_Check_in.py        Monthly planned-vs-actual and discipline score
core/
  planner.py           Month-by-month simulation engine (the waterfall)
  assumptions.py       Returns, glide path, caps
  db.py                SQLite storage
  fx.py                Live exchange rate
  sample.py            Fictional demo user
tests/                 pytest suite for the planning math
```

## Run the tests

```bash
pytest -q
```

## Roadmap

- [ ] Bank statement CSV import and auto-categorized spending
- [ ] Accounts table (separate US / NRE / NRO / brokerage balances)
- [ ] Rental income from a finished property feeding later goals
- [ ] Monte Carlo ranges instead of a single expected return
- [ ] Reminders for the monthly check-in

## Disclaimer

BridgeLedger is a planning tool, not financial, tax or investment advice. Cross-border rules
(NRI accounts, FATCA, nonresident tax filing) depend on your situation. Check with a qualified professional.

## License

MIT
