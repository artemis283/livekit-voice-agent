from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool
from livekit.plugins import openai, noise_cancellation
import json
import sys
import os
from services.portfolio import get_portfolio, get_account_summary, get_trade_history, get_dividends
from services.market import get_stock_price, summarize_portfolio, analyse_trade_history, summarise_dividends
from services.news import get_macro_news, get_portfolio_news


load_dotenv(".env.local")

# Simple in-memory storage for notes
memory = {}


class VoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
                You are a read-only trading analysis assistant powered by the user's live Trading 212 data.
                You do not give financial advice and you do not predict prices.
                You provide data-driven analysis, historical context, and uncertainty-aware summaries.
                When information is incomplete, you explicitly say so.

                Your primary focus is helping the user deeply understand their trading performance:
                - Analyse open positions: P&L %, best and worst performers, concentration risk
                - Analyse trade history: win rate, average P&L per trade, best/worst closed trades, most traded tickers, average hold time
                - Summarise dividend income by ticker
                - Give live macro and stock-specific news context
                - Compare current positions against historical patterns

                When the user asks for analysis, always combine multiple data sources:
                use portfolio_overview AND analyse_trades together for a full picture.

                You have the ability to remember things for the user.
                When they ask you to remember something, use the save_note tool.
                When they ask what you've saved or to recall something, use the get_notes tool.
            """,
        )

    # ── Memory tools ──────────────────────────────────────────────────────────

    @function_tool
    async def save_note(self, note: str) -> str:
        """Save a note to memory. Use this when the user asks you to remember something."""
        note_id = len(memory) + 1
        memory[note_id] = note
        return f"Saved note #{note_id}: {note}"

    @function_tool
    async def get_notes(self) -> str:
        """Retrieve all saved notes. Use this when the user asks what you've remembered."""
        if not memory:
            return "No notes saved yet."
        return "\n".join([f"#{id}: {note}" for id, note in memory.items()])

    @function_tool
    async def delete_notes(self) -> str:
        """Delete all saved notes. Use this when the user asks you to delete their saved notes"""
        memory.clear()
        return "All saved notes have been deleted."

    # ── Portfolio & account tools ─────────────────────────────────────────────

    @function_tool
    async def read_portfolio(self) -> str:
        """Get the user's current open positions (raw data)."""
        return json.dumps(get_portfolio())

    @function_tool
    async def get_price(self, symbol: str) -> str:
        """Get the live price and today's change for a single ticker symbol."""
        data = get_stock_price(symbol)
        return f"{symbol} is trading at ${data['price']} ({data['change_pct']:+.2f}% today)."

    @function_tool
    async def portfolio_overview(self) -> str:
        """
        Get a rich overview of all open positions with live prices, 
        unrealised P&L %, best performer, and worst performer.
        """
        portfolio = get_portfolio()
        lines = summarize_portfolio(portfolio)

        # Concentration risk
        total_value = sum(
            info["shares"] * info["current_price"] for info in portfolio.values()
        )
        if total_value > 0:
            lines.append("\nConcentration (% of portfolio by current value):")
            sorted_pos = sorted(
                portfolio.items(),
                key=lambda x: x[1]["shares"] * x[1]["current_price"],
                reverse=True,
            )
            for ticker, info in sorted_pos[:5]:
                pos_value = info["shares"] * info["current_price"]
                lines.append(f"  {ticker}: {pos_value / total_value * 100:.1f}%")

        return "\n".join(lines)

    @function_tool
    async def get_account_summary(self) -> str:
        """Get the user's account cash balance, invested amount, and total portfolio value."""
        summary = get_account_summary()
        return json.dumps(summary)

    # ── Trade history & analysis tools ───────────────────────────────────────

    @function_tool
    async def analyse_trades(self) -> str:
        """
        Fetch the last 50 historical orders and analyse trading performance:
        win rate, total realised P&L, average P&L per trade, best/worst single trades,
        most traded tickers, and average hold time in days.
        """
        orders = get_trade_history(limit=50)
        stats = analyse_trade_history(orders)
        if "error" in stats:
            return stats["error"]
        lines = [
            f"Trade history analysis ({stats['total_orders_analysed']} orders):",
            f"  Sell trades: {stats['sell_trades']}",
            f"  Win rate: {stats['win_rate_pct']}% ({stats['winning_trades']} wins / {stats['losing_trades']} losses)",
            f"  Total realised P&L: ${stats['total_realised_pnl']:+,.2f}",
            f"  Avg P&L per trade: ${stats['avg_pnl_per_trade']:+,.2f}",
        ]
        if stats.get("best_trade"):
            b = stats["best_trade"]
            lines.append(f"  Best trade: {b['ticker']} +${b['pnl']:.2f}")
        if stats.get("worst_trade"):
            w = stats["worst_trade"]
            lines.append(f"  Worst trade: {w['ticker']} ${w['pnl']:.2f}")
        if stats.get("avg_hold_days") is not None:
            lines.append(f"  Avg hold time: {stats['avg_hold_days']} days")
        if stats.get("most_traded_tickers"):
            top = ", ".join(f"{t['ticker']} ({t['orders']})" for t in stats["most_traded_tickers"])
            lines.append(f"  Most traded: {top}")
        return "\n".join(lines)

    @function_tool
    async def get_dividend_summary(self) -> str:
        """
        Fetch dividend history and summarise total income received,
        broken down by ticker, with the highest-paying stock highlighted.
        """
        dividends = get_dividends(limit=50)
        summary = summarise_dividends(dividends)
        if summary["total_income"] == 0:
            return "No dividend income recorded yet."
        lines = [f"Dividend income summary:  Total received: ${summary['total_income']:.2f}"]
        if summary.get("top_payer"):
            lines.append(f"  Top payer: {summary['top_payer']}")
        lines.append("  By ticker:")
        for ticker, amount in summary["by_ticker"].items():
            lines.append(f"    {ticker}: ${amount:.2f}")
        return "\n".join(lines)

    # ── News tools ────────────────────────────────────────────────────────────

    @function_tool
    async def get_portfolio_news(self) -> str:
        """Get the latest news and sentiment for the user's current holdings."""
        portfolio = get_portfolio()
        tickers = list(portfolio.keys())
        articles = get_portfolio_news(tickers)
        if not articles:
            return "No recent news found for your holdings."
        return "\n\n".join(
            f"{a['headline']} [{a['source']}] – Sentiment: {a.get('sentiment', 'N/A')}\n{a.get('summary', '')}"
            for a in articles
        )

    @function_tool
    async def get_macro_context(self) -> str:
        """Get a live macro news feed from financial sources and Hacker News."""
        news = get_macro_news()
        if not news:
            return "No macro news available right now."
        return "\n\n".join(
            f"{n['headline']} [{n.get('source', 'Unknown')}]" +
            (f" – {n['sentiment']}" if 'sentiment' in n else "") +
            (f"\n{n['summary']}" if n.get('summary') else "")
            for n in news
        )


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="alloy",
            model="gpt-realtime-mini",
        )
    )

    await session.start(
        room=ctx.room,
        agent=VoiceAgent(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Hello there, I am here to assist you with your portfolio analysis. All decisions are your responsibility."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
