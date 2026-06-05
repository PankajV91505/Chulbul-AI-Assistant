"""
Speech-to-Text service powered by faster-whisper (CTranslate2 backend).
Runs locally — no API key needed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy model loader — heavy model stays in memory once loaded
# ---------------------------------------------------------------------------
_model = None


def _get_model():
    """
    Lazily load the faster-whisper model on first call.
    The model stays resident for subsequent transcriptions.
    """
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # heavy import — deferred

        settings = get_settings()
        logger.info(
            "Loading Whisper model '%s' on %s (%s)…",
            settings.whisper_model_size,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Whisper model loaded successfully.")
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def transcribe(audio_path: str | Path) -> tuple[str, Optional[str]]:
    """
    Transcribe an audio file to text.

    Args:
        audio_path: Path to a WAV / MP3 / WEBM file.

    Returns:
        A tuple of (transcribed_text, detected_language_code).
        If transcription fails, returns ("", None).
    """
    model = _get_model()

    try:
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,           # skip silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )
        text = " ".join(seg.text.strip() for seg in segments)
        detected_lang = info.language if info else None
        logger.info(
            "Transcribed %d chars (lang=%s) from %s",
            len(text), detected_lang, Path(audio_path).name,
        )
        return text, detected_lang

    except Exception as exc:
        logger.error("Transcription failed for %s: %s", audio_path, exc)
        return "", None
