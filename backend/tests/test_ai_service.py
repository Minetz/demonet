"""Tests for AI service functions (Gemini REST API calls mocked)."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai import (
    detect_language,
    get_embedding,
    strip_pii,
    summarize_opinions,
    translate_to_english,
)


class TestGetEmbedding:
    @patch("app.services.ai.get_embedding", new_callable=AsyncMock)
    async def test_returns_embedding_list(self, mock_fn):
        mock_fn.return_value = [0.1] * 768
        result = await mock_fn("Hello world")
        assert isinstance(result, list)
        assert len(result) == 768

    @patch("app.services.ai.httpx.AsyncClient")
    async def test_calls_embed_endpoint(self, MockClient):
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": {"values": [0.1] * 768}}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await get_embedding("test text")
        assert len(result) == 768
        call_kwargs = mock_client.post.call_args
        assert "embedContent" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["taskType"] == "SEMANTIC_SIMILARITY"


class TestStripPii:
    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_returns_stripped_text(self, mock_generate):
        mock_generate.return_value = "  A person in a city thinks this is important.  "
        result = await strip_pii("John in Seattle thinks this is important.")
        assert result == "A person in a city thinks this is important."
        assert "John" not in result
        assert "Seattle" not in result

    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_prompt_includes_pii_instructions(self, mock_generate):
        mock_generate.return_value = "output"
        await strip_pii("test input")
        prompt = mock_generate.call_args[0][0]
        assert "PII" in prompt
        assert "anonymiz" in prompt.lower()


class TestDetectLanguage:
    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_returns_two_char_code(self, mock_generate):
        mock_generate.return_value = "  es  "
        result = await detect_language("Hola mundo")
        assert result == "es"
        assert len(result) == 2

    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_truncates_long_response(self, mock_generate):
        mock_generate.return_value = "english"
        result = await detect_language("Hello")
        assert len(result) == 2
        assert result == "en"


class TestTranslateToEnglish:
    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_skips_translation_for_english(self, mock_generate):
        result = await translate_to_english("Already English", "en")
        assert result == "Already English"
        mock_generate.assert_not_called()

    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_translates_non_english(self, mock_generate):
        mock_generate.return_value = "  Hello world  "
        result = await translate_to_english("Hola mundo", "es")
        assert result == "Hello world"


class TestSummarizeOpinions:
    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_returns_summary(self, mock_generate):
        mock_generate.return_value = "People are divided into two camps."
        result = await summarize_opinions(["Opinion A", "Opinion B"], "What matters?")
        assert result == "People are divided into two camps."

    @patch("app.services.ai._generate", new_callable=AsyncMock)
    async def test_prompt_includes_question(self, mock_generate):
        mock_generate.return_value = "summary"
        await summarize_opinions(["Op1"], "Is water wet?")
        prompt = mock_generate.call_args[0][0]
        assert "Is water wet?" in prompt
