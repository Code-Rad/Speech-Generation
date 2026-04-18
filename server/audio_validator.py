"""
audio_validator.py
VoiceForge — Reference Audio Validator & Processor

Validates and processes uploaded reference audio files
before they are saved as voice cloning references.

Validation checks (in order):
  1. File exists on disk
  2. File size within bounds (50KB – 50MB)
  3. File extension is .wav or .mp3
  4. File is readable as audio (soundfile)
  5. Duration within bounds (10 – 60 seconds)
  6. Sample rate at or above minimum (16000 Hz)
  7. Not pure silence (RMS energy check)

Processing (auto-applied after validation passes):
  - MP3 to WAV conversion  (soundfile handles both)
  - Stereo to mono          (average the two channels)
  - Sample rate normalisation to 22050 Hz
  - Amplitude normalisation (peak → 0.95, prevents clipping)
  - Output is always WAV regardless of input format

Dependencies:
  soundfile >= 0.12.1   (pip install soundfile)
  numpy     >= 1.26.0   (pip install numpy)

No other dependencies — no scipy, no ffmpeg, no pydub.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AudioValidationResult:
    """Outcome of a validate() or process() call.

    Fields:
        is_valid:           True if audio passed all checks.
        error_message:      Non-empty string describing the first failed check.
                            Empty string on success.
        duration_seconds:   Measured audio duration (0.0 if unreadable).
        sample_rate:        Detected sample rate in Hz (0 if unreadable).
        channels:           Number of audio channels (0 if unreadable).
        file_size_bytes:    Raw file size in bytes (0 if file missing).
        warnings:           Non-fatal issues — audio is still accepted but
                            quality may be suboptimal.
    """
    is_valid: bool
    error_message: str
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    file_size_bytes: int = 0
    warnings: List[str] = field(default_factory=list)


class AudioValidator:
    """Validates and processes reference audio for voice cloning.

    All public methods catch every exception internally — they never raise.
    Callers check ``result.is_valid`` to determine success/failure.

    Usage:
        validator = AudioValidator()
        result = validator.validate("path/to/upload.wav")
        if result.is_valid:
            result = validator.process("path/to/upload.wav", "path/to/save.wav")
    """

    # ── Quality thresholds ────────────────────────────────────────────────────
    MIN_DURATION_SECONDS: float = 10.0
    MAX_DURATION_SECONDS: float = 60.0
    MIN_FILE_SIZE_BYTES:  int   = 50_000        # 50 KB
    MAX_FILE_SIZE_BYTES:  int   = 50_000_000    # 50 MB
    TARGET_SAMPLE_RATE:   int   = 22050         # Hz — XTTS v2 native rate
    MIN_SAMPLE_RATE:      int   = 16000         # Hz — minimum acceptable
    SILENCE_THRESHOLD:    float = 0.01          # RMS below this → silence
    ALLOWED_EXTENSIONS: frozenset = frozenset({".wav", ".mp3"})

    # Warning thresholds (non-fatal — audio still accepted)
    _WARN_SHORT_DURATION:    float = 15.0   # seconds — cloning may be poor
    _WARN_LONG_DURATION:     float = 45.0   # seconds — longer than needed
    _WARN_LOW_SAMPLE_RATE:   int   = 22050  # Hz — will be resampled

    # ── Public API ────────────────────────────────────────────────────────────

    def validate(self, file_path: str) -> AudioValidationResult:
        """Run all validation checks on an audio file.

        Returns immediately after the first fatal failure (short-circuit).
        Non-fatal warnings are accumulated but do not block acceptance.

        Args:
            file_path: Absolute or relative path to the audio file.

        Returns:
            AudioValidationResult — never raises.
        """
        warnings: List[str] = []
        path = Path(file_path)

        # ── Check 1: File exists ──────────────────────────────────────────────
        if not path.exists():
            return AudioValidationResult(
                is_valid=False,
                error_message=f"Audio file not found: '{file_path}'",
            )

        # ── Check 2: File size ────────────────────────────────────────────────
        try:
            size_bytes = path.stat().st_size
        except OSError as exc:
            return AudioValidationResult(
                is_valid=False,
                error_message=f"Cannot read file metadata: {exc}",
            )

        if size_bytes < self.MIN_FILE_SIZE_BYTES:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"File too small: {size_bytes / 1024:.1f} KB "
                    f"(minimum {self.MIN_FILE_SIZE_BYTES // 1024} KB required). "
                    f"Upload a longer or higher-quality reference audio."
                ),
                file_size_bytes=size_bytes,
            )

        if size_bytes > self.MAX_FILE_SIZE_BYTES:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"File too large: {size_bytes / 1_000_000:.1f} MB "
                    f"(maximum {self.MAX_FILE_SIZE_BYTES // 1_000_000} MB). "
                    f"Trim the audio to under 60 seconds."
                ),
                file_size_bytes=size_bytes,
            )

        # ── Check 3: File extension ───────────────────────────────────────────
        ext = path.suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Unsupported file format: '{ext}'. "
                    f"Upload a WAV or MP3 file."
                ),
                file_size_bytes=size_bytes,
            )

        # ── Check 4: Readable as audio ────────────────────────────────────────
        try:
            audio_data, sample_rate = self._load_audio(file_path)
        except Exception as exc:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Cannot read audio data: {exc}. "
                    f"Ensure the file is a valid, uncorrupted WAV or MP3."
                ),
                file_size_bytes=size_bytes,
            )

        # Measure shape
        import numpy as np  # noqa: PLC0415 (lazy import for startup speed)
        if audio_data.ndim == 1:
            channels = 1
            n_samples = len(audio_data)
        else:
            channels = audio_data.shape[1]
            n_samples = audio_data.shape[0]

        duration = n_samples / sample_rate

        # ── Check 5: Duration ─────────────────────────────────────────────────
        if duration < self.MIN_DURATION_SECONDS:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Audio too short: {duration:.1f} seconds "
                    f"(minimum {self.MIN_DURATION_SECONDS:.0f} seconds required). "
                    f"Upload at least 10 seconds of clear speech."
                ),
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                file_size_bytes=size_bytes,
            )

        if duration > self.MAX_DURATION_SECONDS:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Audio too long: {duration:.1f} seconds "
                    f"(maximum {self.MAX_DURATION_SECONDS:.0f} seconds). "
                    f"Trim the recording to under 60 seconds."
                ),
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                file_size_bytes=size_bytes,
            )

        # ── Check 6: Sample rate ──────────────────────────────────────────────
        if sample_rate < self.MIN_SAMPLE_RATE:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Sample rate too low: {sample_rate} Hz "
                    f"(minimum {self.MIN_SAMPLE_RATE} Hz). "
                    f"Re-record or resample to at least 16 kHz."
                ),
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                file_size_bytes=size_bytes,
            )

        # ── Check 7: Silence detection ────────────────────────────────────────
        mono = self._to_mono(audio_data)
        rms = self._calculate_rms(mono)
        if rms < self.SILENCE_THRESHOLD:
            return AudioValidationResult(
                is_valid=False,
                error_message=(
                    f"Audio contains no speech (RMS energy {rms:.4f} "
                    f"below threshold {self.SILENCE_THRESHOLD}). "
                    f"Upload a recording with clear voice content."
                ),
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                file_size_bytes=size_bytes,
            )

        # ── Accumulate warnings ───────────────────────────────────────────────
        if duration < self._WARN_SHORT_DURATION:
            warnings.append(
                f"Duration {duration:.1f}s is under 15 seconds — "
                f"clone quality may be suboptimal. Use 15–30 seconds for best results."
            )
        if duration > self._WARN_LONG_DURATION:
            warnings.append(
                f"Duration {duration:.1f}s exceeds 45 seconds — "
                f"longer than needed; 15–30 seconds is ideal."
            )
        if sample_rate < self._WARN_LOW_SAMPLE_RATE:
            warnings.append(
                f"Sample rate {sample_rate} Hz will be resampled to "
                f"{self.TARGET_SAMPLE_RATE} Hz during processing."
            )
        if channels > 1:
            warnings.append(
                f"Stereo audio ({channels} channels) will be converted to mono."
            )

        return AudioValidationResult(
            is_valid=True,
            error_message="",
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            file_size_bytes=size_bytes,
            warnings=warnings,
        )

    def process(self, input_path: str, output_path: str) -> AudioValidationResult:
        """Validate then process audio — normalise format, rate, amplitude.

        Only writes ``output_path`` if validation passes. Processing steps:
          1. Validate (all 7 checks)
          2. Load audio with soundfile
          3. Convert stereo → mono
          4. Resample to TARGET_SAMPLE_RATE if needed
          5. Normalise amplitude (peak → 0.95)
          6. Write as WAV to output_path

        Args:
            input_path:  Source audio file (.wav or .mp3).
            output_path: Destination path — always written as WAV.

        Returns:
            AudioValidationResult describing the *processed* file.
            If validation fails: result with is_valid=False, output_path NOT written.
            If processing fails: result with is_valid=False, specific error.
        """
        # Step 1 — Validate first; reject bad audio before touching output_path
        validation_result = self.validate(input_path)
        if not validation_result.is_valid:
            return validation_result

        # Step 2 — Load audio
        try:
            audio_data, sample_rate = self._load_audio(input_path)
        except Exception as exc:
            return AudioValidationResult(
                is_valid=False,
                error_message=f"Processing failed during audio load: {exc}",
            )

        try:
            import numpy as np  # noqa: PLC0415

            # Step 3 — Convert stereo to mono
            if audio_data.ndim > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
                logger.debug("Converted stereo to mono")
            elif audio_data.ndim > 1:
                audio_data = audio_data[:, 0]

            # Step 4 — Resample if needed
            if sample_rate != self.TARGET_SAMPLE_RATE:
                audio_data = self._resample(audio_data, sample_rate, self.TARGET_SAMPLE_RATE)
                logger.debug("Resampled %d Hz → %d Hz", sample_rate, self.TARGET_SAMPLE_RATE)

            # Step 5 — Amplitude normalisation
            peak = float(np.max(np.abs(audio_data)))
            if peak > 0:
                audio_data = audio_data / peak * 0.95
                logger.debug("Amplitude normalised: peak %.4f → 0.95", peak)

            # Step 6 — Write WAV
            import soundfile as sf  # noqa: PLC0415
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out), audio_data, self.TARGET_SAMPLE_RATE, subtype="PCM_16")
            logger.info("Processed audio saved: %s", output_path)

        except Exception as exc:
            return AudioValidationResult(
                is_valid=False,
                error_message=f"Processing step failed: {exc}",
            )

        # Re-measure the processed file
        n_samples = len(audio_data)
        actual_duration = n_samples / self.TARGET_SAMPLE_RATE
        file_size = Path(output_path).stat().st_size

        return AudioValidationResult(
            is_valid=True,
            error_message="",
            duration_seconds=actual_duration,
            sample_rate=self.TARGET_SAMPLE_RATE,
            channels=1,
            file_size_bytes=file_size,
            warnings=validation_result.warnings,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _load_audio(self, file_path: str) -> Tuple:
        """Load audio file and return (audio_data, sample_rate).

        Supports WAV and MP3 via soundfile + libsndfile.

        Args:
            file_path: Path to .wav or .mp3 file.

        Returns:
            Tuple of (numpy.ndarray, int) — audio data and sample rate.

        Raises:
            Exception: If soundfile cannot read the file.
        """
        import soundfile as sf  # noqa: PLC0415
        audio_data, sample_rate = sf.read(file_path, always_2d=False)
        return audio_data, sample_rate

    @staticmethod
    def _to_mono(audio_data) -> "np.ndarray":
        """Convert audio_data to 1-D mono array (no-op if already mono)."""
        import numpy as np  # noqa: PLC0415
        if audio_data.ndim > 1:
            return np.mean(audio_data, axis=1)
        return audio_data

    @staticmethod
    def _calculate_rms(audio_data) -> float:
        """Calculate Root Mean Square energy — a measure of audio loudness.

        Args:
            audio_data: 1-D numpy array of normalised float samples.

        Returns:
            RMS value in [0.0, 1.0]. Values below SILENCE_THRESHOLD
            indicate silence or pure noise with no meaningful speech.
        """
        import numpy as np  # noqa: PLC0415
        if len(audio_data) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_data.astype(np.float64) ** 2)))

    @staticmethod
    def _resample(audio_data, orig_rate: int, target_rate: int):
        """Resample 1-D audio_data from orig_rate to target_rate.

        Uses numpy linear interpolation — no scipy dependency.

        Args:
            audio_data: 1-D numpy float array.
            orig_rate:  Original sample rate in Hz.
            target_rate: Target sample rate in Hz.

        Returns:
            Resampled 1-D numpy float array.
        """
        import numpy as np  # noqa: PLC0415
        orig_len = len(audio_data)
        target_len = int(orig_len * target_rate / orig_rate)
        orig_times = np.linspace(0, 1, orig_len)
        target_times = np.linspace(0, 1, target_len)
        return np.interp(target_times, orig_times, audio_data).astype(audio_data.dtype)


# ── Module-level convenience functions ────────────────────────────────────────

def validate_reference_audio(file_path: str) -> AudioValidationResult:
    """Validate a reference audio file.

    Args:
        file_path: Path to .wav or .mp3 audio file.

    Returns:
        AudioValidationResult — never raises.
    """
    return AudioValidator().validate(file_path)


def process_reference_audio(input_path: str, output_path: str) -> AudioValidationResult:
    """Validate and process a reference audio file.

    Writes processed WAV to output_path only if validation passes.

    Args:
        input_path:  Source .wav or .mp3 file.
        output_path: Destination path for the processed WAV.

    Returns:
        AudioValidationResult — never raises.
    """
    return AudioValidator().process(input_path, output_path)
