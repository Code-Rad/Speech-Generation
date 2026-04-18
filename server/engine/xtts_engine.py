"""
xtts_engine.py
VoiceForge — XTTS v2 Engine (Phase 1 Primary + Fallback)

THE PHASE 1 WORKHORSE. Runs natively on Windows via the Coqui TTS pip package.
No WSL2 required. Supports English, Hindi, and Hinglish with voice cloning.

ROLE IN THE ROUTING CHAIN:
  Phase 1: Primary engine for ALL languages (xtts_v2 → edge_tts)
  Phase 2: Fallback engine when Voxtral or Fish S2 Pro are unavailable

TRADE-OFFS:
  + High-quality voice cloning from a reference WAV file (~10–25 sec)
  + Multilingual: supports EN, HI natively; Hinglish mapped to EN
  + Runs on RTX 4090 (TRIJYA-7) — ~4 GB VRAM at fp16
  - First run downloads ~2 GB model to Coqui cache dir (one-time)
  - Model load takes ~30 seconds on first request
  - CPML license — non-commercial use only

SINGLETON MODEL:
  The TTS model is loaded once and cached at class level (_model).
  Subsequent requests reuse the loaded model — no reload per request.
  Model is loaded lazily (on first generate() or clone_voice() call).
  _model_lock prevents duplicate loading under concurrent requests.

LANGUAGE CODE MAPPING:
  XTTS v2 uses ISO 639-1 codes: "en", "hi", etc.
  Hinglish → "en" (closest supported language; XTTS handles code-switching)

MODEL CACHE PATHS (Coqui TTS auto-selects per OS):
  Windows: C:\\Users\\<user>\\AppData\\Local\\tts\\
  Linux:   ~/.local/share/tts/
  The XTTS v2 folder is named: tts_models--multilingual--multi-dataset--xtts_v2
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

from engine.base_engine import (
    BaseTTSEngine,
    EngineGenerationError,
    EngineType,
    GenerationRequest,
    GenerationResult,
    Language,
    VoiceCloningNotSupportedError,
)
from config import get_settings

logger = logging.getLogger(__name__)

# XTTS v2 language code mapping (XTTS uses ISO 639-1 codes)
_XTTS_LANGUAGE_CODES = {
    Language.ENGLISH:  "en",
    Language.HINDI:    "hi",
    Language.HINGLISH: "en",  # No Hinglish code — EN handles code-switching best
}

# Coqui TTS converts model names to directory names by replacing "/" with "--"
_MODEL_DIR_NAME = "tts_models--multilingual--multi-dataset--xtts_v2"


class XTTSEngine(BaseTTSEngine):
    """Phase 1 primary TTS engine using Coqui XTTS v2.

    Supports all three VoiceForge languages with voice cloning.
    The model is loaded once and cached — never reloaded between requests.

    Usage (via EngineFactory — never instantiate directly):
        engine = EngineFactory.get_engine(EngineType.XTTS_V2)
        result = engine.clone_voice(request, reference_audio_path)
    """

    # ── Singleton model state (shared across all XTTSEngine instances) ─────────
    _model = None                          # Loaded TTS object (None until first use)
    _model_lock: threading.Lock = threading.Lock()
    _model_load_attempted: bool = False    # True after first load attempt (success or fail)
    _model_load_error: Optional[str] = None  # Set if load failed — surfaced in generate()

    # ── Abstract method implementations ───────────────────────────────────────

    def get_engine_type(self) -> EngineType:
        return EngineType.XTTS_V2

    def get_supported_languages(self) -> List[Language]:
        return [Language.ENGLISH, Language.HINDI, Language.HINGLISH]

    def supports_voice_cloning(self) -> bool:
        return True

    def is_available(self) -> bool:
        """Return True if the XTTS v2 model cache exists on disk.

        Checks whether the Coqui TTS model directory exists — does NOT
        load the model or make any network calls. This runs in < 1ms.

        Returns:
            True if model cache directory found; False otherwise.
            Never raises — catches all exceptions and returns False.
        """
        try:
            return self._model_cache_dir().exists()
        except Exception as exc:
            logger.debug("XTTS is_available() check failed: %s", exc)
            return False

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate speech using XTTS v2, with voice cloning if reference audio exists.

        If the voice profile's reference audio file exists in REFERENCE_AUDIO_DIR,
        voice cloning is used (best quality). Otherwise, falls back to XTTS v2's
        default speaker for the language/gender (lower quality, no reference needed).

        Args:
            request: GenerationRequest with text, voice_profile, and output_path.

        Returns:
            GenerationResult with is_draft=False and full metadata.

        Raises:
            EngineGenerationError: If the model cannot be loaded or synthesis fails.
        """
        self.validate_request(request)

        # Resolve reference audio path
        reference_path = self._resolve_reference_audio(request)

        if reference_path is not None:
            logger.debug(
                "XTTS generate(): using voice cloning from '%s'", reference_path
            )
            return self._run_synthesis(
                request=request,
                reference_audio_path=str(reference_path),
            )
        else:
            logger.warning(
                "XTTS generate(): reference audio not found for profile '%s' "
                "(expected: %s). Falling back to default speaker. "
                "Drop a reference .wav in REFERENCE_AUDIO_DIR for cloned voice.",
                request.voice_profile.profile_id,
                request.voice_profile.reference_audio_filename,
            )
            return self._run_synthesis(
                request=request,
                reference_audio_path=None,
            )

    def clone_voice(
        self,
        request: GenerationRequest,
        reference_audio_path: str,
    ) -> GenerationResult:
        """Generate speech using voice cloned from an explicit reference audio file.

        Unlike generate(), this method requires a reference audio path — it does
        NOT fall back to a default speaker. Use this when the caller has already
        located the reference audio and wants explicit cloning.

        Args:
            request: GenerationRequest with text, voice_profile, and output_path.
            reference_audio_path: Absolute path to a .wav reference clip.
                Requirements: 10–25 seconds, clean speech, broadcast quality.

        Returns:
            GenerationResult with is_draft=False and full metadata.

        Raises:
            EngineGenerationError: If the reference file is missing, the model
                cannot be loaded, or synthesis fails.
        """
        self.validate_request(request)

        ref_path = Path(reference_audio_path)
        if not ref_path.exists():
            raise EngineGenerationError(
                f"Reference audio file not found: '{reference_audio_path}'. "
                f"Ensure the file exists before calling clone_voice()."
            )

        logger.debug(
            "XTTS clone_voice(): cloning from '%s'", reference_audio_path
        )
        return self._run_synthesis(
            request=request,
            reference_audio_path=reference_audio_path,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _run_synthesis(
        self,
        request: GenerationRequest,
        reference_audio_path: Optional[str],
    ) -> GenerationResult:
        """Core synthesis logic — loads model if needed, calls tts_to_file().

        Args:
            request: The full GenerationRequest.
            reference_audio_path: Path to reference .wav, or None for default speaker.

        Returns:
            Populated GenerationResult.

        Raises:
            EngineGenerationError: On model load failure or synthesis failure.
        """
        start_time = time.monotonic()

        # Ensure model is loaded (thread-safe, loaded once)
        model = self._get_or_load_model()

        # Build output path
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Map VoiceForge language → XTTS language code
        lang_code = _XTTS_LANGUAGE_CODES.get(
            request.voice_profile.language, "en"
        )

        if lang_code == "en" and request.voice_profile.language == Language.HINGLISH:
            logger.debug(
                "Hinglish request mapped to XTTS language code 'en' "
                "(XTTS handles code-switching in English mode)."
            )

        try:
            if reference_audio_path is not None:
                # Voice cloning mode — highest quality
                model.tts_to_file(
                    text=request.text,
                    speaker_wav=reference_audio_path,
                    language=lang_code,
                    file_path=str(output_path),
                )
            else:
                # Default speaker mode — no reference audio available
                # XTTS v2 picks a random default speaker for the language
                model.tts_to_file(
                    text=request.text,
                    language=lang_code,
                    file_path=str(output_path),
                )
        except Exception as exc:
            raise EngineGenerationError(
                f"XTTS v2 synthesis failed (language='{lang_code}', "
                f"reference='{reference_audio_path}'): {exc}"
            ) from exc

        generation_time = time.monotonic() - start_time
        duration = self._read_audio_duration(output_path)

        logger.info(
            "XTTS v2: generated '%s' (lang=%s, cloned=%s, time=%.2fs)",
            output_path.name,
            lang_code,
            reference_audio_path is not None,
            generation_time,
        )

        return GenerationResult(
            success=True,
            audio_path=str(output_path),
            duration_seconds=duration,
            engine_used=EngineType.XTTS_V2,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=False,  # XTTS v2 is broadcast-quality (not draft)
            error_message="",
            generation_time_seconds=generation_time,
        )

    @classmethod
    def _get_or_load_model(cls):
        """Return the cached TTS model, loading it on the first call.

        Thread-safe — uses _model_lock. After the first successful load,
        subsequent calls return immediately without acquiring the lock.

        Returns:
            A loaded Coqui TTS model object.

        Raises:
            EngineGenerationError: If the model cannot be loaded (library
                not installed, model not downloaded, or CUDA error).
        """
        # Fast path — model already loaded (no lock needed for read)
        if cls._model is not None:
            return cls._model

        with cls._model_lock:
            # Double-check inside lock (another thread may have loaded it)
            if cls._model is not None:
                return cls._model

            # If a previous load attempt failed, surface the cached error
            if cls._model_load_attempted and cls._model_load_error:
                raise EngineGenerationError(
                    f"XTTS v2 model failed to load on previous attempt: "
                    f"{cls._model_load_error}. "
                    f"Restart the server to retry."
                )

            cls._model_load_attempted = True
            logger.info(
                "Loading XTTS v2 model for the first time — "
                "this takes ~30s and requires ~4 GB VRAM..."
            )

            try:
                from TTS.api import TTS  # noqa: PLC0415
            except ImportError as exc:
                cls._model_load_error = str(exc)
                raise EngineGenerationError(
                    f"Coqui TTS library not installed: {exc}. "
                    f"Run: pip install TTS"
                ) from exc

            s = get_settings()
            try:
                model = TTS(
                    model_name=s.XTTS_MODEL_NAME,
                    gpu=s.XTTS_USE_GPU,
                )
                cls._model = model
                logger.info("XTTS v2 model loaded successfully.")
                return cls._model

            except Exception as exc:
                cls._model_load_error = str(exc)
                raise EngineGenerationError(
                    f"XTTS v2 model load failed (model='{s.XTTS_MODEL_NAME}', "
                    f"gpu={s.XTTS_USE_GPU}): {exc}. "
                    f"Ensure PyTorch + CUDA are installed and the model is downloaded."
                ) from exc

    def _resolve_reference_audio(self, request: GenerationRequest) -> Optional[Path]:
        """Resolve the reference audio path for a voice profile.

        Looks up `voice_profile.reference_audio_filename` in the configured
        REFERENCE_AUDIO_DIR. Returns None if the file does not exist (callers
        handle the missing-reference case gracefully).

        Args:
            request: GenerationRequest with a populated voice_profile.

        Returns:
            Path to the reference .wav file, or None if not found.
        """
        if not request.voice_profile.cloning_enabled:
            logger.debug(
                "Voice cloning disabled for profile '%s' — skipping reference audio.",
                request.voice_profile.profile_id,
            )
            return None

        s = get_settings()
        ref_dir = Path(s.REFERENCE_AUDIO_DIR)
        ref_file = ref_dir / request.voice_profile.reference_audio_filename

        if ref_file.exists():
            return ref_file

        # Not found — log at DEBUG (generate() logs the warning)
        logger.debug(
            "Reference audio not found: '%s'. "
            "Drop the file in REFERENCE_AUDIO_DIR to enable voice cloning.",
            ref_file,
        )
        return None

    @staticmethod
    def _model_cache_dir() -> Path:
        """Return the expected Coqui TTS model cache directory for XTTS v2.

        Coqui TTS stores models in an OS-specific location:
          Windows: %LOCALAPPDATA%\\tts\\
          Linux/macOS: ~/.local/share/tts/

        Returns:
            Path to the XTTS v2 model cache subdirectory.
        """
        # Windows: use LOCALAPPDATA env var
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data) / "tts"
        else:
            # Linux / macOS
            base = Path.home() / ".local" / "share" / "tts"

        return base / _MODEL_DIR_NAME

    @staticmethod
    def _read_audio_duration(audio_path: Path) -> float:
        """Read the actual duration of the generated WAV file.

        Uses soundfile for an exact sample count ÷ sample rate calculation.
        Falls back to a rough estimate if soundfile is unavailable.

        Args:
            audio_path: Path to the generated .wav file.

        Returns:
            Duration in seconds (minimum 0.1 seconds).
        """
        try:
            import soundfile as sf  # noqa: PLC0415
            info = sf.info(str(audio_path))
            return max(0.1, info.duration)
        except Exception:
            # soundfile not installed or file unreadable — rough estimate
            try:
                size_bytes = audio_path.stat().st_size
                # WAV at 24 kHz mono 16-bit ≈ 48000 bytes/second
                return max(0.1, size_bytes / 48_000)
            except Exception:
                return 1.0

    @classmethod
    def reset_model_cache(cls) -> None:
        """Unload the cached model and reset load state.

        Used in tests to force a fresh model load. Not called in production.
        Acquires the class-level lock before clearing.
        """
        with cls._model_lock:
            cls._model = None
            cls._model_load_attempted = False
            cls._model_load_error = None
        logger.debug("XTTS v2 model cache reset.")
