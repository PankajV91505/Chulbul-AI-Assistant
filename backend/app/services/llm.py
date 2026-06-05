"""
Groq LLM service — wraps the Groq Python SDK for chat completions.
Supports streaming and non-streaming generation.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from groq import AsyncGroq, APIError, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts — bilingual personality for Chulbul
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = {
    "en": (
        "You are Chulbul — a witty, helpful, and highly capable AI assistant. "
        "You speak fluent English. Be concise, precise, and engaging. "
        "When provided with search results or tool output, synthesize them "
        "into a clear, conversational answer. Never fabricate facts."
    ),
    "hi": (
        "Tum Chulbul ho — ek smart, mazedaar aur bahut kabil AI assistant. "
        "Tum Hinglish ya shuddh Hindi mein baat karte ho. Chhote aur helpful "
        "jawab do. Jab search ya tool ka output mile, usse saaf jawab mein "
        "badlo. Kabhi galat facts mat do."
    ),
}


# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------
_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    """Lazy-initialised async Groq client."""
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env"
            )
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def generate_response(
    user_message: str,
    *,
    language: str = "en",
    context: str = "",
) -> str:
    """
    Non-streaming completion. Returns the full assistant message.

    Args:
        user_message: The user's query.
        language:     "en" or "hi" — selects the system prompt.
        context:      Optional tool output to inject before the user query.
    """
    settings = get_settings()
    client = _get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["en"])},
    ]

    if context:
        messages.append({
            "role": "system",
            "content": f"[Tool Output]\n{context}",
        })

    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
        )
        return response.choices[0].message.content or ""

    except RateLimitError:
        logger.warning("Groq rate-limit hit — returning fallback message.")
        return (
            "I'm a bit overloaded right now. Please wait a moment and try again."
            if language == "en"
            else "Abhi thoda busy hoon, ek minute mein phir try karo."
        )
    except APIError as exc:
        logger.error("Groq API error: %s", exc)
        raise


async def generate_response_stream(
    user_message: str,
    *,
    language: str = "en",
    context: str = "",
) -> AsyncIterator[str]:
    """
    Streaming completion — yields text chunks as they arrive.
    Ideal for the SSE endpoint.
    """
    settings = get_settings()
    client = _get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["en"])},
    ]
    if context:
        messages.append({
            "role": "system",
            "content": f"[Tool Output]\n{context}",
        })
    messages.append({"role": "user", "content": user_message})

    try:
        stream = await client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=settings.groq_temperature,
            max_tokens=settings.groq_max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except RateLimitError:
        logger.warning("Groq rate-limit during stream.")
        yield (
            "Rate limit reached — please try again shortly."
            if language == "en"
            else "Rate limit lag gaya — thodi der mein try karo."
        )
    except APIError as exc:
        logger.error("Groq streaming error: %s", exc)
        raise
