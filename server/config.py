"""
config.py
VoiceForge — Centralized Configuration

THE SINGLE FILE where the engine stack is configured.
Change one environment variable here → entire engine behaviour changes.
Nothing in the engine logic reads os.environ directly — only this file does.

Loading order:
  1. If server/.env exists, load it (via python-dotenv)
  2. Read os.environ for each setting
  3. Fall back to hardcoded defaults

No .env file needed for Phase 1 development — defaults are Phase 1 safe.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Load .env file (if present) ───────────────────────────────────────────────
# Must happen before any os.environ.get() calls below
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        _load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass  # python-dotenv not installed — env vars still work via os.environ


# ── Private helpers ───────────────────────────────────────────────────────────

def _str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, str(default)).strip().lower()
    return val in ("1", "true", "yes", "on")


# ── Settings Dataclass ────────────────────────────────────────────────────────

@dataclass
class Settings:
    """All VoiceForge configuration in one place.

    Every field reads from an environment variable with a safe default.
    To change engine behaviour: set the env var (or update .env).
    To add a new setting: add a field here — nowhere else.

    NEVER import os.environ in engine files — call get_settings() instead.
    """

    # ── Engine Selection ──────────────────────────────────────────────────────
    # Primary engines per language. These are the Phase 2 targets.
    # In Phase 1, get_primary_engine_for_language() overrides these with xtts_v2.
    ENGINE_ENGLISH_PRIMARY: str = field(
        default_factory=lambda: _str("ENGINE_ENGLISH_PRIMARY", "fish_s2_pro")
    )
    ENGINE_HINDI_PRIMARY: str = field(
        default_factory=lambda: _str("ENGINE_HINDI_PRIMARY", "voxtral_tts")
    )
    ENGINE_HINGLISH_PRIMARY: str = field(
        default_factory=lambda: _str("ENGINE_HINGLISH_PRIMARY", "voxtral_tts")
    )

    # Fallback and emergency engines (same for all languages)
    ENGINE_FALLBACK: str = field(
        default_factory=lambda: _str("ENGINE_FALLBACK", "xtts_v2")
    )
    ENGINE_EMERGENCY: str = field(
        default_factory=lambda: _str("ENGINE_EMERGENCY", "edge_tts")
    )

    # ── Phase Control ─────────────────────────────────────────────────────────
    # "1" = Phase 1 only (XTTS v2 + Edge TTS, runs on Windows natively)
    # "2" = Phase 2 (Voxtral + Fish S2 Pro via WSL2 on TRIJYA-7)
    # get_phase() reads VOICEFORGE_PHASE directly from os.environ so it
    # reflects changes immediately without needing to reload the singleton.
    VOICEFORGE_PHASE: str = field(
        default_factory=lambda: _str("VOICEFORGE_PHASE", "1")
    )

    # ── Server Paths ──────────────────────────────────────────────────────────
    VOICE_PROFILES_DIR: str = field(
        default_factory=lambda: _str("VOICE_PROFILES_DIR", "server/voice_profiles")
    )
    REFERENCE_AUDIO_DIR: str = field(
        default_factory=lambda: _str("REFERENCE_AUDIO_DIR", "server/reference_audio")
    )
    OUTPUT_DIR: str = field(
        default_factory=lambda: _str("OUTPUT_DIR", "server/output")
    )

    # ── XTTS v2 Settings ──────────────────────────────────────────────────────
    XTTS_MODEL_NAME: str = field(
        default_factory=lambda: _str(
            "XTTS_MODEL_NAME",
            "tts_models/multilingual/multi-dataset/xtts_v2",
        )
    )
    XTTS_USE_GPU: bool = field(
        default_factory=lambda: _bool("XTTS_USE_GPU", True)
    )

    # ── Voxtral TTS Settings (Phase 2) ───────────────────────────────────────
    # vLLM-Omni runs inside WSL2 on TRIJYA-7.
    # WSL2 exposes its port to Windows on localhost — no Tailscale IP needed.
    VOXTRAL_HOST: str = field(
        default_factory=lambda: _str("VOXTRAL_HOST", "localhost")
    )
    VOXTRAL_PORT: int = field(
        default_factory=lambda: _int("VOXTRAL_PORT", 8091)
    )
    VOXTRAL_MODEL: str = field(
        default_factory=lambda: _str(
            "VOXTRAL_MODEL", "mistralai/Voxtral-4B-TTS-2603"
        )
    )
    VOXTRAL_TIMEOUT: int = field(
        default_factory=lambda: _int("VOXTRAL_TIMEOUT", 120)
    )

    # ── Fish S2 Pro Settings (Phase 2) ────────────────────────────────────────
    # SGLang runs inside WSL2 on TRIJYA-7.
    FISH_HOST: str = field(
        default_factory=lambda: _str("FISH_HOST", "localhost")
    )
    FISH_PORT: int = field(
        default_factory=lambda: _int("FISH_PORT", 8092)
    )
    FISH_MODEL: str = field(
        default_factory=lambda: _str("FISH_MODEL", "fishaudio/s2-pro")
    )
    FISH_TIMEOUT: int = field(
        default_factory=lambda: _int("FISH_TIMEOUT", 120)
    )

    # ── Audio Output ──────────────────────────────────────────────────────────
    DEFAULT_OUTPUT_FORMAT: str = field(
        default_factory=lambda: _str("DEFAULT_OUTPUT_FORMAT", "wav")
    )
    DEFAULT_SAMPLE_RATE: int = field(
        default_factory=lambda: _int("DEFAULT_SAMPLE_RATE", 24000)
    )

    # ── Edge TTS Voice Names ──────────────────────────────────────────────────
    # Microsoft Neural voices used as emergency fallback.
    # Full list: https://learn.microsoft.com/azure/cognitive-services/speech/language-support
    EDGE_TTS_VOICE_EN_MALE: str = field(
        default_factory=lambda: _str("EDGE_TTS_VOICE_EN_MALE", "en-US-GuyNeural")
    )
    EDGE_TTS_VOICE_EN_FEMALE: str = field(
        default_factory=lambda: _str("EDGE_TTS_VOICE_EN_FEMALE", "en-US-JennyNeural")
    )
    EDGE_TTS_VOICE_HI_MALE: str = field(
        default_factory=lambda: _str("EDGE_TTS_VOICE_HI_MALE", "hi-IN-MadhurNeural")
    )
    EDGE_TTS_VOICE_HI_FEMALE: str = field(
        default_factory=lambda: _str("EDGE_TTS_VOICE_HI_FEMALE", "hi-IN-SwaraNeural")
    )


# ── Singleton ──────────────────────────────────────────────────────────────────

_settings: "Settings | None" = None


def get_settings() -> Settings:
    """Return the singleton Settings instance.

    Created on first call. Reads environment variables at creation time.
    Call clear_settings_cache() in tests when you need to change env vars
    and have the new values picked up.

    Returns:
        The singleton Settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def clear_settings_cache() -> None:
    """Reset the Settings singleton. Used in tests only.

    After calling this, the next get_settings() call will re-read all
    environment variables and create a fresh Settings instance.
    """
    global _settings
    _settings = None


# ── Public helper functions ────────────────────────────────────────────────────

def get_phase() -> int:
    """Return the current active phase as an integer (1 or 2).

    IMPORTANT: Reads VOICEFORGE_PHASE directly from os.environ on every call
    (does NOT use the Settings singleton). This ensures that setting
    os.environ['VOICEFORGE_PHASE'] = '1' in tests is reflected immediately
    without needing to call clear_settings_cache().

    Returns:
        1 for Phase 1 (XTTS v2 + Edge TTS, Windows native)
        2 for Phase 2 (all 4 engines, Voxtral + Fish via WSL2)
        1 as safe default for any invalid/missing value
    """
    try:
        return int(os.environ.get("VOICEFORGE_PHASE", "1"))
    except (ValueError, TypeError):
        return 1


def get_primary_engine_for_language(language: str) -> str:
    """Return the configured primary engine name for the given language.

    Respects VOICEFORGE_PHASE:
      Phase 1 → always returns 'xtts_v2' (Phase 2 engines not available)
      Phase 2 → returns the configured ENGINE_*_PRIMARY for the language

    Args:
        language: Language string value — "en", "hi", "hinglish",
                  or Language enum value (coerced to str automatically).

    Returns:
        Engine name string matching an EngineType enum value
        (e.g. "xtts_v2", "fish_s2_pro", "voxtral_tts").
    """
    if get_phase() == 1:
        return "xtts_v2"

    s = get_settings()
    lang = str(language).lower().strip()

    if lang in ("en", "english"):
        return s.ENGINE_ENGLISH_PRIMARY
    elif lang in ("hi", "hindi"):
        return s.ENGINE_HINDI_PRIMARY
    elif lang in ("hinglish",):
        return s.ENGINE_HINGLISH_PRIMARY
    else:
        # Unknown language — fall back to xtts_v2 (most multilingual Phase 1 engine)
        return s.ENGINE_FALLBACK
