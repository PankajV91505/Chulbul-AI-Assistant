"""
Shared utility functions used across the application.
"""

from __future__ import annotations

import re
import uuid
import logging
from pathlib import Path

from app.config import TEMP_AUDIO_DIR

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """Create a new unique session identifier."""
    return uuid.uuid4().hex[:16]


def detect_language_hint(text: str) -> str:
    """
    Naive heuristic to detect if a string is predominantly Hindi (Devanagari)
    or English. Used as a fallback when the frontend doesn't specify language.

    Returns "hi" if > 30% of characters are Devanagari, else "en".
    """
    if not text:
        return "en"
    devanagari = re.findall(r"[\u0900-\u097F]", text)
    ratio = len(devanagari) / max(len(text), 1)
    return "hi" if ratio > 0.30 else "en"


def cleanup_old_audio(max_age_seconds: int = 300) -> int:
    """
    Delete audio files older than *max_age_seconds* from the temp directory.
    Returns the number of files deleted.
    """
    import time

    now = time.time()
    deleted = 0
    for f in TEMP_AUDIO_DIR.glob("chulbul_*.mp3"):
        if (now - f.stat().st_mtime) > max_age_seconds:
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass
    if deleted:
        logger.info("Cleaned up %d old audio files.", deleted)
    return deleted
