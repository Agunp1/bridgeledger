"""SQLite storage layer.

Everything lives in one local file (data/bridgeledger.db by default, override
with the BRIDGELEDGER_DB environment variable). The file is git-ignored, so
your real numbers never end up on GitHub.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "bridgeledger.db"


def db_path() -> Path:
    return Path(os.environ.get("BRIDGELEDGER_DB", DEFAULT_DB))


SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    name                    TEXT    NOT NULL,
    base_currency           TEXT    NOT NULL DEFAULT 'USD',
    income_usd              REAL    NOT NULL DEFAULT 0,   -- monthly take-home in the US
    income_inr              REAL    NOT NULL DEFAULT 0,   -- monthly income in India (rent, etc.)
    essentials_usd          REAL    NOT NULL DEFAULT 0,   -- rent, food, transport, insurance...
    essentials_inr          REAL    NOT NULL DEFAULT 0,   -- fixed family support, bills in India
    lifestyle_pct           REAL    NOT NULL DEFAULT 10,  -- guilt-free spending, % of income
    emergency_balance_usd   REAL    NOT NULL DEFAULT 0,
    emergency_months        REAL    NOT NULL DEFAULT 4,   -- full emergency fund target
    starter_emergency_months REAL   NOT NULL DEFAULT 1,
    fx_usd_inr              REAL    NOT NULL DEFAULT 88.0,
    fx_drift_pct            REAL    NOT NULL DEFAULT 2.0, -- assumed yearly INR depreciation
    remit_fee_pct           REAL    NOT NULL DEFAULT 1.0, -- cost of sending USD to India
    debt_strategy           TEXT    NOT NULL DEFAULT 'avalanche',
    high_interest_apr       REAL    NOT NULL DEFAULT 12,  -- debts at/above this get attacked first
    low_interest_apr        REAL    NOT NULL DEFAULT 6,   -- debts below this only get minimums
    min_goal_share_pct      REAL    NOT NULL DEFAULT 20,  -- goals keep this share even while killing debt
    inflation_usd_pct       REAL    NOT NULL DEFAULT 3.0,
    inflation_inr_pct       REAL    NOT NULL DEFAULT 5.5
);

CREATE TABLE IF NOT EXISTS debts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    country      TEXT NOT NULL DEFAULT 'US',     -- US / India
    currency     TEXT NOT NULL DEFAULT 'USD',    -- USD / INR
    kind         TEXT NOT NULL DEFAULT 'Other',    -- Credit card, Personal loan, Education loan, Home loan, ...
    balance      REAL NOT NULL DEFAULT 0,
    apr          REAL NOT NULL DEFAULT 0,        -- yearly interest %
    min_payment  REAL NOT NULL DEFAULT 0         -- in the debt's own currency
);

CREATE TABLE IF NOT EXISTS goals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    country       TEXT NOT NULL DEFAULT 'US',
    currency      TEXT NOT NULL DEFAULT 'USD',
    target_amount REAL NOT NULL DEFAULT 0,       -- in today's money; inflation is added
    target_date   TEXT NOT NULL,                 -- YYYY-MM
    priority      INTEGER NOT NULL DEFAULT 3,    -- 1 = most important
    current_value REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checkins (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    month          TEXT NOT NULL UNIQUE,         -- YYYY-MM
    income_usd     REAL NOT NULL DEFAULT 0,
    lifestyle_usd  REAL NOT NULL DEFAULT 0,      -- actual guilt-free spending
    debt_paid_usd  REAL NOT NULL DEFAULT 0,      -- actual total debt payments
    invested_usd   REAL NOT NULL DEFAULT 0,      -- actual goal + emergency contributions
    planned_lifestyle_usd REAL NOT NULL DEFAULT 0,
    planned_debt_usd      REAL NOT NULL DEFAULT 0,
    planned_invest_usd    REAL NOT NULL DEFAULT 0,
    score          INTEGER NOT NULL DEFAULT 0,   -- 0-100 discipline score
    notes          TEXT
);
"""

TABLE_COLUMNS = {
    "debts": ["name", "country", "currency", "kind", "balance", "apr", "min_payment"],
    "goals": ["name", "country", "currency", "target_amount", "target_date", "priority", "current_value"],
}


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# ---------- profile ----------

def get_profile() -> dict | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return dict(row) if row else None


def save_profile(values: dict) -> None:
    init_db()
    values = {k: v for k, v in values.items() if k != "id"}
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    updates = ", ".join(f"{k}=excluded.{k}" for k in values)
    with connect() as conn:
        conn.execute(
            f"INSERT INTO profile (id, {cols}) VALUES (1, {marks}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            list(values.values()),
        )


# ---------- debts / goals (edited as whole tables) ----------

def load_table(table: str) -> pd.DataFrame:
    init_db()
    with connect() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id", conn)
    return df


def replace_table(table: str, df: pd.DataFrame) -> None:
    """Replace every row of debts/goals with the edited DataFrame."""
    init_db()
    cols = TABLE_COLUMNS[table]
    clean = df.copy()
    clean = clean.dropna(subset=["name"])
    clean = clean[clean["name"].astype(str).str.strip() != ""]
    with connect() as conn:
        conn.execute(f"DELETE FROM {table}")
        for _, row in clean.iterrows():
            conn.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                [None if pd.isna(row.get(c)) else row.get(c) for c in cols],
            )


# ---------- check-ins ----------

def save_checkin(values: dict) -> None:
    init_db()
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    updates = ", ".join(f"{k}=excluded.{k}" for k in values if k != "month")
    with connect() as conn:
        conn.execute(
            f"INSERT INTO checkins ({cols}) VALUES ({marks}) "
            f"ON CONFLICT(month) DO UPDATE SET {updates}",
            list(values.values()),
        )


def load_checkins() -> pd.DataFrame:
    return load_table("checkins")


def reset_all() -> None:
    """Start over as a brand-new user."""
    path = db_path()
    if path.exists():
        path.unlink()
    init_db()
