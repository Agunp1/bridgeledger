"""Planning assumptions. All of these are editable and deliberately conservative.

They are planning inputs, not predictions or investment advice.
"""

# Long-run nominal yearly returns (%) by currency and asset type.
EXPECTED_RETURNS = {
    "USD": {"equity": 8.0, "safe": 4.0},   # broad US index funds / HYSA, T-bills
    "INR": {"equity": 11.0, "safe": 6.5},  # Indian equity index funds / liquid, debt funds, FDs
}

# Glide path: equity share by years left until the goal.
# Money needed soon must not be exposed to a market crash.
GLIDE_PATH = [  # (minimum years left, equity share)
    (7, 0.80),
    (5, 0.70),
    (3, 0.50),
    (2, 0.30),
    (1, 0.15),
    (0, 0.00),
]

SUGGESTED_VEHICLES = {
    "USD": {"equity": "broad-market index fund / ETF", "safe": "high-yield savings, T-bills, money market"},
    "INR": {"equity": "equity index mutual fund", "safe": "liquid / short-term debt fund, FD"},
}

# How much of the remaining money each early bucket may take in one month,
# so no single bucket starves everything else.
STARTER_EMERGENCY_CAP = 0.50
FULL_EMERGENCY_CAP = 0.30


def equity_share(months_left: int) -> float:
    years = max(months_left, 0) / 12
    for min_years, share in GLIDE_PATH:
        if years >= min_years:
            return share
    return 0.0


def monthly_return(currency: str, months_left: int) -> float:
    r = EXPECTED_RETURNS.get(currency, EXPECTED_RETURNS["USD"])
    eq = equity_share(months_left)
    yearly = eq * r["equity"] + (1 - eq) * r["safe"]
    return (1 + yearly / 100) ** (1 / 12) - 1


def risk_bucket(months_left: int) -> str:
    years = months_left / 12
    if years < 2:
        return "Short term (protect)"
    if years < 5:
        return "Medium term (balanced)"
    return "Long term (growth)"
