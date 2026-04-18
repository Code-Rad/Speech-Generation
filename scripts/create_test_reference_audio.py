"""
create_test_reference_audio.py
VoiceForge — Test Reference Audio Generator

Creates a test reference audio file using Edge TTS for use in
testing the voice cloning upload pipeline.

Generated file:
  server/reference_audio/test_reference_audio.wav
  ~15 seconds of clear English broadcast speech

Usage:
  python scripts/create_test_reference_audio.py
  (run from C:\\VoiceForge\\ or C:\\VoiceForge\\server\\)
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow running from project root or from server/
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_SERVER_DIR = _PROJECT_ROOT / "server"

sys.path.insert(0, str(_SERVER_DIR))

# ── Constants ─────────────────────────────────────────────────────────────────
REFERENCE_SPEECH = (
    "Hello, I am a professional news anchor. "
    "Today we bring you the latest developments from around the world. "
    "Our top story this hour involves significant changes in technology "
    "and artificial intelligence that are reshaping how we consume information. "
    "Scientists have made a breakthrough discovery that promises to transform "
    "the way broadcast media operates in the digital age."
)

VOICE = "en-US-GuyNeural"  # Male English neural voice

OUTPUT_RELATIVE = "server/reference_audio/test_reference_audio.wav"


async def _stream_edge_tts(text: str, voice: str) -> bytes:
    """Stream audio bytes from Edge TTS cloud API."""
    try:
        import edge_tts  # noqa: PLC0415
    except ImportError:
        raise SystemExit(
            "edge-tts not installed. Run: pip install edge-tts"
        )

    communicate = edge_tts.Communicate(text, voice)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])

    if not chunks:
        raise RuntimeError("Edge TTS returned no audio data")
    return b"".join(chunks)


def _mp3_bytes_to_wav(mp3_bytes: bytes, wav_path: Path) -> None:
    """Convert raw MP3 bytes → WAV file via soundfile."""
    try:
        import soundfile as sf  # noqa: PLC0415
    except ImportError:
        raise SystemExit(
            "soundfile not installed. Run: pip install soundfile"
        )

    buf = io.BytesIO(mp3_bytes)
    audio_data, sample_rate = sf.read(buf)
    sf.write(str(wav_path), audio_data, sample_rate)


def main() -> None:
    """Generate and save the test reference audio file."""
    # Resolve output path — works from project root or server/
    candidates = [
        Path.cwd() / OUTPUT_RELATIVE,
        _PROJECT_ROOT / OUTPUT_RELATIVE,
        _SERVER_DIR / "reference_audio" / "test_reference_audio.wav",
    ]
    output_path = None
    for candidate in candidates:
        if candidate.parent.exists():
            output_path = candidate
            break

    if output_path is None:
        # Create directory and use first candidate
        output_path = candidates[1]
        output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generating test reference audio...")
    print(f"Voice: {VOICE}")
    print(f"Text: {REFERENCE_SPEECH[:60]}...")

    mp3_bytes = asyncio.run(_stream_edge_tts(REFERENCE_SPEECH, VOICE))
    print(f"Received {len(mp3_bytes):,} bytes of MP3 audio from Edge TTS")

    _mp3_bytes_to_wav(mp3_bytes, output_path)

    size_bytes = output_path.stat().st_size
    print(f"\nSaved: {output_path}")
    print(f"File size: {size_bytes:,} bytes ({size_bytes / 1024:.1f} KB)")

    # Report actual duration
    try:
        import soundfile as sf  # noqa: PLC0415
        info = sf.info(str(output_path))
        print(f"Duration: {info.duration:.1f} seconds")
        print(f"Sample rate: {info.samplerate} Hz")
        print(f"Channels: {info.channels}")
    except Exception:
        pass

    print("\nTest reference audio ready for upload pipeline testing.")


if __name__ == "__main__":
    main()
