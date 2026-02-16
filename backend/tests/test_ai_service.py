"""Tests for AI service functions (Gemini calls mocked)."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai import (
    detect_language,
    get_embedding,
    strip_pii,
    summarize_opinions,
    translate_to_english,
)


def _make_mock_genai(**kwargs):
    """Create a mock genai module returned by _get_genai()."""
    mock_genai = MagicMock()
    if "embed_return" in kwargs:
        mock_genai.embed_content.return_value = kwargs["embed_return"]
    if "generate_text" in kwargs:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = kwargs["generate_text"]
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
    return mock_genai


class TestGetEmbedding:
    @patch("app.services.ai._get_genai")
    async def test_returns_embedding_list(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(embed_return={"embedding": [0.1] * 768})
        result = await get_embedding("Hello world")
        assert isinstance(result, list)
        assert len(result) == 768

    @patch("app.services.ai._get_genai")
    async def test_passes_semantic_similarity_task(self, mock_get_genai):
        mock_genai = _make_mock_genai(embed_return={"embedding": [0.0]})
        mock_get_genai.return_value = mock_genai
        await get_embedding("test text")
        call_kwargs = mock_genai.embed_content.call_args
        assert call_kwargs[1]["task_type"] == "SEMANTIC_SIMILARITY"


class TestStripPii:
    @patch("app.services.ai._get_genai")
    async def test_returns_stripped_text(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(
            generate_text="  A person in a city thinks this is important.  "
        )
        result = await strip_pii("John in Seattle thinks this is important.")
        assert result == "A person in a city thinks this is important."
        assert "John" not in result
        assert "Seattle" not in result

    @patch("app.services.ai._get_genai")
    async def test_prompt_includes_instructions(self, mock_get_genai):
        mock_genai = _make_mock_genai(generate_text="output")
        mock_get_genai.return_value = mock_genai
        await strip_pii("test input")
        prompt = mock_genai.GenerativeModel().generate_content.call_args[0][0]
        assert "PII" in prompt
        assert "anonymiz" in prompt.lower()


class TestDetectLanguage:
    @patch("app.services.ai._get_genai")
    async def test_returns_two_char_code(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(generate_text="  es  ")
        result = await detect_language("Hola mundo")
        assert result == "es"
        assert len(result) == 2

    @patch("app.services.ai._get_genai")
    async def test_truncates_long_response(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(generate_text="english")
        result = await detect_language("Hello")
        assert len(result) == 2
        assert result == "en"


class TestTranslateToEnglish:
    @patch("app.services.ai._get_genai")
    async def test_skips_translation_for_english(self, mock_get_genai):
        result = await translate_to_english("Already English", "en")
        assert result == "Already English"
        mock_get_genai.assert_not_called()

    @patch("app.services.ai._get_genai")
    async def test_translates_non_english(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(generate_text="  Hello world  ")
        result = await translate_to_english("Hola mundo", "es")
        assert result == "Hello world"


class TestSummarizeOpinions:
    @patch("app.services.ai._get_genai")
    async def test_returns_summary(self, mock_get_genai):
        mock_get_genai.return_value = _make_mock_genai(
            generate_text="People are divided into two camps."
        )
        result = await summarize_opinions(["Opinion A", "Opinion B"], "What matters?")
        assert result == "People are divided into two camps."

    @patch("app.services.ai._get_genai")
    async def test_prompt_includes_question(self, mock_get_genai):
        mock_genai = _make_mock_genai(generate_text="summary")
        mock_get_genai.return_value = mock_genai
        await summarize_opinions(["Op1"], "Is water wet?")
        prompt = mock_genai.GenerativeModel().generate_content.call_args[0][0]
        assert "Is water wet?" in prompt
