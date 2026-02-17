"""Tests for the MCP server tools.

Uses httpx mock transport to simulate the REST API responses,
so we can test MCP tool logic without a running backend.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp_server import (
    get_bridge,
    get_current_question,
    get_opinion,
    get_opinions,
    get_summary,
    set_api_base,
    submit_opinion,
)


# ── Fixtures ───────────────────────────────────────────────────────────


MOCK_QUESTION = {
    "id": 1,
    "text": "When is it okay to lie?",
    "slug": "when-is-it-okay-to-lie",
    "created_at": "2026-02-17T00:00:00+00:00",
}

MOCK_OPINION = {
    "hash": "a7f3c9e2b1d04f8a",
    "anonymized_text": "Sometimes honesty causes more harm than a small lie.",
    "language": "en",
    "region": "Germany",
    "trust_score": 0.5,
    "created_at": "2026-02-17T12:00:00+00:00",
}

MOCK_SUBMIT = {
    "hash": "a7f3c9e2b1d04f8a",
    "anonymized_text": "Sometimes honesty causes more harm than a small lie.",
    "language": "en",
    "nearest": [
        {
            "hash": "b8e4d0f3c2a15e9b",
            "anonymized_text": "White lies protect feelings.",
            "region": "Japan",
            "trust_score": 0.5,
        }
    ],
    "bridge": {
        "hash": "c9f5e1a4d3b26f0c",
        "anonymized_text": "Lying is sometimes compassionate.",
        "region": "Brazil",
        "trust_score": 0.5,
    },
}

MOCK_VISUALIZATION = {
    "question": MOCK_QUESTION,
    "points": [
        {
            "hash": "a7f3c9e2b1d04f8a",
            "x": 0.5,
            "y": -0.3,
            "region": "Germany",
            "text_preview": "Sometimes honesty causes more harm...",
        }
    ],
    "total_opinions": 1,
}

MOCK_SUMMARY = {
    "question": MOCK_QUESTION,
    "summary": "The global perspective reveals three main clusters of thought...",
    "total_opinions": 42,
}

MOCK_BRIDGE = {
    "hash": "c9f5e1a4d3b26f0c",
    "anonymized_text": "Lying is sometimes compassionate.",
    "region": "Brazil",
    "trust_score": 0.5,
}


@pytest.fixture(autouse=True)
def _set_test_api_base():
    set_api_base("http://testserver/api")
    yield
    set_api_base("http://localhost:8000/api")


def _make_ctx(mock_response_data, status_code=200):
    """Build a mock Context whose HTTP client returns a canned response.

    Note: httpx.Response.json() is synchronous, so we use MagicMock for the
    response object (not AsyncMock which would make .json() a coroutine).
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_lifespan = MagicMock()
    mock_lifespan.http_client = mock_client

    mock_request_context = MagicMock()
    mock_request_context.lifespan_context = mock_lifespan

    ctx = MagicMock()
    ctx.request_context = mock_request_context

    return ctx, mock_client


def _make_404_ctx():
    """Build a mock Context whose HTTP client returns 404."""
    return _make_ctx({"detail": "Not found"}, status_code=404)


# ── Tests ──────────────────────────────────────────────────────────────


class TestGetCurrentQuestion:
    async def test_returns_question(self):
        ctx, client = _make_ctx(MOCK_QUESTION)
        result = await get_current_question(ctx)
        data = json.loads(result)
        assert data["text"] == "When is it okay to lie?"
        assert data["slug"] == "when-is-it-okay-to-lie"
        client.get.assert_called_once_with("http://testserver/api/question/current")

    async def test_no_active_question(self):
        ctx, client = _make_ctx(None, status_code=404)
        result = await get_current_question(ctx)
        data = json.loads(result)
        assert "error" in data


class TestSubmitOpinion:
    async def test_submit_with_region(self):
        ctx, client = _make_ctx(MOCK_SUBMIT)
        result = await submit_opinion(ctx, "Honesty is overrated sometimes.", "Germany")
        data = json.loads(result)
        assert data["hash"] == "a7f3c9e2b1d04f8a"
        assert len(data["nearest"]) == 1
        assert data["bridge"]["region"] == "Brazil"
        client.post.assert_called_once_with(
            "http://testserver/api/opinion",
            json={"text": "Honesty is overrated sometimes.", "region": "Germany"},
        )

    async def test_submit_without_region(self):
        ctx, client = _make_ctx(MOCK_SUBMIT)
        result = await submit_opinion(ctx, "Lying is always wrong.")
        data = json.loads(result)
        assert data["hash"] == "a7f3c9e2b1d04f8a"
        client.post.assert_called_once_with(
            "http://testserver/api/opinion",
            json={"text": "Lying is always wrong."},
        )

    async def test_submit_no_question(self):
        ctx, _ = _make_404_ctx()
        result = await submit_opinion(ctx, "Test opinion")
        data = json.loads(result)
        assert "error" in data


class TestGetOpinion:
    async def test_found(self):
        ctx, client = _make_ctx(MOCK_OPINION)
        result = await get_opinion(ctx, "a7f3c9e2b1d04f8a")
        data = json.loads(result)
        assert data["hash"] == "a7f3c9e2b1d04f8a"
        assert data["region"] == "Germany"
        client.get.assert_called_once_with("http://testserver/api/opinion/a7f3c9e2b1d04f8a")

    async def test_not_found(self):
        ctx, _ = _make_404_ctx()
        result = await get_opinion(ctx, "nonexistent")
        data = json.loads(result)
        assert "error" in data


class TestGetOpinions:
    async def test_returns_visualization(self):
        ctx, client = _make_ctx(MOCK_VISUALIZATION)
        result = await get_opinions(ctx)
        data = json.loads(result)
        assert data["total_opinions"] == 1
        assert len(data["points"]) == 1
        assert data["question"]["text"] == "When is it okay to lie?"
        client.get.assert_called_once_with("http://testserver/api/opinions/current")


class TestGetSummary:
    async def test_returns_summary(self):
        ctx, client = _make_ctx(MOCK_SUMMARY)
        result = await get_summary(ctx)
        data = json.loads(result)
        assert data["total_opinions"] == 42
        assert "three main clusters" in data["summary"]
        client.get.assert_called_once_with("http://testserver/api/opinions/current/summary")

    async def test_no_opinions(self):
        ctx, _ = _make_404_ctx()
        result = await get_summary(ctx)
        data = json.loads(result)
        assert "error" in data


class TestGetBridge:
    async def test_found(self):
        ctx, client = _make_ctx(MOCK_BRIDGE)
        result = await get_bridge(ctx, "a7f3c9e2b1d04f8a")
        data = json.loads(result)
        assert data["region"] == "Brazil"
        client.get.assert_called_once_with(
            "http://testserver/api/opinion/a7f3c9e2b1d04f8a/bridge"
        )

    async def test_no_bridge(self):
        ctx, _ = _make_ctx(None, status_code=200)
        result = await get_bridge(ctx, "a7f3c9e2b1d04f8a")
        data = json.loads(result)
        assert "message" in data

    async def test_opinion_not_found(self):
        ctx, _ = _make_404_ctx()
        result = await get_bridge(ctx, "nonexistent")
        data = json.loads(result)
        assert "error" in data
