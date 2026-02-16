from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opinion import Opinion, Question
from app.services.ai import (
    detect_language,
    get_embedding,
    strip_pii,
    translate_to_english,
)


async def get_current_question(db: AsyncSession) -> Question | None:
    result = await db.execute(select(Question).where(Question.active.is_(True)).limit(1))
    return result.scalar_one_or_none()


async def submit_opinion(
    db: AsyncSession,
    question_id: int,
    raw_text: str,
    region: str | None = None,
) -> Opinion:
    """Process and store an opinion: detect language, strip PII, embed, store."""
    language = await detect_language(raw_text)
    anonymized = await strip_pii(raw_text)
    english_text = await translate_to_english(anonymized, language)
    embedding = await get_embedding(english_text)
    opinion_hash = Opinion.generate_hash(raw_text)

    opinion = Opinion(
        hash=opinion_hash,
        question_id=question_id,
        original_text=anonymized,  # We store the anonymized version, never the raw PII
        anonymized_text=english_text,
        language=language,
        region=region,
        embedding=embedding,
    )
    db.add(opinion)
    await db.flush()
    return opinion


async def get_opinion_by_hash(db: AsyncSession, opinion_hash: str) -> Opinion | None:
    result = await db.execute(select(Opinion).where(Opinion.hash == opinion_hash))
    return result.scalar_one_or_none()


async def get_opinions_for_question(
    db: AsyncSession, question_id: int, limit: int = 200
) -> list[Opinion]:
    result = await db.execute(
        select(Opinion)
        .where(Opinion.question_id == question_id)
        .order_by(Opinion.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def find_nearest_opinions(
    db: AsyncSession,
    embedding: list[float],
    question_id: int,
    exclude_hash: str,
    limit: int = 5,
) -> list[Opinion]:
    """Find semantically nearest opinions using pgvector cosine distance."""
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    result = await db.execute(
        text(
            "SELECT *, embedding <=> :embedding::vector AS distance "
            "FROM opinions "
            "WHERE question_id = :qid AND hash != :exclude "
            "ORDER BY distance ASC "
            "LIMIT :lim"
        ),
        {"embedding": embedding_str, "qid": question_id, "exclude": exclude_hash, "lim": limit},
    )
    rows = result.fetchall()
    opinions = []
    for row in rows:
        opinion = await get_opinion_by_hash(db, row.hash)
        if opinion:
            opinions.append(opinion)
    return opinions


async def find_bridge_opinion(
    db: AsyncSession,
    embedding: list[float],
    question_id: int,
    exclude_hash: str,
    region: str | None = None,
) -> Opinion | None:
    """Find the closest mind in the furthest place — semantically similar but geographically distant."""
    # Get the nearest opinions semantically
    nearest = await find_nearest_opinions(db, embedding, question_id, exclude_hash, limit=50)
    if not nearest:
        return None

    if region:
        # Prefer opinions from different regions
        for opinion in nearest:
            if opinion.region and opinion.region != region:
                return opinion

    # Fallback: return the nearest opinion regardless of region
    return nearest[0] if nearest else None
