"""Tests for the shareable opinion card endpoint."""
from unittest.mock import AsyncMock, patch

import pytest


class TestSharePage:
    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_share_page_renders_html(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        resp = await client.post(
            "/api/opinion",
            json={"text": "Honesty matters.", "region": "Brazil"},
        )
        opinion_hash = resp.json()["hash"]

        response = await client.get(f"/s/{opinion_hash}")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        html = response.text
        assert opinion_hash in html
        assert "og:title" in html
        assert "og:description" in html
        assert "twitter:card" in html
        assert "The World's Take" in html
        assert "Brazil" in html
        assert "<svg" in html

    @pytest.mark.asyncio
    async def test_share_page_404_for_missing_hash(self, client):
        response = await client.get("/s/nonexistenthash1")
        assert response.status_code == 404
        assert "not found" in response.text.lower()

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_share_page_shows_language_badge(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        mock_gemini["detect_language"].return_value = "ja"

        resp = await client.post(
            "/api/opinion",
            json={"text": "真実は大切です。"},
        )
        opinion_hash = resp.json()["hash"]

        response = await client.get(f"/s/{opinion_hash}")
        html = response.text
        assert "translated from ja" in html
