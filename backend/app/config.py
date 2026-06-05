"""
Centralized configuration loaded from environment variables.
All secrets and tunables live in .env — never hardcode them.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_AUDIO_DIR = BASE_DIR / "tmp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Settings model — reads from .env automatically
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Application-wide settings, populated from the .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Groq LLM ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.6
    groq_max_tokens: int = 2048

    # --- STT (faster-whisper) ---
    whisper_model_size: str = "base"          # tiny | base | small | medium | large-v3
    whisper_device: str = "cpu"               # cpu | cuda
    whisper_compute_type: str = "int8"        # int8 | float16 | float32

    # --- TTS (edge-tts) ---
    tts_voice_en: str = "en-US-GuyNeural"
    tts_voice_hi: str = "hi-IN-MadhurNeural"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Feature flags ---
    enable_browser_tool: bool = False         # Playwright requires install

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Singleton accessor — cached after first call."""
    return Settings()
