"""Tests for database models."""
import pytest
from datetime import datetime, timezone

from app.models.opinion import Opinion, Question


class TestQuestion:
    def test_create_question(self):
        q = Question(text="What matters most?", slug="what-matters-most", active=True)
        assert q.text == "What matters most?"
        assert q.slug == "what-matters-most"
        assert q.active is True

    @pytest.mark.asyncio
    async def test_persist_question(self, db_session):
        q = Question(text="Test question?", slug="test-question", active=True)
        db_session.add(q)
        await db_session.flush()
        assert q.id is not None
        assert q.created_at is not None

    @pytest.mark.asyncio
    async def test_slug_uniqueness(self, db_session):
        from sqlalchemy.exc import IntegrityError

        q1 = Question(text="Q1", slug="same-slug", active=True)
        q2 = Question(text="Q2", slug="same-slug", active=False)
        db_session.add(q1)
        await db_session.flush()
        db_session.add(q2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestOpinion:
    def test_generate_hash_returns_16_chars(self):
        h = Opinion.generate_hash("Some opinion text")
        assert len(h) == 16
        assert isinstance(h, str)

    def test_generate_hash_is_unique_per_call(self):
        """Each call uses a random salt, so hashes differ even for same text."""
        h1 = Opinion.generate_hash("Same text")
        h2 = Opinion.generate_hash("Same text")
        assert h1 != h2

    def test_generate_hash_is_hex(self):
        h = Opinion.generate_hash("test")
        int(h, 16)  # Raises ValueError if not valid hex

    @pytest.mark.asyncio
    async def test_persist_opinion(self, db_session):
        q = Question(text="Q?", slug="q", active=True)
        db_session.add(q)
        await db_session.flush()

        o = Opinion(
            hash=Opinion.generate_hash("test"),
            question_id=q.id,
            original_text="My original take",
            anonymized_text="My anonymized take",
            language="en",
            region="Germany",
            trust_score=0.5,
        )
        db_session.add(o)
        await db_session.flush()
        assert o.id is not None
        assert o.created_at is not None
        assert o.trust_score == 0.5

    @pytest.mark.asyncio
    async def test_hash_uniqueness(self, db_session):
        from sqlalchemy.exc import IntegrityError

        q = Question(text="Q?", slug="q-unique", active=True)
        db_session.add(q)
        await db_session.flush()

        fixed_hash = "abcdef1234567890"
        o1 = Opinion(
            hash=fixed_hash,
            question_id=q.id,
            original_text="Take 1",
            anonymized_text="Take 1",
        )
        o2 = Opinion(
            hash=fixed_hash,
            question_id=q.id,
            original_text="Take 2",
            anonymized_text="Take 2",
        )
        db_session.add(o1)
        await db_session.flush()
        db_session.add(o2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_default_trust_score(self, db_session):
        q = Question(text="Q?", slug="q-trust", active=True)
        db_session.add(q)
        await db_session.flush()

        o = Opinion(
            hash=Opinion.generate_hash("trust-test"),
            question_id=q.id,
            original_text="test",
            anonymized_text="test",
        )
        db_session.add(o)
        await db_session.flush()
        await db_session.refresh(o)
        assert o.trust_score == 0.5
