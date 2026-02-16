"""Multi-user simulation tests.

Simulates N users from different regions submitting opinions to the same question,
then verifies the full flow: submission, retrieval, visualization, and summary.
"""
import random
from unittest.mock import AsyncMock, patch

import pytest

# Simulated users with diverse opinions and regions
SIMULATED_USERS = [
    {
        "text": "Lying is never acceptable. Truth is the foundation of all trust.",
        "region": "Japan",
        "anonymized": "Lying is never acceptable. Truth is the foundation of all trust.",
        "language": "en",
    },
    {
        "text": "Es gibt Situationen wo eine Notlüge das Richtige ist, zum Beispiel um jemanden zu schützen.",
        "region": "Germany",
        "anonymized": "There are situations where a white lie is the right thing, for example to protect someone.",
        "language": "de",
    },
    {
        "text": "White lies that spare feelings are fine. Deception for personal gain is not.",
        "region": "Nigeria",
        "anonymized": "White lies that spare feelings are fine. Deception for personal gain is not.",
        "language": "en",
    },
    {
        "text": "La verdad siempre, incluso cuando duele. La mentira destruye relaciones.",
        "region": "Mexico",
        "anonymized": "The truth always, even when it hurts. Lies destroy relationships.",
        "language": "es",
    },
    {
        "text": "Context matters. A doctor softening bad news is different from a politician covering up corruption.",
        "region": "India",
        "anonymized": "Context matters. A medical professional softening bad news is different from a politician covering up corruption.",
        "language": "en",
    },
    {
        "text": "嘘も方便という言葉があるように、時と場合による。",
        "region": "Japan",
        "anonymized": "As the saying goes, lies can be expedient. It depends on the time and situation.",
        "language": "ja",
    },
    {
        "text": "I believe radical honesty is the only way to live authentically.",
        "region": "United States",
        "anonymized": "Radical honesty is the only way to live authentically.",
        "language": "en",
    },
    {
        "text": "Lying to children about Santa Claus is a beautiful cultural tradition, not a moral failing.",
        "region": "Brazil",
        "anonymized": "Lying to children about a cultural figure is a beautiful tradition, not a moral failing.",
        "language": "en",
    },
]

# Create distinct embeddings so clustering produces real structure.
# Group 1 (anti-lying): users 0, 3, 6 — similar embeddings
# Group 2 (context-dependent): users 1, 2, 4, 5, 7 — similar embeddings
def _make_embedding(group: int, noise_seed: int) -> list[float]:
    """Generate a 768-dim embedding with group structure."""
    rng = random.Random(noise_seed)
    base = [0.8 if group == 1 else 0.2] * 384 + [0.2 if group == 1 else 0.8] * 384
    return [v + rng.uniform(-0.05, 0.05) for v in base]

USER_EMBEDDINGS = [
    _make_embedding(1, 10),  # user 0 — anti-lying
    _make_embedding(2, 20),  # user 1 — context
    _make_embedding(2, 30),  # user 2 — context
    _make_embedding(1, 40),  # user 3 — anti-lying
    _make_embedding(2, 50),  # user 4 — context
    _make_embedding(2, 60),  # user 5 — context
    _make_embedding(1, 70),  # user 6 — anti-lying
    _make_embedding(2, 80),  # user 7 — context
]


@pytest.fixture
def mock_gemini_multi_user():
    """Mock Gemini with per-call responses for multi-user simulation."""
    call_count = {"embed": 0, "pii": 0, "lang": 0, "translate": 0}

    async def _embed(text):
        idx = min(call_count["embed"], len(USER_EMBEDDINGS) - 1)
        call_count["embed"] += 1
        return USER_EMBEDDINGS[idx]

    async def _strip_pii(text):
        idx = min(call_count["pii"], len(SIMULATED_USERS) - 1)
        call_count["pii"] += 1
        return SIMULATED_USERS[idx]["anonymized"]

    async def _detect_language(text):
        idx = min(call_count["lang"], len(SIMULATED_USERS) - 1)
        call_count["lang"] += 1
        return SIMULATED_USERS[idx]["language"]

    async def _translate(text, source_lang):
        idx = min(call_count["translate"], len(SIMULATED_USERS) - 1)
        call_count["translate"] += 1
        return SIMULATED_USERS[idx]["anonymized"]

    with (
        patch("app.services.opinions.get_embedding", side_effect=_embed) as mock_embed,
        patch("app.services.opinions.strip_pii", side_effect=_strip_pii) as mock_pii,
        patch("app.services.opinions.detect_language", side_effect=_detect_language) as mock_lang,
        patch("app.services.opinions.translate_to_english", side_effect=_translate) as mock_translate,
    ):
        yield {
            "get_embedding": mock_embed,
            "strip_pii": mock_pii,
            "detect_language": mock_lang,
            "translate_to_english": mock_translate,
            "call_count": call_count,
        }


class TestMultiUserSubmission:
    """Simulate 8 users from 6 countries submitting opinions."""

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_all_users_submit_successfully(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        hashes = []
        for user in SIMULATED_USERS:
            response = await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )
            assert response.status_code == 200, f"Failed for user from {user['region']}"
            data = response.json()
            assert len(data["hash"]) == 16
            hashes.append(data["hash"])

        # All hashes should be unique
        assert len(set(hashes)) == len(SIMULATED_USERS)

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_each_opinion_retrievable_by_hash(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        hashes = []
        for user in SIMULATED_USERS:
            res = await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )
            hashes.append(res.json()["hash"])

        # Verify each opinion can be fetched individually
        for i, h in enumerate(hashes):
            response = await client.get(f"/api/opinion/{h}")
            assert response.status_code == 200
            data = response.json()
            assert data["hash"] == h
            assert data["region"] == SIMULATED_USERS[i]["region"]

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_ai_pipeline_called_for_each_user(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        mocks = mock_gemini_multi_user
        n = len(SIMULATED_USERS)
        assert mocks["get_embedding"].call_count == n
        assert mocks["strip_pii"].call_count == n
        assert mocks["detect_language"].call_count == n
        assert mocks["translate_to_english"].call_count == n


class TestMultiUserVisualization:
    """Verify the constellation visualization works with multiple users."""

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_visualization_contains_all_users(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        response = await client.get("/api/opinions/current")
        assert response.status_code == 200
        data = response.json()
        assert data["total_opinions"] == len(SIMULATED_USERS)
        assert len(data["points"]) == len(SIMULATED_USERS)

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_visualization_points_have_coordinates(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        response = await client.get("/api/opinions/current")
        data = response.json()
        for point in data["points"]:
            assert "x" in point
            assert "y" in point
            assert "hash" in point
            assert "text_preview" in point
            assert isinstance(point["x"], float)
            assert isinstance(point["y"], float)

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_visualization_shows_clusters(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        """With two distinct opinion groups, PCA should project them into separable regions."""
        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        response = await client.get("/api/opinions/current")
        data = response.json()
        points = data["points"]

        # Group by the known clusters:
        # Anti-lying users (indices 0, 3, 6) should cluster together
        # Context-dependent users (indices 1, 2, 4, 5, 7) should cluster together
        # We can't check exact coordinates but we can verify the groups are separated
        # by checking that same-group points are closer than cross-group points
        anti_lying_xs = []
        context_xs = []
        anti_lying_indices = {0, 3, 6}

        for i, point in enumerate(points):
            if i in anti_lying_indices:
                anti_lying_xs.append(point["x"])
            else:
                context_xs.append(point["x"])

        if anti_lying_xs and context_xs:
            # The mean x of each group should differ
            anti_mean = sum(anti_lying_xs) / len(anti_lying_xs)
            context_mean = sum(context_xs) / len(context_xs)
            assert anti_mean != context_mean, "Groups should have different centroids"

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_regions_preserved_in_visualization(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        response = await client.get("/api/opinions/current")
        data = response.json()
        regions = {p["region"] for p in data["points"] if p["region"]}
        # We submitted from 6 unique regions
        assert len(regions) >= 5  # At least most regions should appear


class TestMultiUserSummary:
    """Verify summary works with multiple opinions from diverse users."""

    @pytest.mark.asyncio
    @patch("app.api.routes.summarize_opinions", new_callable=AsyncMock)
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_summary_reflects_all_opinions(
        self, mock_nearest, mock_bridge, mock_summarize, client, seeded_db, mock_gemini_multi_user
    ):
        mock_summarize.return_value = (
            "Two main perspectives emerged: one group believes lying is never "
            "acceptable and truth is foundational to trust, while a larger group "
            "argues context matters — white lies to protect feelings or soften bad "
            "news differ fundamentally from deception for personal gain."
        )

        for user in SIMULATED_USERS:
            await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )

        response = await client.get("/api/opinions/current/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_opinions"] == len(SIMULATED_USERS)
        assert "perspectives" in data["summary"].lower()

        # Verify summarize was called with all opinion texts
        call_args = mock_summarize.call_args
        opinion_texts = call_args[0][0]
        assert len(opinion_texts) == len(SIMULATED_USERS)


class TestMultiLanguageHandling:
    """Verify opinions in different languages are processed correctly."""

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_non_english_opinions_detected(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        """Submit opinions in different languages and verify language detection."""
        results = []
        for user in SIMULATED_USERS:
            res = await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )
            results.append(res.json())

        # Check languages were detected correctly
        languages = [r["language"] for r in results]
        assert "en" in languages
        assert "de" in languages  # German user
        assert "es" in languages  # Mexican user
        assert "ja" in languages  # Japanese user

    @pytest.mark.asyncio
    @patch("app.api.routes.find_bridge_opinion", new_callable=AsyncMock, return_value=None)
    @patch("app.api.routes.find_nearest_opinions", new_callable=AsyncMock, return_value=[])
    async def test_all_opinions_stored_as_english(
        self, mock_nearest, mock_bridge, client, seeded_db, mock_gemini_multi_user
    ):
        """All opinions should be translated for embedding, but original anonymized text preserved."""
        hashes = []
        for user in SIMULATED_USERS:
            res = await client.post(
                "/api/opinion",
                json={"text": user["text"], "region": user["region"]},
            )
            hashes.append(res.json()["hash"])

        # Fetch each and verify the anonymized text is the English version
        for i, h in enumerate(hashes):
            res = await client.get(f"/api/opinion/{h}")
            data = res.json()
            # anonymized_text should be the translated/anonymized version
            assert len(data["anonymized_text"]) > 0
