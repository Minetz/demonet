"""Seed the database with the first question."""
import asyncio

from sqlalchemy import select

from app.core.database import async_session, engine, Base
from app.models.opinion import Question


async def seed():
    from sqlalchemy import text as sql_text

    async with engine.begin() as conn:
        await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        existing = await session.execute(select(Question).where(Question.active.is_(True)))
        if existing.scalar_one_or_none():
            print("Active question already exists, skipping seed.")
            return

        question = Question(
            text="When is it okay to lie?",
            slug="when-is-it-okay-to-lie",
            active=True,
        )
        session.add(question)
        await session.commit()
        print(f"Seeded question: '{question.text}' (slug: {question.slug})")


if __name__ == "__main__":
    asyncio.run(seed())
