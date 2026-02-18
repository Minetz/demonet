"""
Seed the opinion constellation with AI-generated perspectives.

Uses Big Five personality profiles to generate diverse, genuine-sounding opinions
so the first real user walks into a living constellation — not an empty room.

Each profile varies across the OCEAN dimensions:
  O - Openness (creative/curious vs practical/conventional)
  C - Conscientiousness (disciplined vs spontaneous)
  E - Extraversion (outgoing vs introspective)
  A - Agreeableness (cooperative/trusting vs competitive/skeptical)
  N - Neuroticism (anxious/emotional vs calm/resilient)

Usage:
    python seed_opinions.py              # seed current active question
    python seed_opinions.py --dry-run    # print opinions without storing
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import Base, async_session, engine
from app.models.opinion import Question
from app.services.ai import _generate
from app.services.opinions import submit_opinion


# Each profile: (label, Big Five description for the prompt, region)
PROFILES = [
    (
        "High-O, Low-A",
        "You are highly open to experience — philosophical, abstract, unconventional. "
        "You are low in agreeableness — blunt, skeptical of social niceties, more interested "
        "in truth than comfort.",
        "Germany",
    ),
    (
        "Low-O, High-C",
        "You are low in openness — practical, concrete, traditional. You are highly "
        "conscientious — rule-following, disciplined, believe in doing what's right.",
        "Japan",
    ),
    (
        "High-E, High-A",
        "You are highly extraverted — warm, expressive, people-oriented. You are highly "
        "agreeable — empathetic, conflict-averse, prioritize harmony.",
        "Brazil",
    ),
    (
        "Low-E, High-N",
        "You are introverted — reflective, inner-world focused. You are high in "
        "neuroticism — anxious, overthinking, acutely aware of how things can go wrong.",
        "South Korea",
    ),
    (
        "High-O, High-A",
        "You are highly open — imaginative, sees many perspectives. You are highly "
        "agreeable — compassionate, believes in the good in people.",
        "Nigeria",
    ),
    (
        "Low-A, Low-C",
        "You are low in agreeableness — competitive, direct, doesn't sugarcoat. "
        "You are low in conscientiousness — spontaneous, flexible with rules, pragmatic.",
        "Russia",
    ),
    (
        "High-C, High-N",
        "You are highly conscientious — duty-bound, meticulous. You are high in "
        "neuroticism — worries about moral consequences, feels guilt intensely.",
        "India",
    ),
    (
        "High-E, Low-N",
        "You are highly extraverted — confident, assertive, comfortable in social settings. "
        "You are low in neuroticism — emotionally stable, relaxed, hard to rattle.",
        "Australia",
    ),
    (
        "Low-O, High-A",
        "You are low in openness — down-to-earth, values tradition and clarity. "
        "You are highly agreeable — kind, considerate, believes lying hurts relationships.",
        "Mexico",
    ),
    (
        "High-O, Low-C",
        "You are highly open — creative, unconventional thinker, loves paradoxes. "
        "You are low in conscientiousness — goes with the flow, resists rigid moral rules.",
        "France",
    ),
    (
        "Low-E, Low-N, High-C",
        "You are introverted and calm — thoughtful, measured, prefers careful analysis. "
        "You are highly conscientious — values consistency and integrity above all.",
        "Finland",
    ),
    (
        "High-A, High-N",
        "You are highly agreeable — deeply caring, wants everyone to be okay. "
        "You are high in neuroticism — anxious about hurting people, torn by moral dilemmas.",
        "Philippines",
    ),
    (
        "Low-A, High-O, Low-N",
        "You are low in agreeableness — independent, iconoclastic. You are highly open "
        "and emotionally stable — calm provocateur who questions assumptions for fun.",
        "United Kingdom",
    ),
    (
        "High-C, Low-O, Low-A",
        "You are highly conscientious and practical — black-and-white moral clarity. "
        "Low in agreeableness — doesn't care if the truth is uncomfortable.",
        "United States",
    ),
    (
        "High-E, High-O, High-A",
        "You are the storyteller — extraverted, imaginative, and warm. Sees lying as "
        "a deeply human act that can't be reduced to rules.",
        "Colombia",
    ),
    (
        "Low everything",
        "You are quiet, practical, emotionally flat, independent, and flexible. "
        "You see this question as simpler than people make it.",
        "Egypt",
    ),
]


async def generate_opinion(personality: str, question_text: str) -> str:
    """Use Gemini to generate an opinion from a personality profile."""
    prompt = (
        f"{personality}\n\n"
        f"You are answering the question: \"{question_text}\"\n\n"
        "Write a short, genuine opinion (2-4 sentences) in first person. "
        "Sound like a real person — not an essay, not a lecture. "
        "Your personality should shape WHAT you think and HOW you express it, "
        "but never mention psychology terms or the Big Five. "
        "Just be that person answering honestly. Return ONLY the opinion text."
    )
    result = await _generate(prompt)
    return result.strip()


async def _init_db():
    """Ensure pgvector extension and tables exist."""
    from sqlalchemy import text as sql_text

    async with engine.begin() as conn:
        await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def seed_opinions(dry_run: bool = False):
    """Generate and submit opinions from each personality profile."""
    if not dry_run:
        await _init_db()

    async with async_session() as session:
        result = await session.execute(
            select(Question).where(Question.active.is_(True)).limit(1)
        )
        question = result.scalar_one_or_none()
        if not question:
            print("No active question found. Run seed.py first.")
            return

        print(f"Question: \"{question.text}\"\n")
        print(f"Generating {len(PROFILES)} personality-driven opinions...\n")

        for i, (label, personality, region) in enumerate(PROFILES, 1):
            print(f"[{i}/{len(PROFILES)}] {label} ({region})")

            opinion_text = await generate_opinion(personality, question.text)
            print(f"  → {opinion_text[:100]}...")

            if not dry_run:
                opinion = await submit_opinion(
                    session, question.id, opinion_text, region
                )
                await session.commit()
                print(f"  ✓ Hash: {opinion.hash}")
            else:
                print("  (dry run — not stored)")

            print()

        print(f"Done. {'Would seed' if dry_run else 'Seeded'} {len(PROFILES)} opinions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed opinions with Big Five personalities")
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't store")
    args = parser.parse_args()
    asyncio.run(seed_opinions(dry_run=args.dry_run))
