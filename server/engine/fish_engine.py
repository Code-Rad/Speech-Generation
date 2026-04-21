"""
fish_engine.py
VoiceForge — Fish Speech S2 Pro Engine (Phase 2 English Primary)

THE ENGLISH CROWN. Fish S2 Pro is the #1 ranked TTS model globally
on TTS-Arena2, trained on 10M+ hours of audio across 80+ languages.
For English news anchor speech, it is unmatched in naturalness and
prosody — indistinguishable from a real broadcast anchor at 44.1kHz.

HOW IT WORKS:
  1. fish-speech API server runs inside WSL2 Ubuntu on TRIJYA-7
     on port 8092 (set in config.py as FISH_PORT)
  2. WSL2 automatically bridges port 8092 to the Windows host
  3. Windows FastAPI (port 8000) calls WSL2 via http://localhost:8092
  4. This engine makes HTTP calls to the fish-speech /v1/tts endpoint

THE BROADCAST TAG:
  Fish S2 Pro supports inline style/emotion control via square-bracket
  tags embedded in the input text. For news anchor output, this engine
  automatically prepends:
      [professional broadcast tone]
  to every input before sending to the API. This single tag transforms
  Fish S2 Pro from a general TTS model into a broadcast-grade news
  anchor voice — no reference audio required for style control.

REQUIREMENTS:
  - WSL2 installed and Ubuntu running on TRIJYA-7
  - fish-speech installed inside WSL2 (run setup_fish_wsl2.sh once)
  - Fish server started: bash /mnt/c/VoiceForge/scripts/start_fish.sh
  - VOICEFORGE_PHASE=2 set in server/.env

TRADE-OFFS:
  + #1 global English TTS quality (TTS-Arena2 ranked)
  + [professional broadcast tone] tag = instant news anchor delivery
  + Zero-shot voice cloning — reference audio passed as base64 JSON
  + 44.1kHz output — highest sample rate of all VoiceForge engines
  - Requires WSL2 setup and manual server start
  - ~30s cold start while model loads into VRAM on first request
  - is_draft always False — this is the target quality for English

VRAM CO-EXISTENCE WITH VOXTRAL:
  Voxtral weights ≈ 8GB + Fish weights ≈ 8.8GB = ~17GB combined.
  Both scripts use --gpu-memory-utilization 0.5 (12GB each = 24GB).
  They co-exist on the RTX 4090. Different language requests route to
  different servers — no contention in normal use.

API:
  TTS generation: POST /v1/tts (JSON, references=[])
  Voice cloning:  POST /v1/tts (JSON, references=[{audio, text}])
  Health check:   GET  /v1/health
"""

from __future__ import annotations

import base64
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


class FishEngine(BaseTTSEngine):
    """Fish Speech S2 Pro Engine — English Primary (Phase 2).

    Connects to the fish-speech API server running inside WSL2 on
    TRIJYA-7 at port 8092. Automatically injects the broadcast tone
    tag into every request for professional news anchor delivery.

    is_draft: Always False — broadcast quality output.
    Cloning:  Zero-shot from 10-30 second reference WAV.

    To start:
        wsl
        bash /mnt/c/VoiceForge/scripts/start_fish.sh
    """

    # ── Broadcast tone tag ────────────────────────────────────────────────────
    # Prepended to all input text — transforms Fish S2 Pro into a
    # news anchor voice without any additional configuration.
    BROADCAST_TAG = "[professional broadcast tone] "

    # ── Abstract method implementations ───────────────────────────────────────

    def get_engine_type(self) -> EngineType:
        return EngineType.FISH_S2_PRO

    def get_supported_languages(self) -> List[Language]:
        # Fish S2 Pro supports 80+ languages — all three VoiceForge languages
        # English is Tier 1 (primary use case), Hindi is fully supported
        return [Language.ENGLISH, Language.HINDI, Language.HINGLISH]

    def supports_voice_cloning(self) -> bool:
        return True

    def is_available(self) -> bool:
        """Check if the fish-speech server is reachable on the configured port.

        Makes a fast TCP socket connection — no HTTP round-trip, no model load.
        Returns within 2 seconds in all cases. Never raises.

        Returns:
            True if fish-speech is accepting connections on FISH_HOST:FISH_PORT.
            False on timeout, connection refused, or any other error.
        """
        try:
            s = get_settings()
            host = s.FISH_HOST
            port = s.FISH_PORT

            with socket.create_connection((host, port), timeout=2.0):
                pass  # Connection accepted — server is listening

            logger.debug("Fish is_available: True (%s:%s reachable)", host, port)
            return True

        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            logger.debug(
                "Fish is_available: False (%s:%s unreachable: %s)",
                get_settings().FISH_HOST,
                get_settings().FISH_PORT,
                exc,
            )
            return False

        except Exception as exc:
            logger.debug("Fish is_available: False (unexpected error: %s)", exc)
            return False

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate speech using Fish S2 Pro via the fish-speech HTTP API.

        Automatically prepends [professional broadcast tone] to the input
        text before sending. If the voice profile has a reference audio
        file on disk, delegates to clone_voice() for voice matching.

        API call:
            POST http://localhost:8092/v1/tts
            Content-Type: application/json
            {
              "text": "[professional broadcast tone] <input text>",
              "format": "wav",
              "streaming": false,
              "references": [],
              "chunk_length": 200,
              "seed": null
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
                "Fish: reference audio found at '%s' — using voice cloning",
                ref_audio_path,
            )
            return self.clone_voice(request, ref_audio_path)

        # Inject broadcast tone tag
        prepared_text = self._prepare_text(request.text)

        logger.info(
            "Fish generate: profile=%s lang=%s text_len=%d (with broadcast tag)",
            request.voice_profile.profile_id,
            request.voice_profile.language.value,
            len(prepared_text),
        )

        payload = {
            "text": prepared_text,
            "format": request.output_format.value,
            "streaming": False,
            "references": [],       # No reference audio — preset voice
            "chunk_length": 200,    # Optimal chunk size for news anchor pacing
            "seed": None,
        }

        try:
            audio_bytes = self._post_json(
                endpoint="/v1/tts",
                payload=payload,
                timeout=s.FISH_TIMEOUT,
            )
        except EngineGenerationError as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=str(exc),
                generation_time_seconds=time.monotonic() - start_time,
            )
        except Exception as exc:
            logger.error("Fish generate unexpected error: %s", exc)
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Unexpected error: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        try:
            duration = self._save_audio_response(audio_bytes, request.output_path)
        except Exception as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Failed to save audio: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        generation_time = time.monotonic() - start_time
        logger.info(
            "Fish: generated %.1fs audio in %.2fs (is_draft=False)",
            duration, generation_time,
        )

        return GenerationResult(
            success=True,
            audio_path=request.output_path,
            duration_seconds=duration,
            engine_used=EngineType.FISH_S2_PRO,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=False,  # Broadcast quality — never True for Fish S2 Pro
            error_message="",
            generation_time_seconds=generation_time,
        )

    def clone_voice(
        self,
        request: GenerationRequest,
        reference_audio_path: str,
    ) -> GenerationResult:
        """Generate speech using zero-shot voice cloning from reference audio.

        Fish S2 Pro accepts reference audio as a base64-encoded WAV inline
        in the JSON request body — no multipart needed. The model extracts
        the speaker's voice characteristics and generates speech in that voice.

        API call:
            POST http://localhost:8092/v1/tts
            Content-Type: application/json
            {
              "text": "[professional broadcast tone] <text>",
              "format": "wav",
              "streaming": false,
              "references": [
                {
                  "audio": "<base64-encoded WAV bytes>",
                  "text": ""
                }
              ],
              "chunk_length": 200,
              "seed": null
            }

        Reference audio recommendations:
            Optimal: 10-30 seconds of clean speech
            Minimum: 3 seconds (quality degrades below this)
            Format: WAV, already validated by AudioValidator (P7)

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
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Reference audio not found: {reference_audio_path}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        # Inject broadcast tone tag into cloned voice too
        prepared_text = self._prepare_text(request.text)

        logger.info(
            "Fish clone_voice: profile=%s ref=%s text_len=%d",
            request.voice_profile.profile_id,
            ref_path.name,
            len(prepared_text),
        )

        # Encode reference audio as base64 for inline JSON embedding
        try:
            ref_bytes = ref_path.read_bytes()
            ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
        except OSError as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Could not read reference audio: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        payload = {
            "text": prepared_text,
            "format": request.output_format.value,
            "streaming": False,
            "references": [
                {
                    "audio": ref_b64,   # Base64-encoded WAV bytes
                    "text": "",         # Optional transcript — empty = auto-detect
                }
            ],
            "chunk_length": 200,
            "seed": None,
        }

        try:
            audio_bytes = self._post_json(
                endpoint="/v1/tts",
                payload=payload,
                timeout=s.FISH_TIMEOUT,
            )
        except EngineGenerationError as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
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
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Unexpected cloning error: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        try:
            duration = self._save_audio_response(audio_bytes, request.output_path)
        except Exception as exc:
            return GenerationResult(
                success=False,
                audio_path="",
                duration_seconds=0.0,
                engine_used=EngineType.FISH_S2_PRO,
                voice_profile_id=request.voice_profile.profile_id,
                language=request.voice_profile.language,
                is_draft=False,
                error_message=f"Failed to save cloned audio: {exc}",
                generation_time_seconds=time.monotonic() - start_time,
            )

        generation_time = time.monotonic() - start_time
        logger.info(
            "Fish clone_voice: %.1fs audio in %.2fs from '%s' (is_draft=False)",
            duration, generation_time, ref_path.name,
        )

        return GenerationResult(
            success=True,
            audio_path=request.output_path,
            duration_seconds=duration,
            engine_used=EngineType.FISH_S2_PRO,
            voice_profile_id=request.voice_profile.profile_id,
            language=request.voice_profile.language,
            is_draft=False,  # Cloned output is broadcast quality
            error_message="",
            generation_time_seconds=generation_time,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _prepare_text(self, text: str) -> str:
        """Prepend the broadcast tone tag to text if not already present.

        The [professional broadcast tone] tag instructs Fish S2 Pro to
        use news anchor delivery style — formal, clear, authoritative.
        Safe to call multiple times — never double-prepends.

        Args:
            text: Raw input text from the user.

        Returns:
            Text with broadcast tag prepended exactly once.
        """
        if text.startswith(self.BROADCAST_TAG):
            return text  # Already tagged — don't double-prepend
        return self.BROADCAST_TAG + text

    def _get_base_url(self) -> str:
        """Return the fish-speech API base URL from config.

        Returns:
            URL string like 'http://localhost:8092'
        """
        s = get_settings()
        return f"http://{s.FISH_HOST}:{s.FISH_PORT}"

    def _post_json(
        self,
        endpoint: str,
        payload: dict,
        timeout: int,
    ) -> bytes:
        """POST a JSON payload to the fish-speech API and return audio bytes.

        Args:
            endpoint: API path, e.g. '/v1/tts'
            payload: JSON-serialisable request body dict.
            timeout: Request timeout in seconds.

        Returns:
            Raw audio bytes from the response body.

        Raises:
            EngineGenerationError: On connection failure, non-200 status,
                or empty/truncated audio response.
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
                f"Could not connect to fish-speech at {url}. "
                f"Start the server: bash /mnt/c/VoiceForge/scripts/start_fish.sh "
                f"(run inside WSL2). Error: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise EngineGenerationError(
                f"fish-speech timed out after {timeout}s at {url}. "
                f"Model may still be loading (~30s cold start). Error: {exc}"
            ) from exc
        except Exception as exc:
            raise EngineGenerationError(
                f"HTTP request to fish-speech failed: {exc}"
            ) from exc

        if response.status_code != 200:
            detail = response.text[:500] if response.text else "(no detail)"
            raise EngineGenerationError(
                f"fish-speech returned HTTP {response.status_code} at {url}. "
                f"Detail: {detail}"
            )

        audio_bytes = response.content
        if not audio_bytes or len(audio_bytes) < 100:
            raise EngineGenerationError(
                f"fish-speech returned empty or truncated audio "
                f"({len(audio_bytes)} bytes). "
                f"Input text may be too short or the model may have failed."
            )

        return audio_bytes

    def _save_audio_response(
        self,
        audio_bytes: bytes,
        output_path: str,
    ) -> float:
        """Save raw audio bytes to output_path and return duration in seconds.

        Creates parent directory if missing.
        Uses soundfile for exact duration. Falls back to byte-size estimate
        if soundfile cannot parse the audio format.

        Args:
            audio_bytes: Raw WAV bytes from fish-speech (44.1kHz).
            output_path: Destination file path string.

        Returns:
            Duration of the audio in seconds (minimum 0.5).

        Raises:
            OSError: If the file cannot be written.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(audio_bytes)

        try:
            info = sf.info(str(out))
            return info.duration
        except Exception as exc:
            logger.warning(
                "soundfile could not read duration from '%s' (%s). "
                "Estimating from file size (44.1kHz 16-bit mono baseline).",
                output_path, exc,
            )
            # Fish outputs 44.1kHz 16-bit mono WAV ≈ 88 200 bytes/s
            return max(0.5, len(audio_bytes) / 88_200)

    def _find_reference_audio(self, request: GenerationRequest) -> str | None:
        """Return the reference audio path for a voice profile, or None.

        Checks REFERENCE_AUDIO_DIR (from config) for the profile's
        reference_audio_filename. Returns None if not found — caller
        then uses preset voice + broadcast tag instead.

        Args:
            request: GenerationRequest with voice_profile.

        Returns:
            Absolute path string to the reference WAV, or None.
        """
        try:
            s = get_settings()
            ref_dir = Path(s.REFERENCE_AUDIO_DIR)
            ref_filename = request.voice_profile.reference_audio_filename

            ref_path = ref_dir / ref_filename
            if ref_path.exists():
                return str(ref_path)

            # Fallback: resolve relative to server/ directory
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
# engine_factory.py imports FishEngine (this class name).
# P13 verification tests reference FishS2ProEngine (this alias).
# Both names point to the same class.
FishS2ProEngine = FishEngine
