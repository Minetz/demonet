"""AI service using Gemini REST API directly via httpx (no SDK dependency)."""
import httpx

from app.core.config import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


async def _generate(prompt: str) -> str:
    """Call Gemini generateContent REST endpoint."""
    url = f"{GEMINI_BASE}/{settings.gemini_model}:generateContent"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector for text using Gemini REST API."""
    url = f"{GEMINI_BASE}/{settings.gemini_embedding_model}:embedContent"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json={
                "model": settings.gemini_embedding_model,
                "content": {"parts": [{"text": text}]},
                "taskType": "SEMANTIC_SIMILARITY",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


async def strip_pii(text: str) -> str:
    """Remove personally identifiable information while preserving opinion substance."""
    result = await _generate(
        "You are a PII anonymization engine. Remove all personally identifiable "
        "information from the following text (names, locations, emails, phone numbers, "
        "addresses, specific organizations, dates of birth, any identifying details) "
        "while preserving the FULL substance and nuance of the opinion expressed. "
        "Replace specific identifiers with generic terms (e.g., 'my city' instead of "
        "'Seattle', 'a person' instead of 'John'). Return ONLY the anonymized text, "
        "nothing else.\n\n"
        f"Text: {text}"
    )
    return result.strip()


async def detect_language(text: str) -> str:
    """Detect the language of text. Returns ISO 639-1 code."""
    result = await _generate(
        "Detect the language of the following text. Return ONLY the ISO 639-1 "
        f"language code (e.g., 'en', 'es', 'ja', 'ar'). Nothing else.\n\n{text}"
    )
    return result.strip().lower()[:2]


async def translate_to_english(text: str, source_lang: str) -> str:
    """Translate text to English for embedding. Returns original if already English."""
    if source_lang == "en":
        return text
    result = await _generate(
        "Translate the following text to English. Preserve the tone, nuance, and "
        f"meaning as faithfully as possible. Return ONLY the translation.\n\n{text}"
    )
    return result.strip()


async def summarize_opinions(opinions: list[str], question: str) -> str:
    """Synthesize a summary of multiple opinions on a question."""
    opinions_text = "\n---\n".join(opinions)
    result = await _generate(
        f"You are summarizing global opinions on the question: '{question}'\n\n"
        f"Here are anonymized opinions from people around the world:\n{opinions_text}\n\n"
        "Provide a concise synthesis that:\n"
        "1. Identifies the main clusters of thought (2-5 perspectives)\n"
        "2. Notes surprising areas of agreement\n"
        "3. Highlights the most unique or unexpected viewpoints\n"
        "4. Does NOT take sides or express a preference\n"
        "Keep it under 200 words."
    )
    return result.strip()
