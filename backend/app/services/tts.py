"""
Text-to-Speech service powered by edge-tts (Microsoft Edge TTS, free).
Generates MP3 files on disk and returns a servable path.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import edge_tts

from app.config import get_settings, TEMP_AUDIO_DIR

logger = logging.getLogger(__name__)


async def synthesize(text: str, *, language: str = "en") -> Path:
    """
    Convert *text* to an MP3 file using edge-tts.

    Args:
        text:     The text to speak.
        language: "en" or "hi" — selects the voice preset.

    Returns:
        Path to the generated MP3 file.

    Raises:
        RuntimeError: If edge-tts fails to produce audio.
    """
    settings = get_settings()
    voice = settings.tts_voice_en if language == "en" else settings.tts_voice_hi

    filename = f"chulbul_{uuid.uuid4().hex[:12]}.mp3"
    output_path = TEMP_AUDIO_DIR / filename

    try:
        communicator = edge_tts.Communicate(text=text, voice=voice)
        await communicator.save(str(output_path))
        logger.info("TTS audio saved → %s (%s)", filename, voice)
        return output_path

    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise RuntimeError(f"TTS synthesis failed: {exc}") from exc


def cleanup_audio(path: Path) -> None:
    """Delete a temporary audio file — best-effort, logs on failure."""
    try:
        if path.exists():
            path.unlink()
            logger.debug("Cleaned up audio file: %s", path.name)
    except OSError as exc:
        logger.warning("Could not delete %s: %s", path, exc)
