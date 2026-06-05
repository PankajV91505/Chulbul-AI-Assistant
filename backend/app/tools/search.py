"""
Web search tool — uses duckduckgo-search (DDGS) for zero-cost web queries.
Returns a formatted summary string suitable for LLM context injection.
"""

from __future__ import annotations

import logging
from typing import Optional

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Maximum results to fetch per query
MAX_RESULTS = 6


async def web_search(query: str, *, max_results: int = MAX_RESULTS) -> str:
    """
    Search the web via DuckDuckGo and return a markdown-formatted summary.

    Args:
        query:       The search query string.
        max_results: Cap on the number of results to return.

    Returns:
        A formatted string of search results, or an error message.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: '{query}'"

        lines: list[str] = [f"### Search results for: {query}\n"]
        for idx, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"**{idx}. {title}**")
            lines.append(f"   {body}")
            if href:
                lines.append(f"   Source: {href}")
            lines.append("")

        formatted = "\n".join(lines)
        logger.info("Web search returned %d results for '%s'", len(results), query)
        return formatted

    except Exception as exc:
        logger.error("Web search failed: %s", exc)
        return f"Web search encountered an error: {exc}"
