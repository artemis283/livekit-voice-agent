# Voice Agent for Portfolio Analysis

A real-time voice assistant built on **LiveKit Agents** and the **OpenAI Realtime API**. You talk to it, and it calls tools to fetch your live Trading 212 portfolio, analyse your trading history, pull market news and answer out loud.

It's deliberately **read-only and guardrailed**: it doesn't give financial advice or predict prices, and it says when data is incomplete. Its one write action, creating a portfolio "Pie", needs explicit confirmation first.

The whole system is containerised and **deployed to Kubernetes through a GitHub Actions CI/CD pipeline**.

## What it can do

| Area | Tools the agent can call |
|---|---|
| **Portfolio** | Open positions, account summary, live prices, unrealised P&L %, best and worst performers, concentration risk |
| **Trade history** | Win rate, realised P&L, average P&L per trade, best and worst trades, most-traded tickers, average hold time |
| **Income** | Dividend income by ticker, top payer |
| **News** | Sentiment-tagged news for your holdings (Alpha Vantage) and a macro feed |
| **Actions** | Ticker lookup, then Pie creation, with validation (allocations must sum to 100%) and user confirmation |
| **Memory** | Save, recall and delete notes during a session |

## Design choices

- **Speech-to-speech with tool calling**: uses `gpt-realtime-mini` through LiveKit, so the agent can call Python functions mid-conversation and answer by voice without a separate speech-to-text → LLM → text-to-speech chain.
- **Guardrails in the system prompt and the tools**: the agent is told what it must not do (no advice, no predictions), to state uncertainty, and to confirm with the user before taking any action. Tool inputs are validated in code, not just in the prompt.
- **Noise cancellation** on the audio input (LiveKit BVC).
- **Secrets via environment variables** only (see `.env.example`).

## Architecture

```
Browser (Next.js frontend) ◄──WebRTC──► LiveKit server ◄──► Python agent (agent/agent.py)
                                                                  │
                                                     OpenAI Realtime (speech ↔ speech)
                                                                  │
                                       ┌─────────────┬────────────┴────────────┐
                                  Trading 212 API  Alpha Vantage        Hacker News
                                  (portfolio,      (prices, news         (macro feed)
                                   orders, pies)    sentiment)
```

## Repository layout

```
agent/      Python LiveKit agent + services (portfolio, market data, news)
frontend/   Next.js web client (based on LiveKit's agent starter template)
k8s/        Kubernetes manifests: agent, frontend, Postgres, ingress
.github/    CI/CD: build Docker images → push to Docker Hub → roll out to the cluster
```

## Deployment

Every push to `main`:
1. Builds Docker images for the agent and the frontend, tagged with the commit SHA
2. Pushes them to Docker Hub
3. Updates the Kubernetes deployments with `kubectl set image` and waits for the rollout to finish

## Running locally

```bash
cp .env.example agent/.env.local   # add LiveKit, OpenAI, Trading 212 and Alpha Vantage keys
cd agent && uv sync && uv run agent.py dev

cd ../frontend && pnpm install && pnpm dev
```

> Tip: set `TRADING212_BASE_URL` to the **demo** endpoint to use a paper-trading account.

## Tech stack

Python · LiveKit Agents · OpenAI Realtime API · Next.js / TypeScript · Docker · Kubernetes · GitHub Actions
