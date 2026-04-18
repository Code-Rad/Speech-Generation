"""
base_engine.py
VoiceForge — Abstract TTS Engine Interface

THE LEGO SOCKET. Every TTS engine must implement BaseTTSEngine.
This file defines the contract. The factory and API layer only ever
talk to this interface — never to concrete implementations directly.

Contents:
  - 5 custom exceptions (typed, independently catchable)
  - 4 enums: EngineType, Language, Gender, OutputFormat
  - 3 data models: VoiceProfile, GenerationRequest, GenerationResult
  - BaseTTSEngine abstract base class (6 abstract + 2 concrete methods)

If this interface changes, ALL engines must be updated. Change carefully.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List


# ── Custom Exceptions ─────────────────────────────────────────────────────────
# Each exception is separate so callers can catch exactly what they need:
#   EngineNotAvailableError  → try next engine in fallback chain
#   EngineGenerationError    → engine was up but request itself failed
#   VoiceCloningNotSupported → don't retry with same engine, try a cloning one
#   InvalidVoiceProfileError → bad config data, fail fast, don't retry
#   UnsupportedLanguageError → wrong engine for this language, route elsewhere

class EngineNotAvailableError(Exception):
    """Raised when an engine is configured but not reachable.

    Examples:
        - TRIJYA-7 is offline (Tailscale disconnected)
        - vLLM-Omni server not started in WSL2
        - SGLang server crashed
        - Engine module is still a placeholder (not yet built)
    """


class EngineGenerationError(Exception):
    """Raised when an engine is available but generation fails.

    Examples:
        - Model loaded but the input text caused an inference error
        - Output file could not be written to disk
        - Audio encoding failed
    """


class VoiceCloningNotSupportedError(Exception):
    """Raised when clone_voice() is called on an engine that does not
    support voice cloning.

    Edge TTS is the only engine that returns False for supports_voice_cloning().
    All other engines (XTTS v2, Voxtral, Fish S2 Pro) support cloning.
    """


class InvalidVoiceProfileError(Exception):
    """Raised when a voice profile JSON file is missing required fields,
    has wrong types, or contains invalid enum values.

    Fail fast — don't attempt generation with a broken profile.
    """


class UnsupportedLanguageError(Exception):
    """Raised when an engine does not support the requested language.

    Example: Edge TTS receiving a language code it has no voice for.
    The factory handles this at routing time via get_supported_languages().
    """


# ── Enums ─────────────────────────────────────────────────────────────────────
# All enums inherit from str so they serialise to JSON naturally
# and compare equal to their string values (e.g. EngineType.EDGE_TTS == "edge_tts")

class EngineType(str, Enum):
    """Identifies which TTS engine is in use.
    Values must match the strings in voice profile JSON engine_preference lists
    and in config.py ENGINE_* settings.
    """
    EDGE_TTS    = "edge_tts"
    XTTS_V2     = "xtts_v2"
    VOXTRAL_TTS = "voxtral_tts"
    FISH_S2_PRO = "fish_s2_pro"


class Language(str, Enum):
    """Supported language codes.
    User selects ONE language before generation — the entire speech stays
    in that language. No mid-speech switching. Ever.
    """
    ENGLISH  = "en"
    HINDI    = "hi"
    HINGLISH = "hinglish"


class Gender(str, Enum):
    """Voice gender for anchor profiles."""
    MALE   = "male"
    FEMALE = "female"


class OutputFormat(str, Enum):
    """Audio output format.
    WAV is lossless — preferred for post-processing pipeline (P7).
    MP3 is for delivery. Conversion handled in audio post-processing.
    """
    WAV = "wav"
    MP3 = "mp3"


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class VoiceProfile:
    """A named anchor voice profile loaded from server/voice_profiles/*.json.

    Represents a configured voice identity (e.g. "anchor_male_en") with its
    preferred engine chain, reference audio filename, and speaking metadata.

    Use VoiceProfile.from_json_file() to load — never construct manually
    in production code (always validate from a JSON file).
    """
    profile_id: str
    display_name: str
    language: Language
    gender: Gender
    engine_preference: List[EngineType]
    reference_audio_filename: str
    speaking_rate: float = 1.0
    style: str = "professional_news"
    description: str = ""
    phase_available: int = 1
    cloning_enabled: bool = True
    notes: str = ""

    @classmethod
    def from_json_file(cls, filepath: str) -> "VoiceProfile":
        """Load and validate a voice profile from a JSON file.

        Args:
            filepath: Path to the .json profile file (absolute or relative
                      to the CWD of the caller).

        Returns:
            A fully validated VoiceProfile instance.

        Raises:
            InvalidVoiceProfileError: If the file is missing, unparseable,
                has missing required fields, or contains invalid enum values.
        """
        _REQUIRED = [
            "profile_id",
            "display_name",
            "language",
            "gender",
            "engine_preference",
            "reference_audio_filename",
        ]

        # Load JSON
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            raise InvalidVoiceProfileError(
                f"Voice profile file not found: {filepath}"
            )
        except json.JSONDecodeError as exc:
            raise InvalidVoiceProfileError(
                f"Invalid JSON in voice profile '{filepath}': {exc}"
            )

        # Check required keys
        missing = [k for k in _REQUIRED if k not in data]
        if missing:
            raise InvalidVoiceProfileError(
                f"Voice profile '{filepath}' is missing required fields: "
                f"{missing}"
            )

        # Validate and coerce enums
        try:
            language = Language(data["language"])
        except ValueError:
            raise InvalidVoiceProfileError(
                f"Invalid language '{data['language']}' in '{filepath}'. "
                f"Valid values: {[lang.value for lang in Language]}"
            )

        try:
            gender = Gender(data["gender"])
        except ValueError:
            raise InvalidVoiceProfileError(
                f"Invalid gender '{data['gender']}' in '{filepath}'. "
                f"Valid values: {[g.value for g in Gender]}"
            )

        try:
            engine_preference = [
                EngineType(e) for e in data["engine_preference"]
            ]
        except ValueError as exc:
            raise InvalidVoiceProfileError(
                f"Invalid engine type in engine_preference in '{filepath}': "
                f"{exc}. Valid values: {[t.value for t in EngineType]}"
            )

        return cls(
            profile_id=str(data["profile_id"]),
            display_name=str(data["display_name"]),
            language=language,
            gender=gender,
            engine_preference=engine_preference,
            reference_audio_filename=str(data["reference_audio_filename"]),
            speaking_rate=float(data.get("speaking_rate", 1.0)),
            style=str(data.get("style", "professional_news")),
            description=str(data.get("description", "")),
            phase_available=int(data.get("phase_available", 1)),
            cloning_enabled=bool(data.get("cloning_enabled", True)),
            notes=str(data.get("notes", "")),
        )


@dataclass
class GenerationRequest:
    """Everything needed to generate one audio segment.

    Built by the API route handler (P5) and passed to the engine.
    The engine writes audio to output_path and returns a GenerationResult.
    """
    text: str
    voice_profile: VoiceProfile
    output_path: str
    output_format: OutputFormat = OutputFormat.WAV


@dataclass
class GenerationResult:
    """The complete outcome of a generation attempt.

    Returned by every engine after generate() or clone_voice().
    The API route handler (P5) serialises this to JSON for the client.
    """
    success: bool
    audio_path: str
    duration_seconds: float
    engine_used: EngineType
    voice_profile_id: str
    language: Language
    is_draft: bool                  # True when Edge TTS was used (emergency)
    error_message: str              # Empty string on success
    generation_time_seconds: float


# ── Abstract Base Class ────────────────────────────────────────────────────────

class BaseTTSEngine(ABC):
    """Abstract base class that every TTS engine must implement.

    This is the Lego socket — all 4 engines are interchangeable because
    they all honour this interface. The factory (engine_factory.py) and
    API routes (main.py) only ever talk to BaseTTSEngine.

    Implementation rules for concrete subclasses:
      1. is_available() must be FAST and synchronous — no network calls,
         no model loads. Return False on any error, never raise.
      2. generate() writes audio to request.output_path before returning.
      3. clone_voice() raises VoiceCloningNotSupportedError if unsupported.
      4. Never import TTS library at module level — always import inside
         methods to prevent startup failures when libraries not installed.
      5. Use validate_request() at the top of generate() and clone_voice().
    """

    # ── Abstract methods (every engine must implement these) ──────────────────

    @abstractmethod
    def get_engine_type(self) -> EngineType:
        """Return the EngineType enum value that identifies this engine."""

    @abstractmethod
    def get_supported_languages(self) -> List[Language]:
        """Return the list of Language values this engine can generate.

        The factory uses this to verify engine-language compatibility before
        routing a request. Always return a non-empty list.
        """

    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """Return True if this engine supports voice cloning.

        Edge TTS: returns False (no cloning, no custom voices).
        XTTS v2:  returns True (clones from .wav reference file).
        Voxtral:  returns True (clones from .wav reference file).
        Fish S2:  returns True (clones from .wav reference file).
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this engine is ready to generate audio right now.

        CRITICAL CONSTRAINTS — violating these breaks the routing chain:
          - Must complete in under 1 second
          - Must NOT make network calls or load ML models
          - Must NOT raise exceptions — catch all errors and return False

        Engine-specific availability signals:
          Edge TTS:    Always True (cloud API, no local GPU needed)
          XTTS v2:     Check that model cache directory exists locally
          Voxtral TTS: Light TCP connect check to VOXTRAL_HOST:VOXTRAL_PORT
          Fish S2 Pro: Light TCP connect check to FISH_HOST:FISH_PORT
        """

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate speech from text and save audio to request.output_path.

        Args:
            request: A GenerationRequest with text, voice profile, and path.

        Returns:
            GenerationResult with success=True and full metadata.
            The audio file at request.output_path must exist after this call.

        Raises:
            EngineGenerationError: If generation fails for any reason.
                Do NOT let other exception types propagate — wrap them.
        """

    @abstractmethod
    def clone_voice(
        self,
        request: GenerationRequest,
        reference_audio_path: str,
    ) -> GenerationResult:
        """Generate speech using a voice cloned from a reference audio file.

        Args:
            request: A GenerationRequest with text, voice profile, and path.
            reference_audio_path: Absolute path to a .wav reference clip.
                Requirements: 10–25 seconds, clean speech, no background
                noise, no music, broadcast quality.

        Returns:
            GenerationResult with success=True and full metadata.

        Raises:
            VoiceCloningNotSupportedError: If this engine does not support
                voice cloning (Edge TTS). Caller should route to a different
                engine.
            EngineGenerationError: If cloning or generation fails.
        """

    # ── Concrete methods (implemented here, usable by all engines) ────────────

    def get_engine_info(self) -> dict:
        """Return engine metadata as a dict for the /engines API endpoint.

        Catches all exceptions from is_available() — this method must never
        crash, even if the engine implementation has a bug.

        Returns:
            dict with keys: engine_type, supported_languages,
            supports_cloning, is_available
        """
        try:
            available = self.is_available()
        except Exception:
            available = False

        return {
            "engine_type": self.get_engine_type().value,
            "supported_languages": [
                lang.value for lang in self.get_supported_languages()
            ],
            "supports_cloning": self.supports_voice_cloning(),
            "is_available": available,
        }

    def validate_request(self, request: GenerationRequest) -> None:
        """Validate a GenerationRequest before processing.

        Call this at the top of generate() and clone_voice() implementations.
        Returns None on success — raises on failure.

        Args:
            request: The request to validate.

        Raises:
            InvalidVoiceProfileError: If voice_profile is None.
            UnsupportedLanguageError: If the request language is not in
                this engine's get_supported_languages() list.
        """
        if request.voice_profile is None:
            raise InvalidVoiceProfileError(
                "GenerationRequest.voice_profile must not be None."
            )
        supported = self.get_supported_languages()
        if request.voice_profile.language not in supported:
            raise UnsupportedLanguageError(
                f"Engine '{self.get_engine_type().value}' does not support "
                f"language '{request.voice_profile.language.value}'. "
                f"Supported languages: {[l.value for l in supported]}"
            )
