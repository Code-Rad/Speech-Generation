"""
main.py
VoiceForge — FastAPI Application

THE FRONT DOOR. Defines the FastAPI app, all API routes, request/response
models, and error handling. This is the only file the outside world talks to.

WHAT THIS FILE DOES:
  - Instantiates the FastAPI app with CORS configured for local dev
  - Defines Pydantic request/response models for all endpoints
  - Implements 6 API routes (see ROUTES section below)
  - Loads voice profiles from server/voice_profiles/*.json on demand
  - Delegates all engine selection to EngineFactory (no engine logic here)
  - Streams generated audio files back as FileResponse

ROUTES:
  GET  /health          — Liveness probe (returns 200 OK with uptime/phase info)
  GET  /voices          — List all voice profiles with metadata
  GET  /engines         — Health status of all 4 TTS engines
  POST /generate        — Generate speech (text + profile_id → audio file)
  POST /clone-voice     — Upload reference audio; immediately generate a sample
  POST /generate-batch  — Generate multiple audio clips in one request

EXTERNAL DEPENDENCIES (all in requirements.txt):
  fastapi, uvicorn, pydantic, aiofiles, python-multipart

TO START:
  cd C:\\VoiceForge\\server
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import glob
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import get_phase, get_settings
from engine.base_engine import (
    EngineNotAvailableError,
    GenerationRequest,
    InvalidVoiceProfileError,
    Language,
    OutputFormat,
    UnsupportedLanguageError,
    VoiceProfile,
)
from engine.engine_factory import EngineFactory
from profile_manager import get_profile_manager, reload_profiles
from audio_validator import validate_reference_audio, process_reference_audio

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App startup timestamp (for /health uptime reporting) ──────────────────────
_STARTUP_TIME = time.monotonic()
_STARTUP_WALL = datetime.now(timezone.utc).isoformat()

# ── FastAPI Application ────────────────────────────────────────────────────────
app = FastAPI(
    title="VoiceForge",
    description=(
        "Broadcast-quality AI TTS platform. "
        "Generates professional voice audio in English, Hindi, and Hinglish "
        "using a swappable engine system with automatic fallback routing."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allows the Next.js frontend (localhost:3000) to call the API during development.
# In production, restrict origins to the actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "x-engine-used",
        "x-is-draft",
        "x-profile-id",
        "x-duration",
        "x-generation-time",
        "content-disposition",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Request / Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateRequest(BaseModel):
    """Request body for POST /generate."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The text to synthesise into speech.",
        examples=["Breaking news: Scientists discover a new species in the Amazon rainforest."],
    )
    profile_id: str = Field(
        ...,
        description=(
            "Voice profile ID. Must match one of the JSON filenames in "
            "server/voice_profiles/ (e.g. 'anchor_male_en')."
        ),
        examples=["anchor_male_en"],
    )
    output_format: str = Field(
        default="wav",
        description="Output audio format. 'wav' (default) or 'mp3'.",
        examples=["wav"],
    )
    require_cloning: bool = Field(
        default=False,
        description=(
            "If True, skip Edge TTS (it cannot clone voices). "
            "Use when voice identity consistency is required."
        ),
    )


class GenerateBatchItem(BaseModel):
    """One item in a batch generation request."""
    text: str = Field(..., min_length=1, max_length=5000)
    profile_id: str
    output_format: str = "wav"


class GenerateBatchRequest(BaseModel):
    """Request body for POST /generate-batch."""
    items: List[GenerateBatchItem] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of up to 20 generation requests to process sequentially.",
    )
    require_cloning: bool = False


class GenerateResponse(BaseModel):
    """Response body for POST /generate and POST /generate-batch items."""
    success: bool
    audio_path: str
    duration_seconds: float
    engine_used: str
    voice_profile_id: str
    language: str
    is_draft: bool
    error_message: str
    generation_time_seconds: float
    download_url: Optional[str] = None  # Set by the API layer if serving the file


class GenerateBatchResponse(BaseModel):
    """Response body for POST /generate-batch."""
    results: List[GenerateResponse]
    total_items: int
    succeeded: int
    failed: int
    total_time_seconds: float


class VoiceProfileResponse(BaseModel):
    """Voice profile metadata returned by GET /voices."""
    profile_id: str
    display_name: str
    language: str
    gender: str
    engine_preference: List[str]
    reference_audio_filename: str
    speaking_rate: float
    style: str
    description: str
    phase_available: int
    cloning_enabled: bool
    reference_audio_exists: bool  # Computed field — is the .wav actually present?


class EngineStatusResponse(BaseModel):
    """Engine status entry returned by GET /engines."""
    engine_type: str
    status: str
    is_available: bool
    supports_cloning: Optional[bool]
    supported_languages: List[str]
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str
    phase: int
    uptime_seconds: float
    started_at: str
    version: str


class CloneVoiceResponse(BaseModel):
    """Response body for POST /clone-voice (success 200)."""
    success: bool
    profile_id: str
    reference_audio_saved: bool
    reference_audio_path: Optional[str] = None
    duration_seconds: float = 0.0
    sample_rate: int = 0
    warnings: List[str] = []
    sample_generated: bool = False
    sample_audio_path: Optional[str] = None
    sample_engine_used: Optional[str] = None
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _load_voice_profile(profile_id: str) -> VoiceProfile:
    """Load and validate a voice profile by ID via the ProfileManager.

    Uses get_profile_manager() for correct path resolution regardless of
    which directory the server was started from.

    Args:
        profile_id: The profile_id string (no .json extension).

    Returns:
        A validated VoiceProfile instance.

    Raises:
        HTTPException 404: If the profile is not found.
        HTTPException 422: If the profile JSON is invalid (caught at load time).
    """
    manager = get_profile_manager()
    profile = manager.get_profile_by_id(profile_id)
    if profile is None:
        available = [p.profile_id for p in manager.get_all_profiles()]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Voice profile '{profile_id}' not found. "
                f"Available profiles: {available}"
            ),
        )
    return profile


def _list_profile_ids() -> List[str]:
    """Return all available voice profile IDs via the ProfileManager."""
    manager = get_profile_manager()
    return [p.profile_id for p in manager.get_all_profiles()]


def _resolve_output_dir() -> Path:
    """Resolve OUTPUT_DIR to an absolute path regardless of server CWD.

    Uses __file__ so the path is always relative to this file's location
    (C:\\VoiceForge\\server\\), not the working directory uvicorn was started from.
    This prevents the 'server/server/output' nested-directory bug that occurs
    when uvicorn is started from C:\\VoiceForge\\server\\.

    Resolution order:
      1. Project-root-relative (parent of server/) — handles 'server/output' setting
      2. Direct sibling of main.py — hardcoded last resort

    Returns:
        Absolute Path to the output directory (created if missing).
    """
    s = get_settings()
    dir_setting = s.OUTPUT_DIR           # e.g. "server/output"
    server_dir  = Path(__file__).parent  # Always C:\VoiceForge\server\
    project_root = server_dir.parent     # Always C:\VoiceForge\

    # Candidate 1: project-root-relative (most common case for "server/output")
    candidate = (project_root / dir_setting).resolve()
    if candidate.exists() and candidate.is_dir():
        return candidate

    # Candidate 2: direct sibling of main.py
    fallback = (server_dir / "output").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _make_output_path(profile_id: str, fmt: str) -> str:
    """Generate a unique output file path in the configured output directory.

    Args:
        profile_id: Voice profile ID (used as a readable prefix).
        fmt: File extension without leading dot — 'wav' or 'mp3'.

    Returns:
        Absolute path string for the output audio file.
    """
    output_dir = _resolve_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{profile_id}_{timestamp}_{unique_id}.{fmt}"
    return str(output_dir / filename)


def _parse_output_format(fmt_str: str) -> OutputFormat:
    """Parse an output format string into an OutputFormat enum.

    Args:
        fmt_str: "wav" or "mp3" (case-insensitive).

    Returns:
        OutputFormat enum value.

    Raises:
        HTTPException 422: If the format string is not recognised.
    """
    try:
        return OutputFormat(fmt_str.lower().strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid output format '{fmt_str}'. Valid values: wav, mp3",
        )


def _result_to_response(result, download_url: Optional[str] = None) -> GenerateResponse:
    """Convert a GenerationResult dataclass to a GenerateResponse Pydantic model."""
    return GenerateResponse(
        success=result.success,
        audio_path=result.audio_path,
        duration_seconds=result.duration_seconds,
        engine_used=result.engine_used.value,
        voice_profile_id=result.voice_profile_id,
        language=result.language.value,
        is_draft=result.is_draft,
        error_message=result.error_message,
        generation_time_seconds=result.generation_time_seconds,
        download_url=download_url,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    tags=["System"],
)
def health() -> HealthResponse:
    """Return server liveness status, current phase, and uptime.

    Always returns HTTP 200 if the server is running. Used by load balancers,
    orchestrators, and the frontend engine dashboard.
    """
    return HealthResponse(
        status="ok",
        phase=get_phase(),
        uptime_seconds=round(time.monotonic() - _STARTUP_TIME, 1),
        started_at=_STARTUP_WALL,
        version=app.version,
    )


@app.get(
    "/voices",
    response_model=List[VoiceProfileResponse],
    summary="List all voice profiles",
    tags=["Voices"],
)
def list_voices() -> List[VoiceProfileResponse]:
    """Return metadata for all configured voice profiles.

    Uses ProfileManager for correct path resolution and centralised loading.
    Also reports whether the reference audio file exists on disk —
    if missing, the engine will fall back to a default speaker.

    Returns:
        List of VoiceProfileResponse objects, one per loaded .json profile file.
    """
    manager = get_profile_manager()
    summaries = manager.get_profiles_summary()

    return [
        VoiceProfileResponse(
            profile_id=s["profile_id"],
            display_name=s["display_name"],
            language=s["language"],
            gender=s["gender"],
            engine_preference=s["engine_preference"],
            reference_audio_filename=s["reference_audio_filename"],
            speaking_rate=s["speaking_rate"],
            style=s["style"],
            description=s["description"],
            phase_available=s["phase_available"],
            cloning_enabled=s["cloning_enabled"],
            reference_audio_exists=s["reference_audio_exists"],
        )
        for s in summaries
    ]


@app.get(
    "/engines",
    response_model=List[EngineStatusResponse],
    summary="Engine health status",
    tags=["System"],
)
def engine_status() -> List[EngineStatusResponse]:
    """Return real-time availability status for all 4 TTS engines.

    Calls is_available() on each engine — this is fast (< 1 second each).
    Engines that are placeholder-only or missing dependencies return status='not_built'.
    Never crashes — errors per engine are caught and reported in the 'error' field.

    Returns:
        List of 4 EngineStatusResponse objects, one per EngineType.
    """
    raw_statuses = EngineFactory.get_all_engine_status()
    return [
        EngineStatusResponse(
            engine_type=s["engine_type"],
            status=s["status"],
            is_available=s.get("is_available", False),
            supports_cloning=s.get("supports_cloning"),
            supported_languages=s.get("supported_languages", []),
            error=s.get("error"),
        )
        for s in raw_statuses
    ]


@app.post(
    "/generate",
    summary="Generate speech from text",
    tags=["Generation"],
)
def generate(request: GenerateRequest) -> FileResponse:
    """Generate broadcast-quality speech from a text script.

    Selects the best available engine for the voice profile's language using the
    configured fallback chain. Returns the generated audio file directly.

    Args (JSON body):
        text: The text to synthesise (1–5000 characters).
        profile_id: Voice profile ID (e.g. 'anchor_male_en').
        output_format: 'wav' (default) or 'mp3'.
        require_cloning: If True, skip Edge TTS (no voice cloning support).

    Returns:
        The generated audio file as a binary download (audio/wav or audio/mpeg).

    HTTP errors:
        404: Voice profile not found.
        422: Invalid profile JSON or unsupported output format.
        503: No TTS engine is available for the requested language/phase.
        500: Engine returned an unexpected error.
    """
    # 1. Load and validate voice profile
    profile = _load_voice_profile(request.profile_id)

    # 2. Parse output format
    fmt = _parse_output_format(request.output_format)

    # 3. Build output path
    output_path = _make_output_path(request.profile_id, fmt.value)

    # 4. Build GenerationRequest
    gen_request = GenerationRequest(
        text=request.text,
        voice_profile=profile,
        output_path=output_path,
        output_format=fmt,
    )

    # 5. Route to best available engine
    try:
        engine = EngineFactory.get_engine_for_request(
            language=profile.language,
            require_cloning=request.require_cloning,
        )
    except EngineNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # 6. Generate audio
    try:
        if profile.cloning_enabled:
            # Prefer clone_voice() if supported and reference audio exists
            ref_path = Path(get_settings().REFERENCE_AUDIO_DIR) / profile.reference_audio_filename
            if engine.supports_voice_cloning() and ref_path.exists():
                result = engine.clone_voice(gen_request, str(ref_path))
            else:
                result = engine.generate(gen_request)
        else:
            result = engine.generate(gen_request)

    except UnsupportedLanguageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Generation failed for profile '%s': %s", request.profile_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {exc}",
        )

    # 7. Return generated file
    if not Path(result.audio_path).exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Engine reported success but output file not found: '{result.audio_path}'",
        )

    media_type = "audio/mpeg" if result.audio_path.endswith(".mp3") else "audio/wav"
    filename = Path(result.audio_path).name

    logger.info(
        "Served audio: profile=%s, engine=%s, draft=%s, duration=%.1fs, file=%s",
        request.profile_id, result.engine_used.value,
        result.is_draft, result.duration_seconds, filename,
    )

    return FileResponse(
        path=result.audio_path,
        media_type=media_type,
        filename=filename,
        headers={
            "X-Engine-Used": result.engine_used.value,
            "X-Is-Draft": str(result.is_draft).lower(),
            "X-Duration-Seconds": str(round(result.duration_seconds, 2)),
            "X-Generation-Time": str(round(result.generation_time_seconds, 2)),
            "X-Voice-Profile": result.voice_profile_id,
            "X-Language": result.language.value,
        },
    )


@app.post(
    "/clone-voice",
    response_model=CloneVoiceResponse,
    summary="Upload reference audio for voice cloning",
    tags=["Voices"],
)
async def clone_voice(
    profile_id: str = Form(
        ...,
        description="Target voice profile ID (e.g. 'anchor_male_en').",
    ),
    audio_file: UploadFile = File(
        ...,
        description="Reference audio file — WAV or MP3, 10–60 seconds of clear speech.",
    ),
    generate_sample: bool = Form(
        default=True,
        description=(
            "If True (default), immediately generate a short sample clip "
            "after upload to confirm the pipeline is working."
        ),
    ),
) -> CloneVoiceResponse:
    """Upload and validate a reference audio file for voice cloning.

    Full pipeline:
      1. Validate profile exists
      2. Save upload to a temp file (preserving extension)
      3. Validate audio quality (duration, sample rate, silence, size)
      4. If validation fails: delete temp, return 422 with error details
      5. Back up existing reference audio if present
      6. Process audio (convert to WAV, mono, 22050 Hz, normalise amplitude)
      7. Save processed WAV to server/reference_audio/<profile's filename>
      8. Delete temp file; reload ProfileManager
      9. Optionally generate a sample clip to confirm the upload worked

    Args (multipart/form-data):
        profile_id:      Voice profile ID (determines save filename).
        audio_file:      WAV or MP3 — 10–60 seconds, broadcast-quality speech.
        generate_sample: Whether to immediately generate a sample clip (default True).

    Returns:
        CloneVoiceResponse with saved-path, audio metrics, warnings, sample info.

    HTTP errors:
        404: Voice profile not found.
        422: Audio validation failed (too short, silent, wrong format, etc.).
        500: Unexpected file I/O or processing error.
    """
    import tempfile  # noqa: PLC0415 (stdlib — always available)
    import shutil    # noqa: PLC0415

    # ── Step 1: Validate profile ──────────────────────────────────────────────
    profile = _load_voice_profile(profile_id)

    # ── Step 2: Save upload to temp file (keep original extension) ────────────
    original_filename = audio_file.filename or "upload.wav"
    ext = Path(original_filename).suffix.lower() or ".wav"
    if ext not in (".wav", ".mp3"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "profile_id": profile_id,
                "error": (
                    f"Unsupported file type '{ext}'. "
                    f"Upload a WAV or MP3 file."
                ),
                "duration_seconds": 0.0,
            },
        )

    s = get_settings()
    manager = get_profile_manager()
    ref_dir = (
        manager._reference_audio_dir
        if manager._reference_audio_dir is not None
        else Path(s.REFERENCE_AUDIO_DIR)
    )
    ref_dir.mkdir(parents=True, exist_ok=True)

    # Write upload to a uniquely-named temp file in the output dir
    tmp_name = f"_tmp_upload_{uuid.uuid4().hex[:8]}{ext}"
    tmp_path = _resolve_output_dir() / tmp_name

    try:
        audio_bytes = await audio_file.read()
        tmp_path.write_bytes(audio_bytes)
        logger.debug("Saved upload to temp: %s (%d bytes)", tmp_path, len(audio_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file to temp location: {exc}",
        )

    final_path = ref_dir / profile.reference_audio_filename
    backup_path: Optional[Path] = None

    try:
        # ── Step 3: Validate audio ────────────────────────────────────────────
        validation = validate_reference_audio(str(tmp_path))
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "profile_id": profile_id,
                    "error": validation.error_message,
                    "duration_seconds": validation.duration_seconds,
                },
            )

        # ── Step 4: Back up existing reference audio if present ───────────────
        if final_path.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = final_path.with_name(
                f"{final_path.stem}_backup_{ts}{final_path.suffix}"
            )
            shutil.copy2(str(final_path), str(backup_path))
            logger.info(
                "Backed up existing reference audio: %s → %s",
                final_path.name, backup_path.name,
            )

        # ── Step 5: Process and save to final location ────────────────────────
        process_result = process_reference_audio(str(tmp_path), str(final_path))
        if not process_result.is_valid:
            # Processing failed — restore backup if we made one
            if backup_path and backup_path.exists():
                shutil.copy2(str(backup_path), str(final_path))
                backup_path.unlink(missing_ok=True)
                logger.warning("Restored backup after processing failure")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "profile_id": profile_id,
                    "error": f"Audio processing failed: {process_result.error_message}",
                    "duration_seconds": process_result.duration_seconds,
                },
            )

        logger.info(
            "Reference audio saved: profile=%s, path=%s, duration=%.1fs, rate=%d Hz",
            profile_id, final_path,
            process_result.duration_seconds, process_result.sample_rate,
        )

        # Clean up backup on success
        if backup_path and backup_path.exists():
            backup_path.unlink(missing_ok=True)

    finally:
        # ── Step 6: Always delete temp file ──────────────────────────────────
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Step 7: Reload ProfileManager (reference_audio_exists now True) ───────
    reload_profiles()

    # ── Step 8: Optionally generate a sample clip ─────────────────────────────
    sample_generated = False
    sample_audio_path: Optional[str] = None
    sample_engine_used: Optional[str] = None

    if generate_sample:
        sample_text = (
            f"This is a sample of the cloned anchor voice "
            f"for {profile.display_name}."
        )
        sample_output = _make_output_path(f"{profile_id}_sample", "wav")
        try:
            # Use require_cloning=False so Edge TTS is available in Phase 1
            # (XTTS v2 model not downloaded yet — Edge TTS confirms upload pipeline)
            engine = EngineFactory.get_engine_for_request(
                language=profile.language,
                require_cloning=False,
            )
            gen_request = GenerationRequest(
                text=sample_text,
                voice_profile=profile,
                output_path=sample_output,
                output_format=OutputFormat.WAV,
            )
            # Run generate() in a thread pool: this is an async endpoint so there's
            # already an event loop running — engine.generate() calls asyncio.run()
            # internally (Edge TTS), which would fail if called directly here.
            # asyncio.to_thread() runs it in a worker thread where no loop is active.
            import asyncio as _asyncio  # noqa: PLC0415
            result = await _asyncio.to_thread(engine.generate, gen_request)
            sample_generated = True
            sample_audio_path = result.audio_path
            sample_engine_used = result.engine_used.value
            logger.info(
                "Sample generated: engine=%s, path=%s",
                sample_engine_used, sample_audio_path,
            )
        except Exception as exc:
            logger.warning(
                "Sample generation skipped (%s). Upload still succeeded.",
                exc,
            )

    # ── Step 9: Return success ────────────────────────────────────────────────
    msg_parts = [
        f"Reference audio uploaded and validated for '{profile.display_name}'.",
        f"Duration: {process_result.duration_seconds:.1f}s at {process_result.sample_rate} Hz.",
    ]
    if process_result.warnings:
        msg_parts.append(f"Warnings: {'; '.join(process_result.warnings)}")
    msg_parts.append(
        "Sample generated successfully." if sample_generated
        else "Sample generation skipped."
    )

    return CloneVoiceResponse(
        success=True,
        profile_id=profile_id,
        reference_audio_saved=True,
        reference_audio_path=str(final_path),
        duration_seconds=process_result.duration_seconds,
        sample_rate=process_result.sample_rate,
        warnings=process_result.warnings,
        sample_generated=sample_generated,
        sample_audio_path=sample_audio_path,
        sample_engine_used=sample_engine_used,
        message=" ".join(msg_parts),
    )


@app.post(
    "/generate-batch",
    response_model=GenerateBatchResponse,
    summary="Generate multiple audio clips in one request",
    tags=["Generation"],
)
def generate_batch(request: GenerateBatchRequest) -> GenerateBatchResponse:
    """Generate multiple audio segments sequentially in a single request.

    Each item is processed independently — failures in one item do not
    stop processing of subsequent items. Each failed item is included
    in the results with success=False and error_message populated.

    Args (JSON body):
        items: List of up to 20 GenerateBatchItem objects.
        require_cloning: If True, skip Edge TTS for all items.

    Returns:
        GenerateBatchResponse with per-item results and aggregate statistics.
    """
    start_time = time.monotonic()
    results: List[GenerateResponse] = []
    succeeded = 0
    failed = 0

    for item in request.items:
        try:
            # Load profile
            profile = _load_voice_profile(item.profile_id)
            fmt = _parse_output_format(item.output_format)
            output_path = _make_output_path(item.profile_id, fmt.value)

            gen_request = GenerationRequest(
                text=item.text,
                voice_profile=profile,
                output_path=output_path,
                output_format=fmt,
            )

            # Route to engine
            engine = EngineFactory.get_engine_for_request(
                language=profile.language,
                require_cloning=request.require_cloning,
            )

            # Generate
            s = get_settings()
            ref_path = Path(s.REFERENCE_AUDIO_DIR) / profile.reference_audio_filename
            if (
                profile.cloning_enabled
                and engine.supports_voice_cloning()
                and ref_path.exists()
            ):
                result = engine.clone_voice(gen_request, str(ref_path))
            else:
                result = engine.generate(gen_request)

            results.append(_result_to_response(result))
            succeeded += 1

        except HTTPException as exc:
            # Re-package HTTP exceptions as failed items (don't abort the batch)
            results.append(
                GenerateResponse(
                    success=False,
                    audio_path="",
                    duration_seconds=0.0,
                    engine_used="",
                    voice_profile_id=item.profile_id,
                    language="",
                    is_draft=False,
                    error_message=exc.detail,
                    generation_time_seconds=0.0,
                )
            )
            failed += 1
        except Exception as exc:
            logger.error(
                "Batch item failed (profile=%s): %s", item.profile_id, exc, exc_info=True
            )
            results.append(
                GenerateResponse(
                    success=False,
                    audio_path="",
                    duration_seconds=0.0,
                    engine_used="",
                    voice_profile_id=item.profile_id,
                    language="",
                    is_draft=False,
                    error_message=str(exc),
                    generation_time_seconds=0.0,
                )
            )
            failed += 1

    total_time = time.monotonic() - start_time
    logger.info(
        "Batch complete: %d/%d succeeded in %.2fs",
        succeeded, len(request.items), total_time,
    )

    return GenerateBatchResponse(
        results=results,
        total_items=len(request.items),
        succeeded=succeeded,
        failed=failed,
        total_time_seconds=round(total_time, 2),
    )


# ── Dev runner ─────────────────────────────────────────────────────────────────
# Run directly for development: python main.py
# For production: uvicorn main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
