import base64
import os
import time
import requests

# Demo paper-trading base URL. Switch to https://live.trading212.com/api/v0 for real money.
BASE_URL = os.getenv("TRADING212_BASE_URL", "https://live.trading212.com/api/v0")


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