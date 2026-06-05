"""
Browser automation tool — lightweight Playwright wrapper.
Performs simple browse-and-extract tasks (e.g. open URL, get page text).

Requires `playwright install chromium` to be run once.
Guarded behind the ENABLE_BROWSER_TOOL feature flag.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def browse_url(url: str, *, extract_text: bool = True) -> str:
    """
    Open a URL in a headless browser and optionally extract visible text.

    Args:
        url:          The URL to navigate to.
        extract_text: If True, returns the visible text content of the page.

    Returns:
        Extracted page text or a status message.
    """
    settings = get_settings()
    if not settings.enable_browser_tool:
        return (
            "Browser automation is disabled. "
            "Set ENABLE_BROWSER_TOOL=true in .env and run "
            "'playwright install chromium' to enable it."
        )

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=15_000, wait_until="domcontentloaded")

            if extract_text:
                content = await page.inner_text("body")
                # Truncate very long pages to stay within LLM context limits
                content = content[:4000]
                logger.info("Extracted %d chars from %s", len(content), url)
            else:
                content = f"Successfully loaded: {url}"

            await browser.close()
            return content

    except ImportError:
        return (
            "Playwright is not installed. Run: "
            "pip install playwright && playwright install chromium"
        )
    except Exception as exc:
        logger.error("Browser automation failed for %s: %s", url, exc)
        return f"Browser automation error: {exc}"
