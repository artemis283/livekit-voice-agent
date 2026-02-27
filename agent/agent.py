from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool
from livekit.plugins import openai, noise_cancellation
import json
import sys
import os
from services.portfolio import get_portfolio, get_account_summary
from services.market import get_stock_price, summarize_portfolio
from services.news import get_macro_news, get_portfolio_news


load_dotenv(".env.local")

# Simple in-memory storage for notes
memory = {}


class VoiceAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
                You are a read-only trading assistant.
                You do not give financial advice.
                You do not predict prices.
                You provide historical context, current data, and uncertainty-aware summaries.
                When information is incomplete, you explicitly say so.

                Your primary focus is helping the user manage their trading portfolio.
                You provide insights, answer questions, and assist with trade execution.
                You also give the user news updates relevant to their portfolio.
                
                You have the ability to remember things for the user.
                When they ask you to remember something, use the save_note tool.
                When they ask what you've saved or to recall something, use the get_notes tool.
            """,
        )

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
    
    @function_tool
    async def read_portfolio(self) -> str:
        """Get the user's current portfolio (read-only)."""
        return json.dumps(get_portfolio())
    
    @function_tool
    async def get_price(self, symbol: str) -> str:
        data = get_stock_price(symbol)
        return f"{symbol} is trading at ${data['price']} ({data['change_pct']}%)."
    
    @function_tool
    async def portfolio_overview(self) -> str:
        portfolio = get_portfolio()
        overview = summarize_portfolio(portfolio)
        return "\n".join(overview)
    
    @function_tool
    async def get_account_summary(self) -> str:
        """Get the user's account cash balance and total portfolio value."""
        summary = get_account_summary()
        return json.dumps(summary)

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
        instructions="Greet the user by saying hello there,  welcome to Founders and Coders."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
