"""
engine_factory.py
VoiceForge — Engine Factory

THE LEGO CONNECTOR. Reads config, instantiates the correct engine,
and implements the full routing + fallback chain.

RULES:
  1. The rest of the codebase ONLY calls EngineFactory — never imports
     concrete engine classes (EdgeTTSEngine, XTTSEngine, etc.) directly.
  2. LAZY IMPORTS: Engine classes are imported INSIDE _create_engine(),
     never at module level. This ensures placeholder engines and engines
     with missing dependencies never crash the server on startup.
  3. The fallback chain is: primary → xtts_v2 → edge_tts.
     In Phase 1, primary IS xtts_v2, so the chain is: xtts_v2 → edge_tts.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List

from engine.base_engine import (
    BaseTTSEngine,
    EngineNotAvailableError,
    EngineType,
    Language,
)
from config import get_phase, get_primary_engine_for_language, get_settings

logger = logging.getLogger(__name__)


class EngineFactory:
    """Creates, caches, and routes to TTS engine instances.

    All methods are class methods — EngineFactory is never instantiated.

    Usage:
        # Get the best engine for a request (handles fallback automatically)
        engine = EngineFactory.get_engine_for_request(Language.ENGLISH)
        result = engine.generate(request)

        # Get a specific engine by type (used in testing)
        engine = EngineFactory.get_engine(EngineType.EDGE_TTS)

        # Get status of all engines (used by /engines endpoint)
        statuses = EngineFactory.get_all_engine_status()
    """

    # Class-level instance cache: engine_type.value → engine instance
    # One instance per engine type, shared across all requests (thread-safe)
    _instances: Dict[str, BaseTTSEngine] = {}
    _lock: threading.Lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def get_engine(cls, engine_type: EngineType) -> BaseTTSEngine:
        """Return a cached engine instance, creating it on first call.

        Thread-safe — uses a class-level lock to prevent duplicate creation
        under concurrent requests.

        Args:
            engine_type: Which engine type to get.

        Returns:
            A BaseTTSEngine subclass instance (cached after first call).

        Raises:
            EngineNotAvailableError: If the engine cannot be instantiated
                (placeholder not yet built, missing pip dependency,
                wrong phase, or import error).
        """
        key = engine_type.value
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls._create_engine(engine_type)
            return cls._instances[key]

    @classmethod
    def get_engine_for_request(
        cls,
        language: Language,
        require_cloning: bool = False,
    ) -> BaseTTSEngine:
        """THE MAIN METHOD — return the best available engine for a request.

        Implements the full routing + fallback chain based on VOICEFORGE_PHASE
        and engine availability at the moment of the call.

        Routing chain:
            Phase 1 (VOICEFORGE_PHASE=1):
                xtts_v2 → edge_tts

            Phase 2 (VOICEFORGE_PHASE=2):
                English:   fish_s2_pro → xtts_v2 → edge_tts
                Hindi:     voxtral_tts → xtts_v2 → edge_tts
                Hinglish:  voxtral_tts → xtts_v2 → edge_tts

        Edge TTS caveats:
            - is_available() always returns True (no GPU needed)
            - supports_voice_cloning() returns False
            - If require_cloning=True, edge_tts is skipped entirely
            - GenerationResult.is_draft is True when edge_tts is used

        Args:
            language: The Language enum value for this request.
            require_cloning: If True, skip Edge TTS (it cannot clone voices).

        Returns:
            The first available BaseTTSEngine in the routing chain.

        Raises:
            EngineNotAvailableError: If no suitable engine is available.
                This should be caught by the API layer and returned as HTTP 503.
        """
        s = get_settings()
        lang_value = language.value  # "en", "hi", or "hinglish"

        primary_name   = get_primary_engine_for_language(lang_value)
        fallback_name  = s.ENGINE_FALLBACK   # always "xtts_v2"
        emergency_name = s.ENGINE_EMERGENCY  # always "edge_tts"

        # Build deduplicated ordered candidate list.
        # Example — Phase 1, English: ["xtts_v2", "edge_tts"]
        # Example — Phase 2, English: ["fish_s2_pro", "xtts_v2", "edge_tts"]
        # Example — Phase 1 (primary == fallback): ["xtts_v2", "edge_tts"]
        seen: set = set()
        candidates: List[str] = []
        for name in [primary_name, fallback_name, emergency_name]:
            if name not in seen:
                seen.add(name)
                candidates.append(name)

        logger.debug(
            "Engine routing for language=%s phase=%s: candidates=%s",
            lang_value, get_phase(), candidates,
        )

        for engine_name in candidates:
            is_emergency = (engine_name == emergency_name)

            # Skip Edge TTS when voice cloning is required
            if is_emergency and require_cloning:
                logger.warning(
                    "Skipping '%s' (emergency engine) — require_cloning=True "
                    "and Edge TTS has no voice cloning support.",
                    engine_name,
                )
                continue

            # Attempt to load the engine (lazy import inside get_engine)
            try:
                engine_type = EngineType(engine_name)
                engine = cls.get_engine(engine_type)
            except (ValueError, EngineNotAvailableError) as exc:
                logger.warning(
                    "Engine '%s' could not be loaded (%s: %s). "
                    "Trying next engine in chain.",
                    engine_name, type(exc).__name__, exc,
                )
                continue

            # Check real-time availability
            if engine.is_available():
                if engine_name == primary_name:
                    logger.info(
                        "Routing to primary engine: %s (language=%s)",
                        engine_name, lang_value,
                    )
                else:
                    logger.warning(
                        "Primary engine '%s' unavailable. "
                        "Falling back to '%s' (language=%s).",
                        primary_name, engine_name, lang_value,
                    )
                return engine
            else:
                logger.warning(
                    "Engine '%s' reports is_available()=False. "
                    "Trying next engine in chain.",
                    engine_name,
                )

        # All candidates exhausted
        cloning_note = " with voice cloning support" if require_cloning else ""
        raise EngineNotAvailableError(
            f"No available TTS engine{cloning_note} for language "
            f"'{lang_value}' (phase={get_phase()}). "
            f"Tried: {candidates}. "
            f"Check TRIJYA-7 connectivity and VOICEFORGE_PHASE setting."
        )

    @classmethod
    def get_all_engine_status(cls) -> List[dict]:
        """Return status information for all 4 engines.

        Used by the GET /engines API endpoint (implemented in P5).
        Never crashes — all exceptions are caught per engine.
        Placeholder engines (not yet built) return status='not_built'.

        Returns:
            List of 4 dicts, one per engine, each containing:
                engine_type, status, is_available, supports_cloning,
                supported_languages, and optionally 'error'.
        """
        statuses: List[dict] = []

        for engine_type in EngineType:
            try:
                engine = cls.get_engine(engine_type)
                info = engine.get_engine_info()
                info["status"] = (
                    "available" if info.get("is_available") else "unavailable"
                )
            except EngineNotAvailableError as exc:
                info = {
                    "engine_type": engine_type.value,
                    "status": "not_built",
                    "error": str(exc),
                    "is_available": False,
                    "supports_cloning": None,
                    "supported_languages": [],
                }
            except Exception as exc:
                logger.warning(
                    "Unexpected error querying status for engine '%s': %s",
                    engine_type.value, exc,
                )
                info = {
                    "engine_type": engine_type.value,
                    "status": "error",
                    "error": str(exc),
                    "is_available": False,
                    "supports_cloning": None,
                    "supported_languages": [],
                }
            statuses.append(info)

        return statuses

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the engine instance cache.

        Forces fresh engine creation on the next call to get_engine().
        Used in tests to reset state between test cases.
        """
        with cls._lock:
            cls._instances.clear()
        logger.debug("Engine instance cache cleared.")

    # ── Private helpers ───────────────────────────────────────────────────────

    @classmethod
    def _create_engine(cls, engine_type: EngineType) -> BaseTTSEngine:
        """Lazy-import and instantiate the correct engine class.

        LAZY IMPORTS: Each engine module is imported only here, inside this
        method, at the moment it is first needed. This means:
          - Placeholder engines (not yet implemented) don't crash startup
          - Engines with missing pip dependencies don't crash startup
          - Only the requested engine's dependencies are imported

        Args:
            engine_type: Which engine type to instantiate.

        Returns:
            A new BaseTTSEngine subclass instance.

        Raises:
            EngineNotAvailableError: If the engine cannot be instantiated.
                This includes: placeholder files, ImportError (missing dep),
                or any error raised by the engine's __init__.
        """
        if engine_type == EngineType.EDGE_TTS:
            try:
                from engine.edge_engine import EdgeTTSEngine  # noqa: PLC0415
                return EdgeTTSEngine()
            except (ImportError, Exception) as exc:
                raise EngineNotAvailableError(
                    f"Edge TTS engine could not be loaded: {exc}. "
                    f"(Built in P3 — run pip install edge-tts first.)"
                ) from exc

        elif engine_type == EngineType.XTTS_V2:
            try:
                from engine.xtts_engine import XTTSEngine  # noqa: PLC0415
                return XTTSEngine()
            except (ImportError, Exception) as exc:
                raise EngineNotAvailableError(
                    f"XTTS v2 engine could not be loaded: {exc}. "
                    f"(Built in P4 — run pip install TTS first.)"
                ) from exc

        elif engine_type == EngineType.VOXTRAL_TTS:
            try:
                from engine.voxtral_engine import VoxtralEngine  # noqa: PLC0415
                return VoxtralEngine()
            except (ImportError, Exception) as exc:
                raise EngineNotAvailableError(
                    f"Voxtral TTS engine could not be loaded: {exc}. "
                    f"(Built in P12 — requires Phase 2 with vLLM-Omni in WSL2.)"
                ) from exc

        elif engine_type == EngineType.FISH_S2_PRO:
            try:
                from engine.fish_engine import FishEngine  # noqa: PLC0415
                return FishEngine()
            except (ImportError, Exception) as exc:
                raise EngineNotAvailableError(
                    f"Fish S2 Pro engine could not be loaded: {exc}. "
                    f"(Built in P13 — requires Phase 2 with SGLang in WSL2.)"
                ) from exc

        else:
            raise EngineNotAvailableError(
                f"Unknown engine type: '{engine_type}'. "
                f"Valid types: {[t.value for t in EngineType]}"
            )
