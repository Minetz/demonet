"""
MCP (Model Context Protocol) server for The World's Take.

Wraps the REST API so AI agents can interact with the opinion network
as first-class citizens. Supports both stdio and streamable-http transports.

Usage:
    # stdio (for Claude Desktop, local tools)
    python -m app.mcp_server

    # streamable-http (for remote agents)
    python -m app.mcp_server --transport streamable-http --port 8001
"""

import argparse
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from mcp.server.fastmcp import Context, FastMCP

DEFAULT_API_BASE = "http://localhost:8000/api"


@dataclass
class AppContext:
    http_client: httpx.AsyncClient


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield AppContext(http_client=client)


mcp = FastMCP(
    "The World's Take",
    instructions=(
        "A global opinion network. Use these tools to read the current question, "
        "submit opinions, explore how the world thinks, and discover unexpected "
        "connections between minds across the planet."
    ),
    lifespan=app_lifespan,
)

# The API base URL — configurable at startup
_api_base = DEFAULT_API_BASE


def set_api_base(url: str):
    global _api_base
    _api_base = url.rstrip("/")


def _get_client(ctx: Context) -> httpx.AsyncClient:
    return ctx.request_context.lifespan_context.http_client


# ── Tools ──────────────────────────────────────────────────────────────


@mcp.tool()
async def get_current_question(ctx: Context) -> str:
    """Get the current weekly question that the whole world is answering.

    Returns the question text, slug, and metadata. Use this to know what
    topic is being discussed before submitting or browsing opinions.
    """
    client = _get_client(ctx)
    resp = await client.get(f"{_api_base}/question/current")
    if resp.status_code == 404:
        return json.dumps({"error": "No active question right now."})
    resp.raise_for_status()
    return json.dumps(resp.json())


@mcp.tool()
async def submit_opinion(ctx: Context, text: str, region: str | None = None) -> str:
    """Submit an opinion on the current question.

    The opinion is anonymized (PII stripped), translated, and embedded for
    semantic clustering. You receive back a unique hash (your opinion signature),
    the nearest similar opinions, and a "bridge" — the closest mind in the
    furthest place.

    Args:
        text: Your opinion (1-5000 characters). Free-form text in any language.
        region: Optional region/country you're from (e.g. "Japan", "Brazil").
    """
    client = _get_client(ctx)
    body = {"text": text}
    if region:
        body["region"] = region
    resp = await client.post(f"{_api_base}/opinion", json=body)
    if resp.status_code == 404:
        return json.dumps({"error": "No active question to submit an opinion for."})
    resp.raise_for_status()
    return json.dumps(resp.json())


@mcp.tool()
async def get_opinion(ctx: Context, opinion_hash: str) -> str:
    """Look up an opinion by its hash signature.

    Every opinion gets a unique hash like 'a7f3c9e2b1d04f8a'. Use this to
    retrieve the anonymized text, trust score, language, and region.

    Args:
        opinion_hash: The 16-character hex hash of the opinion.
    """
    client = _get_client(ctx)
    resp = await client.get(f"{_api_base}/opinion/{opinion_hash}")
    if resp.status_code == 404:
        return json.dumps({"error": f"No opinion found with hash '{opinion_hash}'."})
    resp.raise_for_status()
    return json.dumps(resp.json(), default=str)


@mcp.tool()
async def get_opinions(ctx: Context) -> str:
    """Get all opinions for the current question, clustered for visualization.

    Returns 2D-projected opinion points (via PCA on embeddings) along with
    the question metadata and total count. Each point includes a text preview,
    hash, and region.
    """
    client = _get_client(ctx)
    resp = await client.get(f"{_api_base}/opinions/current")
    if resp.status_code == 404:
        return json.dumps({"error": "No active question."})
    resp.raise_for_status()
    return json.dumps(resp.json(), default=str)


@mcp.tool()
async def get_summary(ctx: Context) -> str:
    """Get an AI-synthesized summary of what the world thinks about the current question.

    Synthesizes all submitted opinions into a structured overview of the major
    perspectives, areas of agreement, and points of tension. Useful for quickly
    understanding the global conversation.
    """
    client = _get_client(ctx)
    resp = await client.get(f"{_api_base}/opinions/current/summary")
    if resp.status_code == 404:
        return json.dumps({"error": "No active question or no opinions yet."})
    resp.raise_for_status()
    return json.dumps(resp.json(), default=str)


@mcp.tool()
async def get_bridge(ctx: Context, opinion_hash: str) -> str:
    """Find the "closest mind, furthest away" for a given opinion.

    Discovers the most semantically similar opinion from the most geographically
    distant contributor. This is the core insight of the network — unexpected
    agreement across boundaries.

    Args:
        opinion_hash: The 16-character hex hash of the opinion to bridge from.
    """
    client = _get_client(ctx)
    resp = await client.get(f"{_api_base}/opinion/{opinion_hash}/bridge")
    if resp.status_code == 404:
        return json.dumps({"error": f"No opinion found with hash '{opinion_hash}'."})
    resp.raise_for_status()
    data = resp.json()
    if data is None:
        return json.dumps({"message": "No bridge found — not enough opinions from different regions yet."})
    return json.dumps(data)


# ── Resources ──────────────────────────────────────────────────────────


@mcp.resource("worldstake://question/current")
async def question_resource() -> str:
    """The current weekly question being asked to the world."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{_api_base}/question/current")
        if resp.status_code == 404:
            return "No active question right now."
        resp.raise_for_status()
        data = resp.json()
        return f"Current question: {data['text']}\nSlug: {data['slug']}"


# ── Entry point ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="The World's Take MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP transport")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport")
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=f"Base URL of the REST API (default: {DEFAULT_API_BASE})",
    )
    args = parser.parse_args()

    set_api_base(args.api_base)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
