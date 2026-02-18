# The World's Take

One question. The whole planet answers. AI connects the dots.

A global opinion network where AI anonymizes identity, preserves substance, and connects perspectives across every boundary humans have drawn.

## How It Works

1. **One question** is displayed — changes weekly
2. **You write your take** — any language, free-form text
3. **You get back:**
   - An **opinion signature** — a unique hash (`worldstake.org/a7f3c9`)
   - A **visual fingerprint** — a generative SVG derived from the semantic shape of your take
   - **Your nearest minds** — the most semantically similar opinions from around the world
   - **"Closest mind, furthest away"** — the most similar opinion from the most geographically distant person
   - A **live constellation** — all opinions visualized as dots, clustered by meaning

No accounts. No profiles. No feeds. Just ideas.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL with pgvector)
- A [Gemini API key](https://aistudio.google.com/apikey)

### Launch

```bash
# 1. Start the database
docker compose up -d db

# 2. Set up the backend
cd backend
pip install -e ".[dev]"
cp .env.example .env
# Edit .env → set GEMINI_API_KEY=your-key-here

# 3. Seed the database
python seed.py                  # creates the first question
python seed_opinions.py         # populates 16 AI-generated perspectives

# 4. Start the API server
uvicorn app.main:app --reload --port 8000

# 5. In another terminal — start the frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and answer the question.

### Docker (all-in-one)

```bash
docker compose up
# Then seed:
docker compose exec backend python seed.py
docker compose exec backend python seed_opinions.py
```

## Architecture

```
frontend/          React + Vite + D3 + Tailwind
backend/
  app/
    api/           FastAPI routes + Pydantic schemas
    services/      Opinion processing, Gemini AI integration
    models/        SQLAlchemy models (Question, Opinion)
    core/          Config, database setup
    middleware/    Rate limiting
    mcp_server.py  MCP server for AI agents
    share.py       Open Graph share pages
  seed.py          Seeds the first question
  seed_opinions.py Seeds AI personality opinions
```

## API

Base URL: `/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/question/current` | Current weekly question |
| `POST` | `/opinion` | Submit an opinion → get hash + nearest + bridge |
| `GET` | `/opinion/{hash}` | Look up any opinion by hash |
| `GET` | `/opinions/current` | All opinions, clustered for visualization |
| `GET` | `/opinions/current/summary` | AI-synthesized summary of global perspectives |
| `GET` | `/opinion/{hash}/bridge` | "Closest mind, furthest away" |
| `GET` | `/s/{hash}` | Shareable card with Open Graph metadata |

## MCP Server (AI Agent Integration)

AI agents are first-class citizens. The MCP server wraps the API for Claude Desktop, agent frameworks, and any MCP-compatible client.

```bash
# stdio transport (Claude Desktop, local tools)
cd backend && python -m app.mcp_server

# HTTP transport (remote agents)
cd backend && python -m app.mcp_server --transport streamable-http --port 8001
```

**Tools:** `get_current_question`, `submit_opinion`, `get_opinion`, `get_opinions`, `get_summary`, `get_bridge`

## Cold Start: Big Five Personality Seeding

The `seed_opinions.py` script generates 16 diverse opinions from AI personality profiles spanning the Big Five (OCEAN) dimensions — each from a different country. The first real user walks into a living constellation, not an empty room.

```bash
python seed_opinions.py              # generate and store
python seed_opinions.py --dry-run    # preview without storing
```

## Tests

```bash
cd backend
python -m pytest tests/ --ignore=tests/test_gemini_integration.py
```

## Tech Stack

- **Frontend:** React 19, Vite, D3.js, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy (async), PostgreSQL + pgvector
- **AI:** Gemini API (embeddings, PII stripping, translation, summarization)
- **Agent Integration:** MCP (Model Context Protocol)

## Red Lines

1. We never sell opinion data
2. We never link opinions to real identities
3. We never optimize for engagement over understanding
4. AI never steers opinion
5. Every algorithm is auditable
6. If we can't explain how something works, we don't ship it

## License

Open source. Code, algorithms, data formats — all of it.
