"""
edge_engine.py
VoiceForge — Edge TTS Engine (Emergency Fallback)

THE EMERGENCY FALLBACK. Always available, no GPU needed, no TRIJYA-7 needed.
Uses Microsoft's Edge TTS cloud API via the edge-tts pip package.

TRADE-OFFS:
  + Always available — cloud API, requires only internet connectivity
  + Supports English and Hindi (voices configured via config.py / .env)
  - Draft quality only — not broadcast-grade; never the target output
  - No voice cloning — uses fixed Microsoft Neural voices per language/gender
  - Requires internet connectivity to Microsoft servers
  - GenerationResult.is_draft is always True

WHAT THIS FILE DOES:
  1. Maps voice profile (language + gender) → Microsoft Neural voice name
  2. Runs edge-tts async streaming synchronously via asyncio.run()
  3. Saves audio bytes to request.output_path
     - MP3 requested  → write raw edge-tts bytes directly (already MP3)
     - WAV requested  → convert MP3 → WAV via soundfile (if available)
  4. Returns GenerationResult with is_draft=True

NOTE: edge-tts always returns MP3 bytes. WAV conversion requires soundfile
      with libsndfile MP3 support (standard on Windows pip builds, libsndfile ≥ 1.1).
      If WAV conversion fails, the engine falls back to saving as MP3 and logs
      a warning — generation still succeeds.
"""

from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import time
from pathlib import Path
from typing import List

from engine.base_engine import (
    BaseTTSEngine,
    EngineGenerationError,
    EngineType,
    Gender,
    GenerationRequest,
    GenerationResult,
    Language,
    VoiceCloningNotSupportedError,
)
from config import get_settings

logger = logging.getLogger(__name__)


class EdgeTTSEngine(BaseTTSEngine):
    """Emergency fallback TTS engine using Microsoft Edge TTS cloud API.

    Always available (True from is_available()). No GPU needed.
    No voice cloning — raises VoiceCloningNotSupportedError if clone_voice() called.
    Returns is_draft=True in every GenerationResult to signal draft quality.

    Usage (via EngineFactory — never instantiate directly):
        engine = EngineFactory.get_engine(EngineType.EDGE_TTS)
        result = engine.generate(request)
        # result.is_draft == True always
    """

    # ── Abstract method implementations ───────────────────────────────────────

    def get_engine_type(self) -> EngineType:
        return EngineType.EDGE_TTS

    def get_supported_languages(self) -> List[Language]:
        # Hinglish uses English voices — the closest available option in Edge TTS.
        return [Language.ENGLISH, Language.HINDI, Language.HINGLISH]

    def supports_voice_cloning(self) -> bool:
        return False

    def is_available(self) -> bool:
        """Always returns True.

        Edge TTS is a cloud API — no local GPU, no model files, no inference
        server required. Actual availability depends on internet connectivity,
        but we never make a network call here (is_available() must be < 1 second).
        """
        return True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate speech using Edge TTS and save to request.output_path.

        Lazy-imports edge-tts inside this method (never at module level).
        Runs the async edge-tts streaming API synchronously via asyncio.run().

        Args:
            request: GenerationRequest with text, voice_profile, and output_path.

        Returns:
            GenerationResult with is_draft=True and full metadata.

        Raises:
            EngineGenerationError: If edge-tts import fails, the cloud API call
                fails, returns empty audio, or the output file cannot be written.
        """
        self.validate_request(request)

        start_time = time.monotonic()
        voice_name = self._pick_voice(request)

        # Lazy import — edge-tts not imported at module level to avoid
        # crashing the server if the package is not installed
        try:
            import edge_tts  # noqa: PLC0415
        except ImportError as exc:
            raise EngineGenerationError(
                f"edge-tts library not installed. "
                f"Run: pip install edge-tts\n"
                f"Original error: {exc}"
            ) from exc

        # ── Step 1: Stream audio bytes from Edge TTS cloud API ─────────────────
        logger.debug(
            "Edge TTS request: voice=%s, text_length=%d chars",
            voice_name, len(request.text),
        )
        try:
            audio_bytes = asyncio.run(
                self._async_stream_audio(edge_tts, request.text, voice_name)
            )
        except EngineGenerationError:
            raise
        except Exception as exc:
            raise EngineGenerationError(
                f"Edge TTS cloud API call failed (voice='{voice_name}'): {exc}"
            ) from exc

        # ── Step 2: Write audio to output_path ─────────────────────────────────
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            actual_path = self._save_audio(
                audio_bytes, output_path, request.output_format.value
            )
        except EngineGenerationError:
            raise
        except Exception as exc:
            raise EngineGenerationError(
                f"Failed to save Edge TTS audio to '{request.output_path}': {exc}"
            ) from exc

        generation_time = time.monotonic() - start_time
        duration_estimate = self._estimate_duration_seconds(request.text)

        logger.info(
            "Edge TTS: generated audio at '%s' (voice=%s, time=%.2fs, draft=True)",
            actual_path, voice_name, generation_time,
        )

        return GenerationResult(
            success=True,
            audio_path=actual_path,
            duration_seconds=duration_estimate,
            engine_used=EngineType.EDGE_TTS,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=True,  # Always True — Edge TTS is emergency-quality only
            error_message="",
            generation_time_seconds=generation_time,
        )

    def clone_voice(
        self,
        request: GenerationRequest,
        reference_audio_path: str,
    ) -> GenerationResult:
        """Always raises — Edge TTS has no voice cloning capability.

        Raises:
            VoiceCloningNotSupportedError: Always. Route to XTTS v2, Voxtral,
                or Fish S2 Pro for voice cloning.
        """
        raise VoiceCloningNotSupportedError(
            "Edge TTS engine does not support voice cloning. "
            "Voice cloning requires XTTS v2, Voxtral TTS, or Fish Speech S2 Pro. "
            "Set require_cloning=True in get_engine_for_request() to skip Edge TTS."
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _pick_voice(self, request: GenerationRequest) -> str:
        """Return the Microsoft Neural voice identifier for this request.

        Voice names come from config.py settings (read from .env / env vars).
        Hinglish requests use the English voice (no dedicated Hinglish voices
        exist in the Microsoft Neural voice library).

        Args:
            request: The GenerationRequest with voice_profile.

        Returns:
            A Microsoft Neural voice name string (e.g. "en-US-GuyNeural").
        """
        s = get_settings()
        lang = request.voice_profile.language
        gender = request.voice_profile.gender

        if lang in (Language.ENGLISH, Language.HINGLISH):
            # Hinglish uses English voices — closest available option
            if lang == Language.HINGLISH:
                logger.debug(
                    "Hinglish request routed to English voice in Edge TTS "
                    "(no dedicated Hinglish voices available)."
                )
            return (
                s.EDGE_TTS_VOICE_EN_FEMALE
                if gender == Gender.FEMALE
                else s.EDGE_TTS_VOICE_EN_MALE
            )
        elif lang == Language.HINDI:
            return (
                s.EDGE_TTS_VOICE_HI_FEMALE
                if gender == Gender.FEMALE
                else s.EDGE_TTS_VOICE_HI_MALE
            )
        else:
            # Defensive fallback — should not reach here after validate_request()
            logger.warning(
                "Edge TTS: unknown language '%s' — falling back to English male voice.",
                lang.value,
            )
            return s.EDGE_TTS_VOICE_EN_MALE

    @staticmethod
    async def _async_stream_audio(
        edge_tts_module,
        text: str,
        voice: str,
    ) -> bytes:
        """Async helper — streams Edge TTS audio and collects it as bytes.

        edge-tts yields audio in chunks; we collect all chunks and join them
        into a single MP3 bytes object.

        Args:
            edge_tts_module: The imported edge_tts module.
            text: The text to synthesise.
            voice: Microsoft Neural voice name.

        Returns:
            Raw MP3 audio bytes.

        Raises:
            EngineGenerationError: If the stream yields no audio data.
        """
        communicate = edge_tts_module.Communicate(text, voice)
        audio_chunks: List[bytes] = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        if not audio_chunks:
            raise EngineGenerationError(
                f"Edge TTS returned no audio data (voice='{voice}'). "
                f"The text may be empty, or the voice name may be invalid."
            )

        return b"".join(audio_chunks)

    @staticmethod
    def _save_audio(mp3_bytes: bytes, output_path: Path, fmt: str) -> str:
        """Write MP3 bytes to output_path, converting to WAV if requested.

        edge-tts always returns MP3. For WAV output we convert via soundfile.
        If WAV conversion fails (soundfile not installed or no MP3 codec),
        we fall back to writing MP3 to the path and log a warning — generation
        still succeeds, just with a different format than requested.

        Args:
            mp3_bytes: Raw MP3 bytes from edge-tts.
            output_path: Destination Path object (may have .wav or .mp3 suffix).
            fmt: Requested format string — "wav" or "mp3".

        Returns:
            String path of the file that was actually written.
        """
        if fmt == "mp3":
            # MP3 requested — write bytes directly
            output_path.write_bytes(mp3_bytes)
            return str(output_path)

        # WAV requested — attempt MP3 → WAV conversion via soundfile
        try:
            import soundfile as sf  # noqa: PLC0415

            mp3_buffer = io.BytesIO(mp3_bytes)
            audio_data, sample_rate = sf.read(mp3_buffer)
            sf.write(str(output_path), audio_data, sample_rate)
            return str(output_path)

        except ImportError:
            # soundfile not installed — save as MP3 with warning
            mp3_fallback = output_path.with_suffix(".mp3")
            mp3_fallback.write_bytes(mp3_bytes)
            logger.warning(
                "soundfile not installed — Edge TTS saved as MP3 instead of WAV: %s. "
                "Run: pip install soundfile",
                mp3_fallback,
            )
            return str(mp3_fallback)

        except Exception as exc:
            # Conversion failed (e.g. libsndfile lacks MP3 codec) — save as MP3
            mp3_fallback = output_path.with_suffix(".mp3")
            mp3_fallback.write_bytes(mp3_bytes)
            logger.warning(
                "WAV conversion failed (%s) — Edge TTS saved as MP3: %s",
                exc, mp3_fallback,
            )
            return str(mp3_fallback)

    @staticmethod
    def _estimate_duration_seconds(text: str) -> float:
        """Rough estimate of audio duration from word count.

        Not used for any business logic — informational only.
        Assumes average news-anchor speaking rate of ~160 words/minute.

        Args:
            text: The synthesised text.

        Returns:
            Estimated duration in seconds (minimum 0.5 seconds).
        """
        word_count = len(text.split())
        words_per_second = 160 / 60  # ≈ 2.67 words/second
        return max(0.5, word_count / words_per_second)
