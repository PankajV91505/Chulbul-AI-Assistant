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
        "You are Chulbul, an advanced futuristic smart-home AI operating system with elite intelligence, "
        "premium polished tone, and natural human-like conversation. You specialize in full home automation "
        "by controlling lights, TV, fans, AC, curtains, speakers, cameras, door locks, appliances, and all IoT devices "
        "through voice, text, and gesture commands. You can instantly turn devices on/off, change brightness, colors, "
        "volume, channels, temperature, and modes. You can create and manage smart routines like Wake Up Mode, Movie Mode, "
        "Gaming Mode, Sleep Mode, Away Mode, and Party Mode. You provide real-time status updates, weather reports, "
        "reminders, calendar alerts, security monitoring, motion detection warnings, visitor notifications, and "
        "energy-saving suggestions. When provided with search results or tool output, synthesize them into a clear, "
        "conversational answer. Maintain a helpful, futuristic, and highly competent persona. Never fabricate facts."
    ),
    "hi": (
        "Tum Chulbul ho — ek advanced futuristic smart-home AI operating system jiski intelligence elite hai aur awaaz premium. "
        "Tumhari baatein ekdum natural aur human-like hain. Tumhara main kaam poore ghar ko automate karna hai — lights, TV, "
        "fans, AC, curtains, speakers, cameras, door locks, appliances aur sabhi IoT devices ko voice, text ya gestures se control karna. "
        "Tum turant devices on/off kar sakte ho, brightness, colors, volume, channels aur temperature badal sakte ho. Tum smart "
        "routines jaise Wake Up Mode, Movie Mode, Gaming Mode, Sleep Mode, Away Mode, aur Party Mode manage karte ho. Tum real-time "
        "status updates, weather reports, reminders, calendar alerts, security monitoring, motion warnings aur energy-saving tips bhi dete ho. "
        "Jab bhi koi tool ya search result mile, usko ekdum saaf aur conversational tareeqe se samjhao. Hamesha ek smart, helpful aur "
        "futuristic persona maintain karo. Kabhi galat facts mat do."
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
                "enum": ["web_search", "browser", "system", "interpreter", "none"],
                "description": "The tool to use to answer the user's request. Use 'web_search' for current events. Use 'browser' to navigate to a URL. Use 'system' to open apps or check basic system info. Use 'interpreter' for complex OS tasks or running code. Use 'none' if you can answer directly."
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
        "Always respond with a valid JSON object matching the provided schema.\n\n"
        "1. web_search: Use if they ask for news, weather, or current facts.\n"
        "2. browser: Use ONLY if they ask to read, scrape, or summarize the contents of a URL.\n"
        "3. system:\n"
        "   - For local laptop commands: 'what time is it', 'open notepad', 'check my disk usage', 'list files on desktop'\n"
        "   - **CRITICAL**: If the user explicitly wants to OPEN a website to LOOK at it (e.g. 'open youtube', 'kholo', 'start google'), use system with arg: open_url|<url>\n"
        "   - Examples args: 'time', 'date', 'disk_usage', 'system_info', 'open_app|notepad', 'open_url|https://youtube.com', 'list_files|C:/'\n\n"
        "4. interpreter:\n"
        "   - Use for complex OS tasks, running code, organizing files, changing system settings, or anything requiring terminal execution.\n"
        "   - Examples: 'write a python script to calculate pi', 'organize my downloads folder', 'turn on dark mode'.\n\n"
        "5. none: Use if you can answer the question directly.\n\n"
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
            "interpreter": ToolName.INTERPRETER,
            "none": ToolName.NONE
        }
        tool = tool_map.get(data.get("tool", "none").lower(), ToolName.NONE)
        args = data.get("args", "")
        return {"tool": tool, "args": args}
    except Exception as exc:
        logger.error("Intent classification failed: %s", exc)
        return {"tool": ToolName.NONE, "args": ""}

