import requests
import os

API_KEY = os.getenv("ALPHA_VANTAGE_KEY")

def get_stock_price(symbol: str):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params).json()
    quote = r.get("Global Quote", {})

    return {
        "price": float(quote.get("05. price", 0)),
        "change_pct": float(quote.get("10. change percent", "0%").replace("%", ""))
    }

def summarize_portfolio(portfolio):
    summary = []
    for symbol, info in portfolio.items():
        price = get_stock_price(symbol)
        pnl = (price["price"] - info["avg_price"]) * info["shares"]
        summary.append(
            f"{symbol}: {info['shares']} shares, P/L approx ${round(pnl, 2)}"
        )
    return summary