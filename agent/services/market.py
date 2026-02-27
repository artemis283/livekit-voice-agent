import requests
import os
from collections import defaultdict
from datetime import datetime

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


def summarize_portfolio(portfolio: dict) -> list[str]:
    """Return a per-position summary with live prices, P&L %, best and worst performers."""
    summary = []
    total_pnl = 0.0
    winners, losers = [], []

    for symbol, info in portfolio.items():
        try:
            price = get_stock_price(symbol)
            live_pnl = (price["price"] - info["avg_price"]) * info["shares"]
            pnl_pct = ((price["price"] - info["avg_price"]) / max(info["avg_price"], 0.01)) * 100
            total_pnl += live_pnl
            summary.append(
                f"{symbol}: {info['shares']} shares @ avg ${info['avg_price']:.2f}, "
                f"now ${price['price']:.2f} ({price['change_pct']:+.2f}% today), "
                f"unrealised P&L ${live_pnl:+.2f} ({pnl_pct:+.2f}%)"
            )
            if live_pnl >= 0:
                winners.append((symbol, live_pnl))
            else:
                losers.append((symbol, live_pnl))
        except Exception:
            summary.append(f"{symbol}: price unavailable")

    if winners or losers:
        summary.append(f"\nTotal unrealised P&L: ${total_pnl:+.2f}")
        if winners:
            best = max(winners, key=lambda x: x[1])
            summary.append(f"Best performer: {best[0]} (${best[1]:+.2f})")
        if losers:
            worst = min(losers, key=lambda x: x[1])
            summary.append(f"Worst performer: {worst[0]} (${worst[1]:+.2f})")

    return summary


def analyse_trade_history(orders: list[dict]) -> dict:
    """Compute trade statistics from a list of historical orders.

    Returns win_rate, total_realised_pnl, avg_pnl_per_trade, best/worst trade,
    most_traded_tickers, and avg_hold_days.
    """
    if not orders:
        return {"error": "No trade history available."}

    filled = [o for o in orders if o.get("status") in ("FILLED", "PARTIALLY_FILLED")]
    if not filled:
        return {"error": "No filled orders found in history."}

    wins, losses = 0, 0
    total_pnl = 0.0
    best_trade = None
    worst_trade = None
    ticker_counts: dict[str, int] = defaultdict(int)
    hold_days_list: list[float] = []

    for o in filled:
        ticker = o.get("ticker", "Unknown")
        ticker_counts[ticker] += 1

        qty = float(o.get("filledQuantity", o.get("quantity", 0)) or 0)
        fill_price = float(o.get("fillPrice", o.get("executedPrice", 0)) or 0)
        avg_price = float(o.get("averagePrice", fill_price) or fill_price)

        # Only calculate P&L for SELL orders (negative quantity in T212)
        if qty < 0:
            pnl = (fill_price - avg_price) * abs(qty)
            total_pnl += pnl
            if pnl >= 0:
                wins += 1
            else:
                losses += 1
            if best_trade is None or pnl > best_trade["pnl"]:
                best_trade = {"ticker": ticker, "pnl": round(pnl, 2), "price": fill_price}
            if worst_trade is None or pnl < worst_trade["pnl"]:
                worst_trade = {"ticker": ticker, "pnl": round(pnl, 2), "price": fill_price}

        try:
            created = o.get("dateCreated") or o.get("creationTime")
            executed = o.get("dateExecuted") or o.get("fillTime")
            if created and executed:
                t1 = datetime.fromisoformat(created.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(executed.replace("Z", "+00:00"))
                hold_days_list.append((t2 - t1).total_seconds() / 86400)
        except Exception:
            pass

    sell_trades = wins + losses
    top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    result: dict = {
        "total_orders_analysed": len(filled),
        "sell_trades": sell_trades,
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate_pct": round((wins / sell_trades * 100) if sell_trades else 0, 1),
        "total_realised_pnl": round(total_pnl, 2),
        "avg_pnl_per_trade": round(total_pnl / sell_trades, 2) if sell_trades else 0,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "most_traded_tickers": [{"ticker": t, "orders": c} for t, c in top_tickers],
    }
    if hold_days_list:
        result["avg_hold_days"] = round(sum(hold_days_list) / len(hold_days_list), 2)
    return result


def summarise_dividends(dividends: list[dict]) -> dict:
    """Aggregate dividend income by ticker and in total."""
    if not dividends:
        return {"total_income": 0.0, "by_ticker": {}}

    total = 0.0
    by_ticker: dict[str, float] = defaultdict(float)
    for d in dividends:
        amount = float(d.get("amount", d.get("grossAmount", 0)) or 0)
        ticker = d.get("ticker", "Unknown")
        total += amount
        by_ticker[ticker] += amount

    sorted_tickers = sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_income": round(total, 2),
        "by_ticker": {t: round(v, 2) for t, v in sorted_tickers},
        "top_payer": sorted_tickers[0][0] if sorted_tickers else None,
    }