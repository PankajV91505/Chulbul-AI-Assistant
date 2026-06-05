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


async def classify_intent(user_message: str) -> dict:
    """
    Use the LLM to classify the intent of the user message into a tool and its arguments.
    Returns a dict with 'tool' (ToolName) and 'args' (string).
    """
    import json
    from app.models.schemas import ToolName
    settings = get_settings()
    client = _get_client()

    schema = {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "enum": ["web_search", "browser", "system", "none"],
                "description": "The tool to use to answer the user's request. Use 'web_search' for current events, news, facts, weather, and general queries that require the internet. Use 'browser' to navigate to a specific URL. Use 'system' to open apps or check system info. Use 'none' if you can answer directly without any tools."
            },
            "args": {
                "type": "string",
                "description": "The arguments to pass to the tool. For web_search, provide the search query. For browser, provide the URL. For system, provide the action (e.g. 'time', 'open_app|notepad'). Leave empty if 'none'."
            }
        },
        "required": ["tool", "args"]
    }

    system_msg = (
        "You are an intent router for an AI assistant. "
        "Analyze the user's request and determine the appropriate tool to fulfill it. "
        "Always respond with a valid JSON object matching the provided schema. "
        "If they ask for news, weather, or current facts, you MUST select 'web_search'. "
        "If they ask to open a website, use 'browser' with the URL. "
        "Return ONLY the JSON, no markdown formatting."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = response.choices[0].message.content
        data = json.loads(result)
        
        tool_map = {
            "web_search": ToolName.WEB_SEARCH,
            "browser": ToolName.BROWSER,
            "system": ToolName.SYSTEM,
            "none": ToolName.NONE
        }
        tool = tool_map.get(data.get("tool", "none").lower(), ToolName.NONE)
        args = data.get("args", "")
        return {"tool": tool, "args": args}
    except Exception as exc:
        logger.error("Intent classification failed: %s", exc)
        return {"tool": ToolName.NONE, "args": ""}

