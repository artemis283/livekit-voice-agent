import os
import requests

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

# Keywords used to filter Hacker News stories for financial/market relevance
_FINANCE_KEYWORDS = {
    "stock", "market", "invest", "trade", "fund", "bank", "economy",
    "gdp", "inflation", "startup", "vc", "ipo", "crypto", "ai", "tech",
    "fed", "rate", "recession", "earnings", "revenue", "profit",
}


def get_portfolio_news(tickers: list[str]) -> list[dict]:
    """Get news sentiment for specific tickers using Alpha Vantage NEWS_SENTIMENT."""
    if not ALPHA_VANTAGE_KEY or not tickers:
        return []
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "NEWS_SENTIMENT",
                "tickers": ",".join(tickers),
                "limit": 5,
                "apikey": ALPHA_VANTAGE_KEY,
            },
            timeout=10,
        )
        r.raise_for_status()
        return [
            {
                "headline": a.get("title", ""),
                "source": a.get("source", ""),
                "sentiment": a.get("overall_sentiment_label", "Neutral"),
                "summary": a.get("summary", "")[:250],
                "url": a.get("url", ""),
            }
            for a in r.json().get("feed", [])[:5]
        ]
    except Exception:
        return []


def _get_hacker_news(limit: int = 4) -> list[dict]:
    """Fetch top finance/tech stories from Hacker News (free, no key required)."""
    HN = "https://hacker-news.firebaseio.com/v0"
    try:
        top_ids = requests.get(f"{HN}/topstories.json", timeout=10).json()
    except Exception:
        return []

    stories = []
    for story_id in top_ids[:40]:
        try:
            item = requests.get(f"{HN}/item/{story_id}.json", timeout=5).json()
            if not item or item.get("type") != "story":
                continue
            title = item.get("title", "").lower()
            if any(kw in title for kw in _FINANCE_KEYWORDS):
                stories.append({
                    "headline": item.get("title", ""),
                    "source": "Hacker News",
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "score": item.get("score", 0),
                })
            if len(stories) >= limit:
                break
        except Exception:
            continue
    return stories


def get_macro_news() -> list[dict]:
    """Combine Alpha Vantage macro news + Hacker News for a live market feed."""
    news = []

    # Alpha Vantage general financial market news
    if ALPHA_VANTAGE_KEY:
        try:
            r = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "NEWS_SENTIMENT",
                    "topics": "financial_markets,economy_macro",
                    "limit": 5,
                    "apikey": ALPHA_VANTAGE_KEY,
                },
                timeout=10,
            )
            r.raise_for_status()
            for a in r.json().get("feed", [])[:5]:
                news.append({
                    "headline": a.get("title", ""),
                    "source": a.get("source", ""),
                    "sentiment": a.get("overall_sentiment_label", "Neutral"),
                    "summary": a.get("summary", "")[:250],
                })
        except Exception:
            pass

    # Supplement with Hacker News
    news += _get_hacker_news(limit=3)
    return news