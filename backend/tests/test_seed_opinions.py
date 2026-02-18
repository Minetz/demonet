"""Tests for the Big Five personality opinion seeder."""

from unittest.mock import AsyncMock, patch

import pytest

from seed_opinions import PROFILES, generate_opinion, seed_opinions


class TestProfiles:
    def test_profiles_have_required_fields(self):
        for label, personality, region in PROFILES:
            assert label, "Each profile needs a label"
            assert len(personality) > 20, f"Profile '{label}' personality too short"
            assert region, f"Profile '{label}' needs a region"

    def test_all_regions_unique(self):
        regions = [r for _, _, r in PROFILES]
        assert len(regions) == len(set(regions)), "Duplicate regions found"

    def test_enough_profiles_for_interesting_constellation(self):
        assert len(PROFILES) >= 10, "Need at least 10 profiles for a meaningful constellation"


class TestGenerateOpinion:
    @patch("seed_opinions._generate", new_callable=AsyncMock)
    async def test_generates_opinion_text(self, mock_generate):
        mock_generate.return_value = "  I think honesty matters most.  "
        result = await generate_opinion("You are introverted.", "When is it okay to lie?")
        assert result == "I think honesty matters most."
        mock_generate.assert_called_once()

    @patch("seed_opinions._generate", new_callable=AsyncMock)
    async def test_prompt_includes_question(self, mock_generate):
        mock_generate.return_value = "Some opinion."
        await generate_opinion("You are extraverted.", "What makes a good leader?")
        prompt = mock_generate.call_args[0][0]
        assert "What makes a good leader?" in prompt

    @patch("seed_opinions._generate", new_callable=AsyncMock)
    async def test_prompt_includes_personality(self, mock_generate):
        mock_generate.return_value = "Some opinion."
        await generate_opinion("You are deeply skeptical.", "When is it okay to lie?")
        prompt = mock_generate.call_args[0][0]
        assert "deeply skeptical" in prompt


class TestSeedOpinions:
    @patch("seed_opinions.submit_opinion", new_callable=AsyncMock)
    @patch("seed_opinions.generate_opinion", new_callable=AsyncMock)
    async def test_dry_run_does_not_store(self, mock_gen, mock_submit, seeded_db):
        mock_gen.return_value = "A generated opinion."
        # Patch async_session to return our test session
        db, question = seeded_db
        with patch("seed_opinions.async_session") as mock_session_maker:
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)
            await seed_opinions(dry_run=True)

        mock_gen.assert_called()
        mock_submit.assert_not_called()

    @patch("seed_opinions._init_db", new_callable=AsyncMock)
    @patch("seed_opinions.submit_opinion", new_callable=AsyncMock)
    @patch("seed_opinions.generate_opinion", new_callable=AsyncMock)
    async def test_stores_all_profiles(self, mock_gen, mock_submit, mock_init, seeded_db):
        mock_gen.return_value = "A generated opinion."
        mock_opinion = AsyncMock()
        mock_opinion.hash = "abc123"
        mock_submit.return_value = mock_opinion

        db, question = seeded_db
        with patch("seed_opinions.async_session") as mock_session_maker:
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)
            await seed_opinions(dry_run=False)

        assert mock_submit.call_count == len(PROFILES)

    @patch("seed_opinions._init_db", new_callable=AsyncMock)
    @patch("seed_opinions.submit_opinion", new_callable=AsyncMock)
    @patch("seed_opinions.generate_opinion", new_callable=AsyncMock)
    async def test_passes_region_to_submit(self, mock_gen, mock_submit, mock_init, seeded_db):
        mock_gen.return_value = "A generated opinion."
        mock_opinion = AsyncMock()
        mock_opinion.hash = "abc123"
        mock_submit.return_value = mock_opinion

        db, question = seeded_db
        with patch("seed_opinions.async_session") as mock_session_maker:
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)
            await seed_opinions(dry_run=False)

        regions_submitted = [call.kwargs.get("region") or call.args[3] for call in mock_submit.call_args_list]
        expected_regions = [r for _, _, r in PROFILES]
        assert regions_submitted == expected_regions
