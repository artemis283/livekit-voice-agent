import base64
import os
import time
import requests

# Demo paper-trading base URL. Switch to https://live.trading212.com/api/v0 for real money.
BASE_URL = os.getenv("TRADING212_BASE_URL", "https://demo.trading212.com/api/v0")


def _get_auth_header() -> str:
    """Build the Trading 212 Basic auth header from environment variables."""
    api_key = os.getenv("TRADING212_API_KEY")
    api_secret = os.getenv("TRADING212_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("TRADING212_API_KEY and TRADING212_API_SECRET must be set in .env.local")
    credentials_string = f"{api_key}:{api_secret}"
    encoded_credentials = base64.b64encode(credentials_string.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded_credentials}"


def get_portfolio() -> dict:
    """Fetch all open positions from the Trading 212 account."""
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/positions", headers=headers, timeout=10)
    r.raise_for_status()
    positions = r.json()

    result = {}
    for pos in positions:
        ticker = pos.get("ticker", "")
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


def get_trade_history(limit: int = 50) -> list[dict]:
    """Fetch historical closed orders using cursor-based pagination.

    Returns up to `limit` filled orders, newest first.
    Uses the Trading 212 /equity/history/orders endpoint.
    Rate limit: 6 req / 1 min.
    """
    headers = {"Authorization": _get_auth_header()}
    orders: list[dict] = []
    path = f"{BASE_URL}/equity/history/orders?limit={min(limit, 50)}"

    while path and len(orders) < limit:
        r = requests.get(path, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        orders.extend(data.get("items", []))
        next_path = data.get("nextPagePath")
        if next_path:
            base_host = BASE_URL.rsplit("/api", 1)[0]
            path = f"{base_host}{next_path}"
        else:
            path = None

    return orders[:limit]


def get_dividends(limit: int = 20) -> list[dict]:
    """Fetch paid dividend history from Trading 212.

    Rate limit: 6 req / 1 min.
    """
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(
        f"{BASE_URL}/equity/history/dividends",
        params={"limit": min(limit, 50)},
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("items", [])


# Simple in-process cache for the instruments list (rate limit: 1 req / 50s)
_instruments_cache: list[dict] = []
_instruments_fetched_at: float = 0.0
_INSTRUMENTS_TTL = 600  # re-fetch at most every 10 minutes


def _get_instruments() -> list[dict]:
    """Fetch and cache all tradable instruments from Trading 212."""
    global _instruments_cache, _instruments_fetched_at
    if _instruments_cache and (time.time() - _instruments_fetched_at) < _INSTRUMENTS_TTL:
        return _instruments_cache
    headers = {"Authorization": _get_auth_header()}
    r = requests.get(f"{BASE_URL}/equity/metadata/instruments", headers=headers, timeout=15)
    r.raise_for_status()
    _instruments_cache = r.json()
    _instruments_fetched_at = time.time()
    return _instruments_cache


def lookup_ticker(query: str, max_results: int = 5) -> list[dict]:
    """Search instruments by company name or ticker symbol.

    Returns up to max_results matches, each with ticker, name, and exchange.
    Matches are ranked: exact ticker > ticker starts-with > name contains.
    Rate limit: shared cache, actual API call at most 1 req / 10 min.
    """
    q = query.strip().upper()
    instruments = _get_instruments()

    exact, starts, contains = [], [], []
    for inst in instruments:
        ticker: str = (inst.get("ticker") or "").upper()
        name: str = (inst.get("name") or "").upper()
        entry = {
            "ticker": inst.get("ticker", ""),
            "name": inst.get("name", ""),
            "exchange": inst.get("exchange", ""),
            "type": inst.get("type", ""),
        }
        if ticker == q or ticker == q + "_US_EQ" or ticker == q + "_EQ":
            exact.append(entry)
        elif ticker.startswith(q):
            starts.append(entry)
        elif q in ticker or q in name:
            contains.append(entry)

    results = (exact + starts + contains)[:max_results]
    return results


def create_pie(
    name: str,
    instrument_allocations: list[dict],
    reinvest_dividends: bool = False,
    end_of_day_dealing: bool = False,
) -> dict:
    """Create a new Trading 212 Pie.

    Args:
        name: Display name for the pie.
        instrument_allocations: List of {"ticker": str, "shares": float} where
            shares is the percentage allocation. Must sum to 100.
        reinvest_dividends: If True, dividends are reinvested into the pie.
        end_of_day_dealing: If True, orders execute at end of day.

    Returns the created pie object from the API.
    Rate limit: 1 req / 5s.
    """
    total = sum(item.get("shares", 0) for item in instrument_allocations)
    if round(total, 4) != 100.0:
        raise ValueError(
            f"Instrument allocations must sum to 100%, currently sum to {total:.2f}%"
        )

    headers = {
        "Authorization": _get_auth_header(),
        "Content-Type": "application/json",
    }
    payload = {
        "name": name,
        "dividendCashAction": "REINVEST" if reinvest_dividends else "TO_ACCOUNT_CASH",
        "endOfDayDealingEnabled": end_of_day_dealing,
        "instrumentShares": instrument_allocations,
    }
    r = requests.post(f"{BASE_URL}/equity/pies", json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()