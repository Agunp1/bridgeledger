"""Live USD -> INR rate from the free Frankfurter API (ECB data, no key needed)."""
from __future__ import annotations

import requests

URL = "https://api.frankfurter.app/latest?from=USD&to=INR"


def fetch_usd_inr(timeout: float = 6.0) -> float | None:
    try:
        resp = requests.get(URL, timeout=timeout)
        resp.raise_for_status()
        return float(resp.json()["rates"]["INR"])
    except Exception:
        return None
