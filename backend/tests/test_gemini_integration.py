"""Integration tests that hit the real Gemini API.

These tests require a valid GEMINI_API_KEY in .env and are skipped if unavailable.
They verify the full AI pipeline produces real, meaningful results.
"""
import pytest

from app.core.config import settings
from app.services.ai import (
    detect_language,
    get_embedding,
    strip_pii,
    summarize_opinions,
    translate_to_english,
)

pytestmark = pytest.mark.skipif(
    not settings.gemini_api_key,
    reason="GEMINI_API_KEY not set",
)


class TestGeminiEmbedding:
    @pytest.mark.asyncio
    async def test_returns_768_dim_vector(self):
        result = await get_embedding("I believe honesty is always the best policy.")
        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_similar_texts_have_similar_embeddings(self):
        e1 = await get_embedding("Lying is wrong and damages trust.")
        e2 = await get_embedding("Dishonesty is harmful and erodes trust.")
        e3 = await get_embedding("I love cooking pasta with fresh tomatoes.")

        # Cosine similarity helper
        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x**2 for x in a) ** 0.5
            norm_b = sum(x**2 for x in b) ** 0.5
            return dot / (norm_a * norm_b)

        sim_related = cosine_sim(e1, e2)
        sim_unrelated = cosine_sim(e1, e3)
        assert sim_related > sim_unrelated, (
            f"Related texts should be more similar ({sim_related:.3f}) "
            f"than unrelated ({sim_unrelated:.3f})"
        )


class TestGeminiPiiStripping:
    @pytest.mark.asyncio
    async def test_removes_names_and_locations(self):
        text = (
            "My name is Sarah Johnson and I live in Portland, Oregon. "
            "I think lying to protect someone's feelings is acceptable."
        )
        result = await strip_pii(text)
        assert "Sarah" not in result
        assert "Johnson" not in result
        assert "Portland" not in result
        assert "Oregon" not in result
        # The opinion substance should survive
        assert "lying" in result.lower() or "lie" in result.lower() or "protect" in result.lower()

    @pytest.mark.asyncio
    async def test_preserves_opinion_substance(self):
        text = (
            "I'm John from Seattle and I believe context matters — "
            "a doctor softening bad news is completely different from "
            "a politician covering up corruption."
        )
        result = await strip_pii(text)
        assert "John" not in result
        assert "Seattle" not in result
        # Core opinion concepts should remain
        assert "context" in result.lower() or "doctor" in result.lower() or "politician" in result.lower()


class TestGeminiLanguageDetection:
    @pytest.mark.asyncio
    async def test_detects_english(self):
        result = await detect_language("Honesty is the best policy in all situations.")
        assert result == "en"

    @pytest.mark.asyncio
    async def test_detects_spanish(self):
        result = await detect_language("La verdad siempre, incluso cuando duele.")
        assert result == "es"

    @pytest.mark.asyncio
    async def test_detects_japanese(self):
        result = await detect_language("嘘も方便という言葉があるように、時と場合による。")
        assert result == "ja"

    @pytest.mark.asyncio
    async def test_detects_german(self):
        result = await detect_language("Es gibt Situationen wo eine Notlüge das Richtige ist.")
        assert result == "de"


class TestGeminiTranslation:
    @pytest.mark.asyncio
    async def test_translates_spanish_to_english(self):
        result = await translate_to_english(
            "La verdad siempre, incluso cuando duele.", "es"
        )
        # Should contain English words about truth/hurting
        assert any(word in result.lower() for word in ["truth", "hurts", "always", "painful"])

    @pytest.mark.asyncio
    async def test_skips_english(self):
        original = "This is already in English."
        result = await translate_to_english(original, "en")
        assert result == original

    @pytest.mark.asyncio
    async def test_translates_japanese_to_english(self):
        result = await translate_to_english(
            "嘘も方便という言葉があるように、時と場合による。", "ja"
        )
        # Should be English text
        assert any(c.isascii() for c in result)
        assert len(result) > 10


class TestGeminiSummarization:
    @pytest.mark.asyncio
    async def test_summarizes_diverse_opinions(self):
        opinions = [
            "Lying is never acceptable. Truth is the foundation of trust.",
            "White lies that spare feelings are fine. Deception for gain is not.",
            "Context matters. A doctor softening news differs from a politician lying.",
            "Radical honesty is the only way to live authentically.",
            "Lying to children about cultural traditions is beautiful, not a moral failing.",
        ]
        result = await summarize_opinions(opinions, "When is it okay to lie?")
        assert len(result) > 50  # Should be a substantive summary
        assert len(result) < 2000  # Should be concise
        # Should identify multiple perspectives
        assert any(word in result.lower() for word in ["perspective", "group", "view", "some", "others", "while"])
