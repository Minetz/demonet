"""Tests for opinion service functions."""
import pytest
from sqlalchemy import select

from app.models.opinion import Opinion, Question
from app.services.opinions import (
    get_current_question,
    get_opinion_by_hash,
    get_opinions_for_question,
    submit_opinion,
)


class TestGetCurrentQuestion:
    @pytest.mark.asyncio
    async def test_returns_active_question(self, seeded_db):
        db, question = seeded_db
        result = await get_current_question(db)
        assert result is not None
        assert result.id == question.id
        assert result.active is True

    @pytest.mark.asyncio
    async def test_returns_none_when_no_active(self, db_session):
        result = await get_current_question(db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_only_inactive(self, db_session):
        q = Question(text="Inactive?", slug="inactive", active=False)
        db_session.add(q)
        await db_session.flush()
        result = await get_current_question(db_session)
        assert result is None


class TestSubmitOpinion:
    @pytest.mark.asyncio
    async def test_creates_opinion_with_ai_processing(self, seeded_db, mock_gemini):
        db, question = seeded_db
        opinion = await submit_opinion(db, question.id, "I think lying is okay to protect someone.")
        assert opinion.hash is not None
        assert len(opinion.hash) == 16
        assert opinion.question_id == question.id
        assert opinion.language == "en"
        assert opinion.anonymized_text == "An anonymized opinion about the topic."
        # Verify AI pipeline was called
        mock_gemini["detect_language"].assert_called_once()
        mock_gemini["strip_pii"].assert_called_once()
        mock_gemini["translate_to_english"].assert_called_once()
        mock_gemini["get_embedding"].assert_called_once()

    @pytest.mark.asyncio
    async def test_stores_anonymized_not_raw(self, seeded_db, mock_gemini):
        db, question = seeded_db
        raw_text = "My name is John from Seattle and I believe lying is fine."
        opinion = await submit_opinion(db, question.id, raw_text)
        # original_text should be the PII-stripped version, NOT the raw input
        assert opinion.original_text != raw_text
        assert opinion.original_text == "An anonymized opinion about the topic."

    @pytest.mark.asyncio
    async def test_stores_region(self, seeded_db, mock_gemini):
        db, question = seeded_db
        opinion = await submit_opinion(db, question.id, "My take", region="Brazil")
        assert opinion.region == "Brazil"

    @pytest.mark.asyncio
    async def test_stores_embedding(self, seeded_db, mock_gemini):
        db, question = seeded_db
        opinion = await submit_opinion(db, question.id, "Test opinion")
        assert opinion.embedding is not None
        assert len(list(opinion.embedding)) == 768


class TestGetOpinionByHash:
    @pytest.mark.asyncio
    async def test_returns_opinion(self, seeded_db, mock_gemini):
        db, question = seeded_db
        opinion = await submit_opinion(db, question.id, "Find me!")
        await db.flush()

        found = await get_opinion_by_hash(db, opinion.hash)
        assert found is not None
        assert found.hash == opinion.hash

    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self, db_session):
        found = await get_opinion_by_hash(db_session, "nonexistent12345")
        assert found is None


class TestGetOpinionsForQuestion:
    @pytest.mark.asyncio
    async def test_returns_opinions(self, seeded_db, mock_gemini):
        db, question = seeded_db
        await submit_opinion(db, question.id, "Opinion 1")
        await submit_opinion(db, question.id, "Opinion 2")
        await submit_opinion(db, question.id, "Opinion 3")
        await db.flush()

        opinions = await get_opinions_for_question(db, question.id)
        assert len(opinions) == 3

    @pytest.mark.asyncio
    async def test_respects_limit(self, seeded_db, mock_gemini):
        db, question = seeded_db
        for i in range(5):
            await submit_opinion(db, question.id, f"Opinion {i}")
        await db.flush()

        opinions = await get_opinions_for_question(db, question.id, limit=2)
        assert len(opinions) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_opinions(self, seeded_db):
        db, question = seeded_db
        opinions = await get_opinions_for_question(db, question.id)
        assert opinions == []

    @pytest.mark.asyncio
    async def test_filters_by_question_id(self, db_session, mock_gemini):
        q1 = Question(text="Q1?", slug="q1", active=True)
        q2 = Question(text="Q2?", slug="q2", active=False)
        db_session.add_all([q1, q2])
        await db_session.flush()

        await submit_opinion(db_session, q1.id, "Opinion for Q1")
        await submit_opinion(db_session, q2.id, "Opinion for Q2")
        await db_session.flush()

        q1_opinions = await get_opinions_for_question(db_session, q1.id)
        q2_opinions = await get_opinions_for_question(db_session, q2.id)
        assert len(q1_opinions) == 1
        assert len(q2_opinions) == 1
