"""Tests for rate limiting middleware."""
import pytest


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_health_endpoint_not_rate_limited(self, client):
        for _ in range(100):
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_requests_include_rate_limit_headers(self, client, seeded_db):
        response = await client.get("/api/question/current")
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers

    @pytest.mark.asyncio
    async def test_read_limit_returns_429(self, client, seeded_db):
        # Exhaust the read limit (60 requests)
        for i in range(60):
            resp = await client.get("/api/question/current")
            assert resp.status_code == 200, f"Request {i + 1} failed unexpectedly"

        # Next request should be rate limited
        resp = await client.get("/api/question/current")
        assert resp.status_code == 429
        data = resp.json()
        assert "Too many requests" in data["detail"]
        assert "retry-after" in resp.headers

    @pytest.mark.asyncio
    async def test_write_limit_is_stricter(self, client, seeded_db, mock_gemini):
        from unittest.mock import AsyncMock, patch

        with patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None), \
             patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[]):
            # Exhaust the write limit (10 requests)
            for i in range(10):
                resp = await client.post(
                    "/api/opinion",
                    json={"text": f"Opinion number {i}", "region": "Test"},
                )
                assert resp.status_code == 200, f"Write {i + 1} failed: {resp.text}"

            # Next write should be rate limited
            resp = await client.post(
                "/api/opinion",
                json={"text": "One too many", "region": "Test"},
            )
            assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_read_and_write_are_separate_buckets(self, client, seeded_db, mock_gemini):
        from unittest.mock import AsyncMock, patch

        with patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None), \
             patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[]):
            # Use up 5 writes
            for i in range(5):
                resp = await client.post(
                    "/api/opinion",
                    json={"text": f"Write {i}", "region": "Test"},
                )
                assert resp.status_code == 200

            # Reads should still work
            resp = await client.get("/api/question/current")
            assert resp.status_code == 200
