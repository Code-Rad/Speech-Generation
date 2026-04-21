"""
voxtral_engine.py
VoiceForge — Voxtral TTS Engine (Phase 2 Hindi/Hinglish Primary)

THE HINDI POWERHOUSE. Mistral's Voxtral-4B-TTS-2603 served via vLLM-Omni
inside WSL2 on TRIJYA-7. Best Hindi quality of any open-source TTS model —
~80% human preference win rate vs ElevenLabs for Hindi content.

HOW IT WORKS:
  1. vLLM-Omni runs inside WSL2 Ubuntu on TRIJYA-7 — port 8091
  2. WSL2 automatically bridges its ports to the Windows host
  3. Windows FastAPI (port 8000) calls WSL2 via http://localhost:8091
  4. This engine makes HTTP calls to vLLM-Omni's OpenAI-compatible TTS endpoint

REQUIREMENTS:
  - WSL2 installed and Ubuntu running on TRIJYA-7
  - vLLM-Omni installed inside WSL2 (run setup_voxtral_wsl2.sh once)
  - Voxtral server started: bash /mnt/c/VoiceForge/scripts/start_voxtral.sh
  - VOICEFORGE_PHASE=2 set in server/.env

TRADE-OFFS:
  + Broadcast-quality Hindi and Hinglish output
  + Zero-shot voice cloning from 3-second reference audio
  + 4.1B parameter model on RTX 4090 — runs well under 24GB VRAM
  - Requires WSL2 setup and manual server start
  - First generation has ~30s cold start while model loads into VRAM
  - is_draft always False — this is the target quality level

API:
  Standard generation: POST /v1/audio/speech (JSON)
  Voice cloning:       POST /v1/audio/speech (multipart/form-data)
  Health check:        GET  /health or GET /v1/models
"""

from __future__ import annotations

import logging
import socket
import time
from pathlib import Path
from typing import List

import httpx
import soundfile as sf

from engine.base_engine import (
    BaseTTSEngine,
    EngineGenerationError,
    EngineType,
    Gender,
    GenerationRequest,
    GenerationResult,
    Language,
    VoiceCloningNotSupportedError,
    UnsupportedLanguageError,
)
from config import get_settings

logger = logging.getLogger(__name__)


class VoxtralEngine(BaseTTSEngine):
    """Voxtral TTS Engine — Hindi/Hinglish Primary (Phase 2).

    Serves Mistral's Voxtral-4B-TTS-2603 via vLLM-Omni running inside
    WSL2 on TRIJYA-7. Calls the vLLM-Omni HTTP API on port 8091.

    is_draft: Always False — broadcast quality output.
    Cloning:  Zero-shot from 3-second+ reference WAV.

    To start:
        wsl
        bash /mnt/c/VoiceForge/scripts/start_voxtral.sh
    """

    # ── Preset voice names understood by vLLM-Omni Voxtral ───────────────────
    # Map (language, gender) → vLLM-Omni preset voice name.
    # These are built-in voices used when no reference audio is available.
    PRESET_VOICES = {
        (Language.HINDI,    Gender.MALE):    "formal_male",
        (Language.HINDI,    Gender.FEMALE):  "formal_female",
        (Language.HINGLISH, Gender.MALE):    "formal_male",
        (Language.HINGLISH, Gender.FEMALE):  "formal_female",
        (Language.ENGLISH,  Gender.MALE):    "casual_male",
        (Language.ENGLISH,  Gender.FEMALE):  "casual_female",
    }

    # Map Language enum → language string Voxtral understands
    LANGUAGE_MAP = {
        Language.ENGLISH:  "English",
        Language.HINDI:    "Hindi",
        Language.HINGLISH: "Hindi",   # Hinglish uses Hindi language model
    }

    # ── Abstract method implementations ───────────────────────────────────────

    def get_engine_type(self) -> EngineType:
        return EngineType.VOXTRAL_TTS

    def get_supported_languages(self) -> List[Language]:
        return [Language.ENGLISH, Language.HINDI, Language.HINGLISH]

    def supports_voice_cloning(self) -> bool:
        return True

    def is_available(self) -> bool:
        """Check if vLLM-Omni is reachable on the configured host:port.

        Makes a fast TCP socket connection attempt — does NOT make an HTTP
        request or load any model. Returns within 2 seconds in all cases.

        Returns:
            True if vLLM-Omni is accepting connections on VOXTRAL_HOST:VOXTRAL_PORT.
            False on any error — network timeout, connection refused, etc.
            Never raises.
        """
        try:
            s = get_settings()
            host = s.VOXTRAL_HOST
            port = s.VOXTRAL_PORT

            # Fast TCP connect — much faster than an HTTP round-trip
            with socket.create_connection((host, port), timeout=2.0):
                pass  # Connection succeeded — server is listening

            logger.debug("Voxtral is_available: True (%s:%s reachable)", host, port)
            return True

        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            logger.debug(
                "Voxtral is_available: False (%s:%s unreachable: %s)",
                get_settings().VOXTRAL_HOST,
                get_settings().VOXTRAL_PORT,
                exc,
            )
            return False

        except Exception as exc:
            # Catch-all — is_available() must never raise
            logger.debug("Voxtral is_available: False (unexpected error: %s)", exc)
            return False

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate speech using Voxtral TTS via vLLM-Omni API.

        Uses preset voice for the language/gender combination. If the voice
        profile has a reference audio file on disk, delegates to clone_voice()
        instead for better voice matching.

        API call:
            POST http://localhost:8091/v1/audio/speech
            Content-Type: application/json
            {
              "model": "mistralai/Voxtral-4B-TTS-2603",
              "input": "<text>",
              "voice": "formal_male",
              "response_format": "wav",
              "language": "Hindi",
              "speed": 1.0
            }

        Returns:
            GenerationResult with success=True and is_draft=False.
            On any error returns GenerationResult with success=False
            and error_message filled in — never raises.
        """
        self.validate_request(request)
        start_time = time.monotonic()
        s = get_settings()

        # If reference audio exists for this profile, use voice cloning
        ref_audio_path = self._find_reference_audio(request)
        if ref_audio_path:
            logger.info(
                "Voxtral: reference audio found at '%s' — using voice cloning",
                ref_audio_path,
            )
            return self.clone_voice(request, ref_audio_path)

        # No reference audio — use preset voice
        preset_voice = self.PRESET_VOICES.get(
            (request.voice_profile.language, request.voice_profile.gender),
            "formal_male",
        )
        language_str = self.LANGUAGE_MAP.get(
            request.voice_profile.language, "Hindi"
        )

        logger.info(
            "Voxtral generate: profile=%s lang=%s voice=%s text_len=%d",
            request.voice_profile.profile_id,
            language_str,
            preset_voice,
            len(request.text),
        )

        payload = {
            "model": s.VOXTRAL_MODEL,
            "input": request.text,
            "voice": preset_voice,
            "response_format": request.output_format.value,
            "language": language_str,
            "speed": request.voice_profile.speaking_rate,
        }

        try:
            audio_bytes = self._post_json(
                endpoint="/v1/audio/speech",
                payload=payload,
                timeout=s.VOXTRAL_TIMEOUT,
            )
        except EngineGenerationError as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=str(exc),
                generation_time_seconds=time.monotonic() - start_time,
            )
        except Exception as exc:
            logger.error("Voxtral generate unexpected error: %s", exc)
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Unexpected error: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        # Save audio and compute duration
        try:
            duration = self._save_audio_response(audio_bytes, request.output_path)
        except Exception as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Failed to save audio: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        generation_time = time.monotonic() - start_time
        logger.info(
            "Voxtral: generated %.1fs audio in %.2fs (is_draft=False)",
            duration, generation_time,
        )

        return GenerationResult(
            success=True,
            audio_path=request.output_path,
            duration_seconds=duration,
            engine_used=EngineType.VOXTRAL_TTS,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=False,  # Broadcast quality — never True for Voxtral
            error_message="",
            generation_time_seconds=generation_time,
        )

    def clone_voice(
        self,
        request: GenerationRequest,
        reference_audio_path: str,
    ) -> GenerationResult:
        """Generate speech using zero-shot voice cloning from reference audio.

        Sends the reference WAV file alongside the text to vLLM-Omni.
        Voxtral extracts the voice characteristics and generates speech
        with that voice identity — no prior training required.

        API call:
            POST http://localhost:8091/v1/audio/speech
            Content-Type: multipart/form-data
            Fields:
              model:            mistralai/Voxtral-4B-TTS-2603
              input:            <text to speak>
              response_format:  wav
              language:         Hindi
              speed:            1.0
              reference_audio:  <WAV file binary>

        Reference audio requirements (enforced by AudioValidator in P7):
            Duration: 3-25 seconds (minimum 3s for zero-shot cloning)
            Format: WAV, clean speech, no background noise

        Returns:
            GenerationResult with success=True and is_draft=False.
        """
        self.validate_request(request)
        start_time = time.monotonic()
        s = get_settings()

        ref_path = Path(reference_audio_path)
        if not ref_path.exists():
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Reference audio not found: {reference_audio_path}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        language_str = self.LANGUAGE_MAP.get(
            request.voice_profile.language, "Hindi"
        )

        logger.info(
            "Voxtral clone_voice: profile=%s lang=%s ref=%s text_len=%d",
            request.voice_profile.profile_id,
            language_str,
            ref_path.name,
            len(request.text),
        )

        try:
            audio_bytes = self._post_multipart_clone(
                text=request.text,
                model=s.VOXTRAL_MODEL,
                response_format=request.output_format.value,
                language=language_str,
                reference_audio_path=ref_path,
                speaking_rate=request.voice_profile.speaking_rate,
                timeout=s.VOXTRAL_TIMEOUT,
            )
        except EngineGenerationError as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Voice cloning failed: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )
        except Exception as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Unexpected cloning error: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        # Save audio and compute duration
        try:
            duration = self._save_audio_response(audio_bytes, request.output_path)
        except Exception as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.VOXTRAL_TTS,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Failed to save cloned audio: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        generation_time = time.monotonic() - start_time
        logger.info(
            "Voxtral clone_voice: %.1fs audio in %.2fs from '%s' (is_draft=False)",
            duration, generation_time, ref_path.name,
        )

        return GenerationResult(
            success=True,
            audio_path=request.output_path,
            duration_seconds=duration,
            engine_used=EngineType.VOXTRAL_TTS,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=False,  # Cloned output is broadcast quality — never True
            error_message="",
            generation_time_seconds=generation_time,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_base_url(self) -> str:
        """Return the vLLM-Omni base URL from config.

        Returns:
            URL string like 'http://localhost:8091'
        """
        s = get_settings()
        return f"http://{s.VOXTRAL_HOST}:{s.VOXTRAL_PORT}"

    def _post_json(
        self,
        endpoint: str,
        payload: dict,
        timeout: int,
    ) -> bytes:
        """POST a JSON payload to vLLM-Omni and return the raw audio bytes.

        Args:
            endpoint: API path, e.g. '/v1/audio/speech'
            payload: JSON-serialisable dict.
            timeout: Request timeout in seconds.

        Returns:
            Raw audio bytes from the response body.

        Raises:
            EngineGenerationError: On connection failure, non-200 status,
                or empty audio response.
        """
        url = self._get_base_url() + endpoint

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers={"Accept": "audio/wav, audio/mpeg, */*"},
                )
        except httpx.ConnectError as exc:
            raise EngineGenerationError(
                f"Could not connect to vLLM-Omni at {url}. "
                f"Start the server: bash /mnt/c/VoiceForge/scripts/start_voxtral.sh "
                f"(run inside WSL2). Error: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EngineGenerationError(
                f"vLLM-Omni timed out after {timeout}s at {url}. "
                f"Model may still be loading (allow ~30s cold start). Error: {exc}"
            ) from exc
        except Exception as exc:
            raise EngineGenerationError(
                f"HTTP request to vLLM-Omni failed: {exc}"
            ) from exc

        if response.status_code != 200:
            detail = response.text[:500] if response.text else "(no detail)"
            raise EngineGenerationError(
                f"vLLM-Omni returned HTTP {response.status_code} at {url}. "
                f"Detail: {detail}"
            )

        audio_bytes = response.content
        if not audio_bytes or len(audio_bytes) < 100:
            raise EngineGenerationError(
                f"vLLM-Omni returned empty or truncated audio "
                f"({len(audio_bytes)} bytes). "
                f"Input text may be too short, or the model may have failed."
            )

        return audio_bytes

    def _post_multipart_clone(
        self,
        text: str,
        model: str,
        response_format: str,
        language: str,
        reference_audio_path: Path,
        speaking_rate: float,
        timeout: int,
    ) -> bytes:
        """POST multipart form-data with reference audio for voice cloning.

        Sends text fields + reference WAV binary to vLLM-Omni.
        vLLM-Omni performs zero-shot speaker adaptation from the reference.

        Args:
            text: Text to synthesise.
            model: Model identifier string.
            response_format: 'wav' or 'mp3'.
            language: Language string ('Hindi', 'English', etc.).
            reference_audio_path: Path to reference WAV file (must exist).
            speaking_rate: Speed multiplier (1.0 = normal).
            timeout: Request timeout in seconds.

        Returns:
            Raw audio bytes.

        Raises:
            EngineGenerationError: On connection error, non-200 response,
                file read error, or empty audio.
        """
        url = self._get_base_url() + "/v1/audio/speech"

        try:
            ref_bytes = reference_audio_path.read_bytes()
        except OSError as exc:
            raise EngineGenerationError(
                f"Could not read reference audio '{reference_audio_path}': {exc}"
            ) from exc

        files = {
            "reference_audio": (
                reference_audio_path.name,
                ref_bytes,
                "audio/wav",
            ),
        }
        data = {
            "model": model,
            "input": text,
            "response_format": response_format,
            "language": language,
            "speed": str(speaking_rate),
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, data=data, files=files)
        except httpx.ConnectError as exc:
            raise EngineGenerationError(
                f"Could not connect to vLLM-Omni at {url} for voice cloning. "
                f"Start the server in WSL2 first. Error: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EngineGenerationError(
                f"Voice cloning request timed out after {timeout}s. "
                f"Model may still be loading. Error: {exc}"
            ) from exc
        except Exception as exc:
            raise EngineGenerationError(
                f"Multipart clone request to vLLM-Omni failed: {exc}"
            ) from exc

        if response.status_code != 200:
            detail = response.text[:500] if response.text else "(no detail)"
            raise EngineGenerationError(
                f"vLLM-Omni clone returned HTTP {response.status_code}. "
                f"Detail: {detail}"
            )

        audio_bytes = response.content
        if not audio_bytes or len(audio_bytes) < 100:
            raise EngineGenerationError(
                f"vLLM-Omni clone returned empty audio ({len(audio_bytes)} bytes). "
                f"Reference audio may be too short (minimum 3 seconds required)."
            )

        return audio_bytes

    def _save_audio_response(
        self,
        audio_bytes: bytes,
        output_path: str,
    ) -> float:
        """Save raw audio bytes to output_path and return duration in seconds.

        Creates parent directory if missing.
        Uses soundfile to compute exact duration from the saved file.
        Falls back to byte-size estimate if soundfile cannot parse the audio.

        Args:
            audio_bytes: Raw audio bytes from vLLM-Omni.
            output_path: Destination file path string.

        Returns:
            Duration of the audio in seconds (minimum 0.5).

        Raises:
            OSError: If the file cannot be written.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(audio_bytes)

        # Compute exact duration using soundfile
        try:
            info = sf.info(str(out))
            return info.duration
        except Exception as exc:
            logger.warning(
                "soundfile could not read duration from '%s' (%s). "
                "Estimating from file size (24kHz 16-bit mono baseline).",
                output_path, exc,
            )
            # Rough estimate: 24kHz 16-bit mono WAV ≈ 48 000 bytes/s
            return max(0.5, len(audio_bytes) / 48_000)

    def _find_reference_audio(self, request: GenerationRequest) -> str | None:
        """Return the reference audio path for a voice profile, or None.

        Checks REFERENCE_AUDIO_DIR (from config) for the profile's
        reference_audio_filename. Returns None if not found — caller
        then uses preset voice instead.

        Args:
            request: GenerationRequest with voice_profile.

        Returns:
            Absolute path string to the reference WAV, or None.
        """
        try:
            s = get_settings()
            ref_dir = Path(s.REFERENCE_AUDIO_DIR)
            ref_filename = request.voice_profile.reference_audio_filename

            # Primary path from config
            ref_path = ref_dir / ref_filename
            if ref_path.exists():
                return str(ref_path)

            # Fallback: relative to server/ directory
            alt_path = Path("server") / "reference_audio" / ref_filename
            if alt_path.exists():
                return str(alt_path)

            return None

        except Exception as exc:
            logger.debug(
                "Could not resolve reference audio for '%s': %s",
                request.voice_profile.profile_id, exc,
            )
            return None


# ── Alias ──────────────────────────────────────────────────────────────────────
# engine_factory.py imports VoxtralEngine (this class name).
# P12 verification tests reference VoxtralTTSEngine (this alias).
# Both names point to the same class — no duplication.
VoxtralTTSEngine = VoxtralEngine
