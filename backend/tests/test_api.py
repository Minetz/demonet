"""Tests for API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest

from app.models.opinion import Opinion, Question


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "name" in data


class TestGetCurrentQuestion:
    @pytest.mark.asyncio
    async def test_returns_active_question(self, client, seeded_db):
        response = await client.get("/api/question/current")
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "When is it okay to lie?"
        assert data["slug"] == "when-is-it-okay-to-lie"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_returns_404_when_no_question(self, client):
        response = await client.get("/api/question/current")
        assert response.status_code == 404


class TestPostOpinion:
    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_submit_opinion_success(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        response = await client.post(
            "/api/opinion",
            json={"text": "I think it's okay to lie to protect someone.", "region": "Japan"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hash" in data
        assert len(data["hash"]) == 16
        assert "anonymized_text" in data
        assert "language" in data
        assert isinstance(data["nearest"], list)

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_submit_without_region(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        response = await client.post(
            "/api/opinion",
            json={"text": "Honesty is always the best policy."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hash" in data

    @pytest.mark.asyncio
    async def test_submit_empty_text_rejected(self, client, seeded_db):
        response = await client.post(
            "/api/opinion",
            json={"text": ""},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_submit_too_long_text_rejected(self, client, seeded_db):
        response = await client.post(
            "/api/opinion",
            json={"text": "x" * 5001},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_returns_404_when_no_question(self, client, mock_gemini):
        response = await client.post(
            "/api/opinion",
            json={"text": "No question to answer."},
        )
        assert response.status_code == 404


class TestGetOpinion:
    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_get_existing_opinion(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        # First submit
        submit_response = await client.post(
            "/api/opinion",
            json={"text": "My take on lying.", "region": "Brazil"},
        )
        opinion_hash = submit_response.json()["hash"]

        # Then fetch
        response = await client.get(f"/api/opinion/{opinion_hash}")
        assert response.status_code == 200
        data = response.json()
        assert data["hash"] == opinion_hash
        assert data["region"] == "Brazil"
        assert "trust_score" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_opinion(self, client):
        response = await client.get("/api/opinion/doesnotexist123")
        assert response.status_code == 404


class TestGetCurrentOpinions:
    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_returns_visualization_data(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini
    ):
        # Submit a couple opinions
        await client.post("/api/opinion", json={"text": "Opinion A"})
        await client.post("/api/opinion", json={"text": "Opinion B"})

        response = await client.get("/api/opinions/current")
        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert "points" in data
        assert "total_opinions" in data
        assert data["total_opinions"] == 2

    @pytest.mark.asyncio
    async def test_returns_empty_points_when_no_opinions(self, client, seeded_db):
        response = await client.get("/api/opinions/current")
        assert response.status_code == 200
        data = response.json()
        assert data["points"] == []
        assert data["total_opinions"] == 0

    @pytest.mark.asyncio
    async def test_returns_404_when_no_question(self, client):
        response = await client.get("/api/opinions/current")
        assert response.status_code == 404


class TestGetSummary:
    @pytest.mark.asyncio
    async def test_returns_404_when_no_question(self, client):
        response = await client.get("/api/opinions/current/summary")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_no_opinions(self, client, seeded_db):
        response = await client.get("/api/opinions/current/summary")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.routes.summarize_opinions", new_callable=AsyncMock)
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_returns_summary(
        self, mock_nearest, mock_bridge, mock_summarize, client, seeded_db, mock_gemini
    ):
        mock_summarize.return_value = "Two main perspectives emerged."

        await client.post("/api/opinion", json={"text": "Opinion 1"})
        await client.post("/api/opinion", json={"text": "Opinion 2"})

        response = await client.get("/api/opinions/current/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Two main perspectives emerged."
        assert data["total_opinions"] == 2


class TestBridgeOpinion:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_opinion(self, client):
        response = await client.get("/api/opinion/nonexistent/bridge")
        assert response.status_code == 404
