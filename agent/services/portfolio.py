import base64
import os
import time
import requests

BASE_URL = os.getenv("TRADING212_BASE_URL", "https://live.trading212.com/api/v0")


def _get_auth_header() -> str:
    """Build the Trading 212 Basic auth header from environment variables."""
    api_key = os.getenv("TRADING212_API_KEY")
    api_secret = os.getenv("TRADING212_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("TRADING212_API_KEY and TRADING212_API_SECRET must be set")
    credentials_string = f"{api_key}:{api_secret}"
    encoded_credentials = base64.b64encode(credentials_string.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_credentials}"


def get_portfolio() -> dict:
    """Fetch all open positions from Trading 212."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/positions", headers=headers, timeout=10)
    r.raise_for_status()
    positions = r.json()
    result = {}
    for pos in positions:
        ticker = pos.get("ticker", "")
        if not ticker:
            continue
        avg = pos.get("averagePrice", 0)
        result[ticker] = {
            "shares": pos.get("quantity", 0),
            "avg_price": avg,
            "current_price": pos.get("currentPrice", 0),
            "pnl": round(pos.get("ppl", 0), 2),
            "pnl_pct": round(
                ((pos.get("currentPrice", 0) - avg) / max(avg, 0.01)) * 100, 2
            ),
        }
    return result


def get_account_summary() -> dict:
    """Fetch account cash balance and overall value from Trading 212."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/account/summary", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def get_order_history(limit: int = 20) -> list:
    """Fetch recent historical orders from Trading 212."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(
        f"{BASE_URL}/equity/history/orders",
        headers=headers,
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("items", data)


def get_pending_orders() -> list:
    """Fetch all currently pending (unfilled) orders from Trading 212."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/orders", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def get_trade_history(limit: int = 50) -> list:
    """Alias for get_order_history with a larger default limit."""
    return get_order_history(limit=limit)


def get_dividends(limit: int = 50) -> list:
    """Fetch dividend payment history from Trading 212."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(
        f"{BASE_URL}/equity/history/dividends",
        headers=headers,
        params={"limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("items", data)


# ── Instruments cache ────────────────────────────────────────────────────
_instruments_cache: list[dict] = []
_instruments_ts: float = 0.0


def _get_instruments() -> list[dict]:
    """Fetch the full instrument list from Trading 212, cached for 10 min."""
    global _instruments_cache, _instruments_ts
    if _instruments_cache and (time.time() - _instruments_ts) < 600:
        return _instruments_cache
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/metadata/instruments", headers=headers, timeout=30)
    r.raise_for_status()
    _instruments_cache = r.json()
    _instruments_ts = time.time()
    return _instruments_cache


def lookup_ticker(query: str, limit: int = 5) -> list[dict]:
    """Search for a Trading 212 instrument by name or partial ticker."""
    instruments = _get_instruments()
    q = query.lower()
    matches = []
    for inst in instruments:
        name = inst.get("name", "").lower()
        ticker = inst.get("ticker", "").lower()
        short = inst.get("shortName", "").lower()
        if q in name or q in ticker or q in short:
            matches.append({
                "ticker": inst.get("ticker", ""),
                "name": inst.get("name", ""),
                "exchange": inst.get("exchange", ""),
                "type": inst.get("type", ""),
            })
        if len(matches) >= limit:
            break
    return matches


def create_pie(name: str, instrument_allocations: list[dict], reinvest_dividends: bool = False) -> dict:
    """Create a new Trading 212 Pie. NOTE: Pies API is deprecated but still functional."""
    headers = {"Authorization": _get_auth_header(), "Content-Type": "application/json"}
    payload = {
        "name": name,
        "dividendCashAction": "REINVEST" if reinvest_dividends else "TO_ACCOUNT_CASH",
        "instrumentShares": {
            item["ticker"]: item["shares"] for item in instrument_allocations
        },
    }
    r = requests.post(f"{BASE_URL}/equity/pies", headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()
